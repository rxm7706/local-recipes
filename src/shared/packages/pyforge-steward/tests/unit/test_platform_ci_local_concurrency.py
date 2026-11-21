"""Story 63.7: overlapping ``platform-ci-local -- --test`` runs must not cross-stop services.

Loads the real ``scripts/platform-ci-local.sh`` with stub pixi env binaries and a
minimal ``src/platform`` tree — no PostgreSQL, Redis or container engine required.

Story 101.1: every process a test here starts carries ``PLATFORM_CI_STUB_MARKER=<tmp_path>``,
and an autouse fixture (imported by the other ``test_platform_ci_local_*`` modules) fails a
test that leaves one behind. The check is scoped to that marker, never to a process name.

Story 126.3: a host with no ``/proc`` (macOS) cannot read another process's environment --
``ps e`` and ``KERN_PROCARGS2`` return none for a system binary such as ``sleep``, which is
what every stand-in becomes. There the marker is the working directory instead: every process
a test starts runs with its cwd at or under ``tmp_path``, a child inherits it as it inherits
the environment, and ``lsof -d cwd`` reads it for any process of the same user. So a process
a test starts carries both, and the guard reads whichever the host can show.
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import signal
import socket
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

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = [
    pytest.mark.live_tree,
    pytest.mark.skipif(
        not (_SCRIPT and _SCRIPT.is_file()),
        reason="scripts/platform-ci-local.sh required",
    ),
]

_MARKER_VAR = "PLATFORM_CI_STUB_MARKER"


def _marker_env(root: Path) -> dict[str, str]:
    """The environment entry every process a test starts carries (Story 101.1)."""
    return {_MARKER_VAR: str(root)}


def _pids_with_cwd_under(root: Path) -> list[int]:
    """Pids, other than this one, whose working directory is ``root`` or below it, read through ``lsof``.

    The marker a host with no ``/proc`` can read (Story 126.3). A zombie has no cwd, so a process
    that has exited never matches. No ``lsof`` means the guard cannot see anything, which is an
    error here, never an empty answer.
    """
    lsof = shutil.which("lsof")
    if lsof is None:
        raise RuntimeError("the leak guard needs /proc or lsof to read a process's marker; this host has neither")
    listing = subprocess.run(
        [lsof, "-a", "-u", str(os.getuid()), "-d", "cwd", "-Fpn"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,  # lsof exits 1 when any process on the host denies it; what it could read is on stdout
    )
    base = os.path.realpath(root)
    me = os.getpid()
    found: list[int] = []
    pid = 0
    for line in listing.stdout.splitlines():
        if line.startswith("p"):
            pid = int(line[1:])
        elif line.startswith("n") and pid and pid != me:
            cwd = line[1:]
            if cwd == base or cwd.startswith(base + os.sep):
                found.append(pid)
    return sorted(set(found))


def _marked_pids(root: Path) -> list[int]:
    """Pids, other than this one, that carry ``root``'s marker.

    Where the host has ``/proc``: an environment holding exactly ``root``'s marker entry. Where it
    has none: a working directory at or under ``root`` (Story 126.3). Scoped to one test's marker,
    never a process name or a host-wide pattern. A zombie's environ reads empty, so a process that
    has exited never matches.
    """
    proc = Path("/proc")
    if not proc.is_dir():
        return _pids_with_cwd_under(root)
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


def _ps_field(pid: int, field: str) -> str:
    """One ``ps`` column for ``pid``, empty when the process is gone: what a host with no ``/proc`` reads (Story 126.3)."""
    ps = shutil.which("ps")
    if ps is None:
        return ""
    out = subprocess.run([ps, "-o", f"{field}=", "-p", str(pid)], capture_output=True, text=True, check=False)
    return out.stdout.strip()


def _cmdline(pid: int) -> str:
    if not Path("/proc").is_dir():
        return _ps_field(pid, "command") or "?"
    try:
        raw = Path("/proc", str(pid), "cmdline").read_bytes()
    except OSError:
        return "?"
    return raw.replace(b"\0", b" ").decode(errors="replace").strip()


def _fail_on_survivors(root: Path, timeout: float = 5.0) -> None:
    """Fail when a process still carries ``root``'s marker at the deadline, after killing each one."""
    survivors = _wait_marked_gone(root, timeout)
    if not survivors:
        return
    described = [f"pid={pid} cmdline={_cmdline(pid)}" for pid in survivors]
    for pid in survivors:
        with contextlib.suppress(OSError):
            os.kill(pid, signal.SIGKILL)
    pytest.fail("processes started by the test outlived it:\n" + "\n".join(described))


