"""Unit tests for dispatch independent verification (Story 22.3, CAP-3)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pyforge.core.process import ProcessResult

from pyforge.marshal.adapters.harness_bmadloop import _SURFACE_RECONCILE_COMMAND
from pyforge.marshal.core import gate, policy
from pyforge.marshal.core.dispatch_retry import (
    DispatchBlockKind,
    classify_dispatch_block,
)
from pyforge.marshal.core.dispatch_verification import (
    PRE_EXISTING_GATE_CODE,
    DispatchVerificationInput,
    DispatchVerificationVerdict,
    extract_failure_paths_from_verify_output,
    gate_verdict_is_clean,
    judge_dispatch_verification,
    path_in_story_blast_radius,
    primary_gate_failure,
    reclassify_pre_existing_gate_findings,
    would_land_on_self_report_only,
)
from pyforge.marshal.core.identity import normalize
from pyforge.marshal.core.model import Finding, Severity
from pyforge.marshal.core.status import FleetHomeFacts, build_fleet_row
from pyforge.marshal.dispatch_verify import (
    compose_dispatch_policy,
    evaluate_dispatch_verification,
)

# Story 79.2 (spec-79-2): the derived hygiene lane, pinned as a literal (not
# imported from `dispatch_verify`) so deleting or renaming the derivation fails
# these tests rather than silently updating them.
LINT_TYPES = "pixi run --frozen -e pyforge-guild lint-types"

# Story 83.2 (spec-83-2): the derived whole-tree check commands, pinned as
# literals so deleting or renaming the derivation fails these tests.
PYFORGE_CORE_TEST = "pixi run --frozen -e pyforge-core pyforge-core-test"
DEFERRED_WORK_CHECK = "pixi run --frozen -e pyforge-guild deferred-work-check"


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


class FakeProcess:
    def run(self, tokens, *, cwd: Path):
        if tokens and tokens[0] == "false":
            return ProcessResult(returncode=1, stdout="", stderr="fail")
        return ProcessResult(returncode=0, stdout="ok", stderr="")


class FakeVcs:
    def __init__(
        self,
        changed: tuple[str, ...] = ("src/shared/packages/pyforge-marshal/src/leak.py",),
    ) -> None:
        self._changed = changed

    def changed_files(self, repo_root: Path, worktree: Path, *, base: str):
        return self._changed


def test_evaluate_dispatch_verification_runs_gates_not_self_report(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    story_key = normalize("22-3-verification-is-the-product-no-landing-on-a-self-report")
    effective, _ = policy.compose(
        project_slug="pyforge-marshal",
        project={"verify_commands": ["false", "true"]},
        flags={},
    )
    envelope = evaluate_dispatch_verification(
        project_slug="pyforge-marshal",
        story_key=story_key,
        worktree=worktree,
        repo_root=tmp_path,
        effective=effective,
        spec_text=None,
        process=FakeProcess(),
        vcs=FakeVcs(),
    )
    inp = DispatchVerificationInput(findings=envelope.findings)
    assert judge_dispatch_verification(inp) == DispatchVerificationVerdict.REFUSED
    assert any(f.code == "MRS-GATE-001" for f in envelope.findings)
    # Story 28.14, CAP-16: zero declared epic_surfaces for epic 22, and the
    # changed file sits under pyforge-marshal's OWN package tree -- the
    # auto-derived default must suppress MRS-GATE-007 here, not just for
    # cli/gate.py's own copy of this fallback.
    assert not any(f.code == "MRS-GATE-007" for f in envelope.findings)
    assert would_land_on_self_report_only(
        DispatchVerificationInput(findings=envelope.findings, harness_self_report_shipped=True)
    )


def test_evaluate_dispatch_verification_appends_surface_guard_after_declared_commands(
    tmp_path: Path,
) -> None:
    """Story 53.1 (spec-53-1, CAP-261a): a dispatch session's own declared
    ``verify_commands`` run first, then the S-13.7 guard -- the SAME order
    ``harness_bmadloop.render_policy_toml`` appends it in for a loop home,
    via the SAME constant (``_SURFACE_RECONCILE_COMMAND``)."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    story_key = normalize("22-3-verification-is-the-product-no-landing-on-a-self-report")
    effective, _ = policy.compose(
        project_slug="pyforge-marshal",
        project={"verify_commands": ["true"]},
        flags={},
    )
    envelope = evaluate_dispatch_verification(
        project_slug="pyforge-marshal",
        story_key=story_key,
        worktree=worktree,
        repo_root=tmp_path,
        effective=effective,
        spec_text=None,
        process=FakeProcess(),
        vcs=FakeVcs(),
    )
    reports = envelope.data["commands"]
    assert [report["command"] for report in reports] == [
        "true",
        _SURFACE_RECONCILE_COMMAND,
        LINT_TYPES,
        PYFORGE_CORE_TEST,
        DEFERRED_WORK_CHECK,
    ]


class FakeProcessGuardFails:
    """Every command succeeds EXCEPT the S-13.7 guard itself -- isolates a
    guard failure from the station's own declared commands, which the
    existing ``FakeProcess`` (fails on ``false``) cannot express since the
    guard is a fixed ``python ...`` invocation, never a station's choice."""

    def run(self, tokens, *, cwd: Path):
        if tokens and tokens[0] == "python":
            return ProcessResult(returncode=1, stdout="", stderr="found drift")
        return ProcessResult(returncode=0, stdout="ok", stderr="")


