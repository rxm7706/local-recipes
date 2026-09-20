"""pyforge.scribe.transcripts — the transcript scanner (CAP-1, Story 3.1).

Curated `.claude/memory/` is a filter: decisions and facts an assistant
stated out loud during a session but that were never explicitly captured
live only in that session's raw `.jsonl` transcript. `scribe capture
--promote` only reaches already-curated personal auto-memory, one layer
above where this gap lives. This module mines a user's own raw session
transcripts (`~/.claude/projects/<encoded-repo-path>/*.jsonl`) for
assistant-authored sentences matching a small set of decision/fact marker
phrases, skips anything whose content already overlaps curated
`.claude/memory/`, and feeds the survivors into the same
proposal-then-confirm mechanics `promote.py` already established.

Read-only against its inputs: `scan_transcripts()` never writes the
transcript files themselves -- a session transcript is a historical log
this package does not own and must never mutate (unlike `promote.py`'s
pointer-stub write-back against its OWN foreign-but-mutable source). The
same curated-overlap check that suppresses already-promoted content also
makes re-running `--transcripts` idempotent: once a candidate is captured,
its text lives in `.claude/memory/`, so the next scan sees it as
curated-covered and stays quiet -- no separate "already scanned" marker is
needed. Zero network calls; pure stdlib (`json`, `re`, `difflib`, `time`)
-- no new dependency (AD-6).

**The scan is bounded (Story 3.3, DW-FU-3-2-2).** Every other compile
surface had a ceiling (`max_commits=100`, `_MAX_DOC_TEXT_CHARS=20_000`,
`timeout=30` on `git log`); this one had none, and Story 3.2 put it on the
unattended nightly path. Three bounds now apply as a precondition of
scheduling it: a file-count cap and a total-byte budget select what is read
(newest files first -- when the surface outgrows the budget, the sessions
most likely to hold not-yet-curated decisions are the recent ones), and a
per-file timeout abandons a pathologically slow file with partial results
rather than hanging the run. Defaults are sized to cover the live surface
measured for DW-FU-3-2-2 (27 files / 631MB) without dropping data. An
optional mtime+size-keyed scan cache (`cache_path`, the one write this
module performs, and only when a caller opts in -- `compile.py` points it
at the graph store's own gitignored directory) makes a re-run over an
unchanged surface skip re-reading unchanged files. The cache stores each
file's raw marker-matched sentences PRE-dedup; the curated-overlap check
re-runs on every scan, so newly curated content still silences a cached
candidate and the proposal is byte-equivalent with or without a cache hit.
"""

from __future__ import annotations

import difflib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

from pyforge.scribe.capture import _DESCRIPTION_MAX_LEN, _truncate
from pyforge.scribe.models import CAPTURE_TYPES, CaptureType, parse_capture_file

#: Marker phrases (case-insensitive substring match against each split
#: sentence) that mark a sentence as containing a decision or fact worth
#: surfacing for human review. A bare substring match produces occasional
#: false positives. For `scribe capture --transcripts` that is absorbed by
#: the human confirm gate, which still stands between every candidate and
#: anything written to `.claude/memory/`. Story 3.2's compile surface has
#: no such gate -- `compile.py::_read_transcript_surface()` registers this
#: same candidate set unattended -- so there a false positive costs one
#: low-overlap node in a derived, fully re-computable graph (AD-1), never a
#: durable curated record (review finding: this note previously claimed the
#: confirm gate as an unconditional property of every caller).
_DECISION_MARKERS: tuple[str, ...] = (
    "we decided",
    "decided to",
    "the decision is",
    "going with",
    "settled on",
    "we'll go with",
    "the plan is to",
    "we chose",
    "chose to",
    "concluded that",
)

#: Simple, dependency-free sentence splitter -- matches this repo's existing
#: "pure regex, no NLP" precedent in `promote.py`'s `rewrite_team_voice()`.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")

