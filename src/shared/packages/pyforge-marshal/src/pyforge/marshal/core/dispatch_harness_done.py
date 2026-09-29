"""Harness-done relaunch gate (Story 29.2, SPEC CAP-11 marshal half).

After the session harness exits ``done``, fleet drain must not start another
``bmad-build-auto``. The next step is CAP-4 land only. Pure functions: parse
the worktree spec's frontmatter facts and shape the operator message. I/O
and landing stay in ``cli/dispatch.py`` / ``dispatch_land.py``.

Story 51.8 (CAP-256, review pass 1): a leading HTML-comment provenance
banner (``_skip_leading_banner``, mirroring ``core/promotion.py``,
``core/spec_surface.py``, and ``core/spec_low_risk.py``'s identical helper)
is skipped before the fence check, so a promoted, banner-topped tracked
spec's ``status:``/``followup_review_recommended:`` are no longer misread as
absent by the ``lines[0] == "---"`` check -- reached via
``cli/dispatch.py``'s harness-done relaunch gate, a real caller reading the
same tracked spec family this parser's siblings already guard against this
bug.
"""

from __future__ import annotations

import ast
import re

_FRONTMATTER_DELIMITER = "---"
_STATUS_KEY = "status:"
_FOLLOWUP_KEY = "followup_review_recommended:"
_BLOCKING_CONDITION_KEY = "blocking_condition:"
_BASELINE_REVISION_KEY = "baseline_revision:"
_BARE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_TRUTHY = frozenset({"true", "yes", "1"})

# Story 51.4: the "Blocking condition:" body-line convention is not
# universal -- some specs only carry the frontmatter scalar above, others
# only a body line (optionally bold-wrapping the value, never the label).
_BLOCKING_CONDITION_BODY_RE = re.compile(r"(?im)^blocking condition:\s*(.+)$")

# Story 51.11: mirrors ``supervisor/intent_gap_preserve.py``'s own
# ``_AUTO_RUN_HEADING_RE`` -- a different module, same heading convention.
_AUTO_RUN_HEADING_RE = re.compile(r"^##\s+Auto Run Result\s*$", re.MULTILINE)

_BANNER_PREFIX = "<!--"
_BANNER_SUFFIX = "-->"


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


def _frontmatter_scalar(text: str, key: str) -> str | None:
    """Read one inline YAML scalar from the first ``---`` frontmatter block."""
    if not isinstance(text, str):
        raise TypeError(f"text must be a str, got {text!r}")
    lines = _skip_leading_banner(text).splitlines()
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
        except ValueError, SyntaxError, TypeError, MemoryError, RecursionError:
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


def parse_blocking_condition(text: str) -> str | None:
    """The spec's own stated reason for ``status: blocked`` (Story 51.4).

    Checked in two forms, since the convention is not universal: a
    frontmatter ``blocking_condition:`` scalar first, then a body line
    reading ``Blocking condition: ...`` (the label is never bold-wrapped,
    the value sometimes is). ``None`` when neither is present so callers
    fall back to a generic message rather than inventing one.
    """
    value = _frontmatter_scalar(text, _BLOCKING_CONDITION_KEY)
    if value is not None:
        return value
    matches = list(_BLOCKING_CONDITION_BODY_RE.finditer(text))
    if not matches:
        return None
    found = matches[-1].group(1).strip().replace("*", "").strip()
    return found or None


def parse_baseline_revision(text: str) -> str | None:
    """The spec's own ``baseline_revision:`` frontmatter scalar (Story
    51.11, CAP-258) -- the run a ``blocked`` halt's Auto Run Result was
    written against, so a stale ``blocked`` spec left over from an earlier
    dispatch pass on this same story is never misattributed to the run
    reading it now (Never bullet 3)."""
    return _frontmatter_scalar(text, _BASELINE_REVISION_KEY)


def has_auto_run_result(text: str) -> bool:
    """True when the spec body carries an ``## Auto Run Result`` heading
    (Story 51.11) -- mirrors ``supervisor/intent_gap_preserve.py``'s own
    heading match. A bare ``status: blocked`` with no such section is not
    enough signal that the harness itself (rather than a hand edit)
    produced this halt."""
    return _AUTO_RUN_HEADING_RE.search(text) is not None


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
