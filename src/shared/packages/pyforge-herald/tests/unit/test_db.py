"""``db.py``'s connection setup, migration runner, transaction/connection
context managers, and one-time legacy-JSON import (Story 13.3).

Every case uses an explicit ``tmp_path``-derived ``db_path`` -- ``db.py``
never assumes a cwd, mirroring every other storage module's own
convention."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time

import pytest

from pyforge.herald import claims, db, notices, progress
from pyforge.herald.errors import HeraldError

# --- connection setup: WAL + busy_timeout -----------------------------------


def test_fresh_connection_is_wal_mode(tmp_path):
    db_path = tmp_path / "herald.db"
    # Through `transaction`, not `connection`: a read of a store that does
    # not exist yet is served from an empty in-memory database (whose
    # journal mode is "memory", not "wal") precisely so it creates nothing.
    with db.transaction(db_path) as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"
    # And every later read of the now-existing file is a real WAL connection.
    with db.connection(db_path) as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"


def test_fresh_connection_has_the_generous_busy_timeout(tmp_path):
    db_path = tmp_path / "herald.db"
    with db.transaction(db_path) as conn:
        timeout_ms = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    assert timeout_ms == db._BUSY_TIMEOUT_MS
    with db.connection(db_path) as conn:
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == db._BUSY_TIMEOUT_MS


def test_first_write_creates_the_database_file_and_parent_dir(tmp_path):
    db_path = tmp_path / "nested" / "dir" / "herald.db"
    with db.transaction(db_path):
        pass
    assert db_path.exists()


def test_a_read_of_a_store_that_does_not_exist_creates_nothing(tmp_path):
    """The I/O matrix's "first WRITE creates `.herald/herald.db`" row, held
    from the other side: a pure read must leave the filesystem untouched,
    as the pre-13.3 JSON modules did (`read_all` on a missing file returned
    `[]` and created nothing).

    Not cosmetic. The repo's `.gitignore` entry is the root-anchored
    `/.herald/` -- deliberately, so a tracked `.herald/` fixture deeper in
    the tree keeps working -- so a read run from any SUBDIRECTORY left an
    untracked `<subdir>/.herald/herald.db` (plus WAL's `-wal`/`-shm`
    sidecars) sitting in `git status`. Every `--list`-shaped command and
    all three exporter scripts take this path."""
    db_path = tmp_path / "nested" / "dir" / "herald.db"
    with db.connection(db_path) as conn:
        assert conn.execute("SELECT count(*) FROM progress").fetchone()[0] == 0
    assert not db_path.exists()
    assert not db_path.parent.exists()
    assert list(tmp_path.iterdir()) == []


def test_a_read_still_migrates_when_legacy_json_is_present(tmp_path):
    """The side-effect-free read above must NOT suppress the legacy import:
    a store that does not exist yet but has legacy JSON beside it still has
    something to migrate, so that read goes through the real database."""
    db_path = tmp_path / "herald.db"
    (tmp_path / "progress.json").write_text(
        json.dumps(
            [
                {
                    "id": "p1",
                    "station": "herald",
                    "date": "2026-01-01",
                    "shipped_capabilities": ["a"],
                    "compute_hours": 1.0,
                    "token_spend": 2,
                    "wall_clock_hours": 3.0,
                    "unblock_narrative": "n",
                    "created_at": "t1",
                    "updated_at": "t2",
                }
            ]
        )
    )
    assert [r.id for r in progress.read_all(db_path)] == ["p1"]
    assert db_path.exists()


def test_a_read_error_is_wrapped_in_herald_error(tmp_path):
    """AD-6 parity between the read and write paths. `cli.dispatch` catches
    only `HeraldError`; a raw `sqlite3.Error` from a read exited as a
    traceback instead of the message-plus-exit-code-1 this story's own
    rewritten runbooks promise."""
    db_path = tmp_path / "herald.db"
    with db.transaction(db_path):
        pass
    raw = sqlite3.connect(db_path)
    raw.execute("DROP TABLE progress")
    raw.commit()
    raw.close()

    with pytest.raises(HeraldError) as excinfo:
        progress.read_all(db_path)
    assert "could not be read" in str(excinfo.value)
    assert "no such table" in str(excinfo.value)


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root bypasses the read-only permission this case depends on",
)
def test_a_non_busy_open_failure_is_not_retried_to_the_busy_timeout(tmp_path):
    """`_set_wal_mode` retries only SQLITE_BUSY. Retrying every
    `OperationalError` regardless burned the full `_BUSY_TIMEOUT_MS` before
    failing -- a measured 30.00s per command against a read-only
    `herald.db` (whose journal-mode switch is itself a write, so it fails
    identically on every attempt), and the same against a filesystem
    without the shared-memory support WAL needs. Neither is something
    waiting can ever resolve."""
    db_path = tmp_path / "herald.db"
    with db.transaction(db_path):
        pass

    read_only = tmp_path / "read-only"
    read_only.mkdir()
    target = read_only / "herald.db"
    target.write_bytes(db_path.read_bytes())
    target.chmod(0o444)
    read_only.chmod(0o555)
    try:
        started = time.monotonic()
        with pytest.raises(HeraldError):
            progress.read_all(target)
        elapsed = time.monotonic() - started
    finally:
        # Restored so pytest's own tmp_path cleanup can remove the tree.
        read_only.chmod(0o755)
        target.chmod(0o644)

    assert elapsed < db._BUSY_TIMEOUT_MS / 1000 / 2, (
        f"a failure waiting cannot resolve stalled for {elapsed:.2f}s; only SQLITE_BUSY may be retried"
    )


def test_wrong_typed_values_are_rejected_by_the_strict_schema(tmp_path):
    """The tables are `STRICT`, which is what makes `read_all`'s "every
    other field is a plain, typed SQL column" claim true. Without it
    SQLite's default type affinity accepts `compute_hours='lots'` from an
    out-of-band write and `read_all` hands it straight back, losing the
    per-record type validation the pre-13.3 JSON reader performed."""
    db_path = tmp_path / "herald.db"
    progress.upsert(
        db_path,
        station="herald",
        date="2026-01-01",
        shipped_capabilities=["a"],
        compute_hours=1.0,
        token_spend=2,
        wall_clock_hours=3.0,
        unblock_narrative="n",
    )
    raw = sqlite3.connect(db_path)
    try:
        with pytest.raises(sqlite3.IntegrityError, match="cannot store TEXT value"):
            raw.execute("UPDATE progress SET compute_hours = 'lots'")
    finally:
        raw.close()


def test_a_legacy_filename_used_as_the_database_path_does_not_self_import(tmp_path):
    """`.herald/claims.json` was this module's DOCUMENTED default path one
    commit ago, and every public function still accepts an explicit path.
    Passing one now made SQLite create the database at that name and the
    migration then `json.load` the file it had just created -- failing
    permanently, and reporting it as a UTF-8 decode error on a "claims
    file", which points nowhere near the cause."""
    db_path = tmp_path / "claims.json"
    claim = claims.create(db_path, project_name="proj", evidence=[])
    assert [c.id for c in claims.read_all(db_path)] == [claim.id]


