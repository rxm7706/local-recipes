"""The ``derived-context`` layer's pure half (Story 28.8,
SPEC-marshal-token-economy CAP-5).

Story 28.1 gave marshal a declared ``[context]`` block whose fourth layer
is ``derived-context``; nothing consumed it. The thing that layer is ABOUT
lives in the ``bmad-build-auto`` skill: ``step-01-clarify-and-route.md``
item 1.A.2 decides whether a cached ``epic-<N>-context.md`` distill is
still usable by asking whether *any* file anywhere under
``planning-artifacts/`` has a newer mtime, and item 1.A.5 re-reads the
previous story's spec for continuity every single iteration. Both are
cache-validity HUNCHES: landing one unrelated story spec invalidates every
epic's distill (an over-eager recompile that re-reads the 65k-token
``epics.md`` and the 46k-token ``PRD.md`` for nothing), while an edit to a
planning document that arrives with an older mtime than the distill is
missed entirely (a stale cache that silently misleads).

This module owns the DECLARATION half of replacing that hunch: which
derived artifacts exist for an epic, which planning sources each one is
derived FROM, and how the freshness answer maps back onto them. It is
pure -- no filesystem, no ``os``, no subprocess (AD-4, enforced by this
package's own import-linter contract). ``cli/context.py`` does the
directory listing and the manifest write; ``adapters/scribe_cli.py`` owns
the subprocess.

**Marshal does not compute freshness.** The incremental-derivation engine
is Scribe's ``compile_surface`` cocoindex extra (scribe Story 6.2;
unifying-strategy Grounding 2026-08-30: "cocoindex is a ``compile_surface``
extra that writes *through* ``GraphStore``, not a GraphStore engine"), and
marshal binds it strictly through the ``scribe index refresh`` CLI grammar
the ``pyforge-scribe`` SKILL.md declares -- never ``import cocoindex``
(this story's own Block-If), never ``import pyforge.scribe`` (that SKILL's
own "the CLI is the public contract"), never a second fingerprint
mechanism of marshal's own (the Never bullet's "a marshal-private
cocoindex flow"). What marshal contributes is the DECLARATION -- the
artifact names and their source sets -- plus the layer flag Story 28.1
already renders; the extra owns the "did these sources change" answer.

**The declared sources are the skill's own document vocabulary, verbatim.**
``EPIC_CONTEXT_SOURCE_PATTERNS`` is copied from
``step-01-clarify-and-route.md``'s own path-B listing (PRD ``*prd*``,
Architecture ``*architecture*``, UX/Design ``*ux*``, Epics ``*epic*``,
Product Brief ``*brief*``) -- the exact set ``compile-epic-context.md``
distills from. Story specs, sprint ledgers, retros, and research notes are
deliberately NOT sources: the distill never reads them, so their churn was
never a reason to recompile it. Narrowing WHICH files count as sources is
the freshness mechanism changing; what the distill contains, its 800-1500
token target, and where it lives are untouched (this story's AC 4).

**The continuity distill's output is layer-gated, and that is deliberate.**
Item 1.A.5's previous-story continuity is extracted fresh every iteration
and never written to disk today. "Incrementally maintained" is meaningless
without something to keep, so an ENABLED layer materializes the extract at
``epic-<N>-continuity.md``, beside the epic-context distill in the same
gitignored Tier-3 directory, and reuses it while its declared sources (the
same-epic story specs) are unchanged. With the layer OFF -- the default,
and the whole fleet's state today -- the skill writes nothing and behaves
exactly as it does now (AC 3). The epic-context distill's own content
contract, token target, and location are untouched either way (the
story's Block-If).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from fnmatch import fnmatchcase

__all__ = (
    "DERIVED_CONTEXT_LAYER",
    "EPIC_CONTEXT_SOURCE_PATTERNS",
    "MODE_COMPILE_ON_HUNCH",
    "MODE_INCREMENTAL",
    "SCRIBE_DECLARE_OPTION",
    "SCRIBE_REFRESH_ARGV",
    "STATE_FRESH",
    "STATE_STALE",
    "STATE_UNKNOWN",
    "ArtifactFreshness",
    "DerivedArtifactDeclaration",
    "continuity_artifact_name",
    "continuity_output_relpath",
    "continuity_source_pattern",
    "declare_derived_context",
    "epic_context_artifact_name",
    "epic_context_output_relpath",
    "implementation_artifacts_relpath",
    "layer_aggressiveness",
    "layer_enabled",
    "manifest_payload",
    "parse_refresh_report",
    "planning_artifacts_relpath",
    "planning_specs_relpath",
    "render_scribe_refresh_argv",
    "resolve_freshness",
    "select_sources",
    "valid_epic",
)

#: The ``CONTEXT_LAYER_NAMES`` member (``core/policy.py``) this story makes
#: load-bearing. Spelled here rather than imported as a bare index so a
#: reader of this module sees which of the five layers it implements; the
#: binding to the closed vocabulary is asserted by this story's own tests.
DERIVED_CONTEXT_LAYER = "derived-context"

#: The two ways an iteration can decide a cached distill's validity.
#: ``incremental`` is this story's mechanism (the scribe extra answered);
#: ``compile-on-hunch`` is today's mtime rule, which stays the behavior for
#: a declared-off layer AND for every degradation path -- an unavailable
#: instrument disables its layer with a named finding, never blocks a run.
MODE_INCREMENTAL = "incremental"
MODE_COMPILE_ON_HUNCH = "compile-on-hunch"

#: Per-artifact freshness. ``fresh`` = the extra skipped it (sources
#: unchanged -> zero recompute); ``stale`` = the extra refreshed it (the
#: sources moved -> exactly one recompute); ``unknown`` = the extra
#: reported neither, which is a contract miss, never silently read as
#: "fresh" (a wrong "fresh" serves a stale distill, the exact failure this
#: story exists to remove).
STATE_FRESH = "fresh"
STATE_STALE = "stale"
STATE_UNKNOWN = "unknown"

#: The scribe CLI grammar marshal binds to, in ONE place (pyforge-scribe
#: SKILL.md, "Index" section). ``--declare`` hands the engine a caller's
#: own ``DerivedArtifact`` registrations instead of scribe's own two: the
#: generic "declare sources -> derived artifact" surface scribe Story 6.2
#: exposed and whose Design Notes name marshal Story 28.8 as its next
#: consumer. ``adapters/scribe_cli.py`` reports a scribe that does not
#: accept it as an ordinary layer degradation, never a crash.
SCRIBE_REFRESH_ARGV: tuple[str, ...] = ("index", "refresh")
SCRIBE_DECLARE_OPTION = "--declare"

#: ``step-01-clarify-and-route.md``'s own path-B planning-document
#: vocabulary, verbatim and in its order. Matched case-insensitively
#: against the plain filenames of ``*.md`` files directly inside a
#: project's ``planning-artifacts/`` -- the same shallow listing the skill
#: itself does ("List files in {{.planning_artifacts}}").
EPIC_CONTEXT_SOURCE_PATTERNS: tuple[str, ...] = (
    "*prd*",
    "*architecture*",
    "*ux*",
    "*epic*",
    "*brief*",
)

#: An epic identifier is the plain integer the skill's own "Identify the
#: epic number {epic_num}" step resolves. Anything else is a caller error
#: rather than a source set -- it would interpolate into an artifact name
#: and a glob.
_EPIC_PATTERN = re.compile(r"[0-9]+")

#: Scribe's own reported output grammar (``cli.py::index_refresh``):
#: ``refreshed: <names>; skipped (unchanged): <names> -> <index path>``.
#: The trailing ``-> path`` is optional here so the off-mode line (which
#: has none) parses through the same expression.
_REPORT_PATTERN = re.compile(
    r"refreshed:\s*(?P<refreshed>.*?);\s*"
    r"skipped\s*\(unchanged\):\s*(?P<skipped>.*?)\s*(?:->.*)?$"
)

#: Scribe prints this for an empty side of the report line.
_EMPTY_LIST_TOKEN = "(none)"

#: A refreshed entry may carry a per-artifact count in parentheses
#: (``graphify-ingest (1 node(s))``) -- marshal's declarations carry none,
#: but the grammar allows it, so the suffix is stripped rather than
#: producing a name no declaration can match.
_COUNT_SUFFIX = re.compile(r"\s*\(.*\)\s*$")


@dataclass(frozen=True)
class DerivedArtifactDeclaration:
    """One "these sources -> this derived artifact" registration.

    ``name`` is the identity the scribe extra fingerprints against, so it
    must be stable across iterations (it is derived from the project slug
    and epic, never from a timestamp or a run id). ``sources`` are
    repo-relative POSIX paths, sorted, and may name a file that does not
    exist -- the extra's own source signature records an absent path as
    absent, so a DELETED planning document still changes the signature
    instead of silently vanishing. ``output`` is the derived file this
    artifact produces, or ``None`` for a distill that is loaded into a
    session's context rather than written (the continuity distill)."""

    name: str
    sources: tuple[str, ...]
    output: str | None = None


