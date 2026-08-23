"""Dispatch session independent verification (Story 22.3, FR-193 CAP-3).

Pure functions only: Epic 2 gate outcomes judge whether a dispatched story
may land. Harness self-reports are recorded for diagnostics but never verdict
inputs (never-false-green; unevaluable ≠ pass).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .model import Finding, Status, status_for
from .verdict import compute_verdict


class DispatchVerificationVerdict(StrEnum):
    """Independent verification outcome before any landing (CAP-3)."""

    VERIFIED = "verified"
    REFUSED = "refused"


@dataclass(frozen=True)
class DispatchVerificationInput:
    """Inputs to the verification judge — gate findings only for the verdict."""

    findings: tuple[Finding, ...]
    # Harness/session self-report — recorded for diagnostics only, never a
    # verdict input (CAP-3 Always bullet; doctor-12.3 refusal fixture).
    harness_self_report_shipped: bool = False


def gate_verdict_is_clean(findings: tuple[Finding, ...]) -> bool:
    """True when Epic 2 gate objects report a fully clean envelope."""
    return status_for(compute_verdict(findings)) is Status.OK


def judge_dispatch_verification(inp: DispatchVerificationInput) -> DispatchVerificationVerdict:
    """Judge verification from gate findings only — never self-report."""
    if gate_verdict_is_clean(inp.findings):
        return DispatchVerificationVerdict.VERIFIED
    return DispatchVerificationVerdict.REFUSED


def primary_gate_failure(findings: tuple[Finding, ...]) -> Finding | None:
    """The most severe non-ok gate finding, for naming in a refusal verdict."""
    verdict = compute_verdict(findings)
    if status_for(verdict) is Status.OK:
        return None
    for finding in findings:
        if status_for(compute_verdict((finding,))) is not Status.OK:
            return finding
    return findings[0] if findings else None


def would_land_on_self_report_only(inp: DispatchVerificationInput) -> bool:
    """True when self-report claims shipped but independent gates refuse."""
    return inp.harness_self_report_shipped and not gate_verdict_is_clean(inp.findings)