def test_duplicate_station_date_in_legacy_progress_json_reports_an_import_failure(
    tmp_path,
):
    """`_connect`'s `sqlite3.IntegrityError` branch: a legacy file carrying
    two records for the same `(station, date)` key (which the JSON array
    tolerated and the new schema does not) must be named as an import
    failure, not misreported as a corrupt database file."""
    db_path = tmp_path / "herald.db"
    record = {
        "station": "herald",
        "date": "2026-01-01",
        "shipped_capabilities": [],
        "compute_hours": 1.0,
        "token_spend": 2,
        "wall_clock_hours": 3.0,
        "unblock_narrative": "n",
        "created_at": "t1",
        "updated_at": "t2",
    }
    (tmp_path / "progress.json").write_text(json.dumps([{**record, "id": "p1"}, {**record, "id": "p2"}]))

    with pytest.raises(HeraldError) as excinfo:
        progress.read_all(db_path)
    message = str(excinfo.value)
    assert "legacy data could not be imported" in message
    assert "is not a valid database" not in message


# --- migration: schema creation + versioning --------------------------------


def test_fresh_database_is_stamped_at_the_latest_schema_version(tmp_path):
    db_path = tmp_path / "herald.db"
    with db.connection(db_path) as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert version == db.SCHEMA_VERSION


