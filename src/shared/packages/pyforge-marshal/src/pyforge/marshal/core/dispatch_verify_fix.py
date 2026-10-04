"""Verification-refusal fix turn — pure decision and prompt (Story 85.1, CAP-286).

When dispatch verification refuses after a finished session, one bounded fix
turn may hand the failure back to the writing harness. AD-4: no I/O here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .dispatch import KIND_DISPATCH_VERIFY_FIX
from .dispatch_verification import DispatchVerificationVerdict, _command_from_gate_001_message
from .gate import CROSS_SURFACE_GATE_CODE
from .journal import FoldResult, JournalEntry, JournalEntryId, Phase
from .model import Finding, Severity, Status, status_for
from .verdict import classify

VERIFY_FIX_LOOP_FLAG_KEY = "pyforge.marshal.verify_fix_loop"
VERIFY_FIX_PROMPT_FILENAME = "verify-fix-prompt.txt"

# Finding codes (Story 85.1)
FIX_TURN_START_FAILED_CODE = "MRS-DISP-058"
FIX_TURN_TIMEOUT_CODE = "MRS-DISP-059"
FIX_TURN_REVERIFY_REFUSED_CODE = "MRS-DISP-060"

_VERIFY_REFUSAL_GATE_PREFIX = "MRS-GATE-"

# Story 85.1 (M7) + 85.3: scrub credential-shaped text before truncation (never after).
_URL_CREDENTIALS = re.compile(r"(?i)([a-z][a-z0-9+.-]*://[^:/@\s]+):([^@\s/]+)@")
_BEARER_TOKEN = re.compile(r"(?i)(Authorization:\s*Bearer\s+)\S+")
_BASIC_AUTH = re.compile(r"(?i)(Authorization:\s*Basic\s+)\S+")
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(\b(?:password|passwd|secret|api[_-]?key|token|database_password|aws_secret_access_key)\s*=\s*['\"]?)[^'\"\s]+(['\"]?)"
)
_YAML_JSON_PASSWORD = re.compile(r"(?i)(^\s*password\s*:\s*)\S+", re.MULTILINE)
_SK_ANT_KEY = re.compile(r"\bsk-ant-[A-Za-z0-9_-]{8,}\b")


def scrub_fix_turn_exposure(text: str) -> str:
    """Redact common credential shapes fix-turn tails may carry (pure, Story 85.1/85.3)."""
    scrubbed = _URL_CREDENTIALS.sub(r"\1:***REDACTED***@", text)
    scrubbed = _BEARER_TOKEN.sub(r"\1***REDACTED***", scrubbed)
    scrubbed = _BASIC_AUTH.sub(r"\1***REDACTED***", scrubbed)
    scrubbed = _SECRET_ASSIGNMENT.sub(r"\1***REDACTED***\2", scrubbed)
    scrubbed = _YAML_JSON_PASSWORD.sub(r"\1***REDACTED***", scrubbed)
    scrubbed = _SK_ANT_KEY.sub("sk-ant-***REDACTED***", scrubbed)
    return scrubbed


def scrub_then_tail_bytes(text: str, *, max_bytes: int) -> str:
    """Redact the full output, then keep at most ``max_bytes`` from the end (Story 85.3)."""
    return tail_bytes(scrub_fix_turn_exposure(text), max_bytes=max_bytes)


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
            tail = scrub_then_tail_bytes(combined, max_bytes=output_tail_bytes)
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
    has_failed_commands: bool = True,
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
    if not has_failed_commands:
        return VerifyFixDecision(run=False, reason="no failed verify command to fix")
    return VerifyFixDecision(run=True)


def choose_verify_fix_launch_mode(
    *,
    resume_argv: tuple[str, ...] | None,
    harness_session_id: str | None = None,
    launch_profile: str | None = None,
    resolved_profile: str | None = None,
) -> VerifyFixLaunchMode:
    if not resume_argv or not harness_session_id:
        return VerifyFixLaunchMode.FIX_ONLY
    if launch_profile is not None and resolved_profile is not None and launch_profile != resolved_profile:
        return VerifyFixLaunchMode.FIX_ONLY
    return VerifyFixLaunchMode.RESUME


def fix_turn_park_message(*, failed_command: str | None) -> str:
    cmd = f" ({failed_command!r})" if failed_command else ""
    return f"verification still refused after one fix turn{cmd} — story parked for the operator (Story 85.1 / 83.10)"


# --------------------------------------------------------------------------
# Story 85.2 (CAP-286): the fix turn still in flight, read off a folded journal -- one pure reading shared by
# the supervisor (which settles a turn a killed supervisor left running) and every CLI reader (which reads that
# turn LIVE). AD-4: no I/O here; the liveness probe stays at the edge (``dispatch_verify.fix_session_alive``).
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class InFlightFixTurn:
    """An open ``dispatch-verify-fix`` INTENT -- no OUTCOME closes it yet.

    ``session_pid`` is the pid the launcher journaled for it (on the INTENT, else on the pid OBSERVATION naming
    it), ``None`` when the launch never recorded one; ``started_at`` is the INTENT's own UTC timestamp, the anchor
    of the turn's wall-clock budget and of the pid-reuse check."""

    intent: JournalEntry
    session_pid: int | None
    started_at: datetime


