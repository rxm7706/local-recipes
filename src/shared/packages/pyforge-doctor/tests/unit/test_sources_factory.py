"""Unit tests for ``pyforge.doctor.sources.factory.gather`` (Story 6.8) --
covers every row of the spec's I/O & Edge-Case Matrix, all 18 origin finding
kinds, and the per-check isolation the module's own docstring describes,
against REAL tmp git repositories (mirrors ``test_sources_ledger.py``'s own
real-git-fixture style; this test file is not restricted to
``cli_bridge.py`` -- only the package source under ``pyforge/doctor/`` is).

Fixture shape: ``_bootstrap`` builds a fully self-consistent, CLEAN
``pyforge-marshal`` project -- every one of the 17 ``TRACKED`` docs pinned at
the live skill version, a sync baseline matching the live fingerprint exactly,
no dreams, no intake specs, no implementation-artifacts -- and commits it.
``gather`` against that fixture returns exactly one aggregate OK Finding
(``test_clean_project_reports_a_single_ok_finding``); every other test starts
from this same clean commit and layers ONE mutation on top, UNCOMMITTED, so a
mutation under ``implementation-artifacts/`` does not also trip
``check_tier_alignment`` (which only flags GIT-TRACKED files) -- see
``_bootstrap``'s own docstring.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import factory

#: ``chmod 000`` does not stop root, so the cannot-evaluate tests below would
#: read a perfectly clean tree and assert a WARN that never comes. The
#: ``test_sources_chain_*.py`` permission tests predate this guard and simply
#: assume an unprivileged runner; skipping is the honest form of the same
#: assumption.
_needs_unprivileged = pytest.mark.skipif(
    os.geteuid() == 0,
    reason="chmod-based unreadable-directory tests are meaningless as root",
)

# Mirrors test_sources_ledger.py's own scrub: a contributor's own git config
# must not decide whether this suite passes (GIT_DIR leakage, commit signing,
# a global core.hooksPath). See that file's own comment for the verified
# regression this fixture prevents.
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


# --------------------------------------------------------------- fixture helpers


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "--initial-branch=main")
    _git(repo, "config", "user.email", "doctor-test@example.com")
    _git(repo, "config", "user.name", "Doctor Test")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "core.hooksPath", "/dev/null")


def _commit_all(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


def _pinned_md(repo: Path, rel: str, version: str, body: str = "body\n") -> Path:
    path = factory._proj(repo) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nsource_pin: conda-forge-expert v{version}\n---\n{body}", encoding="utf-8")
    return path


def _pinned_json(repo: Path, rel: str, version: str) -> Path:
    path = factory._proj(repo) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'{{"source_pin": "conda-forge-expert v{version}"}}\n', encoding="utf-8")
    return path


def _seed_ground_truth(repo: Path, version: str = "1.0.0") -> None:
    """The live-factory scaffolding ``_ground_truth``/``_fingerprint`` read:
    a skill CHANGELOG.md pin, an atlas phase registry (``B``/``C``/``D``/
    ``E`` -> ``atlas_phases=4``, ``max_single_phase="E"``), a SKILL.md
    gotcha range (``G1``/``G3``/``G5`` -> ``gotcha_max=5``), an MCP server
    stub (2 ``@mcp.tool`` markers), a pixi.toml ``[environments]`` block (3
    envs), and the governance roster Part 1 consolidated."""
    skill = repo / ".claude" / "skills" / "conda-forge-expert"
    (skill / "scripts").mkdir(parents=True, exist_ok=True)
    (skill / "CHANGELOG.md").write_text(f"## Changelog\n\n**v{version}**\n", encoding="utf-8")
    (skill / "scripts" / "conda_forge_atlas.py").write_text(
        "SCHEMA_VERSION = 1\n\n"
        "PHASES = [\n"
        '    ("B", "desc"),\n'
        '    ("C", "desc"),\n'
        '    ("D", "desc"),\n'
        '    ("E", "desc"),\n'
        "]\n",
        encoding="utf-8",
    )
    (skill / "SKILL.md").write_text(
        f"---\nname: conda-forge-expert\nversion: {version}\n---\n### G1\nfoo\n### G3\nbar\n### G5\nbaz\n",
        encoding="utf-8",
    )
    tools = repo / ".claude" / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    (tools / "conda_forge_server.py").write_text(
        "@mcp.tool\ndef foo(): ...\n\n@mcp.tool\ndef bar(): ...\n", encoding="utf-8"
    )
    (repo / "pixi.toml").write_text('[environments]\ndefault = ["a"]\nbuild = ["b"]\ndocs = ["c"]\n', encoding="utf-8")
    gov = repo / "docs" / "governance"
    gov.mkdir(parents=True, exist_ok=True)
    (gov / "guild-roster.json").write_text(
        json.dumps(
            {
                "stations": ["marshal", "doctor"],
                "guild_dreams": ["pyforge-charter"],
                "dream_statuses": ["dreamt", "pitched", "specified", "realized", "archived"],
                "dream_types": ["dream", "practice"],
            }
        ),
        encoding="utf-8",
    )


def _seed_all_tracked(repo: Path, version: str = "1.0.0") -> None:
    for rel, _cat in factory.TRACKED:
        if rel.endswith(".json"):
            _pinned_json(repo, rel, version)
        else:
            _pinned_md(repo, rel, version)


def _write_baseline(repo: Path) -> None:
    fingerprint = factory._fingerprint(repo)
    baseline = factory._proj(repo) / ".sync-baseline.json"
    baseline.parent.mkdir(parents=True, exist_ok=True)
    baseline.write_text(json.dumps(fingerprint), encoding="utf-8")


def _bootstrap(repo: Path, version: str = "1.0.0") -> None:
    """Build + commit a fully clean ``pyforge-marshal`` project: every
    TRACKED doc pinned at ``version``, a baseline matching the live
    fingerprint exactly, no dreams/specs/implementation-artifacts.
    ``gather`` against the result is exactly one aggregate OK Finding.

    Callers apply their own mutation AFTER this returns and deliberately do
    NOT commit it again: ``check_tier_alignment`` only flags GIT-TRACKED
    files under ``implementation-artifacts/``, so an uncommitted mutation
    there cannot cross-contaminate a test that is not about tier alignment.
    A test that specifically wants a tracked artifact commits its own
    mutation explicitly (see ``test_git_tracked_impl_artifact_is_flagged``).
    """
    _init_repo(repo)
    _seed_ground_truth(repo, version)
    _seed_all_tracked(repo, version)
    _write_baseline(repo)
    _commit_all(repo, "seed clean pyforge-marshal project")


def _only(findings: tuple, check: str):
    matches = [f for f in findings if f.check == check]
    assert len(matches) == 1, f"expected exactly one {check!r} finding, got {findings!r}"
    return matches[0]


# ------------------------------------------------------------- happy path / OK


def test_clean_project_reports_a_single_ok_finding(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _bootstrap(repo)

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.BMAD_DRIFT
    assert finding.check == "bmad-drift"
    assert finding.status is DoctorStatus.OK


# ------------------------------------------------------------------ pin-missing


def test_pin_missing_reports_fail(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _bootstrap(repo)
    (factory._proj(repo) / "planning-artifacts" / "index.md").unlink()

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.BMAD_DRIFT
    assert finding.check == "pin-missing"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["subject"] == "planning-artifacts/index.md"
    assert finding.evidence["severity"] == "HARD"


def test_pin_missing_is_not_reported_for_a_snapshot_category_doc(tmp_path: Path) -> None:
    """Verbatim from the original: a missing pin on a ``snapshot`` doc is
    not gated -- it is a frozen, dated record, not expected to carry a
    live-tracking pin."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    (factory._proj(repo) / "planning-artifacts" / "validation-report-PRD.md").unlink()

    findings = factory.gather(repo)

    assert len(findings) == 1
    assert findings[0].check == "bmad-drift"
    assert findings[0].status is DoctorStatus.OK


