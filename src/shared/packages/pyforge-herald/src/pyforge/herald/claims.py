"""Success-claim storage (Story 9.1, scaled down; Story 13.3 moved the
backing store from a JSON file to the shared SQLite database in
``db.py``).

Per the 2026-08-08 scope decision recorded in
``docs/dreams/herald-moments-2-4-live-backend.md``, this module persists
``Claim`` records as rows in ``db.py``'s shared ``.herald/herald.db``
(table ``claims``) rather than reaching a live PostgreSQL/SQLAlchemy stack
the original Epic 9 spec assumed. ``evidence``/``edit_history`` stay JSON
``TEXT`` columns (no cross-record query needs them normalized -- the same
reasoning ``progress.py``'s ``shipped_capabilities`` and ``notices.py``'s
``revisions`` follow).

**Versioning (Story 9.1's "thesis edited -> new version, old preserved"
AC), scaled down.** The original AC describes a full version-numbered
history with a ``current: true`` marker. This module instead appends a
``ThesisVersion(thesis, edited_at)`` to ``Claim.edit_history`` whenever
``publish`` is called with a ``thesis`` that differs from the claim's
prior (non-``None``) thesis -- the *old* thesis is preserved in
``edit_history``, the *new* one becomes ``Claim.thesis``. This is a
reasonable scoped-down interpretation: there is exactly one "current"
value (the field itself) and a flat list of what it used to be, without
inventing a version-number sequence no caller yet needs.

**Evidence staleness is computed, never stored.** ``Evidence`` carries
``validated``/``validated_at`` but no persisted ``is_stale`` flag --
staleness (AD-15's 7-day window, ``evidence.STALE_AFTER``) is a function
of "how old is ``validated_at``," recomputed at read time by ``to_dict``
rather than a second field that could drift out of sync with the clock.

**Cross-Moment evidence linking (Story 11.3, scaled down).** A claim's
evidence can cite an Operations Notice (Epic 10) by giving it
``type="notice"``. There is no separate "notice reference" field --
``Evidence.url`` is reused to hold the notice's ``component`` name instead
of an HTTP URL for this one type (documented here rather than adding a
second, mutually-exclusive field for what is still "the one thing this
evidence entry points at"). A ``type="notice"`` entry is never sent through
``evidence.validate_link``/``validate_for_publish`` (it is not a URL, and
there is nothing to ``HEAD``) -- ``publish``'s validation loop below treats
it as trivially valid instead. The *reverse* direction (a Notice seeing
which claims cite it) is a computed, un-persisted view --
``referenced_by_claims`` below -- rather than a new field on ``Notice``:
recomputing "who cites this component" from the claims table at read time
means the two never drift out of sync with each other the way a second
stored copy of the same fact could.

**Concurrency (Story 13.1, closing ``DW-1-4-2``; Story 13.3 moved the
mechanism).** ``create`` has no network step, so it locks its whole
read-modify-write span. ``db.transaction`` -- SQLite's own
``BEGIN IMMEDIATE``/commit -- now IS that lock (see ``db.py``'s module
docstring); everything except ``create``'s pure, no-I/O argument checks,
which run before the transaction opens so a call that cannot succeed
fails fast instead of contending first (see ``create``'s own docstring).
``publish``/``revalidate``/``revalidate_all`` each call
``evidence_mod.validate_link``/``validate_for_publish`` per evidence
entry -- a real HTTP request -- so the transaction must never span that
network I/O (holding a write lock across a live HTTP call would block
every other claims writer for its duration, a liveness regression this
module is explicit about avoiding). Each instead validates every evidence
link UNLOCKED first, then opens the transaction only around re-reading the
fresh claims state, applying the already-computed validation results, and
writing -- exactly the shape Story 13.1 established, now enforced by
SQLite's own transactional locking instead of an OS advisory lock.

Every write function below still calls the module-level ``read_all``/
``_write_all`` (not some internal, differently-named helper) at both the
pre-transaction and in-transaction points, the same shape Story 13.1 gave
them -- ``db.py``'s reentrant ambient-transaction design (module
docstring) means a call to ``read_all``/``_write_all`` from inside an
already-open ``db.transaction`` for the same path joins it rather than
opening a second connection, so the two calls together form one atomic
read-modify-write exactly as they did under ``locking.locked``. This also
means the existing ``monkeypatch.setattr(claims, "read_all", ...)``-based
concurrency tests keep intercepting the same calls unchanged.

**The pre-lock results are carried POSITIONALLY, never in a dict keyed by
``Evidence`` value.** All three keep, per claim, the pre-validation
evidence tuple (``original``) plus an index-aligned tuple of results, and
inside the lock apply ``results[i]`` to the freshly-read
``claim.evidence[i]`` only when ``i < len(original)`` AND
``fresh.evidence[i] == original[i]``; any other fresh entry is left
untouched. That equality check is the discard-stale rule: a concurrent
writer that changed a specific evidence entry between the unlocked
validation and the locked re-read keeps its own (newer) value rather than
being clobbered with a now-stale result. Comparing at a fixed index (rather
than looking an entry up by value) also survives a concurrently-changed
evidence length or ordering.

A ``dict[Evidence, Evidence]`` is wrong here even within ONE claim.
``Evidence`` is a frozen, value-equal dataclass and ``create`` de-duplicates
nothing (it validates only ``type``), so a single claim can legitimately
carry two field-identical entries (same url/type/label). A value-keyed dict
collapses them onto one key: two independent validation calls are made, but
only the last result is retained and is then applied to BOTH entries -- a
claim with a duplicated link whose first check succeeds and whose second
hits a transient 429 would store ``[False, False]`` instead of
``[True, False]``. Operating on one claim at a time does **not** make a
value-keyed map safe.

``revalidate_all`` additionally keys its per-claim structure by claim id
(``dict[str, tuple[original, results]]``) so a lookup only ever searches
within that SAME claim's own results -- never one structure shared across
every claim's evidence, which would additionally let one claim's HTTP
outcome overwrite a different claim's (two different claims can also cite a
field-identical entry).

``publish`` goes one step further than the discard-stale rule. Discarding
is right for ``revalidate``/``revalidate_all``, whose purpose is to RECORD
breakage rather than gate on it; it is not sufficient for ``publish``,
whose contract is that a broken link blocks the publish and nothing is
written. Passing a concurrently-changed entry through unvalidated would
persist ``status="published"`` alongside evidence this call never checked
(and which a concurrent ``revalidate`` may have just proved broken), so
``publish`` re-verifies inside the lock that every entry it is about to
write carries its own validation, and raises ``errors.ClaimStateError``
(writing nothing) when any does not.
"""