def test_evaluate_dispatch_verification_surface_guard_failure_refuses(
    tmp_path: Path,
) -> None:
    """Story 53.1: a session that lands green on its own declared commands
    but leaves the S-13.7 guard's findings unaddressed is REFUSED exactly
    like a failure in any other verify command -- the guard is not merely
    advisory."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    story_key = normalize("22-3-verification-is-the-product-no-landing-on-a-self-report")
    effective, _ = policy.compose(
        project_slug="pyforge-marshal",
        project={"verify_commands": ["true"]},
        flags={},
    )
    envelope = evaluate_dispatch_verification(
        project_slug="pyforge-marshal",
        story_key=story_key,
        worktree=worktree,
        repo_root=tmp_path,
        effective=effective,
        spec_text=None,
        process=FakeProcessGuardFails(),
        vcs=FakeVcs(),
    )
    inp = DispatchVerificationInput(findings=envelope.findings)
    assert judge_dispatch_verification(inp) == DispatchVerificationVerdict.REFUSED
    guard_findings = [
        f for f in envelope.findings if f.code == "MRS-GATE-001" and _SURFACE_RECONCILE_COMMAND in f.message
    ]
    assert guard_findings, envelope.findings


def test_evaluate_dispatch_verification_spec_binding_stays_clean_with_derived_guard(
    tmp_path: Path,
) -> None:
    """Story 53.1, Edge-Case Matrix row 4: a tracked spec's own
    ``## Verification`` declares only the station's own commands -- it never
    names the S-13.7 guard, and the end-to-end ``spec_binding`` result must
    stay clean anyway, not just the isolated ``core/gate.py`` unit
    (``test_gate.py::test_check_spec_binding_derived_surface_guard_stays_implicit``
    covers that unit; this proves the wiring through
    ``evaluate_dispatch_verification`` too)."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    story_key = normalize("22-3-verification-is-the-product-no-landing-on-a-self-report")
    effective, _ = policy.compose(
        project_slug="pyforge-marshal",
        project={"verify_commands": ["false", "true"]},
        flags={},
    )
    spec_text = "## Verification\n\n**Commands:**\n- `false` -- expected: exit 0\n- `true` -- expected: exit 0\n"
    envelope = evaluate_dispatch_verification(
        project_slug="pyforge-marshal",
        story_key=story_key,
        worktree=worktree,
        repo_root=tmp_path,
        effective=effective,
        spec_text=spec_text,
        process=FakeProcess(),
        vcs=FakeVcs(),
    )
    assert envelope.data["spec_binding"]["violations"] == 0


def test_evaluate_dispatch_verification_dedupes_an_already_declared_guard(
    tmp_path: Path,
) -> None:
    """Story 53.1: an operator who already (wrongly -- see the guard
    constant's own "derive, don't declare" docstring) declared the guard in
    a station's ``verify_commands`` must not see it run, or bind, twice."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    story_key = normalize("22-3-verification-is-the-product-no-landing-on-a-self-report")
    effective, _ = policy.compose(
        project_slug="pyforge-marshal",
        project={"verify_commands": ["true", _SURFACE_RECONCILE_COMMAND]},
        flags={},
    )
    envelope = evaluate_dispatch_verification(
        project_slug="pyforge-marshal",
        story_key=story_key,
        worktree=worktree,
        repo_root=tmp_path,
        effective=effective,
        spec_text=None,
        process=FakeProcess(),
        vcs=FakeVcs(),
    )
    reports = envelope.data["commands"]
    assert [report["command"] for report in reports] == [
        "true",
        _SURFACE_RECONCILE_COMMAND,
        LINT_TYPES,
        PYFORGE_CORE_TEST,
        DEFERRED_WORK_CHECK,
    ]


def test_evaluate_dispatch_verification_dedupes_a_guard_declared_with_different_spacing(
    tmp_path: Path,
) -> None:
    """Story 53.1 review finding: the dedup collapses whitespace the same
    way ``gate.check_spec_binding`` does, so a station that declared the
    guard with different internal spacing still runs it exactly once,
    matching ``check_spec_binding``'s own normalization instead of an exact
    string comparison that would miss this case."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    story_key = normalize("22-3-verification-is-the-product-no-landing-on-a-self-report")
    respaced_guard = _SURFACE_RECONCILE_COMMAND.replace(" ", "  ", 1)
    effective, _ = policy.compose(
        project_slug="pyforge-marshal",
        project={"verify_commands": ["true", respaced_guard]},
        flags={},
    )
    envelope = evaluate_dispatch_verification(
        project_slug="pyforge-marshal",
        story_key=story_key,
        worktree=worktree,
        repo_root=tmp_path,
        effective=effective,
        spec_text=None,
        process=FakeProcess(),
        vcs=FakeVcs(),
    )
    reports = envelope.data["commands"]
    assert [report["command"] for report in reports] == [
        "true",
        _SURFACE_RECONCILE_COMMAND,
        LINT_TYPES,
        PYFORGE_CORE_TEST,
        DEFERRED_WORK_CHECK,
    ]


# --- Story 79.2 (spec-79-2): `lint-types` is a derived verification command ---

_STORY_22_3 = "22-3-verification-is-the-product-no-landing-on-a-self-report"


class FakeProcessLintFails:
    """Every command succeeds EXCEPT ``lint-types`` -- isolates a lint failure
    from the station's own commands and the S-13.7 guard. ``output`` is the
    lane's captured stdout; the default carries no file path at all."""

    def __init__(self, output: str = "") -> None:
        self._output = output

    def run(self, tokens, *, cwd: Path):
        if tokens and tokens[-1] == "lint-types":
            return ProcessResult(returncode=1, stdout=self._output, stderr="")
        return ProcessResult(returncode=0, stdout="ok", stderr="")


