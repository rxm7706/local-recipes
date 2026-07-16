"""Unit tests — ``extract/meta_v0.py``'s I/O-matrix rows (Story 2.2):
``MetaV0Extractor`` exercised directly, no CLI.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.warden.discovery import META_YAML_KIND
from pyforge.warden.extract import UnparsableManifestError
from pyforge.warden.extract import meta_v0
from pyforge.warden.extract.meta_v0 import (
    META_V0_REQUIREMENTS_SECTION,
    MetaV0Extractor,
    neutralize_unquoted_braces,
    strip_jinja_statements,
)
from pyforge.warden.models import Ecosystem, ExtractionMode, ScannedManifest
from pyforge.warden.routing import DefaultRouter

FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "projects"
    / "meta_common"
    / "meta.yaml"
)
MANIFEST = ScannedManifest(path="meta.yaml", kind=META_YAML_KIND)


def _extractor() -> MetaV0Extractor:
    return MetaV0Extractor(DefaultRouter())


def write_meta(directory: Path, body: str) -> Path:
    path = directory / "meta.yaml"
    path.write_text(body, encoding="utf-8")
    return path


# --- common-case fixture (I/O matrix row) -------------------------------------


def test_common_case_fixture_extracts_literal_and_set_resolved_deps():
    components = _extractor().extract(FIXTURE, MANIFEST)
    by_name = {c.name: c for c in components}

    assert by_name["python"].version is None
    assert by_name["python"].extraction_mode is ExtractionMode.PARSED

    # {% set version = "1.2.3" %} substituted into `otherpkg {{ version }}`.
    otherpkg = by_name["otherpkg"]
    assert otherpkg.version == "1.2.3"
    assert otherpkg.ecosystem is Ecosystem.CONDA
    assert otherpkg.extraction_mode is ExtractionMode.PARSED

    # test.requires (v0's singular flat list).
    assert "pytest" in by_name
    assert [p.section for p in by_name["pytest"].provenance] == ["test.requires"]


def test_run_constrained_is_excluded_entirely():
    components = _extractor().extract(FIXTURE, MANIFEST)
    names = {c.name for c in components}
    assert "scipy" not in names


# --- {% set %} capture + neutralization ---------------------------------------


def test_strip_jinja_statements_captures_quoted_and_numeric_literals():
    text = (
        '{% set version = "1.2.3" %}\n'
        "{% set build_number = 0 %}\n"
        "requirements:\n"
        "  run: []\n"
    )
    stripped, context = strip_jinja_statements(text)
    assert context == {"version": "1.2.3", "build_number": "0"}
    assert "{%" not in stripped


def test_strip_jinja_statements_blanks_non_set_control_flow_lines():
    text = (
        "{% if linux %}\n"
        "requirements:\n"
        "  run:\n"
        "    - python\n"
        "{% endif %}\n"
    )
    stripped, context = strip_jinja_statements(text)
    assert context == {}
    assert "{%" not in stripped
    assert "requirements:" in stripped


def test_strip_jinja_statements_does_not_capture_a_function_call_rhs():
    text = '{% set version = load_setup_py_data()["version"] %}\n'
    stripped, context = strip_jinja_statements(text)
    assert context == {}  # not a bare literal -- not captured
    assert "{%" not in stripped  # but still blanked, never reaches yaml


# --- Fixes 1 + 3 (2026-07-16 review): {# comments #} + same-line multi-set --


def test_strip_jinja_statements_strips_a_bare_comment():
    text = "{# a comment #}\nrequirements:\n  run: []\n"
    stripped, context = strip_jinja_statements(text)
    assert context == {}
    assert "{#" not in stripped
    assert "requirements:" in stripped


def test_jinja_comment_line_never_breaks_yaml_parse(tmp_path):
    """Fix 1: a bare `{# comment #}` line used to crash the WHOLE
    document's yaml.safe_load (a flow-mapping misparse) -- neither
    `_SET_LINE_RE` nor the old `_JINJA_STATEMENT_LINE_RE` recognized it."""
    body = (
        "{# a comment #}\n"
        "requirements:\n"
        "  run:\n"
        "    - python\n"
    )
    path = write_meta(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "python"


def test_strip_jinja_statements_captures_both_set_tags_sharing_one_line():
    """Fix 3: two `{% set %}` tags on ONE line -- the old `^...$`-anchored
    regex only matched (or captured) the first, losing the second variable
    or leaving garbled leftover delimiter text. Both must be captured."""
    text = (
        '{% set a = "x" %}{% set b = "y" %}\n'
        "requirements:\n"
        "  run: []\n"
    )
    stripped, context = strip_jinja_statements(text)
    assert context == {"a": "x", "b": "y"}
    assert "{%" not in stripped
    assert "%}" not in stripped


def test_strip_jinja_statements_blanks_a_set_tag_sharing_a_line_with_a_comment():
    """Fix 3: a `{% set %}` tag sharing a line with trailing content (here a
    plain YAML comment) was previously never blanked at all (the old regex
    required the WHOLE line to be exactly one tag) -- it must still be
    captured and blanked, leaving the trailing content intact."""
    text = '{% set a = "x" %}  # trailing note\nrequirements:\n  run: []\n'
    stripped, context = strip_jinja_statements(text)
    assert context == {"a": "x"}
    assert "{%" not in stripped
    assert "# trailing note" in stripped


def test_multi_set_per_line_fixture_resolves_both_variables(tmp_path):
    """End-to-end: both variables from a same-line multi-set are correctly
    substituted into their respective dependencies, not silently dropped."""
    body = (
        '{% set name = "otherpkg" %}{% set version = "1.2.3" %}\n'
        "requirements:\n"
        "  run:\n"
        "    - {{ name }} {{ version }}\n"
    )
    path = write_meta(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "otherpkg"
    assert component.version == "1.2.3"


def test_neutralize_unquoted_braces_quotes_a_bare_list_item():
    text = "run:\n  - {{ pin_compatible('numpy') }}\n  - numpy >=1.20\n"
    neutralized = neutralize_unquoted_braces(text)
    assert "- '{{ pin_compatible(''numpy'') }}'" in neutralized
    assert "- numpy >=1.20" in neutralized  # untouched: doesn't start with {{


def test_unquoted_brace_list_item_never_breaks_yaml_parse(tmp_path):
    """The YAML-breaking case: an unquoted `{{ ... }}` list item would
    misparse as flow-mapping syntax if left as-is -- neutralization must
    make the whole document parse successfully, degrading only that ONE
    entry."""
    body = (
        "requirements:\n"
        "  run:\n"
        "    - python\n"
        "    - {{ pin_compatible('numpy') }}\n"
    )
    path = write_meta(tmp_path, body)
    components = _extractor().extract(path, MANIFEST)
    by_name = {c.name: c for c in components}
    assert "python" in by_name
    malformed = by_name["{{ pin_compatible('numpy') }}"]
    assert malformed.extraction_mode is ExtractionMode.RAW_MALFORMED


# --- unresolvable / degraded constructs ---------------------------------------


def test_unresolvable_expression_with_recoverable_name_degrades_to_name_only(
    tmp_path,
):
    body = (
        '{% set version = "1.2.3" %}\n'
        "requirements:\n"
        "  run:\n"
        "    - numpy {{ version.replace('.', '_') }}\n"
    )
    path = write_meta(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "numpy"
    assert component.version is None
    assert component.extraction_mode is ExtractionMode.NAME_ONLY


# --- structural (whole-manifest) failures -------------------------------------


def test_document_none_yields_no_components(tmp_path):
    path = write_meta(tmp_path, "")
    assert _extractor().extract(path, MANIFEST) == ()


def test_non_mapping_document_raises_unparsable(tmp_path):
    path = write_meta(tmp_path, "- just\n- a\n- list\n")
    with pytest.raises(UnparsableManifestError):
        _extractor().extract(path, MANIFEST)


def test_malformed_yaml_raises_unparsable(tmp_path):
    path = write_meta(tmp_path, "requirements: [\n  - broken\n")
    with pytest.raises(UnparsableManifestError):
        _extractor().extract(path, MANIFEST)


def test_missing_requirements_key_yields_no_components(tmp_path):
    path = write_meta(tmp_path, "package:\n  name: mypkg\n")
    assert _extractor().extract(path, MANIFEST) == ()


# --- multi-output ---------------------------------------------------------------


def test_outputs_are_walked_with_indexed_provenance(tmp_path):
    body = (
        "outputs:\n"
        "  - name: sub-a\n"
        "    requirements:\n"
        "      run:\n"
        "        - click\n"
    )
    path = write_meta(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "click"
    assert [p.section for p in component.provenance] == [
        "outputs[0].requirements.run"
    ]


# --- NFR-S5 bounds -------------------------------------------------------------


def test_oversized_manifest_raises_unparsable(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_v0, "_MAX_MANIFEST_BYTES", 32)
    path = write_meta(tmp_path, "requirements:\n  run: []\n# padding padding\n")
    with pytest.raises(UnparsableManifestError, match="size cap"):
        _extractor().extract(path, MANIFEST)


def test_oversized_line_raises_unparsable(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_v0, "_MAX_LINE_BYTES", 16)
    path = write_meta(tmp_path, "requirements:\n  run: []\n# " + ("x" * 32) + "\n")
    with pytest.raises(UnparsableManifestError, match="length cap"):
        _extractor().extract(path, MANIFEST)


def test_manifest_within_bounds_still_parses(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_v0, "_MAX_MANIFEST_BYTES", 10_000)
    monkeypatch.setattr(meta_v0, "_MAX_LINE_BYTES", 500)
    path = write_meta(tmp_path, "requirements:\n  run: []\n")
    assert _extractor().extract(path, MANIFEST) == ()


# --- routing ---------------------------------------------------------------


def test_router_routes_meta_v0_requirements_to_conda():
    ecosystem = DefaultRouter().route(META_YAML_KIND, META_V0_REQUIREMENTS_SECTION)
    assert ecosystem is Ecosystem.CONDA


# --- follow-up review (2026-07-16) -------------------------------------------


def test_conditional_expression_set_rhs_is_never_captured_as_a_literal():
    """`{% set version = "1.0" if unix else "2.0" %}` starts AND ends with a
    quote, so the old first-char==last-char check captured the raw interior
    (`1.0" if unix else "2.0`) as a "resolved literal" -- a corrupted value
    silently reported as a PARSED exact version (verified live before the
    fix). A conditional expression is not a bare literal: it must degrade."""
    _, context = strip_jinja_statements(
        '{% set version = "1.0" if unix else "2.0" %}\n'
    )
    assert context == {}


def test_a_reassigned_set_name_is_ambiguous_and_degrades_its_uses(tmp_path):
    """Two `{% set version %}` tags under `{% if %}`/`{% else %}` branches
    used to collapse last-wins, confidently reporting the wrong branch's
    value as PARSED (verified live before the fix). This parse-as-data
    module never evaluates control flow (Story 2.3 owns it), so a
    re-assigned name is dropped from the context and its uses degrade."""
    body = (
        "{% if win %}\n"
        '{% set version = "1.0.0" %}\n'
        "{% else %}\n"
        '{% set version = "2.0.0" %}\n'
        "{% endif %}\n"
        "requirements:\n"
        "  run:\n"
        "    - otherpkg =={{ version }}\n"
    )
    path = write_meta(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "otherpkg"
    assert component.version is None
    assert component.extraction_mode is ExtractionMode.NAME_ONLY


def test_a_singly_set_name_still_resolves(tmp_path):
    body = (
        '{% set version = "1.2.3" %}\n'
        "requirements:\n"
        "  run:\n"
        "    - otherpkg =={{ version }}\n"
    )
    path = write_meta(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.version == "1.2.3"
    assert component.extraction_mode is ExtractionMode.PARSED


def test_selector_comment_on_a_templated_dep_line_never_becomes_a_version(
    tmp_path,
):
    """`- {{ nv }}  # [linux]` -- the defensive quoting used to swallow the
    selector comment INTO the quoted string (YAML can no longer strip what
    is inside quotes), so the component came back with the corrupted EXACT
    version `'# [linux]'` (verified live before the fix)."""
    body = (
        '{% set nv = "numpy" %}\n'
        "requirements:\n"
        "  run:\n"
        "    - {{ nv }}  # [linux]\n"
    )
    path = write_meta(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "numpy"
    assert component.version is None
    assert component.extraction_mode is ExtractionMode.PARSED


def test_per_output_test_requires_is_walked(tmp_path):
    """`outputs[].test.requires` (the multi-output analog of the top-level
    singular `test.requires`) used to produce no components at all while
    its top-level twin was walked."""
    body = (
        "outputs:\n"
        "  - name: sub-a\n"
        "    test:\n"
        "      requires:\n"
        "        - pytest\n"
    )
    path = write_meta(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "pytest"
    assert [p.section for p in component.provenance] == [
        "outputs[0].test.requires"
    ]
