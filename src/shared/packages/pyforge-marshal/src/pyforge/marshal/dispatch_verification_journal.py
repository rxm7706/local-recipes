"""Shared ``dispatch-verification`` journal payload builder (Story 22.17).

One OUTCOME shape for supervisor and harness-done land-only paths.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .core import dispatch as dispatch_core
from .core import gate as gate_core
from .core import policy
from .core.dispatch_verification import (
    DispatchVerificationInput,
    DispatchVerificationVerdict,
    judge_dispatch_verification,
    primary_gate_failure,
)
from .core.dispatch_verify_fix import (
    command_reports_for_verify_fix,
    extract_failed_verify_commands,
    scrub_then_tail_bytes,
)
from .core.egress import redact_raw_text
from .core.journal import (
    SCOPE_VIOLATION_ADVISORIES_FIELD,
    VERIFY_FAILED_COMMANDS_FIELD,
    JournalEntryId,
    Phase,
    build_entry,
)
from .core.model import Envelope, Finding
from .core.policy import resolve_verify_fix_settings
from .dispatch_verify import verify_fix_loop_enabled


@dataclass(frozen=True)
class DispatchVerificationJournalEntries:
    """INTENT/OUTCOME pair plus offload metadata for ``prepare_for_write_offloading_fields``."""

    intent_entry: object
    outcome_entry: object
    offload_fields: frozenset[str]
    verification_verdict: DispatchVerificationVerdict
    next_counter: int


def build_dispatch_verification_journal_entries(
    *,
    findings: tuple[Finding, ...],
    gate_envelope_verdict: str,
    verify_data: Mapping[str, object],
    repo_root: Path,
    effective: policy.EffectivePolicy,
    run_id: str,
    writer_id: str,
    counter: int,
    ts: str,
) -> DispatchVerificationJournalEntries:
    """Build the supervisor's ``dispatch-verification`` INTENT/OUTCOME pair."""
    verification_verdict = judge_dispatch_verification(DispatchVerificationInput(findings=findings))
    failed = primary_gate_failure(findings)
    record_failed_commands = (
        verification_verdict == DispatchVerificationVerdict.REFUSED and verify_fix_loop_enabled(repo_root=repo_root)[0]
    )
    failed_commands_payload: list[dict[str, object]] = []
    if record_failed_commands:
        reports_tuple = command_reports_for_verify_fix(verify_data)
        fix_settings = resolve_verify_fix_settings(effective)
        for item in extract_failed_verify_commands(reports_tuple, findings):
            combined = "\n".join(part for part in (item.stdout, item.stderr) if part.strip())
            redacted_tail = scrub_then_tail_bytes(
                redact_raw_text(combined) or "",
                max_bytes=fix_settings.output_tail_bytes,
            )
            row: dict[str, object] = {
                "command": item.command,
                "exit_code": item.exit_code,
                "output_tail": redacted_tail,
            }
            if item.gate is not None:
                row["gate"] = item.gate
            failed_commands_payload.append(row)
    scope_advisories = [
        {"code": finding.code, "path": finding.path}
        for finding in findings
        if finding.code in gate_core._SCOPE_VIOLATION_ADVISORY_CODES.values()
    ]
    intent_entry = build_entry(
        id=JournalEntryId(writer_id, counter),
        ts=ts,
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
        phase=Phase.INTENT,
        payload={
            "verdict": verification_verdict.value,
            "gate_verdict": gate_envelope_verdict,
            "failed_gate": failed.code if failed is not None else None,
            "finding_count": len(findings),
        },
    )
    counter += 1
    outcome_entry = build_entry(
        id=JournalEntryId(writer_id, counter),
        ts=ts,
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
        phase=Phase.OUTCOME,
        intent_id=intent_entry.id,
        payload={
            "verdict": verification_verdict.value,
            "ok": verification_verdict == DispatchVerificationVerdict.VERIFIED,
            "failed_gate": failed.code if failed is not None else None,
            "failed_message": failed.message if failed is not None else None,
            "scope_violation_advisories": scope_advisories,
            **({VERIFY_FAILED_COMMANDS_FIELD: failed_commands_payload} if record_failed_commands else {}),
        },
    )
    counter += 1
    offload_fields = (
        frozenset({SCOPE_VIOLATION_ADVISORIES_FIELD, VERIFY_FAILED_COMMANDS_FIELD})
        if record_failed_commands
        else frozenset({SCOPE_VIOLATION_ADVISORIES_FIELD})
    )
    return DispatchVerificationJournalEntries(
        intent_entry=intent_entry,
        outcome_entry=outcome_entry,
        offload_fields=offload_fields,
        verification_verdict=verification_verdict,
        next_counter=counter,
    )


def build_dispatch_verification_journal_entries_from_envelope(
    *,
    envelope: Envelope,
    repo_root: Path,
    effective: policy.EffectivePolicy,
    run_id: str,
    writer_id: str,
    counter: int,
    ts: str,
) -> DispatchVerificationJournalEntries:
    """Convenience wrapper when independent verify produced a full envelope."""
    return build_dispatch_verification_journal_entries(
        findings=envelope.findings,
        gate_envelope_verdict=envelope.verdict.value,
        verify_data=envelope.data,
        repo_root=repo_root,
        effective=effective,
        run_id=run_id,
        writer_id=writer_id,
        counter=counter,
        ts=ts,
    )
