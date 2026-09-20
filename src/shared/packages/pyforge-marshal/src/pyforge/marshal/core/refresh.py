"""``core/refresh.py`` (Story 15.1, FR-133..FR-135, AD-21) -- pure value
types for one fleet-homes refresh. No I/O: the CLI gathers facts via
``VcsPort`` / ``write_policy_toml`` and projects them into these shapes.

Each home reports four checked steps -- ``fast_forward``, ``push``,
``render_policy``, ``sync_status`` -- each ``done | skipped | failed``
(AD-21). A home whose ``fast_forward`` step is ``done`` but whose
``render_policy`` step is not is ``incomplete`` (FR-135: FF-without-render).

``sync_status`` (added alongside the harness_preference/tmux fixes,
2026-09-10) regenerates the station's Tier-3 ``sprint-status.yaml`` (the
file ``marshal factory spin``/``bmad-loop`` read for actionable stories)
from its tracked ``epics.md``. It is independent of the git fast-forward
outcome -- it writes to the SHARED physical
``_bmad-output/projects/<slug>/implementation-artifacts/`` location every
worktree symlinks to, not to the loop home itself -- so it runs even for a
dirty or fast-forward-failed home. Without it, ``sprint-status.yaml`` only
tracks whatever ``bmad-sprint-planning`` last wrote by hand and silently
drifts from the tracked ``sprint-status-ledger.yaml`` that
``marshal factory dispatch``/``bmad-build-auto`` read instead: live incident
2026-09-10, pyforge-mason's copy sat stale from 2026-09-06 (missing two
whole epics) while spin reported "0 done" every run with no error at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

StepStatus = Literal["done", "skipped", "failed"]

STEP_FAST_FORWARD = "fast_forward"
STEP_PUSH = "push"
STEP_RENDER_POLICY = "render_policy"
STEP_SYNC_STATUS = "sync_status"

_STEP_ORDER = (STEP_FAST_FORWARD, STEP_PUSH, STEP_RENDER_POLICY, STEP_SYNC_STATUS)


@dataclass(frozen=True)
class RefreshStep:
    """One checked step of a home's refresh (AD-21)."""

    name: str
    status: StepStatus
    detail: str = ""


@dataclass(frozen=True)
class HomeRefreshResult:
    """One loop home's refresh report (FR-133..FR-135).

    ``readable`` is False when the home could not be probed at all (behind-
    count unavailable) -- still present in the report, never silently
    omitted. ``incomplete`` is True when a fast-forward succeeded but the
    harness-policy re-render did not (FR-135).
    """

    slug: str
    path: str
    branch: str
    readable: bool
    behind_count: int | None
    current_ref: str | None
    steps: tuple[RefreshStep, ...]
    incomplete: bool
    refused_reason: str | None = None

    def step_map(self) -> dict[str, RefreshStep]:
        return {step.name: step for step in self.steps}


def is_incomplete_refresh(steps: tuple[RefreshStep, ...]) -> bool:
    """FR-135: FF succeeded without a successful policy re-render."""
    by_name = {step.name: step for step in steps}
    ff = by_name.get(STEP_FAST_FORWARD)
    render = by_name.get(STEP_RENDER_POLICY)
    if ff is None or render is None:
        return False
    return ff.status == "done" and render.status != "done"


def ordered_steps(
    *,
    fast_forward: RefreshStep,
    push: RefreshStep,
    render_policy: RefreshStep,
    sync_status: RefreshStep,
) -> tuple[RefreshStep, ...]:
    """Canonical step order for envelope / text output."""
    assert fast_forward.name == STEP_FAST_FORWARD
    assert push.name == STEP_PUSH
    assert render_policy.name == STEP_RENDER_POLICY
    assert sync_status.name == STEP_SYNC_STATUS
    return (fast_forward, push, render_policy, sync_status)


def home_result_to_dict(result: HomeRefreshResult) -> dict[str, object]:
    """JSON-safe projection of one home (AD-14)."""
    return {
        "slug": result.slug,
        "path": result.path,
        "branch": result.branch,
        "readable": result.readable,
        "behind_count": result.behind_count,
        "current_ref": result.current_ref,
        "incomplete": result.incomplete,
        "refused_reason": result.refused_reason,
        "steps": [{"name": s.name, "status": s.status, "detail": s.detail} for s in result.steps],
    }
