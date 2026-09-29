"""Conformance tests for the REAL packaged manifest (Story 7.5) -- loads
``pyforge/marshal/seed/templates/manifest.yaml`` through
``importlib.resources`` (the same pattern ``pyforge-warden`` uses for its own
packaged data) and ``load_manifest`` (Story 7.4), then asserts the spec's
I/O & Edge-Case Matrix: zero load errors, the exact per-class entry counts,
the exact ``never_write`` pattern list, the two deliberate dedups
(``.gitignore``, ``CLAUDE.md``) each appearing exactly once, every hybrid
region's body file existing and non-empty, every ``unclassified-deferred``
rationale being real prose rather than a placeholder, and (Story 9.5) that
the packaged manifest passes ``coverage_findings`` with zero findings --
the CI gate that fails the moment a future manifest edit drops coverage.

This file tests DATA, not the loader (``test_seed_model_manifest.py`` already
covers every ``load_manifest`` schema rule with synthetic fixtures) -- so
every assertion here is anchored to the spec's own named numbers, not to
"it loaded, so it must be fine."
"""

from __future__ import annotations

from collections import Counter
from importlib import resources

import pytest

from pyforge.marshal.seed.derive.adapters import ADAPTER_COMPOSITION
from pyforge.marshal.seed.detect.inventory import coverage_counts, coverage_findings
from pyforge.marshal.seed.model.manifest import AppliesTo, ArtifactClass, load_manifest

# The spec's Boundaries section, as corrected by review: 16 referenced,
# 5 copied-managed, 5 copied-seeded, 9 generated-derived (review moved
# `.bmad-loop/policy.toml` here from copied-seeded -- it is rendered whole
# on every `marshal config --write-harness-policy` run, Story 1.10/AD-12/
# AD-35, not a repo-owned seed; Story 11.2 later moves `projects-index` OUT
# to hybrid-managed-region -- see below), 5 hybrid-managed-region,
# 3 unclassified-deferred -- 43 entries total.
EXPECTED_CLASS_COUNTS = {
    ArtifactClass.REFERENCED: 16,
    ArtifactClass.COPIED_MANAGED: 5,
    ArtifactClass.COPIED_SEEDED: 5,
    ArtifactClass.GENERATED_DERIVED: 9,
    ArtifactClass.HYBRID_MANAGED_REGION: 5,
    ArtifactClass.UNCLASSIFIED_DEFERRED: 3,
}

# `coverage_counts` (S-9.5) is keyed by wire value (`ArtifactClass.value`,
# e.g. `"copied-managed"`), not the enum member itself -- derived from
# `EXPECTED_CLASS_COUNTS` above rather than a second hand-typed pin, so the
# two numbers cannot drift apart.
EXPECTED_COVERAGE_COUNTS = {artifact_class.value: count for artifact_class, count in EXPECTED_CLASS_COUNTS.items()}

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
    ("projects-index", "projects-table", ("## Projects",)),
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

# Story 11.2: `projects-table` (projects-index's only region) is
# REPO-COMPUTED (`derive.projects_index.derive_projects_table`), never a
# packaged-static `files/<name>.*.j2` fragment -- there is no fragment to
# ship for it (its content depends on the ADOPTING repo's own live project
# set, not shipped prose), so it is deliberately exempt from both
# region-body-file conformance checks below, the same way Story 11.1
# exempted its three wrapper-template filenames from the sibling "every
# `.j2` file is claimed" check.
_REPO_COMPUTED_REGIONS = frozenset({"projects-table"})


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


def test_packaged_manifest_passes_coverage_findings_with_zero_findings(manifest):
    """S-9.5's own CI gate (the AC this test exists for): ``coverage_findings``
    re-verifies every entry's ``artifact_class``/``rationale`` independently
    of ``load_manifest``'s own validation, so a future manifest edit that
    drops coverage -- an unrecognized ``class``, or an
    ``unclassified-deferred`` entry with a blank ``rationale`` -- fails this
    test, not only a human review of the diff."""
    assert coverage_findings(manifest) == ()


def test_packaged_manifest_coverage_counts_match_the_class_counts(manifest):
    actual = coverage_counts(manifest)
    assert actual == EXPECTED_COVERAGE_COUNTS
    assert sum(actual.values()) == len(manifest.entries) == 43


