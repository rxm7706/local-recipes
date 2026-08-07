"""The upstream contribution register -- pure parsing/classification
(Story 6.8, FR-58, AD-2).

AD-2's "wrap, do not absorb" decision means every real limitation in the
wrapped `bmad-loop` engine gets a Marshal-side workaround. FR-58 requires
that gap be TRACKED, not silently permanent: a tracked register lists each
upstream-shaped gap, Marshal's own compensating workaround, its upstream
status, and the Marshal FR that compensates while the gap is open.

This module is pure data/classification: no I/O, no `os`/`subprocess`/
`time`, no `pyforge.marshal.adapters` import (AD-4). `cli/upstream.py`
reads the tracked register file and `json.loads`es it; this module only
shape-validates and classifies the already-parsed value.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

UPSTREAM_STATUS_OPEN = "open"
UPSTREAM_STATUS_LANDED = "landed"

ALL_UPSTREAM_STATUSES: frozenset[str] = frozenset({UPSTREAM_STATUS_OPEN, UPSTREAM_STATUS_LANDED})

_REQUIRED_STRING_FIELDS: tuple[str, ...] = ("id", "gap", "workaround", "compensating_fr", "upstream_status")


@dataclass(frozen=True)
class UpstreamGapEntry:
    """One tracked upstream-shaped gap (Story 6.8, FR-58)."""

    id: str
    gap: str
    workaround: str
    compensating_fr: str
    upstream_status: str
    note: str | None = None


def parse_register(raw: object) -> tuple[tuple[UpstreamGapEntry, ...], tuple[str, ...]]:
    """Shape-validate an ALREADY-``json.loads``-parsed register document
    (Story 6.8, FR-58). Never raises: the top-level shape (a list, under an
    `"entries"` key or bare) and each entry's own required-string-field
    shape are both defensively checked -- a malformed top-level document
    returns `((), (error,))`; a malformed INDIVIDUAL entry is skipped and
    named in the second tuple, while every other well-formed entry still
    reports (mirrors `_read_probe_state`'s own "degrade, never crash"
    convention applied to a PARSED value instead of a read).

    `upstream_status` must be a member of `ALL_UPSTREAM_STATUSES` -- an
    unrecognized value is treated as a shape failure for that entry (this
    closed vocabulary is enforced HERE, not left for a caller to trust)."""
    if isinstance(raw, Mapping):
        candidate = raw.get("entries")
    else:
        candidate = raw
    if not isinstance(candidate, list):
        return (), ("register document is not a list (or a mapping with an 'entries' list)",)

    entries: list[UpstreamGapEntry] = []
    errors: list[str] = []
    for index, item in enumerate(candidate):
        if not isinstance(item, Mapping):
            errors.append(f"entry[{index}] is not an object")
            continue
        missing = [field for field in _REQUIRED_STRING_FIELDS if not isinstance(item.get(field), str) or not item[field]]
        if missing:
            entry_id = item.get("id") if isinstance(item.get("id"), str) else f"index {index}"
            errors.append(f"entry {entry_id!r} is missing/blank required field(s): {', '.join(missing)}")
            continue
        status = item["upstream_status"]
        if status not in ALL_UPSTREAM_STATUSES:
            errors.append(
                f"entry {item['id']!r} has an unrecognized upstream_status {status!r} "
                f"(expected one of {sorted(ALL_UPSTREAM_STATUSES)})"
            )
            continue
        note = item.get("note")
        if note is not None and not isinstance(note, str):
            errors.append(f"entry {item['id']!r}'s own 'note' field is present but not a string")
            continue
        entries.append(
            UpstreamGapEntry(
                id=item["id"],
                gap=item["gap"],
                workaround=item["workaround"],
                compensating_fr=item["compensating_fr"],
                upstream_status=status,
                note=note,
            )
        )
    return tuple(entries), tuple(errors)


def flagged_for_removal(entries: Iterable[UpstreamGapEntry]) -> tuple[UpstreamGapEntry, ...]:
    """Every entry whose `upstream_status` is `UPSTREAM_STATUS_LANDED` --
    the AC's own "an entry whose upstream status becomes landed flags its
    compensating workaround for removal", made structural. Order-preserving
    over `entries`."""
    return tuple(entry for entry in entries if entry.upstream_status == UPSTREAM_STATUS_LANDED)