def test_migration_creates_every_table(tmp_path):
    db_path = tmp_path / "herald.db"
    with db.connection(db_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}
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
    # ...and left in place is exactly why "once" has to be asserted, not
    # assumed: the file that triggered the import is still sitting there on
    # every subsequent open. A single read proves the import ran, not that
    # `user_version` gating stops it running again.
    assert [r.id for r in progress.read_all(db_path)] == ["p1"]


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
    # Second open with the legacy file still present -- see the "once"
    # comment in the progress case above.
    assert [c.id for c in claims.read_all(db_path)] == ["c1"]


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
    # Second open with the legacy file still present -- see the "once"
    # comment in the progress case above. A re-import would raise here
    # (`component` is a PRIMARY KEY), so this pins the gating, not just the
    # row count.
    assert [n.component for n in notices.list_notices(herald_dir.parent, status="all")] == ["auth-api-v1"]


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
    (herald_dir / "notices-index.json").write_text(json.dumps({"notices": {}, "redirects": {}}))
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
    tables = {row[0] for row in raw.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}
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


# --- 2026-08-13 follow-up review pass: regressions ---------------------------


def test_unreadable_store_raises_instead_of_reading_as_empty(tmp_path):
    """A store that EXISTS but cannot be ``stat``'d must not be mistaken for
    one that was never created.

    ``connection()`` gated on ``Path.exists()``, which returns ``False`` for
    any stat failure (EACCES here, but equally a symlink loop or EIO), so a
    populated database behind an unsearchable parent was served from the
    empty in-memory database: every read returned ``[]``/"not found" with no
    error, while the write path on the identical store raised correctly.
    Fails against the ``exists()`` gate.
    """
    herald_dir = tmp_path / ".herald"
    db_path = herald_dir / "herald.db"
    progress.upsert(
        db_path,
        station="warden",
        date="2026-08-13",
        shipped_capabilities=["gate"],
        compute_hours=1.0,
        token_spend=1,
        wall_clock_hours=1.0,
        unblock_narrative="none",
    )
    assert len(progress.read_all(db_path)) == 1
    os.chmod(herald_dir, 0o000)
    try:
        if os.geteuid() == 0:
            pytest.skip("root bypasses the directory permission this asserts on")
        for read in (
            lambda: progress.read_all(db_path),
            lambda: claims.read_all(db_path),
            lambda: notices.list_notices(tmp_path, status="all"),
        ):
            with pytest.raises(HeraldError):
                read()
    finally:
        os.chmod(herald_dir, 0o755)


def test_notices_mutations_import_legacy_index_before_refusing(tmp_path):
    """``publish``/``close``/``archive_rename``'s pre-transaction fail-fast
    keyed on the database file alone, so on a repo still carrying
    ``.herald/notices-index.json`` the FIRST command an operator ran decided
    the outcome: a mutation reported "no notice found" for a notice plainly
    in the legacy index, while running any read first migrated it and made
    the identical call succeed. Fails against the bare-stat fast path.
    """
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
                        "status": "draft",
                        "path": "notices/2026-08/deprecation/auth-api-v1.md",
                        "created_at": "2026-08-01T00:00:00+00:00",
                        "published_at": None,
                        "closed_at": None,
                        "closed_by": None,
                        "close_reason": None,
                        "revisions": [],
                    }
                },
                "redirects": {},
            }
        ),
        encoding="utf-8",
    )
    # No read first -- publish is the very first command against this repo.
    published = notices.publish_notice(tmp_path, "auth-api-v1")
    assert published.status == "published"


