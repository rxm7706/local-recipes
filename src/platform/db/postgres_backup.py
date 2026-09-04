"""PostgreSQL base backup + drill manifest (Story 41.1).

The Helm backup CronJob invokes ``basebackup`` through the platform image
ENTRYPOINT. Physical backup uses ``pg_basebackup``; a custom-format ``pg_dump``
is written alongside for steward restore drills (not the primary PITR
mechanism — WAL archiving is).

Credentials arrive from env (secretKeyRef); the chart never composes passwords
into the render path (AD-12).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote
from urllib.parse import urlparse


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        msg = f"{name} is required"
        raise ValueError(msg)
    return value


def _connection_params() -> dict[str, str | int]:
    host = _require_env("POSTGRES_HOST")
    port = int(os.environ.get("POSTGRES_PORT", "5432"))
    database = _require_env("POSTGRES_DB")
    user = _require_env("POSTGRES_USER")
    password = _require_env("POSTGRES_PASSWORD")
    return {
        "host": host,
        "port": port,
        "database": database,
        "user": user,
        "password": password,
    }


def _counts_from_live_db(params: dict[str, str | int]) -> dict[str, int]:
    import psycopg2  # noqa: PLC0415 -- platform conda env

    conn = psycopg2.connect(
        host=params["host"],
        port=params["port"],
        dbname=params["database"],
        user=params["user"],
        password=params["password"],
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM run_state")
            run_state_count = int(cursor.fetchone()[0])
            cursor.execute("SELECT COUNT(*) FROM wagtailcore_page")
            wagtail_page_count = int(cursor.fetchone()[0])
    finally:
        conn.close()
    return {
        "run_state_count": run_state_count,
        "wagtail_page_count": wagtail_page_count,
    }


def _ensure_pg_binary(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        msg = f"{name} not found on PATH — add postgresql client tools to the platform image"
        raise RuntimeError(msg)
    return path


def run_basebackup() -> int:
    params = _connection_params()
    backup_root = Path(_require_env("BACKUP_ROOT"))
    stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    base_dir = backup_root / "base" / stamp
    drill_dir = backup_root / "drill" / stamp
    wal_dir = backup_root / "wal"
    base_dir.mkdir(parents=True, exist_ok=True)
    drill_dir.mkdir(parents=True, exist_ok=True)
    wal_dir.mkdir(parents=True, exist_ok=True)

    counts = _counts_from_live_db(params)
    manifest = {
        "timestamp": stamp,
        "run_state_count": counts["run_state_count"],
        "wagtail_page_count": counts["wagtail_page_count"],
        "base_dir": str(base_dir),
        "drill_dump": str(drill_dir / "dump.pgcustom"),
    }

    pg_basebackup = _ensure_pg_binary("pg_basebackup")
    base_argv = [
        pg_basebackup,
        "-h",
        str(params["host"]),
        "-p",
        str(params["port"]),
        "-U",
        str(params["user"]),
        "-D",
        str(base_dir),
        "-Fp",
        "-Xs",
        "-P",
    ]
    env = os.environ.copy()
    env["PGPASSWORD"] = str(params["password"])
    subprocess.run(base_argv, check=True, env=env)  # noqa: S603

    pg_dump = _ensure_pg_binary("pg_dump")
    dump_path = drill_dir / "dump.pgcustom"
    dump_argv = [
        pg_dump,
        "-h",
        str(params["host"]),
        "-p",
        str(params["port"]),
        "-U",
        str(params["user"]),
        "-d",
        str(params["database"]),
        "-Fc",
        "-f",
        str(dump_path),
    ]
    subprocess.run(dump_argv, check=True, env=env)  # noqa: S603

    manifest_path = base_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    latest = backup_root / "base" / "latest"
    if latest.is_symlink() or latest.exists():
        latest.unlink()
    latest.symlink_to(base_dir.name, target_is_directory=True)
    print(f"backup complete: {manifest_path}")
    return 0


def migration_url_params(database_url: str) -> dict[str, str | int]:
    parsed = urlparse(database_url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"postgres", "postgresql"}:
        msg = f"database URL scheme must be postgres, got {scheme!r}"
        raise ValueError(msg)
    return {
        "host": parsed.hostname or "",
        "port": parsed.port or 5432,
        "database": (parsed.path or "").lstrip("/") or "platform",
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
    }


def run_restore_drill(*, backup_path: Path) -> dict[str, object]:
    """Restore drill logic shared with steward restore duty."""
    manifest_path = backup_path / "manifest.json"
    if not manifest_path.is_file() and backup_path.name != "latest":
        manifest_path = backup_path.parent / "manifest.json"
    if not manifest_path.is_file():
        msg = f"manifest.json not found under {backup_path}"
        raise FileNotFoundError(msg)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    dump_path = Path(str(manifest["drill_dump"]))
    if not dump_path.is_file():
        msg = f"drill dump not found: {dump_path}"
        raise FileNotFoundError(msg)

    database_url = _require_env("MIGRATION_DATABASE_URL")
    params = migration_url_params(database_url)
    stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    scratch_db = f"platform_drill_{stamp}"

    import psycopg2  # noqa: PLC0415
    from psycopg2 import sql  # noqa: PLC0415

    admin = psycopg2.connect(
        host=params["host"],
        port=params["port"],
        dbname=params["database"],
        user=params["user"],
        password=params["password"],
    )
    admin.autocommit = True
    try:
        with admin.cursor() as cursor:
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(scratch_db)),
            )
    finally:
        admin.close()

    pg_restore = _ensure_pg_binary("pg_restore")
    env = os.environ.copy()
    env["PGPASSWORD"] = str(params["password"])
    restore_argv = [
        pg_restore,
        "-h",
        str(params["host"]),
        "-p",
        str(params["port"]),
        "-U",
        str(params["user"]),
        "-d",
        scratch_db,
        "--no-owner",
        "--no-acl",
        str(dump_path),
    ]
    try:
        subprocess.run(restore_argv, check=True, env=env)  # noqa: S603
        live_counts = _counts_from_live_db(
            {
                **params,
                "database": scratch_db,
            },
        )
    finally:
        cleanup = psycopg2.connect(
            host=params["host"],
            port=params["port"],
            dbname=params["database"],
            user=params["user"],
            password=params["password"],
        )
        cleanup.autocommit = True
        try:
            with cleanup.cursor() as cursor:
                cursor.execute(
                    sql.SQL(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        "WHERE datname = %s AND pid <> pg_backend_pid()",
                    ),
                    (scratch_db,),
                )
                cursor.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {}").format(
                        sql.Identifier(scratch_db),
                    ),
                )
        finally:
            cleanup.close()

    expected_run_state = int(manifest["run_state_count"])
    expected_wagtail = int(manifest["wagtail_page_count"])
    ok = (
        live_counts["run_state_count"] == expected_run_state
        and live_counts["wagtail_page_count"] == expected_wagtail
    )
    return {
        "ok": ok,
        "manifest_path": str(manifest_path),
        "expected": {
            "run_state_count": expected_run_state,
            "wagtail_page_count": expected_wagtail,
        },
        "actual": live_counts,
        "scratch_database": scratch_db,
    }


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: postgres_backup.py basebackup", file=sys.stderr)
        return 2
    if args[0] == "basebackup":
        return run_basebackup()
    print(f"unknown command: {args[0]!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
