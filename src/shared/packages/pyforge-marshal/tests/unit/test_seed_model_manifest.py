"""Unit tests for ``pyforge.marshal.seed.model.manifest`` (Story 7.4) --
covers the spec's I/O & Edge-Case Matrix for ``load_manifest``: the six
``ArtifactClass`` members, every ``ManifestError`` scenario (naming the
offending id/field), and the ``since``/``until`` version-range filter.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from textwrap import dedent

import pytest
import yaml

from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    Manifest,
    ManifestEntry,
    ManifestError,
    Region,
    load_manifest,
)
from pyforge.marshal.seed.model.version import ModelVersion


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "manifest.yaml"
    path.write_text(dedent(text), encoding="utf-8")
    return path


_VALID_ALL_CLASSES = """\
    model_version: "1.0.0"
    never_write:
      - "docs/dreams/*.md"
    artifacts:
      - id: bmad-loop
        class: referenced
        path: "n/a"
        applies_to: both
        rationale: upstream product, never vendored
        pin: ">=0.9.0,<0.10"
      - id: bmad-switch
        class: copied-managed
        path: "scripts/bmad-switch"
        applies_to: init
        rationale: tool-owned model machinery
      - id: starter-dream
        class: copied-seeded
        path: "docs/dreams/{{ slug }}.md"
        applies_to: init
        rationale: repo-owned from the moment it is written
      - id: claude-md
        class: generated-derived
        path: "CLAUDE.md"
        applies_to: both
        rationale: computed from the neutral contract
      - id: agents-md
        class: hybrid-managed-region
        path: "AGENTS.md"
        applies_to: both
        rationale: neutral contract must upgrade, rest is repo-owned
        format: html
        regions:
          - name: tiers
            anchor: ["## The tiers", "<top>"]
      - id: skills-content
        class: unclassified-deferred
        path: ".claude/skills/**"
        applies_to: adopt
        rationale: model-adjacent but too repo-specific to classify at V1
"""


def test_valid_manifest_one_entry_per_class_returns_typed_manifest(tmp_path):
    manifest = load_manifest(_write(tmp_path, _VALID_ALL_CLASSES))

    assert isinstance(manifest, Manifest)
    assert manifest.model_version == ModelVersion.parse("1.0.0")
    assert manifest.never_write == ("docs/dreams/*.md",)
    assert len(manifest.entries) == 6

    by_id = {entry.id: entry for entry in manifest.entries}
    assert by_id["bmad-loop"].artifact_class is ArtifactClass.REFERENCED
    assert by_id["bmad-loop"].pin == ">=0.9.0,<0.10"
    assert by_id["bmad-switch"].artifact_class is ArtifactClass.COPIED_MANAGED
    assert by_id["starter-dream"].artifact_class is ArtifactClass.COPIED_SEEDED
    assert by_id["claude-md"].artifact_class is ArtifactClass.GENERATED_DERIVED
    assert by_id["agents-md"].artifact_class is ArtifactClass.HYBRID_MANAGED_REGION
    assert by_id["agents-md"].format == "html"
    assert by_id["agents-md"].regions == (Region(name="tiers", anchor=("## The tiers", "<top>")),)
    assert by_id["skills-content"].artifact_class is ArtifactClass.UNCLASSIFIED_DEFERRED

    for entry in manifest.entries:
        assert isinstance(entry, ManifestEntry)
        assert entry.applies_to in AppliesTo
        assert entry.rationale


def test_applies_to_every_member_accepted(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: a
            class: copied-seeded
            path: "x"
            applies_to: init
            rationale: r
          - id: b
            class: copied-seeded
            path: "x"
            applies_to: adopt
            rationale: r
          - id: c
            class: copied-seeded
            path: "x"
            applies_to: both
            rationale: r
    """
    manifest = load_manifest(_write(tmp_path, text))
    by_id = {entry.id: entry for entry in manifest.entries}
    assert by_id["a"].applies_to is AppliesTo.INIT
    assert by_id["b"].applies_to is AppliesTo.ADOPT
    assert by_id["c"].applies_to is AppliesTo.BOTH


# --- ManifestError scenarios -------------------------------------------------


