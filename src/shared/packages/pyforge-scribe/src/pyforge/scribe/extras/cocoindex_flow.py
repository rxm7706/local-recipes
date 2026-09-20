"""pyforge.scribe.extras.cocoindex_flow -- the cocoindex `compile_surface`
incremental-ingest extra (Story 6.2, unifying-strategy Grounding
2026-08-30: "cocoindex is a `compile_surface` extra that writes *through*
`GraphStore`, not a GraphStore engine -- the freshness *engine*, never a
store of record"; stack.md "Estate leverage": "`cocoindex` + `graphifyy` |
scribe | `scribe index`: AST graph + incremental index ... | bind").

Exposes a GENERIC "declare sources -> derived artifact" surface
(`DerivedArtifact` + `refresh_incremental`) that any caller can register
against -- Story 6.1's two derived artifacts (the graphify-ingested code
graph, the foundry-cutover move list) are this story's own first, concrete
consumers (wired into `scribe index refresh`, see `cli.py`), never
special-cased here. A future consumer (marshal Story 28.8's epic-context/
continuity distills) binds to the SAME `scribe index refresh`-shaped CLI
grammar declared in the scribe SKILL.md, never to this module's internals
(AD-7).

**Why `memo_fingerprint`, not the reactive component/App/Runner runtime.**
cocoindex 1.0.20's top-level surface is a live, reactive dataflow runtime
(`mount`/`mount_each`/`use_state`/`Environment`/`App`/`Runner`) built to run
as a long-lived process incrementally re-rendering "components" as their
inputs change. Standing that runtime up here would itself become exactly
the kind of "long-running daemon scribe doesn't own" this story's own
Boundaries & Constraints block. `scribe` is a CLI that is invoked, does its
work, and exits -- never a daemon. `cocoindex.memo_fingerprint(obj)` is the
one piece of that same engine that is a plain, synchronous, stateless
function: it is cocoindex's own canonicalizing content-fingerprint
primitive (the same one the reactive runtime uses internally to decide
whether a memoized computation needs to re-run), usable standalone with no
`Environment`/`App`/event loop and, empirically, zero network calls. Using
it for change detection here genuinely binds "cocoindex's ... model for
change detection" (this spec's Design Notes) without adopting the
long-running pieces of the engine this story explicitly may not adopt.

**The incremental model.** A caller declares one or more `DerivedArtifact`s
-- a name, the source paths (files or directories) the artifact depends on,
and a zero-arg `derive()` callback that recomputes and writes the artifact
(through the `GraphStore` persist port, or as a derived gitignored file --
AC3, never a second store-of-record). `refresh_incremental()` fingerprints
each artifact's current sources with `cocoindex.memo_fingerprint`, compares
against the fingerprint recorded on the PREVIOUS `refresh_incremental()`
call (persisted in a small JSON index alongside `graph.json`, itself a
derived, gitignored artifact -- AC3), and calls `derive()` ONLY for an
artifact whose sources changed (or that has never run before). An artifact
whose sources are unchanged is skipped entirely -- its previously-written
output is left untouched, so "zero recompute" also means "zero risk of
losing a prior artifact's content" (no `store.reset()`-shaped full-rebuild
step is anywhere in this module).

The persisted index holds ONLY `{artifact_name: fingerprint_hex}` pairs --
never node content, citations, or any other fact. It is bookkeeping for
"did this change", not a graph, and is never queried by `recall.py` (AC3).

`cocoindex` is imported ONLY inside this module, and only lazily inside
`_import_cocoindex()` -- declaring the optional `pyforge-scribe[cocoindex]`
extra never requires the heavy dependency until a caller actually invokes
`refresh_incremental()`. Mirrors `extras/graphify.py::_import_graphify()`
exactly (AC4). No `cocoindex.serve` call and no `@coco.fn`/`@cocoindex.fn`
decorator appear anywhere in this package (AC4) -- OpenLineage rides CAP-8,
not a cocoindex-native lineage surface.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from pyforge.core.atomic_write import atomic_write_text
from pyforge.core.errors import PyforgeError

from pyforge.scribe.compile import _rglob_excluding

#: Off by default (air-gap, AD-6) -- only a truthy value turns the extra on.
COCOINDEX_EXTRA_ENV = "SCRIBE_COCOINDEX_EXTRA"
_TRUTHY = frozenset({"1", "true", "yes", "on"})


class CocoindexUnavailableError(PyforgeError):
    """`cocoindex` is not installed but the cocoindex extra was explicitly
    invoked -- install the `pyforge-scribe[cocoindex]` extra (or the
    `cocoindex` conda package)."""


@dataclass(frozen=True)
class DerivedArtifact:
    """One declared "sources -> derived artifact" registration -- the
    generic surface this story exposes. ``sources`` are repo-relative or
    absolute paths (files or directories); ``derive`` is a zero-arg callback
    that recomputes and writes the artifact when called. Nothing here is
    graph/move-list-specific -- `cli.py::index_refresh` is simply this
    module's first caller.
    """

    name: str
    sources: tuple[Path, ...]
    derive: Callable[[], None]


@dataclass(frozen=True)
class RefreshResult:
    """What one `refresh_incremental()` call did, for the CLI layer to
    report back. ``refreshed``/``skipped`` are artifact names, in the order
    they were declared."""

    refreshed: tuple[str, ...]
    skipped: tuple[str, ...]
    index_path: Path


def cocoindex_extra_enabled() -> bool:
    """Off by default (AD-6) -- only a truthy `SCRIBE_COCOINDEX_EXTRA` turns
    the incremental (skip-if-unchanged) behavior on. Callers that are
    themselves an explicit, deliberate invocation (matching
    `extras/graphify.py::ingest_repo`'s own "an explicit CLI invocation is
    already the opt-in" contract) may choose not to consult this at all."""
    return os.environ.get(COCOINDEX_EXTRA_ENV, "").strip().lower() in _TRUTHY


def default_cocoindex_index_path(repo_root: Path) -> Path:
    """The fingerprint index's default location -- alongside `graph.json`
    under `.claude/data/pyforge-scribe/`, already blanket-gitignored
    (`.gitignore:721`); this index is derived, disposable bookkeeping, never
    a second store-of-record (AC3)."""
    return repo_root / ".claude" / "data" / "pyforge-scribe" / "cocoindex-index.json"


def _import_cocoindex():
    try:
        import cocoindex
    except ImportError as exc:
        raise CocoindexUnavailableError(
            "the cocoindex compile_surface extra requires cocoindex "
            "(pip install 'pyforge-scribe[cocoindex]' or the cocoindex conda package)"
        ) from exc
    return cocoindex


def refresh_incremental(
    repo_root: Path,
    artifacts: Iterable[DerivedArtifact],
    *,
    index_path: Path | None = None,
    warnings: list[str] | None = None,
) -> RefreshResult:
    """Recompute only the declared artifacts whose sources changed since the
    last call against this same ``index_path``.

    For each artifact, in declaration order: fingerprint its current
    sources with `cocoindex.memo_fingerprint` (never a hand-rolled hash --
    that is the point of binding the engine), compare against the
    previously persisted fingerprint, and call `artifact.derive()` only on
    a mismatch (including "never run before"). The index is re-persisted
    after every artifact (via `finally`) so a `derive()` raising partway
    through an artifact list does not discard fingerprints already
    recorded for artifacts processed earlier in this same call -- a raised
    exception propagates to the caller unchanged, matching
    `extras/graphify.py`'s own "an explicit verb's failure is not silently
    swallowed" contract; only `compile.py`'s own AUTOMATIC fan-in hooks
    degrade a failure into a warning, and this module does not do that on
    its own behalf.
    """
    resolved_index_path = index_path if index_path is not None else default_cocoindex_index_path(repo_root)
    collected_warnings = warnings if warnings is not None else []
    cocoindex = _import_cocoindex()
    previous = _load_index(resolved_index_path)
    current: dict[str, str] = dict(previous)
    refreshed: list[str] = []
    skipped: list[str] = []
    try:
        for artifact in artifacts:
            signature = _source_signature(repo_root, artifact.sources, collected_warnings)
            fingerprint = bytes(cocoindex.memo_fingerprint(signature)).hex()
            if previous.get(artifact.name) == fingerprint:
                skipped.append(artifact.name)
                current[artifact.name] = fingerprint
                continue
            artifact.derive()
            current[artifact.name] = fingerprint
            refreshed.append(artifact.name)
    finally:
        _save_index(resolved_index_path, current)
    return RefreshResult(refreshed=tuple(refreshed), skipped=tuple(skipped), index_path=resolved_index_path)


def _source_signature(
    repo_root: Path, sources: Sequence[Path], warnings: list[str]
) -> tuple[tuple[str, int | None, int | None], ...]:
    """A deterministic, sorted ``(relpath, size, mtime_ns)`` tuple per file
    under ``sources`` -- a directory contributes every file beneath it
    (recursively, sorted, EXCLUDING the same noise directories
    `compile.py`'s own surfaces exclude -- `_rglob_excluding`/
    `_EXCLUDED_DIR_NAMES`, e.g. `__pycache__`, `.git`, `node_modules` -- so
    routine `__pycache__`/`.pyc` churn under a source like
    `src/shared/packages` never counts as "the source changed"); a missing
    path contributes one ``(relpath, None, None)`` entry so a removed source
    still changes the overall signature instead of silently vanishing.
    Cheap (stat-only, never reads file content) by design: the whole point
    is to decide, cheaply, whether the EXPENSIVE `derive()` step is worth
    running at all.
    """
    entries: list[tuple[str, int | None, int | None]] = []
    for source in sources:
        resolved = source if source.is_absolute() else (repo_root / source)
        if resolved.is_dir():
            for path in _rglob_excluding(resolved, "**/*"):
                entry = _file_entry(path, repo_root, warnings)
                if entry is not None:
                    entries.append(entry)
        elif resolved.is_file():
            entry = _file_entry(resolved, repo_root, warnings)
            if entry is not None:
                entries.append(entry)
        else:
            warnings.append(f"cocoindex source {resolved} does not exist -- treated as absent")
            entries.append((_relpath(resolved, repo_root), None, None))
    entries.sort(key=lambda entry: entry[0])
    return tuple(entries)


def _file_entry(path: Path, repo_root: Path, warnings: list[str]) -> tuple[str, int, int] | None:
    """``None`` (skip, warn) when ``path`` vanishes or becomes unreadable
    between the directory listing and this `.stat()` call -- mirrors
    `extras/move_list.py::scan_move_list`'s own ``except OSError: continue``
    precedent rather than crashing the whole refresh over one racy file."""
    try:
        stat = path.stat()
    except OSError:
        warnings.append(f"cocoindex source {path} could not be stat'ed -- treated as absent")
        return None
    return (_relpath(path, repo_root), stat.st_size, stat.st_mtime_ns)


def _relpath(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _load_index(index_path: Path) -> dict[str, str]:
    if not index_path.is_file():
        return {}
    try:
        document = json.loads(index_path.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return {}
    if not isinstance(document, dict):
        return {}
    fingerprints = document.get("fingerprints", {})
    return fingerprints if isinstance(fingerprints, dict) else {}


def _save_index(index_path: Path, fingerprints: dict[str, str]) -> None:
    document = {"fingerprints": dict(sorted(fingerprints.items()))}
    atomic_write_text(index_path, json.dumps(document, indent=2, sort_keys=True) + "\n")
