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
    #: Story 51.4 (CAP-252): the worktree spec is ``blocked`` (or the whole
    #: diff is spec-only narration) -- landing is refused before verify is
    #: even attempted, distinct from ``REFUSED`` (which implies a verify
    #: attempt ran and failed).
    BLOCKED = "blocked"


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


# --- Story 28.20 (CAP-4): mechanical land-conflict union -----------------

_LEDGER_STATUS_RANK: dict[str, int] = {
    "done": 100,
    "in-progress": 50,
    "review": 50,
    "ready-for-dev": 40,
    "ready": 40,
    "backlog": 10,
    "blocked": 5,
}

SPRINT_LEDGER_BASENAME = "sprint-status-ledger.yaml"


def sprint_ledger_rel_path(project_slug: str) -> str:
    """Repo-relative path to a project's tracked sprint-status ledger."""
    return (
        f"_bmad-output/projects/{project_slug}/planning-artifacts/"
        f"{SPRINT_LEDGER_BASENAME}"
    )


def ledger_status_precedence(left: str, right: str) -> str:
    """Return the higher-precedence ledger status (`done` beats `backlog`)."""
    left_rank = _LEDGER_STATUS_RANK.get(left.strip().lower(), 20)
    right_rank = _LEDGER_STATUS_RANK.get(right.strip().lower(), 20)
    return left if left_rank >= right_rank else right


def union_sprint_ledger_maps(*maps: dict[str, str]) -> dict[str, str]:
    """Union ledger key maps; ``done`` beats ``backlog`` on collisions."""
    merged: dict[str, str] = {}
    for status_map in maps:
        for key, status in status_map.items():
            if key in merged:
                merged[key] = ledger_status_precedence(merged[key], status)
            else:
                merged[key] = status
    return merged


def is_mechanical_conflict_path(path: str) -> bool:
    """True when ``path`` is a known mechanical-only merge conflict."""
    normalized = path.replace("\\", "/")
    return normalized.endswith(f"planning-artifacts/{SPRINT_LEDGER_BASENAME}") or normalized.endswith(
        SPRINT_LEDGER_BASENAME
    )


def unknown_conflict_paths(paths: tuple[str, ...]) -> tuple[str, ...]:
    """Conflict paths that are not mechanical — must escalate, never merge."""
    return tuple(sorted(p for p in paths if not is_mechanical_conflict_path(p)))
