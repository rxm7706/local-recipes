"""pyforge.scribe.compile — the projection builder (Story 2.2/2.3,
AD-1/AD-5/AD-6/AD-9).

`compile_graph()` is the "compile" layer of the architecture's paradigm:
event-sourced capture with a derived, rebuildable read-model. It reads seven
named real-tool surfaces -- `.claude/memory/`, `.memlog.md` files, git
history, retros, CHANGELOGs (PRD Open Question 2, resolved here),
un-curated session transcripts (Story 3.1's `scan_transcripts()`, registered
as a compile source in Story 3.2), and Herald deck fact ledgers
(`presentations/<slug>/facts.yaml`, Story 8.3), in-flight story specs
(Story 10.1), planning pointers (Story 13.1), named docs extras
(Story 14.1) -- and writes one `GraphNode`
per source item through the `GraphStore` port (Story 2.1), never a specific
storage engine's client library directly (AD-5).

Every run is a FULL rebuild, never an incremental patch: `store.reset()`
clears the in-memory state, every surface is re-read from scratch, and
`store.commit()` performs one atomic write of the whole result (AD-1: "the
compiled graph is 100% derived and re-computable from source records at any
time, from scratch, with the same result"). Because node ids are derived
deterministically from source identity (file path / commit sha), and node
content depends only on the current on-disk/in-git state, two consecutive
runs against unchanged sources produce byte-identical `GraphStore` output --
the idempotency Story 2.2 requires.

That reproducibility is per-machine, not repo-wide: six of the seven surfaces
are repo artifacts, but the transcript surface (Story 3.2) reads a per-user,
per-machine `~/.claude/projects/<encoded-cwd>/` tree that is not part of the
repository. Two operators compiling the same commit therefore get the same
six-surface repo core plus whatever transcript nodes their own machine holds --
by design (that local-only content is the gap Epic 3 exists to close), but
worth stating, since the AD-1 quote above otherwise reads as repo-determinism.

`compile_graph()` never prompts and never blocks on input (unattended, FR-11)
-- there is no `typer.confirm()`/`input()` anywhere in this module. A single
degraded surface (a missing `git` binary, one malformed `.claude/memory/`
entry) logs a warning to stderr and is skipped -- it does not abort the rest
of the compile; only a missing/malformed `memory_root` raises, mirroring
`capture.py`'s existing contract.

**Scheduled, not self-scheduling (Story 3.3).** This verb is the schedulable
unit -- the herald Story-13.5 pattern: no scheduler dependency, no GitHub
Actions workflow (every input worth compiling -- `.claude/memory/`, the
per-user transcript root, the gitignored `.claude/data/` store -- is
operator-local, so a GH-hosted runner would compile an empty machine); the
documented trigger is an opt-in operator-installed `crontab` entry, see
`docs/cli-runbooks.md` in this package. Two Story 3.3 guards make that safe:
the transcript scan is bounded (caps/timeout/mtime-cache, see
`transcripts.py`; the cache lives beside the graph store, so it shares the
store's own gitignored, derived-artifact home), and overlapping runs against
one store are refused -- `compile_graph()` takes a non-blocking advisory
lock keyed to the store path (the same stdlib flock pattern as
`capture.py::_locked`, but skip-not-wait) and raises
`CompileInProgressError` when another compile already holds it, which the
CLI reports as a clean exit-0 skip so an overlapping cron firing is never a
corrupted double-write and never red cron mail.

Zero required network calls (AD-6): the only subprocess invoked is
`git log` (local, read-only -- never `fetch`/`pull`/`clone`/`ls-remote`).

**Staleness flag (Story 6.3, CAP-13).** After supersession runs, every
still-CURRENT node whose citation resolves to a git-tracked repo file gets
one more git-timestamp comparison: if that file's latest commit postdates
the node's own `valid_from`, the node is re-upserted with `stale=True`
(`models.GraphNode.stale`). A node Story 2.3 already invalidated (a
declared `supersedes:` edge points at it) is skipped -- it is not current,
so it was never a staleness candidate in the first place. This is the same
git-timestamp-only mechanism epic-wide (memlog/changelog/retro/memory/code
nodes alike) -- no LLM call, no new dependency, and `_apply_supersession()`
is untouched. `commit:`/`transcript:` citations have no git-trackable
source-file counterpart and are never checked.

**Optional eighth surface (Story 6.1).** When `SCRIBE_GRAPHIFY_EXTRA` is
truthy, `compile_graph()` also ingests the named graphify target list
(`src/shared/packages/`, `src/platform/`, `scripts/` — Story 15.1) with the
graphify `compile_surface` extra (`pyforge.scribe.extras.graphify`),
writing `code`-kind `GraphNode`s through this SAME `GraphStore` -- never a
parallel store. Off by default (AD-6): the env var is checked before the
extra's own lazy `graphify` import ever runs, so an off-mode compile is
byte-for-byte identical to the seven-surface compile that predates Story 6.1
(facts.yaml is a named surface, not this extra). If the extra is on but
graphifyy fails to import (or errors during extraction), that degrades to a
warning like every other optional surface here -- it does not abort the rest
of the compile.

**Story 6.2 deliberately does not hook the cocoindex incremental extra into
this function.** `compile_graph()`'s whole contract is `store.reset()` then
rebuild every surface from scratch (AD-1 above) -- a `derive()` step that
`refresh_incremental()` (`pyforge.scribe.extras.cocoindex_flow`) decides to
SKIP would, inside that reset-then-rebuild flow, simply mean those nodes
are never re-upserted into the freshly emptied store and vanish from the
committed graph -- indistinguishable from deleting them, which AD-1
forbids. `scribe index refresh` (`cli.py`) is the actual home for the
cocoindex extra instead: it is upsert-only / independent-file-write for
BOTH of Story 6.1's derived artifacts (graphify ingest, move list), so
"skip" there correctly means "leave the previously-written artifact
exactly as it was", with no reset step to reconcile against.
"""