@dataclass(frozen=True)
class ArtifactFreshness:
    """One declaration's answer from the extra: ``state`` is one of
    ``STATE_FRESH``/``STATE_STALE``/``STATE_UNKNOWN``, carried alongside
    the declaration it answers so a caller renders both without a second
    lookup."""

    name: str
    state: str
    sources: tuple[str, ...]
    output: str | None = None


def valid_epic(epic: object) -> bool:
    """Whether ``epic`` is usable as an epic identifier -- a plain,
    non-empty run of digits. Checked before it is interpolated into an
    artifact name or a glob."""
    return isinstance(epic, str) and _EPIC_PATTERN.fullmatch(epic) is not None


def planning_artifacts_relpath(project_slug: str) -> str:
    """The project's tracked planning-artifacts directory, repo-relative.

    Spelled literally (never via ``_bmad-output/planning-artifacts``, the
    per-worktree symlink) -- CLAUDE.md's standing parallel-agent rule."""
    return f"_bmad-output/projects/{project_slug}/planning-artifacts"


def planning_specs_relpath(project_slug: str) -> str:
    """Where a landed story spec is promoted to (the tracked source of
    record for per-story intent contracts)."""
    return f"{planning_artifacts_relpath(project_slug)}/specs"


def implementation_artifacts_relpath(project_slug: str) -> str:
    """The project's Tier-3 implementation-artifacts directory -- where the
    epic-context distill lives and where step-01 scans for previous-story
    continuity."""
    return f"_bmad-output/projects/{project_slug}/implementation-artifacts"


