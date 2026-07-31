"""Integration test -- Story 1.4, ``@pytest.mark.slow`` (real ``git``/
filesystem I/O against a throwaway temp repo shaped like this one: a
tracked ``_bmad-output/projects/<slug>/planning-artifacts/`` on ``main``).
Drives the full ``marshal init`` command end-to-end through
``cli.main.main`` with the REAL ``GitVcs``/``LocalFs`` adapters (no fakes --
those live in ``tests/unit/test_init.py``), proving the two Acceptance
Criteria a fake-port test cannot: a real git worktree lands on disk on the
right branch, and a real second invocation is a true zero-write no-op.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.cli.main import main


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    return result


def _build_repo(tmp_path: Path, slug: str) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    project_dir = repo / "_bmad-output" / "projects" / slug / "planning-artifacts"
    project_dir.mkdir(parents=True)
    (project_dir / ".gitkeep").write_text("", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "seed project")
    return repo


@pytest.mark.slow
def test_init_end_to_end_provision_then_idempotent_rerun(tmp_path, monkeypatch, capsys):
    slug = "acme"
    repo = _build_repo(tmp_path, slug)
    loop_home_root = tmp_path / "loop-homes"
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(loop_home_root))
    monkeypatch.chdir(repo)

    first_exit = main(["init", slug])
    assert first_exit == 0
    first_out = capsys.readouterr().out
    assert "worktree: done" in first_out
    assert "symlink: done" in first_out
    assert "marker: done" in first_out
    assert f"export BMAD_ACTIVE_PROJECT={slug}" in first_out

    home = loop_home_root / slug
    assert home.is_dir()
    marker = home / "_bmad" / "custom" / ".active-project"
    link = home / "_bmad-output" / "planning-artifacts"
    assert marker.read_text(encoding="utf-8").strip() == slug
    assert link.is_symlink()
    assert link.resolve() == (
        home / "_bmad-output" / "projects" / slug / "planning-artifacts"
    ).resolve()

    # the new branch was created FROM main; main itself was never checked
    # out a second time (the main checkout stays on main throughout).
    home_branch = _git(home, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    assert home_branch == f"loop/{slug}"
    main_branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    assert main_branch == "main"

    marker_mtime_before = marker.stat().st_mtime_ns
    link_target_before = link.readlink()

    second_exit = main(["init", slug])
    assert second_exit == 0
    second_out = capsys.readouterr().out
    assert "worktree: skipped" in second_out
    assert "symlink: skipped" in second_out
    assert "marker: skipped" in second_out

    # true zero-write no-op: neither artifact was touched by the second run
    assert marker.stat().st_mtime_ns == marker_mtime_before
    assert link.readlink() == link_target_before
