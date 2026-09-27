#!/usr/bin/env python3
"""Provision the per-user PostgreSQL + pgvector cluster pyforge-scribe's tests need.

WHY THIS EXISTS. `pyforge-scribe`'s durable GraphStore (Story 28.1) talks to a
real PostgreSQL with pgvector, and its `tests/unit/conftest.py` fails LOUDLY
rather than skipping when it cannot reach one -- deliberately, so a missing
server can never read as a green suite. But the `pyforge-scribe` environment
shipped only the CLIENT (`psycopg`); nothing in the repo provisioned a server.
CI supplies one as a `pgvector/pgvector:pg17` service container, so the gap was
invisible there and only bit locally: 18 tests fail with

    Failed: durable GraphStore requires PostgreSQL with pgvector at
    postgres://postgres:scribe@127.0.0.1:5433/scribe_graph: connection refused

and the only local recourse was hand-rolling a container -- which contradicts
the estate's own local-first posture (`platform-dev`'s pap:AD-16 note: "all
pixi-provisioned, zero containers or managed services").

WHY A SEPARATE ENVIRONMENT. `pgvector` has NO win-64 conda-forge build, and the
`pyforge-scribe` feature inherits the workspace platform list (which includes
win-64). Adding the server there would break that solve outright. So the server
binaries live in the `scribe-pg` feature, restricted to the platforms that have
them, and compose into `pyforge-scribe-pg`. The lean `pyforge-scribe` env that
CI installs is unchanged -- exactly how `platform-dev` layers onto
`python-agent-platform` rather than widening it.

The cluster is per-user state under gitignored `var/`, never a container, and
`up` is idempotent: re-running against a live cluster re-asserts the database,
role and extension instead of failing.

WHY THE SOCKET LIVES ELSEWHERE (Story 22.1). The data dir stays under the
checkout, but the server's Unix socket goes in a short per-user directory:
`SCRIBE_PG_SOCKET_DIR`, else `$XDG_RUNTIME_DIR/scribe-pg`, else
`/tmp/scribe-pg-<uid>`. A worktree's `var/scribe-pg/.s.PGSQL.5433` runs past the
kernel's socket-path limit, and PostgreSQL then refuses to start ("could not
create any Unix-domain sockets").
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import shlex
import shutil
import stat
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLUSTER = ROOT / "var" / "scribe-pg" / "data"
LOGFILE = ROOT / "var" / "scribe-pg" / "server.log"

#: Must match `tests/unit/conftest.py::_DEFAULT_PG_DSN` exactly --
#: `postgres://postgres:scribe@127.0.0.1:5433/scribe_graph`. Kept as separate
#: fields rather than parsed from that constant so this script has no import
#: dependency on the test tree.
PORT = "5433"
SUPERUSER = "postgres"
PASSWORD = "scribe"
DATABASE = "scribe_graph"

#: A Unix socket path (`sun_path`) holds 108 bytes on Linux and 104 on macOS,
#: the terminating NUL included; the server's socket is `<dir>/.s.PGSQL.<port>`.
SOCKET_PATH_MAX = 103 if sys.platform == "darwin" else 107


def _run(args: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, **kw)


def _need(binary: str) -> str:
    found = shutil.which(binary)
    if not found:
        sys.exit(
            f"[scribe-pg] cannot run: `{binary}` is not on PATH. Use the composed "
            f"environment: pixi run -e pyforge-scribe-pg scribe-pg-up"
        )
    return found


def _is_up() -> bool:
    if not shutil.which("pg_isready"):
        return False
    return _run(["pg_isready", "-h", "127.0.0.1", "-p", PORT, "-q"]).returncode == 0


def _socket_dir() -> pathlib.Path:
    """`SCRIBE_PG_SOCKET_DIR`, else `$XDG_RUNTIME_DIR/scribe-pg`, else `/tmp/scribe-pg-<uid>`."""
    override = os.environ.get("SCRIBE_PG_SOCKET_DIR")
    if override:
        return pathlib.Path(override)
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        return pathlib.Path(runtime) / "scribe-pg"
    return pathlib.Path("/tmp") / f"scribe-pg-{os.getuid()}"


def _prepare_socket_dir() -> pathlib.Path | None:
    """Create the socket dir 0700 and check the socket path fits; None, with the reason, if not."""
    sock_dir = _socket_dir()
    socket_file = sock_dir / f".s.PGSQL.{PORT}"
    length = len(os.fsencode(socket_file))
    if length > SOCKET_PATH_MAX:
        sys.stderr.write(
            f"[scribe-pg] socket path {socket_file} is {length} bytes; the limit is "
            f"{SOCKET_PATH_MAX}. Set SCRIBE_PG_SOCKET_DIR to a shorter directory.\n"
        )
        return None
    try:
        sock_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError as exc:
        sys.stderr.write(f"[scribe-pg] cannot create socket directory {sock_dir}: {exc}\n")
        return None
    st = sock_dir.lstat()
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid():
        sys.stderr.write(
            f"[scribe-pg] socket directory {sock_dir} is not a directory you own "
            f"(a symlink, a file, or another user's); set SCRIBE_PG_SOCKET_DIR\n"
        )
        return None
    if st.st_mode & 0o077:
        sock_dir.chmod(0o700)
    return sock_dir


def _socket_dir_in_use() -> str | None:
    """The socket dir this checkout's running server reports (`postmaster.pid` line 5)."""
    pid_file = CLUSTER / "postmaster.pid"
    if not pid_file.is_file():
        return None
    lines = pid_file.read_text(encoding="utf-8", errors="replace").splitlines()
    if len(lines) <= 4:
        return None
    return lines[4].strip() or None


