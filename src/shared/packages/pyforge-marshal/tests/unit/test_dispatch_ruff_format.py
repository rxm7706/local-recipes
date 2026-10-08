"""Story 83.9 / 83.15: pre-verify ``ruff check --fix`` and ``ruff format`` on story-scoped ``.py`` files."""

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
        if tokens[:3] == ["ruff", "check", "--fix"] or tokens[:2] == ["ruff", "format"]:
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
    assert len(process.calls) == 2
    assert process.calls[0][0] == ["ruff", "check", "--fix", "src/pyforge/marshal/sample.py"]
    assert process.calls[1][0] == ["ruff", "format", "src/pyforge/marshal/sample.py"]
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


def test_verification_journals_ruff_format_when_paths_change(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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


class _DiskDirtyVcs:
    """VCS stub that reports HEAD dirtiness from on-disk content changes."""

    def __init__(self, *, scope: tuple[str, ...], worktree: Path) -> None:
        self._scope = scope
        self._worktree = worktree
        self._baseline = {p: (worktree / p).read_bytes() for p in scope}
        self.commits: list[tuple[Path, tuple[Path, ...], object]] = []

    def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str) -> tuple[str, ...]:
        del repo_root
        if base == "HEAD":
            dirty = [p for p in self._scope if (worktree_path / p).read_bytes() != self._baseline.get(p, b"")]
            return tuple(sorted(dirty))
        return self._scope

    def commit_paths(self, repo_root: Path, paths: tuple[Path, ...], message: object) -> str:
        self.commits.append((repo_root, paths, message))
        for path in paths:
            rel = path.as_posix()
            self._baseline[rel] = (self._worktree / rel).read_bytes()
        return "abc123"


def test_apply_ruff_check_fix_removes_safe_violations(tmp_path: Path) -> None:
    """Story 83.15: unused import and import sort are fixed before commit (mutation oracle)."""
    import shutil

    from pyforge.core.process import PosixProcess

    if shutil.which("ruff") is None:
        pytest.skip("ruff not on PATH")

    worktree = tmp_path / "wt"
    repo_root = tmp_path
    pkg = worktree / "src/shared/packages/pyforge-marshal"
    target = pkg / "src/pyforge/marshal/sample.py"
    target.parent.mkdir(parents=True)
    target.write_text("import sys\nimport os\n\nx = 1\n", encoding="utf-8")
    marshal_pkg = Path(__file__).resolve().parents[2]
    shutil.copy(marshal_pkg / "pyproject.toml", pkg / "pyproject.toml")

    vcs = _DiskDirtyVcs(scope=(_STORY_PY,), worktree=worktree)
    process = PosixProcess()

    result = apply_dispatch_ruff_format_before_verify(
        worktree=worktree,
        repo_root=repo_root,
        vcs=vcs,
        process=process,
    )

    assert result.committed is True
    text = target.read_text(encoding="utf-8")
    assert "import os" not in text
    assert "import sys" not in text
    assert "x = 1" in text


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


def test_finalize_verification_order_is_ruff_then_verify_without_reconcile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Story 22.20: first verification still runs ruff, then verify — no reconcile between them."""
    import importlib

    loop_tests = importlib.import_module("test_dispatch_supervisor_main_loop")

    repo_root = loop_tests._repo(tmp_path)
    worktree = loop_tests._worktree(repo_root)
    loop_tests._seed_spec(repo_root, worktree, primary=loop_tests._READY_SPEC_TEXT)
    order: list[str] = []

    def _ruff(**_kwargs: object) -> DispatchRuffFormatResult:
        order.append("ruff")
        return DispatchRuffFormatResult((), False)

    def _evaluate(**_kwargs: object):
        order.append("verify")
        return loop_tests._clean_envelope()

    monkeypatch.setattr(supervisor_main, "run_dispatch_ruff_format_before_verify", _ruff)
    monkeypatch.setattr(supervisor_main, "evaluate_dispatch_verification", _evaluate)
    fs = loop_tests.FakeFs()

    loop_tests._verify(fs, repo_root, worktree)

    assert order == ["ruff", "verify"]


def test_cap4_verification_order_is_ruff_then_verify(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Story 22.20: land-only CAP-4 verification still runs ruff, then verify — no reconcile."""
    import test_dispatch as dispatch_test_helpers

    from pyforge.marshal.cli import dispatch as dispatch_module
    from pyforge.marshal.core.model import build_envelope
    from pyforge.marshal.core.policy import compose

    order: list[str] = []
    repo_root = tmp_path / "repo"
    worktree = tmp_path / "wt"
    worktree.mkdir(parents=True)
    effective_policy = compose(project_slug="pyforge-marshal", project={}, flags={})[0]

    def _ruff(**_kwargs: object) -> DispatchRuffFormatResult:
        order.append("ruff")
        return DispatchRuffFormatResult((), False)

    def _evaluate(**_kwargs: object):
        order.append("verify")
        return build_envelope(command="dispatch verify", verdict="ok", data={}, findings=())

    monkeypatch.setattr(dispatch_module, "run_dispatch_ruff_format_before_verify", _ruff)
    monkeypatch.setattr(dispatch_module, "evaluate_dispatch_verification", _evaluate)

    dispatch_module._verification_verdict_for_cap4(
        slug="pyforge-marshal",
        story_key="22-20-test",
        worktree=worktree,
        repo_root=repo_root,
        effective_policy=effective_policy,
        spec_text="---\nstatus: done\n---\n",
        process=dispatch_test_helpers.FakeProcess(),
        vcs=dispatch_test_helpers.FakeVcs(repo_root),
    )

    assert order == ["ruff", "verify"]
