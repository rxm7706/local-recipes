"""Unit tests for ``pyforge.doctor.sources.chain.gather_due_for_verification``
(Story 11.1, Epic 11/CAP-1) -- covers every row of the spec's I/O &
Edge-Case Matrix against REAL tmp fixture trees, mirroring
``test_sources_chain_deferred_work.py``'s own real-fixture discipline (no
mocks).

Precise day-count assertions go through ``chain._due_for_verification_findings``
directly, using its injectable ``today`` kwarg (Boundaries: "tests never
depend on wall-clock today()"). Finding-shape / wiring-level assertions go
through the public ``chain.gather_due_for_verification`` and deliberately
avoid the ``today`` question altogether by using fixtures whose outcome is
time-invariant: a missing ``verified:`` line (always "never-verified") or a
far-future ``verified:`` date (always "fresh", since ``days_stale`` is
negative for as long as this suite exists).
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from pyforge.doctor.cli_bridge import CliBridgeError
from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import chain

# --- fixture helpers ---------------------------------------------------------


def _project_dir(target: Path, project: str) -> Path:
    return target / "_bmad-output" / "projects" / project


def _write_tracked(target: Path, project: str, text: str) -> Path:
    path = _project_dir(target, project) / "planning-artifacts" / "deferred-work-ledger.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _tracked_rel(project: str) -> str:
    return f"_bmad-output/projects/{project}/planning-artifacts/deferred-work-ledger.md"


# --- git fixture helpers (Story 11.2: churn checks need REAL, dated git
# history) -- mirrors test_sources_marshal_story_status.py's own
# _isolate_git_env/_init_repo/_commit pattern; this test file is not subject
# to the package's sole-subprocess restriction (only pyforge/doctor/
# cli_bridge.py is), so driving real `git` here to build fixtures is fine. ---

_LEAKY_GIT_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_CEILING_DIRECTORIES",
    "GIT_COMMON_DIR",
)


@pytest.fixture(autouse=True)
def _isolate_git_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _LEAKY_GIT_VARS:
        monkeypatch.delenv(var, raising=False)


def _git(target: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=target,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _init_repo(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    _git(target, "init", "-q", "--initial-branch=main")
    _git(target, "config", "user.email", "doctor-test@example.com")
    _git(target, "config", "user.name", "Doctor Test")
    _git(target, "config", "commit.gpgsign", "false")
    _git(target, "config", "core.hooksPath", "/dev/null")


def _commit_file(target: Path, rel_path: str, content: str, when: str) -> None:
    """Write ``rel_path`` under ``target`` with ``content`` and commit it,
    pinning BOTH ``GIT_AUTHOR_DATE`` and ``GIT_COMMITTER_DATE`` to ``when``
    (an ISO datetime with an explicit UTC offset) -- verified live that
    ``git log --since`` filters on COMMITTER date, so both must be set
    explicitly for a deterministic churn-window fixture (Code Map)."""
    path = target / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    _git(target, "add", rel_path)
    env = dict(os.environ)
    env["GIT_AUTHOR_DATE"] = when
    env["GIT_COMMITTER_DATE"] = when
    subprocess.run(
        ["git", "commit", "-q", "-m", f"touch {rel_path}"],
        cwd=target,
        env=env,
        check=True,
    )


# --- Never verified ------------------------------------------------------------


def test_no_verified_line_reports_never_verified(tmp_path: Path) -> None:
    _write_tracked(tmp_path, "proj", "## DW-1\nstatus: open\n")

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert len(findings) == 1
    item = findings[0]
    assert item["reason"] == "never-verified"
    assert item["project"] == "proj"
    assert item["id"] == "DW-1"


# --- Stale -----------------------------------------------------------------------


def test_stale_verified_date_reports_stale_with_days_stale(tmp_path: Path) -> None:
    # 2026-07-15 is 31 days before 2026-08-15 -- one day past the 30-day
    # threshold (DUE_FOR_VERIFICATION_STALENESS_DAYS).
    _write_tracked(
        tmp_path,
        "proj",
        "## DW-1\nstatus: open\nverified: 2026-07-15 — checked once\n",
    )

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert len(findings) == 1
    item = findings[0]
    assert item["reason"] == "stale"
    assert item["project"] == "proj"
    assert item["id"] == "DW-1"
    assert item["days_stale"] == 31


def test_verified_one_day_past_threshold_reports_stale(tmp_path: Path) -> None:
    assert chain.DUE_FOR_VERIFICATION_STALENESS_DAYS == 30
    _write_tracked(tmp_path, "proj", "## DW-1\nverified: 2026-07-15\n")

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert len(findings) == 1
    assert findings[0]["reason"] == "stale"
    assert findings[0]["days_stale"] == 31


# --- Fresh -----------------------------------------------------------------------


def test_fresh_verified_date_reports_nothing(tmp_path: Path) -> None:
    _write_tracked(
        tmp_path,
        "proj",
        "## DW-1\nstatus: open\nverified: 2026-08-10 — recently checked\n",
    )

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert findings == []


def test_verified_exactly_at_threshold_reports_nothing(tmp_path: Path) -> None:
    # 2026-07-16 is EXACTLY 30 days before 2026-08-15 -- "more than 30 days"
    # means exactly 30 is still fresh, not stale.
    _write_tracked(tmp_path, "proj", "## DW-1\nverified: 2026-07-16\n")

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert findings == []


def test_entry_with_two_verified_lines_uses_the_most_recent_one(tmp_path: Path) -> None:
    # Reconciliation appends a fresh `verified:` line rather than replacing
    # the old one (review finding, patch) -- an entry re-checked long after
    # a stale first check must read as fresh, not permanently stale.
    _write_tracked(
        tmp_path,
        "proj",
        "## DW-1\nstatus: open\n"
        "verified: 2026-01-01 — first check, long ago\n"
        "verified: 2026-08-10 — re-checked recently\n",
    )

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert findings == []


# --- Anonymous entry (never selected) ---------------------------------------------


def test_anonymous_headerless_entry_is_never_selected(tmp_path: Path) -> None:
    _write_tracked(tmp_path, "proj", "- source_spec: `foo`\n  verified: 2000-01-01\n")

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert findings == []


# --- Closed/done entry (status is irrelevant) -------------------------------------


def test_closed_done_entry_with_no_verified_line_is_selected_same_as_open(
    tmp_path: Path,
) -> None:
    _write_tracked(tmp_path, "proj", "## DW-1\nstatus: done\nno verified line here\n")

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert len(findings) == 1
    assert findings[0]["reason"] == "never-verified"
    assert findings[0]["id"] == "DW-1"


def test_closed_done_entry_with_stale_verified_is_selected(tmp_path: Path) -> None:
    _write_tracked(
        tmp_path,
        "proj",
        "## DW-1\nstatus: closed\nverified: 2026-07-15 — was closed already\n",
    )

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert len(findings) == 1
    assert findings[0]["reason"] == "stale"


# --- Malformed verified: date ------------------------------------------------------


def test_malformed_verified_date_is_treated_as_never_verified(tmp_path: Path) -> None:
    _write_tracked(tmp_path, "proj", "## DW-1\nverified: not-a-real-date\n")

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert len(findings) == 1
    assert findings[0]["reason"] == "never-verified"


# --- No ledger for a project -------------------------------------------------------


def test_project_with_no_tracked_ledger_contributes_zero_findings(tmp_path: Path) -> None:
    _project_dir(tmp_path, "proj").mkdir(parents=True, exist_ok=True)

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert findings == []


# --- Multi-project isolation ---------------------------------------------------------


def test_two_projects_only_due_projects_entries_are_reported(tmp_path: Path) -> None:
    _write_tracked(tmp_path, "alpha", "## DW-1\nstatus: open\n")  # never-verified, due
    _write_tracked(
        tmp_path,
        "beta",
        "## DW-1\nverified: 2026-08-10 — recent\n",
    )  # fresh, not due

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert len(findings) == 1
    assert findings[0]["project"] == "alpha"


def test_findings_evidence_project_key_names_its_own_project_via_public_api(
    tmp_path: Path,
) -> None:
    _write_tracked(tmp_path, "alpha", "## DW-1\nstatus: open\n")  # never-verified, due
    _write_tracked(tmp_path, "beta", "## DW-1\nverified: 9999-01-01\n")  # far future, fresh

    findings = chain.gather_due_for_verification(tmp_path)

    # Story 11.7: `alpha` and `beta` each ALSO carry a `verification-coverage`
    # item (both have >=1 tracked entry) alongside alpha's own due item --
    # the due item is still appended first, so `findings[0]` is unaffected.
    assert len(findings) == 3
    finding = findings[0]
    assert finding.evidence["project"] == "alpha"


# --- No projects tree at all --------------------------------------------------------


def test_no_projects_tree_reports_one_warn(tmp_path: Path) -> None:
    findings = chain.gather_due_for_verification(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.DUE_FOR_VERIFICATION
    assert finding.check == "due-for-verification-unevaluable"
    assert finding.status is DoctorStatus.WARN
    assert finding.evidence == {"target": str(tmp_path)}
    assert "cannot be evaluated here" in finding.message


# --- Fleet-wide none due -------------------------------------------------------------


def test_fleet_wide_none_due_reports_vacuous_ok_never_empty(tmp_path: Path) -> None:
    _project_dir(tmp_path, "proj").mkdir(parents=True, exist_ok=True)

    findings = chain.gather_due_for_verification(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.DUE_FOR_VERIFICATION
    assert finding.check == "due-for-verification"
    assert finding.status is DoctorStatus.OK
    assert finding.evidence == {"projects_scanned": 0}


def test_fully_fresh_project_reports_vacuous_ok_with_scanned_count(tmp_path: Path) -> None:
    _write_tracked(tmp_path, "proj", "## DW-1\nverified: 9999-01-01\n")

    findings = chain.gather_due_for_verification(tmp_path)

    # Story 11.7: `proj` also carries a `verification-coverage` item (it has
    # 1 tracked entry) appended AFTER the vacuous-OK finding, which stays
    # `findings[0]` unaffected.
    assert len(findings) == 2
    assert findings[0].status is DoctorStatus.OK
    assert findings[0].evidence == {"projects_scanned": 1}
    # review finding, patch: this was the only test exercising the vacuous-OK
    # branch of `_gather_due_for_verification`, but it never inspected
    # `findings[1]` -- pin its content too, not just its count.
    assert findings[1].check == "verification-coverage"
    assert findings[1].evidence["project"] == "proj"
    assert findings[1].evidence["pct"] == 100


# --- Finding shape through the public API (never-verified, time-invariant) -----------


def test_gather_wraps_never_verified_finding_with_correct_shape(tmp_path: Path) -> None:
    _write_tracked(tmp_path, "proj", "## DW-1\nstatus: open\n")

    findings = chain.gather_due_for_verification(tmp_path)

    # Story 11.7: `proj` also carries a `verification-coverage` item (it has
    # 1 tracked entry) appended AFTER this due item, which stays
    # `findings[0]` unaffected.
    assert len(findings) == 2
    finding = findings[0]
    assert finding.source is Source.DUE_FOR_VERIFICATION
    assert finding.check == "due-for-verification"
    assert finding.status is DoctorStatus.WARN
    assert finding.evidence["reason"] == "never-verified"
    assert finding.evidence["project"] == "proj"
    assert finding.evidence["id"] == "DW-1"


def test_gather_never_emits_fail_status(tmp_path: Path) -> None:
    # A mix of never-verified and definitely-stale (far-past) entries --
    # every one of these must WARN, never FAIL (Boundaries).
    _write_tracked(
        tmp_path,
        "proj",
        "## DW-1\nstatus: open\n\n## DW-2\nverified: 2000-01-01 — ancient\n",
    )

    findings = chain.gather_due_for_verification(tmp_path)

    # Story 11.7: `proj` also carries one `verification-coverage` item (an
    # aggregate over its 2 tracked entries, not per-entry) alongside the 2
    # due items.
    assert len(findings) == 3
    assert all(f.status is DoctorStatus.WARN for f in findings)


# --- Unreadable ledger: isolated WARN, other projects unaffected ---------------------


def test_unreadable_tracked_ledger_directory_is_isolated_as_warn(tmp_path: Path) -> None:
    _write_tracked(tmp_path, "proj", "## DW-1\nstatus: open\n")

    pa_dir = _project_dir(tmp_path, "proj") / "planning-artifacts"
    pa_dir.chmod(0o000)
    try:
        findings = chain.gather_due_for_verification(tmp_path)
    finally:
        pa_dir.chmod(0o755)

    assert [f.check for f in findings] == ["due-for-verification-unevaluable"]
    assert findings[0].status is DoctorStatus.WARN
    assert findings[0].evidence["project"] == "proj"
    assert "could not be evaluated here" in findings[0].message


def test_one_unevaluable_project_does_not_hide_another_projects_real_finding(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Mirrors ``test_sources_chain_deferred_work.py``'s own per-project
    isolation test: one project's unreadable ledger must not discard a
    DIFFERENT, well-formed project's real finding."""
    _write_tracked(tmp_path, "good", "## DW-1\nstatus: open\n")  # real due entry
    _project_dir(tmp_path, "zbroken").mkdir(parents=True, exist_ok=True)

    real = chain._check_project_due_for_verification

    def _explode(target, proj, findings, today):
        if proj.name == "zbroken":
            raise RuntimeError("unanticipated shape")
        return real(target, proj, findings, today)

    monkeypatch.setattr(chain, "_check_project_due_for_verification", _explode)

    findings = chain.gather_due_for_verification(tmp_path)

    by_check: dict[str, list] = {}
    for f in findings:
        by_check.setdefault(f.check, []).append(f)

    assert "due-for-verification" in by_check, (
        f"one project's failure hid another's real finding: {[f.check for f in findings]}"
    )
    good = next(f for f in by_check["due-for-verification"] if f.evidence["project"] == "good")
    assert good.status is DoctorStatus.WARN

    warn = next(f for f in by_check["due-for-verification-unevaluable"])
    assert warn.status is DoctorStatus.WARN
    assert warn.evidence["project"] == "zbroken"


