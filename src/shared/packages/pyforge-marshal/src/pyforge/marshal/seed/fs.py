"""``seed/fs.py`` -- the never-write-guarded filesystem primitive (Story
7.3, architecture AD-61, FR-71).

Every module under ``seed/`` that ever touches a target repo's filesystem is
expected to go through exactly this module: an immutable ``NeverWrite``
pattern set plus three guarded functions -- ``write``, ``replace_span``, and
``remove`` -- each resolving its target path to an absolute, symlink-
resolved form and checking it against ``NeverWrite`` *before* touching the
filesystem at all, raising ``NeverWriteViolation`` (Story 7.2) on a match.
FR-71's never-write set (Tier-0 Dreams, Tier-2 planning artifacts, Tier-3,
legacy specs, BMAD installer files) has no enforcement mechanism anywhere
else in this package; this module IS that mechanism. Story 8.3
(``seed/regions/apply.py``, span substitution) is the first concrete
consumer -- its own AC requires writing "through ``fs.replace_span()`` --
never ``Path.write_text``".

``write``/``replace_span`` delegate the actual atomic write to
``pyforge.core.atomic_write.atomic_write_bytes`` (Story 14.2) -- this module
adds no new atomic-write mechanics of its own, only the guard in front of
the existing one.

**Why ``fnmatch``, not a hand-rolled ``**``-aware matcher.**
``pathlib.Path.match()`` at this package's Python 3.12 floor does not
support recursive ``**`` at all (that lands in 3.13's ``full_match``).
``fnmatch.fnmatch`` already treats a run of ``*`` characters as "match
anything including ``/``" -- which makes ``**/planning-artifacts/**`` and a
single ``*`` behave identically under it, exactly the over-matching-is-safe
direction a never-write guard wants, without adding a new dependency or a
bespoke glob engine for a six-pattern list.

**Why the guard resolves for matching but I/O runs against the caller's
original path.** The guard's own resolution is used ONLY to evaluate the
never-write match; the actual I/O (`atomic_write_bytes`/`unlink`) runs
against the caller-supplied `path` unchanged, mirroring `ports/fs.py`'s own
split between `resolve_path` (a probe) and `write_text_atomic` (an
operation on the given path). This has two confirmed, accepted
consequences, both out of this story's scope to hardern further: (1) if
`path`'s own LEAF is a live symlink, `os.replace`/`unlink` acts on the link
itself, not its target -- POSIX `rename(2)` never follows a symlink at its
destination -- so `write`/`replace_span` REPLACE the symlink with a regular
file (orphaning whatever it pointed at) rather than writing through it;
confirmed by direct execution, and the opposite of an earlier draft of this
docstring's claim. No real V1 target artifact (`CLAUDE.md`, `AGENTS.md`,
`.gitignore`, a hybrid-managed-region file) is itself expected to be a
symlink, so this module does not special-case it. (2) There is a
check-then-act (TOCTOU) window between `_guard`'s resolution and the
delegate's own file open: a PARENT-chain symlink swapped in that window
could point the actual I/O somewhere the guard never evaluated. Closing
that would need `O_NOFOLLOW`/fd-based syscalls throughout (`atomic_write`
does not offer this), a scope disproportionate to this tool's threat model
(a local CLI operating on a repo its own operator already controls, not a
sandbox defending against a co-located adversarial process racing the
filesystem mid-syscall) and to this story's own AC, whose one concrete
symlink scenario is a static, already-in-place indirection, not a race.

**Why ``replace_span`` reads the file itself rather than taking pre-read
bytes.** Centralizing read+splice+write in one guarded primitive is what
makes "only the bytes between the markers change; every byte outside the
span is identical" a property of this module itself, provable once, rather
than a discipline every future caller (``regions/apply.py``, and whatever
eventually calls ``update``/``adopt``) has to re-derive correctly on their
own. ``replace_span`` reads with ``path.read_bytes()`` -- never
``read_text`` -- because text-mode I/O can silently translate line endings,
corrupting the byte offsets ``RegionSpan.body_span`` promises (S-8.2's own
byte-not-character discipline, mirrored here).

This module imports ``pyforge.core.atomic_write.atomic_write_bytes`` and
``pyforge.marshal.seed.errors.NeverWriteViolation`` and nothing else from
either ``pyforge.core`` or ``pyforge.marshal`` -- the architecture's "``fs``
imports nothing from the package except ``errors``". It never constructs a
``NeverWrite`` from a ``Manifest`` (a future ``verbs/``-level orchestrator's
job), and it never wraps a generic ``OSError`` (a missing file, a
permission error) from ``read_bytes``/``unlink``/``atomic_write_bytes`` into
any ``SeedError`` leaf -- only a never-write match raises
``NeverWriteViolation``; every other I/O failure propagates unchanged,
matching ``atomic_write``'s own "never introduces a new exception type"
contract.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path

from pyforge.core.atomic_write import atomic_write_bytes

from .errors import NeverWriteViolation


@dataclass(frozen=True)
class NeverWrite:
    """An immutable set of never-write glob patterns, plus an explicit
    exact-path allow-list checked BEFORE them (Story 10.8).

    ``patterns`` carries plain glob strings -- the exact shape
    ``Manifest.never_write`` already carries (Story 7.4) -- never a
    ``Manifest`` object itself (this module must not import ``model``, see
    the module docstring's import-surface bullet). ``frozen=True`` plus a
    ``tuple`` field makes BOTH attribute reassignment (``.patterns = ...``,
    ``FrozenInstanceError``) and element mutation (``.patterns[0] = ...``,
    ``TypeError`` -- tuples are already immutable) raise -- but only once
    ``patterns`` genuinely IS a ``tuple`` of STRIPPED strings: a type hint
    alone is not runtime enforcement, and a caller passing a ``list`` would
    defeat element-level immutability silently (review finding).
    ``__post_init__`` below coerces a ``list`` and strips each pattern the
    same way ``Manifest.never_write``'s own ``__post_init__`` already does
    (Story 7.4 precedent) -- both halves of it: a follow-up review pass
    caught that an earlier draft here coerced the container but forgot the
    strip, so a pattern with stray padding (e.g. a YAML block-scalar typo
    like ``" docs/dreams/*.md"``) would pass validation as non-blank yet
    never match any real, unpadded path -- silently protecting nothing
    while still LOOKING like an active rule. Stripping at construction is
    exactly what closes that gap, and is why ``Manifest.never_write`` does
    it too.

    ``exempt`` is a SEPARATE, EXACT-path allow-list -- never a glob, never
    folded into ``patterns`` -- for the one case ``fnmatch`` has no way to
    express: a manifest-declared writable artifact (``copied-managed``/
    ``copied-seeded``, e.g. ``docs/dreams/README.md``) whose own resolved
    path also matches a BROADER deny glob that must otherwise keep covering
    every other path under it (``docs/dreams/*.md``). ``fnmatch`` has no
    negation, so narrowing the glob string itself would either fail to
    protect every other file it names or require an enumerated,
    existence-dependent rewrite that stops protecting a not-yet-existing
    future file (see ``detect.inventory.writable_exemptions``'s own
    docstring for the full rationale) -- an allow-list checked BEFORE the
    deny-list, in `_matches` below, is the only mechanism that satisfies
    both "the named path is writable" and "every other path matching the
    same glob still refuses". Validated on the SAME principle as
    ``patterns`` -- every member a stripped, non-blank ``str`` -- so a
    caller passing a malformed exempt set fails loudly at construction
    rather than degrading into "nothing is exempt" or a bare ``TypeError``
    from deep inside `_matches`, but MORE LENIENT on container shape:
    coerced from a ``list``, ``set``, OR ``tuple`` to a ``frozenset``
    (``patterns`` coerces a ``list`` only, into a ``tuple`` -- pattern
    ORDER is observable there, since `_matches` reports the FIRST matching
    pattern, while `exempt` is a pure membership set with no order to
    preserve, so the extra container leniency costs nothing). Defaults to
    ``frozenset()`` so every ``NeverWrite(...)``
    construction that predates this field (every call site in this
    package's own test suite until Story 10.8) stays valid unchanged."""

    patterns: tuple[str, ...]
    exempt: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        patterns = tuple(self.patterns) if isinstance(self.patterns, list) else self.patterns
        if not isinstance(patterns, tuple) or not all(
            isinstance(item, str) and item.strip() for item in patterns
        ):
            raise ValueError(
                f"NeverWrite.patterns must contain only non-blank str, got {self.patterns!r}"
            )
        object.__setattr__(self, "patterns", tuple(item.strip() for item in patterns))

        exempt = (
            frozenset(self.exempt)
            if isinstance(self.exempt, (list, set, tuple))
            else self.exempt
        )
        if not isinstance(exempt, frozenset) or not all(
            isinstance(item, str) and item.strip() for item in exempt
        ):
            raise ValueError(
                f"NeverWrite.exempt must contain only non-blank str, got {self.exempt!r}"
            )
        object.__setattr__(self, "exempt", frozenset(item.strip() for item in exempt))


def _matches(never_write: NeverWrite, relative_posix_str: str) -> str | None:
    """The first pattern in ``never_write.patterns`` that matches
    ``relative_posix_str``, or ``None`` if none does -- but ``None``
    IMMEDIATELY, before any pattern is even considered, when
    ``relative_posix_str`` is itself a member of ``never_write.exempt``
    (Story 10.8). The exempt check is a membership test against exact,
    already-resolved paths -- cheap, and deliberately evaluated first so an
    exempt artifact never pays for, or risks disagreeing with, the glob loop
    below.

    Matching uses ``fnmatch.fnmatchcase`` uniformly for every pattern -- no
    distinct ``**``-vs-``*`` handling (see the module docstring's "Why
    ``fnmatch``" note). ``fnmatchcase``, not the platform-``normcase``-folding
    ``fnmatch.fnmatch``: the latter case-folds via ``os.path.normcase``,
    which lowercases on Windows (``ntpath.normcase``) but is a documented
    no-op on EVERY POSIX platform including macOS (``posixpath.normcase``'s
    own docstring: "Has no effect under Posix" -- confirmed by reading its
    source; a follow-up review pass caught that an earlier draft of this
    note incorrectly attributed macOS's case-insensitivity to this same
    ``normcase`` call, when a default macOS filesystem's case-insensitivity
    is actually a SEPARATE, filesystem/VFS-level property `fnmatch` has no
    visibility into and this guard does not attempt to detect or normalize
    against). ``fnmatchcase`` is still the right choice: it makes matching
    deterministic and platform-INDEPENDENT (never folds, on any OS), which
    is what a safety guard wants -- `docs/dreams/*.md` refuses the same set
    of paths regardless of which platform evaluates it, rather than
    depending on Windows's own case-folding to save it. Patterns are checked in
    order and the FIRST hit wins; which one wins among several simultaneous
    matches is not a meaningful distinction for a guard whose only job is
    "block or don't", so no further tie-breaking is defined."""
    if relative_posix_str in never_write.exempt:
        return None
    for pattern in never_write.patterns:
        if fnmatch.fnmatchcase(relative_posix_str, pattern):
            return pattern
    return None


def _guard(path: Path, *, repo_root: Path, never_write: NeverWrite) -> None:
    """The one check ``write``, ``replace_span``, and ``remove`` all share,
    run before any of them touches the filesystem.

    Resolves both ``path`` and ``repo_root`` via ``Path.resolve()``
    (non-strict, symlink-following -- matching ``ports/fs.py::resolve_path``'s
    own documented convention, see the module docstring's second Design
    Note), computes the resolved path relative to the resolved
    ``repo_root`` in POSIX form, and falls back to the resolved path's own
    absolute POSIX string when ``path`` is not under ``repo_root`` at all
    (no pattern is repo-external today, but this must not crash). Raises
    ``NeverWriteViolation`` naming the matched pattern AND both the
    caller-supplied and resolved paths in its message on a hit (review
    finding: the message previously showed only the unresolved ``path`` --
    unhelpful for exactly the symlink-indirect case resolution exists to
    catch, where the caller-visible path gives no hint which real,
    resolved location actually matched); returns ``None`` silently
    otherwise.

    Raises ``ValueError`` upfront if ``repo_root`` does not resolve to an
    existing directory (review finding): without this, a caller passing a
    wrong or misspelled ``repo_root`` silently degrades every repo-relative
    pattern (the common case -- see the module's own `docs/dreams/*.md`
    example) to the repo-external absolute-path fallback, which cannot
    match it -- turning "deny" into a silent "allow" for the exact
    misconfiguration this codebase's own history flags as a recurring
    failure mode. Failing loudly here converts that into an immediate,
    diagnosable error instead."""
    resolved_root = repo_root.resolve()
    if not resolved_root.is_dir():
        raise ValueError(
            f"repo_root {repo_root} does not resolve to an existing directory"
            f" ({resolved_root}) -- refusing to guard against a repo root that may be"
            " wrong, since every repo-relative never-write pattern would silently stop"
            " matching"
        )
    resolved_path = path.resolve()
    try:
        relative_posix_str = resolved_path.relative_to(resolved_root).as_posix()
    except ValueError:
        relative_posix_str = resolved_path.as_posix()

    matched = _matches(never_write, relative_posix_str)
    if matched is not None:
        raise NeverWriteViolation(
            f"{path} (resolved: {resolved_path}) matches never-write pattern {matched!r}",
            remedy=(
                "choose a target path outside the never-write set, or update the"
                " manifest's never-write patterns if this file is meant to be writable"
            ),
        )


def write(path: Path, data: bytes, *, repo_root: Path, never_write: NeverWrite) -> None:
    """Write ``data`` to ``path`` atomically, after the never-write guard
    clears.

    Guards FIRST -- a matching ``path`` never reaches
    ``atomic_write_bytes`` at all, so the filesystem is left completely
    untouched (no temp file, no ``os.replace``). On a clear guard, delegates
    to ``atomic_write_bytes`` (Story 14.2): a temp-file-then-``os.replace``
    write, so an interrupted write cannot truncate an existing ``path`` --
    the underlying exception propagates unchanged on failure, per this
    module's own "no new exception type" contract."""
    _guard(path, repo_root=repo_root, never_write=never_write)
    atomic_write_bytes(path, data)


def replace_span(
    path: Path,
    start: int,
    end: int,
    new_body: bytes,
    *,
    repo_root: Path,
    never_write: NeverWrite,
) -> None:
    """Splice ``new_body`` into ``path`` in place of the byte range
    ``[start, end)``, and write the result atomically.

    Guards FIRST -- a matching ``path`` is never even read. On a clear
    guard, reads ``path.read_bytes()`` (never ``read_text``, see the module
    docstring's third Design Note), splices via
    ``data[:start] + new_body + data[end:]`` -- the exact reconstruction
    identity ``regions/parse.py``'s own Design Notes already document -- and
    writes the result through ``atomic_write_bytes``. Every byte outside
    ``[start, end)`` is therefore byte-identical to the original file; this
    function never re-reads or re-derives the region markers themselves,
    that is the caller's (``regions/apply.py``, Story 8.3) job.

    Raises ``ValueError`` if ``0 <= start <= end <= len(original)`` does not
    hold. Without this, ordinary Python slice semantics accept a negative,
    inverted, or out-of-range span silently -- producing a corrupted
    (duplicated- or dropped-byte-range) splice instead of failing loudly,
    which would directly undermine the "every byte outside the span is
    identical" guarantee this docstring claims (review finding). This is a
    caller-contract violation (a programmer bug in the byte offsets passed
    in), not a filesystem failure or a never-write violation, so it is a
    plain ``ValueError`` -- outside the ``SeedError`` taxonomy, matching
    this module's own "no wrapping of generic errors" Never-boundary.
    Likewise raises ``TypeError`` upfront if ``new_body`` is not ``bytes``
    (review finding: without this, a caller accidentally passing ``str`` --
    plausible, since "new region content" naturally starts life as text
    elsewhere -- previously fell through to a bare, contextless
    ``TypeError: can't concat str to bytes object`` from inside the splice
    expression; this raises the same exception type but names the
    argument and its actual type, matching this function's other
    upfront-validated failure)."""
    if not isinstance(new_body, bytes):
        raise TypeError(f"new_body must be bytes, got {type(new_body).__name__}")
    _guard(path, repo_root=repo_root, never_write=never_write)
    original = path.read_bytes()
    if not (0 <= start <= end <= len(original)):
        raise ValueError(
            f"invalid span [{start}, {end}) for {path} ({len(original)} bytes)"
        )
    spliced = original[:start] + new_body + original[end:]
    atomic_write_bytes(path, spliced)


def remove(path: Path, *, repo_root: Path, never_write: NeverWrite) -> None:
    """Remove ``path``, after the never-write guard clears.

    Guards FIRST -- a matching ``path`` is never unlinked. On a clear
    guard, delegates to ``Path.unlink()`` directly: any ``OSError`` (a
    missing file, a permission error, or -- since ``unlink()`` is
    deliberately not ``rmdir()`` -- an ``IsADirectoryError`` if ``path``
    names a directory) propagates unchanged, per this module's own "no new
    exception type" contract. This module offers no directory-removal
    primitive of its own (unlike `ports/fs.py`'s separate
    `remove_empty_dir`); a directory target is simply an ordinary
    `Path.unlink()` failure here."""
    _guard(path, repo_root=repo_root, never_write=never_write)
    path.unlink()
