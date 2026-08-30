"""The graphify `compile_surface` extra (Story 6.1).

Binds the conda-forge `graphifyy` package (import name `graphify`) as an
OPTIONAL AST code-structure ingest source. Off by default
(`graphify_extra_enabled()`, air-gap AD-6) -- `compile.py` only calls into
this module when the extra is explicitly turned on, so an environment that
never installed `graphifyy` behaves identically to before this story (the
off-mode AC).

`graphify` is imported ONLY in this module (Design Notes: "graphifyy is
imported only inside the extra adapter") -- via a lazy, function-scoped
import, mirroring `graph_store_plane.py`'s lazy `duckdb` import, so a lean
`pyforge-scribe` install (the package is not a hard pixi run-dep of that
environment) degrades to a clear `GraphifyExtraUnavailable`, never an
unguarded `ImportError` traceback.

Two things this module deliberately does NOT do:

* Drive graphify's CLI/agentic-skill pipeline (semantic/LLM extraction,
  clustering, `graphify-out/graph.json` + `GRAPH_REPORT.md` + `graph.html`).
  That pipeline needs an LLM subagent for its semantic pass and writes a
  `graphify-out/` product directory as a side effect -- both wrong for an
  unattended, no-LLM-required nightly compile (FR-11, AD-6). This module
  calls graphify's own AST-only extraction primitives directly
  (`graphify.extract.extract` + `graphify.build.build_from_json` +
  `graphify.analyze.god_nodes`) -- pure, in-memory, no LLM, no API key.
* Create a foundry-root `graphify-out/` directory. graphify's own
  file-content extraction cache is real (`extract(..., cache_root=...)`
  writes small per-file JSON entries so a re-run skips unchanged files),
  but this module always pins `cache_root` under the caller's own
  gitignored `.claude/data/pyforge-scribe/graphify/` tree (never the scan
  root or repo root) AND best-effort redirects graphify's own
  `GRAPHIFY_OUT` output-dir name away from the literal `"graphify-out"` --
  see `_import_graphify()`.

Ingest writes `GraphNode`s (kind="code") -- there is no separate persisted
edge object (`graph_store.py`'s own docstring: "Nodes ARE the facts here").
Each node's `citation` is the bare repo-relative source file path (no
`:L<line>` suffix) so `recall.py`'s existing citation-resolution scheme
(`(repo_root / citation).is_file()`) resolves it unchanged -- this story's
Code Map does not touch `recall.py`.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pyforge.core.errors import PyforgeError
from pyforge.scribe.models import GraphNode

#: Off by default (air-gap, AD-6). Any of "1"/"true"/"yes" (case-insensitive)
#: turns the extra on for `scribe graph compile`'s automatic surface fan-in.
GRAPHIFY_EXTRA_ENV = "SCRIBE_GRAPHIFY_EXTRA"

#: `scribe index report`/`scribe index move-list` are explicit, deliberate
#: invocations -- invoking the subcommand IS the opt-in, so they never
#: consult `GRAPHIFY_EXTRA_ENV`. Only `compile_graph()`'s automatic nightly
#: fan-in respects the off-by-default gate.
_TRUTHY = frozenset({"1", "true", "yes"})

#: Extra directory names graphify's own `_SKIP_DIRS` (detect.py) does not
#: already exclude, but this repo's other surfaces do (compile.py's
#: `_EXCLUDED_DIR_NAMES`, Story 3.3) -- `.pixi` alone holds a full conda
#: environment tree per worktree, and scanning it would dwarf every real
#: source file in cost.
_EXTRA_NOISE_DIR_NAMES = frozenset({".pixi", "dist-conda", "build_artifacts"})


class GraphifyExtraUnavailable(PyforgeError):
    """`graphify` (conda-forge `graphifyy`) is not importable in this
    environment. Raised only when the extra was asked to run (the env-var
    gate was on, or a `scribe index` verb was invoked directly) -- never
    when the extra is simply off."""


def graphify_extra_enabled(*, override: bool | None = None) -> bool:
    """Off by default (air-gap, AD-6). `override` (the CLI's explicit
    `--extra`/`--no-extra` flag) wins when given; otherwise falls back to
    `SCRIBE_GRAPHIFY_EXTRA`."""
    if override is not None:
        return override
    return os.environ.get(GRAPHIFY_EXTRA_ENV, "").strip().lower() in _TRUTHY


def default_graphify_root(repo_root: Path) -> Path:
    """`src/` -- the station/host source tree (`src/platform/` +
    `src/shared/packages/`), not the whole repo. `recipes/` alone holds
    thousands of first-level feedstock directories (the Dream's own "do not
    clone that universe" rule) including `build.sh` files graphify's bash
    extractor would happily walk; defaulting to `src/` keeps an unattended
    nightly compile's optional surface bounded without needing Story
    3.3-style caps of its own. Callers needing a different scope (or a
    single feedstock) pass an explicit root instead."""
    return repo_root / "src"


def _import_graphify(*, cache_dir: Path):
    """Lazy import -- the only place `graphify` is imported anywhere in this
    package. Best-effort redirects graphify's own `GRAPHIFY_OUT` output-dir
    name (read once, at graphify.paths' own import time) away from the
    literal `"graphify-out"`; this is defense in depth, not the primary
    guarantee -- every caller in this module also pins an explicit
    `cache_root` under `cache_dir` (always inside the caller's own
    gitignored tree), so graphify's cache lands there regardless of whether
    this env-var redirect wins the import-order race.
    """
    os.environ.setdefault("GRAPHIFY_OUT", ".")
    try:
        from graphify.analyze import god_nodes
        from graphify.build import build_from_json
        from graphify.extract import collect_files, extract
    except ImportError as exc:
        raise GraphifyExtraUnavailable(
            "the graphify compile_surface extra requires `graphify` "
            "(conda-forge `graphifyy`, an optional pyforge-scribe[graphify] "
            "dependency) which is not installed in this environment"
        ) from exc
    cache_dir.mkdir(parents=True, exist_ok=True)
    return collect_files, extract, build_from_json, god_nodes


def _collect_source_files(scan_root: Path, *, repo_root: Path, collect_files) -> list[Path]:
    if not scan_root.is_dir():
        return []
    candidates = collect_files(scan_root, root=repo_root)
    kept: list[Path] = []
    for path in candidates:
        try:
            rel_parts = path.resolve().relative_to(repo_root.resolve()).parts
        except ValueError:
            kept.append(path)
            continue
        if any(part in _EXTRA_NOISE_DIR_NAMES for part in rel_parts):
            continue
        kept.append(path)
    return kept


def _extract_graph(scan_root: Path, *, repo_root: Path, cache_dir: Path):
    """Shared AST-extraction step for both the ingest path and the report
    path -- returns `(nx.Graph, warnings, god_nodes_fn)`. graphify's own
    per-file content cache (keyed by SHA-256, under `cache_dir`) makes a
    second call in a different process over unchanged sources cheap; this
    function never writes anywhere outside `cache_dir`. Returning
    `god_nodes_fn` alongside the graph means callers that also need
    god-node findings (`build_graphify_report`) do not re-run
    `_import_graphify()` a second time."""
    collect_files, extract, build_from_json, god_nodes_fn = _import_graphify(cache_dir=cache_dir)
    warnings: list[str] = []
    files = _collect_source_files(scan_root, repo_root=repo_root, collect_files=collect_files)
    if not files:
        warnings.append(f"graphify extra: no source files found under {scan_root}")
    extraction = extract(files, cache_root=cache_dir, root=repo_root) if files else {"nodes": [], "edges": []}
    graph = build_from_json(extraction, directed=True, root=str(repo_root))
    return graph, warnings, god_nodes_fn


@dataclass(frozen=True)
class GraphifyIngestResult:
    """What `ingest_graphify_surface()` produced -- for `compile.py` to
    upsert into the `GraphStore` port and report back."""

    nodes: tuple[GraphNode, ...]
    warnings: tuple[str, ...]


def ingest_graphify_surface(
    scan_root: Path,
    *,
    repo_root: Path,
    cache_dir: Path,
) -> GraphifyIngestResult:
    """AST-only structural extraction over `scan_root` -- one `GraphNode`
    (kind="code") per extracted class/function/module entity. Never writes
    through anything but the caller's own `GraphStore` port -- this
    function returns nodes, it does not persist them (matching every other
    `_read_*_surface` in `compile.py`)."""
    graph, warnings, _god_nodes_fn = _extract_graph(scan_root, repo_root=repo_root, cache_dir=cache_dir)
    nodes: list[GraphNode] = []
    for node_id, data in graph.nodes(data=True):
        source_file = data.get("source_file") or ""
        label = data.get("label", node_id)
        location = data.get("source_location", "")
        citation, valid_from = _citation_and_mtime(source_file, repo_root)
        text = f"{label} ({location})".strip() if location else str(label)
        nodes.append(
            GraphNode(
                id=f"code:{node_id}",
                kind="code",
                title=str(label),
                text=text,
                citation=citation,
                valid_from=valid_from,
            )
        )
    return GraphifyIngestResult(nodes=tuple(nodes), warnings=tuple(warnings))


def _citation_and_mtime(source_file: str, repo_root: Path) -> tuple[str, datetime]:
    """Citation is the BARE repo-relative source file (no `:L<line>`
    suffix) so `recall.py`'s existing `(repo_root / citation).is_file()`
    branch resolves it unchanged (this story does not touch `recall.py`).
    `valid_from` is the source file's own mtime, NEVER `datetime.now()` --
    `compile.py`'s idempotency contract requires two consecutive runs over
    unchanged sources to produce byte-identical `GraphStore` output, and a
    fresh `now()` timestamp on every run would break that for every code
    node (the same reasoning `compile.py::_read_memory_surface` and
    `_node_from_text_file` already apply). A missing/unreadable file (a
    rare race between extraction and this read) degrades to `repo_root`'s
    own mtime rather than aborting the whole surface.
    """
    citation = source_file or "."
    target = repo_root / citation
    try:
        mtime = target.stat().st_mtime
    except OSError:
        mtime = repo_root.stat().st_mtime
    return citation, datetime.fromtimestamp(mtime, tz=timezone.utc)


@dataclass(frozen=True)
class GraphifyReport:
    """A GRAPH_REPORT-style summary for `scribe index report` -- a
    lightweight, AST-only analogue of graphify's own `GRAPH_REPORT.md`
    (which additionally needs LLM-driven community detection this
    unattended path deliberately skips)."""

    summary_markdown: str
    god_nodes: tuple[dict, ...]
    node_count: int
    edge_count: int
    warnings: tuple[str, ...]


def build_graphify_report(
    scan_root: Path,
    *,
    repo_root: Path,
    cache_dir: Path,
    top_n: int = 10,
) -> GraphifyReport:
    """AST-only structure report: node/edge counts plus god-node findings
    (`graphify.analyze.god_nodes` -- the most-connected real entities,
    file-level hub nodes excluded)."""
    graph, warnings, god_nodes_fn = _extract_graph(scan_root, repo_root=repo_root, cache_dir=cache_dir)
    god = god_nodes_fn(graph, top_n=top_n)

    lines = [
        f"# GRAPH_REPORT (graphify extra) -- {_relative_or_self(scan_root, repo_root)}",
        "",
        f"- nodes: {graph.number_of_nodes()}",
        f"- edges: {graph.number_of_edges()}",
        "",
        "## God nodes",
    ]
    if god:
        for entry in god:
            lines.append(f"- `{entry['label']}` (degree {entry['degree']})")
    else:
        lines.append("- none found")
    if warnings:
        lines += ["", "## Warnings"]
        lines += [f"- {warning}" for warning in warnings]

    return GraphifyReport(
        summary_markdown="\n".join(lines) + "\n",
        god_nodes=tuple(god),
        node_count=graph.number_of_nodes(),
        edge_count=graph.number_of_edges(),
        warnings=tuple(warnings),
    )


def _relative_or_self(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)


# --- move list (Story 6.1's "its move-list verbs") ----------------------------
#
# Pure text/regex scan -- no `graphify` import. Grouped in this module because
# the story bundles it with the graphify extra ("The graphify ingest extra and
# ITS move-list verbs"), not because it depends on graphify's engine.

_HOST_ROOT_NAME = "platform"
_PY_SUFFIX = ".py"

_IMPORT_PYFORGE_RE = re.compile(r"^\s*(?:from\s+pyforge(?:\.\S+)?\s+import\b|import\s+pyforge(?:\.\S+)?\b)")
_SYS_PATH_RE = re.compile(r"\bsys\.path\.(?:insert|append)\s*\(")
_FIVE_TIER_RE = re.compile(r"\bfive_tier\b|_packages_root\b")
_CFE_CALLER_RE = re.compile(
    r"conda_forge_server|conda-forge-expert|pyforge\.mason\.cfe|from\s+pyforge\.mason\s+import\s+cfe"
)

#: Same traversal-cost discipline as `compile.py::_EXCLUDED_DIR_NAMES`
#: (Story 3.3) -- the move list is a repo-wide `.py` scan and must not
#: re-learn that 9-minute-glob lesson.
_MOVE_LIST_EXCLUDED_DIR_NAMES = frozenset(
    {
        ".git", ".pixi", "node_modules", "worktrees", ".worktrees",
        "data", "dist", "dist-conda", "build_artifacts", "__pycache__",
        ".venv", "venv",
    }
)


@dataclass(frozen=True)
class MoveListFinding:
    category: str
    path: str
    line: int
    snippet: str


def scan_move_list(repo_root: Path) -> list[MoveListFinding]:
    """Foundry-cutover move list (Design Notes / Dream `pyforge-target-
    monorepo.md`): host `import pyforge.*` sites, `sys.path` inserts,
    `five_tier` roots, and CFE (conda-forge-expert) callers -- the four
    categories a monorepo cutover needs to retarget. Deterministic,
    offline, no `graphify` dependency."""
    findings: list[MoveListFinding] = []
    for path in _iter_python_files(repo_root):
        rel = path.relative_to(repo_root).as_posix()
        under_host = path.relative_to(repo_root).parts[:2] == ("src", _HOST_ROOT_NAME)
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines, start=1):
            if under_host and _IMPORT_PYFORGE_RE.match(line):
                findings.append(
                    MoveListFinding("host_import_pyforge", rel, line_no, line.strip())
                )
            if _SYS_PATH_RE.search(line):
                findings.append(MoveListFinding("sys_path_insert", rel, line_no, line.strip()))
            if _FIVE_TIER_RE.search(line):
                findings.append(MoveListFinding("five_tier_root", rel, line_no, line.strip()))
            if _CFE_CALLER_RE.search(line):
                findings.append(MoveListFinding("cfe_caller", rel, line_no, line.strip()))
    findings.sort(key=lambda finding: (finding.category, finding.path, finding.line))
    return findings


def _iter_python_files(repo_root: Path):
    for dirpath, dirnames, filenames in os.walk(repo_root):
        rel_parts = Path(dirpath).relative_to(repo_root).parts
        # `data` is only excluded as the adjacent pair `(".claude", "data")`
        # -- mirrors compile.py::_is_excluded's own documented reasoning, so
        # a legitimate `src/mypackage/data/whatever.py` is never dropped.
        dirnames[:] = [d for d in dirnames if not _is_move_list_excluded(rel_parts + (d,))]
        for filename in filenames:
            if filename.endswith(_PY_SUFFIX):
                yield Path(dirpath) / filename


def _is_move_list_excluded(parts: tuple[str, ...]) -> bool:
    for index, part in enumerate(parts):
        if part == "data":
            if index > 0 and parts[index - 1] == ".claude":
                return True
            continue
        if part in _MOVE_LIST_EXCLUDED_DIR_NAMES:
            return True
    return False


def move_list_to_document(findings: list[MoveListFinding], *, repo_root: Path) -> dict:
    """JSON-serializable move-list document -- a derived, gitignored
    artifact (like `graph.json`), never git-tracked."""
    categories: dict[str, list[dict]] = {}
    for finding in findings:
        categories.setdefault(finding.category, []).append(
            {"path": finding.path, "line": finding.line, "snippet": finding.snippet}
        )
    return {
        "repo_root": str(repo_root),
        "counts": {category: len(items) for category, items in categories.items()},
        "categories": categories,
    }
