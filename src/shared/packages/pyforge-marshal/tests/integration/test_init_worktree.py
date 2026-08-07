"""Integration test -- Stories 1.4/1.5/1.6/1.7/1.8, ``@pytest.mark.slow``
(real ``git``/filesystem I/O against a throwaway temp repo shaped like this
one: a tracked ``_bmad-output/projects/<slug>/planning-artifacts/`` on
``main``). Drives the full ``marshal init``/``marshal homes``/``marshal
preflight``/``marshal teardown`` commands end-to-end through ``cli.main.main``
with the REAL ``GitVcs``/``LocalFs``/``BmadLoopHarness`` adapters (no fakes
-- those live in ``tests/unit/test_init.py``), proving the Acceptance
Criteria a fake-port test cannot: a real git worktree lands on disk on the
right branch, a real second invocation is a true zero-write no-op, the
home's gitignored Tier-3 store (Story 1.5) really resolves to the SAME real
directory as the repo's own canonical copy, ``marshal homes`` (Story 1.6)
really auto-discovers real worktrees via real ``git worktree list`` and
really detects a real hand-edited desync, ``marshal preflight`` (Story 1.7)
really invokes the installed ``bmad-loop --version``, really resolves the
real ``claude`` profile via the installed ``bmad_loop`` package, really
copies a real seed file's bytes, and really persists a machine-scoped
acknowledgement across two invocations, and ``marshal teardown`` (Story 1.8)
really removes a real worktree+branch via real ``git worktree remove``/
``git branch -D``, and -- the story's own headline scenario -- really
recognizes a REAL single-parent squash-merge commit (this repo's own
bmad-loop landing convention) as merged via the real ``git commit-tree``+
``git cherry`` fallback, where real bare ancestry would misreport it as
unmerged.
"""

from __future__ import annotations

import json
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
    # main checkout (a DIFFERENT active project, BOTH top-level artifact
    # links) so this is a genuine regression check, not a trivially-true
    # "still absent" one. The implementation-artifacts link matters most:
    # it is the surface this story's canonical-Tier-3 writes come closest
    # to.
    repo_marker = repo / "_bmad" / "custom" / ".active-project"
    repo_marker.parent.mkdir(parents=True)
    repo_marker.write_text("some-other-project\n", encoding="utf-8")
    repo_planning_link = repo / "_bmad-output" / "planning-artifacts"
    repo_planning_link.symlink_to(Path("projects/some-other-project/planning-artifacts"))
    repo_impl_link = repo / "_bmad-output" / "implementation-artifacts"
    repo_impl_link.symlink_to(Path("projects/some-other-project/implementation-artifacts"))
    repo_marker_before = repo_marker.read_text(encoding="utf-8")
    repo_planning_link_target_before = repo_planning_link.readlink()
    repo_impl_link_target_before = repo_impl_link.readlink()

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

    # the main checkout's own marker/symlinks, seeded above, are untouched
    # by either run -- `marshal init` never writes to `repo_root` itself
    # beyond creating the canonical Tier-3 directory.
    assert repo_marker.read_text(encoding="utf-8") == repo_marker_before
    assert repo_planning_link.readlink() == repo_planning_link_target_before
    assert repo_impl_link.readlink() == repo_impl_link_target_before


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


