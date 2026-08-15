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

import os
import subprocess
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
        cwd=target, env=env, check=True,
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
        tmp_path, "proj",
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
        tmp_path, "proj",
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
        tmp_path, "proj",
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
        tmp_path, "proj",
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
        tmp_path, "beta", "## DW-1\nverified: 2026-08-10 — recent\n",
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

    assert len(findings) == 1
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

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK
    assert findings[0].evidence == {"projects_scanned": 1}


# --- Finding shape through the public API (never-verified, time-invariant) -----------


def test_gather_wraps_never_verified_finding_with_correct_shape(tmp_path: Path) -> None:
    _write_tracked(tmp_path, "proj", "## DW-1\nstatus: open\n")

    findings = chain.gather_due_for_verification(tmp_path)

    assert len(findings) == 1
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
        tmp_path, "proj",
        "## DW-1\nstatus: open\n\n## DW-2\nverified: 2000-01-01 — ancient\n",
    )

    findings = chain.gather_due_for_verification(tmp_path)

    assert len(findings) == 2
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
    tmp_path: Path, monkeypatch,
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
        target, "proj",
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
        target, "proj",
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
        target, "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\n"
        "Touches `src/a.py` (clean) and `src/b.py` (churned).\n",
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
        target, "proj",
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
        target, "proj",
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
            ["git", "commit", "-q", "-m", subject], cwd=target, env=env, check=True,
        )

    # T1: the unrelated LONGER id is introduced first.
    _commit_ledger(
        "## DW-1-1-10 — unrelated\nstatus: open\n",
        "2026-01-05T00:00:00+00:00", "proj: add DW-1-1-10",
    )
    # T2: the source path is touched -- AFTER the confusable neighbour's
    # (wrong, buggy) date but BEFORE the real entry's (correct) date. This
    # is the only window where the two candidate dates disagree.
    _commit_file(target, "src/shared.py", "x = 1\n", "2026-02-05T00:00:00+00:00")
    # T3: the entry actually under test is introduced.
    _commit_ledger(
        "## DW-1-1-10 — unrelated\nstatus: open\n\n"
        "## DW-1-1-1 — the real entry\nCode: `src/shared.py`\n",
        "2026-03-05T00:00:00+00:00", "proj: add DW-1-1-1",
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
        target, "docs/specs/thing.md", "v1\n", "2026-01-01T00:00:00+00:00",
    )
    _commit_file(
        target, "docs/specs/thing.md", "v2\n", "2026-07-10T00:00:00+00:00",
    )  # churned AFTER the verified date -- must not block the skip
    _commit_file(target, "src/foo.py", "x = 1\n", "2026-01-01T00:00:00+00:00")
    _write_tracked(
        target, "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\n"
        "- source_spec: `docs/specs/thing.md`\n"
        "Code: `src/foo.py`\n",
    )

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    assert len(findings) == 1
    assert findings[0].get("skip_reason") == "no-churn"
    assert findings[0]["churn_checked_paths"] == ["src/foo.py"]


# --- Row 9: per-entry git failure is isolated -----------------------------------


def test_per_entry_churn_failure_is_isolated_from_its_project_siblings(
    tmp_path: Path, monkeypatch,
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
        target, "proj",
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
        target, "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\nCode: `src/foo.py`\n",
    )

    findings = chain.gather_due_for_verification(target)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.evidence.get("skip_reason") == "no-churn"
    assert "skip_reason: no-churn" in finding.message
    assert "due for re-check" in finding.message  # base message text intact


def test_message_omits_skip_decision_text_when_no_skip_reason(tmp_path: Path) -> None:
    _write_tracked(tmp_path, "proj", "## DW-1\nstatus: open\n")

    findings = chain.gather_due_for_verification(tmp_path)

    assert len(findings) == 1
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
        target, "src/foo.py", "def _foo(x):\n    return x\n",
        "2026-01-01T00:00:00+00:00",
    )
    # The ledger is COMMITTED and its own claim text backtick-cites `_foo` --
    # without the `:(exclude,glob)**/deferred-work-ledger.md` pathspec, this
    # citation alone would count as a call site and force `escalate`.
    _commit_file(
        target, _tracked_rel("proj"),
        "## DW-1\nverified: 2026-07-01 — checked once\n"
        "Claim: `_foo` is unused and should be removed.\n",
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
        target, "src/foo.py",
        "def _foo(x):\n    return x\n\n\ndef bar():\n"
        "    y = _foo(1)\n    z = _foo(2)\n    return y + z\n",
        "2026-01-01T00:00:00+00:00",
    )
    _commit_file(
        target, _tracked_rel("proj"),
        "## DW-1\nverified: 2026-07-01 — checked once\n"
        "Claim: `_foo` is unused and should be removed.\n",
        "2026-07-01T00:00:00+00:00",
    )

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    assert len(findings) == 1
    item = findings[0]
    assert item["mechanical_verdict"] == "escalate"
    assert item["mechanical_symbol"] == "_foo"
    # 2 live call sites -- the `def _foo(x):` declaration line is excluded.
    assert item["mechanical_call_sites"] == 2


