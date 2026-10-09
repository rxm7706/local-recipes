"""Unit tests for ``pyforge.core.preserve_refs`` (Story 87.3)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from pyforge.core.preserve_refs import (
    PRESERVE_PRODUCERS,
    ContentGateReason,
    PreserveRefConflictError,
    PreserveRefNameError,
    PreserveState,
    PreserveTrailers,
    PurgeList,
    list_preserves,
    parse_archive_ref,
    parse_preserve_ref,
    push_preserve_ref,
    render_archive_heads_ref,
    render_archive_tags_ref,
    render_preserve_ref,
    run_content_gate,
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


def _write_purge_list(repo: Path, *, shas: tuple[str, ...] = (), paths: tuple[str, ...] = ()) -> Path:
    path = repo / "purge-list.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"schema_version": 1, "commit_shas": list(shas), "paths": list(paths)}),
        encoding="utf-8",
    )
    return path


def test_content_gate_refuses_secret_and_oversize(git_pair: tuple[Path, Path]):
    repo, _bare = git_pair
    (repo / "tracked.txt").write_text("sk-ant-api03-SYNTHETICTEST0000000000000000\n", encoding="utf-8")
    _run(repo, "add", "tracked.txt")
    _run(repo, "commit", "-m", "secret")
    bad = _run(repo, "rev-parse", "HEAD").stdout.strip()
    secret_hits = run_content_gate(repo, commit=bad, purge_list=PurgeList(frozenset(), frozenset()))
    assert any(f.reason is ContentGateReason.SECRET for f in secret_hits)

    (repo / "big.bin").write_bytes(b"x" * (5 * 1024 * 1024 + 1))
    _run(repo, "add", "big.bin")
    _run(repo, "commit", "-m", "big")
    big = _run(repo, "rev-parse", "HEAD").stdout.strip()
    size_hits = run_content_gate(repo, commit=big, purge_list=PurgeList(frozenset(), frozenset()))
    assert any(f.reason is ContentGateReason.SIZE_CAP for f in size_hits)

    ancestor = _run(repo, "rev-parse", "HEAD~1").stdout.strip()
    purge = PurgeList(frozenset({ancestor}), frozenset())
    sha_hits = run_content_gate(repo, commit=bad, purge_list=purge)
    assert any(f.reason is ContentGateReason.PURGE_SHA for f in sha_hits)

    purge_path = PurgeList(frozenset(), frozenset({"tracked.txt"}))
    path_hits = run_content_gate(repo, commit=bad, purge_list=purge_path)
    assert any(f.reason is ContentGateReason.PURGE_PATH for f in path_hits)


def test_push_one_refspec_and_verifies_remote(git_pair: tuple[Path, Path]):
    repo, bare = git_pair
    commit = _run(repo, "rev-parse", "HEAD").stdout.strip()
    ref = render_preserve_ref(commit_sha=commit, producer="hand", project_slug="pyforge-marshal", story_key="87.15")
    tag_preserve(repo, refname=ref, commit=commit, trailers=_trailers(commit))
    purge_path = _write_purge_list(repo)
    result = push_preserve_ref(repo, ref, purge_list_path=purge_path, remote="origin")
    assert result.pushed is True
    remote_out = _run(repo, "ls-remote", "origin", ref).stdout.strip()
    assert remote_out


def test_push_refused_tag_stays_local(git_pair: tuple[Path, Path]):
    repo, _ = git_pair
    (repo / "tracked.txt").write_text("sk-ant-api03-SYNTHETICTEST0000000000000000\n", encoding="utf-8")
    _run(repo, "add", "tracked.txt")
    _run(repo, "commit", "-m", "secret")
    commit = _run(repo, "rev-parse", "HEAD").stdout.strip()
    ref = render_preserve_ref(commit_sha=commit, producer="hand", project_slug="pyforge-marshal", story_key="87.15")
    tag_preserve(repo, refname=ref, commit=commit, trailers=_trailers(commit))
    purge_path = _write_purge_list(repo)
    result = push_preserve_ref(repo, ref, purge_list_path=purge_path)
    assert result.pushed is False
    assert any(f.reason is ContentGateReason.SECRET for f in result.findings)
    remote = subprocess.run(["git", "ls-remote", "origin", ref], cwd=repo, capture_output=True, text=True)
    assert remote.stdout.strip() == ""


def test_push_cap_refuses_excess(git_pair: tuple[Path, Path]):
    repo, _ = git_pair
    commit = _run(repo, "rev-parse", "HEAD").stdout.strip()
    purge_path = _write_purge_list(repo)
    refs: list[str] = []
    for i in range(3):
        ref = render_preserve_ref(
            commit_sha=commit, producer="hand", project_slug="pyforge-marshal", story_key=f"87.{i}"
        )
        tag_preserve(repo, refname=ref, commit=commit, trailers=_trailers(commit))
        refs.append(ref)
    result = push_preserve_ref(
        repo,
        refs[0],
        purge_list_path=purge_path,
        run_push_count=20,
        max_per_run=20,
    )
    assert result.pushed is False
    assert any(f.reason is ContentGateReason.PUSH_CAP_RUN for f in result.findings)


def test_content_gate_mutation_secret_rule_required(git_pair: tuple[Path, Path]):
    """Removing the secret-scan rule must fail this guard."""
    import pyforge.core.preserve_refs as mod

    repo, _ = git_pair
    (repo / "tracked.txt").write_text("sk-ant-api03-SYNTHETICTEST0000000000000000\n", encoding="utf-8")
    _run(repo, "add", "tracked.txt")
    _run(repo, "commit", "-m", "secret")
    commit = _run(repo, "rev-parse", "HEAD").stdout.strip()
    empty_patterns: tuple[tuple[str, object], ...] = ()
    original = mod._SECRET_PATTERNS
    mod._SECRET_PATTERNS = empty_patterns  # type: ignore[assignment]
    try:
        findings = run_content_gate(repo, commit=commit, purge_list=PurgeList(frozenset(), frozenset()))
        assert not any(f.reason is ContentGateReason.SECRET for f in findings)
    finally:
        mod._SECRET_PATTERNS = original
    findings = run_content_gate(repo, commit=commit, purge_list=PurgeList(frozenset(), frozenset()))
    assert any(f.reason is ContentGateReason.SECRET for f in findings)