def epic_context_artifact_name(project_slug: str, epic: str) -> str:
    """The scribe-side identity of an epic's context distill."""
    return f"marshal:{project_slug}:epic-{epic}-context"


def continuity_artifact_name(project_slug: str, epic: str) -> str:
    """The scribe-side identity of an epic's previous-story continuity
    distill."""
    return f"marshal:{project_slug}:epic-{epic}-continuity"


def epic_context_output_relpath(project_slug: str, epic: str) -> str:
    """Exactly where the skill already writes the distill -- unchanged by
    this story (AC 4: only the freshness mechanism changes)."""
    return f"{implementation_artifacts_relpath(project_slug)}/epic-{epic}-context.md"


def continuity_output_relpath(project_slug: str, epic: str) -> str:
    """Where an ENABLED layer keeps the previous-story continuity extract,
    beside the epic-context distill in the same gitignored Tier-3
    directory. Written only while the layer is on -- see this module's own
    docstring for why the default (layer off) writes nothing at all."""
    return f"{implementation_artifacts_relpath(project_slug)}/epic-{epic}-continuity.md"


def continuity_source_pattern(epic: str) -> str:
    """The same-epic story-spec glob step-01 item 1.A.5's continuity scan
    reads. Matched case-insensitively against plain filenames."""
    return f"spec-{epic}-*.md"


