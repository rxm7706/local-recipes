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

Read-only: `scan_transcripts()` never writes anywhere, including the
transcript files themselves -- a session transcript is a historical log
this package does not own and must never mutate (unlike `promote.py`'s
pointer-stub write-back against its OWN foreign-but-mutable source). The
same curated-overlap check that suppresses already-promoted content also
makes re-running `--transcripts` idempotent: once a candidate is captured,
its text lives in `.claude/memory/`, so the next scan sees it as
curated-covered and stays quiet -- no separate "already scanned" marker is
needed. Zero network calls; pure stdlib (`json`, `re`, `difflib`) -- no new
dependency (AD-6).
"""

from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from pyforge.scribe.capture import _DESCRIPTION_MAX_LEN, _truncate
from pyforge.scribe.models import CAPTURE_TYPES, CaptureType, parse_capture_file

#: Marker phrases (case-insensitive substring match against each split
#: sentence) that mark a sentence as containing a decision or fact worth
#: surfacing for human review. A bare substring match produces occasional
#: false positives -- acceptable because every candidate still goes through
#: the human confirm gate before anything is written.
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


@dataclass(frozen=True)
class TranscriptCandidate:
    """One un-curated decision/fact sentence mined from a session transcript.

    `text` is the full, untruncated matched sentence -- this is what gets
    captured to `.claude/memory/` if the reviewer confirms. `snippet` is a
    `_truncate()`d preview (~120 chars) used ONLY for the printed proposal's
    provenance line, never written to disk -- mirrors `promote.py`'s
    existing split between `rewritten_text` (full body, captured) and
    `rewritten_description` (truncated, index-line only).
    """

    source_file: Path
    line_number: int
    timestamp: str
    text: str
    snippet: str
    capture_type: CaptureType


@dataclass(frozen=True)
class TranscriptScanProposal:
    """The full scan result -- read-only, nothing here has been written to disk."""

    transcript_root: Path
    candidates: tuple[TranscriptCandidate, ...]


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


def scan_transcripts(transcript_root: Path, memory_root: Path) -> TranscriptScanProposal:
    """Scan every `*.jsonl` under `transcript_root` for un-curated
    decision/fact sentences.

    Read-only against both `transcript_root` and `memory_root`. Mines only
    `type == "assistant"` entries' `message.content[]` blocks with
    `type == "text"` -- never `thinking` (private reasoning) or
    `tool_use`/`tool_result` (mechanical, not "what was said") blocks. A
    malformed JSON line is skipped, never raised on; a file-level read/decode
    failure skips that whole file without aborting the rest of the scan. A
    candidate whose sentence overlaps curated `.claude/memory/` content (or
    an already-accepted candidate from earlier in this same scan) is
    dropped. Raises `ValueError` if `transcript_root` is not a valid
    directory -- before any read.
    """
    if not transcript_root.is_dir():
        exists_but_not_a_dir = transcript_root.exists()
        reason = "is not a directory" if exists_but_not_a_dir else "does not exist"
        raise ValueError(
            f"{transcript_root} {reason} -- pass --source to point at the correct "
            "user-local session-transcript directory"
        )

    seen_sentences: list[str] = _curated_sentences(memory_root)
    candidates: list[TranscriptCandidate] = []

    try:
        jsonl_paths = sorted(transcript_root.glob("*.jsonl"))
    except OSError:
        jsonl_paths = []

    for jsonl_path in jsonl_paths:
        try:
            candidates.extend(_scan_one_file(jsonl_path, seen_sentences))
        except (OSError, UnicodeDecodeError):
            continue

    return TranscriptScanProposal(transcript_root=transcript_root, candidates=tuple(candidates))


def _scan_one_file(jsonl_path: Path, seen_sentences: list[str]) -> list[TranscriptCandidate]:
    """Mine one transcript file for un-curated decision/fact candidates.

    The whole-file read (`read_text`) is deliberately NOT guarded here --
    an `OSError`/`UnicodeDecodeError` propagates to the caller, which wraps
    this call per-file so one unreadable/mis-encoded file never aborts the
    rest of the multi-file scan. The per-line `try/except` around
    `json.loads` below is a separate, narrower guard: it only tolerates a
    single malformed JSON line, not a file-level failure.

    `seen_sentences` is shared across the whole scan (seeded from curated
    memory, mutated in place as candidates are accepted) so a repeated
    decision within one scan -- same file twice, or two different files --
    surfaces only once.
    """
    candidates: list[TranscriptCandidate] = []
    lines = jsonl_path.read_text(encoding="utf-8").splitlines()

    for line_number, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        try:
            entry = json.loads(stripped)
        except (json.JSONDecodeError, ValueError):
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
                normalized = _normalize(sentence)
                if _overlaps(normalized, seen_sentences):
                    continue
                candidates.append(
                    TranscriptCandidate(
                        source_file=jsonl_path,
                        line_number=line_number,
                        timestamp=timestamp,
                        text=sentence,
                        snippet=_truncate(sentence, _DESCRIPTION_MAX_LEN),
                        capture_type=_DEFAULT_CAPTURE_TYPE,
                    )
                )
                seen_sentences.append(normalized)

    return candidates


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
            except (ValueError, OSError):
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
