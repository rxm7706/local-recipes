"""Rule-engine and remote-sweep tests for scripts/worktree_sweep.py."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from pyforge.core.preserve_refs import PreserveTrailers, render_preserve_ref, tag_preserve
from pyforge.testing_kit.flags import flag_states

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import worktree_sweep as ws  # noqa: E402

SCRIPT = REPO_ROOT / "scripts" / "worktree_sweep.py"
PRESERVE_CORE = REPO_ROOT / "src" / "shared" / "packages" / "pyforge-core" / "src"

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


def test_list_worktrees_parses_agent_lock_reason(monkeypatch):
    porcelain = "\n".join(
        [
            "worktree /tmp/agent-wt",
            "HEAD deadbeef",
            "branch refs/heads/worktree-agent-abc",
            "locked claude agent agent-abc (pid 4242 start 100000)",
            "",
        ]
    )

    def fake_git(*args, cwd=None):
        if args[:2] == ("worktree", "list"):
            return porcelain, 0
        return "", 1

    monkeypatch.setattr(ws, "_git", fake_git)
    items = ws.list_worktrees()
    assert len(items) == 1
    assert items[0].locked
    assert items[0].lock_reason == "claude agent agent-abc (pid 4242 start 100000)"


def test_delete_merged_local_branches_dry_run_does_not_delete(monkeypatch):
    calls: list[list[str]] = []

    def fake_git(*args, cwd=None):
        calls.append(list(args))
        if args[:2] == ("branch", "--merged"):
            return "feature-x \n", 0
        if args[:2] == ("merge-base", "--is-ancestor"):
            return "", 0
        if args[:2] == ("branch", "-D"):
            raise AssertionError("dry report must not delete branches")
        return "", 0

    monkeypatch.setattr(ws, "_git", fake_git)
    deleted, _, _ = ws.delete_merged_local_branches(apply=False)
    assert deleted == 0
    assert not any(c[:2] == ["branch", "-D"] for c in calls)


def test_remove_orphan_dir_empty(tmp_path):
    d = tmp_path / "empty-orphan"
    d.mkdir()
    od = ws.OrphanDir(path=str(d), empty=True, verdict="ORPHAN-DIR")
    assert ws.remove_orphan_dir(od)
    assert not d.exists()


def test_locked_worktree_mutation():
    """Removing the stale-lock branch must change verdict (mutation guard)."""
    lookup = _lookup({4242: 100000})
    wt = _wt(locked=True, lock_reason=_AGENT_LOCK, merged=True)
    assert ws.verdict_for(wt, lookup=lookup)[0] == "KEEP"
    lookup_stale = _lookup({4242: None})
    assert ws.verdict_for(wt, lookup=lookup_stale)[0] == "STALE-LOCK"


# --- git + bare-remote fixtures (Story 87.1) ---------------------------------


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def bare_origin(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    return remote


@pytest.fixture
def clone(bare_origin: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo = tmp_path / "repo"
    subprocess.run(["git", "clone", "-q", str(bare_origin), str(repo)], check=True, capture_output=True)
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "T")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-qm", "base")
    _git(repo, "push", "-q", "origin", "main")
    (repo / "docs" / "governance").mkdir(parents=True)
    shutil.copy2(REPO_ROOT / "docs/governance/guild-roster.json", repo / "docs/governance/guild-roster.json")
    shutil.copy2(REPO_ROOT / "docs/governance/preserve-purge-list.json", repo / "docs/governance/preserve-purge-list.json")
    monkeypatch.setattr(ws, "REPO_ROOT", repo)
    monkeypatch.setattr(ws, "ROSTER_PATH", repo / "docs/governance/guild-roster.json")
    return repo


def _push_branch(repo: Path, name: str, *, merged: bool = False) -> str:
    _git(repo, "checkout", "-q", "main")
    _git(repo, "checkout", "-q", "-b", name)
    fname = name.replace("/", "-") + ".txt"
    (repo / fname).write_text(f"content for {name}\n", encoding="utf-8")
    _git(repo, "add", fname)
    _git(repo, "commit", "-qm", f"commit on {name}")
    sha = _git(repo, "rev-parse", "HEAD")
    _git(repo, "push", "-q", "origin", name)
    if merged:
        _git(repo, "checkout", "-q", "main")
        _git(repo, "merge", "-q", "--no-ff", name, "-m", f"merge {name}")
        _git(repo, "push", "-q", "origin", "main")
    else:
        _git(repo, "checkout", "-q", "main")
    return sha


def test_effective_protected_prefixes_unions_floor_with_roster():
    floor = ws.PROTECTED_CODE_FLOOR
    merged = ws.effective_protected_prefixes()
    assert floor <= merged
    assert "refs/heads/attempt-preserve/" in merged
    assert ws.is_protected_branch_name("loop/pyforge-marshal", protected_prefixes=merged)


def test_roster_omit_loop_still_protects_loop_branch():
    roster = {"protected_refs": [{"refname": "refs/heads/attempt-preserve/", "rules": ["deletion"]}]}
    prefixes = ws.effective_protected_prefixes(roster)
    assert ws.is_protected_branch_name("loop/x", protected_prefixes=prefixes)


def test_ruleset_refusal_names_loop_and_attempt_preserve():
    refusal = ws.ruleset_deletion_refusal("loop/pyforge-marshal")
    assert refusal is not None
    assert refusal[0] == "protected-refs-loop-branches"
    refusal2 = ws.ruleset_deletion_refusal("attempt-preserve/foo")
    assert refusal2 is not None
    assert refusal2[0] == "protected-refs-attempt-preserve-branches"


def test_remote_verdict_merged_ancestor_delete(clone: Path):
    sha = _push_branch(clone, "merged-feature", merged=True)
    rows = ws.classify_remote_branches(pr_reader=lambda _b: None)
    by_name = {r.branch: r for r in rows}
    assert by_name["merged-feature"].verdict == "DELETE"
    assert "ancestor" in by_name["merged-feature"].reason
    assert sha


def test_remote_verdict_protected_prefix_keep(clone: Path):
    _push_branch(clone, "loop/pyforge-marshal")
    rows = ws.classify_remote_branches(pr_reader=lambda _b: None)
    assert {r.branch: r.verdict for r in rows}["loop/pyforge-marshal"] == "KEEP"


def test_remote_verdict_open_pr_keep(clone: Path):
    _push_branch(clone, "feature-open-pr")

    def pr_reader(branch: str):
        if branch == "feature-open-pr":
            return {"state": "open", "head": branch}
        return None

    rows = ws.classify_remote_branches(pr_reader=pr_reader)
    assert {r.branch: r.verdict for r in rows}["feature-open-pr"] == "KEEP"


def test_remote_verdict_closed_pr_done_deletes(clone: Path):
    _push_branch(clone, "dispatch/pyforge-marshal/13-1-done")

    def pr_reader(branch: str):
        if branch == "dispatch/pyforge-marshal/13-1-done":
            return {"state": "closed", "head": branch}
        return None

    orig = ws.load_ledgers
    ws.load_ledgers = lambda: {"marshal": {"13-1": "done"}}  # type: ignore[method-assign, assignment]
    try:
        rows = ws.classify_remote_branches(pr_reader=pr_reader)
    finally:
        ws.load_ledgers = orig  # type: ignore[method-assign]
    assert {r.branch: r.verdict for r in rows}["dispatch/pyforge-marshal/13-1-done"] == "DELETE"


def test_remote_verdict_closed_pr_not_done_inspect(clone: Path):
    _push_branch(clone, "dispatch/pyforge-marshal/13-1-open")

    def pr_reader(branch: str):
        if branch == "dispatch/pyforge-marshal/13-1-open":
            return {"state": "closed", "head": branch}
        return None

    orig = ws.load_ledgers
    ws.load_ledgers = lambda: {"marshal": {"13-1": "backlog"}}  # type: ignore[method-assign, assignment]
    try:
        rows = ws.classify_remote_branches(pr_reader=pr_reader)
    finally:
        ws.load_ledgers = orig  # type: ignore[method-assign]
    row = {r.branch: r for r in rows}["dispatch/pyforge-marshal/13-1-open"]
    assert row.verdict == "INSPECT"
    assert "backlog" in row.reason


def test_remote_legacy_recover_prefix_keep_even_when_merged(clone: Path):
    _push_branch(clone, "recover/merged-branch", merged=True)
    rows = ws.classify_remote_branches(pr_reader=lambda _b: None)
    assert {r.branch: r.verdict for r in rows}["recover/merged-branch"] == "KEEP"


def test_github_pr_reader_uses_preloaded_states():
    reader = ws.github_pr_reader({"feature-x": {"state": "open", "head": "feature-x"}})
    assert reader("feature-x") == {"state": "open", "head": "feature-x"}
    assert reader("other") is None


def test_remote_execute_archive_twin_refusal_keeps_branch(clone: Path, tmp_path: Path, monkeypatch):
    _push_branch(clone, "orphan-delete-me", merged=False)

    def pr_reader(branch: str):
        if branch == "orphan-delete-me":
            return {"state": "merged", "head": branch}
        return None

    rows = ws.classify_remote_branches(pr_reader=pr_reader)

    def refuse_push(*_a, **_k):
        return ws.preserve_refs.PushPreserveResult(
            "refs/tags/archive/heads/orphan-delete-me",
            False,
            (ws.preserve_refs.ContentGateFinding(ws.preserve_refs.ContentGateReason.SIZE_CAP, "too big"),),
        )

    monkeypatch.setattr(ws.preserve_refs, "push_preserve_ref", refuse_push)
    findings, _ = ws.execute_remote_deletes(rows, apply=True, preserve_dir=tmp_path / "m")
    assert "refs/heads/orphan-delete-me" in _git(clone, "ls-remote", "--heads", "origin")
    assert any(f.code == "archive-twin-refused" for f in findings)


def test_remote_dry_run_does_not_delete(clone: Path):
    _push_branch(clone, "merged-x", merged=True)
    before = _git(clone, "ls-remote", "--heads", "origin")
    ws.execute_remote_deletes(ws.classify_remote_branches(pr_reader=lambda _b: None), apply=False, preserve_dir=clone / "preserve")
    after = _git(clone, "ls-remote", "--heads", "origin")
    assert before == after


def test_remote_execute_deletes_only_delete_verdicts(clone: Path, tmp_path: Path):
    _push_branch(clone, "to-delete", merged=True)
    _push_branch(clone, "to-keep-open")

    def pr_reader(branch: str):
        if branch == "to-keep-open":
            return {"state": "open", "head": branch}
        return None

    rows = ws.classify_remote_branches(pr_reader=pr_reader)
    preserve = tmp_path / "manifests"
    ws.execute_remote_deletes(rows, apply=True, preserve_dir=preserve)
    heads = _git(clone, "ls-remote", "--heads", "origin")
    assert "refs/heads/to-delete" not in heads
    assert "refs/heads/to-keep-open" in heads
    manifests = list(preserve.glob("remote-sweep-manifest-*.json"))
    assert manifests
    data = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert any(r["branch"] == "to-delete" for r in data["rows"])


def test_remote_execute_writes_archive_twin_before_orphan_delete(clone: Path, tmp_path: Path):
    sha = _push_branch(clone, "orphan-delete-me", merged=False)

    def pr_reader(branch: str):
        if branch == "orphan-delete-me":
            return {"state": "merged", "head": branch}
        return None

    rows = ws.classify_remote_branches(pr_reader=pr_reader)
    preserve = tmp_path / "manifests"
    ws.execute_remote_deletes(rows, apply=True, preserve_dir=preserve)
    assert "refs/heads/orphan-delete-me" not in _git(clone, "ls-remote", "--heads", "origin")
    tags = _git(clone, "ls-remote", "--tags", "origin")
    assert "refs/tags/archive/heads/orphan-delete-me" in tags
    assert sha[:8] in tags


def test_retire_ruleset_protected_refused(clone: Path, tmp_path: Path):
    _push_branch(clone, "loop/station-a")
    _push_branch(clone, "attempt-preserve/keep-me")
    rows, findings = ws.run_retire_branches(
        ["loop/station-a", "attempt-preserve/keep-me"],
        apply=False,
        preserve_dir=tmp_path / "m",
    )
    codes = {f.code for f in findings}
    assert "protected-refs-loop-branches" in codes
    assert "protected-refs-attempt-preserve-branches" in codes
    assert all(r.verdict == "REFUSE" for r in rows)


def test_retire_recovers_branch_with_archive_twin(clone: Path, tmp_path: Path):
    _push_branch(clone, "recover/wip-branch")
    rows, findings = ws.run_retire_branches(["recover/wip-branch"], apply=True, preserve_dir=tmp_path / "m")
    assert not findings
    assert rows[0].verdict == "RETIRE"
    assert "refs/heads/recover/wip-branch" not in _git(clone, "ls-remote", "--heads", "origin")
    tags = _git(clone, "ls-remote", "--tags", "origin")
    assert "refs/tags/archive/heads/recover/wip-branch" in tags


def test_retire_rejects_pattern_and_missing(clone: Path, tmp_path: Path):
    _, findings = ws.run_retire_branches(["loop/*"], apply=False, preserve_dir=tmp_path / "m")
    assert any(f.code == "invalid-name" for f in findings)
    _, findings2 = ws.run_retire_branches(["no-such-branch"], apply=False, preserve_dir=tmp_path / "m")
    assert any(f.code == "missing-branch" for f in findings2)


def test_remote_never_lists_tags_as_candidates(clone: Path):
    _git(clone, "tag", "-a", "v-test", "-m", "t", "main")
    _git(clone, "push", "-q", "origin", "v-test")
    rows = ws.classify_remote_branches(pr_reader=lambda _b: None)
    assert all(not r.branch.startswith("refs/tags/") for r in rows)


def test_mutation_remote_ancestor_rule():
    branch, sha = "b", "deadbeef"
    base = dict(
        pr_reader=lambda _b: None,
        checked_out=set(),
        dispatch_live=set(),
        ledgers={},
        protected_prefixes=ws.effective_protected_prefixes(),
    )

    def run():
        return ws.verdict_for_remote_branch(branch, sha, **base)[0]

    assert run() == "INSPECT"
    orig = ws.tip_is_ancestor_of_origin_main

    def always_yes(_tip):
        return True

    ws.tip_is_ancestor_of_origin_main = always_yes  # type: ignore[assignment]
    try:
        assert run() == "DELETE"
    finally:
        ws.tip_is_ancestor_of_origin_main = orig  # type: ignore[assignment]


def test_mutation_remote_open_pr_rule():
    branch, sha = "feature", "abc12345"

    def pr_open(b: str):
        return {"state": "open", "head": b} if b == branch else None

    v, _ = ws.verdict_for_remote_branch(
        branch,
        sha,
        pr_reader=pr_open,
        checked_out=set(),
        dispatch_live=set(),
        ledgers={},
        protected_prefixes=ws.effective_protected_prefixes(),
    )
    assert v == "KEEP"
    v2, _ = ws.verdict_for_remote_branch(
        branch,
        sha,
        pr_reader=lambda _b: None,
        checked_out=set(),
        dispatch_live=set(),
        ledgers={},
        protected_prefixes=ws.effective_protected_prefixes(),
    )
    assert v2 == "INSPECT"


def test_mutation_protected_floor():
    roster_empty = {"protected_refs": []}
    assert ws.is_protected_branch_name("loop/x", protected_prefixes=ws.effective_protected_prefixes(roster_empty))
    assert not ws.is_protected_branch_name("random/feature", protected_prefixes=frozenset())