# ------------------------------------------------------------------- pin-behind


def test_living_doc_with_old_pin_does_not_report_pin_behind(tmp_path: Path) -> None:
    """Story 33.10: ``source_pin`` on living docs is a re-grounding record,
    not a currency claim — an old pin must not emit ``pin-behind``."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    _pinned_md(repo, "planning-artifacts/index.md", "0.9.0")

    findings = factory.gather(repo)

    assert not any(f.check == "pin-behind" for f in findings)
    assert len(findings) == 1
    assert findings[0].check == "bmad-drift"
    assert findings[0].status is DoctorStatus.OK


def test_pin_behind_on_a_snapshot_doc_reports_ok(tmp_path: Path) -> None:
    """Verbatim from the original: ``sev = INFO if cat == "snapshot" else
    DRIFT`` -- a behind pin on a frozen snapshot doc is worth noting but
    never gates."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    _pinned_md(repo, "planning-artifacts/validation-report-PRD.md", "0.9.0")

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "pin-behind"
    assert finding.status is DoctorStatus.OK
    assert finding.evidence["severity"] == "INFO"


def _pinned_md_raw(repo: Path, rel: str, pin_line: str, body: str = "body\n") -> Path:
    """Like ``_pinned_md``, but the caller supplies the WHOLE ``source_pin``
    value verbatim -- for pin shapes ``_pinned_md``'s single-version
    convenience wrapper cannot express (a compound pin naming two
    versions)."""
    path = factory._proj(repo) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{pin_line}\n---\n{body}", encoding="utf-8")
    return path


def test_compound_pin_with_matching_live_version_reports_clean(tmp_path: Path) -> None:
    """``architecture-bmad-infra.md``'s own real, deliberate format (Story
    25-7): a compound ``source_pin`` naming BOTH the BMAD-core version and
    the conda-forge-expert skill version, e.g. ``'BMAD 6.11.0 / conda-forge-
    expert v8.84.0'``. When the skill-version half matches live exactly,
    this must read as a fully clean pin -- neither ``pin-missing`` (the bug
    this test guards: the pre-fix regex could not parse this shape at all
    and reported the doc as unpinned) nor ``pin-behind`` on a WRONG number
    (a naive fix that made ``conda-forge-expert`` optional in front of a
    lazy prefix-skip would latch onto ``6.11.0``, BMAD's own version, and
    since 6.11 > the live skill version used here would misreport this
    doc as fine for the wrong reason on this particular live version --
    the sibling test below pins live below 6.11 specifically to catch
    that instead)."""
    repo = tmp_path / "repo"
    _bootstrap(repo, "8.84.0")
    _pinned_md_raw(
        repo,
        "planning-artifacts/architecture-bmad-infra.md",
        "source_pin: 'BMAD 6.11.0 / conda-forge-expert v8.84.0'",
    )

    findings = factory.gather(repo)

    assert len(findings) == 1
    assert findings[0].check == "bmad-drift"
    assert findings[0].status is DoctorStatus.OK


def test_compound_pin_on_snapshot_still_reports_behind(tmp_path: Path) -> None:
    """Compound pins on snapshot docs still compare the conda-forge-expert
    half against live ``SKILL.md`` ``version:`` (Story 33.10 leaves snapshot
    ``pin-behind`` at INFO). Living/plan docs suppress behind-ness entirely."""
    repo = tmp_path / "repo"
    _bootstrap(repo, "9.0.0")
    _pinned_md_raw(
        repo,
        "planning-artifacts/validation-report-PRD.md",
        "source_pin: 'BMAD 6.11.0 / conda-forge-expert v8.84.0'",
    )

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "pin-behind"
    assert finding.status is DoctorStatus.OK
    assert finding.evidence["severity"] == "INFO"
    assert "8.84.0" in finding.message
    assert "6.11.0" not in finding.message


def test_pin_naming_conda_forge_expert_with_no_version_after_it_still_reports_missing(
    tmp_path: Path,
) -> None:
    """A corrupt pin that mentions ``conda-forge-expert`` but never actually
    states its version (or states only an unrelated BMAD-core version with
    no ``conda-forge-expert`` marker at all) must still report
    ``pin-missing`` -- the two-phase parse must not become a blanket "find
    ANY version-shaped text somewhere in the value" that papers over real
    corruption, which is exactly the failure mode this module's own
    docstring already records history of (`"fabricated FALSE pin-missing
    HARD findings"` / `"manufactured FOURTEEN FALSE pin-missing HARD
    findings"`) in the opposite direction."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    _pinned_md_raw(
        repo,
        "planning-artifacts/architecture-bmad-infra.md",
        "source_pin: 'BMAD 6.11.0'",
    )

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "pin-missing"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["subject"] == "planning-artifacts/architecture-bmad-infra.md"


# ---------------------------------------------------------- archive hygiene


def test_archive_misplaced_and_stray_file_are_flagged(tmp_path: Path) -> None:
    """A sprint-change-proposal at the planning-artifacts TOP LEVEL (not
    change-history/), a retro at the implementation-artifacts TOP LEVEL (not
    retros/), and a stray .bak file all report HARD/fixable -- verbatim from
    the original. Both misplaced files are simultaneously ``uncovered``
    (``classify()`` has no rule for the WRONG location, only the right one)
    -- a real, deterministic cross-check the original script also exhibits,
    asserted here rather than hidden."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    (factory._plan(repo) / "sprint-change-proposal-x.md").write_text("x\n", encoding="utf-8")
    impl = factory._impl(repo)
    impl.mkdir(parents=True, exist_ok=True)
    (impl / "retro-x.md").write_text("x\n", encoding="utf-8")
    (impl / "scratch.bak").write_text("x\n", encoding="utf-8")

    findings = factory.gather(repo)

    by_check = {(f.check, f.evidence.get("subject")) for f in findings}
    assert ("archive-misplaced", "planning-artifacts/sprint-change-proposal-x.md") in by_check
    assert ("archive-misplaced", "implementation-artifacts/retro-x.md") in by_check
    assert ("stray-file", "implementation-artifacts/scratch.bak") in by_check
    # The cross-check the docstring claims: both misfiled .md files are ALSO
    # `uncovered` (classify() has no rule for the wrong location), while the
    # stray .bak is exempted (STRAY_SUFFIXES). Review pass (Story 6.8) found
    # this claimed but unasserted.
    assert ("uncovered", "planning-artifacts/sprint-change-proposal-x.md") in by_check
    assert ("uncovered", "implementation-artifacts/retro-x.md") in by_check
    assert ("uncovered", "implementation-artifacts/scratch.bak") not in by_check
    for f in findings:
        if f.check in ("archive-misplaced", "stray-file"):
            assert f.status is DoctorStatus.FAIL
            assert f.evidence["fixable"] is True


# --------------------------------------------------------------- spec-status


