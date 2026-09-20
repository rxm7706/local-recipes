"""Definitions for the five `bmad-output-hygiene` finding classes (Story 9.1).

Five pure predicates, one per class — no filesystem or network I/O of their
own. Every input signal (file content, parsed YAML, booleans) is passed in by
the caller: Story 9.2's gather does the repo-wide collection and supplies the
evidence once; this module is only the classification boundary, cited
against the commit that first fixed a real instance of the class it names.

Kept OUTSIDE ``pyforge/doctor/sources/`` on purpose: that package's own
``test_every_real_sources_file_is_mapped_by_at_least_one_source`` meta test
requires every file there to back a registered ``Source`` — registering one
is Story 9.2's wiring job, not this definition-only story's.
"""

from __future__ import annotations

import fnmatch
from collections.abc import Iterable
from enum import StrEnum
from pathlib import PurePosixPath

__all__ = (
    "HygieneFindingKind",
    "is_dead_test_scaffolding",
    "is_hollow_sprint_status",
    "is_orphan_file",
    "is_readme_placeholder",
    "is_stale_dream_status",
)


class HygieneFindingKind(StrEnum):
    """The closed set of five hygiene finding classes the epic pins — see
    each ``is_*`` predicate below for the class it names."""

    DEAD_TEST_SCAFFOLDING = "dead-test-scaffolding"
    HOLLOW_SPRINT_STATUS = "hollow-sprint-status"
    ORPHAN_FILE = "orphan-file"
    README_PLACEHOLDER = "readme-placeholder"
    STALE_DREAM_STATUS = "stale-dream-status"


def is_dead_test_scaffolding(test_relpaths: Iterable[str]) -> bool:
    """``True`` iff none of ``test_relpaths`` match the ``test_*.py`` shape
    used by every real fixture this predicate is grounded in — i.e. only
    ``__init__.py``/``conftest.py``-shaped scaffold is present. An empty
    ``test_relpaths`` also returns ``True`` (vacuously: no real test file is
    present) — the caller (Story 9.2) is expected to only pass paths from a
    directory a marker file (``tests/``, ``pytest.ini``,
    ``playwright.config.ts``) already flagged as a scaffolding candidate.

    Deliberately narrower than pytest's own default discovery (which also
    matches ``*_test.py``): no real fixture across this repo uses that
    alternate shape, and this predicate's definitions are derived from real
    evidence, not from pytest's full default-discovery surface.

    Fixed by ``22da995c``: ``archive/_bmad-output/projects/pyforge-doctor/
    tests/`` held a ``conftest.py`` plus seven ``__init__.py``-only
    subpackages and zero ``test_*.py`` files — a planning tree pretending to
    be a real test suite. A directory with even one real ``test_*.py`` file
    is NOT an instance of this class, regardless of how much other scaffold
    surrounds it.
    """
    return not any(fnmatch.fnmatch(PurePosixPath(relpath).name, "test_*.py") for relpath in test_relpaths)


def is_hollow_sprint_status(parsed_yaml: dict | None) -> bool:
    """``True`` iff a parsed ``sprint-status.yaml`` declares zero epics, zero
    stories, and 0% completion — a sprint plan that was scaffolded but never
    populated. ``None`` (a real ``yaml.safe_load`` outcome for an empty or
    whitespace-only file) and a ``summary:`` key present with a ``None``
    value both return ``False`` rather than raise — malformed input is not a
    match for this specific hollow-template shape.

    Fixed by ``f7654a4c`` (CAP-2): ``archive/_bmad-output/projects/
    pyforge-doctor/planning-artifacts/sprint-status.yaml`` carried
    ``epics: []``, ``stories: []`` and ``completion_percentage: 0%`` while
    the project's real progress lived entirely in the tracked
    ``sprint-status-ledger.yaml`` twin. ``completion_percentage`` is checked
    against both ``0`` (numeric YAML) and ``"0%"`` (the literal string this
    project's own generator emits) since either is a valid parse of the same
    hollow state.
    """
    if not isinstance(parsed_yaml, dict):
        return False
    summary = parsed_yaml.get("summary") or {}
    return (
        parsed_yaml.get("epics") == []
        and parsed_yaml.get("stories") == []
        and summary.get("completion_percentage") in (0, "0%")
    )


def is_readme_placeholder(content: str) -> bool:
    """``True`` iff a station README's content still carries the unfilled
    bracket-token stub — ``[role]`` or ``[responsibilities]`` — rather than
    real per-station prose.

    Fixed by ``5c5e3727`` (CAP-4): every station README was generated from a
    template literally containing ``"... is a [role] station in the PyForge
    factory, responsible for [responsibilities]."`` and never filled in.
    CAP-4 also rewrote a second, byte-identical-stub variant of the same
    defect that carries neither bracket token verbatim — that variant is OUT
    of this predicate's scope; CAP-4's own stated success criterion covers
    only the literal bracket token, not every possible unfilled template
    shape.
    """
    return "[role]" in content or "[responsibilities]" in content


