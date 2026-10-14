"""Story 89.1: a killed ``platform-ci-local`` run must not block the next one."""

from __future__ import annotations

import contextlib
import os
import re
import signal
import socket
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest
from test_platform_ci_local_concurrency import (
    _marker_env,
    _no_stub_process_outlives_the_test,  # noqa: F401 -- autouse: no test here leaves a process behind (Story 101.1)
    _prepare_stub_root,
    _run_platform_ci_local,
    _write_executable,
)

try:
    _REPO_ROOT: Path | None = Path(__file__).resolve().parents[6]
except IndexError:
    _REPO_ROOT = None
_SCRIPT = (_REPO_ROOT / "scripts" / "platform-ci-local.sh") if _REPO_ROOT else None

pytestmark = pytest.mark.skipif(
    not (_SCRIPT and _SCRIPT.is_file()),
    reason="scripts/platform-ci-local.sh required",
)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _env_base(tmp_path: Path, bin_dir: Path, *, lock: Path, work: Path) -> dict[str, str]:
    return {
        "PLATFORM_CI_LOCAL_LOCK": str(lock),
        "PLATFORM_CI_LOCAL_WORK": str(work),
        "PLATFORM_CI_LOCAL_PG_PORT": str(_free_port()),
        "PLATFORM_CI_LOCAL_REDIS_PORT": str(_free_port()),
        "PLATFORM_CI_LOCAL_LOCK_WAIT": "5",
    }


def _standins_alive(work: Path) -> list[int]:
    alive: list[int] = []
    pg_pid_file = work / "pg" / "postmaster.pid"
    if pg_pid_file.is_file():
        pid = int(pg_pid_file.read_text(encoding="utf-8").splitlines()[0])
        if _pid_alive(pid):
            alive.append(pid)
    redis_pid = work / "redis.pid"
    if redis_pid.is_file():
        pid = int(redis_pid.read_text(encoding="utf-8").strip())
        if _pid_alive(pid):
            alive.append(pid)
    return alive


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _reap_standins(work: Path) -> None:
    for pid in _standins_alive(work):
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
        try:
            os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            pass


@pytest.fixture
def stub_root(tmp_path: Path) -> tuple[Path, Path]:
    bin_dir = _prepare_stub_root(tmp_path)
    yield tmp_path, bin_dir
    work = tmp_path / "work"
    if work.exists():
        _reap_standins(work)


def test_no_child_holds_run_lock(stub_root: tuple[Path, Path]) -> None:
    root, bin_dir = stub_root
    lock = root / "lock"
    work = root / "work"
    proc = _run_platform_ci_local(
        root,
        bin_dir,
        stub_log=root / "stub.log",
        env=_env_base(root, bin_dir, lock=lock, work=work),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    log = (root / "stub.log").read_text()
    assert "lock_fd=yes" not in log


def _kill_and_follow(
    root: Path,
    bin_dir: Path,
    *,
    lock: Path,
    work: Path,
    kill_mode: str,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "PIXI_PROJECT_ROOT": str(root),
            "PATH": f"{bin_dir}:{env.get('PATH', '')}",
            "PLATFORM_CI_STUB_SLOW": "1",
            "PLATFORM_CI_LOCAL_ENGINE": "docker",
            "PLATFORM_CI_STUB_LOG": str(root / "holder-stub.log"),
            **_marker_env(root),
        }
    )
    env.update(_env_base(root, bin_dir, lock=lock, work=work))
    assert _SCRIPT is not None
    holder = subprocess.Popen(
        ["bash", str(_SCRIPT), "--test"],
        cwd=root,
        env=env,
        start_new_session=True,
    )
    try:
        time.sleep(1.5)
        if kill_mode == "pg_sigkill":
            os.killpg(holder.pid, signal.SIGKILL)
        elif kill_mode == "shell_sigkill":
            os.kill(holder.pid, signal.SIGKILL)
        elif kill_mode == "pg_sigterm":
            os.killpg(holder.pid, signal.SIGTERM)
        else:
            raise ValueError(kill_mode)
        holder.wait(timeout=15)
    finally:
        # Story 101.1: stop what is left of the holder's group. A SIGKILL to the shell alone
        # leaves its slow python stand-in running for up to 8 s. The services it started lead
        # sessions of their own; the follow run reclaims them.
        with contextlib.suppress(ProcessLookupError):
            os.killpg(holder.pid, signal.SIGKILL)
        holder.wait(timeout=15)
    time.sleep(0.5)
    follow = _run_platform_ci_local(
        root,
        bin_dir,
        stub_log=root / "follow-stub.log",
        env=_env_base(root, bin_dir, lock=lock, work=work),
    )
    return follow


@pytest.mark.parametrize(
    "kill_mode",
    ["pg_sigkill", "shell_sigkill", "pg_sigterm"],
)
def test_killed_run_never_blocks_next(stub_root: tuple[Path, Path], kill_mode: str) -> None:
    if sys.platform == "win32":
        pytest.skip("POSIX-only")
    root, bin_dir = stub_root
    lock = root / "lock"
    work = root / "work"
    follow = _kill_and_follow(root, bin_dir, lock=lock, work=work, kill_mode=kill_mode)
    assert follow.returncode == 0, follow.stdout + follow.stderr
    assert "RESULT: PASS" in follow.stdout
    if kill_mode in ("pg_sigkill", "shell_sigkill"):
        log = (root / "follow-stub.log").read_text()
        assert "stop pg" in log or "stopping postgres" in follow.stderr or "stopping redis" in follow.stderr
    assert _standins_alive(work) == []


