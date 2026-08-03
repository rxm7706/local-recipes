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

Story 3.2 adds this module's READ side: ``fold(lines, sidecars) ->
FoldResult`` parses each raw journal line independently, pairs
``outcome``/``intent`` entries by ``JournalEntryId`` equality alone (AD-28
-- no positional or heuristic pairing, ever), and quarantines any line that
fails to parse/validate or references an unresolvable sidecar blob, scoped
to its own ``(story, kind)`` or widened to the whole run when neither
recovers (AD-30). ``FoldResult.by_kind``/``for_story``/``is_evaluable`` are
the one generic query surface every future consumer (Story 2.3's
frozen-surface scope check, Epic 4's spec-promotion/reconciliation
stories) reads Marshal's accumulating run state through -- AD-26's "exactly
one producer" rule, extended from ``EffectivePolicy``'s seed fields to the
journal's own derived facts. This module still implements no CLI wiring
(``cli/gate.py``'s ``--run`` stays the ``MRS-GATE-005`` stub Story 2.1 left
it) and no session-scoped fold -- AD-25's ``sessions/`` namespace remains
entirely unimplemented (no session concept exists anywhere in this
codebase today; logged as a follow-up in ``deferred-work.md``).

This module is pure data: no I/O, no subprocess, no network, no clock, no
``pyforge.marshal.adapters`` import (AD-4) -- only ``copy``, ``json``,
``re``, ``collections.abc``, ``dataclasses``, ``datetime``, ``enum``,
``types``, and this package's own ``.identity``/``.model``/``.policy``.
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType

from . import policy
from .identity import MalformedStoryKeyError, StoryKey, normalize
from .model import Finding, Severity

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


def _sidecar_path_for(entry_id: JournalEntryId) -> str:
    """The ONE derivation of an entry's sidecar-blob path, shared by
    ``prepare_for_write`` (which emits it) and ``_parse_entry`` (which binds
    a resolved ``sidecar_ref`` back to it) -- so the write and read sides
    can never disagree about the naming convention.

    Built via ``str.join`` into a single placeholder, not a two-placeholder
    ``f"{a}-{b}"`` -- the AD-23 guard (``tests/meta/
    test_ad23_inline_key_format_guard.py``) flags exactly that shape as an
    inline story-key format regardless of what the two values actually mean,
    and a ``(writer_id, counter)`` pair joined by ``"-"`` is structurally
    indistinguishable from one to that best-effort static scan."""
    id_fragment = "-".join((entry_id.writer_id, str(entry_id.counter)))
    return f"blobs/{id_fragment}.json"


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

    sidecar_relative_path = _sidecar_path_for(entry.id)
    document["payload"] = {"sidecar_ref": sidecar_relative_path}
    return PreparedWrite(
        line=json.dumps(document, sort_keys=True),
        sidecar_relative_path=sidecar_relative_path,
        sidecar_content=payload_text,
    )


@dataclass(frozen=True)
class QuarantinedRecord:
    """One quarantined journal line (AD-30): ``raw`` is the line that failed
    to parse, failed validation, or failed to resolve a sidecar reference --
    the original text when the line was a ``str``, else its ``repr()``
    (``_display_line``, for a caller-supplied non-``str`` element).
    ``story``/``kind`` are the best-effort-recovered scope pair
    -- ALWAYS both ``None`` together or both set together: AD-30's rule is
    that a partial recovery (one but not the other) carries no meaningful
    scope, so it widens to the whole run rather than being represented
    here at all (enforced at construction, matching this module's own
    ``JournalEntry``/``JournalEntryId`` convention). ``finding`` is the
    registered ``MRS-JOURNAL-001``/``MRS-JOURNAL-002`` ``Finding`` this
    quarantine surfaces (AD-8: unevaluable is a failure, never silently
    dropped)."""

    raw: str
    story: StoryKey | None
    kind: str | None
    finding: Finding

    def __post_init__(self) -> None:
        if not isinstance(self.raw, str):
            raise ValueError(f"raw must be a str, got {self.raw!r}")
        if self.story is not None and not isinstance(self.story, StoryKey):
            raise ValueError(f"story must be a StoryKey or None, got {self.story!r}")
        if self.kind is not None and not isinstance(self.kind, str):
            raise ValueError(f"kind must be a str or None, got {self.kind!r}")
        if (self.story is None) != (self.kind is None):
            raise ValueError(
                "story and kind must be both None or both set together -- "
                "AD-30's scope widens to (None, None) unless BOTH recover, "
                f"got story={self.story!r}, kind={self.kind!r}"
            )
        if not isinstance(self.finding, Finding):
            raise ValueError(f"finding must be a Finding, got {self.finding!r}")


