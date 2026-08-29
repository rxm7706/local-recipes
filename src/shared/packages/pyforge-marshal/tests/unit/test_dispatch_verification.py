"""Unit tests for dispatch independent verification (Story 22.3, CAP-3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.core.process import ProcessResult
from pyforge.marshal.dispatch_verify import (
    compose_dispatch_policy,
    evaluate_dispatch_verification,
)
from pyforge.marshal.core import policy
from pyforge.marshal.core.dispatch_verification import (
    DispatchVerificationInput,
    DispatchVerificationVerdict,
    gate_verdict_is_clean,
    judge_dispatch_verification,
    primary_gate_failure,
    would_land_on_self_report_only,
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


class FakeProcess:
    def run(self, tokens, *, cwd: Path):
        if tokens and tokens[0] == "false":
            return ProcessResult(returncode=1, stdout="", stderr="fail")
        return ProcessResult(returncode=0, stdout="ok", stderr="")


class FakeVcs:
    def changed_files(self, repo_root: Path, worktree: Path, *, base: str):
        return ("src/shared/packages/pyforge-marshal/src/leak.py",)


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
    assert would_land_on_self_report_only(
        DispatchVerificationInput(
            findings=envelope.findings, harness_self_report_shipped=True
        )
    )