# --- Regression: async def is recognized as a declaration -----------------------


def test_async_def_declaration_is_recognized_and_excluded(tmp_path: Path) -> None:
    target = tmp_path / "target"
    _init_repo(target)
    _commit_file(
        target, "src/foo.py", "async def _foo(x):\n    return x\n",
        "2026-01-01T00:00:00+00:00",
    )
    _commit_file(
        target, _tracked_rel("proj"),
        "## DW-1\nverified: 2026-07-01 — checked once\n"
        "Claim: `_foo` is unused and should be removed.\n",
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
        target, "src/foo.py", "_FOO_CONST = 42\n",
        "2026-01-01T00:00:00+00:00",
    )
    _commit_file(
        target, _tracked_rel("proj"),
        "## DW-1\nverified: 2026-07-01 — checked once\n"
        "Claim: `_FOO_CONST` is unused and should be removed.\n",
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
        target, "src/foo.py", "def _foo(x):\n    return x\n",
        "2026-01-01T00:00:00+00:00",
    )
    _commit_file(
        target, _tracked_rel("proj"),
        "## DW-1\nverified: 2026-07-01 — checked once\n"
        "Claim: `_foo` is unused and should be removed.\n",
        "2026-07-01T00:00:00+00:00",
    )
    # A brand-new caller, written but NEVER `git add`-ed/committed.
    (target / "src" / "new_caller.py").write_text(
        "y = _foo(5)\n", encoding="utf-8",
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
        target, "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\n"
        "`_foo` is unused. See `src/foo.py:10`.\n",
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
        target, "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\n"
        "Investigate feasibility of caching this lookup someday.\n",
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
        target, "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\n"
        "Claim: `Foo.bar` is unused.\n",
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
        target, "src/foo.py", "def _foo(x):\n    return x\n",
        "2026-01-01T00:00:00+00:00",
    )
    _write_tracked(
        target, "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\n"
        "Claim: `_foo` is unused and should be removed.\n",
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
    tmp_path: Path, monkeypatch,
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
        target, "src/foo.py", "def _foo(x):\n    return x\n",
        "2026-01-01T00:00:00+00:00",
    )
    _commit_file(
        target, "src/bar.py", "def _bar():\n    pass\n",
        "2026-01-01T00:00:00+00:00",
    )
    _commit_file(
        target, _tracked_rel("proj"),
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
        target, "src/foo.py", "def _foo(x):\n    return x\n",
        "2026-01-01T00:00:00+00:00",
    )
    _commit_file(
        target, _tracked_rel("proj"),
        "## DW-1\nverified: 2026-07-01 — checked once\n"
        "Claim: `_foo` is unused and should be removed.\n",
        "2026-07-01T00:00:00+00:00",
    )

    findings = chain.gather_due_for_verification(target)

    assert len(findings) == 1
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
        target, "src/foo.py", "def _foo(x):\n    return x\n\n\ndef bar():\n"
        "    y = _foo(1)\n    z = _foo(2)\n    return y + z\n",
        "2026-01-01T00:00:00+00:00",
    )
    _write_tracked(
        target, "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\n"
        "Claim: `_foo` is unused and should be removed.\n",
    )

    findings = chain.gather_due_for_verification(target)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.evidence.get("mechanical_verdict") == "escalate"
    assert "mechanical_verdict: escalate" in finding.message


def test_message_omits_mechanical_text_when_no_mechanical_verdict(
    tmp_path: Path,
) -> None:
    _write_tracked(tmp_path, "proj", "## DW-1\nstatus: open\n")

    findings = chain.gather_due_for_verification(tmp_path)

    assert len(findings) == 1
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
        target, "src/foo.py", "def _foo(x):\n    return x\n",
        "2026-01-01T00:00:00+00:00",
    )
    _commit_file(target, ".gitignore", "ignored_dir/\n", "2026-01-01T00:00:00+00:00")
    _commit_file(
        target, _tracked_rel("proj"),
        "## DW-1\nverified: 2026-07-01 — checked once\n"
        "Claim: `_foo` is unused and should be removed.\n",
        "2026-07-01T00:00:00+00:00",
    )
    # A brand-new caller under a gitignored directory -- never `git add`-ed.
    (target / "ignored_dir").mkdir()
    (target / "ignored_dir" / "caller.py").write_text(
        "y = _foo(5)\n", encoding="utf-8",
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
        target, "src/foo.py",
        "def _foo(x): return _foo(x - 1) if x else 0\n",
        "2026-01-01T00:00:00+00:00",
    )
    _write_tracked(
        target, "proj",
        "## DW-1\nverified: 2026-07-01 — checked once\n"
        "Claim: `_foo` is unused and should be removed.\n",
    )

    findings = chain._due_for_verification_findings(target, today=date(2026, 8, 15))

    assert len(findings) == 1
    item = findings[0]
    assert item["mechanical_verdict"] == "escalate"
    assert item["mechanical_call_sites"] == 1
