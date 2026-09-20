"""Dispatch operator survival + timing (Story 22.6, FR-193 CAP-6).

Pure helpers: supervision state, timing payloads, unsupervised reconcile
from git facts. Attach/resume and journal writes live in ``cli/dispatch.py``
and ``dispatch_supervisor/__main__.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .dispatch import DispatchJournalFacts
from .dispatch_completion import (
    DispatchCompletionInput,
    DispatchGitFacts,
    DispatchSessionVerdict,
    has_git_progress,
    judge_dispatch_completion,
)


@dataclass(frozen=True)
class DispatchTimingRecord:
    """Per-story effort signal for Epic 23 (journal at-source producer)."""

    story_key: str
    story_started_at: str
    story_ended_at: str
    baseline_revision: str
    final_revision: str


@dataclass(frozen=True)
class DispatchSupervisionState:
    """Whether a dispatch run is supervised from journal + process facts."""

    session_alive: bool
    supervisor_alive: bool
    completion_verdict: DispatchSessionVerdict | None
    supervised: bool
    unsupervised_live: bool


def build_timing_record(
    *,
    story_key: str,
    story_started_at: str,
    story_ended_at: str,
    baseline_revision: str,
    final_revision: str,
) -> DispatchTimingRecord:
    return DispatchTimingRecord(
        story_key=story_key,
        story_started_at=story_started_at,
        story_ended_at=story_ended_at,
        baseline_revision=baseline_revision,
        final_revision=final_revision,
    )


def timing_record_payload(record: DispatchTimingRecord) -> dict[str, object]:
    return {
        "story_key": record.story_key,
        "story_started_at": record.story_started_at,
        "story_ended_at": record.story_ended_at,
        "baseline_revision": record.baseline_revision,
        "final_revision": record.final_revision,
    }


def derive_supervision_state(
    *,
    journal: DispatchJournalFacts,
    session_alive: bool,
    supervisor_alive: bool,
    git: DispatchGitFacts | None,
) -> DispatchSupervisionState:
    """Journal + process facts alone — terminal kill of the operator changes nothing."""
    if journal.completion_verdict in {
        DispatchSessionVerdict.COMPLETED.value,
        DispatchSessionVerdict.FAILED.value,
        DispatchSessionVerdict.STOPPED_EXTERNALLY.value,
        # Story 51.11 (CAP-258): a committed `blocked` verdict is terminal --
        # without this, a dead session with committed wip would re-derive as
        # LIVE (has_git_progress=True) and fleet tooling would think the run
        # is still unsupervised-live.
        DispatchSessionVerdict.BLOCKED.value,
    }:
        verdict = DispatchSessionVerdict(journal.completion_verdict)
        return DispatchSupervisionState(
            session_alive=session_alive,
            supervisor_alive=supervisor_alive,
            completion_verdict=verdict,
            supervised=supervisor_alive,
            unsupervised_live=False,
        )
    if git is not None:
        verdict = judge_dispatch_completion(DispatchCompletionInput(session_alive=session_alive, git=git))
    elif session_alive:
        verdict = DispatchSessionVerdict.LIVE
    else:
        verdict = None
    live = verdict == DispatchSessionVerdict.LIVE
    unsupervised = live and not supervisor_alive and (session_alive or (git is not None and has_git_progress(git)))
    return DispatchSupervisionState(
        session_alive=session_alive,
        supervisor_alive=supervisor_alive,
        completion_verdict=verdict,
        supervised=supervisor_alive and live,
        unsupervised_live=unsupervised,
    )


def reconcile_unsupervised_verdict(
    *,
    session_alive: bool,
    git: DispatchGitFacts,
) -> DispatchSessionVerdict:
    """Git facts reconcile completion the supervisor missed while unsupervised."""
    return judge_dispatch_completion(DispatchCompletionInput(session_alive=session_alive, git=git))


def format_entry_ts(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"
