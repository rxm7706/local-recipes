"""Progress record storage (Story 8.1, scaled-down Epic 8; Story 13.3
moved the backing store from a JSON file to the shared SQLite database in
``db.py``).

**Storage shape.** One row per record in ``db.py``'s shared
``.herald/herald.db`` (table ``progress``). ``shipped_capabilities`` is a
JSON array stored as a ``TEXT`` column -- no cross-record query needs it
normalized (Simplicity First), the same reasoning ``claims.py``'s
``evidence``/``edit_history`` and ``notices.py``'s ``revisions`` columns
follow. See ``docs/dreams/herald-moments-2-4-live-backend.md`` for the
full live-database shape this module's data-access seam originally
existed to swap behind without a CLI/web-tab contract change -- this story
is that swap, for progress/claims/notices' local storage (not a live
server).

**Uniqueness key.** ``(station, date)`` -- the epics doc's own Story 8.2 AC
("Creates new Progress record for today (if not exists)") implies at most
one record per station per calendar day. ``upsert`` enforces this: a second
``--update`` for the same station/day replaces the existing record in place
(bumping ``updated_at``, preserving the original ``id``/``created_at``)
rather than accumulating duplicates.

**Concurrency (Story 13.3).** ``db.transaction`` -- SQLite's own
``BEGIN IMMEDIATE``/commit -- replaces ``locking.locked`` as the mechanism
serializing this module's writers; see ``db.py``'s module docstring for the
reentrant-ambient-transaction design that lets ``read_all``/
``_write_all_unlocked`` keep the exact call shape (and therefore the exact
public signature, patchable by a test's ``monkeypatch.setattr``) Story
13.1 established. ``upsert`` operates on a single row directly (no
whole-table read-modify-write) -- a natural simplification once the store
is a real database rather than one JSON array file. ``write_all`` --
this module's other public writer -- still takes the same transaction
``upsert`` does: a caller that skipped it would race a concurrent
``upsert`` exactly as before this module had any locking at all.
``upsert`` itself calls ``_write_all_unlocked`` instead of the public
``write_all`` purely to keep the two names' original relationship; both
now resolve to the SAME ambient transaction when called from inside one
(``db.transaction`` is reentrant), so there is no self-deadlock risk to
avoid the way there was under ``locking.locked``'s non-reentrant lock.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from datetime import date as date_cls
from pathlib import Path

from . import db, errors

DEFAULT_PROGRESS_PATH = db.DEFAULT_DB_PATH
"""Mirrors ``state.DEFAULT_STATE_PATH``'s convention: relative to a repo
root the caller resolves. Redefined to ``db.DEFAULT_DB_PATH`` (rather than
removed) so every existing call site (``cli.py``'s
``progress.DEFAULT_PROGRESS_PATH``) needs zero changes -- see ``db.py``'s
module docstring on why one shared database, not per-module files."""

STATIONS: tuple[str, ...] = (
    "warden",
    "atlas",
    "marshal",
    "mason",
    "doctor",
    "scribe",
    "steward",
    "herald",
)
"""The known PyForge Guild stations -- mirrors ``web/src/components/Sidebar.jsx``'s
``STATIONS`` list. Used only to produce a helpful "did you mean" error
message (``cli.py``'s unknown-station check); an operator naming a station
outside this tuple is still free to record progress for it -- this module
never rejects an unrecognized station, only the CLI's own error message
consults the list."""

_PROGRESS_FIELDS = frozenset(
    (
        "id",
        "station",
        "date",
        "shipped_capabilities",
        "compute_hours",
        "token_spend",
        "wall_clock_hours",
        "unblock_narrative",
        "created_at",
        "updated_at",
    )
)


@dataclass(frozen=True)
class Progress:
    """One station's progress record for one date.

    ``date`` is an ISO ``YYYY-MM-DD`` string (a calendar day, not a
    timestamp -- matches the CLI's own ``--date-range`` convention).
    ``created_at``/``updated_at`` are ISO 8601 UTC datetimes."""

    id: str
    station: str
    date: str
    shipped_capabilities: list[str] = field(default_factory=list)
    compute_hours: float = 0.0
    token_spend: int = 0
    wall_clock_hours: float = 0.0
    unblock_narrative: str = ""
    created_at: str = ""
    updated_at: str = ""


def new_id() -> str:
    return uuid.uuid4().hex


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _fields_problem(record: object) -> str | None:
    if not isinstance(record, dict):
        return "entry is not a JSON object"
    unknown = sorted(set(record) - _PROGRESS_FIELDS)
    if unknown:
        return f"unknown field(s) {', '.join(map(repr, unknown))}"
    missing = sorted(_PROGRESS_FIELDS - set(record))
    if missing:
        return f"missing field(s) {', '.join(map(repr, missing))}"
    if not isinstance(record["id"], str):
        return "field 'id' must be a string"
    if not isinstance(record["station"], str):
        return "field 'station' must be a string"
    if not isinstance(record["date"], str):
        return "field 'date' must be a string"
    caps = record["shipped_capabilities"]
    if not isinstance(caps, list) or not all(isinstance(c, str) for c in caps):
        return "field 'shipped_capabilities' must be an array of strings"
    if not isinstance(record["compute_hours"], (int, float)) or isinstance(record["compute_hours"], bool):
        return "field 'compute_hours' must be a number"
    if not isinstance(record["token_spend"], int) or isinstance(record["token_spend"], bool):
        return "field 'token_spend' must be an integer"
    if not isinstance(record["wall_clock_hours"], (int, float)) or isinstance(record["wall_clock_hours"], bool):
        return "field 'wall_clock_hours' must be a number"
    if not isinstance(record["unblock_narrative"], str):
        return "field 'unblock_narrative' must be a string"
    if not isinstance(record["created_at"], str):
        return "field 'created_at' must be a string"
    if not isinstance(record["updated_at"], str):
        return "field 'updated_at' must be a string"
    return None


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Mirrors ``state._reject_duplicate_keys``: a duplicated key within one
    record's own object is a hand-edit that must fail structurally (AD-6),
    not silently last-wins. Only relevant to ``_read_legacy_json`` now --
    the DB read path has no JSON-object-key concept to duplicate."""
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError(f"duplicate key {key!r}")
        document[key] = value
    return document


def _read_legacy_json(progress_path: Path) -> list[Progress]:
    """The pre-Story-13.3 JSON-file reader, preserved verbatim for the
    one-time legacy import (``db.py``'s ``_import_legacy_v1``) -- so a
    legacy ``progress.json`` that fails this exact validation still raises
    the identical ``errors.HeraldError`` at migration time (Boundaries &
    Constraints). No longer ``read_all``'s own body; that now reads
    through ``db.py``."""
    try:
        with progress_path.open(encoding="utf-8") as fh:
            document = json.load(fh, object_pairs_hook=_reject_duplicate_keys)
    except FileNotFoundError:
        return []
    except (ValueError, OSError, RecursionError) as exc:
        raise errors.HeraldError(f"progress file {progress_path} could not be read: {exc}") from exc
    if not isinstance(document, list):
        raise errors.HeraldError(f"progress file {progress_path} does not hold a JSON array at its top level")
    records: list[Progress] = []
    for index, entry in enumerate(document):
        problem = _fields_problem(entry)
        if problem:
            raise errors.HeraldError(
                f"progress file {progress_path} has a malformed record at index {index}: {problem}"
            )
        records.append(Progress(**entry))
    return records


def _to_params(record: Progress) -> tuple[object, ...]:
    """``record`` as a positional parameter tuple matching the ``progress``
    table's column order -- shared by every INSERT (``_write_all_unlocked``,
    ``upsert``, and ``db.py``'s legacy import)."""
    return (
        record.id,
        record.station,
        record.date,
        json.dumps(record.shipped_capabilities),
        record.compute_hours,
        record.token_spend,
        record.wall_clock_hours,
        record.unblock_narrative,
        record.created_at,
        record.updated_at,
    )


def _row_to_progress(progress_path: Path, row) -> Progress:
    try:
        shipped_capabilities = json.loads(row["shipped_capabilities"])
    except ValueError as exc:
        raise errors.HeraldError(
            f"progress record {row['id']!r} in {progress_path} has malformed shipped_capabilities: {exc}"
        ) from exc
    if not isinstance(shipped_capabilities, list) or not all(isinstance(c, str) for c in shipped_capabilities):
        raise errors.HeraldError(
            f"progress record {row['id']!r} in {progress_path} has malformed "
            f"shipped_capabilities: expected an array of strings"
        )
    return Progress(
        id=row["id"],
        station=row["station"],
        date=row["date"],
        shipped_capabilities=shipped_capabilities,
        compute_hours=row["compute_hours"],
        token_spend=row["token_spend"],
        wall_clock_hours=row["wall_clock_hours"],
        unblock_narrative=row["unblock_narrative"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def read_all(progress_path: Path) -> list[Progress]:
    """Every stored record, or ``[]`` when nothing has been written yet.

    Raises ``errors.HeraldError`` naming ``progress_path`` when a stored
    record's ``shipped_capabilities`` JSON column is malformed -- the one
    corruption still reachable once the store is a schema-enforced
    database: every other field is a plain, typed SQL column in a
    ``STRICT`` table, so SQLite itself rejects a wrong-typed value at
    write time rather than handing it back here. (Without ``STRICT``,
    SQLite's default type affinity accepts e.g. ``compute_hours='lots'``
    from an out-of-band write and returns it verbatim -- the exact
    type-validation ``read_all`` performed on every record pre-13.3.)"""
    with db.connection(progress_path) as conn:
        rows = conn.execute(
            "SELECT id, station, date, shipped_capabilities, compute_hours, "
            "token_spend, wall_clock_hours, unblock_narrative, created_at, "
            "updated_at FROM progress ORDER BY station, date"
        ).fetchall()
        return [_row_to_progress(progress_path, row) for row in rows]


def write_all(progress_path: Path, records: list[Progress]) -> None:
    """Persist ``records`` wholesale (replacing every existing row),
    sorted by ``(station, date)`` before writing so callers relying on
    ``read_all``'s order see it deterministically.

    Takes the same ``db.transaction`` ``upsert`` does (Story 13.3): a
    public whole-table writer that skipped it would race a concurrent
    ``upsert`` exactly as before this module had any concurrency
    primitive at all."""
    with db.transaction(progress_path):
        _write_all_unlocked(progress_path, records)


def _write_all_unlocked(progress_path: Path, records: list[Progress]) -> None:
    """``write_all``'s body -- see the module docstring's Concurrency
    section for why this no longer needs to avoid a separate lock
    acquisition the way it did under ``locking.locked``: ``db.transaction``
    is reentrant, so calling this from inside ``upsert``'s own open
    transaction (or ``write_all``'s) simply joins it."""
    ordered = sorted(records, key=lambda r: (r.station, r.date))
    try:
        with db.transaction(progress_path) as conn:
            conn.execute("DELETE FROM progress")
            conn.executemany(
                "INSERT INTO progress (id, station, date, shipped_capabilities, "
                "compute_hours, token_spend, wall_clock_hours, unblock_narrative, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [_to_params(r) for r in ordered],
            )
    except errors.HeraldError:
        raise
    except (sqlite3.Error, TypeError, ValueError, RecursionError) as exc:
        # The non-`sqlite3` arms are not defensive padding: they are the
        # exact set the pre-Story-13.3 `write_all` caught, and `_to_params`
        # -- which still `json.dumps` the `shipped_capabilities` column --
        # runs inside this `try`. Narrowing to `sqlite3.Error` silently
        # regressed the error contract this story promised to keep
        # unchanged. Verified: a non-serializable capability raised a raw
        # `TypeError` here, and a lone surrogate (what `argv` yields for a
        # non-UTF-8 byte, via `surrogateescape`) raised a raw
        # `UnicodeEncodeError` out of SQLite's own TEXT binding -- a
        # `ValueError` subclass the old `json.dumps(ensure_ascii=True)`
        # path escaped instead. Both reached `cli.dispatch`, which catches
        # only `HeraldError`, as tracebacks.
        raise errors.HeraldError(f"progress file {progress_path} could not be written: {exc}") from exc


def upsert(
    progress_path: Path,
    *,
    station: str,
    date: str,
    shipped_capabilities: list[str],
    compute_hours: float,
    token_spend: int,
    wall_clock_hours: float,
    unblock_narrative: str,
) -> Progress:
    """Create today's (or ``date``'s) record for ``station``, or replace it
    in place if one already exists for the same ``(station, date)`` key
    (Story 8.2/8.3's "Creates new Progress record for today (if not
    exists)" AC). Returns the stored record.

    Raises ``errors.HeraldError`` for a negative cost field -- none of
    compute_hours/token_spend/wall_clock_hours can meaningfully be
    negative, and without this check a typo'd flag was silently stored
    and rendered as-is (e.g. "-5h compute") with no indication anything
    was wrong.

    Operates on the single ``(station, date)`` row directly inside one
    ``db.transaction`` (Story 13.3) rather than reloading and rewriting
    the whole table -- a natural simplification once the store is a real
    database; the transaction's ``BEGIN IMMEDIATE`` gives the same
    "second concurrent writer blocks until the first commits" guarantee
    ``locking.locked`` gave, now enforced by SQLite itself."""
    if compute_hours < 0:
        raise errors.HeraldError("compute_hours must not be negative")
    if token_spend < 0:
        raise errors.HeraldError("token_spend must not be negative")
    if wall_clock_hours < 0:
        raise errors.HeraldError("wall_clock_hours must not be negative")
    try:
        with db.transaction(progress_path) as conn:
            existing = conn.execute(
                "SELECT id, created_at FROM progress WHERE station = ? AND date = ?",
                (station, date),
            ).fetchone()
            timestamp = now_iso()
            if existing is not None:
                updated = Progress(
                    id=existing["id"],
                    station=station,
                    date=date,
                    shipped_capabilities=list(shipped_capabilities),
                    compute_hours=compute_hours,
                    token_spend=token_spend,
                    wall_clock_hours=wall_clock_hours,
                    unblock_narrative=unblock_narrative,
                    created_at=existing["created_at"],
                    updated_at=timestamp,
                )
                conn.execute(
                    "UPDATE progress SET shipped_capabilities = ?, compute_hours = ?, "
                    "token_spend = ?, wall_clock_hours = ?, unblock_narrative = ?, "
                    "updated_at = ? WHERE id = ?",
                    (
                        json.dumps(updated.shipped_capabilities),
                        compute_hours,
                        token_spend,
                        wall_clock_hours,
                        unblock_narrative,
                        timestamp,
                        existing["id"],
                    ),
                )
                return updated
            created = Progress(
                id=new_id(),
                station=station,
                date=date,
                shipped_capabilities=list(shipped_capabilities),
                compute_hours=compute_hours,
                token_spend=token_spend,
                wall_clock_hours=wall_clock_hours,
                unblock_narrative=unblock_narrative,
                created_at=timestamp,
                updated_at=timestamp,
            )
            conn.execute(
                "INSERT INTO progress (id, station, date, shipped_capabilities, "
                "compute_hours, token_spend, wall_clock_hours, unblock_narrative, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                _to_params(created),
            )
            return created
    except errors.HeraldError:
        raise
    except (sqlite3.Error, TypeError, ValueError, RecursionError) as exc:
        # Same set, same reason, as `_write_all_unlocked` above.
        raise errors.HeraldError(f"progress file {progress_path} could not be written: {exc}") from exc


def latest_for_station(progress_path: Path, station: str) -> Progress | None:
    """The most recent (by ``date``) record for ``station``, or ``None``
    when there is none."""
    matches = [r for r in read_all(progress_path) if r.station == station]
    if not matches:
        return None
    return max(matches, key=lambda r: r.date)


def list_records(
    progress_path: Path,
    *,
    station: str | None = None,
    date_range: tuple[date_cls, date_cls] | None = None,
) -> list[Progress]:
    """Every record matching the optional ``station``/``date_range``
    filters, newest first (by ``date``, then ``station`` as a tiebreak for
    determinism)."""
    records = read_all(progress_path)
    if station is not None:
        records = [r for r in records if r.station == station]
    if date_range is not None:
        start, end = date_range
        records = [r for r in records if start <= date_cls.fromisoformat(r.date) <= end]
    return sorted(records, key=lambda r: (r.date, r.station), reverse=True)


def write_snapshot(progress_path: Path, out_dir: Path) -> Path:
    """Write ``out_dir/progress.json`` -- every record under
    ``progress_path`` (``list_records``'s own newest-first default order),
    as the static JSON snapshot the web dashboard's Progress tab reads.
    Returns the written path.

    Moved here (Story 13.5) from ``scripts/export_progress_snapshot.py``'s
    ``export_progress_snapshot`` body, which now delegates to this
    function instead of duplicating the write logic -- ``pyproject.toml``
    only packages ``src/pyforge``, so ``scripts/`` (an unpackaged dev
    convenience) cannot be imported back into ``scheduler.py``, but this
    module can be imported from both. Same output shape either caller
    uses: newest-first, ``json.dumps(..., indent=2)`` plus a trailing
    newline."""
    payload = [asdict(record) for record in list_records(progress_path)]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "progress.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out_path
