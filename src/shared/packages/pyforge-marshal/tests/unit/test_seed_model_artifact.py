"""Unit tests for ``pyforge.marshal.seed.model.artifact`` (Story 7.5) --
``CLASS_BEHAVIOR``'s coverage of exactly the 5 product ``ArtifactClass``
members, ``describe()``'s pairing (including its refusal on
``unclassified-deferred``), and frozen/hashable dataclass conventions
matching ``test_seed_model_manifest.py``'s own house style.
"""

from __future__ import annotations

import dataclasses
import importlib

import pytest

from pyforge.marshal.seed.model.artifact import CLASS_BEHAVIOR, Artifact, describe
from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    ManifestEntry,
    Region,
)

# One class-appropriate ManifestEntry per product class, built directly
# (Story 7.4's own documented "constructible on their own" convention) --
# mirrors this package's fixture idiom rather than round-tripping through
# YAML, since this module's own subject is the CLASS_BEHAVIOR/describe
# pairing, not the loader.
_ENTRY_BY_CLASS = {
    ArtifactClass.REFERENCED: ManifestEntry(
        id="bmad-loop",
        artifact_class=ArtifactClass.REFERENCED,
        path="n/a",
        applies_to=AppliesTo.BOTH,
        rationale="upstream orchestrator, never vendored",
        pin=">=0.8.1",
    ),
    ArtifactClass.COPIED_MANAGED: ManifestEntry(
        id="bmad-switch",
        artifact_class=ArtifactClass.COPIED_MANAGED,
        path="scripts/bmad-switch",
        applies_to=AppliesTo.BOTH,
        rationale="tool-owned model machinery",
    ),
    ArtifactClass.COPIED_SEEDED: ManifestEntry(
        id="starter-dream",
        artifact_class=ArtifactClass.COPIED_SEEDED,
        path="docs/dreams/{{ slug }}.md",
        applies_to=AppliesTo.INIT,
        rationale="repo-owned from the moment it is written",
    ),
    ArtifactClass.GENERATED_DERIVED: ManifestEntry(
        id="gemini-md",
        artifact_class=ArtifactClass.GENERATED_DERIVED,
        path="GEMINI.md",
        applies_to=AppliesTo.BOTH,
        rationale="computed from the neutral contract",
    ),
    ArtifactClass.HYBRID_MANAGED_REGION: ManifestEntry(
        id="agents-md",
        artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
        path="AGENTS.md",
        applies_to=AppliesTo.BOTH,
        rationale="neutral contract must upgrade, rest is repo-owned",
        format="html",
        regions=(Region(name="tiers", anchor=("## The tiers",)),),
    ),
}

_PRODUCT_CLASSES = (
    ArtifactClass.REFERENCED,
    ArtifactClass.COPIED_MANAGED,
    ArtifactClass.COPIED_SEEDED,
    ArtifactClass.GENERATED_DERIVED,
    ArtifactClass.HYBRID_MANAGED_REGION,
)


def test_class_behavior_covers_exactly_the_5_product_classes():
    assert set(CLASS_BEHAVIOR.keys()) == set(_PRODUCT_CLASSES)
    assert ArtifactClass.UNCLASSIFIED_DEFERRED not in CLASS_BEHAVIOR


@pytest.mark.parametrize("artifact_class", _PRODUCT_CLASSES)
def test_every_product_class_behavior_has_non_empty_prose(artifact_class):
    behavior = CLASS_BEHAVIOR[artifact_class]
    assert behavior.definition.strip()
    assert behavior.update_behavior.strip()
    assert behavior.hand_edit_behavior.strip()


@pytest.mark.parametrize("artifact_class", _PRODUCT_CLASSES)
def test_describe_pairs_entry_with_its_own_class_behavior(artifact_class):
    entry = _ENTRY_BY_CLASS[artifact_class]
    artifact = describe(entry)
    assert isinstance(artifact, Artifact)
    assert artifact.entry is entry
    assert artifact.behavior == CLASS_BEHAVIOR[artifact_class]


def test_describe_pairs_do_not_cross_classes():
    """`describe()` must return the CALLER's own class's behavior, not just
    any behavior -- a regression that always returned e.g. REFERENCED's
    behavior would pass a looser "isinstance(Artifact)"-only test."""
    referenced_artifact = describe(_ENTRY_BY_CLASS[ArtifactClass.REFERENCED])
    hybrid_artifact = describe(_ENTRY_BY_CLASS[ArtifactClass.HYBRID_MANAGED_REGION])
    assert referenced_artifact.behavior != hybrid_artifact.behavior