def is_stale_dream_status(dream_status: str, all_station_stories_done: bool) -> bool:
    """``True`` iff a Dream's frontmatter ``status:`` is still
    ``"specified"`` while every one of its station's stories is already
    done — the status field lagging behind the real, completed work.

    Fixed by ``bfa9fd68``: doctor's own Dream sat at ``status: specified``
    with all 16/16 of its station's stories done. A Dream already at
    ``"realized"`` is never flagged regardless of completion (it is already
    correct, not stale); a Dream genuinely mid-flight
    (``all_station_stories_done=False``) is never flagged either — both are
    the logical negation of the one condition this predicate names, not
    separate shapes.
    """
    return dream_status == "specified" and all_station_stories_done


#: Filenames this project's own `planning-artifacts/` convention gives a
#: fixed home, findable regardless of inbound reference -- see
#: `is_orphan_file`. Grounded in `ls _bmad-output/projects/pyforge-doctor/
#: planning-artifacts/` (2026-08-15) plus the fleet-wide `PROJECTS.md`.
_CONVENTIONAL_FILENAMES = frozenset(
    {
        "README.md",
        "PROJECTS.md",
        "epics.md",
        # "epics-with-stories.md" removed 2026-09-07 with the artifact itself (marshal
        # Story 32.4, spec-fleet-consistency-standard CAP-3): BMAD 6.12 produces it
        # nowhere, and a line-diff audit of all eight stations confirmed nothing
        # normative lived only there. A file by that name reappearing is now correctly
        # an orphan, not a conventional planning artifact.
        "test-architecture.md",
        "test-design-architecture.md",
        "test-design-qa.md",
        "test-design-progress-system.md",
        "sprint-status-ledger.yaml",
        "deferred-work-ledger.md",
        "marshal-policy.toml",
    }
)

#: Glob-shaped conventional filenames -- a dated/keyed family, not one fixed
#: name -- see `is_orphan_file`.
_CONVENTIONAL_FILENAME_GLOBS = (
    "implementation-readiness-report-*.md",
    ".bmad-config*.toml",
)

#: Directory names whose CONTENTS are conventional regardless of filename --
#: see `is_orphan_file`.
_CONVENTIONAL_DIRECTORIES = frozenset(
    {
        "prds",
        "architecture",
        "briefs",
        "research",
        "retros",
        "specs",
        "test-design",
        "reviews",
    }
)


def is_orphan_file(relpath: str, has_inbound_references: bool) -> bool:
    """``True`` iff nothing else in the repo references ``relpath`` AND its
    filename/subdirectory does not match this project's own observed
    conventional planning-artifact shape — a file findable only by knowing
    it exists, not by directory convention or by another tracked file
    pointing at it.

    **Precondition:** ``relpath`` must already be relative to a station's
    own ``_bmad-output/projects/<slug>/`` root, never repo-root-relative.
    ``_CONVENTIONAL_DIRECTORIES`` membership is checked against every
    ancestor path component (needed for real nested shapes like
    ``prds/prd-pyforge-doctor-2026-07-25/prd.md``), so a repo-root-relative
    path could spuriously match an unrelated directory elsewhere in the repo
    that happens to share one of those six names.

    Fixed by ``f7654a4c`` (CAP-5), against two real fixtures:
    ``archive/_bmad-output/projects/pyforge-atlas/RESUME-EPIC-10.md``
    (self-marked "✅ CLOSED") and ``archive/_bmad-output/projects/
    pyforge-herald/planning-artifacts/intake-video-scripts-manticore-
    2026-07-31.md`` (no closure banner at all — only a "one-time consumed
    draft" note). A self-declared "closed" banner is deliberately NOT
    required: the second fixture has none, and this predicate must classify
    it ``True`` too, so the mechanical rule is narrower than ``f7654a4c``'s
    own commit-message framing — non-conventional name AND zero inbound
    references, nothing more.

    A conventional name is never overridden by the absence of an inbound
    reference (``planning-artifacts/epics.md`` is not orphaned just because
    nothing links to it — it is found by directory convention); conversely a
    non-conventional name IS overridden by the presence of one (a real
    inbound reference means the file is findable, however it is named).
    """
    if has_inbound_references:
        return False
    path = PurePosixPath(relpath)
    if path.name in _CONVENTIONAL_FILENAMES:
        return False
    if any(fnmatch.fnmatch(path.name, pattern) for pattern in _CONVENTIONAL_FILENAME_GLOBS):
        return False
    return not any(part in _CONVENTIONAL_DIRECTORIES for part in path.parts[:-1])
