"""The waiver suppression engine: schema validation, exact finding-id
matching, expiry-awareness, and ``--bypass`` stanza emission (Story 3.2,
FR24-FR26).

Ownership decisions recorded:

* Waiver ``id`` is the SOLE match key (Design Notes): ``models.py``'s own
  docstring states finding-id stability is "what waiver matching...
  depends on" -- the id already embeds package (and version, for the vuln
  family), so no separate ``package``/``ecosystem`` schema fields exist
  here. Least-privilege (NFR-S3) falls out structurally: a glob/wildcard
  id fails the finding-id family regex, so it is rejected as malformed
  before it can ever match anything -- matching itself is always plain
  string equality, never glob/prefix semantics.
* The three finding-id family regexes are LOCALLY re-declared here
  (mirrors ``config.py``'s own precedent of locally re-declaring
  ``_SEVERITY_ORDER``/``_CONFIDENCE_RANK`` rather than importing across
  modules) -- ``models.py`` stays untouched (it is frozen; see its own
  module docstring).
* A malformed/unparsable/schema-invalid waiver file is fail-closed:
  ``cli.py`` maps ``WaiverParseError`` -> ``ErrorKind.CONFIG_PARSE`` (a YAML
  syntax/read failure) and ``WaiverValidationError`` -> ``ErrorKind.
  CONFIG_VALIDATION`` (a shape/schema failure) -- ``ErrorKind`` is a closed
  enum (see ``models.py``), so this module reuses those two members rather
  than growing it. A missing file is normal (empty waiver set, no error) --
  mirrors ``config.py``'s own missing-file handling.
* Expiry comparisons take ``now: datetime`` as an explicit parameter, never
  calling ``datetime.now()`` internally -- mirrors ``vuln.is_db_stale``'s
  testability convention. Exactly-at-the-boundary is NOT expired (a strict
  inequality), the same boundary rule ``vuln.is_db_stale`` uses for
  staleness.
* ``apply_waivers``/``bypass_blocking``/``warn_blocking`` only ever rewrite
  a rung's ``Status`` to ``BYPASSED``/``WARN`` (or leave it untouched) --
  never import a private ``verdict.py`` name, call an exit primitive with
  a guarded literal, or spell out the 7-rung lattice order
  (``tests/meta/test_verdict_sole_ownership.py`` enforces this for every
  non-``verdict.py`` module, this one included).
* This module reads/writes YAML as DATA: ``yaml.safe_load``/``yaml.
  safe_dump`` only, never ``yaml.load``/``yaml.unsafe_load``, never
  string-concatenation (NFR-S4/D1) -- no I/O beyond reading the one
  candidate file, no subprocess, no network, no exec.
* Story 3.3 (FR23/FR25 -- waiver-expiry visibility + the ``--warn-only``
  adoption on-ramp): ``apply_waivers`` now returns a 3-tuple -- the rungs,
  applied notices (unchanged), and a NEW ``expired_notices`` list, one per
  expired exact-id match (the rung itself is still left untouched -- the
  already-correct re-block fall-through is unchanged; this only makes it
  visible for review). ``warn_blocking`` is the ``--warn-only`` mechanism:
  a ``bypass_blocking``-shaped rewrite targeting ``{Status.
  POLICY_VIOLATION, Status.INDETERMINATE}`` -> ``Status.WARN`` (never
  ``Status.ERROR``), returning both the updated rungs and how many it
  actually rewrote -- ``cli.py`` threads that count into the text report's
  graduate-to-enforcing nudge (see ``report.py``'s own docstring for the
  nudge's precise gating rule).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from .models import Status, StatusDriver

# The three finding-ID families, mirrored verbatim from models.py's own
# copy (locally re-declared per this module's docstring -- models.py is
# frozen and must not be imported across for this). Matched with
# .fullmatch; "[^:\n]" (not "[^:]") so an id can never embed a newline.
_FINDING_ID_FAMILIES = (
    re.compile(r"vuln:[^:\n]+:.+@.+"),
    re.compile(r"hygiene:[^:\n]+:.+"),
    re.compile(r"indeterminate:[^:\n]+:.+"),
)

_SUPPORTED_VERSION = 1
_MAX_REASON_LENGTH = 1000
# Review finding: authorized_by is a username/handle, not free text -- a
# much narrower bound than reason's, kept symmetric in KIND (both are
# length-bounded) rather than in VALUE.
_MAX_AUTHORIZED_BY_LENGTH = 200
_REQUIRED_ENTRY_FIELDS = ("id", "reason", "authorized_by", "accepted_at", "expires_at")

# Rungs already at or below "suppressed"/"inapplicable" have nothing left to
# waive -- never rewritten by apply_waivers/bypass_blocking.
_NON_BLOCKING_STATUSES = frozenset(
    {Status.CLEAN, Status.NOT_APPLICABLE, Status.BYPASSED}
)


class WaiverError(ValueError):
    """Base for this module's typed errors (mirrors ``config.py``'s
    ``_ConfigError`` shape: one common base, two subclasses splitting a
    syntax failure from a shape/schema failure)."""


class WaiverParseError(WaiverError):
    """Malformed/unreadable YAML in ``.warden-waivers.yaml`` -- ``cli.py``
    maps this to ``ErrorKind.CONFIG_PARSE``, ``owner="waiver"``."""


class WaiverValidationError(WaiverError):
    """A shape/schema-invalid waiver document (unknown/missing ``version``,
    a non-family or duplicate id, an oversized ``reason``, ``expires_at <=
    accepted_at``, ...) -- ``cli.py`` maps this to ``ErrorKind.
    CONFIG_VALIDATION``, ``owner="waiver"``."""


@dataclass(frozen=True)
class WaiverEntry:
    """One waiver stanza entry: ``id`` exact-matches a ``Finding.id`` (one
    of the three families -- see the module docstring); ``accepted_at``/
    ``expires_at`` are ISO-8601 strings carrying a UTC offset (validated
    aware-and-parsable at load time)."""

    id: str
    reason: str
    authorized_by: str
    accepted_at: str
    expires_at: str


@dataclass(frozen=True)
class WaiverFile:
    """The whole validated ``.warden-waivers.yaml`` document."""

    version: int
    waivers: tuple[WaiverEntry, ...]


@dataclass(frozen=True)
class WaiverNotice:
    """One waiver that actually suppressed a finding THIS run -- echoed in
    ``--format text`` output (NFR-S3)."""

    id: str
    reason: str
    authorized_by: str
    expires_at: str


def _is_finding_family_id(value: str) -> bool:
    """Whether ``value`` matches one of the three finding-id families --
    the SAME structural check that rejects a wildcard/glob/prefix id as
    malformed (see the module docstring)."""
    return any(family.fullmatch(value) for family in _FINDING_ID_FAMILIES)


def _parse_timestamp(
    value: object, *, path: Path, index: int, field: str
) -> tuple[datetime, str]:
    """Returns ``(parsed, normalized_str)``. Review finding: PyYAML's own
    implicit timestamp resolver turns an UNQUOTED ISO-8601-looking scalar
    (the obvious way to hand-author one) into a native ``datetime.datetime``,
    not a ``str`` -- accepted here directly rather than rejected with a
    confusing "got datetime.datetime(...)" message; ``normalized_str`` is
    what ``WaiverEntry``'s ``str``-typed field stores either way (a quoted
    string round-trips as itself, an unquoted one is re-rendered via
    ``.isoformat()``)."""
    if isinstance(value, datetime):
        parsed = value
        normalized = value.isoformat()
    elif isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise WaiverValidationError(
                f"{path}: waivers[{index}].{field} is not a valid ISO-8601 "
                f"timestamp: {value!r}"
            ) from exc
        normalized = value
    else:
        raise WaiverValidationError(
            f"{path}: waivers[{index}].{field} must be a non-empty ISO-8601 "
            f"string, got {value!r}"
        )
    if parsed.tzinfo is None:
        raise WaiverValidationError(
            f"{path}: waivers[{index}].{field} must carry a UTC offset (a "
            f"naive timestamp is unsafe to compare), got {value!r}"
        )
    return parsed, normalized


def _validate_entry(raw_entry: object, *, path: Path, index: int) -> WaiverEntry:
    if not isinstance(raw_entry, dict):
        raise WaiverValidationError(
            f"{path}: waivers[{index}] must be a mapping, got "
            f"{type(raw_entry).__name__}"
        )
    missing = [field for field in _REQUIRED_ENTRY_FIELDS if field not in raw_entry]
    if missing:
        raise WaiverValidationError(
            f"{path}: waivers[{index}] missing required field(s): {missing}"
        )
    entry_id = raw_entry["id"]
    if not isinstance(entry_id, str) or not entry_id:
        raise WaiverValidationError(
            f"{path}: waivers[{index}].id must be a non-empty string, got "
            f"{entry_id!r}"
        )
    if not _is_finding_family_id(entry_id):
        raise WaiverValidationError(
            f"{path}: waivers[{index}].id {entry_id!r} matches none of the "
            "three finding-id families (no wildcard/glob/prefix matching, "
            "ever)"
        )
    reason = raw_entry["reason"]
    if not isinstance(reason, str):
        raise WaiverValidationError(
            f"{path}: waivers[{index}].reason must be a string, got "
            f"{type(reason).__name__}"
        )
    if len(reason) > _MAX_REASON_LENGTH:
        raise WaiverValidationError(
            f"{path}: waivers[{index}].reason exceeds {_MAX_REASON_LENGTH} "
            "characters"
        )
    authorized_by = raw_entry["authorized_by"]
    if not isinstance(authorized_by, str) or not authorized_by:
        raise WaiverValidationError(
            f"{path}: waivers[{index}].authorized_by must be a non-empty "
            f"string, got {authorized_by!r}"
        )
    if len(authorized_by) > _MAX_AUTHORIZED_BY_LENGTH:
        raise WaiverValidationError(
            f"{path}: waivers[{index}].authorized_by exceeds "
            f"{_MAX_AUTHORIZED_BY_LENGTH} characters"
        )
    accepted_at, accepted_at_str = _parse_timestamp(
        raw_entry["accepted_at"], path=path, index=index, field="accepted_at"
    )
    expires_at, expires_at_str = _parse_timestamp(
        raw_entry["expires_at"], path=path, index=index, field="expires_at"
    )
    if expires_at <= accepted_at:
        raise WaiverValidationError(
            f"{path}: waivers[{index}].expires_at must be after accepted_at"
        )
    return WaiverEntry(
        id=entry_id,
        reason=reason,
        authorized_by=authorized_by,
        accepted_at=accepted_at_str,
        expires_at=expires_at_str,
    )


def _validate_document(document: object, *, path: Path) -> WaiverFile:
    if document is None:
        # An empty file (or one that is only comments) parses to None --
        # treated identically to an empty mapping (still missing `version`,
        # never guessed).
        document = {}
    if not isinstance(document, dict):
        raise WaiverValidationError(
            f"{path}: waiver file must be a mapping, got {type(document).__name__}"
        )
    version = document.get("version")
    # Review finding: `1.0 != 1` is False in Python, so a YAML float would
    # silently pass an `isinstance(version, bool) or version != 1` check --
    # `type(version) is not int` (never `isinstance`, which bool subclasses
    # int through) is the only check that actually enforces "the literal
    # int 1, nothing else".
    if type(version) is not int or version != _SUPPORTED_VERSION:
        raise WaiverValidationError(
            f"{path}: 'version' must be the literal int {_SUPPORTED_VERSION}, "
            f"got {version!r}"
        )
    raw_waivers = document.get("waivers", [])
    if not isinstance(raw_waivers, list):
        raise WaiverValidationError(
            f"{path}: 'waivers' must be a list, got {type(raw_waivers).__name__}"
        )
    entries: list[WaiverEntry] = []
    seen_ids: set[str] = set()
    for index, raw_entry in enumerate(raw_waivers):
        entry = _validate_entry(raw_entry, path=path, index=index)
        if entry.id in seen_ids:
            raise WaiverValidationError(
                f"{path}: duplicate waiver id {entry.id!r} (waivers[{index}])"
            )
        seen_ids.add(entry.id)
        entries.append(entry)
    return WaiverFile(version=version, waivers=tuple(entries))


def load_waivers(path: Path) -> tuple[WaiverEntry, ...]:
    """Load + validate ``.warden-waivers.yaml`` at ``path``.

    A missing file is normal (empty tuple, no error) -- mirrors
    ``config.py``'s own missing-file handling (``path.is_file()``, same
    precedent: a candidate side-file relative to the scan target, not the
    scan-target argument itself -- ``cli.py``'s own top-level target check
    is a stricter, separate concern this module does not mirror). Raises
    ``WaiverParseError`` for an unreadable/malformed-YAML file,
    ``WaiverValidationError`` for a shape/schema problem (unknown/missing
    ``version``, a non-family or duplicate id, an oversized ``reason``,
    ``expires_at <= accepted_at``, ...). ``yaml.safe_load`` only -- never
    ``yaml.load``/``yaml.unsafe_load`` (NFR-S4/D1)."""
    if not path.is_file():
        return ()
    try:
        with path.open("r", encoding="utf-8") as handle:
            document = yaml.safe_load(handle)
    except (yaml.YAMLError, UnicodeDecodeError, RecursionError, OSError) as exc:
        raise WaiverParseError(f"{path}: cannot read or parse: {exc}") from exc
    return _validate_document(document, path=path).waivers


def _is_expired(expires_at: str, *, now: datetime) -> bool:
    """Strict-inequality boundary (mirrors ``vuln.is_db_stale``): exactly
    at ``expires_at`` is NOT expired."""
    return now > datetime.fromisoformat(expires_at)


def _waiver_notice(waiver: WaiverEntry) -> WaiverNotice:
    """Factor the ``WaiverNotice`` construction shared between
    ``apply_waivers``'s applied and expired branches (Story 3.3)."""
    return WaiverNotice(
        id=waiver.id,
        reason=waiver.reason,
        authorized_by=waiver.authorized_by,
        expires_at=waiver.expires_at,
    )


