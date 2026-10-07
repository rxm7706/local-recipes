"""Unit tests for dispatch land healing (Story 28.20, CAP-4)."""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

import pytest
from pyforge.core.process import ProcessError, ProcessResult

from pyforge.marshal import dispatch_land
from pyforge.marshal.adapters.vcs_git import GitVcs, VcsCommandError
from pyforge.marshal.core import dispatch_landing as _dispatch_landing
from pyforge.marshal.core.chain_regen import render_ledger_statuses
from pyforge.marshal.core.dispatch_landing import (
    FLAG_REGISTRY_REL_PATHS,
    SPEC_SURFACE_BASELINE_REL,
    TEAM_MEMORY_INDEX_REL,
    is_deferred_work_path,
    is_flag_registry_path,
    is_mechanical_conflict_path,
    is_memlog_path,
    is_team_memory_index_path,
    ledger_status_precedence,
    specs_whose_baseline_entries_differ,
    three_way_ledger_statuses,
    union_deferred_work_texts,
    union_flag_registry_json_texts,
    union_flag_registry_python_texts,
    union_memlog_texts,
    union_sprint_ledger_maps,
    union_team_memory_index_texts,
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


# --- Story 83.11: team-memory index union -------------------------------------------------------------


def test_is_team_memory_index_path_recognizes_memory_md() -> None:
    assert is_team_memory_index_path(".claude/memory/MEMORY.md")
    assert is_team_memory_index_path(".claude\\memory\\MEMORY.md")
    assert not is_team_memory_index_path(".claude/memory/README.md")


def test_mechanical_conflict_path_recognizes_team_memory_index() -> None:
    ledger = "_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml"
    dw = "_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md"
    assert is_mechanical_conflict_path(TEAM_MEMORY_INDEX_REL, ledger_rel=ledger, deferred_work_rel=dw)
    assert not is_mechanical_conflict_path("src/pyforge/marshal/foo.py", ledger_rel=ledger, deferred_work_rel=dw)


def _memory_index_text(*feedback_extra: str, project_extra: str = "") -> str:
    feedback_body = "\n".join(["- [base-entry](feedback/base-entry.md) — base line", *feedback_extra])
    project_block = "## Project\n"
    if project_extra:
        project_block += f"\n{project_extra}\n"
    return (
        "# Team Memory Index\n\n"
        "Preamble stays fixed.\n\n"
        f"## Feedback\n\n{feedback_body}\n\n"
        f"{project_block}\n"
        "## Reference\n\n"
    )


_MAIN_INDEX_LINE = "- [main-83-11](feedback/main-83-11.md) — appended on main"
_BRANCH_INDEX_LINE = "- [branch-83-11](feedback/branch-83-11.md) — appended on branch"
_SAME_INDEX_LINE = "- [same-83-11](feedback/same-83-11.md) — both sides appended this"


def test_union_team_memory_index_texts_appends_in_same_section() -> None:
    base = _memory_index_text()
    main = _memory_index_text(_MAIN_INDEX_LINE)
    branch = _memory_index_text(_BRANCH_INDEX_LINE)
    result = union_team_memory_index_texts(base, main, branch)
    assert result is not None
    assert _MAIN_INDEX_LINE in result
    assert _BRANCH_INDEX_LINE in result
    assert result.index(_MAIN_INDEX_LINE) < result.index(_BRANCH_INDEX_LINE)


def test_union_team_memory_index_texts_dedupes_identical_appended_line() -> None:
    base = _memory_index_text()
    main = _memory_index_text(_SAME_INDEX_LINE)
    branch = _memory_index_text(_SAME_INDEX_LINE)
    result = union_team_memory_index_texts(base, main, branch)
    assert result is not None
    assert result.count(_SAME_INDEX_LINE) == 1


def test_union_team_memory_index_texts_refuses_edited_existing_line() -> None:
    base = _memory_index_text()
    main = _memory_index_text()
    branch_text = base.replace("base line", "edited line")
    assert union_team_memory_index_texts(base, main, branch_text) is None


def test_union_team_memory_index_texts_appends_to_different_sections() -> None:
    base = _memory_index_text()
    main = _memory_index_text(_MAIN_INDEX_LINE)
    branch = _memory_index_text(project_extra=_BRANCH_INDEX_LINE)
    result = union_team_memory_index_texts(base, main, branch)
    assert result is not None
    assert _MAIN_INDEX_LINE in result
    assert _BRANCH_INDEX_LINE in result


def _index_entry_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("- [")]


def _live_memory_index() -> str:
    repo_root = Path(__file__).resolve().parents[6]
    return (repo_root / ".claude" / "memory" / "MEMORY.md").read_text(encoding="utf-8")


def _section_insert_offset(text: str, heading: str) -> int:
    """Offset just past the newline ending the last non-blank line of ``heading``'s section."""
    start = text.index(f"## {heading}\n")
    next_h2 = text.find("\n## ", start)
    stop = len(text) if next_h2 == -1 else next_h2 + 1
    return start + len(text[start:stop].rstrip("\n")) + 1


def _preamble_insert_offset(text: str) -> int:
    """Offset just past the newline ending the last non-blank line before the first ``## ``."""
    first_h2 = text.index("\n## ") + 1
    return len(text[:first_h2].rstrip("\n")) + 1


def _insert_lines(text: str, offset: int, *lines: str) -> str:
    return text[:offset] + "".join(f"{line}\n" for line in lines) + text[offset:]


def _append_to_section(text: str, heading: str, *lines: str) -> str:
    return _insert_lines(text, _section_insert_offset(text, heading), *lines)


@pytest.mark.parametrize("heading", ["Feedback", "Project", "Reference"], ids=["first", "middle", "last-at-eof"])
def test_union_team_memory_index_texts_live_memory_md_parallel_appends(heading: str) -> None:
    """Stories 83.11 + 83.13 (AC1): base + main's line + the branch's line at the end of the section,
    every other byte -- each blank line around every ``## `` heading -- kept as it was."""
    base = _live_memory_index()
    assert base.endswith("\n")
    main_line = "- [union-probe-main-83-13](feedback/union-probe-main-83-13.md) — Story 83.13 live union probe (main)"
    branch_line = (
        "- [union-probe-branch-83-13](feedback/union-probe-branch-83-13.md) — Story 83.13 live union probe (branch)"
    )
    k = _section_insert_offset(base, heading)
    main = base[:k] + main_line + "\n" + base[k:]
    branch = base[:k] + branch_line + "\n" + base[k:]
    if heading != "Reference":
        assert main[k + len(main_line) + 1 :].startswith("\n## ")
    result = union_team_memory_index_texts(base, main, branch)
    assert result == base[:k] + main_line + "\n" + branch_line + "\n" + base[k:]
    assert result.count("\n\n## ") == base.count("\n\n## ")
    assert len(_index_entry_lines(result)) == len(_index_entry_lines(base)) + 2


def test_union_team_memory_index_texts_unchanged_returns_main_bytes() -> None:
    base = _memory_index_text()
    assert union_team_memory_index_texts(base, base, base) == base
    live = _live_memory_index()
    assert union_team_memory_index_texts(live, live, live) == live


def test_branch_preamble_append_is_kept() -> None:
    """Story 83.13 send-back (MEDIUM-3): a branch-only preamble line survives a main section append."""
    base = _live_memory_index()
    preamble_line = "Branch preamble line (Story 83.13)."
    main_line = "- [preamble-probe-main](feedback/preamble-probe-main.md) — main appends to Feedback"
    branch = _insert_lines(base, _preamble_insert_offset(base), preamble_line)
    main = _append_to_section(base, "Feedback", main_line)
    expected = _insert_lines(main, _preamble_insert_offset(main), preamble_line)
    assert union_team_memory_index_texts(base, main, branch) == expected


def test_union_team_memory_index_texts_branch_lines_in_two_sections() -> None:
    """Story 83.13 send-back (LOW-2): two branch lines in Feedback plus one in Project, main appending to
    Project -- each section's later ``## `` offsets must survive the earlier insert."""
    base = _live_memory_index()
    branch_lines = [f"- [multi-probe-{n}](feedback/multi-probe-{n}.md) — branch line {n}" for n in (1, 2, 3)]
    main_line = "- [multi-probe-main](feedback/multi-probe-main.md) — main appends to Project"
    branch = _append_to_section(_append_to_section(base, "Feedback", *branch_lines[:2]), "Project", branch_lines[2])
    assert union_team_memory_index_texts(base, base, branch) == branch
    main = _append_to_section(base, "Project", main_line)
    expected = _append_to_section(_append_to_section(main, "Feedback", *branch_lines[:2]), "Project", branch_lines[2])
    assert union_team_memory_index_texts(base, main, branch) == expected