def test_packaged_manifest_never_write_matches_the_7_pattern_list_exactly(manifest):
    assert manifest.never_write == EXPECTED_NEVER_WRITE


def test_no_two_materialized_entries_share_a_rendered_path(manifest):
    """Proves the two deliberate dedups hold: `.gitignore` and `CLAUDE.md`
    each appear as exactly one manifest row, not one per class the PRD's
    prose happened to mention them under."""
    rendered_paths = [entry.path for entry in manifest.entries if entry.artifact_class is not ArtifactClass.REFERENCED]
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
        if entry.path == _UNRENDERED_PATH and entry.artifact_class is not ArtifactClass.REFERENCED
    ]
    assert offenders == [], f"only referenced entries may use the {_UNRENDERED_PATH!r} sentinel path: {offenders}"


@pytest.mark.parametrize("path", [".gitignore", "CLAUDE.md"])
def test_dedup_target_appears_exactly_once(manifest, path):
    matches = [entry.id for entry in manifest.entries if entry.path == path]
    assert len(matches) == 1, f"{path} should appear exactly once, got entries: {matches}"


def test_claude_md_is_hybrid_not_also_generated_derived(manifest):
    """The PRD does not settle this one: its GENERATED-DERIVED table names
    CLAUDE.md, and the summary sentence under that table counts 'the four
    agent-adapter files' before naming only three ('all three inspected:
    GEMINI.md, .cursor/rules/specs.mdc, .github/copilot-instructions.md').
    AD-63 is the dispositive source -- '`CLAUDE.md` and `AGENTS.md` receive
    it as a managed region (FR-117); Cursor, Gemini, and Copilot files are
    whole-file generated-derived' -- so CLAUDE.md is HYBRID only."""
    (entry,) = [entry for entry in manifest.entries if entry.path == "CLAUDE.md"]
    assert entry.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION


def test_gitignore_is_hybrid_not_also_copied_managed(manifest):
    (entry,) = [entry for entry in manifest.entries if entry.path == ".gitignore"]
    assert entry.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION


def test_every_hybrid_region_has_a_matching_non_empty_body_file(manifest):
    """Region-body convention (this story, new): one file per region NAME
    at `seed/templates/files/<name>.md.j2` (`.gitignore.j2` for
    `model-ignores`). A test failure here names the missing file, matching
    the I/O matrix's own error-handling column.

    Story 11.2's `projects-table` region is deliberately EXEMPT
    (`_REPO_COMPUTED_REGIONS`): its body is repo-computed
    (`derive.projects_index.derive_projects_table`), never a packaged
    static fragment, so there is no `files/projects-table.*.j2` to ship or
    to check for here -- a static one would be exactly the defect a prior
    implementation attempt at this story shipped and a review pass caught
    (see `verbs/adopt.py`'s own module docstring)."""
    files_root = resources.files("pyforge.marshal.seed.templates") / "files"
    hybrid_entries = [
        entry for entry in manifest.entries if entry.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION
    ]
    assert hybrid_entries, "expected at least one hybrid-managed-region entry"

    for entry in hybrid_entries:
        for region in entry.regions:
            if region.name in _REPO_COMPUTED_REGIONS:
                continue
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
                f"{entry.id}: region {region.name!r} matches more than one body file candidate: {existing}"
            )
            body_text = existing[0].read_text(encoding="utf-8")
            assert body_text.strip(), f"{entry.id}: region {region.name!r} body file is empty"


