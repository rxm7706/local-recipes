"""Unit tests for ``pyforge.marshal.seed.model.manifest`` (Story 7.4) --
covers the spec's I/O & Edge-Case Matrix for ``load_manifest``: the six
``ArtifactClass`` members, every ``ManifestError`` scenario (naming the
offending id/field), and the ``since``/``until`` version-range filter.
"""

from __future__ import annotations

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
    with pytest.raises(ManifestError, match="foo"):
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
    with pytest.raises(ManifestError, match="foo"):
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
    with pytest.raises(ManifestError, match="foo"):
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
    with pytest.raises(ManifestError, match="foo"):
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
    with pytest.raises(ManifestError, match="foo"):
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
    with pytest.raises(ManifestError, match="foo"):
        load_manifest(_write(tmp_path, text))


@pytest.mark.parametrize(
    "missing_field",
    ["id", "class", "path", "applies_to", "rationale"],
)
def test_missing_required_field_raises_manifest_error(tmp_path, missing_field):
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
    with pytest.raises(ManifestError):
        load_manifest(path)


@pytest.mark.parametrize("bad_type_field", ["id", "path"])
def test_wrong_type_required_field_raises_manifest_error(tmp_path, bad_type_field):
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
    with pytest.raises(ManifestError):
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
    with pytest.raises(ManifestError, match="foo"):
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
    with pytest.raises(ManifestError, match="foo"):
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
    with pytest.raises(ManifestError, match="foo"):
        load_manifest(_write(tmp_path, text))


def test_malformed_top_level_model_version_wraps_invalid_version_error(tmp_path):
    text = """\
        model_version: "not-a-version"
        artifacts: []
    """
    with pytest.raises(ManifestError, match="manifest") as excinfo:
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
    with pytest.raises(ManifestError, match="foo"):
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
    with pytest.raises(ManifestError, match="foo"):
        load_manifest(_write(tmp_path, text))


def test_non_mapping_top_level_document_raises_manifest_error(tmp_path):
    text = "- just\n- a\n- list\n"
    with pytest.raises(ManifestError, match="manifest"):
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
            id="x", artifact_class="copied-seeded", path="p", applies_to="init",
            rationale="r", regions=5,
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
    with pytest.raises(ManifestError, match="never_write"):
        load_manifest(_write(tmp_path, text))


def test_falsy_non_list_artifacts_raises_manifest_error(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts: false
    """
    with pytest.raises(ManifestError, match="artifacts"):
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
    with pytest.raises(ManifestError, match="foo"):
        load_manifest(_write(tmp_path, text))


def test_non_mapping_artifacts_entry_raises_manifest_error(tmp_path):
    text = """\
        model_version: "1.0.0"
        artifacts:
          - "just a string, not a mapping"
    """
    with pytest.raises(ManifestError, match=r"artifacts\[0\]"):
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
    with pytest.raises(ManifestError, match="foo"):
        load_manifest(_write(tmp_path, text))


def test_missing_file_raises_manifest_error(tmp_path):
    with pytest.raises(ManifestError, match="could not read"):
        load_manifest(tmp_path / "does-not-exist.yaml")


def test_malformed_yaml_raises_manifest_error(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text(": not: valid: yaml: [", encoding="utf-8")
    with pytest.raises(ManifestError, match="invalid YAML"):
        load_manifest(path)


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
    with pytest.raises(ManifestError, match=r"artifacts\[1\]"):
        load_manifest(_write(tmp_path, text))