from __future__ import annotations

import contextlib
import json
import sqlite3
import uuid
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from . import db, errors
from . import evidence as evidence_mod

DEFAULT_CLAIMS_PATH = db.DEFAULT_DB_PATH
"""Default location, relative to a repo root the caller resolves (mirrors
``state.DEFAULT_STATE_PATH``). Redefined to ``db.DEFAULT_DB_PATH`` (Story
13.3) rather than removed, so every existing call site needs zero
changes -- see ``db.py``'s module docstring on why one shared database."""

EVIDENCE_TYPES = ("test_results", "metrics", "adoption", "other", "notice")
CLAIM_STATUSES = ("draft", "published", "closed")

_EVIDENCE_FIELDS = frozenset(("type", "url", "label", "validated", "validated_at"))
_THESIS_VERSION_FIELDS = frozenset(("thesis", "edited_at"))
_CLAIM_FIELDS = frozenset(
    (
        "id",
        "project_name",
        "status",
        "thesis",
        "shipped_date",
        "created_at",
        "published_at",
        "closed_at",
        "updated_at",
        "evidence",
        "edit_history",
    )
)


@dataclass(frozen=True)
class Evidence:
    """One evidence link -- ``type`` is one of ``EVIDENCE_TYPES``, not
    enforced by the dataclass itself (``create``/callers validate)."""

    type: str
    url: str
    label: str
    validated: bool = False
    validated_at: str | None = None  # ISO 8601, UTC


@dataclass(frozen=True)
class ThesisVersion:
    """One prior thesis value, preserved in ``Claim.edit_history`` when a
    publish supplies a different thesis than the claim already had."""

    thesis: str
    edited_at: str  # ISO 8601, UTC


@dataclass(frozen=True)
class Claim:
    id: str
    project_name: str
    status: str  # draft | published | closed
    thesis: str | None
    shipped_date: str | None  # ISO date (YYYY-MM-DD)
    created_at: str  # ISO 8601, UTC
    published_at: str | None
    closed_at: str | None
    updated_at: str  # ISO 8601, UTC
    evidence: tuple[Evidence, ...] = field(default_factory=tuple)
    edit_history: tuple[ThesisVersion, ...] = field(default_factory=tuple)


def _default_now() -> datetime:
    return datetime.now(UTC)


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """``object_pairs_hook`` refusing a duplicated key in any JSON object in
    a legacy document -- mirrors ``state._reject_duplicate_keys``. Only
    relevant to ``_read_legacy_json`` now."""
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError(f"duplicate key {key!r}")
        document[key] = value
    return document


def _load_legacy_document(claims_path: Path) -> list[object]:
    """The whole legacy claims JSON file as a list, or ``[]`` when the file
    does not exist. Raises ``errors.HeraldError`` naming ``claims_path`` for
    any structural failure (AD-6) -- malformed JSON, an unreadable file, or
    a non-list top level. Used only by ``_read_legacy_json`` (the one-time
    migration import); the live read path is ``read_all``, through
    ``db.py``."""
    try:
        with claims_path.open(encoding="utf-8") as fh:
            document = json.load(fh, object_pairs_hook=_reject_duplicate_keys)
    except FileNotFoundError:
        return []
    except (ValueError, OSError, RecursionError) as exc:
        raise errors.HeraldError(f"claims file {claims_path} could not be read: {exc}") from exc
    if not isinstance(document, list):
        raise errors.HeraldError(f"claims file {claims_path} does not hold a JSON array at its top level")
    return document


