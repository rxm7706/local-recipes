"""pyforge.core.report -- the shared report-envelope schema DATA plus a pure
dict-compose helper (Story 14.3, SPEC-pyforge-core CAP-4).

Deliberately ships schema DATA and a pure dict-merge helper only -- never a
``jsonschema.validate`` call. ``jsonschema`` is third-party, and
``tests/meta/test_leaf_constraint.py`` fails the build on any non-stdlib
import under ``pyforge.core`` (CAP-1's leaf constraint). Each station's own
``jsonschema`` call site (warden's, doctor's production code; marshal's test
call sites) stays exactly where it is -- this module only supplies the base
schema fragment and the composition shape.

``BASE_ENVELOPE_SCHEMA`` requires only that ``schema_version`` is PRESENT
(no type constraint -- warden's is a pattern-matched string, doctor's and
marshal's are integers, so a shared type would break one of the three) and
that ``findings`` is present and is an array (the one field every station's
finding-list already satisfies). It never declares ``additionalProperties``,
so it can neither open nor close what each station's own schema already
decided (warden/doctor open, marshal closed).

``compose(base, station_schema)`` is a pure ``{"allOf": [base,
station_schema]}`` dict merge -- no ``$ref``, no schema registry, no
cross-package URI resolution. Each station's existing schema file is
embedded verbatim, unmodified, as the second ``allOf`` branch: a document
satisfying the composed schema must satisfy BOTH branches, so every payload
that validated against the station schema alone still validates (the base
branch only adds already-satisfied presence checks).
"""

from __future__ import annotations

from typing import Any

BASE_ENVELOPE_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "urn:local-recipes:pyforge-core:base-envelope-schema",
    "type": "object",
    "required": ["schema_version", "findings"],
    "properties": {
        "findings": {"type": "array"},
    },
}


def compose(base: dict[str, Any], station_schema: dict[str, Any]) -> dict[str, Any]:
    """Pure dict merge: a document must satisfy both ``base`` and
    ``station_schema``. Neither argument is mutated or copied deep -- the
    returned dict references both inputs directly."""
    return {"allOf": [base, station_schema]}
