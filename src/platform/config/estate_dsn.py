"""FR-49: estate reads (agents) must target the query plane, never OLTP."""

from __future__ import annotations

_OLTP_PREFIXES = ("postgres://", "postgresql://")
_PLANE_PREFIXES = ("duckdb:", "parquet:", "duckdb://", "parquet://")


class EstateOltpForbidden(ValueError):
    """Text-to-SQL / estate RAG pointed at OLTP or langflow_schema."""


def assert_estate_read_is_plane(dsn: str) -> str:
    """Return ``dsn`` if it is a plane target; raise if it is OLTP."""
    if not isinstance(dsn, str) or not dsn.strip():
        raise EstateOltpForbidden("estate read DSN is empty")
    value = dsn.strip()
    lowered = value.lower()
    if "langflow_schema" in lowered or "search_path=langflow_schema" in lowered:
        raise EstateOltpForbidden("langflow_schema is not the estate read plane")
    if lowered.startswith(_OLTP_PREFIXES):
        raise EstateOltpForbidden("OLTP DSN is forbidden for estate Text-to-SQL")
    if any(lowered.startswith(prefix) for prefix in _PLANE_PREFIXES):
        return value
    if "atlas.duckdb" in lowered:
        return value
    raise EstateOltpForbidden(f"estate read DSN is not the query plane: {dsn!r}")


def estate_datasource_payload(db_name: str, estate_dsn: str) -> dict[str, object]:
    """DB-GPT ``/api/v1/chat/db/add`` body aimed at the plane, not PostgreSQL."""
    dsn = assert_estate_read_is_plane(estate_dsn)
    file_path = dsn.split(":", 1)[-1].lstrip("/")
    return {
        "db_name": db_name,
        "db_type": "duckdb",
        "db_host": "",
        "db_port": 0,
        "db_user": "",
        "db_pwd": "",
        "file_path": file_path,
        "comment": "CAP-19 / FR-49 estate read — query plane, not OLTP",
    }