def test_refuses_port_without_signalling_listener(stub_root: tuple[Path, Path]) -> None:
    root, bin_dir = stub_root
    lock = root / "lock"
    work = root / "work"
    pg_port = _free_port()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", pg_port))
        listener.listen(1)
        proc = _run_platform_ci_local(
            root,
            bin_dir,
            stub_log=root / "port.log",
            env={
                **_env_base(root, bin_dir, lock=lock, work=work),
                "PLATFORM_CI_LOCAL_PG_PORT": str(pg_port),
            },
        )
        assert proc.returncode == 2
        assert str(pg_port) in proc.stderr
        assert _pid_alive(os.getpid())  # listener process still alive


def test_refuses_redis_port_without_signalling_listener(stub_root: tuple[Path, Path]) -> None:
    root, bin_dir = stub_root
    lock = root / "lock"
    work = root / "work"
    redis_port = _free_port()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", redis_port))
        listener.listen(1)
        proc = _run_platform_ci_local(
            root,
            bin_dir,
            stub_log=root / "redis-port.log",
            env={
                **_env_base(root, bin_dir, lock=lock, work=work),
                "PLATFORM_CI_LOCAL_REDIS_PORT": str(redis_port),
            },
        )
        assert proc.returncode == 2
        assert str(redis_port) in proc.stderr


def test_never_signals_reused_pid(stub_root: tuple[Path, Path]) -> None:
    root, bin_dir = stub_root
    lock = root / "lock"
    work = root / "work"
    work.mkdir(parents=True)
    pgdir = work / "pg"
    pgdir.mkdir()
    sleeper = subprocess.Popen(["sleep", "999999"], env={**os.environ, **_marker_env(root)})
    try:
        (pgdir / "postmaster.pid").write_text(f"{sleeper.pid}\n", encoding="utf-8")
        proc = _run_platform_ci_local(
            root,
            bin_dir,
            stub_log=root / "reuse-pg.log",
            env=_env_base(root, bin_dir, lock=lock, work=work),
        )
        assert proc.returncode in (0, 2)
        assert _pid_alive(sleeper.pid)
    finally:
        sleeper.kill()
        sleeper.wait(timeout=5)

    redis_dir = work / "redis"
    redis_dir.mkdir(exist_ok=True)
    sleeper2 = subprocess.Popen(["sleep", "999999"], env={**os.environ, **_marker_env(root)})
    try:
        (work / "redis.pid").write_text(str(sleeper2.pid), encoding="utf-8")
        proc2 = _run_platform_ci_local(
            root,
            bin_dir,
            stub_log=root / "reuse-redis.log",
            env=_env_base(root, bin_dir, lock=lock, work=work / "redis-case"),
        )
        assert proc2.returncode in (0, 2)
        assert _pid_alive(sleeper2.pid)
    finally:
        sleeper2.kill()
        sleeper2.wait(timeout=5)


def test_lock_wait_names_live_holder_and_stale_record(stub_root: tuple[Path, Path]) -> None:
    if sys.platform == "win32":
        pytest.skip("POSIX-only")
    root, bin_dir = stub_root
    lock = root / "lock"
    work = root / "work"
    lock.parent.mkdir(parents=True, exist_ok=True)
    holder_script = root / "lock_holder.sh"
    _write_executable(
        holder_script,
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            exec 9>"{lock}"
            flock 9
            exec sleep 999999
            """
        ),
    )
    holder = subprocess.Popen(
        ["bash", str(holder_script)],
        cwd=root,
        env={**os.environ, **_marker_env(root)},
        start_new_session=True,
    )
    time.sleep(0.3)
    (lock.parent / f"{lock.name}.holder").write_text(
        "pid=999999\ncheckout=dead\nstages=test\nstarted=2020-01-01T00:00:00\n",
        encoding="utf-8",
    )
    try:
        proc = _run_platform_ci_local(
            root,
            bin_dir,
            stub_log=root / "wait.log",
            env={
                **_env_base(root, bin_dir, lock=lock, work=work),
                "PLATFORM_CI_LOCAL_LOCK_WAIT": "2",
            },
        )
        assert proc.returncode == 2
        assert "999999" in proc.stderr
        assert "stale" in proc.stderr.lower()
        assert str(holder.pid) in proc.stderr
        # Story 101.1: the report lists exactly the process holding the lock, never the
        # waiter or its own helpers (the waiter closes fd 9 before it scans).
        listed = [int(pid) for pid in re.findall(r"^  pid=(\d+) cmdline=", proc.stderr, re.MULTILINE)]
        assert listed == [holder.pid], proc.stderr
    finally:
        os.kill(holder.pid, signal.SIGKILL)
        holder.wait(timeout=5)


def test_normal_run_cleans_up(stub_root: tuple[Path, Path]) -> None:
    root, bin_dir = stub_root
    lock = root / "solo.lock"
    work = root / "solo-work"
    ok = _run_platform_ci_local(
        root,
        bin_dir,
        stub_log=root / "ok.log",
        env=_env_base(root, bin_dir, lock=lock, work=work),
    )
    assert ok.returncode == 0
    assert _standins_alive(work) == []

    fail_env = _env_base(root, bin_dir, lock=root / "fail.lock", work=root / "fail-work")
    fail_env["PLATFORM_CI_STUB_FAIL_RUFF"] = "1"
    bad = _run_platform_ci_local(
        root,
        bin_dir,
        stub_log=root / "fail.log",
        env=fail_env,
    )
    assert bad.returncode == 1
    assert _standins_alive(root / "fail-work") == []