def test_logical_dump_restore_is_not_permanently_bricked(tmp_path):
    """``sqlite3 .dump`` does not emit ``PRAGMA user_version``, so a database
    restored from a logical dump -- what the runbooks' "restore from a
    backup" advice can well produce -- comes back fully populated at version
    0. ``_ensure_schema`` then reran the v1 migration and died on "table
    progress already exists", on that command and every later one, with no
    repair path. Fails against non-``IF NOT EXISTS`` schema SQL.
    """
    db_path = tmp_path / ".herald" / "herald.db"
    progress.upsert(
        db_path,
        station="warden",
        date="2026-08-13",
        shipped_capabilities=[],
        compute_hours=0.0,
        token_spend=0,
        wall_clock_hours=0.0,
        unblock_narrative="none",
    )
    source = sqlite3.connect(db_path)
    dump = "\n".join(source.iterdump())
    source.close()
    assert "user_version" not in dump  # the premise this test rests on
    for path in (db_path, tmp_path / ".herald" / "herald.db-wal", tmp_path / ".herald" / "herald.db-shm"):
        if path.exists():
            path.unlink()
    restored = sqlite3.connect(db_path)
    restored.executescript(dump)
    restored.commit()
    restored.close()

    assert [r.station for r in progress.read_all(db_path)] == ["warden"]
    # And the store is writable afterwards, not merely readable.
    progress.upsert(
        db_path,
        station="mason",
        date="2026-08-13",
        shipped_capabilities=[],
        compute_hours=0.0,
        token_spend=0,
        wall_clock_hours=0.0,
        unblock_narrative="none",
    )
    assert len(progress.read_all(db_path)) == 2


def test_claims_create_wraps_a_raw_sqlite_error(tmp_path):
    """``create``'s only read is the ambient one, which ``db.connection``
    deliberately leaves untranslated (the writer owns its critical section)
    -- and ``create`` had no wrapper of its own, making it the single writer
    that leaked a raw ``sqlite3.Error`` past the AD-6 seam to
    ``cli.dispatch``, which catches only ``HeraldError``. Fails against an
    unwrapped ``create``.
    """
    db_path = tmp_path / ".herald" / "herald.db"
    claims.create(db_path, project_name="warden")
    raw = sqlite3.connect(db_path)
    raw.execute("DROP TABLE claims")
    raw.commit()
    raw.close()
    with pytest.raises(HeraldError):
        claims.create(db_path, project_name="mason")


def test_write_paths_wrap_non_sqlite_serialization_failures(tmp_path):
    """The pre-Story-13.3 writers caught ``(OSError, TypeError, ValueError,
    RecursionError)``; the rewrite narrowed that to ``sqlite3.Error`` even
    though ``_to_params``'s ``json.dumps`` still runs inside the ``try``.
    A non-serializable value and a lone surrogate (what ``argv`` yields for
    a non-UTF-8 byte) both escaped as raw ``TypeError``/``UnicodeEncodeError``.
    Fails against a ``sqlite3.Error``-only clause.
    """
    db_path = tmp_path / ".herald" / "herald.db"
    record = progress.Progress(
        id="p1",
        station="warden",
        date="2026-08-13",
        shipped_capabilities=[object()],  # not JSON-serializable
        compute_hours=0.0,
        token_spend=0,
        wall_clock_hours=0.0,
        unblock_narrative="none",
        created_at="t",
        updated_at="t",
    )
    with pytest.raises(HeraldError):
        progress.write_all(db_path, [record])

    with pytest.raises(HeraldError):
        claims.create(db_path, project_name="proj-\udcff")


