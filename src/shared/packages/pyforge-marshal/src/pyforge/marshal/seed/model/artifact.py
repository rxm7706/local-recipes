"""``ClassBehavior``/``Artifact`` data layer (Story 7.5, PRD FR-127).

The extraction-manifest's classification rule (PRD § *The Extraction
Manifest*, architecture's own restatement in the classification-rule table)
names, for each of its five PRODUCT classes, a definition and two behaviors
-- what happens to the artifact on ``marshal seed update`` and what happens
when a human hand-edits it. That table is prose today; this module is its
data form, so a future ``marshal seed explain <artifact>`` (FR-127) can
render an entry's class contract by lookup rather than by re-deriving it
from documentation on every call -- "the model documenting itself to the
agents that read it" (PRD D1).

``CLASS_BEHAVIOR`` deliberately excludes ``ArtifactClass.UNCLASSIFIED_DEFERRED``:
that member is a V1 escape hatch for artifacts "too repo-specific to
classify confidently" (``manifest.py``'s own docstring), so it has no
update/hand-edit contract to describe -- there is nothing an ``explain``
call could honestly report beyond the entry's own ``rationale``.
``describe()`` raises rather than silently omitting one, matching the rest
of this package's house style of naming the offending id instead of
returning ``None`` for a caller to mishandle.

A DIRECTORY entry (a ``path`` ending in ``/``, ``ManifestEntry.is_directory``)
is described by ``DIRECTORY_BEHAVIOR`` rather than by its class's row (Story
86.1, ``DW-FU-7-5-2``): create-if-missing, with every entry beneath it
governed by its own class. Read literally against a directory over a
never-write subtree, ``generated-derived``'s "recomputed every run" was an
instruction to rewrite files the model forbids writing.

Same ``@dataclass(frozen=True)`` idiom as ``manifest.py`` and
``core/model.py``: these are immutable value objects other code (a future
``explain`` CLI, tests) should be able to hash and compare freely.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .manifest import ArtifactClass, ManifestEntry


@dataclass(frozen=True)
class ClassBehavior:
    """One product ``ArtifactClass``'s contract, transcribed verbatim from
    the PRD/architecture classification-rule table's three prose columns.

    ``definition`` is the class's own description (what kind of artifact it
    is); ``update_behavior`` is what ``marshal seed update`` does to an
    artifact of this class; ``hand_edit_behavior`` is what happens when a
    human hand-edits it outside the tool. All three are plain, pre-written
    sentences -- this dataclass carries no validation beyond typing, because
    its instances below (five class rows and ``DIRECTORY_BEHAVIOR``) are the
    module's own fixed, reviewed content, not user- or YAML-supplied data
    (unlike ``manifest.py``'s ``ManifestEntry``, which validates exactly
    because it parses an external file)."""

    definition: str
    update_behavior: str
    hand_edit_behavior: str


# Read-only, and with NO module-level mutable name behind it: every other
# value in this module is a frozen dataclass ("immutable value objects" per
# the module docstring), but the table that decides all of them was a plain
# dict -- and because ``Artifact.__post_init__`` validates against this same
# table, a rebound entry would corrupt ``describe()`` and still pass its own
# guard, undetectably from inside. A ``MappingProxyType`` over a dict that
# stays reachable under its own name does not close that: the proxy is a
# read-only VIEW, so mutating the underlying dict is fully visible through
# it. The literal is therefore built inline and never bound elsewhere.
CLASS_BEHAVIOR: Mapping[ArtifactClass, ClassBehavior] = MappingProxyType(
    {
        ArtifactClass.REFERENCED: ClassBehavior(
            definition=("Not materialized. The repo depends on it by version range; it lives upstream."),
            update_behavior="nothing in the repo changes",
            hand_edit_behavior="n/a",
        ),
        ArtifactClass.COPIED_MANAGED: ClassBehavior(
            definition=("Materialized, tool-owned. The repo should not hand-edit it."),
            update_behavior="regenerated wholesale",
            hand_edit_behavior="`check` reports; `update` refuses without `--force`",
        ),
        ArtifactClass.COPIED_SEEDED: ClassBehavior(
            definition=("Materialized once as a starting point, then repo-owned forever."),
            update_behavior="never touched",
            hand_edit_behavior="expected and fine",
        ),
        ArtifactClass.GENERATED_DERIVED: ClassBehavior(
            definition="Computed from the neutral contract and/or repo state.",
            update_behavior="recomputed every run (idempotent)",
            hand_edit_behavior="overwritten on next run; `check` reports",
        ),
        ArtifactClass.HYBRID_MANAGED_REGION: ClassBehavior(
            definition=("A repo-owned file containing a tool-owned, marker-delimited span."),
            update_behavior="only the span is replaced",
            hand_edit_behavior="`check` reports hash mismatch on the span only",
        ),
    }
)


#: The contract of a DIRECTORY entry, whatever its class (Story 86.1,
#: ``DW-FU-7-5-2``): ``describe()`` pairs it with every non-``referenced``
#: entry whose ``path`` ends in ``/``. A directory is a container, so it is
#: created when missing and otherwise left alone; the files beneath it --
#: ``dreams-dir``'s ``starter-dream``, ``project-subtree``'s
#: ``project-config`` and never-write ``planning-artifacts/`` -- follow their
#: own entries' classes and the never-write set, which wins beneath every
#: directory entry.
DIRECTORY_BEHAVIOR = ClassBehavior(
    definition=(
        "A directory, created if missing. What sits beneath it belongs to the entries that name it,"
        " each under its own class; a never-write path beneath it is never written."
    ),
    update_behavior="created if missing, never recomputed; every entry beneath it follows its own class",
    hand_edit_behavior="its contents follow the classes of the entries beneath it",
)


def _expected_behavior(entry: ManifestEntry) -> ClassBehavior | None:
    """The ``ClassBehavior`` ``entry`` must be paired with: its class's row, or
    ``DIRECTORY_BEHAVIOR`` for a non-``referenced`` directory entry; ``None``
    when its class has no contract at all (``unclassified-deferred``)."""
    behavior = CLASS_BEHAVIOR.get(entry.artifact_class)
    if behavior is not None and entry.is_directory and entry.artifact_class is not ArtifactClass.REFERENCED:
        return DIRECTORY_BEHAVIOR
    return behavior


def _behavior_name(behavior: ClassBehavior) -> str:
    """The wire name of whose contract ``behavior`` is, for a mismatch message."""
    if behavior == DIRECTORY_BEHAVIOR:
        return "a directory entry"
    owner = next((cls for cls, candidate in CLASS_BEHAVIOR.items() if candidate == behavior), None)
    # `.value`, not `.name`: `manifest.py` states the package convention
    # ("every neighbouring message in this module speaks the wire format
    # the author actually writes"), and the author reads these classes as
    # `class: hybrid-managed-region` in YAML -- never as a Python member
    # name.
    return owner.value if owner is not None else "an unrecognized class"


@dataclass(frozen=True)
class Artifact:
    """One manifest entry paired with its class's behavior contract -- the
    shape ``describe()`` returns and a future ``marshal seed explain``
    renders directly.

    ``describe()`` is the sanctioned constructor, but a plain frozen
    dataclass does not stop direct construction with a mismatched pair (an
    entry's own class's behavior swapped for another's) -- ``__post_init__``
    closes that the same way ``Manifest``/``ManifestEntry`` validate their
    own invariants at construction time (Story 7.4 review), not only in a
    factory a caller could bypass.

    Both fields are type-checked first, for the same reason
    ``Manifest.__post_init__`` type-checks its own members: without it a
    non-``ManifestEntry`` raises ``AttributeError`` from the class lookup
    rather than the ``ValueError`` this package's callers catch, and a
    ``None`` behavior paired with an ``unclassified-deferred`` entry would
    slip through the pairing check entirely (``CLASS_BEHAVIOR.get`` returns
    ``None`` for that class, so ``None == None`` short-circuits) -- leaving
    an ``Artifact`` whose ``behavior`` is ``None`` for a future ``explain``
    to dereference."""

    entry: ManifestEntry
    behavior: ClassBehavior

    def __post_init__(self) -> None:
        if not isinstance(self.entry, ManifestEntry):
            raise ValueError(f"entry must be a ManifestEntry, got {type(self.entry).__name__}")
        if not isinstance(self.behavior, ClassBehavior):
            raise ValueError(f"{self.entry.id}: behavior must be a ClassBehavior, got {type(self.behavior).__name__}")
        expected = _expected_behavior(self.entry)
        if expected is None:
            raise ValueError(
                f"{self.entry.id}: class {self.entry.artifact_class.value!r} has no "
                "ClassBehavior -- it describes only its own rationale, so it cannot "
                "be paired into an Artifact"
            )
        if self.behavior == expected:
            return
        raise ValueError(
            f"{self.entry.id}: behavior is {_behavior_name(self.behavior)}'s, not {_behavior_name(expected)}'s"
        )


def describe(entry: ManifestEntry) -> Artifact:
    """Pair ``entry`` with its class's ``ClassBehavior``.

    A directory entry (``ManifestEntry.is_directory``) is paired with
    ``DIRECTORY_BEHAVIOR`` instead of its class's row (Story 86.1).

    Raises ``ValueError`` naming the entry's id when ``entry.artifact_class``
    is ``unclassified-deferred`` (or any future class ``CLASS_BEHAVIOR``
    does not yet cover) -- matching this package's convention of naming the
    offending id rather than returning ``None`` for a caller to dereference
    unchecked.
    """
    behavior = _expected_behavior(entry)
    if behavior is None:
        raise ValueError(
            f"{entry.id}: no ClassBehavior for class {entry.artifact_class.value!r} -- "
            "unclassified-deferred artifacts describe only their own rationale, "
            "not an update/hand-edit contract"
        )
    return Artifact(entry=entry, behavior=behavior)