def _evidence_from_dict(claims_path: Path, claim_id: object, entry: object) -> Evidence:
    malformed = f"claims file {claims_path} has a malformed evidence entry for claim {claim_id!r}"
    if not isinstance(entry, dict):
        raise errors.HeraldError(f"{malformed}: entry is not a JSON object")
    unknown = sorted(set(entry) - _EVIDENCE_FIELDS)
    if unknown:
        raise errors.HeraldError(f"{malformed}: unknown field(s) {', '.join(map(repr, unknown))}")
    try:
        return Evidence(
            type=entry["type"],
            url=entry["url"],
            label=entry["label"],
            validated=bool(entry.get("validated", False)),
            validated_at=entry.get("validated_at"),
        )
    except KeyError as exc:
        raise errors.HeraldError(f"{malformed}: missing field {exc}") from exc


def _thesis_version_from_dict(claims_path: Path, claim_id: object, entry: object) -> ThesisVersion:
    malformed = f"claims file {claims_path} has a malformed edit_history entry for claim {claim_id!r}"
    if not isinstance(entry, dict):
        raise errors.HeraldError(f"{malformed}: entry is not a JSON object")
    unknown = sorted(set(entry) - _THESIS_VERSION_FIELDS)
    if unknown:
        raise errors.HeraldError(f"{malformed}: unknown field(s) {', '.join(map(repr, unknown))}")
    try:
        return ThesisVersion(thesis=entry["thesis"], edited_at=entry["edited_at"])
    except KeyError as exc:
        raise errors.HeraldError(f"{malformed}: missing field {exc}") from exc


def _claim_from_dict(claims_path: Path, entry: object) -> Claim:
    malformed = f"claims file {claims_path} has a malformed claim entry"
    if not isinstance(entry, dict):
        raise errors.HeraldError(f"{malformed}: entry is not a JSON object")
    unknown = sorted(set(entry) - _CLAIM_FIELDS)
    if unknown:
        raise errors.HeraldError(f"{malformed} ({entry.get('id')!r}): unknown field(s) {', '.join(map(repr, unknown))}")
    try:
        claim_id = entry["id"]
        evidence = tuple(_evidence_from_dict(claims_path, claim_id, item) for item in entry.get("evidence", []))
        edit_history = tuple(
            _thesis_version_from_dict(claims_path, claim_id, item) for item in entry.get("edit_history", [])
        )
        return Claim(
            id=claim_id,
            project_name=entry["project_name"],
            status=entry["status"],
            thesis=entry.get("thesis"),
            shipped_date=entry.get("shipped_date"),
            created_at=entry["created_at"],
            published_at=entry.get("published_at"),
            closed_at=entry.get("closed_at"),
            updated_at=entry["updated_at"],
            evidence=evidence,
            edit_history=edit_history,
        )
    except KeyError as exc:
        raise errors.HeraldError(f"{malformed}: missing field {exc}") from exc


def _read_legacy_json(claims_path: Path) -> list[Claim]:
    """The pre-Story-13.3 JSON-file reader, preserved verbatim (this was
    ``read_all``'s entire body) for the one-time legacy import
    (``db.py``'s ``_import_legacy_v1``) -- so a legacy ``claims.json`` that
    fails this exact validation still raises the identical
    ``errors.HeraldError`` at migration time (Boundaries & Constraints)."""
    return [_claim_from_dict(claims_path, entry) for entry in _load_legacy_document(claims_path)]


def _to_params(c: Claim) -> tuple[object, ...]:
    """``c`` as a positional parameter tuple matching the ``claims``
    table's column order -- shared by every INSERT (``_write_all`` and
    ``db.py``'s legacy import)."""
    return (
        c.id,
        c.project_name,
        c.status,
        c.thesis,
        c.shipped_date,
        c.created_at,
        c.published_at,
        c.closed_at,
        c.updated_at,
        json.dumps(
            [
                {
                    "type": e.type,
                    "url": e.url,
                    "label": e.label,
                    "validated": e.validated,
                    "validated_at": e.validated_at,
                }
                for e in c.evidence
            ]
        ),
        json.dumps([{"thesis": v.thesis, "edited_at": v.edited_at} for v in c.edit_history]),
    )


def _row_to_claim(claims_path: Path, row) -> Claim:
    try:
        evidence_raw = json.loads(row["evidence"])
        edit_history_raw = json.loads(row["edit_history"])
    except ValueError as exc:
        raise errors.HeraldError(
            f"claims record {row['id']!r} in {claims_path} has malformed evidence/edit_history JSON: {exc}"
        ) from exc
    if not isinstance(evidence_raw, list) or not isinstance(edit_history_raw, list):
        raise errors.HeraldError(
            f"claims record {row['id']!r} in {claims_path} has malformed evidence/edit_history: expected a JSON array"
        )
    entry = {
        "id": row["id"],
        "project_name": row["project_name"],
        "status": row["status"],
        "thesis": row["thesis"],
        "shipped_date": row["shipped_date"],
        "created_at": row["created_at"],
        "published_at": row["published_at"],
        "closed_at": row["closed_at"],
        "updated_at": row["updated_at"],
        "evidence": evidence_raw,
        "edit_history": edit_history_raw,
    }
    return _claim_from_dict(claims_path, entry)


def read_all(claims_path: Path) -> list[Claim]:
    """Every claim currently stored, in ``rowid`` (insertion) order."""
    with db.connection(claims_path) as conn:
        rows = conn.execute("SELECT * FROM claims ORDER BY rowid").fetchall()
        return [_row_to_claim(claims_path, row) for row in rows]


