"""Harness-done relaunch gate (Story 29.2, SPEC CAP-11 marshal half).

After the session harness exits ``done``, fleet drain must not start another
``bmad-build-auto``. The next step is CAP-4 land only. Pure functions: parse
the worktree spec's frontmatter facts and shape the operator message. I/O
and landing stay in ``cli/dispatch.py`` / ``dispatch_land.py``.
"""

from __future__ import annotations

import ast
import re

_FRONTMATTER_DELIMITER = "---"
_STATUS_KEY = "status:"
_FOLLOWUP_KEY = "followup_review_recommended:"
_BARE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_TRUTHY = frozenset({"true", "yes", "1"})


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


def _frontmatter_scalar(text: str, key: str) -> str | None:
    """Read one inline YAML scalar from the first ``---`` frontmatter block."""
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
        if not stripped.startswith(key):
            continue
        raw = _strip_trailing_comment(stripped[len(key) :].strip()).strip()
        if raw == "":
            return None
        try:
            value = ast.literal_eval(raw)
        except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
            return raw if _BARE_TOKEN_RE.fullmatch(raw) else None
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str) and value != "":
            return value
        if isinstance(value, int) and not isinstance(value, bool):
            return str(value)
        return None
    return None


def parse_spec_status(text: str) -> str | None:
    """Story-spec ``status:`` token, or ``None`` when absent or unreadable."""
    value = _frontmatter_scalar(text, _STATUS_KEY)
    return value.lower() if value is not None else None


def followup_review_recommended(text: str) -> bool:
    """True only when ``followup_review_recommended`` is an explicit truthy.

    Missing, ``false``, or unreadable is not a follow-up — Story 29.1's
    halt rule. Marshal must not relaunch on the same facts.
    """
    value = _frontmatter_scalar(text, _FOLLOWUP_KEY)
    if value is None:
        return False
    return value.lower() in _TRUTHY


def blocks_harness_relaunch(status: str | None, followup: bool) -> bool:
    """True when a further ``bmad-build-auto`` must not start."""
    return status == "done" and not followup


def land_fail_operator_message(
    *,
    story_key: str,
    named_target: str,
    land_verdict: str,
) -> str:
    """CHAIN / awaiting-operator text naming the PR or worktree (CAP-4 fail)."""
    return (
        f"harness-done story {story_key!r} is CAP-4 only — not relaunching "
        f"(land verdict {land_verdict!r}). awaiting-operator / CHAIN: "
        f"{named_target}"
    )