def test_empty_read_connection_follows_the_migration_set(tmp_path, monkeypatch):
    """The read-of-a-missing-store path built its schema from
    ``_SCHEMA_V1_SQL`` directly and then stamped ``SCHEMA_VERSION`` --
    claiming to be current while pinned to v1. With only one migration in
    the set the two shapes are identical, so comparing them as-is asserts
    nothing; the divergence only appears once a v2 exists. A synthetic v2
    is therefore registered here, which is exactly the state the next
    schema change puts the module in.

    Fails against a hardcoded ``_SCHEMA_V1_SQL``: the on-disk store gets
    the v2 column and the in-memory one does not, while both stamp v2.
    """

    def schema_v2(conn):
        conn.execute("ALTER TABLE progress ADD COLUMN note TEXT")

    def migrate_v2(conn, db_path):
        schema_v2(conn)

    monkeypatch.setattr(db, "_SCHEMA_MIGRATIONS", db._SCHEMA_MIGRATIONS + ((2, schema_v2),))
    monkeypatch.setattr(db, "_MIGRATIONS", db._MIGRATIONS + ((2, migrate_v2),))
    monkeypatch.setattr(db, "SCHEMA_VERSION", 2)

    def shape(conn):
        return (
            conn.execute("PRAGMA user_version").fetchone()[0],
            {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")},
            [r[1] for r in conn.execute("PRAGMA table_info(progress)")],
        )

    db_path = tmp_path / ".herald" / "herald.db"
    with db.connection(db_path) as memory_conn:
        assert not db_path.exists()  # still side-effect-free
        memory_shape = shape(memory_conn)
        # The v2 column is reachable, not merely declared.
        memory_conn.execute("SELECT note FROM progress")
    with db.transaction(db_path) as disk_conn:
        disk_shape = shape(disk_conn)

    assert memory_shape == disk_shape
    assert memory_shape[0] == 2


def test_legacy_import_is_skipped_when_the_tables_already_hold_rows(tmp_path):
    """ "Imports once" has to hold on the one path that legitimately reruns
    the v1 migration over populated tables: a database restored from
    ``sqlite3 .dump`` comes back full at ``user_version = 0``.

    The `IF NOT EXISTS` change relied on the tables' own ``PRIMARY KEY``s to
    make a re-import fail loudly, which covers three of the four tables but
    NOT ``claims``, whose ``id`` is deliberately not a key. Every claim was
    silently imported a second time, after which ``revalidate_all`` refused
    permanently with "holds duplicate claim ids" and there is no repair
    tool. Fails against an unguarded ``_import_legacy_v1``.
    """
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
                    "shipped_date": "2026-08-13",
                    "created_at": "2026-08-13T00:00:00+00:00",
                    "published_at": None,
                    "closed_at": None,
                    "updated_at": "2026-08-13T00:00:00+00:00",
                    "evidence": [],
                    "edit_history": [],
                }
            ]
        ),
        encoding="utf-8",
    )
    db_path = herald_dir / "herald.db"
    assert [c.id for c in claims.read_all(db_path)] == ["c1"]

    source = sqlite3.connect(db_path)
    dump = "\n".join(source.iterdump())
    source.close()
    for path in herald_dir.glob("herald.db*"):
        path.unlink()
    restored = sqlite3.connect(db_path)
    restored.executescript(dump)
    restored.commit()
    restored.close()
    # The legacy file is deliberately left in place by the first import, so
    # it is still sitting there for this second migration to find.
    assert (herald_dir / "claims.json").exists()

    assert [c.id for c in claims.read_all(db_path)] == ["c1"]
    # And the store is still operable, not merely un-duplicated.
    claims.revalidate_all(db_path, validate=lambda url: None)


def test_read_paths_wrap_non_sqlite_binding_failures(tmp_path):
    """The write paths were widened to the pre-13.3 exception set for a
    lone surrogate (what ``argv`` yields for a non-UTF-8 byte through
    ``surrogateescape``); the read seam was left at ``sqlite3.Error``, and
    binding a parameter is exactly where SQLite converts Python values.

    Verified through the real CLI before the fix: ``herald success review``
    with a non-UTF-8 byte reached ``read_one``'s ``WHERE id = ?`` and exited
    as a raw ``UnicodeEncodeError`` traceback, not the message-plus-exit-1
    the runbooks promise. Fails against a ``sqlite3.Error``-only clause.
    """
    db_path = tmp_path / ".herald" / "herald.db"
    claims.create(db_path, project_name="warden")
    with pytest.raises(HeraldError):
        claims.read_one(db_path, "\udcff")


