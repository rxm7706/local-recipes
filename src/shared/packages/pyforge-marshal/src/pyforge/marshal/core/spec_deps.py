"""Story dependency graph helpers (Story 28.12 CAP-14, shared with 28.16).

Pure parsing and ordering over already-read epics text and ledger status
pairs -- no I/O (AD-4). Reads ``**Deps:**`` / ``**Depends on:**`` fields
from structured ``### Story E.N:`` sections in a station's epics-family
document, the same mechanical grammar ``pyforge.doctor.sources.deps`` uses
for forward-dependency detection (restated here so marshal dispatch never
imports doctor internals).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence

from .identity import MalformedStoryKeyError, StoryKey, normalize, render_feed_key

STORY_HEADING_RE = re.compile(
    r"^### Story (?P<pe>\d+)\.(?P<pn>\d+[a-z]?): ?"
    r"(?P<title>.*?)(?:\s*\*\(.*?\)\*)?\s*$",
    re.M,
)

DEPS_FIELD_RE = re.compile(r"\*\*(?:Deps|Depends on):\*\* ?(.*?)(?:\s*•|\n|$)")

# ``S-28.12`` (genesis form) or bare ``28.12`` (marshal epics form).
DEP_RE = re.compile(
    r"(?:(?P<station>[a-z][a-z0-9-]*):)?(?:S-)?(?P<epic>\d+)\.(?P<num>\d+[a-z]?|\*)",
    re.I,
)

NO_DEP_RE = re.compile(r"^\s*(?:—|–|-|none|nothing|n/?a)(?![\w-])", re.I)


def parse_deps_text(deps_text: str) -> tuple[StoryKey, ...]:
    """Machine-readable dependency keys from one story's Deps field text."""
    text = str(deps_text).strip()
    if not text or NO_DEP_RE.match(text):
        return ()
    keys: list[StoryKey] = []
    for match in DEP_RE.finditer(text):
        if match.group("num") == "*":
            continue
        try:
            keys.append(normalize(match.group("epic") + "." + match.group("num")))
        except MalformedStoryKeyError:
            continue
    return tuple(keys)


def story_deps_from_epics(epics_text: str) -> dict[str, tuple[StoryKey, ...]]:
    """Map feed story key -> declared dependency keys from epics text."""
    headings = list(STORY_HEADING_RE.finditer(epics_text))
    graph: dict[str, tuple[StoryKey, ...]] = {}
    for index, match in enumerate(headings):
        block_end = headings[index + 1].start() if index + 1 < len(headings) else len(epics_text)
        block = epics_text[match.end() : block_end]
        dep_match = DEPS_FIELD_RE.search(block)
        deps_text = dep_match.group(1).strip() if dep_match else ""
        story_key = match.group("pe") + "." + match.group("pn")
        try:
            feed = render_feed_key(normalize(story_key))
        except MalformedStoryKeyError:
            continue
        graph[feed] = parse_deps_text(deps_text)
    return graph


def _done_keys(statuses: Iterable[tuple[str, str]]) -> frozenset[StoryKey]:
    done: set[StoryKey] = set()
    for raw_key, raw_status in statuses:
        if str(raw_status).strip().lower() != "done":
            continue
        try:
            done.add(normalize(raw_key))
        except MalformedStoryKeyError:
            continue
    return frozenset(done)


def deps_satisfied(
    story_raw: str,
    *,
    done: frozenset[StoryKey],
    graph: Mapping[str, tuple[StoryKey, ...]],
) -> bool:
    """True when every declared dependency of ``story_raw`` is ``done``."""
    try:
        feed = render_feed_key(normalize(story_raw))
    except MalformedStoryKeyError:
        return False
    for dep in graph.get(feed, ()):
        if dep not in done:
            return False
    return True


def ready_backlog(
    backlog: Sequence[str],
    statuses: Iterable[tuple[str, str]],
    graph: Mapping[str, tuple[StoryKey, ...]],
) -> tuple[str, ...]:
    """Backlog stories whose dependencies are satisfied, in backlog order."""
    done = _done_keys(statuses)
    return tuple(story for story in backlog if deps_satisfied(story, done=done, graph=graph))


def story_transitively_depends_on(
    candidate_raw: str,
    in_flight_raw: str,
    graph: Mapping[str, tuple[StoryKey, ...]],
) -> bool:
    """True when ``candidate_raw`` declares a dependency on ``in_flight_raw``."""
    try:
        candidate = render_feed_key(normalize(candidate_raw))
        target = normalize(in_flight_raw)
    except MalformedStoryKeyError:
        return False
    seen: set[str] = set()
    stack = list(graph.get(candidate, ()))
    while stack:
        dep = stack.pop()
        if dep == target:
            return True
        dep_feed = render_feed_key(dep)
        if dep_feed in seen:
            continue
        seen.add(dep_feed)
        stack.extend(graph.get(dep_feed, ()))
    return False
