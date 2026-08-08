"""Success-claim local storage (Story 9.1, scaled down).

The original Epic 9 spec (`epics-with-stories.md` lines 577-654) assumes a
live PostgreSQL/SQLite database reached via SQLAlchemy + Alembic
migrations. Nothing in this package has ever hosted a database or a
server -- Herald is a stateless CLI plus a static web dashboard. Per the
2026-08-08 scope decision recorded in
`docs/dreams/herald-moments-2-4-live-backend.md`, this module instead
persists ``Claim`` records as one JSON array file
(``.herald/claims.json``, ``DEFAULT_CLAIMS_PATH``), written atomically
(temp file + ``os.replace``) -- the same crash-safety convention
``state.py`` already uses for ``.herald/bridge-state.json``.

**JSON array, not slug-keyed object.** ``state.py``'s document is an
object keyed by deck slug because a slug is a stable natural key one
caller already knows before it reads. A claim has no equivalent
caller-known key before creation (its ``id`` is minted by ``create``
itself), so the document is a plain JSON array of claim objects instead.

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
recomputing "who cites this component" from the claims file at read time
means the two files can never drift out of sync with each other the way a
second stored copy of the same fact could.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from . import errors
from . import evidence as evidence_mod

DEFAULT_CLAIMS_PATH = Path(".herald/claims.json")
"""Default location, relative to a repo root the caller resolves (mirrors
``state.DEFAULT_STATE_PATH``)."""

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
    the document -- mirrors ``state._reject_duplicate_keys``; ``json.load``
    applies this to every nested object, not just the top level."""
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError(f"duplicate key {key!r}")
        document[key] = value
    return document


def _load_document(claims_path: Path) -> list[object]:
    """The whole claims file as a list, or ``[]`` when the file does not
    exist yet. Raises ``errors.HeraldError`` naming ``claims_path`` for any
    structural failure (AD-6) -- malformed JSON, an unreadable file, or a
    non-list top level."""
    try:
        with claims_path.open(encoding="utf-8") as fh:
            document = json.load(fh, object_pairs_hook=_reject_duplicate_keys)
    except FileNotFoundError:
        return []
    except (ValueError, OSError, RecursionError) as exc:
        raise errors.HeraldError(
            f"claims file {claims_path} could not be read: {exc}"
        ) from exc
    if not isinstance(document, list):
        raise errors.HeraldError(
            f"claims file {claims_path} does not hold a JSON array at its top level"
        )
    return document


def _evidence_from_dict(claims_path: Path, claim_id: object, entry: object) -> Evidence:
    malformed = f"claims file {claims_path} has a malformed evidence entry for claim {claim_id!r}"
    if not isinstance(entry, dict):
        raise errors.HeraldError(f"{malformed}: entry is not a JSON object")
    unknown = sorted(set(entry) - _EVIDENCE_FIELDS)
    if unknown:
        raise errors.HeraldError(
            f"{malformed}: unknown field(s) {', '.join(map(repr, unknown))}"
        )
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


