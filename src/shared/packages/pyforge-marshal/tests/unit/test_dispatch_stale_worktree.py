"""Story 92.1: vanished worktree runs are stale, never LIVE, and never crash the guard."""

from __future__ import annotations

from pathlib import Path

from pyforge.marshal.cli.dispatch import (
    _compose_policy,
    gather_dispatch_journal_facts,
    resolve_dispatch_session_verdict,
    station_in_flight_conflict,
)
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core.dispatch_completion import DispatchSessionVerdict
from pyforge.marshal.core.journal import JournalEntryId, Phase, build_entry, prepare_for_write


class FakeFs:
    def read_text(self, path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None

    def exists(self, path: Path) -> bool:
        return path.exists()


class FakeVcs:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str):
        raise AssertionError("VcsCommandError must not be raised for stale runs")

    def is_branch_merged(self, repo_root: Path, branch: str, *, into: str, into_ref: str | None = None) -> bool:
        return False

    def commit_subjects(self, repo_root: Path, ref: str):
        return ()

    def worktree_head_sha(self, worktree_path: Path) -> str:
        raise AssertionError("VcsCommandError must not be raised for stale runs")


class ReusedPidProcess:
    def is_alive(self, pid: int) -> bool:
        return pid == 63830

    def process_start_time(self, pid: int) -> float | None:
        return None


def _seed_stale_run(tmp_path: Path, *, missing_worktree: Path) -> Path:
    slug = "pyforge-marshal"
    run_id = "pyforge-marshal-20261004T165202766Z-fc6ece35"
    run_dir = dispatch_core.dispatch_run_dir(tmp_path, slug, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 0),
            ts="2026-10-04T16:52:02.938Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.INTENT,
            payload={
                "story_key": "86.6",
                "worktree_path": str(missing_worktree),
                "baseline_head_sha": "deadbeef0001",
            },
        )
    ).line
    outcome = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 1),
            ts="2026-10-04T16:52:03.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 0),
            payload={"session_pid": 63830, "supervisor_pid": 63831},
        )
    ).line
    (run_dir / "journal.jsonl").write_text(intent + "\n" + outcome + "\n", encoding="utf-8")
    return run_dir


def test_vanished_worktree_is_never_live_and_guard_warns_not_refuses(tmp_path: Path) -> None:
    slug = "pyforge-marshal"
    missing = tmp_path / "gone-worktree"
    _seed_stale_run(tmp_path, missing_worktree=missing)
    run_dir = dispatch_core.dispatch_run_dir(tmp_path, slug, "pyforge-marshal-20261004T165202766Z-fc6ece35")
    journal = gather_dispatch_journal_facts(FakeFs(), run_dir, run_dir.name)
    policy = _compose_policy(slug)
    verdict = resolve_dispatch_session_verdict(
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        process=ReusedPidProcess(),
        repo_root=tmp_path,
        slug=slug,
        journal=journal,
        effective_policy=policy,
    )
    assert verdict != DispatchSessionVerdict.LIVE
    advisories: list = []
    conflict = station_in_flight_conflict(
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        process=ReusedPidProcess(),
        repo_root=tmp_path,
        slug=slug,
        story_key="92-1-candidate",
        effective_policy=policy,
        preflight_advisories=advisories,
    )
    assert conflict is None
    assert any(f.code == "MRS-DISP-064" for f in advisories)
    assert "86.6" in advisories[0].message
    assert "quarantine" in advisories[0].message.lower()
