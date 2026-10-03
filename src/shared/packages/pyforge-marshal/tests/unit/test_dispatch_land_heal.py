"""Unit tests for dispatch land healing (Story 28.20, CAP-4)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.adapters.vcs_git import GitVcs, VcsCommandError
from pyforge.marshal.core import dispatch_landing as _dispatch_landing
from pyforge.marshal.core.chain_regen import render_ledger_statuses
from pyforge.marshal.core.dispatch_landing import (
    is_deferred_work_path,
    is_mechanical_conflict_path,
    is_memlog_path,
    ledger_status_precedence,
    three_way_ledger_statuses,
    union_deferred_work_texts,
    union_memlog_texts,
    union_sprint_ledger_maps,
    unknown_conflict_paths,
)
from pyforge.marshal.core.egress import Redacted
from pyforge.marshal.core.model import Finding, Severity
from pyforge.marshal.dispatch_land_heal import (
    DispatchLandHealResult,
    try_heal_dispatch_land_merge,
)
from pyforge.marshal.ports.commit import VcsRef
from pyforge.marshal.ports.forge import ForgeCommandError, PrInfo


def test_ledger_status_precedence_done_beats_backlog() -> None:
    assert ledger_status_precedence("done", "backlog") == "done"
    assert ledger_status_precedence("backlog", "done") == "done"


def test_union_sprint_ledger_maps_preserves_done_from_both_sides() -> None:
    merged = union_sprint_ledger_maps(
        {"28-19-x": "done", "28-20-y": "backlog"},
        {"28-19-x": "backlog", "28-21-z": "done"},
    )
    assert merged["28-19-x"] == "done"
    assert merged["28-20-y"] == "backlog"
    assert merged["28-21-z"] == "done"


def test_mechanical_conflict_path_recognizes_sprint_ledger() -> None:
    path = "_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml"
    assert is_mechanical_conflict_path(path)
    assert not is_mechanical_conflict_path("src/pyforge/marshal/foo.py")


def test_unknown_conflict_paths_filters_mechanical_only() -> None:
    ledger = "_bmad-output/projects/acme/planning-artifacts/sprint-status-ledger.yaml"
    unknown = unknown_conflict_paths((ledger, "recipes/foo/recipe.yaml"))
    assert unknown == ("recipes/foo/recipe.yaml",)


class FakeVcsHeal:
    def __init__(
        self,
        *,
        conflict_paths: tuple[str, ...] = (),
        main_ledger: str = "",
        branch_ledger: str = "",
        conflict_paths_after_ledger: tuple[str, ...] | None = None,
    ) -> None:
        self.conflict_paths = conflict_paths
        self.conflict_paths_after_ledger = conflict_paths_after_ledger
        self.main_ledger = main_ledger
        self.branch_ledger = branch_ledger
        self.pushed: list[str] = []
        self.commits: list[tuple[Path, tuple[Path, ...], str]] = []
        self.merges: list[tuple[Path, str, dict[str, str], str]] = []
        self.merged: list[tuple[str, str, str]] = []
        self.deleted: list[str] = []
        self._head_sha = "abc111"
        self._merge_tree_calls = 0

    def merge_tree_conflict_paths(self, _repo_root: Path, _base: str, _branch: str):
        self._merge_tree_calls += 1
        if self._merge_tree_calls > 1 and self.conflict_paths_after_ledger is not None:
            return self.conflict_paths_after_ledger
        return self.conflict_paths

    def merge_base(self, _repo_root: Path, _a: str, _b: str) -> str:
        return "base000"

    def file_text_at_ref(self, _repo_root: Path, ref: str, path: str):
        if path.endswith("sprint-status-ledger.yaml"):
            if ref == "base000":
                return ""  # the merge base had no ledger rows: every row is one side's addition
            if ref == "refs/heads/main":
                return self.main_ledger
            return self.branch_ledger
        return None

    def commit_paths(self, repo_root: Path, paths: tuple[Path, ...], message: Redacted):
        self.commits.append((repo_root, paths, message.text))
        self._head_sha = "healed222"
        return self._head_sha

    def merge_ref_resolving(self, worktree_path: Path, ref: VcsRef, *, resolutions, message: Redacted) -> str:
        """Story 59.1: records the merge and writes each resolution, as the real adapter does."""
        self.merges.append((worktree_path, ref.value, dict(resolutions), message.text))
        for rel, text in resolutions.items():
            (worktree_path / rel).parent.mkdir(parents=True, exist_ok=True)
            (worktree_path / rel).write_text(text, encoding="utf-8")
        self._head_sha = "healed222"
        return self._head_sha

    def push(self, _repo_root: Path, branch: str) -> None:
        self.pushed.append(branch)

    def resolve_ref(self, _repo_root: Path, _ref: str) -> str:
        return self._head_sha

    def merge_branch(self, _repo_root: Path, branch: str, *, into: str, subject: str) -> str:
        self.merged.append((branch, into, subject))
        return "localmerge999"

    def delete_branch(self, _repo_root: Path, branch: str, *, force: bool = False) -> None:
        self.deleted.append(branch)


class FakeForgeHeal:
    def __init__(
        self,
        *,
        merge_state: str = "MERGEABLE",
        merge_fail_once: bool = False,
        merge_fail_always: bool = False,
    ) -> None:
        self.merge_state = merge_state
        self.merge_fail_once = merge_fail_once
        self.merge_fail_always = merge_fail_always
        self.merge_calls = 0
        self.closed: list[int] = []

    def pr_merge_state(self, _repo, number: int) -> str:
        return self.merge_state

    def merge_pr(self, _repo, number, strategy, *, expected_head_sha, delete_branch, subject):
        self.merge_calls += 1
        if self.merge_fail_always or (self.merge_fail_once and self.merge_calls == 1):
            raise ForgeCommandError("pull request is not mergeable")

    def close_pr(self, _repo, number: int) -> None:
        self.closed.append(number)


class FakeFsHeal:
    def write_text_atomic(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _ledger_yaml(*pairs: tuple[str, str]) -> str:
    lines = ["development_status:"]
    for key, status in pairs:
        lines.append(f"  {key}: {status}")
    lines.append("")
    return "\n".join(lines)


def test_heal_unions_ledger_only_conflict_and_retries_merge(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    ledger_rel = "_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml"
    vcs = FakeVcsHeal(
        conflict_paths=(ledger_rel,),
        main_ledger=_ledger_yaml(("28-19-x", "done")),
        branch_ledger=_ledger_yaml(("28-20-y", "backlog")),
    )
    forge = FakeForgeHeal()
    pr = PrInfo(number=985, url="https://example/pr/985", state="open", base="main")

    result = try_heal_dispatch_land_merge(
        project_slug="pyforge-marshal",
        git_repo_root=tmp_path,
        worktree=worktree,
        base="main",
        head_branch="dispatch/pyforge-marshal/28.20",
        head_sha="abc123",
        subject="Merge 28.20 into main",
        merge_strategy="merge",
        delete_branch=True,
        repo_ref=type("R", (), {"value": "rxm7706/local-recipes"})(),
        pr=pr,
        fs=FakeFsHeal(),
        vcs=vcs,
        forge=forge,
    )

    assert result == DispatchLandHealResult(healed=True, retried_forge_merge=True)
    assert vcs.pushed == ["dispatch/pyforge-marshal/28.20"]
    assert forge.merge_calls == 1
    # Story 59.1: the union is the resolution of a merge of the probe ref, never a lone commit.
    assert vcs.commits == []
    assert len(vcs.merges) == 1
    merged_into, merged_ref, resolutions, _message = vcs.merges[0]
    assert (merged_into, merged_ref, list(resolutions)) == (worktree, "refs/heads/main", [ledger_rel])
    written = (worktree / ledger_rel).read_text(encoding="utf-8")
    assert "28-19-x: done" in written
    assert "28-20-y: backlog" in written


def test_heal_advances_main_locally_when_merge_tree_clean_and_github_dirty(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = FakeVcsHeal(conflict_paths=())
    forge = FakeForgeHeal(merge_state="DIRTY")
    pr = PrInfo(number=985, url="https://example/pr/985", state="open", base="main")

    result = try_heal_dispatch_land_merge(
        project_slug="pyforge-marshal",
        git_repo_root=tmp_path,
        worktree=worktree,
        base="main",
        head_branch="dispatch/pyforge-marshal/28.20",
        head_sha="abc123",
        subject="Merge 28.20 into main",
        merge_strategy="merge",
        delete_branch=True,
        repo_ref=type("R", (), {"value": "rxm7706/local-recipes"})(),
        pr=pr,
        fs=FakeFsHeal(),
        vcs=vcs,
        forge=forge,
    )

    assert result == DispatchLandHealResult(healed=True, landed_via_local_merge=True)
    assert vcs.merged == [("refs/heads/dispatch/pyforge-marshal/28.20", "main", "Merge 28.20 into main")]
    assert vcs.pushed == ["main"]
    assert forge.closed == [985]
    assert vcs.deleted == ["dispatch/pyforge-marshal/28.20"]


def test_heal_never_advances_main_after_its_own_union_merge_fails_to_land(
    tmp_path: Path,
) -> None:
    """Story 59.1 review (high): this test once asserted the fall-through -- union pushed, forge
    retry refused, re-probe clean, stale DIRTY state -> merge into `main` and push it. With the
    union a real merge the re-probe is always clean, so that path would land the branch on
    `main` past whatever made the forge refuse. The attempt now ends; the next landing attempt
    reads a fresh state and may still take the #985 local advance."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    ledger_rel = "_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml"
    vcs = FakeVcsHeal(
        conflict_paths=(ledger_rel,),
        conflict_paths_after_ledger=(),
        main_ledger=_ledger_yaml(("28-19-x", "done")),
        branch_ledger=_ledger_yaml(("28-20-y", "backlog")),
    )
    forge = FakeForgeHeal(merge_state="DIRTY", merge_fail_always=True)
    pr = PrInfo(number=985, url="https://example/pr/985", state="open", base="main")

    result = try_heal_dispatch_land_merge(
        project_slug="pyforge-marshal",
        git_repo_root=tmp_path,
        worktree=worktree,
        base="main",
        head_branch="dispatch/pyforge-marshal/28.20",
        head_sha="abc123",
        subject="Merge 28.20 into main",
        merge_strategy="merge",
        delete_branch=True,
        repo_ref=type("R", (), {"value": "rxm7706/local-recipes"})(),
        pr=pr,
        fs=FakeFsHeal(),
        vcs=vcs,
        forge=forge,
    )

    assert result == DispatchLandHealResult(healed=False)
    assert vcs.pushed == ["dispatch/pyforge-marshal/28.20"]
    assert vcs.merged == []
    assert forge.closed == []


