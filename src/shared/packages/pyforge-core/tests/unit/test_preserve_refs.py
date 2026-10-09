"""Unit tests for ``pyforge.core.preserve_refs`` (Story 87.3)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pyforge.core.preserve_refs import (
    PRESERVE_PRODUCERS,
    PreserveRefConflictError,
    PreserveRefNameError,
    PreserveState,
    PreserveTrailers,
    list_preserves,
    parse_archive_ref,
    parse_preserve_ref,
    render_archive_heads_ref,
    render_archive_tags_ref,
    render_preserve_ref,
    snapshot_worktree_commit,
    tag_preserve,
)


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)


@pytest.fixture
def git_pair(tmp_path: Path) -> tuple[Path, Path]:
    """A repo with ``origin/main`` on a bare remote."""
    bare = tmp_path / "origin.git"
    work = tmp_path / "work"
    subprocess.run(["git", "init", "--bare", str(bare)], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "init", str(work)], cwd=tmp_path, check=True, capture_output=True, text=True)
    _run(work, "config", "user.email", "t@example.com")
    _run(work, "config", "user.name", "t")
    (work / "tracked.txt").write_text("v1\n", encoding="utf-8")
    _run(work, "add", "tracked.txt")
    _run(work, "commit", "-m", "init")
    _run(work, "remote", "add", "origin", str(bare))
    _run(work, "push", "-u", "origin", "HEAD:main")
    _run(work, "fetch", "origin")
    return work, bare


def _trailers(commit: str, *, producer: str = "hand") -> PreserveTrailers:
    return PreserveTrailers(
        producer=producer,
        provenance="human",
        reason="hand",
        source="test",
        run="run-1",
        journal="journal-1",
        commit=commit,
    )


@pytest.mark.parametrize("producer", sorted(PRESERVE_PRODUCERS))
def test_preserve_name_round_trip(producer: str):
    commit = "abcd1234" * 5
    shapes = (
        ("pyforge-marshal", "87.3"),
        (None, None),
    )
    for slug, story in shapes:
        ref = render_preserve_ref(commit_sha=commit, producer=producer, project_slug=slug, story_key=story)
        assert "2026-" not in ref and "2025-" not in ref
        parsed = parse_preserve_ref(ref)
        assert parsed.producer == producer
        assert parsed.sha8 == commit[:8].lower()
        assert parsed.refname == ref


def test_parse_rejects_malformed_preserve_names():
    with pytest.raises(PreserveRefNameError):
        parse_preserve_ref("refs/tags/" + "preserve/bad/extra/segments/hand-deadbeef")
    with pytest.raises(PreserveRefNameError):
        parse_preserve_ref("refs/tags/" + "preserve/unbound/unknown-deadbeef")


def test_archive_names_round_trip():
    heads = render_archive_heads_ref("loop/pyforge-marshal")
    tags = render_archive_tags_ref("rescue/foo")
    assert parse_archive_ref(heads).path == "loop/pyforge-marshal"
    assert parse_archive_ref(tags).kind == "tags"


def test_snapshot_includes_untracked_without_moving_head(git_pair: tuple[Path, Path]):
    repo, _ = git_pair
    head_before = _run(repo, "rev-parse", "HEAD").stdout.strip()
    branch_before = _run(repo, "symbolic-ref", "HEAD").stdout.strip()
    (repo / "tracked.txt").write_text("v2\n", encoding="utf-8")
    (repo / "new.txt").write_text("new\n", encoding="utf-8")
    snap = snapshot_worktree_commit(repo)
    assert snap is not None
    head_after = _run(repo, "rev-parse", "HEAD").stdout.strip()
    assert head_after == head_before
    assert _run(repo, "symbolic-ref", "HEAD").stdout.strip() == branch_before
    assert "new.txt" in _run(repo, "ls-tree", "-r", "--name-only", snap).stdout
    assert _run(repo, "show", f"{snap}:tracked.txt").stdout.strip() == "v2"


def test_tag_noop_same_name_same_object(git_pair: tuple[Path, Path]):
    repo, _ = git_pair
    commit = _run(repo, "rev-parse", "HEAD").stdout.strip()
    ref = render_preserve_ref(commit_sha=commit, producer="hand", project_slug="pyforge-marshal", story_key="87.3")
    first = tag_preserve(repo, refname=ref, commit=commit, trailers=_trailers(commit))
    second = tag_preserve(repo, refname=ref, commit=commit, trailers=_trailers(commit))
    assert first.noop is False
    assert second.noop is True


def test_tag_refuses_same_name_different_object(git_pair: tuple[Path, Path]):
    repo, _ = git_pair
    base = _run(repo, "rev-parse", "HEAD").stdout.strip()
    ref = render_preserve_ref(commit_sha=base, producer="hand", project_slug="pyforge-marshal", story_key="87.3")
    tag_preserve(repo, refname=ref, commit=base, trailers=_trailers(base))
    (repo / "tracked.txt").write_text("other\n", encoding="utf-8")
    _run(repo, "add", "tracked.txt")
    _run(repo, "commit", "-m", "other")
    other = _run(repo, "rev-parse", "HEAD").stdout.strip()
    with pytest.raises(PreserveRefConflictError):
        tag_preserve(repo, refname=ref, commit=other, trailers=_trailers(other))


def test_story_tree_dedup_is_noop(git_pair: tuple[Path, Path]):
    repo, _ = git_pair
    (repo / "tracked.txt").write_text("dedup\n", encoding="utf-8")
    snap = snapshot_worktree_commit(repo)
    assert snap is not None
    ref_a = render_preserve_ref(commit_sha=snap, producer="hand", project_slug="pyforge-marshal", story_key="87.3")
    ref_b = render_preserve_ref(commit_sha=snap, producer="dispatch", project_slug="pyforge-marshal", story_key="87.3")
    tag_preserve(repo, refname=ref_a, commit=snap, trailers=_trailers(snap, producer="hand"))
    result = tag_preserve(repo, refname=ref_b, commit=snap, trailers=_trailers(snap, producer="dispatch"))
    assert result.noop is True
    assert result.refname == ref_a


def test_list_filters_and_landed_state(git_pair: tuple[Path, Path]):
    repo, _ = git_pair
    on_main = _run(repo, "rev-parse", "HEAD").stdout.strip()
    ref_main = render_preserve_ref(
        commit_sha=on_main, producer="hand", project_slug="pyforge-marshal", story_key="87.1"
    )
    tag_preserve(repo, refname=ref_main, commit=on_main, trailers=_trailers(on_main))
    (repo / "tracked.txt").write_text("side\n", encoding="utf-8")
    _run(repo, "add", "tracked.txt")
    _run(repo, "commit", "-m", "side")
    side = _run(repo, "rev-parse", "HEAD").stdout.strip()
    ref_open = render_preserve_ref(commit_sha=side, producer="dispatch", project_slug="pyforge-mason", story_key="2.4")
    tag_preserve(repo, refname=ref_open, commit=side, trailers=_trailers(side, producer="dispatch"))
    landed = list_preserves(repo, state=PreserveState.LANDED)
    assert len(landed) == 1
    assert landed[0].story_key == "87.1"
    open_rows = list_preserves(repo, station="pyforge-mason", producer="dispatch", state=PreserveState.OPEN)
    assert len(open_rows) == 1
    assert open_rows[0].trailers.producer == "dispatch"