#: A candidate is dropped if its string-similarity ratio against any
#: existing curated sentence meets or exceeds this threshold (see
#: "Dedup against curated memory" in the spec's Design Notes). Stdlib
#: `difflib` -- no new dependency, consistent with AD-6.
_DEDUP_RATIO_THRESHOLD = 0.6

#: Every transcript candidate defaults to this capture type -- a
#: per-candidate manual type override is out of scope for this story; the
#: reviewer accepts or declines the whole batch, matching `--promote`'s
#: existing whole-batch confirm granularity.
_DEFAULT_CAPTURE_TYPE: CaptureType = "project"

#: Scan bounds (Story 3.3). Sized against the DW-FU-3-2-2 measurement of
#: the live surface (27 files / 631MB): ~10x headroom on file count, ~60%
#: on bytes -- generous enough that nothing is silently dropped at
#: introduction, bounded enough that unbounded transcript growth cannot
#: make the nightly compile cost-unbounded again. The timeout matches the
#: `timeout=30` the git-history surface already accepts.
_DEFAULT_MAX_FILES = 256
_DEFAULT_MAX_TOTAL_BYTES = 1_073_741_824  # 1 GiB
_DEFAULT_PER_FILE_TIMEOUT_S = 30.0

#: Bumped whenever the cache entry shape changes -- a mismatched version is
#: treated as an empty cache, never migrated.
_SCAN_CACHE_VERSION = 1


@dataclass(frozen=True)
class TranscriptCandidate:
    """One un-curated decision/fact sentence mined from a session transcript.

    `text` is the full, untruncated matched sentence -- this is what gets
    captured to `.claude/memory/` if the reviewer confirms. `snippet` is a
    `_truncate()`d preview (~120 chars) used for display only, never as the
    record body -- mirrors `promote.py`'s existing split between
    `rewritten_text` (full body, captured) and `rewritten_description`
    (truncated, index-line only). Display-only does not mean in-memory
    only: Story 3.2's compile surface persists `snippet` as a transcript
    `GraphNode.title` (its display field) while `text` carries the full
    sentence, so an earlier "never written to disk" claim here no longer
    holds (review finding).
    """

    source_file: Path
    line_number: int
    timestamp: str
    text: str
    snippet: str
    capture_type: CaptureType