def fix_intent_ref(entry_id: JournalEntryId) -> dict[str, object]:
    """The journal's own id form -- ``{writer_id, counter}``, the shape of a line's ``intent_id`` -- for a payload
    naming the fix-turn INTENT it belongs to."""
    return {"writer_id": entry_id.writer_id, "counter": entry_id.counter}


def _journaled_pid(raw: object) -> int | None:
    # A pid of 0 or below is a process-group address to `kill`, never one session's pid.
    if isinstance(raw, int) and not isinstance(raw, bool) and raw > 0:
        return raw
    return None


def pending_verify_fix_intent(folded: FoldResult, run_id: str) -> JournalEntry | None:
    """The run's latest fix-turn INTENT that no OUTCOME closes, else ``None``."""
    entries = folded.by_kind(KIND_DISPATCH_VERIFY_FIX)
    closed = {
        entry.intent_id
        for entry in entries
        if entry.run_id == run_id and entry.phase is Phase.OUTCOME and entry.intent_id is not None
    }
    for entry in reversed(entries):
        if entry.run_id == run_id and entry.phase is Phase.INTENT and entry.id not in closed:
            return entry
    return None


def in_flight_verify_fix_turn(folded: FoldResult, run_id: str) -> InFlightFixTurn | None:
    """The run's open fix turn with its journaled session pid, else ``None``."""
    intent = pending_verify_fix_intent(folded, run_id)
    if intent is None:
        return None
    session_pid = _journaled_pid(intent.payload.get("session_pid"))
    if session_pid is None:
        ref = fix_intent_ref(intent.id)
        for entry in reversed(folded.by_kind(KIND_DISPATCH_VERIFY_FIX)):
            if entry.run_id != run_id or entry.phase is not Phase.OBSERVATION:
                continue
            if entry.payload.get("fix_intent_id") != ref:
                continue
            session_pid = _journaled_pid(entry.payload.get("session_pid"))
            if session_pid is not None:
                break
    # `JournalEntry` validates `ts` with `datetime.fromisoformat` at construction, so this parse cannot fail.
    return InFlightFixTurn(intent=intent, session_pid=session_pid, started_at=datetime.fromisoformat(intent.ts))


def fix_turn_remaining_budget_s(*, budget_s: float, started_at: datetime, now: datetime) -> float:
    """What is left of a fix turn's wall-clock budget, measured from its INTENT's UTC timestamp -- so a restarted
    supervisor never resets the budget (N7) and never trusts another process's monotonic clock."""
    return max(0.0, budget_s - (now - started_at).total_seconds())
