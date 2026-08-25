"""Run `liquibase update` against MIGRATION_DATABASE_URL (canopy AD-9).

The Helm Liquibase Job invokes this through the image ENTRYPOINT so pixi
puts `liquibase` and `python` on PATH. Credentials stay in env
(secretKeyRef); the chart never composes user:password into the render.
"""

from __future__ import annotations

import os
import subprocess
import sys
from urllib.parse import unquote
from urllib.parse import urlparse

POOLING_HOST_MARKERS = ("pgbouncer", "pgpool", "pg-bouncer", "pg-pool")
CHANGELOG_FILE = "db/changelog/db.changelog-master.yaml"
DEFAULTS_FILE = "db/liquibase.properties"


def jdbc_url_from_migration_database_url(database_url: str) -> tuple[str, str, str]:
    """Return (jdbc_url_with_currentSchema, username, password).

    FR-21a: currentSchema is on the connection; pooling-proxy hosts are
    refused so DDL cannot land on a transaction-pooled session.
    """
    parsed = urlparse(database_url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"postgres", "postgresql"}:
        msg = f"MIGRATION_DATABASE_URL scheme must be postgres, got {scheme!r}"
        raise ValueError(msg)
    host = (parsed.hostname or "").lower()
    if not host:
        msg = "MIGRATION_DATABASE_URL is missing a hostname"
        raise ValueError(msg)
    for marker in POOLING_HOST_MARKERS:
        if marker in host:
            msg = (
                f"MIGRATION_DATABASE_URL host {host!r} looks like a pooling "
                f"proxy ({marker}); the Liquibase Job must connect directly "
                f"to PostgreSQL (FR-21a)"
            )
            raise ValueError(msg)
    port = parsed.port or 5432
    database = (parsed.path or "").lstrip("/") or "platform"
    username = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    jdbc = f"jdbc:postgresql://{host}:{port}/{database}?currentSchema=public"
    return jdbc, username, password


def liquibase_update_argv(database_url: str) -> list[str]:
    jdbc, username, password = jdbc_url_from_migration_database_url(database_url)
    return [
        "liquibase",
        f"--defaults-file={DEFAULTS_FILE}",
        f"--changelog-file={CHANGELOG_FILE}",
        "--liquibase-schema-name=liquibase",
        "--preserve-schema-case=false",
        f"--url={jdbc}",
        f"--username={username}",
        f"--password={password}",
        "update",
    ]


def main(argv: list[str] | None = None) -> int:
    del argv
    database_url = os.environ.get("MIGRATION_DATABASE_URL", "")
    if not database_url:
        sys.stderr.write("MIGRATION_DATABASE_URL is required\n")
        return 2
    try:
        cmd = liquibase_update_argv(database_url)
    except ValueError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2
    return subprocess.call(cmd)  # noqa: S603 -- fixed argv from this module


if __name__ == "__main__":
    raise SystemExit(main())