@dataclass(frozen=True)
class TranscriptScanProposal:
    """The full scan result -- read-only, nothing here has been written to
    disk (the opt-in scan cache is the one exception, and it never holds
    anything the proposal does not).

    `warnings` (Story 3.3) carries per-scan degradation notes -- files
    skipped by the caps, a per-file timeout, an unwritable cache -- in the
    same "warn and keep going" voice `compile.py`'s own warning channel
    uses; empty on a fully clean scan.
    """

    transcript_root: Path
    candidates: tuple[TranscriptCandidate, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class _RawMatch:
    """One marker-matched sentence, PRE-dedup -- the unit the scan cache
    stores. Dedup against curated memory deliberately happens after cache
    resolution (see the module docstring), so this carries no overlap
    verdict."""

    line_number: int
    timestamp: str  # passthrough from the transcript entry -- like
    # `TranscriptCandidate.timestamp`, a non-string JSON value (e.g. epoch
    # millis) flows through unconverted; `compile.py` guards for that.
    text: str


@dataclass(frozen=True)
class _FileStat:
    """One candidate transcript file's identity for cap selection and
    cache keying."""

    path: Path
    size: int
    mtime_ns: int


def default_transcript_root() -> Path:
    """Claude Code's per-project session-transcript dir for the current cwd.

    Mirrors `promote.py`'s `default_user_local_root()` path-encoding
    heuristic exactly (every non-alphanumeric character in the absolute cwd
    path becomes a literal `-`, one-for-one), but resolves to
    `~/.claude/projects/<encoded-cwd>/` -- the parent of `.../memory/` --
    since raw `*.jsonl` session transcripts live directly in that directory,
    not in a `memory` subdirectory. `--source` is the escape hatch, same as
    its sibling.
    """
    encoded = re.sub(r"[^A-Za-z0-9]", "-", str(Path.cwd()))
    return Path.home() / ".claude" / "projects" / encoded


def scan_transcripts(
    transcript_root: Path,
    memory_root: Path,
    *,
    max_files: int = _DEFAULT_MAX_FILES,
    max_total_bytes: int = _DEFAULT_MAX_TOTAL_BYTES,
    per_file_timeout_s: float | None = _DEFAULT_PER_FILE_TIMEOUT_S,
    cache_path: Path | None = None,
) -> TranscriptScanProposal:
    """Scan `*.jsonl` under `transcript_root` for un-curated decision/fact
    sentences, within the Story 3.3 bounds.

    Read-only against both `transcript_root` and `memory_root` (the opt-in
    `cache_path` is the one write). Mines only `type == "assistant"`
    entries' `message.content[]` blocks with `type == "text"` -- never
    `thinking` (private reasoning) or `tool_use`/`tool_result` (mechanical,
    not "what was said") blocks. A malformed JSON line is skipped, never
    raised on; a file-level read/decode failure skips that whole file
    without aborting the rest of the scan. A candidate whose sentence
    overlaps curated `.claude/memory/` content (or an already-accepted
    candidate from earlier in this same scan) is dropped. Raises
    `ValueError` if `transcript_root` is not a valid directory -- before
    any read.

    Bounds: at most `max_files` files are read, allocated newest-first
    against a `max_total_bytes` byte budget (the byte cap bounds the
    whole-file `read_text`; the per-file timeout bounds line processing
    after the read); files skipped by either cap surface as one summary
    warning. `per_file_timeout_s=None` disables the timeout. A timed-out
    file keeps its partial matches (with a warning) and is left uncached so
    the next run retries it. `cache_path=None` (the default) disables the
    cache entirely -- callers with no durable home for it (the interactive
    `--transcripts` flow) simply pay the full scan.
    """
    if not transcript_root.is_dir():
        exists_but_not_a_dir = transcript_root.exists()
        reason = "is not a directory" if exists_but_not_a_dir else "does not exist"
        raise ValueError(
            f"{transcript_root} {reason} -- pass --source to point at the correct "
            "user-local session-transcript directory"
        )

    warnings: list[str] = []

    try:
        jsonl_paths = sorted(transcript_root.glob("*.jsonl"))
    except OSError:
        jsonl_paths = []

    stats: list[_FileStat] = []
    for jsonl_path in jsonl_paths:
        try:
            st = jsonl_path.stat()
        except OSError:
            continue  # same silent per-file tolerance the read path has
        stats.append(_FileStat(path=jsonl_path, size=st.st_size, mtime_ns=st.st_mtime_ns))

    selected = _select_within_caps(stats, max_files, max_total_bytes, warnings, transcript_root)

    cache = _read_scan_cache(cache_path)
    # Prune deleted files only -- a present file skipped by this run's caps
    # keeps its (still mtime+size-valid) entry for a future run.
    surviving_keys = {str(fs.path) for fs in stats}
    new_cache: dict[str, dict] = {k: v for k, v in cache.items() if k in surviving_keys}

    raw_by_file: dict[Path, list[_RawMatch]] = {}
    for fs in selected:
        key = str(fs.path)
        matches = _matches_from_cache(cache.get(key), fs)
        if matches is None:
            try:
                matches, timed_out_line = _scan_one_file(fs.path, per_file_timeout_s)
            except OSError, UnicodeDecodeError:
                continue
            if timed_out_line is not None:
                warnings.append(
                    f"transcript scan timed out after {per_file_timeout_s:g}s in "
                    f"{fs.path.name} at line {timed_out_line} -- partial results kept, "
                    "file left uncached"
                )
            else:
                new_cache[key] = {
                    "mtime_ns": fs.mtime_ns,
                    "size": fs.size,
                    "matches": [{"line": m.line_number, "timestamp": m.timestamp, "text": m.text} for m in matches],
                }
        raw_by_file[fs.path] = matches

    # Dedup phase -- after cache resolution, so newly curated content still
    # silences a cached candidate. Iteration order (sorted filename, then
    # line order) matches the pre-3.3 inline dedup byte-for-byte.
    seen_sentences: list[str] = _curated_sentences(memory_root)
    candidates: list[TranscriptCandidate] = []
    for jsonl_path in sorted(raw_by_file):
        for match in raw_by_file[jsonl_path]:
            normalized = _normalize(match.text)
            if _overlaps(normalized, seen_sentences):
                continue
            candidates.append(
                TranscriptCandidate(
                    source_file=jsonl_path,
                    line_number=match.line_number,
                    timestamp=match.timestamp,
                    text=match.text,
                    snippet=_truncate(match.text, _DESCRIPTION_MAX_LEN),
                    capture_type=_DEFAULT_CAPTURE_TYPE,
                )
            )
            seen_sentences.append(normalized)

    if cache_path is not None:
        _write_scan_cache(cache_path, new_cache, warnings)

    return TranscriptScanProposal(
        transcript_root=transcript_root,
        candidates=tuple(candidates),
        warnings=tuple(warnings),
    )


def _select_within_caps(
    stats: list[_FileStat],
    max_files: int,
    max_total_bytes: int,
    warnings: list[str],
    transcript_root: Path,
) -> list[_FileStat]:
    """Allocate the file-count and byte budgets newest-first (mtime
    descending, filename tiebreak), then hand the survivors back in
    sorted-filename order so the scan/dedup order stays exactly what
    Story 3.1 established. Greedy: an oversized file is skipped but a
    smaller, older one that still fits is kept. One summary warning covers
    everything skipped -- per-file noise would drown a 27-file surface.
    """
    by_recency = sorted(stats, key=lambda fs: (-fs.mtime_ns, fs.path.name))
    kept: list[_FileStat] = []
    budget = max_total_bytes
    skipped = 0
    for fs in by_recency:
        if len(kept) >= max_files or fs.size > budget:
            skipped += 1
            continue
        kept.append(fs)
        budget -= fs.size
    if skipped:
        warnings.append(
            f"transcript scan capped: skipped {skipped} of {len(stats)} file(s) under "
            f"{transcript_root} (max_files={max_files}, max_total_bytes={max_total_bytes}; "
            "newest files are scanned first)"
        )
    return sorted(kept, key=lambda fs: fs.path.name)


def _scan_one_file(jsonl_path: Path, per_file_timeout_s: float | None) -> tuple[list[_RawMatch], int | None]:
    """Mine one transcript file for ALL marker-matched sentences (pre-dedup).

    Returns ``(matches, timed_out_at_line)`` -- the second element is
    ``None`` on a complete scan, or the 1-based line the deadline fired on
    (everything before it is kept as a partial result).

    The whole-file read (`read_text`) is deliberately NOT guarded here --
    an `OSError`/`UnicodeDecodeError` propagates to the caller, which wraps
    this call per-file so one unreadable/mis-encoded file never aborts the
    rest of the multi-file scan. The per-line `try/except` around
    `json.loads` below is a separate, narrower guard: it only tolerates a
    single malformed JSON line, not a file-level failure. Dedup no longer
    happens here (Story 3.3): raw matches must be cacheable independent of
    the curated-memory state at scan time, so the overlap check moved to
    `scan_transcripts()`'s post-cache dedup phase.
    """
    deadline = None if per_file_timeout_s is None else time.monotonic() + per_file_timeout_s
    matches: list[_RawMatch] = []
    lines = jsonl_path.read_text(encoding="utf-8").splitlines()

    for line_number, raw_line in enumerate(lines, start=1):
        if deadline is not None and time.monotonic() > deadline:
            return matches, line_number
        stripped = raw_line.strip()
        if not stripped:
            continue
        try:
            entry = json.loads(stripped)
        except json.JSONDecodeError, ValueError:
            continue
        if not isinstance(entry, dict) or entry.get("type") != "assistant":
            continue

        timestamp = entry.get("timestamp") or "unknown time"
        message = entry.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue

        for block in content:
            if not isinstance(block, dict) or block.get("type") != "text":
                continue
            block_text = block.get("text")
            if not isinstance(block_text, str):
                continue

            for sentence in _split_sentences(block_text):
                if not _matches_marker(sentence):
                    continue
                matches.append(_RawMatch(line_number=line_number, timestamp=timestamp, text=sentence))

    return matches, None


def _read_scan_cache(cache_path: Path | None) -> dict[str, dict]:
    """The cache's `files` map, or `{}` for a missing/malformed/mismatched
    cache -- a broken cache is never fatal and never repaired in place; the
    next `_write_scan_cache()` simply replaces it."""
    if cache_path is None:
        return {}
    try:
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return {}
    if not isinstance(raw, dict) or raw.get("version") != _SCAN_CACHE_VERSION:
        return {}
    files = raw.get("files")
    return files if isinstance(files, dict) else {}


def _matches_from_cache(entry: object, fs: _FileStat) -> list[_RawMatch] | None:
    """Reconstruct a file's cached raw matches, or `None` for a miss --
    a stale (mtime/size moved) or structurally unexpected entry is a miss,
    never an error."""
    if not isinstance(entry, dict):
        return None
    if entry.get("mtime_ns") != fs.mtime_ns or entry.get("size") != fs.size:
        return None
    raw_matches = entry.get("matches")
    if not isinstance(raw_matches, list):
        return None
    out: list[_RawMatch] = []
    try:
        for m in raw_matches:
            out.append(
                _RawMatch(
                    line_number=int(m["line"]),
                    timestamp=m["timestamp"],
                    text=str(m["text"]),
                )
            )
    except KeyError, TypeError, ValueError:
        return None
    return out


def _write_scan_cache(cache_path: Path, files: dict[str, dict], warnings: list[str]) -> None:
    """Persist the cache -- an unwritable destination degrades to a warning
    (the scan result is already complete; the cache only prices the NEXT
    run), matching the compile surfaces' warn-and-keep-going posture."""
    payload = {"version": _SCAN_CACHE_VERSION, "files": files}
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, TypeError, ValueError) as exc:
        warnings.append(f"transcript scan cache not writable ({cache_path}): {exc}")