def test_describe_raises_value_error_naming_the_id_for_unclassified_deferred():
    entry = ManifestEntry(
        id="claude-skills",
        artifact_class=ArtifactClass.UNCLASSIFIED_DEFERRED,
        path=".claude/skills/**",
        applies_to=AppliesTo.BOTH,
        rationale="too repo-specific to classify confidently at V1",
    )
    with pytest.raises(ValueError, match=r"^claude-skills: no ClassBehavior for class 'unclassified-deferred'"):
        describe(entry)


def test_class_behavior_and_artifact_are_frozen_and_hashable():
    """Matches `test_schema_dataclasses_are_frozen_and_hashable`'s own
    convention in `test_seed_model_manifest.py`: explicit `hash()` checks,
    not a vacuous non-empty-set-literal assertion that can never fail."""
    behavior = CLASS_BEHAVIOR[ArtifactClass.COPIED_MANAGED]
    artifact = describe(_ENTRY_BY_CLASS[ArtifactClass.COPIED_MANAGED])

    with pytest.raises(dataclasses.FrozenInstanceError):
        behavior.definition = "mutated"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        artifact.entry = artifact.entry  # type: ignore[misc]

    assert isinstance(hash(behavior), int)
    assert isinstance(hash(artifact), int)


# Verbatim wording from the PRD § *The Extraction Manifest* classification-
# rule table (mirrored in architecture's own restatement) -- all 3 prose
# columns for all 5 product classes, not a spot-check. A prior pass here
# checked only 2 of the 5 classes and missed a real dropped-backtick
# transcription error in COPIED_MANAGED.hand_edit_behavior; this table would
# have caught it.
_PRD_TABLE = {
    ArtifactClass.REFERENCED: (
        ("Not materialized. The repo depends on it by version range; it lives upstream."),
        "nothing in the repo changes",
        "n/a",
    ),
    ArtifactClass.COPIED_MANAGED: (
        "Materialized, tool-owned. The repo should not hand-edit it.",
        "regenerated wholesale",
        "`check` reports; `update` refuses without `--force`",
    ),
    ArtifactClass.COPIED_SEEDED: (
        "Materialized once as a starting point, then repo-owned forever.",
        "never touched",
        "expected and fine",
    ),
    ArtifactClass.GENERATED_DERIVED: (
        "Computed from the neutral contract and/or repo state.",
        "recomputed every run (idempotent)",
        "overwritten on next run; `check` reports",
    ),
    ArtifactClass.HYBRID_MANAGED_REGION: (
        "A repo-owned file containing a tool-owned, marker-delimited span.",
        "only the span is replaced",
        "`check` reports hash mismatch on the span only",
    ),
}


@pytest.mark.parametrize("artifact_class", _PRODUCT_CLASSES)
def test_class_behavior_transcribes_the_prd_classification_table_verbatim(artifact_class):
    """Every prose column, every class -- an accidental edit to any single
    field fails a specific, named case rather than passing silently because
    a different field/class happened to be the one spot-checked.

    Scope, stated honestly: `_PRD_TABLE` is a hand-transcription pinned
    beside the module's own, so this guards `CLASS_BEHAVIOR` against being
    edited in isolation -- it does NOT detect drift in the other direction.
    Nothing here reads `prd.md`, and nothing can: the PRD is a planning
    artifact outside the wheel, so a unit test that parsed it would fail on
    any installed-package run. If the PRD's classification-rule table is
    ever amended, BOTH literals must be updated by hand and no test will
    say so."""
    behavior = CLASS_BEHAVIOR[artifact_class]
    definition, update_behavior, hand_edit_behavior = _PRD_TABLE[artifact_class]
    assert behavior.definition == definition
    assert behavior.update_behavior == update_behavior
    assert behavior.hand_edit_behavior == hand_edit_behavior


