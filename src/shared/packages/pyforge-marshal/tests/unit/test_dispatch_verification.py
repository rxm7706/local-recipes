"""Unit tests for dispatch independent verification (Story 22.3, CAP-3).

Story 116.2 (spec-pyforge-marshal:CAP-305): the tests that hand this checkout's root to the verification moved
to ``test_dispatch_verification_live_tree.py``; every test here builds its own tree under ``tmp_path``.
"""

from __future__ import annotations

from pathlib import Path

from pyforge.core.process import ProcessResult

from pyforge.marshal.core import gate
from pyforge.marshal.core.dispatch_retry import (
    DispatchBlockKind,
    classify_dispatch_block,
)
from pyforge.marshal.core.dispatch_verification import (
    COMMIT_ATTRIBUTION_GATE_CODE,
    PRE_EXISTING_GATE_CODE,
    DispatchVerificationInput,
    DispatchVerificationVerdict,
    extract_failure_paths_from_verify_output,
    findings_for_commit_attribution_violations,
    gate_verdict_is_clean,
    judge_dispatch_verification,
    path_in_story_blast_radius,
    primary_gate_failure,
    reclassify_pre_existing_gate_findings,
    would_land_on_self_report_only,
)
from pyforge.marshal.core.egress import Redacted
from pyforge.marshal.core.model import Finding, Severity
from pyforge.marshal.core.status import FleetHomeFacts, build_fleet_row
from pyforge.marshal.dispatch_verify import (
    PRE_VERIFICATION_DEFERRED_WORK_INTAKE_CODE,
    compose_dispatch_policy,
    coverage_gate_commands_for_changed_files,
    cross_station_meta_test_commands_for_changed_files,
    run_pre_verification_deferred_work_intake,
)

# Story 116.2 (spec-pyforge-marshal:CAP-305): a path literal that names a tracked file is joined from its
# segments, so steward's trigger-map derivation does not read it as a file this suite opens -- each is a
# fixture path or a value the code under test names, never a read of the tracked tree.


def _fake_git_log_empty(tokens: list[str]) -> ProcessResult | None:
    """Story 83.17/83.24: empty log/diff only for the exact CFE branch-check invocations."""
    if not tokens or tokens[0] != "git":
        return None
    if "log" in tokens and "--no-merges" in tokens and any("..HEAD" in token for token in tokens):
        return ProcessResult(returncode=0, stdout="", stderr="")
    if "diff" in tokens and "--name-only" in tokens and any(token == "HEAD" for token in tokens):
        return ProcessResult(returncode=0, stdout="", stderr="")
    return None


# Story 83.12 (spec-83-12): pinned literals so removing the derivation fails these tests.
MARSHAL_COVERAGE_GATE = "pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate"
SCRIBE_COVERAGE_GATE = "pixi run --frozen -e pyforge-scribe pyforge-scribe-coverage-gate"
DOCTOR_COVERAGE_GATE = "pixi run --frozen -e pyforge-doctor pyforge-doctor-coverage-gate"

# Story 83.23 (spec-83-23): pinned literals so removing the derivation fails these tests.
DOCTOR_CROSS_STATION_META = (
    "pixi run --frozen -e pyforge-doctor python -m pytest -q "
    "src/shared/packages/pyforge-doctor/tests/meta/test_coverage_gate_stays_outside_every_station.py "
    "src/shared/packages/pyforge-doctor/tests/meta/test_flag_gate_stays_outside_every_station.py"
)
STEWARD_CROSS_STATION_META = (
    "pixi run --frozen -e pyforge-steward python -m pytest -q "
    "src/shared/packages/pyforge-steward/tests/meta/test_no_station_assumes_local_recipes.py"
)
_DEFAULT_CROSS_STATION_META = (DOCTOR_CROSS_STATION_META, STEWARD_CROSS_STATION_META)


def test_compose_dispatch_policy_reads_a_real_project_toml(tmp_path: Path) -> None:
    """Regression: `tomllib.loads` takes `str`, not the `bytes` `read_bytes()`
    returns -- a live TypeError crashed the dispatch supervisor for any
    project with a real `marshal-policy.toml` (2026-08-29, atlas Story 21.1's
    dispatch)."""
    project_dir = tmp_path / "_bmad-output" / "projects" / "acme" / "planning-artifacts"
    project_dir.mkdir(parents=True)
    (project_dir / "marshal-policy.toml").write_text('gate_mode = "none"\n', encoding="utf-8")
    effective = compose_dispatch_policy("acme", tmp_path)
    assert effective.seed_view()["gate_mode"].value == "none"
    assert effective.seed_view()["gate_mode"].layer.value == "project"


