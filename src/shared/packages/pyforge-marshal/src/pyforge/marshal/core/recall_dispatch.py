"""Pure recall disposition for factory dispatch (Story 93.1).

Maps one fold attempt to the ``data["recall"]`` journal payload both engines
echo. Subprocess and filesystem work stay in ``adapters/`` (AD-4).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from . import recall_feedback
from .recall_feedback import RecallInjectionResult

__all__ = (
    "RecallDisposition",
    "disposition_for_layer_gate",
    "disposition_from_injection",
    "seed_recall_disposition",
)

_OUTCOME_NOT_REACHED = "not-reached"
_OUTCOME_DISABLED = "disabled"
_OUTCOME_NO_STATION = "no-station"
_OUTCOME_GROUNDED = "grounded"
_OUTCOME_MISS = "miss"
_OUTCOME_FAILED = "failed"


@dataclass(frozen=True)
class RecallDisposition:
    attempted: bool
    outcome: str
    reason: str | None = None
    cached: bool = False

    def journal_payload(self) -> dict[str, object]:
        return {
            "attempted": self.attempted,
            "outcome": self.outcome,
            "reason": self.reason,
            "cached": self.cached,
        }


def seed_recall_disposition() -> RecallDisposition:
    """Layer-off shape before the fold runs (Story 77.1 ``wire`` pattern)."""
    return RecallDisposition(attempted=False, outcome=_OUTCOME_NOT_REACHED)


def disposition_for_layer_gate(
    *,
    context_layers: Mapping[str, Mapping[str, object]],
    station_slug: str | None,
) -> RecallDisposition | None:
    """When the fold never runs, name why (disabled / no-station)."""
    if not recall_feedback.layer_enabled(context_layers.get(recall_feedback.RECALL_LAYER)):
        return RecallDisposition(attempted=False, outcome=_OUTCOME_DISABLED)
    if not station_slug:
        return RecallDisposition(attempted=False, outcome=_OUTCOME_NO_STATION)
    return None


def disposition_from_injection(
    injection: RecallInjectionResult | None,
    *,
    cached_block: bool,
) -> RecallDisposition:
    if injection is None or not injection.attempted:
        return seed_recall_disposition()
    if not injection.ok:
        return RecallDisposition(
            attempted=True,
            outcome=_OUTCOME_FAILED,
            reason=injection.reason,
            cached=False,
        )
    if injection.injected:
        return RecallDisposition(
            attempted=True,
            outcome=_OUTCOME_GROUNDED,
            cached=cached_block,
        )
    return RecallDisposition(attempted=True, outcome=_OUTCOME_MISS, cached=cached_block)