def read_one(claims_path: Path, claim_id: str) -> Claim:
    """``claim_id``'s stored claim. Raises ``errors.ClaimNotFoundError``
    when no claim with that id exists.

    Looks the row up directly by ``id`` (a targeted ``WHERE`` clause)
    rather than decoding every row via ``read_all`` -- an unrelated
    malformed row elsewhere in the table must not block looking up a claim
    whose own row is perfectly healthy; only the matched row's own
    malformation (if any) raises, preserving AD-6 for the one entry that's
    actually relevant."""
    with db.connection(claims_path) as conn:
        row = conn.execute("SELECT * FROM claims WHERE id = ?", (claim_id,)).fetchone()
    if row is None:
        raise errors.ClaimNotFoundError(f"no claim found with id {claim_id!r}")
    return _row_to_claim(claims_path, row)


def list_claims(
    claims_path: Path,
    *,
    status: str | None = None,
    date_range: tuple[date, date] | None = None,
) -> list[Claim]:
    """Every stored claim, optionally filtered by ``status`` and/or a
    ``(start, end)`` inclusive range over ``shipped_date``. A claim with no
    ``shipped_date`` is excluded whenever ``date_range`` is given -- an
    unset date cannot be tested against a range."""
    claims = read_all(claims_path)
    if status is not None:
        claims = [c for c in claims if c.status == status]
    if date_range is not None:
        start, end = date_range
        filtered = []
        for c in claims:
            if c.shipped_date is None:
                continue
            shipped = date.fromisoformat(c.shipped_date)
            if start <= shipped <= end:
                filtered.append(c)
        claims = filtered
    return claims


@contextlib.contextmanager
def _write_transaction(claims_path: Path) -> Iterator[None]:
    """``db.transaction`` plus this module's AD-6 error translation, for
    the whole critical section rather than just its write.

    ``db.connection`` translates a raw storage failure into
    ``errors.HeraldError`` for STANDALONE reads only -- inside a
    transaction it deliberately leaves translation to the writer that owns
    the critical section (see its docstring). Every writer here opens its
    transaction with a fresh in-transaction ``read_all``, and that read was
    covered by nothing: ``_write_all``'s own wrapper starts later, and the
    standalone ``read_all`` these functions take BEFORE opening the
    transaction is a different call. Verified: with the fault arriving
    during ``publish``'s unlocked evidence-validation window, the
    in-transaction ``read_all`` raised
    ``sqlite3.OperationalError: no such table: claims`` straight through
    ``cli.dispatch``, which catches only ``HeraldError``, as a traceback."""
    try:
        with db.transaction(claims_path):
            yield
    except errors.HeraldError:
        raise
    except (sqlite3.Error, TypeError, ValueError, RecursionError) as exc:
        # Same set, same reason, as `_write_all` -- see the comment there.
        raise errors.HeraldError(f"claims could not be written to {claims_path}: {exc}") from exc


def _write_all(claims_path: Path, claims: Sequence[Claim]) -> None:
    """Persist the whole claims list, replacing every existing row (Story
    13.3: was an atomic JSON-file rewrite; now one ``db.transaction``
    doing ``DELETE`` + re-``INSERT``). Reentrant the same way every other
    write in this module is -- see the module docstring's Concurrency
    section -- so a call from inside ``create``/``publish``/``revalidate``/
    ``revalidate_all``'s own open transaction joins it rather than opening
    a second one."""
    try:
        with db.transaction(claims_path) as conn:
            conn.execute("DELETE FROM claims")
            conn.executemany(
                "INSERT INTO claims (id, project_name, status, thesis, "
                "shipped_date, created_at, published_at, closed_at, updated_at, "
                "evidence, edit_history) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [_to_params(c) for c in claims],
            )
    except errors.HeraldError:
        raise
    except (sqlite3.Error, TypeError, ValueError, RecursionError) as exc:
        # Same set, same reason, as `progress._write_all_unlocked` -- see
        # the comment there. `_to_params` `json.dumps` the `evidence`/
        # `edit_history` columns inside this `try`, and the plain TEXT
        # columns bind through SQLite's UTF-8 encoder.
        raise errors.HeraldError(f"claims could not be written to {claims_path}: {exc}") from exc


def create(
    claims_path: Path,
    *,
    project_name: str,
    shipped_date: str | None = None,
    evidence: Sequence[Evidence] = (),
    now: Callable[[], datetime] = _default_now,
    today: Callable[[], date] = date.today,
    id_factory: Callable[[], str] = lambda: str(uuid.uuid4()),
) -> Claim:
    """Create a draft ``Claim`` (Story 9.2, scaled down: a CLI command an
    operator runs by hand supplies exactly the fields the original spec's
    webhook payload would have extracted). Appends it to ``claims_path``
    and returns it.

    No network step, so the whole read-modify-write body below runs inside
    ``db.transaction`` (Story 13.3; see the module docstring's Concurrency
    section). The pure, no-I/O argument checks just below are validated
    BEFORE the transaction is opened: they depend on nothing but this
    call's own arguments, so a call that is going to fail on basic
    validation fails fast without first contending on the write lock."""
    if not project_name.strip():
        raise errors.HeraldError("project_name must not be empty")
    for e in evidence:
        if e.type not in EVIDENCE_TYPES:
            raise errors.HeraldError(f"evidence type {e.type!r} must be one of {EVIDENCE_TYPES}")
    # `_write_transaction`, not a bare `db.transaction`, for the AD-6
    # reason its docstring gives: the ambient `read_all` below is covered
    # by nothing else.
    with _write_transaction(claims_path):
        timestamp = now().isoformat()
        claim = Claim(
            id=id_factory(),
            project_name=project_name,
            status="draft",
            thesis=None,
            shipped_date=(shipped_date if shipped_date is not None else today().isoformat()),
            created_at=timestamp,
            published_at=None,
            closed_at=None,
            updated_at=timestamp,
            evidence=tuple(evidence),
            edit_history=(),
        )
        claims = read_all(claims_path)
        claims.append(claim)
        _write_all(claims_path, claims)
        return claim


