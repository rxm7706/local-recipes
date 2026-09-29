"""Repo inventory walker + structural artifact classification (Stories 9.2
+ 9.4, architecture AD-53/AD-54/AD-55/AD-59/AD-61, PRD FR-80/FR-81, P-03/P-07).

Epic 9's detect stage already has a manifest loader (S-7.4), a whole-file
region parser (S-8.2), and a findings vocabulary (S-9.1) -- but nothing yet
answers "what does this manifest entry actually look like in the target
repo right now," the fact every later plan/finding/hash story needs. This
module is that answer: ``classify(manifest, repo_root) -> Inventory`` walks
``repo_root`` exactly ONCE (the epics AC's "walked once, cached"
requirement -- a caller invokes this once and reuses the returned
``Inventory`` for both plan building and finding emission, rather than each
consumer re-walking the tree itself), then classifies every manifest entry
against that one walk's result plus a direct filesystem check on the
entry's own declared path.

``ArtifactState`` declares all four epics-AC members (``absent``,
``present-conformant``, ``present-divergent``, ``present-legacy``); S-9.2
shipped the type with no ``PRESENT_LEGACY`` call site (mirroring S-9.1's own
"type exists before every member has a real call site" precedent for
``FindingType``), and S-9.4 -- this module's other author -- is the story
that adds it: a present entry whose manifest ``legacy_of`` names a successor
id classifies ``present-legacy`` UNCONDITIONALLY, ahead of every
class-specific structural rule below (see the legacy paragraph after them,
and AD-59: a recognized legacy artifact is "never written to," so Genesis
stops caring about its internal structure the moment ``legacy_of`` is set).
Per-class rules, all purely STRUCTURAL (presence/absence and, for
``hybrid-managed-region``, whether S-8.2's ``parse_regions`` finds every
declared region -- never a content-hash comparison, which is S-9.3's own
layer, P-07):

- ``referenced``: always ``present-conformant`` -- ``model/artifact.py``'s
  own ``CLASS_BEHAVIOR`` names this class "not materialized," so there is
  nothing in the repo tree to inspect. A ``referenced`` entry's own
  ``legacy_of`` (if any) is never consulted -- the legacy short-circuit runs
  only after a real filesystem presence check, and this class returns before
  reaching one.
- Any other class, path absent: ``absent`` -- including a ``legacy_of``-
  bearing entry: legacy classification requires presence, per the module's
  own I/O Matrix (S-9.4).
- ``hybrid-managed-region``, path present: read as UTF-8 and run
  ``parse_regions``. ``present-conformant`` iff every declared region name
  is among the returned spans; ``present-divergent`` for a missing region,
  a present-but-non-regular-file path, an unreadable or non-UTF-8 file, or a
  ``RegionParseError``/``MarkerError``/``NotImplementedError`` (the last from
  a legally-constructible but reserved ``RegionFormat.SLASHSTAR`` entry) from
  the parser -- all caught here, never propagated, because each is "present
  but not what the manifest expects" (the PRD's own J2 worked example:
  ``CLAUDE.md`` reported ``present-divergent``, resolved by "insert a
  managed region at an anchor"). This rule never runs at all for a
  ``legacy_of``-bearing entry -- see below.
- Every other present class (``copied-managed``, ``copied-seeded``,
  ``generated-derived``, and V1's ``unclassified-deferred`` escape hatch,
  which gets no special-casing here either): ``present-conformant``.

**The legacy short-circuit (S-9.4).** A present entry (any class except
``referenced``, which never reaches this point) with ``legacy_of is not
None`` classifies ``present-legacy`` regardless of what its class-specific
structural rule above would otherwise say -- including a
``hybrid-managed-region`` entry whose declared regions are missing, which
would otherwise be ``present-divergent``. This is deliberate, not an
oversight the hybrid rule should also apply: AD-59 frames ``present-legacy``
as "never written to," so once an entry is recognized as legacy, Genesis
never inspects its internal structure again -- the check runs BEFORE the
``hybrid-managed-region`` branch precisely so that branch is never reached
for a legacy entry. ``classify()`` collects every ``present-legacy``
classification into ``Inventory.legacy`` in the same single walk (no second
pass); ``effective_never_write()`` and ``legacy_findings()`` are two of this
module's small legacy consumers, turning that collection into,
respectively, the write-guard set a later plan builder (S-9.6) must honor
and the one INFO ``Finding`` per legacy artifact a ``check`` renderer will
eventually surface.

S-10.8 (FR-83/FR-84's own never-write collision, architecture AD-61) adds
this module's third small consumer: ``writable_exemptions(manifest,
inventory) -> frozenset[str]``, the ALLOW-list counterpart to
``effective_never_write()``'s pure deny-list. A manifest can declare a
``copied-managed``/``copied-seeded`` artifact whose own path ALSO matches a
broader ``never_write`` glob meant to cover other files under it (the
shipped manifest's own ``dreams-readme`` -- ``docs/dreams/README.md`` --
under ``docs/dreams/*.md``) -- ``fnmatch`` has no negation, so the guard
cannot express "deny this glob except that one path" as a single pattern.
``writable_exemptions`` resolves that: every entry whose ``artifact_class``
is ``COPIED_MANAGED`` or ``COPIED_SEEDED`` (the epics AC's own two named
classes; ``REFERENCED``/``GENERATED_DERIVED``/``HYBRID_MANAGED_REGION``/
``UNCLASSIFIED_DEFERRED`` are never exempted this way) contributes its
``path``, minus every path already in ``inventory.legacy`` -- AD-59 still
wins: a path that is ALSO recognized as ``present-legacy`` is never
writable, even if a manifest-declared writable entry happens to share its
location. Like ``effective_never_write()``, it trusts ``manifest.entries``
and ``inventory.legacy`` exactly as given (already ``applies_to``-filtered
by the caller) and performs no filesystem access of its own beyond what
``inventory`` already recorded. ``effective_never_write()`` itself is
UNCHANGED by this addition -- it stays the pure deny-list; the caller
(``verbs/adopt.py``'s ``run_adopt``) passes both into ``fs.NeverWrite``'s
two separate fields (``patterns``/``exempt``), never merging them here.

An entry's own declared ``path`` is always checked DIRECTLY against the
live filesystem, regardless of the walk's own exclusion rules below (the
epics AC's "unless an artifact explicitly targets them" carve-out) --
exclusions only shrink ``Inventory.tree``, the cached walk result; they
never hide a manifest-named path from classification. That direct check
first resolves the path safely WITHIN ``repo_root`` (`_resolve_within_repo`)
-- an absolute or ``../``-traversing ``entry.path`` (a shape
``ManifestEntry`` itself does not reject) is classified ``absent`` rather
than ever dereferenced outside the target repo.

The walk itself prunes two independent things while descending, never
after the fact: a directory named ``.git``, ``node_modules``, or ``.pixi``
at any depth, and every path the repo-ROOT ``.gitignore`` matches (V1: root
only, no nested ``.gitignore`` files -- real git's negation semantics
interacting with nested-file precedence is out of this story's bounded
scope, and a target repo's root ``.gitignore`` is the common case this
package's own repo, and the PRD's worked examples, exercise). The matcher
is a hand-rolled ``gitwildmatch`` subset (comments, blank lines, ``!``
negation with last-match-wins semantics, a trailing unescaped ``/`` for
directory-only, repo-root anchoring whenever the pattern carries a ``/``
ANYWHERE before the end -- leading (``/only-root.txt``) or embedded
(``docs/generated``), matching real gitignore's own rule, not merely a
leading slash -- ``*``/``?`` glob translation that does NOT cross ``/``
boundaries, and ``**`` support that DOES, with a trailing ``**`` segment
(``build/**``) translated as an unconditional "everything inside", distinct
from a leading/middle ``**``'s optional "zero or more segments") --
directly mirroring ``model/version.py``'s own documented
precedent for the identical class of decision ("pulling in a real SemVer
package for ~80 lines of grammar is exactly the kind of speculative
dependency Simplicity First forbids"): a root-only ``gitwildmatch`` subset
is comparably bounded, and this package's own module-dependency rule
already forbids the one dependency-free alternative (shelling out to
``git``, which lives in ``adapters/vcs_git.py``, unreachable from
``detect``). ``**`` support specifically exists because this repo's own
root ``.gitignore`` uses patterns shaped like ``.idea/**/workspace.xml``.

Never in this module (see each story's own Never boundary for the full
list): no content-hash comparison (S-9.3, a different layer -- P-07); no
``.marshal/seed-state.yml`` read of any kind (no state-store story exists
yet); no automated Tier-1 -> Tier-2 migration logic of any kind (AD-59,
explicitly out of V1 -- S-9.4's own Never boundary; ``LegacyRecord`` is a
pure in-memory precursor, never a migration actuator); no ``Action``/plan-
exclusion logic (S-9.6's own job, a later story -- this module only produces
the ``effective_never_write()``/``Inventory.legacy`` primitives that story
consumes); no nested-``.gitignore`` consultation; no ``pathspec``,
``git ls-files``, or any subprocess/adapter import -- ``detect`` sits below
``adapters/`` in the module-dependency chain (architecture § Module
dependency rules: ``detect`` reaches only ``model``/``state``/``regions``/
``engine``/``derive``), so this module is stdlib-only aside from its own
sibling ``.findings`` import (S-9.4 -- the identical precedent
``hashes.py`` already set for a ``detect``-internal import, not a new
external dependency), matching every sibling ``detect``/``regions``/
``model`` module in this package; and no recursive content comparison for a
directory-shaped whole-file artifact -- a present directory is simply
present.

S-9.4 adds this module's first ``Finding`` construction: ``legacy_findings()``
builds one INFO ``legacy-present`` ``Finding`` per ``LegacyRecord``, via
``Finding.new`` (``hashes.py``'s own construction convention) -- never
``HARD``/``DRIFT``, and no ``classify()`` classification outcome in this
module ever constructs a ``Finding`` beyond that one call site.

S-9.5 (FR-69/SC-10, architecture AD-54) adds this module's second and last:
``coverage_findings()``/``coverage_counts()`` give manifest coverage its own
explicit, independently testable definition, mirroring the split
``effective_never_write()``/``legacy_findings()`` already established --
without it, SC-10's "100% manifest coverage" claim rested entirely on
``ManifestEntry.__post_init__`` (S-7.4/7.5, ``model/manifest.py``) never
having a bug, with no second, decoupled gate. Unlike every other function in
this module, both take a bare ``Manifest`` -- no ``Inventory``/``repo_root``
-- because coverage is intrinsic to the manifest alone, not a property of
the target repo the way `classify()`'s own per-entry filesystem check is.
Both explicitly re-verify ``entry.artifact_class``/``entry.rationale`` via
``isinstance``/direct inspection rather than trusting the loader's
guarantee that produced ``entry`` in the first place -- defense in depth,
the same "structural guarantee is not enough, verify explicitly" stance
``Finding.__post_init__`` itself already takes for its own ``remedy`` field.
An entry fails coverage when either ``entry.artifact_class`` is not a
genuine ``ArtifactClass`` member, or it is
``ArtifactClass.UNCLASSIFIED_DEFERRED`` with a blank ``rationale``.
``coverage_findings()`` emits one HARD ``uncovered`` ``Finding`` per failing
entry, in manifest entry order (matching `legacy_findings`'s own ordering
convention); ``coverage_counts()`` buckets every entry by class wire-value
or the literal ``"uncovered"`` key -- sparse, `Counter`-style, never
zero-padded for a class with no entries -- so
``sum(coverage_counts(manifest).values()) == len(manifest.entries)`` always
holds. Both route through one private ``_uncovered_reason()`` check so the
two can never drift on what "covered" means (mirroring `hashes.py`'s own
``_hash_mismatch_detail`` precedent: one private "why" helper, several
public callers).

``classify()`` performs reads only: no writes, no subprocess, no network.
"""

