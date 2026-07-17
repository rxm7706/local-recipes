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
    capture_selector_comments,
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
    version `'# [linux]'` (verified live before the fix). Since Story 2.3,
    the trailing `# [linux]` is ALSO a real selector-comment capture (the
    line is still a `- <content>  # [<cond>]` list-item line even though
    its content is templated) -- correctly tagged `[sel:linux]` and
    escalated to UNION_MARKED (superseding 2.2's assumption that a
    selector comment has zero semantic effect on the component)."""
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
    assert component.extraction_mode is ExtractionMode.UNION_MARKED
    assert [p.section for p in component.provenance] == ["requirements.run[sel:linux]"]


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


# --- numeric {% set %} literals mirror jinja's own coercion (2026-07-16) -----


def test_numeric_set_literal_is_captured_as_jinja_would_render_it():
    """Jinja evaluates a numeric literal through Python int/float semantics
    and renders it via str(): `{% set version = 2.10 %}` renders '2.1', NOT
    the source spelling '2.10' (verified live against real jinja2 AND the
    conda-build renderer). Capturing the raw text used to report a
    confident exact version the real render disagrees with."""
    _, ctx = strip_jinja_statements(
        '{% set version = 2.10 %}{% set build = 3 %}{% set neg = -1.50 %}'
    )
    assert ctx == {"version": "2.1", "build": "3", "neg": "-1.5"}


def test_non_plain_numeric_set_rhs_is_not_captured():
    """Exponents, inf/nan (jinja NAMES, not literals), underscores, and
    leading `+` are all outside the plain-decimal shapes -- not captured,
    so their uses degrade rather than guess."""
    _, ctx = strip_jinja_statements(
        "{% set a = 1e3 %}{% set b = nan %}{% set c = 1_000 %}{% set d = +1.2 %}"
    )
    assert ctx == {}


def test_numeric_set_version_resolves_to_the_render_value(tmp_path):
    path = write_meta(
        tmp_path,
        "{% set version = 2.10 %}\n"
        "requirements:\n"
        "  run:\n"
        "    - otherpkg =={{ version }}\n",
    )
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "otherpkg"
    # '2.1' is what the real conda-build render emits for this document.
    assert component.version == "2.1"


# --- duplicate keys after {% if %}/{% else %} blanking (fixed 2026-07-16) ----


def test_duplicated_key_branches_fail_closed_never_silently_drop_one(tmp_path):
    """The classic v0 platform-conditional idiom duplicates a key across
    `{% if %}`/`{% else %}` branches; after statement blanking PyYAML's
    last-wins semantics silently kept ONLY the else branch -- `winpkg`
    produced no component at all: not NAME_ONLY, not RAW_MALFORMED, just
    gone (verified live before the fix). The strict loader now rejects the
    duplicate key: a typed whole-manifest error (never a silent
    false-green); real branch-union semantics are Story 2.3's control-flow
    work."""
    path = write_meta(
        tmp_path,
        "{% if win %}\n"
        "requirements:\n"
        "  run:\n"
        "    - winpkg ==1.0\n"
        "{% else %}\n"
        "requirements:\n"
        "  run:\n"
        "    - linuxpkg ==2.0\n"
        "{% endif %}\n",
    )
    with pytest.raises(UnparsableManifestError, match="duplicate mapping key"):
        _extractor().extract(path, MANIFEST)


def test_branch_entries_inside_one_list_still_union(tmp_path):
    """The same-list form (no duplicated keys) keeps its union behavior --
    the fail-closed guard above is scoped to the duplicate-KEY shape only."""
    path = write_meta(
        tmp_path,
        "requirements:\n"
        "  run:\n"
        "    - alwayspkg ==1.0\n"
        "{% if win %}\n"
        "    - winpkg ==1.0\n"
        "{% endif %}\n",
    )
    components = _extractor().extract(path, MANIFEST)
    assert {c.name for c in components} == {"alwayspkg", "winpkg"}


# --- Story 2.3: compiler()/stdlib()/pin_subpackage() build-tool exclude -------


def test_compiler_and_stdlib_calls_are_excluded_entirely(tmp_path):
    body = (
        "requirements:\n"
        "  build:\n"
        "    - {{ compiler('c') }}\n"
        "    - {{ stdlib('c') }}\n"
        "    - python\n"
    )
    path = write_meta(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "python"


def test_pin_subpackage_call_is_excluded_entirely(tmp_path):
    body = (
        '{% set name = "mypkg" %}\n'
        "requirements:\n"
        "  run:\n"
        "    - {{ pin_subpackage(name + '-core', exact=True) }}\n"
        "    - click\n"
    )
    path = write_meta(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "click"


def test_build_tool_call_sharing_a_line_with_unrelated_text_degrades(tmp_path):
    """The C0b silent-drop the `[^{}]*` regex fix closes: a SECOND,
    unrelated `{{ }}` expression sharing the line with a
    compiler()/stdlib()/pin_subpackage() call must NOT be swallowed whole
    by the exclude regex's `fullmatch` -- it falls through to the generic
    degrade ladder instead (kept, marked, never silently excluded)."""
    body = (
        "requirements:\n"
        "  build:\n"
        "    - {{ compiler('c') }} {{ pin_compatible('numpy') }}\n"
    )
    path = write_meta(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.extraction_mode is ExtractionMode.RAW_MALFORMED


# --- Story 2.3: `# [cond]` selector-comment union, line-number-correlated ----


def test_selector_comment_sibling_entries_are_unioned_and_tagged(tmp_path):
    body = (
        "requirements:\n"
        "  run:\n"
        "    - pywin32  # [win]\n"
        "    - unixlib  # [unix]\n"
    )
    path = write_meta(tmp_path, body)
    components = _extractor().extract(path, MANIFEST)
    tagged = {(c.name, c.provenance[0].section, c.extraction_mode) for c in components}
    assert tagged == {
        ("pywin32", "requirements.run[sel:win]", ExtractionMode.UNION_MARKED),
        ("unixlib", "requirements.run[sel:unix]", ExtractionMode.UNION_MARKED),
    }


def test_uncommented_occurrence_walked_before_commented_is_not_swapped(tmp_path):
    """THE exact review-pass-2 live-reproduced shape:
    `requirements.run: [helper, "helper  # [win]"]` -- an uncommented
    occurrence of the SAME dependency text, listed BEFORE a commented one,
    in the SAME list. The content-keyed FIFO-queue mechanism review pass 1
    shipped wrongly tagged the FIRST (uncommented) occurrence here (its
    queue held exactly one entry, and ANY lookup by that content popped it
    regardless of which occurrence actually carried the comment); the
    line-number mechanism has zero collision risk and must not swap.

    Asserted as an ORDERED list of per-entry (name, section, mode) tuples
    (document order) -- never a sorted()-over-section-strings comparison,
    which cannot detect a swapped attribution (the exact gap that let
    review pass 2's bug slip through a "passing" test)."""
    body = "requirements:\n  run:\n    - helper\n    - helper  # [win]\n"
    path = write_meta(tmp_path, body)
    components = _extractor().extract(path, MANIFEST)
    entries = [
        (c.name, c.provenance[0].section, c.extraction_mode) for c in components
    ]
    assert entries == [
        ("helper", "requirements.run", ExtractionMode.PARSED),
        ("helper", "requirements.run[sel:win]", ExtractionMode.UNION_MARKED),
    ]


def test_same_text_in_two_sections_is_correctly_attributed(tmp_path):
    body = (
        "requirements:\n"
        "  build:\n"
        "    - helper\n"
        "  run:\n"
        "    - helper  # [win]\n"
    )
    path = write_meta(tmp_path, body)
    components = _extractor().extract(path, MANIFEST)
    tagged = {(c.name, c.provenance[0].section, c.extraction_mode) for c in components}
    assert tagged == {
        ("helper", "requirements.build", ExtractionMode.PARSED),
        ("helper", "requirements.run[sel:win]", ExtractionMode.UNION_MARKED),
    }


def test_non_conventional_section_order_still_correctly_attributed(tmp_path):
    """`run:` physically BEFORE `build:` in the raw text (the WALK order is
    still the fixed ``(build, host, run)`` tuple, unaffected) -- proves
    line-based correlation, unlike FIFO, doesn't depend on walk order
    matching document order at all."""
    body = (
        "requirements:\n"
        "  run:\n"
        "    - helper  # [win]\n"
        "  build:\n"
        "    - helper\n"
    )
    path = write_meta(tmp_path, body)
    components = _extractor().extract(path, MANIFEST)
    tagged = {(c.name, c.provenance[0].section, c.extraction_mode) for c in components}
    assert tagged == {
        ("helper", "requirements.build", ExtractionMode.PARSED),
        ("helper", "requirements.run[sel:win]", ExtractionMode.UNION_MARKED),
    }


def test_duplicate_pre_comment_text_different_conditions_both_attributed(
    tmp_path,
):
    """Two DISTINCT source lines sharing identical dep text, each with its
    OWN `# [cond]` comment -- both correctly attributed by line number (no
    collision, no "last-wins" needed at all, unlike the superseded
    content-keyed mechanisms)."""
    body = (
        "requirements:\n"
        "  run:\n"
        "    - helper  # [win]\n"
        "    - helper  # [osx]\n"
    )
    path = write_meta(tmp_path, body)
    components = _extractor().extract(path, MANIFEST)
    tagged = {(c.name, c.provenance[0].section, c.extraction_mode) for c in components}
    assert tagged == {
        ("helper", "requirements.run[sel:win]", ExtractionMode.UNION_MARKED),
        ("helper", "requirements.run[sel:osx]", ExtractionMode.UNION_MARKED),
    }


def test_selector_comment_on_a_non_list_item_line_is_never_captured(tmp_path):
    """`skip: true  # [win]` -- a non-list-item line -- must NEVER be
    captured as a selector comment (Boundaries' own "Never" clause)."""
    body = (
        "build:\n"
        "  skip: true  # [win]\n"
        "requirements:\n"
        "  run:\n"
        "    - helper\n"
    )
    path = write_meta(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.extraction_mode is ExtractionMode.PARSED
    assert component.provenance[0].section == "requirements.run"


def test_capture_selector_comments_ignores_non_list_item_lines():
    comments = capture_selector_comments(
        "build:\n  skip: true  # [win]\nrequirements:\n  run:\n    - helper  # [unix]\n"
    )
    assert comments == {4: "unix"}


def test_capture_selector_comments_ignores_blank_bracket():
    """Review Pass 3 fix: a blank/whitespace-only bracket (`# []`, a
    plausible editing leftover) carries no real condition -- it must NOT
    be captured, since tagging it would produce a meaningless `[sel:]`
    suffix and wrongly escalate an otherwise-PARSED entry to
    UNION_MARKED for a distinction that doesn't exist."""
    comments = capture_selector_comments(
        "requirements:\n  run:\n    - helper  # []\n    - other  # [   ]\n"
    )
    assert comments == {}


def test_blank_selector_bracket_leaves_entry_untagged_parsed(tmp_path):
    body = "requirements:\n  run:\n    - helper  # []\n"
    path = write_meta(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.extraction_mode is ExtractionMode.PARSED
    assert component.provenance[0].section == "requirements.run"


def test_captured_condition_is_truncated_unconditionally(tmp_path):
    """The captured `# [cond]` text is bounded via `truncate_for_name`
    before being used in the `[sel:COND]` tag -- an arbitrarily long
    condition must never embed unbounded into `Provenance.section`
    (NFR-S5; mirrors recipe_v1.py's identical `if:` condition bound)."""
    long_condition = "x" * 500
    body = f"requirements:\n  run:\n    - helper  # [{long_condition}]\n"
    path = write_meta(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    section = component.provenance[0].section
    assert len(section) < 300
    assert section.endswith("…[truncated]]")


def test_deeply_nested_yaml_raises_unparsable_not_a_crash(tmp_path):
    """v0 has no recursive WALKER of its own (that construct is v1-only),
    but the shared RecursionError guard must still hold for a
    pathologically nested (but well within the 5MB manifest cap) YAML
    document -- never a raw crash (Story 2.3, Review Pass 1 correction #2,
    mirrored onto meta_v0.py's own extract())."""
    depth = 3000
    nested = "[" * depth + "1" + "]" * depth
    body = f"requirements:\n  run: []\nextra:\n  value: {nested}\n"
    path = write_meta(tmp_path, body)
    with pytest.raises(UnparsableManifestError):
        _extractor().extract(path, MANIFEST)
