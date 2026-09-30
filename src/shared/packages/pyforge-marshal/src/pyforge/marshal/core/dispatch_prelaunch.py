"""Pure pre-launch predicates (Story 65.1, spec-pyforge-marshal CAP-274).

Everything in this module is a question a drain can answer about a queued
story WITHOUT launching it: does its tracked spec bind, is it parked only in
prose, does an ``order_overrides`` list do anything, are its declared Deps
``done``. No I/O (AD-4) -- ``cli/drain_plan.py`` does the reads and hands the
text in; ``marshal factory drain --plan`` reports the answers, and Story 65.2
reuses ``spec_binding_findings`` to refuse the same story inside
``dispatch_once`` before it provisions anything.

The predicates never decide anything the launch path does not already decide:
``spec_binding_findings`` is ``gate.check_spec_binding`` over
``spec_binding.parse_success_signal`` (the pair the post-session gate runs),
``unmet_deps`` reads the same ``**Deps:**`` graph ``spec_deps`` builds for the
parallel wave. Only the prose-park detector and the inert-override check are
new -- and both only REPORT: the declared skip (``skip_policies``) stays the one
park mechanism, and a prose park is never honoured by the drain.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from . import gate, spec_binding
from .dispatch_fleet import DONE_STATUS
from .identity import MalformedStoryKeyError, StoryKey, normalize, render_feed_key
from .model import Finding
from .spec_deps import STORY_HEADING_RE

# --- spec binding (shared with Story 65.2) -----------------------------------


def spec_binding_findings(
    spec_text: str | None,
    policy_commands: Sequence[str],
) -> tuple[Finding, ...]:
    """The ``MRS-GATE-010`` / ``MRS-GATE-011`` findings the post-session gate
    would report for ``spec_text`` against ``policy_commands`` (pure).

    ``spec_text is None`` -- no tracked spec could be read -- and a spec with no
    ``## Verification`` heading both bind against nothing (``MRS-GATE-010``);
    a declared command missing from ``policy_commands`` is ``MRS-GATE-011``.
    ``policy_commands`` must be the commands the gate itself runs, i.e. the
    station's ``verify_commands`` widened with the derived surface guard
    (``dispatch_verify._verify_commands_with_surface_guard``) -- the caller owns
    that widening because the guard constant lives in an adapter, which core may
    not import (AD-4)."""
    declared = spec_binding.parse_success_signal(spec_text) if spec_text is not None else None
    return gate.check_spec_binding(declared, tuple(policy_commands))


# --- prose park --------------------------------------------------------------

# Markdown emphasis is stripped before matching: the real steward wording is
# ``do **not** dispatch``. Underscores are only emphasis at a word edge
# (``_not_``), never inside an identifier (``is_parked``).
_EMPHASIS_RE = re.compile(r"[*`~]+|(?<![A-Za-z0-9])_+|_+(?![A-Za-z0-9])")
# ``parked`` as a word (not inside an identifier); ``unparked`` / ``un-parked``
# are the opposite claim.
_PARKED_RE = re.compile(r"(?<![A-Za-z0-9_])(?<!un-)parked\b", re.IGNORECASE)
_DO_NOT_DISPATCH_RE = re.compile(r"\bdo\s+not\s+dispatch\b", re.IGNORECASE)
_EXCERPT_LIMIT = 200

# The `N` of `### Story E.N:` -- digits plus an optional lowercase suffix.
_STORY_NUMBER_RE = re.compile(r"(\d+)([a-z]?)")

# An epic-level heading closes the last story of the epic above it; without it
# an epic's preamble would be read as part of that story's block.
_EPIC_HEADING_RE = re.compile(r"^## ", re.MULTILINE)


@dataclass(frozen=True)
class ProsePark:
    """One prose park marker: where it was read and the line that carries it."""

    source: str
    excerpt: str


def story_epics_blocks(epics_text: str) -> dict[StoryKey, str]:
    """``{story: its block of an epics-family document}`` (pure).

    A block runs from the story's ``### Story N.M:`` heading line to the next
    story heading or the next ``## `` (epic) heading. It is the same
    ``### Story`` splitter ``dispatch_fleet.parse_epics_dependencies`` reads
    ``**Deps:**`` from, extended to stop at an epic boundary."""
    headings = list(STORY_HEADING_RE.finditer(epics_text))
    blocks: dict[StoryKey, str] = {}
    for index, match in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(epics_text)
        epic_break = _EPIC_HEADING_RE.search(epics_text, match.end())
        if epic_break is not None and epic_break.start() < end:
            end = epic_break.start()
        number = _STORY_NUMBER_RE.fullmatch(match.group("pn"))
        if number is None:
            continue
        key = StoryKey(epic=int(match.group("pe")), seq=int(number.group(1)), suffix=number.group(2))
        block = epics_text[match.start() : end]
        blocks[key] = f"{blocks[key]}\n{block}" if key in blocks else block
    return blocks


def _park_line(text: str) -> str | None:
    stripped = _EMPHASIS_RE.sub("", text)
    for line in stripped.splitlines():
        if _PARKED_RE.search(line) or _DO_NOT_DISPATCH_RE.search(line):
            return line.strip()[:_EXCERPT_LIMIT]
    return None


def find_prose_park(
    *,
    story: str,
    station_skips: Mapping[str, str],
    epics_block: str | None,
    spec_text: str | None,
) -> ProsePark | None:
    """The prose park marker of ``story`` that no ``skip_policies`` entry mirrors.

    "Parked" or "do not dispatch" (case-insensitive, emphasis stripped) in the
    story's ``epics.md`` block or in its tracked spec. ``None`` when the story
    carries no marker, or when ``station_skips`` already names it -- a park
    that lives in code is the one mechanism, so it is not a finding. Pure."""
    if story in station_skips:
        return None
    for source, text in (("epics.md", epics_block), ("tracked spec", spec_text)):
        if not text:
            continue
        line = _park_line(text)
        if line is not None:
            return ProsePark(source=source, excerpt=line)
    return None


# --- order overrides ---------------------------------------------------------


def inert_override_keys(
    override: Sequence[str] | None,
    statuses: Iterable[tuple[str, str]],
) -> tuple[str, ...]:
    """The keys of an ``order_overrides`` list that changes nothing (pure).

    A non-empty list whose every key is ``done`` in the station's tracked
    ledger, or absent from it, moves no story -- yet its being non-empty
    switches the Story 28.12 ``Deps:`` sort off (``dispatch_fleet.
    station_backlog``). Returns those keys (de-duplicated, in list order) when
    the WHOLE list is inert, and ``()`` for an empty list or one with any live
    key."""
    if not override:
        return ()
    status_by_key: dict[str, str] = {}
    for raw_key, raw_status in statuses:
        if isinstance(raw_key, str):
            status_by_key[raw_key] = str(raw_status).strip().lower()
    for key in override:
        status = status_by_key.get(key)
        if status is not None and status != DONE_STATUS:
            return ()
    return tuple(dict.fromkeys(override))


# --- deps readiness ----------------------------------------------------------


def unmet_deps(
    story: str,
    statuses: Iterable[tuple[str, str]],
    graph: Mapping[str, tuple[StoryKey, ...]],
) -> tuple[StoryKey, ...]:
    """The declared ``**Deps:**`` of ``story`` that are not ``done`` (pure).

    ``graph`` is feed story key -> declared dependency keys, the shape
    ``spec_deps.story_deps_from_epics`` produces and the parallel wave gates on
    (``spec_deps.ready_backlog``). A malformed ``story`` has no readable Deps."""
    try:
        feed = render_feed_key(normalize(story))
    except MalformedStoryKeyError:
        return ()
    done: set[StoryKey] = set()
    for raw_key, raw_status in statuses:
        if not isinstance(raw_key, str) or str(raw_status).strip().lower() != DONE_STATUS:
            continue
        try:
            done.add(normalize(raw_key))
        except MalformedStoryKeyError:
            continue
    return tuple(dep for dep in graph.get(feed, ()) if dep not in done)