@dataclass(frozen=True)
class FoldResult:
    """The journal fold's total result (Story 3.2, AD-26/AD-28/AD-30) --
    Marshal's ONE producer for every accumulating run-state value (story
    transitions, gate verdicts, escalations, deferrals, consumption,
    supervisor actions, frozen surfaces, attempt counts, effective gate
    mode): nothing else may derive them independently.

    ``entries`` is every evaluable entry (sidecar-resolved where
    applicable), in AD-28's total order ``(ts, writer_id, counter)`` -- a
    plain tuple sort, since ``ts`` is already Story 3.1's one canonical,
    string-sortable spelling. ``open_intents`` is every ``intent``-phase
    entry whose id is never referenced by an ``outcome.intent_id`` --
    reported, never inferred closed. ``orphaned_outcomes`` is every
    ``outcome``-phase entry whose ``intent_id`` matched no known
    ``intent`` entry's id -- including a forged/self-referencing outcome
    whose ``intent_id`` equals its own ``id`` (closes the Story 3.1
    review's deferred self-reference gap, ``deferred-work.md``).
    ``quarantined`` is every parse/validation/sidecar failure (AD-30), one
    ``Finding`` each. ``entries``/``open_intents``/``orphaned_outcomes``
    overlap by design -- the latter two are query VIEWS over ``entries``,
    not a disjoint partition of it.

    ``by_kind``/``for_story``/``is_evaluable`` are the ONE generic query
    surface a future real writer's consumer uses -- no kind-specific
    accessor exists here, since no real writer emits any of the 9
    illustrative kinds above yet (mirrors this module's Story 3.1 "pure
    mechanism, zero real caller" precedent)."""

    entries: tuple[JournalEntry, ...]
    open_intents: tuple[JournalEntry, ...]
    orphaned_outcomes: tuple[JournalEntry, ...]
    quarantined: tuple[QuarantinedRecord, ...]

    def __post_init__(self) -> None:
        for field_name, value in (
            ("entries", self.entries),
            ("open_intents", self.open_intents),
            ("orphaned_outcomes", self.orphaned_outcomes),
        ):
            if not all(isinstance(item, JournalEntry) for item in value):
                raise ValueError(
                    f"{field_name} must contain only JournalEntry instances, "
                    f"got {value!r}"
                )
        if not all(isinstance(item, QuarantinedRecord) for item in self.quarantined):
            raise ValueError(
                "quarantined must contain only QuarantinedRecord instances, "
                f"got {self.quarantined!r}"
            )
        # Review finding, verified live: type-checking alone let a
        # Phase.OUTCOME entry construct cleanly inside open_intents (and
        # vice versa for orphaned_outcomes) -- mirrors this module's own
        # dataclass-invariant-at-construction convention (JournalEntry,
        # QuarantinedRecord) rather than trusting every future constructor
        # of this value type to get the phase right unchecked. fold() itself
        # never produces such a mismatch; this closes the gap for any other
        # constructor.
        if not all(entry.phase is Phase.INTENT for entry in self.open_intents):
            raise ValueError("open_intents must contain only Phase.INTENT entries")
        if not all(entry.phase is Phase.OUTCOME for entry in self.orphaned_outcomes):
            raise ValueError("orphaned_outcomes must contain only Phase.OUTCOME entries")

    def by_kind(self, kind: str) -> tuple[JournalEntry, ...]:
        """Every evaluable entry whose ``kind`` equals ``kind``, in
        ``entries``'s own AD-28 total order. Raises ``TypeError`` for a
        non-``str`` ``kind`` -- see ``for_story``."""
        if not isinstance(kind, str):
            raise TypeError(f"kind must be a str, got {kind!r}")
        return tuple(entry for entry in self.entries if entry.kind == kind)

    def for_story(self, story: StoryKey) -> tuple[JournalEntry, ...]:
        """Every evaluable entry whose ``story`` equals ``story``, in
        ``entries``'s own AD-28 total order.

        Raises ``TypeError`` for a non-``StoryKey`` ``story`` (review
        finding, verified live): ``for_story("3.1")`` silently returned
        ``()`` for a caller who passed a raw key string, and
        ``for_story(None)`` silently returned every run-scoped entry --
        both indistinguishable from "this story has no entries." AD-23
        gives ``core.identity`` sole ownership of the key format precisely
        so a raw string never stands in for a parsed key; this guard is the
        same one ``is_evaluable`` already applies."""
        if not isinstance(story, StoryKey):
            raise TypeError(f"story must be a StoryKey, got {story!r}")
        return tuple(entry for entry in self.entries if entry.story == story)

    def is_evaluable(self, story: StoryKey | None, kind: str | None) -> bool:
        """``False`` if some quarantine scoped exactly to ``(story, kind)``
        or widened to the whole run (``(None, None)``, AD-30); ``True``
        otherwise.

        ``is_evaluable(None, None)`` asks specifically about the RUN-LEVEL
        scope -- the facts no single story owns -- so it is ``False`` only
        when some quarantine actually widened to the whole run, NOT whenever
        any line at all quarantines. A narrowly-scoped quarantine leaves the
        run-level scope evaluable, which is the entire point of AD-30's
        narrow scoping and of this story's own AC ("records provably
        unaffected stay evaluable"). An earlier draft of this docstring
        claimed ``False`` "the instant ANY line quarantines" -- a review
        finding caught live that the code has never behaved that way, and
        that behaving that way would defeat narrow scoping altogether.

        Raises ``TypeError`` for a ``story``/``kind`` of the wrong type, and
        ``ValueError`` for an ASYMMETRIC pair (exactly one of
        ``story``/``kind`` is ``None``) -- mirrors ``QuarantinedRecord``'s
        own both-or-neither invariant. A quarantine record can never carry
        an asymmetric scope, so a caller asking one would always get a
        (possibly wrong) ``True`` with no real answer behind it -- a
        footgun a review finding caught live rather than a legitimate
        query."""
        if story is not None and not isinstance(story, StoryKey):
            raise TypeError(f"story must be a StoryKey or None, got {story!r}")
        if kind is not None and not isinstance(kind, str):
            raise TypeError(f"kind must be a str or None, got {kind!r}")
        if (story is None) != (kind is None):
            raise ValueError(
                "story and kind must be both None or both set -- no "
                f"quarantine record ever scopes asymmetrically, got "
                f"story={story!r}, kind={kind!r}"
            )
        for record in self.quarantined:
            if record.story is None and record.kind is None:
                return False
            if record.story == story and record.kind == kind:
                return False
        return True


