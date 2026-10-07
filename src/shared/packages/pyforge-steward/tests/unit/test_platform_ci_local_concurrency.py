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


def _prepare_stub_root(root: Path) -> Path:
    """One-time layout: ``bin/``, pixi env stubs, minimal ``src/platform``."""
    bin_dir = root / "bin"

    service_stub = textwrap.dedent(
        """\
        #!/usr/bin/env bash
        log="${PLATFORM_CI_STUB_LOG:-/dev/null}"
        name="$(basename "$0")"
        work=""
        args=("$@")
        for i in "${!args[@]}"; do
          if [ "${args[$i]}" = "-D" ]; then work="${args[$((i + 1))]%/pg}"; fi
        done
        echo "$name $*" >> "$log"
        case "$name" in
          pg_ctl)
            if [[ "$*" == *stop* ]]; then
              echo "stop pg $$" >> "$log"
              if [ "${PLATFORM_CI_LOCAL_NO_LOCK:-0}" = 1 ] && [ -n "$work" ] && [ -f "$work/.active" ]; then
                active="$(cat "$work/.active")"
                if [ "$active" != "$$" ]; then
                  echo "cross-stop $$ vs active $active" >> "$log"
                  touch "$work/.broken"
                fi
              fi
            fi
            if [[ "$*" == *start* ]]; then
              echo "start pg $$" >> "$log"
              if [ -n "$work" ]; then echo "$$" > "$work/.active"; fi
              if [ "${PLATFORM_CI_STUB_SLOW:-0}" = 1 ]; then sleep 6; fi
            fi
            ;;
          pg_isready)
            if [ -n "$work" ] && [ -f "$work/.broken" ]; then exit 1; fi
            ;;
          redis-server) echo "start redis $$" >> "$log" ;;
          initdb) echo "initdb $$" >> "$log" ;;
        esac
        exit 0
        """
    )

    dev_bin = root / ".pixi" / "envs" / "platform-dev" / "bin"
    for name in ("initdb", "pg_ctl", "pg_isready", "psql", "redis-server"):
        _write_executable(dev_bin / name, service_stub)

    python_stub = textwrap.dedent(
        """\
        #!/usr/bin/env bash
        log="${PLATFORM_CI_STUB_LOG:-/dev/null}"
        echo "python $@ $$" >> "$log"
        exit 0
        """
    )
    for env in ("platform-ci-test", "platform-dev", "pyforge-warden"):
        env_bin = root / ".pixi" / "envs" / env / "bin"
        _write_executable(env_bin / "python", python_stub)
        if env == "platform-ci-test":
            ruff_stub = textwrap.dedent(
                """\
                #!/usr/bin/env bash
                if [ "${PLATFORM_CI_STUB_FAIL_RUFF:-0}" = 1 ]; then exit 1; fi
                exit 0
                """
            )
            _write_executable(env_bin / "ruff", ruff_stub)
            _write_executable(env_bin / "mypy", "#!/usr/bin/env bash\nexit 0\n")

    docker_stub = textwrap.dedent(
        """\
        #!/usr/bin/env bash
        log="${PLATFORM_CI_STUB_LOG:-/dev/null}"
        echo "docker $*" >> "$log"
        exit 0
        """
    )
    _write_executable(bin_dir / "docker", docker_stub)

    plat = root / "src" / "platform"
    plat.mkdir(parents=True, exist_ok=True)
    _write_executable(plat / "manage.py", "#!/usr/bin/env bash\nexit 0\n")
    (plat / "tests" / "policy").mkdir(parents=True, exist_ok=True)
    return bin_dir


