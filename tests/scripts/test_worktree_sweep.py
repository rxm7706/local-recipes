"""Rule-engine tests for scripts/worktree_sweep.py (pure helpers, no live /proc)."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import worktree_sweep as ws  # noqa: E402

_AGENT_LOCK = "claude agent agent-abc (pid 4242 start 100000)"


def _lookup(table: dict[int, int | None]):
    def fn(pid: int) -> int | None:
        return table.get(pid)

    return fn


def _wt(**kw) -> ws.Worktree:
    base = dict(path="/tmp/x", branch="marshal/3-1-thing", category="dispatch", exists=True, merged=True)
    base.update(kw)
    return ws.Worktree(**base)


def test_primary_and_loop_homes_are_never_swept():
    assert ws.verdict_for(_wt(category="primary"))[0] == "KEEP"
    assert ws.verdict_for(_wt(category="loop-home", dirty_files=["?? x"]))[0] == "KEEP"


def test_live_process_blocks_everything():
    assert ws.verdict_for(_wt(live_cwd=True))[0] == "KEEP"


def test_clean_ancestor_is_deletable():
    assert ws.verdict_for(_wt())[0] == "DELETE"


def test_missing_path_is_pruned():
    assert ws.verdict_for(_wt(exists=False))[0] == "PRUNE"


def test_done_story_with_pushed_branch_is_deletable_even_when_unmerged():
    wt = _wt(merged=False, unmerged_commits=2, ledger_status="done", branch_on_origin=True)
    assert ws.verdict_for(wt)[0] == "DELETE"


def test_done_story_not_on_origin_is_preserved_first():
    wt = _wt(merged=False, unmerged_commits=2, ledger_status="done", branch_on_origin=False)
    assert ws.verdict_for(wt)[0] == "PRESERVE-THEN-DELETE"


def test_live_story_is_kept():
    wt = _wt(merged=False, unmerged_commits=1, ledger_status="backlog", branch_on_origin=True)
    assert ws.verdict_for(wt)[0] == "KEEP"


def test_no_ledger_key_is_inspect():
    assert ws.verdict_for(_wt(merged=False, unmerged_commits=1, ledger_status="n/a"))[0] == "INSPECT"


def test_untracked_scratch_and_lock_churn_are_deletable():
    assert ws.verdict_for(_wt(dirty_files=["?? scratch/"]))[0] == "DELETE"
    assert ws.verdict_for(_wt(dirty_files=[" M pixi.lock"]))[0] == "DELETE"


def test_tracked_edits_on_done_story_are_preserved_first():
    wt = _wt(dirty_files=[" M src/a.py"], ledger_status="done")
    assert ws.verdict_for(wt)[0] == "PRESERVE-THEN-DELETE"
    assert ws.verdict_for(_wt(dirty_files=[" M src/a.py"], ledger_status="n/a"))[0] == "INSPECT"


def test_attempt_preserve_branch_keeps_branch_drops_worktree_only_when_pushed():
    assert ws.verdict_for(_wt(branch="attempt-preserve/2026-x", branch_on_origin=True))[0] == "DELETE-WORKTREE-KEEP-BRANCH"
    assert ws.verdict_for(_wt(branch="attempt-preserve/2026-x", branch_on_origin=False))[0] == "KEEP"


def test_station_and_story_key_mapping():
    assert ws.station_of("/x", "dispatch/pyforge-mason/13.1") == "mason"
    assert ws.story_key_of("dispatch/pyforge-mason/13.1") == "13-1"
    assert ws.story_key_of("bmad-loop/20260815-115702-0501/11-3-mechanically-checkable") == "11-3"
    assert ws.story_key_of("attempt-preserve/20260821-082415-mason-6-3-github") == "6-3"
    assert ws.story_key_of("marshal/story-10-7-seed-init") == "10-7"
    assert ws.story_key_of("worktree-agent-a66f8ac40fb74af2c") is None


def test_live_agent_lock_is_keep():
    lookup = _lookup({4242: 100000})
    wt = _wt(locked=True, lock_reason=_AGENT_LOCK, merged=True)
    assert ws.verdict_for(wt, lookup=lookup)[0] == "KEEP"


def test_stale_lock_dead_pid_is_stale_lock():
    lookup = _lookup({4242: None})
    wt = _wt(locked=True, lock_reason=_AGENT_LOCK, merged=True)
    v, reason = ws.verdict_for(wt, lookup=lookup)
    assert v == "STALE-LOCK"
    assert "not running" in reason
    assert "merged" in reason


def test_stale_lock_pid_reuse_is_stale_lock():
    lookup = _lookup({4242: 999999})
    wt = _wt(locked=True, lock_reason=_AGENT_LOCK, merged=False, unmerged_commits=1)
    v, reason = ws.verdict_for(wt, lookup=lookup)
    assert v == "STALE-LOCK"
    assert "start time" in reason
    assert "unmerged" in reason


def test_merged_stale_lock_is_executable_as_delete():
    wt = _wt(locked=True, lock_reason=_AGENT_LOCK, merged=True, verdict="STALE-LOCK")
    assert ws.effective_execute_verdict(wt) == "DELETE"


def test_unmerged_stale_lock_is_not_executable():
    wt = _wt(locked=True, lock_reason=_AGENT_LOCK, merged=False, verdict="STALE-LOCK")
    assert ws.effective_execute_verdict(wt) == "STALE-LOCK"


def test_non_agent_lock_stays_keep():
    lookup = _lookup({})
    wt = _wt(locked=True, lock_reason="manual lock", merged=True)
    assert ws.verdict_for(wt, lookup=lookup)[0] == "KEEP"


def test_orphan_empty_dir_verdict():
    od = ws.OrphanDir(path="/tmp/orphan", empty=True)
    assert ws.verdict_for_orphan(od) == ("ORPHAN-DIR", "empty unregistered worktree directory")


def test_orphan_nonempty_dir_is_inspect():
    od = ws.OrphanDir(path="/tmp/orphan", empty=False)
    assert ws.verdict_for_orphan(od)[0] == "INSPECT"


def test_orphan_scan_skips_registered(tmp_path, monkeypatch):
    root = tmp_path / "claude" / "worktrees"
    root.mkdir(parents=True)
    registered = {str((root / "agent-1").resolve())}
    (root / "agent-1").mkdir()
    (root / "agent-orphan").mkdir()
    monkeypatch.setattr(ws, "orphan_scan_roots", lambda: [root])
    orphans = ws.list_orphan_dirs(registered)
    assert len(orphans) == 1
    assert orphans[0].path.endswith("agent-orphan")


def test_bmad_loops_not_in_orphan_roots():
    roots = [str(p) for p in ws.orphan_scan_roots()]
    assert not any(str(ws.LOOP_HOMES_ROOT) in r for r in roots)


def test_locked_worktree_mutation():
    """Removing the stale-lock branch must change verdict (mutation guard)."""
    lookup = _lookup({4242: 100000})
    wt = _wt(locked=True, lock_reason=_AGENT_LOCK, merged=True)
    assert ws.verdict_for(wt, lookup=lookup)[0] == "KEEP"
    lookup_stale = _lookup({4242: None})
    assert ws.verdict_for(wt, lookup=lookup_stale)[0] == "STALE-LOCK"