def test_artifact_rejects_a_behavior_that_does_not_match_the_entrys_own_class():
    """`Artifact` is documented as pairing an entry with ITS OWN class's
    behavior (see `describe()`'s docstring), but as a plain frozen dataclass
    nothing stopped direct construction with a mismatched pair -- the same
    hazard `Manifest`/`ManifestEntry` were hardened against in Story 7.4
    review (validate in `__post_init__`, not only in the factory)."""
    entry = _ENTRY_BY_CLASS[ArtifactClass.REFERENCED]
    wrong_behavior = CLASS_BEHAVIOR[ArtifactClass.HYBRID_MANAGED_REGION]
    with pytest.raises(ValueError, match=r"bmad-loop: behavior is hybrid-managed-region's, not referenced's"):
        Artifact(entry=entry, behavior=wrong_behavior)


def test_artifact_rejects_a_none_behavior_for_an_unclassified_deferred_entry():
    """The mismatch guard above compared `self.behavior` against
    `CLASS_BEHAVIOR.get(...)`, which returns `None` for
    `unclassified-deferred` -- so `None == None` short-circuited and an
    `Artifact` whose `behavior` is `None` constructed cleanly, exactly the
    mismatched pairing the guard exists to prevent. A future `explain` would
    then raise `AttributeError` on `.update_behavior`, one layer away from
    the validation."""
    entry = ManifestEntry(
        id="claude-skills",
        artifact_class=ArtifactClass.UNCLASSIFIED_DEFERRED,
        path=".claude/skills/**",
        applies_to=AppliesTo.BOTH,
        rationale="too repo-specific to classify confidently at V1",
    )
    with pytest.raises(ValueError, match=r"^claude-skills: behavior must be a ClassBehavior, got NoneType"):
        Artifact(entry=entry, behavior=None)  # type: ignore[arg-type]


def test_artifact_rejects_an_unclassified_deferred_entry_even_with_a_real_behavior():
    """Passing the type check is not enough: `unclassified-deferred` has no
    class contract at all, so no `ClassBehavior` is the right one for it."""
    entry = ManifestEntry(
        id="pixi-toml-tasks",
        artifact_class=ArtifactClass.UNCLASSIFIED_DEFERRED,
        path="pixi.toml",
        applies_to=AppliesTo.BOTH,
        rationale="task blocks are model-adjacent but too repo-specific at V1",
    )
    with pytest.raises(
        ValueError,
        match=r"^pixi-toml-tasks: class 'unclassified-deferred' has no ClassBehavior",
    ):
        Artifact(entry=entry, behavior=CLASS_BEHAVIOR[ArtifactClass.REFERENCED])


@pytest.mark.parametrize("bad_entry", [None, "agents-md", 7])
def test_artifact_rejects_a_non_manifest_entry_with_value_error(bad_entry):
    """`Manifest.__post_init__` isinstance-checks its own members and raises
    `ValueError`; `Artifact` held one and checked nothing, so a wrong type
    surfaced as `AttributeError` from the class lookup -- uncatchable by a
    caller following this package's documented `ValueError` convention."""
    with pytest.raises(ValueError, match=r"^entry must be a ManifestEntry, got "):
        Artifact(entry=bad_entry, behavior=CLASS_BEHAVIOR[ArtifactClass.REFERENCED])  # type: ignore[arg-type]


def test_class_behavior_table_is_read_only():
    """Every other value in `artifact.py` is a frozen dataclass, but the
    table that decides all of them was a plain mutable dict -- and because
    `Artifact.__post_init__` validates against the SAME table, a rebound
    entry would corrupt `describe()` and still pass its own guard, leaving
    the corruption undetectable from inside the module."""
    with pytest.raises(TypeError):
        CLASS_BEHAVIOR[ArtifactClass.COPIED_SEEDED] = CLASS_BEHAVIOR[  # type: ignore[index]
            ArtifactClass.REFERENCED
        ]


def test_no_mutable_module_level_alias_backs_the_read_only_table():
    """A `MappingProxyType` is a read-only VIEW, not a copy: while the table
    was also bound to a module-level `_CLASS_BEHAVIOR`, `import
    _CLASS_BEHAVIOR; _CLASS_BEHAVIOR[cls] = other` was fully visible through
    `CLASS_BEHAVIOR` -- so the test above passed while the exact corruption
    its own docstring describes stayed reachable. The literal is now built
    inline; nothing else in the module may bind it."""
    module = importlib.import_module("pyforge.marshal.seed.model.artifact")
    mutable_aliases = [
        name for name, value in vars(module).items() if isinstance(value, dict) and set(value) <= set(ArtifactClass)
    ]
    assert mutable_aliases == [], (
        f"the class-behavior table must not be reachable under a mutable name: {mutable_aliases}"
    )
