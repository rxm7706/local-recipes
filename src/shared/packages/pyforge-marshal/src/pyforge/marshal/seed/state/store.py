"""``.marshal/seed-state.yml`` -- the tool-owned state document and its
atomic store (Story 10.2, architecture FR-102/FR-103/FR-104/FR-105/FR-107,
P-01/P-08/AR-6/AD-58).

Genesis had no state before this module. ``detect/hashes.py``'s
``check_managed_file(..., recorded_sha)`` took a value nobody could supply,
``detect/inventory.py`` and ``plan/build.py`` both documented "no read of
``.marshal/seed-state.yml``", and ``StateInvalid`` (exit 5) had no raise
site anywhere under ``seed/``. Without a tool-owned, schema-validated state
file, the repo and Genesis's belief about it can silently disagree -- the
exact failure class AR-6/P-08 are written against, and one this repo has
already lived through once with the ``bmad-switch`` marker.

**Eleven keys, no twelfth.** ``model_version``, ``seed_model_version``,
``adopted_at``, ``last_update``, ``mode``, ``agents``, ``managed``,
``skips``, ``legacy``, ``migrations_applied``, ``opted_out`` (FR-102's ten
plus ``opted_out``, which the epics AC adds). ``schema.json`` ``require``s
all eleven and closes the document with ``additionalProperties: false``, so
a field invented in code but not in the schema fails its own write. A
genuinely new field needs a PRD/architecture amendment first -- notably
there is no ``slug`` and no free-form ``answers`` map here (see
``copier_data`` below).

**Every READ validates; every read failure is a finding, not a crash.**
``read_state`` validates the parsed document against the packaged
``schema.json`` with ``jsonschema.Draft202012Validator`` BEFORE any field is
consumed, and converts every failure mode it can meet -- an unreadable
file, non-UTF-8 bytes, invalid YAML, a duplicate mapping key, a merge key,
a non-mapping root, a schema violation, a shape violation caught by
``from_json_dict`` -- into ``StateInvalid`` (exit 5) carrying a remedy. No
``jsonschema``, ``yaml``, ``OSError``, or ``UnicodeDecodeError`` type
escapes this module's read path (FR-104's "never a traceback"). Turning
that ``StateInvalid`` into a ``FindingType.STATE_INVALID`` finding is
``detect``'s job, not this module's. The ONE other ``SeedError`` the read
path can raise is ``InternalError`` (exit 10), and only for a broken
INSTALLATION -- a missing or corrupt packaged ``schema.json``, which is a
fact about the running artifact, never about this repository's state file.

**The WRITE path converts only its own schema failure.** ``write_state``
validates the serialized document first and raises ``StateInvalid`` before
any I/O if it does not conform -- but an ``OSError`` or a
``NeverWriteViolation`` raised by ``fs.write`` propagates unchanged: a
failed write means the ENVIRONMENT refused, not that state is invalid, and
mislabelling the two would send an operator to repair a file that is fine.

**An absent state file is not invalid.** ``read_state`` returns ``None``,
because ``marshal seed check`` must run against a never-adopted repo and
report the absence rather than raise on it. A dangling SYMLINK at the state
path is the one thing that looks like absence and is not: the link says the
repo was established, so a missing target is ``StateInvalid``, never
``None``.

**One atomic replace, through the one write boundary.** ``write_state``
serializes, then makes exactly ONE ``fs.write`` call (P-01: ``seed/fs.py``
is the only path to a target repo's filesystem; P-08: one atomic replace).
This module implements no temp-file or rename mechanics of its own --
``fs.write`` already delegates to ``pyforge.core.atomic_write``, and
``pyforge-core``'s CAP-7 sole-ownership meta test fails the build for any
module outside ``pyforge-core`` that grows a second implementation.

**Import surface.** stdlib, ``yaml``, ``jsonschema``, ``seed.errors``,
``seed.fs``, ``seed.model.version`` -- nothing else. Never ``seed.detect``,
``seed.plan``, ``seed.apply``, ``seed.verbs``, or ``seed.engine`` (the
architecture's no-upward-imports rule). That is also why
``ManagedArtifact.artifact_class`` is a plain wire ``str`` rather than
``model.manifest.ArtifactClass``: the schema's ``class`` enum is the
contract, and ``tests/unit/test_seed_state_store.py`` asserts the enum and
the schema agree so the deliberate duplication cannot drift.

**The opt-out API is five pure functions over an already-shipped key**
(Story 8.5, FR-112/AD-58). ``opted_out`` shipped with S-10.2 and nothing
consumed it: a maintainer who DELETED a managed region's markers was
indistinguishable from one who never had the region, so the tool re-inserted
it on the next run. ``opt_out_key`` / ``opt_out_key_or_none`` /
``is_opted_out`` / ``record_opt_out`` / ``clear_opt_out`` close that --
without a twelfth key, without a ``schema.json`` edit, and without a
state-schema migration. Both mutators are PURE (``dataclasses.replace``,
never in-place), idempotent, and keep ``opted_out`` sorted, so two runs
recording the same pairs in different orders write byte-identical state.
``opt_out_key`` validates against the packaged schema's OWN
``properties.opted_out.items.pattern`` rather than a hand-copied regex and
rather than importing ``regions.markers.REGION_NAME_PATTERN`` -- the first
would be a second spelling free to drift from the wire contract, and the
second is not on this module's import surface at all (see above).
``opt_out_key_or_none`` is the same rule with the opposite answer for an
inadmissible pair (``None``, not a raise), public because ``plan/build.py``
asks exactly that question and must not re-spell it.

BOTH mutators also drop the artifact's ``managed[]`` claim for that region
(one shared filter, ``_without_region_claim``). For ``record_opt_out`` that
is what makes the opt-out survive: with the claim retained, a "was installed
once, markers now gone" derivation re-derives the opt-out on every later run.
For ``clear_opt_out`` it is what makes the WITHDRAWAL real: a DERIVED opt-out
has no recorded key to remove, so removing only the key leaves the claim
standing and the derivation re-fires forever. Neither mutator refreshes
``last_update`` -- the write time belongs to the verb that persists the state
(``write_state`` does not stamp it either).

Nothing here WRITES: a mutator returns a new ``SeedState`` for a verb to
persist through the existing ``write_state``.

**Genesis never reads the Copier answers file.** FR-105/AD-52: state is the
single source of truth for the answers, re-supplied to Copier via ``data=``
on every render -- ``copier_data(state)`` is that projection. This module
contains no reference to the answers file's path at all, and
``tests/unit/test_seed_state_store.py`` asserts its source text does not.

**Why ``_StrictLoader`` is re-declared here.** ``model/manifest.py`` owns
the same duplicate-key-rejecting loader but exposes it only as a private
symbol, and importing a neighbour's private name is worse than a
twenty-line duplication. The alternative -- plain ``SafeLoader`` -- would
let a hand-edited duplicate key load silently last-wins in the one file
whose entire premise is that it is not hand-edited. The two loaders are no
longer identical: this one refuses a YAML merge key outright, which the
manifest's (whose file a human legitimately authors) tolerates once -- see
``_StrictLoader``'s own docstring for why the state file cannot afford
that tolerance.
"""

from __future__ import annotations

import dataclasses
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from importlib import metadata, resources
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from .. import fs
from ..errors import InternalError, StateInvalid
from ..model.version import ModelVersion

# FR-103's do-not-hand-edit header, re-emitted on every write and ignored
# on read (YAML comments carry no value). First LINE is a comment, and the
# block says in plain words who owns the file and what to do instead --
# the AC is about what a human sees when they open it, not about a machine
# marker, so this is prose rather than a parseable directive.
_HEADER = (
    "# DO NOT HAND-EDIT -- this file is owned by `marshal seed`.\n"
    "#\n"
    "# It records what the tool established in this repository, and the tool\n"
    "# rewrites it in full on every run, so any edit you make here is lost at\n"
    "# the next write. Until that write, the tool BELIEVES what it reads: an\n"
    "# edit that still fits the schema is acted on as if the tool had made it\n"
    "# -- silently, with no warning that the file and the repository now\n"
    "# disagree. Only an edit that breaks the schema is reported (exit 5).\n"
    "#\n"
    "# To change what is recorded, run the `marshal seed` verb that owns it\n"
    "# (init / adopt / update). To stop managing an artifact or a region,\n"
    "# use the tool's own opt-out, never a manual deletion below.\n"
    "#\n"
    "# This file IS meant to be committed: it is how a clone learns what the\n"
    "# tool already owns here.\n"
)

