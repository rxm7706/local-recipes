"""Story 63.7: overlapping ``platform-ci-local -- --test`` runs must not cross-stop services.

Loads the real ``scripts/platform-ci-local.sh`` with stub pixi env binaries and a
minimal ``src/platform`` tree — no PostgreSQL, Redis or container engine required.

Story 101.1: every process a test here starts carries ``PLATFORM_CI_STUB_MARKER=<tmp_path>``,
and an autouse fixture (imported by the other ``test_platform_ci_local_*`` modules) fails a
test that leaves one behind. The check is scoped to that marker, never to a process name.
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import signal
import subprocess
import sys
import textwrap
import threading
import time
from collections.abc import Iterator
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

_MARKER_VAR = "PLATFORM_CI_STUB_MARKER"


def _marker_env(root: Path) -> dict[str, str]:
    """The environment entry every process a test starts carries (Story 101.1)."""
    return {_MARKER_VAR: str(root)}


def _marked_pids(root: Path) -> list[int]:
    """Pids, other than this one, whose environment holds exactly ``root``'s marker entry.

    Scoped to one test's marker, never a process name or a host-wide pattern. A zombie's
    environ reads empty, so a process that has exited never matches.
    """
    proc = Path("/proc")
    if not proc.is_dir():
        return []
    entry = f"{_MARKER_VAR}={root}".encode()
    me = os.getpid()
    found: list[int] = []
    for name in os.listdir(proc):
        if not name.isdigit() or int(name) == me:
            continue
        try:
            environ = (proc / name / "environ").read_bytes()
        except OSError:
            continue
        if entry in environ.split(b"\0"):
            found.append(int(name))
    return sorted(found)


def _wait_marked_gone(root: Path, timeout: float = 5.0) -> list[int]:
    """Poll until no process carries ``root``'s marker; return whatever is left at the deadline."""
    deadline = time.monotonic() + timeout
    while True:
        pids = _marked_pids(root)
        if not pids or time.monotonic() >= deadline:
            return pids
        time.sleep(0.1)


def _cmdline(pid: int) -> str:
    try:
        raw = Path("/proc", str(pid), "cmdline").read_bytes()
    except OSError:
        return "?"
    return raw.replace(b"\0", b" ").decode(errors="replace").strip()


@pytest.fixture(autouse=True)
def _no_stub_process_outlives_the_test(tmp_path: Path) -> Iterator[None]:
    """Story 101.1: a test that leaves a process carrying its marker fails, after those are killed."""
    yield
    survivors = _wait_marked_gone(tmp_path)
    if not survivors:
        return
    described = [f"pid={pid} cmdline={_cmdline(pid)}" for pid in survivors]
    for pid in survivors:
        with contextlib.suppress(OSError):
            os.kill(pid, signal.SIGKILL)
    pytest.fail("processes started by the test outlived it:\n" + "\n".join(described))


