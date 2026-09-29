"""pyforge.scribe.extras.graphify -- the graphify `compile_surface` ingest
extra (Story 6.1, unifying-strategy Grounding 2026-08-30: "cocoindex is a
`compile_surface` extra that writes *through* `GraphStore`, not a GraphStore
engine"; stack.md "Estate leverage": "`cocoindex` + `graphifyy` | scribe |
`scribe index`: AST graph + incremental index ... | bind").

This extra is not the symbol-navigation API. Marshal codegraph
(``.codegraph/codegraph.db``) owns "where is this symbol?"; ``code:``
nodes stay an AST / ``index report`` / ``--mode code`` surface.

Binds graphifyy (>=0.9.51, Apache-2.0) as an OPTIONAL ingest source: when
`SCRIBE_GRAPHIFY_EXTRA` is truthy, `compile.py`'s fan-in (and the explicit
`scribe index build` verb) call `ingest_repo()` here to turn a folder of
code into `GraphNode`s written through the `GraphStore` persist port
(`open_graph_store`) -- never a second/parallel store (AC2). Absent or off
(the air-gap default, AD-6), `graphify_extra_enabled()` gates every call
site before the heavy import is ever reached -- `compile_graph()`'s own
fan-in short-circuits on the env var, so an off-mode compile never even
calls into this module's `_import_graphify()`.

`graphify` (the `graphifyy` distribution's import name) is imported ONLY
inside this module, and only lazily inside `_import_graphify()` --
declaring the optional `pyforge-scribe[graphify]` extra never requires the
heavy dependency until a caller actually enables the extra. Mirrors
`graph_store_pg.py::_import_psycopg` / `graph_store_plane.py::_import_duckdb`
exactly (AC4).

graphify's own on-disk AST-extraction cache (`extract(..., cache_root=...)`)
is pointed at Scribe's own already-gitignored derived-artifact home
(`.claude/data/pyforge-scribe/graphify-cache/`, same tree `compile.py`'s
`default_store_path()` docstring describes as blanket-gitignored via
`.gitignore:718`) -- so no foundry-root `graphify-out/` product dir is ever
created (AC4).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from pyforge.core.errors import PyforgeError

from pyforge.scribe.models import GraphNode

#: Off by default (air-gap, AD-6) -- only a truthy value turns the extra on.
GRAPHIFY_EXTRA_ENV = "SCRIBE_GRAPHIFY_EXTRA"
_TRUTHY = frozenset({"1", "true", "yes", "on"})

#: Bounded default ingest target: the pyforge station package tree, not the
#: whole repo -- `recipes/` alone has thousands of first-level directories,
#: the same cost concern Story 3.3 bounded for the compile's other surfaces.
#: Single-path APIs (`index report`, `--target` help) still name this path.
DEFAULT_GRAPHIFY_TARGET = Path("src") / "shared" / "packages"

#: Extra-on compile / `index build` with no `--target` (Story 15.1).
#: Named list only — never `recipes/` and never the repo root.
DEFAULT_GRAPHIFY_TARGETS = (
    DEFAULT_GRAPHIFY_TARGET,
    Path("src") / "platform",
    Path("scripts"),
)

#: graphify's own AST-extraction disk cache, redirected under Scribe's
#: already-gitignored `.claude/data/` home (AC4) instead of a foundry-root
#: `graphify-out/`.
_CACHE_SUBDIR = Path(".claude") / "data" / "pyforge-scribe" / "graphify-cache"


class GraphifyUnavailableError(PyforgeError):
    """`graphifyy` is not installed but the graphify extra was explicitly
    invoked -- install the `pyforge-scribe[graphify]` extra (or the
    `graphifyy` conda package)."""


def graphify_extra_enabled() -> bool:
    """Off by default (AD-6) -- only a truthy `SCRIBE_GRAPHIFY_EXTRA` turns
    the automatic `compile_graph()` fan-in hook on. `scribe index build`
    does not consult this: an explicit CLI invocation is already the
    deliberate opt-in."""
    return os.environ.get(GRAPHIFY_EXTRA_ENV, "").strip().lower() in _TRUTHY


def _import_graphify():
    try:
        import graphify
    except ImportError as exc:
        raise GraphifyUnavailableError(
            "the graphify compile_surface extra requires graphifyy "
            "(pip install 'pyforge-scribe[graphify]' or the graphifyy conda package)"
        ) from exc
    return graphify


def _graphify_api(graphify, name: str):
    """Return a callable public name from graphifyy.

    graphifyy's package uses lazy ``__getattr__`` exports AND same-named
    submodules (``graphify/extract.py``). After ``collect_files`` imports
    that submodule, ``graphify.extract`` is the module, not the function
    ``__getattr__`` would have returned — calling it raises TypeError.
    Unwrap ``module.<name>`` when the attribute itself is not callable.
    """
    attr = getattr(graphify, name)
    if callable(attr):
        return attr
    nested = getattr(attr, name, None)
    if callable(nested):
        return nested
    raise TypeError(f"graphify.{name} is not callable")


def ingest_repo(
    repo_root: Path,
    *,
    target: Path | None = None,
    warnings: list[str] | None = None,
) -> list[GraphNode]:
    """Ingest ``target`` (repo-relative) with graphifyy and return
    `GraphNode`s ready for `GraphStore.upsert_node()` -- never a
    parallel store (AC2).

    When ``target`` is omitted, walk `DEFAULT_GRAPHIFY_TARGETS` (Story
    15.1): `src/shared/packages/`, `src/platform/`, `scripts/`. Missing
    optional list entries are silent. A warning fires only when no
    default target exists, or when an explicit ``target`` is missing.

    The target-existence check runs BEFORE the lazy `graphify` import: a
    repo with none of the named trees (or an explicit target that does
    not exist) degrades to a warning and zero nodes without ever requiring
    graphifyy to be installed. Only once there is something to ingest does
    this raise `GraphifyUnavailableError` when the package is missing --
    callers that must degrade instead of abort (`compile.py`'s fan-in)
    catch that themselves, matching every other optional compile surface's
    own degrade-not-abort contract.
    """
    collected_warnings = warnings if warnings is not None else []
    if target is not None:
        resolved_targets = [(repo_root / target).resolve()]
        if not resolved_targets[0].is_dir():
            collected_warnings.append(f"graphify ingest target {resolved_targets[0]} does not exist -- skipped")
            return []
    else:
        resolved_targets = [
            (repo_root / rel).resolve() for rel in DEFAULT_GRAPHIFY_TARGETS if (repo_root / rel).is_dir()
        ]
        if not resolved_targets:
            collected_warnings.append("graphify ingest targets do not exist -- skipped")
            return []

    graphify = _import_graphify()
    nodes: list[GraphNode] = []
    for resolved_target in resolved_targets:
        graph = _build_graph(graphify, repo_root, resolved_target)
        for node_id, attrs in graph.nodes(data=True):
            node = _graph_node_from_graphify(node_id, attrs, repo_root)
            if node is not None:
                nodes.append(node)
    return nodes


def _build_graph(graphify, repo_root: Path, target: Path):
    """Run graphify's own extract -> build pipeline over ``target``,
    anchoring `source_file` values to ``repo_root`` (so citations come out
    repo-relative, matching every other compile surface) and redirecting
    the AST cache away from the foundry root (AC4)."""
    cache_root = repo_root / _CACHE_SUBDIR
    cache_root.mkdir(parents=True, exist_ok=True)
    collect_files = _graphify_api(graphify, "collect_files")
    extract = _graphify_api(graphify, "extract")
    build_from_json = _graphify_api(graphify, "build_from_json")
    files = collect_files(target, root=repo_root)
    if not files:
        extraction = {"nodes": [], "edges": [], "hyperedges": []}
    else:
        extraction = extract(files, cache_root=cache_root, root=repo_root, parallel=False)
    return build_from_json(extraction, root=repo_root)


def _graph_node_from_graphify(node_id: object, attrs: dict, repo_root: Path) -> GraphNode | None:
    """One graphify graph node -> one `GraphNode`. Nodes without a
    `source_file` (graphify's own cross-file-reference stubs, e.g. an
    imported-but-not-extracted type annotation) have nothing to cite and are
    dropped -- an uncited node could never pass `recall.py`'s AD-8 check
    anyway.
    """
    source_file = attrs.get("source_file")
    if not source_file:
        return None
    label = attrs.get("label") or str(node_id)
    node_type = attrs.get("type") or attrs.get("file_type") or "code"
    location = attrs.get("source_location") or ""
    citation = f"{source_file}:{location}" if location else str(source_file)
    return GraphNode(
        id=f"code:{node_id}",
        kind="code",
        title=str(label),
        text=f"{node_type} {label} ({source_file})",
        citation=citation,
        valid_from=_source_mtime(repo_root, str(source_file)),
    )


def _source_mtime(repo_root: Path, source_file: str) -> datetime:
    try:
        return datetime.fromtimestamp((repo_root / source_file).stat().st_mtime, tz=timezone.utc)
    except OSError:
        return datetime.now(timezone.utc)


def build_graph_report(
    repo_root: Path,
    *,
    target: Path | None = None,
    top_n: int = 10,
) -> str:
    """A GRAPH_REPORT-style summary of ``target``'s graphify graph, including
    God-node findings (`graphify.god_nodes`) -- AC3. Returns text only; the
    caller (`scribe index report`) owns writing it to a derived, gitignored
    path. Raises `ValueError` if ``target`` does not exist -- unlike
    `ingest_repo()`, an explicit report request has nothing useful to
    degrade to.
    """
    resolved_target = (repo_root / (target if target is not None else DEFAULT_GRAPHIFY_TARGET)).resolve()
    if not resolved_target.is_dir():
        raise ValueError(f"graphify report target {resolved_target} does not exist")

    graphify = _import_graphify()
    graph = _build_graph(graphify, repo_root, resolved_target)
    god = _graphify_api(graphify, "god_nodes")(graph, top_n=top_n)

    try:
        rel_target = resolved_target.relative_to(repo_root)
    except ValueError:
        rel_target = resolved_target

    lines = [
        f"# GRAPH_REPORT -- {rel_target.as_posix()}",
        "",
        f"- nodes: {graph.number_of_nodes()}",
        f"- edges: {graph.number_of_edges()}",
        "",
        "## God Nodes",
        "",
    ]
    if god:
        lines.extend(f"- {entry.get('label', entry.get('id'))} (degree={entry.get('degree')})" for entry in god)
    else:
        lines.append("(none)")
    return "\n".join(lines) + "\n"
