#!/usr/bin/env python3
"""Provision the per-user PostgreSQL + pgvector cluster pyforge-scribe's tests need.

WHY THIS EXISTS. `pyforge-scribe`'s durable GraphStore (Story 28.1) talks to a
real PostgreSQL with pgvector, and its `tests/unit/conftest.py` fails LOUDLY
rather than skipping when it cannot reach one -- deliberately, so a missing
server can never read as a green suite. But the `pyforge-scribe` environment
shipped only the CLIENT (`psycopg`); nothing in the repo provisioned a server.
CI supplies one as a `pgvector/pgvector:pg16` service container, so the gap was
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
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
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


def up() -> int:
    _need("initdb"), _need("pg_ctl"), _need("psql")
    CLUSTER.parent.mkdir(parents=True, exist_ok=True)

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
        LOGFILE.parent.mkdir(parents=True, exist_ok=True)
        r = _run([
            "pg_ctl", "-D", str(CLUSTER), "-l", str(LOGFILE), "-w", "start",
            "-o", f"-p {PORT} -k {CLUSTER.parent} -c listen_addresses=127.0.0.1",
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
        print(f"[scribe-pg] started on 127.0.0.1:{PORT}")

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
    print(f"[scribe-pg] {'listening' if live else 'not listening'} on 127.0.0.1:{PORT}"
          f"  (cluster {'present' if (CLUSTER / 'PG_VERSION').is_file() else 'absent'})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("verb", choices=("up", "down", "status"))
    return {"up": up, "down": down, "status": status}[ap.parse_args().verb]()


if __name__ == "__main__":
    sys.exit(main())
