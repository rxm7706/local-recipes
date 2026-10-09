"""Story 87.4: engine scratch ref promotion to preserve tags."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pyforge.core.preserve_refs import list_local_preserve_tags, ref_on_origin
from pyforge.testing_kit.flags import flag_states

from pyforge.marshal.ports.harness import DeferredStory, TaskPhaseSnapshot
from pyforge.marshal.supervisor.engine_preserve import (
    promote_engine_ref,
    read_new_journal_objects,
    reconcile_unpromoted_engine_refs,
    tag_intent_gap_attempt,
    targets_from_journal_events,
    targets_from_run_snapshot,
)

_FLAG = "pyforge.marshal.preserve_refs"
_SLUG = "pyforge-marshal"
_STORY = "87.4"
_RUN = "20261009-run1"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)


@pytest.fixture
def git_pair(tmp_path: Path) -> tuple[Path, Path]:
    bare = tmp_path / "origin.git"
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "--bare", str(bare)], cwd=tmp_path, check=True)
    subprocess.run(["git", "init", str(repo)], cwd=tmp_path, check=True)
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    purge_dir = repo / "docs" / "governance"
    purge_dir.mkdir(parents=True, exist_ok=True)
    (purge_dir / "preserve-purge-list.json").write_text(
        '{"schema_version": 1, "commit_shas": [], "paths": []}\n',
        encoding="utf-8",
    )
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "init")
    _git(repo, "branch", "-M", "main")
    _git(repo, "remote", "add", "origin", str(bare))
    _git(repo, "push", "-u", "origin", "main")
    _git(repo, "fetch", "origin")
    return repo, bare


def test_journal_event_extraction():
    events = (
        {
            "kind": "attempt-commits-preserved",
            "payload": {"story_key": "87-4", "ref": "attempt-preserve/run-deadbeef"},
        },
        {"kind": "worktree-kept", "payload": {"story_key": "1.1", "path": "/tmp/wt"}},
        {
            "kind": "story-deferred",
            "payload": {"story_key": "87-4", "preserve_ref": "attempt-preserve/x-y"},
        },
    )
    targets = targets_from_journal_events(events)
    refs = {t.engine_ref for t in targets}
    assert refs == {"attempt-preserve/run-deadbeef", "attempt-preserve/x-y"}


def test_read_new_journal_objects_byte_offset(tmp_path: Path):
    journal = tmp_path / "journal.jsonl"
    journal.write_text('{"kind":"a"}\n', encoding="utf-8")
    first, off1 = read_new_journal_objects(journal, byte_offset=0)
    assert len(first) == 1
    journal.write_text('{"kind":"a"}\n{"kind":"b"}\n', encoding="utf-8")
    second, off2 = read_new_journal_objects(journal, byte_offset=off1)
    assert [e.get("kind") for e in second] == ["b"]
    assert off2 == len(journal.read_bytes())


@flag_states(_FLAG)
def test_promote_engine_ref_tags_and_pushes(git_pair: tuple[Path, Path], flag_provider: dict[str, bool]):
    if not flag_provider[_FLAG]:
        pytest.skip("preserve_refs flag off in this parametrization")
    repo, _bare = git_pair
    _git(repo, "branch", "-f", "attempt-preserve/run1-deadbeef", "HEAD")
    first = promote_engine_ref(
        repo,
        engine_ref="attempt-preserve/run1-deadbeef",
        project_slug=_SLUG,
        story_key=_STORY,
        run_id=_RUN,
        journal_path="/tmp/journal.jsonl",
        reason="test",
        push=True,
    )
    assert first is not None
    assert first.preserve_tag.startswith(f"preserve/{_SLUG}/87.4/bmad-loop-")
    assert ref_on_origin(repo, first.refname)
    second = promote_engine_ref(
        repo,
        engine_ref="attempt-preserve/run1-deadbeef",
        project_slug=_SLUG,
        story_key=_STORY,
        run_id=_RUN,
        journal_path="/tmp/journal.jsonl",
        reason="test",
        push=True,
    )
    assert second is not None
    assert second.noop


@flag_states(_FLAG)
def test_promote_uses_rev_parse_not_journal_sha(git_pair: tuple[Path, Path], flag_provider: dict[str, bool]):
    if not flag_provider[_FLAG]:
        pytest.skip("preserve_refs flag off")
    repo, _ = git_pair
    _git(repo, "branch", "-f", "attempt-preserve/run1-00000000", "HEAD")
    (repo / "moved.txt").write_text("m\n", encoding="utf-8")
    _git(repo, "add", "moved.txt")
    _git(repo, "commit", "-m", "move tip")
    live_tip = _git(repo, "rev-parse", "HEAD").stdout.strip()
    _git(repo, "branch", "-f", "attempt-preserve/run1-00000000", live_tip)
    outcome = promote_engine_ref(
        repo,
        engine_ref="attempt-preserve/run1-00000000",
        project_slug=_SLUG,
        story_key=_STORY,
        run_id=_RUN,
        journal_path="j",
        reason="test",
        push=False,
    )
    assert outcome is not None
    tags = list_local_preserve_tags(repo)
    assert tags[0].commit == live_tip


@flag_states(_FLAG)
def test_reconcile_lists_unpromoted_scratch(git_pair: tuple[Path, Path], flag_provider: dict[str, bool]):
    if not flag_provider[_FLAG]:
        pytest.skip("preserve_refs flag off")
    repo, _ = git_pair
    (repo / "orphan.txt").write_text("orphan\n", encoding="utf-8")
    _git(repo, "add", "orphan.txt")
    _git(repo, "commit", "-m", "orphan commit")
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    branch = f"attempt-preserve/orphan-{head[:8]}"
    _git(repo, "branch", branch, head)
    _git(repo, "reset", "--hard", "HEAD~1")
    scratch = reconcile_unpromoted_engine_refs(repo)
    assert branch in scratch


@flag_states(_FLAG)
def test_intent_gap_tag_shape(git_pair: tuple[Path, Path], flag_provider: dict[str, bool]):
    if not flag_provider[_FLAG]:
        pytest.skip("preserve_refs flag off")
    repo, _ = git_pair
    tip = _git(repo, "rev-parse", "HEAD").stdout.strip()
    out = tag_intent_gap_attempt(
        repo,
        tip_sha=tip,
        project_slug=_SLUG,
        story_key=_STORY,
        run_id=_RUN,
        journal_path="j",
        push=False,
    )
    assert out is not None
    assert out.preserve_tag.startswith(f"preserve/{_SLUG}/87.4/intent-gap-")


def test_targets_from_run_snapshot_skips_preserve_tags():
    task = TaskPhaseSnapshot(
        story_key="87.4",
        phase="dev-running",
        commit_sha=None,
        worktree_path="/tmp",
        baseline_commit="abc",
        preserve_ref="preserve/pyforge-marshal/87.4/bmad-loop-deadbeef",
    )
    deferred = (
        DeferredStory(
            story_key="87.5",
            reason="r",
            attempt=1,
            branch="b",
            worktree_path="/w",
            spec_file="s",
            preserve_ref="attempt-preserve/run-y",
        ),
    )
    targets = targets_from_run_snapshot([task], deferred)
    assert len(targets) == 1
    assert targets[0].engine_ref == "attempt-preserve/run-y"


def test_mutation_promotion_required(git_pair: tuple[Path, Path]):
    """Reconcile scan surfaces scratch when no preserve tag holds the commit."""
    repo, _ = git_pair
    (repo / "mut.txt").write_text("mut\n", encoding="utf-8")
    _git(repo, "add", "mut.txt")
    _git(repo, "commit", "-m", "mut commit")
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    branch = f"attempt-preserve/mut-{head[:8]}"
    _git(repo, "branch", branch, head)
    _git(repo, "reset", "--hard", "HEAD~1")
    assert reconcile_unpromoted_engine_refs(repo)