# --- Never raises: non-UTF-8 bytes -----------------------------------------------


def test_non_utf8_tracked_ledger_never_raises(tmp_path: Path) -> None:
    tracked = _project_dir(tmp_path, "proj") / "planning-artifacts" / "deferred-work-ledger.md"
    tracked.parent.mkdir(parents=True, exist_ok=True)
    tracked.write_bytes(b"## DW-1\nverified: caf\xe9\n")

    findings = chain.gather_due_for_verification(tmp_path)

    assert findings  # returned rather than raised
    assert all(f.source is Source.DUE_FOR_VERIFICATION for f in findings)
    assert findings[0].evidence["reason"] == "never-verified"


# --- degrade_on_exception safety net -------------------------------------------------


def test_gather_degrades_on_unexpected_exception(tmp_path: Path, monkeypatch) -> None:
    def _boom(target: Path, *, today=None):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(chain, "_due_for_verification_findings", _boom)

    findings = chain.gather_due_for_verification(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN
    assert findings[0].source is Source.DUE_FOR_VERIFICATION
    assert "RuntimeError" in findings[0].message


# === Story 11.2: churn-based cost filtering ====================================
#
# One test per I/O & Edge-Case Matrix row (spec's own table), all against
# REAL `git init`-ed fixtures with dated commits -- no mocking of `run_git`
# itself, so these tests exercise the actual two-step `_churn_since`
# algorithm and the anchored `_authored_date` pickaxe end to end.


# --- Row 1: single path, untouched since date ---------------------------------


def test_single_path_untouched_since_date_gets_skip_reason_no_churn(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(target, "src/foo.py", "print('v1')\n", "2026-01-01T00:00:00+00:00")
    _write_tracked(
        target,
        "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\nCode: `src/foo.py:10`\n",
    )

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    assert len(findings) == 1
    item = findings[0]
    assert item["reason"] == "stale"
    assert item.get("skip_reason") == "no-churn"
    assert item["churn_checked_paths"] == ["src/foo.py"]


# --- Row 2: single path, touched since date ------------------------------------


def test_single_path_touched_since_date_has_no_skip_reason(tmp_path: Path) -> None:
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(target, "src/foo.py", "print('v1')\n", "2026-01-01T00:00:00+00:00")
    _commit_file(target, "src/foo.py", "print('v2')\n", "2026-07-10T00:00:00+00:00")
    _write_tracked(
        target,
        "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\nCode: `src/foo.py:10`\n",
    )

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    assert len(findings) == 1
    item = findings[0]
    assert item["reason"] == "stale"
    # Finding otherwise identical to 11.1's own shape -- no skip_reason key.
    assert "skip_reason" not in item
    assert "churn_checked_paths" not in item


# --- Row 3: two paths, one churned ----------------------------------------------


def test_two_paths_one_churned_blocks_the_skip(tmp_path: Path) -> None:
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(target, "src/a.py", "a = 1\n", "2026-01-01T00:00:00+00:00")
    _commit_file(target, "src/b.py", "b = 1\n", "2026-01-01T00:00:00+00:00")
    _commit_file(target, "src/b.py", "b = 2\n", "2026-07-10T00:00:00+00:00")
    _write_tracked(
        target,
        "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\nTouches `src/a.py` (clean) and `src/b.py` (churned).\n",
    )

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    assert len(findings) == 1
    assert "skip_reason" not in findings[0]


# --- Row 4: path never tracked here ---------------------------------------------


def test_path_never_tracked_here_blocks_the_skip(tmp_path: Path) -> None:
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(target, "src/other.py", "x = 1\n", "2026-01-01T00:00:00+00:00")
    _write_tracked(
        target,
        "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\n"
        "See `bmad_loop/verify.py:1474` (external package, not this repo).\n",
    )

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    assert len(findings) == 1
    # An unresolved path (step 1 empty) must NOT read as churn-free.
    assert "skip_reason" not in findings[0]


# --- Row 5: no extractable path --------------------------------------------------


def test_no_extractable_path_has_no_skip_reason(tmp_path: Path) -> None:
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(target, "src/unrelated.py", "x = 1\n", "2026-01-01T00:00:00+00:00")
    _write_tracked(
        target,
        "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\n"
        "Uses `pin_subpackage` and `compiler()` correctly, no path cited.\n",
    )

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    assert len(findings) == 1
    assert "skip_reason" not in findings[0]


# --- Row 6: never-verified, authoring date resolvable (+ id-prefix collision) --


def test_authored_date_resolves_correctly_despite_id_prefix_collision(
    tmp_path: Path,
) -> None:
    """``DW-1-1-1`` is a left-anchor substring of ``DW-1-1-10`` -- a naive
    unanchored search for the shorter id collides with the longer id's own
    introduction commit and returns that EARLIER, wrong date (Boundaries).
    This test makes the two candidate dates DISAGREE about whether the same
    source path counts as churned, so a correct vs. buggy resolution
    produces a different, observable skip decision rather than merely a
    different (but equally inert) date value."""
    target = tmp_path / "target"
    _init_repo(target)
    tracked = _write_tracked(target, "proj", "## DW-1-1-10 — unrelated\nstatus: open\n")

    def _commit_ledger(text: str, when: str, subject: str) -> None:
        tracked.write_text(text, encoding="utf-8")
        _git(target, "add", str(tracked.relative_to(target)))
        env = dict(os.environ)
        env["GIT_AUTHOR_DATE"] = when
        env["GIT_COMMITTER_DATE"] = when
        subprocess.run(
            ["git", "commit", "-q", "-m", subject],
            cwd=target,
            env=env,
            check=True,
        )

    # T1: the unrelated LONGER id is introduced first.
    _commit_ledger(
        "## DW-1-1-10 — unrelated\nstatus: open\n",
        "2026-01-05T00:00:00+00:00",
        "proj: add DW-1-1-10",
    )
    # T2: the source path is touched -- AFTER the confusable neighbour's
    # (wrong, buggy) date but BEFORE the real entry's (correct) date. This
    # is the only window where the two candidate dates disagree.
    _commit_file(target, "src/shared.py", "x = 1\n", "2026-02-05T00:00:00+00:00")
    # T3: the entry actually under test is introduced.
    _commit_ledger(
        "## DW-1-1-10 — unrelated\nstatus: open\n\n## DW-1-1-1 — the real entry\nCode: `src/shared.py`\n",
        "2026-03-05T00:00:00+00:00",
        "proj: add DW-1-1-1",
    )

    resolved = chain._authored_date(target, tracked, "DW-1-1-1")
    assert resolved == date(2026, 3, 5)  # not 2026-01-05, the buggy date

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))
    by_id = {f["id"]: f for f in findings}
    # Correct (2026-03-05): src/shared.py has zero commits since -> skip.
    # Buggy (2026-01-05): src/shared.py's T2 commit would read as churned.
    assert by_id["DW-1-1-1"].get("skip_reason") == "no-churn"


