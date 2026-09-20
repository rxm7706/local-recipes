"""Shared SQLite storage for ``progress.py``/``claims.py``/``notices.py``
(Story 13.3, closing Epic 13's LB-1). One database file --
``.herald/herald.db`` -- carries all three schemas; ``state.py`` keeps its
own ``.herald/bridge-state.json`` + ``locking.py`` unchanged (out of this
story's Surface).

This module owns everything storage-adjacent that used to be
``locking.py``'s job for these three modules: opening a connection (WAL
journal mode, a generous ``busy_timeout`` so concurrent writers
block-and-serialize instead of raising "database is locked"), a
version-tracked migration runner (embedded SQL, not separate ``.sql``
files -- avoids a hatchling packaging-data risk with no in-repo precedent),
a one-time legacy-JSON import, and the ``transaction``/``connection``
context managers that replace ``locking.locked`` as the concurrency
primitive.

**Reentrant, ambient transactions.** ``progress.py``/``claims.py``/
``notices.py`` each keep the exact call shape Story 13.1 established:
a public read function (``read_all``, ...) is called BOTH standalone (a
plain lookup, or a test seeding state directly) AND from inside a write
function's own critical section (the "fresh read" that follows an
unlocked evidence-validation window in ``claims.publish``/``revalidate``/
``revalidate_all``). Threading an explicit ``sqlite3.Connection`` through
every call would change every one of those signatures and break the
existing ``monkeypatch.setattr(claims, "read_all", ...)``-based
concurrency tests, which replace the whole public symbol with a
single-``path``-argument wrapper. Instead, ``transaction()`` tracks the
current thread's open transaction (path -> connection) on a
``threading.local`` stack: a call for the SAME ``db_path`` from the SAME
thread while a transaction is already open silently joins it (no nested
``BEGIN``, no second commit) instead of opening a second connection and
self-deadlocking against the first. A call from a DIFFERENT thread for the
same path is a genuinely different writer and blocks on SQLite's own
``BEGIN IMMEDIATE`` -- exactly Story 13.1's "second writer blocks until
the first releases" contract, now enforced by the database instead of an
advisory file lock.

``connection()`` is the read-side twin: ambient-aware the same way, but
when opening a FRESH connection (no ambient transaction for this path) it
never issues ``BEGIN IMMEDIATE`` -- a standalone read must never contend
with a concurrent writer (WAL's whole point: readers see a consistent
snapshot without blocking, and never block a writer either).
"""

from __future__ import annotations

import contextlib
import sqlite3
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path

from . import errors

DEFAULT_DB_PATH = Path(".herald/herald.db")
"""Mirrors ``state.DEFAULT_STATE_PATH``'s convention: relative to a repo
root the caller resolves. Shared by all three modules -- see the module
docstring's "one shared database" framing."""

_BUSY_TIMEOUT_MS = 30_000
"""Generous enough that a normal write (a handful of small statements)
never times out waiting for a concurrent writer to release the lock, per
this story's "never raise 'database is locked'" requirement. Not
unbounded: an operator killing a process mid-write still releases the
lock immediately (SQLite's own transaction rollback-on-disconnect), so
there is no hang-forever failure mode to avoid the way ``locking.py``'s
"no timeout at all" choice had to."""

_LEGACY_FILENAMES = ("progress.json", "claims.json", "notices-index.json")
"""The pre-Story-13.3 per-module JSON stores ``_import_legacy_v1`` adopts,
named relative to ``db_path.parent``. Also what ``connection()`` consults
to decide whether a read against a not-yet-existing database has anything
to migrate."""

_local = threading.local()


def _stack() -> list[tuple[str, sqlite3.Connection]]:
    # Not `getattr(_local, "stack", None)`: bridge-core (this module
    # included, per test_bridge.py's AST sweep) may never name dynamic
    # attribute-access machinery at all, since a static check cannot see
    # what it reaches at runtime -- `try`/`except AttributeError` is the
    # equivalent lazy-init idiom without naming `getattr`.
    try:
        return _local.stack
    except AttributeError:
        _local.stack = []
        return _local.stack


