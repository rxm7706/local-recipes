"""Dispatch session landing eligibility (Story 22.4, FR-193 CAP-4).

Pure functions only: verification outcome and git facts judge whether a
dispatched story may land via existing Epic 4 machinery. Never land on
self-report without passing independent verification (Story 22.3).
"""

from __future__ import annotations

from enum import StrEnum

from . import promotion
from .dispatch_verification import DispatchVerificationVerdict


class DispatchLandingVerdict(StrEnum):
    """Landing outcome for a verified dispatch session (CAP-4)."""

    LANDED = "landed"
    REFUSED = "refused"
    ALREADY_LANDED = "already_landed"
    SKIPPED_UNVERIFIED = "skipped-unverified"


def may_attempt_dispatch_landing(
    verification_verdict: DispatchVerificationVerdict,
    *,
    story_merged_on_main: bool,
) -> bool:
    """True when independent verification passed and the story is not yet on main."""
    return (
        verification_verdict == DispatchVerificationVerdict.VERIFIED
        and not story_merged_on_main
    )


def refuse_unverified_landing(
    verification_verdict: DispatchVerificationVerdict,
) -> bool:
    """True when landing must be refused because verification did not pass."""
    return verification_verdict != DispatchVerificationVerdict.VERIFIED


def merge_subject_is_marshal_native(
    subject: str, template: str, project_slug: str
) -> bool:
    """True when ``subject`` classifies marshal-native (FR-187 / Story 5.10)."""
    return bool(
        promotion.marshal_native_merged_keys((subject,), template, project_slug)
    )
