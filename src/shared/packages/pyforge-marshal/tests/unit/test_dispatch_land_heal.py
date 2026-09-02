"""Unit tests for dispatch land healing (Story 28.20, CAP-4)."""

from __future__ import annotations

from pathlib import Path

from pyforge.marshal.core.dispatch_landing import (
    is_mechanical_conflict_path,
    ledger_status_precedence,
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
        self.merged: list[tuple[str, str, str]] = []
        self.deleted: list[str] = []
        self._head_sha = "abc111"
        self._merge_tree_calls = 0

    def merge_tree_conflict_paths(self, _repo_root: Path, _base: str, _branch: str):
        self._merge_tree_calls += 1
        if self._merge_tree_calls > 1 and self.conflict_paths_after_ledger is not None:
            return self.conflict_paths_after_ledger
        return self.conflict_paths

    def file_text_at_ref(self, _repo_root: Path, ref: str, path: str):
        if path.endswith("sprint-status-ledger.yaml"):
            if ref == "main":
                return self.main_ledger
            return self.branch_ledger
        return None

    def commit_paths(self, repo_root: Path, paths: tuple[Path, ...], message: str):
        self.commits.append((repo_root, paths, message))
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
    assert len(vcs.commits) == 1
    assert vcs.commits[0][0] == worktree
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


def test_heal_falls_through_to_local_advance_when_ledger_retry_stays_dirty(
    tmp_path: Path,
) -> None:
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

    assert result == DispatchLandHealResult(healed=True, landed_via_local_merge=True)
    assert vcs.pushed == ["dispatch/pyforge-marshal/28.20", "main"]
    assert vcs.merged == [("dispatch/pyforge-marshal/28.20", "main", "Merge 28.20 into main")]
    assert forge.closed == [985]


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
