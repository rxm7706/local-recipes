"""pyforge.scribe.compile — the projection builder (Story 2.2/2.3,
AD-1/AD-5/AD-6/AD-9).

`compile_graph()` is the "compile" layer of the architecture's paradigm:
event-sourced capture with a derived, rebuildable read-model. It reads five
named real-tool surfaces -- `.claude/memory/`, `.memlog.md` files, git
history, retros, and CHANGELOGs (PRD Open Question 2, resolved here) -- and
writes one `GraphNode` per source item through the `GraphStore` port (Story
2.1), never a specific storage engine's client library directly (AD-5).

Every run is a FULL rebuild, never an incremental patch: `store.reset()`
clears the in-memory state, every surface is re-read from scratch, and
`store.commit()` performs one atomic write of the whole result (AD-1: "the
compiled graph is 100% derived and re-computable from source records at any
time, from scratch, with the same result"). Because node ids are derived
deterministically from source identity (file path / commit sha), and node
content depends only on the current on-disk/in-git state, two consecutive
runs against unchanged sources produce byte-identical `GraphStore` output --
the idempotency Story 2.2 requires.

`compile_graph()` never prompts and never blocks on input (unattended, FR-11)
-- there is no `typer.confirm()`/`input()` anywhere in this module. A single
degraded surface (a missing `git` binary, one malformed `.claude/memory/`
entry) logs a warning to stderr and is skipped -- it does not abort the rest
of the compile; only a missing/malformed `memory_root` raises, mirroring
`capture.py`'s existing contract.

Zero required network calls (AD-6): the only subprocess invoked is
`git log` (local, read-only -- never `fetch`/`pull`/`clone`/`ls-remote`).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pyforge.scribe.graph_store import GraphStore
from pyforge.scribe.models import CAPTURE_TYPES, GraphNode, GraphNodeKind, parse_capture_file

#: Directories excluded from every repo-wide glob -- vendored, generated, or
#: runtime-scratch trees that would otherwise dominate node count / cost.
_EXCLUDED_DIR_NAMES = frozenset(
    {
        ".git",
        ".pixi",
        "node_modules",
        "worktrees",
        "data",  # .claude/data -- the graph store's own gitignored home
        "dist",
        "dist-conda",
        "build_artifacts",
        "__pycache__",
        ".venv",
        "venv",
    }
)

_DEFAULT_MAX_COMMITS = 100
_MAX_DOC_TEXT_CHARS = 20_000  # bound lexical-scan/serialization cost per node


@dataclass(frozen=True)
class CompileResult:
    """What `compile_graph()` did, for the CLI layer to report back."""

    node_count: int
    invalidated_count: int
    store_path: Path
    warnings: tuple[str, ...]


def default_store_path(repo_root: Path) -> Path:
    """The default `GraphStore` location -- `.claude/data/` is already
    blanket-gitignored (`.gitignore:718`); the compiled graph is a derived,
    disposable artifact (AD-1), never tracked alongside `.claude/memory/`'s
    intentionally-checked-in entries."""
    return repo_root / ".claude" / "data" / "pyforge-scribe" / "graph.json"


def compile_graph(
    *,
    memory_root: Path,
    repo_root: Path,
    store: GraphStore | None = None,
    store_path: Path | None = None,
    nightly: bool = False,
    max_commits: int = _DEFAULT_MAX_COMMITS,
) -> CompileResult:
    """Rebuild the compiled graph from scratch from the five named surfaces.

    `nightly` is accepted for CLI/scheduling clarity only -- compile is
    unattended-by-construction either way (no prompts in any code path).
    Raises `ValueError` if `memory_root` does not exist, before any read.
    Pass `store` directly (e.g. a `FlatFileGraphStore` under `tmp_path`) in
    tests instead of relying on `store_path`'s repo-relative default.
    """
    if not memory_root.is_dir():
        raise ValueError(
            f"{memory_root} does not exist -- run `scribe graph compile` from the repo root "
            "(the checked-in .claude/memory/ tree must already exist)"
        )

    if store is None:
        from pyforge.scribe.graph_store import FlatFileGraphStore

        store = FlatFileGraphStore(store_path or default_store_path(repo_root))

    warnings: list[str] = []
    store.reset()

    memory_nodes = _read_memory_surface(memory_root, repo_root, warnings)
    for node in memory_nodes:
        store.upsert_node(node)

    for node in _read_memlog_surface(repo_root):
        store.upsert_node(node)

    for node in _read_changelog_surface(repo_root):
        store.upsert_node(node)

    for node in _read_retro_surface(repo_root):
        store.upsert_node(node)

    for node in _read_git_surface(repo_root, max_commits, warnings):
        store.upsert_node(node)

    invalidated_count = _apply_supersession(memory_root, memory_nodes, store, warnings)

    store.commit()

    resolved_path = getattr(store, "store_path", store_path or default_store_path(repo_root))
    return CompileResult(
        node_count=len(list(store.iter_nodes())),
        invalidated_count=invalidated_count,
        store_path=resolved_path,
        warnings=tuple(warnings),
    )


# --- surface: .claude/memory/ -------------------------------------------------


def _read_memory_surface(
    memory_root: Path, repo_root: Path, warnings: list[str]
) -> list[GraphNode]:
    nodes: list[GraphNode] = []
    for capture_type in CAPTURE_TYPES:
        type_dir = memory_root / capture_type
        if not type_dir.is_dir():
            continue
        for path in sorted(type_dir.glob("*.md")):
            try:
                record = parse_capture_file(path)
            except ValueError as exc:
                warnings.append(f"skipped malformed memory entry {path}: {exc}")
                continue
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            nodes.append(
                GraphNode(
                    id=f"memory:{capture_type}/{path.stem}",
                    kind="memory",
                    title=record.name,
                    text=record.text,
                    citation=_citation_for(path, repo_root),
                    valid_from=mtime,
                )
            )
    return nodes


def _citation_for(path: Path, repo_root: Path) -> str:
    """A repo-relative citation string when possible (AD-8: resolvable),
    falling back to the absolute path if `path` sits outside `repo_root`
    (e.g. a test fixture using an unrelated `tmp_path`)."""
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)


# --- surface: .memlog.md files -----------------------------------------------


def _read_memlog_surface(repo_root: Path) -> list[GraphNode]:
    return [
        _node_from_text_file(path, kind="memlog", repo_root=repo_root)
        for path in _rglob_excluding(repo_root, "**/.memlog.md")
    ]


# --- surface: CHANGELOG.md files ---------------------------------------------


def _read_changelog_surface(repo_root: Path) -> list[GraphNode]:
    return [
        _node_from_text_file(path, kind="doc", repo_root=repo_root)
        for path in _rglob_excluding(repo_root, "**/CHANGELOG.md")
    ]


# --- surface: *retro*.md files ------------------------------------------------


def _read_retro_surface(repo_root: Path) -> list[GraphNode]:
    return [
        _node_from_text_file(path, kind="doc", repo_root=repo_root)
        for path in _rglob_excluding(repo_root, "**/*retro*.md")
    ]


def _is_excluded(parts: tuple[str, ...]) -> bool:
    """Review finding: matching bare directory NAMES anywhere in the path
    (the original approach) silently drops a legitimate CHANGELOG.md/
    .memlog.md/*retro*.md living under ANY directory literally named
    ``data`` (e.g. ``src/mypackage/data/CHANGELOG.md``) -- ``data`` is only
    meant to exclude THIS repo's own ``.claude/data`` (the graph store's
    gitignored home), so it is matched as the adjacent pair
    ``(".claude", "data")`` instead of the bare name. Every other excluded
    name (``.git``, ``node_modules``, ``dist``, ...) is unambiguous enough
    to keep matching anywhere."""
    for index, part in enumerate(parts):
        if part == "data":
            if index > 0 and parts[index - 1] == ".claude":
                return True
            continue
        if part in _EXCLUDED_DIR_NAMES:
            return True
    return False


def _rglob_excluding(repo_root: Path, pattern: str) -> list[Path]:
    results = []
    for path in sorted(repo_root.glob(pattern)):
        if not path.is_file():
            continue
        if _is_excluded(path.relative_to(repo_root).parts[:-1]):
            continue
        results.append(path)
    return results


def _node_from_text_file(path: Path, *, kind: GraphNodeKind, repo_root: Path) -> GraphNode:
    relpath = path.relative_to(repo_root).as_posix()
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) > _MAX_DOC_TEXT_CHARS:
        text = text[:_MAX_DOC_TEXT_CHARS]
    title = next((line.strip("# ").strip() for line in text.splitlines() if line.strip()), relpath)
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return GraphNode(
        id=f"{kind}:{relpath}",
        kind=kind,
        title=title or relpath,
        text=text,
        citation=relpath,
        valid_from=mtime,
    )


# --- surface: git history -----------------------------------------------------

_GIT_LOG_UNIT_SEP = "\x1f"
_GIT_LOG_RECORD_SEP = "\x1e"


def _read_git_surface(repo_root: Path, max_commits: int, warnings: list[str]) -> list[GraphNode]:
    git_bin = shutil.which("git")
    if git_bin is None:
        warnings.append("git binary not found on PATH -- skipping git-history surface")
        return []

    fmt = f"%H{_GIT_LOG_UNIT_SEP}%aI{_GIT_LOG_UNIT_SEP}%s{_GIT_LOG_RECORD_SEP}"
    argv = [git_bin, "log", f"-n{max_commits}", f"--pretty=format:{fmt}"]
    try:
        completed = subprocess.run(
            argv,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        warnings.append(f"git log failed -- skipping git-history surface: {exc}")
        return []

    if completed.returncode != 0:
        warnings.append(f"git log exited {completed.returncode} -- skipping git-history surface")
        return []

    nodes: list[GraphNode] = []
    for record in completed.stdout.split(_GIT_LOG_RECORD_SEP):
        record = record.strip("\n")
        if not record.strip():
            continue
        parts = record.split(_GIT_LOG_UNIT_SEP)
        if len(parts) != 3:
            continue
        sha, authored_at, subject = parts
        try:
            valid_from = datetime.fromisoformat(authored_at)
        except ValueError:
            valid_from = datetime.now(timezone.utc)
        nodes.append(
            GraphNode(
                id=f"commit:{sha}",
                kind="commit",
                title=subject,
                text=subject,
                citation=f"commit:{sha}",
                valid_from=valid_from,
            )
        )
    return nodes


# --- supersession (Story 2.3) -------------------------------------------------


def _apply_supersession(
    memory_root: Path,
    memory_nodes: list[GraphNode],
    store: GraphStore,
    warnings: list[str],
) -> int:
    """For every memory record whose frontmatter names a prior record as
    superseded (`supersedes: "<type>/<slug>"`), invalidate the prior node's
    validity in the graph (AD-4: mark ended, never delete). A dangling
    reference (the named prior record does not exist / was never a node in
    this compile) is logged and skipped -- an unattended nightly compile
    must not crash on a stale or mistyped reference.
    """
    invalidated = 0
    node_by_id = {node.id: node for node in memory_nodes}
    for capture_type in CAPTURE_TYPES:
        type_dir = memory_root / capture_type
        if not type_dir.is_dir():
            continue
        for path in sorted(type_dir.glob("*.md")):
            try:
                record = parse_capture_file(path)
            except ValueError:
                continue  # already warned in _read_memory_surface
            except OSError as exc:
                # This directory was already scanned once in
                # _read_memory_surface -- a file that existed then can
                # legitimately be gone by the time this second pass reaches
                # it (e.g. a concurrent `scribe capture` cleanup, or simply
                # normal repo activity during an unattended nightly run).
                # Review finding: an earlier draft only caught ValueError
                # here, so this re-read's own FileNotFoundError crashed the
                # whole compile instead of degrading like every other
                # surface.
                warnings.append(f"skipped {path} during supersession pass: {exc}")
                continue
            if not record.supersedes:
                continue
            target_id = f"memory:{record.supersedes}"
            source_id = f"memory:{capture_type}/{path.stem}"
            source_node = node_by_id.get(source_id)
            if target_id not in node_by_id:
                warnings.append(
                    f"{path}: supersedes {record.supersedes!r} does not resolve to a known "
                    "memory node -- skipped"
                )
                continue
            ended_at = source_node.valid_from if source_node is not None else datetime.now(timezone.utc)
            store.invalidate_edge(target_id, ended_at=ended_at, superseded_by=source_id)
            invalidated += 1
    return invalidated