def apply_waivers(
    rungs: Sequence[tuple[Status, StatusDriver | None]],
    waivers: Sequence[WaiverEntry],
    *,
    now: datetime,
) -> tuple[
    list[tuple[Status, StatusDriver | None]],
    list[WaiverNotice],
    list[WaiverNotice],
]:
    """Exact finding-id match + not-expired -> rewrite that rung's
    ``Status`` to ``BYPASSED`` and collect an applied notice; exact match +
    expired -> the rung is left UNTOUCHED (the already-correct re-block
    fall-through -- unchanged from pre-3.3) and an expired notice is
    collected instead (Story 3.3 -- makes that fall-through visible for
    review); no match at all -> untouched, no notice either way. Returns
    ``(rungs, applied_notices, expired_notices)``; both notice lists are
    deduplicated by waiver id and sorted by id."""
    by_id = {waiver.id: waiver for waiver in waivers}
    updated: list[tuple[Status, StatusDriver | None]] = []
    applied: dict[str, WaiverNotice] = {}
    expired: dict[str, WaiverNotice] = {}
    for status, driver in rungs:
        waiver = by_id.get(driver.finding_id) if driver is not None else None
        if waiver is not None and status not in _NON_BLOCKING_STATUSES:
            if _is_expired(waiver.expires_at, now=now):
                updated.append((status, driver))
                expired.setdefault(waiver.id, _waiver_notice(waiver))
            else:
                updated.append((Status.BYPASSED, driver))
                applied.setdefault(waiver.id, _waiver_notice(waiver))
        else:
            updated.append((status, driver))
    return (
        updated,
        sorted(applied.values(), key=lambda notice: notice.id),
        sorted(expired.values(), key=lambda notice: notice.id),
    )