# The eleven top-level keys, in the order `to_json_dict` emits them and
# `schema.json` requires them. Named once so the two orderings cannot drift.
STATE_KEYS: tuple[str, ...] = (
    "model_version",
    "seed_model_version",
    "adopted_at",
    "last_update",
    "mode",
    "agents",
    "managed",
    "skips",
    "legacy",
    "migrations_applied",
    "opted_out",
)

_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

_SCHEMA_FILENAME = "schema.json"

# The one `class` value that carries `inserted_region_spans` (one span per
# installed region, Story 82.13). A WIRE string, not
# `model.manifest.ArtifactClass.HYBRID_MANAGED_REGION` -- this module may not
# import `model.manifest` (module docstring's import surface), and
# `schema.json`'s own enum is the contract either way.
_REGION_ARTIFACT_CLASS = "hybrid-managed-region"


class _StrictLoader(yaml.SafeLoader):
    """``SafeLoader`` that rejects a repeated mapping key -- and a merge key
    of any kind -- rather than silently keeping the last one, the same
    technique ``model/manifest.py`` applies to the manifest, re-declared
    here (see the module docstring) rather than imported from a
    neighbour's private namespace.

    A state file with two ``mode:`` keys, or a ``managed`` entry with two
    ``body_sha:`` keys, would otherwise load clean with the SECOND value
    winning -- so the file a human reviewed in the diff is not the file
    Genesis loaded. ``ConstructorError`` is a ``YAMLError``, so
    ``read_state``'s existing handler already reports it as
    ``StateInvalid``.

    **A merge key is refused outright, not tolerated as an override
    idiom.** An earlier draft allowed a single ``<<:`` on the grounds that
    the merge idiom exists precisely to let an explicit key override an
    inherited one -- but that left the duplicate rule bypassable in one
    line: ``SafeConstructor.flatten_mapping()`` splices the ANCHORED node's
    pairs straight into ``node.value`` without ever calling this method on
    that node, so ``<<: &shared`` with two ``mode:`` keys beneath it loaded
    clean, last-wins, which is the exact outcome this class exists to
    prevent (confirmed by direct execution). Scanning the anchored node too
    would be a second, subtler rule to keep true; refusing merges is the
    honest one, because this file is tool-written and ``write_state``
    (``yaml.safe_dump``) emits no anchor, alias, or merge key at all --
    ``schema.json``'s own description already says so. A ``<<:`` here is
    therefore always a hand edit, never something Genesis produced.

    The non-mapping guard is the same class of escape: ``!!map "x"`` reaches
    this method with a ``ScalarNode``, and iterating ``node.value`` (a
    ``str``) raised a bare ``ValueError`` straight past ``read_state``'s
    ``YAMLError`` handler, breaking FR-104's "only ``StateInvalid``"
    contract. Reported as a ``ConstructorError`` so it funnels to
    ``StateInvalid`` like every other malformed document."""

    def construct_mapping(self, node: Any, deep: bool = False) -> dict:
        if not isinstance(node, yaml.MappingNode):
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"expected a mapping node, but found {node.id}",
                node.start_mark,
            )
        # Snapshot the authored keys BEFORE delegating: `SafeConstructor`
        # runs `flatten_mapping()`, which splices a merge key's inherited
        # pairs into `node.value` in place, so a post-delegation scan sees
        # the merged result rather than the document.
        authored_key_nodes = []
        for key_node, _ in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found a YAML merge key '<<' -- this file is tool-written and never contains anchors or merges",
                    key_node.start_mark,
                )
            authored_key_nodes.append(key_node)
        mapping = super().construct_mapping(node, deep=deep)
        seen: set[Any] = set()
        for key_node in authored_key_nodes:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate key {key!r}",
                    key_node.start_mark,
                )
            seen.add(key)
        return mapping


#: Longest ``repr`` this module ever interpolates into an operator-facing
#: message. A malformed state document is frequently a LARGE one (a whole
#: file pasted into the wrong key, a 5,000-entry list), and every message
#: below ends up in a `StateInvalid` an operator reads on one terminal
#: line -- so the value is abbreviated rather than echoed whole (review
#: finding). Wide enough that a realistic offending value still shows in
#: full; short enough that nothing here can emit a multi-kilobyte line.
_MAX_INTERPOLATED_REPR = 120


def _abbreviate(value: Any) -> str:
    """``repr(value)``, truncated to ``_MAX_INTERPOLATED_REPR`` characters
    with a trailing ellipsis when it would otherwise run longer.

    The truncation marker is deliberately visible: an operator must be able
    to tell "this is the value, in full" from "this is the front of it",
    because the second reading is the one that sends them to the file
    itself."""
    rendered = repr(value)
    if len(rendered) <= _MAX_INTERPOLATED_REPR:
        return rendered
    return f"{rendered[: _MAX_INTERPOLATED_REPR - 3]}..."


def _require_key(data: dict[str, Any], key: str, *, context: str) -> Any:
    """Look up ``key`` in ``data``, raising ``ValueError`` naming both the
    missing key and which type's ``from_json_dict`` was reading it --
    mirrors ``plan/types.py``'s identical helper, for the identical
    reason (a bare ``KeyError`` does not say which document key is
    missing without re-reading the traceback)."""
    if key not in data:
        raise ValueError(f"{context}: missing required key {key!r}")
    return data[key]


