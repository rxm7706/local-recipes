"""Unit tests for ``core.teardown_preserve`` (Story 87.7)."""

from __future__ import annotations

from pathlib import Path

import pytest
import test_init as init_fixtures
from pyforge.core.preserve_refs import (
    LocalPreserveTag,
    PreserveObservation,
    PreserveRecord,
    PreserveState,
    PreserveTrailers,
)

from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.core import teardown_preserve as tp
from pyforge.marshal.core.teardown_preserve import scan_teardown_unpreserved
from pyforge.marshal.ports.vcs import WorktreeEntry

FakeVcs = init_fixtures.FakeVcs


def _scan(
    *,
    repo_root: Path,
    home: Path,
    slug: str = "acme",
    branch: str = "loop/acme",
    vcs: FakeVcs | None = None,
    nested: tuple[WorktreeEntry, ...] = (),
) -> tp.TeardownPreserveScan:
    vcs = vcs or FakeVcs(repo_root=repo_root)
    return scan_teardown_unpreserved(
        repo_root=repo_root,
        home=home,
        slug=slug,
        branch=branch,
        vcs=vcs,
        nested_worktrees=nested,
    )


def test_scan_reports_non_empty_failed_patch(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    repo.mkdir()
    home.mkdir()
    run_dir = home / ".bmad-loop" / "runs" / "run1" / "failed" / "1-1"
    run_dir.mkdir(parents=True)
    patch = run_dir / "changes.patch"
    patch.write_text("diff\n", encoding="utf-8")
    token = patch.relative_to(home).as_posix()

    vcs = FakeVcs(repo_root=repo)
    vcs.remote_branches = {"loop/acme"}
    result = _scan(repo_root=repo, home=home, vcs=vcs)

    assert any(i.abandon_token == token for i in result.items)


def test_scan_skips_empty_patch_and_covered_patch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    repo.mkdir()
    home.mkdir()
    run_dir = home / ".bmad-loop" / "runs" / "run1" / "failed" / "1-1"
    run_dir.mkdir(parents=True)
    patch = run_dir / "changes.patch"
    patch.write_text("", encoding="utf-8")
    covered = run_dir / "changes2.patch"
    covered.write_text("diff\n", encoding="utf-8")
    rel = covered.relative_to(home).as_posix()

    record = PreserveRecord(
        refname="refs/tags/preserve/acme/1.1/dispatch-deadbeef",
        object_sha="deadbeef",
        project_slug="acme",
        story_key="1.1",
        producer="dispatch",
        sha8="deadbeef",
        state=PreserveState.OPEN,
        trailers=PreserveTrailers(
            producer="dispatch",
            provenance="test",
            reason="test",
            source=rel,
            run="run1",
            journal="j",
            commit="c",
        ),
    )
    monkeypatch.setattr(tp, "list_preserves", lambda _repo: [record])
    monkeypatch.setattr(tp, "observe_preserve_debt", lambda _repo: None)

    vcs = FakeVcs(repo_root=repo)
    vcs.remote_branches = {"loop/acme"}
    result = _scan(repo_root=repo, home=home, vcs=vcs)

    assert not any(i.abandon_token == rel for i in result.items)


def test_scan_unpromoted_scratch_and_debt_tags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    repo.mkdir()
    (home / ".bmad-loop" / "runs" / "run1").mkdir(parents=True)

    scratch_ref = "refs/heads/attempt-preserve/run1-attempt"
    local_tag = LocalPreserveTag(
        refname="refs/tags/preserve/acme/1.1/dispatch-abc12345",
        commit="abc12345",
        run="run1",
        producer="dispatch",
        project_slug="acme",
        story_key="1.1",
        sha8="abc12345",
    )
    observation = PreserveObservation(
        tags=(local_tag,),
        local_only_tags=(local_tag,),
        unpromoted_scratch=(scratch_ref,),
    )
    monkeypatch.setattr(tp, "observe_preserve_debt", lambda _repo: observation)
    monkeypatch.setattr(tp, "list_preserves", lambda _repo: [])
    monkeypatch.setattr(tp, "list_local_preserve_tags", lambda _repo: [local_tag])
    monkeypatch.setattr(tp, "ref_on_origin", lambda _repo, _ref: False)

    result = _scan(repo_root=repo, home=home, slug="acme")

    assert any(i.abandon_token == "attempt-preserve/run1-attempt" for i in result.items)
    assert "preserve/acme/1.1/dispatch-abc12345" in result.preserve_debt_tags


def test_scan_branch_unpreserved_and_origin_skips_primary(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    repo.mkdir()
    home.mkdir()
    vcs = FakeVcs(repo_root=repo)
    vcs.remote_branches = {"loop/acme"}
    vcs.refs["loop/acme"] = "orphan-tip"
    vcs.refs["orphan-branch"] = "orphan-tip2"

    result = _scan(repo_root=repo, home=home, branch="orphan-branch", vcs=vcs)

    tokens = {i.abandon_token for i in result.items}
    assert "orphan-branch" in tokens

    on_origin = _scan(repo_root=repo, home=home, branch="loop/acme", vcs=vcs)
    assert "loop/acme" not in {i.abandon_token for i in on_origin.items}


def test_scan_nested_bmad_loop_branch_and_worktree_fallback(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    repo.mkdir()
    home.mkdir()
    (home / ".bmad-loop" / "runs" / "run1").mkdir(parents=True)
    nested_path = home / "nested-wt"
    nested_path.mkdir()
    nested = (
        WorktreeEntry(path=nested_path, branch="bmad-loop/run1/story"),
        WorktreeEntry(path=home / "other", branch="feature/unrelated"),
    )
    vcs = FakeVcs(repo_root=repo)
    vcs.fail_list_worktrees = VcsCommandError("list failed")
    vcs.refs["bmad-loop/run1/story"] = "tip-sha"

    result = _scan(
        repo_root=repo,
        home=home,
        branch="loop/acme",
        vcs=vcs,
        nested=nested,
    )

    assert any(i.abandon_token == "bmad-loop/run1/story" for i in result.items)


def test_scan_resolve_ref_failure_skips_branch(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    repo.mkdir()
    home.mkdir()

    class _Vcs(FakeVcs):
        def resolve_ref(self, repo_root: Path, ref: str) -> str:
            raise VcsCommandError("missing")

    vcs = _Vcs(repo_root=repo)

    result = _scan(repo_root=repo, home=home, branch="missing-branch", vcs=vcs)

    assert result.items == ()


def test_commit_needs_preserve_respects_durable_refs(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    repo.mkdir()
    home.mkdir()

    class _Vcs(FakeVcs):
        def is_commit_ancestor(self, repo_root: Path, ancestor: str, descendant: str) -> bool:
            return ancestor == "merged-tip"

        def commit_contained_in_tag_prefixes(self, repo_root: Path, commit: str, tag_prefixes: tuple[str, ...]) -> bool:
            return commit == "tagged-tip"

        def commit_contained_in_remote_refs(self, repo_root: Path, commit: str) -> bool:
            return commit == "remote-tip"

    vcs = _Vcs(repo_root=repo)
    assert tp._commit_needs_preserve(vcs, repo, "merged-tip") is False
    assert tp._commit_needs_preserve(vcs, repo, "tagged-tip") is False
    assert tp._commit_needs_preserve(vcs, repo, "remote-tip") is False
    assert tp._commit_needs_preserve(vcs, repo, "lonely-tip") is True


def test_helpers_patch_tokens_and_preserve_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    outside = tmp_path / "outside.patch"
    assert tp._patch_abandon_token(home, outside) == outside.as_posix()

    rel_patch = home / "p" / "changes.patch"
    rel_patch.parent.mkdir(parents=True)
    sources = frozenset({str(rel_patch), rel_patch.name, "p/changes.patch"})
    assert tp._patch_covered_by_preserve(home, rel_patch, sources) is True

    record = PreserveRecord(
        refname="refs/tags/preserve/acme/1.1/dispatch-deadbeef",
        object_sha="deadbeef",
        project_slug="acme",
        story_key="1.1",
        producer="dispatch",
        sha8="deadbeef",
        state=PreserveState.OPEN,
        trailers=PreserveTrailers(
            producer="dispatch",
            provenance="test",
            reason="test",
            source="p/changes.patch",
            run="run1",
            journal="j",
            commit="c",
        ),
    )
    monkeypatch.setattr(tp, "list_preserves", lambda _repo: [record])
    assert "p/changes.patch" in tp._preserve_sources_for_home(tmp_path, home)

    monkeypatch.setattr(tp, "list_preserves", lambda _repo: (_ for _ in ()).throw(RuntimeError("boom")))
    assert tp._preserve_sources_for_home(tmp_path, home) == frozenset()

    assert tp._scratch_belongs_to_home("refs/heads/attempt-preserve-dirty/foo", frozenset()) is True
    assert tp._scratch_belongs_to_home("refs/heads/attempt-preserve/run9-x", frozenset({"run9"})) is True
    assert tp._bmad_loop_branch_belongs(frozenset({"run1"}), "bmad-loop/run1/story") is True
    assert tp._bmad_loop_branch_belongs(frozenset(), "loop/acme") is False
