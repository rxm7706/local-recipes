"""Progress record local storage (Story 8.1, scaled-down Epic 8).

The full Epic 8 spec
(``_bmad-output/projects/pyforge-herald/planning-artifacts/epics-with-stories.md``
lines 359-568) assumes a live PostgreSQL/SQLite database behind SQLAlchemy +
Alembic migrations. Nothing else in this repo's Herald architecture (a
stateless CLI plus a static web dashboard) has ever hosted a persistent
service, so the first pass is scaled down to a single local JSON file --
``.herald/progress.json`` -- holding a JSON array of records, following the
same repo-root-relative, explicit-``Path``-argument convention
``state.py``'s ``DEFAULT_STATE_PATH``/``read``/``write`` already established
(AD-5's shape, reused rather than reinvented). See
``docs/dreams/herald-moments-2-4-live-backend.md`` for the deferred
live-database shape this module's data-access seam is meant to swap behind
without a CLI/web-tab contract change.

**Storage shape.** A JSON array of objects (not NDJSON): the whole file is
small (one record per station per day, a handful of stations), so there is
no streaming/append-only need NDJSON would justify, and a plain array is the
simplest thing that round-trips through ``json.load``/``json.dump`` the same
way ``state.py``'s single JSON object does.

**Uniqueness key.** ``(station, date)`` -- the epics doc's own Story 8.2 AC
("Creates new Progress record for today (if not exists)") implies at most
one record per station per calendar day. ``upsert`` enforces this: a second
``--update`` for the same station/day replaces the existing record in place
(bumping ``updated_at``, preserving the original ``id``/``created_at``)
rather than accumulating duplicates.

**Concurrency.** Same atomic-write pattern as ``state.py``/``deck_pipeline.py``:
write to a temp file in the same directory, then ``os.replace``. This is
crash-safety, not concurrency-safety -- two concurrent writers each
load-then-replace the whole document, and the loser's update is silently
lost, exactly like ``state.py``'s own documented limit. No current caller
writes concurrently.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from datetime import date as date_cls
from pathlib import Path

from . import errors

DEFAULT_PROGRESS_PATH = Path(".herald/progress.json")
"""Mirrors ``state.DEFAULT_STATE_PATH``'s convention: relative to a repo
root the caller resolves."""

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
    if not isinstance(record["compute_hours"], (int, float)) or isinstance(
        record["compute_hours"], bool
    ):
        return "field 'compute_hours' must be a number"
    if not isinstance(record["token_spend"], int) or isinstance(
        record["token_spend"], bool
    ):
        return "field 'token_spend' must be an integer"
    if not isinstance(record["wall_clock_hours"], (int, float)) or isinstance(
        record["wall_clock_hours"], bool
    ):
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
    not silently last-wins."""
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError(f"duplicate key {key!r}")
        document[key] = value
    return document


def read_all(progress_path: Path) -> list[Progress]:
    """Every stored record, or ``[]`` when the file does not exist yet.

    Raises ``errors.HeraldError`` on malformed JSON, a non-array top level,
    or any record failing ``_fields_problem`` -- mirrors ``state._load_document``'s
    discipline: a corrupt or hand-edited file fails structurally, never
    silently."""
    try:
        with progress_path.open(encoding="utf-8") as fh:
            document = json.load(fh, object_pairs_hook=_reject_duplicate_keys)
    except FileNotFoundError:
        return []
    except (ValueError, OSError, RecursionError) as exc:
        raise errors.HeraldError(
            f"progress file {progress_path} could not be read: {exc}"
        ) from exc
    if not isinstance(document, list):
        raise errors.HeraldError(
            f"progress file {progress_path} does not hold a JSON array at its top level"
        )
    records: list[Progress] = []
    for index, entry in enumerate(document):
        problem = _fields_problem(entry)
        if problem:
            raise errors.HeraldError(
                f"progress file {progress_path} has a malformed record at "
                f"index {index}: {problem}"
            )
        records.append(Progress(**entry))
    return records


def write_all(progress_path: Path, records: list[Progress]) -> None:
    """Persist ``records`` wholesale, atomically (temp file + ``os.replace``),
    mirroring ``state.write``'s crash-safety pattern. Sorted by
    ``(station, date)`` before writing so the on-disk file is deterministic
    across runs regardless of insertion order."""
    ordered = sorted(records, key=lambda r: (r.station, r.date))
    document = [asdict(r) for r in ordered]
    try:
        progress_path.parent.mkdir(parents=True, exist_ok=True)
        handle, tmp_name = tempfile.mkstemp(
            dir=progress_path.parent, prefix=f".{progress_path.name}-", suffix=".tmp"
        )
    except OSError as exc:
        raise errors.HeraldError(
            f"progress file {progress_path} could not be written: {exc}"
        ) from exc
    try:
        try:
            fh = os.fdopen(handle, "w", encoding="utf-8")
        except BaseException:
            os.close(handle)
            raise
        with fh:
            json.dump(document, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp_name, progress_path)
    except BaseException as exc:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        if isinstance(exc, (OSError, TypeError, ValueError, RecursionError)):
            raise errors.HeraldError(
                f"progress file {progress_path} could not be written: {exc}"
            ) from exc
        raise


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
    was wrong."""
    if compute_hours < 0:
        raise errors.HeraldError("compute_hours must not be negative")
    if token_spend < 0:
        raise errors.HeraldError("token_spend must not be negative")
    if wall_clock_hours < 0:
        raise errors.HeraldError("wall_clock_hours must not be negative")
    records = read_all(progress_path)
    timestamp = now_iso()
    for index, existing in enumerate(records):
        if existing.station == station and existing.date == date:
            updated = Progress(
                id=existing.id,
                station=station,
                date=date,
                shipped_capabilities=list(shipped_capabilities),
                compute_hours=compute_hours,
                token_spend=token_spend,
                wall_clock_hours=wall_clock_hours,
                unblock_narrative=unblock_narrative,
                created_at=existing.created_at,
                updated_at=timestamp,
            )
            records[index] = updated
            write_all(progress_path, records)
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
    records.append(created)
    write_all(progress_path, records)
    return created


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
