"""Conformance tests for the REAL packaged manifest (Story 7.5) -- loads
``pyforge/marshal/seed/templates/manifest.yaml`` through
``importlib.resources`` (the same pattern ``pyforge-warden`` uses for its own
packaged data) and ``load_manifest`` (Story 7.4), then asserts the spec's
I/O & Edge-Case Matrix: zero load errors, the exact per-class entry counts,
the exact ``never_write`` pattern list, the two deliberate dedups
(``.gitignore``, ``CLAUDE.md``) each appearing exactly once, every hybrid
region's body file existing and non-empty, and every ``unclassified-deferred``
rationale being real prose rather than a placeholder.

This file tests DATA, not the loader (``test_seed_model_manifest.py`` already
covers every ``load_manifest`` schema rule with synthetic fixtures) -- so
every assertion here is anchored to the spec's own named numbers, not to
"it loaded, so it must be fine."
"""

from __future__ import annotations

from collections import Counter
from importlib import resources

import pytest
from pyforge.marshal.seed.model.manifest import AppliesTo, ArtifactClass, load_manifest

# The spec's Boundaries section, as corrected by review: 16 referenced,
# 5 copied-managed, 5 copied-seeded, 10 generated-derived (review moved
# `.bmad-loop/policy.toml` here from copied-seeded -- it is rendered whole
# on every `marshal config --write-harness-policy` run, Story 1.10/AD-12/
# AD-35, not a repo-owned seed), 4 hybrid-managed-region,
# 3 unclassified-deferred -- 43 entries total.
EXPECTED_CLASS_COUNTS = {
    ArtifactClass.REFERENCED: 16,
    ArtifactClass.COPIED_MANAGED: 5,
    ArtifactClass.COPIED_SEEDED: 5,
    ArtifactClass.GENERATED_DERIVED: 10,
    ArtifactClass.HYBRID_MANAGED_REGION: 4,
    ArtifactClass.UNCLASSIFIED_DEFERRED: 3,
}

# The spec's Always bullet: exactly 7 never-write patterns.
EXPECTED_NEVER_WRITE = (
    "docs/dreams/*.md",
    "**/planning-artifacts/**",
    "**/implementation-artifacts/**",
    "docs/specs/*.md",
    "_bmad/bmm/**",
    "_bmad/core/**",
    "_bmad/skf/**",
)

# REFERENCED entries are not materialized, so every one of them shares the
# sentinel path "n/a" (Story 7.4's own fixture convention) -- the AC's "no
# two entries share a rendered path" is about MATERIALIZED artifacts, so
# this sentinel is excluded from the duplicate-path check below rather than
# failing it 16 times over. The exclusion is keyed on the CLASS, not on the
# string: keying it on the string let a materialized entry authored with
# `path: "n/a"` escape every path assertion in this module and reach the
# write guard as a literal relative path named `n/a`.
_UNRENDERED_PATH = "n/a"

# The spec's Boundaries name each hybrid entry's regions AND their exact
# anchors. AD-56 makes a wrong anchor silently non-fatal -- "insertion goes
# after the first match; if none matches, the region is appended at end of
# file" -- and `Region.__post_init__` validates only non-blankness, so a
# typo'd or stale anchor relocates a managed region to EOF with nothing
# failing. Pinned exactly, per (entry id, region name, anchor).
EXPECTED_REGION_ANCHORS = {
    ("agents-md", "tiers", ("## The tiers",)),
    ("agents-md", "portability-contract", ("## Portability contract",)),
    ("agents-md", "dream-first-workflow", ("## Dream-first workflow",)),
    ("claude-md", "tiers", ("### Spec-driven, framework-neutral layout",)),
    ("claude-md", "bmad-multiproject", ("### Multi-Project Pattern",)),
    ("gitignore", "model-ignores", ("<top>",)),
    ("readme-badge", "model-badge", ("<top>",)),
}

# `applies_to: init` is load-bearing, not incidental: the never-write
# exemption this story deliberately left unencoded (Design Notes) uses it as
# its only discriminator -- a future fs-guard/orchestrator story computes an
# effective NeverWrite set by excluding exactly the copied-seeded+init
# entries whose own paths sit inside a never-write glob. Flipping either to
# `both` silently removes that signal, so the sets are pinned by id.
EXPECTED_INIT_ONLY_ENTRY_IDS = {"starter-dream", "specs-readme"}
EXPECTED_ADOPT_ONLY_ENTRY_IDS = {"specs-dir-legacy"}


@pytest.fixture(scope="module")
def manifest():
    manifest_ref = resources.files("pyforge.marshal.seed.templates") / "manifest.yaml"
    with resources.as_file(manifest_ref) as manifest_path:
        return load_manifest(manifest_path)


