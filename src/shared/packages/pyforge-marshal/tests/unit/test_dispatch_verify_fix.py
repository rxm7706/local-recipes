"""Story 85.1 (CAP-286): verification-refusal fix turn."""

from __future__ import annotations

from pyforge.marshal.core.dispatch_verify_fix import (
    FailedVerifyCommand,
    VerifyFixLaunchMode,
    build_verify_fix_prompt,
    choose_verify_fix_launch_mode,
    decide_verify_fix_turn,
    extract_failed_verify_commands,
    tail_bytes,
)
from pyforge.marshal.core.dispatch_verification import DispatchVerificationVerdict
from pyforge.marshal.core.harness_profile import parse_profile
from pyforge.marshal.core.harness_profile import render_verify_fix_argv as render_fix
from pyforge.marshal.core.model import Finding, Severity
from pyforge.marshal.core.policy import DEFAULT_POLICY, compose


def test_decide_verify_fix_turn_requires_flag_and_refusal():
    assert decide_verify_fix_turn(
        flag_enabled=False,
        verification_verdict=DispatchVerificationVerdict.REFUSED.value,
        has_git_progress=True,
        fix_turn_already_ran=False,
        session_alive=False,
    ).run is False
    assert decide_verify_fix_turn(
        flag_enabled=True,
        verification_verdict=DispatchVerificationVerdict.VERIFIED.value,
        has_git_progress=True,
        fix_turn_already_ran=False,
        session_alive=False,
    ).run is False
    assert decide_verify_fix_turn(
        flag_enabled=True,
        verification_verdict=DispatchVerificationVerdict.REFUSED.value,
        has_git_progress=True,
        fix_turn_already_ran=False,
        session_alive=False,
    ).run is True


def test_build_verify_fix_prompt_uses_tail_only():
    failed = (
        FailedVerifyCommand(
            command="pixi run -e pyforge-guild lint-types",
            stdout="A" * 100,
            stderr="B" * 100,
            exit_code=1,
        ),
    )
    prompt = build_verify_fix_prompt(failed, output_tail_bytes=20)
    assert "bmad-build-auto" not in prompt
    assert "pixi run -e pyforge-guild lint-types" in prompt
    assert "AAAA" not in prompt or len(prompt) < 300


def test_tail_bytes_bounds_output():
    text = "0123456789" * 50
    tailed = tail_bytes(text, max_bytes=15)
    assert len(tailed.encode("utf-8")) <= 15


def test_extract_failed_verify_commands_from_gate_reports():
    reports = (
        {
            "command": "pixi run test",
            "returncode": 1,
            "stdout": "fail",
            "stderr": "",
        },
    )
    findings = (
        Finding(
            code="MRS-GATE-001",
            severity=Severity.ERROR,
            message="verify command 'pixi run test' exited 1",
        ),
    )
    extracted = extract_failed_verify_commands(reports, findings)
    assert len(extracted) == 1
    assert extracted[0].command == "pixi run test"


def test_resume_vs_fix_only_from_profile():
    profile = parse_profile(
        {
            "name": "fake",
            "binary": "fake",
            "argv": ["{prompt}"],
            "resume_argv": ["--continue", "{prompt}"],
        },
        source="t",
    )
    assert choose_verify_fix_launch_mode(resume_argv=profile.resume_argv) == VerifyFixLaunchMode.RESUME
    bare = parse_profile({"name": "bare", "binary": "bare", "argv": ["{prompt}"]}, source="t")
    assert choose_verify_fix_launch_mode(resume_argv=bare.resume_argv) == VerifyFixLaunchMode.FIX_ONLY


def test_render_verify_fix_resume_argv():
    profile = parse_profile(
        {
            "name": "fake",
            "binary": "fake",
            "argv": ["{prompt}"],
            "resume_argv": ["--continue", "{prompt}"],
        },
        source="t",
    )
    argv, _, _ = render_fix(
        profile,
        mode="resume",
        binary_path="/bin/fake",
        worktree=__import__("pathlib").Path("/tmp/wt"),
        prompt="fix it",
        model=None,
    )
    assert "--continue" in argv
    assert "fix it" in argv


def test_policy_verify_fix_defaults_compose():
    effective, _ = compose(project_slug="pyforge-marshal", project={}, flags={})
    block = effective.dispatch.value
    assert block["verify_fix_output_tail_bytes"] == DEFAULT_POLICY["dispatch"]["verify_fix_output_tail_bytes"]
    assert block["verify_fix_wall_clock_minutes"] == DEFAULT_POLICY["dispatch"]["verify_fix_wall_clock_minutes"]


def test_fix_turn_rule_mutation_flag_off_skips_turn():
    """Removing the flag gate makes this fail (was run=True)."""
    assert (
        decide_verify_fix_turn(
            flag_enabled=True,
            verification_verdict=DispatchVerificationVerdict.REFUSED.value,
            has_git_progress=True,
            fix_turn_already_ran=False,
            session_alive=False,
        ).run
        is True
    )
    assert (
        decide_verify_fix_turn(
            flag_enabled=False,
            verification_verdict=DispatchVerificationVerdict.REFUSED.value,
            has_git_progress=True,
            fix_turn_already_ran=False,
            session_alive=False,
        ).run
        is False
    )
