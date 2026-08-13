"""Unit tests for ``pyforge.core.report`` (Story 14.3, CAP-4).

Covers the intent contract's I/O & Edge-Case Matrix rows that concern the
pure primitives shipped here (``BASE_ENVELOPE_SCHEMA`` shape, ``compose()``
merge shape). The ``jsonschema``-validation rows (a real captured report
from each station validating against the composed schema) are proven at
each STATION's own test suite instead -- pyforge-core ships zero
``jsonschema`` dependency (CAP-1's leaf constraint), so no test here may
import it either.
"""

from __future__ import annotations

from pyforge.core.report import BASE_ENVELOPE_SCHEMA, compose


def test_base_envelope_schema_requires_schema_version_present_untyped():
    assert "schema_version" in BASE_ENVELOPE_SCHEMA["required"]
    # No type constraint anywhere for schema_version: warden's is a
    # pattern-matched string, doctor's/marshal's are integers.
    assert "schema_version" not in BASE_ENVELOPE_SCHEMA.get("properties", {})


def test_base_envelope_schema_requires_findings_as_an_array():
    assert "findings" in BASE_ENVELOPE_SCHEMA["required"]
    assert BASE_ENVELOPE_SCHEMA["properties"]["findings"]["type"] == "array"


def test_base_envelope_schema_never_declares_additional_properties():
    assert "additionalProperties" not in BASE_ENVELOPE_SCHEMA


def test_compose_shape_is_a_pure_allof_merge():
    station_schema = {"type": "object", "required": ["x"]}
    composed = compose(BASE_ENVELOPE_SCHEMA, station_schema)
    assert composed == {"allOf": [BASE_ENVELOPE_SCHEMA, station_schema]}


def test_compose_embeds_each_input_verbatim_not_copied():
    base = {"a": 1}
    station_schema = {"b": 2}
    composed = compose(base, station_schema)
    assert composed["allOf"][0] is base
    assert composed["allOf"][1] is station_schema
