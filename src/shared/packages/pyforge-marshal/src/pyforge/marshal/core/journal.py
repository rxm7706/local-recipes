"""Run identity minting and the pure journal-entry-shaping core (Story 3.1,
architecture spine AD-25/AD-28/AD-30).

Marshal has no run concept at all before this module: nine loop homes share
one canonical Tier-3 store, and without a Marshal-owned run identifier and a
durable, concurrency-safe append protocol they would either collide on an
externally-minted id or corrupt a shared journal file under concurrent
writers -- the exact incident AD-25/AD-28/AD-30 exist to prevent.

``mint_run_id`` mints AD-25's ``<slug>-<utc-compact>-<random>`` run id.
``Phase``/``JournalEntryId``/``JournalEntry``/``build_entry`` are the
pure entry-shaping core: AD-28's three-valued phase vocabulary, the
composite ``(writer_id, counter)`` id (a per-writer monotonic counter, never
a per-run one -- AD-30 mandates a lock-free ``O_APPEND`` protocol with two
concurrent writers by design, and no coordination-free way exists to mint a
unique per-run integer), and the entry itself with its ``intent_id``
invariant enforced at construction. ``SIDECAR_THRESHOLD_BYTES``/
``PreparedWrite``/``prepare_for_write`` are AD-30's 4 KiB sidecar-blob
decision: a payload that would make one journal line too large is rewritten
to a ``{"sidecar_ref": ...}`` pointer, with the original payload text
returned separately for the caller to write to that path.

Every clock reading, random token, and writer id is a fact the CALLER
already gathered and passes in -- mirroring ``core/egress.py::
build_gate_record``'s "already-obtained timestamp" convention exactly. This
module does no I/O, no subprocess, no clock read (AD-4): the physical
append/mkdir protocols this module's output feeds live on ``FsPort``/
``LocalFs`` instead (``ports/fs.py``'s ``append_line``/
``create_dir_exclusive``, Story 3.1's other half).

**No CLI wiring, again.** No ``marshal run``/``marshal launch`` command
exists anywhere in the codebase yet (confirmed live: ``find src -iname
'*journal*'`` returned nothing before this story) -- that is Story 3.3
(``Detached launch with scoped story selection``, ``backlog``). This is the
fourth consecutive story (after 2.4, 2.5, 2.6) to ship a fully-tested pure
mechanism with zero real caller; here it is structural, not a pattern of
convenience -- this module is its OWN prerequisite for every later Epic-3
story (3.2's fold, 3.3's launch, 3.4's supervisor), so nothing in the tree
can call it yet. See ``deferred-work.md`` for the tracked follow-ups.

This module implements neither the journal's READ side (the fold,
quarantine-on-malformed-line, ``unevaluable`` scoping -- Story 3.2's own
title and AC set) nor AD-25's ``sessions/`` namespace (no session concept
exists anywhere in this codebase today; logged as a follow-up).

This module is pure data: no I/O, no subprocess, no network, no clock, no
``pyforge.marshal.adapters`` import (AD-4) -- only ``copy``, ``json``,
``re``, ``collections.abc``, ``dataclasses``, ``datetime``, ``enum``, and
this package's own ``.identity``/``.policy``.
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from . import policy
from .identity import StoryKey

# AD-28's three-valued phase vocabulary. The earlier two-valued set forced
# gate verdicts, story transitions, and other non-outcome facts into
# `outcome`, which then required a mandatory `intent_id` that does not exist
# for any of them -- `observation` records something true without claiming
# an action was attempted, and carries no `intent_id`.
class Phase(StrEnum):
    """AD-28's three-valued journal-entry vocabulary. Defined HERE, not
    ``core/model.py``, since nothing outside this story's own surface
    consumes it yet."""

    INTENT = "intent"
    OUTCOME = "outcome"
    OBSERVATION = "observation"


# `writer_id` becomes part of a sidecar blob filename (`prepare_for_write`),
# so its charset is filesystem-safe by construction, not merely "any str".
_WRITER_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

# AD-25's compact millisecond-UTC form: YYYYMMDDTHHMMSSmmmZ, e.g.
# "20260803T054512123Z". Fixed-width only -- mint_run_id treats this as an
# opaque, already-formatted sort key (a caller-supplied fact, AD-4), not a
# value to parse or calendar-validate; correctness of its underlying instant
# is the caller's concern, the same way `build_gate_record` never validates
# that a caller-supplied `tree_revision` names a real commit.
_UTC_COMPACT_PATTERN = re.compile(r"^[0-9]{8}T[0-9]{6}[0-9]{3}Z$")

_RANDOM_TOKEN_PATTERN = re.compile(r"^[a-z0-9]+$")

# Stricter than `core/egress.py::_TIMESTAMP_PATTERN`, deliberately: journal
# entries ARE string-sorted against each other (AD-28's total order is
# `(ts, writer_id, counter)`, comparing `ts` AS TEXT), while gate records
# never are. Two legitimate spellings of the same instant would sort
# inconsistently relative to a canonically-spelled peer -- silently
# violating the total order Story 3.2's fold depends on. One canonical
# spelling -- `T`/`Z` only, exactly 3 fractional digits -- closes that gap
# at write time. NOT imported from `core/egress.py`: that pattern is
# module-private and answers a different, looser question.
_ENTRY_TIMESTAMP_PATTERN = re.compile(
    r"^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])"
    r"T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]\.[0-9]{3}Z$"
)

SIDECAR_THRESHOLD_BYTES = 4096


def mint_run_id(slug: str, utc_compact: str, random_token: str) -> str:
    """AD-25's run-id minting: ``f"{slug}-{utc_compact}-{random_token}"``,
    the ``<slug>-<utc-compact>-<random>`` form, minted at ``intent`` time
    before any spawn -- globally unique, sortable chronologically WITHIN a
    slug (never across the fleet -- fleet-wide chronology sorts on a
    record's ``ts``, never on the id).

    ``slug`` is validated via ``core.policy._is_valid_project_slug`` -- the
    SAME check ``cli/init.py`` already reuses three times, so no second slug
    regex exists in this package. ``utc_compact`` must match the fixed-width
    compact millisecond-UTC pattern ``YYYYMMDDTHHMMSSmmmZ`` (e.g.
    ``"20260803T054512123Z"``). ``random_token`` must be a non-empty
    lowercase-alphanumeric ``str``. Every argument is a fact the CALLER
    already gathered (AD-4) -- this function reads no clock and generates no
    randomness. Raises ``ValueError`` naming the malformed component for any
    of the three."""
    if not isinstance(slug, str) or not policy._is_valid_project_slug(slug):
        raise ValueError(f"slug must be a valid project slug, got {slug!r}")
    if not isinstance(utc_compact, str) or not _UTC_COMPACT_PATTERN.match(utc_compact):
        raise ValueError(
            "utc_compact must match the compact millisecond-UTC pattern "
            f"YYYYMMDDTHHMMSSmmmZ (e.g. '20260803T054512123Z'), got {utc_compact!r}"
        )
    if not isinstance(random_token, str) or not _RANDOM_TOKEN_PATTERN.match(random_token):
        raise ValueError(
            "random_token must be a non-empty lowercase-alphanumeric str, "
            f"got {random_token!r}"
        )
    return f"{slug}-{utc_compact}-{random_token}"


@dataclass(frozen=True, order=True)
class JournalEntryId:
    """The composite id ``(writer_id, counter)`` (AD-28): ``writer_id`` is
    unique per appending process (a supervisor, a CLI invocation), and
    ``counter`` is monotonic WITHIN that writer -- never across the run.
    AD-30 mandates a lock-free ``O_APPEND`` protocol with two concurrent
    writers by design, and no coordination-free way exists to mint a unique
    per-run integer, so this is the only achievable id shape.

    ``order=True`` gives a deterministic tie-break sort for free: AD-28's
    ``(ts, writer_id, counter)`` total order compares ``ts`` first at the
    caller/fold level, and this class's own field order supplies the exact
    ``(writer_id, counter)`` tail.
    """

    writer_id: str
    counter: int

    def __post_init__(self) -> None:
        if not isinstance(self.writer_id, str) or not _WRITER_ID_PATTERN.match(self.writer_id):
            raise ValueError(
                f"writer_id must match {_WRITER_ID_PATTERN.pattern!r} "
                f"(non-empty, filesystem-safe), got {self.writer_id!r}"
            )
        if (
            not isinstance(self.counter, int)
            or isinstance(self.counter, bool)
            or self.counter < 0
        ):
            raise ValueError(f"counter must be a non-negative int, got {self.counter!r}")


def _id_to_json_dict(entry_id: JournalEntryId) -> dict[str, object]:
    return {"writer_id": entry_id.writer_id, "counter": entry_id.counter}


@dataclass(frozen=True)
class JournalEntry:
    """One journal line's shape (AD-28): ``{id, ts, run_id, kind, phase,
    story?, intent_id?, payload}``. ``__post_init__`` enforces every
    invariant at construction, matching every other dataclass in this
    package (``Finding``/``Envelope``/``StoryKey``):

    - ``ts`` matches the millisecond-precision UTC pattern
      (``_ENTRY_TIMESTAMP_PATTERN``), validated the same two-layer way
      ``build_gate_record`` validates ``timestamp`` -- regex spelling, then
      ``datetime.fromisoformat`` for genuine calendar validity (a regex
      alone would admit e.g. Feb 30).
    - ``intent_id`` is present if and only if ``phase is Phase.OUTCOME`` --
      mandatory on every outcome, absent on every intent/observation
      (AD-28's rule, extended to ``intent`` since an intent entry has
      nothing prior to reference).
    - ``run_id``/``kind`` are non-blank ``str`` (``.strip()`` check,
      matching ``build_gate_record``'s own ``tree_revision``/``command``
      convention).
    - ``story``, if present, is a ``StoryKey`` (reuses
      ``core.identity.StoryKey`` -- never a second key type).
    - ``payload`` is coerced to a fresh plain ``dict`` via a deep copy, then
      ``json.dumps``-checked, exactly like ``Envelope.data`` -- never
      accepts a non-serializable value, and never lets the caller mutate
      this entry's stored payload through their own original reference.

    ``to_json_dict()`` renders the schema shape: ``id``/``intent_id`` as
    nested ``{"writer_id", "counter"}`` objects (the composite stays
    structured, never string-encoded -- no parser to write or maintain for
    Story 3.2's fold), ``phase``/``story`` as their string forms, and the
    optional keys ``story``/``intent_id`` omitted entirely when absent
    (mirrors ``Finding.to_json_dict``'s own optional-``path`` convention).
    """

    id: JournalEntryId
    ts: str
    run_id: str
    kind: str
    phase: Phase
    story: StoryKey | None
    intent_id: JournalEntryId | None
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        if not isinstance(self.id, JournalEntryId):
            raise ValueError(f"id must be a JournalEntryId, got {self.id!r}")

        if not isinstance(self.ts, str) or not _ENTRY_TIMESTAMP_PATTERN.match(self.ts):
            raise ValueError(
                "ts must use the millisecond-precision UTC ISO-8601 spelling "
                "YYYY-MM-DDTHH:MM:SS.mmmZ (exactly 3 fractional digits, 'T' "
                f"and 'Z' only), got {self.ts!r}"
            )
        try:
            datetime.fromisoformat(self.ts)
        except ValueError as exc:
            raise ValueError(f"ts is not a valid calendar date/time: {self.ts!r}") from exc

        if not isinstance(self.run_id, str) or not self.run_id.strip():
            raise ValueError(f"run_id must be a non-blank str, got {self.run_id!r}")
        if not isinstance(self.kind, str) or not self.kind.strip():
            raise ValueError(f"kind must be a non-blank str, got {self.kind!r}")

        object.__setattr__(self, "phase", Phase(self.phase))

        if self.story is not None and not isinstance(self.story, StoryKey):
            raise ValueError(f"story must be a StoryKey or None, got {self.story!r}")
        if self.intent_id is not None and not isinstance(self.intent_id, JournalEntryId):
            raise ValueError(
                f"intent_id must be a JournalEntryId or None, got {self.intent_id!r}"
            )

        if self.phase is Phase.OUTCOME and self.intent_id is None:
            raise ValueError("intent_id is required when phase is Phase.OUTCOME")
        if self.phase is not Phase.OUTCOME and self.intent_id is not None:
            raise ValueError(
                f"intent_id must be absent when phase is {self.phase.value!r} "
                "-- mandatory only for phase: outcome"
            )

        if not isinstance(self.payload, Mapping):
            raise ValueError(f"payload must be a Mapping, got {self.payload!r}")
        try:
            copied_payload = copy.deepcopy(dict(self.payload))
        except TypeError as exc:
            raise ValueError(f"payload is not deep-copyable: {exc}") from exc
        # Checked BEFORE the plain json.dumps() below (review finding,
        # verified live): a bare json.dumps() silently coerces a non-str key
        # (e.g. the int 1) to its string form on output without raising, so
        # a mixed-type-key payload passed construction cleanly -- then later
        # crashed prepare_for_write's own json.dumps(..., sort_keys=True)
        # with an unhandled TypeError, since sort_keys sorts the ORIGINAL
        # (key, value) tuples before stringifying, and int/str keys are not
        # orderable against each other. Rejecting non-str keys here instead
        # keeps `entry.payload` (in-memory) and every serialization of it
        # (sorted or not) in agreement, and gives a clear ValueError instead
        # of a crash two functions away from the actual cause.
        if not all(isinstance(key, str) for key in copied_payload):
            raise ValueError(
                f"payload keys must all be str, got {copied_payload!r}"
            )
        try:
            json.dumps(copied_payload)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"payload is not JSON-serializable: {exc}") from exc
        object.__setattr__(self, "payload", copied_payload)

    def to_json_dict(self) -> dict[str, object]:
        document: dict[str, object] = {
            "id": _id_to_json_dict(self.id),
            "ts": self.ts,
            "run_id": self.run_id,
        }
        if self.story is not None:
            document["story"] = str(self.story)
        document["kind"] = self.kind
        document["phase"] = self.phase.value
        if self.intent_id is not None:
            document["intent_id"] = _id_to_json_dict(self.intent_id)
        # Deep-copied: self.payload is already a defensive deep copy of the
        # caller's original input, but returning it directly would still let
        # a caller of to_json_dict() mutate THIS entry's stored value
        # through the returned dict (mirrors Envelope.to_json_dict).
        document["payload"] = copy.deepcopy(self.payload)
        return document


def build_entry(
    *,
    id: JournalEntryId,
    ts: str,
    run_id: str,
    kind: str,
    phase: Phase | str,
    payload: Mapping[str, object],
    story: StoryKey | None = None,
    intent_id: JournalEntryId | None = None,
) -> JournalEntry:
    """The keyword-only constructor (mirrors ``core.model.build_envelope``'s
    identical "thin keyword-only forwarding constructor" role): ``story``/
    ``intent_id`` default ``None`` -- the schema's own two optional fields --
    every other argument is mandatory. Performs no validation of its own;
    every invariant is ``JournalEntry.__post_init__``'s."""
    return JournalEntry(
        id=id,
        ts=ts,
        run_id=run_id,
        kind=kind,
        phase=phase,
        story=story,
        intent_id=intent_id,
        payload=payload,
    )


@dataclass(frozen=True)
class PreparedWrite:
    """The result of ``prepare_for_write`` (AD-30's 4 KiB sidecar-blob
    decision): ``line`` is the ready-to-append JSON line, WITHOUT a trailing
    newline -- ``FsPort.append_line`` owns that. ``sidecar_relative_path``/
    ``sidecar_content`` are both ``None`` together for an inline payload, or
    both set together (the blob's run-relative path,
    ``blobs/<writer_id>-<counter>.json``, and its original serialized JSON
    text) when the entry's payload exceeded ``SIDECAR_THRESHOLD_BYTES``."""

    line: str
    sidecar_relative_path: str | None
    sidecar_content: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.line, str):
            raise ValueError(f"line must be a str, got {self.line!r}")
        if (self.sidecar_relative_path is None) != (self.sidecar_content is None):
            raise ValueError(
                "sidecar_relative_path and sidecar_content must be both None "
                "or both set together"
            )


def prepare_for_write(entry: JournalEntry) -> PreparedWrite:
    """Pure sidecar-threshold decision (AD-30): if ``entry.payload``'s own
    UTF-8 JSON byte length exceeds ``SIDECAR_THRESHOLD_BYTES``, the returned
    line embeds ``{"sidecar_ref": "blobs/<writer_id>-<counter>.json"}`` in
    ``payload``'s place instead -- derived solely from ``entry.id``,
    globally unique within the run by construction, no path input needed --
    and ``sidecar_content`` carries the ORIGINAL payload's serialized text
    for the caller to write to that path. A small payload inlines normally:
    ``sidecar_relative_path``/``sidecar_content`` are both ``None``, and
    ``line`` embeds the payload as-is."""
    if not isinstance(entry, JournalEntry):
        raise TypeError(f"entry must be a JournalEntry, got {entry!r}")

    payload_text = json.dumps(entry.payload, sort_keys=True)
    document = entry.to_json_dict()

    if len(payload_text.encode("utf-8")) <= SIDECAR_THRESHOLD_BYTES:
        return PreparedWrite(
            line=json.dumps(document, sort_keys=True),
            sidecar_relative_path=None,
            sidecar_content=None,
        )

    # Built via `str.join` into a single placeholder, not a two-placeholder
    # `f"{a}-{b}"` -- the AD-23 guard (tests/meta/test_ad23_inline_key_format
    # _guard.py) flags exactly that shape as an inline story-key format
    # regardless of what the two values actually mean, and a (writer_id,
    # counter) pair joined by "-" is structurally indistinguishable from one
    # to that best-effort static scan.
    id_fragment = "-".join((entry.id.writer_id, str(entry.id.counter)))
    sidecar_relative_path = f"blobs/{id_fragment}.json"
    document["payload"] = {"sidecar_ref": sidecar_relative_path}
    return PreparedWrite(
        line=json.dumps(document, sort_keys=True),
        sidecar_relative_path=sidecar_relative_path,
        sidecar_content=payload_text,
    )