def _ambient(key: str) -> sqlite3.Connection | None:
    for path, conn in reversed(_stack()):
        if path == key:
            return conn
    return None


def _is_busy(exc: sqlite3.OperationalError) -> bool:
    """Whether ``exc`` is the transient contention signature ``SQLITE_BUSY``
    -- the only failure ``_set_wal_mode``'s retry loop can ever resolve by
    waiting. Matched on the message because ``sqlite3.OperationalError``
    carries no distinguishing subclass or numeric code across the versions
    this package supports (``sqlite3_errorcode``/``sqlite3_errorname`` are
    3.11+ only, and the same text is what every SQLite build emits)."""
    text = str(exc).lower()
    return "locked" in text or "busy" in text


def _set_wal_mode(conn: sqlite3.Connection) -> None:
    """Switch ``conn`` into WAL journal mode, retrying past the one gap
    ``busy_timeout`` does not cover: converting a database's journal mode
    (unlike an ordinary read or write) requires momentarily exclusive
    access to the whole file, and SQLite returns ``SQLITE_BUSY``
    immediately -- without invoking the busy handler's retry loop -- when
    another connection merely has the file open, even one taking no lock
    at all. This only ever bites the very first connection(s) racing to
    open a brand new database file (WAL, once set, is persisted in the
    file header, so every later connection's own attempt is an instant
    no-op); a short bounded retry loop here closes that startup race the
    same way ``locking._acquire`` retries past ``msvcrt.locking``'s ~10s
    internal timeout on Windows -- the underlying primitive does not honor
    an indefinite wait on its own, so this module does.

    Only ``SQLITE_BUSY`` is retried. Waiting cannot resolve any other
    ``OperationalError`` here, and retrying one regardless burned the full
    ``_BUSY_TIMEOUT_MS`` before failing: a read-only ``herald.db`` (whose
    journal-mode switch is a write, so it raises "attempt to write a
    readonly database" on every attempt) stalled each command for a
    measured 30.00s, as did a filesystem without the shared-memory support
    WAL needs (NFS and friends, which fail with "unable to open database
    file" on every connection, not just the first). Those now surface
    immediately."""
    deadline = time.monotonic() + _BUSY_TIMEOUT_MS / 1000
    while True:
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            return
        except sqlite3.OperationalError as exc:
            if not _is_busy(exc) or time.monotonic() >= deadline:
                raise
            time.sleep(0.02)


def _connect(db_path: Path) -> sqlite3.Connection:
    """Open a connection to ``db_path``, ensuring its parent directory and
    schema exist -- every caller (read or write, standalone or ambient)
    goes through this, so nothing separately worries about "has the
    database been created yet."

    ``isolation_level=None`` puts the connection in autocommit mode: no
    implicit ``BEGIN`` before a statement, so ``transaction()`` has full
    control over exactly when a write transaction (``BEGIN IMMEDIATE``)
    opens, and ``connection()``'s standalone reads never accidentally start
    one either."""
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path, timeout=_BUSY_TIMEOUT_MS / 1000, isolation_level=None)
    except (OSError, sqlite3.OperationalError) as exc:
        raise errors.HeraldError(f"{db_path} could not be opened: {exc}") from exc
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(f"PRAGMA busy_timeout = {_BUSY_TIMEOUT_MS}")
        _set_wal_mode(conn)
        conn.execute("PRAGMA foreign_keys = ON")
        _ensure_schema(conn, db_path)
    except sqlite3.OperationalError as exc:
        conn.close()
        raise errors.HeraldError(f"{db_path} could not be opened: {exc}") from exc
    except sqlite3.IntegrityError as exc:
        # Checked BEFORE `sqlite3.DatabaseError` below -- `IntegrityError`
        # is one of its subclasses, and this is a distinct failure: a
        # `UNIQUE`/`NOT NULL`/etc. violation in data the migration is
        # importing (e.g. two legacy `progress.json` records sharing the
        # `(station, date)` key the schema now enforces), not a corrupt
        # database file.
        conn.close()
        raise errors.HeraldError(f"{db_path}: legacy data could not be imported: {exc}") from exc
    except sqlite3.DatabaseError as exc:
        conn.close()
        raise errors.HeraldError(f"{db_path} is not a valid database: {exc}") from exc
    except BaseException:
        conn.close()
        raise
    return conn