def _write_executable(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _prepare_stub_root(root: Path) -> Path:
    """One-time layout: ``bin/``, pixi env stubs, minimal ``src/platform``."""
    bin_dir = root / "bin"

    # The postgres and redis-server stand-ins exec their long-running process, so the pid the
    # stub records is the one the stop path kills; a bash wrapper's sleep child outlived every
    # stop (Story 101.1). ``exec -a "$0 $*"`` keeps the cmdline that _is_our_postgres and
    # _is_our_redis prove. pg_ctl reads its action as a whole argument: a substring match on
    # "$*" took a tmp path naming "start" for a start, so a stop started a second postgres.
    service_stub = textwrap.dedent(
        """\
        #!/usr/bin/env bash
        log="${PLATFORM_CI_STUB_LOG:-/dev/null}"
        lock="${PLATFORM_CI_LOCAL_LOCK:-}"
        name="$(basename "$0")"
        work=""
        pgdata=""
        action=""
        args=("$@")
        for i in "${!args[@]}"; do
          if [ "${args[$i]}" = "-D" ]; then
            pgdata="${args[$((i + 1))]}"
            work="${pgdata%/pg}"
          fi
          case "${args[$i]}" in start|stop) action="${args[$i]}" ;; esac
        done
        held=""
        if [ -n "$lock" ]; then
          for fd in /proc/self/fd/*; do
            target="$(readlink "$fd" 2>/dev/null || true)"
            [ "$target" = "$lock" ] && held=yes
          done
        fi
        echo "$name $* pid=$$ lock_fd=${held:-no}" >> "$log"
        case "$name" in
          pg_ctl)
            if [ "$action" = stop ]; then
              echo "stop pg $$" >> "$log"
              if [ -n "$pgdata" ] && [ -f "$pgdata/postmaster.pid" ]; then
                kill "$(head -1 "$pgdata/postmaster.pid")" 2>/dev/null || true
              fi
              if [ "${PLATFORM_CI_LOCAL_NO_LOCK:-0}" = 1 ] && [ -n "$work" ] && [ -f "$work/.active" ]; then
                active="$(cat "$work/.active")"
                if [ "$active" != "$$" ]; then
                  echo "cross-stop $$ vs active $active" >> "$log"
                  touch "$work/.broken"
                fi
              fi
            fi
            if [ "$action" = start ]; then
              echo "start pg $$" >> "$log"
              if [ -n "$pgdata" ]; then
                cat > "$pgdata/postgres" <<'STIN'
        #!/usr/bin/env bash
        exec -a "$0 $*" sleep 999999
        STIN
                chmod +x "$pgdata/postgres"
                setsid "$pgdata/postgres" -D "$pgdata" >> "$log" 2>&1 &
                echo $! > "$pgdata/postmaster.pid"
                echo "spawned postgres pid=$! marker=${PLATFORM_CI_STUB_MARKER:-none}" >> "$log"
                if [ -n "$work" ]; then echo "$!" > "$work/.active"; fi
              fi
            fi
            ;;
          pg_isready)
            if [ -n "$work" ] && [ -f "$work/.broken" ]; then exit 1; fi
            ;;
          redis-server)
            rdir=""
            rport=""
            prev=""
            for arg in "$@"; do
              if [ "$prev" = "--dir" ]; then rdir="$arg"; fi
              if [ "$prev" = "--port" ]; then rport="$arg"; fi
              prev="$arg"
            done
            pidfile=""
            for i in "${!args[@]}"; do
              if [ "${args[$i]}" = "--pidfile" ]; then pidfile="${args[$((i + 1))]}"; fi
            done
            echo "start redis $$" >> "$log"
            if [ -n "$rdir" ]; then
              cat > "$rdir/redis-server" <<'STIN'
        #!/usr/bin/env bash
        exec -a "$0 $*" sleep 999999
        STIN
              chmod +x "$rdir/redis-server"
              setsid "$rdir/redis-server" --port "${rport:-0}" >> "$log" 2>&1 &
              [ -n "$pidfile" ] && echo $! > "$pidfile"
              echo "spawned redis-server pid=$! marker=${PLATFORM_CI_STUB_MARKER:-none}" >> "$log"
            fi
            ;;
          initdb)
            data=""
            prev=""
            for arg in "$@"; do
              if [ "$prev" = "-D" ]; then data="$arg"; fi
              prev="$arg"
            done
            [ -n "$data" ] && mkdir -p "$data"
            echo "initdb $$" >> "$log"
            ;;
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
        if [ "${PLATFORM_CI_STUB_SLOW:-0}" = 1 ]; then sleep 8; fi
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

    pixi_stub = textwrap.dedent(
        """\
        #!/usr/bin/env bash
        log="${PLATFORM_CI_STUB_LOG:-/dev/null}"
        lock="${PLATFORM_CI_LOCAL_LOCK:-}"
        held=""
        if [ -n "$lock" ]; then
          for fd in /proc/self/fd/*; do
            target="$(readlink "$fd" 2>/dev/null || true)"
            [ "$target" = "$lock" ] && held=yes
          done
        fi
        echo "pixi $* pid=$$ lock_fd=${held:-no}" >> "$log"
        if [[ " $* " == *" install "* ]]; then
          if flock -n "$lock" true 2>/dev/null; then
            echo "pixi flock_n=held" >> "$log"
          else
            echo "pixi flock_n=blocked" >> "$log"
          fi
          env_name=""
          prev=""
          for arg in "$@"; do
            if [ "$prev" = "-e" ]; then env_name="$arg"; fi
            prev="$arg"
          done
          exit_code=0
          case "$env_name" in
            platform-ci-test) exit_code="${PLATFORM_CI_STUB_PIXI_EXIT_CIT:-0}" ;;
            platform-dev) exit_code="${PLATFORM_CI_STUB_PIXI_EXIT_DEV:-0}" ;;
            pyforge-warden) exit_code="${PLATFORM_CI_STUB_PIXI_EXIT_WRD:-0}" ;;
          esac
          if [ "$exit_code" != 0 ]; then exit "$exit_code"; fi
          root="${PIXI_PROJECT_ROOT:-}"
          if [ -n "$root" ] && [ -n "$env_name" ]; then
            meta="$root/.pixi/envs/$env_name/conda-meta"
            mkdir -p "$meta"
            write_hash="${PLATFORM_CI_STUB_PIXI_WRITE_HASH:-}"
            if [ -n "$write_hash" ]; then
              printf '{"environment_lock_file_hash":"%s"}\\n' "$write_hash" > "$meta/pixi"
            elif [ "${PLATFORM_CI_STUB_PIXI_LEAVE_HASH:-0}" != 1 ]; then
              if [ -f "$meta/pixi" ]; then
                :
              else
                printf '{"environment_lock_file_hash":"new"}\\n' > "$meta/pixi"
              fi
            fi
          fi
        fi
        exit 0
        """
    )
    _write_executable(bin_dir / "pixi", pixi_stub)

    plat = root / "src" / "platform"
    plat.mkdir(parents=True, exist_ok=True)
    _write_executable(plat / "manage.py", "#!/usr/bin/env bash\nexit 0\n")
    (plat / "tests" / "policy").mkdir(parents=True, exist_ok=True)
    return bin_dir


def _write_recording_fuser(bin_dir: Path) -> None:
    """Put a ``fuser`` first on the run's PATH that logs each call (Story 101.1).

    It hands each call to the host's ``fuser``, or, where there is none, to the same
    fork-free ``/proc`` walk the script falls back to, so the listing stays the real one.
    """
    real = shutil.which("fuser") or ""
    _write_executable(
        bin_dir / "fuser",
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            echo "fuser $*" >> "${{PLATFORM_CI_STUB_LOG:-/dev/null}}"
            if [ -n "{real}" ]; then exec "{real}" "$@"; fi
            target="${{@: -1}}"
            for fd in /proc/[0-9]*/fd/*; do
              [ "$fd" -ef "$target" ] || continue
              fd="${{fd#/proc/}}"
              printf ' %s' "${{fd%%/*}}"
            done
            echo
            """
        ),
    )


def _fuser_scans(stub_log: Path) -> list[str]:
    """The recording ``fuser``'s calls in ``stub_log``: one per holder scan."""
    return [ln for ln in stub_log.read_text(encoding="utf-8").splitlines() if ln.startswith("fuser ")]


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
    run_env.update(_marker_env(root))
    run_env.setdefault("PLATFORM_CI_LOCAL_PG_PORT", "35432")
    run_env.setdefault("PLATFORM_CI_LOCAL_REDIS_PORT", "36379")
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

    _write_recording_fuser(bin_dir)  # Story 101.1: counts the report's scans
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
    # Story 101.1: with a live .holder record too, the report scans once; the listing and the
    # live-record check read the same scan.
    assert len(_fuser_scans(tmp_path / "waiter.log")) == 1, _fuser_scans(tmp_path / "waiter.log")


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
            **_marker_env(tmp_path),
        }
    )
    assert _SCRIPT is not None
    holder = subprocess.Popen(
        ["bash", str(_SCRIPT), "--test"],
        cwd=tmp_path,
        env=env,
        start_new_session=True,
    )
    time.sleep(1)
    os.killpg(holder.pid, signal.SIGKILL)
    holder.wait(timeout=10)
    time.sleep(0.5)
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
    time.sleep(2)
    t2.start()
    t1.join(timeout=90)
    t2.join(timeout=90)

    assert len(results) == 2
    logs = (tmp_path / "run1.log").read_text() + (tmp_path / "run2.log").read_text()
    pass_count = sum(p.returncode == 0 and "RESULT: PASS" in p.stdout for p in results)
    assert pass_count < 2 or _log_has_cross_stop(logs), (
        f"without a lock, overlapping runs must cross-stop or fail; logs:\n{logs}"
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


def _wait_comm(pid: int, comm: str, timeout: float = 5.0) -> str:
    """Poll ``/proc/<pid>/comm`` until it reads ``comm``; return the last value read."""
    deadline = time.monotonic() + timeout
    seen = ""
    while time.monotonic() < deadline:
        try:
            seen = Path("/proc", str(pid), "comm").read_text(encoding="utf-8").strip()
        except OSError:
            seen = ""
        if seen == comm:
            break
        time.sleep(0.05)
    return seen


def _running(pid: int) -> bool:
    """True while ``pid`` exists and is not a zombie."""
    try:
        stat = Path("/proc", str(pid), "stat").read_text(encoding="utf-8")
    except OSError:
        return False
    return stat.rsplit(")", 1)[-1].split()[0] != "Z"


def _wait_not_running(pid: int, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while _running(pid):
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.05)
    return True


def test_stub_start_stop_cycle_leaves_no_process(tmp_path: Path) -> None:
    """Story 101.1: each service stand-in records the process the stop path kills.

    Before the fix the recorded pid was a bash wrapper and its ``sleep 999999`` child
    outlived every stop, two per run; 6,222 had gathered on the host by 2026-10-14.
    """
    if not Path("/proc/self/fd").is_dir():
        pytest.skip("needs /proc")
    bin_dir = _prepare_stub_root(tmp_path)
    dev_bin = tmp_path / ".pixi" / "envs" / "platform-dev" / "bin"
    env = {**os.environ, **_marker_env(tmp_path), "PLATFORM_CI_STUB_LOG": str(tmp_path / "stub.log")}

    pgdata = tmp_path / "direct" / "pg"
    pgdata.mkdir(parents=True)
    subprocess.run([str(dev_bin / "pg_ctl"), "-D", str(pgdata), "start"], env=env, check=True, timeout=30)
    pg_pid = int((pgdata / "postmaster.pid").read_text(encoding="utf-8").split()[0])
    assert _wait_comm(pg_pid, "sleep") == "sleep"
    assert pg_pid in _marked_pids(tmp_path), "the postgres stand-in dropped the test's marker"
    pg_cmd = _cmdline(pg_pid)
    assert "postgres" in pg_cmd and f"-D {pgdata}" in pg_cmd, pg_cmd
    subprocess.run([str(dev_bin / "pg_ctl"), "-D", str(pgdata), "stop", "-m", "fast"], env=env, check=True, timeout=30)

    rdir = tmp_path / "direct" / "redis"
    rdir.mkdir()
    pidfile = tmp_path / "direct" / "redis.pid"
    subprocess.run(
        [str(dev_bin / "redis-server"), "--port", "0", "--dir", str(rdir), "--pidfile", str(pidfile)],
        env=env,
        check=True,
        timeout=30,
    )
    redis_pid = int(pidfile.read_text(encoding="utf-8").strip())
    assert _wait_comm(redis_pid, "sleep") == "sleep"
    assert redis_pid in _marked_pids(tmp_path), "the redis-server stand-in dropped the test's marker"
    assert "redis-server" in _cmdline(redis_pid)
    os.kill(redis_pid, signal.SIGTERM)
    assert _wait_marked_gone(tmp_path) == []

    proc = _run_platform_ci_local(
        tmp_path,
        bin_dir,
        stub_log=tmp_path / "cycle.log",
        env={
            "PLATFORM_CI_LOCAL_LOCK": str(tmp_path / "cycle.lock"),
            "PLATFORM_CI_LOCAL_WORK": str(tmp_path / "cycle-work"),
        },
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    # The run's own stand-ins carried the marker, so the autouse fixture can see them, and the
    # pid each stop line names is the process the stand-in spawned and recorded.
    log = (tmp_path / "cycle.log").read_text(encoding="utf-8")
    spawned_rows = re.findall(r"^spawned (postgres|redis-server) pid=(\d+) marker=(.*)$", log, re.M)
    assert sorted(name for name, _pid, _marker in spawned_rows) == ["postgres", "redis-server"], log
    for name, _pid, marker in spawned_rows:
        assert marker == str(tmp_path), f"{name} stand-in ran without the test's marker: {marker!r}"
    spawned = {name: int(pid) for name, pid, _marker in spawned_rows}
    pg_stop = re.search(r"stopping postgres \(pid (\d+)\)", proc.stderr)
    redis_stop = re.search(r"stopping redis \(pid (\d+)\)", proc.stderr)
    assert pg_stop and redis_stop, proc.stderr
    recorded_pg = int((tmp_path / "cycle-work" / "pg" / "postmaster.pid").read_text(encoding="utf-8").split()[0])
    assert int(pg_stop.group(1)) == spawned["postgres"] == recorded_pg, (proc.stderr, log)
    assert int(redis_stop.group(1)) == spawned["redis-server"], (proc.stderr, log)
    for name, pid in spawned.items():
        assert _wait_not_running(pid), f"{name} stand-in pid {pid} outlived its stop"
    assert _wait_marked_gone(tmp_path) == []


def _holding_path_function() -> str:
    """The script's own ``_pids_holding_path`` definition, verbatim."""
    assert _SCRIPT is not None
    match = re.search(r"^_pids_holding_path\(\) \{\n.*?^\}\n", _SCRIPT.read_text(encoding="utf-8"), re.M | re.S)
    assert match, "_pids_holding_path not found in scripts/platform-ci-local.sh"
    return match.group(0)


@pytest.mark.parametrize(
    "tools",
    [("fuser", "tr", "sed", "sort"), ("sort",)],
    ids=["fuser", "proc-walk-without-fuser-or-readlink"],
)
def test_pids_holding_path_lists_each_holder_once_sorted(tmp_path: Path, tools: tuple[str, ...]) -> None:
    """Story 101.1: one pid per line, sorted and unique, by fuser or by the fork-free /proc walk.

    The second case puts only ``sort`` on PATH, so the walk can fork neither ``fuser`` nor a
    ``readlink`` per descriptor (110 s at 6,549 processes before the fix).
    """
    if not Path("/proc/self/fd").is_dir():
        pytest.skip("needs /proc")
    found = {name: shutil.which(name) for name in tools}
    missing = sorted(name for name, path in found.items() if path is None)
    if missing:
        pytest.skip(f"not on PATH: {', '.join(missing)}")
    bash = shutil.which("bash")
    assert bash is not None
    tool_dir = tmp_path / "tools"
    tool_dir.mkdir()
    for name, path in found.items():
        assert path is not None
        (tool_dir / name).symlink_to(path)
    target = tmp_path / "held.lock"
    target.touch()
    env = {**os.environ, **_marker_env(tmp_path)}
    holders = [
        # one holder on two descriptors, one on one
        subprocess.Popen([bash, "-c", 'exec 8>"$1" 9>"$1"; exec sleep 999999', "_", str(target)], env=env),
        subprocess.Popen([bash, "-c", 'exec 9>"$1"; exec sleep 999999', "_", str(target)], env=env),
    ]
    try:
        for holder in holders:
            assert _wait_comm(holder.pid, "sleep") == "sleep"
        scan = subprocess.run(
            [bash, "-c", _holding_path_function() + '_pids_holding_path "$1"\n', "_", str(target)],
            env={"PATH": str(tool_dir), **_marker_env(tmp_path)},
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert scan.returncode == 0, scan.stderr
        assert scan.stdout == "".join(f"{pid}\n" for pid in sorted(h.pid for h in holders)), scan.stdout
    finally:
        for holder in holders:
            holder.kill()
            holder.wait(timeout=5)