@pytest.mark.slow
def test_homes_end_to_end_two_clean_worktrees_then_a_real_desync(tmp_path, monkeypatch, capsys):
    """Story 1.6: real ``git worktree list`` auto-discovery against two
    real ``marshal init``-provisioned worktrees, then a hand-edited marker
    (exactly the kind of external tampering ``marshal homes`` exists to
    catch) really trips ``MRS-HOMES-001`` on a second real invocation."""
    slug_one = "acme"
    repo = _build_repo(tmp_path, slug_one)
    slug_two = "beta"
    beta_dir = repo / "_bmad-output" / "projects" / slug_two / "planning-artifacts"
    beta_dir.mkdir(parents=True)
    (beta_dir / ".gitkeep").write_text("", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "seed second project")

    loop_home_root = tmp_path / "loop-homes"
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(loop_home_root))
    monkeypatch.chdir(repo)

    assert main(["init", slug_one]) == 0
    capsys.readouterr()
    assert main(["init", slug_two]) == 0
    capsys.readouterr()

    exit_code = main(["homes", "--format", "json"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    homes_by_slug = {row["slug"]: row for row in payload["data"]["homes"]}
    assert set(homes_by_slug) == {slug_one, slug_two}
    for row in homes_by_slug.values():
        assert row["desynced"] is False
        assert row["active_project"] == row["slug"]
    assert payload["data"]["main_checkout"]["desynced"] is False
    assert payload["findings"] == []

    # Real external tampering: hand-edit acme's own marker to name a
    # different project while its symlink/branch stay put.
    acme_marker = loop_home_root / slug_one / "_bmad" / "custom" / ".active-project"
    acme_marker.write_text(f"{slug_two}\n", encoding="utf-8")

    second_exit = main(["homes", "--format", "json"])
    assert second_exit != 0
    second_payload = json.loads(capsys.readouterr().out)
    codes = {finding["code"] for finding in second_payload["findings"]}
    assert "MRS-HOMES-001" in codes
    acme_row = next(
        row for row in second_payload["data"]["homes"] if row["slug"] == slug_one
    )
    assert acme_row["desynced"] is True
    beta_row = next(
        row for row in second_payload["data"]["homes"] if row["slug"] == slug_two
    )
    assert beta_row["desynced"] is False  # unaffected by acme's own tampering


def _seed_bmad_config_and_sprint_status(project: Path) -> None:
    """A real ``_bmad/bmm/config.yaml`` + a real, valid ``sprint-status.yaml``
    at the path it resolves to -- ``marshal init`` deliberately does not
    create the TOP-LEVEL ``_bmad-output/implementation-artifacts`` symlink
    (Story 1.5's own Design Notes, out of that story's scope), so a fresh
    home has no story feed until this (or a real ``bmad-switch``) runs.
    A real directory here, not a symlink -- simplest fixture shape that
    satisfies ``bmad_loop.bmadconfig.load_paths``/``sprintstatus.load``."""
    bmad_dir = project / "_bmad" / "bmm"
    bmad_dir.mkdir(parents=True, exist_ok=True)
    (bmad_dir / "config.yaml").write_text(
        "implementation_artifacts: '{project-root}/_bmad-output/implementation-artifacts'\n"
        "planning_artifacts: '{project-root}/_bmad-output/planning-artifacts'\n",
        encoding="utf-8",
    )
    feed_dir = project / "_bmad-output" / "implementation-artifacts"
    feed_dir.mkdir(parents=True, exist_ok=True)
    (feed_dir / "sprint-status.yaml").write_text("development_status: {}\n", encoding="utf-8")


@pytest.mark.slow
def test_preflight_end_to_end_converges_seeds_and_acknowledges(tmp_path, monkeypatch, capsys):
    """Story 1.7: a real end-to-end ``marshal preflight`` pass -- the real
    ``bmad-loop --version`` subprocess call, the real installed
    ``bmad_loop.adapters.profile``/``multiplexer``/``bmadconfig``/
    ``sprintstatus`` reads, a real ``shutil.copy2`` seed-file copy, and a
    real machine-scoped acknowledgement file -- proving what
    ``tests/unit/test_init.py``'s ``FakeHarness`` cannot: the REAL adapters
    wired together converge to exit 0 and stay well under NFR-14's 10s
    budget."""
    import time

    slug = "acme"
    repo = _build_repo(tmp_path, slug)
    loop_home_root = tmp_path / "loop-homes"
    state_home = tmp_path / "state-home"
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(loop_home_root))
    monkeypatch.setenv("MARSHAL_STATE_HOME", str(state_home))
    monkeypatch.chdir(repo)

    # A real seed-file SOURCE in the main checkout, so the copy step really
    # copies real bytes (never a symlink) rather than skip.
    (repo / ".mcp.json").write_text('{"mcpServers": {}}', encoding="utf-8")

    assert main(["init", slug]) == 0
    capsys.readouterr()

    home = loop_home_root / slug
    _seed_bmad_config_and_sprint_status(home)
    # Story 6.3's own MRS-ADP-003 (projection conformance, now an
    # unconditional `run_preflight` step) expects the canonical skill tree
    # to exist in the home -- a real git-worktree-provisioned loop home
    # gets `.claude/skills` for free (it's tracked repo content), but this
    # fixture's own synthetic home is not a real worktree checkout. An
    # empty directory is sufficient: the check only probes `is_dir()`.
    (home / ".claude" / "skills").mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    first_exit = main(["preflight", slug, "--acknowledge", "claude"])
    elapsed = time.perf_counter() - started
    first_out = capsys.readouterr().out
    assert first_exit == 0, first_out
    assert elapsed < 10.0, f"preflight took {elapsed:.2f}s, over NFR-14's 10s budget"
    assert "findings:" not in first_out
    assert "harness_version: 0.9.0" in first_out
    assert "adapter: name='claude' binary_present=True" in first_out
    assert "story_feed: resolvable=True" in first_out
    assert "main_checked_out_once: True" in first_out
    assert "first_run_acknowledged: True" in first_out

    # the seed file really landed as real bytes, never a symlink
    seeded = home / ".mcp.json"
    assert seeded.is_file()
    assert not seeded.is_symlink()
    assert seeded.read_text(encoding="utf-8") == '{"mcpServers": {}}'

    # the acknowledgement really persists across a SECOND invocation with no
    # --acknowledge flag, and the now-present seed file is reported skipped
    second_exit = main(["preflight", slug])
    second_out = capsys.readouterr().out
    assert second_exit == 0, second_out
    assert "findings:" not in second_out
    assert "first_run_acknowledged: True" in second_out
    assert "  .mcp.json: skipped" in second_out


@pytest.mark.slow
def test_preflight_refuses_an_unprovisioned_loop_home(tmp_path, monkeypatch, capsys):
    slug = "acme"
    repo = _build_repo(tmp_path, slug)
    loop_home_root = tmp_path / "loop-homes"
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(loop_home_root))
    monkeypatch.setenv("MARSHAL_STATE_HOME", str(tmp_path / "state-home"))
    monkeypatch.chdir(repo)
    # deliberately no `marshal init` call first

    exit_code = main(["preflight", slug])
    out = capsys.readouterr().out
    assert exit_code != 0
    assert "MRS-PREFLIGHT-009" in out
    assert "marshal init" in out


