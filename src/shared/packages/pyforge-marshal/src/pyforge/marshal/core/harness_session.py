"""Pure session-harness log classification (dispatch hotfix 2026-09-01).

When a detached harness exits before any git progress, the dispatch
supervisor and fleet drain need to distinguish transient billing/auth
failures (retry with the next ``harness_preference`` profile) from
terminal story failures.
"""

from __future__ import annotations

from enum import StrEnum


class HarnessSessionOutcome(StrEnum):
    OK = "ok"
    QUOTA_EXCEEDED = "quota_exceeded"
    AUTH_FAILURE = "auth_failure"
    UNKNOWN = "unknown"


_QUOTA_MARKERS: tuple[str, ...] = (
    "monthly spend limit",
    "spend limit",
    "usage limit",
    "rate limit",
    "quota exceeded",
    "insufficient quota",
)

_AUTH_MARKERS: tuple[str, ...] = (
    "not logged in",
    "authentication required",
    "login required",
    "invalid api key",
    "unauthorized",
)


def classify_session_log(log_text: str | None) -> HarnessSessionOutcome:
    if not log_text or not log_text.strip():
        return HarnessSessionOutcome.UNKNOWN
    lowered = log_text.lower()
    if any(marker in lowered for marker in _QUOTA_MARKERS):
        return HarnessSessionOutcome.QUOTA_EXCEEDED
    if any(marker in lowered for marker in _AUTH_MARKERS):
        return HarnessSessionOutcome.AUTH_FAILURE
    return HarnessSessionOutcome.UNKNOWN


def is_transient_harness_session_outcome(outcome: HarnessSessionOutcome) -> bool:
    return outcome in {
        HarnessSessionOutcome.QUOTA_EXCEEDED,
        HarnessSessionOutcome.AUTH_FAILURE,
    }
