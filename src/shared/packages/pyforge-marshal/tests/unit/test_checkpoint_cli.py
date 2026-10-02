"""``marshal factory checkpoint`` (Story 34.2; Story 82.9 routes its commit through ``CommitPort``).

``cli/checkpoint.py`` had no direct tests, and its three precondition findings (``MRS-CHK-001``/``002``/
``003``) were never registered, so every failure path raised ``UnregisteredFindingCodeError`` out of
``Finding(...)`` instead of exiting non-zero. Story 82.9 touched the module (its ``vcs`` is now a
``CommittingVcs``), which put it under the touched-module coverage floor; these tests cover every branch.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

import pytest
from pyforge.core.process import PosixProcess

from pyforge.marshal.adapters.fs_local import LocalFs
from pyforge.marshal.adapters.vcs_git import GitVcs, VcsCommandError
from pyforge.marshal.cli import checkpoint as checkpoint_module
from pyforge.marshal.core.egress import Redacted


class _Vcs:
    """The reads and the one commit ``commit_worktree_checkpoint`` makes."""

    def __init__(self, *, root: Path | None = None, not_a_repo: bool = False, dirty: bool = True, commit_raises=False):
        self._root = root
        self._not_a_repo = not_a_repo
        self._dirty = dirty
        self._commit_raises = commit_raises
        self.commits: list[tuple[Path, tuple[Path, ...], object]] = []

    def repo_common_root(self, start):
        if self._not_a_repo:
            raise VcsCommandError("fatal: not a git repository")
        return self._root if self._root is not None else start

    def has_uncommitted_changes(self, worktree_path):
        return self._dirty

    def changed_files(self, repo_root, worktree_path, *, base):
        return ("work.txt",)

    def commit_paths(self, repo_root, paths, message):
        if self._commit_raises:
            raise VcsCommandError("git commit failed: hook rejected")
        self.commits.append((repo_root, tuple(paths), message))
        return "feedface"


def _journal(*, worktree: Path | None, story: str | None):
    return SimpleNamespace(worktree_path=str(worktree) if worktree is not None else None, story_key=story)


def _context(tmp_path: Path, journal):
    return (tmp_path, tmp_path / "run", "run-1", journal, None)


def _patch_context(monkeypatch, value):
    monkeypatch.setattr(checkpoint_module, "_load_latest_dispatch_context", lambda **kwargs: value)


def test_an_in_flight_dispatch_worktree_is_checkpointed_with_a_redacted_subject(tmp_path, monkeypatch, capsys):
    worktree = tmp_path / "wt"
    _patch_context(monkeypatch, _context(tmp_path, _journal(worktree=worktree, story="82.9")))
    vcs = _Vcs()

    code = checkpoint_module._run_factory_checkpoint("pyforge-marshal", fs=LocalFs(), vcs=vcs)

    assert code == 0
    assert capsys.readouterr().out == f"checkpointed {worktree} at feedface\n"
    ((repo_root, paths, message),) = vcs.commits
    assert repo_root == worktree
    assert paths == (Path("work.txt"),)
    assert isinstance(message, Redacted)  # AD-34: commit text is egress
    assert message.text == "wip: 82.9 (auto-checkpoint)"


@pytest.mark.parametrize("journal", [_journal(worktree=None, story="82.9"), _journal(worktree=Path("/wt"), story=None)])
def test_a_dispatch_journal_with_no_worktree_or_story_is_an_error_not_a_crash(tmp_path, monkeypatch, journal):
    _patch_context(monkeypatch, _context(tmp_path, journal))
    vcs = _Vcs()

    code = checkpoint_module._run_factory_checkpoint("pyforge-marshal", vcs=vcs)

    assert code != 0  # MRS-CHK-001 is registered: it used to raise UnregisteredFindingCodeError here
    assert vcs.commits == []


def test_outside_a_git_repository_is_an_error_not_a_crash(monkeypatch):
    _patch_context(monkeypatch, None)

    code = checkpoint_module._run_factory_checkpoint("pyforge-marshal", vcs=_Vcs(not_a_repo=True))

    assert code != 0  # MRS-CHK-002


def test_no_loop_home_is_an_error_not_a_crash(tmp_path, monkeypatch):
    _patch_context(monkeypatch, None)
    monkeypatch.setattr(checkpoint_module, "_home_path", lambda slug: tmp_path / "no-such-home")
    vcs = _Vcs(root=tmp_path)

    code = checkpoint_module._run_factory_checkpoint("pyforge-marshal", vcs=vcs)

    assert code != 0  # MRS-CHK-003
    assert vcs.commits == []


def test_with_no_dispatch_journal_the_stations_loop_home_is_checkpointed_under_its_slug(tmp_path, monkeypatch, capsys):
    _patch_context(monkeypatch, None)
    home = tmp_path / "loop-home"
    home.mkdir()
    monkeypatch.setattr(checkpoint_module, "_home_path", lambda slug: home)
    vcs = _Vcs(root=tmp_path)

    code = checkpoint_module._run_factory_checkpoint("pyforge-marshal", vcs=vcs)

    assert code == 0
    assert f"checkpointed {home} at feedface" in capsys.readouterr().out
    ((repo_root, _paths, message),) = vcs.commits
    assert repo_root == home
    assert message.text == "wip: pyforge-marshal (auto-checkpoint)"


def test_a_clean_worktree_is_skipped_and_exits_zero(tmp_path, monkeypatch, capsys):
    worktree = tmp_path / "wt"
    _patch_context(monkeypatch, _context(tmp_path, _journal(worktree=worktree, story="82.9")))
    vcs = _Vcs(dirty=False)

    code = checkpoint_module._run_factory_checkpoint("pyforge-marshal", vcs=vcs)

    captured = capsys.readouterr()
    assert code == 0
    assert captured.err == f"checkpoint skipped for {worktree}: clean worktree\n"
    assert vcs.commits == []


def test_a_failed_commit_is_reported_and_exits_non_zero(tmp_path, monkeypatch, capsys):
    worktree = tmp_path / "wt"
    _patch_context(monkeypatch, _context(tmp_path, _journal(worktree=worktree, story="82.9")))

    code = checkpoint_module._run_factory_checkpoint("pyforge-marshal", vcs=_Vcs(commit_raises=True))

    err = capsys.readouterr().err
    assert code == 1
    assert "checkpoint skipped for" in err
    assert "hook rejected" in err  # the reason names the failure


def test_the_cli_entry_builds_the_real_adapters(monkeypatch):
    seen: dict = {}

    def fake(slug, *, fs, vcs, process):
        seen.update(slug=slug, fs=fs, vcs=vcs, process=process)
        return 7

    monkeypatch.setattr(checkpoint_module, "_run_factory_checkpoint", fake)

    assert checkpoint_module.run_factory_checkpoint(argparse.Namespace(slug="pyforge-marshal")) == 7
    assert seen["slug"] == "pyforge-marshal"
    assert isinstance(seen["fs"], LocalFs)
    assert isinstance(seen["vcs"], GitVcs)
    assert isinstance(seen["process"], PosixProcess)


def test_omitted_ports_default_to_the_real_adapters(tmp_path, monkeypatch):
    captured: dict = {}

    def fake_context(**kwargs):
        captured.update(kwargs)
        return _context(tmp_path, _journal(worktree=None, story=None))

    monkeypatch.setattr(checkpoint_module, "_load_latest_dispatch_context", fake_context)

    assert checkpoint_module._run_factory_checkpoint("pyforge-marshal") != 0
    assert isinstance(captured["fs"], LocalFs)
    assert isinstance(captured["vcs"], GitVcs)
    assert isinstance(captured["process"], PosixProcess)
    assert captured["slug"] == "pyforge-marshal"
