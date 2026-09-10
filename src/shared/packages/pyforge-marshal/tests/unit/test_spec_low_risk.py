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
