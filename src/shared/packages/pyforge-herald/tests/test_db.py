"""``db.py``'s connection setup, migration runner, transaction/connection
context managers, and one-time legacy-JSON import (Story 13.3).

Every case uses an explicit ``tmp_path``-derived ``db_path`` -- ``db.py``
never assumes a cwd, mirroring every other storage module's own
convention."""

from __future__ import annotations

import json
import sqlite3
import threading
import time

import pytest
from pyforge.herald import claims, db, notices, progress
from pyforge.herald.errors import HeraldError


# --- connection setup: WAL + busy_timeout -----------------------------------


def test_fresh_connection_is_wal_mode(tmp_path):
    db_path = tmp_path / "herald.db"
    with db.connection(db_path) as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"


def test_fresh_connection_has_the_generous_busy_timeout(tmp_path):
    db_path = tmp_path / "herald.db"
    with db.connection(db_path) as conn:
        timeout_ms = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    assert timeout_ms == db._BUSY_TIMEOUT_MS


def test_first_connection_creates_the_database_file_and_parent_dir(tmp_path):
    db_path = tmp_path / "nested" / "dir" / "herald.db"
    with db.connection(db_path):
        pass
    assert db_path.exists()


# --- migration: schema creation + versioning --------------------------------


def test_fresh_database_is_stamped_at_the_latest_schema_version(tmp_path):
    db_path = tmp_path / "herald.db"
    with db.connection(db_path) as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert version == db.SCHEMA_VERSION