from __future__ import annotations

import contextlib
import fnmatch
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pyforge.core.errors import PyforgeError

from pyforge.scribe.extras.graphify import graphify_extra_enabled, ingest_repo
from pyforge.scribe.graph_store import GraphStore
from pyforge.scribe.models import CAPTURE_TYPES, GraphNode, GraphNodeKind, parse_capture_file
from pyforge.scribe.transcripts import (
    TranscriptCandidate,
    default_transcript_root,
    scan_transcripts,
)

#: Directories excluded from every repo-wide glob -- vendored, generated, or
#: runtime-scratch trees that would otherwise dominate node count / cost.
_EXCLUDED_DIR_NAMES = frozenset(
    {
        ".git",
        ".pixi",
        "node_modules",
        "worktrees",
        # Story 3.3: the dot-prefixed worktree home at the repo root
        # (`.worktrees/`) holds the same full duplicate checkouts the bare
        # "worktrees" entry was always meant to exclude (`.cursor/worktrees`,
        # `.claude/worktrees`) -- indexing them mints duplicate memlog/
        # changelog/retro nodes citing throwaway trees.
        ".worktrees",
        "data",  # .claude/data -- the graph store's own gitignored home
        "dist",
        "dist-conda",
        "build_artifacts",
        "__pycache__",
        ".venv",
        "venv",
        # Story 8.4: not fleet truth — archived BMAD trees, gitignored
        # execution output, and test fixtures.
        "archive",
        "implementation-artifacts",
        "tests",
    }
)

_DEFAULT_MAX_COMMITS = 100
_MAX_DOC_TEXT_CHARS = 20_000  # bound lexical-scan/serialization cost per node
#: Pointer nodes (Story 13.1) never carry the source body. Keep the
#: extract well under the general doc bound so a PRD cannot sneak in
#: through truncation.
_MAX_POINTER_TEXT_CHARS = 4_000
_MAX_POINTER_IDS = 60
_MAX_POINTER_HEADINGS = 40
_FR_TOKEN_RE = re.compile(r"\bFR-\d+\b")
_AD_TOKEN_RE = re.compile(r"\bAD-\d+\b")
_POINTER_HEADING_RE = re.compile(r"^#{1,3}\s+(?P<label>(?:Epic\s+\d+|Story\s+\d+\.\d+)\b.*)$")


class CompileInProgressError(PyforgeError, RuntimeError):
    """Another `scribe graph compile` currently holds this store's lock
    (Story 3.3). Benign under a scheduler -- the CLI turns it into an
    exit-0 skip, mirroring the `flock -n` semantics the runbook's cron
    line adds as its own outer layer."""


