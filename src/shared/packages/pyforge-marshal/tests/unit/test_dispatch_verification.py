"""Unit tests for dispatch independent verification (Story 22.3, CAP-3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.core.process import ProcessResult
from pyforge.marshal.adapters.harness_bmadloop import _SURFACE_RECONCILE_COMMAND
from pyforge.marshal.dispatch_verify import (
    compose_dispatch_policy,
    evaluate_dispatch_verification,
)
from pyforge.marshal.core import gate, policy
from pyforge.marshal.core.dispatch_verification import (
    DispatchVerificationInput,
    DispatchVerificationVerdict,
    PRE_EXISTING_GATE_CODE,
    extract_failure_paths_from_verify_output,
    gate_verdict_is_clean,
    judge_dispatch_verification,
    path_in_story_blast_radius,
    primary_gate_failure,
    reclassify_pre_existing_gate_findings,
    would_land_on_self_report_only,
)
from pyforge.marshal.core.dispatch_retry import (
    DispatchBlockKind,
    classify_dispatch_block,
)
from pyforge.marshal.core.identity import normalize
from pyforge.marshal.core.model import Finding, Severity
from pyforge.marshal.core.status import FleetHomeFacts, build_fleet_row


def test_compose_dispatch_policy_reads_a_real_project_toml(tmp_path: Path) -> None:
    """Regression: `tomllib.loads` takes `str`, not the `bytes` `read_bytes()`
    returns -- a live TypeError crashed the dispatch supervisor for any
    project with a real `marshal-policy.toml` (2026-08-29, atlas Story 21.1's
    dispatch)."""
    project_dir = tmp_path / "_bmad-output" / "projects" / "acme" / "planning-artifacts"
    project_dir.mkdir(parents=True)
    (project_dir / "marshal-policy.toml").write_text(
        'gate_mode = "none"\n', encoding="utf-8"
    )
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
    inp = DispatchVerificationInput(
        findings=findings, harness_self_report_shipped=True
    )
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
    inp = DispatchVerificationInput(
        findings=findings, harness_self_report_shipped=True
    )
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


class FakeProcess:
    def run(self, tokens, *, cwd: Path):
        if tokens and tokens[0] == "false":
            return ProcessResult(returncode=1, stdout="", stderr="fail")
        return ProcessResult(returncode=0, stdout="ok", stderr="")


class FakeVcs:
    def __init__(
        self,
        changed: tuple[str, ...] = (
            "src/shared/packages/pyforge-marshal/src/leak.py",
        ),
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
        DispatchVerificationInput(
            findings=envelope.findings, harness_self_report_shipped=True
        )
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
        f
        for f in envelope.findings
        if f.code == "MRS-GATE-001" and _SURFACE_RECONCILE_COMMAND in f.message
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
    spec_text = (
        "## Verification\n"
        "\n"
        "**Commands:**\n"
        "- `false` -- expected: exit 0\n"
        "- `true` -- expected: exit 0\n"
    )
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
    respaced_guard = " ".join(_SURFACE_RECONCILE_COMMAND.split(" ", 1))
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
    ]


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
    assert judge_dispatch_verification(
        DispatchVerificationInput(findings=envelope.findings)
    ) == DispatchVerificationVerdict.VERIFIED


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
    assert judge_dispatch_verification(
        DispatchVerificationInput(findings=hard_envelope.findings)
    ) == DispatchVerificationVerdict.REFUSED
    assert judge_dispatch_verification(
        DispatchVerificationInput(findings=warn_envelope.findings)
    ) == DispatchVerificationVerdict.VERIFIED


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
    changed = (
        "src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/foo.py",
    )
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
                "ERROR collecting tests/packaging/test_deps_atlas.py\n"
                "ModuleNotFoundError: No module named 'pandas'\n"
            ),
        },
    )
    surface = ("src/shared/packages/pyforge-marshal/**",)
    changed = (
        "src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_retry.py",
    )
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
    assert judge_dispatch_verification(
        DispatchVerificationInput(findings=findings)
    ) == DispatchVerificationVerdict.VERIFIED


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
    changed = (
        "src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_retry.py",
    )
    findings = reclassify_pre_existing_gate_findings(
        (gate_001,),
        command_reports=reports,
        changed_files=changed,
        effective_surface=surface,
        project_slug="pyforge-marshal",
    )
    assert findings == (gate_001,)
    assert judge_dispatch_verification(
        DispatchVerificationInput(findings=findings)
    ) == DispatchVerificationVerdict.REFUSED


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
                "ERROR collecting tests/packaging/test_deps_atlas.py\n"
                "ModuleNotFoundError: No module named 'pandas'\n"
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
    assert judge_dispatch_verification(
        DispatchVerificationInput(findings=findings)
    ) == DispatchVerificationVerdict.VERIFIED


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
                "ERROR collecting tests/packaging/test_deps_atlas.py\n"
                "ModuleNotFoundError: No module named 'pandas'\n"
            ),
        },
    )
    changed = (
        "src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_retry.py",
    )
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
    assert judge_dispatch_verification(
        DispatchVerificationInput(findings=findings)
    ) == DispatchVerificationVerdict.VERIFIED


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
                stderr=(
                    "tests/unit/test_dispatch_retry.py:10: AssertionError\n"
                ),
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
        vcs=FakeVcs(
            changed=(
                "src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_retry.py",
            )
        ),
    )
    codes = [finding.code for finding in envelope.findings]
    assert "MRS-GATE-001" not in codes
    assert PRE_EXISTING_GATE_CODE in codes
    assert judge_dispatch_verification(
        DispatchVerificationInput(findings=envelope.findings)
    ) == DispatchVerificationVerdict.VERIFIED


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
        vcs=FakeVcs(
            changed=(
                "src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_retry.py",
            )
        ),
    )
    assert any(finding.code == "MRS-GATE-001" for finding in envelope.findings)
    assert judge_dispatch_verification(
        DispatchVerificationInput(findings=envelope.findings)
    ) == DispatchVerificationVerdict.REFUSED


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
    assert gate.changed_files_touch_shared_surface(
        ("src/platform/settings.py",)
    )
    assert not gate.changed_files_touch_shared_surface(
        ("src/shared/packages/pyforge-marshal/leak.py",)
    )


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
        vcs=FakeVcs(
            changed=(
                "src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py",
            )
        ),
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
    assert judge_dispatch_verification(
        DispatchVerificationInput(findings=envelope.findings)
    ) == DispatchVerificationVerdict.VERIFIED


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
    assert judge_dispatch_verification(
        DispatchVerificationInput(findings=envelope.findings)
    ) == DispatchVerificationVerdict.REFUSED


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
        assert envelope.data["cross_surface_check"]["command"] == (
            gate.shared_surface_verify_command()
        )
        assert any(f.code == "MRS-GATE-015" for f in envelope.findings)
