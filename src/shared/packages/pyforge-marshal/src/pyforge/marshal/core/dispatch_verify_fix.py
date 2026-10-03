"""Verification-refusal fix turn — pure decision and prompt (Story 85.1, CAP-286).

When dispatch verification refuses after a finished session, one bounded fix
turn may hand the failure back to the writing harness. AD-4: no I/O here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .dispatch_verification import DispatchVerificationVerdict, _command_from_gate_001_message
from .gate import CROSS_SURFACE_GATE_CODE
from .model import Finding, Severity, Status, status_for
from .verdict import classify, compute_verdict

VERIFY_FIX_LOOP_FLAG_KEY = "pyforge.marshal.verify_fix_loop"

# Finding codes (Story 85.1)
FIX_TURN_START_FAILED_CODE = "MRS-DISP-058"
FIX_TURN_TIMEOUT_CODE = "MRS-DISP-059"
FIX_TURN_REVERIFY_REFUSED_CODE = "MRS-DISP-060"

_VERIFY_REFUSAL_GATE_PREFIX = "MRS-GATE-"


class VerifyFixLaunchMode(StrEnum):
    RESUME = "resume"
    FIX_ONLY = "fix_only"


@dataclass(frozen=True)
class FailedVerifyCommand:
    command: str
    stdout: str
    stderr: str
    exit_code: int | None


@dataclass(frozen=True)
class VerifyFixSettings:
    output_tail_bytes: int
    wall_clock_seconds: float


@dataclass(frozen=True)
class VerifyFixDecision:
    run: bool
    reason: str | None = None


def tail_bytes(text: str, *, max_bytes: int) -> str:
    """Keep at most ``max_bytes`` from the end of ``text`` (UTF-8 safe enough for logs)."""
    if max_bytes <= 0:
        return ""
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return text
    return encoded[-max_bytes:].decode("utf-8", errors="replace")


def extract_failed_verify_commands(
    command_reports: tuple[dict[str, object], ...],
    findings: tuple[Finding, ...],
) -> tuple[FailedVerifyCommand, ...]:
    """Failed gate verify commands from verification reports (MRS-GATE-001 family)."""
    failed_commands: set[str] = set()
    for finding in findings:
        if finding.severity is not Severity.ERROR:
            continue
        code = finding.code
        if not code.startswith(_VERIFY_REFUSAL_GATE_PREFIX):
            continue
        if status_for(classify(code)) is Status.OK:
            continue
        if code == "MRS-GATE-014":
            continue
        if code == "MRS-GATE-001" or code == CROSS_SURFACE_GATE_CODE:
            cmd = _command_from_gate_001_message(finding.message)
            if cmd is not None:
                failed_commands.add(cmd)
        elif code == "MRS-GATE-018":
            failed_commands.add("pre-verification deferred-work intake")
    if not failed_commands and findings:
        verdict = compute_verdict(findings)
        if status_for(verdict) is not Status.OK:
            primary = findings[0]
            failed_commands.add(primary.message.split(":", 1)[0][:200])
    by_command: dict[str, FailedVerifyCommand] = {}
    for report in command_reports:
        command = report.get("command")
        if not isinstance(command, str) or command not in failed_commands:
            continue
        exit_raw = report.get("returncode")
        exit_code = exit_raw if isinstance(exit_raw, int) else None
        stdout = str(report.get("stdout") or "")
        stderr = str(report.get("stderr") or "")
        by_command[command] = FailedVerifyCommand(
            command=command,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
        )
    ordered: list[FailedVerifyCommand] = []
    for command in failed_commands:
        if command in by_command:
            ordered.append(by_command[command])
        else:
            ordered.append(FailedVerifyCommand(command=command, stdout="", stderr="", exit_code=None))
    return tuple(sorted(ordered, key=lambda item: item.command))


def build_verify_fix_prompt(
    failed: tuple[FailedVerifyCommand, ...],
    *,
    output_tail_bytes: int,
) -> str:
    """Fix-turn prompt: failed command(s) and bounded output tail only."""
    lines = [
        "Dispatch verification refused after your session finished.",
        "Apply the smallest fix that makes the failing command(s) pass, then commit.",
        "Do not run a full story implementation again; fix only what verification named.",
        "",
    ]
    for item in failed:
        lines.append(f"Failed command: {item.command}")
        if item.exit_code is not None:
            lines.append(f"Exit code: {item.exit_code}")
        combined = "\n".join(part for part in (item.stdout, item.stderr) if part.strip())
        if combined.strip():
            tail = tail_bytes(combined, max_bytes=output_tail_bytes)
            lines.append("Output tail:")
            lines.append(tail)
        lines.append("")
    return "\n".join(lines).strip()


def decide_verify_fix_turn(
    *,
    flag_enabled: bool,
    verification_verdict: str | None,
    has_git_progress: bool,
    fix_turn_already_ran: bool,
    session_alive: bool,
) -> VerifyFixDecision:
    """Whether dispatch may run exactly one fix turn for this refusal."""
    if not flag_enabled:
        return VerifyFixDecision(run=False, reason="verify_fix_loop flag off")
    if fix_turn_already_ran:
        return VerifyFixDecision(run=False, reason="fix turn already journaled for this run")
    if session_alive:
        return VerifyFixDecision(run=False, reason="session still alive")
    if verification_verdict != DispatchVerificationVerdict.REFUSED.value:
        return VerifyFixDecision(run=False, reason="verification did not refuse")
    if not has_git_progress:
        return VerifyFixDecision(run=False, reason="no git progress on the story branch")
    return VerifyFixDecision(run=True)


def choose_verify_fix_launch_mode(
    *,
    resume_argv: tuple[str, ...] | None,
) -> VerifyFixLaunchMode:
    if resume_argv:
        return VerifyFixLaunchMode.RESUME
    return VerifyFixLaunchMode.FIX_ONLY


def fix_turn_park_message(*, failed_command: str | None) -> str:
    cmd = f" ({failed_command!r})" if failed_command else ""
    return f"verification still refused after one fix turn{cmd} — story parked for the operator (Story 85.1 / 83.10)"