@pytest.fixture(autouse=True)
def _no_stub_process_outlives_the_test(tmp_path: Path) -> Iterator[None]:
    """Story 101.1: a test that leaves a process carrying its marker fails, after those are killed."""
    yield
    _fail_on_survivors(tmp_path)


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
    # Story 129.1: each stand-in sleeps a bounded lifetime (PLATFORM_CI_STUB_LIFETIME_S, 600 s by
    # default), so one a killed test process never reaps exits by itself instead of living for days.
    service_stub = textwrap.dedent(
        """\
        #!/usr/bin/env bash
        log="${PLATFORM_CI_STUB_LOG:-/dev/null}"
        lock="${PLATFORM_CI_LOCAL_LOCK:-}"
        name="$(basename "$0")"
        # Story 125.1: setsid(1) where the host has it; where it has none, the same call from python.
        # Either way the pid the caller reads from $! is the session leader the stand-in becomes.
        new_session() {
          if command -v setsid >/dev/null 2>&1; then exec setsid "$@"; fi
          exec python3 -c 'import os, sys; os.setsid(); os.execv(sys.argv[1], sys.argv[1:])' "$@"
        }
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
          # Story 125.1: a host with no /proc answers the same question through lsof.
          if [ ! -d /proc/self/fd ] && lsof -a -p $$ -t -- "$lock" >/dev/null 2>&1; then held=yes; fi
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
        exec -a "$0 $*" sleep "${PLATFORM_CI_STUB_LIFETIME_S:-600}"
        STIN
                chmod +x "$pgdata/postgres"
                new_session "$pgdata/postgres" -D "$pgdata" >> "$log" 2>&1 &
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
        exec -a "$0 $*" sleep "${PLATFORM_CI_STUB_LIFETIME_S:-600}"
        STIN
              chmod +x "$rdir/redis-server"
              new_session "$rdir/redis-server" --port "${rport:-0}" >> "$log" 2>&1 &
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
          # Story 125.1: a host with no /proc answers the same question through lsof.
          if [ ! -d /proc/self/fd ] && lsof -a -p $$ -t -- "$lock" >/dev/null 2>&1; then held=yes; fi
        fi
        echo "pixi $* pid=$$ lock_fd=${held:-no}" >> "$log"
        if [[ " $* " == *" install "* ]]; then
          # Story 125.1: flock(1) where the host has it; where it has none, the same flock(2) probe from python.
          try_lock() {
            if command -v flock >/dev/null 2>&1; then
              flock -n "$1" true 2>/dev/null
              return
            fi
            python3 -c 'import fcntl, sys; fcntl.flock(open(sys.argv[1]), fcntl.LOCK_EX | fcntl.LOCK_NB)' "$1" 2>/dev/null
          }
          if try_lock "$lock"; then
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
    """Poll the process's command name until it reads ``comm``; return the last value read.

    ``/proc/<pid>/comm`` where the host has one; ``ps -o ucomm=`` where it has none (Story 126.3). ``ucomm`` is the
    name of the binary the process runs; BSD ``comm`` is its ``argv[0]``, which the stand-ins rewrite with ``exec -a``.
    """
    deadline = time.monotonic() + timeout
    seen = ""
    has_proc = Path("/proc").is_dir()
    while time.monotonic() < deadline:
        if has_proc:
            try:
                seen = Path("/proc", str(pid), "comm").read_text(encoding="utf-8").strip()
            except OSError:
                seen = ""
        else:
            seen = _ps_field(pid, "ucomm")
        if seen == comm:
            break
        time.sleep(0.05)
    return seen


def _running(pid: int) -> bool:
    """True while ``pid`` exists and is not a zombie."""
    if not Path("/proc").is_dir():
        state = _ps_field(pid, "stat")  # Story 126.3: empty once the process is gone
        return bool(state) and not state.startswith("Z")
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


def test_a_stand_in_nobody_stops_exits_after_its_lifetime(tmp_path: Path) -> None:
    """Story 129.1: a stand-in a killed test never reaped exits by itself once its lifetime is up."""
    _prepare_stub_root(tmp_path)
    dev_bin = tmp_path / ".pixi" / "envs" / "platform-dev" / "bin"
    env = {
        **os.environ,
        **_marker_env(tmp_path),
        "PLATFORM_CI_STUB_LOG": str(tmp_path / "stub.log"),
        "PLATFORM_CI_STUB_LIFETIME_S": "1",
    }
    pgdata = tmp_path / "left" / "pg"
    pgdata.mkdir(parents=True)
    subprocess.run([str(dev_bin / "pg_ctl"), "-D", str(pgdata), "start"], env=env, cwd=tmp_path, check=True, timeout=30)
    pg_pid = int((pgdata / "postmaster.pid").read_text(encoding="utf-8").split()[0])
    rdir = tmp_path / "left" / "redis"
    rdir.mkdir()
    pidfile = tmp_path / "left" / "redis.pid"
    subprocess.run(
        [str(dev_bin / "redis-server"), "--port", "0", "--dir", str(rdir), "--pidfile", str(pidfile)],
        env=env,
        cwd=tmp_path,
        check=True,
        timeout=30,
    )
    redis_pid = int(pidfile.read_text(encoding="utf-8").strip())
    # Neither is stopped: each must leave on its own.
    assert _wait_not_running(pg_pid, timeout=15), "the postgres stand-in outlived its lifetime"
    assert _wait_not_running(redis_pid, timeout=15), "the redis-server stand-in outlived its lifetime"
    assert _wait_marked_gone(tmp_path) == []


def test_stub_start_stop_cycle_leaves_no_process(tmp_path: Path) -> None:
    """Story 101.1: each service stand-in records the process the stop path kills.

    Before the fix the recorded pid was a bash wrapper and its ``sleep 999999`` child
    outlived every stop, two per run; 6,222 had gathered on the host by 2026-10-14.

    Story 126.3: the stand-ins are started in ``tmp_path``, the marker a host with no ``/proc``
    reads, so this runs wherever the guard can see a process.
    """
    bin_dir = _prepare_stub_root(tmp_path)
    dev_bin = tmp_path / ".pixi" / "envs" / "platform-dev" / "bin"
    env = {**os.environ, **_marker_env(tmp_path), "PLATFORM_CI_STUB_LOG": str(tmp_path / "stub.log")}

    pgdata = tmp_path / "direct" / "pg"
    pgdata.mkdir(parents=True)
    subprocess.run([str(dev_bin / "pg_ctl"), "-D", str(pgdata), "start"], env=env, cwd=tmp_path, check=True, timeout=30)
    pg_pid = int((pgdata / "postmaster.pid").read_text(encoding="utf-8").split()[0])
    assert _wait_comm(pg_pid, "sleep") == "sleep"
    assert pg_pid in _marked_pids(tmp_path), "the postgres stand-in dropped the test's marker"
    pg_cmd = _cmdline(pg_pid)
    assert "postgres" in pg_cmd and f"-D {pgdata}" in pg_cmd, pg_cmd
    subprocess.run(
        [str(dev_bin / "pg_ctl"), "-D", str(pgdata), "stop", "-m", "fast"],
        env=env,
        cwd=tmp_path,
        check=True,
        timeout=30,
    )

    rdir = tmp_path / "direct" / "redis"
    rdir.mkdir()
    pidfile = tmp_path / "direct" / "redis.pid"
    subprocess.run(
        [str(dev_bin / "redis-server"), "--port", "0", "--dir", str(rdir), "--pidfile", str(pidfile)],
        env=env,
        cwd=tmp_path,
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
    if "fuser" not in tools and not Path("/proc/self/fd").is_dir():
        pytest.skip("needs /proc: the walk without fuser reads /proc/<pid>/fd")
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
        subprocess.Popen(
            [bash, "-c", 'exec 8>"$1" 9>"$1"; exec sleep 999999', "_", str(target)], env=env, cwd=tmp_path
        ),
        subprocess.Popen([bash, "-c", 'exec 9>"$1"; exec sleep 999999', "_", str(target)], env=env, cwd=tmp_path),
    ]
    try:
        for holder in holders:
            assert _wait_comm(holder.pid, "sleep") == "sleep"
        scan = subprocess.run(
            [bash, "-c", _holding_path_function() + '_pids_holding_path "$1"\n', "_", str(target)],
            env={"PATH": str(tool_dir), **_marker_env(tmp_path)},
            cwd=tmp_path,
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


def _start_left_behind(root: Path) -> subprocess.Popen[bytes]:
    """A stand-in as the stubs leave one: ``sleep`` leading its own session, started the way every test starts a process."""
    return subprocess.Popen(
        ["sleep", "999999"],
        cwd=root,
        env={**os.environ, **_marker_env(root)},
        start_new_session=True,
    )


def _wait_marked(root: Path, pid: int, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while pid not in _marked_pids(root):
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.05)
    return True


def test_guard_catches_a_stand_in_left_behind(tmp_path: Path) -> None:
    """Story 126.3: the leak guard sees a process a test leaves, fails the test and kills it, on this host.

    Where the guard read only ``/proc/<pid>/environ`` it returned nothing on a host with no ``/proc``,
    so "no process outlives the test" passed whatever a test left. This leaves a stand-in on purpose.
    """
    left = _start_left_behind(tmp_path)
    try:
        assert _wait_marked(tmp_path, left.pid), f"the guard cannot see pid {left.pid}: {_marked_pids(tmp_path)}"
        with pytest.raises(pytest.fail.Exception, match=rf"outlived it:\n(.*\n)*pid={left.pid} cmdline=.*sleep"):
            _fail_on_survivors(tmp_path, timeout=0.3)
        assert left.wait(timeout=5) == -signal.SIGKILL, "the guard did not kill the process it reported"
    finally:
        if left.poll() is None:
            left.kill()
            left.wait(timeout=5)
    assert _wait_marked_gone(tmp_path) == []


def test_guard_ignores_another_tests_process(tmp_path: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
    """Story 126.3: the marker is one test's own; a process carrying another root's marker is not this test's."""
    other_root = tmp_path_factory.mktemp("another-test")
    other = _start_left_behind(other_root)
    try:
        assert _wait_marked(other_root, other.pid)
        assert other.pid not in _marked_pids(tmp_path)
        _fail_on_survivors(tmp_path, timeout=0.3)  # nothing of this test's is left: no failure
        assert other.poll() is None, "the guard killed a process that was not this test's"
    finally:
        other.kill()
        other.wait(timeout=5)
    assert _wait_marked_gone(other_root) == []


# --------------------------------------------------------------------------- Story 126.3
# The container stage's port check and the image context's tar work on a host with no ``ss`` or GNU tar.
# ``stage_container`` asked ``ss -ltn`` whether port 8000 was taken, and ``export_context`` passed GNU tar's
# ``--ignore-failed-read``. On macOS there is no ``ss`` (the check read "free" whatever held the port) and the tar
# is bsdtar (which rejects the option, so the context came out empty). Both now go through a helper that keeps
# the Linux command and falls back where the host lacks it. Each helper is loaded verbatim from the script and
# run under a PATH that holds only the tools one branch may use, so both branches are proven on any host.


def _script_text() -> str:
    assert _SCRIPT is not None
    return _SCRIPT.read_text(encoding="utf-8")


def _function(name: str) -> str:
    """One top-level function of the script, verbatim."""
    match = re.search(rf"^{re.escape(name)}\(\) \{{\n.*?^\}}\n", _script_text(), re.M | re.S)
    assert match, f"{name} not found in scripts/platform-ci-local.sh"
    return match.group(0)


def _tool_dir(tmp_path: Path, name: str, tools: tuple[str, ...]) -> Path:
    """A directory holding symlinks to exactly ``tools``; skips, naming the tool, when the host lacks one."""
    missing = sorted(tool for tool in tools if shutil.which(tool) is None)
    if missing:
        pytest.skip(f"not on PATH: {', '.join(missing)}")
    directory = tmp_path / name
    directory.mkdir()
    for tool in tools:
        found = shutil.which(tool)
        assert found is not None
        (directory / tool).symlink_to(found)
    return directory


def _bash() -> str:
    bash = shutil.which("bash")
    assert bash is not None
    return bash


def _run(
    tmp_path: Path, body: str, *args: str, path: Path, stdin: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [_bash(), "-c", body, "_", *args],
        env={"PATH": str(path), **_marker_env(tmp_path)},
        cwd=tmp_path,
        input=stdin,
        capture_output=True,
        timeout=60,
        check=False,
    )


def _port_is_bound(tmp_path: Path, port: int, *, path: Path) -> int:
    body = _function("_listener_on_port") + _function("_port_is_bound") + '_port_is_bound "$1"\n'
    return _run(tmp_path, body, str(port), path=path).returncode


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_the_two_stages_call_the_helpers() -> None:
    """Neither stage keeps a host-specific command of its own."""
    text = _script_text()
    stage = text[text.index("  stage_container() {") : text.index("  stage_promotion() {")]
    assert 'if _port_is_bound "$APP_PORT"; then' in stage
    assert "ss -ltn" not in stage
    context = text[text.index("  export_context() {") : text.index("  stage_images() {")]
    assert "| _tar_listed_paths | tar -xf - -C" in context
    assert "--ignore-failed-read" not in context


def test_port_check_without_ss_sees_a_listener_through_lsof(tmp_path: Path) -> None:
    """The host has no ``ss``: a bound port reads bound and a free one free, through ``lsof``."""
    tools = _tool_dir(tmp_path, "no-ss", ("lsof", "head"))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = int(listener.getsockname()[1])
        assert _port_is_bound(tmp_path, port, path=tools) == 0
    assert _port_is_bound(tmp_path, _free_port(), path=tools) != 0


def test_port_check_with_ss_reads_ss_and_needs_no_pid(tmp_path: Path) -> None:
    """The host has ``ss``: the check is the ``ss -ltn`` one, which sees a listener that shows no pid."""
    tools = _tool_dir(tmp_path, "with-ss", ("grep",))
    _write_executable(
        tools / "ss",
        textwrap.dedent(
            """\
            #!/bin/bash
            [ "$1" = "-ltn" ] || { echo "unexpected ss arguments: $*" >&2; exit 64; }
            echo "State  Recv-Q Send-Q Local Address:Port Peer Address:Port"
            echo "LISTEN 0      4096         0.0.0.0:8000      0.0.0.0:*"
            """
        ),
    )
    _write_executable(tools / "lsof", "#!/bin/bash\necho 'lsof must not run where ss exists' >&2\nexit 64\n")
    assert _port_is_bound(tmp_path, 8000, path=tools) == 0
    assert _port_is_bound(tmp_path, 800, path=tools) != 0
    assert _port_is_bound(tmp_path, 18000, path=tools) != 0


def _tree_with_a_listed_path_gone(tmp_path: Path) -> tuple[Path, bytes]:
    source = tmp_path / "source"
    (source / "src" / "platform").mkdir(parents=True)
    (source / "src" / "platform" / "Containerfile").write_text("FROM scratch\n", encoding="utf-8")
    (source / "name with space.txt").write_text("kept\n", encoding="utf-8")
    listed = ("src/platform/Containerfile", "deleted-but-still-listed.txt", "name with space.txt")
    return source, b"".join(name.encode() + b"\0" for name in listed)


def _archive_and_extract(tmp_path: Path, *, path: Path) -> tuple[subprocess.CompletedProcess[bytes], Path]:
    source, listing = _tree_with_a_listed_path_gone(tmp_path)
    out = tmp_path / "context"
    out.mkdir()
    body = _function("_tar_listed_paths") + 'cd "$1" && _tar_listed_paths | tar -xf - -C "$2"\n'
    return _run(tmp_path, body, str(source), str(out), path=path, stdin=listing), out


def _context_files(out: Path) -> list[str]:
    return sorted(str(found.relative_to(out)) for found in out.rglob("*") if found.is_file())


_EXPECTED_CONTEXT = ["name with space.txt", "src/platform/Containerfile"]


def test_context_tar_on_this_host_passes_over_a_missing_path(tmp_path: Path) -> None:
    """Whatever tar this host has, a path that is listed but gone does not empty the context."""
    tools = _tool_dir(tmp_path, "host-tar", ("tar",))
    proc, out = _archive_and_extract(tmp_path, path=tools)
    assert proc.returncode == 0, proc.stderr
    assert _context_files(out) == _EXPECTED_CONTEXT


def test_context_tar_without_gnu_tar_never_passes_the_gnu_option(tmp_path: Path) -> None:
    """A tar that is not GNU tar refuses ``--ignore-failed-read`` and a missing path; the helper gives it neither."""
    real_tar = shutil.which("tar")
    assert real_tar is not None
    tools = tmp_path / "bsd-tar"
    _write_executable(
        tools / "tar",
        textwrap.dedent(
            f"""\
            #!/bin/bash
            if [ "$1" = "--version" ]; then echo "bsdtar 3.5.3 - libarchive 3.7.4"; exit 0; fi
            for arg in "$@"; do
              [ "$arg" = "--ignore-failed-read" ] && {{ echo "tar: Option --ignore-failed-read is not supported" >&2; exit 1; }}
            done
            echo "tar $*" >> "{tmp_path / "tar.log"}"
            exec "{real_tar}" "$@"
            """
        ),
    )
    proc, out = _archive_and_extract(tmp_path, path=tools)
    assert proc.returncode == 0, proc.stderr
    assert _context_files(out) == _EXPECTED_CONTEXT
    assert "tar --null -T - -cf -\n" in (tmp_path / "tar.log").read_text(encoding="utf-8")


def test_context_tar_with_gnu_tar_keeps_the_gnu_command(tmp_path: Path) -> None:
    """Where tar is GNU tar the archive command is the one the script has always run."""
    tools = tmp_path / "gnu-tar"
    _write_executable(
        tools / "tar",
        textwrap.dedent(
            f"""\
            #!/bin/bash
            if [ "$1" = "--version" ]; then echo "tar (GNU tar) 1.35"; exit 0; fi
            echo "tar $*" >> "{tmp_path / "tar.log"}"
            """
        ),
    )
    listing = b"a\0b\0"
    proc = _run(tmp_path, _function("_tar_listed_paths") + "_tar_listed_paths\n", path=tools, stdin=listing)
    assert proc.returncode == 0, proc.stderr
    assert (tmp_path / "tar.log").read_text(encoding="utf-8") == "tar --null -T - -cf - --ignore-failed-read\n"