def _has_legacy_data(db_path: Path, *names: str) -> bool:
    """Whether any of ``names`` (default: every pre-Story-13.3 JSON store)
    sits next to ``db_path``, i.e. whether a first connection here would
    have a legacy import to run.

    Uses ``_is_definitely_absent`` rather than ``exists()`` for the reason
    that helper spells out: a legacy file that is merely un-``stat``-able
    is not an absent one, and reading it as absent split the read and write
    answers apart. Verified: with an un-``stat``-able ``progress.json``
    beside a not-yet-created database, ``read_all`` was served from the
    empty in-memory database and returned ``[]``, while a write on the same
    store correctly reported that the legacy file could not be read."""
    return any(not _is_definitely_absent(db_path.parent / name) for name in (names or _LEGACY_FILENAMES))


def _is_definitely_absent(db_path: Path) -> bool:
    """Whether ``db_path`` is DEFINITIVELY not there, as opposed to merely
    un-``stat``-able.

    Deliberately NOT ``db_path.exists()``, for the reason
    ``notices._require_existing_index`` and ``state.read`` both spell out:
    ``Path.exists`` returns ``False`` whenever the stat fails for ANY
    reason (an unsearchable parent, a symlink loop, EACCES, EIO), so a
    database that exists but cannot be read would be indistinguishable
    from one that was never created. Routed through ``exists()``, every
    read of such a store was served from the empty in-memory database
    below and returned ``[]``/"not found" -- and since all three exporter
    scripts are pure readers, a transient permissions fault silently
    rewrote healthy ``web/public/*.json`` snapshots to ``[]`` with exit
    code 0, while the write path on the identical store correctly raised.
    Only a definitively absent path (or a non-directory parent component)
    reads as empty now; every other stat failure falls through to
    ``_connect``, whose own error handling reports the real fault."""
    try:
        db_path.stat()
    except FileNotFoundError, NotADirectoryError:
        return True
    except OSError:
        return False
    return False