def test_heal_escalates_unknown_conflict_paths(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = FakeVcsHeal(conflict_paths=("recipes/foo/recipe.yaml",))
    forge = FakeForgeHeal(merge_state="CONFLICTING")
    pr = PrInfo(number=1, url="https://example/pr/1", state="open", base="main")

    result = try_heal_dispatch_land_merge(
        project_slug="pyforge-marshal",
        git_repo_root=tmp_path,
        worktree=worktree,
        base="main",
        head_branch="dispatch/pyforge-marshal/28.20",
        head_sha="abc123",
        subject="Merge 28.20 into main",
        merge_strategy="merge",
        delete_branch=False,
        repo_ref=type("R", (), {"value": "rxm7706/local-recipes"})(),
        pr=pr,
        fs=FakeFsHeal(),
        vcs=vcs,
        forge=forge,
    )

    assert result.healed is False
    assert result.escalated_paths == ("recipes/foo/recipe.yaml",)
    assert forge.merge_calls == 0


def test_heal_with_the_real_git_adapter_escalates_a_real_conflict_by_name(tmp_path: Path) -> None:
    """Story 58.1 (CAP-268): until 2026-09-27 the real adapter read every conflict as clean, so
    this path was only ever exercised through the fake above. With the real `GitVcs` a genuine
    conflict outside the sprint ledger is escalated naming its path, before the forge is asked."""
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)

    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "T")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    git("add", "README.md")
    git("commit", "-qm", "base")
    git("checkout", "-qb", "dispatch/pyforge-marshal/58.1")
    (repo / "README.md").write_text("branch\n", encoding="utf-8")
    git("commit", "-qam", "branch edits README")
    git("checkout", "-q", "main")
    (repo / "README.md").write_text("main\n", encoding="utf-8")
    git("commit", "-qam", "main edits README")
    forge = FakeForgeHeal(merge_state="CONFLICTING")

    result = try_heal_dispatch_land_merge(
        project_slug="pyforge-marshal",
        git_repo_root=repo,
        worktree=repo,
        base="main",
        head_branch="dispatch/pyforge-marshal/58.1",
        head_sha="unused",
        subject="Merge 58.1 into main",
        merge_strategy="merge",
        delete_branch=False,
        repo_ref=type("R", (), {"value": "rxm7706/local-recipes"})(),
        pr=PrInfo(number=58, url="https://example/pr/58", state="open", base="main"),
        fs=FakeFsHeal(),
        vcs=GitVcs(),
        forge=forge,
    )

    assert result == DispatchLandHealResult(healed=False, escalated_paths=("README.md",))
    assert forge.merge_calls == 0


# --- Story 59.1 (CAP-269): the union heal as a real merge of origin/main --------------------------

_LEDGER = "_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml"
_FOREIGN_LEDGER = "_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml"
_HEAD = "dispatch/pyforge-marshal/59.1"
_ORIGIN_MAIN = "refs/remotes/origin/main"


def _run_git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def _generated_ledger(*pairs: tuple[str, str]) -> str:
    return "# GENERATED — do not hand-edit.\ndevelopment_status:\n" + "".join(f"  {k}: {v}\n" for k, v in pairs)


class _HonestForge:
    """Merges only what GitHub would: a real `merge-tree --write-tree` of the remote's main and
    the pushed head must be clean. Anything else is the forge's not-mergeable error."""

    def __init__(self, clone: Path, *, refuse: bool = False) -> None:
        self.clone, self.refuse, self.merge_calls, self.closed = clone, refuse, 0, []

    def pr_merge_state(self, _repo, _number):
        return "CONFLICTING"

    def merge_pr(self, _repo, _number, _strategy, *, expected_head_sha, delete_branch, subject):
        self.merge_calls += 1
        if self.refuse:  # e.g. a required check went red on the new head
            raise ForgeCommandError("Required status check has not succeeded")
        _run_git(self.clone, "fetch", "-q", "origin")
        clean = subprocess.run(
            ["git", "-C", str(self.clone), "merge-tree", "--write-tree", _ORIGIN_MAIN, f"refs/remotes/origin/{_HEAD}"],
            capture_output=True,
            text=True,
        )
        if clean.returncode != 0:
            raise ForgeCommandError("Pull request is not mergeable: the merge commit cannot be cleanly created")

    def close_pr(self, _repo, number):
        self.closed.append(number)


def _landing(
    tmp_path: Path,
    *,
    base: dict[str, str],
    main: dict[str, str],
    branch: dict[str, str],
) -> tuple[Path, Path, Path]:
    """A bare remote, a clone (the landing's repo root) and a dispatch worktree on `_HEAD`: the
    branch commits `branch`'s files and is pushed; `main` then commits `main`'s and is pushed."""
    remote, clone, wt = tmp_path / "remote.git", tmp_path / "clone", tmp_path / "wt"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    subprocess.run(["git", "clone", "-q", str(remote), str(clone)], check=True, capture_output=True)
    _run_git(clone, "config", "user.email", "t@example.com")
    _run_git(clone, "config", "user.name", "T")

    def write(root: Path, files: dict[str, str]) -> None:
        for rel, text in files.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text, encoding="utf-8")

    write(clone, base)
    _run_git(clone, "add", "-A")
    _run_git(clone, "commit", "-qm", "base")
    _run_git(clone, "push", "-q", "origin", "main")
    _run_git(clone, "worktree", "add", "-q", "-b", _HEAD, str(wt), "main")
    write(wt, branch)
    _run_git(wt, "add", "-A")
    _run_git(wt, "commit", "-qm", "branch")
    _run_git(wt, "push", "-q", "-u", "origin", _HEAD)
    write(clone, main)
    _run_git(clone, "add", "-A")
    _run_git(clone, "commit", "-qm", "main moves on")
    _run_git(clone, "push", "-q", "origin", "main")
    _run_git(clone, "fetch", "-q", "origin")  # what dispatch land does right before the heal
    return remote, clone, wt


def _heal(clone: Path, wt: Path, forge: _HonestForge, *, await_checks=None) -> DispatchLandHealResult:
    return try_heal_dispatch_land_merge(
        project_slug="pyforge-marshal",
        git_repo_root=clone,
        worktree=wt,
        base="main",
        head_branch=_HEAD,
        head_sha="unused",
        subject="Merge 59.1 into main",
        merge_strategy="merge",
        delete_branch=False,
        repo_ref=type("R", (), {"value": "rxm7706/local-recipes"})(),
        pr=PrInfo(number=59, url="https://example/pr/59", state="open", base="main"),
        fs=FakeFsHeal(),
        vcs=GitVcs(),
        forge=forge,
        probe_ref=_ORIGIN_MAIN,
        await_checks=await_checks,
    )


