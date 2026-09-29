"""One boot script raises both plane faces (Story 20.1, CAP-5).

The 2026-08-26 ``query-plane-face`` operator ruling answered "both, one boot
script": this module is the ONE pixi-sourced boot path for the CAP-19 query
plane's two faces.

1. The **in-process library face** is always raised (AD-16 local-first):
   ``boot_query_plane`` opens ``atlas.duckdb`` through the existing
   :func:`pyforge.atlas.duckdb_writer.connect_writer` seam — never a second
   writer, never a second ``.duckdb`` file. A second boot invocation is
   refused with the existing :class:`~pyforge.atlas.duckdb_writer.SecondWriterRefused`.
2. The **Mosaic ``duckdb-server`` HTTP/Arrow face** is launched from this SAME
   module — the one and only ``duckdb-server`` launch site in the atlas
   surface (gated by ``tests/singularity/test_one_duckdb_server_launch_site.py``)
   — but only when a platform-stack-up signal is present (explicit
   ``stack_up=`` argument first, else env ``PYFORGE_PLATFORM_STACK_UP``).
   With the stack down the boot degrades to library-face-only with a
   structured notice, never a crash.

Subprocess contract — bound from the INSTALLED package, never training data
(verified 2026-08-27 against duckdb-server 0.31.0 in the pyforge-atlas env):

* argv is ``duckdb-server <db_path>`` — ``pkg/__main__.py::serve`` reads
  exactly one optional positional (``sys.argv[1]``, default ``":memory:"``).
  There is NO port flag and NO host flag; ``pkg/server.py::server`` hard-codes
  ``app.listen(3000, …)`` (socketify), so :data:`DEFAULT_PORT` is 3000 and a
  real launch refuses any other port rather than reporting an endpoint that
  points nowhere.
* the server opens the path **eagerly, read-write** (``duckdb.connect(db_path)``
  at startup) and requires no extension ``INSTALL`` at boot, so the AD-13
  Block-If (network ``INSTALL`` at boot) does not trigger.
* duckdb 1.5.5 refuses ANY second cross-process open — read-only or
  read-write — while a read-write connection is held (verified live), and the
  ``file:…?access_mode=read_only`` URI form is not accepted by
  ``duckdb.connect``. The two faces therefore cannot both hold live DuckDB
  connections on the same file; see the "yield" step in
  :func:`boot_query_plane` for the recorded handling (also in the story
  spec's Design Notes).

Provisioning failures mirror :mod:`pyforge.atlas.live_attach`'s
LOAD-only-never-INSTALL discipline: the typed
:class:`DuckDBServerNotProvisionedError` names the exact provisioning step and
the boot never shells out to any installer.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import signal
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pyforge.core.errors import PyforgeError

from pyforge.atlas.duckdb_writer import (
    ATLAS_DUCKDB_NAME,
    LockedDuckDB,
    connect_writer,
)

STACK_UP_ENV = "PYFORGE_PLATFORM_STACK_UP"
_TRUTHY = frozenset({"1", "true", "yes", "on"})

SERVER_EXECUTABLE = "duckdb-server"
DEFAULT_HOST = "127.0.0.1"
# Bound from the installed server source: pkg/server.py::server hard-codes
# app.listen(3000, …); no CLI flag can change it (duckdb-server 0.27–0.31).
DEFAULT_PORT = 3000
# Repo-root-relative default for the CLI (the pixi task runs at repo root);
# lands inside the atlas member's gitignored data/ tree.
DEFAULT_PLANE_PATH = Path("src/shared/packages/pyforge-atlas/data/plane") / ATLAS_DUCKDB_NAME

Launcher = Callable[[Sequence[str]], Any]


class DuckDBServerNotProvisionedError(PyforgeError, RuntimeError):
    """``duckdb-server`` is not provisioned — the boot path must not INSTALL."""


def stack_is_up(override: bool | None = None) -> bool:
    """Resolve the platform-stack-up signal (Story 20.1 Design Notes).

    An explicit ``override`` wins; else env ``PYFORGE_PLATFORM_STACK_UP``
    (truthy: 1/true/yes/on, case-insensitive). Absence of the signal IS
    "stack down". A live health probe can be wired into the same parameter
    later without changing this contract.
    """
    if override is not None:
        return bool(override)
    return os.environ.get(STACK_UP_ENV, "").strip().lower() in _TRUTHY


@dataclass(frozen=True)
class HttpFace:
    """The raised HTTP/Arrow face: its endpoint plus the launched process handle."""

    endpoint: str
    process: Any


@dataclass
class PlaneBoot:
    """Result of :func:`boot_query_plane` — the caller owns closing the handles."""

    library: LockedDuckDB
    http: HttpFace | None
    notices: list[dict[str, Any]] = field(default_factory=list)


def _server_argv(executable: str, db_path: Path) -> list[str]:
    # The whole launch contract: one positional, the DuckDB path
    # (pkg/__main__.py::serve, verified against the installed 0.31.0).
    return [executable, str(db_path)]


def _launch_duckdb_server(argv: Sequence[str]) -> subprocess.Popen[bytes]:
    """The ONE ``duckdb-server`` launch site in the whole atlas surface.

    Story 14.4, CAP-6: stays raw ``subprocess.Popen``, exempted file-level
    in ``test_process_sole_ownership.py`` -- ``_shutdown``'s graceful
    terminate -> wait(timeout) -> kill -> wait sequence (below) needs the
    LIVE ``Popen`` handle's own lifecycle methods. ``pyforge.core.process``
    offers no equivalent: ``run`` blocks until completion,
    ``spawn_detached`` returns a bare pid with no terminate/wait/kill at
    all -- neither fits a supervised long-running server this module must
    later shut down cleanly.
    """
    return subprocess.Popen(list(argv))  # noqa: S603 — fixed argv, no shell


def boot_query_plane(
    path: Path | str,
    *,
    stack_up: bool | None = None,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    launcher: Launcher | None = None,
) -> PlaneBoot:
    """Raise the plane's face(s): library always, HTTP only when the stack is up.

    ``launcher`` is a test seam: when injected it receives the argv and returns
    the process handle, and no executable preflight runs (the launcher IS the
    provisioning). When ``None``, the real ``duckdb-server`` is resolved from
    PATH and launched from the one :func:`_launch_duckdb_server` site.
    """
    library = connect_writer(path)
    notices: list[dict[str, Any]] = []

    if not stack_is_up(stack_up):
        notices.append(
            {
                "event": "http-face-not-raised",
                "reason": "stack-down",
                "library_face": "up",
                "path": str(path),
                "hint": (
                    f"set {STACK_UP_ENV}=1 (or pass stack_up=True) to raise "
                    "the HTTP/Arrow face from this same boot script"
                ),
            }
        )
        return PlaneBoot(library=library, http=None, notices=notices)

    try:
        if launcher is None:
            if host != DEFAULT_HOST:
                raise ValueError(
                    "the installed duckdb-server (0.27–0.31) has no host "
                    "flag — the boot merely REPORTS the endpoint, so "
                    f"host={host!r} would advertise an endpoint that may "
                    "point nowhere (the same failure the port guard "
                    f"prevents); pass host={DEFAULT_HOST!r} or inject a "
                    "launcher that owns the endpoint contract"
                )
            if port != DEFAULT_PORT:
                raise ValueError(
                    "the installed duckdb-server (0.27–0.31) hard-codes its "
                    f"listen port to {DEFAULT_PORT} (pkg/server.py::server "
                    "app.listen) — there is no port flag to honor "
                    f"port={port}; pass port={DEFAULT_PORT} or inject a "
                    "launcher that owns the endpoint contract"
                )
            executable = shutil.which(SERVER_EXECUTABLE)
            if executable is None:
                raise DuckDBServerNotProvisionedError(
                    f"the {SERVER_EXECUTABLE!r} executable is not provisioned "
                    "on PATH, so the HTTP/Arrow face cannot be raised. The "
                    "boot path never runs an installer (mirrors canopy "
                    "AD-13's LOAD-only discipline). Provision it via the "
                    "pyforge-atlas pixi env, which carries duckdb-server on "
                    "linux-64: `pixi install -e pyforge-atlas`, then retry."
                )
            chosen_launcher: Launcher = _launch_duckdb_server
        else:
            executable = SERVER_EXECUTABLE
            chosen_launcher = launcher
        argv = _server_argv(executable, Path(path))

        # Yield the DuckDB file lock to the server process, KEEPING the plane
        # writer filelock (Story 20.1 chosen handling, recorded in the story
        # spec's Design Notes): duckdb 1.5.5 refuses ANY second cross-process
        # open while a read-write connection is held (verified live
        # 2026-08-27), and the installed server opens the path eagerly,
        # read-write, at startup — so a live in-process connection would make
        # the server crash at boot. Closing only the raw connection (not the
        # LockedDuckDB) keeps `atlas.duckdb.writer.lock` held for the boot's
        # whole lifetime: SecondWriterRefused still guards the plane against
        # any other pyforge writer, and the server is the plane's sole DuckDB
        # holder while the HTTP face lives. In-process re-close on
        # `library.close()` is a no-op (verified).
        library._con.close()  # noqa: SLF001 — deliberate: yield the DB, keep the lock
        notices.append(
            {
                "event": "library-face-yielded",
                "reason": "duckdb-single-process-lock",
                "path": str(path),
                "detail": (
                    "duckdb allows one read-write process XOR N read-only "
                    "processes per file; the HTTP face's server opens the "
                    "path read-write, so the in-process connection yields "
                    "while the plane writer filelock stays held by this boot"
                ),
            }
        )
        process = chosen_launcher(argv)
    except BaseException:
        # BaseException, not Exception: a KeyboardInterrupt / SystemExit
        # between connect_writer and return must not leak the writer filelock
        # to in-process API callers (review finding 3, Story 20.1).
        library.close()
        raise

    endpoint = f"http://{host}:{port}/"
    notices.append(
        {
            "event": "http-face-raised",
            "endpoint": endpoint,
            "path": str(path),
            "pid": getattr(process, "pid", None),
        }
    )
    return PlaneBoot(
        library=library,
        http=HttpFace(endpoint=endpoint, process=process),
        notices=notices,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="query-plane-boot",
        description=(
            "Story 20.1 (CAP-5): the ONE boot script raising both plane "
            "faces — library face always, Mosaic duckdb-server HTTP/Arrow "
            f"face only when {STACK_UP_ENV} is truthy (1/true/yes/on)."
        ),
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_PLANE_PATH,
        help=(f"plane database path (basename must be {ATLAS_DUCKDB_NAME}; default: {DEFAULT_PLANE_PATH})"),
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"host used in the reported HTTP endpoint (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=(
            f"HTTP face port (default and, for the installed duckdb-server, "
            f"the only honorable value: {DEFAULT_PORT} — hard-coded upstream)"
        ),
    )
    return parser


def _shutdown(process: Any) -> None:
    process.terminate()
    try:
        process.wait(timeout=10)
    except Exception:
        process.kill()
        process.wait(timeout=10)


def _supervise(boot: PlaneBoot) -> int:
    """Foreground-supervise the HTTP face (CLI, stack-up path; main thread
    only — the SIGTERM registration below requires it).

    SIGINT → clean shutdown, exit 130 (NFR-6 interrupted). SIGTERM (a
    systemd/CI stop) is funneled through the SAME clean shutdown and also
    exits 130, so stopping the supervisor can never orphan the duckdb-server
    child holding the plane read-write with the filelock left behind (review
    finding 7, Story 20.1). The server exiting on its own is an error
    (exit 2) — a supervisor with nothing left to supervise did not succeed.
    """
    assert boot.http is not None
    process = boot.http.process

    def _on_sigterm(signum: int, frame: object) -> None:
        # Same terminate/wait/kill of the child, same library-handle close,
        # same exit 130 as SIGINT.
        raise KeyboardInterrupt

    previous = signal.signal(signal.SIGTERM, _on_sigterm)
    try:
        returncode = process.wait()
        print(
            json.dumps({"event": "http-face-exited", "returncode": returncode}),
            file=sys.stderr,
        )
        return 2
    except KeyboardInterrupt:
        _shutdown(process)
        return 130
    finally:
        signal.signal(signal.SIGTERM, previous)
        boot.library.close()


def _best_effort_teardown(boot: PlaneBoot) -> None:
    """Post-boot escape hatch (CLI): leave no child and no held lock behind.

    Never raises — it runs on paths that are already exiting on an interrupt
    or an unexpected error (review finding 2, Story 20.1).
    """
    if boot.http is not None:
        with contextlib.suppress(Exception):
            _shutdown(boot.http.process)
    with contextlib.suppress(Exception):
        boot.library.close()


def main(argv: list[str] | None = None) -> int:
    """Boot the plane; print one-line JSON envelope(s); NFR-6 exit codes.

    0 pass / 1 policy fail (typed refusals: SecondWriterRefused,
    DuckDBServerNotProvisionedError) / 2 error / 130 interrupted (SIGINT, or
    SIGTERM while supervising). Stack-down boots, emits the notice envelope,
    releases and exits 0 (the library face is in-process — holding it in a
    foreground CLI serves no other process); stack-up stays foreground as the
    server's supervisor.
    """
    args = _build_parser().parse_args(argv)
    try:
        boot = boot_query_plane(args.path, host=args.host, port=args.port)
    except PyforgeError as exc:
        # SecondWriterRefused / DuckDBServerNotProvisionedError: typed refusals.
        print(
            json.dumps(
                {
                    "event": "boot-refused",
                    "error": type(exc).__name__,
                    "detail": str(exc),
                }
            )
        )
        return 1
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    try:
        for notice in boot.notices:
            print(json.dumps(notice))
        sys.stdout.flush()

        if boot.http is None:
            boot.library.close()
            return 0
        return _supervise(boot)
    except KeyboardInterrupt:
        _best_effort_teardown(boot)
        return 130
    except Exception as exc:
        # Failures AFTER boot_query_plane returned (notice printing,
        # supervise/shutdown internals) must not escape the NFR-6 mapping as
        # Python's default exit 1 — that code means "policy fail" (review
        # finding 2, Story 20.1).
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        _best_effort_teardown(boot)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
