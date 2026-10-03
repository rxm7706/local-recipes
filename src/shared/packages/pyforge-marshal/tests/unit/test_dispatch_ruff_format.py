"""Story 83.9: pre-verify ``ruff format`` on story-scoped ``.py`` files."""

from __future__ import annotations

from pathlib import Path

import pytest
from pyforge.core.process import ProcessResult

from pyforge.marshal.core.dispatch_ruff_format import (
    DispatchRuffFormatResult,
    apply_dispatch_ruff_format_before_verify,
    story_scoped_pyforge_py_paths,
)
from pyforge.marshal.dispatch_supervisor import __main__ as supervisor_main

_STORY_PY = "src/shared/packages/pyforge-marshal/src/pyforge/marshal/sample.py"
_OTHER_PY = "src/shared/packages/pyforge-scribe/src/pyforge/scribe/other.py"


def test_story_scoped_pyforge_py_paths_filters_packages() -> None:
    paths = (
        _STORY_PY,
        "docs/readme.md",
        "src/shared/packages/pyforge-marshal/README.md",
        "src/platform/foo.py",
        _OTHER_PY,
    )
    assert story_scoped_pyforge_py_paths(paths) == (_STORY_PY, _OTHER_PY)


class _FormatVcs:
    def __init__(self, *, scope: tuple[str, ...], head: tuple[str, ...]) -> None:
        self._scope = scope
        self._head = head
        self.commits: list[tuple[Path, tuple[Path, ...], object]] = []

    def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str) -> tuple[str, ...]:
        del repo_root, worktree_path
        return self._head if base == "HEAD" else self._scope

    def commit_paths(self, repo_root: Path, paths: tuple[Path, ...], message: object) -> str:
        self.commits.append((repo_root, paths, message))
        self._head = ()
        return "abc123"


class _FormatProcess:
    def __init__(self, vcs: _FormatVcs) -> None:
        self.vcs = vcs
        self.calls: list[tuple[list[str], Path]] = []

    def run(self, tokens: list[str], *, cwd: Path) -> ProcessResult:
        self.calls.append((tokens, cwd))
        if tokens[:2] == ["ruff", "format"]:
            self.vcs._head = self.vcs._scope
        return ProcessResult(0, "", "")


def test_apply_formats_only_story_scoped_paths_and_commits(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    pkg = worktree / "src/shared/packages/pyforge-marshal"
    target = pkg / "src/pyforge/marshal/sample.py"
    target.parent.mkdir(parents=True)
    target.write_text("x=1\n", encoding="utf-8")
    (pkg / "pyproject.toml").write_text("[tool.ruff]\n", encoding="utf-8")

    vcs = _FormatVcs(scope=(_STORY_PY,), head=())
    process = _FormatProcess(vcs)

    result = apply_dispatch_ruff_format_before_verify(
        worktree=worktree,
        repo_root=tmp_path,
        vcs=vcs,
        process=process,
    )

    assert result == DispatchRuffFormatResult((_STORY_PY,), True)
    assert process.calls
    assert process.calls[0][0] == ["ruff", "format", "src/pyforge/marshal/sample.py"]
    assert vcs.commits


def test_apply_skips_when_already_formatted(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    vcs = _FormatVcs(scope=(_STORY_PY,), head=())
    process = _FormatProcess(vcs)
    process.run = lambda tokens, *, cwd: ProcessResult(0, "", "")  # type: ignore[method-assign]

    result = apply_dispatch_ruff_format_before_verify(
        worktree=worktree,
        repo_root=tmp_path,
        vcs=vcs,
        process=process,
    )

    assert result == DispatchRuffFormatResult((), False)
    assert not vcs.commits


def test_verification_journals_ruff_format_when_paths_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib

    loop_tests = importlib.import_module("test_dispatch_supervisor_main_loop")

    repo_root = loop_tests._repo(tmp_path)
    worktree = loop_tests._worktree(repo_root)
    loop_tests._seed_spec(repo_root, worktree, primary=loop_tests._READY_SPEC_TEXT)
    loop_tests._patch_verification(monkeypatch, loop_tests._clean_envelope)
    monkeypatch.setattr(
        supervisor_main,
        "run_dispatch_ruff_format_before_verify",
        lambda **_: DispatchRuffFormatResult((_STORY_PY,), True),
    )
    fs = loop_tests.FakeFs()

    counter = loop_tests._verify(fs, repo_root, worktree)

    assert counter == 4
    assert any("dispatch-ruff-format" in line for _, line, _ in fs.appended)


def test_mutation_verification_without_ruff_format_journal_partner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutation partner: skipping the journal hook must drop the format entry."""
    import importlib

    loop_tests = importlib.import_module("test_dispatch_supervisor_main_loop")

    repo_root = loop_tests._repo(tmp_path)
    worktree = loop_tests._worktree(repo_root)
    loop_tests._seed_spec(repo_root, worktree, primary=loop_tests._READY_SPEC_TEXT)
    loop_tests._patch_verification(monkeypatch, loop_tests._clean_envelope)
    monkeypatch.setattr(
        supervisor_main,
        "run_dispatch_ruff_format_before_verify",
        lambda **_: DispatchRuffFormatResult((_STORY_PY,), True),
    )
    monkeypatch.setattr(supervisor_main, "_run_and_journal_ruff_format", lambda **kwargs: kwargs["counter"])
    fs = loop_tests.FakeFs()

    counter = loop_tests._verify(fs, repo_root, worktree)

    assert counter == 2
    assert not any("dispatch-ruff-format" in line for _, line, _ in fs.appended)