class FakeProcessCoreTestFails:
    """Every command succeeds EXCEPT ``pyforge-core-test`` -- isolates a
    core test failure from other commands."""

    def run(self, tokens, *, cwd: Path):
        if tokens and tokens[-1] == "pyforge-core-test":
            return ProcessResult(returncode=1, stdout="", stderr="core test failed")
        return ProcessResult(returncode=0, stdout="ok", stderr="")


class FakeProcessDeferredWorkFails:
    """Every command succeeds EXCEPT ``deferred-work-check`` -- isolates a
    deferred work check failure from other commands."""

    def run(self, tokens, *, cwd: Path):
        if tokens and tokens[-1] == "deferred-work-check":
            return ProcessResult(returncode=1, stdout="", stderr="found uncited verified lines")
        return ProcessResult(returncode=0, stdout="ok", stderr="")


def _verify_with(
    tmp_path: Path,
    *,
    verify_commands: list[str],
    process,
    spec_text: str | None = None,
    slug: str = "pyforge-marshal",
    vcs: FakeVcs | None = None,
):
    worktree = tmp_path / "wt"
    worktree.mkdir(parents=True, exist_ok=True)
    effective, _ = policy.compose(
        project_slug=slug,
        project={"verify_commands": verify_commands},
        flags={},
    )
    return evaluate_dispatch_verification(
        project_slug=slug,
        story_key=normalize(_STORY_22_3),
        worktree=worktree,
        repo_root=tmp_path,
        effective=effective,
        spec_text=spec_text,
        process=process,
        vcs=vcs or FakeVcs(),
    )


def test_evaluate_dispatch_verification_runs_lint_types_once_after_the_station_commands(
    tmp_path: Path,
) -> None:
    """Story 79.2, AC1: whatever a station's own ``verify_commands`` say, the
    hygiene lane runs exactly once, after them."""
    envelope = _verify_with(tmp_path, verify_commands=["true", "echo ok"], process=FakeProcess())
    commands = [report["command"] for report in envelope.data["commands"]]
    assert commands == [
        "true",
        "echo ok",
        _SURFACE_RECONCILE_COMMAND,
        LINT_TYPES,
        PYFORGE_CORE_TEST,
        DEFERRED_WORK_CHECK,
    ]
    assert commands.count(LINT_TYPES) == 1
    assert envelope.findings == ()


def test_evaluate_dispatch_verification_lint_types_runs_for_a_station_with_no_commands(
    tmp_path: Path,
) -> None:
    """Story 79.2, AC1: a bare ``verify_commands = []`` station is gated on
    ``lint-types`` too -- it is derived, never read from the station's list."""
    envelope = _verify_with(tmp_path, verify_commands=[], process=FakeProcess())
    assert [report["command"] for report in envelope.data["commands"]] == [
        _SURFACE_RECONCILE_COMMAND,
        LINT_TYPES,
        PYFORGE_CORE_TEST,
        DEFERRED_WORK_CHECK,
    ]


def test_evaluate_dispatch_verification_lint_types_failure_refuses_naming_the_lane(
    tmp_path: Path,
) -> None:
    """Story 79.2, AC2 / Edge-Case Matrix row 2: a change that is green on the
    station's own commands and the guard but red on ``lint-types`` is REFUSED,
    and the finding names ``lint-types`` (an ordinary MRS-GATE-001)."""
    envelope = _verify_with(tmp_path, verify_commands=["true"], process=FakeProcessLintFails())
    inp = DispatchVerificationInput(findings=envelope.findings)
    assert judge_dispatch_verification(inp) == DispatchVerificationVerdict.REFUSED
    lint_findings = [f for f in envelope.findings if f.code == "MRS-GATE-001" and "lint-types" in f.message]
    assert len(lint_findings) == 1, envelope.findings
    assert LINT_TYPES in lint_findings[0].message
    assert primary_gate_failure(envelope.findings) is not None


# The three real `lint-types` output shapes. `scripts/lint_types.py` runs ruff/mypy
# with cwd = the package dir, so every path is PACKAGE-relative -- it can never equal
# the story's repo-relative changed file below.
_SCRIBE_CHANGED = ("src/shared/packages/pyforge-scribe/src/pyforge/scribe/catalog.py",)
_LINT_OUTPUTS = {
    "ruff-format": "Would reformat: src/pyforge/scribe/catalog.py\n1 file would be reformatted\n",
    "ruff-check": "src/pyforge/scribe/catalog.py:12:5: E501 Line too long (121 > 120)\nFound 1 error.\n",
    "mypy": "src/pyforge/scribe/catalog.py:12: error: Incompatible types in assignment  [assignment]\n",
}


@pytest.mark.parametrize("output", _LINT_OUTPUTS.values(), ids=_LINT_OUTPUTS.keys())
def test_evaluate_dispatch_verification_lint_types_red_on_the_story_own_file_is_never_pre_existing(
    tmp_path: Path, output: str
) -> None:
    """Story 79.2, AC2 (review finding): a lint-types red whose output names the
    story's OWN changed file -- as a package-relative path -- must refuse as
    MRS-GATE-001 and never be downgraded to MRS-GATE-014 by the 28.22
    pre-existing reclassifier, which cannot match package-relative paths against
    repo-relative changed files and would call every lint failure "outside the
    story's blast radius" (verdict ``verified``)."""
    envelope = _verify_with(
        tmp_path,
        slug="pyforge-scribe",
        verify_commands=["true"],
        process=FakeProcessLintFails(output),
        vcs=FakeVcs(changed=_SCRIBE_CHANGED),
    )
    assert judge_dispatch_verification(DispatchVerificationInput(findings=envelope.findings)) == (
        DispatchVerificationVerdict.REFUSED
    )
    lint_findings = [f for f in envelope.findings if f.code == "MRS-GATE-001" and "lint-types" in f.message]
    assert len(lint_findings) == 1, envelope.findings
    assert not any(f.code == PRE_EXISTING_GATE_CODE for f in envelope.findings), envelope.findings


