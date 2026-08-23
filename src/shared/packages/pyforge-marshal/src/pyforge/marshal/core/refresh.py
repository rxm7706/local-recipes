"""``core/refresh.py`` (Story 15.1, FR-133..FR-135, AD-21) -- pure value
types for one fleet-homes refresh. No I/O: the CLI gathers facts via
``VcsPort`` / ``write_policy_toml`` and projects them into these shapes.

Each home reports three checked steps -- ``fast_forward``, ``push``,
``render_policy`` -- each ``done | skipped | failed`` (AD-21). A home whose
``fast_forward`` step is ``done`` but whose ``render_policy`` step is not
is ``incomplete`` (FR-135: FF-without-render).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

StepStatus = Literal["done", "skipped", "failed"]

STEP_FAST_FORWARD = "fast_forward"
STEP_PUSH = "push"
STEP_RENDER_POLICY = "render_policy"

_STEP_ORDER = (STEP_FAST_FORWARD, STEP_PUSH, STEP_RENDER_POLICY)


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
) -> tuple[RefreshStep, ...]:
    """Canonical step order for envelope / text output."""
    assert fast_forward.name == STEP_FAST_FORWARD
    assert push.name == STEP_PUSH
    assert render_policy.name == STEP_RENDER_POLICY
    return (fast_forward, push, render_policy)


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
        "steps": [
            {"name": s.name, "status": s.status, "detail": s.detail} for s in result.steps
        ],
    }