def test_real_heal_merges_origin_main_when_both_sides_add_adjacent_ledger_rows(tmp_path: Path) -> None:
    """The case the single-parent union never cleared: two landings each mint a row."""
    remote, clone, wt = _landing(
        tmp_path,
        base={_LEDGER: _generated_ledger(("57-1-a", "done"), ("6-1-b", "done"))},
        main={_LEDGER: _generated_ledger(("57-1-a", "done"), ("58-1-x", "backlog"), ("6-1-b", "done"))},
        branch={_LEDGER: _generated_ledger(("57-1-a", "done"), ("59-1-y", "done"), ("6-1-b", "done"))},
    )
    forge = _HonestForge(clone)

    result = _heal(clone, wt, forge)

    assert result == DispatchLandHealResult(healed=True, retried_forge_merge=True)
    assert forge.merge_calls == 1
    pushed = _run_git(remote, "rev-parse", _HEAD).strip()
    parents = _run_git(clone, "rev-list", "--parents", "-n", "1", pushed).split()[1:]
    assert parents[1] == _run_git(clone, "rev-parse", _ORIGIN_MAIN).strip()  # a real merge of the base
    ledger = _run_git(clone, "show", f"{pushed}:{_LEDGER}")
    assert "58-1-x: backlog" in ledger and "59-1-y: done" in ledger
    assert ledger.startswith("# GENERATED")  # the base's header survives


def test_real_heal_resolves_a_same_row_conflict_to_the_precedence_winner(tmp_path: Path) -> None:
    remote, clone, wt = _landing(
        tmp_path,
        base={_LEDGER: _generated_ledger(("57-1-a", "backlog"))},
        main={_LEDGER: _generated_ledger(("57-1-a", "done"))},
        branch={_LEDGER: _generated_ledger(("57-1-a", "in-progress"))},
    )
    forge = _HonestForge(clone)

    assert _heal(clone, wt, forge) == DispatchLandHealResult(healed=True, retried_forge_merge=True)
    assert "57-1-a: done" in _run_git(remote, "show", f"{_HEAD}:{_LEDGER}")


def test_real_heal_escalates_a_conflict_beside_the_ledger_and_pushes_nothing(tmp_path: Path) -> None:
    remote, clone, wt = _landing(
        tmp_path,
        base={_LEDGER: _generated_ledger(("57-1-a", "backlog")), "README.md": "base\n"},
        main={_LEDGER: _generated_ledger(("57-1-a", "done")), "README.md": "main\n"},
        branch={_LEDGER: _generated_ledger(("57-1-a", "in-progress")), "README.md": "branch\n"},
    )
    head_before = _run_git(remote, "rev-parse", _HEAD).strip()
    forge = _HonestForge(clone)

    assert _heal(clone, wt, forge) == DispatchLandHealResult(healed=False, escalated_paths=("README.md",))
    assert forge.merge_calls == 0
    assert _run_git(remote, "rev-parse", _HEAD).strip() == head_before
    assert _run_git(wt, "status", "--porcelain") == ""


def test_real_heal_escalates_another_projects_ledger_by_name(tmp_path: Path) -> None:
    """Only the landing project's own ledger is mechanical; before Story 59.1 any path ending in
    the ledger's basename was, so this conflict was neither healed nor escalated."""
    remote, clone, wt = _landing(
        tmp_path,
        base={_FOREIGN_LEDGER: _generated_ledger(("1-1-s", "backlog"))},
        main={_FOREIGN_LEDGER: _generated_ledger(("1-1-s", "done"))},
        branch={_FOREIGN_LEDGER: _generated_ledger(("1-1-s", "in-progress"))},
    )
    head_before = _run_git(remote, "rev-parse", _HEAD).strip()
    forge = _HonestForge(clone)

    assert _heal(clone, wt, forge) == DispatchLandHealResult(healed=False, escalated_paths=(_FOREIGN_LEDGER,))
    assert _run_git(remote, "rev-parse", _HEAD).strip() == head_before


_ADJACENT = {
    "base": {_LEDGER: _generated_ledger(("57-1-a", "done"), ("6-1-b", "done"))},
    "main": {_LEDGER: _generated_ledger(("57-1-a", "done"), ("58-1-x", "backlog"), ("6-1-b", "done"))},
    "branch": {_LEDGER: _generated_ledger(("57-1-a", "done"), ("59-1-y", "done"), ("6-1-b", "done"))},
}


def test_real_heal_never_lands_on_main_when_the_retried_forge_merge_is_refused(tmp_path: Path) -> None:
    """Story 59.1 review (high), case A: the union merge is pushed, the forge still refuses (a red
    required check) -- the heal must end there, never push `main` itself or close the PR."""
    remote, clone, wt = _landing(tmp_path, **_ADJACENT)
    main_before = _run_git(remote, "rev-parse", "main").strip()
    forge = _HonestForge(clone, refuse=True)

    assert _heal(clone, wt, forge) == DispatchLandHealResult(healed=False)
    assert _run_git(remote, "rev-parse", "main").strip() == main_before
    assert forge.closed == []


def test_real_heal_never_lands_on_main_when_its_push_is_rejected(tmp_path: Path) -> None:
    """Case F: someone else pushed to the PR branch; the union merge's push is rejected as
    non-fast-forward -- `main` must not receive the local branch (it lacks their commit)."""
    remote, clone, wt = _landing(tmp_path, **_ADJACENT)
    tree = _run_git(clone, "rev-parse", f"refs/remotes/origin/{_HEAD}^{{tree}}").strip()
    theirs = _run_git(clone, "commit-tree", tree, "-p", f"refs/remotes/origin/{_HEAD}", "-m", "reviewer fix").strip()
    _run_git(clone, "push", "-q", "origin", f"{theirs}:refs/heads/{_HEAD}")
    main_before = _run_git(remote, "rev-parse", "main").strip()
    forge = _HonestForge(clone)

    assert _heal(clone, wt, forge) == DispatchLandHealResult(healed=False)
    assert _run_git(remote, "rev-parse", "main").strip() == main_before
    assert _run_git(remote, "rev-parse", _HEAD).strip() == theirs
    assert forge.merge_calls == 0 and forge.closed == []


def test_real_heal_keeps_mains_own_changes_to_rows_the_branch_never_touched(tmp_path: Path) -> None:
    """Review cases B and C: resolved against the merge base, `main`'s `blocked` flip and its
    retired row both survive -- a two-way union put the row back at `backlog` and resurrected
    the retired one."""
    remote, clone, wt = _landing(
        tmp_path,
        base={_LEDGER: _generated_ledger(("40-1-old", "done"), ("57-1-a", "backlog"), ("6-1-b", "done"))},
        main={_LEDGER: _generated_ledger(("57-1-a", "blocked"), ("58-1-x", "backlog"), ("6-1-b", "done"))},
        branch={
            _LEDGER: _generated_ledger(
                ("40-1-old", "done"), ("57-1-a", "backlog"), ("59-1-y", "done"), ("6-1-b", "done")
            )
        },
    )
    forge = _HonestForge(clone)

    assert _heal(clone, wt, forge) == DispatchLandHealResult(healed=True, retried_forge_merge=True)
    ledger = _run_git(remote, "show", f"{_HEAD}:{_LEDGER}")
    assert "57-1-a: blocked" in ledger
    assert "40-1-old" not in ledger
    assert "58-1-x: backlog" in ledger and "59-1-y: done" in ledger


def test_three_way_ledger_statuses_takes_the_changed_side_never_unfinishes_and_never_unblocks() -> None:
    base = {"a": "backlog", "b": "backlog", "gone": "done", "c": "in-progress", "d": "backlog", "e": "backlog"}
    main = {"a": "blocked", "b": "backlog", "c": "done", "d": "in-progress", "e": "blocked", "m": "backlog"}
    branch = {"a": "backlog", "b": "done", "gone": "done", "c": "blocked", "d": "done", "e": "review", "r": "done"}
    assert three_way_ledger_statuses(base, main, branch) == {
        "a": "blocked",  # only main changed it
        "b": "done",  # only the branch changed it
        "c": "done",  # both changed it: done never regresses (review 2 -- ledger-regression reds it)
        "d": "done",  # both changed it: precedence
        "e": "blocked",  # both changed it, neither done: blocked is never undone mechanically
        "m": "backlog",  # main added it
        "r": "done",  # the branch added it
    }  # "gone": main retired it, the branch left it alone


def test_three_way_ledger_statuses_keeps_a_row_one_side_removed_and_the_other_changed() -> None:
    assert three_way_ledger_statuses({"k": "backlog"}, {}, {"k": "done"}) == {"k": "done"}