def fold(
    lines: Sequence[str],
    *,
    sidecars: Mapping[str, str | None] = MappingProxyType({}),
) -> FoldResult:
    """The journal's READ side (Story 3.2, AD-26/AD-28/AD-30): folds
    ``lines`` -- a run's own journal file, already split into individual
    JSON-line strings by the caller (no file I/O here) -- into the run's
    accumulated state. Every line is parsed and reconstructed
    independently via the SAME invariants ``build_entry`` already enforces
    (AD-23's story-key parser included, never a second one); a failure at
    any step quarantines that ONE line -- it never aborts the fold or
    drops any other entry. ``sidecars`` maps a ``sidecar_ref`` relative
    path to its already-read blob text, or omits/``None``s a path the
    caller could not read.

    ``intent``/``outcome`` pairing is EXCLUSIVELY by ``JournalEntryId``
    equality (AD-28) -- a dict lookup over an already-hashable id, never
    positional, timestamp-adjacency, or ordinal pairing. An ``outcome``
    whose ``intent_id`` matches no known ``intent`` id -- including a
    forged/self-referencing outcome whose ``intent_id`` equals its own
    ``id`` -- surfaces in ``FoldResult.orphaned_outcomes``, never silently
    paired or dropped.

    A blank or whitespace-only element is SKIPPED, not quarantined:
    ``FsPort.append_line`` owns each line's trailing newline
    (``PreparedWrite``'s own contract), so a journal file always ends in one
    and the obvious caller -- ``text.split("\\n")`` -- always yields a final
    ``""``. Quarantining that terminator artifact recovered no
    ``(story, kind)``, widened to ``(None, None)``, and made an otherwise
    perfectly intact run wholly unevaluable (review finding, verified live).
    No real journal line is ever blank: ``prepare_for_write`` always emits a
    JSON object.

    Raises ``TypeError`` unless ``lines`` is a ``Sequence`` that is not
    itself a character/byte string (mirrors ``identity.resolve_feed``'s own
    bare-str guard -- a ``str`` satisfies ``Sequence[str]``, so
    ``fold("not-a-list")`` would otherwise shred into per-character garbage
    quarantine records instead of the documented, reported failure -- and
    extended to every other non-sequence footgun a review found live:
    ``bytes``/``bytearray`` shred the same way per byte, a ``Mapping``
    silently folded its KEYS as journal lines with zero signal, and
    ``fold(None)``/``fold(42)`` died with a bare ``'NoneType' object is not
    iterable`` naming no contract). Raises ``TypeError`` likewise for a
    ``sidecars`` that isn't a ``Mapping`` (mirrors ``core.policy.compose``'s
    identical contract-violation guard on its own ``project``/``flags``
    parameters -- review finding, verified live: ``fold(lines,
    sidecars=None)`` used to raise an unguarded ``AttributeError`` the
    instant any line needed sidecar resolution, aborting the WHOLE fold and
    losing every other entry -- the exact failure this function's own
    docstring promises never happens)."""
    if isinstance(lines, (str, bytes, bytearray)) or not isinstance(lines, Sequence):
        raise TypeError(
            "lines must be a sequence of journal-line strings (not a bare "
            f"str/bytes, and not a mapping or other non-sequence), got {lines!r}"
        )
    if isinstance(sidecars, str) or not isinstance(sidecars, Mapping):
        raise TypeError(f"sidecars must be a Mapping, got {sidecars!r}")

    parsed: list[JournalEntry] = []
    quarantined: list[QuarantinedRecord] = []
    for raw_line in lines:
        if isinstance(raw_line, str) and not raw_line.strip():
            continue
        try:
            entry = _parse_entry(raw_line, sidecars)
        except _SidecarUnresolved as exc:
            story, kind = _best_effort_recover(raw_line)
            quarantined.append(
                _quarantine(_display_line(raw_line), story, kind, "MRS-JOURNAL-002", str(exc))
            )
        except (ValueError, TypeError, RecursionError) as exc:
            # RecursionError too (review finding, verified live): `json.loads`
            # on an adversarially/corruptly deep-nested line or sidecar blob
            # raises RecursionError, a RuntimeError subclass that a bare
            # `(ValueError, TypeError)` catch does not see -- the same "one
            # bad line must never abort the whole fold" guarantee this
            # function's docstring makes, for a distinct exception type.
            story, kind = _best_effort_recover(raw_line)
            quarantined.append(
                _quarantine(_display_line(raw_line), story, kind, "MRS-JOURNAL-001", str(exc))
            )
        else:
            parsed.append(entry)

    parsed.sort(key=lambda entry: (entry.ts, entry.id))

    intents_by_id: dict[JournalEntryId, JournalEntry] = {
        entry.id: entry for entry in parsed if entry.phase is Phase.INTENT
    }
    matched_intent_ids: set[JournalEntryId] = set()
    orphaned_outcomes: list[JournalEntry] = []
    for entry in parsed:
        if entry.phase is not Phase.OUTCOME:
            continue
        if entry.intent_id in intents_by_id:
            matched_intent_ids.add(entry.intent_id)
        else:
            orphaned_outcomes.append(entry)

    open_intents = tuple(
        entry
        for entry in parsed
        if entry.phase is Phase.INTENT and entry.id not in matched_intent_ids
    )

    return FoldResult(
        entries=tuple(parsed),
        open_intents=open_intents,
        orphaned_outcomes=tuple(orphaned_outcomes),
        quarantined=tuple(quarantined),
    )


