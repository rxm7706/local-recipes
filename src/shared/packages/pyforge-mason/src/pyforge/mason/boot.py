"""Mason boot re-index (steward Story 25.4 / FR-29 / BS-8).

PostgreSQL is the canonical index. Lane 1 media is an optional RWX
directory (canopy AD-13), never MinIO/S3. Unique-key upsert means a killed
boot plus a restart applies each artifact once.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pyforge.core.errors import PyforgeError

_CREATE_INDEX = """
CREATE TABLE IF NOT EXISTS mason_index (
    artifact_key TEXT PRIMARY KEY,
    size INTEGER NOT NULL,
    source TEXT NOT NULL
)
"""

_UPSERT = """
INSERT INTO mason_index (artifact_key, size, source)
VALUES (?, ?, ?)
ON CONFLICT (artifact_key) DO NOTHING
"""

_INSERT_ALWAYS = """
INSERT INTO mason_index (artifact_key, size, source)
VALUES (?, ?, ?)
"""


class BootInterrupted(PyforgeError, Exception):
    """Test seam: reconcile stopped mid-flight. Resume with the same store.

    Multi-inherits ``PyforgeError`` directly (Story 14.3, CAP-5) rather than
    ``MasonError``: ``MasonError.__init__`` requires ``(identifier,
    message)``, which would break this class's bare ``raise
    BootInterrupted`` call site -- ``PyforgeError`` is a no-``__init__``
    marker, so re-parenting here changes nothing observable.
    """


class IndexStore(Protocol):
    def upsert(self, artifact_key: str, size: int, source: str) -> None: ...

    def row_count(self) -> int: ...

    def keys(self) -> tuple[str, ...]: ...


@dataclass(frozen=True)
class ReconcileReport:
    scanned: int
    row_count: int


class SqliteIndexStore:
    """PostgreSQL-shaped unique-key index (same ``ON CONFLICT`` SQL)."""

    def __init__(self, connection: sqlite3.Connection | None = None) -> None:
        self._conn = connection or sqlite3.connect(":memory:")
        self._conn.execute(_CREATE_INDEX)

    def upsert(self, artifact_key: str, size: int, source: str) -> None:
        self._conn.execute(_UPSERT, (artifact_key, size, source))
        self._conn.commit()

    def row_count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM mason_index").fetchone()
        return int(row[0])

    def keys(self) -> tuple[str, ...]:
        rows = self._conn.execute("SELECT artifact_key FROM mason_index ORDER BY artifact_key").fetchall()
        return tuple(str(r[0]) for r in rows)


class NaiveAppendStore:
    """AD-15 trap: INSERT with no unique key — restart duplicates rows."""

    def __init__(self) -> None:
        self._conn = sqlite3.connect(":memory:")
        self._conn.execute(
            """
            CREATE TABLE mason_index (
                artifact_key TEXT NOT NULL,
                size INTEGER NOT NULL,
                source TEXT NOT NULL
            )
            """
        )

    def upsert(self, artifact_key: str, size: int, source: str) -> None:
        self._conn.execute(_INSERT_ALWAYS, (artifact_key, size, source))
        self._conn.commit()

    def row_count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM mason_index").fetchone()
        return int(row[0])

    def keys(self) -> tuple[str, ...]:
        rows = self._conn.execute("SELECT artifact_key FROM mason_index ORDER BY artifact_key").fetchall()
        return tuple(str(r[0]) for r in rows)


def scan_rwx(rwx_root: Path | None) -> tuple[tuple[str, int], ...]:
    """List files under an RWX mount. Missing root → empty (PG-only boot)."""
    if rwx_root is None or not rwx_root.is_dir():
        return ()
    found: list[tuple[str, int]] = []
    for path in sorted(rwx_root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(rwx_root).as_posix()
        found.append((rel, path.stat().st_size))
    return tuple(found)


def reconcile_boot(
    store: IndexStore,
    rwx_root: Path | None = None,
    *,
    interrupt_after: int | None = None,
    apply: Callable[[IndexStore, str, int, str], None] | None = None,
) -> ReconcileReport:
    """Re-index RWX files into the unique-key store. Idempotent on restart."""
    writer = apply or _unique_upsert
    artifacts = scan_rwx(rwx_root)
    applied = 0
    for key, size in artifacts:
        if interrupt_after is not None and applied >= interrupt_after:
            raise BootInterrupted
        writer(store, key, size, "rwx")
        applied += 1
    return ReconcileReport(scanned=len(artifacts), row_count=store.row_count())


def _unique_upsert(store: IndexStore, key: str, size: int, source: str) -> None:
    store.upsert(key, size, source)


def insert_always(store: IndexStore, key: str, size: int, source: str) -> None:
    """Naive INSERT used only to prove the AD-15 trap."""
    store.upsert(key, size, source)