def _seed_real_gitignore(repo: Path) -> None:
    """Commits the SAME two ``.gitignore`` patterns this repo's own root
    ``.gitignore`` carries for a loop home's ``_bmad/custom/.active-project``
    marker and ``_bmad-output/planning-artifacts`` symlink -- without this, a
    freshly ``marshal init``-provisioned worktree in a throwaway test repo
    (which starts with no ``.gitignore`` at all) would report those two
    ``run_init``-written paths as untracked, making ``has_uncommitted_changes``
    report every fresh home dirty regardless of any REAL uncommitted work."""
    (repo / ".gitignore").write_text(
        "_bmad/custom/.active-project\n"
        "_bmad-output/planning-artifacts\n"
        "_bmad-output/projects/*/implementation-artifacts/\n"
        "_bmad-output/projects/*/implementation-artifacts\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-m", "seed gitignore")


@pytest.mark.slow
def test_teardown_end_to_end_removes_a_clean_merged_home(tmp_path, monkeypatch, capsys):
    """Story 1.8 AC: a provisioned, clean loop home's worktree AND branch
    are really removed, and a real ``git worktree list`` is clean
    afterward. A second real invocation reports ``already_removed`` with no
    error (the spec's own literal Verification instruction)."""
    slug = "acme"
    repo = _build_repo(tmp_path, slug)
    _seed_real_gitignore(repo)
    loop_home_root = tmp_path / "loop-homes"
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(loop_home_root))
    monkeypatch.chdir(repo)

    assert main(["init", slug]) == 0
    capsys.readouterr()
    home = loop_home_root / slug
    assert home.is_dir()

    exit_code = main(["teardown", slug])
    out = capsys.readouterr().out
    assert exit_code == 0, out
    assert "removed: True" in out
    assert not home.exists()

    worktrees = _git(repo, "worktree", "list", "--porcelain").stdout
    assert str(home) not in worktrees
    branches = _git(repo, "branch", "--list", f"loop/{slug}").stdout
    assert branches.strip() == ""

    second_exit = main(["teardown", slug])
    second_out = capsys.readouterr().out
    assert second_exit == 0, second_out
    assert "already_removed: True" in second_out
    assert "findings:" not in second_out