def test_compose_dispatch_policy_degrades_on_a_malformed_toml(tmp_path: Path) -> None:
    project_dir = tmp_path / "_bmad-output" / "projects" / "acme" / "planning-artifacts"
    project_dir.mkdir(parents=True)
    (project_dir / "marshal-policy.toml").write_text("not = [valid toml", encoding="utf-8")
    effective = compose_dispatch_policy("acme", tmp_path)
    assert effective.seed_view()["gate_mode"].layer.value == "default"


def test_judge_verified_when_gate_findings_clean() -> None:
    inp = DispatchVerificationInput(findings=(), harness_self_report_shipped=True)
    assert judge_dispatch_verification(inp) == DispatchVerificationVerdict.VERIFIED


def test_judge_refused_when_gate_fails() -> None:
    findings = (
        Finding(
            code="MRS-GATE-001",
            severity=Severity.ERROR,
            message="verify command 'false' exited 1",
        ),
    )
    inp = DispatchVerificationInput(findings=findings)
    assert judge_dispatch_verification(inp) == DispatchVerificationVerdict.REFUSED


def test_self_report_alone_never_produces_verified_on_failing_gates() -> None:
    findings = (
        Finding(
            code="MRS-GATE-001",
            severity=Severity.ERROR,
            message="verify command 'pytest' exited 1",
        ),
    )
    inp = DispatchVerificationInput(findings=findings, harness_self_report_shipped=True)
    assert judge_dispatch_verification(inp) == DispatchVerificationVerdict.REFUSED
    assert would_land_on_self_report_only(inp) is True


def test_doctor_12_3_fixture_two_live_reproducible_leaks() -> None:
    """Canonical refusal: self-marked shipped + gate fail + out-of-surface diff."""
    findings = (
        Finding(
            code="MRS-GATE-001",
            severity=Severity.ERROR,
            message="verify command 'pixi run test' exited 1",
        ),
        Finding(
            code="MRS-GATE-007",
            severity=Severity.ERROR,
            message="changed path 'src/leak.py' is outside the effective surface",
            path="src/leak.py",
        ),
    )
    inp = DispatchVerificationInput(findings=findings, harness_self_report_shipped=True)
    assert gate_verdict_is_clean(inp.findings) is False
    assert judge_dispatch_verification(inp) == DispatchVerificationVerdict.REFUSED
    assert would_land_on_self_report_only(inp) is True
    failed = primary_gate_failure(inp.findings)
    assert failed is not None
    assert failed.code in {"MRS-GATE-001", "MRS-GATE-007"}


def test_self_report_with_clean_gates_does_not_block_verification() -> None:
    inp = DispatchVerificationInput(findings=(), harness_self_report_shipped=True)
    assert would_land_on_self_report_only(inp) is False
    assert judge_dispatch_verification(inp) == DispatchVerificationVerdict.VERIFIED


def test_build_fleet_row_surfaces_refused_verification() -> None:
    facts = FleetHomeFacts(
        slug="pyforge-marshal",
        branch="loop/pyforge-marshal",
        has_run=False,
        dispatch_story="22-3-example",
        dispatch_engine_alive=False,
        dispatch_completion_verdict="live",
        dispatch_verification_verdict="refused",
        dispatch_verification_failed_gate="MRS-GATE-001",
    )
    row, finding = build_fleet_row(facts)
    assert finding is None
    assert row["dispatch_verification_verdict"] == "refused"
    assert row["dispatch_verification_failed_gate"] == "MRS-GATE-001"


def test_build_fleet_row_surfaces_warn_mode_scope_advisories() -> None:
    """Story 28.15 (CAP-17), AC4: 'marshal status ... render a warn-mode
    violation finding, not journal-only'."""
    facts = FleetHomeFacts(
        slug="pyforge-marshal",
        branch="loop/pyforge-marshal",
        has_run=False,
        dispatch_story="28-15-example",
        dispatch_engine_alive=False,
        dispatch_completion_verdict="live",
        dispatch_verification_verdict="verified",
        dispatch_verification_scope_advisories=(
            {
                "code": "MRS-GATE-012",
                "message": "scope-violation mode is 'warn' ...",
                "path": "src/leak.py",
            },
        ),
    )
    row, finding = build_fleet_row(facts)
    assert finding is None
    assert row["dispatch_verification_scope_advisories"] == [
        {
            "code": "MRS-GATE-012",
            "message": "scope-violation mode is 'warn' ...",
            "path": "src/leak.py",
        }
    ]