def _thesis_version_from_dict(
    claims_path: Path, claim_id: object, entry: object
) -> ThesisVersion:
    malformed = f"claims file {claims_path} has a malformed edit_history entry for claim {claim_id!r}"
    if not isinstance(entry, dict):
        raise errors.HeraldError(f"{malformed}: entry is not a JSON object")
    unknown = sorted(set(entry) - _THESIS_VERSION_FIELDS)
    if unknown:
        raise errors.HeraldError(
            f"{malformed}: unknown field(s) {', '.join(map(repr, unknown))}"
        )
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
        raise errors.HeraldError(
            f"{malformed} ({entry.get('id')!r}): unknown field(s) {', '.join(map(repr, unknown))}"
        )
    try:
        claim_id = entry["id"]
        evidence = tuple(
            _evidence_from_dict(claims_path, claim_id, item)
            for item in entry.get("evidence", [])
        )
        edit_history = tuple(
            _thesis_version_from_dict(claims_path, claim_id, item)
            for item in entry.get("edit_history", [])
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


def _write_all(claims_path: Path, claims: Sequence[Claim]) -> None:
    """Persist the whole claims list atomically -- temp file in the same
    directory, then ``os.replace`` (mirrors ``state.write``'s crash-safety
    discipline, including its limit: no ``fsync``)."""
    document = [
        {
            "id": c.id,
            "project_name": c.project_name,
            "status": c.status,
            "thesis": c.thesis,
            "shipped_date": c.shipped_date,
            "created_at": c.created_at,
            "published_at": c.published_at,
            "closed_at": c.closed_at,
            "updated_at": c.updated_at,
            "evidence": [
                {
                    "type": e.type,
                    "url": e.url,
                    "label": e.label,
                    "validated": e.validated,
                    "validated_at": e.validated_at,
                }
                for e in c.evidence
            ],
            "edit_history": [
                {"thesis": v.thesis, "edited_at": v.edited_at} for v in c.edit_history
            ],
        }
        for c in claims
    ]
    could_not_write = f"claims could not be written to {claims_path}"
    try:
        claims_path.parent.mkdir(parents=True, exist_ok=True)
        handle, tmp_name = tempfile.mkstemp(
            dir=claims_path.parent, prefix=f".{claims_path.name}-", suffix=".tmp"
        )
    except OSError as exc:
        raise errors.HeraldError(f"{could_not_write}: {exc}") from exc
    try:
        try:
            fh = os.fdopen(handle, "w", encoding="utf-8")
        except BaseException:
            os.close(handle)
            raise
        with fh:
            json.dump(document, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp_name, claims_path)
    except BaseException as exc:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        if isinstance(exc, (OSError, TypeError, ValueError, RecursionError)):
            raise errors.HeraldError(f"{could_not_write}: {exc}") from exc
        raise


def read_all(claims_path: Path) -> list[Claim]:
    """Every claim currently stored, in file order."""
    return [
        _claim_from_dict(claims_path, entry) for entry in _load_document(claims_path)
    ]


def read_one(claims_path: Path, claim_id: str) -> Claim:
    """``claim_id``'s stored claim. Raises ``errors.ClaimNotFoundError``
    when no claim with that id exists.

    Decodes each raw entry lazily rather than via ``read_all`` -- an
    unrelated malformed entry elsewhere in the file must not block looking
    up a claim whose own entry is perfectly healthy. An entry whose ``id``
    field itself can't even be read cheaply is skipped rather than
    aborting the whole lookup; only the matched entry's own malformation
    (if it turns out to be the requested id) still raises, preserving
    AD-6 for the one entry that's actually relevant."""
    for entry in _load_document(claims_path):
        if isinstance(entry, dict) and entry.get("id") == claim_id:
            return _claim_from_dict(claims_path, entry)
    raise errors.ClaimNotFoundError(f"no claim found with id {claim_id!r}")


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
    and returns it."""
    if not project_name.strip():
        raise errors.HeraldError("project_name must not be empty")
    for e in evidence:
        if e.type not in EVIDENCE_TYPES:
            raise errors.HeraldError(
                f"evidence type {e.type!r} must be one of {EVIDENCE_TYPES}"
            )
    timestamp = now().isoformat()
    claim = Claim(
        id=id_factory(),
        project_name=project_name,
        status="draft",
        thesis=None,
        shipped_date=shipped_date if shipped_date is not None else today().isoformat(),
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
    make ``evidence.validate_for_publish`` unpatchable from a test."""
    if validate is None:
        validate = evidence_mod.validate_for_publish
    claims = read_all(claims_path)
    index = next((i for i, c in enumerate(claims) if c.id == claim_id), None)
    if index is None:
        raise errors.ClaimNotFoundError(f"no claim found with id {claim_id!r}")
    claim = claims[index]
    if claim.status != "draft":
        raise errors.ClaimStateError(
            f"claim {claim_id!r} is already {claim.status!r}; only a draft claim can be published"
        )
    final_thesis = thesis if thesis is not None else claim.thesis
    if not final_thesis:
        raise errors.HeraldError(
            f"claim {claim_id!r} has no thesis; supply --thesis to publish"
        )
    timestamp = now()
    broken: list[str] = []
    for e in claim.evidence:
        if e.type == "notice":
            # A "notice" evidence entry's `url` holds a Notice component
            # name, not an HTTP URL (see module docstring) -- nothing to
            # HEAD, so it is trivially valid rather than run through the
            # HTTP-based `validate`.
            continue
        try:
            validate(e.url)
        except errors.EvidenceLinkError as exc:
            broken.append(f"{e.url} ({exc})")
    if broken:
        # Regression: raising on the FIRST broken link meant an operator
        # fixing evidence one publish-attempt at a time hit the next
        # broken link on each retry instead of seeing the full list once.
        raise errors.EvidenceLinkError(
            f"claim {claim_id!r} has {len(broken)} broken evidence link(s): "
            f"{'; '.join(broken)}. Fix or remove before publishing."
        )
    validated_evidence = tuple(
        replace(e, validated=True, validated_at=timestamp.isoformat())
        for e in claim.evidence
    )
    edit_history = claim.edit_history
    if claim.thesis is not None and claim.thesis != final_thesis:
        edit_history = (
            *edit_history,
            ThesisVersion(thesis=claim.thesis, edited_at=timestamp.isoformat()),
        )
    updated = replace(
        claim,
        status="published",
        thesis=final_thesis,
        published_at=timestamp.isoformat(),
        updated_at=timestamp.isoformat(),
        evidence=validated_evidence,
        edit_history=edit_history,
    )
    claims[index] = updated
    _write_all(claims_path, claims)
    return updated


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
    parameter default."""
    if validate is None:
        validate = evidence_mod.validate_link
    claims = read_all(claims_path)
    index = next((i for i, c in enumerate(claims) if c.id == claim_id), None)
    if index is None:
        raise errors.ClaimNotFoundError(f"no claim found with id {claim_id!r}")
    claim = claims[index]
    timestamp = now()
    revalidated_evidence = tuple(
        _revalidated_entry(e, validate=validate, timestamp_iso=timestamp.isoformat())
        for e in claim.evidence
    )
    updated = replace(
        claim, evidence=revalidated_evidence, updated_at=timestamp.isoformat()
    )
    claims[index] = updated
    _write_all(claims_path, claims)
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
    parameter default."""
    if validate is None:
        validate = evidence_mod.validate_link
    timestamp = now()
    claims = read_all(claims_path)
    updated_claims = []
    for claim in claims:
        revalidated_evidence = tuple(
            _revalidated_entry(
                e, validate=validate, timestamp_iso=timestamp.isoformat()
            )
            for e in claim.evidence
        )
        updated_claims.append(
            replace(
                claim, evidence=revalidated_evidence, updated_at=timestamp.isoformat()
            )
        )
    _write_all(claims_path, updated_claims)
    return updated_claims


def is_stale(
    evidence_item: Evidence, *, now: datetime, stale_after=evidence_mod.STALE_AFTER
) -> bool:
    """Whether ``evidence_item`` is overdue for re-validation -- computed
    from ``validated_at`` against ``now``, never stored (see module
    docstring). An evidence link never validated (``validated_at is None``)
    is always stale."""
    if evidence_item.validated_at is None:
        return True
    validated_at = datetime.fromisoformat(evidence_item.validated_at)
    return (now - validated_at) > stale_after


def to_dict(
    claim: Claim, *, now: Callable[[], datetime] = _default_now
) -> dict[str, Any]:
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
        "edit_history": [
            {"thesis": v.thesis, "edited_at": v.edited_at} for v in claim.edit_history
        ],
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


def referenced_by_claims(claims_path: Path, component: str) -> list[Claim]:
    """Story 11.3's backlink: every stored claim carrying a ``type="notice"``
    evidence entry whose ``url`` names ``component`` -- the computed,
    un-persisted view a Notice's ``get`` output uses to show "which claims
    cite this" (see module docstring). Returns claims of any status (a
    draft claim can already cite a notice before it is published); sorted
    by ``created_at`` for a deterministic order across runs."""
    matching = [
        c
        for c in read_all(claims_path)
        if any(e.type == "notice" and e.url == component for e in c.evidence)
    ]
    return sorted(matching, key=lambda c: c.created_at)
