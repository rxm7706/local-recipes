"""Stage-boundary push classification (Story 3.8, architecture spine
AD-46/FR-61): ``PushTrigger``/``classify_push_triggers`` -- the pure
function that turns two consecutive ``HarnessPort.run_status_snapshot``-
derived task readings into the set of stage boundaries a story crossed
between them.

Lives in ``supervisor/``, not ``core/`` (per this story's own Code Map --
distinct from ``core/supervise.py``'s ``evaluate_idle``/``evaluate_ceiling``/
``evaluate_escalation``, which share a module because they are all pure
decisions over ``RunStatusSnapshot``-shaped or clock-derived inputs
``supervisor/__main__.py`` alone consumes). This module is still pure in the
identical sense (AD-20): no port, no clock call, no I/O, no subprocess --
every value it needs is a fact the CALLER already gathered by reading
``HarnessPort.run_status_snapshot`` twice, once per tick. This is what lets
every transition be tested in milliseconds against synthetic
``TaskPhaseSnapshot`` mappings, with no real bmad-loop process or
``state.json`` anywhere near the test.

**Why diffing two consecutive snapshots, not a single-observation
classifier.** Mirrors ``evaluate_escalation``'s own Design Notes rationale
(see ``core/supervise.py``): a stage boundary is EDGE-triggered ("the review
verdict just got recorded" is only knowable by comparing against what was
true last tick), unlike ``evaluate_ceiling``'s level-triggered "is the
observed quantity past the limit right now". ``supervisor/__main__.py``
keeps the previous tick's ``Mapping[str, TaskPhaseSnapshot]`` and calls this
function every tick while ``watched_alive`` holds.

**Why the signature carries ``TaskPhaseSnapshot`` (phase AND
``commit_sha``), not the plain ``Mapping[str, str]`` of phases alone the
intent-contract's own Boundaries text names.** See the spec's own Spec
Change Log: ``dev-commit-landed`` is defined as "a story's ``commit_sha``
newly non-``None``", a fact a phase-only mapping cannot carry. Passing the
full per-task snapshot (mirroring ``RunStatusSnapshot.tasks``'s own shape)
lets one function classify all three boundaries from one pair of readings,
rather than needing a second, parallel ``Mapping[str, str | None]``
argument pair for commit shas alone.

**A story missing from the ``previous`` mapping entirely** (the first tick
this run's state was observed, or a story bmad-loop only just added to
``state.json``) is treated as "not previously in that boundary state" --
``previous.get(story_key)`` degrading to ``None`` reads as "phase ``None``,
``commit_sha`` ``None``", so a story already sitting in
``Phase.REVIEW_VERIFY``/``Phase.DONE`` (or already carrying a commit) the
FIRST time this run observes it still fires its trigger(s) exactly once --
the correct behaviour for a durability watcher: better one redundant push
than a missed one, and pushing an already-pushed branch is a no-op at the
git level.

**A story regressing phase** (which bmad-loop's own engine never does, but
this function must not crash on) produces no trigger for the boundary it
regressed FROM -- only forward crossings INTO ``review-verify``/``done``, or
``commit_sha`` newly non-``None``, are named. A phase moving OFF
``"done"``/``"review-verify"`` and back on again would re-fire (each crossing
is independent, per-tick), which is the correct reading of "every crossed
boundary in the interval is reported" (the spec's own Always bullet) --
this codebase does not special-case a shape bmad-loop's own engine never
produces.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from ..ports.harness import TaskPhaseSnapshot

#: The three named stage boundaries (AD-46), plus no fourth -- this is a
#: closed set, never a free-text reason class (mirrors ``LadderRung``/
#: ``CeilingStatus``/``EscalationStatus``'s own closed-``StrEnum``
#: convention in ``core/supervise.py``, spelled as a ``Literal`` here since
#: no caller needs to iterate or order these three).
PushBoundary = Literal[
    "review-verdict-recorded",
    "dev-commit-landed",
    "story-merged",
]

#: bmad-loop's own ``Phase`` string values this module compares against --
#: plain string literals, never an import of ``bmad_loop.model.Phase``
#: (AD-3 reserves that import for ``adapters/harness_bmadloop.py`` alone;
#: this mirrors ``adapters/harness_bmadloop.py::run_status_snapshot``'s own
#: "name a bmad-loop-owned raw value by its known-live shape" precedent).
_REVIEW_VERIFY_PHASE = "review-verify"
_DONE_PHASE = "done"


@dataclass(frozen=True)
class PushTrigger:
    """One story's crossing of one named stage boundary (Story 3.8,
    AD-46) -- a plain, frozen value type ``classify_push_triggers`` returns,
    mirroring ``core/supervise.py``'s own "facts the caller could not have
    known in advance" convention for its pure decisions' outputs.
    ``story_key`` is the task's own ``StoryTask.story_key`` (bmad-loop's
    native slug spelling, exactly ``TaskPhaseSnapshot.story_key``'s own
    convention -- the caller renders it via ``core.identity`` before
    journaling, mirroring every other harness-native key this package
    re-spells at its own journal boundary)."""

    story_key: str
    boundary: PushBoundary


def classify_push_triggers(
    previous: Mapping[str, TaskPhaseSnapshot],
    current: Mapping[str, TaskPhaseSnapshot],
) -> tuple[PushTrigger, ...]:
    """Pure: every stage boundary a story in ``current`` crossed since
    ``previous`` was observed (Story 3.8, AD-46/FR-61). No port, no clock
    call, no I/O -- both mappings are facts the CALLER already gathered, via
    two consecutive ``HarnessPort.run_status_snapshot`` reads (each keyed by
    ``TaskPhaseSnapshot.story_key``).

    Iterates ``current`` (a story absent from ``current`` -- e.g. removed
    from ``state.json``, which bmad-loop's own engine never does -- crosses
    no boundary by definition, since there is nothing to compare). For each
    story: ``previous.get(story_key)`` -- ``None`` if this story was not in
    the prior observation, read as "phase ``None``, ``commit_sha`` ``None``"
    (see this module's own docstring for why that is the correct default,
    not an error). Three independent checks, each producing at most one
    ``PushTrigger``, so a single story can cross MORE than one boundary in
    one diff (the spec's own edge-case matrix: ``commit_sha`` turning
    non-``None`` and phase reaching ``Phase.DONE`` in the same tick is the
    common shape against the installed bmad-loop 0.9.0 engine, not a bug):

    - ``"review-verdict-recorded"`` -- ``current.phase == "review-verify"``
      and ``previous`` was not.
    - ``"dev-commit-landed"`` -- ``current.commit_sha is not None`` and
      ``previous``'s was ``None``.
    - ``"story-merged"`` -- ``current.phase == "done"`` and ``previous`` was
      not.

    Returns triggers in ``current``'s own iteration order (``state.json``'s
    own ``tasks`` order, per ``TaskPhaseSnapshot``'s own docstring), each
    story's own three checks in the fixed order above -- deterministic, not
    that any caller depends on the ordering today."""
    triggers: list[PushTrigger] = []
    for story_key, current_task in current.items():
        previous_task = previous.get(story_key)
        previous_phase = previous_task.phase if previous_task is not None else None
        previous_commit_sha = (
            previous_task.commit_sha if previous_task is not None else None
        )

        if (
            current_task.phase == _REVIEW_VERIFY_PHASE
            and previous_phase != _REVIEW_VERIFY_PHASE
        ):
            triggers.append(PushTrigger(story_key, "review-verdict-recorded"))

        if current_task.commit_sha is not None and previous_commit_sha is None:
            triggers.append(PushTrigger(story_key, "dev-commit-landed"))

        if current_task.phase == _DONE_PHASE and previous_phase != _DONE_PHASE:
            triggers.append(PushTrigger(story_key, "story-merged"))

    return tuple(triggers)
