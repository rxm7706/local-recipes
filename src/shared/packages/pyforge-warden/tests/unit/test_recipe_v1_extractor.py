"""Unit tests — ``extract/recipe_v1.py``'s I/O-matrix rows (Story 2.2):
``RecipeV1Extractor`` exercised directly, no CLI.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.warden.discovery import RECIPE_YAML_KIND
from pyforge.warden.extract import UnparsableManifestError
from pyforge.warden.extract import recipe_v1
from pyforge.warden.extract.recipe_v1 import (
    RECIPE_V1_REQUIREMENTS_SECTION,
    RecipeV1Extractor,
    best_effort_name,
    context_map,
    neutralize_bare_braces,
    strip_jinja_comments,
    substitute_bare_vars,
)
from pyforge.warden.models import (
    Ecosystem,
    ExtractionMode,
    ScannedManifest,
    WithholdReason,
)
from pyforge.warden.routing import DefaultRouter

FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "projects"
    / "recipe_common"
    / "recipe.yaml"
)
MANIFEST = ScannedManifest(path="recipe.yaml", kind=RECIPE_YAML_KIND)


def _extractor() -> RecipeV1Extractor:
    return RecipeV1Extractor(DefaultRouter())


def write_recipe(directory: Path, body: str) -> Path:
    path = directory / "recipe.yaml"
    path.write_text(body, encoding="utf-8")
    return path


# --- common-case fixture (I/O matrix row 1) -----------------------------------


def test_common_case_fixture_extracts_literal_and_context_resolved_deps():
    components = _extractor().extract(FIXTURE, MANIFEST)
    by_name = {c.name: c for c in components}

    # Literal, unversioned run dep.
    assert by_name["python"].version is None
    assert by_name["python"].extraction_mode is ExtractionMode.PARSED

    # Literal, range-only run dep (never a guessed exact version). numpy is
    # a verified-map hit in the real bundled map, so `_conda_component`'s
    # own (pre-2.2, unchanged) trusted branch reports `no-version` here
    # rather than `range-only` -- either way, withheld and never matchable.
    assert by_name["numpy"].version is None
    assert by_name["numpy"].vuln_matchable is False
    assert by_name["numpy"].indeterminate_reason in (
        WithholdReason.RANGE_ONLY,
        WithholdReason.UNMAPPED_ECOSYSTEM,
        WithholdReason.NO_VERSION,
    )

    # Context-var-resolved exact-pin run dep: ${{ name }} ==${{ version }}.
    mypkg = by_name["mypkg"]
    assert mypkg.version == "1.2.3"
    assert mypkg.ecosystem is Ecosystem.CONDA
    assert mypkg.extraction_mode is ExtractionMode.PARSED

    # tests[0].requirements.run.
    assert "pytest" in by_name
    pytest_provenance = [p.section for p in by_name["pytest"].provenance]
    assert pytest_provenance == ["tests[0].requirements.run"]


def test_run_constraints_are_excluded_entirely():
    components = _extractor().extract(FIXTURE, MANIFEST)
    names = {c.name for c in components}
    assert "scipy" not in names


def test_provenance_sections_are_specific_per_requirements_block():
    components = _extractor().extract(FIXTURE, MANIFEST)
    by_name = {c.name: c for c in components}
    assert [p.section for p in by_name["pip"].provenance] == ["requirements.host"]
    assert [p.section for p in by_name["mypkg"].provenance] == ["requirements.run"]


# --- bare-token substitution ---------------------------------------------------


def test_substitute_bare_vars_resolves_dollar_prefixed_and_bare_forms():
    context = {"name": "mypkg", "version": "1.2.3"}
    assert substitute_bare_vars("${{ name }}", context) == "mypkg"
    assert substitute_bare_vars("{{ version }}", context) == "1.2.3"
    assert substitute_bare_vars("${{ name }} ${{ version }}", context) == (
        "mypkg 1.2.3"
    )


def test_substitute_bare_vars_leaves_unknown_var_untouched():
    assert substitute_bare_vars("${{ unknown }}", {}) == "${{ unknown }}"


def test_substitute_bare_vars_never_resolves_a_filter_or_expression():
    """A filter/expression construct structurally can't match the bare-var
    regex -- left untouched, never partially evaluated."""
    context = {"version": "1.2.3"}
    raw = "${{ version.replace('.', '_') }}"
    assert substitute_bare_vars(raw, context) == raw


def test_best_effort_name_scrapes_the_prefix_before_the_marker():
    assert best_effort_name("numpy ${{ version.replace('.','_') }}") == "numpy"
    assert best_effort_name("${{ pin_compatible('numpy') }}") is None
    assert best_effort_name("   ") is None


def test_best_effort_name_strips_trailing_operator_debris():
    """`python >=${{ python_min }}` is the canonical conda-forge templated
    pin (`python_min` is a variant variable, never in `context:`) -- the
    whole prefix used to become a component literally named `'python >='`,
    a garbage token that can never hit the conda->pypi map (verified live
    before the fix). The name is the first token with operator debris
    stripped."""
    assert best_effort_name("python >=${{ python_min }}") == "python"
    assert best_effort_name("numpy>=${{ v }}") == "numpy"
    assert best_effort_name("numpy <${{ v }}") == "numpy"
    assert best_effort_name("numpy 1.2.${{ v }}") == "numpy"
    assert best_effort_name(">=${{ v }}") is None


def test_context_map_excludes_non_scalar_and_bool_values():
    document = {
        "context": {
            "name": "mypkg",
            "version": "1.2.3",
            "build_number": 0,
            "is_extra": True,
            "extra_list": ["a", "b"],
            "extra_map": {"k": "v"},
        }
    }
    ctx = context_map(document)
    assert ctx == {"name": "mypkg", "version": "1.2.3", "build_number": "0"}


def test_context_map_absent_or_wrong_type_yields_empty():
    assert context_map({}) == {}
    assert context_map({"context": "not-a-mapping"}) == {}


# --- Fixes 1 + 2 (2026-07-16 review): {# comments #} + bare {{ }} braces -----


def test_strip_jinja_comments_strips_a_bare_comment():
    text = "{# a comment #}\nrequirements:\n  run: []\n"
    stripped = strip_jinja_comments(text)
    assert "{#" not in stripped
    assert "requirements:" in stripped


def test_jinja_comment_line_never_breaks_yaml_parse(tmp_path):
    """Fix 1: recipe_v1.py ran NO neutralize pass at all before this fix, so
    a bare `{# comment #}` line crashed the WHOLE document's yaml.safe_load
    (a flow-mapping misparse) exactly like meta_v0.py's identical bug."""
    body = "{# a comment #}\nrequirements:\n  run:\n    - python\n"
    path = write_recipe(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "python"


def test_neutralize_bare_braces_quotes_a_bare_list_item():
    text = "run:\n  - {{ name }}\n  - numpy >=1.20\n"
    neutralized = neutralize_bare_braces(text)
    assert "- '{{ name }}'" in neutralized
    assert "- numpy >=1.20" in neutralized  # untouched: doesn't start with {{


def test_neutralize_bare_braces_leaves_a_dollar_prefixed_scalar_untouched():
    """v1's own valid syntax (`${{ VAR }}`) is already a safely-parseable
    plain scalar (starts with `$`, not `{`) -- neutralize_bare_braces must
    never touch it."""
    text = "run:\n  - ${{ name }}\n"
    assert neutralize_bare_braces(text) == text


def test_bare_brace_list_item_never_breaks_yaml_parse_and_still_resolves(
    tmp_path,
):
    """Fix 2: recipe.yaml's documented v1 syntax is `${{ VAR }}` (the
    `$`-prefixed form); a bare (un-`$`-prefixed) `{{ VAR }}` used to crash
    the WHOLE document's yaml.safe_load. `_BARE_VAR_RE`'s optional `$`
    prefix already treats the bare form as an equally detectable
    substitution target once the document parses (shared with v0), so a
    KNOWN context var still resolves correctly -- never a crash, and not
    even necessarily a degrade."""
    body = (
        "context:\n"
        "  name: mypkg\n"
        "requirements:\n"
        "  run:\n"
        "    - python\n"
        "    - {{ name }}\n"
    )
    path = write_recipe(tmp_path, body)
    components = _extractor().extract(path, MANIFEST)
    by_name = {c.name: c for c in components}
    assert "python" in by_name
    mypkg = by_name["mypkg"]
    assert mypkg.extraction_mode is ExtractionMode.PARSED


def test_bare_brace_unresolvable_construct_is_raw_malformed(tmp_path):
    """The bare-brace counterpart of
    test_unresolvable_expression_with_no_recoverable_name_is_raw_malformed:
    an unresolvable construct behind a BARE `{{ }}` still degrades
    gracefully (never crashes, never guesses) once neutralization lets the
    document parse at all."""
    body = "requirements:\n  run:\n    - {{ pin_compatible('numpy') }}\n"
    path = write_recipe(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.extraction_mode is ExtractionMode.RAW_MALFORMED
    assert component.name == "{{ pin_compatible('numpy') }}"
    assert component.vuln_matchable is False


# --- unresolvable / degraded constructs (I/O matrix row) ----------------------


def test_unresolvable_expression_with_recoverable_name_degrades_to_name_only(
    tmp_path,
):
    body = (
        "context:\n"
        '  version: "1.2.3"\n'
        "requirements:\n"
        "  run:\n"
        "    - numpy ${{ version.replace('.', '_') }}\n"
    )
    path = write_recipe(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "numpy"
    assert component.version is None
    assert component.extraction_mode is ExtractionMode.NAME_ONLY


def test_unresolvable_expression_with_no_recoverable_name_is_raw_malformed(
    tmp_path,
):
    body = (
        "requirements:\n"
        "  run:\n"
        "    - ${{ pin_compatible('scipy') }}\n"
    )
    path = write_recipe(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.extraction_mode is ExtractionMode.RAW_MALFORMED
    assert component.name == "${{ pin_compatible('scipy') }}"
    assert component.vuln_matchable is False


def test_non_string_requirement_entry_is_raw_malformed(tmp_path):
    body = "requirements:\n  run:\n    - 42\n"
    path = write_recipe(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.extraction_mode is ExtractionMode.RAW_MALFORMED
    assert component.name == "42"


# --- structural (whole-manifest) failures -------------------------------------


def test_document_none_yields_no_components(tmp_path):
    path = write_recipe(tmp_path, "")
    assert _extractor().extract(path, MANIFEST) == ()


def test_non_mapping_document_raises_unparsable(tmp_path):
    path = write_recipe(tmp_path, "- just\n- a\n- list\n")
    with pytest.raises(UnparsableManifestError):
        _extractor().extract(path, MANIFEST)


def test_malformed_yaml_raises_unparsable(tmp_path):
    path = write_recipe(tmp_path, "requirements: [\n  - broken\n")
    with pytest.raises(UnparsableManifestError):
        _extractor().extract(path, MANIFEST)


def test_missing_requirements_key_yields_no_components(tmp_path):
    path = write_recipe(tmp_path, "package:\n  name: mypkg\n")
    assert _extractor().extract(path, MANIFEST) == ()


def test_requirements_non_dict_degrades_to_nothing_here(tmp_path):
    """2.2 only guarantees no-crash behavior for what it doesn't recognize
    (Story 2.3 owns the full construct matrix) -- a structurally odd
    requirements shape yields zero components rather than crashing."""
    path = write_recipe(tmp_path, "requirements: not-a-mapping\n")
    assert _extractor().extract(path, MANIFEST) == ()


# --- multi-output ---------------------------------------------------------------


def test_outputs_are_walked_with_indexed_provenance(tmp_path):
    body = (
        "outputs:\n"
        "  - package:\n"
        "      name: sub-a\n"
        "    requirements:\n"
        "      run:\n"
        "        - click\n"
        "  - package:\n"
        "      name: sub-b\n"
        "    requirements:\n"
        "      run:\n"
        "        - rich\n"
    )
    path = write_recipe(tmp_path, body)
    components = _extractor().extract(path, MANIFEST)
    by_name = {c.name: c for c in components}
    assert set(by_name) == {"click", "rich"}
    assert [p.section for p in by_name["click"].provenance] == [
        "outputs[0].requirements.run"
    ]
    assert [p.section for p in by_name["rich"].provenance] == [
        "outputs[1].requirements.run"
    ]


def test_outputs_run_constraints_are_excluded(tmp_path):
    body = (
        "outputs:\n"
        "  - package:\n"
        "      name: sub-a\n"
        "    requirements:\n"
        "      run:\n"
        "        - click\n"
        "      run_constraints:\n"
        "        - scipy >=1.0\n"
    )
    path = write_recipe(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "click"


# --- NFR-S5 bounds -------------------------------------------------------------


def test_oversized_manifest_raises_unparsable(tmp_path, monkeypatch):
    monkeypatch.setattr(recipe_v1, "_MAX_MANIFEST_BYTES", 32)
    path = write_recipe(tmp_path, "requirements:\n  run: []\n# padding padding\n")
    with pytest.raises(UnparsableManifestError, match="size cap"):
        _extractor().extract(path, MANIFEST)


def test_oversized_line_raises_unparsable(tmp_path, monkeypatch):
    monkeypatch.setattr(recipe_v1, "_MAX_LINE_BYTES", 16)
    path = write_recipe(
        tmp_path, "requirements:\n  run: []\n# " + ("x" * 32) + "\n"
    )
    with pytest.raises(UnparsableManifestError, match="length cap"):
        _extractor().extract(path, MANIFEST)


def test_manifest_within_bounds_still_parses(tmp_path, monkeypatch):
    monkeypatch.setattr(recipe_v1, "_MAX_MANIFEST_BYTES", 10_000)
    monkeypatch.setattr(recipe_v1, "_MAX_LINE_BYTES", 500)
    path = write_recipe(tmp_path, "requirements:\n  run: []\n")
    assert _extractor().extract(path, MANIFEST) == ()


# --- routing ---------------------------------------------------------------


# --- follow-up review (2026-07-16) -------------------------------------------


def test_canonical_python_min_pin_degrades_to_a_usable_python_name(tmp_path):
    """End-to-end: the fleet's most common templated shape (`python >=${{
    python_min }}`) must yield a NAME_ONLY component named `python`, never
    `'python >='`."""
    body = (
        "requirements:\n"
        "  run:\n"
        "    - python >=${{ python_min }}\n"
    )
    path = write_recipe(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "python"
    assert component.version is None
    assert component.extraction_mode is ExtractionMode.NAME_ONLY


def test_range_specifier_withholds_as_range_only_not_no_version(tmp_path):
    """`classify_conda_specifier`'s computed withhold reason used to be
    discarded at every conda call site, so a range-declared dep dishonestly
    reported `no-version` (RANGE_ONLY was unreachable for conda
    components)."""
    body = (
        "requirements:\n"
        "  run:\n"
        "    - numpy >=1.20\n"
    )
    path = write_recipe(tmp_path, body)
    (ranged,) = _extractor().extract(path, MANIFEST)
    assert ranged.indeterminate_reason is WithholdReason.RANGE_ONLY

    # A genuinely bare dep (same verified-mapped name, so UNMAPPED
    # precedence doesn't mask the version reason) still reports NO_VERSION.
    path = write_recipe(tmp_path, "requirements:\n  run:\n    - numpy\n")
    (bare,) = _extractor().extract(path, MANIFEST)
    assert bare.indeterminate_reason is WithholdReason.NO_VERSION


def test_selector_comment_on_a_bare_brace_line_never_becomes_a_version(
    tmp_path,
):
    """The defensive quoting of a bare `{{ ... }}` line used to swallow a
    trailing selector comment INTO the quoted string -- mirrors
    `meta_v0.py`'s identical fix (2026-07-16)."""
    body = (
        "context:\n"
        "  nv: numpy\n"
        "requirements:\n"
        "  run:\n"
        "    - {{ nv }}  # [linux]\n"
    )
    path = write_recipe(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "numpy"
    assert component.version is None


def test_per_output_tests_are_walked(tmp_path):
    """`outputs[].tests[]` (the multi-output analog of the top-level
    `tests[]`) used to produce no components at all while its top-level
    twin was walked."""
    body = (
        "outputs:\n"
        "  - package:\n"
        "      name: sub-a\n"
        "    tests:\n"
        "      - requirements:\n"
        "          run:\n"
        "            - pytest\n"
    )
    path = write_recipe(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "pytest"
    assert [p.section for p in component.provenance] == [
        "outputs[0].tests[0].requirements.run"
    ]


def test_router_routes_recipe_v1_requirements_to_conda():
    ecosystem = DefaultRouter().route(RECIPE_YAML_KIND, RECIPE_V1_REQUIREMENTS_SECTION)
    assert ecosystem is Ecosystem.CONDA


# --- float-typed context values (fixed 2026-07-16) ---------------------------


def test_context_map_drops_float_values():
    """YAML has already destroyed the source spelling by the time
    `context_map` runs (`version: 1.20` parses as the float 1.2), while the
    real rattler-build renderer preserves the raw text (verified live: the
    identical document renders `==1.20`) -- so `str(value)` fabricated a
    confidently-wrong exact version (`'1.2'`) and fed it to CVE matching.
    Floats are now excluded from capture; integers round-trip and stay."""
    ctx = context_map({"context": {"version": 1.20, "python_min": 3.10, "n": 1}})
    assert ctx == {"n": "1"}


def test_float_context_use_degrades_to_name_only_never_a_wrong_version(
    tmp_path,
):
    path = write_recipe(
        tmp_path,
        "context:\n"
        "  version: 1.20\n"
        "requirements:\n"
        "  run:\n"
        "    - otherpkg ==${{ version }}\n",
    )
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "otherpkg"
    assert component.version is None
    assert component.extraction_mode is ExtractionMode.NAME_ONLY


# --- a marker abutting the name token itself (fixed 2026-07-16) ---------------


def test_best_effort_name_returns_none_when_the_marker_abuts_the_name():
    """`mypkg-data-${{ version }}` is a templated-SUFFIX name: the pre-marker
    text used to become a component literally named `mypkg-data-` -- an
    impossible conda name presented as a plausible component (and stripping
    further would fabricate a DIFFERENT package's identity). The entry
    degrades to RAW_MALFORMED instead."""
    assert best_effort_name("mypkg-data-${{ version }}") is None
    assert best_effort_name("mypkg.${{ ver }}") is None
    # Operator-abutting and whitespace-separated forms keep their clean name.
    assert best_effort_name("numpy>=${{ v }}") == "numpy"
    assert best_effort_name("python >=${{ python_min }}") == "python"


def test_templated_suffix_name_degrades_to_raw_malformed(tmp_path):
    path = write_recipe(
        tmp_path,
        "requirements:\n  run:\n    - mypkg-data-${{ version }}\n",
    )
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.extraction_mode is ExtractionMode.RAW_MALFORMED


# --- Story 2.3: compiler()/stdlib()/pin_subpackage() build-tool exclude -------


def test_compiler_and_stdlib_calls_are_excluded_entirely(tmp_path):
    body = (
        "requirements:\n"
        "  build:\n"
        '    - ${{ compiler("c") }}\n'
        '    - ${{ stdlib("c") }}\n'
        "    - python\n"
    )
    path = write_recipe(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "python"


def test_pin_subpackage_call_is_excluded_entirely(tmp_path):
    body = (
        "context:\n"
        "  name: mypkg\n"
        "requirements:\n"
        "  run:\n"
        '    - ${{ pin_subpackage(name + "-core", exact=True) }}\n'
        "    - click\n"
    )
    path = write_recipe(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "click"


def test_build_tool_call_sharing_a_line_with_unrelated_text_degrades(tmp_path):
    """The C0b silent-drop the `[^{}]*` regex fix closes: a SECOND,
    unrelated `${{ }}` expression sharing the line with a
    compiler()/stdlib()/pin_subpackage() call must NOT be swallowed whole
    by the exclude regex's `fullmatch` -- it falls through to the generic
    degrade ladder instead (kept, marked, never silently excluded)."""
    body = (
        "requirements:\n"
        "  build:\n"
        '    - ${{ compiler("c") }} ${{ pin_compatible("numpy") }}\n'
    )
    path = write_recipe(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.extraction_mode is ExtractionMode.RAW_MALFORMED


# --- Story 2.3: if/then/else selector-union -----------------------------------


def test_if_then_else_both_branches_are_unioned_and_tagged(tmp_path):
    body = (
        "requirements:\n"
        "  run:\n"
        "    - if: linux\n"
        "      then:\n"
        "        - numpy >=1.20\n"
        "      else:\n"
        "        - numpy\n"
    )
    path = write_recipe(tmp_path, body)
    components = _extractor().extract(path, MANIFEST)
    # Per-entry (name, section, mode) tuples -- never a sorted()-over-
    # section-strings comparison, which cannot detect a swapped attribution
    # (the exact review-pass-2 test-quality fix, applied here too even
    # though v1's condition never comes from comment-correlation).
    tagged = {(c.name, c.provenance[0].section, c.extraction_mode) for c in components}
    assert tagged == {
        ("numpy", "requirements.run[if:linux]", ExtractionMode.UNION_MARKED),
        ("numpy", "requirements.run[else:linux]", ExtractionMode.UNION_MARKED),
    }


def test_if_then_scalar_form_without_else_contributes_only_then(tmp_path):
    """Real v1 syntax allows a single scalar `then` with no `else` at all
    (e.g. conda-forge's actionlint recipe: `if: win / then: posix`) --
    ordinary, valid, and must contribute exactly the `then` side, nothing
    for the absent `else`."""
    body = "requirements:\n  run:\n    - if: win\n      then: posix\n"
    path = write_recipe(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "posix"
    assert component.provenance[0].section == "requirements.run[if:win]"
    assert component.extraction_mode is ExtractionMode.UNION_MARKED


def test_nested_if_inside_then_concatenates_section_tags(tmp_path):
    body = (
        "requirements:\n"
        "  run:\n"
        "    - if: linux\n"
        "      then:\n"
        "        - if: x86_64\n"
        "          then:\n"
        "            - numpydeep\n"
        "          else:\n"
        "            - numpydeep-generic\n"
        "      else:\n"
        "        - numpylin\n"
    )
    path = write_recipe(tmp_path, body)
    components = _extractor().extract(path, MANIFEST)
    tagged = {(c.name, c.provenance[0].section) for c in components}
    assert tagged == {
        ("numpydeep", "requirements.run[if:linux][if:x86_64]"),
        ("numpydeep-generic", "requirements.run[if:linux][else:x86_64]"),
        ("numpylin", "requirements.run[else:linux]"),
    }


def test_build_tool_call_inside_if_then_else_branch_is_excluded(tmp_path):
    body = (
        "requirements:\n"
        "  build:\n"
        "    - if: linux\n"
        "      then:\n"
        '        - ${{ compiler("c") }}\n'
        "      else:\n"
        "        - clang\n"
    )
    path = write_recipe(tmp_path, body)
    components = _extractor().extract(path, MANIFEST)
    assert {c.name for c in components} == {"clang"}


def test_degraded_leaf_inside_if_then_else_keeps_its_own_mode_but_is_tagged(
    tmp_path,
):
    """A leaf that ALSO degrades (an unresolved nested construct) keeps its
    NAME_ONLY mode -- the degrade ladder is a more specific signal than the
    union tag -- but the section suffix still applies either way."""
    body = (
        "context:\n"
        '  version: "1.2.3"\n'
        "requirements:\n"
        "  run:\n"
        "    - if: linux\n"
        "      then:\n"
        "        - numpy ${{ version.replace('.', '_') }}\n"
    )
    path = write_recipe(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.name == "numpy"
    assert component.extraction_mode is ExtractionMode.NAME_ONLY
    assert component.provenance[0].section == "requirements.run[if:linux]"


def test_if_only_entry_with_neither_then_nor_else_degrades_to_raw_malformed(
    tmp_path,
):
    """Review Pass 2 correction: an `if`-dict entry carrying NEITHER a
    `then` NOR an `else` key must still yield exactly ONE RAW_MALFORMED
    component -- never silently zero."""
    body = "requirements:\n  run:\n    - if: linux\n"
    path = write_recipe(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.extraction_mode is ExtractionMode.RAW_MALFORMED
    assert component.provenance[0].section == "requirements.run[if:linux]"


def test_if_else_present_then_missing_degrades_then_side_only(tmp_path):
    """`if`/`else` present with `then` missing (Review Pass 1 KEEP
    instruction's regression test): the `then` side degrades to ONE
    RAW_MALFORMED leaf (via the same "unrecognized shape" path a missing
    key falls into), while `else` still contributes its own real,
    correctly-tagged component(s)."""
    body = "requirements:\n  run:\n    - if: linux\n      else:\n        - numpy\n"
    path = write_recipe(tmp_path, body)
    components = _extractor().extract(path, MANIFEST)
    tagged = {(c.name, c.provenance[0].section, c.extraction_mode) for c in components}
    assert (
        "numpy",
        "requirements.run[else:linux]",
        ExtractionMode.UNION_MARKED,
    ) in tagged
    malformed = [c for c in components if c.extraction_mode is ExtractionMode.RAW_MALFORMED]
    assert len(malformed) == 1
    assert malformed[0].provenance[0].section == "requirements.run[if:linux]"


def test_unrecognized_then_shape_degrades_to_raw_malformed(tmp_path):
    """A `then` value that is neither a string, a list, nor an `if`-dict
    (here a bare int) degrades to RAW_MALFORMED rather than vanishing."""
    body = "requirements:\n  run:\n    - if: linux\n      then: 42\n"
    path = write_recipe(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.extraction_mode is ExtractionMode.RAW_MALFORMED
    assert component.provenance[0].section == "requirements.run[if:linux]"


def test_then_empty_list_degrades_to_raw_malformed(tmp_path):
    """Review Pass 3 fix: an explicitly EMPTY `then:` list (`then: []`) is
    the same class of degenerate shape as a missing `then` key -- it must
    NOT silently fall through the list-walking loop to a bare empty
    return, contradicting "`then` ALWAYS contributes"."""
    body = "requirements:\n  run:\n    - if: linux\n      then: []\n"
    path = write_recipe(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    assert component.extraction_mode is ExtractionMode.RAW_MALFORMED
    assert component.provenance[0].section == "requirements.run[if:linux]"


def test_condition_label_is_truncated_unconditionally(tmp_path):
    """The `if:` condition is bounded via `truncate_for_name`
    unconditionally -- an arbitrarily long condition scalar must never
    embed unbounded into `Provenance.section` (NFR-S5)."""
    long_condition = "x" * 500
    body = (
        "requirements:\n"
        "  run:\n"
        f"    - if: {long_condition}\n"
        "      then: posix\n"
    )
    path = write_recipe(tmp_path, body)
    (component,) = _extractor().extract(path, MANIFEST)
    section = component.provenance[0].section
    assert len(section) < 300
    assert section.endswith("…[truncated]]")


def test_deeply_nested_if_then_else_raises_unparsable_not_a_crash(tmp_path):
    """A pathologically nested (but well within the 5MB manifest cap)
    if/then/else chain must degrade honestly via UnparsableManifestError,
    never crash the process with a raw RecursionError (Review Pass 1
    correction #2)."""
    depth = 2000
    opens = "".join(f'{{if: c{i}, then: [\n' for i in range(depth))
    closes = "".join("]}\n" for _ in range(depth))
    body = f"requirements:\n  run:\n    - {opens}mypkg{closes}"
    path = write_recipe(tmp_path, body)
    with pytest.raises(UnparsableManifestError):
        _extractor().extract(path, MANIFEST)
