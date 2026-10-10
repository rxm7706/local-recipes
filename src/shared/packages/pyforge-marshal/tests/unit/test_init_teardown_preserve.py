"""Story 87.7: teardown unpreserved-work refusal (flag pyforge.marshal.preserve_refs)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import test_init as init_fixtures
from pyforge.testing_kit.flags import flag_states

from pyforge.marshal.adapters.fs_local import LocalFs
from pyforge.marshal.adapters.vcs_git import GitVcs
from pyforge.marshal.cli.init import ENV_LOOP_HOME_ROOT, run_teardown
from pyforge.marshal.core.verdict import EXIT_OK

FakeFs = init_fixtures.FakeFs
FakeVcs = init_fixtures.FakeVcs
_provisioned_teardown_vcs = init_fixtures._provisioned_teardown_vcs
_teardown_namespace = init_fixtures._teardown_namespace

_FLAG = "pyforge.marshal.preserve_refs"


def _patch_preserve_flag(monkeypatch: pytest.MonkeyPatch, flag_provider: dict[str, bool]) -> None:
    from pyforge.marshal.core import dispatch_preserve

    monkeypatch.setattr(
        dispatch_preserve,
        "preserve_refs_flag_on",
        lambda **kwargs: flag_provider[_FLAG],
    )


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    return tmp_path / "main-repo"


@pytest.fixture
def git_pair(repo_root: Path) -> tuple[Path, Path]:
    """Bare origin + clone; loop/acme worktree at the pinned loop-home root."""
    bare = repo_root.parent / "origin.git"
    subprocess.run(["git", "init", "--bare", str(bare)], check=True)
    subprocess.run(["git", "init", str(repo_root)], check=True)
    _git(repo_root, "config", "user.email", "t@example.com")
    _git(repo_root, "config", "user.name", "t")
    purge_dir = repo_root / "docs" / "governance"
    purge_dir.mkdir(parents=True, exist_ok=True)
    (purge_dir / "preserve-purge-list.json").write_text(
        '{"schema_version": 1, "commit_shas": [], "paths": []}\n',
        encoding="utf-8",
    )
    (repo_root / "README.md").write_text("base\n", encoding="utf-8")
    (repo_root / ".gitignore").write_text(".bmad-loop/\n", encoding="utf-8")
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-m", "init")
    _git(repo_root, "branch", "-M", "main")
    _git(repo_root, "remote", "add", "origin", str(bare))
    _git(repo_root, "push", "-u", "origin", "main")
    _git(repo_root, "fetch", "origin")
    home = Path(os.environ[ENV_LOOP_HOME_ROOT]) / "acme"
    home.mkdir(parents=True, exist_ok=True)
    _git(repo_root, "worktree", "add", "-b", "loop/acme", str(home), "main")
    return repo_root, home


@flag_states(_FLAG)
def test_teardown_flag_off_ignores_unpreserved_patch(
    repo_root, tmp_path, capsys, flag_provider: dict[str, bool]
):
    if flag_provider[_FLAG]:
        pytest.skip("flag-on path covered by other tests")
    home = Path(os.environ[ENV_LOOP_HOME_ROOT]) / "acme"
    home.mkdir(parents=True, exist_ok=True)
    vcs = _provisioned_teardown_vcs(repo_root, home, "acme")
    fs = FakeFs(project_dirs={home})
    patch_dir = home / ".bmad-loop" / "runs" / "run1" / "failed" / "1-1"
    patch_dir.mkdir(parents=True)
    (patch_dir / "changes.patch").write_text("diff\n", encoding="utf-8")
    exit_code = run_teardown(_teardown_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code == EXIT_OK


@flag_states(_FLAG)
def test_teardown_refuses_unpreserved_patch_flag_on(
    git_pair: tuple[Path, Path], capsys, flag_provider: dict[str, bool], monkeypatch: pytest.MonkeyPatch
):
    if not flag_provider[_FLAG]:
        pytest.skip("preserve_refs flag off in this parametrization")
    _patch_preserve_flag(monkeypatch, flag_provider)
    repo, home = git_pair
    monkeypatch.chdir(repo)
    patch_dir = home / ".bmad-loop" / "runs" / "run1" / "failed" / "1-1"
    patch_dir.mkdir(parents=True)
    patch = patch_dir / "changes.patch"
    patch.write_text("diff\n", encoding="utf-8")
    token = patch.relative_to(home).as_posix()
    exit_code = run_teardown(_teardown_namespace("acme"), vcs=GitVcs(), fs=LocalFs())
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-TEARDOWN-006" in out
    assert token in out


@flag_states(_FLAG)
def test_teardown_abandon_exact_set_proceeds(
    git_pair: tuple[Path, Path], capsys, flag_provider: dict[str, bool], monkeypatch: pytest.MonkeyPatch
):
    if not flag_provider[_FLAG]:
        pytest.skip("preserve_refs flag off in this parametrization")
    _patch_preserve_flag(monkeypatch, flag_provider)
    repo, home = git_pair
    monkeypatch.chdir(repo)
    patch_dir = home / ".bmad-loop" / "runs" / "run1" / "failed" / "1-1"
    patch_dir.mkdir(parents=True)
    patch = patch_dir / "changes.patch"
    patch.write_text("diff\n", encoding="utf-8")
    token = patch.relative_to(home).as_posix()
    exit_code = run_teardown(
        _teardown_namespace("acme", force=True, abandon=[token]),
        vcs=GitVcs(),
        fs=LocalFs(),
    )
    assert exit_code == EXIT_OK


@flag_states(_FLAG)
def test_teardown_loop_on_origin_not_unpreserved(
    git_pair: tuple[Path, Path], capsys, flag_provider: dict[str, bool], monkeypatch: pytest.MonkeyPatch
):
    if not flag_provider[_FLAG]:
        pytest.skip("preserve_refs flag off in this parametrization")
    _patch_preserve_flag(monkeypatch, flag_provider)
    repo, home = git_pair
    monkeypatch.chdir(home)
    (home / "extra.txt").write_text("x\n", encoding="utf-8")
    _git(home, "add", "extra.txt")
    _git(home, "commit", "-m", "loop tip")
    _git(repo, "push", "origin", "loop/acme:loop/acme")
    _git(repo, "fetch", "origin")
    _git(repo, "checkout", "main")
    _git(repo, "merge", "loop/acme", "--no-edit")
    _git(repo, "push", "origin", "main")
    _git(repo, "fetch", "origin")
    monkeypatch.chdir(repo)
    exit_code = run_teardown(_teardown_namespace("acme"), vcs=GitVcs(), fs=LocalFs())
    assert exit_code == EXIT_OK
