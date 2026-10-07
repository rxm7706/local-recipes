"""Story 63.7: overlapping ``platform-ci-local -- --test`` runs must not cross-stop services.

Loads the real ``scripts/platform-ci-local.sh`` with stub pixi env binaries and a
minimal ``src/platform`` tree — no PostgreSQL, Redis or container engine required.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path

import pytest

try:
    _REPO_ROOT: Path | None = Path(__file__).resolve().parents[6]
except IndexError:
    _REPO_ROOT = None
_SCRIPT = (_REPO_ROOT / "scripts" / "platform-ci-local.sh") if _REPO_ROOT else None

pytestmark = pytest.mark.skipif(
    not (_SCRIPT and _SCRIPT.is_file()),
    reason="scripts/platform-ci-local.sh required",
)


def _write_executable(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _stub_bin(root: Path, *, stub_log: Path, slow: bool = False, fail_ruff: bool = False) -> Path:
    """Return ``root/bin`` prepended to PATH: docker + pixi env stubs."""
    bin_dir = root / "bin"
    log = stub_log
    slow_flag = "1" if slow else "0"
    fail_ruff_flag = "1" if fail_ruff else "0"

    service_stub = textwrap.dedent(
        f"""\
        #!/usr/bin/env bash
        log="{log}"
        name="$(basename "$0")"
        echo "$name $*" >> "$log"
        case "$name" in
          pg_ctl)
            if [[ "$*" == *stop* ]]; then echo "stop pg $$" >> "$log"; fi
            if [[ "$*" == *start* ]]; then echo "start pg $$" >> "$log"; fi
            ;;
          redis-server) echo "start redis $$" >> "$log" ;;
          initdb) echo "initdb $$" >> "$log" ;;
        esac
        exit 0
        """
    )

    for name in ("initdb", "pg_ctl", "pg_isready", "psql", "redis-server"):
        _write_executable(bin_dir / name, service_stub)

    python_stub = textwrap.dedent(
        f"""\
        #!/usr/bin/env bash
        log="{log}"
        if [ "{slow_flag}" = 1 ]; then sleep 3; fi
        if [[ "$1" == *manage.py* ]] || [[ "$1" == *pytest* ]] || [[ "$1" == *db.sqlmigrate* ]]; then
          echo "python-test $$" >> "$log"
          exit 0
        fi
        echo "python $@ $$" >> "$log"
        exit 0
        """
    )
    for env in ("platform-ci-test", "platform-dev", "pyforge-warden"):
        env_bin = root / ".pixi" / "envs" / env / "bin"
        _write_executable(env_bin / "python", python_stub)
        if env == "platform-ci-test":
            ruff_stub = textwrap.dedent(
                f"""\
                #!/usr/bin/env bash
                if [ "{fail_ruff_flag}" = 1 ]; then exit 1; fi
                exit 0
                """
            )
            _write_executable(env_bin / "ruff", ruff_stub)
            _write_executable(env_bin / "mypy", "#!/usr/bin/env bash\nexit 0\n")

    docker_stub = textwrap.dedent(
        f"""\
        #!/usr/bin/env bash
        echo "docker $*" >> "{log}"
        exit 0
        """
    )
    _write_executable(bin_dir / "docker", docker_stub)
    return bin_dir


def _minimal_platform(root: Path) -> None:
    plat = root / "src" / "platform"
    plat.mkdir(parents=True)
    _write_executable(
        plat / "manage.py",
        "#!/usr/bin/env bash\nexit 0\n",
    )
    (plat / "tests").mkdir()
    (plat / "tests" / "policy").mkdir()


def _run_platform_ci_local(
    root: Path,
    *,
    stub_log: Path,
    env: dict[str, str] | None = None,
    slow: bool = False,
    fail_ruff: bool = False,
) -> subprocess.CompletedProcess[str]:
    assert _SCRIPT is not None
    bin_dir = _stub_bin(root, stub_log=stub_log, slow=slow, fail_ruff=fail_ruff)
    _minimal_platform(root)
    run_env = os.environ.copy()
    run_env["PIXI_PROJECT_ROOT"] = str(root)
    run_env["PATH"] = f"{bin_dir}:{run_env.get('PATH', '')}"
    run_env["PLATFORM_CI_LOCAL_ENGINE"] = "docker"
    if env:
        run_env.update(env)
    return subprocess.run(
        ["bash", str(_SCRIPT), "--test"],
        cwd=root,
        env=run_env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _parse_service_events(log_text: str) -> list[tuple[str, str]]:
    """Return (event, pid) tuples for postgres lifecycle lines."""
    out: list[tuple[str, str]] = []
    for line in log_text.splitlines():
        if line.startswith("start pg "):
            out.append(("start", line.rsplit(" ", 1)[-1]))
        elif line.startswith("stop pg "):
            out.append(("stop", line.rsplit(" ", 1)[-1]))
    return out


def test_two_overlapping_runs_with_lock_both_pass(tmp_path: Path) -> None:
    lock = tmp_path / "platform-ci-local.lock"
    work = tmp_path / "work"
    log1 = tmp_path / "run1.log"
    log2 = tmp_path / "run2.log"
    results: list[subprocess.CompletedProcess[str]] = []

    def runner(log: Path, slow: bool) -> None:
        results.append(
            _run_platform_ci_local(
                tmp_path,
                stub_log=log,
                slow=slow,
                env={
                    "PLATFORM_CI_LOCAL_LOCK": str(lock),
                    "PLATFORM_CI_LOCAL_WORK": str(work),
                    "PLATFORM_CI_LOCAL_LOCK_WAIT": "120",
                },
            )
        )

    t1 = threading.Thread(target=runner, args=(log1, True))
    t2 = threading.Thread(target=runner, args=(log2, False))
    t1.start()
    time.sleep(1)
    t2.start()
    t1.join(timeout=90)
    t2.join(timeout=90)

    assert len(results) == 2
    for proc in results:
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "RESULT: PASS" in proc.stdout

    ev1 = _parse_service_events(log1.read_text())
    ev2 = _parse_service_events(log2.read_text())
    assert ev1 and ev1[0][0] == "start"
    if any(e[0] == "stop" for e in ev1):
        stop_pid = next(e[1] for e in ev1 if e[0] == "stop")
        assert stop_pid == ev1[0][1], "run 1's postgres must not be stopped by another pid"


def test_one_run_fails_other_passes_under_lock(tmp_path: Path) -> None:
    lock = tmp_path / "platform-ci-local.lock"
    work = tmp_path / "work"
    log_ok = tmp_path / "ok.log"
    log_fail = tmp_path / "fail.log"
    results: list[subprocess.CompletedProcess[str]] = []

    def runner(log: Path, *, fail_ruff: bool, slow: bool) -> None:
        results.append(
            _run_platform_ci_local(
                tmp_path,
                stub_log=log,
                slow=slow,
                fail_ruff=fail_ruff,
                env={
                    "PLATFORM_CI_LOCAL_LOCK": str(lock),
                    "PLATFORM_CI_LOCAL_WORK": str(work),
                    "PLATFORM_CI_LOCAL_LOCK_WAIT": "120",
                },
            )
        )

    t1 = threading.Thread(target=runner, kwargs={"log": log_fail, "fail_ruff": True, "slow": True})
    t2 = threading.Thread(target=runner, kwargs={"log": log_ok, "fail_ruff": False, "slow": False})
    t1.start()
    time.sleep(1)
    t2.start()
    t1.join(timeout=90)
    t2.join(timeout=90)

    assert len(results) == 2
    codes = sorted(p.returncode for p in results)
    assert codes == [0, 1]
    outputs = [p.stdout for p in results]
    assert sum("RESULT: PASS" in o for o in outputs) == 1
    assert sum("RESULT: FAIL" in o for o in outputs) == 1


def test_lock_wait_timeout_names_holder(tmp_path: Path) -> None:
    lock = tmp_path / "platform-ci-local.lock"
    work = tmp_path / "work"
    log_holder = tmp_path / "holder.log"
    holder_done: list[subprocess.CompletedProcess[str]] = []

    def hold() -> None:
        holder_done.append(
            _run_platform_ci_local(
                tmp_path,
                stub_log=log_holder,
                slow=True,
                env={
                    "PLATFORM_CI_LOCAL_LOCK": str(lock),
                    "PLATFORM_CI_LOCAL_WORK": str(work),
                    "PLATFORM_CI_LOCAL_LOCK_WAIT": "120",
                },
            )
        )

    t = threading.Thread(target=hold)
    t.start()
    time.sleep(1)
    waiter = _run_platform_ci_local(
        tmp_path,
        stub_log=tmp_path / "waiter.log",
        env={
            "PLATFORM_CI_LOCAL_LOCK": str(lock),
            "PLATFORM_CI_LOCAL_WORK": str(work / "waiter"),
            "PLATFORM_CI_LOCAL_LOCK_WAIT": "2",
        },
    )
    t.join(timeout=90)
    assert waiter.returncode == 2
    assert "holder" in waiter.stderr.lower() or "lock held" in waiter.stderr.lower()
    assert "pid=" in waiter.stderr


def test_sigkilled_holder_does_not_block_next_run(tmp_path: Path) -> None:
    if sys.platform == "win32":
        pytest.skip("SIGKILL holder test is POSIX-only")
    lock = tmp_path / "platform-ci-local.lock"
    work = tmp_path / "work"
    log_holder = tmp_path / "holder.log"
    bin_dir = _stub_bin(tmp_path, stub_log=log_holder, slow=True)
    _minimal_platform(tmp_path)
    env = os.environ.copy()
    env.update(
        {
            "PIXI_PROJECT_ROOT": str(tmp_path),
            "PATH": f"{bin_dir}:{env.get('PATH', '')}",
            "PLATFORM_CI_LOCAL_LOCK": str(lock),
            "PLATFORM_CI_LOCAL_WORK": str(work),
            "PLATFORM_CI_LOCAL_LOCK_WAIT": "120",
            "PLATFORM_CI_LOCAL_ENGINE": "docker",
        }
    )
    holder = subprocess.Popen(
        ["bash", str(_SCRIPT), "--test"],
        cwd=tmp_path,
        env=env,
    )
    time.sleep(1)
    os.kill(holder.pid, signal.SIGKILL)
    holder.wait(timeout=10)
    follow = _run_platform_ci_local(
        tmp_path,
        stub_log=tmp_path / "follow.log",
        env={
            "PLATFORM_CI_LOCAL_LOCK": str(lock),
            "PLATFORM_CI_LOCAL_WORK": str(work),
            "PLATFORM_CI_LOCAL_LOCK_WAIT": "30",
        },
    )
    assert follow.returncode == 0
    assert "RESULT: PASS" in follow.stdout


def test_without_lock_overlapping_runs_do_not_both_pass(tmp_path: Path) -> None:
    work = tmp_path / "shared-work"
    log1 = tmp_path / "run1.log"
    log2 = tmp_path / "run2.log"
    results: list[subprocess.CompletedProcess[str]] = []

    def runner(log: Path, slow: bool) -> None:
        results.append(
            _run_platform_ci_local(
                tmp_path,
                stub_log=log,
                slow=slow,
                env={
                    "PLATFORM_CI_LOCAL_NO_LOCK": "1",
                    "PLATFORM_CI_LOCAL_WORK": str(work),
                },
            )
        )

    t1 = threading.Thread(target=runner, args=(log1, True))
    t2 = threading.Thread(target=runner, args=(log2, False))
    t1.start()
    time.sleep(0.5)
    t2.start()
    t1.join(timeout=90)
    t2.join(timeout=90)

    assert len(results) == 2
    pass_count = sum(p.returncode == 0 and "RESULT: PASS" in p.stdout for p in results)
    assert pass_count < 2, "without a lock, overlapping runs must not both pass"


def test_single_run_summary_unchanged(tmp_path: Path) -> None:
    log = tmp_path / "solo.log"
    proc = _run_platform_ci_local(
        tmp_path,
        stub_log=log,
        env={
            "PLATFORM_CI_LOCAL_LOCK": str(tmp_path / "solo.lock"),
            "PLATFORM_CI_LOCAL_WORK": str(tmp_path / "solo-work"),
        },
    )
    assert proc.returncode == 0
    assert "RESULT: PASS" in proc.stdout
    assert "===== platform-ci-local summary" in proc.stdout