def publish(
    claims_path: Path,
    claim_id: str,
    *,
    thesis: str | None = None,
    validate: Callable[[str], evidence_mod.LinkValidation] | None = None,
    now: Callable[[], datetime] = _default_now,
) -> Claim:
    """Publish a draft claim (Story 9.3 + 9.5 wiring): validates every
    evidence link via ``validate`` (default: ``evidence.validate_for_publish``,
    which raises ``errors.EvidenceLinkError`` naming the first broken link --
    propagated unchanged, publish is rejected, nothing is written), then
    updates ``status``/``published_at``/``thesis``/each evidence entry's
    ``validated``/``validated_at``.

    Raises ``errors.ClaimStateError`` when the claim is not currently
    ``draft`` (no republish-in-place path), and ``errors.HeraldError`` when
    neither ``thesis`` nor the claim's existing thesis is set -- a claim
    cannot publish with no thesis at all.

    ``validate`` defaults to ``None`` and is resolved to
    ``evidence_mod.validate_for_publish`` *inside* the function body, not as
    a parameter default -- a parameter default is bound once at import
    time, which would freeze in the pre-monkeypatch function object and
    make ``evidence.validate_for_publish`` unpatchable from a test.

    Validates every evidence link UNLOCKED (a real HTTP request per entry)
    before opening the transaction -- the transaction only ever spans the
    fresh load/apply/write span that follows (Story 13.1/13.3; see the
    module docstring's Concurrency section). The results are carried
    POSITIONALLY, index-aligned with the evidence tuple they were computed
    from, and applied back only where the freshly-read entry at that index
    still equals the entry that was validated. Because ``publish``'s
    contract is that a broken link blocks the publish, an entry the
    discard-stale rule would pass through unvalidated (a concurrent writer
    changed it during the unlocked HTTP window) aborts the whole call with
    ``errors.ClaimStateError`` instead -- a claim is never persisted as
    ``published`` carrying evidence this call did not itself validate.

    ``thesis`` is likewise resolved against the FRESH in-transaction read,
    not the pre-validation one: falling back to the pre-lock
    ``claim.thesis`` would publish a stale thesis over one a concurrent
    writer set during the unlocked HTTP window, and file that writer's
    NEWER text into ``edit_history`` as though it were the superseded
    version."""
    if validate is None:
        validate = evidence_mod.validate_for_publish
    no_thesis = f"claim {claim_id!r} has no thesis; supply --thesis to publish"
    claims = read_all(claims_path)
    index = next((i for i, c in enumerate(claims) if c.id == claim_id), None)
    if index is None:
        raise errors.ClaimNotFoundError(f"no claim found with id {claim_id!r}")
    claim = claims[index]
    if claim.status != "draft":
        raise errors.ClaimStateError(
            f"claim {claim_id!r} is already {claim.status!r}; only a draft claim can be published"
        )
    # Fail fast, before spending HTTP requests on evidence links, on a call
    # that has no thesis to publish. Advisory only: the value actually
    # written is recomputed from the fresh in-lock read below, so this
    # pre-lock read decides nothing.
    if not (thesis if thesis is not None else claim.thesis):
        raise errors.HeraldError(no_thesis)
    timestamp = now()
    timestamp_iso = timestamp.isoformat()
    broken: list[str] = []
    # Index-aligned with `original_evidence` -- one result per evidence
    # POSITION, never a dict keyed by `Evidence` value (see module
    # docstring: a single claim may carry two field-identical entries, and
    # a value-keyed map collapses them onto one result).
    original_evidence = claim.evidence
    results: list[Evidence] = []
    for e in original_evidence:
        if e.type == "notice":
            # A "notice" evidence entry's `url` holds a Notice component
            # name, not an HTTP URL (see module docstring) -- nothing to
            # HEAD, so it is trivially valid rather than run through the
            # HTTP-based `validate`.
            results.append(replace(e, validated=True, validated_at=timestamp_iso))
            continue
        try:
            validate(e.url)
        except errors.EvidenceLinkError as exc:
            broken.append(f"{e.url} ({exc})")
            # Placeholder only, to keep `results` index-aligned: a
            # non-empty `broken` raises just below, so it is never applied.
            results.append(e)
        else:
            results.append(replace(e, validated=True, validated_at=timestamp_iso))
    if broken:
        # Regression: raising on the FIRST broken link meant an operator
        # fixing evidence one publish-attempt at a time hit the next
        # broken link on each retry instead of seeing the full list once.
        raise errors.EvidenceLinkError(
            f"claim {claim_id!r} has {len(broken)} broken evidence link(s): "
            f"{'; '.join(broken)}. Fix or remove before publishing."
        )

    with _write_transaction(claims_path):
        fresh_claims = read_all(claims_path)  # fresh state, not the pre-validation read
        fresh_index = next((i for i, c in enumerate(fresh_claims) if c.id == claim_id), None)
        if fresh_index is None:
            raise errors.ClaimNotFoundError(f"no claim found with id {claim_id!r}")
        fresh_claim = fresh_claims[fresh_index]
        if fresh_claim.status != "draft":
            raise errors.ClaimStateError(
                f"claim {claim_id!r} is already {fresh_claim.status!r}; only a draft claim can be published"
            )
        # Apply this call's results by INDEX, and only where the fresh
        # entry at that index is still exactly the entry that was validated
        # (the discard-stale rule -- see the module docstring).
        carried = tuple(
            i < len(original_evidence) and e == original_evidence[i] for i, e in enumerate(fresh_claim.evidence)
        )
        validated_evidence = tuple(results[i] if carried[i] else e for i, e in enumerate(fresh_claim.evidence))
        if not all(carried):
            # Discarding a stale result is right for `revalidate`, whose
            # job is to RECORD breakage. It is not enough here: passing a
            # concurrently-changed entry through unvalidated would persist
            # `status="published"` alongside evidence this call never
            # checked (and which a concurrent `revalidate` may have just
            # proved broken), silently bypassing publish's own broken-link
            # gate. Write nothing and make the operator re-run instead.
            raise errors.ClaimStateError(
                f"claim {claim_id!r} had its evidence changed by another writer "
                f"while this publish was validating links; nothing was written -- "
                f"re-run publish to validate the current evidence"
            )
        # Resolved here, not from the pre-lock read: `claim.thesis` is a
        # snapshot from before the unlocked validation window, so publishing
        # it would silently revert a thesis a concurrent writer set during
        # that window -- and push the newer text into `edit_history` as the
        # superseded one, inverting the two.
        final_thesis = thesis if thesis is not None else fresh_claim.thesis
        if not final_thesis:
            # The pre-lock check passed, so a concurrent writer cleared the
            # thesis during the validation window. Same refusal, same
            # message -- publishing an empty thesis is never allowed.
            raise errors.HeraldError(no_thesis)
        edit_history = fresh_claim.edit_history
        if fresh_claim.thesis is not None and fresh_claim.thesis != final_thesis:
            edit_history = (
                *edit_history,
                ThesisVersion(thesis=fresh_claim.thesis, edited_at=timestamp_iso),
            )
        updated = replace(
            fresh_claim,
            status="published",
            thesis=final_thesis,
            published_at=timestamp_iso,
            updated_at=timestamp_iso,
            evidence=validated_evidence,
            edit_history=edit_history,
        )
        fresh_claims[fresh_index] = updated
        _write_all(claims_path, fresh_claims)
        return updated