@dataclass(frozen=True)
class CompileResult:
    """What `compile_graph()` did, for the CLI layer to report back."""

    node_count: int
    invalidated_count: int
    stale_count: int
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
    transcript_root: Path | None = None,
    compiled_at: datetime | None = None,
) -> CompileResult:
    """Rebuild the compiled graph from scratch from the seven named surfaces.

    `nightly` is accepted for CLI/scheduling clarity only -- compile is
    unattended-by-construction either way (no prompts in any code path).
    Raises `ValueError` if `memory_root` does not exist, before any read;
    raises `CompileInProgressError` (Story 3.3) if another compile already
    holds this store's lock, before any store mutation.
    Pass `store` directly (e.g. a `FlatFileGraphStore` under `tmp_path`) in
    tests instead of relying on `store_path`'s repo-relative default.
    `transcript_root` defaults to `default_transcript_root()` when `None`
    (production wiring), matching the `store`/`store_path` injection pattern
    already used for testability -- pass an explicit, empty directory in
    tests to avoid picking up a developer machine's real session transcripts.
    """
    if not memory_root.is_dir():
        raise ValueError(
            f"{memory_root} does not exist -- run `scribe graph compile` from the repo root "
            "(the checked-in .claude/memory/ tree must already exist)"
        )

    if store is None:
        from pyforge.scribe.graph_store_plugins import open_graph_store

        store = open_graph_store(store_path or default_store_path(repo_root))

    resolved_path = Path(getattr(store, "store_path", store_path or default_store_path(repo_root)))

    with _compile_lock(resolved_path):
        warnings: list[str] = []
        compile_started = compiled_at or datetime.now(timezone.utc)
        store.reset()
        if hasattr(store, "compiled_at"):
            store.compiled_at = compile_started

        memory_nodes = _read_memory_surface(memory_root, repo_root, warnings)
        for node in memory_nodes:
            store.upsert_node(node)

        for node in _read_memlog_surface(repo_root):
            store.upsert_node(node)

        for node in _read_changelog_surface(repo_root):
            store.upsert_node(node)

        for node in _read_retro_surface(repo_root):
            store.upsert_node(node)

        for node in _read_facts_ledger_surface(repo_root):
            store.upsert_node(node)

        for node in _read_dream_surface(repo_root):
            store.upsert_node(node)

        for node in _read_spec_surface(repo_root):
            store.upsert_node(node)

        for node in _read_story_spec_surface(repo_root):
            store.upsert_node(node)

        for node in _read_planning_pointer_surface(repo_root):
            store.upsert_node(node)

        for node in _read_named_docs_surface(repo_root):
            store.upsert_node(node)

        for node in _read_git_surface(repo_root, max_commits, warnings):
            store.upsert_node(node)

        resolved_transcript_root = transcript_root if transcript_root is not None else default_transcript_root()
        transcript_nodes = _read_transcript_surface(
            memory_root,
            resolved_transcript_root,
            warnings,
            cache_path=_transcript_scan_cache_path(resolved_path),
        )
        for node in transcript_nodes:
            store.upsert_node(node)

        if graphify_extra_enabled():
            try:
                for node in ingest_repo(repo_root, warnings=warnings):
                    store.upsert_node(node)
            except Exception as exc:  # noqa: BLE001 -- an extra degrades, it never aborts a nightly compile
                warnings.append(f"graphify compile_surface extra failed -- skipped: {exc}")

        invalidated_count = _apply_supersession(memory_root, memory_nodes, store, warnings)

        stale_count = _apply_staleness(store, repo_root, warnings, compiled_at=compile_started)

        store.commit()

    return CompileResult(
        node_count=len(list(store.iter_nodes())),
        invalidated_count=invalidated_count,
        stale_count=stale_count,
        store_path=resolved_path,
        warnings=tuple(warnings),
    )


def _transcript_scan_cache_path(resolved_store_path: Path) -> Path:
    """The scan cache lives beside the graph store file (Story 3.3) -- in
    production that is `.claude/data/pyforge-scribe/`, already gitignored
    and already the home of derived, disposable artifacts (AD-1); in tests
    it follows the injected store into `tmp_path` so no test ever touches a
    real cache."""
    return resolved_store_path.parent / "transcript-scan-cache.json"


@contextlib.contextmanager
def _compile_lock(store_target: Path):
    """Refuse -- never queue -- an overlapping compile against one store
    (Story 3.3).

    The same cross-platform stdlib advisory-lock shape as
    `capture.py::_locked` (``fcntl`` on POSIX, ``msvcrt`` on Windows; lock
    file in the OS temp dir keyed by the resolved target path, never inside
    the repo tree), with one deliberate difference: `capture()` WAITS up to
    its timeout because two captures are both meant to land, while two
    concurrent compiles are pure waste -- each is a full rebuild of the
    same derived store -- so a busy lock raises `CompileInProgressError`
    immediately instead of polling.
    """
    root_key = hashlib.sha256(str(store_target.resolve()).encode("utf-8")).hexdigest()[:16]
    lock_path = Path(tempfile.gettempdir()) / f"pyforge-scribe-compile-{root_key}.lock"
    lock_file = open(lock_path, "a+")
    busy_message = (
        f"another `scribe graph compile` already holds the lock for {store_target} "
        f"({lock_path}) -- skipped, nothing recompiled"
    )
    try:
        if sys.platform == "win32":
            import msvcrt

            lock_file.seek(0)  # lock a consistent byte-0 region across processes
            try:
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise CompileInProgressError(busy_message) from None
            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise CompileInProgressError(busy_message) from None
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    finally:
        lock_file.close()


# --- surface: .claude/memory/ -------------------------------------------------