@pytest.mark.parametrize("separator", ["\u2028", "\x0b", "\x1c", "\x85"], ids=["u2028", "x0b", "x1c", "x85"])
def test_union_team_memory_index_texts_keeps_non_newline_line_separators(separator: str) -> None:
    """Story 83.13 send-back (LOW-3): parsing splits on ``\\n`` only, like the reconstruction, so a line
    carrying a ``str.splitlines`` boundary comes back byte for byte (and never reads as a heading)."""
    base = _live_memory_index()
    odd_line = f"- [odd-probe](feedback/odd-probe.md) — odd{separator}tail{separator}## not a heading"
    main_line = "- [odd-probe-main](feedback/odd-probe-main.md) — main appends to Feedback"
    branch = _append_to_section(base, "Feedback", odd_line)
    assert union_team_memory_index_texts(base, base, branch) == branch
    main = _append_to_section(base, "Feedback", main_line)
    expected = _append_to_section(base, "Feedback", main_line, odd_line)
    assert union_team_memory_index_texts(base, main, branch) == expected


def test_mutation_union_team_memory_index_reconstruction_removed() -> None:
    """Re-rendering the index instead of reconstructing it from main's lines breaks this (Story 83.13 AC3)."""
    base = _memory_index_text()
    main = _memory_index_text(_MAIN_INDEX_LINE)
    branch = _memory_index_text(_BRANCH_INDEX_LINE)
    assert union_team_memory_index_texts(base, main, branch) == _memory_index_text(_MAIN_INDEX_LINE, _BRANCH_INDEX_LINE)


def test_mutation_mechanical_set_includes_team_memory_index() -> None:
    """Removing `.claude/memory/MEMORY.md` from the mechanical set breaks this test."""
    ledger = "_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml"
    dw = "_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md"
    assert is_mechanical_conflict_path(TEAM_MEMORY_INDEX_REL, ledger_rel=ledger, deferred_work_rel=dw)


def test_mutation_union_team_memory_index_texts_stub_none_refuses_append() -> None:
    base = _memory_index_text()
    main = _memory_index_text(_MAIN_INDEX_LINE)
    branch = _memory_index_text(_BRANCH_INDEX_LINE)
    assert union_team_memory_index_texts(base, main, branch) is not None


