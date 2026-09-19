"""Unit tests for ``pyforge.marshal.core.spec_low_risk`` (Story 33.5)."""

from __future__ import annotations

import pytest

from pyforge.marshal.core.spec_low_risk import LowRiskParseError, parse_declared_low_risk

_HEADER = "title: 'x'\ntype: 'feature'\n"


def _frontmatter(body: str) -> str:
    return f"---\n{body}---\n\n<intent-contract>\n"


def test_absent_key_returns_false():
    text = _frontmatter(_HEADER)
    assert parse_declared_low_risk(text) is False


def test_explicit_false_returns_false():
    text = _frontmatter(_HEADER + "declared_low_risk: false\n")
    assert parse_declared_low_risk(text) is False


def test_explicit_true_returns_true():
    text = _frontmatter(_HEADER + "declared_low_risk: true\n")
    assert parse_declared_low_risk(text) is True


def test_python_literal_true_returns_true():
    text = _frontmatter(_HEADER + "declared_low_risk: True\n")
    assert parse_declared_low_risk(text) is True


def test_trailing_comment_on_true():
    text = _frontmatter(_HEADER + "declared_low_risk: true  # mechanical doc fix\n")
    assert parse_declared_low_risk(text) is True


def test_bare_yes_returns_true():
    text = _frontmatter(_HEADER + "declared_low_risk: yes\n")
    assert parse_declared_low_risk(text) is True


def test_malformed_non_bool_returns_false():
    text = _frontmatter(_HEADER + "declared_low_risk: maybe\n")
    assert parse_declared_low_risk(text) is False


def test_multiline_block_raises():
    text = _frontmatter(_HEADER + "declared_low_risk:\n  true\n")
    with pytest.raises(LowRiskParseError):
        parse_declared_low_risk(text)


def test_no_frontmatter_returns_false():
    assert parse_declared_low_risk("no frontmatter\n") is False


def test_blank_line_before_banner_reads_true():
    """Story 51.8 (DW-FU-50-5/CAP-256): a promoted, banner-topped tracked
    spec's ``declared_low_risk: true`` must not be misread as ``False`` --
    a leading blank line before the banner's opening marker must not fall
    through to "no frontmatter" either."""
    text = "\n<!-- Promoted ... -->\n" + _frontmatter(_HEADER + "declared_low_risk: true\n")
    assert parse_declared_low_risk(text) is True


def test_spaces_before_banner_reads_true():
    text = "  <!-- Promoted ... -->\n" + _frontmatter(_HEADER + "declared_low_risk: true\n")
    assert parse_declared_low_risk(text) is True


def test_bom_before_banner_reads_true():
    text = "\ufeff<!-- Promoted ... -->\n" + _frontmatter(_HEADER + "declared_low_risk: true\n")
    assert parse_declared_low_risk(text) is True


def test_banner_below_frontmatter_unaffected():
    """The banner-BELOW-frontmatter shape never starts with ``<!--``, so it
    is untouched by the banner-skip and must keep parsing exactly as
    before."""
    text = _frontmatter(_HEADER + "declared_low_risk: true\n") + "<!-- Promoted ... -->\n"
    assert parse_declared_low_risk(text) is True


def test_unclosed_banner_above_frontmatter_reads_false():
    """An unclosed ``<!--`` is not a banner this parser recognizes -- the
    text still doesn't start with ``---``, so it stays absent, not
    declared."""
    text = "<!-- never closed\n" + _frontmatter(_HEADER + "declared_low_risk: true\n")
    assert parse_declared_low_risk(text) is False