from __future__ import annotations

import os
import re
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from ..model.manifest import ArtifactClass, Manifest, ManifestEntry
from ..regions.markers import MarkerError
from ..regions.parse import RegionParseError, parse_regions
from .findings import Finding, FindingType, Severity


class ArtifactState(StrEnum):
    """The four-state classification vocabulary the epics AC names
    verbatim, kebab-case wire values matching ``ArtifactClass``/
    ``FindingType``'s established convention. ``PRESENT_LEGACY``'s first
    producing code path is `_classify_entry`'s legacy short-circuit (S-9.4)
    -- see the module docstring."""

    ABSENT = "absent"
    PRESENT_CONFORMANT = "present-conformant"
    PRESENT_DIVERGENT = "present-divergent"
    PRESENT_LEGACY = "present-legacy"


@dataclass(frozen=True)
class Classification:
    """One manifest entry's classified state. Carries no ``__post_init__``
    validation, unlike ``model/manifest.py``'s ``ManifestEntry`` -- this
    dataclass is `classify`'s own COMPUTED OUTPUT, never externally
    supplied data to validate (the same reasoning ``model/artifact.py``'s
    ``ClassBehavior`` gives for its own unvalidated shape), and both fields
    are already well-typed by construction: ``entry_id`` comes from a
    ``ManifestEntry.id`` `load_manifest` already required to be a non-blank
    str, and ``state`` is always a real ``ArtifactState`` member this
    module itself produced."""

    entry_id: str
    state: ArtifactState