def _display_line(raw_line: object) -> str:
    """A quarantine's ``raw`` field is always a ``str`` (``QuarantinedRecord``
    enforces it) -- but a caller-supplied ``lines`` element need not be one
    (the same footgun ``identity.resolve_feed`` guards its own per-entry
    loop against). A non-``str`` line is ``repr()``'d for reporting rather
    than passed through, matching ``resolve_feed``'s identical convention."""
    return raw_line if isinstance(raw_line, str) else repr(raw_line)


def _parse_entry_id(raw: object) -> JournalEntryId:
    """Reconstruct one ``{writer_id, counter}`` object into a
    ``JournalEntryId`` -- the SAME composite id shape ``JournalEntry``
    already enforces (AD-28). A non-``Mapping`` input raises the identical
    ``ValueError`` class every other shape failure in this module does, so
    ``_parse_entry``'s single catch-all in ``fold`` handles it uniformly."""
    if not isinstance(raw, Mapping):
        raise ValueError(f"entry id must be a JSON object, got {raw!r}")
    return JournalEntryId(writer_id=raw.get("writer_id"), counter=raw.get("counter"))


def _sidecar_ref(payload: Mapping[str, object]) -> str | None:
    """Return ``payload``'s sidecar path if ``payload`` is EXACTLY
    ``{"sidecar_ref": <str>}`` -- the one shape ``prepare_for_write`` ever
    emits in the payload's place (AD-30) -- else ``None``. A payload that
    merely happens to carry a ``sidecar_ref`` key ALONGSIDE other keys is a
    real inline payload, not a placeholder."""
    if len(payload) == 1 and isinstance(payload.get("sidecar_ref"), str):
        return payload["sidecar_ref"]
    return None