def test_mechanical_paths_given_the_project_ledger_are_that_ledger_only() -> None:
    assert is_mechanical_conflict_path(_LEDGER, ledger_rel=_LEDGER)
    assert not is_mechanical_conflict_path(_FOREIGN_LEDGER, ledger_rel=_LEDGER)
    assert unknown_conflict_paths((_LEDGER, _FOREIGN_LEDGER), ledger_rel=_LEDGER) == (_FOREIGN_LEDGER,)


def test_render_ledger_statuses_keeps_the_template_header_and_sorts_the_map() -> None:
    template = "# GENERATED\n# note\ndevelopment_status:\n  9-1-z: done\n"
    assert render_ledger_statuses(template, {"b-2": "backlog", "a-1": "done"}) == (
        "# GENERATED\n# note\ndevelopment_status:\n  a-1: done\n  b-2: backlog\n"
    )
    assert render_ledger_statuses("", {"a-1": "done"}) == "development_status:\n  a-1: done\n"


# --- Story 78.1 (CAP-283): a landing unions append-only memlogs ------------------------------------

_MEMLOG = "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md"
_CO_MEMLOG = "_bmad-output/projects/pyforge-core/planning-artifacts/specs/spec-pyforge-core/.memlog.md"
_T0, _T1, _T2 = "2026-09-30T10:00", "2026-09-30T11:00", "2026-09-30T12:00"


def _memlog(*entries: str, updated: str = _T0, **fields: str) -> str:
    """A memlog in `_bmad/scripts/memlog.py`'s shape: `updated:` last, a blank line, the entries."""
    meta = {"topic": "Marshal", **fields, "updated": updated}
    head = "".join(f"{key}: {value}\n" for key, value in meta.items())
    return f"---\n{head}---\n\n" + "\n".join(entries) + "\n"


def test_is_memlog_path_reads_the_basename_in_any_project() -> None:
    assert is_memlog_path(_MEMLOG) and is_memlog_path(_CO_MEMLOG) and is_memlog_path(".memlog.md")
    assert is_memlog_path("a\\b\\.memlog.md")
    assert not is_memlog_path("specs/spec-x/memlog.md")
    assert not is_memlog_path("specs/spec-x/.memlog.md.bak")
    assert not is_memlog_path("specs/spec-x/SPEC.md")


def test_a_memlog_is_mechanical_beside_the_landing_ledger_only() -> None:
    assert is_mechanical_conflict_path(_MEMLOG, ledger_rel=_LEDGER)
    assert is_mechanical_conflict_path(_CO_MEMLOG, ledger_rel=_LEDGER)
    assert unknown_conflict_paths((_MEMLOG, _LEDGER, _FOREIGN_LEDGER, "README.md"), ledger_rel=_LEDGER) == (
        "README.md",
        _FOREIGN_LEDGER,
    )


_A, _M1, _M2, _B1, _B2 = ("- (event) a", "- (event) m1", "- (event) m2", "- (event) b1", "- (event) b2")
_NO_FENCE = "- (event) a\n"
_OPEN_FENCE = "---\ntopic: Marshal\n- (event) a\n"


@pytest.mark.parametrize(
    ("base", "main", "branch", "expected"),
    [
        pytest.param(  # both appended and restamped: main's frontmatter, its body, the branch's lines
            _memlog(_A, updated=_T0),
            _memlog(_A, _M1, _M2, updated=_T2),
            _memlog(_A, _B1, _B2, updated=_T1),
            _memlog(_A, _M1, _M2, _B1, _B2, updated=_T2),
            id="both-appended",
        ),
        pytest.param(  # the branch restamped later than main: `updated:` is the later stamp
            _memlog(_A, updated=_T0),
            _memlog(_A, _M1, updated=_T1),
            _memlog(_A, _B1, updated=_T2),
            _memlog(_A, _M1, _B1, updated=_T2),
            id="later-stamp-is-the-branchs",
        ),
        pytest.param(  # only the branch appended: the branch's text
            _memlog(_A, updated=_T0),
            _memlog(_A, updated=_T0),
            _memlog(_A, _B1, updated=_T1),
            _memlog(_A, _B1, updated=_T1),
            id="only-the-branch-appended",
        ),
        pytest.param(  # only main appended: main's text
            _memlog(_A, updated=_T0),
            _memlog(_A, _M1, updated=_T1),
            _memlog(_A, updated=_T0),
            _memlog(_A, _M1, updated=_T1),
            id="only-main-appended",
        ),
        pytest.param(  # a line both sides appended appears once, in main's position
            _memlog(_A, updated=_T0),
            _memlog(_A, _M1, _M2, updated=_T2),
            _memlog(_A, _M2, _B1, updated=_T1),
            _memlog(_A, _M1, _M2, _B1, updated=_T2),
            id="shared-line-appears-once",
        ),
        pytest.param(  # an entry the branch repeats on purpose is never dropped
            _memlog(_A, updated=_T0),
            _memlog(_A, _M1, updated=_T1),
            _memlog(_A, _M1, _M1, updated=_T1),
            _memlog(_A, _M1, _M1, updated=_T1),
            id="a-repeated-entry-is-kept",
        ),
        pytest.param(  # an empty base body: everything either side wrote is appended
            _memlog(updated=_T0),
            _memlog(_M1, updated=_T1),
            _memlog(_B1, updated=_T2),
            _memlog(_M1, _B1, updated=_T2),
            id="empty-base-body",
        ),
        pytest.param(  # a field only one side changed takes that side's value, whichever side
            _memlog(_A, updated=_T0, goal="g0", topic="t0"),
            _memlog(_A, _M1, updated=_T1, goal="g0", topic="t1"),
            _memlog(_A, _B1, updated=_T2, goal="g1", topic="t0"),
            _memlog(_A, _M1, _B1, updated=_T2, goal="g1", topic="t1"),
            id="a-field-only-one-side-changed",
        ),
        pytest.param(  # both sides changed a field to the same value
            _memlog(_A, updated=_T0, topic="t0"),
            _memlog(_A, _M1, updated=_T1, topic="t1"),
            _memlog(_A, _B1, updated=_T2, topic="t1"),
            _memlog(_A, _M1, _B1, updated=_T2, topic="t1"),
            id="a-field-both-changed-alike",
        ),
        pytest.param(  # a field only the branch added lands before `updated:`, which stays last
            _memlog(_A, updated=_T0),
            _memlog(_A, _M1, updated=_T1),
            _memlog(_A, _B1, updated=_T2, goal="lift retention"),
            _memlog(_A, _M1, _B1, updated=_T2, goal="lift retention"),
            id="a-field-the-branch-added",
        ),
        pytest.param(  # a rewritten base line, on the branch
            _memlog(_A, _M1, updated=_T0),
            _memlog(_A, _M1, _M2, updated=_T1),
            _memlog(_A, "- (event) m1 edited", _B1, updated=_T2),
            None,
            id="rewritten-by-the-branch",
        ),
        pytest.param(  # a rewritten base line, on main
            _memlog(_A, _M1, updated=_T0),
            _memlog(_A, "- (event) m1 edited", _M2, updated=_T1),
            _memlog(_A, _M1, _B1, updated=_T2),
            None,
            id="rewritten-by-main",
        ),
        pytest.param(  # a dropped trailing base line
            _memlog(_A, _M1, updated=_T0),
            _memlog(_A, _M1, _M2, updated=_T1),
            _memlog(_A, updated=_T2),
            None,
            id="truncated-body",
        ),
        pytest.param(  # a dropped base body altogether
            _memlog(_A, updated=_T0),
            _memlog(_A, _M1, updated=_T1),
            _memlog(updated=_T2),
            None,
            id="emptied-body",
        ),
        pytest.param(  # reordered base lines
            _memlog(_A, _M1, updated=_T0),
            _memlog(_A, _M1, _M2, updated=_T1),
            _memlog(_M1, _A, _B1, updated=_T2),
            None,
            id="reordered",
        ),
        pytest.param(  # a field both sides changed differently
            _memlog(_A, updated=_T0, topic="t0"),
            _memlog(_A, _M1, updated=_T1, topic="from main"),
            _memlog(_A, _B1, updated=_T2, topic="from branch"),
            None,
            id="topic-changed-differently",
        ),
        pytest.param(  # main removed a field the branch changed
            _memlog(_A, updated=_T0, goal="g0"),
            _memlog(_A, _M1, updated=_T1),
            _memlog(_A, _B1, updated=_T2, goal="g1"),
            None,
            id="removed-on-one-side-changed-on-the-other",
        ),
        pytest.param(_memlog(_A), _NO_FENCE, _memlog(_A, _B1), None, id="no-frontmatter-on-main"),
        pytest.param(_memlog(_A), _memlog(_A, _M1), _NO_FENCE, None, id="no-frontmatter-on-the-branch"),
        pytest.param(_NO_FENCE, _memlog(_A, _M1), _memlog(_A, _B1), None, id="no-frontmatter-in-the-base"),
        pytest.param(_memlog(_A), _OPEN_FENCE, _memlog(_A, _B1), None, id="unterminated-frontmatter"),
        pytest.param("", _memlog(_A, _M1), _memlog(_A, _B1), None, id="added-on-both-sides"),
    ],
)
def test_union_memlog_texts(base: str, main: str, branch: str, expected: str | None) -> None:
    assert union_memlog_texts(base, main, branch) == expected