@dataclass(frozen=True)
class LegacyRecord:
    """One entry classified `present-legacy` (S-9.4): its own id and path,
    plus the successor id its manifest ``legacy_of`` names. Carries no
    ``__post_init__`` validation, for the same reason `Classification` above
    carries none -- this is `classify`'s own COMPUTED OUTPUT, built only from
    an already-validated ``ManifestEntry``'s own ``id``/``path``/
    ``legacy_of`` fields (`model/manifest.py`'s ``__post_init__`` already
    guarantees each is a non-blank str, and ``legacy_of`` is non-``None`` by
    construction -- see `classify`).

    This is the pure in-memory precursor a future state store (no
    `state/store.py` yet) will serialize into ``state.legacy[]`` -- mirroring
    S-9.3's own ``recorded_sha``-is-a-caller-supplied-parameter precedent:
    this module produces the fact, a later story persists it."""

    entry_id: str
    path: str
    legacy_of: str


@dataclass(frozen=True)
class Inventory:
    """One `classify()` call's full result: the repo root it walked, the
    cached tree (every walked, non-excluded regular file's path,
    POSIX-separated and relative to ``repo_root``), every manifest entry's
    classification, and every `LegacyRecord` for an entry classified
    `present-legacy` (S-9.4, same field order as `classify`'s own
    `Classification` list -- manifest entry order, since both are built from
    one pass over ``manifest.entries``). This is the "walked once, cached"
    structure the epics AC requires -- a caller invokes `classify()` once and
    reuses this for both plan building and finding emission, rather than
    re-walking the tree per consumer."""

    repo_root: Path
    tree: frozenset[str]
    classifications: tuple[Classification, ...]
    legacy: tuple[LegacyRecord, ...]


