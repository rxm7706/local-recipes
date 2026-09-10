#!/usr/bin/env python3
"""Provision a real local S3-compatible object-storage server for platform dev/test.

WHY THIS EXISTS. Story 50.1 (pyforge-steward, Epic 50) landed the AD-1 exception
that lets pyforge *consume* S3-compatible object storage -- production target is
NetApp StorageGRID, ops-provided and externally operated. Nobody develops or
tests against production StorageGRID, and nothing pixi-installable existed
locally to consume yet. This script provisions a REAL local server -- never a
mock -- so Story 50.3's S3-client seam (and anything after it) has something
honest to round-trip against.

TWO PLUGGABLE BACKENDS, chosen via `PYFORGE_OBJECT_STORAGE_BACKEND`
(default: `silo`):

- `silo` (DEFAULT) -- pgsty/silo, a community-maintained MinIO server fork
  (Story 50.1's own recipe). Full Linux/macOS/Windows conda-forge-equivalent
  coverage upstream (this repo only ships a linux-64 build today, published
  to SelfExplainML), real MinIO-API-compatible S3 server.
- `garage` -- already on conda-forge today, Linux/macOS only (NO win-64
  build -- verified live via conda-forge repodata). Chosen when the operator
  needs a genuinely different implementation to test against, or on a
  platform where Silo's binary hasn't been published yet.

Both backends bind the S3 API to the SAME canonical endpoint --
127.0.0.1:9000 -- so a consumer (Story 50.3's client) never needs to know
which backend is running underneath. Credentials are also identical across
both backends (dev-only, never used against real StorageGRID).

WHY A SEPARATE ENVIRONMENT. Garage has NO win-64 conda-forge build, and the
workspace's default platform list includes win-64 -- adding these
dependencies to an existing feature would break that solve outright. This
mirrors the `scribe-pg` / pgvector precedent exactly (see scripts/scribe_pg.py).

Server state lives under gitignored `var/platform-object-storage/<backend>/`,
never a container. `up` is idempotent: re-running against a live server
re-asserts (prints ready) rather than failing or restarting it. `garage` on
Windows refuses cleanly with a named gap and a pointer to `silo` -- it never
silently no-ops.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import platform
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE_DIR = ROOT / "var" / "platform-object-storage"

#: The one S3 endpoint a consumer ever needs to know, regardless of backend.
#: Must match Story 50.3's client-seam config default.
S3_API_PORT = 9000
SILO_CONSOLE_PORT = 9001
GARAGE_RPC_PORT = 3901
GARAGE_ADMIN_PORT = 3903

#: Dev-only credentials, identical across both backends -- never used against
#: real StorageGRID (which is ops-provisioned and out of this script's scope).
ACCESS_KEY = "pyforgeplatformdev"
SECRET_KEY = "pyforgeplatformdevsecretkey12345"
DEFAULT_BUCKET = "platform-dev"

BACKEND_ENV = "PYFORGE_OBJECT_STORAGE_BACKEND"
DEFAULT_BACKEND = "silo"
VALID_BACKENDS = ("silo", "garage")

_HEALTH_POLL_SECONDS = 30


def _need(binary: str, *, feature: str) -> str:
    found = shutil.which(binary)
    if not found:
        sys.exit(
            f"[platform-object-storage] cannot run: `{binary}` is not on PATH. "
            f"Use the composed environment: pixi run -e {feature} "
            f"platform-object-storage-up"
        )
    return found


def _http_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:  # noqa: S310
            return resp.status == 200
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def _read_pid(pidfile: pathlib.Path) -> int | None:
    if not pidfile.is_file():
        return None
    try:
        return int(pidfile.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None


def _process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    else:
        return True


def _stop_pid(pidfile: pathlib.Path, *, name: str, is_up) -> int:
    pid = _read_pid(pidfile)
    if pid is None or not _process_alive(pid):
        pidfile.unlink(missing_ok=True)
        print(f"[platform-object-storage] {name}: not running")
        return 0
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pidfile.unlink(missing_ok=True)
        return 0
    for _ in range(15):
        if not is_up() and not _process_alive(pid):
            break
        time.sleep(1)
    else:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    pidfile.unlink(missing_ok=True)
    print(f"[platform-object-storage] {name}: stopped")
    return 0


def _spawn(args: list[str], *, log_path: pathlib.Path, env: dict, pidfile: pathlib.Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as logfh:
        proc = subprocess.Popen(  # noqa: S603
            args,
            stdout=logfh,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,
        )
    pidfile.write_text(str(proc.pid), encoding="utf-8")


# --------------------------------------------------------------------------
# silo backend (DEFAULT)
# --------------------------------------------------------------------------

_SILO_DIR = BASE_DIR / "silo"
_SILO_DATA = _SILO_DIR / "data"
_SILO_LOG = _SILO_DIR / "server.log"
_SILO_PIDFILE = _SILO_DIR / "server.pid"


def _silo_is_up() -> bool:
    return _http_ok(f"http://127.0.0.1:{S3_API_PORT}/minio/health/live")


def _silo_up() -> int:
    binary = _need("silo", feature="platform-object-storage")
    _SILO_DATA.mkdir(parents=True, exist_ok=True)

    if _silo_is_up():
        print(f"[platform-object-storage] silo: already listening on 127.0.0.1:{S3_API_PORT}")
    else:
        env = {
            **os.environ,
            "MINIO_ROOT_USER": ACCESS_KEY,
            "MINIO_ROOT_PASSWORD": SECRET_KEY,
        }
        _spawn(
            [
                binary, "server", str(_SILO_DATA),
                "--address", f":{S3_API_PORT}",
                "--console-address", f":{SILO_CONSOLE_PORT}",
            ],
            log_path=_SILO_LOG, env=env, pidfile=_SILO_PIDFILE,
        )
        for _ in range(_HEALTH_POLL_SECONDS):
            if _silo_is_up():
                break
            time.sleep(1)
        else:
            sys.exit(f"[platform-object-storage] silo: server did not become ready; see {_SILO_LOG}")
        print(f"[platform-object-storage] silo: started on 127.0.0.1:{S3_API_PORT}")

    print(f"[platform-object-storage] silo: ready -- http://127.0.0.1:{S3_API_PORT} "
          f"(access key {ACCESS_KEY}, secret ***)")
    print(f"[platform-object-storage] silo: console at http://127.0.0.1:{SILO_CONSOLE_PORT}")
    return 0


def _silo_down() -> int:
    return _stop_pid(_SILO_PIDFILE, name="silo", is_up=_silo_is_up)


def _silo_status() -> int:
    live = _silo_is_up()
    print(f"[platform-object-storage] silo: {'listening' if live else 'not listening'} "
          f"on 127.0.0.1:{S3_API_PORT}  (data dir {'present' if _SILO_DATA.is_dir() else 'absent'})")
    return 0


# --------------------------------------------------------------------------
# garage backend (alternative -- NO win-64 build, refuses cleanly there)
# --------------------------------------------------------------------------

_GARAGE_DIR = BASE_DIR / "garage"
_GARAGE_DATA = _GARAGE_DIR / "data"
_GARAGE_META = _GARAGE_DIR / "meta"
_GARAGE_CONFIG = _GARAGE_DIR / "garage.toml"
_GARAGE_LOG = _GARAGE_DIR / "server.log"
_GARAGE_PIDFILE = _GARAGE_DIR / "server.pid"


def _garage_refuse_on_windows() -> bool:
    """Named gap, not a silent no-op -- Garage ships no win-64 conda-forge build
    (verified live against conda-forge repodata: 0 builds vs 7 each on
    linux-64/linux-aarch64/osx-64/osx-arm64)."""
    if platform.system() != "Windows":
        return False
    sys.stderr.write(
        "[platform-object-storage] garage: has no win-64 conda-forge build -- "
        f"this backend cannot run on Windows. Use the default backend instead "
        f"(unset {BACKEND_ENV}, or set it to `silo`), which ships a native "
        "Windows binary.\n"
    )
    return True


def _garage_render_config() -> str:
    import secrets  # noqa: PLC0415

    rpc_secret = secrets.token_hex(32)
    return (
        f'metadata_dir = "{_GARAGE_META}"\n'
        f'data_dir = "{_GARAGE_DATA}"\n'
        'db_engine = "sqlite"\n'
        "replication_factor = 1\n"
        "\n"
        f'rpc_bind_addr = "127.0.0.1:{GARAGE_RPC_PORT}"\n'
        f'rpc_public_addr = "127.0.0.1:{GARAGE_RPC_PORT}"\n'
        f'rpc_secret = "{rpc_secret}"\n'
        "\n"
        "[s3_api]\n"
        's3_region = "garage"\n'
        f'api_bind_addr = "127.0.0.1:{S3_API_PORT}"\n'
        'root_domain = ".s3.garage.localhost"\n'
        "\n"
        "[admin]\n"
        f'api_bind_addr = "127.0.0.1:{GARAGE_ADMIN_PORT}"\n'
    )


def _garage_is_up(binary: str) -> bool:
    if not _GARAGE_CONFIG.is_file():
        return False
    result = subprocess.run(  # noqa: S603
        [binary, "-c", str(_GARAGE_CONFIG), "health", "-q"],
        capture_output=True,
    )
    return result.returncode == 0


def _garage_up() -> int:
    if _garage_refuse_on_windows():
        return 1
    binary = _need("garage", feature="platform-object-storage")
    _GARAGE_DATA.mkdir(parents=True, exist_ok=True)
    _GARAGE_META.mkdir(parents=True, exist_ok=True)

    if not _GARAGE_CONFIG.is_file():
        _GARAGE_CONFIG.write_text(_garage_render_config(), encoding="utf-8")
        print(f"[platform-object-storage] garage: wrote config to {_GARAGE_CONFIG.relative_to(ROOT)}")

    if _garage_is_up(binary):
        print(f"[platform-object-storage] garage: already listening on 127.0.0.1:{S3_API_PORT}")
    else:
        env = {
            **os.environ,
            "GARAGE_DEFAULT_ACCESS_KEY": ACCESS_KEY,
            "GARAGE_DEFAULT_SECRET_KEY": SECRET_KEY,
            "GARAGE_DEFAULT_BUCKET": DEFAULT_BUCKET,
        }
        _spawn(
            [binary, "-c", str(_GARAGE_CONFIG), "server",
             "--single-node", "--default-access-key", "--default-bucket"],
            log_path=_GARAGE_LOG, env=env, pidfile=_GARAGE_PIDFILE,
        )
        for _ in range(_HEALTH_POLL_SECONDS):
            if _garage_is_up(binary):
                break
            time.sleep(1)
        else:
            sys.exit(f"[platform-object-storage] garage: server did not become ready; see {_GARAGE_LOG}")
        print(f"[platform-object-storage] garage: started on 127.0.0.1:{S3_API_PORT}")

    print(f"[platform-object-storage] garage: ready -- http://127.0.0.1:{S3_API_PORT} "
          f"(access key {ACCESS_KEY}, secret ***, bucket {DEFAULT_BUCKET!r})")
    return 0


def _garage_down() -> int:
    if _garage_refuse_on_windows():
        return 1
    binary = shutil.which("garage")
    is_up = (lambda: _garage_is_up(binary)) if binary else (lambda: False)
    return _stop_pid(_GARAGE_PIDFILE, name="garage", is_up=is_up)


def _garage_status() -> int:
    if _garage_refuse_on_windows():
        return 1
    binary = shutil.which("garage")
    live = _garage_is_up(binary) if binary else False
    print(f"[platform-object-storage] garage: {'listening' if live else 'not listening'} "
          f"on 127.0.0.1:{S3_API_PORT}  (data dir {'present' if _GARAGE_DATA.is_dir() else 'absent'})")
    return 0


# --------------------------------------------------------------------------
# dispatcher
# --------------------------------------------------------------------------

_DISPATCH = {
    "silo": {"up": _silo_up, "down": _silo_down, "status": _silo_status},
    "garage": {"up": _garage_up, "down": _garage_down, "status": _garage_status},
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("verb", choices=("up", "down", "status"))
    args = ap.parse_args(argv)

    backend = os.environ.get(BACKEND_ENV) or DEFAULT_BACKEND
    if backend not in VALID_BACKENDS:
        sys.stderr.write(
            f"[platform-object-storage] unknown backend {backend!r} -- choose one "
            f"of: {', '.join(VALID_BACKENDS)} (set via {BACKEND_ENV})\n"
        )
        return 1

    return _DISPATCH[backend][args.verb]()


if __name__ == "__main__":
    sys.exit(main())