def test_build_fleet_row_omits_scope_advisories_key_when_empty() -> None:
    """The sparse-key convention every OTHER optional dispatch field in this
    row already follows (`dispatch_verification_failed_gate` et al.) --
    never a fabricated empty list."""
    facts = FleetHomeFacts(
        slug="pyforge-marshal",
        branch="loop/pyforge-marshal",
        has_run=False,
        dispatch_story="28-15-example",
        dispatch_engine_alive=False,
        dispatch_completion_verdict="live",
        dispatch_verification_verdict="verified",
    )
    row, _finding = build_fleet_row(facts)
    assert "dispatch_verification_scope_advisories" not in row


def test_build_fleet_row_surfaces_landing_findings() -> None:
    """Story 53.2 review (I1): `execute_dispatch_land`'s envelope findings
    (MRS-DISP-047/048) must render, not just journal -- same AC4 rationale
    as the scope-advisories precedent above."""
    facts = FleetHomeFacts(
        slug="pyforge-marshal",
        branch="loop/pyforge-marshal",
        has_run=False,
        dispatch_story="53-2-example",
        dispatch_engine_alive=False,
        dispatch_completion_verdict="live",
        dispatch_landing_findings=(
            {
                "code": "MRS-DISP-048",
                "severity": "error",
                "message": "cannot commit/push spec-surface reconcile",
            },
        ),
    )
    row, finding = build_fleet_row(facts)
    assert finding is None
    assert row["dispatch_landing_findings"] == [
        {
            "code": "MRS-DISP-048",
            "severity": "error",
            "message": "cannot commit/push spec-surface reconcile",
        }
    ]


def test_build_fleet_row_omits_landing_findings_key_when_empty() -> None:
    facts = FleetHomeFacts(
        slug="pyforge-marshal",
        branch="loop/pyforge-marshal",
        has_run=False,
        dispatch_story="53-2-example",
        dispatch_engine_alive=False,
        dispatch_completion_verdict="live",
    )
    row, _finding = build_fleet_row(facts)
    assert "dispatch_landing_findings" not in row


class FakeVcs:
    def __init__(
        self,
        changed: tuple[str, ...] = ("src/shared/packages/pyforge-marshal/src/leak.py",),
    ) -> None:
        self._changed = changed

    def changed_files(self, repo_root: Path, worktree: Path, *, base: str):
        return self._changed


# --- Story 79.2 (spec-79-2): `lint-types` is a derived verification command ---

# --- Story 83.2 (spec-83-2): pyforge-core-test and deferred-work-check derived commands ---


# --- Story 83.12 (spec-83-12): per-station coverage-gate derived commands ---


def test_coverage_gate_commands_for_changed_files_derives_marshal_gate() -> None:
    """Mutation guard: without derivation this returns an empty tuple."""
    changed = ("src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py",)
    assert coverage_gate_commands_for_changed_files(changed) == (MARSHAL_COVERAGE_GATE,)


def test_coverage_gate_commands_for_changed_files_ignores_planning_and_core_src() -> None:
    planning = ("/".join(("_bmad-output", "projects", "pyforge-marshal", "planning-artifacts", "epics.md")),)
    core_only = ("/".join(("src", "shared", "packages", "pyforge-core", "src", "pyforge", "core", "process.py")),)
    assert coverage_gate_commands_for_changed_files(planning) == ()
    assert coverage_gate_commands_for_changed_files(core_only) == ()


def test_coverage_gate_commands_for_changed_files_ignores_testing_kit_src() -> None:
    """Story 83.12: testing-kit is not one of the eight coverage-gate stations."""
    changed = ("src/shared/packages/pyforge-testing-kit/src/pyforge/testing_kit/foo.py",)
    assert coverage_gate_commands_for_changed_files(changed) == ()


def test_coverage_gate_commands_for_changed_files_two_stations_once_each() -> None:
    changed = (
        "src/shared/packages/pyforge-marshal/src/pyforge/marshal/a.py",
        "src/shared/packages/pyforge-doctor/src/pyforge/doctor/b.py",
    )
    assert coverage_gate_commands_for_changed_files(changed) == (
        DOCTOR_COVERAGE_GATE,
        MARSHAL_COVERAGE_GATE,
    )


