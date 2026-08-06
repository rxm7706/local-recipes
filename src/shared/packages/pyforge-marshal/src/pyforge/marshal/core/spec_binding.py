"""Parses a tracked story spec's own Success signal (Story 2.7, AD-4/AD-49).

Every spec authored under ``planning-artifacts/specs/`` this project has
produced already carries a ``## Verification`` section with a
``**Commands:**`` sub-list, in exactly this shape (verified live against
``spec-3-7-escalation-deferral-and-resume.md``/
``spec-3-8-stage-bound-durability-and-fleet-launch-wiring.md``, the two
specs tracked at the time this module was written)::

    ## Verification

    **Commands:**
    - `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: ...
    - `pixi run --frozen -e pyforge-marshal lint-imports ...` -- expected: ...

    **Manual checks (if no CLI):**
    - ...

That section IS the spec's machine-parseable Success signal -- the promise
its author made about what a green gate means. ``parse_success_signal``
extracts the backtick-quoted command from each bullet under
``**Commands:**``, pure, no I/O (AD-4): the caller (``cli/gate.py``) already
read the spec file's bytes.

``None`` vs. an empty tuple is a deliberate, meaningful distinction,
mirroring Story 2.3's own ``spec_surface`` "no declared surface" vs.
"declared empty surface" discipline (``core/gate.py::
compute_effective_surface``'s own docstring):

- ``None`` -- no ``## Verification`` heading exists AT ALL. There is
  nothing to bind against; the caller (``core/gate.py::check_spec_binding``)
  treats this the same as "no tracked spec at all".
- ``()`` -- a ``## Verification`` heading exists but no ``**Commands:**``
  sub-list under it (or the sub-list has zero backtick-quoted commands). The
  spec explicitly promises nothing machine-checkable; that is a real,
  parsed answer, not a parse failure.

A malformed bullet (a ``- `` list item with no backtick-quoted command) is
skipped, not treated as the end of the list or a parse failure for the
whole section -- the I/O matrix's own "degrades gracefully" row.
"""

from __future__ import annotations

import re

# Any ATX heading (# through ######) -- the boundary that ends the
# `## Verification` section, regardless of the ending heading's own level.
_HEADING = re.compile(r"^#{1,6}[ \t]", re.MULTILINE)

# The exact heading this module targets (Design Notes: not a new frontmatter
# field -- the existing `## Verification` section already is the canonical
# Success signal). Matched against a WHOLE line, no trailing content.
_VERIFICATION_HEADING = re.compile(r"^## Verification[ \t]*$", re.MULTILINE)

# The `**Commands:**` sub-heading immediately under `## Verification`, per
# every spec this project has tracked so far.
_COMMANDS_SUBHEADING = re.compile(r"^\*\*Commands:\*\*[ \t]*$", re.MULTILINE)

# A markdown bullet whose text begins with a backtick-quoted command --
# `- \`<command>\` ...` (with 0+ leading whitespace, matched against an
# already-stripped line). The command is everything up to the NEXT
# backtick, never crossing one -- a command itself is never expected to
# contain a literal backtick.
_BULLET_COMMAND = re.compile(r"^-\s+`([^`]+)`")


def parse_success_signal(spec_text: str) -> tuple[str, ...] | None:
    """Extract the ordered tuple of commands named under a tracked spec's
    ``## Verification`` -> ``**Commands:**`` section. Pure, no I/O (AD-4).

    Returns ``None`` when ``spec_text`` has no ``## Verification`` heading
    at all -- "nothing to bind against", not "bound to nothing" (see this
    module's own docstring). Returns ``()`` when the heading exists but no
    ``**Commands:**`` sub-list is found under it (before the next heading),
    or when that sub-list has no bullet whose text opens with a
    backtick-quoted command. Every OTHER bullet under ``**Commands:**`` --
    up to the next bolded sub-heading (e.g. ``**Manual checks...**``), a
    blank line followed by non-bullet prose, or the next ATX heading --
    contributes its command in declaration order; a malformed bullet (no
    backtick-quoted command) is skipped, not a parse failure for the whole
    section.

    Line endings are normalized to bare ``\\n`` FIRST (review finding, P4):
    ``re.MULTILINE``'s ``$`` matches immediately before a ``\\n`` but NOT
    before a trailing ``\\r``, so every heading regex here (anchored on
    ``$``) failed to match a CRLF-terminated spec file at all -- a genuinely
    present ``## Verification`` section silently fell through to ``None``
    ("nothing to bind against") purely because of how the file's line
    endings were saved. Normalizing once, up front, fixes every anchored
    regex in this module at once rather than making each one CRLF-aware.
    """
    spec_text = spec_text.replace("\r\n", "\n").replace("\r", "\n")

    heading_match = _VERIFICATION_HEADING.search(spec_text)
    if heading_match is None:
        return None

    next_heading = _HEADING.search(spec_text, heading_match.end())
    section_end = next_heading.start() if next_heading is not None else len(spec_text)
    section = spec_text[heading_match.end() : section_end]

    commands_match = _COMMANDS_SUBHEADING.search(section)
    if commands_match is None:
        return ()

    commands: list[str] = []
    for line in section[commands_match.end() :].split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("**"):
            # A sibling bolded sub-heading (e.g. "**Manual checks...**")
            # closes the Commands list.
            break
        bullet = _BULLET_COMMAND.match(stripped)
        if bullet is not None:
            commands.append(bullet.group(1))
        elif not stripped.startswith("-"):
            # Non-bullet prose after the list (rare, but not itself a
            # bullet the malformed-bullet tolerance is meant to cover) also
            # closes the list, rather than being scanned forever.
            break
        # A bullet with no backtick-quoted command (`stripped.startswith("-")`
        # but the regex above did not match) is silently skipped -- the I/O
        # matrix's "malformed bullet" row -- and the loop continues.
    return tuple(commands)