def test_an_unstattable_legacy_store_is_not_read_as_absent(tmp_path):
    """``_has_legacy_data`` asked ``exists()``, which collapses every stat
    failure into "absent" -- the hazard ``_is_definitely_absent`` exists to
    catch, one helper over. A legacy file behind a symlink loop made the
    read path serve ``[]`` from the empty in-memory database while the write
    path on the same store correctly reported it could not be read. Fails
    against the ``exists()`` predicate.
    """
    herald_dir = tmp_path / ".herald"
    herald_dir.mkdir(parents=True)
    legacy = herald_dir / "progress.json"
    legacy.symlink_to(legacy)  # ELOOP: stat fails, the file is not absent
    assert legacy.exists() is False  # the premise this test rests on
    db_path = herald_dir / "herald.db"
    with pytest.raises(HeraldError):
        progress.read_all(db_path)


def test_the_two_migration_sets_carry_the_same_versions():
    """``_SCHEMA_MIGRATIONS`` (structure only, for the read of a store that
    does not exist yet) and ``_MIGRATIONS`` (structure plus data) are two
    hand-kept tuples whose agreement was stated only in a docstring.
    Registering a version in one and forgetting the other puts back exactly
    the defect ``_empty_read_connection`` was rebuilt to fix: a read served
    from a schema stamped current but shaped a version behind.
    """
    assert [version for version, _ in db._SCHEMA_MIGRATIONS] == [version for version, _ in db._MIGRATIONS]


def test_notices_fail_fast_creates_nothing_when_another_legacy_store_exists(tmp_path):
    """The notices fail-fast bypasses itself when legacy data is waiting to
    be migrated -- but it asked whether ANY of the three legacy stores
    exists, so an unrelated ``progress.json`` (a repo that used
    ``herald progress`` and never ``herald notice``) suppressed it and put
    back the ``.herald/`` tree the fast path exists to avoid creating on a
    pure error path. Fails against the unnarrowed predicate.
    """
    herald_dir = tmp_path / ".herald"
    herald_dir.mkdir(parents=True)
    (herald_dir / "progress.json").write_text("[]", encoding="utf-8")

    with pytest.raises(HeraldError):
        notices.publish_notice(tmp_path, "auth-api-v1")
    assert not (herald_dir / "herald.db").exists()


def test_claims_publish_wraps_a_raw_sqlite_error_from_its_in_transaction_read(tmp_path):
    """``create`` was wrapped on the reasoning that ``publish``/
    ``revalidate``/``revalidate_all`` take their first ``read_all`` before
    the transaction opens and are therefore covered. Their SECOND,
    in-transaction ``read_all`` is ambient -- which ``db.connection``
    deliberately leaves untranslated -- and nothing wrapped it, so a fault
    arriving during the unlocked evidence-validation window (seconds to
    minutes wide for ``revalidate_all``) reached ``cli.dispatch``, which
    catches only ``HeraldError``, as a traceback. Fails against a bare
    ``db.transaction`` in ``publish``.
    """
    db_path = tmp_path / ".herald" / "herald.db"
    claim = claims.create(
        db_path,
        project_name="warden",
        evidence=[claims.Evidence(type="metrics", url="https://example.com/1", label="m")],
    )

    def drop_the_table_mid_validation(url):
        raw = sqlite3.connect(db_path)
        raw.execute("DROP TABLE claims")
        raw.commit()
        raw.close()

    with pytest.raises(HeraldError):
        claims.publish(db_path, claim.id, thesis="t", validate=drop_the_table_mid_validation)