def test_a_memlog_union_is_a_fixed_point_of_a_second_union() -> None:
    """Applying the same branch onto the union again adds nothing: no entry twice."""
    base = _memlog(_A, updated=_T0)
    main = _memlog(_A, _M1, updated=_T2)
    branch = _memlog(_A, _B1, updated=_T1)
    once = union_memlog_texts(base, main, branch)
    assert once is not None
    assert union_memlog_texts(base, once, branch) == once


def _entry_counts(text: str, *entries: str) -> list[int]:
    return [text.splitlines().count(entry) for entry in entries]


def _two_memlogs(*, main_entry: str = _M1, branch_entry: str = _B1) -> dict[str, dict[str, str]]:
    """Base, main and branch files for two memlogs: the landing's own and a co-governor's."""
    return {
        "base": {_MEMLOG: _memlog(_A, updated=_T0), _CO_MEMLOG: _memlog(_A, updated=_T0)},
        "main": {_MEMLOG: _memlog(_A, main_entry, updated=_T2), _CO_MEMLOG: _memlog(_A, main_entry, updated=_T2)},
        "branch": {_MEMLOG: _memlog(_A, branch_entry, updated=_T1), _CO_MEMLOG: _memlog(_A, branch_entry, updated=_T1)},
    }


def _assert_merge_of_origin_main(remote: Path, clone: Path) -> str:
    """The pushed head is a merge commit whose second parent is `origin/main`; returns its sha."""
    pushed = _run_git(remote, "rev-parse", _HEAD).strip()
    parents = _run_git(clone, "rev-list", "--parents", "-n", "1", pushed).split()[1:]
    assert len(parents) == 2
    assert parents[1] == _run_git(clone, "rev-parse", _ORIGIN_MAIN).strip()
    return pushed


def test_real_heal_unions_memlogs_both_sides_appended_to(tmp_path: Path) -> None:
    """The 2026-09-30 refusals: two stories each append to the same memlogs -- the landing's own
    Spec's and a co-governor's -- and restamp `updated:`. Both are healed in one merge."""
    remote, clone, wt = _landing(tmp_path, **_two_memlogs())
    forge = _HonestForge(clone)

    result = _heal(clone, wt, forge)

    assert result == DispatchLandHealResult(
        healed=True, retried_forge_merge=True, healed_memlog_paths=(_CO_MEMLOG, _MEMLOG)
    )
    assert forge.merge_calls == 1
    pushed = _assert_merge_of_origin_main(remote, clone)
    for rel in (_MEMLOG, _CO_MEMLOG):
        text = _run_git(clone, "show", f"{pushed}:{rel}")
        assert text == _memlog(_A, _M1, _B1, updated=_T2)
        assert _entry_counts(text, _A, _M1, _B1) == [1, 1, 1]
    assert _run_git(wt, "status", "--porcelain") == ""


def test_real_heal_unions_a_line_both_sides_appended_once(tmp_path: Path) -> None:
    remote, clone, wt = _landing(tmp_path, **_two_memlogs(main_entry=_M1, branch_entry=_M1))
    forge = _HonestForge(clone)

    result = _heal(clone, wt, forge)

    assert result == DispatchLandHealResult(
        healed=True, retried_forge_merge=True, healed_memlog_paths=(_CO_MEMLOG, _MEMLOG)
    )
    pushed = _assert_merge_of_origin_main(remote, clone)
    assert _entry_counts(_run_git(clone, "show", f"{pushed}:{_MEMLOG}"), _A, _M1) == [1, 1]


def test_real_heal_resolves_memlogs_and_the_ledger_in_the_same_merge(tmp_path: Path) -> None:
    files = _two_memlogs()
    remote, clone, wt = _landing(
        tmp_path,
        base={**files["base"], **_ADJACENT["base"]},
        main={**files["main"], **_ADJACENT["main"]},
        branch={**files["branch"], **_ADJACENT["branch"]},
    )
    forge = _HonestForge(clone)

    result = _heal(clone, wt, forge)

    assert result == DispatchLandHealResult(
        healed=True, retried_forge_merge=True, healed_memlog_paths=(_CO_MEMLOG, _MEMLOG)
    )
    assert forge.merge_calls == 1
    pushed = _assert_merge_of_origin_main(remote, clone)
    assert _run_git(clone, "rev-list", "--merges", "--count", f"{_ORIGIN_MAIN}..{pushed}").strip() == "1"
    ledger = _run_git(clone, "show", f"{pushed}:{_LEDGER}")
    assert "58-1-x: backlog" in ledger and "59-1-y: done" in ledger
    assert _entry_counts(_run_git(clone, "show", f"{pushed}:{_MEMLOG}"), _A, _M1, _B1) == [1, 1, 1]


def test_real_heal_unions_a_co_governor_memlog_alone(tmp_path: Path) -> None:
    """Only a co-governor's memlog conflicts, under another project: still mechanical."""
    remote, clone, wt = _landing(
        tmp_path,
        base={_CO_MEMLOG: _memlog(_A, updated=_T0)},
        main={_CO_MEMLOG: _memlog(_A, _M1, updated=_T2)},
        branch={_CO_MEMLOG: _memlog(_A, _B1, updated=_T1)},
    )

    result = _heal(clone, wt, _HonestForge(clone))

    assert result == DispatchLandHealResult(healed=True, retried_forge_merge=True, healed_memlog_paths=(_CO_MEMLOG,))


def test_real_heal_escalates_an_edited_memlog_by_name_and_pushes_nothing(tmp_path: Path) -> None:
    remote, clone, wt = _landing(
        tmp_path,
        base={_MEMLOG: _memlog(_A, _M1, updated=_T0), _CO_MEMLOG: _memlog(_A, updated=_T0)},
        main={_MEMLOG: _memlog(_A, _M1, _M2, updated=_T2), _CO_MEMLOG: _memlog(_A, _M1, updated=_T2)},
        branch={
            _MEMLOG: _memlog(_A, "- (event) m1 edited", updated=_T1),
            _CO_MEMLOG: _memlog(_A, _B1, updated=_T1),
        },
    )
    head_before = _run_git(remote, "rev-parse", _HEAD).strip()
    wt_head_before = _run_git(wt, "rev-parse", "HEAD").strip()
    forge = _HonestForge(clone)

    # only the edited memlog escalates: the co-governor's own is still append-only on both sides
    assert _heal(clone, wt, forge) == DispatchLandHealResult(healed=False, escalated_paths=(_MEMLOG,))
    assert forge.merge_calls == 0
    assert _run_git(remote, "rev-parse", _HEAD).strip() == head_before
    assert _run_git(wt, "rev-parse", "HEAD").strip() == wt_head_before
    assert _run_git(wt, "status", "--porcelain") == ""


def test_real_heal_escalates_a_memlog_added_on_both_sides(tmp_path: Path) -> None:
    remote, clone, wt = _landing(
        tmp_path,
        base={"README.md": "base\n"},
        main={_MEMLOG: _memlog(_M1, updated=_T2)},
        branch={_MEMLOG: _memlog(_B1, updated=_T1)},
    )
    head_before = _run_git(remote, "rev-parse", _HEAD).strip()

    assert _heal(clone, wt, _HonestForge(clone)) == DispatchLandHealResult(healed=False, escalated_paths=(_MEMLOG,))
    assert _run_git(remote, "rev-parse", _HEAD).strip() == head_before


def test_real_heal_escalates_a_conflict_beside_a_memlog_and_commits_nothing(tmp_path: Path) -> None:
    files = _two_memlogs()
    remote, clone, wt = _landing(
        tmp_path,
        base={**files["base"], "README.md": "base\n"},
        main={**files["main"], "README.md": "main\n"},
        branch={**files["branch"], "README.md": "branch\n"},
    )
    head_before = _run_git(remote, "rev-parse", _HEAD).strip()
    wt_head_before = _run_git(wt, "rev-parse", "HEAD").strip()
    forge = _HonestForge(clone)

    assert _heal(clone, wt, forge) == DispatchLandHealResult(healed=False, escalated_paths=("README.md",))
    assert forge.merge_calls == 0
    assert _run_git(remote, "rev-parse", _HEAD).strip() == head_before
    assert _run_git(wt, "rev-parse", "HEAD").strip() == wt_head_before
    assert _run_git(wt, "status", "--porcelain") == ""