def _require_unique_ids(claims_path: Path, claims: list[Claim]) -> None:
    """Refuse a claims table holding two claims with the same id.

    ``revalidate_all`` keys its validation results by claim id, which is
    only sound while ids are unique: two claims sharing one would collapse
    onto a single map entry and let one claim's HTTP outcome overwrite the
    other's. ``create`` generates a uuid4 per claim, so this only happens
    with an injected ``id_factory`` or a merged/hand-written claims table --
    refuse structurally rather than silently corrupting one of them.

    Called twice per ``revalidate_all``: once on the pre-lock read (which
    builds the map) and once on the fresh in-lock read (which consumes it),
    because a duplicate can be written between the two."""
    if len({c.id for c in claims}) != len(claims):
        raise errors.HeraldError(
            f"{claims_path} holds duplicate claim ids; refusing to revalidate until they are unique"
        )


def _revalidated_entry(
    e: Evidence,
    *,
    validate: Callable[[str], evidence_mod.LinkValidation],
    timestamp_iso: str,
) -> Evidence:
    """One evidence entry, re-checked -- except a ``"notice"``-type entry
    (see module docstring): its ``url`` is a Notice component name, not an
    HTTP URL, so it is left ``validated=True`` (trivially valid, mirroring
    ``publish``'s own treatment) rather than run through ``validate``."""
    if e.type == "notice":
        return replace(e, validated=True, validated_at=timestamp_iso)
    return replace(e, validated=validate(e.url).is_valid, validated_at=timestamp_iso)


