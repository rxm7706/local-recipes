"""Repo inventory walker + structural artifact classification (Story 9.2,
architecture AD-53/AD-54/AD-55/AD-59/AD-61, PRD FR-80, P-03/P-07).

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

``ArtifactState`` declares all four epics-AC members now (``absent``,
``present-conformant``, ``present-divergent``, ``present-legacy``) even
though this story's own classification logic never emits
``present-legacy`` -- S-9.4 extends this same classifier with the
``legacy_of`` manifest field and is the first story with a real
``PRESENT_LEGACY`` call site (mirrors S-9.1's own "type exists before every
member has a real call site" precedent for ``FindingType``). Per-class
rules, all purely STRUCTURAL (presence/absence and, for
``hybrid-managed-region``, whether S-8.2's ``parse_regions`` finds every
declared region -- never a content-hash comparison, which is S-9.3's own
layer, P-07):

- ``referenced``: always ``present-conformant`` -- ``model/artifact.py``'s
  own ``CLASS_BEHAVIOR`` names this class "not materialized," so there is
  nothing in the repo tree to inspect.
- Any other class, path absent: ``absent``.
- ``hybrid-managed-region``, path present: read as UTF-8 and run
  ``parse_regions``. ``present-conformant`` iff every declared region name
  is among the returned spans; ``present-divergent`` for a missing region,
  a present-but-non-regular-file path, an unreadable or non-UTF-8 file, or a
  ``RegionParseError``/``MarkerError``/``NotImplementedError`` (the last from
  a legally-constructible but reserved ``RegionFormat.SLASHSTAR`` entry) from
  the parser -- all caught here, never propagated, because each is "present
  but not what the manifest expects" (the PRD's own J2 worked example:
  ``CLAUDE.md`` reported ``present-divergent``, resolved by "insert a
  managed region at an anchor").
- Every other present class (``copied-managed``, ``copied-seeded``,
  ``generated-derived``, and V1's ``unclassified-deferred`` escape hatch,
  which gets no special-casing here either): ``present-conformant``.

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

Never in this module (see the story's own Never boundary for the full
list): no content-hash comparison (S-9.3); no ``legacy_of``/
``present-legacy``-producing logic (S-9.4); no ``.marshal/seed-state.yml``
read of any kind (this story depends on S-7.4/S-8.2/S-9.1 only -- no
state-store story); no ``Finding`` construction (a later story's job); no
nested-``.gitignore`` consultation; no ``pathspec``, ``git ls-files``, or
any subprocess/adapter import -- ``detect`` sits below ``adapters/`` in the
module-dependency chain (architecture § Module dependency rules: ``detect``
reaches only ``model``/``state``/``regions``/``engine``/``derive``), so
this module is stdlib-only, matching every sibling ``detect``/``regions``/
``model`` module in this package; and no recursive content comparison for a
directory-shaped whole-file artifact -- a present directory is simply
present.

``classify()`` performs reads only: no writes, no subprocess, no network.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from ..model.manifest import ArtifactClass, Manifest, ManifestEntry
from ..regions.markers import MarkerError
from ..regions.parse import RegionParseError, parse_regions


class ArtifactState(StrEnum):
    """The four-state classification vocabulary the epics AC names
    verbatim, kebab-case wire values matching ``ArtifactClass``/
    ``FindingType``'s established convention. ``PRESENT_LEGACY`` has no
    producing code path in this story -- see the module docstring."""

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
class Inventory:
    """One `classify()` call's full result: the repo root it walked, the
    cached tree (every walked, non-excluded regular file's path,
    POSIX-separated and relative to ``repo_root``), and every manifest
    entry's classification. This is the "walked once, cached" structure the
    epics AC requires -- a caller invokes `classify()` once and reuses this
    for both plan building and finding emission, rather than re-walking the
    tree per consumer."""

    repo_root: Path
    tree: frozenset[str]
    classifications: tuple[Classification, ...]


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
    matches exactly one non-``/`` character, everything else is literal.
    ``re.escape`` happens to escape both glob characters too (as
    ``\\*``/``\\?``), so substituting those two escaped forms back out is
    enough -- no character-by-character loop needed."""
    escaped = re.escape(segment)
    return escaped.replace(r"\*", "[^/]*").replace(r"\?", "[^/]")


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
    except (OSError, UnicodeDecodeError):
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
    except (OSError, UnicodeDecodeError):
        return ArtifactState.PRESENT_DIVERGENT
    # `ManifestEntry.__post_init__` requires a non-None `format` on every
    # hybrid-managed-region entry -- narrows for the type checker; see
    # `cli/init.py`'s identical convention.
    assert entry.format is not None
    try:
        spans = parse_regions(text, entry.format)
    except (RegionParseError, MarkerError, NotImplementedError):
        return ArtifactState.PRESENT_DIVERGENT
    found_names = {span.name for span in spans}
    declared_names = {region.name for region in entry.regions}
    if declared_names <= found_names:
        return ArtifactState.PRESENT_CONFORMANT
    return ArtifactState.PRESENT_DIVERGENT


def _resolve_within_repo(repo_root: Path, entry_path: str) -> Path | None:
    """Resolve ``entry_path`` against ``repo_root``, or ``None`` if the
    result would escape it.

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
    resolved_root = repo_root.resolve()
    candidate = (repo_root / entry_path).resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        return None
    return candidate


def _classify_entry(entry: ManifestEntry, repo_root: Path) -> ArtifactState:
    """One entry's state, per its ``artifact_class`` -- always against a
    DIRECT filesystem check on ``entry.path``, never merely against
    `_walk_tree`'s `Inventory.tree` (the explicit-target carve-out)."""
    if entry.artifact_class is ArtifactClass.REFERENCED:
        # Not materialized (`model/artifact.py`'s own `CLASS_BEHAVIOR`) --
        # nothing in the repo tree to inspect.
        return ArtifactState.PRESENT_CONFORMANT
    target = _resolve_within_repo(repo_root, entry.path)
    if target is None or not target.exists():
        return ArtifactState.ABSENT
    if entry.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION:
        return _classify_hybrid(entry, target)
    # copied-managed / copied-seeded / generated-derived /
    # unclassified-deferred: present is always present-conformant here --
    # content-hash divergence is S-9.3's own layer (P-07), not checked in
    # this story.
    return ArtifactState.PRESENT_CONFORMANT


def classify(manifest: Manifest, repo_root: Path) -> Inventory:
    """This module's public entry point (Story 9.2): one walk of
    ``repo_root`` (`_walk_tree`), then a per-entry structural
    classification -- see the module docstring for the per-class rules.
    Read-only throughout: no write, no subprocess, no network call
    anywhere in this call graph."""
    tree = _walk_tree(repo_root)
    classifications = tuple(
        Classification(entry_id=entry.id, state=_classify_entry(entry, repo_root))
        for entry in manifest.entries
    )
    return Inventory(repo_root=repo_root, tree=tree, classifications=classifications)