# --- Row 7: never-verified, authoring date unresolvable ------------------------


def test_never_verified_unresolvable_authoring_date_has_no_skip_reason(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(target, "src/foo.py", "x = 1\n", "2026-01-01T00:00:00+00:00")
    # The tracked ledger is written directly to disk but never committed --
    # its own git history is empty, so the anchored `-G` pickaxe search
    # cannot find any introduction commit for the id at all.
    _write_tracked(target, "proj", "## DW-1\nCode: `src/foo.py`\n")

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    assert len(findings) == 1
    assert findings[0]["reason"] == "never-verified"
    assert "skip_reason" not in findings[0]


# --- Row 8: source_spec: cites a path -------------------------------------------


def test_source_spec_path_is_never_a_churn_candidate(tmp_path: Path) -> None:
    """The entry's own `source_spec:` value (a `.md` path) is EXCLUDED from
    extraction even when it would otherwise block the skip -- proven here
    by making the source_spec path itself churn AFTER the verified date
    while the entry's real, non-source_spec code citation stays clean: the
    entry must still be skipped, which is only possible if the excluded
    path never entered the churn check at all."""
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(
        target,
        "docs/specs/thing.md",
        "v1\n",
        "2026-01-01T00:00:00+00:00",
    )
    _commit_file(
        target,
        "docs/specs/thing.md",
        "v2\n",
        "2026-07-10T00:00:00+00:00",
    )  # churned AFTER the verified date -- must not block the skip
    _commit_file(target, "src/foo.py", "x = 1\n", "2026-01-01T00:00:00+00:00")
    _write_tracked(
        target,
        "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\n- source_spec: `docs/specs/thing.md`\nCode: `src/foo.py`\n",
    )

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    assert len(findings) == 1
    assert findings[0].get("skip_reason") == "no-churn"
    assert findings[0]["churn_checked_paths"] == ["src/foo.py"]


# --- Row 9: per-entry git failure is isolated -----------------------------------


def test_per_entry_churn_failure_is_isolated_from_its_project_siblings(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Simulates a REAL ``run_git`` failure (``CliBridgeError``) for one
    path, not an artificial exception from an internal helper -- exercises
    ``_churn_since``'s own internal try/except (the actual production
    isolation mechanism), proving the AC against the real code path rather
    than a testing shim (review finding, patch: the prior version
    monkeypatched ``_churn_since`` itself to raise, which only ever
    exercised ``_attach_churn_skip``'s redundant OUTER except -- a path
    ``_churn_since`` never actually takes in production, since it already
    catches every ``run_git`` failure mode internally)."""
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(target, "src/clean.py", "x = 1\n", "2026-01-01T00:00:00+00:00")
    _commit_file(target, "src/boom.py", "y = 1\n", "2026-01-01T00:00:00+00:00")
    _write_tracked(
        target,
        "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\nCode: `src/clean.py`\n\n"
        "## DW-2\nverified: 2026-07-01 — checked once\nCode: `src/boom.py`\n",
    )

    real_run_git = chain.run_git

    def _flaky_run_git(target_: Path, args: list[str], **kwargs):
        if any("src/boom.py" in a for a in args):
            raise CliBridgeError("simulated per-entry git hiccup")
        return real_run_git(target_, args, **kwargs)

    monkeypatch.setattr(chain, "run_git", _flaky_run_git)

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    by_id = {f["id"]: f for f in findings}
    assert len(findings) == 2
    assert by_id["DW-1"].get("skip_reason") == "no-churn"
    assert "skip_reason" not in by_id["DW-2"]


# --- Message text carries the skip decision -------------------------------------


def test_message_appends_skip_decision_text_when_skip_reason_present(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(target, "src/foo.py", "x = 1\n", "2026-01-01T00:00:00+00:00")
    _write_tracked(
        target,
        "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\nCode: `src/foo.py`\n",
    )

    findings = chain.gather_due_for_verification(target)

    # Story 11.7: `proj` also carries a `verification-coverage` item (it has
    # 1 tracked entry) appended AFTER this due item, which stays
    # `findings[0]` unaffected.
    assert len(findings) == 2
    finding = findings[0]
    assert finding.evidence.get("skip_reason") == "no-churn"
    assert "skip_reason: no-churn" in finding.message
    assert "due for re-check" in finding.message  # base message text intact


def test_message_omits_skip_decision_text_when_no_skip_reason(tmp_path: Path) -> None:
    _write_tracked(tmp_path, "proj", "## DW-1\nstatus: open\n")

    findings = chain.gather_due_for_verification(tmp_path)

    # Story 11.7: `proj` also carries a `verification-coverage` item (it has
    # 1 tracked entry) appended AFTER this due item, which stays
    # `findings[0]` unaffected.
    assert len(findings) == 2
    assert "skip_reason" not in findings[0].message


# === Story 11.3: mechanical verification of grep-recomputable claims ==========
#
# One test per I/O & Edge-Case Matrix row (spec's own table), plus regression
# coverage for four review-pass findings (self-citation exclusion, async def
# recognition, variable/constant exclusion via has_declaration, --untracked
# detection). All against REAL `git init`-ed fixtures with dated commits --
# no mocking of `run_git` itself except in the one test that specifically
# needs to simulate a real `git grep` failure, mirroring Story 11.2's own
# testing discipline. None of these entries cite a path token (`.`-extension
# or `/`), so none is ever churn-skipped by 11.2's own filter -- each
# survives to be offered to the mechanical check, matching the Boundaries'
# "only offer... entries that SURVIVE Story 11.2's churn filter" rule. Every
# ledger in this section is COMMITTED (via `_commit_file`, not the bare
# `_write_tracked`), matching real production shape -- a tracked ledger is a
# committed Tier-2 artifact -- so these tests actually exercise the same
# tracked-file scope `git grep` sees in production, unlike an untracked
# fixture that would hide a self-citation bug regardless of whether the
# implementation excludes it.


# --- Row 1: claimed unused, still unused (also regression: ledger
# self-citation must not count as a call site) -----------------------------


def test_claimed_unused_still_unused_gets_mechanical_verdict_still_open(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(
        target,
        "src/foo.py",
        "def _foo(x):\n    return x\n",
        "2026-01-01T00:00:00+00:00",
    )
    # The ledger is COMMITTED and its own claim text backtick-cites `_foo` --
    # without the `:(exclude,glob)**/deferred-work-ledger.md` pathspec, this
    # citation alone would count as a call site and force `escalate`.
    _commit_file(
        target,
        _tracked_rel("proj"),
        "## DW-1\nverified: 2026-07-01 — checked once\nClaim: `_foo` is unused and should be removed.\n",
        "2026-07-01T00:00:00+00:00",
    )

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    assert len(findings) == 1
    item = findings[0]
    assert item["reason"] == "stale"
    assert "skip_reason" not in item  # no path cited, never churn-skipped
    assert item["mechanical_verdict"] == "still-open"
    assert item["mechanical_symbol"] == "_foo"
    assert item["mechanical_call_sites"] == 0


# --- Row 2: claimed unused, now referenced --------------------------------------


def test_claimed_unused_now_referenced_gets_mechanical_verdict_escalate(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(
        target,
        "src/foo.py",
        "def _foo(x):\n    return x\n\n\ndef bar():\n    y = _foo(1)\n    z = _foo(2)\n    return y + z\n",
        "2026-01-01T00:00:00+00:00",
    )
    _commit_file(
        target,
        _tracked_rel("proj"),
        "## DW-1\nverified: 2026-07-01 — checked once\nClaim: `_foo` is unused and should be removed.\n",
        "2026-07-01T00:00:00+00:00",
    )

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    assert len(findings) == 1
    item = findings[0]
    assert item["mechanical_verdict"] == "escalate"
    assert item["mechanical_symbol"] == "_foo"
    # 2 live call sites -- the `def _foo(x):` declaration line is excluded.
    assert item["mechanical_call_sites"] == 2


# --- Regression: a pruned-dir untracked reference never forces escalate ---------


def test_untracked_reference_inside_a_pruned_dir_does_not_force_escalate(
    tmp_path: Path,
) -> None:
    """2026-08-30: `_call_site_count`'s `--untracked --no-exclude-standard`
    git grep un-ignores `.gitignore` entirely -- against a real fleet with a
    32GB `.pixi/`, an unbounded scan of every pruned vendor/cache dir made
    this check hard-timeout every real invocation. A reference sitting only
    inside a pruned dir (here `.pixi/`, from `env_hygiene.py`'s own
    `_PRUNED_DIR_NAMES`) must not count as a live call site -- proving the
    fix's pathspec excludes are wired into the actual git grep call, not
    just present in a docstring."""
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(
        target,
        "src/foo.py",
        "def _foo(x):\n    return x\n",
        "2026-01-01T00:00:00+00:00",
    )
    # Untracked, inside a pruned dir -- no .gitignore needed: the exclude
    # pathspec is unconditional, independent of what .gitignore says.
    decoy = target / ".pixi" / "decoy.py"
    decoy.parent.mkdir(parents=True, exist_ok=True)
    decoy.write_text("y = _foo(1)\nz = _foo(2)\n", encoding="utf-8")
    _commit_file(
        target,
        _tracked_rel("proj"),
        "## DW-1\nverified: 2026-07-01 — checked once\nClaim: `_foo` is unused and should be removed.\n",
        "2026-07-01T00:00:00+00:00",
    )

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    assert len(findings) == 1
    item = findings[0]
    # Without the pruned-dir excludes, the two decoy references would force
    # `escalate` with `mechanical_call_sites == 2`.
    assert item["mechanical_verdict"] == "still-open"
    assert item["mechanical_call_sites"] == 0


# --- Regression: async def is recognized as a declaration -----------------------


def test_async_def_declaration_is_recognized_and_excluded(tmp_path: Path) -> None:
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(
        target,
        "src/foo.py",
        "async def _foo(x):\n    return x\n",
        "2026-01-01T00:00:00+00:00",
    )
    _commit_file(
        target,
        _tracked_rel("proj"),
        "## DW-1\nverified: 2026-07-01 — checked once\nClaim: `_foo` is unused and should be removed.\n",
        "2026-07-01T00:00:00+00:00",
    )

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    assert len(findings) == 1
    item = findings[0]
    # Without async-def recognition, its own declaration line would be
    # miscounted as a live call site, forcing `escalate` on a dead function.
    assert item["mechanical_verdict"] == "still-open"
    assert item["mechanical_call_sites"] == 0


# --- Regression: a variable/constant "declaration" gets no verdict --------------


def test_variable_declaration_gets_no_mechanical_verdict(tmp_path: Path) -> None:
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(
        target,
        "src/foo.py",
        "_FOO_CONST = 42\n",
        "2026-01-01T00:00:00+00:00",
    )
    _commit_file(
        target,
        _tracked_rel("proj"),
        "## DW-1\nverified: 2026-07-01 — checked once\nClaim: `_FOO_CONST` is unused and should be removed.\n",
        "2026-07-01T00:00:00+00:00",
    )

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    assert len(findings) == 1
    item = findings[0]
    # `_FOO_CONST` never resolves to a `def`/`class`/`async def` declaration
    # -- this story mechanically checks "unused function" claims only, so a
    # bare variable/constant is left for Story 11.4's agent rather than risk
    # its own assignment line being miscounted as a call site.
    assert not any(k.startswith("mechanical_") for k in item)


# --- Regression: an untracked (not-yet-committed) reference is still seen ------


def test_untracked_file_reference_is_still_detected(tmp_path: Path) -> None:
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(
        target,
        "src/foo.py",
        "def _foo(x):\n    return x\n",
        "2026-01-01T00:00:00+00:00",
    )
    _commit_file(
        target,
        _tracked_rel("proj"),
        "## DW-1\nverified: 2026-07-01 — checked once\nClaim: `_foo` is unused and should be removed.\n",
        "2026-07-01T00:00:00+00:00",
    )
    # A brand-new caller, written but NEVER `git add`-ed/committed.
    (target / "src" / "new_caller.py").write_text(
        "y = _foo(5)\n",
        encoding="utf-8",
    )

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    assert len(findings) == 1
    item = findings[0]
    # Without `--untracked`, this reference would be invisible and the
    # entry would mechanically (and falsely) confirm `still-open`.
    assert item["mechanical_verdict"] == "escalate"
    assert item["mechanical_call_sites"] == 1


# --- Row 3: entry is churn-skipped ------------------------------------------------


def test_churn_skipped_entry_gets_no_mechanical_check(tmp_path: Path) -> None:
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(target, "src/foo.py", "x = 1\n", "2026-01-01T00:00:00+00:00")
    _write_tracked(
        target,
        "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\n`_foo` is unused. See `src/foo.py:10`.\n",
    )

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    assert len(findings) == 1
    item = findings[0]
    # Churn-free since the verified date -- 11.2 skips it.
    assert item.get("skip_reason") == "no-churn"
    # A churn-skipped entry is never offered to the mechanical check, even
    # though its own body contains a recognizable unused-symbol claim.
    assert "mechanical_verdict" not in item
    assert "mechanical_symbol" not in item
    assert "mechanical_call_sites" not in item


# --- Row 4: no recognizable claim --------------------------------------------------


def test_no_recognizable_claim_has_no_mechanical_keys(tmp_path: Path) -> None:
    target = tmp_path / "target"
    _init_repo(target)
    _write_tracked(
        target,
        "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\nInvestigate feasibility of caching this lookup someday.\n",
    )

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    assert len(findings) == 1
    item = findings[0]
    # Byte-identical in shape to what 11.1/11.2 alone would have produced --
    # no mechanical_* key of any kind.
    assert not any(k.startswith("mechanical_") for k in item)


# --- Row 5: dotted symbol cited -----------------------------------------------------


def test_dotted_symbol_claim_is_not_recognized(tmp_path: Path) -> None:
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(target, "src/other.py", "x = 1\n", "2026-01-01T00:00:00+00:00")
    _write_tracked(
        target,
        "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\nClaim: `Foo.bar` is unused.\n",
    )

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    assert len(findings) == 1
    item = findings[0]
    assert not any(k.startswith("mechanical_") for k in item)


# --- Row 6: symbol's only occurrence is its own def -------------------------------


def test_symbol_only_occurrence_is_its_own_def_is_still_open(tmp_path: Path) -> None:
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(
        target,
        "src/foo.py",
        "def _foo(x):\n    return x\n",
        "2026-01-01T00:00:00+00:00",
    )
    _write_tracked(
        target,
        "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\nClaim: `_foo` is unused and should be removed.\n",
    )

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    assert len(findings) == 1
    item = findings[0]
    # The definition line itself is excluded from the count -- confirmed
    # unused, not merely "the only match happens to be its own def".
    assert item["mechanical_verdict"] == "still-open"
    assert item["mechanical_call_sites"] == 0


# --- Row 7: git grep hard failure is isolated ---------------------------------------


def test_git_grep_hard_failure_is_isolated_from_its_project_siblings(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Simulates a REAL ``run_git`` failure (``CliBridgeError``) for one
    entry's mechanical check -- exercises ``_attach_mechanical_verdict``'s
    own isolation, proving the AC against the real code path rather than an
    artificial internal-helper exception, mirroring
    ``test_per_entry_churn_failure_is_isolated_from_its_project_siblings``
    (Story 11.2)."""
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(
        target,
        "src/foo.py",
        "def _foo(x):\n    return x\n",
        "2026-01-01T00:00:00+00:00",
    )
    _commit_file(
        target,
        "src/bar.py",
        "def _bar():\n    pass\n",
        "2026-01-01T00:00:00+00:00",
    )
    _commit_file(
        target,
        _tracked_rel("proj"),
        "## DW-1\nverified: 2026-07-01 — checked once\n`_foo` is unused.\n\n"
        "## DW-2\nverified: 2026-07-01 — checked once\n`_bar` is unused.\n",
        "2026-07-01T00:00:00+00:00",
    )

    real_run_git = chain.run_git

    def _flaky_run_git(target_: Path, args: list[str], **kwargs):
        if args[:1] == ["grep"] and "_foo" in args:
            raise CliBridgeError("simulated git grep hiccup")
        return real_run_git(target_, args, **kwargs)

    monkeypatch.setattr(chain, "run_git", _flaky_run_git)

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    by_id = {f["id"]: f for f in findings}
    assert len(findings) == 2
    # DW-1's mechanical check failed -- no mechanical_* keys for THIS entry.
    assert not any(k.startswith("mechanical_") for k in by_id["DW-1"])
    # DW-2 (a different entry, same project) is entirely unaffected.
    assert by_id["DW-2"].get("mechanical_verdict") == "still-open"


# --- Message text carries the mechanical verdict ------------------------------------


def test_message_appends_still_open_text_when_mechanical_verdict_present(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(
        target,
        "src/foo.py",
        "def _foo(x):\n    return x\n",
        "2026-01-01T00:00:00+00:00",
    )
    _commit_file(
        target,
        _tracked_rel("proj"),
        "## DW-1\nverified: 2026-07-01 — checked once\nClaim: `_foo` is unused and should be removed.\n",
        "2026-07-01T00:00:00+00:00",
    )

    findings = chain.gather_due_for_verification(target)

    # Story 11.7: `proj` also carries a `verification-coverage` item (it has
    # 1 tracked entry) appended AFTER this due item, which stays
    # `findings[0]` unaffected.
    assert len(findings) == 2
    finding = findings[0]
    assert finding.evidence.get("mechanical_verdict") == "still-open"
    assert "mechanical_verdict: still-open" in finding.message
    assert "due for re-check" in finding.message  # base message text intact


def test_message_appends_escalate_text_when_mechanical_verdict_present(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(
        target,
        "src/foo.py",
        "def _foo(x):\n    return x\n\n\ndef bar():\n    y = _foo(1)\n    z = _foo(2)\n    return y + z\n",
        "2026-01-01T00:00:00+00:00",
    )
    _write_tracked(
        target,
        "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\nClaim: `_foo` is unused and should be removed.\n",
    )

    findings = chain.gather_due_for_verification(target)

    # Story 11.7: `proj` also carries a `verification-coverage` item (it has
    # 1 tracked entry) appended AFTER this due item, which stays
    # `findings[0]` unaffected.
    assert len(findings) == 2
    finding = findings[0]
    assert finding.evidence.get("mechanical_verdict") == "escalate"
    assert "mechanical_verdict: escalate" in finding.message


def test_message_omits_mechanical_text_when_no_mechanical_verdict(
    tmp_path: Path,
) -> None:
    _write_tracked(tmp_path, "proj", "## DW-1\nstatus: open\n")

    findings = chain.gather_due_for_verification(tmp_path)

    # Story 11.7: `proj` also carries a `verification-coverage` item (it has
    # 1 tracked entry) appended AFTER this due item, which stays
    # `findings[0]` unaffected.
    assert len(findings) == 2
    assert "mechanical_verdict" not in findings[0].message


# === Follow-up review pass: two more real correctness gaps ====================
#
# Both empirically confirmed against a real `git init` fixture before being
# patched. Both push in the one direction the story's own vocabulary must
# never produce: a false `still-open`.


def test_gitignored_untracked_reference_is_still_detected(tmp_path: Path) -> None:
    """`--untracked` alone still honors `.gitignore` -- a symbol referenced
    only from a new, untracked file under a gitignored directory was
    invisible to the search without `--no-exclude-standard`, reopening the
    false-`still-open` gap `--untracked` was added to close."""
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(
        target,
        "src/foo.py",
        "def _foo(x):\n    return x\n",
        "2026-01-01T00:00:00+00:00",
    )
    _commit_file(target, ".gitignore", "ignored_dir/\n", "2026-01-01T00:00:00+00:00")
    _commit_file(
        target,
        _tracked_rel("proj"),
        "## DW-1\nverified: 2026-07-01 — checked once\nClaim: `_foo` is unused and should be removed.\n",
        "2026-07-01T00:00:00+00:00",
    )
    # A brand-new caller under a gitignored directory -- never `git add`-ed.
    (target / "ignored_dir").mkdir()
    (target / "ignored_dir" / "caller.py").write_text(
        "y = _foo(5)\n",
        encoding="utf-8",
    )

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    assert len(findings) == 1
    item = findings[0]
    assert item["mechanical_verdict"] == "escalate"
    assert item["mechanical_call_sites"] == 1


def test_recursive_one_liner_self_call_is_counted(tmp_path: Path) -> None:
    """A single-line recursive declaration (e.g. ``def _foo(x): return
    _foo(x - 1) if x else 0``) is ONE matched line that is both the
    declaration AND a genuine self-call -- excluding the whole line as
    "the declaration" previously undercounted that real usage as zero."""
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(
        target,
        "src/foo.py",
        "def _foo(x): return _foo(x - 1) if x else 0\n",
        "2026-01-01T00:00:00+00:00",
    )
    _write_tracked(
        target,
        "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\nClaim: `_foo` is unused and should be removed.\n",
    )

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    assert len(findings) == 1
    item = findings[0]
    assert item["mechanical_verdict"] == "escalate"
    assert item["mechanical_call_sites"] == 1


# --- Story 11.5: cross-project code-root discoverability -----------------------
#
# Covers the spec's own I/O & Edge-Case Matrix: (a) `_known_project_code_roots`
# itself -- multi-project discovery, a project deliberately missing its code
# root; (b) a `due-for-verification` Finding's evidence carrying
# `other_project_roots` excluding its own project, including the single-
# project-fleet (empty dict) and never-on-unevaluable edge cases; (c) an
# integration-style test reproducing the real `atlas DW-I5-1` shape end to
# end via `apply_verification_verdicts.py`'s own `_apply_project`.


def _make_project(target: Path, project: str) -> Path:
    """A bare, empty ``_bmad-output/projects/<project>/`` directory -- enough
    for ``_known_project_code_roots`` to consider it a known project (mirrors
    ``test_project_with_no_tracked_ledger_contributes_zero_findings``'s own
    bare-directory fixture); no tracked ledger required."""
    d = _project_dir(target, project)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_code_root_file(target: Path, project: str, rel_path: str, content: str) -> Path:
    """A real file under ``src/shared/packages/<project>/<rel_path>`` --
    also ensures ``project``'s own ``_bmad-output/projects/<project>/``
    directory exists via ``_make_project`` (ALWAYS required for
    ``_known_project_code_roots`` to enumerate the project at all, regardless
    of whether it also turns out to have a real code root)."""
    _make_project(target, project)
    path = target / "src" / "shared" / "packages" / project / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# --- (a) _known_project_code_roots itself ---------------------------------------


def test_known_project_code_roots_maps_only_projects_with_a_real_code_root(
    tmp_path: Path,
) -> None:
    """Multi-project fixture: ``alpha`` has a matching
    ``src/shared/packages/alpha/`` code root, ``beta`` is a real, known
    project directory with NO matching code root (a doc-only or partially-
    external station) -- ``beta`` must be SILENTLY OMITTED from the map,
    never included with a guessed or empty path (I/O matrix: "Project with
    no code root")."""
    _write_code_root_file(tmp_path, "alpha", "src/pyforge/alpha/__init__.py", "")
    _make_project(tmp_path, "beta")

    roots = chain._known_project_code_roots(tmp_path)

    assert roots == {"alpha": "src/shared/packages/alpha"}
    assert "beta" not in roots


def test_known_project_code_roots_single_project_fleet(tmp_path: Path) -> None:
    """A lone known project with a real code root still maps to itself --
    whether it gets EXCLUDED from its own findings is
    ``_check_project_due_for_verification``'s own job, covered below."""
    _write_code_root_file(tmp_path, "solo", "README.md", "")

    roots = chain._known_project_code_roots(tmp_path)

    assert roots == {"solo": "src/shared/packages/solo"}


def test_known_project_code_roots_no_projects_tree_degrades_to_empty_dict(
    tmp_path: Path,
) -> None:
    """``target`` is not a monorepo root at all -- degrades to ``{}``, the
    same vacuous-degrade shape ``_due_for_verification_findings``'s own guard
    already uses one layer up (I/O matrix: "Unreadable/missing
    `_bmad-output/projects/`")."""
    assert chain._known_project_code_roots(tmp_path) == {}


# --- (b) other_project_roots attached to due-for-verification items ------------


def test_due_for_verification_item_carries_other_project_roots_excluding_own(
    tmp_path: Path,
) -> None:
    """A due entry in project ``alpha`` names every OTHER known project's
    code root under ``other_project_roots`` -- excluding ``alpha``'s own,
    even though ``alpha`` also has a real code root; ``gamma`` (a known
    project with no code root) is silently omitted too."""
    _write_tracked(tmp_path, "alpha", "## DW-1\nstatus: open\n")  # never-verified, due
    _write_code_root_file(tmp_path, "alpha", "README.md", "")
    _write_code_root_file(tmp_path, "beta", "README.md", "")
    _make_project(tmp_path, "gamma")  # known, but no code root

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert len(findings) == 1
    assert findings[0]["other_project_roots"] == {"beta": "src/shared/packages/beta"}


def test_multiple_due_entries_in_one_project_each_get_their_own_equal_copy(
    tmp_path: Path,
) -> None:
    """A project with TWO due entries: both findings carry an EQUAL
    ``other_project_roots`` (the recompute-once-per-project map, unchanged
    across entries) but NOT the same object -- mutating one finding's dict
    in place must never leak into the other's (review finding, patch:
    verifies the per-item ``dict(other_roots)`` copy directly, not just
    indirectly via a single-entry fixture)."""
    _write_tracked(
        tmp_path,
        "alpha",
        "## DW-1\nstatus: open\n\n## DW-2\nstatus: open\n",
    )
    _write_code_root_file(tmp_path, "beta", "README.md", "")

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert len(findings) == 2
    first, second = findings[0]["other_project_roots"], findings[1]["other_project_roots"]
    assert first == second == {"beta": "src/shared/packages/beta"}
    assert first is not second

    first["beta"] = "tampered"
    assert second == {"beta": "src/shared/packages/beta"}


def test_single_project_fleet_other_project_roots_is_empty_dict(tmp_path: Path) -> None:
    """Single-project fleet (I/O matrix): no siblings to list, so
    ``other_project_roots`` is an empty dict on that project's own findings,
    never absent and never omitted."""
    _write_tracked(tmp_path, "solo", "## DW-1\nstatus: open\n")

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert len(findings) == 1
    assert findings[0]["other_project_roots"] == {}


def test_other_project_roots_survives_the_public_api_finding_wrap(tmp_path: Path) -> None:
    """The evidence key survives the ``Finding`` wrap through the public
    ``gather_due_for_verification`` API."""
    _write_tracked(tmp_path, "alpha", "## DW-1\nstatus: open\n")
    _write_code_root_file(tmp_path, "beta", "README.md", "")

    findings = chain.gather_due_for_verification(tmp_path)

    # Story 11.7: `alpha` also carries a `verification-coverage` item (it has
    # 1 tracked entry) appended AFTER this due item, which stays
    # `findings[0]` unaffected (`beta` has no tracked ledger of its own, so
    # it contributes no coverage item here).
    assert len(findings) == 2
    finding = findings[0]
    assert finding.check == "due-for-verification"
    assert finding.evidence["other_project_roots"] == {"beta": "src/shared/packages/beta"}


def test_due_for_verification_unevaluable_item_has_no_other_project_roots_key(
    tmp_path: Path,
) -> None:
    """A ``due-for-verification-unevaluable`` item (one project's own tracked-
    ledger directory is unreadable) never carries ``other_project_roots`` --
    that key is exclusively a ``due-for-verification`` item's own (Boundaries:
    "never on due-for-verification-unevaluable"), mirroring
    ``test_unreadable_tracked_ledger_directory_is_isolated_as_warn``'s own
    chmod fixture."""
    _write_tracked(tmp_path, "zbroken", "## DW-1\nstatus: open\n")
    _write_code_root_file(tmp_path, "beta", "README.md", "")

    pa_dir = _project_dir(tmp_path, "zbroken") / "planning-artifacts"
    pa_dir.chmod(0o000)
    try:
        findings = chain.gather_due_for_verification(tmp_path)
    finally:
        pa_dir.chmod(0o755)

    assert [f.check for f in findings] == ["due-for-verification-unevaluable"]
    assert "other_project_roots" not in findings[0].evidence


# --- (c) integration: a cross-project close via apply_verification_verdicts.py --


def _load_apply_verdicts_module():
    """Dynamically loads the real ``scripts/apply_verification_verdicts.py``
    as a fresh module object, via ``importlib.util.spec_from_file_location``
    -- never ``sys.path`` manipulation, and never a subprocess (unlike
    ``tests/scripts/test_apply_verification_verdicts.py``'s own precedent,
    which needs a subprocess specifically to patch the script's hard-coded
    ``REPO_ROOT`` line before it runs as ``__main__``): this test calls
    ``_apply_project`` directly, so patching the loaded module OBJECT's own
    ``REPO_ROOT`` attribute after import is enough, and a fresh module object
    per call means that patch can never leak into a sibling test. Registered
    in `sys.modules` only for the DURATION of `exec_module` below, then
    popped back out (review finding, patch): the caller keeps its own
    reference to the returned `module` object regardless, so nothing needs
    the registry entry to persist afterward, and leaving a fixed key
    resident in `sys.modules` for the rest of the test session would risk a
    stale entry (e.g. a since-deleted `tmp_path` still referenced by its
    `REPO_ROOT`) colliding with any future test that loads under the same
    name."""
    script_path = Path(__file__).resolve().parents[6] / "scripts" / "apply_verification_verdicts.py"
    spec = importlib.util.spec_from_file_location(
        "apply_verification_verdicts_under_test",
        script_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered in `sys.modules` BEFORE `exec_module` -- the script's own
    # `from __future__ import annotations` makes every annotation a string,
    # and `@dataclass` (`_Outcome`) resolves a string annotation by looking
    # up `cls.__module__` in `sys.modules`; skipping this step raises
    # `AttributeError: 'NoneType' object has no attribute '__dict__'` at
    # import time, verified empirically.
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        del sys.modules[spec.name]
    return module


def test_cross_project_evidence_closes_the_entry_via_apply_verification_verdicts(
    tmp_path: Path,
) -> None:
    """Reproduces the real ``atlas DW-I5-1`` shape end to end (Intent): a due
    entry lives in project ``alpha``, the real fix is committed under project
    ``beta``'s own code root, ``alpha``'s Finding evidence names ``beta``'s
    code root under ``other_project_roots`` (the discoverability half this
    story adds), and a verifying agent citing ``beta``'s ``file:line`` as
    evidence is accepted UNMODIFIED by ``apply_verification_verdicts.py``'s
    own ``_apply_project`` -- proving CAP-5's own claim that "nothing
    structurally blocks a cross-project close" (Intent)."""
    _write_tracked(tmp_path, "alpha", "## DW-1\nstatus: open\n")
    _write_code_root_file(
        tmp_path,
        "beta",
        "src/pyforge/beta/core/policy.py",
        "def fixed(): ...\n",
    )

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))
    assert len(findings) == 1
    beta_root = findings[0]["other_project_roots"]["beta"]
    assert beta_root == "src/shared/packages/beta"

    verdicts_module = _load_apply_verdicts_module()
    verdicts_module.REPO_ROOT = tmp_path

    outcome = verdicts_module._apply_project(
        "alpha",
        [
            {
                "id": "DW-1",
                "verdict": "resolved",
                "evidence": f"Fixed in {beta_root}/src/pyforge/beta/core/policy.py:1",
            }
        ],
        date(2026, 8, 21),
    )

    assert outcome.status == "applied"
    tracked_text = (tmp_path / "_bmad-output" / "projects" / "alpha" / verdicts_module.TRACKED_REL).read_text(
        encoding="utf-8"
    )
    assert "verified: 2026-08-21 — resolved — Fixed in src/shared/packages/beta" in tracked_text


# --- Story 11.6: near-duplicate entries surface as one defect class -----------
#
# Covers the spec's own I/O & Edge-Case Matrix: (a) the real precedent shape
# -- 3 due entries, one per project, citing the identical backtick-quoted
# path token -- one cluster; (b) a same-project duplicate never clusters;
# (c) normalized-identical `summary:` text across projects clusters on
# `matched_on: "summary"`; (d) distinct paths/distinct text never clusters;
# (e) the correlation pass itself failing degrades to zero clusters without
# discarding any already-computed per-entry Finding; (f) the cluster Finding
# survives the public `gather_due_for_verification` API wrap.


# --- (a) real precedent shape: 3 projects, identical path token ----------------


def test_three_projects_citing_same_path_token_form_one_cluster(tmp_path: Path) -> None:
    """The real precedent shape (Intent): 3 due entries, one per project (A,
    B, C), each citing the identical backtick-quoted path token -- exactly
    one `due-for-verification-cluster` Finding naming all 3 members."""
    _write_tracked(
        tmp_path,
        "alpha",
        "## DW-1\nstatus: open\nCode: `shared/thing.py` looks wrong here\n",
    )
    _write_tracked(
        tmp_path,
        "beta",
        "## DW-2\nstatus: open\nAlso touches `shared/thing.py` differently\n",
    )
    _write_tracked(
        tmp_path,
        "gamma",
        "## DW-3\nstatus: open\nStill about `shared/thing.py` too, elsewhere\n",
    )

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    clusters = [f for f in findings if f["kind"] == "due-for-verification-cluster"]
    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster["matched_on"] == "path"
    assert cluster["matched_value"] == "shared/thing.py"
    assert sorted((m["project"], m["id"]) for m in cluster["members"]) == [
        ("alpha", "DW-1"),
        ("beta", "DW-2"),
        ("gamma", "DW-3"),
    ]


# --- (b) same-project duplicate: never clusters ---------------------------------


def test_two_entries_same_project_sharing_path_token_do_not_cluster(tmp_path: Path) -> None:
    """Two due entries in the SAME project citing the identical path token
    must NOT cluster -- a cluster requires members from at least two
    DIFFERENT projects (Boundaries: "a shared token/text within one
    project's own ledger never clusters")."""
    _write_tracked(
        tmp_path,
        "alpha",
        "## DW-1\nstatus: open\nCode: `shared/thing.py`\n\n## DW-2\nstatus: open\nAlso `shared/thing.py`\n",
    )

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert [f["kind"] for f in findings] == [
        "due-for-verification",
        "due-for-verification",
    ]


# --- (c) near-identical claim text across projects ------------------------------


def test_two_entries_different_projects_matching_summary_text_form_one_cluster(
    tmp_path: Path,
) -> None:
    """Two due entries in different projects with normalized-identical
    `summary:` text -- one cluster Finding, `matched_on: "summary"`, 2
    members. Differing whitespace/casing on each side proves the match is
    NORMALIZED, never verbatim."""
    _write_tracked(
        tmp_path,
        "alpha",
        "## DW-1\nstatus: open\nsummary: The retry loop never backs off\n",
    )
    _write_tracked(
        tmp_path,
        "beta",
        "## DW-2\nstatus: open\nsummary:   the RETRY loop   never backs off  \n",
    )

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    clusters = [f for f in findings if f["kind"] == "due-for-verification-cluster"]
    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster["matched_on"] == "summary"
    assert sorted((m["project"], m["id"]) for m in cluster["members"]) == [
        ("alpha", "DW-1"),
        ("beta", "DW-2"),
    ]
    # review finding, patch: matched_value is the ORIGINAL claim text, never
    # the casefolded/whitespace-collapsed grouping key -- _normalize_claim's
    # own docstring promises the normalized form is never human/agent-facing.
    assert cluster["matched_value"] == "The retry loop never backs off"


def test_matched_value_is_never_the_normalized_grouping_key(tmp_path: Path) -> None:
    """`matched_value` must never equal the casefolded/whitespace-collapsed
    form `_normalize_claim` produces -- only the representative member's
    ORIGINAL text (review finding, patch)."""
    _write_tracked(
        tmp_path,
        "alpha",
        "## DW-1\nstatus: open\nsummary: Mixed CASE   with   extra spaces\n",
    )
    _write_tracked(
        tmp_path,
        "beta",
        "## DW-2\nstatus: open\nsummary: mixed case with extra spaces\n",
    )

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    cluster = next(f for f in findings if f["kind"] == "due-for-verification-cluster")
    assert cluster["matched_value"] != chain._normalize_claim(cluster["matched_value"])
    assert cluster["matched_value"] in (
        "Mixed CASE   with   extra spaces",
        "mixed case with extra spaces",
    )


def test_reason_only_flat_shape_entries_cluster_on_reason_text(tmp_path: Path) -> None:
    """Two due entries carrying only `reason:` (the flat "review-budget-
    followup" shape, no `summary:` at all) with normalized-identical text
    still cluster on `matched_on: "summary"` via the `reason:` fallback
    (Tasks & Acceptance: "preferring summary: then reason:")."""
    _write_tracked(
        tmp_path,
        "alpha",
        "## DW-FU-1\nstatus: open\nreason: the CLI flag was never wired up\n",
    )
    _write_tracked(
        tmp_path,
        "beta",
        "## DW-FU-2\nstatus: open\nreason: the cli flag was never wired up\n",
    )

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    clusters = [f for f in findings if f["kind"] == "due-for-verification-cluster"]
    assert len(clusters) == 1
    assert clusters[0]["matched_on"] == "summary"
    assert sorted((m["project"], m["id"]) for m in clusters[0]["members"]) == [
        ("alpha", "DW-FU-1"),
        ("beta", "DW-FU-2"),
    ]


def test_empty_summary_field_falls_back_to_reason(tmp_path: Path) -> None:
    """An entry whose `summary:` field is present but EMPTY falls back to
    `reason:` rather than using the empty string as a match key (which would
    spuriously cluster every entry with a blank summary together) --
    `fields.get("summary") or fields.get("reason")` is a deliberate,
    correct precedence, not an oversight (review finding: documented by a
    test, not just a docstring claim)."""
    _write_tracked(
        tmp_path,
        "alpha",
        "## DW-1\nstatus: open\nsummary:\nreason: the real claim text here\n",
    )
    _write_tracked(
        tmp_path,
        "beta",
        "## DW-2\nstatus: open\nsummary: \nreason: the real claim text here\n",
    )

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    clusters = [f for f in findings if f["kind"] == "due-for-verification-cluster"]
    assert len(clusters) == 1
    assert clusters[0]["matched_value"] == "the real claim text here"


def test_two_in_one_project_plus_one_in_another_form_a_three_member_cluster(
    tmp_path: Path,
) -> None:
    """A shared path token cited by TWO entries in project A and ONE entry
    in project B yields ONE 3-member cluster, not something narrower --
    ALL items sharing the key are included once the key qualifies as
    cross-project, not merely the cross-project pairs (docstring: "a key
    hit by two entries in project A and one in project B still yields one
    3-member cluster")."""
    _write_tracked(
        tmp_path,
        "alpha",
        "## DW-1\nstatus: open\nCode: `shared/thing.py`\n\n## DW-2\nstatus: open\nAlso `shared/thing.py`\n",
    )
    _write_tracked(
        tmp_path,
        "beta",
        "## DW-3\nstatus: open\nStill `shared/thing.py`\n",
    )

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    clusters = [f for f in findings if f["kind"] == "due-for-verification-cluster"]
    assert len(clusters) == 1
    assert sorted((m["project"], m["id"]) for m in clusters[0]["members"]) == [
        ("alpha", "DW-1"),
        ("alpha", "DW-2"),
        ("beta", "DW-3"),
    ]


def test_dual_match_on_path_and_text_never_merges_into_one_cluster(tmp_path: Path) -> None:
    """A pair matching on BOTH a shared path token AND normalized-identical
    claim text produces TWO independent cluster items, never one merged
    group (Boundaries: "Never merge overlapping clusters ... out of scope
    for this story's narrow, mechanical shape")."""
    _write_tracked(
        tmp_path,
        "alpha",
        "## DW-1\nstatus: open\nsummary: the exact same claim\nCode: `shared/thing.py`\n",
    )
    _write_tracked(
        tmp_path,
        "beta",
        "## DW-2\nstatus: open\nsummary: the exact same claim\nCode: `shared/thing.py`\n",
    )

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    clusters = [f for f in findings if f["kind"] == "due-for-verification-cluster"]
    assert len(clusters) == 2
    matched_on_values = sorted(c["matched_on"] for c in clusters)
    assert matched_on_values == ["path", "summary"]
    for cluster in clusters:
        assert sorted((m["project"], m["id"]) for m in cluster["members"]) == [
            ("alpha", "DW-1"),
            ("beta", "DW-2"),
        ]


def test_duplicate_id_within_one_ledger_never_double_counts_a_member(
    tmp_path: Path,
) -> None:
    """A malformed ledger with two physical entries sharing one `DW-` id
    (a known, pre-existing data-quality edge case this exact file already
    documents for `_check_project_due_for_verification`'s own per-entry
    attachments) must never produce a cluster with the same `(project, id)`
    member listed twice (review finding, patch: `_entry_named_paths`/
    `_entry_claim_text` collapse a duplicate id to its last occurrence, so
    both physical entries look up the same data -- `members` is deduplicated
    by `(project, id)` specifically to bound this to "at most one entry per
    id," never a doubled count)."""
    _write_tracked(
        tmp_path,
        "alpha",
        "## DW-1\nstatus: open\nCode: `shared/thing.py`\n\n## DW-1\nstatus: open\nAlso `shared/thing.py` here too\n",
    )
    _write_tracked(
        tmp_path,
        "beta",
        "## DW-2\nstatus: open\nAlso `shared/thing.py`\n",
    )

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    clusters = [f for f in findings if f["kind"] == "due-for-verification-cluster"]
    assert len(clusters) == 1
    members = clusters[0]["members"]
    assert len(members) == len({(m["project"], m["id"]) for m in members})


# --- (d) no shared signal: never clusters ----------------------------------------


def test_distinct_paths_and_distinct_text_do_not_cluster(tmp_path: Path) -> None:
    """Due entries in different projects with distinct paths and distinct
    text -- no cluster emitted at all."""
    _write_tracked(
        tmp_path,
        "alpha",
        "## DW-1\nstatus: open\nsummary: alpha's own unrelated issue\nCode: `alpha/only.py`\n",
    )
    _write_tracked(
        tmp_path,
        "beta",
        "## DW-2\nstatus: open\nsummary: beta's own totally different issue\nCode: `beta/only.py`\n",
    )

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert [f["kind"] for f in findings] == [
        "due-for-verification",
        "due-for-verification",
    ]


# --- (e) the correlation pass itself failing degrades to zero clusters ---------


def test_correlation_pass_failure_degrades_to_zero_clusters_but_keeps_per_entry_findings(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A project's ledger becoming unreadable SPECIFICALLY during the
    correlation pass's own re-read (not during `_check_project_due_for_
    verification`'s own per-entry pass) must degrade the WHOLE correlation
    pass to zero clusters, never crash, and never discard any already-
    computed per-entry Finding (Boundaries: "Isolate the whole correlation
    pass in one try/except ... degrades to 'no clusters found' ... never
    crashes or discards the already-computed per-entry findings").

    Monkeypatches `_entry_claim_text` -- a function called ONLY from the
    correlation pass, never from `_check_project_due_for_verification` --
    so both projects' own per-entry passes genuinely succeed FIRST (proving
    the two per-entry findings below are real, not accidentally suppressed
    by the same failure); only the correlation pass's own re-read fails.
    The fixture shares a path token across both projects specifically so
    that, absent the induced failure, a cluster WOULD have formed -- proving
    the zero-cluster outcome is the induced degrade, not just "nothing to
    cluster"."""
    _write_tracked(
        tmp_path,
        "alpha",
        "## DW-1\nstatus: open\nCode: `shared/thing.py`\n",
    )
    _write_tracked(
        tmp_path,
        "beta",
        "## DW-2\nstatus: open\nCode: `shared/thing.py`\n",
    )

    def _boom(path):
        raise OSError("simulated unreadable ledger during correlation")

    monkeypatch.setattr(chain, "_entry_claim_text", _boom)

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    per_entry = [f for f in findings if f["kind"] == "due-for-verification"]
    clusters = [f for f in findings if f["kind"] == "due-for-verification-cluster"]
    assert {(f["project"], f["id"]) for f in per_entry} == {
        ("alpha", "DW-1"),
        ("beta", "DW-2"),
    }
    assert clusters == []


# --- (f) public API: the cluster Finding survives the wrap ----------------------


def test_cluster_finding_survives_gather_due_for_verification_public_api(
    tmp_path: Path,
) -> None:
    """The cluster Finding survives `gather_due_for_verification`'s wrap
    with `check == "due-for-verification-cluster"` and `evidence` carrying
    `matched_on`/`matched_value`/`members` (Tasks & Acceptance). No
    `verified:` line on either entry -- always "never-verified", so this
    stays time-invariant (module docstring's own testing discipline)."""
    _write_tracked(
        tmp_path,
        "alpha",
        "## DW-1\nstatus: open\nCode: `shared/thing.py`\n",
    )
    _write_tracked(
        tmp_path,
        "beta",
        "## DW-2\nstatus: open\nAlso `shared/thing.py`\n",
    )

    findings = chain.gather_due_for_verification(tmp_path)

    clusters = [f for f in findings if f.check == "due-for-verification-cluster"]
    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster.source is Source.DUE_FOR_VERIFICATION
    assert cluster.status is DoctorStatus.WARN
    assert cluster.evidence["matched_on"] == "path"
    assert cluster.evidence["matched_value"] == "shared/thing.py"
    assert sorted((m["project"], m["id"]) for m in cluster.evidence["members"]) == [
        ("alpha", "DW-1"),
        ("beta", "DW-2"),
    ]


# === Story 11.7: aggregate verification coverage ================================
#
# Covers the spec's own I/O & Edge-Case Matrix for `_verification_coverage`
# directly against REAL tmp fixture trees -- mirrors Story 11.5's own
# `_known_project_code_roots` testing discipline (lines 1217+ above) of unit-
# testing a new pure helper directly, plus one integration-style test proving
# the item survives `gather_due_for_verification`'s own Finding wrap (the
# story's own AC wording). Direct-helper tests pin `today` (mirrors this
# module's own "precise day-count assertions" convention); the one public-API
# test below uses a far-future `verified:` date to stay time-invariant
# (module docstring's own testing discipline), exactly like
# `test_findings_evidence_project_key_names_its_own_project_via_public_api`'s
# own `9999-01-01` fixture above.


def test_verification_coverage_mixed_staleness_reports_correct_total_and_pct(
    tmp_path: Path,
) -> None:
    """10 tracked entries, 4 verified within the 30-day window (the spec's
    own I/O matrix example): total=10, verified_within_window=4, pct=40."""
    text = "".join(
        f"## DW-{n}\nverified: 2026-08-{10 - n:02d}\n\n" for n in range(1, 5)
    )  # DW-1..DW-4: verified 2026-08-09..2026-08-06 -- all within 30 days
    text += "".join(f"## DW-{n}\nverified: 2026-01-01 — ancient\n\n" for n in range(5, 8))  # DW-5..DW-7: stale
    text += "".join(f"## DW-{n}\nstatus: open\n\n" for n in range(8, 11))  # DW-8..DW-10: never-verified
    _write_tracked(tmp_path, "proj", text)

    items = chain._verification_coverage(tmp_path, today=date(2026, 8, 15))

    assert len(items) == 1
    item = items[0]
    assert item["kind"] == "verification-coverage"
    assert item["project"] == "proj"
    assert item["total"] == 10
    assert item["verified_within_window"] == 4
    assert item["window_days"] == chain.DUE_FOR_VERIFICATION_STALENESS_DAYS
    assert item["pct"] == 40


def test_verification_coverage_all_fresh_reports_pct_100(tmp_path: Path) -> None:
    _write_tracked(
        tmp_path,
        "proj",
        "## DW-1\nverified: 2026-08-10\n\n## DW-2\nverified: 2026-08-01\n",
    )

    items = chain._verification_coverage(tmp_path, today=date(2026, 8, 15))

    assert len(items) == 1
    assert items[0]["total"] == 2
    assert items[0]["verified_within_window"] == 2
    assert items[0]["pct"] == 100


def test_verification_coverage_none_verified_reports_pct_0(tmp_path: Path) -> None:
    _write_tracked(
        tmp_path,
        "proj",
        "## DW-1\nstatus: open\n\n## DW-2\nverified: 2000-01-01 — ancient\n",
    )

    items = chain._verification_coverage(tmp_path, today=date(2026, 8, 15))

    assert len(items) == 1
    assert items[0]["total"] == 2
    assert items[0]["verified_within_window"] == 0
    assert items[0]["pct"] == 0


def test_verification_coverage_zero_tracked_entries_emits_no_item(tmp_path: Path) -> None:
    """A project directory that exists but has no tracked ledger file at
    all -- zero tracked entries -- must emit no item (Boundaries: "a '0% of
    0' line is noise, not signal")."""
    _project_dir(tmp_path, "proj").mkdir(parents=True, exist_ok=True)

    items = chain._verification_coverage(tmp_path, today=date(2026, 8, 15))

    assert items == []


def test_verification_coverage_anonymous_headerless_entries_emit_no_item(
    tmp_path: Path,
) -> None:
    """A ledger with content but zero ID'd entries (no ``## DW-...`` heading)
    counts as zero tracked entries too."""
    _write_tracked(tmp_path, "proj", "- source_spec: `foo`\n  verified: 2000-01-01\n")

    items = chain._verification_coverage(tmp_path, today=date(2026, 8, 15))

    assert items == []


def test_verification_coverage_no_projects_tree_degrades_to_empty_list(
    tmp_path: Path,
) -> None:
    assert chain._verification_coverage(tmp_path, today=date(2026, 8, 15)) == []


def test_verification_coverage_multiple_projects_each_get_own_item(
    tmp_path: Path,
) -> None:
    _write_tracked(tmp_path, "alpha", "## DW-1\nverified: 2026-08-10\n")
    _write_tracked(
        tmp_path,
        "beta",
        "## DW-1\nstatus: open\n\n## DW-2\nstatus: open\n",
    )

    items = chain._verification_coverage(tmp_path, today=date(2026, 8, 15))

    by_project = {item["project"]: item for item in items}
    assert set(by_project) == {"alpha", "beta"}
    assert by_project["alpha"]["total"] == 1
    assert by_project["alpha"]["pct"] == 100
    assert by_project["beta"]["total"] == 2
    assert by_project["beta"]["pct"] == 0


def test_verification_coverage_unreadable_ledger_is_isolated_per_project(
    tmp_path: Path,
) -> None:
    """Mirrors ``test_unreadable_tracked_ledger_directory_is_isolated_as_warn``'s
    own chmod fixture: one project's unreadable tracked-ledger directory must
    not discard another, ALREADY-COMPUTED project's coverage item."""
    _write_tracked(tmp_path, "good", "## DW-1\nverified: 2026-08-10\n")
    _write_tracked(tmp_path, "broken", "## DW-1\nstatus: open\n")

    pa_dir = _project_dir(tmp_path, "broken") / "planning-artifacts"
    pa_dir.chmod(0o000)
    try:
        items = chain._verification_coverage(tmp_path, today=date(2026, 8, 15))
    finally:
        pa_dir.chmod(0o755)

    assert [item["project"] for item in items] == ["good"]
    assert items[0]["total"] == 1
    assert items[0]["verified_within_window"] == 1
    assert items[0]["pct"] == 100


def test_due_for_verification_message_verification_coverage_branch() -> None:
    item = {
        "kind": "verification-coverage",
        "project": "proj",
        "total": 10,
        "verified_within_window": 4,
        "window_days": chain.DUE_FOR_VERIFICATION_STALENESS_DAYS,
        "pct": 40,
    }
    assert chain._due_for_verification_message(item) == ("proj: 40% of 10 tracked entries verified within 30 days.")


def test_gather_due_for_verification_carries_verification_coverage_item(
    tmp_path: Path,
) -> None:
    """AC: given a project's tracked ledger with a known mix of verified/
    stale/never-verified entries, `gather_due_for_verification`'s evidence
    carries a `verification-coverage` item with the correct total/
    verified_within_window/pct."""
    _write_tracked(
        tmp_path,
        "proj",
        "## DW-1\nverified: 9999-01-01 — always fresh\n\n"
        "## DW-2\nverified: 2000-01-01 — ancient\n\n"
        "## DW-3\nstatus: open\n",
    )

    findings = chain.gather_due_for_verification(tmp_path)

    coverage = [f for f in findings if f.check == "verification-coverage"]
    assert len(coverage) == 1
    finding = coverage[0]
    assert finding.source is Source.DUE_FOR_VERIFICATION
    assert finding.status is DoctorStatus.WARN
    assert finding.evidence["project"] == "proj"
    assert finding.evidence["total"] == 3
    assert finding.evidence["verified_within_window"] == 1
    assert finding.evidence["pct"] == 33
    assert finding.message == ("proj: 33% of 3 tracked entries verified within 30 days.")


# --- Path-token precision (2026-09-08): a dotted symbol is not a file ----------


@pytest.mark.parametrize(
    "token",
    [
        "src/pyforge/doctor/sources/chain.py",
        "scripts/detectors.py",
        "pixi.toml",
        "AGENTS.md",
        "pixi.lock",
        "docs/dreams/pyforge-marshal",  # slash, no extension
    ],
)
def test_is_path_token_accepts_real_files(token: str) -> None:
    assert chain._is_path_token(token) is True


@pytest.mark.parametrize(
    "token",
    [
        "os.replace",
        "Path.glob",
        "Finding.path",
        "CurrencyEngine.run",
        "pyforge.doctor.sources",
        "json.dumps",
        "github.com",
        "0.73.0",
    ],
)
def test_is_path_token_rejects_attribute_access(token: str) -> None:
    """These are what the old any-`.<alnum>` pattern swept in: 471 of 1,450
    dotted-only tokens across the eight tracked ledgers were attribute
    accesses or version strings. None can resolve to a file, so admitting
    them made every churn verdict read 'not skipped' for the wrong reason."""
    assert chain._is_path_token(token) is False


def test_dotted_symbol_is_never_a_churn_candidate(tmp_path: Path) -> None:
    """End-to-end twin of ``test_source_spec_path_is_never_a_churn_candidate``:
    an entry citing BOTH a real file and a dotted symbol must be skipped on
    the real file alone, with the symbol absent from the checked set."""
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(target, "src/foo.py", "x = 1\n", "2026-01-01T00:00:00+00:00")
    _write_tracked(
        target,
        "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\nCode: `src/foo.py` calls `os.replace` on `Finding.path`\n",
    )

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    assert len(findings) == 1
    assert findings[0].get("skip_reason") == "no-churn"
    assert findings[0]["churn_checked_paths"] == ["src/foo.py"]


def test_path_extensions_cover_every_cited_tracked_file() -> None:
    """`_PATH_EXTENSIONS` is derived from measurement, so it must not silently
    fall behind the ledgers it was derived from.

    Sweeps the live tracked ledgers for dotted-only citations whose trailing
    segment names a real tracked file, and asserts the set admits it. A new
    file type cited in a future entry fails HERE rather than silently
    dropping out of the churn check.
    """
    root = Path(__file__).resolve().parents[6]
    ledgers = sorted(root.glob("_bmad-output/projects/*/planning-artifacts/deferred-work-ledger.md"))
    if not ledgers:
        pytest.skip("tracked ledgers unavailable (packaged install)")
    # `git ls-files`, not `rglob` -- the working tree carries `.pixi`
    # environments that dwarf the repo, and "tracked" is the set this
    # assertion actually means.
    listing = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if listing.returncode != 0:
        pytest.skip("git unavailable")
    tracked_basenames = {line.rsplit("/", 1)[-1] for line in listing.stdout.split()}
    missing: dict[str, str] = {}
    for ledger in ledgers:
        text = ledger.read_text(encoding="utf-8", errors="replace")
        for m in chain._PATH_TOKEN_RE.finditer(text):
            token = m.group(1)
            if "/" in token or "." not in token:
                continue
            ext = token.rsplit(".", 1)[-1].lower()
            if ext in chain._PATH_EXTENSIONS:
                continue
            if token in tracked_basenames:
                missing[ext] = token
    assert not missing, (
        "cited real files whose extension _PATH_EXTENSIONS omits: "
        f"{missing} — add the extension (and say why in its comment)"
    )