def revalidate(
    claims_path: Path,
    claim_id: str,
    *,
    validate: Callable[[str], evidence_mod.LinkValidation] | None = None,
    now: Callable[[], datetime] = _default_now,
) -> Claim:
    """Story 9.5's scaled-down "weekly async validation": an operator-run,
    on-demand re-check of one claim's evidence links (never raises on a
    broken link -- unlike ``publish``, this call's whole point is to
    surface breakage, not reject it). Updates each entry's
    ``validated``/``validated_at`` in place and persists.

    ``validate`` is resolved to ``evidence_mod.validate_link`` inside the
    function body -- see ``publish``'s docstring for why this can't be a
    parameter default.

    Validates every evidence link UNLOCKED (real HTTP) before opening the
    transaction, exactly like ``publish`` -- see its docstring and the
    module docstring's Concurrency section. The results are carried
    POSITIONALLY (index-aligned with the evidence tuple they were computed
    from), never in a dict keyed by ``Evidence`` value: operating on a
    single claim does NOT make a value-keyed map safe, because one claim
    can carry two field-identical entries whose two validation calls
    returned different outcomes."""
    if validate is None:
        validate = evidence_mod.validate_link
    claims = read_all(claims_path)
    index = next((i for i, c in enumerate(claims) if c.id == claim_id), None)
    if index is None:
        raise errors.ClaimNotFoundError(f"no claim found with id {claim_id!r}")
    claim = claims[index]
    timestamp = now()
    timestamp_iso = timestamp.isoformat()
    original_evidence = claim.evidence
    results = tuple(_revalidated_entry(e, validate=validate, timestamp_iso=timestamp_iso) for e in original_evidence)

    with _write_transaction(claims_path):
        fresh_claims = read_all(claims_path)  # fresh state, not the pre-validation read
        fresh_index = next((i for i, c in enumerate(fresh_claims) if c.id == claim_id), None)
        if fresh_index is None:
            raise errors.ClaimNotFoundError(f"no claim found with id {claim_id!r}")
        fresh_claim = fresh_claims[fresh_index]
        carried = [i < len(original_evidence) and e == original_evidence[i] for i, e in enumerate(fresh_claim.evidence)]
        if (original_evidence or fresh_claim.evidence) and not any(carried):
            # Not one of this run's results survived onto the claim about to
            # be written, so `updated_at` would assert a validation that
            # never landed. Leave the claim byte-for-byte unchanged -- the
            # same rule `revalidate_all` applies to a claim it never
            # validated. Two distinct concurrent edits reach here:
            #   * `original_evidence` non-empty -- this run validated
            #     entries and a concurrent writer changed (or removed)
            #     every one of them, so the discard-stale rule dropped
            #     every result. Guarded on `original_evidence` rather than
            #     on `fresh_claim.evidence` because a writer *emptying* the
            #     tuple leaves the fresh one falsy, which would otherwise
            #     skip exactly the case this branch exists to catch.
            #   * `fresh_claim.evidence` non-empty -- this run had nothing
            #     to validate (the claim carried no evidence when it was
            #     read) and a concurrent writer *added* entries during the
            #     unlocked window. Zero validation calls were made, so
            #     those entries are unchecked and must not be stamped as
            #     though they had been.
            # A claim that had no evidence at either point is a different
            # thing entirely -- nothing was discarded and nothing appeared,
            # so it still gets its ordinary `updated_at` stamp, unchanged
            # from before this story.
            return fresh_claim
        revalidated_evidence = tuple(results[i] if carried[i] else e for i, e in enumerate(fresh_claim.evidence))
        updated = replace(fresh_claim, evidence=revalidated_evidence, updated_at=timestamp_iso)
        fresh_claims[fresh_index] = updated
        _write_all(claims_path, fresh_claims)
        return updated


def revalidate_all(
    claims_path: Path,
    *,
    validate: Callable[[str], evidence_mod.LinkValidation] | None = None,
    now: Callable[[], datetime] = _default_now,
) -> list[Claim]:
    """``revalidate`` for every stored claim, one shared ``now()`` timestamp
    across the whole batch (mirrors ``evidence.schedule_async_validation``'s
    own "one run, one timestamp" discipline).

    ``validate`` is resolved to ``evidence_mod.validate_link`` inside the
    function body -- see ``publish``'s docstring for why this can't be a
    parameter default.

    Validates every evidence link UNLOCKED (real HTTP) before opening the
    transaction, same as ``publish``/``revalidate``, carrying each claim's
    results POSITIONALLY as an ``(original, results)`` index-aligned pair
    rather than in a dict keyed by ``Evidence`` value (see the module
    docstring: one claim can carry two field-identical entries, which a
    value-keyed map collapses onto a single result).

    That pair is additionally keyed by claim id
    (``validated_by_claim: dict[str, tuple[tuple[Evidence, ...],
    tuple[Evidence, ...]]]``) rather than held in one structure shared
    across every claim's evidence. ``Evidence`` is a frozen, value-equal
    dataclass, so two DIFFERENT claims citing a field-identical entry
    (same url/type/label) would otherwise let one claim's validation
    outcome silently overwrite another's; keying by claim id first means a
    lookup only ever searches within that SAME claim's own results."""
    if validate is None:
        validate = evidence_mod.validate_link
    timestamp = now()
    timestamp_iso = timestamp.isoformat()
    claims = read_all(claims_path)
    _require_unique_ids(claims_path, claims)
    validated_by_claim: dict[str, tuple[tuple[Evidence, ...], tuple[Evidence, ...]]] = {
        c.id: (
            c.evidence,
            tuple(_revalidated_entry(e, validate=validate, timestamp_iso=timestamp_iso) for e in c.evidence),
        )
        for c in claims
    }

    with _write_transaction(claims_path):
        fresh_claims = read_all(claims_path)  # fresh state, not the pre-validation read
        # Re-checked against the FRESH read, not just the pre-lock one: the
        # duplicate this guard exists to refuse can be written during the
        # unlocked validation window, and the loop below looks results up in
        # `fresh_claims`. Checking only the stale read would let exactly the
        # collapse this guards against through -- both same-id claims
        # matching one map entry, so one claim's HTTP outcome (and this
        # run's `updated_at`) lands on a claim that was never validated.
        _require_unique_ids(claims_path, fresh_claims)
        updated_claims = []
        for claim in fresh_claims:
            if claim.id not in validated_by_claim:
                # Created concurrently, after this run's pre-lock validation
                # scan started -- this run never actually checked its
                # evidence, so leave it byte-for-byte unchanged (including
                # `updated_at`: stamping it would claim a validation that
                # never happened).
                updated_claims.append(claim)
                continue
            original_evidence, results = validated_by_claim[claim.id]
            carried = [i < len(original_evidence) and e == original_evidence[i] for i, e in enumerate(claim.evidence)]
            if (original_evidence or claim.evidence) and not any(carried):
                # Not one of this run's results for this claim survived --
                # either every entry it validated was changed/removed
                # concurrently, or it had nothing to validate and a
                # concurrent writer added entries this run never checked.
                # Same reasoning as the never-validated branch just above:
                # do not stamp `updated_at` for a validation that never
                # landed. See `revalidate`'s matching branch for why the
                # guard reads both tuples rather than either one alone.
                updated_claims.append(claim)
                continue
            revalidated_evidence = tuple(results[i] if carried[i] else e for i, e in enumerate(claim.evidence))
            updated_claims.append(replace(claim, evidence=revalidated_evidence, updated_at=timestamp_iso))
        _write_all(claims_path, updated_claims)
        return updated_claims