def test_migration_creates_every_table(tmp_path):
    db_path = tmp_path / "herald.db"
    with db.connection(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    assert {"progress", "claims", "notices_index", "notices_redirects"} <= tables


def test_migration_is_idempotent_across_repeated_opens(tmp_path):
    """Opening the same database many times must not re-run the migration
    or disturb existing data."""
    db_path = tmp_path / "herald.db"
    progress.upsert(
        db_path,
        station="warden",
        date="2026-08-08",
        shipped_capabilities=["a"],
        compute_hours=1.0,
        token_spend=100,
        wall_clock_hours=1.0,
        unblock_narrative="",
    )
    for _ in range(3):
        with db.connection(db_path) as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
        assert version == db.SCHEMA_VERSION
    assert len(progress.read_all(db_path)) == 1


def test_unknown_future_schema_version_halts(tmp_path):
    """Boundaries & Constraints -> Block If: a database stamped with a
    ``user_version`` this build does not know about must HALT, never
    silently overwrite or downgrade."""
    db_path = tmp_path / "herald.db"
    with db.connection(db_path):
        pass
    raw = sqlite3.connect(db_path)
    raw.execute(f"PRAGMA user_version = {db.SCHEMA_VERSION + 1}")
    raw.commit()
    raw.close()

    with pytest.raises(HeraldError, match="user_version"):
        with db.connection(db_path):
            pass

    raw = sqlite3.connect(db_path)
    version = raw.execute("PRAGMA user_version").fetchone()[0]
    raw.close()
    assert version == db.SCHEMA_VERSION + 1, "a HALT must not rewrite the version"


def test_corrupt_database_file_raises_herald_error(tmp_path):
    db_path = tmp_path / "herald.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_bytes(b"not a sqlite database")
    with pytest.raises(HeraldError, match="not a valid database"):
        with db.connection(db_path):
            pass


# --- legacy JSON import -----------------------------------------------------


def test_legacy_progress_json_is_imported_once(tmp_path):
    herald_dir = tmp_path / ".herald"
    herald_dir.mkdir(parents=True)
    (herald_dir / "progress.json").write_text(
        json.dumps(
            [
                {
                    "id": "p1",
                    "station": "warden",
                    "date": "2026-08-08",
                    "shipped_capabilities": ["gate"],
                    "compute_hours": 1.5,
                    "token_spend": 1000,
                    "wall_clock_hours": 2.0,
                    "unblock_narrative": "none",
                    "created_at": "2026-08-08T00:00:00+00:00",
                    "updated_at": "2026-08-08T00:00:00+00:00",
                }
            ]
        ),
        encoding="utf-8",
    )
    db_path = herald_dir / "herald.db"
    records = progress.read_all(db_path)
    assert [r.id for r in records] == ["p1"]
    # Legacy file left in place, inert, not deleted.
    assert (herald_dir / "progress.json").exists()


def test_legacy_claims_json_is_imported_once(tmp_path):
    herald_dir = tmp_path / ".herald"
    herald_dir.mkdir(parents=True)
    (herald_dir / "claims.json").write_text(
        json.dumps(
            [
                {
                    "id": "c1",
                    "project_name": "warden",
                    "status": "draft",
                    "thesis": None,
                    "shipped_date": "2026-08-01",
                    "created_at": "2026-08-01T00:00:00+00:00",
                    "published_at": None,
                    "closed_at": None,
                    "updated_at": "2026-08-01T00:00:00+00:00",
                    "evidence": [],
                    "edit_history": [],
                }
            ]
        ),
        encoding="utf-8",
    )
    db_path = herald_dir / "herald.db"
    stored = claims.read_all(db_path)
    assert [c.id for c in stored] == ["c1"]
    assert (herald_dir / "claims.json").exists()


def test_legacy_notices_index_json_is_imported_once(tmp_path):
    herald_dir = tmp_path / ".herald"
    herald_dir.mkdir(parents=True)
    (herald_dir / "notices-index.json").write_text(
        json.dumps(
            {
                "notices": {
                    "auth-api-v1": {
                        "type": "deprecation",
                        "component": "auth-api-v1",
                        "what": "deprecated",
                        "why": "superseded",
                        "migration": "swap it",
                        "deadline": None,
                        "reason_link": None,
                        "status": "published",
                        "path": "notices/2026-08/deprecation/auth-api-v1.md",
                        "created_at": "2026-08-01T00:00:00+00:00",
                        "published_at": "2026-08-01T00:00:00+00:00",
                        "closed_at": None,
                        "closed_by": None,
                        "close_reason": None,
                        "revisions": [],
                    }
                },
                "redirects": {"old-name": "auth-api-v1"},
            }
        ),
        encoding="utf-8",
    )
    db_path = herald_dir / "herald.db"
    found = notices.get_notice(herald_dir.parent, "auth-api-v1", index_path=db_path)
    assert found.component == "auth-api-v1"
    resolved = notices.get_notice(herald_dir.parent, "old-name", index_path=db_path)
    assert resolved.component == "auth-api-v1"
    assert (herald_dir / "notices-index.json").exists()


def test_all_three_legacy_files_import_together(tmp_path):
    """The Edge-Case Matrix's "Legacy import" row: all three files present,
    no ``herald.db`` yet -- the first migration imports every record from
    every one of them, once."""
    herald_dir = tmp_path / ".herald"
    herald_dir.mkdir(parents=True)
    (herald_dir / "progress.json").write_text(
        json.dumps(
            [
                {
                    "id": "p1",
                    "station": "warden",
                    "date": "2026-08-08",
                    "shipped_capabilities": [],
                    "compute_hours": 0,
                    "token_spend": 0,
                    "wall_clock_hours": 0,
                    "unblock_narrative": "",
                    "created_at": "t",
                    "updated_at": "t",
                }
            ]
        )
    )
    (herald_dir / "claims.json").write_text(
        json.dumps(
            [
                {
                    "id": "c1",
                    "project_name": "warden",
                    "status": "draft",
                    "thesis": None,
                    "shipped_date": None,
                    "created_at": "t",
                    "published_at": None,
                    "closed_at": None,
                    "updated_at": "t",
                    "evidence": [],
                    "edit_history": [],
                }
            ]
        )
    )
    (herald_dir / "notices-index.json").write_text(
        json.dumps({"notices": {}, "redirects": {}})
    )
    db_path = herald_dir / "herald.db"
    assert len(progress.read_all(db_path)) == 1
    assert len(claims.read_all(db_path)) == 1
    assert notices.list_notices(herald_dir.parent, index_path=db_path, status="all") == []


def test_legacy_import_is_a_noop_when_no_legacy_files_exist(tmp_path):
    db_path = tmp_path / ".herald" / "herald.db"
    assert progress.read_all(db_path) == []
    assert claims.read_all(db_path) == []


def test_legacy_corrupt_progress_json_fails_migration_structurally(tmp_path):
    """A legacy file that fails today's own validation must fail migration
    the same way (``errors.HeraldError``), never silently dropped."""
    herald_dir = tmp_path / ".herald"
    herald_dir.mkdir(parents=True)
    (herald_dir / "progress.json").write_text("{not valid json", encoding="utf-8")
    db_path = herald_dir / "herald.db"

    with pytest.raises(HeraldError, match="progress.json"):
        progress.read_all(db_path)


def test_legacy_progress_json_non_list_top_level_fails_migration_structurally(tmp_path):
    """``_load_legacy_document``'s "non-list top-level document" check is
    reachable only through the migration import path now (the live read
    path is ``read_all``, through ``db.py``) -- exercise it there."""
    herald_dir = tmp_path / ".herald"
    herald_dir.mkdir(parents=True)
    (herald_dir / "progress.json").write_text("{}", encoding="utf-8")
    db_path = herald_dir / "herald.db"

    with pytest.raises(HeraldError, match="does not hold a JSON array"):
        progress.read_all(db_path)


def test_legacy_claims_json_unknown_field_fails_migration_structurally(tmp_path):
    """``_claim_from_dict``'s "unknown field" check is reachable only
    through the migration import path now -- exercise it there."""
    herald_dir = tmp_path / ".herald"
    herald_dir.mkdir(parents=True)
    (herald_dir / "claims.json").write_text(
        json.dumps(
            [
                {
                    "id": "c1",
                    "project_name": "warden",
                    "status": "draft",
                    "thesis": None,
                    "shipped_date": None,
                    "created_at": "t",
                    "published_at": None,
                    "closed_at": None,
                    "updated_at": "t",
                    "evidence": [],
                    "edit_history": [],
                    "bogus_field": "oops",
                }
            ]
        ),
        encoding="utf-8",
    )
    db_path = herald_dir / "herald.db"

    with pytest.raises(HeraldError, match="unknown field"):
        claims.read_all(db_path)


def test_legacy_import_failure_leaves_nothing_partially_imported(tmp_path):
    """The whole migration (schema creation + every file's import) runs in
    one transaction: a corrupt legacy file rolls the entire attempt back,
    so a subsequent call retries from scratch rather than seeing a
    half-migrated database."""
    herald_dir = tmp_path / ".herald"
    herald_dir.mkdir(parents=True)
    (herald_dir / "claims.json").write_text(
        json.dumps(
            [
                {
                    "id": "c1",
                    "project_name": "warden",
                    "status": "draft",
                    "thesis": None,
                    "shipped_date": None,
                    "created_at": "t",
                    "published_at": None,
                    "closed_at": None,
                    "updated_at": "t",
                    "evidence": [],
                    "edit_history": [],
                }
            ]
        )
    )
    (herald_dir / "notices-index.json").write_text("not valid json at all")
    db_path = herald_dir / "herald.db"

    with pytest.raises(HeraldError):
        progress.read_all(db_path)

    raw = sqlite3.connect(db_path)
    version = raw.execute("PRAGMA user_version").fetchone()[0]
    tables = {
        row[0]
        for row in raw.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    raw.close()
    assert version == 0
    assert "claims" not in tables, "the claims half of a rolled-back migration must not persist"

    # Retrying still fails the same way, and still imports nothing.
    with pytest.raises(HeraldError):
        claims.read_all(db_path)


# --- reentrant ambient transactions ------------------------------------------


def test_nested_transaction_calls_for_the_same_path_join_the_outer_one(tmp_path):
    """A nested ``db.transaction`` call (same thread, same path) must not
    self-deadlock -- it joins the already-open transaction instead of
    opening a second connection and contending with itself."""
    db_path = tmp_path / "herald.db"

    def _inner() -> None:
        with db.transaction(db_path) as inner_conn:
            inner_conn.execute("SELECT 1")

    with db.transaction(db_path):
        _inner()  # must return promptly, not hang


def test_connection_reuses_the_ambient_transaction_for_the_same_path(tmp_path):
    """A ``db.connection`` call from inside an open ``db.transaction`` for
    the SAME path must see that transaction's own uncommitted writes --
    the "fresh read inside the lock" shape ``claims.publish`` depends on."""
    db_path = tmp_path / "herald.db"
    with db.connection(db_path):
        pass  # ensure schema exists first

    with db.transaction(db_path) as conn:
        conn.execute(
            "INSERT INTO progress (id, station, date, shipped_capabilities, "
            "compute_hours, token_spend, wall_clock_hours, unblock_narrative, "
            "created_at, updated_at) VALUES ('x', 'warden', '2026-08-08', "
            "'[]', 0, 0, 0, '', 't', 't')"
        )
        with db.connection(db_path) as read_conn:
            count = read_conn.execute("SELECT COUNT(*) FROM progress").fetchone()[0]
        assert count == 1, "a nested connection() must see the open transaction's own write"


def test_a_second_thread_blocks_until_the_first_transaction_commits(tmp_path):
    """Cross-thread proof that ``db.transaction`` genuinely serializes
    writers, the database-level replacement for ``locking.locked``."""
    db_path = tmp_path / "herald.db"
    with db.connection(db_path):
        pass  # ensure schema exists first

    first_holds_lock = threading.Event()
    release_first = threading.Event()
    second_acquired_at: list[float] = []

    def holder() -> None:
        with db.transaction(db_path):
            first_holds_lock.set()
            release_first.wait(timeout=5)

    def contender() -> None:
        assert first_holds_lock.wait(timeout=5)
        with db.transaction(db_path):
            second_acquired_at.append(1)

    t1 = threading.Thread(target=holder)
    t2 = threading.Thread(target=contender)
    t1.start()
    t1_ready = first_holds_lock.wait(timeout=5)
    assert t1_ready
    t2.start()
    time.sleep(0.2)
    assert not second_acquired_at, "the second writer must not proceed while the first holds the lock"
    release_first.set()
    t1.join(timeout=5)
    t2.join(timeout=5)
    assert second_acquired_at == [1]
