"""Story 87.5: dispatch preserve tags on origin (flag on/off + mutations)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pyforge.core.preserve_refs import (
    PreserveTrailers,
    list_local_preserve_tags,
    ref_on_origin,
    render_preserve_ref,
    snapshot_worktree_commit,
    tag_preserve,
)
from pyforge.testing_kit.flags import flag_states, flagd_tree

from pyforge.marshal.adapters.fs_local import LocalFs
from pyforge.marshal.adapters.vcs_git import GitVcs
from pyforge.marshal.cli.dispatch import gather_dispatch_journal_facts
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core.dispatch_completion import DispatchSessionVerdict
from pyforge.marshal.core.dispatch_preserve import (
    PRESERVE_REFS_FLAG_KEY,
    should_journal_dispatch_preserve,
    tag_dispatch_worktree_preserve,
)
from pyforge.marshal.core.journal import Phase, build_entry, prepare_for_write
from pyforge.marshal.core.status import FleetHomeFacts, _merge_dispatch_row_fields
from pyforge.marshal.dispatch_supervisor import __main__ as supervisor_main

_FLAG = PRESERVE_REFS_FLAG_KEY
_SLUG = "pyforge-marshal"
_STORY = "87.5"
_RUN_ID = "20261009-abc12345"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


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
    (repo / "tracked.txt").write_text("v1\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt", "docs/governance/preserve-purge-list.json")
    _git(repo, "commit", "-m", "init")
    _git(repo, "branch", "-M", "main")
    _git(repo, "remote", "add", "origin", str(bare))
    _git(repo, "push", "-u", "origin", "main")
    _git(repo, "fetch", "origin")
    return repo, bare


def _run_dir(repo_root: Path) -> Path:
    path = dispatch_core.dispatch_run_dir(repo_root, _SLUG, _RUN_ID)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _journal_preserve_outcome(run_dir: Path, *, preserve_tag: str | None = None) -> None:
    from pyforge.marshal.core.journal import JournalEntryId

    writer = "test-writer"
    intent = build_entry(
        id=JournalEntryId(writer, 0),
        ts="2026-10-09T12:00:00.000Z",
        run_id=_RUN_ID,
        kind=dispatch_core.KIND_DISPATCH_PRESERVE,
        phase=Phase.INTENT,
        payload={"preserve_ref": "failed/87.5/changes.patch", "story_key": _STORY},
    )
    outcome_payload: dict[str, object] = {
        "preserve_ref": "failed/87.5/changes.patch",
        "ok": True,
    }
    if preserve_tag is not None:
        outcome_payload["preserve_tag"] = preserve_tag
    outcome = build_entry(
        id=JournalEntryId(writer, 1),
        ts="2026-10-09T12:00:01.000Z",
        run_id=_RUN_ID,
        kind=dispatch_core.KIND_DISPATCH_PRESERVE,
        phase=Phase.OUTCOME,
        intent_id=intent.id,
        payload=outcome_payload,
    )
    journal = run_dir / "journal.jsonl"
    journal.write_text(
        prepare_for_write(intent).line + "\n" + prepare_for_write(outcome).line + "\n",
        encoding="utf-8",
    )


@flag_states(_FLAG)
def test_should_journal_dispatch_preserve_flag_off_only_failed(
    flag_provider: dict[str, bool],
):
    flag_on = flag_provider[_FLAG]
    for verdict in (
        DispatchSessionVerdict.FAILED,
        DispatchSessionVerdict.STOPPED_EXTERNALLY,
        DispatchSessionVerdict.BLOCKED,
    ):
        got = should_journal_dispatch_preserve(flag_on=flag_on, verdict=verdict, has_progress=True)
        if flag_on:
            assert got is True
        else:
            assert got is (verdict is DispatchSessionVerdict.FAILED)


def test_should_journal_dispatch_preserve_requires_progress():
    assert (
        should_journal_dispatch_preserve(
            flag_on=True,
            verdict=DispatchSessionVerdict.FAILED,
            has_progress=False,
        )
        is False
    )


def test_mutation_stopped_verdict_requires_flag_on():
    assert (
        should_journal_dispatch_preserve(
            flag_on=False,
            verdict=DispatchSessionVerdict.STOPPED_EXTERNALLY,
            has_progress=True,
        )
        is False
    )


@flag_states(_FLAG)
def test_supervisor_preserve_journals_tag_when_flag_on(
    git_pair: tuple[Path, Path],
    flag_provider: dict[str, bool],
    monkeypatch: pytest.MonkeyPatch,
):
    repo, _bare = git_pair
    flags_path = flagd_tree(repo, {_FLAG: "on" if flag_provider[_FLAG] else "off"})
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flags_path))
    (repo / "tracked.txt").write_text("v2\n", encoding="utf-8")
    (repo / "u.txt").write_text("untracked\n", encoding="utf-8")
    run_dir = _run_dir(repo)
    fs = LocalFs()
    vcs = GitVcs()
    baseline = vcs.worktree_head_sha(repo)
    counter = supervisor_main._journal_dispatch_preserve(
        fs=fs,
        vcs=vcs,
        run_dir=run_dir,
        run_id=_RUN_ID,
        writer_id="dispatch-supervisor-test",
        counter=0,
        story_key=_STORY,
        worktree=repo,
        baseline_head_sha=baseline,
        repo_root=repo,
        project_slug=_SLUG,
        completion_verdict="failed",
    )
    assert counter == 2
    facts = gather_dispatch_journal_facts(fs, run_dir, _RUN_ID)
    assert facts.preserve_ref is not None
    if flag_provider[_FLAG]:
        assert facts.preserve_tag is not None
        assert facts.preserve_tag.startswith("preserve/")
        tags = list_local_preserve_tags(repo)
        assert any(t.refname.endswith(facts.preserve_tag.split("/", 1)[-1]) or facts.preserve_tag in t.refname for t in tags)
    else:
        assert facts.preserve_tag is None


@flag_states(_FLAG)
def test_tag_dedup_writes_one_local_tag(
    git_pair: tuple[Path, Path],
    flag_provider: dict[str, bool],
    monkeypatch: pytest.MonkeyPatch,
):
    if not flag_provider[_FLAG]:
        pytest.skip("dedup applies when preserve refs are enabled")
    repo, _bare = git_pair
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(repo, {_FLAG: "on"})))
    (repo / "w.txt").write_text("work\n", encoding="utf-8")
    vcs = GitVcs()
    kwargs = dict(
        vcs=vcs,
        repo_root=repo,
        worktree=repo,
        project_slug=_SLUG,
        story_key=_STORY,
        run_id=_RUN_ID,
        journal_path="journal.jsonl",
        reason="dispatch failed",
        push=False,
    )
    first = tag_dispatch_worktree_preserve(**kwargs)
    second = tag_dispatch_worktree_preserve(**kwargs)
    assert first is not None and second is not None
    assert first.refname == second.refname
    assert second.noop is True
    assert len(list_local_preserve_tags(repo)) == 1


def test_mutation_dedup_second_tag_would_fail_without_noop(git_pair: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch):
    repo, _bare = git_pair
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(repo, {_FLAG: "on"})))
    (repo / "w.txt").write_text("work\n", encoding="utf-8")
    vcs = GitVcs()
    kwargs = dict(
        vcs=vcs,
        repo_root=repo,
        worktree=repo,
        project_slug=_SLUG,
        story_key=_STORY,
        run_id=_RUN_ID,
        journal_path="journal.jsonl",
        reason="dispatch failed",
        push=False,
    )
    tag_dispatch_worktree_preserve(**kwargs)
    commit = snapshot_worktree_commit(repo) or vcs.worktree_head_sha(repo)
    refname = render_preserve_ref(
        commit_sha=commit,
        producer="dispatch",
        project_slug=_SLUG,
        story_key=_STORY,
    )
    trailers = PreserveTrailers(
        producer="dispatch",
        provenance="machine",
        reason="duplicate",
        source=str(repo),
        run="other",
        journal="j",
        commit=commit,
    )
    result = tag_preserve(repo, refname=refname, commit=commit, trailers=trailers)
    assert result.noop is True


def test_status_row_shows_dispatch_preserve_tag():
    facts = FleetHomeFacts(
        slug=_SLUG,
        branch=f"loop/{_SLUG}",
        has_run=True,
        dispatch_story=_STORY,
        dispatch_preserve_tag="preserve/pyforge-marshal/87.5/dispatch-deadbeef",
    )
    row = _merge_dispatch_row_fields({}, facts)
    assert row["dispatch_preserve_tag"] == "preserve/pyforge-marshal/87.5/dispatch-deadbeef"


def test_gather_journal_reads_preserve_tag(git_pair: tuple[Path, Path]):
    repo, _bare = git_pair
    run_dir = _run_dir(repo)
    tag = "preserve/pyforge-marshal/87.5/dispatch-01234567"
    _journal_preserve_outcome(run_dir, preserve_tag=tag)
    fs = LocalFs()
    facts = gather_dispatch_journal_facts(fs, run_dir, _RUN_ID)
    assert facts.preserve_tag == tag


@flag_states(_FLAG)
def test_untracked_file_in_preserve_tree(
    git_pair: tuple[Path, Path],
    flag_provider: dict[str, bool],
    monkeypatch: pytest.MonkeyPatch,
):
    if not flag_provider[_FLAG]:
        pytest.skip("flag-on only")
    repo, bare = git_pair
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(repo, {_FLAG: "on"})))
    untracked = repo / "only-local.txt"
    untracked.write_text("secret sauce\n", encoding="utf-8")
    vcs = GitVcs()
    outcome = tag_dispatch_worktree_preserve(
        vcs=vcs,
        repo_root=repo,
        worktree=repo,
        project_slug=_SLUG,
        story_key=_STORY,
        run_id=_RUN_ID,
        journal_path="j",
        reason="dispatch stopped_externally",
        push=True,
    )
    assert outcome is not None
    assert ref_on_origin(repo, outcome.refname)
    short = outcome.refname.removeprefix("refs/tags/")
    _git(repo, "fetch", "origin", f"refs/tags/{short}:refs/tags/{short}")
    show = subprocess.check_output(
        ["git", "show", f"{outcome.refname}^{{tree}}:only-local.txt"],
        cwd=repo,
        text=True,
    )
    assert "secret sauce" in show