# Pruned by directory NAME, at any depth -- never descended into, regardless
# of any manifest entry's own path (which is still checked directly, per
# the module docstring's explicit-target carve-out -- this set only shrinks
# `Inventory.tree`).
_EXCLUDED_DIR_NAMES = frozenset({".git", "node_modules", ".pixi"})


@dataclass(frozen=True)
class _GitignoreRule:
    """One compiled root-``.gitignore`` line: the regex to test with
    ``.fullmatch()`` (never ``.match()`` -- no embedded ``^``/``$``
    anchors, matching ``model/version.py``'s own documented convention: a
    ``$``-anchored pattern alone matches immediately before a trailing
    ``"\\n"``), whether the line was ``!``-negated, and whether its
    original trailing ``/`` restricts it to directories only."""

    pattern: re.Pattern[str]
    negated: bool
    dir_only: bool


def _translate_segment_to_regex(segment: str) -> str:
    """Translate one gitignore glob SEGMENT (no ``/`` inside it) to a regex
    fragment: ``*`` matches any run of characters except ``/``, ``?``
    matches exactly one non-``/`` character, a bracket expression
    (``[abc]``, ``[a-z]``, ``[!abc]``/``[^abc]`` negated) becomes the
    equivalent regex character class, everything else is literal.

    Confirmed live against this repo's own root ``.gitignore``, which uses
    bracket expressions extensively (``*.py[cod]``, ``[Dd]ebug/``,
    ``[Ww][Ii][Nn]32/``, dozens more) -- a blanket ``re.escape`` (the
    prior form) turns ``[cod]`` into a literal 5-character string nothing
    ever matches, so every one of those exclusions silently matched
    nothing at all. An unterminated ``[`` (no closing ``]``) falls back to
    a literal ``[``, matching real gitignore's own tolerance for that
    shape."""
    pieces: list[str] = []
    index = 0
    length = len(segment)
    while index < length:
        char = segment[index]
        if char == "*":
            pieces.append("[^/]*")
            index += 1
        elif char == "?":
            pieces.append("[^/]")
            index += 1
        elif char == "[":
            negated = segment[index + 1 : index + 2] in ("!", "^")
            search_from = index + 2 if negated else index + 1
            end = segment.find("]", search_from)
            if end == -1:
                pieces.append(re.escape(char))
                index += 1
                continue
            inner = segment[search_from:end]
            inner = inner.replace("\\", "\\\\").replace("]", "\\]")
            pieces.append(f"[{'^' if negated else ''}{inner}]")
            index = end + 1
        else:
            pieces.append(re.escape(char))
            index += 1
    return "".join(pieces)


def _translate_pattern_to_regex(pattern: str, *, anchored: bool) -> re.Pattern[str]:
    """Translate one gitignore pattern body (``!`` negation and any
    dir-only trailing ``/`` already stripped by the caller) into a regex
    matched with ``.fullmatch()`` against a POSIX-relative path from
    ``repo_root``.

    ``**`` is translated per path SEGMENT (split on ``/``): a lone ``**``
    segment becomes "zero or more full path segments," absorbing one of its
    own adjacent literal slashes -- so ``.idea/**/workspace.xml`` (this
    repo's own root ``.gitignore``) matches both the zero-intermediate-dir
    case (``.idea/workspace.xml``) and any deeper one. An UNANCHORED
    pattern (no leading ``/``) additionally matches at any depth, prefixed
    with the same "zero or more leading segments" fragment.

    A TRAILING ``**`` segment (the pattern's last, e.g. ``build/**``) is a
    special case, handled separately from a leading/middle one: real git
    defines it as "matches everything inside" the preceding prefix, which is
    an UNCONDITIONAL ``.*`` after the prefix's own ``/`` -- never the
    optional ``(?:.*/)?`` a leading/middle ``**`` uses. Reusing the optional
    form here would require the matched string to end in a literal ``/``
    (fine for a bare directory, but no regular file path this module walks
    ever carries one), so every trailing-``**`` pattern would silently
    match nothing at all -- confirmed by review against this repo's own
    root ``.gitignore``, which uses exactly this shape.
    """
    if pattern == "**":
        body = ".*"
    else:
        segments = pattern.split("/")
        pieces: list[str] = []
        previous_was_double_star = False
        for index, segment in enumerate(segments):
            if index > 0 and not previous_was_double_star:
                pieces.append("/")
            if segment == "**":
                if index == len(segments) - 1:
                    pieces.append(".*")
                else:
                    pieces.append("(?:.*/)?")
                previous_was_double_star = True
            else:
                pieces.append(_translate_segment_to_regex(segment))
                previous_was_double_star = False
        body = "".join(pieces)
    if not anchored:
        body = f"(?:.*/)?{body}"
    return re.compile(body)