def _server_major() -> str | None:
    """Major version of the env's server binaries (`pg_ctl (PostgreSQL) 17.11` -> `17`)."""
    m = re.search(r"\(PostgreSQL\)\s+(\d+)", _run(["pg_ctl", "--version"]).stdout)
    return m.group(1) if m else None


def _move_aside_other_major() -> int:
    """A data dir from another major version cannot start under these binaries.

    Story 67.1 moved `scribe-pg` from PostgreSQL 18 to 17, so every existing
    PG18 cluster would otherwise fail `pg_ctl start` ("database files are
    incompatible with server"). The cluster holds disposable test data, so it
    is moved aside (never deleted) and `up` re-initialises.
    """
    version_file = CLUSTER / "PG_VERSION"
    if not version_file.is_file():
        return 0
    data_major, server_major = version_file.read_text().strip(), _server_major()
    if server_major is None or data_major == server_major:
        return 0
    if _is_up():
        sys.stderr.write(
            f"[scribe-pg] {CLUSTER.relative_to(ROOT)} is PostgreSQL {data_major} and a server is "
            f"still listening on 127.0.0.1:{PORT}; stop it with the environment that started it "
            f"(PostgreSQL {data_major}) before `scribe-pg-up` on {server_major}\n"
        )
        return 1
    aside = CLUSTER.with_name(f"data.pg{data_major}")
    n = 1
    while aside.exists():
        aside = CLUSTER.with_name(f"data.pg{data_major}.{n}")
        n += 1
    CLUSTER.rename(aside)
    print(
        f"[scribe-pg] data dir was PostgreSQL {data_major}, server is {server_major}: "
        f"moved it to {aside.relative_to(ROOT)} and re-initialising (test data only)"
    )
    return 0


