"""Story 87.13: fleet poll sync fast-forwards ``loop/*`` only (AD-46).

Uses real git repositories and a bare ``origin``, mirroring
``test_bmad_loop_baseline_drift_check.py``'s harness style.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
SYNC_SH = SCRIPTS / "fleet_poll_sync.sh"
HOURLY_SH = SCRIPTS / "fleet-poll-hourly.sh"


def _git(repo: Path, *args: str, env: dict | None = None) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    ).stdout.strip()


def _git_env() -> dict[str, str]:
    return {
        **os.environ,
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
    }


def _init_clone_with_remote(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Bare remote, a clone on ``loop/acme``, returns (remote, clone, env)."""
    env = _git_env()
    remote = tmp_path / "remote.git"
    clone = tmp_path / "home"
    subprocess.run(
        ["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True, env=env
    )
    subprocess.run(
        ["git", "clone", "-q", str(remote), str(clone)],
        check=True,
        env=env,
        capture_output=True,
    )
    _git(clone, "config", "user.email", "t@example.com", env=env)
    _git(clone, "config", "user.name", "T", env=env)
    (clone / "README.md").write_text("base\n", encoding="utf-8")
    _git(clone, "add", "README.md", env=env)
    _git(clone, "commit", "-qm", "init", env=env)
    _git(clone, "checkout", "-b", "loop/acme", env=env)
    _git(clone, "push", "-u", "origin", "loop/acme", env=env)
    _git(clone, "checkout", "main", env=env)
    _git(clone, "merge", "--ff-only", "loop/acme", env=env)
    _git(clone, "push", "origin", "main", env=env)
    _git(clone, "checkout", "loop/acme", env=env)
    return remote, clone, env


def _run_sync(repo: Path, env: dict) -> subprocess.CompletedProcess[str]:
    cmd = f'source "{SYNC_SH}" && fleet_poll_sync "{repo}"'
    return subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
        env=env,
    )


def test_fleet_poll_scripts_never_rebase_or_push_main():
    """AC mutation guard: forbidden rewrite/push forms stay absent."""
    hourly = HOURLY_SH.read_text(encoding="utf-8")
    sync = SYNC_SH.read_text(encoding="utf-8")
    combined = hourly + sync
    assert "pull --rebase" not in combined
    assert "push origin main" not in combined
    assert "--ff-only" in sync


def test_fleet_poll_sync_fast_forwards_loop_branch_when_behind_origin_main(
    tmp_path: Path,
):
    remote, home, env = _init_clone_with_remote(tmp_path)
    tip_before = _git(home, "rev-parse", "HEAD", env=env)

    # Advance origin/main on the bare remote via a second clone.
    upstream = tmp_path / "upstream"
    subprocess.run(
        ["git", "clone", "-q", str(remote), str(upstream)],
        check=True,
        env=env,
        capture_output=True,
    )
    _git(upstream, "config", "user.email", "t@example.com", env=env)
    _git(upstream, "config", "user.name", "T", env=env)
    (upstream / "on-main.txt").write_text("new on main\n", encoding="utf-8")
    _git(upstream, "add", "on-main.txt", env=env)
    _git(upstream, "commit", "-qm", "advance main", env=env)
    _git(upstream, "push", "origin", "main", env=env)

    result = _run_sync(home, env)
    assert result.returncode == 0, result.stderr
    tip_after = _git(home, "rev-parse", "HEAD", env=env)
    origin_main = _git(home, "rev-parse", "origin/main", env=env)
    assert tip_before != tip_after
    assert tip_after == origin_main


def test_fleet_poll_sync_logs_diverged_and_does_not_rewrite(tmp_path: Path):
    remote, home, env = _init_clone_with_remote(tmp_path)
    (home / "local-only.txt").write_text("diverge\n", encoding="utf-8")
    _git(home, "add", "local-only.txt", env=env)
    _git(home, "commit", "-qm", "local commit on loop/acme", env=env)
    tip_before = _git(home, "rev-parse", "HEAD", env=env)

    upstream = tmp_path / "upstream"
    subprocess.run(
        ["git", "clone", "-q", str(remote), str(upstream)],
        check=True,
        env=env,
        capture_output=True,
    )
    _git(upstream, "config", "user.email", "t@example.com", env=env)
    _git(upstream, "config", "user.name", "T", env=env)
    (upstream / "on-main.txt").write_text("remote main moved\n", encoding="utf-8")
    _git(upstream, "add", "on-main.txt", env=env)
    _git(upstream, "commit", "-qm", "advance main", env=env)
    _git(upstream, "push", "origin", "main", env=env)

    result = _run_sync(home, env)
    assert result.returncode == 0, result.stderr
    assert "fleet-poll: diverged:" in result.stderr
    assert _git(home, "rev-parse", "HEAD", env=env) == tip_before


def test_fleet_poll_sync_skips_non_loop_branch(tmp_path: Path):
    env = _git_env()
    repo = tmp_path / "repo"
    subprocess.run(
        ["git", "init", "-q", "-b", "dispatch/acme", str(repo)], check=True, env=env
    )
    _git(repo, "config", "user.email", "t@example.com", env=env)
    _git(repo, "config", "user.name", "T", env=env)
    (repo / "f.txt").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "f.txt", env=env)
    _git(repo, "commit", "-qm", "init", env=env)
    tip = _git(repo, "rev-parse", "HEAD", env=env)

    result = _run_sync(repo, env)
    assert result.returncode == 0
    assert _git(repo, "rev-parse", "HEAD", env=env) == tip


def test_fleet_poll_sync_mutation_if_merge_ff_only_removed(tmp_path: Path):
    """Removing ``merge --ff-only`` must fail the behind-main case."""
    sync = SYNC_SH.read_text(encoding="utf-8")
    if "merge --ff-only origin/main" not in sync:
        pytest.fail("expected merge --ff-only origin/main in fleet_poll_sync.sh")
