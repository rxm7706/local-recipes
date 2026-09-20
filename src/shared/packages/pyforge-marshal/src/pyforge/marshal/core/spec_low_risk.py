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

Story 51.8 (CAP-256, DW-FU-50-5): a leading HTML-comment provenance banner
(``_skip_leading_banner``, mirroring ``core/promotion.py`` and
``core/spec_surface.py``'s identical helper) is skipped before the fence
check, so a promoted, banner-topped tracked spec's ``declared_low_risk: true``
is no longer misread as ``False`` by the ``lines[0] == "---"`` check.

This module is pure data: no I/O (AD-4).
"""

from __future__ import annotations

import ast
import re

from pyforge.core.errors import PyforgeError

_FRONTMATTER_DELIMITER = "---"
_LOW_RISK_KEY = "declared_low_risk:"

_BANNER_PREFIX = "<!--"
_BANNER_SUFFIX = "-->"

_BARE_BOOL_RE = re.compile(r"^(?i:true|false|yes|no)$")


def _skip_leading_banner(text: str) -> str:
    """Skip a leading HTML-comment provenance banner (Story 50.5/51.8,
    CAP-248/CAP-256) -- see ``core.promotion``'s identical helper for the
    full rationale: a recovered or minted tracked spec may carry a
    ``<!-- ... -->`` banner ABOVE its frontmatter fence instead of below
    it, and this parser's ``lines[0] == "---"`` check must not read that
    as "no frontmatter at all". Tolerates a leading BOM, blank lines, or
    spaces before the banner's opening marker -- the banner need not sit
    at literal text offset 0. Returns ``text`` unchanged when no banner is
    found there, or when the marker is never closed."""
    stripped = text.lstrip("\ufeff \t\r\n")
    if not stripped.startswith(_BANNER_PREFIX):
        return text
    end = stripped.find(_BANNER_SUFFIX, len(_BANNER_PREFIX))
    if end == -1:
        return text
    return stripped[end + len(_BANNER_SUFFIX) :].lstrip()


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

    lines = _skip_leading_banner(text).splitlines()
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
        except ValueError, SyntaxError, TypeError, MemoryError, RecursionError:
            lowered = raw.lower()
            if _BARE_BOOL_RE.fullmatch(lowered):
                return lowered in {"true", "yes"}
            return False
        if isinstance(value, bool):
            return value
        return False

    return False
