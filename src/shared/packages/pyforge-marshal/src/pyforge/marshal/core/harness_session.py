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
    HARNESS_MISCONFIG = "harness_misconfig"
    BACKGROUND_TASK_CEILING = "background_task_ceiling"
    UNKNOWN = "unknown"


# Each harness words its own usage wall differently, and that wording is a
# transient outcome (it changes as harnesses ship copy updates) — keyed per
# harness in one place so a future wording change touches one entry, not a
# flat list with no provenance. ``classify_session_log`` pools every
# harness's markers because the log text alone doesn't say which harness
# produced it (Story 50.2, spec-pyforge-marshal CAP-245).
_QUOTA_MARKERS_BY_HARNESS: dict[str, tuple[str, ...]] = {
    "claude": (
        "monthly spend limit",
        "spend limit",
        "usage limit",
        "rate limit",
        "quota exceeded",
        "insufficient quota",
    ),
    "cursor": (
        "out of usage",
        "increase your limit",
    ),
}

_QUOTA_MARKERS: tuple[str, ...] = tuple(marker for markers in _QUOTA_MARKERS_BY_HARNESS.values() for marker in markers)

_AUTH_MARKERS: tuple[str, ...] = (
    "not logged in",
    "authentication required",
    "login required",
    "invalid api key",
    "unauthorized",
)

# Harness exits before git progress (model routing, profile config).
_HARNESS_CONFIG_MARKERS: tuple[str, ...] = (
    "cannot use this model",
    "model not found",
    "unknown model",
    "is not an available model",
)

# Story 51.4 (CAP-252, epics.md widening): the harness's own print-mode
# background-wait ceiling (Claude Code's 600s cap) kills the session before
# it can commit real work -- the exact 51.3 incident. Transient: the next
# dispatch of the same story is expected to make progress, not repeat.
_BACKGROUND_TASK_CEILING_MARKERS: tuple[str, ...] = ("background tasks still running",)


def classify_session_log(log_text: str | None) -> HarnessSessionOutcome:
    if not log_text or not log_text.strip():
        return HarnessSessionOutcome.UNKNOWN
    lowered = log_text.lower()
    if any(marker in lowered for marker in _QUOTA_MARKERS):
        return HarnessSessionOutcome.QUOTA_EXCEEDED
    if any(marker in lowered for marker in _AUTH_MARKERS):
        return HarnessSessionOutcome.AUTH_FAILURE
    if any(marker in lowered for marker in _HARNESS_CONFIG_MARKERS):
        return HarnessSessionOutcome.HARNESS_MISCONFIG
    if any(marker in lowered for marker in _BACKGROUND_TASK_CEILING_MARKERS):
        return HarnessSessionOutcome.BACKGROUND_TASK_CEILING
    return HarnessSessionOutcome.UNKNOWN


def is_transient_harness_session_outcome(outcome: HarnessSessionOutcome) -> bool:
    return outcome in {
        HarnessSessionOutcome.QUOTA_EXCEEDED,
        HarnessSessionOutcome.AUTH_FAILURE,
        HarnessSessionOutcome.HARNESS_MISCONFIG,
        HarnessSessionOutcome.BACKGROUND_TASK_CEILING,
    }