def _read_memory_surface(memory_root: Path, repo_root: Path, warnings: list[str]) -> list[GraphNode]:
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
    """Station retros only — not `*retro*` anywhere (story specs, skill
    templates, team-memory slugs, gitignored implementation copies)."""
    nodes: list[GraphNode] = []
    pattern = repo_root / "_bmad-output" / "projects"
    if not pattern.is_dir():
        return []
    for path in sorted(pattern.glob("*/planning-artifacts/retros/*.md")):
        if path.is_file() and not _is_excluded(path.relative_to(repo_root).parts):
            nodes.append(_node_from_text_file(path, kind="doc", repo_root=repo_root))
    return nodes


# --- surface: Herald fact ledgers (Story 8.3) ---------------------------------


def _read_facts_ledger_surface(repo_root: Path) -> list[GraphNode]:
    """One `kind=doc` node per `presentations/<slug>/facts.yaml`.

    Herald owns derivation (`deck-facts`); Scribe only compiles the derived
    ledger. Missing `presentations/` is the ordinary case in a tmp fixture
    and contributes zero nodes with no warning. Nested or repo-root
    `facts.yaml` files are not this surface -- the glob is one slug deep so
    the 558-file presentations tree (fragments, `.dc.html`, dated Marp,
    copied deck engines) stays out.
    """
    presentations = repo_root / "presentations"
    if not presentations.is_dir():
        return []
    nodes: list[GraphNode] = []
    for path in sorted(presentations.glob("*/facts.yaml")):
        if not path.is_file():
            continue
        node = _node_from_text_file(path, kind="doc", repo_root=repo_root)
        nodes.append(node.model_copy(update={"title": _facts_ledger_title(node.text, node.citation)}))
    return nodes


