"""Dispatch session landing eligibility (Story 22.4, FR-193 CAP-4).

Pure functions only: verification outcome and git facts judge whether a
dispatched story may land via existing Epic 4 machinery. Never land on
self-report without passing independent verification (Story 22.3).
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

from . import promotion
from .dispatch_verification import DispatchVerificationVerdict
from .model import Severity


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
    return verification_verdict == DispatchVerificationVerdict.VERIFIED and not story_merged_on_main


def refuse_unverified_landing(
    verification_verdict: DispatchVerificationVerdict,
) -> bool:
    """True when landing must be refused because verification did not pass."""
    return verification_verdict != DispatchVerificationVerdict.VERIFIED


def merge_subject_is_marshal_native(subject: str, template: str, project_slug: str) -> bool:
    """True when ``subject`` classifies marshal-native (FR-187 / Story 5.10)."""
    return bool(promotion.marshal_native_merged_keys((subject,), template, project_slug))


def landing_was_refused(landing_findings: tuple[Mapping[str, object], ...]) -> bool:
    """True when a dispatch landing's journaled findings include a refusal:
    an ERROR-severity finding. A WARN-only landing (MRS-DISP-047) is not a
    refusal (Story 56.1)."""
    return any(finding.get("severity") == Severity.ERROR for finding in landing_findings)


def landing_refusal_superseded(
    landing_findings: tuple[Mapping[str, object], ...],
    *,
    story_merged_on_main: bool,
) -> bool:
    """True when a dispatch landing was refused and its story has since
    landed on ``main`` by another route (Story 56.1, CAP-266).

    The refusal stays the journal's process fact (AD-5); this reports git's
    repository fact beside it (AD-33), never in place of it."""
    return story_merged_on_main and landing_was_refused(landing_findings)


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
    return f"_bmad-output/projects/{project_slug}/planning-artifacts/{SPRINT_LEDGER_BASENAME}"


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


def three_way_ledger_statuses(
    base: Mapping[str, str],
    main: Mapping[str, str],
    branch: Mapping[str, str],
) -> dict[str, str]:
    """Story 59.1 review: resolve two ledger maps against their merge base, row by row. A row
    only one side changed (added, re-statused or removed) takes that side; a row both sides
    changed alike takes it; a row one side removed and the other re-statused is kept; a row both
    re-statused differently takes ``done`` if either side finished it (``done`` never regresses
    -- ``ledger-regression`` reds that, and ``promote_sprint_status`` ranks ``done`` strictly
    senior to ``blocked``), else ``blocked`` if either side set it (un-blocking is the
    operator's, never a mechanical merge's -- AGENTS.md), else ``ledger_status_precedence``.
    A two-way union resurrected retired rows and undid the base's own changes."""
    out: dict[str, str] = {}
    for key in sorted(set(base) | set(main) | set(branch)):
        was, ours, theirs = base.get(key), main.get(key), branch.get(key)
        if ours == theirs:
            value = ours
        elif ours == was:
            value = theirs
        elif theirs == was:
            value = ours
        elif ours is None or theirs is None:
            value = ours if ours is not None else theirs
        elif "done" in (ours, theirs):
            value = "done"
        elif "blocked" in (ours, theirs):
            value = "blocked"
        else:
            value = ledger_status_precedence(ours, theirs)
        if value is not None:
            out[key] = value
    return out


def is_mechanical_conflict_path(path: str, *, ledger_rel: str | None = None) -> bool:
    """True when ``path`` is a known mechanical-only merge conflict. Given ``ledger_rel`` (the
    landing project's own ledger), only that exact path is mechanical -- another project's
    ledger is not this landing's to resolve (Story 59.1)."""
    normalized = path.replace("\\", "/")
    if ledger_rel is not None:
        return normalized == ledger_rel
    return normalized.endswith(f"planning-artifacts/{SPRINT_LEDGER_BASENAME}") or normalized.endswith(
        SPRINT_LEDGER_BASENAME
    )


def unknown_conflict_paths(paths: tuple[str, ...], *, ledger_rel: str | None = None) -> tuple[str, ...]:
    """Conflict paths that are not mechanical — must escalate, never merge."""
    return tuple(sorted(p for p in paths if not is_mechanical_conflict_path(p, ledger_rel=ledger_rel)))


# --- Story 51.11 (CAP-258): blocked-twin promotion --------------------------


def blocked_twin_promotion_text(*, primary_text: str | None, worktree_text: str) -> str | None:
    """Text to write onto the primary's tracked copy of a story spec when a
    dispatch worktree halts ``blocked`` with its commit uncommitted (Story
    51.11), or ``None`` when no write is needed.

    The promoted twin is byte-identical to the worktree's own blocked spec
    — the same story's tracked spec at two physical paths (Story 51.7's
    dispatch-branch/primary split) — never independently reconstructed.
    Returns ``None`` when the primary copy is unreadable (``primary_text``
    is ``None``: nothing to overwrite) or already carries this exact text
    (idempotent — a re-run promotes nothing a second time).
    """
    if primary_text is None or primary_text == worktree_text:
        return None
    return worktree_text