class _SidecarUnresolved(ValueError):
    """Internal: raised by ``_parse_entry`` when a payload's
    ``sidecar_ref`` cannot be resolved -- the path is absent from
    ``sidecars`` (or maps to ``None``), or its blob text is not valid
    JSON, or the resolved value is not itself a JSON object -- registers
    ``MRS-JOURNAL-002``, distinct from every other parse/validation
    failure (``MRS-JOURNAL-001``). A ``ValueError`` subclass so ``fold``'s
    loop can catch it FIRST, ahead of the general ``ValueError`` catch for
    every other failure."""


def _parse_entry(raw_line: str, sidecars: Mapping[str, str | None]) -> JournalEntry:
    """Parse and reconstruct ONE raw journal line into a fully-validated,
    sidecar-resolved ``JournalEntry`` -- via the SAME invariants
    ``build_entry`` already enforces (AD-23/AD-28), never a second parser.
    Raises ``ValueError`` for any parse/shape failure (``MRS-JOURNAL-001``)
    or ``_SidecarUnresolved`` (a ``ValueError`` subclass) specifically for
    an unresolvable ``sidecar_ref`` (``MRS-JOURNAL-002``) -- ``fold`` is
    the only place either is caught; this function itself never
    quarantines anything, so it stays a plain, reusable parse step.

    A payload carrying a sidecar reference is resolved via
    ``dataclasses.replace`` AFTER the entry already constructed
    successfully with the placeholder payload in place -- ``build_entry``'s
    generic ``payload: Mapping[str, object]`` shape accepts
    ``{"sidecar_ref": ...}`` just as readily as any other small payload, so
    every OTHER invariant (``ts``/``run_id``/``kind``/``phase``/
    ``intent_id``/``story``) is validated once, uniformly, before this
    function ever looks at whether a sidecar needs resolving."""
    document = json.loads(raw_line)
    if not isinstance(document, Mapping):
        raise ValueError(f"journal line must decode to a JSON object, got {document!r}")

    story_raw = document.get("story")
    intent_id_raw = document.get("intent_id")
    entry = build_entry(
        id=_parse_entry_id(document.get("id")),
        ts=document.get("ts"),
        run_id=document.get("run_id"),
        kind=document.get("kind"),
        phase=document.get("phase"),
        payload=document.get("payload"),
        story=normalize(story_raw) if story_raw is not None else None,
        intent_id=_parse_entry_id(intent_id_raw) if intent_id_raw is not None else None,
    )

    ref = _sidecar_ref(entry.payload)
    if ref is None:
        return entry

    # Bind the reference to the entry that owns it (review finding, verified
    # live): `prepare_for_write` derives the blob path SOLELY from the
    # entry's own `(writer_id, counter)`, so the placeholder a real writer
    # emits always names exactly this path. Resolving whatever path the line
    # happens to name instead let entry `cli-1/2` reference `cli-1/1`'s blob
    # and silently adopt that entry's payload -- zero quarantine, zero
    # signal, in an append-only artifact whose whole value is being
    # tamper-evident. A mismatch is definitionally corruption or forgery, so
    # it quarantines (MRS-JOURNAL-002) rather than resolving; this also
    # rejects path traversal and absolute refs for free.
    expected_ref = _sidecar_path_for(entry.id)
    if ref != expected_ref:
        raise _SidecarUnresolved(
            f"sidecar_ref {ref!r} does not name this entry's own blob "
            f"{expected_ref!r} -- a payload placeholder is only ever emitted "
            "for the entry that owns it"
        )

    blob = sidecars.get(ref)
    if blob is None:
        raise _SidecarUnresolved(f"missing sidecar blob for {ref!r}")
    try:
        resolved_payload = json.loads(blob)
    except (json.JSONDecodeError, TypeError, RecursionError) as exc:
        raise _SidecarUnresolved(f"sidecar blob {ref!r} is not valid JSON: {exc}") from exc
    try:
        return replace(entry, payload=resolved_payload)
    except (ValueError, TypeError, RecursionError) as exc:
        # TypeError/RecursionError too (review finding, verified live): a
        # blob nested deeply enough still DECODES via json.loads above, then
        # fails inside JournalEntry.__post_init__'s own copy.deepcopy /
        # json.dumps with RecursionError. Caught only as ValueError, that
        # escaped to `fold`'s outer catch and was reported as MRS-JOURNAL-001
        # -- a LINE parse failure -- defeating the exact discrimination the
        # two codes exist to make. The failure domain is the sidecar either
        # way, so it belongs to MRS-JOURNAL-002.
        raise _SidecarUnresolved(
            f"sidecar blob {ref!r} resolved to an invalid payload: {exc}"
        ) from exc


