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
        check=False,
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


# Steward Story 133.2 (DW-steward-review-2026-11-24-2, defects 3 and 4).


def test_fleet_poll_sync_pushes_the_loop_branch_to_origin(tmp_path: Path):
    """``git push --ff-only`` is not a push option: git refused it, ``2>/dev/null || true`` hid the refusal, and
    a loop branch ahead of its remote was never pushed."""
    remote, home, env = _init_clone_with_remote(tmp_path)
    (home / "local-only.txt").write_text("ahead\n", encoding="utf-8")
    _git(home, "add", "local-only.txt", env=env)
    _git(home, "commit", "-qm", "local commit on loop/acme", env=env)
    tip = _git(home, "rev-parse", "HEAD", env=env)
    assert _git(remote, "rev-parse", "refs/heads/loop/acme", env=env) != tip

    result = _run_sync(home, env)
    assert result.returncode == 0, result.stderr
    assert _git(remote, "rev-parse", "refs/heads/loop/acme", env=env) == tip
    assert _git(remote, "rev-parse", "refs/heads/main", env=env) != tip  # never main


def test_fleet_poll_sync_uses_no_push_flag_git_lacks():
    sync = SYNC_SH.read_text(encoding="utf-8")
    pushes = [
        line.strip()
        for line in sync.splitlines()
        if " push " in line and not line.lstrip().startswith("#")
    ]
    assert pushes, "expected fleet_poll_sync.sh to push the loop branch"
    assert [line for line in pushes if "--ff-only" in line] == []
    assert [
        line for line in pushes if "--force" in line or " -f " in line or "+" in line
    ] == []


def test_fleet_poll_hourly_never_sleeps_more_than_an_hour_between_ticks(tmp_path: Path):
    """The loop slept to the next half hour, ticked, then slept a further hour before sleeping to the next half
    hour again: one tick every two hours. Run with a fake clock stopped at :30:00 and a fake ``sleep`` that records
    its argument in the tick log and ends the loop on its fourth call."""
    import itertools
    import shutil

    scripts = tmp_path / "repo" / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy(SYNC_SH, scripts / SYNC_SH.name)
    shutil.copy(HOURLY_SH, scripts / HOURLY_SH.name)
    log = tmp_path / "repo" / ".cursor" / "fleet-poll.log"
    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    (fakebin / "date").write_text(
        "#!/usr/bin/env bash\n"
        'case "${1:-}" in\n'
        "  +%-M) echo 30 ;;\n"
        "  +%-S) echo 0 ;;\n"
        "  *) echo 2020-01-01T00:30:00Z ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    (fakebin / "sleep").write_text(
        "#!/usr/bin/env bash\n"
        f'log="{log}"\n'
        'mkdir -p "$(dirname "$log")"\n'
        'if [ "$(grep -c "^SLEEP " "$log" 2>/dev/null || true)" -ge 3 ]; then kill -TERM "$PPID"; exit 0; fi\n'
        'echo "SLEEP $1" >> "$log"\n',
        encoding="utf-8",
    )
    for name in ("date", "sleep"):
        (fakebin / name).chmod(0o755)
    env = {
        **_git_env(),
        "PATH": f"{fakebin}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(tmp_path / "home"),
    }
    subprocess.run(
        ["bash", str(scripts / HOURLY_SH.name)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    events = [
        line
        for line in log.read_text(encoding="utf-8").splitlines()
        if line.startswith(("SLEEP ", "=== fleet-poll"))
    ]
    ticks = [
        index
        for index, line in enumerate(events)
        if line.startswith("=== fleet-poll tick")
    ]
    assert len(ticks) >= 2, events
    for earlier, later in itertools.pairwise(ticks):
        slept = sum(
            int(line.split()[1])
            for line in events[earlier:later]
            if line.startswith("SLEEP ")
        )
        assert 0 < slept <= 3600, events
    assert len(ticks) == 3, events  # three sleeps, three ticks: one an hour