def test_evaluate_dispatch_verification_core_test_red_on_the_story_own_file_is_never_pre_existing(
    tmp_path: Path,
) -> None:
    """Story 83.2, reclassification test: a pyforge-core-test failure must refuse as
    MRS-GATE-001 and never be downgraded to MRS-GATE-014 by the pre-existing reclassifier."""
    envelope = _verify_with(
        tmp_path,
        slug="pyforge-scribe",
        verify_commands=["true"],
        process=FakeProcessCoreTestFails(),
        vcs=FakeVcs(changed=_SCRIBE_CHANGED),
    )
    assert judge_dispatch_verification(DispatchVerificationInput(findings=envelope.findings)) == (
        DispatchVerificationVerdict.REFUSED
    )
    core_findings = [f for f in envelope.findings if f.code == "MRS-GATE-001" and "pyforge-core-test" in f.message]
    assert len(core_findings) == 1, envelope.findings
    assert not any(f.code == PRE_EXISTING_GATE_CODE for f in envelope.findings), envelope.findings


def test_evaluate_dispatch_verification_deferred_work_red_on_the_story_own_file_is_never_pre_existing(
    tmp_path: Path,
) -> None:
    """Story 83.2, reclassification test: a deferred-work-check failure must refuse as
    MRS-GATE-001 and never be downgraded to MRS-GATE-014 by the pre-existing reclassifier."""
    envelope = _verify_with(
        tmp_path,
        slug="pyforge-scribe",
        verify_commands=["true"],
        process=FakeProcessDeferredWorkFails(),
        vcs=FakeVcs(changed=_SCRIBE_CHANGED),
    )
    assert judge_dispatch_verification(DispatchVerificationInput(findings=envelope.findings)) == (
        DispatchVerificationVerdict.REFUSED
    )
    deferred_findings = [
        f for f in envelope.findings if f.code == "MRS-GATE-001" and "deferred-work-check" in f.message
    ]
    assert len(deferred_findings) == 1, envelope.findings
    assert not any(f.code == PRE_EXISTING_GATE_CODE for f in envelope.findings), envelope.findings


def test_evaluate_dispatch_verification_surface_guard_red_on_the_story_own_file_is_never_pre_existing(
    tmp_path: Path,
) -> None:
    """Story 83.2, reclassification test: a surface reconcile (S-13.7 guard) failure must
    refuse as MRS-GATE-001 and never be downgraded to MRS-GATE-014 by the pre-existing
    reclassifier -- the guard reads the whole tree and its failures must refuse."""
    envelope = _verify_with(
        tmp_path,
        slug="pyforge-scribe",
        verify_commands=["true"],
        process=FakeProcessGuardFails(),
        vcs=FakeVcs(changed=_SCRIBE_CHANGED),
    )
    assert judge_dispatch_verification(DispatchVerificationInput(findings=envelope.findings)) == (
        DispatchVerificationVerdict.REFUSED
    )
    guard_findings = [
        f for f in envelope.findings if f.code == "MRS-GATE-001" and "spec_surface_reconcile" in f.message
    ]
    assert len(guard_findings) == 1, envelope.findings
    assert not any(f.code == PRE_EXISTING_GATE_CODE for f in envelope.findings), envelope.findings


def test_evaluate_dispatch_verification_lint_types_green_is_not_a_finding(tmp_path: Path) -> None:
    """Story 79.2, Edge-Case Matrix row 1: a clean change verifies."""
    envelope = _verify_with(tmp_path, verify_commands=["true"], process=FakeProcess())
    assert judge_dispatch_verification(DispatchVerificationInput(findings=envelope.findings)) == (
        DispatchVerificationVerdict.VERIFIED
    )


def test_evaluate_dispatch_verification_dedupes_an_already_declared_lint_types(
    tmp_path: Path,
) -> None:
    """Story 79.2, AC3 / Edge-Case Matrix row 3: a station that already lists
    ``lint-types`` still runs it once -- moved after its own commands, never
    twice."""
    envelope = _verify_with(tmp_path, verify_commands=[LINT_TYPES, "true"], process=FakeProcess())
    commands = [report["command"] for report in envelope.data["commands"]]
    assert commands == ["true", _SURFACE_RECONCILE_COMMAND, LINT_TYPES, PYFORGE_CORE_TEST, DEFERRED_WORK_CHECK]


def test_evaluate_dispatch_verification_dedupes_a_lint_types_declared_with_different_spacing(
    tmp_path: Path,
) -> None:
    """Story 79.2, AC3: the dedupe collapses whitespace the way the surface
    guard's does (and ``gate.check_spec_binding`` does)."""
    respaced = LINT_TYPES.replace(" ", "  ", 1)
    envelope = _verify_with(tmp_path, verify_commands=["true", respaced], process=FakeProcess())
    commands = [report["command"] for report in envelope.data["commands"]]
    assert commands == ["true", _SURFACE_RECONCILE_COMMAND, LINT_TYPES, PYFORGE_CORE_TEST, DEFERRED_WORK_CHECK]


def test_evaluate_dispatch_verification_a_declared_lint_types_failure_still_refuses_once(
    tmp_path: Path,
) -> None:
    """Story 79.2, AC3 + AC2: the de-duplicated lane still refuses, with ONE
    finding, not one per spelling."""
    envelope = _verify_with(tmp_path, verify_commands=["true", LINT_TYPES], process=FakeProcessLintFails())
    lint_findings = [f for f in envelope.findings if f.code == "MRS-GATE-001" and "lint-types" in f.message]
    assert len(lint_findings) == 1, envelope.findings