@pytest.mark.slow
def test_teardown_end_to_end_refuses_dirty_then_force_removes(tmp_path, monkeypatch, capsys):
    slug = "acme"
    repo = _build_repo(tmp_path, slug)
    _seed_real_gitignore(repo)
    loop_home_root = tmp_path / "loop-homes"
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(loop_home_root))
    monkeypatch.chdir(repo)

    assert main(["init", slug]) == 0
    capsys.readouterr()
    home = loop_home_root / slug
    (home / "uncommitted.txt").write_text("real uncommitted work\n", encoding="utf-8")

    refused_exit = main(["teardown", slug])
    refused_out = capsys.readouterr().out
    assert refused_exit != 0
    assert "MRS-TEARDOWN-003" in refused_out
    assert "uncommitted changes" in refused_out
    assert home.is_dir()  # nothing removed

    forced_exit = main(["teardown", slug, "--force"])
    forced_out = capsys.readouterr().out
    assert forced_exit == 0, forced_out
    assert "forced: True" in forced_out
    assert not home.exists()


@pytest.mark.slow
def test_teardown_end_to_end_recognizes_a_real_squash_merge(tmp_path, monkeypatch, capsys):
    """The story's own headline scenario, live-verified during planning and
    now pinned as a regression test: a branch landed via THIS REPO's own
    single-parent squash-merge convention removes cleanly with NO --force,
    even though real bare ancestry (``git merge-base --is-ancestor``) would
    report it as unmerged."""
    slug = "acme"
    repo = _build_repo(tmp_path, slug)
    _seed_real_gitignore(repo)
    loop_home_root = tmp_path / "loop-homes"
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(loop_home_root))
    monkeypatch.chdir(repo)

    assert main(["init", slug]) == 0
    capsys.readouterr()
    home = loop_home_root / slug

    (home / "FEATURE.md").write_text("real feature work\n", encoding="utf-8")
    _git(home, "add", "FEATURE.md")
    _git(home, "commit", "-m", "feature work")

    # This repo's own landing convention: `git merge --squash` + a normal
    # commit -- a SINGLE-parent commit on main, never an ancestry-visible
    # merge.
    _git(repo, "merge", "--squash", f"loop/{slug}")
    _git(repo, "commit", "-m", f"Merge loop/{slug} into main")
    squash_commit = _git(repo, "cat-file", "-p", "HEAD").stdout
    assert squash_commit.count("\nparent ") + (
        1 if squash_commit.startswith("parent ") else 0
    ) == 1

    ancestry = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", f"loop/{slug}", "main"],
        capture_output=True,
    )
    assert ancestry.returncode != 0  # confirms bare ancestry WOULD misreport this

    exit_code = main(["teardown", slug])
    out = capsys.readouterr().out
    assert exit_code == 0, out
    assert "removed: True" in out
    assert "forced" not in out  # no --force needed or given
    assert not home.exists()
    assert _git(repo, "branch", "--list", f"loop/{slug}").stdout.strip() == ""