def select_sources(
    directory_relpath: str,
    filenames: Iterable[str],
    patterns: Sequence[str],
    *,
    suffix: str = ".md",
) -> tuple[str, ...]:
    """The repo-relative paths under ``directory_relpath`` whose filename
    ends with ``suffix`` and matches at least one of ``patterns``.

    Pure: the caller supplies the listing. Matching is case-insensitive
    (``PRD.md`` and ``prd.md`` are the same document to the skill, which
    describes its patterns in lowercase) and deduplicated -- a name
    matching two patterns contributes one source, not two. Sorted, so the
    declaration a manifest carries is byte-stable across iterations and
    cannot itself look like a change."""
    lowered_patterns = tuple(pattern.lower() for pattern in patterns)
    lowered_suffix = suffix.lower()
    selected: set[str] = set()
    for filename in filenames:
        lowered = filename.lower()
        if lowered_suffix and not lowered.endswith(lowered_suffix):
            continue
        if any(_glob_match(lowered, pattern) for pattern in lowered_patterns):
            selected.add(f"{directory_relpath}/{filename}")
    return tuple(sorted(selected))


def _glob_match(name: str, pattern: str) -> bool:
    """``fnmatchcase``, never ``fnmatch.fnmatch``: the latter normalizes
    case through ``os.path.normcase``, so the same declaration would
    resolve differently on a case-insensitive filesystem than on the linux
    loop fleet. Both arguments are already lowercased by the caller, which
    is where this module's own case-insensitivity comes from."""
    return fnmatchcase(name, pattern)


def declare_derived_context(
    *,
    project_slug: str,
    epic: str,
    planning_filenames: Iterable[str],
    planning_spec_filenames: Iterable[str] = (),
    implementation_filenames: Iterable[str] = (),
) -> tuple[DerivedArtifactDeclaration, ...]:
    """The two derived-context artifacts for ``epic``, with their declared
    sources resolved from caller-supplied directory listings.

    The epic-context distill's sources are the planning documents
    ``compile-epic-context.md`` actually reads. The continuity distill's
    sources are the same-epic story specs step-01 item 1.A.5 scans, in BOTH
    places this repo keeps them: the tracked ``planning-artifacts/specs/``
    (the promoted source of record) and the gitignored
    ``implementation-artifacts/`` (where a run drafts one first).

    Raises ``ValueError`` for a malformed slug or epic -- both interpolate
    into an artifact identity and a path, so a bad value is a caller
    contract violation, not a finding this pure layer could report."""
    if not project_slug or "/" in project_slug or "\\" in project_slug or ".." in project_slug:
        raise ValueError(f"invalid project slug: {project_slug!r}")
    if not valid_epic(epic):
        raise ValueError(f"invalid epic identifier: {epic!r}")

    epic_sources = select_sources(
        planning_artifacts_relpath(project_slug),
        planning_filenames,
        EPIC_CONTEXT_SOURCE_PATTERNS,
    )
    spec_pattern = (continuity_source_pattern(epic),)
    continuity_sources = select_sources(
        planning_specs_relpath(project_slug), planning_spec_filenames, spec_pattern
    ) + select_sources(
        implementation_artifacts_relpath(project_slug),
        implementation_filenames,
        spec_pattern,
    )
    return (
        DerivedArtifactDeclaration(
            name=epic_context_artifact_name(project_slug, epic),
            sources=epic_sources,
            output=epic_context_output_relpath(project_slug, epic),
        ),
        DerivedArtifactDeclaration(
            name=continuity_artifact_name(project_slug, epic),
            sources=tuple(sorted(continuity_sources)),
            output=continuity_output_relpath(project_slug, epic),
        ),
    )