class FakeVcsHealWithTeamMemory(FakeVcsHeal):
    def __init__(
        self,
        *,
        memory_base: str = "",
        memory_main: str = "",
        memory_branch: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.memory_base = memory_base
        self.memory_main = memory_main
        self.memory_branch = memory_branch

    def file_text_at_ref(self, repo_root: Path, ref: str, path: str) -> str | None:
        if path == TEAM_MEMORY_INDEX_REL:
            if ref == "base000":
                return self.memory_base
            if ref == "refs/heads/main":
                return self.memory_main
            return self.memory_branch
        return super().file_text_at_ref(repo_root, ref, path)


def test_heal_unions_team_memory_index_conflict_and_retries_merge(tmp_path: Path) -> None:
    base = _memory_index_text()
    main = _memory_index_text(_MAIN_INDEX_LINE)
    branch = _memory_index_text(_BRANCH_INDEX_LINE)
    vcs = FakeVcsHealWithTeamMemory(
        conflict_paths=(TEAM_MEMORY_INDEX_REL,),
        memory_base=base,
        memory_main=main,
        memory_branch=branch,
    )
    forge = FakeForgeHeal()
    worktree = tmp_path / "wt"
    worktree.mkdir()
    pr = PrInfo(number=8311, url="https://example/pr/8311", state="open", base="main")

    result = try_heal_dispatch_land_merge(
        project_slug="pyforge-marshal",
        git_repo_root=tmp_path,
        worktree=worktree,
        base="main",
        head_branch="dispatch/pyforge-marshal/83.11",
        head_sha="abc123",
        subject="Merge 83.11 into main",
        merge_strategy="merge",
        delete_branch=True,
        repo_ref=type("R", (), {"value": "rxm7706/local-recipes"})(),
        pr=pr,
        fs=FakeFsHeal(),
        vcs=vcs,
        forge=forge,
    )

    assert result == DispatchLandHealResult(healed=True, retried_forge_merge=True)
    assert forge.merge_calls == 1
    written = (worktree / TEAM_MEMORY_INDEX_REL).read_text(encoding="utf-8")
    assert _MAIN_INDEX_LINE in written
    assert _BRANCH_INDEX_LINE in written


# --- Story 22.18: spec-surface baseline heal -------------------------------------------------------

_SPEC_A = "pyforge-marshal/spec-pyforge-marshal"
_SPEC_B = "pyforge-steward/spec-pyforge-steward"
_SPEC_C = "pyforge-core/spec-pyforge-core"
_MEMLOG_A = "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md"
_MEMLOG_C = "_bmad-output/projects/pyforge-core/planning-artifacts/specs/spec-pyforge-core/.memlog.md"


def _baseline_entry(memlog: str = "aaa") -> dict[str, object]:
    return {"files": {}, "memlog": memlog}


def _baseline_json(**specs: dict[str, object]) -> str:
    return json.dumps({name: entry for name, entry in specs.items()}, indent=1) + "\n"


def test_specs_whose_baseline_entries_differ_names_changed_specs_only() -> None:
    base = _baseline_json(
        alpha=_baseline_entry("1"),
        beta=_baseline_entry("2"),
    )
    branch = _baseline_json(
        alpha=_baseline_entry("1"),
        beta=_baseline_entry("3"),
        gamma=_baseline_entry("4"),
    )
    assert specs_whose_baseline_entries_differ(base, branch) == frozenset({"beta", "gamma"})


def test_mechanical_conflict_path_recognizes_spec_surface_baseline() -> None:
    ledger = "_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml"
    dw = "_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md"
    assert is_mechanical_conflict_path(SPEC_SURFACE_BASELINE_REL, ledger_rel=ledger, deferred_work_rel=dw)


def test_mutation_mechanical_set_includes_spec_surface_baseline() -> None:
    """Removing the baseline from the mechanical set breaks this test (Story 22.18 AC)."""
    ledger = "_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml"
    dw = "_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md"
    assert is_mechanical_conflict_path(SPEC_SURFACE_BASELINE_REL, ledger_rel=ledger, deferred_work_rel=dw)


def _22_18_landing(
    tmp_path: Path,
    *,
    branch_files: dict[str, str],
    main_files: dict[str, str],
    base_files: dict[str, str] | None = None,
) -> tuple[Path, Path, Path]:
    base = base_files or {
        SPEC_SURFACE_BASELINE_REL: _baseline_json(
            **{
                _SPEC_A: _baseline_entry("base"),
                _SPEC_B: _baseline_entry("base"),
                _SPEC_C: _baseline_entry("base"),
            }
        ),
        _MEMLOG_A: _memlog(_A, updated=_T0),
        _MEMLOG_C: _memlog(_A, updated=_T0),
    }
    branch = {**base, **branch_files}
    main = {**base, **main_files}
    return _landing(tmp_path, base=base, main=main, branch=branch)


class _RecordingReconcile:
    def __init__(self, *, refuse: bool = False, finding: Finding | None = None) -> None:
        self.calls: list[tuple[frozenset[str], bool]] = []
        self.refuse = refuse
        self.finding = finding

    def __call__(self, *, branch_stamp_specs: frozenset[str], push_when_done: bool):
        self.calls.append((branch_stamp_specs, push_when_done))

        class _Outcome:
            pass

        outcome = _Outcome()
        outcome.refuse = self.refuse
        outcome.finding = self.finding or (
            Finding(code="MRS-DISP-048", severity=Severity.ERROR, message="reconcile refused") if self.refuse else None
        )
        return outcome


def test_heal_escalates_baseline_conflict_without_reconcile(tmp_path: Path) -> None:
    """Direct callers with no reconcile still get MRS-DISP-038 on the baseline."""
    _, clone, wt = _22_18_landing(
        tmp_path,
        branch_files={
            SPEC_SURFACE_BASELINE_REL: _baseline_json(
                **{
                    _SPEC_A: _baseline_entry("branch"),
                    _SPEC_B: _baseline_entry("base"),
                    _SPEC_C: _baseline_entry("branch"),
                }
            ),
            _MEMLOG_A: _memlog(_A, _B1, updated=_T1),
            _MEMLOG_C: _memlog(_A, _B1, updated=_T1),
        },
        main_files={
            SPEC_SURFACE_BASELINE_REL: _baseline_json(
                **{
                    _SPEC_A: _baseline_entry("base"),
                    _SPEC_B: _baseline_entry("main"),
                    _SPEC_C: _baseline_entry("main"),
                }
            ),
        },
    )
    head_before = _run_git(clone, "rev-parse", _HEAD).strip()
    forge = _HonestForge(clone)

    result = _heal(clone, wt, forge)

    assert result == DispatchLandHealResult(healed=False, escalated_paths=(SPEC_SURFACE_BASELINE_REL,))
    assert forge.merge_calls == 0
    assert _run_git(clone, "rev-parse", _HEAD).strip() == head_before


def test_heal_resolves_baseline_to_main_and_calls_reconcile_once_before_push(tmp_path: Path) -> None:
    _, clone, wt = _22_18_landing(
        tmp_path,
        branch_files={
            SPEC_SURFACE_BASELINE_REL: _baseline_json(
                **{
                    _SPEC_A: _baseline_entry("branch"),
                    _SPEC_B: _baseline_entry("base"),
                    _SPEC_C: _baseline_entry("branch"),
                }
            ),
            _MEMLOG_A: _memlog(_A, _B1, updated=_T1),
            _MEMLOG_C: _memlog(_A, _B1, updated=_T1),
        },
        main_files={
            SPEC_SURFACE_BASELINE_REL: _baseline_json(
                **{
                    _SPEC_A: _baseline_entry("base"),
                    _SPEC_B: _baseline_entry("main"),
                    _SPEC_C: _baseline_entry("main"),
                }
            ),
        },
    )
    forge = _HonestForge(clone)
    reconcile = _RecordingReconcile()

    result = try_heal_dispatch_land_merge(
        project_slug="pyforge-marshal",
        git_repo_root=clone,
        worktree=wt,
        base="main",
        head_branch=_HEAD,
        head_sha="unused",
        subject="Merge 22.18 into main",
        merge_strategy="merge",
        delete_branch=False,
        repo_ref=type("R", (), {"value": "rxm7706/local-recipes"})(),
        pr=PrInfo(number=2218, url="https://example/pr/2218", state="open", base="main"),
        fs=FakeFsHeal(),
        vcs=GitVcs(),
        forge=forge,
        probe_ref=_ORIGIN_MAIN,
        reconcile_spec_surface=reconcile,
    )

    assert result.healed is True and result.retried_forge_merge is True
    assert reconcile.calls == [(frozenset({_SPEC_A, _SPEC_C}), False)]
    merged_baseline = _run_git(clone, "show", f"{_HEAD}:{SPEC_SURFACE_BASELINE_REL}")
    assert _SPEC_B in merged_baseline and '"memlog": "main"' in merged_baseline
    assert forge.merge_calls == 1


def test_heal_reconcile_refusal_pushes_nothing_and_never_retries_merge(tmp_path: Path) -> None:
    remote, clone, wt = _22_18_landing(
        tmp_path,
        branch_files={
            SPEC_SURFACE_BASELINE_REL: _baseline_json(
                **{
                    _SPEC_A: _baseline_entry("branch"),
                    _SPEC_B: _baseline_entry("base"),
                    _SPEC_C: _baseline_entry("branch"),
                }
            ),
            _MEMLOG_A: _memlog(_A, _B1, updated=_T1),
            _MEMLOG_C: _memlog(_A, _B1, updated=_T1),
        },
        main_files={
            SPEC_SURFACE_BASELINE_REL: _baseline_json(
                **{
                    _SPEC_A: _baseline_entry("base"),
                    _SPEC_B: _baseline_entry("main"),
                    _SPEC_C: _baseline_entry("main"),
                }
            ),
        },
    )
    head_before = _run_git(remote, "rev-parse", _HEAD).strip()
    forge = _HonestForge(clone)
    reconcile = _RecordingReconcile(refuse=True)

    result = try_heal_dispatch_land_merge(
        project_slug="pyforge-marshal",
        git_repo_root=clone,
        worktree=wt,
        base="main",
        head_branch=_HEAD,
        head_sha="unused",
        subject="Merge 22.18 into main",
        merge_strategy="merge",
        delete_branch=False,
        repo_ref=type("R", (), {"value": "rxm7706/local-recipes"})(),
        pr=PrInfo(number=2218, url="https://example/pr/2218", state="open", base="main"),
        fs=FakeFsHeal(),
        vcs=GitVcs(),
        forge=forge,
        probe_ref=_ORIGIN_MAIN,
        reconcile_spec_surface=reconcile,
    )

    assert result.healed is False
    assert result.reconcile_refusal is not None
    assert result.reconcile_refusal.code == "MRS-DISP-048"
    assert forge.merge_calls == 0
    assert _run_git(remote, "rev-parse", _HEAD).strip() == head_before


def test_heal_escalates_non_mechanical_path_beside_baseline(tmp_path: Path) -> None:
    _, clone, wt = _22_18_landing(
        tmp_path,
        branch_files={
            SPEC_SURFACE_BASELINE_REL: _baseline_json(
                **{
                    _SPEC_A: _baseline_entry("branch"),
                    _SPEC_B: _baseline_entry("base"),
                    _SPEC_C: _baseline_entry("base"),
                }
            ),
            "README.md": "branch\n",
        },
        main_files={
            SPEC_SURFACE_BASELINE_REL: _baseline_json(
                **{
                    _SPEC_A: _baseline_entry("base"),
                    _SPEC_B: _baseline_entry("main"),
                    _SPEC_C: _baseline_entry("base"),
                }
            ),
            "README.md": "main\n",
        },
    )
    head_before = _run_git(clone, "rev-parse", _HEAD).strip()
    forge = _HonestForge(clone)
    reconcile = _RecordingReconcile()

    result = try_heal_dispatch_land_merge(
        project_slug="pyforge-marshal",
        git_repo_root=clone,
        worktree=wt,
        base="main",
        head_branch=_HEAD,
        head_sha="unused",
        subject="Merge 22.18 into main",
        merge_strategy="merge",
        delete_branch=False,
        repo_ref=type("R", (), {"value": "rxm7706/local-recipes"})(),
        pr=PrInfo(number=2218, url="https://example/pr/2218", state="open", base="main"),
        fs=FakeFsHeal(),
        vcs=GitVcs(),
        forge=forge,
        probe_ref=_ORIGIN_MAIN,
        reconcile_spec_surface=reconcile,
    )

    assert result == DispatchLandHealResult(healed=False, escalated_paths=("README.md",))
    assert reconcile.calls == []
    assert _run_git(clone, "rev-parse", _HEAD).strip() == head_before


# --- Story 22.19: a landing unions the flag registry when two flag stories land in turn ---------------

_FLAGS_JSON = "src/platform/config/flags.json"
_OVERLAYS_JSON = "src/platform/config/flag-overlays.json"
_TEST_FLAGS_PY = "src/shared/packages/pyforge-core/tests/unit/test_flags.py"
_TEST_OPENFEATURE_PY = "src/platform/tests/test_openfeature_file_flags.py"
_REGISTRY_PATHS = (_FLAGS_JSON, _OVERLAYS_JSON, _TEST_FLAGS_PY, _TEST_OPENFEATURE_PY)
_ENVIRONMENTS = ("dev", "staging", "production")
_BASE_KEYS = ("pyforge.three_surfaces", "pyforge.base_two")
_K1, _K2 = "pyforge.herald.k_one", "pyforge.warden.k_two"


def _flag_definition(key: str, story: str | None = None) -> dict[str, object]:
    return {
        "state": "ENABLED",
        "variants": {"on": True, "off": False},
        "defaultVariant": "off",
        "metadata": {
            "owner": "warden",
            "story": story or f"story-{key}",
            "created": "2026-10-07",
            "on_everywhere": "",
            "cleanup_by": "",
        },
    }


def _flags_json(*keys: str, stories: dict[str, str] | None = None) -> str:
    stories = stories or {}
    return json.dumps({"flags": {k: _flag_definition(k, stories.get(k)) for k in keys}}, indent=2) + "\n"


def _overlays_doc(*keys: str, values: dict[str, str] | None = None) -> dict[str, dict[str, str]]:
    values = values or {}
    return {env: {k: values.get(k, "on") for k in keys} for env in _ENVIRONMENTS}


def _overlays_json(*keys: str, values: dict[str, str] | None = None) -> str:
    return json.dumps(_overlays_doc(*keys, values=values), indent=2) + "\n"


def _clock_entry(key: str, tag: str = "14-3-") -> str:
    return f'    "{key}": ("warden", "{tag}", "2026-10-07", "", ""),\n'


def _test_flags_py(
    *keys: str, comment: str = "# the per-environment booleans", tags: dict[str, str] | None = None
) -> str:
    """The three named dicts of core's ``test_flags.py`` (module-level ``_SHIPPED_CLOCKS``, then two
    function-local dicts), one entry per key, with a comment line above ``per_environment``."""
    tags = tags or {}
    clocks = "".join(_clock_entry(k, tags.get(k, "14-3-")) for k in keys)
    expected = "".join(f'        "{k}": True,\n' for k in keys)
    per_env = "".join(f'        "{k}": {{"dev": True, "staging": True, "production": False}},\n' for k in keys)
    return (
        "_SHIPPED_CLOCKS = {\n"
        + clocks
        + "}\n\n\ndef test_values():\n    expected = {\n"
        + expected
        + "    }\n    "
        + comment
        + "\n    per_environment = {\n"
        + per_env
        + "    }\n    assert expected and per_environment\n"
    )


def _test_openfeature_py(*keys: str) -> str:
    entries = "".join(
        f'    "{k}": {{\n        "dev": True,\n        "staging": True,\n        "production": False,\n    }},\n'
        for k in keys
    )
    return "_SHIPPED_BOOLEANS = {\n" + entries + "}\n_METADATA_FIELDS = ('owner',)\n"


def _registry_files(*keys: str) -> dict[str, str]:
    return {
        _FLAGS_JSON: _flags_json(*keys),
        _OVERLAYS_JSON: _overlays_json(*keys),
        _TEST_FLAGS_PY: _test_flags_py(*keys),
        _TEST_OPENFEATURE_PY: _test_openfeature_py(*keys),
    }


def _named_dict_keys(text: str, name: str) -> list[list[str]]:
    """The keys of every dict literal in ``text`` assigned to ``name``, in source order."""
    out: list[list[str]] = []
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            assert isinstance(node.value, ast.Dict)
            out.append([ast.literal_eval(k) for k in node.value.keys if k is not None])
    return out


class _RecordingCheck:
    """A healed-tree check that records what git looked like when it ran."""

    def __init__(self, wt: Path, remote: Path, *, finding: Finding | None = None, events=None) -> None:
        self.wt, self.remote, self.finding = wt, remote, finding
        self.events = events if events is not None else []
        self.calls = 0
        self.head_when_called = ""
        self.remote_head_when_called = ""
        self.parents_when_called: list[str] = []

    def __call__(self) -> Finding | None:
        self.calls += 1
        self.events.append("check")
        self.head_when_called = _run_git(self.wt, "rev-parse", "HEAD").strip()
        self.parents_when_called = _run_git(self.wt, "rev-list", "--parents", "-n", "1", "HEAD").split()[1:]
        self.remote_head_when_called = _run_git(self.remote, "rev-parse", _HEAD).strip()
        return self.finding


def _heal_registry(clone: Path, wt: Path, forge: _HonestForge, *, check=None, reconcile=None, await_checks=None):
    return try_heal_dispatch_land_merge(
        project_slug="pyforge-marshal",
        git_repo_root=clone,
        worktree=wt,
        base="main",
        head_branch=_HEAD,
        head_sha="unused",
        subject="Merge 22.19 into main",
        merge_strategy="merge",
        delete_branch=False,
        repo_ref=type("R", (), {"value": "rxm7706/local-recipes"})(),
        pr=PrInfo(number=2219, url="https://example/pr/2219", state="open", base="main"),
        fs=FakeFsHeal(),
        vcs=GitVcs(),
        forge=forge,
        probe_ref=_ORIGIN_MAIN,
        await_checks=await_checks,
        reconcile_spec_surface=reconcile,
        healed_tree_check=check,
    )


def _two_key_landing(tmp_path: Path):
    return _landing(
        tmp_path,
        base=_registry_files(*_BASE_KEYS),
        main=_registry_files(*_BASE_KEYS, _K1),
        branch=_registry_files(*_BASE_KEYS, _K2),
    )


# --- the constant and the classifiers ---


def test_the_flag_registry_is_exactly_the_four_paths() -> None:
    assert set(FLAG_REGISTRY_REL_PATHS) == set(_REGISTRY_PATHS)
    assert len(FLAG_REGISTRY_REL_PATHS) == 4


def test_is_flag_registry_path_takes_exactly_those_paths() -> None:
    assert all(is_flag_registry_path(p) for p in _REGISTRY_PATHS)
    assert is_flag_registry_path(_FLAGS_JSON.replace("/", "\\"))
    for other in (
        "src/platform/config/flags.json.bak",
        "src/platform/config/other.json",
        "flags.json",
        "src/shared/packages/pyforge-core/tests/unit/test_other.py",
        "src/platform/tests/test_flags.py",
        "x/" + _FLAGS_JSON,
    ):
        assert not is_flag_registry_path(other)


def test_the_registry_paths_are_mechanical_and_no_longer_unknown() -> None:
    for path in _REGISTRY_PATHS:
        assert is_mechanical_conflict_path(path)
    assert unknown_conflict_paths((*_REGISTRY_PATHS, "recipes/foo/recipe.yaml")) == ("recipes/foo/recipe.yaml",)


def test_mutation_mechanical_set_includes_the_flag_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Story 22.19 AC: remove the registry paths from the mechanical set and this fails."""
    assert is_mechanical_conflict_path(_FLAGS_JSON)
    monkeypatch.setattr(_dispatch_landing, "FLAG_REGISTRY_REL_PATHS", ())
    assert not is_mechanical_conflict_path(_FLAGS_JSON)
    assert unknown_conflict_paths(_REGISTRY_PATHS) == tuple(sorted(_REGISTRY_PATHS))


# --- the JSON union (pure) ---


def test_json_union_takes_mains_keys_then_the_branchs() -> None:
    base = _flags_json(*_BASE_KEYS)
    result = union_flag_registry_json_texts(base, _flags_json(*_BASE_KEYS, _K1), _flags_json(*_BASE_KEYS, _K2))
    assert result.refusal is None
    assert result.text == _flags_json(*_BASE_KEYS, _K1, _K2)
    assert result.text == json.dumps(json.loads(result.text), indent=2) + "\n"


def test_json_union_of_overlays_unions_every_environment() -> None:
    base = _overlays_json(*_BASE_KEYS)
    result = union_flag_registry_json_texts(base, _overlays_json(*_BASE_KEYS, _K1), _overlays_json(*_BASE_KEYS, _K2))
    assert result.text == _overlays_json(*_BASE_KEYS, _K1, _K2)
    assert [list(env) for env in json.loads(result.text).values()] == [[*_BASE_KEYS, _K1, _K2]] * 3


def test_json_union_takes_a_key_only_one_side_changed_and_honours_deletions() -> None:
    base = _flags_json("a", "b", "c", stories={"a": "old"})
    main = _flags_json("a", "b", "c", stories={"a": "new"})  # main edits a
    branch = _flags_json("a", "c", stories={"a": "old"})  # branch removes b
    result = union_flag_registry_json_texts(base, main, branch)
    assert result.text == _flags_json("a", "c", stories={"a": "new"})


def test_json_union_takes_a_key_both_sides_set_to_an_equal_value() -> None:
    base = _flags_json("a")
    side = _flags_json("a", "same")
    assert union_flag_registry_json_texts(base, side, side).text == side


def test_json_union_refuses_a_key_both_sides_set_to_different_values_naming_the_dotted_key() -> None:
    base = _flags_json(*_BASE_KEYS)
    main = _flags_json(*_BASE_KEYS, _K1, stories={_K1: "main's story"})
    branch = _flags_json(*_BASE_KEYS, _K1, stories={_K1: "branch's story"})
    result = union_flag_registry_json_texts(base, main, branch)
    assert result.text is None
    assert result.refusal == f"key flags.{_K1}"


def test_json_union_refuses_an_overlay_variant_set_two_ways_naming_the_environment_and_key() -> None:
    base = _overlays_json(*_BASE_KEYS)
    main = _overlays_doc(*_BASE_KEYS, _K1, values={_K1: "on"})
    branch = _overlays_doc(*_BASE_KEYS, _K1, values={_K1: "off"})
    result = union_flag_registry_json_texts(
        base, json.dumps(main, indent=2) + "\n", json.dumps(branch, indent=2) + "\n"
    )
    assert result.refusal == f"key dev.{_K1}"


def test_json_union_refuses_a_deleted_key_the_other_side_changed() -> None:
    base = _flags_json("a", "b")
    result = union_flag_registry_json_texts(base, _flags_json("a"), _flags_json("a", "b", stories={"b": "edited"}))
    assert result.refusal == "key flags.b"


@pytest.mark.parametrize("which", ["main", "branch"])
def test_json_union_never_reformats_a_side_that_is_not_in_the_canonical_form(which: str) -> None:
    base = _flags_json(*_BASE_KEYS)
    canonical_main, canonical_branch = _flags_json(*_BASE_KEYS, _K1), _flags_json(*_BASE_KEYS, _K2)
    odd = json.dumps(json.loads(canonical_main if which == "main" else canonical_branch), indent=4) + "\n"
    main, branch = (odd, canonical_branch) if which == "main" else (canonical_main, odd)
    result = union_flag_registry_json_texts(base, main, branch)
    assert result.text is None and which in (result.refusal or "")


def test_json_union_refuses_a_missing_trailing_newline() -> None:
    base = _flags_json(*_BASE_KEYS)
    result = union_flag_registry_json_texts(base, _flags_json(*_BASE_KEYS, _K1).rstrip("\n"), _flags_json(*_BASE_KEYS))
    assert result.text is None and "main" in (result.refusal or "")


@pytest.mark.parametrize(
    "bad",
    ["", "{not json", "[]", '{"flags": []}', '{"flags": {"a": 1}, "extra": 2}'],
)
def test_json_union_refuses_a_side_that_does_not_parse_or_has_a_non_object_member(bad: str) -> None:
    good = _flags_json(*_BASE_KEYS)
    for texts in ((good, bad, good), (good, good, bad), (bad, good, good)):
        assert union_flag_registry_json_texts(*texts).text is None


# --- the Python union (pure, over handwritten diff3 text) ---


def _hunk(ours: str, theirs: str, base: str = "") -> str:
    return f"<<<<<<< main\n{ours}||||||| base\n{base}=======\n{theirs}>>>>>>> branch\n"


def _marked_clocks(ours: str, theirs: str, *, base: str = "", tail: str = "") -> str:
    return "_SHIPPED_CLOCKS = {\n" + _clock_entry("a") + _hunk(ours, theirs, base) + "}\n" + tail


def test_python_union_keeps_mains_section_then_the_branchs_verbatim() -> None:
    result = union_flag_registry_python_texts(_TEST_FLAGS_PY, _marked_clocks(_clock_entry("m"), _clock_entry("b")))
    assert result.refusal is None
    assert result.text == "_SHIPPED_CLOCKS = {\n" + _clock_entry("a") + _clock_entry("m") + _clock_entry("b") + "}\n"


def test_python_union_resolves_several_hunks_in_three_named_dicts() -> None:
    marked = (
        "_SHIPPED_CLOCKS = {\n"
        + _hunk(_clock_entry("m"), _clock_entry("b"))
        + "}\n\n\ndef f():\n    expected = {\n"
        + _hunk('        "m": True,\n', '        "b": True,\n')
        + "    }\n    per_environment = {\n"
        + _hunk('        "m": {"dev": True},\n', '        "b": {"dev": False},\n')
        + "    }\n"
    )
    result = union_flag_registry_python_texts(_TEST_FLAGS_PY, marked)
    assert result.refusal is None and result.text is not None
    assert [_named_dict_keys(result.text, n) for n in ("_SHIPPED_CLOCKS", "expected", "per_environment")] == [
        [["m", "b"]],
        [["m", "b"]],
        [["m", "b"]],
    ]


def test_python_union_accepts_a_clean_merge_with_no_hunks() -> None:
    clean = "_SHIPPED_BOOLEANS = {\n    'a': True,\n    'b': False,\n}\n"
    assert union_flag_registry_python_texts(_TEST_OPENFEATURE_PY, clean).text == clean


def test_python_union_refuses_a_hunk_with_a_base_section() -> None:
    marked = _marked_clocks(_clock_entry("m"), _clock_entry("b"), base=_clock_entry("old"))
    result = union_flag_registry_python_texts(_TEST_FLAGS_PY, marked)
    assert result.text is None and "hunk 1" in (result.refusal or "")


def test_python_union_refuses_a_changed_comment_above_per_environment() -> None:
    marked = (
        "def f():\n"
        + _hunk("    # main's note\n", "    # branch's note\n", base="    # the per-environment booleans\n")
        + "    per_environment = {\n        'a': 1,\n    }\n"
    )
    result = union_flag_registry_python_texts(_TEST_FLAGS_PY, marked)
    assert result.text is None and result.refusal


def test_python_union_refuses_an_added_comment_that_is_not_a_dict_entry() -> None:
    marked = (
        "def f():\n"
        + _hunk("    # main's note\n", "    # branch's note\n")
        + "    per_environment = {\n        'a': 1,\n    }\n"
    )
    assert union_flag_registry_python_texts(_TEST_FLAGS_PY, marked).text is None


def test_python_union_refuses_a_side_that_is_not_complete_dict_entries() -> None:
    half = '    "m": (\n        "warden",\n'
    result = union_flag_registry_python_texts(_TEST_FLAGS_PY, _marked_clocks(half, _clock_entry("b")))
    assert result.text is None and "pure addition" in (result.refusal or "")


def test_python_union_refuses_an_empty_side() -> None:
    assert union_flag_registry_python_texts(_TEST_FLAGS_PY, _marked_clocks("", _clock_entry("b"))).text is None


def test_python_union_refuses_a_hunk_outside_the_named_dicts() -> None:
    marked = "_OTHER = {\n" + _hunk(_clock_entry("m"), _clock_entry("b")) + "}\n"
    result = union_flag_registry_python_texts(_TEST_FLAGS_PY, marked)
    assert result.text is None and "not inside a named dict" in (result.refusal or "")


def test_python_union_refuses_the_wrong_files_named_dict() -> None:
    """The platform module's one target is ``_SHIPPED_BOOLEANS``; core's dict names do not count there."""
    marked = _marked_clocks(_clock_entry("m"), _clock_entry("b"))
    assert union_flag_registry_python_texts(_TEST_OPENFEATURE_PY, marked).text is None


def test_python_union_refuses_a_hunk_inside_an_entrys_nested_dict() -> None:
    marked = "per_environment = {\n    'a': {\n" + _hunk('        "m": 1,\n', '        "b": 2,\n') + "    },\n}\n"
    assert union_flag_registry_python_texts(_TEST_FLAGS_PY, marked).text is None


def test_python_union_refuses_the_same_key_added_with_different_text_naming_it() -> None:
    ours = _clock_entry("pyforge.x", "1-1-")
    theirs = _clock_entry("pyforge.x", "2-2-")
    result = union_flag_registry_python_texts(_TEST_FLAGS_PY, _marked_clocks(ours, theirs))
    assert result.text is None and result.refusal == "key pyforge.x"


def test_python_union_refuses_a_resolution_that_does_not_parse() -> None:
    no_comma = '    "m": 1\n'  # a complete entry on its own, but not once the branch's follows it
    result = union_flag_registry_python_texts(_TEST_FLAGS_PY, _marked_clocks(no_comma, _clock_entry("b")))
    assert result.text is None and "does not parse" in (result.refusal or "")


@pytest.mark.parametrize(
    "marked",
    [
        "<<<<<<< main\nx\n",  # never closed
        "=======\n",  # a stray separator
        "<<<<<<< main\nx\n=======\ny\n>>>>>>> branch\n",  # a hunk without its diff3 base section
    ],
)
def test_python_union_refuses_malformed_markers(marked: str) -> None:
    assert union_flag_registry_python_texts(_TEST_FLAGS_PY, marked).text is None


def test_python_union_refuses_a_path_that_is_not_a_python_registry() -> None:
    assert union_flag_registry_python_texts(_FLAGS_JSON, "x = 1\n").text is None


# --- merge_file_diff3 (the real git adapter) ---


def test_git_vcs_merge_file_diff3_returns_git_s_marked_three_way_merge(tmp_path: Path) -> None:
    marked = GitVcs().merge_file_diff3(tmp_path, "a\nb\nc\n", "a\nb\nmain\nc\n", "a\nb\nbranch\nc\n")
    assert marked == "a\nb\n<<<<<<< main\nmain\n||||||| base\n=======\nbranch\n>>>>>>> branch\nc\n"


def test_git_vcs_merge_file_diff3_merges_a_non_conflicting_pair_cleanly(tmp_path: Path) -> None:
    assert GitVcs().merge_file_diff3(tmp_path, "a\nb\nc\n", "A\nb\nc\n", "a\nb\nC\n") == "A\nb\nC\n"


# --- the heal, over real git ---


def test_real_heal_unions_two_flag_keys_across_all_four_registry_files(tmp_path: Path) -> None:
    """Story 22.19 AC 1: herald 29.1's key on main, warden 14.3's on the branch."""
    remote, clone, wt = _two_key_landing(tmp_path)
    head_before = _run_git(remote, "rev-parse", _HEAD).strip()
    forge = _HonestForge(clone)
    check = _RecordingCheck(wt, remote)

    result = _heal_registry(clone, wt, forge, check=check)

    assert result == DispatchLandHealResult(healed=True, retried_forge_merge=True)  # no MRS-DISP-038 escalation
    # the check ran once, on the merged commit (a real merge of origin/main), before anything was pushed
    assert check.calls == 1
    origin_main = _run_git(clone, "rev-parse", _ORIGIN_MAIN).strip()
    assert check.parents_when_called[1] == origin_main
    assert check.remote_head_when_called == head_before
    # one merge, one push, one retried merge
    pushed = _run_git(remote, "rev-parse", _HEAD).strip()
    assert pushed == check.head_when_called != head_before
    assert forge.merge_calls == 1
    assert _run_git(clone, "rev-list", "--count", f"{origin_main}..{pushed}").strip() == "2"  # branch + merge
    # the four files hold both keys, main's first
    assert _run_git(clone, "show", f"{pushed}:{_FLAGS_JSON}") == _flags_json(*_BASE_KEYS, _K1, _K2)
    assert _run_git(clone, "show", f"{pushed}:{_OVERLAYS_JSON}") == _overlays_json(*_BASE_KEYS, _K1, _K2)
    clocks = _run_git(clone, "show", f"{pushed}:{_TEST_FLAGS_PY}")
    assert [_named_dict_keys(clocks, n) for n in ("_SHIPPED_CLOCKS", "expected", "per_environment")] == [
        [[*_BASE_KEYS, _K1, _K2]]
    ] * 3
    booleans = _run_git(clone, "show", f"{pushed}:{_TEST_OPENFEATURE_PY}")
    assert _named_dict_keys(booleans, "_SHIPPED_BOOLEANS") == [[*_BASE_KEYS, _K1, _K2]]
    assert "_METADATA_FIELDS" in booleans  # the rest of the file is git's own merge, untouched
    assert _run_git(wt, "status", "--porcelain").strip() == ""


def test_real_heal_checks_the_tree_when_only_one_registry_file_conflicts(tmp_path: Path) -> None:
    """A registry path resolved is enough to run the check."""
    base = _registry_files(*_BASE_KEYS)
    main = {**base, _TEST_FLAGS_PY: _test_flags_py(*_BASE_KEYS, _K1)}
    branch = {**base, _TEST_FLAGS_PY: _test_flags_py(*_BASE_KEYS, _K2)}
    remote, clone, wt = _landing(tmp_path, base=base, main=main, branch=branch)
    check = _RecordingCheck(wt, remote)

    result = _heal_registry(clone, wt, _HonestForge(clone), check=check)

    assert result.healed is True and check.calls == 1


def test_real_heal_escalates_the_same_flag_key_with_different_values_naming_it(tmp_path: Path) -> None:
    """Story 22.19 AC 2: nothing is committed, pushed or merged."""
    base = _registry_files(*_BASE_KEYS)
    main = {**base, _FLAGS_JSON: _flags_json(*_BASE_KEYS, _K1, stories={_K1: "main's"})}
    branch = {**base, _FLAGS_JSON: _flags_json(*_BASE_KEYS, _K1, stories={_K1: "branch's"})}
    remote, clone, wt = _landing(tmp_path, base=base, main=main, branch=branch)
    head_before = _run_git(remote, "rev-parse", _HEAD).strip()
    wt_head_before = _run_git(wt, "rev-parse", "HEAD").strip()
    forge = _HonestForge(clone)
    check = _RecordingCheck(wt, remote)

    result = _heal_registry(clone, wt, forge, check=check)

    assert result == DispatchLandHealResult(healed=False, escalated_paths=(f"{_FLAGS_JSON} (key flags.{_K1})",))
    assert check.calls == 0 and forge.merge_calls == 0
    assert _run_git(remote, "rev-parse", _HEAD).strip() == head_before
    assert _run_git(wt, "rev-parse", "HEAD").strip() == wt_head_before
    assert _run_git(wt, "status", "--porcelain").strip() == ""


def test_real_heal_escalates_the_same_overlay_key_in_one_environment(tmp_path: Path) -> None:
    base = _registry_files(*_BASE_KEYS)
    main_overlays = _overlays_doc(*_BASE_KEYS, _K1)
    branch_overlays = _overlays_doc(*_BASE_KEYS, _K1)
    branch_overlays["production"][_K1] = "off"
    main = {**base, _OVERLAYS_JSON: json.dumps(main_overlays, indent=2) + "\n"}
    branch = {**base, _OVERLAYS_JSON: json.dumps(branch_overlays, indent=2) + "\n"}
    _remote, clone, wt = _landing(tmp_path, base=base, main=main, branch=branch)
    forge = _HonestForge(clone)

    result = _heal_registry(clone, wt, forge, check=lambda: None)

    assert result == DispatchLandHealResult(healed=False, escalated_paths=(f"{_OVERLAYS_JSON} (key production.{_K1})",))
    assert forge.merge_calls == 0


def test_real_heal_escalates_a_python_entry_added_on_both_sides_with_different_text(tmp_path: Path) -> None:
    base = _registry_files(*_BASE_KEYS)
    main = {**base, _TEST_FLAGS_PY: _test_flags_py(*_BASE_KEYS, _K1, tags={_K1: "main-"})}
    branch = {**base, _TEST_FLAGS_PY: _test_flags_py(*_BASE_KEYS, _K1, tags={_K1: "branch-"})}
    _remote, clone, wt = _landing(tmp_path, base=base, main=main, branch=branch)
    forge = _HonestForge(clone)

    result = _heal_registry(clone, wt, forge, check=lambda: None)

    assert result.healed is False and forge.merge_calls == 0
    assert result.escalated_paths == (f"{_TEST_FLAGS_PY} (key {_K1})",)


def test_real_heal_escalates_a_hunk_that_is_not_an_addition_and_merges_nothing(tmp_path: Path) -> None:
    """Story 22.19 AC 3: both sides edit the comment above `per_environment`."""
    base = _registry_files(*_BASE_KEYS)
    main = {**base, _TEST_FLAGS_PY: _test_flags_py(*_BASE_KEYS, comment="# main's note")}
    branch = {**base, _TEST_FLAGS_PY: _test_flags_py(*_BASE_KEYS, comment="# branch's note")}
    remote, clone, wt = _landing(tmp_path, base=base, main=main, branch=branch)
    head_before = _run_git(remote, "rev-parse", _HEAD).strip()
    wt_head_before = _run_git(wt, "rev-parse", "HEAD").strip()
    forge = _HonestForge(clone)
    check = _RecordingCheck(wt, remote)

    result = _heal_registry(clone, wt, forge, check=check)

    assert result.healed is False
    assert len(result.escalated_paths) == 1 and result.escalated_paths[0].startswith(f"{_TEST_FLAGS_PY} (")
    assert check.calls == 0 and forge.merge_calls == 0
    assert _run_git(remote, "rev-parse", _HEAD).strip() == head_before
    assert _run_git(wt, "rev-parse", "HEAD").strip() == wt_head_before


def test_real_heal_escalates_a_comment_added_beside_the_entries(tmp_path: Path) -> None:
    base = _registry_files(*_BASE_KEYS)
    text = base[_TEST_OPENFEATURE_PY]
    main = {**base, _TEST_OPENFEATURE_PY: text.replace("}\n_META", "    # main's note\n}\n_META", 1)}
    branch = {**base, _TEST_OPENFEATURE_PY: text.replace("}\n_META", "    # branch's note\n}\n_META", 1)}
    _remote, clone, wt = _landing(tmp_path, base=base, main=main, branch=branch)

    result = _heal_registry(clone, wt, _HonestForge(clone), check=lambda: None)

    assert result.healed is False
    assert result.escalated_paths and result.escalated_paths[0].startswith(_TEST_OPENFEATURE_PY)


@pytest.mark.parametrize("side", ["main", "branch"])
def test_real_heal_escalates_a_flags_json_that_is_not_canonical_and_never_reformats_it(
    tmp_path: Path, side: str
) -> None:
    """Story 22.19 AC 6."""
    base = _registry_files(*_BASE_KEYS)
    odd = json.dumps(json.loads(_flags_json(*_BASE_KEYS, _K1 if side == "main" else _K2)), indent=4) + "\n"
    main = {**base, _FLAGS_JSON: odd if side == "main" else _flags_json(*_BASE_KEYS, _K1)}
    branch = {**base, _FLAGS_JSON: odd if side == "branch" else _flags_json(*_BASE_KEYS, _K2)}
    remote, clone, wt = _landing(tmp_path, base=base, main=main, branch=branch)
    head_before = _run_git(remote, "rev-parse", _HEAD).strip()
    forge = _HonestForge(clone)

    result = _heal_registry(clone, wt, forge, check=lambda: None)

    assert result.healed is False and forge.merge_calls == 0
    assert len(result.escalated_paths) == 1 and result.escalated_paths[0].startswith(f"{_FLAGS_JSON} (")
    assert _run_git(remote, "rev-parse", _HEAD).strip() == head_before
    assert (wt / _FLAGS_JSON).read_text(encoding="utf-8") == (
        odd if side == "branch" else _flags_json(*_BASE_KEYS, _K2)
    )


def test_real_heal_without_a_healed_tree_check_escalates_the_registry_and_resolves_nothing(tmp_path: Path) -> None:
    """Story 22.19 AC 5: a direct caller (no check) gets MRS-DISP-038's plain paths, as before."""
    remote, clone, wt = _two_key_landing(tmp_path)
    head_before = _run_git(remote, "rev-parse", _HEAD).strip()
    wt_head_before = _run_git(wt, "rev-parse", "HEAD").strip()
    forge = _HonestForge(clone)

    result = _heal_registry(clone, wt, forge, check=None)

    assert result == DispatchLandHealResult(healed=False, escalated_paths=tuple(sorted(_REGISTRY_PATHS)))
    assert forge.merge_calls == 0
    assert _run_git(remote, "rev-parse", _HEAD).strip() == head_before
    assert _run_git(wt, "rev-parse", "HEAD").strip() == wt_head_before


def test_real_heal_pushes_nothing_when_the_healed_tree_check_fails(tmp_path: Path) -> None:
    """Story 22.19 AC 4: the merge is committed locally, then refused before the push."""
    remote, clone, wt = _two_key_landing(tmp_path)
    head_before = _run_git(remote, "rev-parse", _HEAD).strip()
    refusal = Finding(
        code="MRS-DISP-038",
        severity=Severity.ERROR,
        message="`pixi run --frozen -e pyforge-guild flag-gate-check` exited 1",
    )
    forge = _HonestForge(clone)
    check = _RecordingCheck(wt, remote, finding=refusal)
    await_calls: list[str] = []

    def await_checks(sha: str) -> None:
        await_calls.append(sha)

    result = _heal_registry(clone, wt, forge, check=check, await_checks=await_checks)

    assert result == DispatchLandHealResult(healed=False, healed_tree_refusal=refusal)
    assert result.healed_tree_refusal is refusal
    assert check.calls == 1
    assert len(check.parents_when_called) == 2  # the merge commit existed when the check ran
    assert _run_git(remote, "rev-parse", _HEAD).strip() == head_before  # nothing pushed
    assert await_calls == [] and forge.merge_calls == 0  # no wait, no retried merge


def test_real_heal_refuses_an_unrelated_conflict_beside_the_registry(tmp_path: Path) -> None:
    """Never newly mechanical: every other unknown path still escalates, and nothing is merged."""
    base = {**_registry_files(*_BASE_KEYS), "README.md": "base\n"}
    main = {**_registry_files(*_BASE_KEYS, _K1), "README.md": "main\n"}
    branch = {**_registry_files(*_BASE_KEYS, _K2), "README.md": "branch\n"}
    remote, clone, wt = _landing(tmp_path, base=base, main=main, branch=branch)
    head_before = _run_git(remote, "rev-parse", _HEAD).strip()
    check = _RecordingCheck(wt, remote)

    result = _heal_registry(clone, wt, _HonestForge(clone), check=check)

    assert result == DispatchLandHealResult(healed=False, escalated_paths=("README.md",))
    assert check.calls == 0
    assert _run_git(remote, "rev-parse", _HEAD).strip() == head_before


def test_real_heal_does_not_resolve_a_look_alike_path(tmp_path: Path) -> None:
    other = "src/platform/config/flags.json.orig"
    _remote, clone, wt = _landing(
        tmp_path,
        base={other: _flags_json(*_BASE_KEYS)},
        main={other: _flags_json(*_BASE_KEYS, _K1)},
        branch={other: _flags_json(*_BASE_KEYS, _K2)},
    )

    result = _heal_registry(clone, wt, _HonestForge(clone), check=lambda: None)

    assert result == DispatchLandHealResult(healed=False, escalated_paths=(other,))


def test_mutation_real_two_key_landing_is_refused_without_the_registry_in_the_mechanical_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Story 22.19 AC (mutation): with the registry paths removed, the first criterion's landing is refused
    (the heal escalates every registry path; ``execute_dispatch_land`` raises MRS-DISP-038 on that)."""
    remote, clone, wt = _two_key_landing(tmp_path)
    monkeypatch.setattr(_dispatch_landing, "FLAG_REGISTRY_REL_PATHS", ())
    check = _RecordingCheck(wt, remote)

    result = _heal_registry(clone, wt, _HonestForge(clone), check=check)

    assert result.healed is False and result.escalated_paths == tuple(sorted(_REGISTRY_PATHS))
    assert check.calls == 0


def _baseline_of(**memlogs: str) -> str:
    return _baseline_json(**{name: _baseline_entry(memlog) for name, memlog in memlogs.items()})


def test_real_heal_resolves_registry_and_baseline_in_one_merge_then_stamps_then_checks_then_pushes(
    tmp_path: Path,
) -> None:
    """Story 22.19 AC: the warden 14.3 shape -- registry and `.spec-surface-baseline.json` together."""
    base_files = {
        **_registry_files(*_BASE_KEYS),
        SPEC_SURFACE_BASELINE_REL: _baseline_of(**{_SPEC_A: "base", _SPEC_B: "base"}),
        _MEMLOG_A: _memlog(_A, updated=_T0),
    }
    main_files = {
        **_registry_files(*_BASE_KEYS, _K1),
        SPEC_SURFACE_BASELINE_REL: _baseline_of(**{_SPEC_A: "main", _SPEC_B: "main"}),
    }
    branch_files = {
        **_registry_files(*_BASE_KEYS, _K2),
        SPEC_SURFACE_BASELINE_REL: _baseline_of(**{_SPEC_A: "branch", _SPEC_B: "base"}),
        _MEMLOG_A: _memlog(_A, _B1, updated=_T1),
    }
    remote, clone, wt = _landing(tmp_path, base=base_files, main=main_files, branch=branch_files)
    head_before = _run_git(remote, "rev-parse", _HEAD).strip()
    events: list[str] = []
    forge = _HonestForge(clone)
    check = _RecordingCheck(wt, remote, events=events)
    reconcile = _RecordingReconcile()

    def ordered_reconcile(*, branch_stamp_specs, push_when_done):
        events.append("reconcile")
        # at the re-stamp the merge is committed, the registry already unioned, and nothing is pushed
        assert _run_git(wt, "show", f"HEAD:{_FLAGS_JSON}") == _flags_json(*_BASE_KEYS, _K1, _K2)
        assert _run_git(remote, "rev-parse", _HEAD).strip() == head_before
        return reconcile(branch_stamp_specs=branch_stamp_specs, push_when_done=push_when_done)

    result = _heal_registry(clone, wt, forge, check=check, reconcile=ordered_reconcile)

    assert result == DispatchLandHealResult(healed=True, retried_forge_merge=True)
    assert events == ["reconcile", "check"]  # re-stamp, then the check, then (below) one push
    assert reconcile.calls == [(frozenset({_SPEC_A}), False)]
    assert check.calls == 1 and check.remote_head_when_called == head_before
    pushed = _run_git(remote, "rev-parse", _HEAD).strip()
    assert pushed == check.head_when_called and pushed != head_before
    assert len(check.parents_when_called) == 2  # one merge resolved the registry AND the baseline
    assert forge.merge_calls == 1
    merged_baseline = _run_git(clone, "show", f"{pushed}:{SPEC_SURFACE_BASELINE_REL}")
    assert '"memlog": "main"' in merged_baseline  # the baseline resolves to main's, for the re-stamp


def test_real_heal_does_not_check_or_push_when_the_restamp_refuses_beside_the_registry(tmp_path: Path) -> None:
    base_files = {**_registry_files(*_BASE_KEYS), SPEC_SURFACE_BASELINE_REL: _baseline_of(**{_SPEC_A: "base"})}
    main_files = {**_registry_files(*_BASE_KEYS, _K1), SPEC_SURFACE_BASELINE_REL: _baseline_of(**{_SPEC_A: "main"})}
    branch_files = {
        **_registry_files(*_BASE_KEYS, _K2),
        SPEC_SURFACE_BASELINE_REL: _baseline_of(**{_SPEC_A: "branch"}),
    }
    remote, clone, wt = _landing(tmp_path, base=base_files, main=main_files, branch=branch_files)
    head_before = _run_git(remote, "rev-parse", _HEAD).strip()
    check = _RecordingCheck(wt, remote)
    forge = _HonestForge(clone)

    result = _heal_registry(clone, wt, forge, check=check, reconcile=_RecordingReconcile(refuse=True))

    assert result.healed is False and result.reconcile_refusal is not None
    assert check.calls == 0 and forge.merge_calls == 0
    assert _run_git(remote, "rev-parse", _HEAD).strip() == head_before


def test_a_heal_with_no_registry_conflict_never_runs_the_healed_tree_check(tmp_path: Path) -> None:
    remote, clone, wt = _landing(
        tmp_path,
        base={_LEDGER: _generated_ledger(("57-1-a", "done"))},
        main={_LEDGER: _generated_ledger(("57-1-a", "done"), ("58-1-x", "backlog"))},
        branch={_LEDGER: _generated_ledger(("57-1-a", "done"), ("59-1-y", "done"))},
    )
    check = _RecordingCheck(wt, remote)

    result = _heal_registry(clone, wt, _HonestForge(clone), check=check)

    assert result.healed is True and check.calls == 0


# --- the landing's own healed-tree check (dispatch_land._healed_tree_flag_registry_check) ---

_OK = ProcessResult(returncode=0, stdout="", stderr="")


class _ScriptedProcess:
    """A ``ProcessPort`` double: records ``(argv, cwd, timeout_s)``; ``outcomes[i]`` answers call ``i``."""

    def __init__(self, *outcomes: ProcessResult | Exception) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[tuple[list[str], Path, float | None]] = []

    def run(self, argv, *, cwd: Path, timeout_s: float | None = None) -> ProcessResult:
        self.calls.append((list(argv), cwd, timeout_s))
        outcome = self.outcomes[len(self.calls) - 1] if len(self.calls) <= len(self.outcomes) else _OK
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_the_landing_builds_the_check_that_runs_exactly_the_three_commands(tmp_path: Path) -> None:
    """Story 22.19 AC: the three commands of "The union rules", the platform one in `src/platform`."""
    process = _ScriptedProcess(ProcessResult(returncode=0, stdout="WARN something", stderr=""), _OK, _OK)

    finding = dispatch_land._healed_tree_flag_registry_check(tmp_path, process)()

    assert finding is None
    assert [(argv, cwd) for argv, cwd, _t in process.calls] == [
        (["pixi", "run", "--frozen", "-e", "pyforge-guild", "flag-gate-check"], tmp_path),
        (
            [
                "pixi",
                "run",
                "--frozen",
                "-e",
                "pyforge-core",
                "pytest",
                "src/shared/packages/pyforge-core/tests/unit/test_flags.py",
                "-q",
            ],
            tmp_path,
        ),
        (
            [
                "pixi",
                "run",
                "--frozen",
                "-e",
                "platform-ci-test",
                "env",
                "-u",
                "PYTHONSAFEPATH",
                "python",
                "-m",
                "pytest",
                "tests/test_openfeature_file_flags.py",
                "-q",
                "-p",
                "no:cacheprovider",
            ],
            tmp_path / "src" / "platform",
        ),
    ]
    assert all(timeout is not None for _a, _c, timeout in process.calls)


@pytest.mark.parametrize("failing", [0, 1, 2])
@pytest.mark.parametrize("code", [1, 2])
def test_a_failing_command_refuses_with_mrs_disp_038_naming_it_and_its_exit_code(
    tmp_path: Path, failing: int, code: int
) -> None:
    outcomes: list[ProcessResult | Exception] = [_OK, _OK, _OK]
    outcomes[failing] = ProcessResult(
        returncode=code, stdout="ok line\nFAIL flag-x: cleanup_by passed\nFAIL flag-y: bad story\n", stderr=""
    )
    process = _ScriptedProcess(*outcomes)

    finding = dispatch_land._healed_tree_flag_registry_check(tmp_path, process)()

    assert finding is not None and finding.code == "MRS-DISP-038" and finding.severity == Severity.ERROR
    name = ("flag-gate-check", "test_flags.py", "test_openfeature_file_flags.py")[failing]
    assert name in finding.message and f"exited {code}" in finding.message
    assert "FAIL flag-x: cleanup_by passed" in finding.message and "ok line" not in finding.message
    assert len(process.calls) == failing + 1  # the first failure stops the check


def test_a_failure_detail_is_bounded(tmp_path: Path) -> None:
    noisy = "".join(f"FAIL flag-{i}: {'x' * 200}\n" for i in range(100))
    process = _ScriptedProcess(ProcessResult(returncode=1, stdout=noisy, stderr=""))
    finding = dispatch_land._healed_tree_flag_registry_check(tmp_path, process)()
    assert finding is not None and len(finding.message) < 2000


def test_a_failing_test_module_with_no_fail_lines_carries_the_output_tail(tmp_path: Path) -> None:
    process = _ScriptedProcess(
        _OK, ProcessResult(returncode=1, stdout="E assert 1 == 2\n1 failed in 0.1s\n", stderr="")
    )
    finding = dispatch_land._healed_tree_flag_registry_check(tmp_path, process)()
    assert finding is not None and "1 failed in 0.1s" in finding.message


def test_a_timeout_or_an_env_that_will_not_run_refuses_with_mrs_disp_038(tmp_path: Path) -> None:
    process = _ScriptedProcess(ProcessError("command timed out after 1800.0s: pixi run"))
    finding = dispatch_land._healed_tree_flag_registry_check(tmp_path, process)()
    assert finding is not None and finding.code == "MRS-DISP-038"
    assert "flag-gate-check" in finding.message and "timed out" in finding.message
