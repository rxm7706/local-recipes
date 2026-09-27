"""Unit tests for dispatch land healing (Story 28.20, CAP-4)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from pyforge.marshal.adapters.vcs_git import GitVcs
from pyforge.marshal.core.chain_regen import render_ledger_statuses
from pyforge.marshal.core.dispatch_landing import (
    is_mechanical_conflict_path,
    ledger_status_precedence,
    three_way_ledger_statuses,
    union_sprint_ledger_maps,
    unknown_conflict_paths,
)
from pyforge.marshal.dispatch_land_heal import (
    DispatchLandHealResult,
    try_heal_dispatch_land_merge,
)
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
            if ref == "main":
                return self.main_ledger
            return self.branch_ledger
        return None

    def commit_paths(self, repo_root: Path, paths: tuple[Path, ...], message: str):
        self.commits.append((repo_root, paths, message))
        self._head_sha = "healed222"
        return self._head_sha

    def merge_ref_resolving(self, worktree_path: Path, ref: str, *, resolutions, message: str) -> str:
        """Story 59.1: records the merge and writes each resolution, as the real adapter does."""
        self.merges.append((worktree_path, ref, dict(resolutions), message))
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
    assert (merged_into, merged_ref, list(resolutions)) == (worktree, "main", [ledger_rel])
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
    assert vcs.merged == [("dispatch/pyforge-marshal/28.20", "main", "Merge 28.20 into main")]
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


def _heal(clone: Path, wt: Path, forge: _HonestForge) -> DispatchLandHealResult:
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