def test_evaluate_dispatch_verification_spec_binding_unchanged_by_the_derived_lint_types(
    tmp_path: Path,
) -> None:
    """Story 79.2, AC4 / Edge-Case Matrix row 4: a spec that names only the
    station's own commands binds clean with ``lint-types`` widened in (an
    undeclared extra is never a finding), and a spec that DOES declare
    ``lint-types`` binds clean too. A genuinely removed command still reds."""
    station = ["false", "true"]
    own_only = "## Verification\n\n**Commands:**\n- `false` -- expected: exit 0\n- `true` -- expected: exit 0\n"
    with_lint = own_only + f"- `{LINT_TYPES}` -- expected: exit 0\n"
    removed = own_only + "- `echo gone` -- expected: exit 0\n"
    clean_own = _verify_with(tmp_path / "a", verify_commands=station, process=FakeProcess(), spec_text=own_only)
    clean_lint = _verify_with(tmp_path / "b", verify_commands=station, process=FakeProcess(), spec_text=with_lint)
    reds = _verify_with(tmp_path / "c", verify_commands=station, process=FakeProcess(), spec_text=removed)
    assert clean_own.data["spec_binding"]["violations"] == 0
    assert clean_lint.data["spec_binding"]["violations"] == 0
    assert reds.data["spec_binding"]["violations"] == 1
    assert not any(f.code == "MRS-GATE-011" for f in clean_own.findings + clean_lint.findings)


# --- Story 83.2 (spec-83-2): pyforge-core-test and deferred-work-check derived commands ---


def test_evaluate_dispatch_verification_core_test_failure_refuses_naming_the_command(
    tmp_path: Path,
) -> None:
    """Story 83.2, AC1: a change that is green on the station's own commands
    but red on ``pyforge-core-test`` is REFUSED, and the finding names the
    command (an ordinary MRS-GATE-001)."""
    envelope = _verify_with(tmp_path, verify_commands=["true"], process=FakeProcessCoreTestFails())
    inp = DispatchVerificationInput(findings=envelope.findings)
    assert judge_dispatch_verification(inp) == DispatchVerificationVerdict.REFUSED
    core_findings = [f for f in envelope.findings if f.code == "MRS-GATE-001" and "pyforge-core-test" in f.message]
    assert len(core_findings) == 1, envelope.findings
    assert PYFORGE_CORE_TEST in core_findings[0].message
    assert primary_gate_failure(envelope.findings) is not None


def test_evaluate_dispatch_verification_deferred_work_failure_refuses_naming_the_command(
    tmp_path: Path,
) -> None:
    """Story 83.2, AC2: a change that is green on the station's own commands
    but red on ``deferred-work-check`` is REFUSED, and the finding names the
    command (an ordinary MRS-GATE-001)."""
    envelope = _verify_with(tmp_path, verify_commands=["true"], process=FakeProcessDeferredWorkFails())
    inp = DispatchVerificationInput(findings=envelope.findings)
    assert judge_dispatch_verification(inp) == DispatchVerificationVerdict.REFUSED
    deferred_findings = [
        f for f in envelope.findings if f.code == "MRS-GATE-001" and "deferred-work-check" in f.message
    ]
    assert len(deferred_findings) == 1, envelope.findings
    assert DEFERRED_WORK_CHECK in deferred_findings[0].message
    assert primary_gate_failure(envelope.findings) is not None


def test_evaluate_dispatch_verification_dedupes_already_declared_whole_tree_commands(
    tmp_path: Path,
) -> None:
    """Story 83.2: stations that already declare the whole-tree commands
    still run them once, de-duplicated like the other derived commands."""
    envelope = _verify_with(
        tmp_path, verify_commands=["true", PYFORGE_CORE_TEST, DEFERRED_WORK_CHECK], process=FakeProcess()
    )
    commands = [report["command"] for report in envelope.data["commands"]]
    assert commands == ["true", _SURFACE_RECONCILE_COMMAND, LINT_TYPES, PYFORGE_CORE_TEST, DEFERRED_WORK_CHECK]
    assert commands.count(PYFORGE_CORE_TEST) == 1
    assert commands.count(DEFERRED_WORK_CHECK) == 1


def test_every_tracked_story_spec_binds_the_same_with_lint_types_widened() -> None:
    """Story 79.2, AC4, against the live tree: for every tracked story spec
    of every station, widening the policy's commands with the derived
    ``lint-types`` lane adds no ``MRS-GATE-010``/``MRS-GATE-011`` finding the
    pre-79.2 widening (station commands + the S-13.7 guard) did not already
    report -- ``gate.check_spec_binding`` is one-directional.

    Story 83.2: extends to include the new whole-tree check commands."""
    import tomllib

    from pyforge.marshal.core import spec_binding
    from pyforge.marshal.dispatch_verify import _verify_commands_with_surface_guard

    repo_root = Path(__file__).resolve().parents[6]
    spec_paths = sorted(repo_root.glob("_bmad-output/projects/*/planning-artifacts/specs/spec-*.md"))
    if not spec_paths:
        pytest.skip("no tracked story specs in this checkout")
    effective_by_slug: dict[str, policy.EffectivePolicy] = {}
    checked = 0
    for spec_path in spec_paths:
        slug = spec_path.parents[2].name
        if slug not in effective_by_slug:
            policy_path = spec_path.parents[1] / "marshal-policy.toml"
            project = tomllib.loads(policy_path.read_text(encoding="utf-8")) if policy_path.is_file() else {}
            effective_by_slug[slug], _ = policy.compose(project_slug=slug, project=dict(project), flags={})
        effective = effective_by_slug[slug]
        declared = spec_binding.parse_success_signal(spec_path.read_text(encoding="utf-8"))
        before = (*effective.verify_commands.value, _SURFACE_RECONCILE_COMMAND)
        widened = _verify_commands_with_surface_guard(effective)
        assert LINT_TYPES in widened
        assert PYFORGE_CORE_TEST in widened
        assert DEFERRED_WORK_CHECK in widened
        before_messages = {f.message for f in gate.check_spec_binding(declared, before)}
        after_messages = {f.message for f in gate.check_spec_binding(declared, widened)}
        assert after_messages <= before_messages, (spec_path.name, after_messages - before_messages)
        checked += 1
    assert checked == len(spec_paths)