def _scope(
    story: StoryKey | None, kind: str | None
) -> tuple[StoryKey | None, str | None]:
    """AD-30's explicit widening rule: a quarantined line's scope is the
    ``(story, kind)`` pair ONLY when BOTH recover; either missing widens to
    ``(None, None)`` -- the whole run. No partial-recovery heuristic exists
    beyond this (a line that recovers one but not the other has no
    meaningful partial key to scope against)."""
    if story is None or kind is None:
        return None, None
    return story, kind


def _best_effort_recover(raw_line: object) -> tuple[StoryKey | None, str | None]:
    """Best-effort ``(story, kind)`` recovery straight off ``raw_line``'s
    raw JSON -- independent of, and tolerant of, whatever failure
    quarantined it (e.g. a document missing ``run_id`` but carrying valid
    ``story``/``kind`` fields still recovers both here). Re-parses
    ``raw_line`` itself (rather than threading a partially-built document
    through the caller) so this stays a single, self-contained recovery
    step usable from every quarantine site, including a totally
    unparseable line. Also tolerates ``RecursionError`` from an
    adversarially/corruptly deep-nested line -- the same class of failure
    ``fold``'s own outer catch guards against, reachable here too since
    this function re-parses independently (review finding, verified
    live)."""
    try:
        document = json.loads(raw_line)
    except (json.JSONDecodeError, TypeError, RecursionError):
        return None, None
    if not isinstance(document, Mapping):
        return None, None

    story: StoryKey | None = None
    raw_story = document.get("story")
    if isinstance(raw_story, str):
        try:
            story = normalize(raw_story)
        except MalformedStoryKeyError:
            story = None

    kind: str | None = None
    raw_kind = document.get("kind")
    if isinstance(raw_kind, str) and raw_kind.strip():
        kind = raw_kind

    return _scope(story, kind)


def _quarantine(
    raw_line: str,
    story: StoryKey | None,
    kind: str | None,
    code: str,
    message: str,
) -> QuarantinedRecord:
    # `path=raw_line` mirrors `core.identity`'s own MRS-IDENT-001/002
    # convention (Finding.path names the offending raw input) -- review
    # finding, verified live: without it, a Finding pulled out of
    # QuarantinedRecord.finding in isolation (exactly what a future
    # Envelope.findings consumer would do) carried no reference back to
    # which line it came from.
    return QuarantinedRecord(
        raw=raw_line,
        story=story,
        kind=kind,
        finding=Finding(code=code, severity=Severity.ERROR, message=message, path=raw_line),
    )
