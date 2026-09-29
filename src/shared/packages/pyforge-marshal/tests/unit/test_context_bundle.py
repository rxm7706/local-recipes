"""Story 46.2 (spec-pyforge-marshal CAP-192) -- the pure context-bundle
contract: deterministic assembly + digest, and the digest-mismatch
finding."""

from __future__ import annotations

import hashlib
import json

from pyforge.marshal.core import context_bundle
from pyforge.marshal.core.derived_context import DerivedArtifactDeclaration
from pyforge.marshal.core.model import Severity, Verdict
from pyforge.marshal.core.verdict import compute_verdict

_DERIVED_LAYER = {"enabled": True, "aggressiveness": "medium"}
_PLANNING_LAYER = {"enabled": False, "aggressiveness": "medium"}

_DECL_A = DerivedArtifactDeclaration(
    name="marshal:slug:epic-7-context",
    sources=("a.md", "b.md"),
    output="epic-7-context.md",
)
_DECL_B = DerivedArtifactDeclaration(
    name="marshal:slug:epic-7-continuity",
    sources=(),
    output=None,
)


def _bundle(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "epic": "7",
        "derived_context_layer": _DERIVED_LAYER,
        "planning_graph_layer": _PLANNING_LAYER,
        "declarations": (_DECL_A, _DECL_B),
    }
    kwargs.update(overrides)
    return context_bundle.assemble_bundle(**kwargs)  # type: ignore[arg-type]


class TestAssembleBundle:
    def test_shape_is_json_safe_with_schema_and_epic(self):
        bundle = _bundle()
        assert bundle["schema"] == context_bundle.BUNDLE_SCHEMA
        assert bundle["schema_version"] == context_bundle.BUNDLE_SCHEMA_VERSION
        assert bundle["epic"] == "7"
        # Round-trips through json.dumps with no TypeError -- plain data only.
        json.dumps(bundle, sort_keys=True)

    def test_derived_context_carries_enabled_aggressiveness_and_declarations(self):
        bundle = _bundle()
        derived = bundle["derived_context"]
        assert isinstance(derived, dict)
        assert derived["enabled"] is True
        assert derived["aggressiveness"] == "medium"
        assert derived["declarations"] == [
            {"name": "marshal:slug:epic-7-context", "sources": ["a.md", "b.md"], "output": "epic-7-context.md"},
            {"name": "marshal:slug:epic-7-continuity", "sources": [], "output": None},
        ]

    def test_planning_graph_carries_enabled_and_aggressiveness_only(self):
        bundle = _bundle()
        assert bundle["planning_graph"] == {"enabled": False, "aggressiveness": "medium"}

    def test_declarations_are_sorted_by_name_regardless_of_input_order(self):
        forward = _bundle(declarations=(_DECL_A, _DECL_B))
        reversed_order = _bundle(declarations=(_DECL_B, _DECL_A))
        assert forward == reversed_order

    def test_none_layers_read_as_disabled(self):
        bundle = _bundle(derived_context_layer=None, planning_graph_layer=None)
        assert bundle["derived_context"]["enabled"] is False
        assert bundle["derived_context"]["aggressiveness"] is None
        assert bundle["planning_graph"] == {"enabled": False, "aggressiveness": None}

    def test_empty_declarations_produce_an_empty_list(self):
        bundle = _bundle(declarations=())
        assert bundle["derived_context"]["declarations"] == []


class TestBundleDigest:
    def test_two_assemblies_of_identical_inputs_are_byte_identical(self):
        first = context_bundle.bundle_digest(_bundle())
        second = context_bundle.bundle_digest(_bundle())
        assert first == second

    def test_out_of_order_declarations_still_produce_an_identical_digest(self):
        forward = context_bundle.bundle_digest(_bundle(declarations=(_DECL_A, _DECL_B)))
        reversed_order = context_bundle.bundle_digest(_bundle(declarations=(_DECL_B, _DECL_A)))
        assert forward == reversed_order

    def test_a_changed_declaration_changes_the_digest(self):
        baseline = context_bundle.bundle_digest(_bundle())
        changed_decl = DerivedArtifactDeclaration(name=_DECL_A.name, sources=("a.md",), output=_DECL_A.output)
        changed = context_bundle.bundle_digest(_bundle(declarations=(changed_decl, _DECL_B)))
        assert baseline != changed

    def test_a_changed_layer_config_changes_the_digest(self):
        baseline = context_bundle.bundle_digest(_bundle())
        changed = context_bundle.bundle_digest(
            _bundle(derived_context_layer={"enabled": False, "aggressiveness": "medium"})
        )
        assert baseline != changed

    def test_digest_is_the_sha256_hex_of_the_canonical_sorted_key_json(self):
        bundle = _bundle()
        expected = hashlib.sha256(json.dumps(bundle, sort_keys=True).encode("utf-8")).hexdigest()
        assert context_bundle.bundle_digest(bundle) == expected


class TestDigestMismatchFinding:
    def test_code_severity_and_message_names_both_digests(self):
        finding = context_bundle.digest_mismatch_finding(epic="7", expected="a" * 64, computed="b" * 64)
        assert finding.code == "MRS-CTX-008"
        assert finding.severity is Severity.WARN
        assert "a" * 64 in finding.message
        assert "b" * 64 in finding.message
        assert "7" in finding.message

    def test_classifies_as_warn_and_never_blocks(self):
        finding = context_bundle.digest_mismatch_finding(epic="7", expected="a" * 64, computed="b" * 64)
        assert compute_verdict([finding]) is Verdict.WARN
