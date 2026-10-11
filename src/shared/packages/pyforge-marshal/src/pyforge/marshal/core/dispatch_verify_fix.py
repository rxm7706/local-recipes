"""Verification-refusal fix turn — pure decision and prompt (Story 85.1, CAP-286).

When dispatch verification refuses after a finished session, one bounded fix
turn may hand the failure back to the writing harness. AD-4: no I/O here.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .dispatch import KIND_DISPATCH_VERIFY_FIX
from .dispatch_cfe_commit import is_terminal_cfe_verify_refusal
from .dispatch_verification import (
    DispatchVerificationVerdict,
    _command_from_verify_refusal_message,
)
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
#
# Story 85.4: the scrub runs in the supervisor's thread on the full output of every failed command, so every rule
# here is linear in the text -- no quantifier can match one character two ways, and a run of identifier or scheme
# characters is tried from its first character only (the lookbehinds); `token_budget.py:42:5:` keeps its line and
# column, and a value is never taken from the next line. `test_dispatch_verify_fix.py` times each rule on 100 KB
# adversarial input.
#: A terminal control sequence (an ANSI colour code): removed first, since `\x1b[32m` ends in a letter that would
#: hide the start of every rule after it, and it carries nothing the fix needs (85.4 review LOW-3).
_TERMINAL_CONTROL = re.compile(r"\x1b\[[0-?]*+[ -/]*+[@-~]")
#: A URL's userinfo password (an empty user too), to its `@` (a `://` inside it included). The scheme is tried from
#: the start of a run of scheme characters only; when no `@` follows the `:` before whitespace, the run is consumed
#: unchanged (``password`` unset), so no later scheme in the same run rescans it -- none of them can reach an `@`.
_URL_CREDENTIALS = re.compile(
    r"(?i)(?<![a-z0-9+.-])(?P<userinfo>[a-z0-9+.-]++://[^:/@\s]*+):(?:(?P<password>[^@\s]++)@|[^@\s]*+)"
)
#: An `Authorization:` header's credentials, whatever the scheme (`Bearer`, `Basic`, `token`, ...).
_AUTHORIZATION = re.compile(r"(?i)(Authorization:[ \t]*(?:[A-Za-z][A-Za-z0-9_-]*[ \t]+)?)\S+")
#: A `Cookie:` or `Set-Cookie:` header's value, to the end of its line.
_COOKIE = re.compile(r"(?i)(\bCookie:[ \t]*)[^\r\n]+")
#: What a key or flag names a secret by (85.3 landing review H3).
_SECRET_WORD = r"(?:password|passwd|secret|token|api[_-]?key|access[_-]?key)"
#: A bare identifier carrying a secret word (`DATABASE_PASSWORD`, `GITHUB_TOKEN`, `AWS_SECRET_ACCESS_KEY`,
#: `db_password`), taken whole: never a `.`, so a file name such as `token_budget.py` is no key.
_SECRET_IDENTIFIER = r"(?=[A-Za-z0-9_-]*?" + _SECRET_WORD + r")[A-Za-z0-9_-]++"
#: A quoted key: a dotted name carrying a secret word (`"db.password"`, `'spring.datasource.password'`), or a
#: credential header named whole (`"Authorization"`, `'cookie'`).
_SECRET_QUOTED_KEY = (
    r"(?P<kq>['\"])(?:(?=[A-Za-z0-9_.-]*?" + _SECRET_WORD + r")[A-Za-z0-9_.-]++"
    r"|(?:proxy-)?authorization|(?:set-)?cookie)(?P=kq)"
)
#: A quoted value to its closing quote on the same line (escapes included), or a bare one to the next whitespace
#: (an unclosed opening quote is taken with it).
_SECRET_VALUE = r"(?:(?P<vq>['\"])(?:\\.|(?!(?P=vq))[^\\\n])*(?P=vq)|['\"]?[^\s'\"]+)"
#: One key=value / key: value rule (85.3 landing review H3): a quoted key then `=` (never `==`) or any `:`, or a
#: bare secret identifier then `=` or a `:` no digit or second `:` follows (never `bin/token:42:5:`); then the value,
#: on the same line.
_SECRET_KEY_VALUE = re.compile(
    r"(?i)(?<![A-Za-z0-9_-])(?P<key>"
    r"(?:" + _SECRET_QUOTED_KEY + r"[ \t]*(?:=(?!=)|:)"
    r"|" + _SECRET_IDENTIFIER + r"[ \t]*(?:=(?!=)|:(?![\d:])))"
    r"[ \t]*)" + _SECRET_VALUE
)
#: A command-line flag naming a secret and its space-separated value (`--password hunter2`); a following flag is
#: never taken as the value.
_SECRET_FLAG_VALUE = re.compile(
    r"(?i)(?<![A-Za-z0-9_-])(?P<key>--?" + _SECRET_IDENTIFIER + r"[ \t]+)(?!-)" + _SECRET_VALUE
)
_SK_ANT_KEY = re.compile(r"sk-ant-[A-Za-z0-9_-]+")
#: A bare GitHub token of a real token's length -- `gh[pousr]_` and 36 or more characters, `github_pat_` and 20 or
#: more, as `core/egress.py` -- so a module name such as `ghp_import` is no token (85.4 review LOW-5).
_GITHUB_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_])(gh[pousr]_(?=[A-Za-z0-9]{36})|github_pat_(?=[A-Za-z0-9_]{20}))[A-Za-z0-9_]+"
)
_REDACTED = "***REDACTED***"


def _redact_url_password(match: re.Match[str]) -> str:
    if match.group("password") is None:
        return match.group(0)
    return f"{match.group('userinfo')}:{_REDACTED}@"


def _redact_secret_value(match: re.Match[str]) -> str:
    quote = match.group("vq") or ""
    return f"{match.group('key')}{quote}{_REDACTED}{quote}"


def scrub_fix_turn_exposure(text: str) -> str:
    """Redact common credential shapes fix-turn tails may carry (pure, Story 85.1/85.3/85.4)."""
    scrubbed = _TERMINAL_CONTROL.sub("", text)
    scrubbed = _URL_CREDENTIALS.sub(_redact_url_password, scrubbed)
    scrubbed = _AUTHORIZATION.sub(rf"\1{_REDACTED}", scrubbed)
    scrubbed = _COOKIE.sub(rf"\1{_REDACTED}", scrubbed)
    scrubbed = _SECRET_KEY_VALUE.sub(_redact_secret_value, scrubbed)
    scrubbed = _SECRET_FLAG_VALUE.sub(_redact_secret_value, scrubbed)
    scrubbed = _SK_ANT_KEY.sub(f"sk-ant-{_REDACTED}", scrubbed)
    scrubbed = _GITHUB_TOKEN.sub(rf"\1{_REDACTED}", scrubbed)
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
    gate: str | None = None


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


def command_reports_for_verify_fix(verify_data: Mapping[str, object]) -> tuple[dict[str, object], ...]:
    """Story verify reports plus cross-surface check reports (Story 85.7)."""
    reports: list[dict[str, object]] = []
    commands = verify_data.get("commands")
    if isinstance(commands, list):
        for item in commands:
            if isinstance(item, dict):
                reports.append(dict(item))
    cross_checks = verify_data.get("cross_surface_checks")
    if isinstance(cross_checks, list):
        for entry in cross_checks:
            if not isinstance(entry, Mapping):
                continue
            report = entry.get("report")
            if not isinstance(report, dict):
                continue
            merged = dict(report)
            cmd = entry.get("command")
            if isinstance(cmd, str) and "command" not in merged:
                merged["command"] = cmd
            reports.append(merged)
    return tuple(reports)


def extract_failed_verify_commands(
    command_reports: tuple[dict[str, object], ...],
    findings: tuple[Finding, ...],
) -> tuple[FailedVerifyCommand, ...]:
    """Failed gate verify commands from verification reports (MRS-GATE-001 and MRS-GATE-015)."""
    failed_by_command: dict[str, str] = {}
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
            cmd = _command_from_verify_refusal_message(finding.message)
            if cmd is not None:
                failed_by_command[cmd] = code
    by_command: dict[str, FailedVerifyCommand] = {}
    for report in command_reports:
        command = report.get("command")
        if not isinstance(command, str) or command not in failed_by_command:
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
            gate=failed_by_command[command],
        )
    ordered: list[FailedVerifyCommand] = []
    for command in failed_by_command:
        gate = failed_by_command[command]
        if command in by_command:
            ordered.append(by_command[command])
        else:
            ordered.append(FailedVerifyCommand(command=command, stdout="", stderr="", exit_code=None, gate=gate))
    return tuple(sorted(ordered, key=lambda item: item.command))


_FLAG_OUTPUT_SIGNALS = (
    "flags.json",
    "flag-overlays.json",
    "test_flags.py",
    "test_openfeature_file_flags.py",
    "flag-gate-check",
    "flag-default-env-mismatch",
)

_FLAG_REGISTRATION_DOC = "docs/reference/story-spec-flag-block.md"
_FLAG_REGISTRATION_SECTION = "Registering a flag"
_FLAG_REGISTRATION_PATHS = (
    "src/platform/config/flags.json",
    "src/platform/config/flag-overlays.json",
    "src/shared/packages/pyforge-core/tests/unit/test_flags.py",
    "src/platform/tests/test_openfeature_file_flags.py",
)


def _story_spec_has_flag_block(story_spec_text: str | None) -> bool:
    if not story_spec_text:
        return False
    if not story_spec_text.startswith("---"):
        return False
    end = story_spec_text.find("\n---", 3)
    if end == -1:
        return False
    frontmatter = story_spec_text[3:end]
    return (
        re.search(r"(?m)^flag:\s*$", frontmatter) is not None or re.search(r"(?m)^flag:\s*\S", frontmatter) is not None
    )


def verify_fix_prompt_flag_checklist_applies(
    failed: tuple[FailedVerifyCommand, ...],
    *,
    story_spec_text: str | None = None,
) -> bool:
    """Whether the fix-turn prompt should carry the flag registration checklist (Story 85.6)."""
    if _story_spec_has_flag_block(story_spec_text):
        return True
    blob = "\n".join(part for item in failed for part in (item.stdout, item.stderr, item.command) if part)
    lowered = blob.casefold()
    return any(signal.casefold() in lowered for signal in _FLAG_OUTPUT_SIGNALS)


def build_verify_fix_prompt(
    failed: tuple[FailedVerifyCommand, ...],
    *,
    output_tail_bytes: int,
    story_spec_text: str | None = None,
) -> str:
    """Fix-turn prompt: failed command(s) and bounded output tail only."""
    lines = [
        "Dispatch verification refused after your session finished.",
        "Apply the smallest fix that makes the failing command(s) pass, then commit.",
        "Do not run a full story implementation again; fix only what verification named.",
        "",
        "Reproduce and confirm your fix by re-running exactly the failed command(s) quoted below — "
        "verbatim, with no substitutions.",
        "Do not run a package's raw tests directory (for example pytest under "
        "src/shared/packages/<station>/tests); use the station's pixi verify task instead "
        "(it applies the correct markers and deselections).",
        "",
    ]
    if verify_fix_prompt_flag_checklist_applies(failed, story_spec_text=story_spec_text):
        lines.extend(
            [
                "This failure involves feature-flag registration. Before re-verifying, touch all four "
                "registration points:",
                f"- {_FLAG_REGISTRATION_PATHS[0]}",
                f"- {_FLAG_REGISTRATION_PATHS[1]} (per-environment values follow the story spec's flag.default)",
                f"- {_FLAG_REGISTRATION_PATHS[2]}",
                f"- {_FLAG_REGISTRATION_PATHS[3]}",
                f"See {_FLAG_REGISTRATION_DOC} § *{_FLAG_REGISTRATION_SECTION}* for the full checklist.",
                "",
            ]
        )
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
    verification_failed_gate: str | None = None,
) -> VerifyFixDecision:
    """Whether dispatch may run exactly one fix turn for this refusal."""
    if is_terminal_cfe_verify_refusal(verification_failed_gate):
        return VerifyFixDecision(run=False, reason="unsanctioned CFE commit on branch -- terminal")
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