def test_duplicate_id_raises_manifest_error_naming_it(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: copied-seeded
            path: "x"
            applies_to: init
            rationale: r
          - id: foo
            class: copied-seeded
            path: "y"
            applies_to: init
            rationale: r2
    """
    with pytest.raises(ManifestError, match=r"^foo: duplicate id"):
        load_manifest(_write(tmp_path, text))


def test_unrecognized_class_raises_manifest_error(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: bogus-class
            path: "x"
            applies_to: init
            rationale: r
    """
    with pytest.raises(ManifestError, match=r"^foo: .*not a valid ArtifactClass"):
        load_manifest(_write(tmp_path, text))


def test_hybrid_missing_regions_raises_manifest_error(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: hybrid-managed-region
            path: "x"
            applies_to: init
            rationale: r
            format: html
    """
    with pytest.raises(ManifestError, match=r"^foo: .*require at least one region"):
        load_manifest(_write(tmp_path, text))


def test_hybrid_empty_regions_list_raises_manifest_error(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: hybrid-managed-region
            path: "x"
            applies_to: init
            rationale: r
            format: html
            regions: []
    """
    with pytest.raises(ManifestError, match=r"^foo: .*require at least one region"):
        load_manifest(_write(tmp_path, text))


def test_hybrid_missing_format_raises_manifest_error(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: hybrid-managed-region
            path: "x"
            applies_to: init
            rationale: r
            regions:
              - name: tiers
                anchor: ["## Tiers"]
    """
    with pytest.raises(ManifestError, match=r"^foo: .*require a non-empty format"):
        load_manifest(_write(tmp_path, text))


def test_referenced_missing_pin_raises_manifest_error(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: referenced
            path: "n/a"
            applies_to: both
            rationale: r
    """
    with pytest.raises(ManifestError, match=r"^foo: .*require a non-empty pin"):
        load_manifest(_write(tmp_path, text))


@pytest.mark.parametrize(
    ("missing_field", "expected_message"),
    [
        # Anchored on the REASON, not merely on "something failed": a bare
        # `pytest.raises(ManifestError)` passes for any load failure at
        # all, so a regression that changes WHICH rule fires stays green.
        ("id", r"^artifacts\[0\]: id must be a non-empty, non-blank str, got None"),
        ("class", r"^foo: None is not a valid ArtifactClass"),
        ("path", r"^foo: path must be a non-empty, non-blank str, got None"),
        ("applies_to", r"^foo: None is not a valid AppliesTo"),
        ("rationale", r"^foo: rationale must be a non-empty, non-blank str, got None"),
    ],
)
def test_missing_required_field_raises_manifest_error(tmp_path, missing_field, expected_message):
    entry = {
        "id": "foo",
        "class": "copied-seeded",
        "path": "x",
        "applies_to": "init",
        "rationale": "r",
    }
    del entry[missing_field]
    document = {"model_version": "1.0.0", "artifacts": [entry]}
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    with pytest.raises(ManifestError, match=expected_message):
        load_manifest(path)


@pytest.mark.parametrize(
    ("bad_type_field", "expected_message"),
    [
        # Asserting the REASON, not merely that entry "foo" failed somehow:
        # a bare match on the id passes for any rule firing, so a
        # regression that swaps which check catches the value stays green.
        ("id", r"^artifacts\[0\]: id must be a non-empty, non-blank str"),
        ("class", r"^foo: .*not a valid ArtifactClass"),
        ("path", r"^foo: path must be a non-empty, non-blank str"),
        ("applies_to", r"^foo: .*not a valid AppliesTo"),
        ("rationale", r"^foo: rationale must be a non-empty, non-blank str"),
    ],
)
def test_wrong_type_required_field_raises_manifest_error(tmp_path, bad_type_field, expected_message):
    entry = {
        "id": "foo",
        "class": "copied-seeded",
        "path": "x",
        "applies_to": "init",
        "rationale": "r",
    }
    entry[bad_type_field] = 123  # an int where a str is required
    document = {"model_version": "1.0.0", "artifacts": [entry]}
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    with pytest.raises(ManifestError, match=expected_message):
        load_manifest(path)


def test_invalid_applies_to_raises_manifest_error(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: copied-seeded
            path: "x"
            applies_to: sometimes
            rationale: r
    """
    with pytest.raises(ManifestError, match=r"^foo: .*not a valid AppliesTo"):
        load_manifest(_write(tmp_path, text))


def test_malformed_since_raises_manifest_error(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: copied-seeded
            path: "x"
            applies_to: init
            rationale: r
            since: "not-a-version"
    """
    with pytest.raises(ManifestError, match=r"^foo: since: .*not a valid SemVer"):
        load_manifest(_write(tmp_path, text))


def test_malformed_until_raises_manifest_error(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: copied-seeded
            path: "x"
            applies_to: init
            rationale: r
            until: "not-a-version"
    """
    with pytest.raises(ManifestError, match=r"^foo: until: .*not a valid SemVer"):
        load_manifest(_write(tmp_path, text))


def test_malformed_top_level_model_version_wraps_invalid_version_error(tmp_path):
    text = """\
        model_version: "not-a-version"
        artifacts: []
    """
    with pytest.raises(ManifestError, match=r"^manifest: model_version: .*not a valid SemVer") as excinfo:
        load_manifest(_write(tmp_path, text))
    assert excinfo.value.__cause__ is not None


def test_until_not_greater_than_since_raises_manifest_error(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: copied-seeded
            path: "x"
            applies_to: init
            rationale: r
            since: "1.0.0"
            until: "1.0.0"
    """
    with pytest.raises(ManifestError, match=r"^foo: until \(1\.0\.0\) must be strictly greater"):
        load_manifest(_write(tmp_path, text))


def test_until_less_than_since_raises_manifest_error(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: copied-seeded
            path: "x"
            applies_to: init
            rationale: r
            since: "2.0.0"
            until: "1.0.0"
    """
    with pytest.raises(ManifestError, match=r"^foo: until \(1\.0\.0\) must be strictly greater than since \(2\.0\.0\)"):
        load_manifest(_write(tmp_path, text))


def test_non_mapping_top_level_document_raises_manifest_error(tmp_path):
    text = "- just\n- a\n- list\n"
    with pytest.raises(ManifestError, match=r"^manifest: top-level document must be a mapping"):
        load_manifest(_write(tmp_path, text))


# --- since/until version-range filtering ------------------------------------


def test_entry_retired_exactly_at_until_is_excluded(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: retired
            class: copied-seeded
            path: "x"
            applies_to: init
            rationale: r
            until: "1.0.0"
    """
    manifest = load_manifest(_write(tmp_path, text))
    assert manifest.entries == ()


def test_entry_kept_when_since_at_or_before_model_version_and_no_until(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: kept
            class: copied-seeded
            path: "x"
            applies_to: init
            rationale: r
            since: "0.9.0"
    """
    manifest = load_manifest(_write(tmp_path, text))
    assert [entry.id for entry in manifest.entries] == ["kept"]


def test_entry_excluded_when_since_after_model_version(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: future
            class: copied-seeded
            path: "x"
            applies_to: init
            rationale: r
            since: "1.1.0"
    """
    manifest = load_manifest(_write(tmp_path, text))
    assert manifest.entries == ()


def test_entry_kept_when_until_strictly_after_model_version(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: still-here
            class: copied-seeded
            path: "x"
            applies_to: init
            rationale: r
            until: "1.0.1"
    """
    manifest = load_manifest(_write(tmp_path, text))
    assert [entry.id for entry in manifest.entries] == ["still-here"]


def test_mixed_range_filtering_across_several_entries(tmp_path):
    text = """\
        model_version: "1.5.0"
        artifacts:
          - id: always
            class: copied-seeded
            path: "x"
            applies_to: init
            rationale: r
          - id: retired
            class: copied-seeded
            path: "x"
            applies_to: init
            rationale: r
            until: "1.5.0"
          - id: not-yet
            class: copied-seeded
            path: "x"
            applies_to: init
            rationale: r
            since: "2.0.0"
          - id: in-window
            class: copied-seeded
            path: "x"
            applies_to: init
            rationale: r
            since: "1.0.0"
            until: "2.0.0"
    """
    manifest = load_manifest(_write(tmp_path, text))
    assert {entry.id for entry in manifest.entries} == {"always", "in-window"}


# --- defaults -----------------------------------------------------------------


def test_never_write_defaults_to_empty_tuple(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts: []
    """
    manifest = load_manifest(_write(tmp_path, text))
    assert manifest.never_write == ()


def test_artifacts_defaults_to_empty_tuple(tmp_path):
    text = 'model_version: "1.0.0"\n'
    manifest = load_manifest(_write(tmp_path, text))
    assert manifest.entries == ()


def test_legacy_of_is_captured_when_present(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: legacy-specs
            class: copied-managed
            path: "docs/specs"
            applies_to: adopt
            rationale: preserve + record, never migrate
            legacy_of: planning-artifacts
    """
    manifest = load_manifest(_write(tmp_path, text))
    assert manifest.entries[0].legacy_of == "planning-artifacts"


# --- Region / ManifestEntry direct construction (defense in depth) ---------


def test_region_rejects_empty_anchor():
    with pytest.raises(ValueError):
        Region(name="tiers", anchor=())


def test_region_rejects_empty_name():
    with pytest.raises(ValueError):
        Region(name="", anchor=("x",))


def test_manifest_entry_rejects_unrecognized_class_directly():
    with pytest.raises(ValueError):
        ManifestEntry(
            id="x",
            artifact_class="bogus",
            path="p",
            applies_to="init",
            rationale="r",
        )


def test_manifest_entry_regions_wrong_type_raises_value_error_not_type_error():
    """A non-list/tuple `regions` must raise the class's own documented
    `ValueError` contract, not leak a raw `TypeError` from an unguarded
    `tuple(...)` call (review finding: matches `Region.anchor`'s existing
    guarded pattern in the same file)."""
    with pytest.raises(ValueError):
        ManifestEntry(
            id="x",
            artifact_class="copied-seeded",
            path="p",
            applies_to="init",
            rationale="r",
            regions=5,
        )


def test_manifest_never_write_wrong_type_raises_value_error_not_type_error():
    with pytest.raises(ValueError):
        Manifest(model_version=ModelVersion.parse("1.0.0"), never_write=5, entries=())


def test_manifest_entries_wrong_type_raises_value_error_not_type_error():
    with pytest.raises(ValueError):
        Manifest(model_version=ModelVersion.parse("1.0.0"), never_write=(), entries=5)


# --- review-driven patches: `or []` masking, I/O wrapping, error locators --


def test_falsy_non_list_never_write_raises_manifest_error(tmp_path):
    """`never_write: 0` is falsy but present and wrong-typed -- the old
    `raw_document.get(...) or []` idiom silently treated it as absent
    instead of raising."""
    text = """\
        model_version: "1.0.0"
        never_write: 0
        artifacts: []
    """
    with pytest.raises(ManifestError, match=r"^manifest: never_write must be a list of non-blank str"):
        load_manifest(_write(tmp_path, text))


def test_falsy_non_list_artifacts_raises_manifest_error(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts: false
    """
    with pytest.raises(ManifestError, match=r"^manifest: artifacts must be a list$"):
        load_manifest(_write(tmp_path, text))


def test_falsy_non_list_regions_raises_manifest_error(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: copied-seeded
            path: "x"
            applies_to: init
            rationale: r
            regions: 0
    """
    with pytest.raises(ManifestError, match=r"^foo: regions must be a list, got 0$"):
        load_manifest(_write(tmp_path, text))


def test_non_mapping_artifacts_entry_raises_manifest_error(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - "just a string, not a mapping"
    """
    with pytest.raises(
        ManifestError,
        match=(
            r"^artifacts\[0\]: entry must be a mapping,"
            r" got 'just a string, not a mapping'$"
        ),
    ):
        load_manifest(_write(tmp_path, text))


def test_non_mapping_region_raises_manifest_error(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: hybrid-managed-region
            path: "x"
            applies_to: init
            rationale: r
            format: html
            regions:
              - "just a string, not a mapping"
    """
    with pytest.raises(ManifestError, match=r"^foo: regions\[0\]: region must be a mapping"):
        load_manifest(_write(tmp_path, text))


def test_missing_file_raises_manifest_error(tmp_path):
    with pytest.raises(ManifestError, match=r"^manifest: could not read .*does-not-exist\.yaml: "):
        load_manifest(tmp_path / "does-not-exist.yaml")


def test_malformed_yaml_raises_manifest_error(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text(": not: valid: yaml: [", encoding="utf-8")
    with pytest.raises(ManifestError, match=r"^manifest: invalid YAML in .*bad\.yaml: "):
        load_manifest(path)


def test_deeply_nested_yaml_raises_manifest_error(tmp_path):
    """PyYAML's composer recurses per nesting level, so a deeply nested
    document blew the stack with a raw RecursionError -- the same escape
    class as UnicodeDecodeError, on the very input (malformed YAML) the
    ManifestError-only contract names."""
    text = 'model_version: "1.0.0"\nartifacts: ' + "[" * 500 + "]" * 500 + "\n"
    with pytest.raises(ManifestError, match=r"^manifest: .* is nested too deeply to parse$"):
        load_manifest(_write(tmp_path, text))


def test_error_message_disambiguates_second_bad_entry_by_index(tmp_path):
    """Two entries both missing `id` must not collapse into the same
    indistinguishable message -- the second one's error names its index."""
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: good
            class: copied-seeded
            path: "x"
            applies_to: init
            rationale: r
          - class: copied-seeded
            path: "x"
            applies_to: init
            rationale: r
    """
    with pytest.raises(
        ManifestError,
        match=r"^artifacts\[1\]: id must be a non-empty, non-blank str, got None$",
    ):
        load_manifest(_write(tmp_path, text))


# --- strict wire shape: no silently-dropped keys ------------------------------


def test_duplicate_top_level_key_raises_manifest_error(tmp_path):
    """PyYAML's default loader keeps the LAST duplicate key silently, so a
    manifest with two `model_version:` lines would load as a different
    document than the one a human reviewed in the diff."""
    text = 'model_version: "1.0.0"\nmodel_version: "9.9.9"\nartifacts: []\n'
    with pytest.raises(
        ManifestError,
        # (?s) -- the YAML error's own file/line/column detail spans lines.
        match=r"(?s)^manifest: invalid YAML in .*found duplicate key 'model_version'",
    ):
        load_manifest(_write(tmp_path, text))


def test_duplicate_key_within_entry_raises_manifest_error(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: copied-seeded
            path: "one.md"
            path: "two.md"
            applies_to: init
            rationale: r
    """
    # `manifest: `, not `foo: ` -- a YAML-level failure is composed before
    # any entry structure exists to address, which is what ManifestError's
    # docstring promises.
    with pytest.raises(ManifestError, match=r"(?s)^manifest: invalid YAML in .*found duplicate key 'path'"):
        load_manifest(_write(tmp_path, text))


def test_unrecognized_top_level_key_raises_manifest_error(tmp_path):
    """A misspelled `artifacts:` must not degrade into an empty manifest."""
    text = 'model_version: "1.0.0"\nartefacts: []\n'
    with pytest.raises(ManifestError, match=r"^manifest: unrecognized top-level key\(s\): artefacts"):
        load_manifest(_write(tmp_path, text))


def test_unrecognized_entry_key_raises_manifest_error(tmp_path):
    """`untl:` would otherwise mean the entry silently never retires."""
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: copied-seeded
            path: "x"
            applies_to: init
            rationale: r
            untl: "2.0.0"
    """
    with pytest.raises(ManifestError, match=r"^foo: unrecognized entry key\(s\): untl"):
        load_manifest(_write(tmp_path, text))


def test_unrecognized_region_key_raises_manifest_error(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: hybrid-managed-region
            path: "AGENTS.md"
            applies_to: both
            rationale: r
            format: markdown
            regions:
              - name: tiers
                anchor: ["## Tiers"]
                anchors: ["typo"]
    """
    with pytest.raises(ManifestError, match=r"^foo: regions\[0\] \(tiers\): unrecognized region key\(s\): anchors"):
        load_manifest(_write(tmp_path, text))


# --- class-appropriate fields -------------------------------------------------


@pytest.mark.parametrize(
    ("extra_yaml", "expected_message"),
    [
        ('pin: ">=1.0"', r"^foo: pin is only valid on referenced entries"),
        ("format: markdown", r"^foo: format is only valid on hybrid-managed-region entries"),
        (
            'regions:\n              - {name: tiers, anchor: ["## Tiers"]}',
            r"^foo: regions are only valid on hybrid-managed-region entries",
        ),
    ],
)
def test_field_on_wrong_class_raises_manifest_error(tmp_path, extra_yaml, expected_message):
    """Requiring a field on its own class but ignoring it elsewhere is a
    silent no-op: the author believes the region/pin is honored, and
    nothing ever tells them otherwise."""
    text = f"""\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: copied-managed
            path: "x"
            applies_to: init
            rationale: r
            {extra_yaml}
    """
    with pytest.raises(ManifestError, match=expected_message):
        load_manifest(_write(tmp_path, text))


def test_duplicate_region_names_within_entry_raises_manifest_error(tmp_path):
    """A region name is its identity in the marker wire format -- two
    same-named regions give the writer two spans for one marker pair."""
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: hybrid-managed-region
            path: "AGENTS.md"
            applies_to: both
            rationale: r
            format: markdown
            regions:
              - name: tiers
                anchor: ["## Tiers"]
              - name: tiers
                anchor: ["## Other"]
    """
    with pytest.raises(ManifestError, match=r"^foo: region names must be unique"):
        load_manifest(_write(tmp_path, text))


def test_same_region_name_across_different_entries_is_allowed(tmp_path):
    """Uniqueness is per-entry, not global -- CLAUDE.md and AGENTS.md may
    both carry a region called `tiers`."""
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: agents-md
            class: hybrid-managed-region
            path: "AGENTS.md"
            applies_to: both
            rationale: r
            format: html
            regions:
              - name: tiers
                anchor: ["## Tiers"]
          - id: claude-md
            class: hybrid-managed-region
            path: "CLAUDE.md"
            applies_to: both
            rationale: r
            format: html
            regions:
              - name: tiers
                anchor: ["## Tiers"]
    """
    manifest = load_manifest(_write(tmp_path, text))
    assert [entry.id for entry in manifest.entries] == ["agents-md", "claude-md"]


def test_empty_never_write_pattern_raises_manifest_error(tmp_path):
    """Every other string field here is non-empty; an empty pattern
    reaching S-7.3's guard could match every path."""
    text = 'model_version: "1.0.0"\nnever_write: [""]\nartifacts: []\n'
    with pytest.raises(
        ManifestError,
        match=r"^manifest: never_write\[0\] must be a non-empty, non-blank str, got ''$",
    ):
        load_manifest(_write(tmp_path, text))


# --- file-level failures stay inside the ManifestError contract ---------------


def test_non_utf8_file_raises_manifest_error(tmp_path):
    """UnicodeDecodeError is a ValueError, NOT an OSError, so it escaped
    the `OSError`/`YAMLError` handlers."""
    path = tmp_path / "manifest.yaml"
    path.write_bytes(b'model_version: "\xff\xfe1.0.0"\n')
    with pytest.raises(ManifestError, match=r"^manifest: .*manifest\.yaml is not valid UTF-8: "):
        load_manifest(path)


def test_unusable_model_version_component_raises_manifest_error(tmp_path):
    """A grammatically valid but absurd component (CPython refuses int()
    past 4300 digits) must not escape as a raw ValueError."""
    text = f'model_version: "{"1" * 5000}.0.0"\nartifacts: []\n'
    with pytest.raises(ManifestError, match=r"^manifest: model_version: .*has an unusable numeric component: "):
        load_manifest(_write(tmp_path, text))


# --- immutability -------------------------------------------------------------


def test_schema_dataclasses_are_frozen_and_hashable():
    """P-11 leans on these being immutable value objects."""
    region = Region(name="tiers", anchor=("## Tiers",))
    entry = ManifestEntry(
        id="foo",
        artifact_class=ArtifactClass.COPIED_SEEDED,
        path="x",
        applies_to=AppliesTo.INIT,
        rationale="r",
    )
    manifest = Manifest(model_version=ModelVersion.parse("1.0.0"), never_write=(), entries=(entry,))
    for obj, field_name in ((region, "name"), (entry, "id"), (manifest, "never_write")):
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(obj, field_name, "mutated")
    # `assert {region, entry, manifest}` would be vacuous -- a non-empty set
    # literal is always truthy, so the assertion itself could never fail and
    # a `__hash__ = None` regression would surface as an unnamed TypeError.
    for obj in (region, entry, manifest):
        assert isinstance(hash(obj), int)


# --- _StrictLoader rejects AUTHORED duplicates, not merge-key overrides -------


def test_yaml_merge_key_override_is_accepted(tmp_path):
    """`<<: *anchor` is legal YAML whose entire purpose is that an explicit
    key wins, and it is the idiom a human reaches for in a file of
    near-identical entries. Scanning the node AFTER SafeConstructor's own
    `flatten_mapping()` splices the inherited pairs in reported the
    override as a duplicate, pointing at a line the author never repeated.
    """
    text = """\
        model_version: "1.0.0"
        artifacts:
          - &base
            id: base
            class: copied-seeded
            path: "a"
            applies_to: both
            rationale: r
          - <<: *base
            id: bar
            path: "b"
    """
    manifest = load_manifest(_write(tmp_path, text))
    assert [(entry.id, entry.path) for entry in manifest.entries] == [("base", "a"), ("bar", "b")]
    # Inherited-but-not-overridden keys still arrive.
    assert manifest.entries[1].rationale == "r"


def test_authored_duplicate_key_inside_a_merged_entry_still_rejected(tmp_path):
    """The merge-key allowance must not reopen the hazard it sits next to:
    a key the author genuinely wrote twice is still an error."""
    text = """\
        model_version: "1.0.0"
        artifacts:
          - &base
            id: base
            class: copied-seeded
            path: "a"
            applies_to: both
            rationale: r
          - <<: *base
            id: bar
            id: baz
    """
    with pytest.raises(ManifestError, match="found duplicate key 'id'"):
        load_manifest(_write(tmp_path, text))


# --- whitespace-only is not "non-empty" ---------------------------------------


@pytest.mark.parametrize(
    ("blank_field", "expected_message"),
    [
        # A blank `rationale` satisfies AD-55's reviewability requirement
        # without being reviewable; a blank `path` reaches S-7.3's guard
        # indistinguishable from a real target; a blank `id` cannot be
        # addressed by `explain <id>` -- and, having no visible characters,
        # cannot even label its own error, so it falls back to the index.
        ("id", r"^artifacts\[0\]: id must be a non-empty, non-blank str"),
        ("path", r"^foo: path must be a non-empty, non-blank str"),
        ("rationale", r"^foo: rationale must be a non-empty, non-blank str"),
    ],
)
def test_whitespace_only_required_field_raises_manifest_error(tmp_path, blank_field, expected_message):
    entry = {
        "id": "foo",
        "class": "copied-seeded",
        "path": "x",
        "applies_to": "init",
        "rationale": "r",
    }
    entry[blank_field] = "   "
    document = {"model_version": "1.0.0", "artifacts": [entry]}
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    with pytest.raises(ManifestError, match=expected_message):
        load_manifest(path)


def test_whitespace_only_optional_field_raises_manifest_error(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: referenced
            path: "n/a"
            applies_to: both
            rationale: r
            pin: "   "
    """
    with pytest.raises(ManifestError, match=r"^foo: pin must be a non-empty, non-blank str or None"):
        load_manifest(_write(tmp_path, text))


def test_whitespace_only_region_name_raises_manifest_error(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: hybrid-managed-region
            path: "AGENTS.md"
            applies_to: both
            rationale: r
            format: html
            regions:
              - name: "  "
                anchor: ["## Tiers"]
    """
    with pytest.raises(ManifestError, match=r"^foo: regions\[0\]: region name must be a non-empty, non-blank str"):
        load_manifest(_write(tmp_path, text))


def test_whitespace_only_never_write_pattern_raises_manifest_error(tmp_path):
    text = 'model_version: "1.0.0"\nnever_write: ["   "]\nartifacts: []\n'
    with pytest.raises(
        ManifestError,
        match=r"^manifest: never_write\[0\] must be a non-empty, non-blank str, got '   '$",
    ):
        load_manifest(_write(tmp_path, text))


def test_never_write_error_names_the_offending_pattern(tmp_path):
    """The one error in the module that named neither a locator nor the
    offending value. On S-7.5's real deny-list, "one of these is wrong" is
    a manual bisect -- the same defect already fixed at `artifacts[N]`,
    `regions[N] (name)` and `since:`/`until:`."""
    text = 'model_version: "1.0.0"\nnever_write: ["a", 42, "b"]\nartifacts: []\n'
    with pytest.raises(
        ManifestError,
        match=r"^manifest: never_write\[1\] must be a non-empty, non-blank str, got 42$",
    ):
        load_manifest(_write(tmp_path, text))


def test_never_write_pattern_is_stored_stripped(tmp_path):
    """A deny-pattern carrying stray padding matches nothing, so a rule
    that reads as present in the diff would silently protect no path."""
    text = 'model_version: "1.0.0"\nnever_write: ["  AGENTS.md  "]\nartifacts: []\n'
    assert load_manifest(_write(tmp_path, text)).never_write == ("AGENTS.md",)


# --- region errors name the offending region ----------------------------------


def test_region_error_names_the_offending_region(tmp_path):
    """An entry may carry several regions; reporting only which ENTRY
    failed leaves the operator to guess which region to edit -- the same
    defect already fixed one level up (`artifacts[N]`) and one field over
    (`since:`/`until:`)."""
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: hybrid-managed-region
            path: "AGENTS.md"
            applies_to: both
            rationale: r
            format: html
            regions:
              - name: one
                anchor: ["## One"]
              - name: two
                anchor: []
              - name: three
                anchor: ["## Three"]
    """
    with pytest.raises(ManifestError, match=r"^foo: regions\[1\] \(two\): anchor must be a non-empty list of str"):
        load_manifest(_write(tmp_path, text))


def test_region_error_falls_back_to_the_index_when_the_name_is_unusable(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: hybrid-managed-region
            path: "AGENTS.md"
            applies_to: both
            rationale: r
            format: html
            regions:
              - name: one
                anchor: ["## One"]
              - "not-a-mapping"
    """
    with pytest.raises(ManifestError, match=r"^foo: regions\[1\]: region must be a mapping"):
        load_manifest(_write(tmp_path, text))


# --- id uniqueness holds on the in-memory path too -----------------------------


def test_manifest_rejects_duplicate_entry_ids_when_constructed_directly():
    """The module documents these dataclasses as constructible on their own
    ("tests, a future in-memory manifest builder"), but unique ids -- the
    invariant every downstream consumer keys on -- were enforced only in
    `load_manifest`."""
    entries = tuple(
        ManifestEntry(
            id="dup",
            artifact_class=ArtifactClass.COPIED_SEEDED,
            path=path,
            applies_to=AppliesTo.BOTH,
            rationale="r",
        )
        for path in ("a", "b")
    )
    with pytest.raises(ValueError, match=r"entry ids must be unique, got duplicates: \['dup'\]"):
        Manifest(model_version=ModelVersion.parse("1.0.0"), never_write=(), entries=entries)


# --- top-level model_version: the two likeliest authoring mistakes -------------


def test_missing_model_version_key_raises_manifest_error(tmp_path):
    """Reported as a missing REQUIRED key, not as `parse(None)`'s type
    error ("version must be a str, got None"), which reads as a bug report
    rather than an instruction to add the line."""
    with pytest.raises(ManifestError, match=r"^manifest: model_version: required key is missing$"):
        load_manifest(_write(tmp_path, "artifacts: []\n"))


def test_unquoted_model_version_parses_as_a_float_and_is_rejected(tmp_path):
    """`model_version: 1.0` is a YAML float, not a version string."""
    with pytest.raises(ManifestError, match=r"^manifest: model_version: version must be a str, got 1.0$"):
        load_manifest(_write(tmp_path, "model_version: 1.0\nartifacts: []\n"))


# --- whitespace is not part of an identity --------------------------------------


def test_padded_id_is_stripped_and_collides_with_its_bare_twin(tmp_path):
    """Deciding validity on `.strip()` while STORING the padding made
    surrounding whitespace significant to identity and to nothing else:
    `id: "foo"` and `id: " foo "` loaded as two distinct entries that render
    identically, defeating the AC's duplicate-id rule and leaving neither
    reachable by `explain foo`."""
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: "foo"
            class: copied-seeded
            path: "a.md"
            applies_to: both
            rationale: r
          - id: "  foo  "
            class: copied-seeded
            path: "b.md"
            applies_to: both
            rationale: r
    """
    with pytest.raises(ManifestError, match=r"^foo: duplicate id$"):
        load_manifest(_write(tmp_path, text))


def test_padded_text_fields_are_stored_stripped(tmp_path):
    """A padded `path` would reach S-7.3's guard matching no pattern and no
    file; a padded `pin`/`legacy_of` would never match its counterpart."""
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: "  foo  "
            class: referenced
            path: "  AGENTS.md  "
            applies_to: both
            rationale: "  because  "
            pin: "  >=3.7b  "
            legacy_of: "  old-id  "
    """
    entry = load_manifest(_write(tmp_path, text)).entries[0]
    assert (entry.id, entry.path, entry.rationale) == ("foo", "AGENTS.md", "because")
    assert (entry.pin, entry.legacy_of) == (">=3.7b", "old-id")


def test_blank_anchor_item_raises_manifest_error(tmp_path):
    """An anchor is AD-56's literal line-prefix matcher, so a
    whitespace-only one matches the first indented line in the target file
    and splices the managed region at an arbitrary position -- the same
    "matches everything" hazard that disqualifies an empty `never_write`
    pattern. This was the one string field the non-blank sweep missed."""
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: hybrid-managed-region
            path: "AGENTS.md"
            applies_to: both
            rationale: r
            format: html
            regions:
              - name: tiers
                anchor: ["   "]
    """
    with pytest.raises(
        ManifestError,
        match=r"^foo: regions\[0\] \(tiers\): anchor must contain only non-blank str",
    ):
        load_manifest(_write(tmp_path, text))


def test_anchor_item_keeps_its_own_leading_whitespace(tmp_path):
    """Unlike an id or a path, an anchor's leading whitespace is
    significant -- an author may deliberately anchor on an indented line --
    so a non-blank anchor is NOT stripped."""
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: hybrid-managed-region
            path: "AGENTS.md"
            applies_to: both
            rationale: r
            format: html
            regions:
              - name: tiers
                anchor: ["    - nested item"]
    """
    entry = load_manifest(_write(tmp_path, text)).entries[0]
    assert entry.regions[0].anchor == ("    - nested item",)


# --- a field the class does not take is reported as such ------------------------


def test_regions_on_a_non_hybrid_class_is_reported_before_region_shape(tmp_path):
    """Building the regions first reported `anchor must be a non-empty
    list` -- telling the author to repair a region the class forbids
    outright."""
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: copied-seeded
            path: "a.md"
            applies_to: both
            rationale: r
            regions:
              - name: tiers
                anchor: []
    """
    with pytest.raises(
        ManifestError,
        match=r"^foo: regions are only valid on hybrid-managed-region entries,"
        r" got class 'copied-seeded'$",
    ):
        load_manifest(_write(tmp_path, text))


def test_unrecognized_class_still_reports_itself_before_the_regions_gate(tmp_path):
    """The early regions gate must not shadow the class error itself."""
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: bogus-class
            path: "a.md"
            applies_to: both
            rationale: r
            regions:
              - name: tiers
                anchor: []
    """
    with pytest.raises(ManifestError, match=r"^foo: .*not a valid ArtifactClass"):
        load_manifest(_write(tmp_path, text))


def test_wrong_typed_pin_on_a_non_referenced_class_reports_the_class_rule(tmp_path):
    """`pin: 5` on a `copied-managed` entry read "pin must be a non-empty,
    non-blank str", sending the author to fix the type of a field they must
    delete."""
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: copied-managed
            path: "a.md"
            applies_to: both
            rationale: r
            pin: 5
    """
    with pytest.raises(ManifestError, match=r"^foo: pin is only valid on referenced entries, got 5$"):
        load_manifest(_write(tmp_path, text))


# --- a repeated merge key is an authored duplicate ------------------------------


def test_repeated_merge_key_raises_manifest_error(tmp_path):
    """PyYAML resolves two `<<:` keys last-wins; the equivalent
    `<<: [*a, *b]` sequence spelling resolves first-wins. Two spellings of
    "inherit from a and b" producing opposite artifacts is exactly what
    `_StrictLoader` exists to prevent, and the merge exemption was written
    for ONE merge key overriding an inherited value."""
    text = """\
        model_version: "1.0.0"
        artifacts:
          - &a
            id: base_a
            class: copied-seeded
            path: "from-a.md"
            applies_to: both
            rationale: r
          - &b
            id: base_b
            class: copied-seeded
            path: "from-b.md"
            applies_to: both
            rationale: r
          - <<: *a
            <<: *b
            id: merged
    """
    with pytest.raises(ManifestError, match=r"(?s)^manifest: invalid YAML in .*found duplicate merge key '<<'"):
        load_manifest(_write(tmp_path, text))


def test_merge_key_sequence_is_accepted_and_resolves_first_wins(tmp_path):
    """The sanctioned way to merge several anchors stays legal."""
    text = """\
        model_version: "1.0.0"
        artifacts:
          - &a
            id: base_a
            class: copied-seeded
            path: "from-a.md"
            applies_to: both
            rationale: r
          - &b
            id: base_b
            class: copied-seeded
            path: "from-b.md"
            applies_to: both
            rationale: r
          - <<: [*a, *b]
            id: merged
    """
    manifest = load_manifest(_write(tmp_path, text))
    merged = next(entry for entry in manifest.entries if entry.id == "merged")
    assert merged.path == "from-a.md"


# --- dataclass-level type guards (direct construction) --------------------------


def test_region_anchor_rejects_non_str_items():
    with pytest.raises(ValueError, match=r"anchor must contain only non-blank str"):
        Region(name="tiers", anchor=(1, 2))  # pyright: ignore[reportArgumentType]


def test_entry_regions_rejects_non_region_items():
    with pytest.raises(ValueError, match=r"regions must contain only Region instances"):
        ManifestEntry(
            id="foo",
            artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
            path="x",
            applies_to=AppliesTo.INIT,
            rationale="r",
            format="html",
            regions=("not-a-region",),  # pyright: ignore[reportArgumentType]
        )


@pytest.mark.parametrize("bound", ["since", "until"])
def test_entry_bounds_reject_non_model_version(bound):
    with pytest.raises(ValueError, match=rf"{bound} must be a ModelVersion or None, got '1.0.0'"):
        ManifestEntry(
            id="foo",
            artifact_class=ArtifactClass.COPIED_SEEDED,
            path="x",
            applies_to=AppliesTo.INIT,
            rationale="r",
            **{bound: "1.0.0"},  # pyright: ignore[reportArgumentType]
        )


def test_manifest_rejects_non_model_version():
    with pytest.raises(ValueError, match=r"model_version must be a ModelVersion, got '1.0.0'"):
        Manifest(
            model_version="1.0.0",  # pyright: ignore[reportArgumentType]
            never_write=(),
            entries=(),
        )


def test_manifest_rejects_non_entry_items():
    with pytest.raises(ValueError, match=r"entries must contain only ManifestEntry instances"):
        Manifest(
            model_version=ModelVersion.parse("1.0.0"),
            never_write=(),
            entries=("not-an-entry",),  # pyright: ignore[reportArgumentType]
        )


# --- Story 8.1: the two forward-referenced checks S-7.4 left open ----------
# (see this module's own docstring + the S-7.4 spec's Review Triage Log --
# S-8.1 builds the `RegionFormat` registry / `REGION_NAME_PATTERN` in
# `seed/regions/markers.py` and wires both back in here.)


def test_unregistered_format_raises_manifest_error_naming_id_and_format(tmp_path):
    """AD-53's registry has exactly three members (html/hash/slashstar);
    `xml` is not one of them."""
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: hybrid-managed-region
            path: "AGENTS.md"
            applies_to: both
            rationale: r
            format: xml
            regions:
              - name: tiers
                anchor: ["## Tiers"]
    """
    with pytest.raises(ManifestError, match=r"^foo: .*xml.*not a valid RegionFormat"):
        load_manifest(_write(tmp_path, text))


def test_marker_unsafe_region_name_raises_manifest_error_naming_id_and_name(tmp_path):
    """A region name is a marker-safe token (`REGION_NAME_PATTERN`, shared
    with `markers.py`'s `BeginMarker`/`EndMarker`) -- a raw space or `=`
    would be ambiguous inside the rendered `region=<name>` marker field."""
    text = """\
        model_version: "1.0.0"
        artifacts:
          - id: foo
            class: hybrid-managed-region
            path: "AGENTS.md"
            applies_to: both
            rationale: r
            format: html
            regions:
              - name: "my region"
                anchor: ["## Tiers"]
    """
    with pytest.raises(ManifestError, match=r"^foo: regions\[0\] \(my region\): region name must match .*my region"):
        load_manifest(_write(tmp_path, text))
