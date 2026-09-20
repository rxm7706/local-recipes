"""Attribute a legacy bare-form merge subject by the paths its diff touches
(Story 27.5, spec-pyforge-doctor CAP-80's amended Approach).

**The regression, twice.** Story 27.1 scoped ``sources/marshal.py``'s and
``sources/ledger.py``'s templated-merge-subject match to each station's OWN
``merge_subject_template`` — but AD-24's repo-default (``Merge {key} into
main``, no station token) still exists as a real merge shape wherever a
station has not (yet) overridden its template, or landed a story BEFORE it
did. Marshal's own ``34-3`` landed exactly this way on 2026-09-12
(``dcda31b8cb``); once marshal's policy moved to a scoped template (PR
#1467), ``story-status`` on ``main`` reported it a false green — ``done`` in
the feed, no merge commit anywhere (PR #1471).

Story 27.3 tried gating the bare form on "the querying station's OWN
tracked ledger knows the key" alone. Its own review found the gap: with
eight stations sharing one story-numbering grammar, two stations knowing the
SAME integer key is the common case, not the exception — that rule reopened
the exact cross-station collision Story 27.1 (CAP-78) had just closed. It
reverted, landed empty (PR #1476), and was re-minted as this story.

**The fix.** A bare-form merge subject is attributed to the querying station
iff BOTH:

1. ``sha``'s first-parent diff (``git diff --name-only <sha>^1 <sha>``)
   touches at least one path under that station's own
   ``_bmad-output/projects/<slug>/`` or ``src/shared/packages/<slug>/``
   prefix — git, the sole authority for what a merge actually shipped,
   decides who a bare subject belongs to, never a numeric coincidence.
2. that station's own tracked ledger already has a row for the extracted
   key, ANY status (see below) — confirming this is really one of the
   station's own numbered stories, not a path that happens to be touched by
   an unrelated fleet-wide commit that also grazes this station's tree.

Neither alone is safe: path-only would attribute a fleet-wide mop commit
that grazes many packages to EVERY station it touches; ledger-only is
27.3's own reopened collision. Both together resolve the real incident
(marshal's ``34-3``, whose first-parent diff touches ONLY
``pyforge-marshal`` paths — verified live) without reopening either gap.

**Any tracked status, not done-only** — unlike Story 27.3's own reverted
``load_done_story_keys``. That restriction existed because ledger
membership was the SOLE gate then, so "known" had to also mean "safe to
trust" on its own. The diff-path gate above now independently confirms the
merge's OWN file changes belong to this station; ledger membership only
needs to confirm the key is genuinely one of this station's own (not a
same-numbered sibling's), which any tracked row already shows. Mirrors
``pyforge.marshal.dispatch_supervisor.__main__._load_known_story_keys``
(Story 35.1, spec-marshal-templated-merge-subject-cross-project-collision
CAP-1), which already treats ANY tracked status as "known" for the
identical corroboration purpose.

**One function, both sources** (this story's own Boundaries): both
``sources/marshal.py::gather_story_status`` (Routes 2/3) and
``sources/ledger.py::gather_direction`` (``_merged_ids_for_project``) call
``attribute_bare_merge`` below, rather than each restating the diff-path
classification and its caching. Sibling per-file helpers
(``_project_merge_subject_template``, ``_parse_statuses``) stay duplicated
per the package's existing precedent — only the diff-path attribution
decision is shared here, mirroring ``rekey.py``'s own placement directly
under ``pyforge/doctor/`` (not ``sources/``): a concern exactly two
``sources/*.py`` files need, with no third.

**Degrades, never crashes.** A ``git diff`` call that fails for a given
``sha`` (missing parent, corrupted repo, a GC'd object) yields
``diff_unreadable_sha`` set on the returned :class:`BareMergeAttribution`
rather than raising or silently attributing — the caller decides how to
surface that (a WARN naming the sha, folded into its own existing
Finding-emission idiom); this module never builds a ``Finding`` itself,
mirroring ``rekey.py``'s own "reader, not judge" posture.

**The independence rule.** Reads the DURABLE ARTIFACTS only — a tracked
ledger and ``git diff`` — and never imports ``pyforge.marshal`` (or any
other station package). Mirrors ``sources/marshal.py``'s and ``sources/
ledger.py``'s own independence rationale (see either module's own
docstring).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pyforge.core.landing_evidence import StoryKeyRef, parse_templated_merge_subject

from .cli_bridge import CliBridgeError, run_git

__all__ = (
    "BARE_MERGE_SUBJECT_TEMPLATE",
    "BareMergeAttribution",
    "DiffCache",
    "attribute_bare_merge",
    "known_story_keys",
    "station_slugs_touched",
)

#: AD-24's repo-default merge-subject template — carries no station token of
#: its own (Story 27.1's own acknowledged residual). Identical to
#: ``sources/marshal.py``'s / ``sources/ledger.py``'s own private
#: ``_MERGE_SUBJECT_TEMPLATE`` constants — kept in sync by hand, the same
#: precedent those two files' own small duplicated constants already follow.
BARE_MERGE_SUBJECT_TEMPLATE = "Merge {key} into main"

_PROJECTS_REL = "_bmad-output/projects"
_PACKAGES_REL = "src/shared/packages"
_LEDGER_SUFFIX = "planning-artifacts/sprint-status-ledger.yaml"

#: A tracked-ledger key is ``<epic>-<seq>[suffix]-<kebab-title>`` — mirrors
#: ``sources/marshal.py``'s own ``_FEED_KEY_RE``. An ``epic-<n>``/``epic-<n>-
#: retrospective`` aggregate row never matches (no leading digit), so it is
#: excluded without a separate check.
_LEDGER_KEY_RE = re.compile(r"^(\d+)-(\d+)([a-z])?-")

#: Memoizes :func:`station_slugs_touched` within ONE gather run —
#: ``{sha: slugs-or-None}``. A caller creates one instance per top-level
#: ``gather_story_status``/``gather_direction`` invocation and threads it
#: through every call, so the same merge sha's diff is fetched at most once
#: even though a run audits many story keys against the same merge history
#: (``git`` is the one expensive call this module makes; a local ledger read
#: is not worth caching the same way).
DiffCache = dict[str, frozenset[str] | None]


def _git(target: Path, *args: str) -> str | None:
    """``git`` stdout, or ``None`` on any failure.

    Routes through ``cli_bridge.run_git`` — AD-5 makes that module the SOLE
    subprocess site in the package. Mirrors ``sources/marshal.py``'s and
    ``sources/ledger.py``'s own private ``_git`` wrappers.
    """
    try:
        return run_git(target, list(args))
    except CliBridgeError, UnicodeDecodeError:
        return None


def _classify_diff_paths(paths: list[str]) -> frozenset[str]:
    """Station slugs (``pyforge-<station>``) named by ``_bmad-output/
    projects/<slug>/…`` or ``src/shared/packages/<slug>/…`` paths. A path
    under neither prefix (docs, root config, a recipe) contributes nothing —
    the whole point being that a merge touching no station path attributes
    to no station at all."""
    slugs: set[str] = set()
    for path in paths:
        for prefix in (_PROJECTS_REL, _PACKAGES_REL):
            head = f"{prefix}/"
            if path.startswith(head):
                slug = path[len(head) :].split("/", 1)[0]
                if slug:
                    slugs.add(slug)
                break
    return frozenset(slugs)


def station_slugs_touched(target: Path, sha: str, cache: DiffCache) -> frozenset[str] | None:
    """Station slugs ``sha``'s first-parent diff touches, or ``None`` when
    the ``git diff`` call itself fails — "cannot evaluate", never a crash
    and never an empty-set false negative. Memoized in ``cache`` (see
    :data:`DiffCache`)."""
    if sha in cache:
        return cache[sha]
    raw = _git(target, "diff", "--name-only", f"{sha}^1", sha)
    result = None if raw is None else _classify_diff_paths(raw.splitlines())
    cache[sha] = result
    return result


def _parse_ledger_statuses(text: str) -> dict[str, str]:
    """``key: value`` pairs under ``development_status:`` — a deliberately
    tiny parser rather than PyYAML, mirroring ``sources/marshal.py``'s and
    ``sources/ledger.py``'s own ``_parse_statuses``: the file's shape is
    fixed by its own generator, and this must keep working on a
    partially-corrupt blob rather than raising."""
    out: dict[str, str] = {}
    in_block = False
    for raw in text.splitlines():
        if raw.startswith("development_status:"):
            in_block = True
            continue
        if not in_block:
            continue
        if raw and not raw.startswith((" ", "\t")):
            break
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if sep:
            out[key.strip()] = value.strip()
    return out


def known_story_keys(target: Path, project_slug: str) -> frozenset[StoryKeyRef]:
    """Every story key ``project_slug``'s OWN tracked
    ``sprint-status-ledger.yaml`` has a row for, at ANY status (see module
    docstring for why this diverges from Story 27.3's done-only reading).
    Read from the WORKING TREE, mirroring ``sources/marshal.py``'s and
    ``sources/ledger.py``'s own ledger reads for this same file.

    Degrades to ``frozenset()`` (fails CLOSED — corroborates nothing) on a
    missing or unreadable ledger, never raises: that can only ever COST an
    attribution the ledger would otherwise have granted, never wrongly
    grant one.
    """
    path = target / _PROJECTS_REL / project_slug / _LEDGER_SUFFIX
    try:
        text = path.read_text(encoding="utf-8")
    except OSError, UnicodeDecodeError:
        return frozenset()
    keys: set[StoryKeyRef] = set()
    for raw_key in _parse_ledger_statuses(text):
        match = _LEDGER_KEY_RE.match(raw_key)
        if match is None:
            continue
        keys.add(
            StoryKeyRef(
                epic=int(match.group(1)),
                seq=int(match.group(2)),
                suffix=match.group(3) or "",
            )
        )
    return frozenset(keys)


@dataclass(frozen=True)
class BareMergeAttribution:
    """One decision for one ``(subject, sha)`` pair.

    ``key`` is the attributed story key, or ``None`` on any miss (including
    "subject is not the bare shape at all"). ``diff_unreadable_sha`` is set
    only when the shape and ledger gates both passed but the diff query
    itself failed — the one case a caller must surface as a WARN rather
    than a silent non-match, since it means "not evaluated", not "evaluated
    and did not attribute".
    """

    key: StoryKeyRef | None
    diff_unreadable_sha: str | None = None


def attribute_bare_merge(
    subject: str,
    sha: str,
    *,
    target: Path,
    project_slug: str,
    known_keys: frozenset[StoryKeyRef],
    cache: DiffCache,
) -> BareMergeAttribution:
    """Attribute ``subject`` (the bare legacy merge form) to
    ``project_slug`` iff ``sha``'s first-parent diff touches ONLY that
    station's own paths AND the extracted key is a member of ``known_keys``
    — both conditions, never one (see module docstring). ``known_keys`` is
    the caller-supplied result of :func:`known_story_keys` for
    ``project_slug`` — passed in rather than read here so a caller auditing
    many subjects for the SAME station reads its ledger once, not once per
    subject.

    Exclusive touch, not mere membership: a diff touching TWO stations' own
    paths (a fleet-wide mop commit) must attribute to NEITHER when both
    stations' own ledgers independently know the key (the common case under
    one shared grammar) — `project_slug in slugs` alone would let such a
    commit attribute to every station it grazes, one audit at a time,
    reopening the exact collision the module docstring's "neither alone is
    safe" paragraph describes.
    """
    key = parse_templated_merge_subject(subject, BARE_MERGE_SUBJECT_TEMPLATE, project_slug)
    if key is None or key not in known_keys:
        return BareMergeAttribution(key=None)
    slugs = station_slugs_touched(target, sha, cache)
    if slugs is None:
        return BareMergeAttribution(key=None, diff_unreadable_sha=sha)
    if slugs == frozenset({project_slug}):
        return BareMergeAttribution(key=key)
    return BareMergeAttribution(key=None)