# --- Story 83.23 (spec-83-23): cross-station meta-test derived commands ---


def test_cross_station_meta_test_commands_derived_for_core_src_without_coverage_gate() -> None:
    """AC: core ``src/`` touches derive steward meta-tests but not a coverage gate."""
    changed = ("/".join(("src", "shared", "packages", "pyforge-core", "src", "pyforge", "core", "process.py")),)
    assert coverage_gate_commands_for_changed_files(changed) == ()
    assert cross_station_meta_test_commands_for_changed_files(changed) == _DEFAULT_CROSS_STATION_META


def test_cross_station_meta_test_commands_derived_for_testing_kit_src() -> None:
    changed = ("src/shared/packages/pyforge-testing-kit/src/pyforge/testing_kit/foo.py",)
    assert coverage_gate_commands_for_changed_files(changed) == ()
    assert cross_station_meta_test_commands_for_changed_files(changed) == _DEFAULT_CROSS_STATION_META


def test_cross_station_meta_test_commands_empty_for_planning_only() -> None:
    planning = ("/".join(("_bmad-output", "projects", "pyforge-marshal", "planning-artifacts", "epics.md")),)
    assert cross_station_meta_test_commands_for_changed_files(planning) == ()


def test_cross_station_meta_test_commands_mutation_guard_nonempty_constant() -> None:
    """Mutation: an empty constant would derive nothing for a touched ``src/`` path."""
    changed = ("src/shared/packages/pyforge-marshal/src/pyforge/marshal/x.py",)
    derived = cross_station_meta_test_commands_for_changed_files(changed)
    assert derived == _DEFAULT_CROSS_STATION_META


class _CommittingFakeVcs(FakeVcs):
    def __init__(self) -> None:
        super().__init__(changed=())
        self.committed: list[tuple[Path, tuple[Path, ...]]] = []

    def commit_paths(self, worktree: Path, paths: tuple[Path, ...], message: Redacted) -> str:
        self.committed.append((worktree, paths))
        return "deadbeef"


class _IntakeScriptProcess:
    """Runs ``deferred_work_intake.py`` with a controlled exit and optional ledger write."""

    def __init__(self, *, intake_exit: int = 0, append_ledger: str | None = None) -> None:
        self._intake_exit = intake_exit
        self._append_ledger = append_ledger

    def run(self, tokens, *, cwd: Path):
        git_log = _fake_git_log_empty(list(tokens))
        if git_log is not None:
            return git_log
        joined = " ".join(tokens)
        if "deferred_work_intake.py" in joined:
            if self._append_ledger is not None:
                ledger = cwd / "_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md"
                ledger.parent.mkdir(parents=True, exist_ok=True)
                ledger.write_text(self._append_ledger, encoding="utf-8")
            return ProcessResult(
                returncode=self._intake_exit,
                stdout="" if self._intake_exit == 0 else "",
                stderr="intake refused" if self._intake_exit else "",
            )
        return ProcessResult(returncode=0, stdout="ok", stderr="")