def is_stale(evidence_item: Evidence, *, now: datetime, stale_after=evidence_mod.STALE_AFTER) -> bool:
    """Whether ``evidence_item`` is overdue for re-validation -- computed
    from ``validated_at`` against ``now``, never stored (see module
    docstring). An evidence link never validated (``validated_at is None``)
    is always stale."""
    if evidence_item.validated_at is None:
        return True
    validated_at = datetime.fromisoformat(evidence_item.validated_at)
    return (now - validated_at) > stale_after


def to_dict(claim: Claim, *, now: Callable[[], datetime] = _default_now) -> dict[str, Any]:
    """The JSON-serializable shape used by both the CLI's ``--json`` output
    and the web snapshot exporter -- includes each evidence entry's
    computed ``is_stale`` (see ``is_stale``)."""
    current_time = now()
    return {
        "id": claim.id,
        "project_name": claim.project_name,
        "status": claim.status,
        "thesis": claim.thesis,
        "shipped_date": claim.shipped_date,
        "created_at": claim.created_at,
        "published_at": claim.published_at,
        "closed_at": claim.closed_at,
        "updated_at": claim.updated_at,
        "evidence": [
            {
                "type": e.type,
                "url": e.url,
                "label": e.label,
                "validated": e.validated,
                "validated_at": e.validated_at,
                "is_stale": is_stale(e, now=current_time),
            }
            for e in claim.evidence
        ],
        "edit_history": [{"thesis": v.thesis, "edited_at": v.edited_at} for v in claim.edit_history],
    }


def snapshot(
    claims_path: Path,
    *,
    status: str = "published",
    now: Callable[[], datetime] = _default_now,
) -> list[dict[str, Any]]:
    """The web dashboard's static-JSON-snapshot payload (Story 9.4): every
    claim matching ``status``, newest first by ``published_at`` (falling
    back to ``shipped_date`` for a claim with no ``published_at`` -- never
    the case for ``status="published"``, but keeps this reusable for a
    future ``status="draft"`` snapshot too). Each entry is
    ``to_dict``'s shape -- the same one the CLI's ``--json`` output uses,
    so the web tab and the CLI can never silently disagree on what a claim
    looks like."""
    matching = list_claims(claims_path, status=status)
    matching.sort(key=lambda c: c.published_at or c.shipped_date or "", reverse=True)
    return [to_dict(c, now=now) for c in matching]


def referenced_by_claims(claims_path: Path, component: str, *, aliases: Sequence[str] = ()) -> list[Claim]:
    """Story 11.3's backlink: every stored claim carrying a ``type="notice"``
    evidence entry whose ``url`` names ``component`` (or one of ``aliases``)
    -- the computed, un-persisted view a Notice's ``get`` output uses to
    show "which claims cite this" (see module docstring). Returns claims
    of any status (a draft claim can already cite a notice before it is
    published); sorted by ``created_at`` for a deterministic order across
    runs.

    ``aliases`` exists because a claim's ``Evidence.url`` for a
    ``type="notice"`` entry stores the LITERAL component name an operator
    cited at creation time, never re-resolved after a later rename
    (``notices.archive_rename``) -- without also matching every old name
    that now redirects to ``component`` (via ``notices.aliases_for``), a
    claim citing the pre-rename name would silently and permanently drop
    out of this backlink the moment the notice it cites gets renamed."""
    names = {component, *aliases}
    matching = [c for c in read_all(claims_path) if any(e.type == "notice" and e.url in names for e in c.evidence)]
    return sorted(matching, key=lambda c: c.created_at)
