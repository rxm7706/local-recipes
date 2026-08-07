"""Unit tests for ``pyforge.marshal.core.spec_difficulty`` (Story 6.1,
FR-48/FR-51/AD-19) -- ``parse_declared_difficulty``'s parsing matrix:
present, absent, and malformed. Mirrors ``test_spec_surface.py``'s own
structure exactly (Story 2.3's identical three-way discipline)."""

from __future__ import annotations

import pytest

from pyforge.marshal.core.spec_difficulty import (
    DifficultyParseError,
    parse_declared_difficulty,
)

_HEADER = "title: 'x'\ntype: 'feature'\n"


def _frontmatter(body: str) -> str:
    return f"---\n{body}---\n\n<intent-contract>\n"


# --- present -------------------------------------------------------------------


def test_present_bare_scalar_difficulty_returns_the_value():
    text = _frontmatter(_HEADER + "difficulty: heavy\n")
    assert parse_declared_difficulty(text) == "heavy"


def test_present_single_quoted_difficulty_returns_the_value():
    text = _frontmatter(_HEADER + "difficulty: 'heavy'\n")
    assert parse_declared_difficulty(text) == "heavy"


def test_present_double_quoted_difficulty_returns_the_value():
    text = _frontmatter(_HEADER + 'difficulty: "heavy"\n')
    assert parse_declared_difficulty(text) == "heavy"


def test_present_hyphenated_bare_scalar_difficulty_returns_the_value():
    text = _frontmatter(_HEADER + "difficulty: extra-heavy\n")
    assert parse_declared_difficulty(text) == "extra-heavy"


def test_present_bare_scalar_with_trailing_comment_returns_the_value():
    """Edge Case Hunter finding: a trailing YAML comment on an otherwise
    ordinary declaration must not be silently dropped -- an entirely
    ordinary authoring habit (`difficulty: heavy  # rationale`) must parse
    exactly as if the comment were absent, never fall through to
    `None` just because the bare-token charset check saw the comment text."""
    text = _frontmatter(_HEADER + "difficulty: heavy  # rationale\n")
    assert parse_declared_difficulty(text) == "heavy"


def test_present_quoted_scalar_with_trailing_comment_returns_the_value():
    text = _frontmatter(_HEADER + 'difficulty: "heavy"  # rationale\n')
    assert parse_declared_difficulty(text) == "heavy"


def test_present_bare_scalar_with_immediately_adjacent_hash_is_not_a_comment():
    """A `#` NOT preceded by whitespace is not a YAML comment start -- it is
    part of the scalar, and the whole thing is not a valid bare token, so
    this remains the malformed-value `None` case, never a truncated
    `"heavy"`."""
    text = _frontmatter(_HEADER + "difficulty: heavy#not-a-comment\n")
    assert parse_declared_difficulty(text) is None


# --- absent ------------------------------------------------------------------


def test_no_frontmatter_at_all_returns_none():
    assert parse_declared_difficulty("no frontmatter here\n") is None


def test_frontmatter_present_but_no_difficulty_key_returns_none():
    text = _frontmatter(_HEADER)
    assert parse_declared_difficulty(text) is None


def test_unclosed_frontmatter_returns_none():
    text = "---\n" + _HEADER + "difficulty: heavy\n"
    assert parse_declared_difficulty(text) is None


def test_empty_string_returns_none():
    assert parse_declared_difficulty("") is None


def test_difficulty_key_outside_the_frontmatter_block_is_ignored():
    text = _frontmatter(_HEADER) + "\ndifficulty: heavy\n"
    assert parse_declared_difficulty(text) is None


# --- malformed -----------------------------------------------------------------


def test_malformed_empty_quoted_string_returns_none():
    text = _frontmatter(_HEADER + "difficulty: ''\n")
    assert parse_declared_difficulty(text) is None


def test_malformed_non_string_literal_returns_none():
    text = _frontmatter(_HEADER + "difficulty: 3\n")
    assert parse_declared_difficulty(text) is None


def test_malformed_list_value_returns_none():
    text = _frontmatter(_HEADER + 'difficulty: ["heavy"]\n')
    assert parse_declared_difficulty(text) is None


def test_malformed_bare_scalar_with_embedded_space_returns_none():
    text = _frontmatter(_HEADER + "difficulty: extra heavy\n")
    assert parse_declared_difficulty(text) is None


def test_malformed_arbitrary_code_is_never_executed():
    """``ast.literal_eval`` never evaluates a call expression, and a call
    expression is not a bare token either -- proves the parser is safe
    against an adversarial spec file, not merely that it happens to reject
    one example."""
    text = _frontmatter(_HEADER + "difficulty: __import__('os').system('true')\n")
    assert parse_declared_difficulty(text) is None


# --- multi-line block form (mirrors SurfaceParseError's own rationale) ---------


def test_multiline_block_difficulty_raises_difficulty_parse_error_not_none():
    """A multi-line YAML block -- `difficulty:` alone on its line, then
    further content -- is a form this parser does not support, and must NOT
    collapse into the same `None` a genuinely absent `difficulty:` key
    returns: a real, deliberate declaration this parser simply cannot see
    must never be silently discarded as though nothing were declared."""
    text = _frontmatter(_HEADER + "difficulty:\n  heavy\n")
    with pytest.raises(DifficultyParseError):
        parse_declared_difficulty(text)


def test_multiline_block_difficulty_with_trailing_whitespace_raises():
    text = _frontmatter(_HEADER + "difficulty:   \n  heavy\n")
    with pytest.raises(DifficultyParseError):
        parse_declared_difficulty(text)


def test_multiline_block_difficulty_with_trailing_comment_raises():
    text = _frontmatter(_HEADER + "difficulty:  # see below\n  heavy\n")
    with pytest.raises(DifficultyParseError):
        parse_declared_difficulty(text)


# --- type contract -------------------------------------------------------------


def test_rejects_non_str_input():
    with pytest.raises(TypeError):
        parse_declared_difficulty(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        parse_declared_difficulty(123)  # type: ignore[arg-type]