def test_run_pre_verification_deferred_work_intake_refusal_returns_mrs_gate_018(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    (worktree / "scripts").mkdir()
    (worktree / "scripts" / "deferred_work_intake.py").write_text("# stub\n", encoding="utf-8")
    finding = run_pre_verification_deferred_work_intake(
        process=_IntakeScriptProcess(intake_exit=2),
        committing_vcs=_CommittingFakeVcs(),
        worktree=worktree,
        project_slug="pyforge-marshal",
    )
    assert finding is not None
    assert finding.code == PRE_VERIFICATION_DEFERRED_WORK_INTAKE_CODE
    assert "refused" in finding.message


def test_run_pre_verification_deferred_work_intake_commits_when_ledger_changes(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    (worktree / "scripts").mkdir()
    (worktree / "scripts" / "deferred_work_intake.py").write_text("# stub\n", encoding="utf-8")
    vcs = _CommittingFakeVcs()
    new_body = "### DW-TEST-1\n\nsummary\n"
    assert (
        run_pre_verification_deferred_work_intake(
            process=_IntakeScriptProcess(append_ledger=new_body),
            committing_vcs=vcs,
            worktree=worktree,
            project_slug="pyforge-marshal",
        )
        is None
    )
    assert len(vcs.committed) == 1


def test_run_pre_verification_deferred_work_intake_no_op_does_not_commit(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    ledger = worktree / "_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("stable\n", encoding="utf-8")
    (worktree / "scripts").mkdir()
    (worktree / "scripts" / "deferred_work_intake.py").write_text("# stub\n", encoding="utf-8")
    vcs = _CommittingFakeVcs()
    assert (
        run_pre_verification_deferred_work_intake(
            process=_IntakeScriptProcess(),
            committing_vcs=vcs,
            worktree=worktree,
            project_slug="pyforge-marshal",
        )
        is None
    )
    assert vcs.committed == []


# --- Story 28.15: scope-violation enforcement mode (CAP-17) ------------------


# --- Story 28.22: verify blast radius / pre-existing-gate (CAP-5) ------------


def test_extract_failure_paths_from_pytest_collection_output() -> None:
    stderr = (
        "ERROR collecting tests/packaging/test_deps_atlas.py\n"
        "ImportError while importing test module "
        "'/tmp/wt/tests/packaging/test_deps_atlas.py'.\n"
        "ModuleNotFoundError: No module named 'pandas'\n"
    )
    paths = extract_failure_paths_from_verify_output("", stderr)
    assert paths == ("tests/packaging/test_deps_atlas.py",)


def test_path_in_story_blast_radius_matches_changed_or_surface() -> None:
    surface = ("src/shared/packages/pyforge-marshal/**",)
    changed = ("src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/foo.py",)
    assert path_in_story_blast_radius(
        "src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/foo.py",
        changed_files=changed,
        effective_surface=surface,
    )
    assert path_in_story_blast_radius(
        "src/shared/packages/pyforge-marshal/tests/unit/test_foo.py",
        changed_files=(),
        effective_surface=surface,
        project_slug="pyforge-marshal",
    )
    assert path_in_story_blast_radius(
        "tests/unit/test_foo.py",
        changed_files=(),
        effective_surface=surface,
        project_slug="pyforge-marshal",
    )
    assert not path_in_story_blast_radius(
        "tests/packaging/test_deps_atlas.py",
        changed_files=changed,
        effective_surface=surface,
        project_slug="pyforge-marshal",
    )


def test_reclassify_leaves_cross_surface_gate_015_unchanged() -> None:
    """Story 85.7 AC7: MRS-GATE-015 is never downgraded to MRS-GATE-014."""
    gate_015 = Finding(
        code="MRS-GATE-015",
        severity=Severity.ERROR,
        message="cross-surface verify command 'pixi run -e pyforge-guild flag-gate-check' exited 1",
    )
    findings = reclassify_pre_existing_gate_findings(
        (gate_015,),
        command_reports=(),
        changed_files=("/".join(("docs", "dreams", "pyforge-marshal.md")),),
        effective_surface=("docs/dreams/**",),
        project_slug="pyforge-marshal",
    )
    assert findings == (gate_015,)


def test_reclassify_pre_existing_gate_downgrades_unrelated_verify_failure() -> None:
    gate_001 = Finding(
        code="MRS-GATE-001",
        severity=Severity.ERROR,
        message="verify command 'pixi run pyforge-deps-test' exited 1",
    )
    reports = (
        {
            "command": "pixi run pyforge-deps-test",
            "stdout": "",
            "stderr": (
                "ERROR collecting tests/packaging/test_deps_atlas.py\nModuleNotFoundError: No module named 'pandas'\n"
            ),
        },
    )
    surface = ("src/shared/packages/pyforge-marshal/**",)
    changed = ("src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_retry.py",)
    findings = reclassify_pre_existing_gate_findings(
        (gate_001,),
        command_reports=reports,
        changed_files=changed,
        effective_surface=surface,
        project_slug="pyforge-marshal",
    )
    assert len(findings) == 1
    assert findings[0].code == PRE_EXISTING_GATE_CODE
    assert findings[0].severity is Severity.WARN
    assert (
        judge_dispatch_verification(DispatchVerificationInput(findings=findings))
        == DispatchVerificationVerdict.VERIFIED
    )


def test_reclassify_keeps_marshal_package_failure_as_gate_001() -> None:
    gate_001 = Finding(
        code="MRS-GATE-001",
        severity=Severity.ERROR,
        message="verify command 'pixi run pyforge-marshal-test' exited 1",
    )
    reports = (
        {
            "command": "pixi run pyforge-marshal-test",
            "stdout": "",
            "stderr": (
                "tests/unit/test_dispatch_retry.py:42: AssertionError\n"
                "FAILED tests/unit/test_dispatch_retry.py::test_example\n"
            ),
        },
    )
    surface = ("src/shared/packages/pyforge-marshal/**",)
    changed = ("src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_retry.py",)
    findings = reclassify_pre_existing_gate_findings(
        (gate_001,),
        command_reports=reports,
        changed_files=changed,
        effective_surface=surface,
        project_slug="pyforge-marshal",
    )
    assert findings == (gate_001,)
    assert (
        judge_dispatch_verification(DispatchVerificationInput(findings=findings)) == DispatchVerificationVerdict.REFUSED
    )


def test_reclassify_pre_existing_gate_with_empty_changed_files() -> None:
    """Doc-only / no-diff scope: unrelated verify reds still downgrade."""
    gate_001 = Finding(
        code="MRS-GATE-001",
        severity=Severity.ERROR,
        message="verify command 'pixi run pyforge-deps-test' exited 1",
    )
    reports = (
        {
            "command": "pixi run pyforge-deps-test",
            "stdout": "",
            "stderr": (
                "ERROR collecting tests/packaging/test_deps_atlas.py\nModuleNotFoundError: No module named 'pandas'\n"
            ),
        },
    )
    surface = ("src/shared/packages/pyforge-marshal/**",)
    findings = reclassify_pre_existing_gate_findings(
        (gate_001,),
        command_reports=reports,
        changed_files=(),
        effective_surface=surface,
        project_slug="pyforge-marshal",
    )
    assert len(findings) == 1
    assert findings[0].code == PRE_EXISTING_GATE_CODE
    assert (
        judge_dispatch_verification(DispatchVerificationInput(findings=findings))
        == DispatchVerificationVerdict.VERIFIED
    )


def test_reclassify_pre_existing_gate_with_empty_effective_surface() -> None:
    """AD-27: empty effective_surface must not skip reclassification when changed_files exist."""
    gate_001 = Finding(
        code="MRS-GATE-001",
        severity=Severity.ERROR,
        message="verify command 'pixi run pyforge-deps-test' exited 1",
    )
    reports = (
        {
            "command": "pixi run pyforge-deps-test",
            "stdout": "",
            "stderr": (
                "ERROR collecting tests/packaging/test_deps_atlas.py\nModuleNotFoundError: No module named 'pandas'\n"
            ),
        },
    )
    changed = ("src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_retry.py",)
    findings = reclassify_pre_existing_gate_findings(
        (gate_001,),
        command_reports=reports,
        changed_files=changed,
        effective_surface=(),
        project_slug="pyforge-marshal",
    )
    assert len(findings) == 1
    assert findings[0].code == PRE_EXISTING_GATE_CODE
    assert findings[0].severity is Severity.WARN
    assert (
        judge_dispatch_verification(DispatchVerificationInput(findings=findings))
        == DispatchVerificationVerdict.VERIFIED
    )


def test_pre_existing_gate_is_terminal_for_dispatch_retry() -> None:
    kind = classify_dispatch_block(
        session_log="",
        failed_gate=PRE_EXISTING_GATE_CODE,
        changed_path_count=2,
    )
    assert kind is DispatchBlockKind.TERMINAL


# --- Story 22.12: shared-surface cross-suite gate (CAP-12) -------------------


def test_changed_files_touch_shared_surface_prefix() -> None:
    assert gate.changed_files_touch_shared_surface(("src/platform/settings.py",))
    assert not gate.changed_files_touch_shared_surface(("src/shared/packages/pyforge-marshal/leak.py",))


# --- Story 22.14: multi-rule cross-surface gate --------------------------------


# --- Story 83.17 (spec-83-17): commit-attribution gate -------------------------


def test_findings_for_commit_attribution_violations_names_the_commit() -> None:
    sha = "deadbeef0123456789abcdef0123456789abcdef"
    findings = findings_for_commit_attribution_violations(
        (
            (
                sha,
                "Fix the widget",
                ((2, "Co-Authored-By trailer", "Co-authored-by: Cursor <cursoragent@cursor.com>"),),
            ),
        )
    )
    assert len(findings) == 1
    assert findings[0].code == COMMIT_ATTRIBUTION_GATE_CODE
    assert "deadbee" in findings[0].message
    assert "Fix the widget" in findings[0].message
    assert "Co-Authored-By trailer" in findings[0].message


def test_findings_for_commit_attribution_violations_empty_when_clean() -> None:
    assert findings_for_commit_attribution_violations(()) == ()
