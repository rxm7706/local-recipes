"""Integration test -- Stories 1.4/1.5, ``@pytest.mark.slow`` (real ``git``/
filesystem I/O against a throwaway temp repo shaped like this one: a
tracked ``_bmad-output/projects/<slug>/planning-artifacts/`` on ``main``).
Drives the full ``marshal init`` command end-to-end through
``cli.main.main`` with the REAL ``GitVcs``/``LocalFs`` adapters (no fakes --
those live in ``tests/unit/test_init.py``), proving the Acceptance Criteria
a fake-port test cannot: a real git worktree lands on disk on the right
branch, a real second invocation is a true zero-write no-op, and the home's
gitignored Tier-3 store (Story 1.5) really resolves to the SAME real
directory as the repo's own canonical copy.
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

    # Story 1.5 AC: "the main checkout's own marker and symlinks are
    # unchanged" -- seed state resembling a real bmad-switch-established
    # main checkout (a DIFFERENT active project) so this is a genuine
    # regression check, not a trivially-true "still absent" one.
    repo_marker = repo / "_bmad" / "custom" / ".active-project"
    repo_marker.parent.mkdir(parents=True)
    repo_marker.write_text("some-other-project\n", encoding="utf-8")
    repo_planning_link = repo / "_bmad-output" / "planning-artifacts"
    repo_planning_link.symlink_to(Path("projects/some-other-project/planning-artifacts"))
    repo_marker_before = repo_marker.read_text(encoding="utf-8")
    repo_planning_link_target_before = repo_planning_link.readlink()

    first_exit = main(["init", slug])
    assert first_exit == 0
    first_out = capsys.readouterr().out
    assert "worktree: done" in first_out
    assert "tier3_backlink: done" in first_out
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

    # Story 1.5: the home's Tier-3 store resolves to the SAME real
    # directory as the repo's own canonical copy -- one canonical store,
    # not a per-worktree fork.
    home_tier3 = home / "_bmad-output" / "projects" / slug / "implementation-artifacts"
    canonical_tier3 = repo / "_bmad-output" / "projects" / slug / "implementation-artifacts"
    assert home_tier3.is_symlink()
    assert canonical_tier3.is_dir()
    assert home_tier3.resolve() == canonical_tier3.resolve()

    # the new branch was created FROM main; main itself was never checked
    # out a second time (the main checkout stays on main throughout).
    home_branch = _git(home, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    assert home_branch == f"loop/{slug}"
    main_branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    assert main_branch == "main"

    marker_mtime_before = marker.stat().st_mtime_ns
    link_target_before = link.readlink()
    tier3_link_target_before = home_tier3.readlink()

    second_exit = main(["init", slug])
    assert second_exit == 0
    second_out = capsys.readouterr().out
    assert "worktree: skipped" in second_out
    assert "tier3_backlink: skipped" in second_out
    assert "symlink: skipped" in second_out
    assert "marker: skipped" in second_out

    # true zero-write no-op: neither artifact was touched by the second run
    assert marker.stat().st_mtime_ns == marker_mtime_before
    assert link.readlink() == link_target_before
    assert home_tier3.readlink() == tier3_link_target_before

    # the main checkout's own marker/symlink, seeded above, are untouched by
    # either run -- `marshal init` never writes to `repo_root` itself beyond
    # creating the canonical Tier-3 directory.
    assert repo_marker.read_text(encoding="utf-8") == repo_marker_before
    assert repo_planning_link.readlink() == repo_planning_link_target_before


@pytest.mark.slow
def test_init_refuses_a_real_nonempty_local_tier3_directory(tmp_path, monkeypatch, capsys):
    """The headline new capability (MRS-INIT-005), proven against the REAL
    adapters -- not just the FakeFs coverage in tests/unit/test_init.py."""
    slug = "acme"
    repo = _build_repo(tmp_path, slug)
    loop_home_root = tmp_path / "loop-homes"
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(loop_home_root))
    monkeypatch.chdir(repo)

    first_exit = main(["init", slug])
    assert first_exit == 0
    capsys.readouterr()

    home = loop_home_root / slug
    home_tier3 = home / "_bmad-output" / "projects" / slug / "implementation-artifacts"
    # Simulate this repo's own documented live incident: something (e.g. a
    # BMAD write-skill) populates the local Tier-3 path with a real,
    # non-empty directory before/instead of the backlink.
    home_tier3.unlink()
    home_tier3.mkdir()
    stray_file = home_tier3 / "sprint-status.yaml"
    stray_file.write_text("status: in-progress\n", encoding="utf-8")

    second_exit = main(["init", slug])
    assert second_exit != 0
    out = capsys.readouterr().out
    assert "MRS-INIT-005" in out
    assert str(home_tier3) in out
    assert "tier3_backlink: failed" in out

    # left untouched: no data lost, nothing replaced
    assert home_tier3.is_dir()
    assert not home_tier3.is_symlink()
    assert stray_file.read_text(encoding="utf-8") == "status: in-progress\n"