def _curated_sentences(memory_root: Path) -> list[str]:
    """Every sentence from every curated `.claude/memory/<type>/*.md` body,
    normalized for the overlap check.

    A curated file with malformed frontmatter (`parse_capture_file()`
    raises `ValueError`) or an unreadable file (`OSError`) is skipped, not
    fatal to the whole scan -- the same "skip the one bad input, keep
    going" posture this module applies to a malformed transcript file.
    """
    sentences: list[str] = []
    for capture_type in CAPTURE_TYPES:
        type_dir = memory_root / capture_type
        if not type_dir.is_dir():
            continue
        try:
            md_paths = sorted(type_dir.glob("*.md"))
        except OSError:
            continue
        for md_path in md_paths:
            try:
                record = parse_capture_file(md_path)
            except ValueError, OSError:
                continue
            sentences.extend(_normalize(s) for s in _split_sentences(record.text))
    return sentences


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


def _matches_marker(sentence: str) -> bool:
    lowered = sentence.lower()
    return any(marker in lowered for marker in _DECISION_MARKERS)


def _normalize(text: str) -> str:
    return " ".join(text.split()).lower()


def _overlaps(normalized_sentence: str, curated_normalized: list[str]) -> bool:
    return any(
        difflib.SequenceMatcher(None, normalized_sentence, curated).ratio() >= _DEDUP_RATIO_THRESHOLD
        for curated in curated_normalized
    )