def test_packaged_manifest_loads_with_model_version_1_0_0(manifest):
    assert str(manifest.model_version) == "1.0.0"


def test_packaged_manifest_class_counts_match_the_spec_exactly(manifest):
    actual_counts = Counter(entry.artifact_class for entry in manifest.entries)
    assert actual_counts == EXPECTED_CLASS_COUNTS
    assert len(manifest.entries) == sum(EXPECTED_CLASS_COUNTS.values()) == 43


def test_packaged_manifest_never_write_matches_the_7_pattern_list_exactly(manifest):
    assert manifest.never_write == EXPECTED_NEVER_WRITE


def test_no_two_materialized_entries_share_a_rendered_path(manifest):
    """Proves the two deliberate dedups hold: `.gitignore` and `CLAUDE.md`
    each appear as exactly one manifest row, not one per class the PRD's
    prose happened to mention them under."""
    rendered_paths = [
        entry.path
        for entry in manifest.entries
        if entry.artifact_class is not ArtifactClass.REFERENCED
    ]
    duplicates = sorted(path for path, count in Counter(rendered_paths).items() if count > 1)
    assert duplicates == [], f"paths claimed by more than one entry: {duplicates}"


def test_only_referenced_entries_use_the_unrendered_path_sentinel(manifest):
    """Closes the converse of `test_referenced_entries_all_use_the_unrendered
    _path_sentinel`. The duplicate-path check above excludes REFERENCED
    entries by class; if a MATERIALIZED entry were authored with
    `path: "n/a"`, it would clear `_require_text`, sit outside the referenced-
    only assertion, and reach the write guard as a literal relative path
    named `n/a`."""
    offenders = [
        entry.id
        for entry in manifest.entries
        if entry.path == _UNRENDERED_PATH
        and entry.artifact_class is not ArtifactClass.REFERENCED
    ]
    assert offenders == [], (
        f"only referenced entries may use the {_UNRENDERED_PATH!r} sentinel path: {offenders}"
    )


@pytest.mark.parametrize("path", [".gitignore", "CLAUDE.md"])
def test_dedup_target_appears_exactly_once(manifest, path):
    matches = [entry.id for entry in manifest.entries if entry.path == path]
    assert len(matches) == 1, f"{path} should appear exactly once, got entries: {matches}"


def test_claude_md_is_hybrid_not_also_generated_derived(manifest):
    """The PRD's GENERATED-DERIVED table names CLAUDE.md, but its own
    summary sentence ('all three inspected: GEMINI.md, .cursor/rules/specs.mdc,
    .github/copilot-instructions.md') deliberately excludes it -- CLAUDE.md
    is HYBRID only."""
    (entry,) = [entry for entry in manifest.entries if entry.path == "CLAUDE.md"]
    assert entry.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION


def test_gitignore_is_hybrid_not_also_copied_managed(manifest):
    (entry,) = [entry for entry in manifest.entries if entry.path == ".gitignore"]
    assert entry.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION


def test_every_hybrid_region_has_a_matching_non_empty_body_file(manifest):
    """Region-body convention (this story, new): one file per region NAME
    at `seed/templates/files/<name>.md.j2` (`.gitignore.j2` for
    `model-ignores`). A test failure here names the missing file, matching
    the I/O matrix's own error-handling column."""
    files_root = resources.files("pyforge.marshal.seed.templates") / "files"
    hybrid_entries = [
        entry
        for entry in manifest.entries
        if entry.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION
    ]
    assert hybrid_entries, "expected at least one hybrid-managed-region entry"

    for entry in hybrid_entries:
        for region in entry.regions:
            candidates = [
                files_root / f"{region.name}.md.j2",
                files_root / f"{region.name}.gitignore.j2",
            ]
            existing = [candidate for candidate in candidates if candidate.is_file()]
            assert existing, (
                f"{entry.id}: region {region.name!r} has no body file at "
                f"seed/templates/files/{region.name}.md.j2 (or .gitignore.j2)"
            )
            assert len(existing) == 1, (
                f"{entry.id}: region {region.name!r} matches more than one body "
                f"file candidate: {existing}"
            )
            body_text = existing[0].read_text(encoding="utf-8")
            assert body_text.strip(), f"{entry.id}: region {region.name!r} body file is empty"