def up() -> int:
    _need("initdb"), _need("pg_ctl"), _need("psql")
    CLUSTER.parent.mkdir(parents=True, exist_ok=True)
    if _move_aside_other_major():
        return 1

    if not (CLUSTER / "PG_VERSION").is_file():
        pwfile = CLUSTER.parent / ".initpw"
        pwfile.write_text(PASSWORD, encoding="utf-8")
        try:
            r = _run([
                "initdb", "-D", str(CLUSTER), "-U", SUPERUSER,
                "--auth=scram-sha-256", f"--pwfile={pwfile}", "--encoding=UTF8",
            ])
            if r.returncode:
                sys.stderr.write(r.stdout + r.stderr)
                return 1
        finally:
            pwfile.unlink(missing_ok=True)   # never leave the password on disk
        print(f"[scribe-pg] initialised cluster at {CLUSTER.relative_to(ROOT)}")

    if _is_up():
        print(f"[scribe-pg] already listening on 127.0.0.1:{PORT}")
    else:
        sock_dir = _prepare_socket_dir()
        if sock_dir is None:
            return 1
        LOGFILE.parent.mkdir(parents=True, exist_ok=True)
        r = _run([
            "pg_ctl", "-D", str(CLUSTER), "-l", str(LOGFILE), "-w", "start",
            "-o", f"-p {PORT} -k {shlex.quote(str(sock_dir))} -c listen_addresses=127.0.0.1",
        ])
        if r.returncode:
            sys.stderr.write(r.stdout + r.stderr)
            sys.stderr.write(f"\n[scribe-pg] server log: {LOGFILE}\n")
            return 1
        for _ in range(30):
            if _is_up():
                break
            time.sleep(1)
        else:
            return sys.exit(f"[scribe-pg] server did not become ready; see {LOGFILE}")
        print(f"[scribe-pg] started on 127.0.0.1:{PORT} (socket dir {sock_dir})")

    env = {**os.environ, "PGPASSWORD": PASSWORD}
    base = ["psql", "-h", "127.0.0.1", "-p", PORT, "-U", SUPERUSER, "-v", "ON_ERROR_STOP=1"]
    exists = _run([*base, "-tAc", f"SELECT 1 FROM pg_database WHERE datname='{DATABASE}'",
                   "-d", "postgres"], env=env).stdout.strip()
    if exists != "1":
        r = _run([*base, "-d", "postgres", "-c", f'CREATE DATABASE "{DATABASE}"'], env=env)
        if r.returncode:
            sys.stderr.write(r.stdout + r.stderr)
            return 1
        print(f"[scribe-pg] created database {DATABASE}")

    r = _run([*base, "-d", DATABASE, "-c", "CREATE EXTENSION IF NOT EXISTS vector"], env=env)
    if r.returncode:
        sys.stderr.write(r.stdout + r.stderr)
        sys.stderr.write("[scribe-pg] `CREATE EXTENSION vector` failed -- is pgvector installed?\n")
        return 1

    print(f"[scribe-pg] ready: postgres://{SUPERUSER}:***@127.0.0.1:{PORT}/{DATABASE} (pgvector enabled)")
    print("[scribe-pg] run the suite with: pixi run -e pyforge-scribe pyforge-scribe-test")
    return 0


def down() -> int:
    if not (CLUSTER / "PG_VERSION").is_file():
        print("[scribe-pg] no cluster to stop")
        return 0
    _need("pg_ctl")
    r = _run(["pg_ctl", "-D", str(CLUSTER), "-m", "fast", "-w", "stop"])
    if r.returncode and _is_up():
        sys.stderr.write(r.stdout + r.stderr)
        return 1
    print("[scribe-pg] stopped")
    return 0


def status() -> int:
    live = _is_up()
    in_use = _socket_dir_in_use()
    socket = f"socket dir {in_use}" if in_use else f"socket dir {_socket_dir()} (configured)"
    print(f"[scribe-pg] {'listening' if live else 'not listening'} on 127.0.0.1:{PORT}"
          f"  (cluster {'present' if (CLUSTER / 'PG_VERSION').is_file() else 'absent'}; {socket})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("verb", choices=("up", "down", "status"))
    return {"up": up, "down": down, "status": status}[ap.parse_args().verb]()


if __name__ == "__main__":
    sys.exit(main())
