"""Classification of the check runs a forge reports on a commit (Story 80.1,
spec-pyforge-marshal CAP-284 / FR-231).

A dispatch landing waits for its PR head's check runs before it merges
(``dispatch_land.py``). This module is the pure half of that wait: given the
runs the forge reported at one instant, say whether they are green, red,
pending or absent. It owns no clock and no I/O (AD-4) -- the poll loop, the
sleeping and the forge read all live in ``dispatch_land.py``.

Every rung errs toward not merging (AD-8: a pending or unevaluable signal is
never passing):

- a run whose ``status`` is anything but ``completed`` is **pending**;
- a ``completed`` run is **green** only on ``success``, ``skipped`` or
  ``neutral`` -- any other conclusion (``failure``, ``cancelled``,
  ``timed_out``, ``action_required``, ``stale``, ``startup_failure``, a
  conclusion the forge adds tomorrow) and a ``completed`` run with NO
  conclusion are **red**;
- **red beats pending**: one run already red refuses at once, without
  waiting for the others to finish;
- no runs at all is its own state, **empty** -- never green here, because
  whether an empty set is acceptable is the caller's call (a head whose
  workflows have not registered yet is not a head with no checks).

``CheckRun`` lives here, not in ``ports/forge.py``, because ``ports/`` already
imports ``core/`` (``ports/forge.py`` imports ``..core.egress``) and never the
reverse.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

#: The only conclusions of a ``completed`` run that count as passing.
GREEN_CONCLUSIONS: frozenset[str] = frozenset({"success", "skipped", "neutral"})

#: The one ``status`` that carries a conclusion (the forge's own vocabulary).
COMPLETED_STATUS = "completed"


@dataclass(frozen=True)
class CheckRun:
    """One check run the forge reports on a commit: its ``name``, its
    ``status`` (``queued``/``in_progress``/``completed``/...) and its
    ``conclusion`` (``None`` until the run completes)."""

    name: str
    status: str
    conclusion: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError(f"name must be a non-empty str, got {self.name!r}")
        if not isinstance(self.status, str) or not self.status:
            raise ValueError(f"status must be a non-empty str, got {self.status!r}")
        if self.conclusion is not None and not isinstance(self.conclusion, str):
            raise ValueError(f"conclusion must be a str or None, got {self.conclusion!r}")

    def to_json_dict(self) -> dict[str, object]:
        """The plain-JSON form the landing journal records."""
        return {"name": self.name, "status": self.status, "conclusion": self.conclusion}


class CheckState(StrEnum):
    """The four things a set of check runs can be."""

    GREEN = "green"
    RED = "red"
    PENDING = "pending"
    EMPTY = "empty"


@dataclass(frozen=True)
class CheckVerdict:
    """The classification of one set of runs: its ``state``, plus the ``red``
    runs (non-empty only when ``state`` is ``RED``) and the ``pending`` runs
    (non-empty only when ``state`` is ``PENDING``, or ``RED`` with runs still
    unfinished)."""

    state: CheckState
    red: tuple[CheckRun, ...] = ()
    pending: tuple[CheckRun, ...] = ()


def classify_check_runs(runs: Iterable[CheckRun]) -> CheckVerdict:
    """Classify the check runs reported on a commit at one instant.

    ``EMPTY`` when there are none; otherwise ``RED`` when any run is
    ``completed`` with a conclusion outside ``GREEN_CONCLUSIONS`` (red beats
    pending), else ``PENDING`` when any run has not ``completed``, else
    ``GREEN``."""
    red: list[CheckRun] = []
    pending: list[CheckRun] = []
    seen = 0
    for run in runs:
        seen += 1
        if run.status != COMPLETED_STATUS:
            pending.append(run)
        elif run.conclusion not in GREEN_CONCLUSIONS:
            red.append(run)
    if seen == 0:
        return CheckVerdict(state=CheckState.EMPTY)
    if red:
        return CheckVerdict(state=CheckState.RED, red=tuple(red), pending=tuple(pending))
    if pending:
        return CheckVerdict(state=CheckState.PENDING, pending=tuple(pending))
    return CheckVerdict(state=CheckState.GREEN)
