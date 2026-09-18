"""A station's own DONE keys corroborate its legacy-template merge history
(spec-pyforge-doctor CAP-80, Story 27.3).

**The regression this closes.** Story 27.1 made ``sources/marshal.py`` and
``sources/ledger.py`` read each station's *current* ``merge_subject_template``
from its tracked ``marshal-policy.toml``. Marshal landed ``34-3`` on
2026-09-12 as ``Merge 34-3 into main`` under the then-default (bare)
template; the moment marshal's policy moved to ``Merge pyforge-marshal/{key}
into main`` (PR #1467), that subject stopped matching marshal's own CURRENT
template, and ``story-status`` on ``main`` reported ``marshal/34-3`` as a
false green with no landing evidence anywhere — a ``done`` story orphaned by
its own station's template move (PR #1471).

**The fix.** The bare legacy form (``Merge {key} into main``, AD-24's
repo-default, carrying no station token of its own) is attributed to the
querying station only when that station's OWN tracked ledger
(``sprint-status-ledger.yaml``) ALREADY marks the extracted key ``done`` —
mirrors ``pyforge.marshal.dispatch_supervisor.__main__._load_known_story_
keys``'s own ``known_keys`` corroboration (Story 35.1,
``spec-marshal-templated-merge-subject-cross-project-collision`` CAP-1),
reimplemented here rather than imported: Doctor's independence rule (see
``sources/marshal.py``'s own module docstring) forbids importing
``pyforge.marshal``.

**Why DONE-only, diverging from Story 35.1's own broader "any status"
semantics.** Marshal's own ``_load_known_story_keys`` corroborates against
every key the ledger has a row for, regardless of status — sufficient for
its own use (confirming a story that IS being dispatched is really one of
the project's own), but pyforge-doctor's own tracked ``marshal-policy.toml``
records a live false-positive this broader form produces: "another
station's 'Merge N-M into main' merge reads as this station's N.M already
merged" the instant the two stations' ledgers happen to share a numeric key
(herald PR #1457's finding). ``sources/ledger.py``'s own
``test_sibling_default_template_merge_is_not_attributed_when_station_has_
its_own`` fixture is exactly this collision (atlas's own ledger carries a
NON-done ``13-5`` entry that coincidentally matches a sibling's bare-form
merge) and must keep reporting nothing. Restricting corroboration to keys
already ``done`` closes that gap: both call sites only need this fallback to
confirm a key ALREADY marked ``done``, so a same-numbered but not-yet-done
sibling entry can never falsely corroborate.

**One function, both sources** (this story's own Boundaries): both
``sources/marshal.py::gather_story_status`` and
``sources/ledger.py::gather_direction`` call ``legacy_bare_merge_key``
below, rather than each restating the corroboration rule — the one piece of
this fix that must not fork between the two files. Sibling per-file helpers
(``_project_merge_subject_template``, ``_parse_statuses``) stay duplicated
per the package's existing precedent (see either module's own docstring for
why); only the corroboration DECISION is shared.

**Degrades, never crashes** — the house rule for every Doctor source: a
missing, unreadable, or malformed ledger degrades ``load_done_story_keys``
to ``frozenset()`` (fails CLOSED — corroborates nothing). That can only ever
COST an attribution the ledger would otherwise have granted; it can never
wrongly grant one.

Reads the tracked ledger directly off the WORKING TREE (plain ``pathlib``,
no git), exactly as ``sources/marshal.py``'s own ``_ledgers``/``gather`` and
``sources/ledger.py``'s own ``gather_direction`` already do for this same
file — pure stdlib, no station package imported, so this module never
compromises either caller's independence rule.
"""

from __future__ import annotations

import re
from pathlib import Path

from pyforge.core.landing_evidence import StoryKeyRef, parse_templated_merge_subject

__all__ = (
    "LEGACY_MERGE_SUBJECT_TEMPLATE",
    "legacy_bare_merge_key",
    "load_done_story_keys",
)

PROJECTS_PREFIX = "_bmad-output/projects"
LEDGER_SUFFIX = "planning-artifacts/sprint-status-ledger.yaml"
TERMINAL = frozenset({"done"})

#: AD-24's repo-default merge-subject template — carries no station token,
#: so a subject rendered from it can never be attributed to a station by its
#: text alone (see module docstring). Kept identical to
#: ``sources/marshal.py``/``sources/ledger.py``'s own private
#: ``_MERGE_SUBJECT_TEMPLATE`` constants.
LEGACY_MERGE_SUBJECT_TEMPLATE = "Merge {key} into main"

#: A tracked-ledger key is ``<epic>-<seq>[suffix]-<kebab-title>`` — mirrors
#: ``sources/marshal.py``'s own ``_FEED_KEY_RE`` (the Tier-3 feed and the
#: tracked ledger share this exact shape by construction: ``sprint-ledger-
#: sync`` generates the ledger from the feed). An ``epic-<n>``/``epic-<n>-
#: retrospective`` aggregate row never matches (no leading digit), so it is
#: excluded without a separate check.
_LEDGER_KEY_RE = re.compile(r"^(\d+)-(\d+)([a-z])?-")


def _ledger_key_to_ref(raw_key: str) -> StoryKeyRef | None:
    match = _LEDGER_KEY_RE.match(raw_key)
    if match is None:
        return None
    return StoryKeyRef(
        epic=int(match.group(1)),
        seq=int(match.group(2)),
        suffix=match.group(3) or "",
    )


def _parse_statuses(text: str) -> dict[str, str]:
    """``key: value`` pairs under ``development_status:``.

    A deliberately tiny parser rather than PyYAML, mirroring ``sources/
    marshal.py``'s and ``sources/ledger.py``'s own ``_parse_statuses``: the
    file's shape is fixed by its own generator, and this must keep working
    on a partially-corrupt blob rather than raising.
    """
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


def load_done_story_keys(target: Path, project_slug: str) -> frozenset[StoryKeyRef]:
    """Every story key ``project_slug``'s OWN tracked
    ``sprint-status-ledger.yaml`` already marks ``done`` — the corroborating,
    station-scoped signal a bare legacy merge subject's own text cannot
    provide (see module docstring for why this is DONE-only, not every
    status the ledger carries). Read from the WORKING TREE.

    Degrades to ``frozenset()`` (fails closed) on a missing or unreadable
    ledger, never raises.
    """
    path = target / PROJECTS_PREFIX / project_slug / LEDGER_SUFFIX
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return frozenset()
    keys: set[StoryKeyRef] = set()
    for raw_key, status in _parse_statuses(text).items():
        if status not in TERMINAL:
            continue
        ref = _ledger_key_to_ref(raw_key)
        if ref is not None:
            keys.add(ref)
    return frozenset(keys)


def legacy_bare_merge_key(
    subject: str, *, known_keys: frozenset[StoryKeyRef]
) -> StoryKeyRef | None:
    """``subject`` parsed as AD-24's bare legacy form, but ONLY when the
    extracted key is a member of ``known_keys`` — ``None`` otherwise,
    including when ``subject`` does not match the legacy shape at all.

    This is the ONE corroboration rule (spec-pyforge-doctor CAP-80's own
    Boundaries: "one function, both sources") — never re-implemented per
    caller. A bare subject naming a key the querying station's own ledger
    does not (yet) mark done is the cross-station poison CAP-78 closed;
    this function is what keeps it closed while still letting a station's
    genuinely own pre-template-move history through.
    """
    key = parse_templated_merge_subject(subject, LEGACY_MERGE_SUBJECT_TEMPLATE)
    if key is not None and key in known_keys:
        return key
    return None
