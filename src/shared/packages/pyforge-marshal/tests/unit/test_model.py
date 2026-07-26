"""Unit tests for ``pyforge.marshal.core.model`` (Story 1.1) -- covers the
spec's I/O & Edge-Case Matrix for the Finding/Envelope contract, plus
jsonschema validation of ``Envelope.to_json_dict()`` against the packaged
``schemas/envelope.v1.json``.

``core.findings.REGISTERED_CODES`` starts an empty ``frozenset()`` (Design
Notes) -- every test needing a *valid* ``Finding`` registers a synthetic
code via ``monkeypatch`` first, mirroring the sibling meta-tests'
convention of never seeding invented production codes.
"""

from __future__ import annotations

import json
import re
from importlib import resources

import jsonschema
import pytest

from pyforge.marshal.core import findings
from pyforge.marshal.core.model import (
    Envelope,
    Finding,
    Severity,
    Status,
    Verdict,
    build_envelope,
    status_for,
)

_SYNTHETIC_CODE = "MRS-TST-001"


@pytest.fixture
def registered_code(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(findings, "REGISTERED_CODES", frozenset({_SYNTHETIC_CODE}))
    return _SYNTHETIC_CODE


def _schema() -> dict:
    schema_text = (
        resources.files("pyforge.marshal")
        .joinpath("schemas", "envelope.v1.json")
        .read_text(encoding="utf-8")
    )
    return json.loads(schema_text)


def _finding(code: str, severity: Severity = Severity.WARN) -> Finding:
    return Finding(code=code, severity=severity, message="m")


# --- Finding: construction / coercion / registry enforcement ---------------


def test_finding_constructs_with_registered_code(registered_code):
    finding = _finding(registered_code)
    assert finding.code == registered_code
    assert finding.severity is Severity.WARN
    assert finding.path is None


def test_finding_accepts_raw_string_severity(registered_code):
    finding = Finding(code=registered_code, severity="error", message="m")
    assert finding.severity is Severity.ERROR


def test_finding_unregistered_code_rejected():
    with pytest.raises(findings.UnregisteredFindingCodeError):
        Finding(code="MRS-ZZZ-999", severity=Severity.WARN, message="m")


def test_finding_malformed_code_rejected_before_membership_check():
    with pytest.raises(findings.UnregisteredFindingCodeError):
        Finding(code="not-a-code", severity=Severity.WARN, message="m")


def test_finding_to_json_dict_omits_path_when_none(registered_code):
    assert _finding(registered_code).to_json_dict() == {
        "code": registered_code,
        "severity": "warn",
        "message": "m",
    }


def test_finding_to_json_dict_includes_path_when_present(registered_code):
    finding = Finding(
        code=registered_code, severity=Severity.INFO, message="m", path="x/y"
    )
    assert finding.to_json_dict()["path"] == "x/y"


# --- status_for --------------------------------------------------------


@pytest.mark.parametrize(
    "verdict,expected",
    [
        (Verdict.CLEAN, Status.OK),
        (Verdict.WARN, Status.OK),
        (Verdict.UNEVALUABLE, Status.ERROR),
        (Verdict.SCOPE_VIOLATION, Status.ERROR),
        (Verdict.GATE_FAILED, Status.ERROR),
        (Verdict.ERROR, Status.ERROR),
    ],
)
def test_status_for_partitions_every_verdict(verdict, expected):
    assert status_for(verdict) is expected


def test_status_for_accepts_raw_string():
    assert status_for("clean") is Status.OK
    assert status_for("error") is Status.ERROR


# --- Envelope: construction, coercion, AD-39 raise scenarios ---------------


def test_envelope_valid_construction_per_verdict(registered_code):
    for verdict in Verdict:
        envelope = build_envelope(command="x", verdict=verdict, data={}, findings=())
        assert envelope.status is status_for(verdict)
        assert envelope.verdict is verdict


def test_envelope_mismatched_status_and_verdict_rejected():
    with pytest.raises(ValueError):
        Envelope(
            schema_version=1,
            command="x",
            status=Status.OK,
            verdict=Verdict.ERROR,
            data={},
            data_version=1,
            findings=(),
        )


def test_envelope_ok_status_with_error_finding_rejected(registered_code):
    error_finding = Finding(code=registered_code, severity=Severity.ERROR, message="m")
    with pytest.raises(ValueError):
        Envelope(
            schema_version=1,
            command="x",
            status=Status.OK,
            verdict=Verdict.CLEAN,
            data={},
            data_version=1,
            findings=(error_finding,),
        )


def test_envelope_data_is_defensively_copied(registered_code):
    data = {"k": "v"}
    envelope = build_envelope(command="x", verdict=Verdict.CLEAN, data=data)
    data["k"] = "mutated"
    assert envelope.data == {"k": "v"}


def test_envelope_data_nested_mutable_value_is_deep_copied(registered_code):
    """A shallow ``dict(data)`` copy still shares any NESTED list/dict with
    the caller -- mutating that nested structure after construction must not
    leak into the (supposedly frozen) envelope."""
    data = {"paths": ["a", "b"]}
    envelope = build_envelope(command="x", verdict=Verdict.CLEAN, data=data)
    data["paths"].append("c")
    assert envelope.data == {"paths": ["a", "b"]}


def test_envelope_to_json_dict_does_not_leak_a_live_data_reference(registered_code):
    envelope = build_envelope(command="x", verdict=Verdict.CLEAN, data={"paths": ["a"]})
    document = envelope.to_json_dict()
    document["data"]["paths"].append("mutated")
    assert envelope.data == {"paths": ["a"]}


def test_envelope_rejects_wrong_schema_version(registered_code):
    with pytest.raises(ValueError):
        Envelope(
            schema_version=2,
            command="x",
            status=Status.OK,
            verdict=Verdict.CLEAN,
            data={},
            data_version=1,
            findings=(),
        )


@pytest.mark.parametrize("bad_data_version", [0, -1, True])
def test_envelope_rejects_invalid_data_version(bad_data_version):
    with pytest.raises(ValueError):
        Envelope(
            schema_version=1,
            command="x",
            status=Status.OK,
            verdict=Verdict.CLEAN,
            data={},
            data_version=bad_data_version,
            findings=(),
        )


def test_envelope_rejects_non_dict_data():
    with pytest.raises(ValueError):
        Envelope(
            schema_version=1,
            command="x",
            status=Status.OK,
            verdict=Verdict.CLEAN,
            data="not-a-dict",
            data_version=1,
            findings=(),
        )


def test_envelope_to_json_dict_shape(registered_code):
    finding = _finding(registered_code)
    envelope = build_envelope(
        command="x",
        verdict=Verdict.WARN,
        data={"a": 1},
        findings=(finding,),
        assumptions=("assumed x",),
    )
    assert envelope.to_json_dict() == {
        "schema_version": 1,
        "command": "x",
        "status": "ok",
        "verdict": "warn",
        "data": {"a": 1},
        "data_version": 1,
        "findings": [finding.to_json_dict()],
        "assumptions": ["assumed x"],
    }


# --- Schema validation -------------------------------------------------------


def test_envelope_json_dict_validates_against_schema_for_every_verdict(
    registered_code,
):
    schema = _schema()
    for verdict in Verdict:
        severity = Severity.WARN if status_for(verdict) is Status.OK else Severity.ERROR
        finding = Finding(code=registered_code, severity=severity, message="m")
        envelope = build_envelope(
            command="x", verdict=verdict, data={}, findings=(finding,)
        )
        jsonschema.validate(envelope.to_json_dict(), schema)


def test_envelope_missing_key_fails_schema():
    document = {
        "schema_version": 1,
        "command": "x",
        "status": "ok",
        "verdict": "clean",
        "data": {},
        "data_version": 1,
        "findings": [],
        # "assumptions" deliberately omitted
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(document, _schema())


def test_envelope_unknown_top_level_key_fails_schema():
    document = {
        "schema_version": 1,
        "command": "x",
        "status": "ok",
        "verdict": "clean",
        "data": {},
        "data_version": 1,
        "findings": [],
        "assumptions": [],
        "stauts": "ok",  # typo'd extra key -- additionalProperties: false must catch it
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(document, _schema())


def test_finding_unknown_key_fails_schema():
    document = {
        "code": "MRS-TST-001",
        "severity": "warn",
        "message": "m",
        "eviddence": {},  # typo'd extra key
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(document, _schema()["$defs"]["finding"])


def test_findings_code_pattern_matches_the_packaged_schema_pattern():
    """``core.findings.CODE_PATTERN`` and ``schemas/envelope.v1.json``'s
    ``finding.code`` pattern are independent copies of the same rule -- this
    test is the tripwire that catches them drifting apart."""
    schema_pattern = _schema()["$defs"]["finding"]["properties"]["code"]["pattern"]
    probes = [
        "MRS-GATE-001",
        "MRS-A-000",
        "not-a-code",
        "MRS-gate-001",
        "MRS-GATE-01",
        "MRS-GATE-001\n",
    ]
    for probe in probes:
        assert bool(findings.CODE_PATTERN.fullmatch(probe)) == bool(
            re.fullmatch(schema_pattern, probe)
        ), f"CODE_PATTERN/schema pattern diverge on {probe!r}"