def test_every_body_file_is_claimed_by_a_declared_region(manifest):
    """The reverse direction of the check above. `templates/files/` ships in
    the wheel, and the region-name -> body-file mapping is a naming
    convention with no schema field behind it (Design Notes), so the tests
    are its only specification. One-directional coverage lets a renamed or
    removed region leave an orphaned `.j2` shipping to every adopting repo
    with a fully green suite."""
    files_root = resources.files("pyforge.marshal.seed.templates") / "files"
    declared_names = {
        region.name
        for entry in manifest.entries
        if entry.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION
        for region in entry.regions
    }
    shipped_names = {
        # `<region-name>.md.j2` / `<region-name>.gitignore.j2` -- strip the
        # `.j2` and whatever host-file suffix precedes it.
        path.name.split(".", 1)[0]
        for path in files_root.iterdir()
        if path.is_file() and path.name.endswith(".j2")
    }
    assert shipped_names == declared_names, (
        f"orphaned body files: {sorted(shipped_names - declared_names)}; "
        f"regions with no body file: {sorted(declared_names - shipped_names)}"
    )


def test_every_hybrid_region_declares_its_exact_anchor(manifest):
    """AD-56: a region whose anchor matches nothing is appended at end of
    file rather than erroring, and `Region.__post_init__` validates only
    non-blankness -- so a typo'd or stale anchor silently relocates a managed
    span. The spec's Boundaries name each anchor exactly; pin them."""
    actual = {
        (entry.id, region.name, region.anchor)
        for entry in manifest.entries
        if entry.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION
        for region in entry.regions
    }
    assert actual == EXPECTED_REGION_ANCHORS


def test_applies_to_scoping_matches_the_spec(manifest):
    """`applies_to: init` is the discriminator the deferred never-write
    exemption depends on (Design Notes) -- nothing else in the schema marks
    which entries are exempt from the never-write globs their own paths sit
    inside. Pin the non-`both` sets so a flip cannot pass silently."""
    init_only = {
        entry.id for entry in manifest.entries if entry.applies_to is AppliesTo.INIT
    }
    adopt_only = {
        entry.id for entry in manifest.entries if entry.applies_to is AppliesTo.ADOPT
    }
    assert init_only == EXPECTED_INIT_ONLY_ENTRY_IDS
    assert adopt_only == EXPECTED_ADOPT_ONLY_ENTRY_IDS


def test_unclassified_deferred_entries_have_real_non_generic_rationale(manifest):
    """S-9.5's future coverage check treats a bare deferral as uncovered, so
    every `unclassified-deferred` entry's `rationale` must be real prose,
    not a placeholder -- `manifest.py` already enforces non-blank, but not
    "not a stub"."""
    placeholders = {"todo", "tbd", "n/a", "unknown", "-"}
    deferred_entries = [
        entry
        for entry in manifest.entries
        if entry.artifact_class is ArtifactClass.UNCLASSIFIED_DEFERRED
    ]
    assert len(deferred_entries) == EXPECTED_CLASS_COUNTS[ArtifactClass.UNCLASSIFIED_DEFERRED]
    for entry in deferred_entries:
        rationale = entry.rationale.strip()
        assert rationale.lower() not in placeholders, f"{entry.id}: placeholder rationale"
        assert len(rationale) >= 20, f"{entry.id}: rationale too short to be real prose: {rationale!r}"


def test_no_entry_anywhere_has_a_placeholder_rationale(manifest):
    """The prior pass only checked the 3 `unclassified-deferred` entries --
    `rationale` is a required, non-blank field on all 43 (`manifest.py`
    enforces that), but nothing enforced that a non-blank value is not
    itself a stub (e.g. a copy-pasted "TODO"). Every entry, not just the
    deferred three, must clear the same bar."""
    placeholders = {"todo", "tbd", "n/a", "unknown", "-"}
    for entry in manifest.entries:
        rationale = entry.rationale.strip()
        assert rationale.lower() not in placeholders, f"{entry.id}: placeholder rationale"


def test_no_entry_uses_legacy_of(manifest):
    """The spec's own Never bullet: no entry in this V1 manifest needs
    `legacy_of` yet (AD-59's mechanism stays unexercised)."""
    legacy_entries = [entry.id for entry in manifest.entries if entry.legacy_of is not None]
    assert legacy_entries == []


def test_referenced_entries_all_use_the_unrendered_path_sentinel(manifest):
    referenced_entries = [
        entry for entry in manifest.entries if entry.artifact_class is ArtifactClass.REFERENCED
    ]
    assert len(referenced_entries) == EXPECTED_CLASS_COUNTS[ArtifactClass.REFERENCED]
    for entry in referenced_entries:
        assert entry.path == _UNRENDERED_PATH
        assert entry.pin, f"{entry.id}: referenced entry must carry a non-empty pin"