def _iter_gitignore_lines(text: str) -> Iterator[tuple[str, bool, bool]]:
    """Yield ``(pattern_body, negated, dir_only)`` for every non-comment,
    non-blank line of a ``.gitignore``'s text, in file order -- the order
    `_is_gitignored`'s last-match-wins negation depends on.
    ``pattern_body`` still carries its own leading ``/`` (if any); the
    caller resolves anchoring."""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        negated = line.startswith("!")
        if negated:
            line = line[1:]
        dir_only = line.endswith("/")
        if dir_only:
            line = line[:-1]
        if not line:
            continue
        yield line, negated, dir_only


def _load_gitignore_rules(repo_root: Path) -> tuple[_GitignoreRule, ...]:
    """Parse ``repo_root/.gitignore`` (V1: root only -- see the module
    docstring) into an ordered rule tuple. A missing, unreadable, or
    non-UTF-8 ``.gitignore`` yields no rules -- degrading to "nothing is
    gitignore-excluded" rather than raising, matching this story's own I/O
    Matrix ("No error" on every row)."""
    gitignore_path = repo_root / ".gitignore"
    try:
        text = gitignore_path.read_text(encoding="utf-8")
    except OSError, UnicodeDecodeError:
        return ()
    rules: list[_GitignoreRule] = []
    for pattern_body, negated, dir_only in _iter_gitignore_lines(text):
        # Real gitignore semantics (confirmed by review, previously missed
        # here): a pattern is anchored to the `.gitignore`'s own directory
        # whenever it contains a `/` ANYWHERE before the end -- not only a
        # LEADING one. `pattern_body` has already had its dir-only trailing
        # `/` stripped by `_iter_gitignore_lines`, so a sole-trailing-slash
        # pattern like `build/` (now bare `build`) correctly stays
        # unanchored here, while an embedded one like `docs/generated` or
        # this repo's own `.idea/**/workspace.xml` is now correctly
        # anchored -- previously both incorrectly matched at any depth.
        anchored = "/" in pattern_body
        pattern_body = pattern_body.removeprefix("/")
        if not pattern_body:
            continue
        rules.append(
            _GitignoreRule(
                pattern=_translate_pattern_to_regex(pattern_body, anchored=anchored),
                negated=negated,
                dir_only=dir_only,
            )
        )
    return tuple(rules)


def _is_gitignored(rel_posix: str, *, is_dir: bool, rules: tuple[_GitignoreRule, ...]) -> bool:
    """Whether ``rel_posix`` (a POSIX-relative path from ``repo_root``) is
    excluded by ``rules`` -- last-match-wins across the whole ordered list,
    real gitignore semantics: a later rule (an unnegated re-exclusion, or a
    ``!`` negation) overrides an earlier one that also matched."""
    ignored = False
    for rule in rules:
        if rule.dir_only and not is_dir:
            continue
        if rule.pattern.fullmatch(rel_posix) is not None:
            ignored = not rule.negated
    return ignored


def _walk_tree(repo_root: Path) -> frozenset[str]:
    """One walk of ``repo_root`` -- `classify` calls this exactly once per
    invocation, the epics AC's "walked once, cached" requirement. Returns
    the POSIX-relative path of every regular file NOT pruned by the fixed
    ``.git``/``node_modules``/``.pixi`` directory-name set (at any depth)
    or by the repo-root ``.gitignore``. Both exclusions are applied WHILE
    walking (pruned directories are never descended into) -- this function
    only shrinks `Inventory.tree`; `classify` checks an entry's own
    declared path directly against the filesystem, bypassing this result
    entirely (the module docstring's explicit-target carve-out)."""
    rules = _load_gitignore_rules(repo_root)
    tree: set[str] = set()
    for dirpath, dirnames, filenames in os.walk(repo_root):
        current_dir = Path(dirpath)
        kept_dirnames = []
        for dirname in dirnames:
            if dirname in _EXCLUDED_DIR_NAMES:
                continue
            dir_rel = (current_dir / dirname).relative_to(repo_root).as_posix()
            if _is_gitignored(dir_rel, is_dir=True, rules=rules):
                continue
            kept_dirnames.append(dirname)
        # Mutating `dirnames` IN PLACE is what tells `os.walk` (topdown, the
        # default) not to descend into a pruned directory at all --
        # reassigning the loop variable itself would have no effect.
        dirnames[:] = kept_dirnames

        for filename in filenames:
            file_path = current_dir / filename
            if not file_path.is_file():
                continue
            file_rel = file_path.relative_to(repo_root).as_posix()
            if _is_gitignored(file_rel, is_dir=False, rules=rules):
                continue
            tree.add(file_rel)
    return frozenset(tree)


