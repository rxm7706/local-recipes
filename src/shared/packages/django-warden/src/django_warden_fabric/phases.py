"""Derived progress phases (Story 8.2) — monotonic by construction.

``_phase_guard`` ensures no phase chooses its own number: callers advance
only via ``advance(job)``, which increments ``phase_index`` within
``PHASES``. Progress percent = ``phase_index / len(PHASES)``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class PhaseJob(Protocol):
    phase_index: int

    def save(self, *, update_fields: list[str] | None = None) -> None: ...


PHASES: tuple[str, ...] = (
    "validate",
    "materialize",
    "scan",
    "sbom",
    "persist",
    "complete",
)


@dataclass(frozen=True)
class PhaseProgress:
    index: int
    name: str
    total: int

    @property
    def ratio(self) -> float:
        if self.total == 0:
            return 1.0
        return self.index / self.total


def current_progress(job: PhaseJob) -> PhaseProgress:
    idx = min(job.phase_index, len(PHASES))
    name = PHASES[idx - 1] if idx > 0 else "queued"
    if idx >= len(PHASES):
        name = PHASES[-1]
    return PhaseProgress(index=idx, name=name, total=len(PHASES))


def advance(job: PhaseJob, expected_next: str) -> PhaseProgress:
    """Advance exactly one phase.

    ``expected_next`` must match ``PHASES[job.phase_index]``.
    """
    if job.phase_index >= len(PHASES):
        msg = "job already complete; cannot advance"
        raise RuntimeError(msg)
    expected = PHASES[job.phase_index]
    if expected_next != expected:
        msg = (
            f"phase guard: expected {expected!r}, got {expected_next!r} "
            f"(no phase chooses its own number)"
        )
        raise RuntimeError(msg)
    job.phase_index += 1
    job.save(update_fields=["phase_index", "updated_at"])
    return current_progress(job)