def _require_str(value: Any, *, context: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{context}: expected a str, got {_abbreviate(value)}")
    return value


def _require_int(value: Any, *, context: str) -> int:
    # `isinstance(value, bool)` is excluded explicitly -- `bool` is a
    # subtype of `int` in Python, so `True` would otherwise load as the
    # byte offset `1`. Same stance as `plan/types.py::_require_bool`'s
    # mirror-image check.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{context}: expected an int, got {_abbreviate(value)}")
    return value


def _require_str_tuple(value: Any, *, context: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{context}: expected a list, got {_abbreviate(value)}")
    return tuple(_require_str(item, context=f"{context}[]") for item in value)


def _require_object_list(value: Any, *, context: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{context}: expected a list of JSON objects, got {_abbreviate(value)}")
    return value


def _reject_duplicates(values: tuple[str, ...], *, context: str) -> None:
    """Raise ``ValueError`` naming every repeated member of ``values``.

    State's own version of ``model/manifest.py``'s entry-id uniqueness
    rule, which state has to repeat rather than import (the no-upward /
    no-``model.manifest`` import surface): a second ``managed`` entry
    claiming the same ``id`` -- or the same ``path`` -- makes the
    recorded-hash lookup ORDER-dependent, so ``check_managed_file`` would
    compare against whichever of the two duplicate rows happened to be
    found first."""
    duplicates = sorted({value for value in values if values.count(value) > 1})
    if duplicates:
        raise ValueError(f"{context}: must be unique, got duplicates: {duplicates}")


@dataclass(frozen=True)
class RegionSpanRecord:
    """A managed region's identity, body extent and body hash, as recorded
    in state: the region ``name``, the UTF-8 BYTE offsets of its body
    (markers excluded -- mirroring ``regions/parse.py``'s
    ``RegionSpan.name`` + ``RegionSpan.body_span``), and the ``body_sha`` of
    that body.

    Deliberately NOT a serialization of the whole ``RegionSpan``: AD-58
    needs only enough to withdraw the tool's claim (strip the region
    without touching surrounding content), and a recorded
    ``begin_span``/``end_span``/declared ``sha`` would be three more
    values to keep true across every subsequent hand-edit of the
    surrounding file.

    ``body_sha`` is ``detect/hashes.py::hash_content``'s shipped shape (8
    lowercase hex), enforced by the schema's own ``pattern`` rather than
    re-checked here, exactly as ``ManagedArtifact.body_sha`` is (Story
    82.13). It is per region because rung 6 compares each region body to its
    own recorded value: with one artifact-level hash, every sibling of the
    one region state could attest to had nothing to compare against."""

    name: str
    start: int
    end: int
    body_sha: str

    def __post_init__(self) -> None:
        """Reject a negative or INVERTED span at construction, the same
        ``0 <= start <= end`` rule ``fs.replace_span`` already applies to
        its own arguments and for the same reason (review finding).

        Ordinary Python slice semantics accept ``end < start`` silently,
        and an eject splice built from such a record --
        ``doc[:start] + doc[end:]`` -- then DUPLICATES the bytes between
        them instead of stripping a region: the exact opposite of AD-58's
        "withdraw the claim without touching surrounding content". A plain
        ``ValueError`` rather than a ``SeedError`` leaf, matching this
        module's other caller-contract checks; ``read_state`` is the layer
        that turns it into ``StateInvalid``."""
        if not (0 <= self.start <= self.end):
            raise ValueError(
                f"RegionSpanRecord: requires 0 <= start <= end, got start={self.start!r}, end={self.end!r}"
            )

    def to_json_dict(self) -> dict[str, Any]:
        return {"name": self.name, "start": self.start, "end": self.end, "body_sha": self.body_sha}

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> RegionSpanRecord:
        if not isinstance(data, dict):
            raise ValueError(f"RegionSpanRecord: expected a JSON object, got {_abbreviate(data)}")
        return cls(
            name=_require_str(
                _require_key(data, "name", context="RegionSpanRecord"),
                context="RegionSpanRecord.name",
            ),
            start=_require_int(
                _require_key(data, "start", context="RegionSpanRecord"),
                context="RegionSpanRecord.start",
            ),
            end=_require_int(
                _require_key(data, "end", context="RegionSpanRecord"),
                context="RegionSpanRecord.end",
            ),
            body_sha=_require_str(
                _require_key(data, "body_sha", context="RegionSpanRecord"),
                context="RegionSpanRecord.body_sha",
            ),
        )


@dataclass(frozen=True)
class ManagedArtifact:
    """One artifact the tool currently claims (AD-58): its manifest
    ``id``, its repo-relative ``path``, its class, the ``body_sha`` last
    recorded for it, and -- for a ``hybrid-managed-region`` claim -- one
    ``RegionSpanRecord`` per region installed into an otherwise human-owned
    file.

    ``artifact_class`` (not ``class`` -- a reserved word) serializes to
    the YAML key literally spelled ``class``, matching
    ``model/manifest.py::ManifestEntry``'s own convention. It carries the
    WIRE string, never ``ArtifactClass``: this module may not import
    ``model.manifest`` (module docstring's import surface), and the
    schema's own ``class`` enum is the contract either way.

    ``body_sha`` carries ``detect/hashes.py::hash_content``'s shipped
    shape (8 lowercase hex, no prefix), enforced by the schema's own
    ``pattern`` rather than re-checked here -- which is what makes a
    malformed recorded hash a ``StateInvalid`` at READ time, so it can
    never reach ``check_managed_file``/``check_managed_region`` at all.

    ``inserted_region_spans`` is non-empty for a ``hybrid-managed-region``
    claim and ``()`` for every other class -- an IFF, enforced in
    ``__post_init__`` and mirrored by ``schema.json``'s own
    ``if``/``then``/``else`` on ``class``. It holds one span per installed
    region (Story 82.13), so a hybrid artifact declaring several regions can
    attest to each of them: the opt-out of one deleted region no longer
    leaves its siblings unrecorded. A hybrid's ``body_sha`` is its FIRST
    span's, so the two cannot disagree about the one region both name."""

    id: str
    path: str
    artifact_class: str
    body_sha: str
    inserted_region_spans: tuple[RegionSpanRecord, ...]

    def __post_init__(self) -> None:
        """Couple ``class`` to ``inserted_region_spans``: non-empty if and
        only if the class is ``hybrid-managed-region``, with unique region
        names and a ``body_sha`` that is the first span's.

        Each rule is one a JSON Schema keyword cannot state (a uniqueness
        BY A FIELD, an equality between two fields) or one the schema states
        and this constructor must keep true for a code-constructed value
        too. A hybrid claim with no span is one an eject cannot withdraw at
        all (AD-58 needs the byte offsets); a whole-file claim carrying a
        span invites an eject to splice a file it was supposed to remove
        outright; two spans of one name leave a recorded-hash lookup
        order-dependent, the failure ``_reject_duplicates`` exists for. A
        ``list`` is accepted and frozen to a ``tuple``, as ``SeedState``
        does for its own sequences."""
        spans = self.inserted_region_spans
        if not isinstance(spans, (list, tuple)) or not all(isinstance(span, RegionSpanRecord) for span in spans):
            raise ValueError(
                f"ManagedArtifact {self.id!r}: inserted_region_spans must be a sequence of"
                f" RegionSpanRecord, got {_abbreviate(spans)}"
            )
        object.__setattr__(self, "inserted_region_spans", tuple(spans))
        spans = self.inserted_region_spans
        if self.artifact_class == _REGION_ARTIFACT_CLASS and not spans:
            raise ValueError(
                f"ManagedArtifact {self.id!r}: class {_REGION_ARTIFACT_CLASS!r} requires an"
                " inserted_region_spans entry (an eject cannot withdraw the claim without it)"
            )
        if spans and self.artifact_class != _REGION_ARTIFACT_CLASS:
            raise ValueError(
                f"ManagedArtifact {self.id!r}: inserted_region_spans belongs only to class"
                f" {_REGION_ARTIFACT_CLASS!r}, got {self.artifact_class!r}"
            )
        _reject_duplicates(
            tuple(span.name for span in spans),
            context=f"ManagedArtifact {self.id!r}: inserted_region_spans[].name",
        )
        if spans and self.body_sha != spans[0].body_sha:
            raise ValueError(
                f"ManagedArtifact {self.id!r}: body_sha {self.body_sha!r} must equal its first"
                f" inserted_region_spans entry's body_sha ({spans[0].body_sha!r}, region {spans[0].name!r})"
            )

    def to_json_dict(self) -> dict[str, Any]:
        """Always the new shape: ``inserted_region_spans`` as an array
        (``[]`` for a non-hybrid claim). The old one-span key is never
        emitted -- it is read-only (see ``from_json_dict``)."""
        return {
            "id": self.id,
            "path": self.path,
            "class": self.artifact_class,
            "body_sha": self.body_sha,
            "inserted_region_spans": [span.to_json_dict() for span in self.inserted_region_spans],
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> ManagedArtifact:
        """The inverse of ``to_json_dict``, which also reads the shape every
        state file written before Story 82.13 carries.

        That shape had ONE nullable ``inserted_region_span`` (an object for a
        hybrid claim, ``None`` otherwise) and no hash of its own, because the
        artifact's ``body_sha`` was that region's. It loads as a one-element
        ``inserted_region_spans`` whose ``body_sha`` is the artifact's, or
        ``()`` for ``None`` -- so no old file is rejected, and the next
        ``write_state`` rewrites it in the new shape. Carrying both keys, or
        neither, is a shape violation (the schema's ``oneOf`` already refuses
        it at read time; this is the same rule for a direct caller)."""
        if not isinstance(data, dict):
            raise ValueError(f"ManagedArtifact: expected a JSON object, got {_abbreviate(data)}")
        body_sha = _require_str(
            _require_key(data, "body_sha", context="ManagedArtifact"),
            context="ManagedArtifact.body_sha",
        )
        has_spans = "inserted_region_spans" in data
        has_legacy_span = "inserted_region_span" in data
        if has_spans == has_legacy_span:
            raise ValueError(
                "ManagedArtifact: carries exactly one of 'inserted_region_spans' and"
                f" 'inserted_region_span', got {'both' if has_spans else 'neither'}"
            )
        spans: tuple[RegionSpanRecord, ...]
        if has_spans:
            spans = tuple(
                RegionSpanRecord.from_json_dict(item)
                for item in _require_object_list(
                    data["inserted_region_spans"], context="ManagedArtifact.inserted_region_spans"
                )
            )
        else:
            legacy_span = data["inserted_region_span"]
            if legacy_span is None:
                spans = ()
            elif isinstance(legacy_span, dict):
                spans = (RegionSpanRecord.from_json_dict({**legacy_span, "body_sha": body_sha}),)
            else:
                raise ValueError(
                    f"ManagedArtifact.inserted_region_span: expected a JSON object or null, got {_abbreviate(legacy_span)}"
                )
        return cls(
            id=_require_str(
                _require_key(data, "id", context="ManagedArtifact"),
                context="ManagedArtifact.id",
            ),
            path=_require_str(
                _require_key(data, "path", context="ManagedArtifact"),
                context="ManagedArtifact.path",
            ),
            artifact_class=_require_str(
                _require_key(data, "class", context="ManagedArtifact"),
                context="ManagedArtifact.class",
            ),
            body_sha=body_sha,
            inserted_region_spans=spans,
        )


@dataclass(frozen=True)
class LegacyArtifact:
    """One entry classified ``present-legacy``, the persisted form of
    ``detect/inventory.py``'s in-memory ``LegacyRecord``. Its
    ``entry_id`` is spelled ``id`` on the wire, matching
    ``managed[]``'s own key; ``path`` and ``legacy_of`` are unchanged.

    The field names are MIRRORED here, never imported: ``state`` must not
    import ``detect`` (the architecture's no-upward-imports rule)."""

    id: str
    path: str
    legacy_of: str

    def to_json_dict(self) -> dict[str, Any]:
        return {"id": self.id, "path": self.path, "legacy_of": self.legacy_of}

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> LegacyArtifact:
        if not isinstance(data, dict):
            raise ValueError(f"LegacyArtifact: expected a JSON object, got {_abbreviate(data)}")
        return cls(
            id=_require_str(
                _require_key(data, "id", context="LegacyArtifact"),
                context="LegacyArtifact.id",
            ),
            path=_require_str(
                _require_key(data, "path", context="LegacyArtifact"),
                context="LegacyArtifact.path",
            ),
            legacy_of=_require_str(
                _require_key(data, "legacy_of", context="LegacyArtifact"),
                context="LegacyArtifact.legacy_of",
            ),
        )


@dataclass(frozen=True)
class SeedState:
    """The whole state document, in memory -- the eleven fields FR-102 and
    the epics AC name, and nothing else.

    Every collection is a ``tuple``, never a ``list``: this is a frozen
    value object callers compare and pass around, and a mutable member
    would make ``frozen=True`` a half-promise (the same reasoning
    ``fs.NeverWrite`` and ``plan.types.Plan`` already apply).

    ``model_version`` is a typed ``ModelVersion`` (A-05's operating-model
    clock, whose ordering matters for migrations); ``seed_model_version``
    stays a plain ``str`` -- it is an installed distribution's PEP 440
    version, a provenance record this module never orders or compares.

    ``__post_init__`` does exactly the work ``schema.json`` CANNOT do, and
    no more: it coerces each sequence field to a ``tuple`` and enforces the
    cross-entry rules no JSON Schema keyword can express. Everything a
    schema keyword already covers (patterns, enums, required keys) stays
    there and is deliberately NOT re-checked here -- a hand-written second
    copy of those rules could only drift.

    * **Coercion** (mirroring ``fs.NeverWrite.__post_init__``'s technique,
      ``object.__setattr__`` on a frozen dataclass). A type hint is not
      runtime enforcement: ``SeedState(agents=["claude"], ...)`` previously
      wrote fine, came back from ``read_state`` as a NON-equal object, and
      let ``state.agents.append(...)`` mutate the "frozen" instance --
      making ``frozen=True`` a half-promise, the exact defect Story 7.4
      already closed on ``NeverWrite`` and ``Manifest`` (review finding).
    * **Uniqueness across entries.** Duplicate ``managed[].id`` /
      ``managed[].path`` and duplicate ``legacy[].id`` are rejected, the
      same invariant ``model/manifest.py`` enforces for manifest entries:
      two rows claiming one artifact make the recorded-hash lookup
      order-dependent. ``uniqueItems`` cannot express "unique BY A FIELD".
    * **Version-wise ``migrations_applied`` uniqueness.**
      ``uniqueItems`` compares strings, but ``ModelVersion`` excludes build
      metadata from equality (SemVer 2.0.0 section 10), so ``["1.2.0",
      "1.2.0+build"]`` passed as two entries while naming ONE version --
      and a migration guarded by that list could run twice, the single
      thing it exists to prevent."""

    model_version: ModelVersion
    seed_model_version: str
    adopted_at: str
    last_update: str
    mode: str
    agents: tuple[str, ...]
    managed: tuple[ManagedArtifact, ...]
    skips: tuple[str, ...]
    legacy: tuple[LegacyArtifact, ...]
    migrations_applied: tuple[str, ...]
    opted_out: tuple[str, ...]

    def __post_init__(self) -> None:
        for name, item_type in (
            ("agents", str),
            ("managed", ManagedArtifact),
            ("skips", str),
            ("legacy", LegacyArtifact),
            ("migrations_applied", str),
            ("opted_out", str),
        ):
            self._coerce_sequence(name, item_type)

        # The one field whose declared type no JSON Schema can police:
        # `to_json_dict` renders `model_version` through `str(...)`, so a
        # plain `str` passed here serializes identically, validates, is
        # written -- and comes back from `read_state` as a `ModelVersion`,
        # a silently NON-equal round-trip. It is the same half-promise the
        # sequence coercion above closes, on the one field that is not a
        # `str` the schema already checks (review finding).
        if not isinstance(self.model_version, ModelVersion):
            raise ValueError(
                "SeedState.model_version: must be a ModelVersion, not"
                f" {type(self.model_version).__name__} -- parse it with"
                " ModelVersion.parse() so the value round-trips equal"
            )

        _reject_duplicates(tuple(artifact.id for artifact in self.managed), context="SeedState.managed[].id")
        _reject_duplicates(
            tuple(artifact.path for artifact in self.managed),
            context="SeedState.managed[].path",
        )
        _reject_duplicates(tuple(artifact.id for artifact in self.legacy), context="SeedState.legacy[].id")

        # `ModelVersion.parse` raises `InvalidVersionError`, itself a
        # `ValueError` -- the same class every other check here raises.
        applied: list[tuple[ModelVersion, str]] = []
        for entry in self.migrations_applied:
            version = ModelVersion.parse(entry)
            for seen_version, seen_entry in applied:
                if seen_version == version:
                    raise ValueError(
                        "SeedState.migrations_applied: must name each model version"
                        f" once, but {entry!r} and {seen_entry!r} are the same version"
                        " (build metadata does not make two versions distinct --"
                        " SemVer 2.0.0 section 10)"
                    )
            applied.append((version, entry))

    def _coerce_sequence(self, name: str, item_type: type) -> None:
        """Freeze one sequence field to a ``tuple`` of ``item_type``.

        A ``list`` and a ``tuple`` are both accepted (callers legitimately
        build lists); a ``str`` is NOT, even though it is iterable, because
        ``tuple("claude")`` would silently become six one-character
        "agents"."""
        value = getattr(self, name)
        if not isinstance(value, (list, tuple)) or not all(isinstance(item, item_type) for item in value):
            raise ValueError(f"SeedState.{name}: expected a sequence of {item_type.__name__}, got {_abbreviate(value)}")
        object.__setattr__(self, name, tuple(value))

    def to_json_dict(self) -> dict[str, Any]:
        """Fixed key order -- ``STATE_KEYS``, which is also the order
        ``schema.json`` requires them in, so a human diffing two state
        files never sees a reordering that means nothing."""
        return {
            "model_version": str(self.model_version),
            "seed_model_version": self.seed_model_version,
            "adopted_at": self.adopted_at,
            "last_update": self.last_update,
            "mode": self.mode,
            "agents": list(self.agents),
            "managed": [artifact.to_json_dict() for artifact in self.managed],
            "skips": list(self.skips),
            "legacy": [artifact.to_json_dict() for artifact in self.legacy],
            "migrations_applied": list(self.migrations_applied),
            "opted_out": list(self.opted_out),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> SeedState:
        """The inverse of ``to_json_dict``. Raises a plain ``ValueError``
        naming the offending field for anything that does not fit --
        never a ``SeedError`` leaf: this is a caller-contract violation on
        load, the same class ``plan/types.py``'s own ``from_json_dict``
        reports. ``read_state`` is the layer that translates it into
        ``StateInvalid``, so a direct caller of this method still sees the
        precise shape complaint."""
        if not isinstance(data, dict):
            raise ValueError(f"SeedState: expected a JSON object, got {_abbreviate(data)}")
        raw_managed = _require_object_list(
            _require_key(data, "managed", context="SeedState"), context="SeedState.managed"
        )
        raw_legacy = _require_object_list(_require_key(data, "legacy", context="SeedState"), context="SeedState.legacy")
        raw_model_version = _require_str(
            _require_key(data, "model_version", context="SeedState"),
            context="SeedState.model_version",
        )
        return cls(
            # `ModelVersion.parse` raises `InvalidVersionError`, itself a
            # `ValueError` -- the same class every other failure here
            # raises, so no separate translation is needed.
            model_version=ModelVersion.parse(raw_model_version),
            seed_model_version=_require_str(
                _require_key(data, "seed_model_version", context="SeedState"),
                context="SeedState.seed_model_version",
            ),
            adopted_at=_require_str(
                _require_key(data, "adopted_at", context="SeedState"),
                context="SeedState.adopted_at",
            ),
            last_update=_require_str(
                _require_key(data, "last_update", context="SeedState"),
                context="SeedState.last_update",
            ),
            mode=_require_str(_require_key(data, "mode", context="SeedState"), context="SeedState.mode"),
            agents=_require_str_tuple(_require_key(data, "agents", context="SeedState"), context="SeedState.agents"),
            managed=tuple(ManagedArtifact.from_json_dict(item) for item in raw_managed),
            skips=_require_str_tuple(_require_key(data, "skips", context="SeedState"), context="SeedState.skips"),
            legacy=tuple(LegacyArtifact.from_json_dict(item) for item in raw_legacy),
            migrations_applied=_require_str_tuple(
                _require_key(data, "migrations_applied", context="SeedState"),
                context="SeedState.migrations_applied",
            ),
            opted_out=_require_str_tuple(
                _require_key(data, "opted_out", context="SeedState"),
                context="SeedState.opted_out",
            ),
        )


def state_path(repo_root: Path) -> Path:
    """``<repo_root>/.marshal/seed-state.yml`` -- mirrors
    ``plan/build.py::default_plan_path``'s shape.

    Unlike ``.marshal/plan.json``, this path is deliberately NOT covered
    by the packaged ``.gitignore`` region: FR-107 keeps state git-tracked,
    because it is how a fresh clone learns what the tool already owns."""
    return repo_root / ".marshal" / "seed-state.yml"


@lru_cache(maxsize=1)
def _opt_out_pattern() -> re.Pattern[str]:
    """The packaged schema's OWN ``opted_out`` item pattern, compiled once
    per process.

    Read through ``_load_schema()`` (defined below; resolved at call time)
    rather than transcribed here, so the runtime check and the wire contract
    are one rule: a key this function accepts is a key ``write_state``'s own
    validation accepts, permanently, without a second spelling free to drift.
    Not an import of ``regions.markers.REGION_NAME_PATTERN`` either -- that
    module is not on this one's import surface (module docstring), and it
    covers only the region HALF of the key.

    ``lru_cache`` here does NOT reintroduce the shared-mutable-object hazard
    ``_load_schema`` documents: a compiled ``re.Pattern`` is immutable, so
    every caller holding the same object can corrupt nothing for anyone else.
    Only the pattern is cached; ``_load_schema`` itself still re-parses.

    Matched with ``re.match``, not ``.fullmatch()``: the schema pattern is
    already anchored at BOTH ends (``^`` ... ``(?![\\s\\S])``) -- see the
    schema's own ``timestamp`` note on why the terminator is not a bare
    ``$`` -- so re-anchoring it would state the same rule twice.

    A packaged schema that parses but has lost this key (or carries a
    pattern ``re`` will not compile) is an ``InternalError`` (exit 10) with
    the same reinstall remedy ``_schema_text``/``_load_schema`` already give
    their own two failure modes -- not the bare ``KeyError``/``re.error``
    the raw subscript chain used to raise. Same corruption, same broken
    install, so the same loud, actionable exit; and the chain is reachable
    from ``build_plan`` via ``opt_out_key_or_none``, which is documented as
    degrading rather than crashing on a bad pair. ``opted_out.items`` is
    also one of only two INLINE patterns in a schema whose dominant
    convention is ``$ref: #/$defs/...``, so a future refactor toward that
    convention lands here first."""
    schema = _load_schema()
    try:
        pattern = schema["properties"]["opted_out"]["items"]["pattern"]
        return re.compile(pattern)
    except (KeyError, TypeError, re.error) as exc:
        raise InternalError(
            "the packaged seed-state schema has no usable properties.opted_out.items.pattern",
            remedy="reinstall pyforge-marshal; the packaged schema.json is corrupt",
        ) from exc


def opt_out_key_or_none(artifact_id: str, region: str) -> str | None:
    """``f"{artifact_id}#{region}"`` if the schema's ``opted_out`` grammar
    admits it, else ``None`` -- the one place the key is spelled.

    Split out from ``opt_out_key`` because the two callers need OPPOSITE
    handling of an inadmissible pair. Recording one is a caller-contract
    violation and must raise; ASKING whether one is recorded has a
    well-defined answer without raising -- no, because a key this grammar
    rejects can never appear in a schema-valid ``opted_out`` list at all.

    PUBLIC, and re-exported from ``seed/state/__init__.py``, because that
    second half is not this module's question alone: ``plan/build.py`` asks
    exactly it, once per declared region, and had grown its own
    ``try``/``except ValueError`` around ``opt_out_key`` to spell the same
    "inadmissible key means not-opted-out" rule a second time. One function
    with two documented answers is the whole reason this one exists; a
    private name would have left every consumer outside this module
    re-deriving it.

    **Why both halves are ``isinstance``-checked before interpolation.**
    An f-string renders ANY object, so a non-``str`` half used to reach the
    pattern as its ``repr``: ``opt_out_key(None, "tiers")`` rendered
    ``"None#tiers"``, which the grammar HAPPILY matches -- a perfectly
    schema-valid key naming an artifact id no manifest can ever carry, so
    the opt-out it records is one no ``--reinstate`` and no re-insertion can
    ever clear. A type hint is not runtime enforcement (the same reasoning
    ``SeedState.__post_init__``'s coercion applies, and the same defensive
    re-check ``_require_str`` and ``detect/inventory.py::_uncovered_reason``
    make on fields their own constructors already typed): the check has to
    exist here, ahead of the interpolation, because after it the evidence is
    gone."""
    if not isinstance(artifact_id, str) or not isinstance(region, str):
        return None
    key = f"{artifact_id}#{region}"
    return key if _opt_out_pattern().match(key) is not None else None


def opt_out_key(artifact_id: str, region: str) -> str:
    """The wire spelling of one opt-out: ``<artifact-id>#<region>``.

    Raises ``ValueError`` naming the offending pair when the rendered key
    does not match the packaged schema's own ``opted_out`` item pattern --
    a plain ``ValueError``, not a ``SeedError`` leaf, matching this module's
    other caller-contract checks (``RegionSpanRecord.__post_init__``,
    ``utc_timestamp``) and ``plan/build.py``'s own mismatched-argument
    raise. Raising HERE rather than at ``write_state`` is the point: a
    caller that mints an unrepresentable key learns it at the call that
    minted it, not three layers later as an anonymous schema violation
    against a document it can no longer explain.

    The two halves fail for different reasons, both named by the message:
    each must be a ``str`` (see ``opt_out_key_or_none`` on why a non-``str``
    half is refused BEFORE it is interpolated rather than after), the
    artifact half must carry no whitespace and no ``#`` (the separator
    itself -- the grammar every manifest id and ``managed[].id`` is held to
    too, Story 82.13, so any id state can hold is spellable here), while the
    region half is ``regions.markers``'s marker-safe
    token -- lowercase alnum, then alnum or hyphen -- so an opted-out region
    name can always be rendered back into a real marker."""
    key = opt_out_key_or_none(artifact_id, region)
    if key is None:
        raise ValueError(
            f"opt_out_key({_abbreviate(artifact_id)}, {_abbreviate(region)}): the"
            " rendered key does not match the seed-state schema's opted_out pattern"
            f" {_opt_out_pattern().pattern!r} -- both halves must be str, the artifact"
            " half must carry no whitespace and no '#', and the region half must be a"
            " marker-safe token (lowercase alnum, then alnum or hyphen)"
        )
    return key


def is_opt_out_key(key: object) -> bool:
    """Whether ``key`` is already a rendered opt-out key this grammar
    admits -- the ASKING half for a key that arrives whole, where
    ``opt_out_key_or_none`` is the asking half for a pair that arrives in
    two pieces.

    PUBLIC for the same reason ``opt_out_key_or_none`` is: ``plan/build.py``
    takes a set of ALREADY-rendered keys and had no way to check one
    without either splitting it back into halves (re-deriving "a key is two
    halves joined by ``#``", which is part of the grammar and so a second
    spelling of it) or reaching into ``_opt_out_pattern``. Both are the
    defect this group of functions exists to avoid.

    Takes ``object``, not ``str``: its whole job is policing input a type
    hint did not, so a non-``str`` answers ``False`` rather than raising --
    the same tolerance ``opt_out_key_or_none`` shows a non-``str`` half,
    and for the same reason (see its docstring)."""
    return isinstance(key, str) and _opt_out_pattern().match(key) is not None


def is_opted_out(state: SeedState | None, artifact_id: str, region: str) -> bool:
    """Whether ``state`` records an opt-out for this artifact/region pair.

    Takes ``SeedState | None``, unlike the two mutators below, because that
    is the type ``read_state`` actually returns: a never-adopted repo has
    recorded no opt-out for anything, which is a true and useful answer
    (``False``), not a caller error every consumer would have to guard
    around. The mutators cannot be tolerant the same way -- there is no
    ``SeedState`` to derive a new one FROM.

    An inadmissible pair answers ``False`` rather than raising, for the
    reason ``opt_out_key_or_none`` documents: such a key cannot appear in a
    schema-valid ``opted_out`` at all, so "is it recorded?" is answerable
    without minting it."""
    if state is None:
        return False
    key = opt_out_key_or_none(artifact_id, region)
    return key is not None and key in state.opted_out


def _require_state(state: SeedState | None, *, context: str) -> SeedState:
    """``state``, or a ``ValueError`` naming ``context`` when it is ``None``.

    ``read_state`` returns ``SeedState | None``, so a caller handing the
    ``None`` straight through to a mutator is a realistic mistake rather
    than a hypothetical one -- and an unguarded ``dataclasses.replace(None,
    ...)`` reaches the operator as ``AttributeError: 'NoneType' object has
    no attribute 'managed'``, which names neither the function they called
    nor what they got wrong. ``is_opted_out`` is deliberately NOT routed
    through this: "has a never-adopted repo recorded this opt-out?" has a
    true answer (``False``), while "derive a new state from no state" has
    none."""
    if state is None:
        raise ValueError(
            f"{context}: requires a SeedState, got None -- read_state returns None"
            " for a never-adopted repo, and there is no state to derive a new one"
            " FROM; establish the repo (`marshal seed init` / `adopt`) or handle"
            " the None before calling"
        )
    return state


def _without_region_claim(state: SeedState, artifact_id: str, region: str) -> tuple[ManagedArtifact, ...]:
    """``state.managed`` minus the claim on ONE region of ONE artifact: the
    span named ``region`` is dropped from the entry whose ``id`` is
    ``artifact_id``, and the entry itself goes only when no span is left.

    THE one spelling of that filter, consumed by both mutators, so the claim
    ``record_opt_out`` drops and the claim ``clear_opt_out`` drops can never
    become two subtly different rules. A hybrid entry holds one span per
    installed region (Story 82.13), so opting out of one region leaves its
    siblings' claims standing: the entry is rebuilt with the remaining spans,
    and its ``body_sha`` follows the new first span (``ManagedArtifact`` keeps
    the two equal). Dropping the whole entry is forced only when the last span
    goes, by the span-present-iff-hybrid invariant, which forbids a hybrid
    claim with no span. A whole-file claim on the same id (no span at all), an
    entry that does not record ``region``, and a claim on a different
    ARTIFACT id are all left untouched."""
    kept: list[ManagedArtifact] = []
    for artifact in state.managed:
        remaining = tuple(span for span in artifact.inserted_region_spans if span.name != region)
        if artifact.id != artifact_id or len(remaining) == len(artifact.inserted_region_spans):
            kept.append(artifact)
        elif remaining:
            kept.append(dataclasses.replace(artifact, body_sha=remaining[0].body_sha, inserted_region_spans=remaining))
    return tuple(kept)


def record_opt_out(state: SeedState, artifact_id: str, region: str) -> SeedState:
    """Record an opt-out for one artifact/region pair, returning a NEW
    ``SeedState`` -- ``dataclasses.replace``, never an in-place mutation of
    a frozen value object (and never a write: persisting is the calling
    verb's job, through the existing ``write_state``).

    Two edits, not one. ``opted_out`` gains the key, DEDUPED and SORTED, so
    recording the same pairs in two different orders writes byte-identical
    state -- and so calling this twice is a no-op the second time.

    ``managed`` LOSES the artifact's claim on that region, through
    ``_without_region_claim``. Relinquishing the claim is what makes
    ``clear_opt_out`` real: were it retained, the "installed once, markers
    now deleted" derivation would re-derive this opt-out on every later run,
    so a reinstate could never take effect and ``--reinstate`` would be
    inert. AD-58 reads the same way: ``managed[]`` is Genesis's claim on an
    artifact, and an opt-out withdraws it; the next apply's insertion
    re-establishes it.

    **Only that region's claim goes.** A hybrid artifact records one span per
    installed region (Story 82.13, DW-FU-8-5-6), so opting out of one of
    several leaves the others' claims -- and their hashes, which rung 6 and
    ``check`` compare against -- standing, and the entry goes whole only when
    its last span does. Until 82.13 state held at most ONE span per artifact:
    an opt-out of a deleted region could be honoured for one region of a
    multi-region artifact, and its siblings fell to ``MISSING`` and were
    re-inserted. A whole-file claim on the same ``id`` and a claim on a
    DIFFERENT artifact id are untouched.

    **PRECONDITION, and it is the caller's to check: the region must not be
    PRESENT in the file.** Identical to ``clear_opt_out``'s, for the
    identical reason -- both mutators drop the claim through the same
    unconditional ``_without_region_claim``, and neither is given the file
    that alone distinguishes "markers deleted" from "markers still there"
    (review finding: this obligation was stated on one of the two and not
    the other). Called on a region still present, this discards a live
    claim and its recorded ``body_sha``, after which
    ``detect/hashes.py::check_managed_region`` has nothing to compare
    against and ``build_plan`` plans no insertion to rebuild it. See
    ``clear_opt_out`` for the full walk-through and for ``DW-FU-8-5-4``,
    the verb-side guard both mutators are waiting on: record only a pair
    ``detect/optout.py`` classifies ``OPTED_OUT`` -- which, by rung 1, a
    present region never is.

    Does NOT refresh ``last_update``. Stamping the write time belongs to the
    verb that PERSISTS the state -- ``write_state`` does not stamp it either
    -- so a verb must refresh it (``utc_timestamp()``) alongside this
    mutation. These two mutators are this module's first, and therefore set
    that convention."""
    state = _require_state(state, context="record_opt_out")
    key = opt_out_key(artifact_id, region)
    return dataclasses.replace(
        state,
        managed=_without_region_claim(state, artifact_id, region),
        opted_out=tuple(sorted(set(state.opted_out) | {key})),
    )


def clear_opt_out(state: SeedState, artifact_id: str, region: str) -> SeedState:
    """Withdraw one recorded opt-out, returning a NEW ``SeedState`` -- the
    mechanism S-10.6's ``adopt --reinstate`` calls, so a region the operator
    opted out of is planned for insertion again on the next run.

    Two edits, the same two ``record_opt_out`` makes, and the second one is
    what makes ``--reinstate`` work at all. Removing the ``opted_out`` key
    alone is NOT enough, because an opt-out has two sources and this
    function must withdraw both: ``detect/optout.py``'s ladder answers
    ``OPTED_OUT`` for a RECORDED key (rung 2) *and* for a surviving
    ``managed[]`` claim whose region is no longer in the file (rung 3).
    A DERIVED opt-out -- markers deleted, claim still present, ``opted_out``
    still empty because no mutating verb has run yet -- has no key to
    remove: clearing one that was never there is a no-op, rung 3 fires
    again on the very next run, and the region can never be reinstated. So
    ``managed`` loses that claim here too, through the same
    ``_without_region_claim`` filter, which is what turns the withdrawal
    into a real one.

    In the ordinary ``record_opt_out``-then-``clear_opt_out`` sequence that
    second edit is a NO-OP: ``record_opt_out`` already dropped the claim,
    and this function does not reconstruct it. Nor should it -- a claim
    records what the tool actually installed (``body_sha``, the inserted
    span's real byte offsets), facts a reinstate does not yet have because
    nothing has been inserted. The next apply re-establishes the claim from
    the write it actually performs.

    **PRECONDITION, and it is the caller's to check: the region must not be
    PRESENT in the file.** The claim drop above is unconditional, because
    state alone cannot tell the two claim-bearing cases apart -- "markers
    deleted, claim survives" (a derived opt-out, which must lose the claim)
    and "markers present, claim survives" (an ordinary managed region, which
    must keep it) differ only in the FILE, which this pure function never
    sees. Called on the second, it discards a live claim and with it the
    recorded ``body_sha``: ``detect/hashes.py::check_managed_region`` then
    reads the region as adopted out-of-band and reports a HARD
    ``managed-region-modified`` on every later run, while ``build_plan``
    plans no insertion (the region IS present), so nothing re-establishes
    the claim. Gating this inside the function is not possible without
    giving it the file, which the frozen ``(state, artifact_id, region)``
    signature forbids; the check therefore belongs to the verb that calls
    it, which already has the classification in hand -- clear only a pair
    ``detect/optout.py`` classifies ``OPTED_OUT``. Recorded as
    ``DW-FU-8-5-4`` until S-10.6's ``adopt --reinstate`` exists to carry it.

    Idempotent: clearing a pair that is not recorded and not claimed returns
    an equal ``SeedState``. Keeps ``opted_out`` sorted for the same
    byte-identity reason ``record_opt_out`` does. Raises the same
    ``ValueError`` as ``opt_out_key`` for an inadmissible pair -- a caller
    asking to clear a key that could never have been stored is stating a
    contract violation, not observing an empty result.

    Does NOT refresh ``last_update``, for the reason ``record_opt_out``'s
    own docstring gives: the stamp belongs to the verb that persists the
    result.

    Sorts AND DEDUPES what it keeps, exactly as ``record_opt_out`` does
    (review finding, confirmed by execution). ``SeedState.__post_init__``
    runs ``_reject_duplicates`` on ``managed[].id`` but not on
    ``opted_out``, so a hand-built state can carry a repeated key; the two
    mutators disagreed about it, and clearing an UNRELATED pair on such a
    state returned one whose surviving duplicates then failed
    ``write_state``'s ``uniqueItems`` check -- a reinstate that could not be
    persisted, reported against a key the caller never touched. Normalizing
    on the way out means either mutator repairs the shape, and neither can
    hand back a state the schema rejects."""
    state = _require_state(state, context="clear_opt_out")
    key = opt_out_key(artifact_id, region)
    return dataclasses.replace(
        state,
        managed=_without_region_claim(state, artifact_id, region),
        opted_out=tuple(sorted({entry for entry in state.opted_out if entry != key})),
    )


@lru_cache(maxsize=1)
def _schema_text() -> str:
    """The packaged ``state/schema.json``'s raw text, read once per
    process.

    Resolved through ``importlib.resources`` rather than ``__file__``
    arithmetic (the idiom ``engine/copier.py`` already uses for the
    packaged templates), so it keeps working from a zipped or relocated
    install.

    A missing or unreadable resource is an ``InternalError`` (exit 10), not
    a ``StateInvalid`` (review finding): ``_load_schema`` is called from
    inside ``read_state``'s ``except ValidationError`` scope, so the raw
    ``FileNotFoundError`` previously escaped the read path entirely and
    broke FR-104's "only ``StateInvalid``" contract -- and it would have
    been the WRONG finding anyway. A packaging failure is a broken
    installation; sending an operator to repair a state file that is
    perfectly fine is exactly the mislabelling this module's write path
    already refuses to do. ``lru_cache`` does not memoize exceptions, so a
    transient read failure is retried rather than pinned for the process."""
    try:
        schema_ref = resources.files("pyforge.marshal.seed.state") / _SCHEMA_FILENAME
        return schema_ref.read_text(encoding="utf-8")
    except (OSError, ModuleNotFoundError) as exc:
        raise InternalError(
            f"the packaged seed-state {_SCHEMA_FILENAME} could not be read: {exc}",
            remedy=(
                "reinstall pyforge-marshal -- the schema ships inside the distribution"
                " and its absence is a broken installation, not a problem with this"
                " repository's state file"
            ),
        ) from exc


def _load_schema() -> dict[str, Any]:
    """A FRESH parse of the packaged schema on every call.

    Deliberately not ``lru_cache``d itself: a cached call handed every
    caller the SAME mutable dict, so one caller mutating it (a test
    tweaking a pattern, a future helper popping a key) silently poisoned
    every later validation in the process (review finding). Only the TEXT
    is cached -- ``json.loads`` per call is microseconds and buys back a
    value nobody can corrupt for anyone else."""
    try:
        return json.loads(_schema_text())
    except json.JSONDecodeError as exc:
        raise InternalError(
            f"the packaged seed-state {_SCHEMA_FILENAME} is not valid JSON: {exc}",
            remedy=(
                "reinstall pyforge-marshal -- a corrupt packaged schema is a broken"
                " installation, not a problem with this repository's state file"
            ),
        ) from exc


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    """The one validator both ``read_state`` and ``write_state`` use.

    ``Draft202012Validator`` explicitly, never ``jsonschema.validate``:
    the latter re-infers the dialect from ``$schema`` on every call and
    re-compiles the schema each time, and a schema that lost its
    ``$schema`` line would silently validate under a different draft's
    semantics."""
    return Draft202012Validator(_load_schema())


def _validation_detail(error: ValidationError) -> str:
    """A ``ValidationError`` rendered as ``<field path>: <reason>``.

    ``json_path`` (e.g. ``$.managed[0].body_sha``) rather than the raw
    deque, because the AC requires the raised ``StateInvalid`` to NAME the
    offending field path -- and for a document-level failure (an unknown
    top-level key) ``json_path`` is just ``$``, which still reads
    correctly."""
    return f"{error.json_path}: {error.message}"


def read_state(repo_root: Path) -> SeedState | None:
    """Read, validate, and decode ``<repo_root>/.marshal/seed-state.yml``.

    Returns ``None`` when the file does not exist -- a never-adopted repo
    is not an invalid one, and ``marshal seed check`` must be able to run
    against it. A DANGLING SYMLINK at the state path is not absence: the
    link is itself the record that this repo was established, so a missing
    target is ``StateInvalid``.

    Raises ``StateInvalid`` (exit 5, always with a remedy) for every other
    failure: an unreadable file, non-UTF-8 bytes, malformed YAML, a
    duplicate mapping key, a merge key, a non-mapping root, a schema
    violation, or a shape violation ``SeedState.from_json_dict`` catches.
    No ``OSError``, ``UnicodeDecodeError``, ``yaml.YAMLError``, or
    ``jsonschema`` exception type ever escapes this function (FR-104)."""
    path = state_path(repo_root)
    try:
        raw_bytes = path.read_bytes()
    except FileNotFoundError as exc:
        # Checked by ATTEMPTING the read rather than by a prior
        # `path.exists()` probe: the probe form has a race window in which
        # the file can vanish between check and read, reporting a
        # never-adopted repo as invalid state. A directory at this path is
        # an `IsADirectoryError` -- an `OSError`, handled below -- not a
        # missing file, and is correctly reported as invalid.
        if path.is_symlink():
            # A DANGLING symlink raises the same FileNotFoundError as a
            # genuinely absent file, so the absence branch used to swallow
            # it and report an adopted repo as never-adopted -- after which
            # `init` could re-establish over an existing installation
            # (review finding). `is_symlink()` lstats, so it is True for a
            # broken link and False for real absence: the link EXISTS and
            # says this repo was adopted, only its target is gone.
            raise StateInvalid(
                f"{path} is a symlink whose target does not exist",
                remedy=(
                    "restore the link's target, or replace the link with the tracked"
                    " .marshal/seed-state.yml from version control -- do not re-run"
                    " `marshal seed init`, this repo has already been established"
                ),
            ) from exc
        return None
    except OSError as exc:
        raise StateInvalid(
            f"could not read {path}: {exc}",
            remedy=("check the file's permissions and that .marshal/seed-state.yml is a regular file, then re-run"),
        ) from exc

    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StateInvalid(
            f"{path} is not valid UTF-8: {exc}",
            remedy=(
                "restore the file from version control (it is git-tracked) or re-run"
                " `marshal seed adopt` to regenerate it"
            ),
        ) from exc

    try:
        # `_StrictLoader` is a `SafeLoader` subclass -- no arbitrary-object
        # construction, just `SafeLoader` plus duplicate-key rejection.
        document = yaml.load(text, Loader=_StrictLoader)
    except yaml.YAMLError as exc:
        raise StateInvalid(
            f"invalid YAML in {path}: {exc}",
            remedy=(
                "restore the file from version control (it is git-tracked) or re-run"
                " `marshal seed adopt` to regenerate it"
            ),
        ) from exc
    except RecursionError as exc:
        # PyYAML's composer recurses per nesting level, so a deeply nested
        # document blows the stack instead of reporting a `YAMLError` --
        # the same escape class `model/manifest.py::load_manifest` already
        # closes for the manifest.
        raise StateInvalid(
            f"{path} is nested too deeply to parse",
            remedy="restore the file from version control (it is git-tracked)",
        ) from exc

    if not isinstance(document, dict):
        raise StateInvalid(
            f"{path}: top-level document must be a mapping, got {_abbreviate(document)}",
            remedy=(
                "restore the file from version control (it is git-tracked) or re-run"
                " `marshal seed adopt` to regenerate it"
            ),
        )

    try:
        _validator().validate(document)
    except ValidationError as exc:
        raise StateInvalid(
            f"{path} does not match the seed-state schema -- {_validation_detail(exc)}",
            remedy=(
                "do not hand-edit this file; restore it from version control or re-run"
                " `marshal seed adopt` to regenerate it"
            ),
        ) from exc

    try:
        return SeedState.from_json_dict(document)
    except ValueError as exc:
        # Defense in depth: the schema above already rejects every shape
        # `from_json_dict` checks, so reaching here means the schema and
        # the dataclasses have drifted apart -- still a state problem from
        # the caller's point of view, never a traceback.
        raise StateInvalid(
            f"{path} could not be decoded: {exc}",
            remedy=(
                "restore the file from version control (it is git-tracked) or re-run"
                " `marshal seed adopt` to regenerate it"
            ),
        ) from exc


def write_state(state: SeedState, *, repo_root: Path, never_write: fs.NeverWrite) -> None:
    """Serialize ``state`` and write it to
    ``<repo_root>/.marshal/seed-state.yml`` in exactly one atomic replace.

    Validates the serialized document against the same packaged schema
    ``read_state`` uses, BEFORE any I/O: an invalid ``SeedState`` raises
    ``StateInvalid`` with nothing written and any existing file left
    byte-identical.

    The write itself is a single ``fs.write`` call -- the never-write
    guard (P-01), which delegates the atomic replace to
    ``pyforge.core.atomic_write`` (P-08). A ``NeverWriteViolation`` (exit
    4) or an ``OSError`` from that call propagates UNCHANGED: the
    environment refused the write, which is not the same fact as state
    being invalid.

    One further escape, documented rather than converted: a ``repo_root``
    that does not resolve to an existing DIRECTORY raises a plain
    ``ValueError`` from ``fs._guard`` -- outside the ``SeedError``
    taxonomy and not an ``OSError``, so a caller catching
    ``(SeedError, OSError)`` gets a traceback (review finding). Wrapping it
    here would fight ``fs.py``'s own contract, which raises exactly that
    ``ValueError`` on purpose: a wrong ``repo_root`` silently disables
    every repo-relative never-write pattern, so it must fail loudly as the
    caller bug it is, not be re-labelled as invalid state."""
    document = state.to_json_dict()
    try:
        _validator().validate(document)
    except ValidationError as exc:
        raise StateInvalid(
            f"refusing to write invalid seed state -- {_validation_detail(exc)}",
            remedy=("correct the SeedState field the message names before calling write_state (nothing was written)"),
        ) from exc

    body = yaml.safe_dump(
        document,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    fs.write(
        state_path(repo_root),
        (_HEADER + body).encode("utf-8"),
        repo_root=repo_root,
        never_write=never_write,
    )


def seed_model_version() -> str:
    """This package's own installed version -- A-05's second clock, and
    the value ``SeedState.seed_model_version`` records.

    Read from installed distribution metadata rather than a hardcoded
    constant, so it cannot drift from the artifact actually running.
    Raises ``InternalError`` (exit 10) if the distribution is not
    installed at all: that is a broken environment, not invalid state and
    not a user error."""
    try:
        return metadata.version("pyforge-marshal")
    except metadata.PackageNotFoundError as exc:
        raise InternalError(
            "the pyforge-marshal distribution is not installed, so its version cannot be recorded in seed state",
            remedy=(
                "install pyforge-marshal into the running environment (e.g."
                " `pixi run -e pyforge-marshal ...`) rather than importing it from a"
                " source tree on sys.path"
            ),
        ) from exc


def utc_timestamp(moment: datetime | None = None) -> str:
    """The ONE producer of ``adopted_at``/``last_update``'s wire shape:
    second-precision UTC RFC-3339, ``T``/``Z`` only -- exactly what
    ``schema.json``'s ``timestamp`` pattern accepts.

    ``moment`` defaults to now. An explicitly supplied NAIVE datetime
    raises ``ValueError``: ``astimezone`` would silently interpret it as
    LOCAL time, so a caller in a non-UTC zone would record an instant
    that never happened -- the class of silent error this module exists to
    prevent, and a caller-contract violation rather than a state failure
    (so a plain ``ValueError``, matching ``fs.replace_span``'s own
    upfront argument checks)."""
    if moment is None:
        return datetime.now(UTC).strftime(_TIMESTAMP_FORMAT)
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        raise ValueError(f"utc_timestamp requires a timezone-aware datetime, got naive {moment!r}")
    return moment.astimezone(UTC).strftime(_TIMESTAMP_FORMAT)


def copier_data(state: SeedState) -> dict[str, Any]:
    """The answers projection re-supplied to Copier via
    ``MaterializeRequest.data`` on every render (FR-105/AD-52).

    State is the single source of truth for these answers -- Genesis never
    reads them back out of the answers file Copier itself writes. The
    projection carries only what state actually KNOWS: the two clocks, the
    establishing mode, and the agent list. Per-invocation inputs a
    template also needs (notably ``slug``) are supplied by the verbs on
    top of this dict; state deliberately has no ``slug`` field, and
    inventing one would breach the eleven-key contract."""
    return {
        "model_version": str(state.model_version),
        "seed_model_version": state.seed_model_version,
        "mode": state.mode,
        "agents": list(state.agents),
    }