def test_every_body_file_is_claimed_by_a_declared_region(manifest):
    """The reverse direction of the check above. `templates/files/` ships in
    the wheel, and the region-name -> body-file mapping is a naming
    convention with no schema field behind it (Design Notes), so the tests
    are its only specification. One-directional coverage lets a renamed or
    removed region leave an orphaned `.j2` shipping to every adopting repo
    with a fully green suite.

    Story 11.1 added a SECOND, disjoint category of `.j2` file under this
    same directory: whole-file agent-adapter WRAPPER templates
    (`derive.adapters.ADAPTER_COMPOSITION`'s own `wrapper` filenames) --
    never a region body, never spliced verbatim into a managed region, read
    by `derive.adapters.render_adapter` instead and covered by their own
    dedicated suite (`test_seed_derive_adapters.py`). Excluded here by exact
    filename so this test's "every `.j2` file must be a claimed region body"
    claim stays precise about which files it is actually claiming that for.

    Story 11.2 excludes `projects-table` from `declared_names` on the SAME
    principle, mirrored on the opposite side of the mapping: it is a real,
    declared hybrid region with no `files/*.j2` counterpart AT ALL (by
    design -- see the sibling check above), so counting it here would make
    this test fail for having correctly shipped no orphaned file.
    """
    files_root = resources.files("pyforge.marshal.seed.templates") / "files"
    declared_names = {
        region.name
        for entry in manifest.entries
        if entry.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION
        for region in entry.regions
        if region.name not in _REPO_COMPUTED_REGIONS
    }
    wrapper_filenames = {spec.wrapper for spec in ADAPTER_COMPOSITION.values()}
    shipped_names = {
        # `<region-name>.md.j2` / `<region-name>.gitignore.j2` -- strip the
        # `.j2` and whatever host-file suffix precedes it.
        path.name.split(".", 1)[0]
        for path in files_root.iterdir()
        if path.is_file() and path.name.endswith(".j2") and path.name not in wrapper_filenames
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
    init_only = {entry.id for entry in manifest.entries if entry.applies_to is AppliesTo.INIT}
    adopt_only = {entry.id for entry in manifest.entries if entry.applies_to is AppliesTo.ADOPT}
    assert init_only == EXPECTED_INIT_ONLY_ENTRY_IDS
    assert adopt_only == EXPECTED_ADOPT_ONLY_ENTRY_IDS


def test_unclassified_deferred_entries_have_real_non_generic_rationale(manifest):
    """S-9.5's future coverage check treats a bare deferral as uncovered, so
    every `unclassified-deferred` entry's `rationale` must be real prose,
    not a placeholder -- `manifest.py` already enforces non-blank, but not
    "not a stub"."""
    placeholders = {"todo", "tbd", "n/a", "unknown", "-"}
    deferred_entries = [
        entry for entry in manifest.entries if entry.artifact_class is ArtifactClass.UNCLASSIFIED_DEFERRED
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
    referenced_entries = [entry for entry in manifest.entries if entry.artifact_class is ArtifactClass.REFERENCED]
    assert len(referenced_entries) == EXPECTED_CLASS_COUNTS[ArtifactClass.REFERENCED]
    for entry in referenced_entries:
        assert entry.path == _UNRENDERED_PATH
        assert entry.pin, f"{entry.id}: referenced entry must carry a non-empty pin"


def test_referenced_pins_match_the_live_environment_exactly(manifest):
    """The pin IS the payload of a referenced entry -- it is the whole of
    what FR-95's floor check reads -- yet a non-emptiness assertion was its
    only guard, while every other number in this file is pinned exactly
    (class counts, `never_write`, anchors, `applies_to` sets).

    That gap already cost one high-severity defect: `bmad-loop` shipped
    `>=0.8.1` while `pixi.toml` declared `>=0.9.0` and `pyforge-marshal`'s
    own `pyproject.toml` requires `bmad-loop>=0.9.0,<0.10` -- i.e. the
    manifest certified an environment in which the tool performing the check
    cannot install. The whole suite was green. A silent revert would be
    green again.

    These values are the live `pixi.toml` constraints (the Boundaries' rule
    where `pixi.toml` and the PRD disagree). Changing one here is fine --
    changing it *only* here, or *only* in the manifest, is what this
    catches.
    """
    expected = {
        "bmad-method": ">=6.11.0",
        "bmad-loop": ">=0.11.0",
        "copier": ">=9.17,<10",
        "tmux": ">=3.7b_",
        "bmad-installed-skills": ">=6.11.0",
        "pixi": ">=0.76.1",
        "bmad-builder": ">=2.2.1",
        "bmad-method-test-architecture-enterprise": ">=1.23.2",
        "bmad-creative-intelligence-suite": ">=0.3.1",
        "bmad-skill-forge": ">=6.11.0",
        "bmad-dashboard": ">=1.2.2.dev0",
        "bmad-manticore": ">=3.1.0.dev0",
        "bmad-labs-skills": ">=1.0.0.dev0",
        "bmad-utility-skills": ">=2.0.0",
        "bmad-method-wds-expansion": ">=0.4.3",
        "bmad-module-template": ">=0.1.0",
    }
    actual = {entry.id: entry.pin for entry in manifest.entries if entry.artifact_class is ArtifactClass.REFERENCED}
    assert actual == expected