def manifest_payload(
    declarations: Sequence[DerivedArtifactDeclaration],
) -> dict[str, object]:
    """The JSON body marshal hands the scribe grammar's ``--declare``.

    Plain, JSON-safe data only, sorted by artifact name: the manifest is
    written on every invocation, and an unstable ordering would churn a
    file for no reason. ``output`` is carried through as ``null`` for the
    continuity distill rather than omitted, so every entry has the same
    key set."""
    return {
        "artifacts": [
            {
                "name": declaration.name,
                "sources": list(declaration.sources),
                "output": declaration.output,
            }
            for declaration in sorted(declarations, key=lambda item: item.name)
        ]
    }


def render_scribe_refresh_argv(binary_path: str, manifest_path: str) -> tuple[str, ...]:
    """The one place the scribe grammar's argv is spelled."""
    return (binary_path, *SCRIBE_REFRESH_ARGV, SCRIBE_DECLARE_OPTION, manifest_path)


def parse_refresh_report(text: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
    """Scribe's ``refreshed: ...; skipped (unchanged): ...`` report line,
    split into the two name tuples -- ``None`` when no such line is
    present.

    Reads the LAST matching line, not the first: the grammar emits
    ``warning: ...`` lines to stderr but a caller may hand this combined
    output, and a future scribe that prints a preamble must not shadow the
    real report."""
    match = None
    for line in text.splitlines():
        candidate = _REPORT_PATTERN.search(line.strip())
        if candidate is not None:
            match = candidate
    if match is None:
        return None
    return (
        _split_names(match.group("refreshed")),
        _split_names(match.group("skipped")),
    )


def _split_names(segment: str) -> tuple[str, ...]:
    stripped = segment.strip()
    if not stripped or stripped == _EMPTY_LIST_TOKEN:
        return ()
    names = []
    for chunk in stripped.split(","):
        name = _COUNT_SUFFIX.sub("", chunk.strip()).strip()
        if name and name != _EMPTY_LIST_TOKEN:
            names.append(name)
    return tuple(names)


def resolve_freshness(
    declarations: Sequence[DerivedArtifactDeclaration],
    *,
    refreshed: Sequence[str],
    skipped: Sequence[str],
) -> tuple[ArtifactFreshness, ...]:
    """Map the extra's answer back onto the declarations, in declaration
    order.

    ``skipped`` (sources unchanged) is the zero-recompute case and reads
    ``fresh``; ``refreshed`` (the extra re-derived it) reads ``stale`` --
    the caller must recompile. A declaration the extra named in NEITHER
    list reads ``unknown``, never ``fresh``: silently treating an
    unanswered artifact as current is exactly the stale-cache failure this
    story removes. ``refreshed`` wins over ``skipped`` for the (contract-
    violating) case of a name appearing in both -- the conservative
    direction is always "recompute"."""
    refreshed_set = set(refreshed)
    skipped_set = set(skipped)
    results: list[ArtifactFreshness] = []
    for declaration in declarations:
        if declaration.name in refreshed_set:
            state = STATE_STALE
        elif declaration.name in skipped_set:
            state = STATE_FRESH
        else:
            state = STATE_UNKNOWN
        results.append(
            ArtifactFreshness(
                name=declaration.name,
                state=state,
                sources=declaration.sources,
                output=declaration.output,
            )
        )
    return tuple(results)


def layer_enabled(layer: Mapping[str, object] | None) -> bool:
    """Whether the declared ``derived-context`` layer is on. ``None`` (no
    layer resolved at all) reads as off -- the same "layer absent = off"
    rule ``policy.resolve_context_layers`` composes, never re-derived."""
    return bool((layer or {}).get("enabled", False))


def layer_aggressiveness(layer: Mapping[str, object] | None) -> str | None:
    """The declared aggressiveness rung, or ``None`` when the layer
    declares none. This story shapes and reports it; CAP-8's graduated
    ladder is the story that escalates it."""
    value = (layer or {}).get("aggressiveness")
    return value if isinstance(value, str) else None
