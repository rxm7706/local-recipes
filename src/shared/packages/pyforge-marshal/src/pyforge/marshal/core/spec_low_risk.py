"""The story-spec-declared ``declared_low_risk:`` frontmatter reader (Story 33.5,
spec-risk-tiered-review-depth enablement).

``parse_declared_low_risk`` mirrors ``core/spec_difficulty.py`` and
``core/spec_surface.py``'s established frontmatter discipline: a minimal,
dependency-free parser over the ``---``-delimited block every tracked story
spec already carries. No ``pyyaml``/``ruamel.yaml``.

Unlike ``difficulty:`` (a string scalar), ``declared_low_risk:`` is a boolean
scalar -- ``true``/``false`` via ``ast.literal_eval`` (stdlib only, safe).
An absent key returns ``False`` (mechanical default: not declared low-risk).
A present key whose inline value is not a Python ``bool`` after parsing is
treated as ``False`` -- functionally identical to absent for the AND-gate in
``classify_review_tier``.

A ``declared_low_risk:`` key with no inline value (multi-line YAML block form)
raises ``LowRiskParseError``, mirroring ``DifficultyParseError`` / AD-27:
callers must report it, never swallow into ``False``.

This module is pure data: no I/O (AD-4).
"""

from __future__ import annotations

import ast
import re

from pyforge.core.errors import PyforgeError

_FRONTMATTER_DELIMITER = "---"
_LOW_RISK_KEY = "declared_low_risk:"

_BARE_BOOL_RE = re.compile(r"^(?i:true|false|yes|no)$")


def _strip_trailing_comment(raw: str) -> str:
    in_single = False
    in_double = False
    for index, char in enumerate(raw):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            if index == 0 or raw[index - 1].isspace():
                return raw[:index].rstrip()
    return raw


class LowRiskParseError(PyforgeError, ValueError):
    """Raised when ``declared_low_risk:`` is present but carries no inline
    value (multi-line YAML block form this parser does not support)."""


def parse_declared_low_risk(text: str) -> bool:
    """Parse ``declared_low_risk:`` from ``text``'s frontmatter block.

    Returns ``False`` when: no recognizable frontmatter; no ``declared_low_risk:``
    key; or the inline value is not a valid boolean literal.

    Raises ``LowRiskParseError`` for the unsupported multi-line block form.
    Raises ``TypeError`` if ``text`` is not a ``str``."""
    if not isinstance(text, str):
        raise TypeError(f"text must be a str, got {text!r}")

    lines = text.splitlines()
    if not lines or lines[0].strip() != _FRONTMATTER_DELIMITER:
        return False

    frontmatter: list[str] = []
    closed = False
    for line in lines[1:]:
        if line.strip() == _FRONTMATTER_DELIMITER:
            closed = True
            break
        frontmatter.append(line)
    if not closed:
        return False

    for line in frontmatter:
        stripped = line.strip()
        if not stripped.startswith(_LOW_RISK_KEY):
            continue
        raw = stripped[len(_LOW_RISK_KEY) :].strip()
        raw = _strip_trailing_comment(raw).strip()
        if raw == "":
            raise LowRiskParseError(
                "declared_low_risk: is present but has no inline value -- only "
                "the one-line scalar form is supported (declared_low_risk: true "
                "or declared_low_risk: false); a multi-line YAML block is not "
                "parsed and must not be silently treated as absent"
            )
        try:
            value = ast.literal_eval(raw)
        except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
            lowered = raw.lower()
            if _BARE_BOOL_RE.fullmatch(lowered):
                return lowered in {"true", "yes"}
            return False
        if isinstance(value, bool):
            return value
        return False

    return False
