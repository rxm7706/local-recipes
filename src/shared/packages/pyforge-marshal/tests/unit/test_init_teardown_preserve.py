"""Story 87.7: teardown unpreserved-work refusal (flag pyforge.marshal.preserve_refs)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pyforge.testing_kit.flags import flag_states

from pyforge.marshal.cli.init import run_teardown
from pyforge.marshal.core.verdict import EXIT_OK

from .test_init import FakeFs, FakeVcs, _provisioned_teardown_vcs, _teardown_namespace

_FLAG = "pyforge.marshal.preserve_refs"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)


@pytest.fixture
def git_pair(tmp_path: Path) -> tuple[Path, Path, Path]:
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
    home = tmp_path / "loop-homes" / "acme"
    home.mkdir(parents=True)
    _git(repo, "worktree", "add", "-b", "loop/acme", str(home), "main")
    return repo, bare, home


@flag_states(_FLAG)
def test_teardown_flag_off_ignores_unpreserved_patch(
    repo_root, tmp_path, capsys, monkeypatch, flag_provider: dict[str, bool]
):
    if flag_provider[_FLAG]:
        pytest.skip("flag-on path covered by other tests")
    home = tmp_path / "loop-homes" / "acme"
    vcs = _provisioned_teardown_vcs(repo_root, home, "acme")
    fs = FakeFs(project_dirs={home})
    patch_dir = home / ".bmad-loop" / "runs" / "run1" / "failed" / "1-1"
    patch_dir.mkdir(parents=True)
    (patch_dir / "changes.patch").write_text("diff\n", encoding="utf-8")
    exit_code = run_teardown(_teardown_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code == EXIT_OK


@flag_states(_FLAG)
def test_teardown_refuses_unpreserved_patch_flag_on(
    git_pair: tuple[Path, Path, Path], capsys, flag_provider: dict[str, bool]
):
    if not flag_provider[_FLAG]:
        pytest.skip("preserve_refs flag off in this parametrization")
    repo, _bare, home = git_pair
    vcs = FakeVcs(repo_root=repo, worktrees={"loop/acme": home}, branches={"loop/acme"})
    vcs.remote_branches = frozenset({"loop/acme"})
    fs = FakeFs(project_dirs={home})
    patch_dir = home / ".bmad-loop" / "runs" / "run1" / "failed" / "1-1"
    patch_dir.mkdir(parents=True)
    patch = patch_dir / "changes.patch"
    patch.write_text("diff\n", encoding="utf-8")
    token = patch.relative_to(home).as_posix()
    exit_code = run_teardown(_teardown_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-TEARDOWN-006" in out
    assert token in out


@flag_states(_FLAG)
def test_teardown_abandon_exact_set_proceeds(
    git_pair: tuple[Path, Path, Path], capsys, flag_provider: dict[str, bool]
):
    if not flag_provider[_FLAG]:
        pytest.skip("preserve_refs flag off in this parametrization")
    repo, _bare, home = git_pair
    vcs = FakeVcs(repo_root=repo, worktrees={"loop/acme": home}, branches={"loop/acme"})
    vcs.remote_branches = frozenset({"loop/acme"})
    fs = FakeFs(project_dirs={home})
    patch_dir = home / ".bmad-loop" / "runs" / "run1" / "failed" / "1-1"
    patch_dir.mkdir(parents=True)
    patch = patch_dir / "changes.patch"
    patch.write_text("diff\n", encoding="utf-8")
    token = patch.relative_to(home).as_posix()
    exit_code = run_teardown(_teardown_namespace("acme", force=True, abandon=[token]), vcs=vcs, fs=fs)
    assert exit_code == EXIT_OK
    assert vcs.remove_worktree_calls


@flag_states(_FLAG)
def test_teardown_loop_on_origin_not_unpreserved(
    git_pair: tuple[Path, Path, Path], capsys, flag_provider: dict[str, bool]
):
    if not flag_provider[_FLAG]:
        pytest.skip("preserve_refs flag off in this parametrization")
    repo, bare, home = git_pair
    (home / "extra.txt").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "extra.txt")
    _git(repo, "commit", "-m", "loop tip")
    tip = _git(repo, "rev-parse", "HEAD").stdout.strip()
    _git(repo, "push", "origin", "loop/acme:loop/acme")
    _git(repo, "fetch", "origin")
    vcs = FakeVcs(
        repo_root=repo,
        worktrees={"loop/acme": home},
        branches={"loop/acme"},
        refs={"loop/acme": tip, "HEAD": tip},
    )
    vcs.remote_branches = frozenset({"loop/acme"})
    vcs.is_commit_ancestor = lambda *a, **k: False  # type: ignore[method-assign]
    vcs.commit_contained_in_remote_refs = lambda *a, **k: True  # type: ignore[method-assign]
    fs = FakeFs(project_dirs={home})
    exit_code = run_teardown(_teardown_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code == EXIT_OK