def _classify_hybrid(entry: ManifestEntry, target: Path) -> ArtifactState:
    """A present ``hybrid-managed-region`` entry: ``present-conformant``
    iff every declared region name is found by `parse_regions`; every other
    outcome (not a regular file, unreadable, non-UTF-8, or a
    structure/grammar/unimplemented-format error) is ``present-divergent``
    -- all "present but not what the manifest expects" (see the module
    docstring). Every exception `parse_regions`/`read_text` can raise for a
    legally-constructible entry is caught here and turned into that same
    state, never propagated -- including a reserved ``RegionFormat.SLASHSTAR``
    entry (a real, ``ManifestEntry``-legal value that
    ``markers.parse_marker_line`` rejects with a bare ``NotImplementedError``,
    confirmed by review to otherwise crash this whole function instead of
    degrading like every sibling error path) and an OS-level read failure
    (permissions, a race after the ``is_file()`` check above -- the same
    ``OSError`` class `_load_gitignore_rules` already catches for its own,
    analogous read)."""
    if not target.is_file():
        return ArtifactState.PRESENT_DIVERGENT
    try:
        text = target.read_text(encoding="utf-8")
    except OSError, UnicodeDecodeError:
        return ArtifactState.PRESENT_DIVERGENT
    # `ManifestEntry.__post_init__` requires a non-None `format` on every
    # hybrid-managed-region entry -- narrows for the type checker; see
    # `cli/init.py`'s identical convention.
    assert entry.format is not None
    try:
        spans = parse_regions(text, entry.format)
    except RegionParseError, MarkerError, NotImplementedError:
        return ArtifactState.PRESENT_DIVERGENT
    found_names = {span.name for span in spans}
    declared_names = {region.name for region in entry.regions}
    if declared_names <= found_names:
        return ArtifactState.PRESENT_CONFORMANT
    return ArtifactState.PRESENT_DIVERGENT


def _resolve_within_repo(repo_root: Path, resolved_root: Path, entry_path: str) -> Path | None:
    """Resolve ``entry_path`` against ``repo_root``, or ``None`` if the
    result would escape it. ``resolved_root`` is ``repo_root.resolve()``,
    computed once by `classify` and threaded through -- re-resolving the
    same fixed root on every manifest entry would repeat the same
    filesystem lookup for no benefit, unlike `_walk_tree`'s own "walked
    once, cached" tree, which is genuinely expensive to redo.

    ``ManifestEntry.path`` (``model/manifest.py``) validates only that the
    string is non-blank -- an absolute path (``/etc/hostname``) or a
    ``../``-traversal is not rejected there, and ``Path.__truediv__``
    silently DISCARDS ``repo_root`` entirely when the right operand is
    absolute (documented ``pathlib`` behavior). Confirmed by review: without
    this guard, such an entry makes classification read an arbitrary host
    path instead of anything under the target repo -- this module's whole
    reason for taking ``repo_root`` as an argument. Detect's job is
    classifying artifacts WITHIN the target repo, so an entry whose declared
    path resolves outside it is never "present" from this module's own
    vantage point, regardless of what exists elsewhere on the host --
    `_classify_entry` treats a ``None`` result the same as ``ABSENT``."""
    candidate = (repo_root / entry_path).resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        return None
    return candidate