def test_real_heal_names_both_the_other_file_and_the_edited_memlog(tmp_path: Path) -> None:
    remote, clone, wt = _landing(
        tmp_path,
        base={_MEMLOG: _memlog(_A, updated=_T0), "README.md": "base\n"},
        main={_MEMLOG: _memlog(_A, _M1, updated=_T2), "README.md": "main\n"},
        branch={_MEMLOG: _memlog("- (event) a edited", updated=_T1), "README.md": "branch\n"},
    )

    assert _heal(clone, wt, _HonestForge(clone)) == DispatchLandHealResult(
        healed=False, escalated_paths=("README.md", _MEMLOG)
    )


def test_real_heal_never_lands_on_main_when_a_memlog_heal_is_refused_by_the_forge(tmp_path: Path) -> None:
    """CAP-269's guarantee holds for a memlog heal: a refused retry leaves remote `main` untouched."""
    remote, clone, wt = _landing(tmp_path, **_two_memlogs())
    main_before = _run_git(remote, "rev-parse", "main").strip()
    forge = _HonestForge(clone, refuse=True)

    assert _heal(clone, wt, forge) == DispatchLandHealResult(healed=False)
    assert _run_git(remote, "rev-parse", "main").strip() == main_before
    assert forge.closed == []


class _UnreadableVcs(FakeVcsHeal):
    """A git read of the merge base or of a conflicted path fails mid-heal."""

    def __init__(self, *, fail_on: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._fail_on = fail_on

    def merge_base(self, repo_root: Path, a: str, b: str) -> str:
        if self._fail_on == "merge_base":
            raise VcsCommandError("git merge-base failed")
        return super().merge_base(repo_root, a, b)

    def file_text_at_ref(self, repo_root: Path, ref: str, path: str):
        if self._fail_on == "file_text_at_ref":
            raise VcsCommandError(f"git show {ref}:{path} failed")
        return super().file_text_at_ref(repo_root, ref, path)


@pytest.mark.parametrize("fail_on", ["merge_base", "file_text_at_ref"])
@pytest.mark.parametrize("conflicts", [(_MEMLOG,), (_LEDGER,), (_LEDGER, _MEMLOG)])
def test_heal_refuses_cleanly_when_a_resolution_read_fails(
    tmp_path: Path, conflicts: tuple[str, ...], fail_on: str
) -> None:
    """Story 78.1 review: the reads that feed the resolutions moved into their own helper and now
    cover every memlog. A failed git read is a refusal (`healed=False`, nothing merged or pushed,
    the forge never asked to merge) -- never an exception out of the heal, which `dispatch land`
    does not catch there."""
    vcs = _UnreadableVcs(fail_on=fail_on, conflict_paths=conflicts)
    forge = FakeForgeHeal(merge_state="CONFLICTING")

    result = try_heal_dispatch_land_merge(
        project_slug="pyforge-marshal",
        git_repo_root=tmp_path,
        worktree=tmp_path,
        base="main",
        head_branch=_HEAD,
        head_sha="unused",
        subject="Merge 78.1 into main",
        merge_strategy="merge",
        delete_branch=False,
        repo_ref=type("R", (), {"value": "rxm7706/local-recipes"})(),
        pr=PrInfo(number=78, url="https://example/pr/78", state="open", base="main"),
        fs=FakeFsHeal(),
        vcs=vcs,
        forge=forge,
        probe_ref=_ORIGIN_MAIN,
    )

    assert result == DispatchLandHealResult(healed=False)
    assert vcs.merges == [] and vcs.pushed == [] and vcs.commits == []
    assert forge.merge_calls == 0 and forge.closed == []


# --- Story 80.1 (CAP-284): the union heal waits for the head it pushes ------------------------------

_RED_FINDING = Finding(code="MRS-DISP-056", severity=Severity.ERROR, message="the pushed head has a red check run")


def _union_heal(tmp_path: Path, vcs: FakeVcsHeal, forge: FakeForgeHeal, **kwargs):
    worktree = tmp_path / "wt"
    worktree.mkdir(exist_ok=True)
    return try_heal_dispatch_land_merge(
        project_slug="pyforge-marshal",
        git_repo_root=tmp_path,
        worktree=worktree,
        base="main",
        head_branch="dispatch/pyforge-marshal/80.1",
        head_sha="abc123",
        subject="Merge 80.1 into main",
        merge_strategy="merge",
        delete_branch=True,
        repo_ref=type("R", (), {"value": "rxm7706/local-recipes"})(),
        pr=PrInfo(number=80, url="https://example/pr/80", state="open", base="main"),
        fs=FakeFsHeal(),
        vcs=vcs,
        forge=forge,
        **kwargs,
    )


def _ledger_conflict_vcs() -> FakeVcsHeal:
    return FakeVcsHeal(
        conflict_paths=(_LEDGER,),
        main_ledger=_ledger_yaml(("28-19-x", "done")),
        branch_ledger=_ledger_yaml(("28-20-y", "backlog")),
    )


def test_union_heal_hands_the_pushed_head_to_await_checks_before_the_retried_merge(tmp_path: Path) -> None:
    events: list[str] = []

    class _Forge(FakeForgeHeal):
        def merge_pr(self, _repo, number, strategy, *, expected_head_sha, delete_branch, subject):
            events.append(f"merge:{expected_head_sha.value}")

    def await_checks(sha: str) -> None:
        events.append(f"await:{sha}")

    result = _union_heal(tmp_path, _ledger_conflict_vcs(), _Forge(), await_checks=await_checks)

    assert result == DispatchLandHealResult(healed=True, retried_forge_merge=True)
    assert events == ["await:healed222", "merge:healed222"]  # the PUSHED union head, then its merge


def test_union_heal_merges_nothing_when_await_checks_refuses_and_reports_its_finding(tmp_path: Path) -> None:
    vcs, forge = _ledger_conflict_vcs(), FakeForgeHeal()

    result = _union_heal(tmp_path, vcs, forge, await_checks=lambda _sha: _RED_FINDING)

    assert result == DispatchLandHealResult(healed=False, checks_refusal=_RED_FINDING)
    assert result.checks_refusal is _RED_FINDING
    assert forge.merge_calls == 0  # no retried merge ...
    assert forge.closed == []  # ... and the PR stays open
    assert vcs.pushed == ["dispatch/pyforge-marshal/80.1"]  # the union head itself was pushed
    assert vcs.merged == []  # nor did the fallback advance `main`


def test_the_local_main_advance_takes_no_wait(tmp_path: Path) -> None:
    """It merges the SAME head the landing's pre-merge wait already cleared -- a second wait there
    would only delay it."""

    def await_checks(sha: str):
        raise AssertionError(f"the local-main advance must not wait ({sha})")

    result = _union_heal(
        tmp_path, FakeVcsHeal(conflict_paths=()), FakeForgeHeal(merge_state="DIRTY"), await_checks=await_checks
    )

    assert result == DispatchLandHealResult(healed=True, landed_via_local_merge=True)


def test_real_heal_pushes_the_union_head_but_never_merges_it_when_await_checks_refuses(tmp_path: Path) -> None:
    """Over real git: the head `await_checks` is asked about is the one on the remote, and a refusal
    leaves it there for CI -- a later landing merges it once green."""
    remote, clone, wt = _landing(tmp_path, **_ADJACENT)
    main_before = _run_git(remote, "rev-parse", "main").strip()
    forge = _HonestForge(clone)
    asked: list[str] = []

    def await_checks(sha: str) -> Finding:
        asked.append(sha)
        return _RED_FINDING

    result = _heal(clone, wt, forge, await_checks=await_checks)

    assert result == DispatchLandHealResult(healed=False, checks_refusal=_RED_FINDING)
    assert forge.merge_calls == 0 and forge.closed == []
    assert asked == [_run_git(remote, "rev-parse", _HEAD).strip()]
    assert _run_git(remote, "rev-parse", "main").strip() == main_before


def test_real_heal_merges_the_union_head_once_await_checks_clears_it(tmp_path: Path) -> None:
    remote, clone, wt = _landing(tmp_path, **_ADJACENT)
    forge = _HonestForge(clone)

    result = _heal(clone, wt, forge, await_checks=lambda _sha: None)

    assert result == DispatchLandHealResult(healed=True, retried_forge_merge=True)
    assert forge.merge_calls == 1


# --- Story 83.3: deferred-work ledger union ----------------------------------------------------------


def test_is_deferred_work_path_recognizes_deferred_work_ledger() -> None:
    assert is_deferred_work_path("_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md")
    assert is_deferred_work_path("_bmad-output/projects/pyforge-core/planning-artifacts/deferred-work-ledger.md")
    assert not is_deferred_work_path("src/pyforge/marshal/foo.py")
    assert not is_deferred_work_path("deferred-work.md")


def test_mechanical_conflict_path_recognizes_deferred_work_ledger() -> None:
    dw_path = "_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md"
    ledger_path = "_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml"

    assert is_mechanical_conflict_path(dw_path, deferred_work_rel=dw_path)
    assert is_mechanical_conflict_path(ledger_path, ledger_rel=ledger_path)
    assert not is_mechanical_conflict_path(dw_path, ledger_rel=ledger_path)  # Wrong type
    assert not is_mechanical_conflict_path("src/pyforge/marshal/foo.py", deferred_work_rel=dw_path)


def _deferred_work_text(
    *entries: str, frontmatter: str = "---\ndoc_type: deferred-work-ledger\n---\n\n# Deferred Work\n\n"
) -> str:
    """Create a deferred work ledger text with the given DW entries."""
    if entries:
        return frontmatter + "\n\n".join(entries) + "\n"
    else:
        return frontmatter.rstrip() + "\n"


def test_union_deferred_work_texts_both_sides_append_entries() -> None:
    """Both sides append new DW entries after the same base."""
    base = _deferred_work_text("### DW-1: Base entry\norigin: test\nstatus: open")
    main = _deferred_work_text(
        "### DW-1: Base entry\norigin: test\nstatus: open", "### DW-2: Main entry\norigin: main\nstatus: open"
    )
    branch = _deferred_work_text(
        "### DW-1: Base entry\norigin: test\nstatus: open", "### DW-3: Branch entry\norigin: branch\nstatus: open"
    )

    result = union_deferred_work_texts(base, main, branch)

    assert result is not None
    assert "### DW-1: Base entry" in result
    assert "### DW-2: Main entry" in result
    assert "### DW-3: Branch entry" in result
    # Entries should be in order: base, then main's additions, then branch's additions
    base_pos = result.find("### DW-1:")
    main_pos = result.find("### DW-2:")
    branch_pos = result.find("### DW-3:")
    assert base_pos < main_pos < branch_pos


def test_union_deferred_work_texts_only_branch_appends() -> None:
    """Only the branch side appends a new entry."""
    base = _deferred_work_text("### DW-1: Base entry\norigin: test\nstatus: open")
    main = base  # No changes on main
    branch = _deferred_work_text(
        "### DW-1: Base entry\norigin: test\nstatus: open", "### DW-2: Branch entry\norigin: branch\nstatus: open"
    )

    result = union_deferred_work_texts(base, main, branch)

    assert result is not None
    assert "### DW-1: Base entry" in result
    assert "### DW-2: Branch entry" in result


def test_union_deferred_work_texts_only_main_appends() -> None:
    """Only main side appends a new entry."""
    base = _deferred_work_text("### DW-1: Base entry\norigin: test\nstatus: open")
    main = _deferred_work_text(
        "### DW-1: Base entry\norigin: test\nstatus: open", "### DW-2: Main entry\norigin: main\nstatus: open"
    )
    branch = base  # No changes on branch

    result = union_deferred_work_texts(base, main, branch)

    assert result is not None
    assert "### DW-1: Base entry" in result
    assert "### DW-2: Main entry" in result
    assert "### DW-3:" not in result


def test_union_deferred_work_texts_both_add_same_entry() -> None:
    """Both sides add the same entry - should appear only once."""
    base = _deferred_work_text("### DW-1: Base entry\norigin: test\nstatus: open")
    same_entry = "### DW-2: Same entry\norigin: both\nstatus: open"
    main = _deferred_work_text("### DW-1: Base entry\norigin: test\nstatus: open", same_entry)
    branch = _deferred_work_text("### DW-1: Base entry\norigin: test\nstatus: open", same_entry)

    result = union_deferred_work_texts(base, main, branch)

    assert result is not None
    assert "### DW-1: Base entry" in result
    assert result.count("### DW-2: Same entry") == 1


def test_union_deferred_work_texts_refuses_edited_entry() -> None:
    """Should refuse when an existing entry is edited."""
    base = _deferred_work_text("### DW-1: Base entry\norigin: test\nstatus: open")
    main = _deferred_work_text("### DW-1: Base entry\norigin: test\nstatus: done")  # Status changed
    branch = _deferred_work_text(
        "### DW-1: Base entry\norigin: test\nstatus: open", "### DW-2: Branch entry\norigin: branch\nstatus: open"
    )

    result = union_deferred_work_texts(base, main, branch)

    assert result is None  # Should refuse


def test_union_deferred_work_texts_refuses_a_line_appended_to_the_last_entry_beside_a_main_append() -> None:
    """Both sides append, and the branch's suffix starts with a line added to the base's last entry:
    the whole-block union would drop that line, so it refuses (landing review, 2026-10-03)."""
    base = "### DW-1: Base entry\n\n- summary: s\n  status: open\n"
    main = base + "\n### DW-2: Main entry\n\n- summary: m\n  status: open\n"
    branch = base + "  verified: 2026-10-03 -- still open\n\n### DW-3: Branch entry\n\n- summary: b\n  status: open\n"

    assert union_deferred_work_texts(base, main, branch) is None


def test_union_deferred_work_texts_refuses_dropped_entry() -> None:
    """Should refuse when an entry is dropped."""
    base = _deferred_work_text(
        "### DW-1: First entry\norigin: test\nstatus: open", "### DW-2: Second entry\norigin: test\nstatus: open"
    )
    main = _deferred_work_text("### DW-1: First entry\norigin: test\nstatus: open")  # DW-2 dropped
    branch = _deferred_work_text(
        "### DW-1: First entry\norigin: test\nstatus: open",
        "### DW-2: Second entry\norigin: test\nstatus: open",
        "### DW-3: Branch entry\norigin: branch\nstatus: open",
    )

    result = union_deferred_work_texts(base, main, branch)

    assert result is None  # Should refuse


def test_union_deferred_work_texts_empty_base() -> None:
    """Handle case where base has no DW entries."""
    frontmatter = "---\ndoc_type: deferred-work-ledger\n---\n\n# Deferred Work\n\n"
    base = frontmatter
    main = _deferred_work_text("### DW-1: Main entry\norigin: main\nstatus: open", frontmatter=frontmatter)
    branch = _deferred_work_text("### DW-2: Branch entry\norigin: branch\nstatus: open", frontmatter=frontmatter)

    result = union_deferred_work_texts(base, main, branch)

    assert result is not None
    assert "### DW-1: Main entry" in result
    assert "### DW-2: Branch entry" in result


def _dw_block_count(text: str) -> int:
    return len(_dispatch_landing._opaque_dw_blocks(text)[1])


def test_union_deferred_work_texts_live_marshal_ledger_mixed_formats() -> None:
    """AC 2026-10-03: union on a copy of the real ledger preserves every base block and both appends."""
    repo_root = Path(__file__).resolve().parents[6]
    ledger_path = repo_root / "_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md"
    base = ledger_path.read_text(encoding="utf-8")
    base_count = _dw_block_count(base)

    main_append = "\n\n### DW-TEST-MAIN-83-3: Story 83.3 union probe (main)\norigin: test\nstatus: open\n"
    branch_append = (
        "\n\n### DW-TEST-BRANCH-83-3: Story 83.3 union probe (branch)\n"
        "- source_spec: `spec-83-3-the-landing-heal-unions-appended-deferred-work-rows-the-way-it-unions-memlog-entries.md`\n"
        "  status: open\n"
    )
    main = base.rstrip("\n") + main_append
    branch = base.rstrip("\n") + branch_append

    result = union_deferred_work_texts(base, main, branch)

    assert result is not None
    assert result.startswith(base.rstrip("\n"))
    assert _dw_block_count(result) == base_count + 2
    assert "DW-TEST-MAIN-83-3" in result
    assert "DW-TEST-BRANCH-83-3" in result


def test_union_deferred_work_texts_parallel_append_dedupes_shared_block() -> None:
    """Parallel branches from the same base: shared append once, branch-only row kept."""
    block_a = "### DW-A: Shared append\norigin: test\nstatus: open\n"
    block_b = "### DW-B: Branch-only append\norigin: test\nstatus: open\n"
    base = _deferred_work_text("### DW-1: Base entry\norigin: test\nstatus: open")
    main = base.rstrip("\n") + "\n\n" + block_a
    branch = base.rstrip("\n") + "\n\n" + block_a + "\n\n" + block_b

    result = union_deferred_work_texts(base, main, branch)

    assert result is not None
    assert result.count("### DW-A:") == 1
    assert "### DW-B:" in result


def test_union_deferred_work_texts_refuses_legacy_entry_edit_on_live_ledger() -> None:
    """AC 2026-10-03: editing a legacy ``## DW-`` entry while appending refuses union."""
    repo_root = Path(__file__).resolve().parents[6]
    ledger_path = repo_root / "_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md"
    base = ledger_path.read_text(encoding="utf-8")
    probe = "\n\n### DW-PROBE-83-3-LEGACY: union legacy-edit probe\norigin: test\nstatus: open\n"
    branch = base.rstrip("\n") + probe
    main = base.replace("status: open\n  severity: low", "status: closed\n  severity: low", 1)
    main = main.rstrip("\n") + probe

    assert union_deferred_work_texts(base, main, branch) is None


def test_union_deferred_work_texts_main_a_branch_a_b_exact_bytes() -> None:
    """AC 2026-10-03: shared append once, branch-only second row, one blank line between entries."""
    block_a = "### DW-A: Shared append\norigin: test\nstatus: open\n"
    block_b = "### DW-B: Branch-only append\norigin: test\nstatus: open\n"
    base = _deferred_work_text("### DW-1: Base entry\norigin: test\nstatus: open")
    main = base.rstrip("\n") + "\n\n" + block_a
    branch = main.rstrip("\n") + "\n\n" + block_b

    result = union_deferred_work_texts(base, main, branch)

    assert result is not None
    assert result.count("### DW-A:") == 1
    assert result.count("### DW-B:") == 1
    dw_b = result.index("### DW-B:")
    assert result[dw_b - 2 : dw_b] == "\n\n"
    assert result.startswith(base)
    assert block_a.strip() in result
    assert block_b.strip() in result


def test_mutation_union_deferred_work_texts_stub_none_refuses_append() -> None:
    """Mutation partner: a union that always returns None breaks the live-ledger append proof."""
    base = _deferred_work_text("### DW-1: Base entry\norigin: test\nstatus: open")
    main = _deferred_work_text(
        "### DW-1: Base entry\norigin: test\nstatus: open", "### DW-2: Main entry\norigin: main\nstatus: open"
    )
    branch = _deferred_work_text(
        "### DW-1: Base entry\norigin: test\nstatus: open", "### DW-3: Branch entry\norigin: branch\nstatus: open"
    )
    assert union_deferred_work_texts(base, main, branch) is not None


def test_unknown_conflict_paths_filters_deferred_work() -> None:
    """Test that unknown_conflict_paths properly filters deferred work ledgers."""
    dw_path = "_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md"
    ledger_path = "_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml"
    unknown_path = "src/pyforge/marshal/foo.py"

    unknown = unknown_conflict_paths(
        (dw_path, ledger_path, unknown_path), ledger_rel=ledger_path, deferred_work_rel=dw_path
    )

    assert unknown == (unknown_path,)


class FakeVcsHealWithDeferredWork(FakeVcsHeal):
    """Extended fake VCS that can handle deferred work ledger conflicts."""

    def __init__(
        self, *, deferred_work_base: str = "", deferred_work_main: str = "", deferred_work_branch: str = "", **kwargs
    ):
        super().__init__(**kwargs)
        self.deferred_work_base = deferred_work_base
        self.deferred_work_main = deferred_work_main
        self.deferred_work_branch = deferred_work_branch

    def file_text_at_ref(self, _repo_root: Path, ref: str, path: str):
        if path.endswith("deferred-work-ledger.md"):
            if ref == "base000":
                return self.deferred_work_base
            if ref == "refs/heads/main":
                return self.deferred_work_main
            return self.deferred_work_branch
        return super().file_text_at_ref(_repo_root, ref, path)


def test_heal_unions_deferred_work_ledger_conflict_and_retries_merge(tmp_path: Path) -> None:
    """Test that deferred work ledger conflicts are healed and merge is retried."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    dw_rel = "_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md"

    base_dw = _deferred_work_text("### DW-1: Base entry\norigin: test\nstatus: open")
    main_dw = _deferred_work_text(
        "### DW-1: Base entry\norigin: test\nstatus: open", "### DW-2: Main entry\norigin: main\nstatus: open"
    )
    branch_dw = _deferred_work_text(
        "### DW-1: Base entry\norigin: test\nstatus: open", "### DW-3: Branch entry\norigin: branch\nstatus: open"
    )

    vcs = FakeVcsHealWithDeferredWork(
        conflict_paths=(dw_rel,),
        deferred_work_base=base_dw,
        deferred_work_main=main_dw,
        deferred_work_branch=branch_dw,
    )
    forge = FakeForgeHeal()
    pr = PrInfo(number=831, url="https://example/pr/831", state="open", base="main")

    result = try_heal_dispatch_land_merge(
        project_slug="pyforge-marshal",
        git_repo_root=tmp_path,
        worktree=worktree,
        base="main",
        head_branch="dispatch/pyforge-marshal/83.3",
        head_sha="abc123",
        subject="Merge 83.3 into main",
        merge_strategy="merge",
        delete_branch=True,
        repo_ref=type("R", (), {"value": "rxm7706/local-recipes"})(),
        pr=pr,
        fs=FakeFsHeal(),
        vcs=vcs,
        forge=forge,
    )

    assert result == DispatchLandHealResult(healed=True, retried_forge_merge=True)
    assert vcs.pushed == ["dispatch/pyforge-marshal/83.3"]
    assert forge.merge_calls == 1
    assert len(vcs.merges) == 1
    merged_into, merged_ref, resolutions, _message = vcs.merges[0]
    assert (merged_into, merged_ref, list(resolutions)) == (worktree, "refs/heads/main", [dw_rel])

    # Check that the union was created correctly
    written = (worktree / dw_rel).read_text(encoding="utf-8")
    assert "### DW-1: Base entry" in written
    assert "### DW-2: Main entry" in written
    assert "### DW-3: Branch entry" in written


def test_heal_escalates_edited_deferred_work_entry(tmp_path: Path) -> None:
    """Test that editing existing deferred work entries escalates the conflict."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    dw_rel = "_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md"

    base_dw = _deferred_work_text("### DW-1: Base entry\norigin: test\nstatus: open")
    main_dw = _deferred_work_text("### DW-1: Base entry\norigin: test\nstatus: done")  # Status changed
    branch_dw = _deferred_work_text(
        "### DW-1: Base entry\norigin: test\nstatus: open", "### DW-2: Branch entry\norigin: branch\nstatus: open"
    )

    vcs = FakeVcsHealWithDeferredWork(
        conflict_paths=(dw_rel,),
        deferred_work_base=base_dw,
        deferred_work_main=main_dw,
        deferred_work_branch=branch_dw,
    )
    forge = FakeForgeHeal()
    pr = PrInfo(number=832, url="https://example/pr/832", state="open", base="main")

    result = try_heal_dispatch_land_merge(
        project_slug="pyforge-marshal",
        git_repo_root=tmp_path,
        worktree=worktree,
        base="main",
        head_branch="dispatch/pyforge-marshal/83.3",
        head_sha="abc123",
        subject="Merge 83.3 into main",
        merge_strategy="merge",
        delete_branch=True,
        repo_ref=type("R", (), {"value": "rxm7706/local-recipes"})(),
        pr=pr,
        fs=FakeFsHeal(),
        vcs=vcs,
        forge=forge,
    )

    assert result.healed is False
    assert result.escalated_paths == (dw_rel,)
    assert forge.merge_calls == 0


def test_heal_escalates_other_projects_deferred_work_ledger(tmp_path: Path) -> None:
    """Test that conflicts in another project's deferred work ledger are escalated."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    foreign_dw_rel = "_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md"

    vcs = FakeVcsHeal(conflict_paths=(foreign_dw_rel,))
    forge = FakeForgeHeal()
    pr = PrInfo(number=833, url="https://example/pr/833", state="open", base="main")

    result = try_heal_dispatch_land_merge(
        project_slug="pyforge-marshal",  # Different project
        git_repo_root=tmp_path,
        worktree=worktree,
        base="main",
        head_branch="dispatch/pyforge-marshal/83.3",
        head_sha="abc123",
        subject="Merge 83.3 into main",
        merge_strategy="merge",
        delete_branch=True,
        repo_ref=type("R", (), {"value": "rxm7706/local-recipes"})(),
        pr=pr,
        fs=FakeFsHeal(),
        vcs=vcs,
        forge=forge,
    )

    assert result.healed is False
    assert result.escalated_paths == (foreign_dw_rel,)
    assert forge.merge_calls == 0
