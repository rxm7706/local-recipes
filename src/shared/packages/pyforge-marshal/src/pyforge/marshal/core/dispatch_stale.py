"""Stale dispatch runs whose worktree vanished (Story 92.1, CAP-5/CAP-163)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..ports.fs import FsPort
from . import dispatch as dispatch_core
from .dispatch_completion import DispatchSessionVerdict
from .dispatch_supervisor_state import landing_journal_indicates_complete

_STALE_QUARANTINE_SUFFIX = "implementation-artifacts/dispatch-runs-quarantine/README.md"


@dataclass(frozen=True)
class DispatchStaleRun:
    run_id: str
    story_key: str
    worktree_path: str
    remedy: str


def _dispatch_stale_quarantine_remedy(slug: str) -> str:
    return (
        f"move the run dir to _bmad-output/projects/{slug}/"
        f"implementation-artifacts/dispatch-runs-quarantine/ and list it in "
        f"{_STALE_QUARANTINE_SUFFIX}; moving it back reverses it"
    )


def dispatch_run_is_stale(*, fs: FsPort, journal: dispatch_core.DispatchJournalFacts) -> bool:
    """True when the journaled worktree is gone and the run never finished landing."""
    if journal.worktree_path is None:
        return False
    if journal.completion_verdict in {
        DispatchSessionVerdict.COMPLETED.value,
        DispatchSessionVerdict.FAILED.value,
        DispatchSessionVerdict.STOPPED_EXTERNALLY.value,
        DispatchSessionVerdict.BLOCKED.value,
    }:
        return False
    if landing_journal_indicates_complete(journal.landing_verdict):
        return False
    worktree = Path(journal.worktree_path)
    exists = getattr(fs, "exists", None)
    if exists is not None:
        return not exists(worktree)
    return not worktree.exists()


def stale_dispatch_run(
    *,
    fs: FsPort,
    journal: dispatch_core.DispatchJournalFacts,
    run_id: str,
    slug: str,
) -> DispatchStaleRun | None:
    if journal.story_key is None or not dispatch_run_is_stale(fs=fs, journal=journal):
        return None
    assert journal.worktree_path is not None
    return DispatchStaleRun(
        run_id=run_id,
        story_key=journal.story_key,
        worktree_path=journal.worktree_path,
        remedy=_dispatch_stale_quarantine_remedy(slug),
    )


def stale_dispatch_run_payload(stale: DispatchStaleRun) -> dict[str, str]:
    return {
        "run_id": stale.run_id,
        "story_key": stale.story_key,
        "worktree_path": stale.worktree_path,
        "remedy": stale.remedy,
    }