def test_spec_status_stale_reports_warn_when_a_matching_retro_exists(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _bootstrap(repo)
    impl = factory._impl(repo)
    impl.mkdir(parents=True, exist_ok=True)
    (impl / "spec-foo.md").write_text("---\nstatus: in-progress\n---\nbody\n", encoding="utf-8")
    (impl / "retros").mkdir(parents=True, exist_ok=True)
    (impl / "retros" / "retro-foo-2026-01-01.md").write_text("retro\n", encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "spec-status-stale"
    assert finding.status is DoctorStatus.WARN
    assert "shipped" in finding.message


def test_spec_status_still_in_flight_with_no_retro_is_not_flagged(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _bootstrap(repo)
    impl = factory._impl(repo)
    impl.mkdir(parents=True, exist_ok=True)
    (impl / "spec-foo.md").write_text("---\nstatus: in-progress\n---\nbody\n", encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 1
    assert findings[0].check == "bmad-drift"


# ------------------------------------------------------------- deferred-work


def test_deferred_work_with_no_reconciliation_stamp_reports_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _bootstrap(repo)
    impl = factory._impl(repo)
    impl.mkdir(parents=True, exist_ok=True)
    (impl / "deferred-work.md").write_text("nothing here\n", encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "deferred-stale"
    assert finding.status is DoctorStatus.WARN
    assert "no 'Last reconciled" in finding.message


def test_deferred_work_reconciled_behind_live_reports_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _bootstrap(repo)
    impl = factory._impl(repo)
    impl.mkdir(parents=True, exist_ok=True)
    (impl / "deferred-work.md").write_text("Last reconciled: v0.9.0\n", encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "deferred-stale"
    assert finding.status is DoctorStatus.WARN
    assert "0.9.0" in finding.message


def test_deferred_work_reconciled_at_live_is_clean(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _bootstrap(repo)
    impl = factory._impl(repo)
    impl.mkdir(parents=True, exist_ok=True)
    (impl / "deferred-work.md").write_text("Last reconciled: v1.0.0\n", encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 1
    assert findings[0].check == "bmad-drift"


# ------------------------------------------------------------------ count-stale


def test_count_stale_reports_ok(tmp_path: Path) -> None:
    """INFO -> OK (the module's own severity mapping): non-gating,
    review-only."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    _pinned_md(repo, "planning-artifacts/index.md", "1.0.0", body="the schema v0 is old\n")

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "count-stale"
    assert finding.status is DoctorStatus.OK
    assert "schema" in finding.message


# -------------------------------------------------------------------- stale-rule


def test_stale_rule_content_reports_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _bootstrap(repo)
    _pinned_md(repo, "planning-artifacts/index.md", "1.0.0", body="branch naming: <recipe-name>-<version>\n")

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "stale-rule"
    assert finding.status is DoctorStatus.WARN


# --------------------------------------------------------------- phase-list-stale


def test_phase_list_stale_reports_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _bootstrap(repo)
    _pinned_md(repo, "planning-artifacts/index.md", "1.0.0", body="phases: B/C/D/F/G\n")

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "phase-list-stale"
    assert finding.status is DoctorStatus.WARN
    assert "E" in finding.message


# ------------------------------------------------------------------------ baseline


def test_no_baseline_reports_ok(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _seed_ground_truth(repo)
    _seed_all_tracked(repo)
    _commit_all(repo, "no baseline yet")

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "no-baseline"
    assert finding.status is DoctorStatus.OK


def test_baseline_corrupt_reports_fail(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _seed_ground_truth(repo)
    _seed_all_tracked(repo)
    baseline = factory._proj(repo) / ".sync-baseline.json"
    baseline.parent.mkdir(parents=True, exist_ok=True)
    baseline.write_text("{not json", encoding="utf-8")
    _commit_all(repo, "corrupt baseline")

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "baseline-corrupt"
    assert finding.status is DoctorStatus.FAIL


def test_baseline_corrupt_does_not_blank_an_unrelated_real_finding(tmp_path: Path) -> None:
    """The spec's own malformed-input example: a corrupt baseline must not
    discard another check's real finding produced in the same run."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _seed_ground_truth(repo)
    _seed_all_tracked(repo)
    (factory._proj(repo) / "planning-artifacts" / "index.md").unlink()
    baseline = factory._proj(repo) / ".sync-baseline.json"
    baseline.parent.mkdir(parents=True, exist_ok=True)
    baseline.write_text("{not json", encoding="utf-8")
    _commit_all(repo, "corrupt baseline + missing pin")

    findings = factory.gather(repo)

    checks = {f.check for f in findings}
    assert "baseline-corrupt" in checks
    assert "pin-missing" in checks


def test_surface_changed_reports_warn(tmp_path: Path) -> None:
    """Mutating the live MCP-tool count after the baseline was written (not
    a doc pin, which would also cascade into ``pin-behind`` findings) --
    isolates ``surface-changed`` cleanly."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    server = repo / ".claude" / "tools" / "conda_forge_server.py"
    server.write_text(server.read_text(encoding="utf-8") + "\n@mcp.tool\ndef baz(): ...\n", encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "surface-changed"
    assert finding.status is DoctorStatus.WARN
    assert finding.evidence["subject"] == "mcp_tools"


# ------------------------------------------------------------------------- coverage


def test_spike_report_is_classified_and_not_flagged_uncovered(tmp_path: Path) -> None:
    """The real 2026-08-11 shape (PR #427, Marshal Story 7.6): a design-spike's
    PASS/FAIL report at the project's ``planning-artifacts/`` root must be
    classified rather than falling through to ``UNKNOWN``."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    (factory._plan(repo) / "spike-0-copier-api-fit-report.md").write_text("verdict: PASS\n", encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 1
    assert findings[0].check == "bmad-drift"
    assert findings[0].status is DoctorStatus.OK


def test_rekey_map_is_classified_and_not_flagged_uncovered(tmp_path: Path) -> None:
    """The fold PR's re-key map (Story 25.3, spec-one-chain-per-station CAP-3(g)),
    ``planning-artifacts/rekey-YYYY-MM-DD.md``. Found live 2026-09-16 on the marshal
    pilot (PR #1389): the first map ever written fell through to ``uncovered``
    because 25.3 shipped the readers but no classification rule."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    (factory._plan(repo) / "rekey-2026-09-16.md").write_text(
        "# Re-key map\n\n12-2-old-slug -> 12-2-new-slug\n", encoding="utf-8"
    )

    findings = factory.gather(repo)

    assert len(findings) == 1
    assert findings[0].check == "bmad-drift"
    assert findings[0].status is DoctorStatus.OK
    assert factory.classify(Path("planning-artifacts/rekey-2026-09-16.md"), repo) == "tracked:plan"
    # Undated or mis-dated names are NOT the shape (AGENTS.md § Dates: YYYY-MM-DD only).
    assert factory.classify(Path("planning-artifacts/rekey.md"), repo) != "tracked:plan"


def test_a_second_spike_index_is_also_classified(tmp_path: Path) -> None:
    """Proves the rule generalizes over the spike index and slug -- not
    hard-coded to ``spike-0`` -- so a future ``spike-1``/``spike-2`` report
    following the same convention stays covered."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    (factory._plan(repo) / "spike-2-some-other-thing-report.md").write_text("verdict: FAIL\n", encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 1
    assert findings[0].check == "bmad-drift"
    assert findings[0].status is DoctorStatus.OK


def test_spike_report_look_alike_without_a_numeric_index_still_hard_fails(tmp_path: Path) -> None:
    """The fail-closed default must survive: a look-alike outside the agreed
    pattern (missing the numeric spike index) is still a hole, not a pass."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    (factory._plan(repo) / "spike-copier-api-fit-report.md").write_text("verdict: PASS\n", encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "uncovered"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["subject"] == "planning-artifacts/spike-copier-api-fit-report.md"


def test_tea_test_design_artifacts_are_classified_and_not_flagged_uncovered(
    tmp_path: Path,
) -> None:
    """The real 2026-09-07 shape (Story 31.1): TEA's `bmad-testarch-test-design`
    output -- `test-design-architecture.md`, `test-design-qa.md`,
    `test-design/<slug>-handoff.md`, `test-design-progress-system.md` -- plus a
    top-level equivalence report under `planning-artifacts/reviews/`, kept as
    additive artifacts alongside `test-architecture.md`. Must be classified
    rather than falling through to `UNKNOWN`."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    plan = factory._plan(repo)
    (plan / "test-design-architecture.md").write_text("x\n", encoding="utf-8")
    (plan / "test-design-qa.md").write_text("x\n", encoding="utf-8")
    (plan / "test-design-progress-system.md").write_text("x\n", encoding="utf-8")
    (plan / "test-design").mkdir(parents=True, exist_ok=True)
    (plan / "test-design" / "pyforge-marshal-handoff.md").write_text("x\n", encoding="utf-8")
    (plan / "reviews").mkdir(parents=True, exist_ok=True)
    (plan / "reviews" / "tea-equivalence-2026-09-07.md").write_text("x\n", encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 1
    assert findings[0].check == "bmad-drift"
    assert findings[0].status is DoctorStatus.OK


def test_fleet_drain_run_records_are_classified_and_not_flagged_uncovered(
    tmp_path: Path,
) -> None:
    """The real 2026-08-29/30 shape: `marshal factory drain` campaign records
    (`fleet-drain-supervisor.log`, `journal.jsonl`) under a third `*-runs/`
    directory name the `runs/`/`dispatch-runs/` rules don't match -- must be
    classified rather than falling through to `UNKNOWN`."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    run_dir = factory._impl(repo) / "fleet-drain-runs" / "pyforge-marshal-20260830T010055392Z-4088e463"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "fleet-drain-supervisor.log").write_text("x\n", encoding="utf-8")
    (run_dir / "journal.jsonl").write_text("{}\n", encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 1
    assert findings[0].check == "bmad-drift"
    assert findings[0].status is DoctorStatus.OK


def test_worktree_sweep_verdicts_are_classified_and_not_flagged_uncovered(
    tmp_path: Path,
) -> None:
    """The real 2026-09-05 shape: the dated per-worktree verdict table that
    `scripts/worktree_sweep.py --format json` emits, saved by the operator at
    marshal's implementation-artifacts root (`worktree-verdicts-<date>.json`)
    -- must be classified rather than falling through to `UNKNOWN`."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    impl = factory._impl(repo)
    impl.mkdir(parents=True, exist_ok=True)
    (impl / "worktree-verdicts-2026-09-05.json").write_text(
        '{"generated": "2026-09-05", "items": []}\n', encoding="utf-8"
    )

    findings = factory.gather(repo)

    assert len(findings) == 1
    assert findings[0].check == "bmad-drift"
    assert findings[0].status is DoctorStatus.OK


def test_flat_spec_with_underscore_in_slug_is_classified_and_not_flagged_uncovered(
    tmp_path: Path,
) -> None:
    """The real 2026-09-12 shape (mason 15.1 recovery pass): a flat spec's slug
    can carry an underscore verbatim when it names a real code symbol
    (`...-dispatch-max_parallel-key.md`) -- the hyphen-only character class
    rejected it and tripped `uncovered`."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    specs = factory._plan(repo) / "specs"
    specs.mkdir(parents=True, exist_ok=True)
    (specs / "spec-33-8-the-first-live-fan-out-wave-on-a-real-dispatch-max_parallel-key.md").write_text(
        "x\n", encoding="utf-8"
    )

    findings = factory.gather(repo)

    assert len(findings) == 1
    assert findings[0].check == "bmad-drift"
    assert findings[0].status is DoctorStatus.OK


def test_flat_spec_memlog_sibling_is_classified_and_not_flagged_uncovered(
    tmp_path: Path,
) -> None:
    """The real 2026-09-12 shape (Story 33.3): a flat spec's OWN `.memlog.md`
    sibling filed beside it (`spec-33-3-....md` + `spec-33-3-....memlog.md`)
    rather than inside a `spec-<name>/` folder -- must be classified rather
    than falling through to `UNKNOWN`."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    specs = factory._plan(repo) / "specs"
    specs.mkdir(parents=True, exist_ok=True)
    (specs / "spec-33-3-the-layers-are-enabled-on-factory-spin.memlog.md").write_text("x\n", encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 1
    assert findings[0].check == "bmad-drift"
    assert findings[0].status is DoctorStatus.OK


def test_benchmark_artifact_is_classified_and_not_flagged_uncovered(
    tmp_path: Path,
) -> None:
    """The real 2026-09-12 shape (Story 28.31): a measured comparison record
    committed at `planning-artifacts/benchmarks/<slug>.json`, a sibling
    convention to `reviews/` for one-off benchmark results -- must be
    classified rather than falling through to `UNKNOWN`."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    benchmarks = factory._plan(repo) / "benchmarks"
    benchmarks.mkdir(parents=True, exist_ok=True)
    (benchmarks / "structure-graph-dispatch-28-31.json").write_text('{"story": "28.31"}\n', encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 1
    assert findings[0].check == "bmad-drift"
    assert findings[0].status is DoctorStatus.OK


def test_uncovered_file_reports_fail(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _bootstrap(repo)
    (factory._proj(repo) / "randomfile.txt").write_text("x\n", encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "uncovered"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["subject"] == "randomfile.txt"


# -------------------------------------------------------------------- tier alignment


def test_git_tracked_impl_artifact_is_flagged(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _bootstrap(repo)
    impl = factory._impl(repo)
    impl.mkdir(parents=True, exist_ok=True)
    # Spec-shaped name: matches classify()'s own `tracked:spec` rule, so this
    # test isolates tier-alignment's own finding without also tripping
    # check_coverage's `uncovered`.
    (impl / "spec-tracked-test.md").write_text("body\n", encoding="utf-8")
    _commit_all(repo, "accidentally track a Tier-3 spec")

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "tracked-impl-artifact"
    assert finding.status is DoctorStatus.FAIL
    assert "git mv to docs/specs" in finding.message


def test_docs_specs_nonmd_reports_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _bootstrap(repo)
    docs_specs = repo / "docs" / "specs"
    docs_specs.mkdir(parents=True, exist_ok=True)
    (docs_specs / "foo.txt").write_text("x\n", encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "docs-specs-nonmd"
    assert finding.status is DoctorStatus.WARN


def test_tier_alignment_degrades_to_warn_when_git_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The spec's own row: git unavailable / target not a repository --
    ``check_tier_alignment`` names the cause instead of silently reporting a
    confident-clean "nothing tracked". An unrelated real finding
    (pin-missing) and an unrelated clean-OK finding (no-baseline) both
    survive alongside it -- proving the degradation is isolated to the one
    check that actually needs git."""
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    _seed_ground_truth(repo)
    _seed_all_tracked(repo)
    (factory._proj(repo) / "planning-artifacts" / "index.md").unlink()
    # Deliberately never `git init` here -- but "not a repository" is only
    # true if git's upward discovery also stops. The autouse fixture SCRUBS
    # GIT_CEILING_DIRECTORIES, so a contributor whose TMPDIR sits inside a
    # checkout would have git find that outer repo, exit 0, and fail this
    # test with a bare KeyError instead of a diagnosable assertion -- leaving
    # the degradation path it is the only test for unverified. Pin the
    # ceiling to tmp_path (resolved: git ignores symlinked ceiling entries).
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.resolve()))

    findings = factory.gather(repo)

    by_check = {f.check: f for f in findings}
    assert by_check["pin-missing"].status is DoctorStatus.FAIL
    assert by_check["no-baseline"].status is DoctorStatus.OK
    unevaluable = by_check["bmad-drift-unevaluable"]
    assert unevaluable.status is DoctorStatus.WARN
    assert "check_tier_alignment" in unevaluable.message
    assert unevaluable.evidence == {"check": "check_tier_alignment", "target": str(repo)}


# --------------------------------------------------------------------- spec index


def test_spec_unindexed_reports_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _bootstrap(repo)
    docs_specs = repo / "docs" / "specs"
    docs_specs.mkdir(parents=True, exist_ok=True)
    (docs_specs / "bar.md").write_text("x\n", encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "spec-unindexed"
    assert finding.status is DoctorStatus.WARN
    assert finding.evidence["subject"] == "docs/specs/bar.md"


def test_spec_indexed_in_claude_md_is_not_flagged(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _bootstrap(repo)
    docs_specs = repo / "docs" / "specs"
    docs_specs.mkdir(parents=True, exist_ok=True)
    (docs_specs / "bar.md").write_text("x\n", encoding="utf-8")
    (repo / "CLAUDE.md").write_text("See docs/specs/bar.md for details.\n", encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 1
    assert findings[0].check == "bmad-drift"


# ------------------------------------------------------------------- Dream vocab


def test_dream_vocab_invalid_status_and_type_report_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _bootstrap(repo)
    dreams = repo / "docs" / "dreams"
    dreams.mkdir(parents=True, exist_ok=True)
    (dreams / "foo.md").write_text("---\nstatus: bogus\ntype: bogus\nowner: marshal\n---\n", encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 2
    assert all(f.check == "dream-vocab" and f.status is DoctorStatus.WARN for f in findings)
    messages = " ".join(f.message for f in findings)
    assert "status" in messages and "type" in messages


def test_dream_status_with_a_trailing_yaml_comment_is_read_not_reported_missing(tmp_path: Path) -> None:
    """26 live Dreams write `status: realized   # absorbed into X on <date>` -- a
    trailing comment is ordinary YAML and must neither read as "no status:" nor
    hide an off-vocabulary value behind it (2026-09-05)."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    dreams = repo / "docs" / "dreams"
    dreams.mkdir(parents=True, exist_ok=True)
    (dreams / "ok.md").write_text(
        "---\nstatus: realized   # 2026-08-22 absorbed into foo\ntype: dream   # note\nowner: marshal\n---\n",
        encoding="utf-8",
    )
    (dreams / "bad.md").write_text(
        "---\nstatus: bogus   # a comment must not launder the value\ntype: dream\nowner: marshal\n---\n",
        encoding="utf-8",
    )

    findings = [f for f in factory.gather(repo) if f.check == "dream-vocab"]

    assert [f.evidence["subject"] for f in findings] == ["docs/dreams/bad.md"]
    assert "bogus" in findings[0].message


def test_dream_with_no_status_reports_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _bootstrap(repo)
    dreams = repo / "docs" / "dreams"
    dreams.mkdir(parents=True, exist_ok=True)
    (dreams / "foo.md").write_text("---\nowner: marshal\n---\n", encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "dream-vocab"
    assert "no status:" in finding.message


def test_dream_readme_is_never_evaluated(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _bootstrap(repo)
    dreams = repo / "docs" / "dreams"
    dreams.mkdir(parents=True, exist_ok=True)
    (dreams / "README.md").write_text("not a dream\n", encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 1
    assert findings[0].check == "bmad-drift"


# ------------------------------------------------------------------ Dream owners


def test_dream_with_no_owner_reports_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _bootstrap(repo)
    dreams = repo / "docs" / "dreams"
    dreams.mkdir(parents=True, exist_ok=True)
    (dreams / "foo.md").write_text("---\nstatus: dreamt\n---\n", encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "dream-unowned"
    assert "no owner:" in finding.message


def test_dream_owned_by_guild_but_not_a_reserved_dream_reports_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _bootstrap(repo)
    dreams = repo / "docs" / "dreams"
    dreams.mkdir(parents=True, exist_ok=True)
    (dreams / "foo.md").write_text("---\nstatus: dreamt\nowner: guild\n---\n", encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "dream-unowned"
    assert "reserved" in finding.message


def test_dream_owned_by_an_unknown_station_reports_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _bootstrap(repo)
    dreams = repo / "docs" / "dreams"
    dreams.mkdir(parents=True, exist_ok=True)
    (dreams / "foo.md").write_text("---\nstatus: dreamt\nowner: nonexistent\n---\n", encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "dream-unowned"
    assert "eight Smiths" in finding.message


def test_dream_owned_by_a_known_station_is_clean(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _bootstrap(repo)
    dreams = repo / "docs" / "dreams"
    dreams.mkdir(parents=True, exist_ok=True)
    (dreams / "foo.md").write_text("---\nstatus: dreamt\nowner: marshal\n---\n", encoding="utf-8")

    findings = factory.gather(repo)

    assert len(findings) == 1
    assert findings[0].check == "bmad-drift"


def test_a_malformed_roster_degrades_only_the_two_checks_that_read_it(tmp_path: Path) -> None:
    """The spec's own malformed-input row: a broken
    ``docs/governance/guild-roster.json`` must degrade ONLY
    ``check_dream_vocab``/``check_dream_owners`` -- an unrelated real
    finding (pin-missing) must survive in the same run."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    dreams = repo / "docs" / "dreams"
    dreams.mkdir(parents=True, exist_ok=True)
    (dreams / "foo.md").write_text("---\nstatus: dreamt\nowner: marshal\n---\n", encoding="utf-8")
    (repo / "docs" / "governance" / "guild-roster.json").write_text("{not json", encoding="utf-8")
    (factory._proj(repo) / "planning-artifacts" / "index.md").unlink()

    findings = factory.gather(repo)

    checks = [f.check for f in findings]
    assert checks.count("bmad-drift-unevaluable") == 2
    assert "pin-missing" in checks
    unevaluable_names = {f.evidence["check"] for f in findings if f.check == "bmad-drift-unevaluable"}
    assert unevaluable_names == {"check_dream_vocab", "check_dream_owners"}


# --------------------------------------------------------------- project dir absent


def test_project_dir_absent_reports_warn_not_a_confident_ok(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.BMAD_DRIFT
    assert finding.check == "bmad-drift-unevaluable"
    assert finding.status is DoctorStatus.WARN
    assert "pyforge-marshal" in finding.message


# -------------------------------------------------------- per-check isolation (mutation)


def test_one_check_raising_does_not_discard_the_others_real_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The story's own core acceptance criterion: one ported check's
    exception degrades to exactly one named ``bmad-drift-unevaluable`` WARN,
    while every OTHER check's real finding in the same run survives.
    ``check_pins`` is monkeypatched to raise; ``check_pins`` itself would
    otherwise have reported nothing (the fixture's pins are all clean), so a
    second mutation (a missing pin would BE what check_pins reports, which
    is exactly what's being suppressed) is intentionally avoided -- instead
    an unrelated check (dream ownership) is given a real finding to prove
    survival."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    dreams = repo / "docs" / "dreams"
    dreams.mkdir(parents=True, exist_ok=True)
    (dreams / "foo.md").write_text("---\nstatus: dreamt\n---\n", encoding="utf-8")

    def _boom(_target: Path) -> list:
        raise RuntimeError("simulated check_pins failure")

    monkeypatch.setattr(factory, "check_pins", _boom)

    findings = factory.gather(repo)

    checks = {f.check for f in findings}
    assert "dream-unowned" in checks
    unevaluable = [f for f in findings if f.check == "bmad-drift-unevaluable"]
    assert len(unevaluable) == 1
    assert unevaluable[0].status is DoctorStatus.WARN
    assert unevaluable[0].evidence == {"check": "check_pins", "target": str(repo)}
    assert "check_pins" in unevaluable[0].message
    assert "RuntimeError" in unevaluable[0].message
    assert "simulated check_pins failure" in unevaluable[0].message


def test_gather_wraps_an_unanticipated_gather_level_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The outer ``degrade_on_exception`` net: an exception _gather itself
    cannot anticipate (here, simulated by making ``_proj`` explode) still
    degrades to one WARN rather than propagating."""
    repo = tmp_path / "repo"
    _bootstrap(repo)

    def _boom(_target: Path) -> Path:
        raise RuntimeError("simulated catastrophic failure")

    monkeypatch.setattr(factory, "_proj", _boom)

    findings = factory.gather(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.BMAD_DRIFT
    assert finding.check == "bmad-drift"
    assert finding.status is DoctorStatus.WARN
    assert "RuntimeError" in finding.message


# ------------------------------------------- cannot-evaluate, not clean (6.8 follow-up)
#
# Every test below reproduces a case the FIRST review pass left open and the
# follow-up pass closed. Before the fix each one produced NO finding at all --
# a confident clean bill of health for a question that could not be asked --
# which is the exact defect class this module's per-check isolation exists to
# turn into an honest WARN. They are the first permission-based tests in this
# file; `test_sources_chain_*.py` carry the equivalents for their own modules.


def _unevaluable_checks(findings: tuple) -> set[str]:
    return {f.evidence["check"] for f in findings if f.check == "bmad-drift-unevaluable"}


def test_baseline_valid_json_of_the_wrong_shape_reports_fail(tmp_path: Path) -> None:
    """The ``isinstance(base, dict)`` guard. Both pre-existing
    baseline-corrupt tests write ``"{not json"``, which takes the
    ``ValueError`` path -- so this branch, added by the first review pass,
    shipped with no coverage at all. A JSON array parses fine and then
    ``AttributeError``s on ``.get()``."""
    for index, payload in enumerate(("[]", "42", '"oops"')):
        repo = tmp_path / f"repo-{index}"
        _init_repo(repo)
        _seed_ground_truth(repo)
        _seed_all_tracked(repo)
        baseline = factory._proj(repo) / ".sync-baseline.json"
        baseline.write_text(payload, encoding="utf-8")

        findings = factory.gather(repo)

        finding = _only(findings, "baseline-corrupt")
        assert finding.status is DoctorStatus.FAIL
        assert finding.message == "baseline JSON is not an object"
        assert not _unevaluable_checks(findings), (
            f"{payload} degraded to the coarse per-check net instead of the "
            f"precise baseline-corrupt finding: {findings}"
        )


@_needs_unprivileged
def test_unreadable_nested_dir_warns_instead_of_reporting_full_coverage(
    tmp_path: Path,
) -> None:
    """``Path.rglob`` swallows ``OSError`` mid-walk and yields nothing, so an
    unreadable subdirectory read as "no files here" -- and no files reads as
    fully covered. Reproduced before the fix: one ``chmod 000`` on a nested
    ``planning-artifacts/specs/`` erased a real ``uncovered`` HARD finding
    AND a real ``stale-rule`` WARN with no WARN of any kind in their place."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    nested = factory._proj(repo) / "planning-artifacts" / "specs"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "junkfile.txt").write_text("unclassifiable\n", encoding="utf-8")
    (nested / "note.md").write_text("use <recipe-name>-<version>\n", encoding="utf-8")

    before = factory.gather(repo)
    assert {"uncovered", "stale-rule"} <= {f.check for f in before}

    nested.chmod(0o000)
    try:
        after = factory.gather(repo)
    finally:
        nested.chmod(0o755)

    assert not any(f.status is DoctorStatus.OK and f.check == "bmad-drift" for f in after), (
        f"an unreadable nested dir was reported as a clean project: {after}"
    )
    assert {"check_coverage", "check_stale_rules"} <= _unevaluable_checks(after)
    assert all("PermissionError" in f.message for f in after if f.check == "bmad-drift-unevaluable")


@_needs_unprivileged
def test_unreadable_implementation_artifacts_warns_for_deferred_work(
    tmp_path: Path,
) -> None:
    """``check_deferred_work``/``check_baseline`` gated on the bare
    ``Path.is_file()``, which answers ``False`` for an unreadable ANCESTOR.
    Before the fix an unreadable ``implementation-artifacts/`` made three
    sibling checks WARN while this one silently reported clean -- an operator
    saw "3 checks unevaluable" and had no way to learn there was a fourth."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    impl = factory._impl(repo)
    impl.mkdir(parents=True, exist_ok=True)
    (impl / "deferred-work.md").write_text("Last reconciled: v0.9.0\n", encoding="utf-8")

    assert _only(factory.gather(repo), "deferred-stale").status is DoctorStatus.WARN

    impl.chmod(0o000)
    try:
        after = factory.gather(repo)
    finally:
        impl.chmod(0o755)

    assert "check_deferred_work" in _unevaluable_checks(after)


@_needs_unprivileged
def test_unreadable_dreams_dir_warns_instead_of_reporting_no_dream_drift(
    tmp_path: Path,
) -> None:
    """The same swallow one directory over: ``docs/dreams/`` statable but
    unreadable made both Dream checks report clean."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    dreams = repo / "docs" / "dreams"
    dreams.mkdir(parents=True, exist_ok=True)
    (dreams / "orphan.md").write_text("---\nstatus: bogus\n---\n", encoding="utf-8")

    assert "dream-vocab" in {f.check for f in factory.gather(repo)}

    dreams.chmod(0o000)
    try:
        after = factory.gather(repo)
    finally:
        dreams.chmod(0o755)

    assert {"check_dream_vocab", "check_dream_owners"} <= _unevaluable_checks(after)


def test_non_utf8_byte_does_not_discard_a_sibling_docs_real_finding(
    tmp_path: Path,
) -> None:
    """``_read`` caught ``OSError`` only, so one stray latin-1 byte raised
    ``UnicodeDecodeError`` out of the whole check -- taking a DIFFERENT,
    perfectly readable file's real ``stale-rule`` finding with it."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    plan = factory._proj(repo) / "planning-artifacts"
    (plan / "readable.md").write_text("use <recipe-name>-<version>\n", encoding="utf-8")
    (plan / "mojibake.md").write_bytes(b"caf\xe9 uses <recipe-name>-<version>\n")

    findings = factory.gather(repo)

    stale = [f for f in findings if f.check == "stale-rule"]
    assert {f.evidence["subject"] for f in stale} == {
        "planning-artifacts/readable.md",
        "planning-artifacts/mojibake.md",
    }, f"a non-UTF-8 byte discarded a sibling doc's finding: {findings}"
    assert not _unevaluable_checks(findings)


def test_unknown_live_version_warns_but_keeps_the_pin_missing_half(
    tmp_path: Path,
) -> None:
    """An unreadable ``SKILL.md`` ``version:`` makes the behind-ness half
    unanswerable — an honest WARN — while ``pin-missing`` (which never needed
    the live version) still runs, mirroring ``check_tier_alignment``'s own
    git-unavailable shape."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _seed_ground_truth(repo)
    _seed_all_tracked(repo, version="0.1.0")
    (factory._proj(repo) / "planning-artifacts" / "index.md").write_text(
        "no pin at all\n",
        encoding="utf-8",
    )
    _commit_all(repo, "seed behind-pinned project")

    before = {f.check for f in factory.gather(repo)}
    assert "pin-missing" in before

    skill_md = repo / ".claude" / "skills" / "conda-forge-expert" / "SKILL.md"
    skill_md.write_text("### G1\nno frontmatter version\n", encoding="utf-8")
    after = factory.gather(repo)

    assert not any(f.check == "pin-behind" for f in after)
    assert _only(after, "pin-missing").status is DoctorStatus.FAIL
    assert "check_pins" in _unevaluable_checks(after)


def test_unreadable_phase_registry_warns_instead_of_fabricating_phase_n(
    tmp_path: Path,
) -> None:
    """``_max_single_phase`` fell back to a hardcoded ``"N"``, manufacturing
    a specific, actionable-looking ``omits phases through N`` claim out of
    ground truth that was never read. It now raises -- but LAZILY, so a repo
    with no phase list anywhere stays quiet rather than WARNing about a
    registry it never needed."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    atlas = repo / ".claude" / "skills" / "conda-forge-expert" / "scripts" / "conda_forge_atlas.py"

    # No judgeable phase list anywhere: silence, not a WARN.
    atlas.unlink()
    assert "check_phase_lists" not in _unevaluable_checks(factory.gather(repo))

    # Now give it something to judge -- with the registry still unreadable.
    (factory._proj(repo) / "planning-artifacts" / "index.md").write_text(
        "---\nsource_pin: conda-forge-expert v1.0.0\n---\npipeline: B/C/D/E/F\n",
        encoding="utf-8",
    )
    after = factory.gather(repo)

    assert not any(f.check == "phase-list-stale" for f in after), (
        f"fabricated a phase verdict from an unreadable registry: {after}"
    )
    assert "check_phase_lists" in _unevaluable_checks(after)


def test_every_unevaluable_finding_carries_the_same_evidence_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``bmad-drift-unevaluable`` is produced by two sites -- a per-check
    failure (``_unevaluable``) and ``_gather``'s own missing-project guard. A
    consumer grouping by ``evidence["check"]`` must not KeyError depending on
    which fired; the rule ``sources/ledger.py`` states explicitly for its own
    pair.

    The second follow-up review pass found this test reaching the guard
    TWICE -- ``repo / "nowhere"`` has no ``pyforge-marshal`` project either,
    so ``_unevaluable``, whose ``evidence["check"]`` is a FUNCTION name
    rather than the literal ``"bmad-drift"``, was never actually exercised by
    the one test that names it. The per-check operand now forces a real check
    to raise inside a real project, which is what makes the two shapes
    genuinely comparable."""
    repo = tmp_path / "repo"
    _bootstrap(repo)

    def _boom(target: Path) -> list:
        raise OSError("simulated per-check failure")

    monkeypatch.setattr(factory, "check_pins", _boom)

    absent = factory.gather(tmp_path / "not-a-bmad-repo")
    per_check = factory.gather(repo)

    # Both producers really fired -- otherwise the key assertion below is
    # vacuous for whichever one was missed.
    assert [f.check for f in absent] == ["bmad-drift-unevaluable"]
    assert {f.evidence["check"] for f in absent} == {"bmad-drift"}
    assert _unevaluable_checks(per_check) == {"check_pins"}

    for findings in (absent, per_check):
        for f in findings:
            if f.check != "bmad-drift-unevaluable":
                continue
            assert sorted(f.evidence) == ["check", "target"], f.evidence


@_needs_unprivileged
def test_unreadable_doc_neither_hides_a_finding_nor_fabricates_pin_missing(
    tmp_path: Path,
) -> None:
    """``_read`` caught every ``OSError`` and answered ``""``, so an
    unreadable FILE was indistinguishable from an absent one -- the last
    member of the cannot-evaluate family two prior passes left open, and the
    only one that fails in BOTH directions.

    Hiding: an unreadable ``.md`` loses its own ``stale-rule`` WARN and the
    run reports a confident aggregate OK. Fabricating: ``_doc_pin`` reads
    ``""`` as "this doc states no pin", so an unreadable tracked doc is
    reported as a ``pin-missing`` HARD FAIL -- a specific, actionable-looking
    accusation against a doc whose pin is perfectly intact."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    plan = factory._proj(repo) / "planning-artifacts"
    stale = plan / "note.md"
    stale.write_text("use <recipe-name>-<version>\n", encoding="utf-8")

    assert "stale-rule" in {f.check for f in factory.gather(repo)}

    stale.chmod(0o000)
    (plan / "index.md").chmod(0o000)
    try:
        after = factory.gather(repo)
    finally:
        stale.chmod(0o644)
        (plan / "index.md").chmod(0o644)

    assert not any(f.status is DoctorStatus.OK and f.check == "bmad-drift" for f in after), (
        f"an unreadable doc was reported as a clean project: {after}"
    )
    assert not any(f.check == "pin-missing" for f in after), (
        f"an unreadable doc was slandered as missing its pin: {after}"
    )
    assert {"check_pins", "check_stale_rules"} <= _unevaluable_checks(after)


def test_read_still_answers_empty_for_a_directory_named_like_a_doc(
    tmp_path: Path,
) -> None:
    """``check_stale_rules`` selects by SUFFIX alone, so it reaches a
    directory named ``*.md``. The origin read that as empty
    (``IsADirectoryError`` is an ``OSError``); narrowing ``_read`` must not
    turn a filing oddity into a cannot-evaluate WARN."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    (factory._proj(repo) / "planning-artifacts" / "notes.md").mkdir()

    findings = factory.gather(repo)

    assert not _unevaluable_checks(findings), findings
    assert {f.check for f in findings} == {"bmad-drift"}


@_needs_unprivileged
def test_unreadable_planning_tree_keeps_the_readable_trees_hard_findings(
    tmp_path: Path,
) -> None:
    """``check_archive_hygiene`` scans two INDEPENDENT trees, and scanned
    both in one try-scope -- so an unreadable ``planning-artifacts/`` took
    ``implementation-artifacts/``'s real HARD findings down with it, even
    though that tree was never visited. ``check_pins`` and
    ``check_tier_alignment`` already split their own independent halves."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    impl = factory._impl(repo)
    impl.mkdir(parents=True, exist_ok=True)
    (impl / "retro-thing.md").write_text("retro\n", encoding="utf-8")
    (impl / "junk.patch").write_text("diff\n", encoding="utf-8")

    before = {f.check for f in factory.gather(repo)}
    assert {"archive-misplaced", "stray-file"} <= before

    plan = factory._proj(repo) / "planning-artifacts"
    plan.chmod(0o000)
    try:
        after = factory.gather(repo)
    finally:
        plan.chmod(0o755)

    assert "check_archive_hygiene" in _unevaluable_checks(after)
    hygiene = {(f.check, f.evidence["subject"]) for f in after if f.check in {"archive-misplaced", "stray-file"}}
    assert hygiene == {
        ("archive-misplaced", "implementation-artifacts/retro-thing.md"),
        ("stray-file", "implementation-artifacts/junk.patch"),
    }, f"an unreadable planning tree discarded the readable tree's findings: {after}"


def test_finding_order_is_stable_across_readdir_order(tmp_path: Path) -> None:
    """Raw ``glob``/``rglob`` yields ``readdir`` order, so the same repo state
    produced a different finding ORDER on different clones -- defeating any
    diff- or snapshot-based consumer of ``doctor report``. Every collection
    site now lists through ``_listdir``, which sorts."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    plan = factory._proj(repo) / "planning-artifacts"
    for name in ("z-note.md", "a-note.md", "m-note.md"):
        (plan / name).write_text("use <recipe-name>-<version>\n", encoding="utf-8")

    subjects = [f.evidence["subject"] for f in factory.gather(repo) if f.check == "stale-rule"]

    assert subjects == sorted(subjects)
    assert len(subjects) == 3


@_needs_unprivileged
def test_unreadable_unrelated_ground_truth_leaves_check_pins_untouched(
    tmp_path: Path,
) -> None:
    """``_live_version`` resolved the live skill version through
    ``_ground_truth``, which eagerly reads all SIX surface facts -- so every
    pin comparison was coupled to five files it does not need. Once ``_read``
    was narrowed to raise (prior pass), that coupling became a live
    regression: ``chmod 000`` on ``pixi.toml``, read only by ``_env_count``,
    raised ``PermissionError`` past ``check_pins``' ``except ValueError`` and
    erased a real ``pin-missing`` HARD finding -- the exact outcome
    ``check_pins``' own docstring promises cannot happen.

    ``pixi.toml`` is genuinely nothing to do with pins, so the fix is not
    merely that the finding survives: ``check_pins`` must not degrade at
    all."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    # A real, unambiguous pin-missing HARD finding to protect.
    (factory._proj(repo) / "planning-artifacts" / "PRD.md").write_text(
        "# PRD\nno frontmatter pin here\n", encoding="utf-8"
    )
    assert "pin-missing" in {f.check for f in factory.gather(repo)}

    (repo / "pixi.toml").chmod(0o000)
    try:
        after = factory.gather(repo)
    finally:
        (repo / "pixi.toml").chmod(0o644)

    assert "pin-missing" in {f.check for f in after}, (
        f"an unreadable pixi.toml erased a real pin-missing finding: {after}"
    )
    assert "check_pins" not in _unevaluable_checks(after), f"check_pins degraded over a file it never needed: {after}"


@_needs_unprivileged
def test_unreadable_skill_md_degrades_only_the_behind_half_of_check_pins(
    tmp_path: Path,
) -> None:
    """The companion to the test above, for the file ``_live_version``
    genuinely DOES need. ``_read`` raises ``PermissionError`` on an
    unreadable ``SKILL.md``, and ``check_pins``' ``except ValueError``
    caught only the absent case -- so the readable-but-denied case took the
    whole check with it, ``pin-missing`` included.

    Only the behind-ness comparison is unanswerable here; a doc with no pin
    at all is still definitively broken, so that half must still report."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    (factory._proj(repo) / "planning-artifacts" / "PRD.md").write_text(
        "# PRD\nno frontmatter pin here\n", encoding="utf-8"
    )
    skill_md = repo / ".claude" / "skills" / "conda-forge-expert" / "SKILL.md"

    skill_md.chmod(0o000)
    try:
        after = factory.gather(repo)
    finally:
        skill_md.chmod(0o644)

    assert "pin-missing" in {f.check for f in after}, f"an unreadable SKILL.md discarded a real HARD finding: {after}"
    assert "check_pins" in _unevaluable_checks(after), f"the unanswerable behind-ness half went silently clean: {after}"


@_needs_unprivileged
def test_unreadable_baseline_is_not_reported_as_corrupt(tmp_path: Path) -> None:
    """``check_baseline`` wrapped ``json.loads(_read(...))`` in ``except
    (ValueError, OSError)``, inherited from the origin -- and ``_read`` now
    raises ``PermissionError`` (an ``OSError``) for a file that exists but
    cannot be read. So a byte-for-byte VALID baseline was reported as a
    ``baseline-corrupt`` HARD finding: "cannot parse baseline JSON" about a
    file that was never parsed.

    "I could not read it" is not "it is corrupt". Genuine corruption is
    still a HARD finding (``test_baseline_corrupt_reports_fail``)."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    baseline = factory._proj(repo) / ".sync-baseline.json"
    assert json.loads(baseline.read_text(encoding="utf-8"))  # intact before the chmod

    baseline.chmod(0o000)
    try:
        after = factory.gather(repo)
    finally:
        baseline.chmod(0o644)

    assert not any(f.check == "baseline-corrupt" for f in after), (
        f"an intact baseline was accused of being corrupt: {after}"
    )
    assert "check_baseline" in _unevaluable_checks(after), f"an unreadable baseline went silently clean: {after}"


@_needs_unprivileged
def test_one_unreadable_doc_keeps_its_readable_siblings_findings(
    tmp_path: Path,
) -> None:
    """``_read`` raises so "cannot evaluate" is never "clean", but
    ``_gather``'s isolation boundary is the CHECK -- so inside a loop that
    raise discarded every readable SIBLING's real finding too.

    Reproduced: three docs each carrying the stale branch-naming rule
    produce three ``stale-rule`` findings; ``chmod 000`` on the middle one
    produced ZERO, and one WARN in their place. The WARN must name the file
    it lost, not just the check."""
    repo = tmp_path / "repo"
    _bootstrap(repo)
    plan = factory._proj(repo) / "planning-artifacts"
    for name in ("a-note.md", "b-note.md", "c-note.md"):
        (plan / name).write_text("use <recipe-name>-<version>\n", encoding="utf-8")

    assert len([f for f in factory.gather(repo) if f.check == "stale-rule"]) == 3

    (plan / "b-note.md").chmod(0o000)
    try:
        after = factory.gather(repo)
    finally:
        (plan / "b-note.md").chmod(0o644)

    survivors = {f.evidence["subject"] for f in after if f.check == "stale-rule"}
    assert survivors == {
        "planning-artifacts/a-note.md",
        "planning-artifacts/c-note.md",
    }, f"one unreadable doc discarded its readable siblings' findings: {after}"

    lost = [f for f in after if f.check == "bmad-drift-unevaluable" and f.evidence["check"] == "check_stale_rules"]
    assert len(lost) == 1, after
    assert "b-note.md" in lost[0].message, f"the WARN does not name the file it lost: {lost[0].message}"
