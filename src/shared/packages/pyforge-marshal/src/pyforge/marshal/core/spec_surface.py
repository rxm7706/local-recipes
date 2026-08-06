"""The story-spec-declared ``surface:`` frontmatter reader (Story 2.3,
architecture spine AD-4/AD-27).

``parse_declared_surface`` is a minimal, dependency-free parser: no
``pyyaml``/``ruamel.yaml`` (absent from this package's dependencies today,
and adding one for a single list field is disproportionate). It supports
exactly the flow-sequence form on one line, ``surface: ["glob1", "glob2"]``,
extracted from the frontmatter block (the ``---``-delimited header every
tracked story spec in this repo already carries) and parsed via
``ast.literal_eval`` -- stdlib only, and safe against arbitrary code
execution since ``literal_eval`` accepts only Python literals, never an
expression.

Pure parsing over an ALREADY-READ string (AD-4: ``core/**`` performs no
I/O, spawns no process, reads no clock, imports nothing from ``os``,
``subprocess``, ``pathlib``'s I/O methods, ``time``, or
``pyforge.marshal.adapters``) -- ``cli/gate.py`` reads the spec file's
bytes (the impure edge) and passes the text in here.

A missing ``surface:`` key returns ``None`` -- "no declared surface" -- a
malformed one (present but unparseable, or not a list of non-empty
strings) ALSO returns ``None``: this module's own contract is narrowing
only (AD-27), and a spec that failed to declare a well-formed surface has
nothing to narrow the policy surface with, exactly as if it declared
nothing at all. An EXPLICITLY empty list, ``surface: []``, is a distinct
fact -- it returns ``()``, never ``None`` -- "declared empty" and "declared
nothing" must not collapse (both are legitimate, but a caller reading
"empty tuple" as "no declared surface" would then treat a real, deliberate
empty-surface declaration as absent, silently WIDENING the effective
surface back to the policy surface alone -- exactly the expansion AD-27
forbids).

This module is pure data: no I/O, no subprocess, no network, no clock, no
``pyforge.marshal.adapters`` import (AD-4) -- only ``ast``.
"""

from __future__ import annotations

import ast

_FRONTMATTER_DELIMITER = "---"
_SURFACE_KEY = "surface:"


def parse_declared_surface(text: str) -> tuple[str, ...] | None:
    """Parse the ``surface:`` field out of ``text``'s YAML-ish frontmatter
    block (the region between the first line -- which must be exactly
    ``---`` -- and the next line that is exactly ``---``).

    Returns ``None`` when: ``text`` carries no recognizable frontmatter
    block (no leading ``---``, or no closing ``---``); the block has no
    ``surface:`` key; the key's value fails to parse as a Python literal
    (``ast.literal_eval``); or the parsed value is not a ``list`` of
    non-empty strings. Otherwise returns the declared globs as a tuple,
    preserving order and duplicates (deduplication and glob validity are a
    caller's concern, not this parser's).

    Raises ``TypeError`` if ``text`` is not a ``str`` -- a contract
    violation, matching ``core.policy.compose``'s own type-guard
    convention, never a silent ``None``."""
    if not isinstance(text, str):
        raise TypeError(f"text must be a str, got {text!r}")

    lines = text.splitlines()
    if not lines or lines[0].strip() != _FRONTMATTER_DELIMITER:
        return None

    frontmatter: list[str] = []
    closed = False
    for line in lines[1:]:
        if line.strip() == _FRONTMATTER_DELIMITER:
            closed = True
            break
        frontmatter.append(line)
    if not closed:
        return None

    for line in frontmatter:
        stripped = line.strip()
        if not stripped.startswith(_SURFACE_KEY):
            continue
        raw = stripped[len(_SURFACE_KEY) :].strip()
        try:
            value = ast.literal_eval(raw)
        except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
            return None
        if isinstance(value, list) and all(
            isinstance(item, str) and item != "" for item in value
        ):
            return tuple(value)
        return None

    return None
