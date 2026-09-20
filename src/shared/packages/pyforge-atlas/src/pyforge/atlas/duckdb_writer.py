"""Single-writer discipline for ``atlas.duckdb`` (FR-27, BS-5, canopy AD-15).

Atlas still defaults RAG/BSL to in-memory DuckDB. File-backed ``atlas.duckdb``
must go through this opener: one exclusive writer; readers pass ``read_only=True``.
Live Postgres is ``ATTACH … READ_ONLY`` on this same handle
(:func:`pyforge.atlas.live_attach.attach_postgres_readonly`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import filelock
from pyforge.core.errors import PyforgeError

ATLAS_DUCKDB_NAME = "atlas.duckdb"
# Story 41.2: the one declared writer module for file-backed ``atlas.duckdb``.
DUCKDB_WRITER_MODULE = "pyforge.atlas.duckdb_writer"


class SecondWriterRefused(PyforgeError, RuntimeError):
    """A writer already holds ``atlas.duckdb``."""


def _require_atlas_path(path: Path | str) -> Path:
    resolved = Path(path)
    if resolved.name != ATLAS_DUCKDB_NAME:
        msg = f"only {ATLAS_DUCKDB_NAME} is the analytical store; got {resolved.name!r}"
        raise ValueError(msg)
    return resolved


def _lock_path(db_path: Path) -> Path:
    return Path(str(db_path) + ".writer.lock")


def connect_writer(path: Path | str) -> LockedDuckDB:
    """Open ``atlas.duckdb`` for write. A second writer is refused immediately."""
    db_path = _require_atlas_path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    lock = filelock.FileLock(str(_lock_path(db_path)), thread_local=False)
    try:
        lock.acquire(timeout=0)
    except filelock.Timeout as exc:
        raise SecondWriterRefused(f"another writer already holds {db_path}") from exc
    con = duckdb.connect(str(db_path), read_only=False)
    return LockedDuckDB(con, lock)


def connect_reader(path: Path | str) -> duckdb.DuckDBPyConnection:
    """Open ``atlas.duckdb`` with ``read_only=True`` (no writer lock)."""
    db_path = _require_atlas_path(path)
    return duckdb.connect(str(db_path), read_only=True)


class LockedDuckDB:
    """DuckDB handle that releases the exclusive writer lock on ``close()``.

    DuckDB's C connection object does not allow assigning ``close``.
    """

    __slots__ = ("_con", "_lock")

    def __init__(
        self,
        con: duckdb.DuckDBPyConnection,
        lock: filelock.BaseFileLock,
    ) -> None:
        object.__setattr__(self, "_con", con)
        object.__setattr__(self, "_lock", lock)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._con, name)

    def close(self) -> None:
        try:
            self._con.close()
        finally:
            if self._lock.is_locked:
                self._lock.release()