def _run_platform_ci_local(
    root: Path,
    bin_dir: Path,
    *,
    stub_log: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    assert _SCRIPT is not None
    run_env = os.environ.copy()
    run_env["PIXI_PROJECT_ROOT"] = str(root)
    run_env["PATH"] = f"{bin_dir}:{run_env.get('PATH', '')}"
    run_env["PLATFORM_CI_LOCAL_ENGINE"] = "docker"
    run_env["PLATFORM_CI_STUB_LOG"] = str(stub_log)
    if env:
        run_env.update(env)
    stub_log.parent.mkdir(parents=True, exist_ok=True)
    stub_log.write_text("", encoding="utf-8")
    return subprocess.run(
        ["bash", str(_SCRIPT), "--test"],
        cwd=root,
        env=run_env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _log_has_cross_stop(log_text: str) -> bool:
    return "cross-stop" in log_text


def test_two_overlapping_runs_with_lock_both_pass(tmp_path: Path) -> None:
    lock = tmp_path / "platform-ci-local.lock"
    work = tmp_path / "work"
    bin_dir = _prepare_stub_root(tmp_path)
    results: list[subprocess.CompletedProcess[str]] = []

    def runner(log: Path, *, slow: bool) -> None:
        results.append(
            _run_platform_ci_local(
                tmp_path,
                bin_dir,
                stub_log=log,
                env={
                    "PLATFORM_CI_LOCAL_LOCK": str(lock),
                    "PLATFORM_CI_LOCAL_WORK": str(work),
                    "PLATFORM_CI_LOCAL_LOCK_WAIT": "120",
                    "PLATFORM_CI_STUB_SLOW": "1" if slow else "0",
                },
            )
        )

    t1 = threading.Thread(target=runner, args=(tmp_path / "run1.log",), kwargs={"slow": True})
    t2 = threading.Thread(target=runner, args=(tmp_path / "run2.log",), kwargs={"slow": False})
    t1.start()
    time.sleep(1)
    t2.start()
    t1.join(timeout=90)
    t2.join(timeout=90)

    assert len(results) == 2
    for proc in results:
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "RESULT: PASS" in proc.stdout

    log1 = (tmp_path / "run1.log").read_text()
    log2 = (tmp_path / "run2.log").read_text()
    assert not _log_has_cross_stop(log1), log1
    assert not _log_has_cross_stop(log2), log2


def test_one_run_fails_other_passes_under_lock(tmp_path: Path) -> None:
    lock = tmp_path / "platform-ci-local.lock"
    work = tmp_path / "work"
    bin_dir = _prepare_stub_root(tmp_path)
    results: list[subprocess.CompletedProcess[str]] = []

    def runner(log: Path, *, fail_ruff: bool, slow: bool) -> None:
        results.append(
            _run_platform_ci_local(
                tmp_path,
                bin_dir,
                stub_log=log,
                env={
                    "PLATFORM_CI_LOCAL_LOCK": str(lock),
                    "PLATFORM_CI_LOCAL_WORK": str(work),
                    "PLATFORM_CI_LOCAL_LOCK_WAIT": "120",
                    "PLATFORM_CI_STUB_FAIL_RUFF": "1" if fail_ruff else "0",
                    "PLATFORM_CI_STUB_SLOW": "1" if slow else "0",
                },
            )
        )

    t1 = threading.Thread(
        target=runner,
        args=(tmp_path / "fail.log",),
        kwargs={"fail_ruff": True, "slow": True},
    )
    t2 = threading.Thread(
        target=runner,
        args=(tmp_path / "ok.log",),
        kwargs={"fail_ruff": False, "slow": False},
    )
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
    bin_dir = _prepare_stub_root(tmp_path)
    holder_done: list[subprocess.CompletedProcess[str]] = []

    def hold() -> None:
        holder_done.append(
            _run_platform_ci_local(
                tmp_path,
                bin_dir,
                stub_log=tmp_path / "holder.log",
                env={
                    "PLATFORM_CI_LOCAL_LOCK": str(lock),
                    "PLATFORM_CI_LOCAL_WORK": str(work),
                    "PLATFORM_CI_LOCAL_LOCK_WAIT": "120",
                    "PLATFORM_CI_STUB_SLOW": "1",
                },
            )
        )

    t = threading.Thread(target=hold)
    t.start()
    time.sleep(1)
    waiter = _run_platform_ci_local(
        tmp_path,
        bin_dir,
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
    bin_dir = _prepare_stub_root(tmp_path)
    env = os.environ.copy()
    env.update(
        {
            "PIXI_PROJECT_ROOT": str(tmp_path),
            "PATH": f"{bin_dir}:{env.get('PATH', '')}",
            "PLATFORM_CI_LOCAL_LOCK": str(lock),
            "PLATFORM_CI_LOCAL_WORK": str(work),
            "PLATFORM_CI_LOCAL_LOCK_WAIT": "120",
            "PLATFORM_CI_LOCAL_ENGINE": "docker",
            "PLATFORM_CI_STUB_SLOW": "1",
        }
    )
    assert _SCRIPT is not None
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
        bin_dir,
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
    bin_dir = _prepare_stub_root(tmp_path)
    results: list[subprocess.CompletedProcess[str]] = []

    def runner(log: Path, *, slow: bool) -> None:
        results.append(
            _run_platform_ci_local(
                tmp_path,
                bin_dir,
                stub_log=log,
                env={
                    "PLATFORM_CI_LOCAL_NO_LOCK": "1",
                    "PLATFORM_CI_LOCAL_WORK": str(work),
                    "PLATFORM_CI_STUB_SLOW": "1" if slow else "0",
                },
            )
        )

    t1 = threading.Thread(target=runner, args=(tmp_path / "run1.log",), kwargs={"slow": True})
    t2 = threading.Thread(target=runner, args=(tmp_path / "run2.log",), kwargs={"slow": False})
    t1.start()
    time.sleep(0.5)
    t2.start()
    t1.join(timeout=90)
    t2.join(timeout=90)

    assert len(results) == 2
    logs = (tmp_path / "run1.log").read_text() + (tmp_path / "run2.log").read_text()
    pass_count = sum(p.returncode == 0 and "RESULT: PASS" in p.stdout for p in results)
    assert pass_count < 2 or _log_has_cross_stop(logs), (
        "without a lock, overlapping runs must cross-stop or fail"
    )


def test_single_run_summary_unchanged(tmp_path: Path) -> None:
    bin_dir = _prepare_stub_root(tmp_path)
    proc = _run_platform_ci_local(
        tmp_path,
        bin_dir,
        stub_log=tmp_path / "solo.log",
        env={
            "PLATFORM_CI_LOCAL_LOCK": str(tmp_path / "solo.lock"),
            "PLATFORM_CI_LOCAL_WORK": str(tmp_path / "solo-work"),
        },
    )
    assert proc.returncode == 0
    assert "RESULT: PASS" in proc.stdout
    assert "===== platform-ci-local summary" in proc.stdout
