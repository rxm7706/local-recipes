"""The story-spec-declared ``difficulty:`` frontmatter reader (Story 6.1,
FR-48/FR-51/AD-19).

``parse_declared_difficulty`` mirrors ``core/spec_surface.py::
parse_declared_surface``'s established three-way "absent (mechanical
default) / present-and-parseable / present-and-malformed" discipline
exactly (Story 2.3 already solved the exact shape of problem this module
needs solved again -- a frontmatter scalar with an absent/malformed/
unsupported three-way split -- and reusing its DISCIPLINE, never its code,
keeps this codebase's own frontmatter-reading convention singular rather
than letting a second, subtly-different parser drift in). No
``pyyaml``/``ruamel.yaml`` (absent from this package's dependencies, and
adding one for a single scalar field is disproportionate) -- a minimal,
dependency-free parser reading the ``---``-delimited frontmatter block
every tracked story spec in this repo already carries.

Unlike ``surface:`` (a flow-sequence of globs), ``difficulty:`` is a single
SCALAR -- a bare word (``difficulty: heavy``, the ordinary unquoted YAML
plain-scalar form) or a quoted string (``difficulty: "heavy"``/
``difficulty: 'heavy'``). Both are supported: a quoted value is parsed via
``ast.literal_eval`` (stdlib only, safe against arbitrary code execution --
``literal_eval`` accepts only Python literals, never an expression); an
UNQUOTED value that is not itself valid Python syntax (the ordinary case
for a bare identifier-shaped difficulty name) is accepted directly when it
is composed only of letters, digits, ``_``, or ``-`` -- the same charset
this package's own slug/story-key vocabularies already use elsewhere. A
trailing YAML comment on either form (``difficulty: heavy  # rationale``)
is stripped first (``_strip_trailing_comment``, YAML's own whitespace-
preceded/not-inside-a-quote rule) before either branch runs, so an
otherwise ordinary declaration with a trailing comment parses exactly as
if the comment were absent -- it must not fall through to "no well-formed
value" just because prose followed the value on the same line.
Anything else that fails to parse (a Python literal that is not a non-empty
string, or a bare token containing characters outside that charset) is
treated as "no well-formed value" and returns ``None``, exactly like
``parse_declared_surface``'s own "malformed VALUE" case: this module's own
job is resolving which difficulty tier applies, not enforcing a closed
vocabulary (``core.policy.model_tier_map`` already treats an unmapped
difficulty as "no override" rather than an error), so a value this parser
cannot read is functionally identical to no value at all.

A ``difficulty:`` key present with NO inline value at all -- i.e. the
multi-line YAML block form (``difficulty:`` alone on its own line, or
followed only by a trailing comment) -- is a THIRD, distinct case from
either of the above: this parser supports exactly the one-line scalar
form, so a multi-line block is not "malformed content this parser
rejected", it is "a form this parser was never told how to read at all".
Collapsing that into the same ``None`` a genuinely absent ``difficulty:``
key returns would silently discard a real, deliberate declaration this
parser simply cannot see -- this case instead raises
``DifficultyParseError``, mirroring ``SurfaceParseError``'s own identical
rationale: callers must catch this and report it, never swallow it into a
bare ``None``.

This module is pure data: no I/O, no subprocess, no network, no clock, no
``pyforge.marshal.adapters`` import (AD-4) -- only ``ast``/``re``.
"""

from __future__ import annotations

import ast
import re

_FRONTMATTER_DELIMITER = "---"
_DIFFICULTY_KEY = "difficulty:"

# The bare-token charset a difficulty name may use when written unquoted
# (the ordinary YAML plain-scalar case) -- the same charset this package's
# own slug/story-key vocabularies already use elsewhere (e.g.
# ``core.policy._SLUG_CHARS``), never re-derived a second way.
_BARE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _strip_trailing_comment(raw: str) -> str:
    """Strip a YAML-style trailing comment from an inline scalar value.

    A ``#`` starts a comment when it is preceded by whitespace (or sits at
    the very start of the value) and is not inside a quoted string --
    exactly YAML's own rule. Without this, an entirely ordinary declaration
    like ``difficulty: heavy  # rationale`` would fail both the
    ``ast.literal_eval`` branch (a bare identifier plus trailing prose is
    not a Python literal) and the bare-token charset check (the comment
    text isn't in ``[A-Za-z0-9_-]+``), silently discarding a real,
    deliberate declaration into ``None`` -- exactly the failure mode this
    module's own docstring says must never happen."""
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


class DifficultyParseError(ValueError):
    """Raised by ``parse_declared_difficulty`` when the frontmatter's
    ``difficulty:`` key is PRESENT but carries no inline value on its own
    line -- the multi-line YAML block form (``difficulty:`` alone, or with
    only a trailing comment). Distinct from a merely malformed/unsupported
    inline value (which returns ``None``, per this module's own
    narrowing-only-by-omission contract): a present-but-unsupported-FORM key
    is neither "declared" nor "absent", and must not be silently treated as
    the latter -- callers must catch this and report it, never swallow it
    into a bare ``None``."""


def parse_declared_difficulty(text: str) -> str | None:
    """Parse the ``difficulty:`` field out of ``text``'s YAML-ish frontmatter
    block (the region between the first line -- which must be exactly
    ``---`` -- and the next line that is exactly ``---``).

    Returns ``None`` when: ``text`` carries no recognizable frontmatter
    block (no leading ``---``, or no closing ``---``); the block has no
    ``difficulty:`` key; or the key's inline value is neither a valid
    non-empty-string Python literal nor a bare token drawn from
    ``[A-Za-z0-9_-]+``. Otherwise returns the declared difficulty as a
    string.

    Raises ``DifficultyParseError`` when ``difficulty:`` is present but
    carries no inline value at all -- the multi-line YAML block form this
    parser does not support (see that class's own docstring): distinct from
    a malformed/unsupported inline value, which returns ``None``.

    Raises ``TypeError`` if ``text`` is not a ``str`` -- a contract
    violation, matching ``parse_declared_surface``'s own type-guard
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
        if not stripped.startswith(_DIFFICULTY_KEY):
            continue
        raw = stripped[len(_DIFFICULTY_KEY) :].strip()
        raw = _strip_trailing_comment(raw).strip()
        if raw == "":
            # Either nothing followed `difficulty:` at all, or only a
            # trailing comment did (`difficulty:  # rationale`) -- the
            # multi-line YAML block form (`difficulty:` alone, or with only
            # a trailing comment, followed by further lines this parser does
            # not read) -- a form this parser was never told how to read,
            # not a malformed value. Must not collapse into the same `None`
            # a genuinely absent key returns (see module docstring /
            # DifficultyParseError).
            raise DifficultyParseError(
                "difficulty: is present but has no inline value -- only the "
                "one-line scalar form is supported (difficulty: heavy or "
                'difficulty: "heavy"); a multi-line YAML block is not '
                "parsed and must not be silently treated as absent"
            )
        try:
            value = ast.literal_eval(raw)
        except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
            # Not valid Python literal syntax -- the ordinary case for a
            # bare, unquoted YAML plain scalar (`difficulty: heavy`).
            # Accepted directly when it is composed only of this module's
            # own bare-token charset; anything else (embedded whitespace, a
            # YAML-flow-shaped fragment that still failed to parse, stray
            # punctuation) is "no well-formed value" -- returns None exactly
            # like a malformed inline value does, never an error.
            return raw if _BARE_TOKEN_RE.fullmatch(raw) else None
        if isinstance(value, str) and value != "":
            return value
        return None

    return None