def _classify_entry(entry: ManifestEntry, repo_root: Path, resolved_root: Path) -> ArtifactState:
    """One entry's state, per its ``artifact_class`` -- always against a
    DIRECT filesystem check on ``entry.path``, never merely against
    `_walk_tree`'s `Inventory.tree` (the explicit-target carve-out)."""
    if entry.artifact_class is ArtifactClass.REFERENCED:
        # Not materialized (`model/artifact.py`'s own `CLASS_BEHAVIOR`) --
        # nothing in the repo tree to inspect. `entry.legacy_of` (if any) is
        # never consulted for this class -- the legacy short-circuit below
        # only runs once a real filesystem presence check has passed, and a
        # referenced entry never reaches one.
        return ArtifactState.PRESENT_CONFORMANT
    target = _resolve_within_repo(repo_root, resolved_root, entry.path)
    if target is None or not target.exists():
        return ArtifactState.ABSENT
    # S-9.4: a present entry naming a successor is `present-legacy`
    # UNCONDITIONALLY -- ahead of the `hybrid-managed-region` structural
    # check below, which a legacy entry must never reach (AD-59: "never
    # written to" means Genesis stops inspecting a recognized legacy
    # artifact's internal structure, so a hybrid-managed-region entry with a
    # missing declared region does not fall through to present-divergent
    # once legacy_of is set -- see the module docstring).
    if entry.legacy_of is not None:
        return ArtifactState.PRESENT_LEGACY
    if entry.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION:
        return _classify_hybrid(entry, target)
    # copied-managed / copied-seeded / generated-derived /
    # unclassified-deferred: present is always present-conformant here --
    # content-hash divergence is S-9.3's own layer (P-07), not checked in
    # this story.
    return ArtifactState.PRESENT_CONFORMANT


def classify(manifest: Manifest, repo_root: Path) -> Inventory:
    """This module's public entry point (Story 9.2, extended by S-9.4): one
    walk of ``repo_root`` (`_walk_tree`), then a per-entry structural
    classification -- see the module docstring for the per-class rules.
    ``Inventory.legacy`` is built from that SAME pass, one `LegacyRecord`
    per entry whose computed state is `present-legacy` (S-9.4's own "no
    second pass, no extra filesystem access" requirement) -- never a
    separate walk over ``manifest.entries``. Read-only throughout: no
    write, no subprocess, no network call anywhere in this call graph."""
    tree = _walk_tree(repo_root)
    resolved_root = repo_root.resolve()
    classifications: list[Classification] = []
    legacy: list[LegacyRecord] = []
    for entry in manifest.entries:
        state = _classify_entry(entry, repo_root, resolved_root)
        classifications.append(Classification(entry_id=entry.id, state=state))
        if state is ArtifactState.PRESENT_LEGACY:
            # `entry.legacy_of` is guaranteed non-None here -- it is the
            # only way `_classify_entry` produces `PRESENT_LEGACY`.
            assert entry.legacy_of is not None
            legacy.append(LegacyRecord(entry_id=entry.id, path=entry.path, legacy_of=entry.legacy_of))
    return Inventory(
        repo_root=repo_root,
        tree=tree,
        classifications=tuple(classifications),
        legacy=tuple(legacy),
    )


def effective_never_write(manifest: Manifest, inventory: Inventory) -> frozenset[str]:
    """The write-guard set a later plan builder (S-9.6) must honor: every
    manifest-declared ``never_write`` pattern, UNION the ``path`` of every
    `LegacyRecord` in ``inventory.legacy``. A legacy artifact is never
    written to (AD-59) whether or not the manifest's own ``never_write`` list
    happens to already name its path -- folding it in here means S-9.6 needs
    only ONE set to consult, not two independent ones it could forget to
    check both of."""
    return frozenset(manifest.never_write) | {record.path for record in inventory.legacy}


# The exempt classes `writable_exemptions` ever draws from -- the epics AC's
# own two named classes (see that function's own docstring, and the module
# docstring's S-10.8 paragraph, for why the other four never qualify).
_WRITABLE_EXEMPTION_CLASSES = frozenset({ArtifactClass.COPIED_MANAGED, ArtifactClass.COPIED_SEEDED})


def writable_exemptions(manifest: Manifest, inventory: Inventory) -> frozenset[str]:
    """The exact-path allow-list `fs.NeverWrite.exempt`/rung 4's own exempt
    check ultimately enforce (S-10.8): every entry's ``path`` whose
    ``artifact_class`` is in `_WRITABLE_EXEMPTION_CLASSES`, MINUS every path
    already in ``inventory.legacy`` -- AD-59's "never written to" still wins
    even when a manifest-declared writable entry happens to name the same
    location a legacy record also claims (module docstring's own S-10.8
    paragraph). Like `effective_never_write`, trusts ``manifest.entries`` as
    given (already ``applies_to``-filtered by the caller -- it does not
    itself inspect ``entry.applies_to`` against "the running verb") and
    performs no filesystem access beyond what ``inventory`` already
    recorded.

    Deliberately does NOT consult `classify()`'s own per-entry
    `ArtifactState` at all -- unlike `effective_never_write`, which only
    ever draws from `inventory.legacy` (a state-derived collection), this
    function draws from `manifest.entries` directly: a `copied-managed`/
    `copied-seeded` entry that is currently `ABSENT` (the ordinary "create
    it for the first time" case, and the shape this story's own confirmed
    defect reproduces) still needs its path exempted, precisely because the
    write that would MAKE it present is the one rung 4 was refusing."""
    legacy_paths = {record.path for record in inventory.legacy}
    return (
        frozenset(entry.path for entry in manifest.entries if entry.artifact_class in _WRITABLE_EXEMPTION_CLASSES)
        - legacy_paths
    )


