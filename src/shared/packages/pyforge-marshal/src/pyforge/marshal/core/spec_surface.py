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
malformed VALUE (present, with an inline value, but unparseable, or not a
list of non-empty strings) ALSO returns ``None``: this module's own
contract is narrowing only (AD-27), and a spec that failed to declare a
well-formed surface has nothing to narrow the policy surface with, exactly
as if it declared nothing at all. An EXPLICITLY empty list,
``surface: []``, is a distinct fact -- it returns ``()``, never ``None`` --
"declared empty" and "declared nothing" must not collapse (both are
legitimate, but a caller reading "empty tuple" as "no declared surface"
would then treat a real, deliberate empty-surface declaration as absent,
silently WIDENING the effective surface back to the policy surface alone --
exactly the expansion AD-27 forbids).

A ``surface:`` key present with NO inline value at all -- i.e. a multi-line
YAML BLOCK form (``surface:`` alone on its line, followed by ``- "glob"``
lines) -- is a THIRD, distinct case from either of the above (review
finding, Edge Case Hunter): this parser supports exactly the one-line
flow-sequence form, so a multi-line block is not "malformed content this
parser rejected", it is "a form this parser was never told how to read at
all". Collapsing that into the same ``None`` a genuinely absent ``surface:``
key returns would silently WIDEN the effective surface back to the full
policy surface for a spec author who (reasonably) wrote multi-line YAML --
the exact AD-27 violation this module exists to prevent. This case instead
raises ``SurfaceParseError`` -- see that class's own docstring.

This module is pure data: no I/O, no subprocess, no network, no clock, no
``pyforge.marshal.adapters`` import (AD-4) -- only ``ast``.
"""

from __future__ import annotations

import ast

_FRONTMATTER_DELIMITER = "---"
_SURFACE_KEY = "surface:"


class SurfaceParseError(ValueError):
    """Raised by ``parse_declared_surface`` when the frontmatter's
    ``surface:`` key is PRESENT but carries no inline value on its own
    line -- the multi-line YAML block form (``surface:`` alone, followed by
    ``- "glob"`` lines). Distinct from a merely malformed inline value
    (which returns ``None``, per this module's own narrowing-only
    contract): a present-but-unsupported-FORM key is neither "declared" nor
    "absent", and must not be silently treated as the latter (AD-27) --
    callers must catch this and report it, never swallow it into a bare
    ``None``."""


def parse_declared_surface(text: str) -> tuple[str, ...] | None:
    """Parse the ``surface:`` field out of ``text``'s YAML-ish frontmatter
    block (the region between the first line -- which must be exactly
    ``---`` -- and the next line that is exactly ``---``).

    Returns ``None`` when: ``text`` carries no recognizable frontmatter
    block (no leading ``---``, or no closing ``---``); the block has no
    ``surface:`` key; the key's inline value fails to parse as a Python
    literal (``ast.literal_eval``); or the parsed value is not a ``list``
    of non-empty strings. Otherwise returns the declared globs as a tuple,
    preserving order and duplicates (deduplication and glob validity are a
    caller's concern, not this parser's).

    Raises ``SurfaceParseError`` when ``surface:`` is present but carries
    no inline value at all -- the multi-line YAML block form this parser
    does not support (see that class's own docstring): distinct from a
    malformed inline value, which returns ``None``.

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
        if raw == "" or raw.startswith("#"):
            # The multi-line YAML block form (`surface:` alone, or with
            # only a trailing comment, followed by `- "glob"` lines on
            # subsequent lines) -- a form this parser was never told how
            # to read, not a malformed value. Must not collapse into the
            # same `None` a genuinely absent key returns (see module
            # docstring / SurfaceParseError).
            raise SurfaceParseError(
                "surface: is present but has no inline value -- only the "
                "one-line flow-sequence form is supported "
                '(surface: ["glob1", "glob2"]); a multi-line YAML block is '
                "not parsed and must not be silently treated as absent"
            )
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
