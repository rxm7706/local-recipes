"""Unit tests for Story 28.21 — push dispatch branch before verify (CAP-4)."""

from __future__ import annotations

import json
from pathlib import Path

from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core.dispatch_completion import DispatchGitFacts
from pyforge.marshal.core.dispatch_push import may_push_dispatch_branch_before_verify
from pyforge.marshal.core.journal import JournalEntryId, Phase, build_entry, fold, prepare_for_write
from pyforge.marshal.dispatch_supervisor.__main__ import (
    _dispatch_push_already_journaled,
    _run_and_journal_dispatch_push,
)

_STORY_KEY = "28.21"
_BRANCH = dispatch_core.dispatch_worktree_branch("pyforge-marshal", _STORY_KEY)


def _git_facts(
    *,
    baseline: str = "baseline0001",
    current: str = "story0002",
    changed_paths: tuple[str, ...] = (),
) -> DispatchGitFacts:
    return DispatchGitFacts(
        baseline_head_sha=baseline,
        current_head_sha=current,
        changed_paths=changed_paths,
        branch_merged=False,
        story_merged_on_main=False,
    )


def test_may_push_requires_git_progress() -> None:
    assert not may_push_dispatch_branch_before_verify(
        _git_facts(baseline="same", current="same"),
    )
    assert may_push_dispatch_branch_before_verify(_git_facts())
    assert may_push_dispatch_branch_before_verify(
        _git_facts(baseline="same", current="same", changed_paths=("src/a.py",)),
    )


def test_may_push_refuses_unattributable_branch() -> None:
    assert not may_push_dispatch_branch_before_verify(
        _git_facts(),
        branch_refusal="legacy branch unattributable",
    )


class FakeFs:
    def __init__(self) -> None:
        self.files: dict[Path, str] = {}
        self.appended: list[tuple[Path, str, bool]] = []

    def append_line(self, path: Path, line: str, *, fsync: bool) -> None:
        self.appended.append((path, line, fsync))
        text = self.files.get(path, "")
        if text and not text.endswith("\n"):
            text += "\n"
        self.files[path] = text + line + "\n"

    def write_text_atomic(self, path: Path, content: str) -> None:
        self.files[path] = content


class FakeVcs:
    def __init__(
        self,
        repo_root: Path,
        *,
        branch: str = _BRANCH,
    ) -> None:
        self.repo_root = repo_root
        self.branch = branch
        self.pushed: list[str] = []
        self.fail_push: Exception | None = None

    def branch_exists(self, _repo_root: Path, branch: str) -> bool:
        return branch == self.branch

    def worktree_path_for_branch(self, _repo_root: Path, _branch: str) -> Path | None:
        return None

    def push(self, repo_root: Path, branch: str) -> None:
        self.pushed.append(branch)
        if self.fail_push:
            raise self.fail_push


def test_run_and_journal_dispatch_push_pushes_before_verify(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    journal_path = run_dir / "journal.jsonl"
    fs = FakeFs()
    fs.files[journal_path] = ""
    vcs = FakeVcs(tmp_path)

    counter = _run_and_journal_dispatch_push(
        fs=fs,
        vcs=vcs,
        run_dir=run_dir,
        run_id="run-28-21",
        writer_id="test-writer",
        counter=0,
        repo_root=tmp_path,
        slug="pyforge-marshal",
        story_key=_STORY_KEY,
        worktree=tmp_path / "wt",
        git_facts=_git_facts(),
    )

    assert counter == 2
    assert vcs.pushed == [_BRANCH]
    lines = fs.files[journal_path].splitlines()
    assert len(lines) == 2
    entries = [json.loads(line) for line in lines]
    assert entries[0]["kind"] == dispatch_core.KIND_DISPATCH_PUSH
    assert entries[0]["phase"] == Phase.INTENT.value
    assert entries[1]["phase"] == Phase.OUTCOME.value
    assert entries[1]["payload"]["outcome"] == "pushed"
    assert entries[1]["payload"]["ok"] is True


def test_run_and_journal_dispatch_push_pushes_unresolved_branch_name(
    tmp_path: Path,
) -> None:
    """First push may mint ``origin/dispatch/...`` before the ref existed locally."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    journal_path = run_dir / "journal.jsonl"
    fs = FakeFs()
    fs.files[journal_path] = ""
    vcs = FakeVcs(tmp_path, branch="dispatch/pyforge-marshal/not-this-one")

    counter = _run_and_journal_dispatch_push(
        fs=fs,
        vcs=vcs,
        run_dir=run_dir,
        run_id="run-mint",
        writer_id="test-writer",
        counter=0,
        repo_root=tmp_path,
        slug="pyforge-marshal",
        story_key=_STORY_KEY,
        worktree=tmp_path / "wt",
        git_facts=_git_facts(),
    )

    assert counter == 2
    assert vcs.pushed == [_BRANCH]


def test_run_and_journal_dispatch_push_skips_without_git_progress(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    journal_path = run_dir / "journal.jsonl"
    fs = FakeFs()
    fs.files[journal_path] = ""
    vcs = FakeVcs(tmp_path)

    counter = _run_and_journal_dispatch_push(
        fs=fs,
        vcs=vcs,
        run_dir=run_dir,
        run_id="run-empty",
        writer_id="test-writer",
        counter=0,
        repo_root=tmp_path,
        slug="pyforge-marshal",
        story_key=_STORY_KEY,
        worktree=tmp_path / "wt",
        git_facts=_git_facts(baseline="same", current="same"),
    )

    assert counter == 0
    assert vcs.pushed == []
    assert fs.files[journal_path] == ""


def test_run_and_journal_dispatch_push_journals_push_failure(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    journal_path = run_dir / "journal.jsonl"
    fs = FakeFs()
    fs.files[journal_path] = ""
    vcs = FakeVcs(tmp_path)
    vcs.fail_push = VcsCommandError("no network")

    _run_and_journal_dispatch_push(
        fs=fs,
        vcs=vcs,
        run_dir=run_dir,
        run_id="run-fail",
        writer_id="test-writer",
        counter=0,
        repo_root=tmp_path,
        slug="pyforge-marshal",
        story_key=_STORY_KEY,
        worktree=tmp_path / "wt",
        git_facts=_git_facts(),
    )

    outcome = json.loads(fs.files[journal_path].splitlines()[1])
    assert outcome["payload"]["outcome"] == "push-failed"
    assert outcome["payload"]["ok"] is False
    assert outcome["payload"]["finding"]["code"] == "MRS-DISP-037"


def test_dispatch_push_already_journaled() -> None:
    line = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 1),
            ts="2026-09-01T00:00:00.000Z",
            run_id="run-1",
            kind=dispatch_core.KIND_DISPATCH_PUSH,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 0),
            payload={"ok": True},
        )
    ).line
    folded = fold([line])
    assert _dispatch_push_already_journaled(folded, "run-1")
    assert not _dispatch_push_already_journaled(folded, "run-2")
