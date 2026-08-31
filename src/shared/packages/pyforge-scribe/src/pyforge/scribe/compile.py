"""pyforge.scribe.compile — the projection builder (Story 2.2/2.3,
AD-1/AD-5/AD-6/AD-9).

`compile_graph()` is the "compile" layer of the architecture's paradigm:
event-sourced capture with a derived, rebuildable read-model. It reads six
named real-tool surfaces -- `.claude/memory/`, `.memlog.md` files, git
history, retros, CHANGELOGs (PRD Open Question 2, resolved here), and
un-curated session transcripts (Story 3.1's `scan_transcripts()`, registered
as a compile source in Story 3.2) -- and writes one `GraphNode` per source
item through the `GraphStore` port (Story 2.1), never a specific storage
engine's client library directly (AD-5).

Every run is a FULL rebuild, never an incremental patch: `store.reset()`
clears the in-memory state, every surface is re-read from scratch, and
`store.commit()` performs one atomic write of the whole result (AD-1: "the
compiled graph is 100% derived and re-computable from source records at any
time, from scratch, with the same result"). Because node ids are derived
deterministically from source identity (file path / commit sha), and node
content depends only on the current on-disk/in-git state, two consecutive
runs against unchanged sources produce byte-identical `GraphStore` output --
the idempotency Story 2.2 requires.

That reproducibility is per-machine, not repo-wide: five of the six surfaces
are repo artifacts, but the transcript surface (Story 3.2) reads a per-user,
per-machine `~/.claude/projects/<encoded-cwd>/` tree that is not part of the
repository. Two operators compiling the same commit therefore get the same
five-surface core plus whatever transcript nodes their own machine holds --
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

**Optional seventh surface (Story 6.1).** When `SCRIBE_GRAPHIFY_EXTRA` is
truthy, `compile_graph()` also ingests `src/shared/packages/` with the
graphify `compile_surface` extra (`pyforge.scribe.extras.graphify`),
writing `code`-kind `GraphNode`s through this SAME `GraphStore` -- never a
parallel store. Off by default (AD-6): the env var is checked before the
extra's own lazy `graphify` import ever runs, so an off-mode compile is
byte-for-byte identical to the six-surface compile that predates this
story. If the extra is on but graphifyy fails to import (or errors during
extraction), that degrades to a warning like every other optional surface
here -- it does not abort the rest of the compile.
"""

from __future__ import annotations

import contextlib
import fnmatch
import hashlib
import os
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
    }
)

_DEFAULT_MAX_COMMITS = 100
_MAX_DOC_TEXT_CHARS = 20_000  # bound lexical-scan/serialization cost per node


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
) -> CompileResult:
    """Rebuild the compiled graph from scratch from the six named surfaces.

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

    resolved_path = Path(
        getattr(store, "store_path", store_path or default_store_path(repo_root))
    )

    with _compile_lock(resolved_path):
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

        resolved_transcript_root = (
            transcript_root if transcript_root is not None else default_transcript_root()
        )
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

        store.commit()

    return CompileResult(
        node_count=len(list(store.iter_nodes())),
        invalidated_count=invalidated_count,
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
    except (ValueError, TypeError):
        # TypeError: a transcript entry whose `timestamp` field is a JSON
        # number (or any other non-string value) makes `fromisoformat`
        # raise TypeError rather than ValueError -- review finding.
        pass
    else:
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromtimestamp(candidate.source_file.stat().st_mtime, tz=timezone.utc)
    except (OSError, OverflowError):
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
                    f"{path}: supersedes {record.supersedes!r} does not resolve to a known "
                    "memory node -- skipped"
                )
                continue
            ended_at = source_node.valid_from if source_node is not None else datetime.now(timezone.utc)
            store.invalidate_edge(target_id, ended_at=ended_at, superseded_by=source_id)
            invalidated += 1
    return invalidated
