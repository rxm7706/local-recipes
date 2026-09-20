"""Read-only live Postgres attach on the CAP-19 plane (FR-46, canopy AD-22).

Consumer boot ``LOAD``s ``postgres`` from the pre-provisioned extension cache
and ``ATTACH … READ_ONLY``. It never ``INSTALL``s (canopy AD-22). Federation is
DuckDB SQL on the plane connection — not a pandas SQL dataset.
"""

from __future__ import annotations

import re
from typing import Any

from pyforge.core.errors import PyforgeError

DEFAULT_ATTACH_ALIAS = "oltp"

# \Z (not $) so a trailing newline cannot slip through.
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\Z")


class PostgresNotProvisionedError(PyforgeError, RuntimeError):
    """``postgres`` cannot be LOADed offline — the consumer path must not INSTALL."""


def _valid_identifier(value: str, what: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER_RE.match(value):
        raise ValueError(f"invalid {what} identifier {value!r}: must match {_IDENTIFIER_RE.pattern}")
    return value


def _sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _disable_extension_network(con: Any) -> None:
    con.execute("SET autoinstall_known_extensions = false")
    con.execute("SET autoload_known_extensions = false")


def load_postgres_offline(con: Any) -> None:
    """LOAD ``postgres`` from the local extension cache. Never INSTALL."""
    _disable_extension_network(con)
    try:
        con.execute("LOAD postgres")
    except Exception as exc:
        raise PostgresNotProvisionedError(
            "the DuckDB 'postgres' extension is not provisioned in the local "
            "extension cache, so it cannot be LOADed offline. The consumer path "
            "never runs a network INSTALL (canopy AD-22). Provision the cache in an "
            f"attended session, then retry. Underlying error: {type(exc).__name__}: {exc}"
        ) from exc


def attach_postgres_readonly(
    connection: Any,
    dsn: str,
    *,
    alias: str = DEFAULT_ATTACH_ALIAS,
) -> None:
    """ATTACH a Postgres DSN on an existing plane connection as ``READ_ONLY``.

    ``connection`` is a plane handle from ``connect_writer`` / ``connect_reader``.
    This does not open a second writable ``.duckdb``.
    """
    if not isinstance(dsn, str) or not dsn.strip():
        raise ValueError("postgres DSN must be a non-empty string")
    dsn = dsn.strip()
    alias = _valid_identifier(alias, "attach alias")
    load_postgres_offline(connection)
    connection.execute(f"ATTACH {_sql_string(dsn)} AS {alias} (TYPE POSTGRES, READ_ONLY)")