def _empty_read_connection(db_path: Path) -> sqlite3.Connection:
    """A throwaway in-memory database carrying the current schema and no
    rows -- what ``connection()`` hands a read of a store that does not
    exist yet.

    Going through ``_connect`` instead would create the database file (and
    its parent directory, and WAL's ``-wal``/``-shm`` sidecars) as a side
    effect of a pure read, which is both a behavior change from the
    pre-13.3 JSON modules (``read_all`` on a missing file returned ``[]``
    and touched nothing) and a visible one: the repo's ``.gitignore`` entry
    is the root-anchored ``/.herald/``, deliberately so a tracked
    ``.herald/`` test fixture deeper in the tree keeps working, so any
    ``herald`` read run from a SUBDIRECTORY left an untracked
    ``<subdir>/.herald/herald.db`` behind in ``git status``. The three
    exporter scripts and every ``--list``-shaped command hit this path.

    The schema comes from ``_SCHEMA_MIGRATIONS`` -- the same ordered set
    of structural steps every on-disk database is built from -- rather than
    a second, hand-kept copy of the v1 SQL. Applying that SQL directly and
    then stamping ``user_version = SCHEMA_VERSION`` claimed to be current
    while being pinned to v1: the first migration added after this story
    would have given an on-disk store the v2 shape and this one the v1
    shape, both stamped v2, so every read of a not-yet-existing store
    (fresh repo, all three exporters, every ``--list``-shaped command)
    would fail against columns the rest of the code had every reason to
    expect.

    Only the STRUCTURAL half runs here, never ``_ensure_schema``/
    ``_import_legacy_v1``. This connection is a throwaway that must not
    touch the filesystem at all: routing it through the full migration
    runner made a pure read of a not-yet-existing store attempt the legacy
    JSON import, which is both pointless (``connection()`` only takes this
    path when ``_has_legacy_data`` is false) and wrong under exactly the
    stat failure ``_is_definitely_absent`` exists to catch."""
    conn = sqlite3.connect(":memory:", isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        for _version, apply_schema in _SCHEMA_MIGRATIONS:
            apply_schema(conn)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    except BaseException:
        conn.close()
        raise
    return conn


@contextlib.contextmanager
def connection(db_path: Path) -> Iterator[sqlite3.Connection]:
    """A connection for reading ``db_path`` -- the ambient transaction's
    connection when called from inside one for the SAME path (so a read
    taken mid-write sees that write's own uncommitted rows), otherwise a
    short-lived standalone connection that never takes a write lock (see
    module docstring).

    A read of a store that does not exist yet (and has no legacy JSON
    beside it to migrate) is served from an empty in-memory database --
    reads stay side-effect-free, see ``_empty_read_connection``.

    A failure raised while reading is wrapped in ``errors.HeraldError``
    here, at the seam, so the read functions match the write functions'
    existing AD-6 contract without repeating the same ``try``/``except`` in
    all six of them. ``cli.dispatch`` catches only ``HeraldError``; an
    unwrapped one exited as a traceback instead of the "message plus exit
    code 1" this story's own rewritten runbooks promise.

    The caught set is deliberately the write paths' set, not just
    ``sqlite3.Error``: binding a parameter is where SQLite converts Python
    values, and it raises the same non-``sqlite3`` types there that
    ``progress``/``claims``/``notices``'s writers already catch. Verified
    through the real CLI: ``herald success review $'\\xff'`` -- a non-UTF-8
    argv byte, which ``surrogateescape`` hands on as a lone surrogate --
    reached ``read_one``'s ``WHERE id = ?`` and exited as a raw
    ``UnicodeEncodeError`` traceback, the exact failure the write half was
    already fixed for."""
    key = str(Path(db_path).resolve())
    ambient = _ambient(key)
    if ambient is not None:
        # Inside a transaction: that writer's own wrapper owns error
        # translation for the whole critical section, including this read.
        yield ambient
        return
    if _is_definitely_absent(db_path) and not _has_legacy_data(db_path):
        conn = _empty_read_connection(db_path)
    else:
        conn = _connect(db_path)
    try:
        yield conn
    except (sqlite3.Error, TypeError, ValueError, RecursionError) as exc:
        raise errors.HeraldError(f"{db_path} could not be read: {exc}") from exc
    finally:
        conn.close()


@contextlib.contextmanager
def transaction(db_path: Path) -> Iterator[sqlite3.Connection]:
    """The write-side "lock" replacing ``locking.locked`` for
    progress/claims/notices: ``BEGIN IMMEDIATE`` takes SQLite's own write
    lock for the ``with`` block's span, committing on normal exit and
    rolling back on any exception -- so a caller's whole
    read-modify-write happens atomically, the same guarantee
    ``locking.locked`` gave via an OS advisory lock.

    Reentrant per (thread, path) -- see the module docstring's "ambient
    transactions" section. A nested call for the SAME path on the SAME
    thread joins the already-open transaction and does not itself commit,
    roll back, or close the connection; only the outermost call that
    actually opened it does."""
    key = str(Path(db_path).resolve())
    ambient = _ambient(key)
    if ambient is not None:
        yield ambient
        return
    conn = _connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
    except sqlite3.OperationalError as exc:
        conn.close()
        raise errors.HeraldError(f"{db_path} could not be opened: {exc}") from exc
    except sqlite3.DatabaseError as exc:
        conn.close()
        raise errors.HeraldError(f"{db_path} is not a valid database: {exc}") from exc
    stack = _stack()
    entry = (key, conn)
    stack.append(entry)
    try:
        try:
            yield conn
        except BaseException:
            # Suppressed: a rollback failure here would replace the
            # exception that actually caused the abort with a far less
            # useful one, and the connection is closed either way below --
            # which rolls back any still-open transaction on its own.
            with contextlib.suppress(sqlite3.Error):
                conn.rollback()
            raise
        else:
            try:
                conn.commit()
            except sqlite3.Error as exc:
                raise errors.HeraldError(f"{db_path} could not be written: {exc}") from exc
    finally:
        # Remove THIS frame's own entry, not whatever is on top: an
        # out-of-LIFO exit (an `ExitStack` holding transactions for two
        # different paths, a generator-based helper) would otherwise
        # deregister a different path's still-open transaction, leaving a
        # closed connection registered as ambient for it. Every call site
        # today nests with plain `with` statements, so this is latent --
        # and costs nothing to close off.
        for index in range(len(stack) - 1, -1, -1):
            if stack[index] is entry:
                del stack[index]
                break
        conn.close()


# --- schema + migrations ----------------------------------------------------

# `claims.id` is deliberately NOT a PRIMARY KEY/UNIQUE column below, unlike
# `progress.id` and `notices_index.component`: uniqueness there is an
# application-level concern (`claims._require_unique_ids`, Story 13.1
# pass-4), not a schema-level one, matching the pre-Story-13.3 JSON array's
# own semantics -- nothing prevented two array entries sharing an id; only
# `revalidate_all`'s own guard refused to operate on such a file. A schema
# constraint here would make that guard unreachable (the write that creates
# the duplicate would fail first, with a raw SQL message instead of
# `claims`'s own "duplicate claim ids" one) and silently change a
# documented, tested behavior.
#
# `IF NOT EXISTS` on every table: `user_version` and the tables themselves
# can legitimately disagree, and without it that state is unrecoverable.
# `sqlite3 .dump` does NOT emit `PRAGMA user_version`, so a database
# restored from a logical dump -- which is what an operator following the
# "restore `.herald/herald.db` from a backup" advice in `cli-runbooks.md`
# and `automation-troubleshooting.md` may well have -- comes back with all
# four tables populated and `user_version = 0`. `_ensure_schema` then reran
# this migration and failed on `table progress already exists`, permanently:
# every subsequent command raised the same error, with no repair path and a
# message pointing at nothing an operator could act on. Verified before and
# after. Re-running the migration over already-present tables is now a
# no-op, and `_import_legacy_v1` skips any store whose table already holds
# rows, so the import half is a no-op on that path too -- see its own
# docstring for why "the PRIMARY KEY would catch a re-import" was not
# enough.
_SCHEMA_V1_SQL = """
CREATE TABLE IF NOT EXISTS progress (
  id TEXT PRIMARY KEY,
  station TEXT NOT NULL,
  date TEXT NOT NULL,
  shipped_capabilities TEXT NOT NULL,
  compute_hours REAL NOT NULL,
  token_spend INTEGER NOT NULL,
  wall_clock_hours REAL NOT NULL,
  unblock_narrative TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(station, date)
) STRICT;

CREATE TABLE IF NOT EXISTS claims (
  id TEXT NOT NULL,
  project_name TEXT NOT NULL,
  status TEXT NOT NULL,
  thesis TEXT,
  shipped_date TEXT,
  created_at TEXT NOT NULL,
  published_at TEXT,
  closed_at TEXT,
  updated_at TEXT NOT NULL,
  evidence TEXT NOT NULL,
  edit_history TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS notices_index (
  component TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  what TEXT NOT NULL,
  why TEXT NOT NULL,
  migration TEXT NOT NULL,
  deadline TEXT,
  reason_link TEXT,
  status TEXT NOT NULL,
  path TEXT NOT NULL,
  created_at TEXT NOT NULL,
  published_at TEXT,
  closed_at TEXT,
  closed_by TEXT,
  close_reason TEXT,
  revisions TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS notices_redirects (
  old_component TEXT PRIMARY KEY,
  new_component TEXT NOT NULL
) STRICT;
"""


def _import_legacy_v1(conn: sqlite3.Connection, db_path: Path) -> None:
    """The first migration's data half: import any pre-existing
    ``.herald/{progress,claims,notices-index}.json`` sitting next to
    ``db_path``, once. Deferred imports (not module-level) to avoid a
    circular import -- ``progress``/``claims``/``notices`` each import
    ``db`` at module scope, so ``db`` importing them back at module scope
    would deadlock the import machinery; a function-local import has no
    such problem since by the time this runs, every module involved has
    already finished loading.

    Reuses each module's OWN legacy-JSON reader/validator
    (``_read_legacy_json``/``_read_legacy_index_document`` -- the exact
    ``read_all``/``_load_index_document`` bodies this story replaces), so a
    legacy file that fails today's validation raises the identical
    ``errors.HeraldError`` here, inside the SAME transaction as the schema
    creation above -- a validation failure partway through rolls back the
    whole migration (nothing partially imported), and the next call retries
    from scratch against the still-broken file until an operator fixes or
    removes it.

    Each store is skipped when its destination table already holds rows,
    which is what makes "once" true on the one path that can legitimately
    run this migration over populated tables: a database restored from
    `sqlite3 .dump` (see the `IF NOT EXISTS` note above) comes back with
    every table full and `user_version = 0`, so the whole v1 step reruns.
    Relying on the tables' own `PRIMARY KEY`s to catch that -- the previous
    reasoning -- covers `progress`/`notices_index`/`notices_redirects` but
    NOT `claims`, whose `id` is deliberately not a key (see the schema
    comment above). Verified: restoring such a dump beside a legacy
    `claims.json` silently re-imported every claim a second time, after
    which `revalidate_all` refused permanently with "holds duplicate claim
    ids" and no repair tool. An emptiness check is also the more accurate
    reading of "imports ... once, idempotently": a re-run is a no-op rather
    than an `IntegrityError` an operator has to interpret."""
    from . import claims as claims_mod
    from . import notices as notices_mod
    from . import progress as progress_mod

    def already_populated(*tables: str) -> bool:
        return any(conn.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone() is not None for table in tables)

    legacy_dir = db_path.parent

    def legacy(name: str) -> Path | None:
        """``name``'s legacy file, or ``None`` when that name IS the
        database being migrated.

        ``.herald/progress.json``/``claims.json``/``notices-index.json``
        were these modules' DOCUMENTED default paths one commit ago, and
        every public function still accepts an explicit path, so a caller
        or script that hard-coded one now hands it here as ``db_path``.
        Without this guard SQLite created the database at that name and
        the import below then tried to ``json.load`` the file it had just
        created -- failing permanently, and reporting it as a UTF-8 decode
        error on a "claims file", which points nowhere near the cause."""
        candidate = legacy_dir / name
        if candidate.resolve() == db_path.resolve():
            return None
        return candidate

    progress_file, claims_file, notices_file = (legacy(name) for name in _LEGACY_FILENAMES)

    if progress_file is not None and not already_populated("progress"):
        for record in progress_mod._read_legacy_json(progress_file):
            conn.execute(
                "INSERT INTO progress (id, station, date, shipped_capabilities, "
                "compute_hours, token_spend, wall_clock_hours, unblock_narrative, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                progress_mod._to_params(record),
            )

    if claims_file is not None and not already_populated("claims"):
        for claim in claims_mod._read_legacy_json(claims_file):
            conn.execute(
                "INSERT INTO claims (id, project_name, status, thesis, shipped_date, "
                "created_at, published_at, closed_at, updated_at, evidence, "
                "edit_history) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                claims_mod._to_params(claim),
            )

    # Both notices tables come from the one legacy index document, so
    # either one already holding rows means that document was imported.
    if notices_file is None or already_populated("notices_index", "notices_redirects"):
        return
    document = notices_mod._read_legacy_index_document(notices_file)
    for entry in document["notices"].values():
        notice = notices_mod._entry_to_notice(entry)
        conn.execute(
            "INSERT INTO notices_index (component, type, what, why, migration, "
            "deadline, reason_link, status, path, created_at, published_at, "
            "closed_at, closed_by, close_reason, revisions) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            notices_mod._to_params(notice),
        )
    for old, new in document["redirects"].items():
        conn.execute(
            "INSERT INTO notices_redirects (old_component, new_component) VALUES (?, ?)",
            (old, new),
        )


def _schema_v1(conn: sqlite3.Connection) -> None:
    """v1's STRUCTURAL half, with no data migration and no filesystem
    access -- separated from ``_migrate_v1`` so ``_empty_read_connection``
    can build the current shape without also running the legacy import.

    `Connection.executescript` implicitly COMMITs any pending transaction
    before running -- exactly the `BEGIN IMMEDIATE` this migration must
    stay inside of, so the schema creation and the legacy import roll back
    together on failure. Each statement is run individually through the
    ordinary `execute`, which does not touch the open transaction.

    Split on a bare `;` (not `;\\n\\n`) so this survives any reformatting of
    `_SCHEMA_V1_SQL` -- the blank-line-separated shape is incidental to how
    the statements are written, not a delimiter this should depend on.
    """
    for statement in _SCHEMA_V1_SQL.split(";"):
        statement = statement.strip()
        if statement:
            conn.execute(statement)


def _migrate_v1(conn: sqlite3.Connection, db_path: Path) -> None:
    _schema_v1(conn)
    _import_legacy_v1(conn, db_path)


_SCHEMA_MIGRATIONS: tuple[tuple[int, Callable[[sqlite3.Connection], None]], ...] = ((1, _schema_v1),)
"""Structure only, in version order -- what a database's shape is built
from when there is no data to migrate. Every entry here must have a
matching version in ``_MIGRATIONS`` below; ``_MIGRATIONS`` is the full
step (structure plus whatever data work that version needs)."""

_MIGRATIONS: tuple[tuple[int, Callable[[sqlite3.Connection, Path], None]], ...] = ((1, _migrate_v1),)

SCHEMA_VERSION = _MIGRATIONS[-1][0]
"""The highest ``user_version`` this build knows how to produce or read.
``_ensure_schema`` HALTs rather than guesses when it finds a database
stamped higher than this (Boundaries & Constraints -> Block If)."""


def _ensure_schema(conn: sqlite3.Connection, db_path: Path) -> None:
    """Bring ``db_path`` to ``SCHEMA_VERSION``, or HALT if it is already
    stamped with a version newer than this build understands.

    The cheap check (``PRAGMA user_version`` -- already at target, return
    immediately) runs unlocked, so a connection that finds the schema
    current -- the overwhelming majority of calls, standalone reads
    included -- never takes a write lock at all. Only a database that
    actually needs migrating pays for ``BEGIN IMMEDIATE``, and re-checks
    the version once inside it (a concurrent migrator may have already
    finished while this connection waited for the lock)."""
    try:
        current = conn.execute("PRAGMA user_version").fetchone()[0]
    except sqlite3.DatabaseError as exc:
        raise errors.HeraldError(f"{db_path} is not a valid database: {exc}") from exc
    if current > SCHEMA_VERSION:
        raise errors.HeraldError(
            f"{db_path} has user_version={current}, newer than this build's "
            f"latest known migration ({SCHEMA_VERSION}); refusing to overwrite "
            f"or downgrade it -- upgrade herald, or point at a different database"
        )
    if current == SCHEMA_VERSION:
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        current = conn.execute("PRAGMA user_version").fetchone()[0]
        if current > SCHEMA_VERSION:
            raise errors.HeraldError(
                f"{db_path} has user_version={current}, newer than this build's "
                f"latest known migration ({SCHEMA_VERSION}); refusing to "
                f"overwrite or downgrade it -- upgrade herald, or point at a "
                f"different database"
            )
        for version, migrate in _MIGRATIONS:
            if version <= current:
                continue
            migrate(conn, db_path)
            conn.execute(f"PRAGMA user_version = {version}")
    except BaseException:
        conn.rollback()
        raise
    else:
        conn.commit()