def test_evaluate_dispatch_verification_unconfigured_epic_still_denies_outside_default(
    tmp_path: Path,
) -> None:
    """Story 28.14, CAP-16: dispatch_verify.py's own copy of the "declared
    wins, else fall back to the auto-derived default" resolver must deny a
    changed file OUTSIDE the auto-derived default exactly like
    cli/gate.py's copy does -- not just the fact that its file matched the
    default in the test above."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    story_key = normalize("22-3-verification-is-the-product-no-landing-on-a-self-report")
    # Story 28.15 (CAP-17): `hard` declared explicitly -- this test is about
    # Story 28.14's surface computation, not about enforcement mode, and the
    # default flipped to `warn` (MRS-GATE-012, not MRS-GATE-007) since this
    # test was written.
    effective, _ = policy.compose(
        project_slug="pyforge-marshal",
        project={"scope_violation_mode": "hard"},
        flags={},
    )

    envelope = evaluate_dispatch_verification(
        project_slug="pyforge-marshal",
        story_key=story_key,
        worktree=worktree,
        repo_root=tmp_path,
        effective=effective,
        spec_text=None,
        process=FakeProcess(),
        vcs=FakeVcs(changed=("recipes/anything/recipe.yaml",)),
    )
    assert any(f.code == "MRS-GATE-007" for f in envelope.findings)


def test_evaluate_dispatch_verification_declared_entry_wins_over_auto_derived_default(
    tmp_path: Path,
) -> None:
    """Story 28.14, CAP-16: a DECLARED `[epic_surfaces]` entry is used
    outright at the dispatch call site too -- the auto-derived default is
    never consulted or merged in, even for a path (here `pixi.toml`) the
    default would have permitted."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    story_key = normalize("22-3-verification-is-the-product-no-landing-on-a-self-report")
    # Story 28.15 (CAP-17): `hard` declared explicitly for the same reason
    # as the sibling test above -- this test is about Story 28.14's
    # declared-entry-wins resolution, not about enforcement mode.
    effective, _ = policy.compose(
        project_slug="pyforge-marshal",
        project={
            "epic_surfaces": {"22": ["recipes/x/**"]},
            "scope_violation_mode": "hard",
        },
        flags={},
    )

    envelope = evaluate_dispatch_verification(
        project_slug="pyforge-marshal",
        story_key=story_key,
        worktree=worktree,
        repo_root=tmp_path,
        effective=effective,
        spec_text=None,
        process=FakeProcess(),
        vcs=FakeVcs(changed=("pixi.toml",)),
    )
    assert any(f.code == "MRS-GATE-007" for f in envelope.findings)


# --- Story 28.15: scope-violation enforcement mode (CAP-17) ------------------


def test_evaluate_dispatch_verification_no_declared_mode_defaults_to_warn_and_verifies(
    tmp_path: Path,
) -> None:
    """AC1/CAP-17: a violation under the undeclared (warn) default lands as
    an MRS-GATE-012 advisory and independent verification still VERIFIES --
    exactly the "never permanently deadlocks an autonomous drain" property
    this story exists for."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    story_key = normalize("22-3-verification-is-the-product-no-landing-on-a-self-report")
    effective, _ = policy.compose(project_slug="pyforge-marshal", project={}, flags={})

    envelope = evaluate_dispatch_verification(
        project_slug="pyforge-marshal",
        story_key=story_key,
        worktree=worktree,
        repo_root=tmp_path,
        effective=effective,
        spec_text=None,
        process=FakeProcess(),
        vcs=FakeVcs(changed=("recipes/anything/recipe.yaml",)),
    )
    assert envelope.data["scope_check"]["mode"] == "warn"
    codes = [f.code for f in envelope.findings]
    assert "MRS-GATE-007" not in codes
    assert "MRS-GATE-012" in codes
    assert (
        judge_dispatch_verification(DispatchVerificationInput(findings=envelope.findings))
        == DispatchVerificationVerdict.VERIFIED
    )


def test_evaluate_dispatch_verification_off_mode_reports_zero_findings(
    tmp_path: Path,
) -> None:
    """AC3: off declared -- MRS-GATE-007 (and its warn-mode advisory) never
    appear at all."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    story_key = normalize("22-3-verification-is-the-product-no-landing-on-a-self-report")
    effective, _ = policy.compose(
        project_slug="pyforge-marshal",
        project={"scope_violation_mode": "off"},
        flags={},
    )

    envelope = evaluate_dispatch_verification(
        project_slug="pyforge-marshal",
        story_key=story_key,
        worktree=worktree,
        repo_root=tmp_path,
        effective=effective,
        spec_text=None,
        process=FakeProcess(),
        vcs=FakeVcs(changed=("recipes/anything/recipe.yaml",)),
    )
    assert envelope.data["scope_check"]["mode"] == "off"
    assert envelope.data["scope_check"]["violations"] == 0
    codes = [f.code for f in envelope.findings]
    assert "MRS-GATE-007" not in codes
    assert "MRS-GATE-012" not in codes


