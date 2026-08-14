"""Unit tests for ``pyforge.marshal.seed.detect.findings`` (Story 9.1) --
covers the spec's I/O & Edge-Case Matrix: valid/direct construction,
mismatched-remedy and blank-field rejection, ``Finding.new(...)`` string
coercion and invalid-value rejection, ``REMEDIES`` completeness, and
``to_json_dict()`` stability, plus frozen/hashable dataclass conventions
matching ``test_seed_model_artifact.py``'s own house style.
"""

from __future__ import annotations

import dataclasses

import pytest
from pyforge.marshal.seed.detect.findings import (
    REMEDIES,
    Finding,
    FindingType,
    Severity,
)


def test_finding_new_resolves_remedy_from_remedies():
    finding = Finding.new(Severity.HARD, FindingType.ARTIFACT_MISSING, "AGENTS.md", "missing")
    assert finding.severity is Severity.HARD
    assert finding.type is FindingType.ARTIFACT_MISSING
    assert finding.path == "AGENTS.md"
    assert finding.message == "missing"
    assert finding.remedy == REMEDIES[FindingType.ARTIFACT_MISSING]


def test_direct_construction_with_correct_remedy_matches_finding_new():
    direct = Finding(
        Severity.INFO,
        FindingType.LEGACY_PRESENT,
        "docs/specs/x.md",
        "legacy",
        REMEDIES[FindingType.LEGACY_PRESENT],
    )
    via_new = Finding.new(Severity.INFO, FindingType.LEGACY_PRESENT, "docs/specs/x.md", "legacy")
    assert direct == via_new


def test_direct_construction_with_mismatched_remedy_raises_value_error():
    with pytest.raises(ValueError, match=r"^uncovered: remedy must be "):
        Finding(Severity.HARD, FindingType.UNCOVERED, "x", "m", "wrong text")


@pytest.mark.parametrize("blank_path", ["", "   "])
def test_blank_path_raises_value_error(blank_path):
    with pytest.raises(ValueError, match=r"^path must be a non-empty, non-blank str"):
        Finding.new(Severity.HARD, FindingType.UNCOVERED, blank_path, "m")


@pytest.mark.parametrize("blank_message", ["", "   "])
def test_blank_message_raises_value_error(blank_message):
    with pytest.raises(ValueError, match=r"^message must be a non-empty, non-blank str"):
        Finding.new(Severity.HARD, FindingType.UNCOVERED, "x", blank_message)


def test_finding_new_coerces_plain_matching_strings():
    finding = Finding.new("HARD", "uncovered", "x", "m")
    assert finding.severity is Severity.HARD
    assert finding.type is FindingType.UNCOVERED
    assert isinstance(finding.severity, Severity)
    assert isinstance(finding.type, FindingType)


def test_direct_construction_also_coerces_plain_matching_strings():
    """``__post_init__`` owns the coercion, not ``Finding.new`` -- direct
    construction must normalize identically."""
    finding = Finding("HARD", "uncovered", "x", "m", REMEDIES[FindingType.UNCOVERED])  # type: ignore[arg-type]
    assert finding.severity is Severity.HARD
    assert finding.type is FindingType.UNCOVERED


def test_finding_new_rejects_invalid_severity_string():
    with pytest.raises(ValueError):
        Finding.new("CRITICAL", "uncovered", "x", "m")


def test_finding_new_rejects_invalid_type_string():
    with pytest.raises(ValueError):
        Finding.new("HARD", "not-a-real-type", "x", "m")


def test_remedies_has_a_non_empty_str_entry_for_every_finding_type():
    for finding_type in FindingType:
        assert finding_type in REMEDIES
        remedy = REMEDIES[finding_type]
        assert isinstance(remedy, str)
        assert remedy.strip()


def test_finding_type_is_exactly_the_12_members_the_epics_ac_names():
    # A count-only check would still pass a typo'd/renamed member -- pin the
    # exact kebab-case value set the epics AC names.
    assert {member.value for member in FindingType} == {
        "artifact-missing",
        "managed-file-modified",
        "managed-region-modified",
        "managed-region-missing",
        "derived-stale",
        "model-behind",
        "state-invalid",
        "never-write-violation",
        "referenced-dep-missing",
        "uncovered",
        "legacy-present",
        "opted-out",
    }


def test_finding_new_and_direct_construction_raise_identically_for_a_type_missing_from_remedies(
    monkeypatch,
):
    # Exercises the otherwise-dead "no REMEDIES entry" path (currently
    # unreachable in production since REMEDIES covers every real member)
    # through both construction routes, proving they raise the same
    # ValueError rather than Finding.new leaking a bare KeyError.
    import pyforge.marshal.seed.detect.findings as findings_module

    incomplete_remedies = {
        k: v for k, v in REMEDIES.items() if k is not FindingType.UNCOVERED
    }
    monkeypatch.setattr(findings_module, "REMEDIES", incomplete_remedies)

    with pytest.raises(ValueError, match=r"^uncovered: no REMEDIES entry"):
        Finding.new(Severity.HARD, FindingType.UNCOVERED, "x", "m")

    with pytest.raises(ValueError, match=r"^uncovered: no REMEDIES entry"):
        Finding(Severity.HARD, FindingType.UNCOVERED, "x", "m", "anything")


def test_path_and_message_are_stripped_before_storage():
    finding = Finding.new(Severity.HARD, FindingType.UNCOVERED, "  x  ", "  m  ")
    assert finding.path == "x"
    assert finding.message == "m"


def test_to_json_dict_has_stable_key_order_and_plain_str_values():
    finding = Finding.new(Severity.HARD, FindingType.UNCOVERED, "x", "m")
    result = finding.to_json_dict()
    assert list(result.keys()) == ["severity", "type", "path", "message", "remedy"]
    assert result == {
        "severity": "HARD",
        "type": "uncovered",
        "path": "x",
        "message": "m",
        "remedy": REMEDIES[FindingType.UNCOVERED],
    }
    assert all(isinstance(value, str) for value in result.values())


def test_finding_is_frozen_and_hashable():
    finding = Finding.new(Severity.HARD, FindingType.UNCOVERED, "x", "m")
    with pytest.raises(dataclasses.FrozenInstanceError):
        finding.path = "y"  # type: ignore[misc]
    assert isinstance(hash(finding), int)