def legacy_findings(inventory: Inventory) -> tuple[Finding, ...]:
    """One INFO ``legacy-present`` `Finding` per `LegacyRecord` in
    ``inventory.legacy``, in that same order (manifest entry order -- see
    `classify`) -- never ``HARD``/``DRIFT`` (AD-59: a recognized legacy
    artifact is a preserved, intentional convention, not a conformance
    problem). Each message names both the artifact's own path and its
    successor id (``record.legacy_of``), so a human reading the finding
    knows what superseded it without cross-referencing the manifest.
    Constructed via `Finding.new` (never bare `Finding(...)`), matching
    `hashes.py`'s own construction convention -- so `remedy` always resolves
    from `REMEDIES[FindingType.LEGACY_PRESENT]` rather than being hand-typed
    here."""
    return tuple(
        Finding.new(
            Severity.INFO,
            FindingType.LEGACY_PRESENT,
            record.path,
            f"{record.path}: superseded by '{record.legacy_of}'; preserved, never modified",
        )
        for record in inventory.legacy
    )


def _uncovered_reason(entry: ManifestEntry) -> str | None:
    """Why ``entry`` fails S-9.5's coverage rule, or ``None`` if it passes --
    the single shared definition `coverage_findings`/`coverage_counts` both
    consult, so the two can never drift on what "covered" means (see the
    module docstring).

    Re-verifies ``entry.artifact_class``/``entry.rationale`` directly rather
    than trusting `ManifestEntry.__post_init__` (S-7.4/7.5) already having
    enforced both -- defense in depth. Both checks are ``isinstance`` guards,
    deliberate on both fields (not ``entry.artifact_class in ArtifactClass``,
    not a bare ``entry.rationale.strip()``, not a truthiness test): a caller
    that force-sets either field past ``__post_init__``
    (``object.__setattr__``, as this module's own tests do to reach these
    otherwise-unreachable branches) can leave a plain ``str`` equal to a real
    ``ArtifactClass`` member's own value (which would otherwise read as
    covered despite carrying no genuine class identity, since
    ``ArtifactClass`` is a ``StrEnum``) or a non-``str`` ``rationale``
    (``None`` included) that ``.strip()`` would raise on instead of
    reporting as uncovered -- exactly the "never assumed from the field's
    static type" defensive re-check this story exists to add, applied
    symmetrically to both fields it inspects."""
    if not isinstance(entry.artifact_class, ArtifactClass):
        return f"artifact_class {entry.artifact_class!r} is not a valid ArtifactClass member"
    if entry.artifact_class is ArtifactClass.UNCLASSIFIED_DEFERRED and (
        not isinstance(entry.rationale, str) or not entry.rationale.strip()
    ):
        return "unclassified-deferred entry has a blank rationale"
    return None


def coverage_findings(manifest: Manifest) -> tuple[Finding, ...]:
    """One HARD ``uncovered`` `Finding` per entry `_uncovered_reason` fails,
    in manifest entry order (matching `legacy_findings`'s own ordering
    convention) -- S-9.5's own explicit, independently testable second gate
    on SC-10's "100% manifest coverage" claim (see the module docstring).
    Constructed via `Finding.new` (never bare `Finding(...)`), matching
    every other real call site in this module, so `remedy` always resolves
    from `REMEDIES[FindingType.UNCOVERED]` (already documented, S-9.1)
    rather than being hand-typed here."""
    findings: list[Finding] = []
    for entry in manifest.entries:
        reason = _uncovered_reason(entry)
        if reason is None:
            continue
        findings.append(
            Finding.new(
                Severity.HARD,
                FindingType.UNCOVERED,
                entry.path,
                f"{entry.id}: {reason}",
            )
        )
    return tuple(findings)


def coverage_counts(manifest: Manifest) -> dict[str, int]:
    """One bucket per class actually present in ``manifest.entries``, keyed
    by wire value (``entry.artifact_class.value``, e.g. ``"copied-managed"``)
    -- sparse, `Counter`-style, never zero-padded for a class with no
    entries in this manifest. An entry `_uncovered_reason` fails is counted
    under the literal key ``"uncovered"`` instead, so
    ``sum(coverage_counts(manifest).values()) == len(manifest.entries)``
    always holds, whether or not every entry passes coverage. Built via
    ``Counter`` -- matching `test_seed_templates_manifest.py`'s own
    ``Counter(entry.artifact_class for entry in manifest.entries)`` idiom for
    the identical per-class tally -- rather than a hand-rolled
    ``dict.get``/increment loop."""
    keys = (
        "uncovered" if _uncovered_reason(entry) is not None else entry.artifact_class.value
        for entry in manifest.entries
    )
    return dict(Counter(keys))