def test_evaluate_dispatch_verification_two_stations_apply_their_own_mode_independently(
    tmp_path: Path,
) -> None:
    """AC5: one station's declared mode never changes another's."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    story_key = normalize("22-3-verification-is-the-product-no-landing-on-a-self-report")
    hard_effective, _ = policy.compose(
        project_slug="pyforge-marshal",
        project={"scope_violation_mode": "hard"},
        flags={},
    )
    warn_effective, _ = policy.compose(
        project_slug="pyforge-atlas",
        project={"scope_violation_mode": "warn"},
        flags={},
    )

    hard_envelope = evaluate_dispatch_verification(
        project_slug="pyforge-marshal",
        story_key=story_key,
        worktree=worktree,
        repo_root=tmp_path,
        effective=hard_effective,
        spec_text=None,
        process=FakeProcess(),
        vcs=FakeVcs(changed=("recipes/anything/recipe.yaml",)),
    )
    warn_envelope = evaluate_dispatch_verification(
        project_slug="pyforge-atlas",
        story_key=story_key,
        worktree=worktree,
        repo_root=tmp_path,
        effective=warn_effective,
        spec_text=None,
        process=FakeProcess(),
        vcs=FakeVcs(changed=("recipes/anything/recipe.yaml",)),
    )
    assert (
        judge_dispatch_verification(DispatchVerificationInput(findings=hard_envelope.findings))
        == DispatchVerificationVerdict.REFUSED
    )
    assert (
        judge_dispatch_verification(DispatchVerificationInput(findings=warn_envelope.findings))
        == DispatchVerificationVerdict.VERIFIED
    )


def test_evaluate_dispatch_verification_threads_the_real_project_slug_into_the_resolver(
    tmp_path: Path,
) -> None:
    """Review pass 2 (finding 5): every OTHER test in this file passes
    `project_slug="pyforge-marshal"` -- so a regression that hardcoded that
    literal at `dispatch_verify.py:181-183` instead of threading this
    function's own `project_slug` parameter through to
    `gate.resolve_policy_surface` would pass every one of them undetected
    (their slug happens to match the hardcoded value, and
    `data["scope_check"]` never exposes `policy_surface` to catch it via
    the payload either).

    Uses a DIFFERENT slug (``"acme"``) and a changed file inside ONLY
    acme's own auto-derived package-tree default
    (``src/shared/packages/acme/**``, Story 28.14/CAP-16's
    ``default_epic_surface``) -- deliberately NOT a bookkeeping path like
    ``pixi.toml`` (identical across every slug's default, so it cannot
    distinguish "real project_slug" from "hardcoded pyforge-marshal").
    This only stays green if the real parameter -- not a hardcoded literal
    -- drives the resolver."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    story_key = normalize("22-3-verification-is-the-product-no-landing-on-a-self-report")
    effective, _ = policy.compose(project_slug="acme", project={}, flags={})

    envelope = evaluate_dispatch_verification(
        project_slug="acme",
        story_key=story_key,
        worktree=worktree,
        repo_root=tmp_path,
        effective=effective,
        spec_text=None,
        process=FakeProcess(),
        vcs=FakeVcs(changed=("src/shared/packages/acme/module.py",)),
    )
    assert not any(f.code == "MRS-GATE-007" for f in envelope.findings)


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


class PackagingFailProcess:
    def run(self, tokens, *, cwd: Path):
        command = " ".join(tokens)
        if "pyforge-deps-test" in command:
            return ProcessResult(
                returncode=1,
                stdout="",
                stderr=(
                    "ERROR collecting tests/packaging/test_deps_atlas.py\n"
                    "ModuleNotFoundError: No module named 'pandas'\n"
                ),
            )
        if "pyforge-marshal-test" in command:
            return ProcessResult(
                returncode=1,
                stdout="",
                stderr=("tests/unit/test_dispatch_retry.py:10: AssertionError\n"),
            )
        return ProcessResult(returncode=0, stdout="ok", stderr="")


def test_evaluate_dispatch_verification_pre_existing_packaging_gate_warns(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    story_key = normalize("28-22-verify-blast-radius-pre-existing-gate")
    effective, _ = policy.compose(
        project_slug="pyforge-marshal",
        project={
            "verify_commands": [
                "pixi run pyforge-deps-test",
                "true",
            ]
        },
        flags={},
    )
    envelope = evaluate_dispatch_verification(
        project_slug="pyforge-marshal",
        story_key=story_key,
        worktree=worktree,
        repo_root=tmp_path,
        effective=effective,
        spec_text=None,
        process=PackagingFailProcess(),
        vcs=FakeVcs(changed=("src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_retry.py",)),
    )
    codes = [finding.code for finding in envelope.findings]
    assert "MRS-GATE-001" not in codes
    assert PRE_EXISTING_GATE_CODE in codes
    assert (
        judge_dispatch_verification(DispatchVerificationInput(findings=envelope.findings))
        == DispatchVerificationVerdict.VERIFIED
    )


def test_evaluate_dispatch_verification_marshal_test_failure_still_refuses(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    story_key = normalize("28-22-verify-blast-radius-pre-existing-gate")
    effective, _ = policy.compose(
        project_slug="pyforge-marshal",
        project={"verify_commands": ["pixi run pyforge-marshal-test", "true"]},
        flags={},
    )
    envelope = evaluate_dispatch_verification(
        project_slug="pyforge-marshal",
        story_key=story_key,
        worktree=worktree,
        repo_root=tmp_path,
        effective=effective,
        spec_text=None,
        process=PackagingFailProcess(),
        vcs=FakeVcs(changed=("src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_retry.py",)),
    )
    assert any(finding.code == "MRS-GATE-001" for finding in envelope.findings)
    assert (
        judge_dispatch_verification(DispatchVerificationInput(findings=envelope.findings))
        == DispatchVerificationVerdict.REFUSED
    )


# --- Story 22.12: shared-surface cross-suite gate (CAP-12) -------------------


class CrossSurfaceProcess:
    """Fake process that passes station verify but can fail platform-ci-local."""

    def __init__(self, *, platform_exit: int = 0) -> None:
        self._platform_exit = platform_exit
        self.platform_invocations = 0

    def run(self, tokens, *, cwd: Path):
        joined = " ".join(tokens)
        if "platform-ci-local" in joined:
            self.platform_invocations += 1
            return ProcessResult(
                returncode=self._platform_exit,
                stdout="",
                stderr="platform fail" if self._platform_exit else "",
            )
        if tokens and tokens[0] == "false":
            return ProcessResult(returncode=1, stdout="", stderr="fail")
        return ProcessResult(returncode=0, stdout="ok", stderr="")


def test_changed_files_touch_shared_surface_prefix() -> None:
    assert gate.changed_files_touch_shared_surface(("src/platform/settings.py",))
    assert not gate.changed_files_touch_shared_surface(("src/shared/packages/pyforge-marshal/leak.py",))


def test_evaluate_dispatch_verification_station_only_diff_skips_cross_surface(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    story_key = normalize(
        "22-12-a-shared-surface-diff-also-clears-its-own-full-suite-not-just-the-station-s-bound-gate"
    )
    effective, _ = policy.compose(
        project_slug="pyforge-marshal",
        project={"verify_commands": ["true"]},
        flags={},
    )
    process = CrossSurfaceProcess()
    envelope = evaluate_dispatch_verification(
        project_slug="pyforge-marshal",
        story_key=story_key,
        worktree=worktree,
        repo_root=tmp_path,
        effective=effective,
        spec_text=None,
        process=process,
        vcs=FakeVcs(changed=("src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py",)),
    )
    assert envelope.data["cross_surface_check"]["checked"] is False
    assert process.platform_invocations == 0
    assert "MRS-GATE-015" not in [f.code for f in envelope.findings]


def test_evaluate_dispatch_verification_platform_diff_runs_cross_surface_pass(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    story_key = normalize(
        "22-12-a-shared-surface-diff-also-clears-its-own-full-suite-not-just-the-station-s-bound-gate"
    )
    effective, _ = policy.compose(
        project_slug="pyforge-marshal",
        project={"verify_commands": ["true"]},
        flags={},
    )
    process = CrossSurfaceProcess(platform_exit=0)
    envelope = evaluate_dispatch_verification(
        project_slug="pyforge-marshal",
        story_key=story_key,
        worktree=worktree,
        repo_root=tmp_path,
        effective=effective,
        spec_text=None,
        process=process,
        vcs=FakeVcs(changed=("src/platform/tests/test_ws_events.py",)),
    )
    assert envelope.data["cross_surface_check"]["checked"] is True
    assert process.platform_invocations == 1
    assert "MRS-GATE-015" not in [f.code for f in envelope.findings]
    assert (
        judge_dispatch_verification(DispatchVerificationInput(findings=envelope.findings))
        == DispatchVerificationVerdict.VERIFIED
    )


def test_evaluate_dispatch_verification_49_14_fixture_bound_green_platform_red(
    tmp_path: Path,
) -> None:
    """49.14 replay: station-bound gate green, full platform suite red -> REFUSED."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    story_key = normalize(
        "22-12-a-shared-surface-diff-also-clears-its-own-full-suite-not-just-the-station-s-bound-gate"
    )
    effective, _ = policy.compose(
        project_slug="pyforge-steward",
        project={"verify_commands": ["true"]},
        flags={},
    )
    process = CrossSurfaceProcess(platform_exit=1)
    envelope = evaluate_dispatch_verification(
        project_slug="pyforge-steward",
        story_key=story_key,
        worktree=worktree,
        repo_root=tmp_path,
        effective=effective,
        spec_text=None,
        process=process,
        vcs=FakeVcs(changed=("src/platform/host/urls.py",)),
    )
    assert process.platform_invocations == 1
    assert any(f.code == "MRS-GATE-015" for f in envelope.findings)
    assert (
        judge_dispatch_verification(DispatchVerificationInput(findings=envelope.findings))
        == DispatchVerificationVerdict.REFUSED
    )


def test_evaluate_dispatch_verification_cross_station_same_cross_surface_bar(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    story_key = normalize(
        "22-12-a-shared-surface-diff-also-clears-its-own-full-suite-not-just-the-station-s-bound-gate"
    )
    changed = ("src/platform/middleware.py",)
    for slug in ("pyforge-steward", "pyforge-atlas"):
        process = CrossSurfaceProcess(platform_exit=1)
        effective, _ = policy.compose(
            project_slug=slug,
            project={"verify_commands": ["true"]},
            flags={},
        )
        envelope = evaluate_dispatch_verification(
            project_slug=slug,
            story_key=story_key,
            worktree=worktree,
            repo_root=tmp_path,
            effective=effective,
            spec_text=None,
            process=process,
            vcs=FakeVcs(changed=changed),
        )
        assert envelope.data["cross_surface_check"]["command"] == (gate.shared_surface_verify_command())
        assert any(f.code == "MRS-GATE-015" for f in envelope.findings)
