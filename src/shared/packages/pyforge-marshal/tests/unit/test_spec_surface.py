"""Unit tests for ``pyforge.marshal.core.spec_surface`` (Story 2.3,
AD-4/AD-27) -- ``parse_declared_surface``'s parsing matrix: present,
absent, and malformed."""

from __future__ import annotations

import pytest

from pyforge.marshal.core.spec_surface import SurfaceParseError, parse_declared_surface

_HEADER = "title: 'x'\ntype: 'feature'\n"


def _frontmatter(body: str) -> str:
    return f"---\n{body}---\n\n<intent-contract>\n"


# --- present -------------------------------------------------------------------


def test_present_surface_returns_the_declared_globs():
    text = _frontmatter(_HEADER + 'surface: ["recipes/x/**", "recipes/y/**"]\n')
    assert parse_declared_surface(text) == ("recipes/x/**", "recipes/y/**")


def test_present_single_glob_surface():
    text = _frontmatter(_HEADER + 'surface: ["recipes/x/**"]\n')
    assert parse_declared_surface(text) == ("recipes/x/**",)


def test_present_explicit_empty_surface_returns_empty_tuple_not_none():
    """AD-27's own narrowing-only contract: 'declared empty' and 'declared
    nothing' must not collapse -- an explicit ``surface: []`` narrows to
    NOTHING, distinct from no declaration at all."""
    text = _frontmatter(_HEADER + "surface: []\n")
    result = parse_declared_surface(text)
    assert result == ()
    assert result is not None


def test_surface_preserves_declaration_order_and_duplicates():
    text = _frontmatter(_HEADER + 'surface: ["b/**", "a/**", "a/**"]\n')
    assert parse_declared_surface(text) == ("b/**", "a/**", "a/**")


# --- absent ----------------------------------------------------------------


def test_no_frontmatter_at_all_returns_none():
    assert parse_declared_surface("no frontmatter here\n") is None


def test_frontmatter_present_but_no_surface_key_returns_none():
    text = _frontmatter(_HEADER)
    assert parse_declared_surface(text) is None


def test_unclosed_frontmatter_returns_none():
    text = "---\n" + _HEADER + 'surface: ["a/**"]\n'
    assert parse_declared_surface(text) is None


def test_empty_string_returns_none():
    assert parse_declared_surface("") is None


def test_surface_key_outside_the_frontmatter_block_is_ignored():
    text = _frontmatter(_HEADER) + '\nsurface: ["a/**"]\n'
    assert parse_declared_surface(text) is None


# --- malformed ---------------------------------------------------------------


def test_malformed_unparseable_literal_returns_none():
    text = _frontmatter(_HEADER + "surface: [this is not valid python\n")
    assert parse_declared_surface(text) is None


def test_malformed_not_a_list_returns_none():
    text = _frontmatter(_HEADER + 'surface: "recipes/x/**"\n')
    assert parse_declared_surface(text) is None


def test_malformed_list_of_non_strings_returns_none():
    text = _frontmatter(_HEADER + "surface: [1, 2, 3]\n")
    assert parse_declared_surface(text) is None


def test_malformed_list_containing_empty_string_returns_none():
    text = _frontmatter(_HEADER + 'surface: ["a/**", ""]\n')
    assert parse_declared_surface(text) is None


def test_malformed_dict_value_returns_none():
    text = _frontmatter(_HEADER + 'surface: {"a": "b"}\n')
    assert parse_declared_surface(text) is None


def test_malformed_arbitrary_code_is_never_executed():
    """``ast.literal_eval`` never evaluates a call expression -- proves the
    parser is safe against an adversarial spec file, not merely that it
    happens to reject one example."""
    text = _frontmatter(_HEADER + "surface: [__import__('os').system('true')]\n")
    assert parse_declared_surface(text) is None


# --- multi-line block form (AD-27, review finding: Edge Case Hunter) -----------


def test_multiline_block_surface_raises_surface_parse_error_not_none():
    """A multi-line YAML block -- `surface:` alone on its line, then `- ...`
    entries -- is a form this parser does not support, and must NOT collapse
    into the same `None` a genuinely absent `surface:` key returns (that
    would silently WIDEN the effective surface back to the full policy
    surface, the exact AD-27 violation this module exists to prevent)."""
    text = _frontmatter(_HEADER + 'surface:\n  - "recipes/x/**"\n  - "recipes/y/**"\n')
    with pytest.raises(SurfaceParseError):
        parse_declared_surface(text)


def test_multiline_block_surface_with_trailing_whitespace_raises():
    text = _frontmatter(_HEADER + 'surface:   \n  - "recipes/x/**"\n')
    with pytest.raises(SurfaceParseError):
        parse_declared_surface(text)


def test_multiline_block_surface_with_trailing_comment_raises():
    text = _frontmatter(_HEADER + 'surface:  # a block follows\n  - "recipes/x/**"\n')
    with pytest.raises(SurfaceParseError):
        parse_declared_surface(text)


# --- type contract -------------------------------------------------------------


def test_rejects_non_str_input():
    with pytest.raises(TypeError):
        parse_declared_surface(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        parse_declared_surface(123)  # type: ignore[arg-type]