def bypass_blocking(
    rungs: Sequence[tuple[Status, StatusDriver | None]],
) -> list[tuple[Status, StatusDriver | None]]:
    """``--bypass``: force every still-non-clean, Finding-backed rung
    (never an ``error:...``-driven rung, whose id matches none of the three
    finding-id families) to ``BYPASSED`` -- the CLI's blanket suppression,
    distinct from a real waiver file's exact-id matching in
    ``apply_waivers``."""
    return [
        (
            Status.BYPASSED
            if driver is not None
            and status not in _NON_BLOCKING_STATUSES
            and _is_finding_family_id(driver.finding_id)
            else status,
            driver,
        )
        for status, driver in rungs
    ]


# --warn-only downgrades EXACTLY these two still-blocking statuses to WARN
# -- never Status.ERROR (a tool malfunction must always surface honestly
# regardless of adoption mode), never an already non-blocking/WARN rung. A
# 2-element frozenset, not the full 7-status lattice order (guard-safe --
# see tests/meta/test_verdict_sole_ownership.py).
_WARN_ONLY_DOWNGRADE_STATUSES = frozenset(
    {Status.POLICY_VIOLATION, Status.INDETERMINATE}
)


def warn_blocking(
    rungs: Sequence[tuple[Status, StatusDriver | None]],
) -> tuple[list[tuple[Status, StatusDriver | None]], int]:
    """``--warn-only`` (Story 3.3, FR23/FR25): downgrade every still-
    blocking, Finding-backed rung (``POLICY_VIOLATION``/``INDETERMINATE``)
    to ``WARN`` -- mirrors ``bypass_blocking``'s shape (including its
    ``driver is not None`` defense-in-depth guard) but targets ``WARN``
    instead of ``BYPASSED`` and this module's narrow 2-status set instead
    of ``_NON_BLOCKING_STATUSES``'s complement. Deliberately sweeps EVERY
    ``INDETERMINATE`` cause it sees (including the D2(c) empty-extraction
    rung and any other generic ``indeterminate:<reason>:<pkg>`` cause) --
    a broad, adoption-oriented sweep per this story's own intent, not a
    curated per-driver allowlist (unlike ``--allow-empty``'s narrow,
    single-driver exit-code exception, which this is NOT the same
    mechanism as).

    Called in ``cli.py`` AFTER the existing ``apply_waivers``/``--bypass``
    block, so a waiver still shows as ``bypassed`` distinctly and
    warn-only only mops up whatever is still blocking. Returns the updated
    rungs AND how many DISTINCT findings were actually rewritten -- counted
    by ``finding_id``, not by rung, since ``interfaces.py``'s per-component
    ``indeterminate:<reason>:<name>`` id carries no version segment: two
    components sharing a name at different versions (``inventory.py``'s
    documented "distinct versions stay distinct" merge policy) landing on
    the same reason/token produce two rungs referencing the SAME one
    ``Finding`` (itself already deduped by id in ``interfaces.py``) -- a
    raw per-rung counter would overcount relative to ``report.findings``.
    The text report's graduate-to-enforcing nudge names this exact,
    finding-deduped count, never the report's total finding count (which
    would also include findings warn-only never touched)."""
    updated: list[tuple[Status, StatusDriver | None]] = []
    downgraded_ids: set[str] = set()
    for status, driver in rungs:
        if driver is not None and status in _WARN_ONLY_DOWNGRADE_STATUSES:
            updated.append((Status.WARN, driver))
            downgraded_ids.add(driver.finding_id)
        else:
            updated.append((status, driver))
    return updated, len(downgraded_ids)


def emit_bypass_stanza(
    rungs: Sequence[tuple[Status, StatusDriver | None]],
    *,
    reason: str,
    authorized_by: str,
    accepted_at: datetime,
    expiry_days: int,
) -> str:
    """One ``.warden-waivers.yaml``-ready stanza entry per still-non-clean,
    Finding-backed rung -- ``yaml.safe_dump`` only (NFR-S4/D1), never
    string concatenation. Printed to stdout for a human to commit; this
    tool never writes it into the scanned repository tree itself."""
    ids = sorted(
        {
            driver.finding_id
            for status, driver in rungs
            if driver is not None
            and status not in _NON_BLOCKING_STATUSES
            and _is_finding_family_id(driver.finding_id)
        }
    )
    expires_at = accepted_at + timedelta(days=expiry_days)
    document = {
        "version": _SUPPORTED_VERSION,
        "waivers": [
            {
                "id": finding_id,
                "reason": reason,
                "authorized_by": authorized_by,
                "accepted_at": accepted_at.isoformat(),
                "expires_at": expires_at.isoformat(),
            }
            for finding_id in ids
        ],
    }
    return yaml.safe_dump(document, sort_keys=False)