def _facts_ledger_title(text: str, relpath: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("deck:"):
            deck = stripped.split(":", 1)[1].strip().strip("\"'")
            return f"facts:{deck}" if deck else relpath
        return stripped
    return relpath


_ACTIVE_DREAM_STATUSES = frozenset({"dreamt", "pitched", "specified"})
_ACTIVE_SPEC_STATUSES = frozenset({"ready", "in-progress"})
#: Ledger rows that mean "this story spec is the one a session is on."
#: `done` is the historical corpus. `backlog` is not yet handed to dev.
_IN_FLIGHT_STORY_STATUSES = frozenset({"ready-for-dev", "in-progress", "review"})
_STORY_SPEC_NAME_RE = re.compile(r"^spec-(?P<key>\d+-\d+-.+)\.md$")
_LEDGER_RELPATH = Path("planning-artifacts") / "sprint-status-ledger.yaml"


def _frontmatter_status(text: str) -> str | None:
    if not text.startswith("---"):
        return None
    closing = text.find("\n---", 3)
    if closing < 0:
        return None
    for line in text[3:closing].splitlines():
        stripped = line.strip()
        if stripped.startswith("status:"):
            raw = stripped.split(":", 1)[1].strip()
            token = raw.split()[0] if raw else ""
            return token.strip("'\"") or None
    return None


def _read_dream_surface(repo_root: Path) -> list[GraphNode]:
    dreams = repo_root / "docs" / "dreams"
    if not dreams.is_dir():
        return []
    nodes: list[GraphNode] = []
    for path in sorted(dreams.glob("*.md")):
        if path.name == "README.md" or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if _frontmatter_status(text) not in _ACTIVE_DREAM_STATUSES:
            continue
        nodes.append(_node_from_text_file(path, kind="doc", repo_root=repo_root))
    return nodes


def _read_spec_surface(repo_root: Path) -> list[GraphNode]:
    specs_root = repo_root / "_bmad-output" / "projects"
    if not specs_root.is_dir():
        return []
    nodes: list[GraphNode] = []
    for path in sorted(specs_root.glob("*/planning-artifacts/specs/*/SPEC.md")):
        if not path.is_file() or _is_excluded(path.relative_to(repo_root).parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if _frontmatter_status(text) not in _ACTIVE_SPEC_STATUSES:
            continue
        nodes.append(_node_from_text_file(path, kind="doc", repo_root=repo_root))
    return nodes


def _parse_ledger_story_status(text: str) -> dict[str, str]:
    """Map story keys to statuses from a sprint-status-ledger.yaml body.

    Line parser only — compile stays off PyYAML (Story 8.3). Epic keys are
    ignored. A later top-level key ends the `development_status:` block."""
    statuses: dict[str, str] = {}
    in_block = False
    for line in text.splitlines():
        if not in_block:
            if line.startswith("development_status:"):
                in_block = True
            continue
        if line and not line[0].isspace() and not line.startswith("#"):
            break
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key, value = key.strip(), value.strip().strip("'\"")
        if not key or key.startswith("epic-"):
            continue
        statuses[key] = value
    return statuses


def _read_story_spec_surface(repo_root: Path) -> list[GraphNode]:
    """In-flight story specs only (Story 10.1). Ledger is the oracle."""
    projects = repo_root / "_bmad-output" / "projects"
    if not projects.is_dir():
        return []
    nodes: list[GraphNode] = []
    for project_dir in sorted(p for p in projects.iterdir() if p.is_dir()):
        ledger_path = project_dir / _LEDGER_RELPATH
        if not ledger_path.is_file():
            continue
        statuses = _parse_ledger_story_status(ledger_path.read_text(encoding="utf-8", errors="replace"))
        specs = project_dir / "planning-artifacts" / "specs"
        if not specs.is_dir():
            continue
        for path in sorted(specs.glob("spec-*-*.md")):
            if not path.is_file():
                continue
            match = _STORY_SPEC_NAME_RE.fullmatch(path.name)
            if match is None:
                continue
            if statuses.get(match.group("key")) not in _IN_FLIGHT_STORY_STATUSES:
                continue
            if _is_excluded(path.relative_to(repo_root).parts):
                continue
            nodes.append(_node_from_text_file(path, kind="doc", repo_root=repo_root))
    return nodes


def _read_planning_pointer_surface(repo_root: Path) -> list[GraphNode]:
    """Named Brief / PRD / Architecture-spine / ``epics.md`` pointers
    (Story 13.1). Documents stay SoT as files; the graph stores title,
    path, status, and an FR/AD/heading extract — never the body."""
    projects = repo_root / "_bmad-output" / "projects"
    if not projects.is_dir():
        return []
    nodes: list[GraphNode] = []
    for project_dir in sorted(p for p in projects.iterdir() if p.is_dir()):
        planning = project_dir / "planning-artifacts"
        if not planning.is_dir():
            continue
        for path, role in _planning_pointer_candidates(planning):
            if _is_excluded(path.relative_to(repo_root).parts):
                continue
            nodes.append(_node_from_planning_pointer(path, role=role, repo_root=repo_root))
    return nodes


def _planning_pointer_candidates(planning: Path) -> list[tuple[Path, str]]:
    """Named globs only — not a walk of ``planning-artifacts/``."""
    found: list[tuple[Path, str]] = []
    seen: set[Path] = set()

    def _add(path: Path, role: str) -> None:
        resolved = path.resolve()
        if resolved in seen or not path.is_file():
            return
        seen.add(resolved)
        found.append((path, role))

    for name, role in (
        ("epics.md", "epics"),
        ("prd.md", "prd"),
        ("PRD.md", "prd"),
        ("architecture.md", "architecture"),
    ):
        _add(planning / name, role)
    for path in sorted(planning.glob("prds/*/prd.md")):
        _add(path, "prd")
    for path in sorted(planning.glob("briefs/*/brief.md")):
        _add(path, "brief")
    for path in sorted(planning.glob("architecture/*/ARCHITECTURE-SPINE.md")):
        _add(path, "architecture")
    return found


def _unique_tokens(text: str, pattern: re.Pattern[str], *, limit: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for match in pattern.finditer(text):
        token = match.group(0)
        if token in seen:
            continue
        seen.add(token)
        out.append(token)
        if len(out) >= limit:
            break
    return out


def _pointer_headings(text: str) -> list[str]:
    headings: list[str] = []
    for line in text.splitlines():
        match = _POINTER_HEADING_RE.match(line.strip())
        if match is None:
            continue
        headings.append(match.group("label").strip()[:120])
        if len(headings) >= _MAX_POINTER_HEADINGS:
            break
    return headings


def _node_from_planning_pointer(path: Path, *, role: str, repo_root: Path) -> GraphNode:
    relpath = path.relative_to(repo_root).as_posix()
    raw = path.read_text(encoding="utf-8", errors="replace")
    status = _frontmatter_status(raw) or "-"
    title = next(
        (line.strip("# ").strip() for line in raw.splitlines() if line.startswith("#")),
        f"pointer:{role}:{relpath}",
    )
    ids = _unique_tokens(raw, _FR_TOKEN_RE, limit=_MAX_POINTER_IDS)
    remaining = _MAX_POINTER_IDS - len(ids)
    if remaining:
        ids.extend(_unique_tokens(raw, _AD_TOKEN_RE, limit=remaining))
    headings = _pointer_headings(raw)
    lines = [
        f"pointer:{role}",
        f"path:{relpath}",
        f"status:{status}",
        f"title:{title}",
    ]
    if ids:
        lines.append("ids: " + " ".join(ids))
    if headings:
        lines.append("headings:")
        lines.extend(f"- {item}" for item in headings)
    text = "\n".join(lines)
    if len(text) > _MAX_POINTER_TEXT_CHARS:
        text = text[:_MAX_POINTER_TEXT_CHARS]
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return GraphNode(
        id=f"doc:{relpath}",
        kind="doc",
        title=title or relpath,
        text=text,
        citation=relpath,
        valid_from=mtime,
    )


def _read_named_docs_surface(repo_root: Path) -> list[GraphNode]:
    """How-tos and the library catalog only (Story 14.1). Never ``docs/**``."""
    nodes: list[GraphNode] = []
    how_to = repo_root / "docs" / "how-to"
    if how_to.is_dir():
        for path in sorted(how_to.glob("*.md")):
            if path.name == "README.md" or not path.is_file():
                continue
            nodes.append(_node_from_text_file(path, kind="doc", repo_root=repo_root))
    catalog = repo_root / "docs" / "reference" / "library-llms-full.md"
    if catalog.is_file():
        nodes.append(_node_from_library_catalog_extract(catalog, repo_root=repo_root))
    return nodes


def _node_from_library_catalog_extract(path: Path, *, repo_root: Path) -> GraphNode:
    """``##`` section titles only — the catalog file stays SoT."""
    relpath = path.relative_to(repo_root).as_posix()
    raw = path.read_text(encoding="utf-8", errors="replace")
    title = next(
        (line.strip("# ").strip() for line in raw.splitlines() if line.startswith("#")),
        relpath,
    )
    headings = [line.strip() for line in raw.splitlines() if line.startswith("## ")][:_MAX_POINTER_HEADINGS]
    lines = [
        "pointer:library-catalog",
        f"path:{relpath}",
        f"title:{title}",
    ]
    if headings:
        lines.append("headings:")
        lines.extend(f"- {item[3:].strip()}" for item in headings)
    text = "\n".join(lines)
    if len(text) > _MAX_POINTER_TEXT_CHARS:
        text = text[:_MAX_POINTER_TEXT_CHARS]
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return GraphNode(
        id=f"doc:{relpath}",
        kind="doc",
        title=title or relpath,
        text=text,
        citation=relpath,
        valid_from=mtime,
    )


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
    """All files whose NAME matches ``pattern``'s final component, outside
    the excluded directories.

    Implemented as an `os.walk` that PRUNES excluded directories instead of
    a `Path.glob("**/...")` that filters them afterwards (Story 3.3 review
    finding: glob still traversed `.git`/`.pixi`/the worktree homes it was
    about to discard, and on the live repo the `.memlog.md` glob alone
    exceeded 9 minutes -- which made the "nightly" compile verb
    non-terminating in practice, the exact condition Story 3.3 exists to
    end). The result set is identical to the old post-hoc filter: a file
    was excluded iff some ancestor path component tripped `_is_excluded`,
    and refusing to descend at the first tripping component removes exactly
    those files. Like `Path.glob`, `os.walk` does not follow directory
    symlinks, and neither hides dot-prefixed entries.
    """
    name_pattern = pattern.rsplit("/", 1)[-1]
    results: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        rel_parts = Path(dirpath).relative_to(repo_root).parts
        dirnames[:] = [d for d in dirnames if not _is_excluded(rel_parts + (d,))]
        for filename in filenames:
            # fnmatchcase, not fnmatch: `Path.glob` matched case-sensitively
            # on every platform, and this must stay a pure traversal-cost
            # fix, never a silent node-set change.
            if not fnmatch.fnmatchcase(filename, name_pattern):
                continue
            path = Path(dirpath) / filename
            if path.is_file():
                results.append(path)
    return sorted(results)


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


# --- surface: session transcripts (Story 3.1's scanner, registered here as a
# --- compile source per Story 3.2 / CAP-2) ------------------------------------


def _read_transcript_surface(
    memory_root: Path,
    transcript_root: Path,
    warnings: list[str],
    cache_path: Path | None = None,
) -> list[GraphNode]:
    """Registers Story 3.1's `scan_transcripts()` output as the sixth
    compile source (CAP-2). All decision-marking/dedup logic -- and, since
    Story 3.3, the caps/timeout bounds and the mtime+size scan cache
    (`cache_path`, pointed at the store's own directory by
    `compile_graph()`) -- lives in that scanner; no second implementation
    here (Epic 3's own Cross-Story Dependencies). The scanner's own
    warnings (cap skips, per-file timeouts, an unwritable cache) are
    forwarded onto this compile's warning channel. A missing/unreadable
    `transcript_root` (the ordinary case: transcripts are per-user/local,
    so a machine that has simply never run a session against this repo has
    no root at all) degrades to a warning and zero nodes, same as every
    other optional surface -- it never aborts the compile.

    A per-`(source_file, line_number)` occurrence counter disambiguates
    multiple candidates on one transcript line into distinct ids:
    `transcript:<file>:L<line>` for the first, `transcript:<file>:L<line>:1`,
    `:2`, ... for repeats. Keying off the candidate's own file+line identity
    (rather than a single global running index) keeps an already-assigned id
    stable when a new transcript file contributes *different* content: a
    global index would re-number every later candidate instead. It does NOT
    make ids stable in general -- `scan_transcripts()` dedups repeated
    sentences across files in sorted-filename order, so the SAME sentence
    appearing in a new, earlier-sorting file re-homes that node onto the new
    file's id (review finding: verified, `session-z.jsonl:L1` ->
    `session-a.jsonl:L1`). Node identity here follows the surviving
    candidate's own file+line, not a stable per-fact key.
    """
    try:
        proposal = scan_transcripts(transcript_root, memory_root, cache_path=cache_path)
    except ValueError as exc:
        warnings.append(_transcript_unavailable_warning(transcript_root, exc))
        return []

    warnings.extend(proposal.warnings)

    # `scan_transcripts()` swallows an `OSError` from its own glob, so an
    # existing-but-unreadable root would otherwise be indistinguishable from
    # "nothing decision-shaped was said" -- zero nodes AND zero warnings,
    # contradicting this story's own "missing/unreadable ... degrades to a
    # warning" contract (review finding). Probe the listing explicitly.
    #
    # Only when the scan came back empty, though: candidates ARE proof the
    # root was listable, and probing unconditionally meant a root pruned
    # between the scan and the probe (the same rotate-mid-compile race
    # `_transcript_valid_from()` guards) threw away real, already-computed
    # nodes and mislabelled them "does not exist -- expected" (review
    # finding: reproduced).
    if not proposal.candidates:
        try:
            next(transcript_root.iterdir(), None)
        except OSError as exc:
            warnings.append(_transcript_unavailable_warning(transcript_root, exc))
            return []

    nodes: list[GraphNode] = []
    occurrence: dict[tuple[Path, int], int] = {}
    for candidate in proposal.candidates:
        key = (candidate.source_file, candidate.line_number)
        index = occurrence.get(key, 0)
        occurrence[key] = index + 1
        citation = f"{candidate.source_file.name}:L{candidate.line_number}"
        node_id = f"transcript:{citation}" if index == 0 else f"transcript:{citation}:{index}"
        nodes.append(
            GraphNode(
                id=node_id,
                kind="transcript",
                title=candidate.snippet,
                text=candidate.text,
                citation=citation,
                valid_from=_transcript_valid_from(candidate),
            )
        )
    return nodes


def _transcript_unavailable_warning(transcript_root: Path, exc: Exception) -> str:
    """The one warning wording for every "surface contributed nothing"
    reason.

    Deliberately does NOT forward `scan_transcripts()`'s own `ValueError`
    text: that message ends in "pass --source to point at the correct
    user-local session-transcript directory", and `--source` exists on
    `scribe capture --transcripts`, not on `scribe graph compile` (which
    this story's own contract forbids giving one) -- so forwarding it told
    operators of the unattended path to reach for a flag that command does
    not accept (review finding). The reason is re-derived here instead, so
    a genuine misconfiguration stays just as diagnosable.
    """
    if not transcript_root.exists():
        reason = "does not exist"
    elif not transcript_root.is_dir():
        reason = "is not a directory"
    else:
        reason = f"is not readable ({exc.__class__.__name__})"
    return (
        f"transcript surface unavailable ({transcript_root} {reason}) -- expected "
        "when this machine has no session transcripts for this repo; contributed "
        "zero transcript nodes"
    )


def _transcript_valid_from(candidate: TranscriptCandidate) -> datetime:
    """`candidate.timestamp` parsed as ISO-8601 first; falling back to the
    source file's own mtime -- deliberately NOT `datetime.now()` as the FIRST
    fallback (unlike the git-surface's unparseable-date fallback above),
    because `datetime.now()` here would break `compile_graph()`'s own
    byte-identical-rerun guarantee for any candidate lacking a parseable
    timestamp. `fromisoformat()` is guarded against both `ValueError` (an
    unparseable string) and `TypeError` (a non-string `timestamp`, e.g. a
    raw JSON number) -- review finding. The mtime `stat()` call is itself
    guarded: a transcript file is per-user/local and can be pruned or
    rotated outside Scribe's control, so it can vanish between
    `scan_transcripts()` returning its candidates and this stat -- that race
    (plus `OverflowError` from an out-of-range mtime -- review finding)
    degrades to `datetime.now(timezone.utc)` (breaking idempotency only in
    this narrow, rare case, same tradeoff the git-surface already accepts
    for its own unparseable-date case) rather than raising and aborting the
    whole compile.

    The parsed result is normalized to tz-aware UTC. A transcript timestamp
    carrying no offset (`"2026-08-20T12:00:00"`) parses to a NAIVE datetime,
    and every other surface's `valid_from` is tz-aware UTC -- mixing the two
    on one graph makes any cross-node comparison (sorting, an AD-4
    bi-temporal `valid_from` filter) raise `TypeError: can't compare
    offset-naive and offset-aware datetimes` (review finding: reproduced).
    A naive timestamp is read as UTC, matching the mtime fallback below.
    """
    try:
        parsed = datetime.fromisoformat(candidate.timestamp)
    except ValueError, TypeError:
        # TypeError: a transcript entry whose `timestamp` field is a JSON
        # number (or any other non-string value) makes `fromisoformat`
        # raise TypeError rather than ValueError -- review finding.
        pass
    else:
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromtimestamp(candidate.source_file.stat().st_mtime, tz=timezone.utc)
    except OSError, OverflowError:
        # OverflowError: `fromtimestamp()` can raise this for an
        # out-of-range mtime, per its own docs -- review finding.
        return datetime.now(timezone.utc)


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
                    f"{path}: supersedes {record.supersedes!r} does not resolve to a known memory node -- skipped"
                )
                continue
            ended_at = source_node.valid_from if source_node is not None else datetime.now(timezone.utc)
            store.invalidate_edge(target_id, ended_at=ended_at, superseded_by=source_id)
            invalidated += 1
    return invalidated


# --- staleness flag (Story 6.3, CAP-13) ---------------------------------------

#: A `code` node's citation (Story 6.1's graphify extra) carries a
#: `:L<line>` suffix the underlying source file's own path does not --
#: strip it before treating the citation as a path. Every other citation
#: shape checked here (`memory`/`memlog`/`doc`) is already a bare
#: repo-relative path.
_STALENESS_CODE_CITATION_RE = re.compile(r"^(?P<path>.+):L[0-9]+$")

#: Node kinds with no git-trackable source-file counterpart to compare
#: against: a `commit` node's citation (`commit:<sha>`) names the commit
#: itself, not a file, and a `transcript` node's citation is a per-user,
#: per-machine session log that is never part of this repo's git history
#: (Story 3.2) -- mirrors `recall.py::_citation_is_resolvable`'s own split.
_STALENESS_EXEMPT_KINDS = frozenset({"commit", "transcript"})


def _staleness_source_path(node: GraphNode) -> str | None:
    """The repo-relative path to compare against `compiled_at`, or `None`
    when this node's citation has no git-trackable source file."""
    if node.kind in _STALENESS_EXEMPT_KINDS:
        return None
    if node.kind == "code":
        match = _STALENESS_CODE_CITATION_RE.match(node.citation)
        return match.group("path") if match else node.citation
    return node.citation


def _apply_staleness(
    store: GraphStore,
    repo_root: Path,
    warnings: list[str],
    *,
    compiled_at: datetime,
) -> int:
    """Flag `stale=True` on every CURRENT node (Story 6.3 / 8.4) whose
    source file's latest git commit is authored after `compiled_at`.

    A git-timestamp comparison only -- no LLM call, no new dependency, and
    `_apply_supersession()` above is untouched: this function only READS
    `node.is_current`, it never writes `valid_until`/`superseded_by`. A node
    Story 2.3 already invalidated is not current, so it is skipped here --
    "a node with a declared `supersedes:` edge pointing at it ... is never
    flagged stale" holds for free, without re-deriving the supersedes graph.
    """
    git_bin = shutil.which("git")
    if git_bin is None:
        warnings.append("git binary not found on PATH -- skipping staleness check")
        return 0

    flagged = 0
    for node in list(store.iter_nodes()):
        if not node.is_current or node.stale:
            continue
        relpath = _staleness_source_path(node)
        if relpath is None:
            continue
        latest_commit_time = _git_latest_commit_time(repo_root, relpath, git_bin)
        if latest_commit_time is None:
            continue
        if latest_commit_time > compiled_at:
            store.upsert_node(node.model_copy(update={"stale": True}))
            flagged += 1
    return flagged


def source_committed_after(repo_root: Path, node: GraphNode, compiled_at: datetime) -> bool:
    """True when this node's git-trackable source has a commit after
    `compiled_at` (Story 11.1). Missing git or no history is False."""
    relpath = _staleness_source_path(node)
    if relpath is None:
        return False
    git_bin = shutil.which("git")
    if git_bin is None:
        return False
    latest = _git_latest_commit_time(repo_root, relpath, git_bin)
    return latest is not None and latest > compiled_at


def _git_latest_commit_time(repo_root: Path, relpath: str, git_bin: str) -> datetime | None:
    """The authored date of the latest commit touching `relpath`, or `None`
    when it has no git history (never committed -- the ordinary case for a
    just-captured or gitignored source, not an error) or `git` itself
    fails/times out -- degrades like every other optional git read in this
    module rather than aborting the compile."""
    argv = [git_bin, "log", "-1", "--format=%aI", "--", relpath]
    try:
        completed = subprocess.run(
            argv,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except OSError, subprocess.TimeoutExpired:
        return None
    if completed.returncode != 0:
        return None
    output = completed.stdout.strip()
    if not output:
        return None
    try:
        return datetime.fromisoformat(output)
    except ValueError:
        return None
