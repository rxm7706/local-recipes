"""Pure dispatch-supervisor tick helpers (hotfix 2026-09-01)."""

from __future__ import annotations

# Default: five supervisor ticks (~5 minutes at 60s) before forcing another
# land attempt when verify already passed but merge has not landed.
DEFAULT_STUCK_LAND_TICK_THRESHOLD = 5


def should_retry_stuck_land(
    *,
    verification_verdict: str | None,
    story_merged_on_main: bool,
    landing_journaled: bool,
    stuck_land_ticks: int,
    threshold: int = DEFAULT_STUCK_LAND_TICK_THRESHOLD,
) -> bool:
    return (
        verification_verdict == "verified"
        and not story_merged_on_main
        and not landing_journaled
        and stuck_land_ticks >= threshold
    )


def supervisor_should_exit(
    *,
    completion_verdict: str,
    story_merged_on_main: bool,
) -> bool:
    """Terminal states where the detached supervisor may stop heartbeating."""
    return story_merged_on_main or completion_verdict in {"completed", "failed"}
