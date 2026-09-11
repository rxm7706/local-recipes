"""Mason boot reconciliation on host startup (CAP-10 / BS-8).

``django_mason_portal`` is the production boot path for Mason on the host.
PostgreSQL is the canonical index; Lane 1 media (``MEDIA_ROOT``) is scanned
when present (canopy AD-13).
"""

from __future__ import annotations

from pathlib import Path

from django.db import connection

from pyforge.mason.boot import reconcile_boot

_CREATE_INDEX = """
CREATE TABLE IF NOT EXISTS mason_index (
    artifact_key TEXT PRIMARY KEY,
    size INTEGER NOT NULL,
    source TEXT NOT NULL
)
"""

_UPSERT = """
INSERT INTO mason_index (artifact_key, size, source)
VALUES (%s, %s, %s)
ON CONFLICT (artifact_key) DO NOTHING
"""


class DjangoPgIndexStore:
    """PostgreSQL-backed ``IndexStore`` for Mason boot reconcile."""

    def __init__(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute(_CREATE_INDEX)

    def upsert(self, artifact_key: str, size: int, source: str) -> None:
        with connection.cursor() as cursor:
            cursor.execute(_UPSERT, (artifact_key, size, source))

    def row_count(self) -> int:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM mason_index")
            row = cursor.fetchone()
        return int(row[0])

    def keys(self) -> tuple[str, ...]:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT artifact_key FROM mason_index ORDER BY artifact_key",
            )
            rows = cursor.fetchall()
        return tuple(str(row[0]) for row in rows)


def run_mason_boot_reconcile() -> None:
    """Re-index Lane 1 media into the canonical PostgreSQL index on boot."""
    from django.conf import settings

    media_root = getattr(settings, "MEDIA_ROOT", None)
    rwx_root = Path(media_root) if media_root else None
    store = DjangoPgIndexStore()
    reconcile_boot(store, rwx_root)
