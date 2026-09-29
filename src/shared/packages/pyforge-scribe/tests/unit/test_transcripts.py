"""Unit tests for pyforge.scribe.transcripts — the transcript scanner
(Story 3.1).

Every test uses `tmp_path` for both the fake transcript root and the
`.claude/memory/` curated tree — never the real
`~/.claude/projects/<encoded-path>/*.jsonl` transcripts — matching the I/O &
Edge-Case Matrix in
spec-3-1-the-scanner-surfaces-what-sessions-said-but-memory-missed.md.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from pyforge.scribe.transcripts import default_transcript_root, scan_transcripts

_MEMORY_MD_STARTER = """# Team Memory Index

## Feedback

## Project

## Reference
"""


@pytest.fixture()
def repo_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    return root


@pytest.fixture()
def memory_root(repo_root: Path) -> Path:
    root = repo_root / ".claude" / "memory"
    root.mkdir(parents=True)
    (root / "MEMORY.md").write_text(_MEMORY_MD_STARTER, encoding="utf-8")
    return root


@pytest.fixture()
def transcript_root(tmp_path: Path) -> Path:
    root = tmp_path / "transcripts"
    root.mkdir()
    return root


def _assistant_line(
    *,
    text_blocks: list[str] | None = None,
    thinking: str | None = None,
    tool_use: bool = False,
    tool_result: bool = False,
    timestamp: str = "2026-08-20T12:00:00.000Z",
) -> str:
    """Build one realistic assistant-turn JSONL line, matching the live
    `~/.claude/projects/<encoded>/*.jsonl` shape: a top-level `type`/
    `timestamp`, and `message.content[]` blocks."""
    content: list[dict] = []
    if thinking is not None:
        content.append({"type": "thinking", "thinking": thinking, "signature": "sig"})
    for text in text_blocks or []:
        content.append({"type": "text", "text": text})
    if tool_use:
        content.append({"type": "tool_use", "id": "tu_1", "name": "Bash", "input": {}})
    if tool_result:
        content.append({"type": "tool_result", "tool_use_id": "tu_1", "content": "ok"})
    entry = {
        "type": "assistant",
        "timestamp": timestamp,
        "message": {"content": content},
    }
    return json.dumps(entry)


def _user_line(text: str) -> str:
    entry = {
        "type": "user",
        "timestamp": "2026-08-20T12:00:00.000Z",
        "message": {"content": [{"type": "text", "text": text}]},
    }
    return json.dumps(entry)


def _write_jsonl(transcript_root: Path, filename: str, lines: list[str]) -> Path:
    path = transcript_root / filename
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_curated(memory_root: Path, capture_type: str, slug: str, text: str) -> Path:
    type_dir = memory_root / capture_type
    type_dir.mkdir(parents=True, exist_ok=True)
    path = type_dir / f"{slug}.md"
    path.write_text(
        f'---\nname: "{slug}"\ndescription: "{text[:60]}"\nmetadata:\n  type: {capture_type}\n---\n{text}\n',
        encoding="utf-8",
    )
    return path


# --- I/O Matrix row 1: un-curated decision surfaces ------------------------


def test_uncurated_decision_surfaces_as_one_candidate(transcript_root: Path, memory_root: Path) -> None:
    _write_jsonl(
        transcript_root,
        "session-a.jsonl",
        [_assistant_line(text_blocks=["We decided to use SQLite for the local cache."])],
    )

    proposal = scan_transcripts(transcript_root, memory_root)

    assert len(proposal.candidates) == 1
    candidate = proposal.candidates[0]
    assert candidate.text == "We decided to use SQLite for the local cache."
    assert candidate.snippet == candidate.text  # short text, no truncation needed
    assert candidate.capture_type == "project"
    assert candidate.source_file == transcript_root / "session-a.jsonl"
    assert candidate.line_number == 1
    assert candidate.timestamp == "2026-08-20T12:00:00.000Z"


# --- I/O Matrix row 2: curated-covered content stays quiet ------------------


def test_curated_covered_content_stays_quiet(transcript_root: Path, memory_root: Path) -> None:
    _write_curated(memory_root, "project", "sqlite-cache", "We decided to use SQLite for the local cache.")
    _write_jsonl(
        transcript_root,
        "session-a.jsonl",
        # Case-different, same content -- must still be recognized as
        # curated-covered (case/whitespace-insensitive dedup).
        [_assistant_line(text_blocks=["We decided to use sqlite for the local cache"])],
    )

    proposal = scan_transcripts(transcript_root, memory_root)

    assert proposal.candidates == ()


def test_curated_dedup_does_not_suppress_unrelated_content(transcript_root: Path, memory_root: Path) -> None:
    _write_curated(memory_root, "project", "sqlite-cache", "We decided to use SQLite for the local cache.")
    _write_jsonl(
        transcript_root,
        "session-a.jsonl",
        [_assistant_line(text_blocks=["We chose to deprecate the legacy webhook retry queue entirely."])],
    )

    proposal = scan_transcripts(transcript_root, memory_root)

    assert len(proposal.candidates) == 1
    assert "webhook retry queue" in proposal.candidates[0].text


# --- I/O Matrix row 3: non-text blocks are never mined ----------------------


def test_thinking_and_tool_blocks_are_never_mined(transcript_root: Path, memory_root: Path) -> None:
    _write_jsonl(
        transcript_root,
        "session-a.jsonl",
        [
            _assistant_line(thinking="We decided to use SQLite for the local cache."),
            _assistant_line(tool_use=True, tool_result=True),
        ],
    )

    proposal = scan_transcripts(transcript_root, memory_root)

    assert proposal.candidates == ()


def test_non_assistant_entries_are_never_mined(transcript_root: Path, memory_root: Path) -> None:
    _write_jsonl(
        transcript_root,
        "session-a.jsonl",
        [_user_line("We decided to use SQLite for the local cache.")],
    )

    proposal = scan_transcripts(transcript_root, memory_root)

    assert proposal.candidates == ()


# --- I/O Matrix row 4: malformed transcript line ----------------------------


def test_malformed_json_line_is_skipped_scanning_continues(transcript_root: Path, memory_root: Path) -> None:
    _write_jsonl(
        transcript_root,
        "session-a.jsonl",
        [
            "{not valid json",
            _assistant_line(text_blocks=["We decided to use SQLite for the local cache."]),
        ],
    )

    proposal = scan_transcripts(transcript_root, memory_root)

    assert len(proposal.candidates) == 1
    assert proposal.candidates[0].line_number == 2


def test_blank_lines_are_skipped(transcript_root: Path, memory_root: Path) -> None:
    _write_jsonl(
        transcript_root,
        "session-a.jsonl",
        [
            "",
            "   ",
            _assistant_line(text_blocks=["We decided to use SQLite for the local cache."]),
        ],
    )

    proposal = scan_transcripts(transcript_root, memory_root)

    assert len(proposal.candidates) == 1
    assert proposal.candidates[0].line_number == 3


# --- I/O Matrix row 5: missing transcript root ------------------------------


def test_missing_transcript_root_raises_value_error_naming_source(memory_root: Path, tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    with pytest.raises(ValueError, match="--source"):
        scan_transcripts(missing, memory_root)


# --- Full-text vs. truncated snippet ----------------------------------------


def test_candidate_at_or_beyond_truncation_boundary_keeps_full_text(transcript_root: Path, memory_root: Path) -> None:
    long_sentence = (
        "We decided to migrate the entire ingestion pipeline from the legacy REST "
        "polling architecture to a fully event-driven Kafka-based system after "
        "benchmarking showed a forty percent reduction in end-to-end latency "
        "during peak load testing."
    )
    assert len(long_sentence) > 120
    _write_jsonl(transcript_root, "session-a.jsonl", [_assistant_line(text_blocks=[long_sentence])])

    proposal = scan_transcripts(transcript_root, memory_root)

    assert len(proposal.candidates) == 1
    candidate = proposal.candidates[0]
    assert candidate.text == long_sentence
    assert len(candidate.snippet) <= 120
    assert candidate.snippet != candidate.text
    assert candidate.snippet.endswith("…")


# --- Per-file fault tolerance ------------------------------------------------


def test_file_level_read_failure_does_not_abort_other_files(
    transcript_root: Path, memory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad_path = _write_jsonl(
        transcript_root,
        "aaa-bad.jsonl",
        [_assistant_line(text_blocks=["We decided to use SQLite for the local cache."])],
    )
    _write_jsonl(
        transcript_root,
        "bbb-good.jsonl",
        [_assistant_line(text_blocks=["We chose to deprecate the legacy webhook retry queue entirely."])],
    )

    real_read_text = Path.read_text

    def _flaky_read_text(self: Path, *args, **kwargs):
        if self == bad_path:
            raise OSError("simulated unreadable file")
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _flaky_read_text)

    proposal = scan_transcripts(transcript_root, memory_root)

    assert len(proposal.candidates) == 1
    assert "webhook retry queue" in proposal.candidates[0].text


def test_non_utf8_transcript_file_is_skipped_not_fatal(transcript_root: Path, memory_root: Path) -> None:
    bad_path = transcript_root / "aaa-bad.jsonl"
    bad_path.write_bytes(b"\xff\xfe\x00garbage-not-utf8")
    _write_jsonl(
        transcript_root,
        "bbb-good.jsonl",
        [_assistant_line(text_blocks=["We chose to deprecate the legacy webhook retry queue entirely."])],
    )

    proposal = scan_transcripts(transcript_root, memory_root)

    assert len(proposal.candidates) == 1
    assert "webhook retry queue" in proposal.candidates[0].text


# --- Intra-scan dedup --------------------------------------------------------


def test_repeated_sentence_within_one_file_yields_one_candidate(transcript_root: Path, memory_root: Path) -> None:
    _write_jsonl(
        transcript_root,
        "session-a.jsonl",
        [
            _assistant_line(text_blocks=["We decided to use SQLite for the local cache."]),
            _assistant_line(text_blocks=["We decided to use SQLite for the local cache."]),
        ],
    )

    proposal = scan_transcripts(transcript_root, memory_root)

    assert len(proposal.candidates) == 1


def test_repeated_sentence_across_two_files_yields_one_candidate(transcript_root: Path, memory_root: Path) -> None:
    _write_jsonl(
        transcript_root,
        "session-a.jsonl",
        [_assistant_line(text_blocks=["We decided to use SQLite for the local cache."])],
    )
    _write_jsonl(
        transcript_root,
        "session-b.jsonl",
        [_assistant_line(text_blocks=["We decided to use SQLite for the local cache."])],
    )

    proposal = scan_transcripts(transcript_root, memory_root)

    assert len(proposal.candidates) == 1


# --- Multi-file sorted scan order -------------------------------------------


def test_multi_file_scan_is_in_sorted_filename_order(transcript_root: Path, memory_root: Path) -> None:
    _write_jsonl(
        transcript_root,
        "zzz-second.jsonl",
        [_assistant_line(text_blocks=["We chose to deprecate the legacy webhook retry queue entirely."])],
    )
    _write_jsonl(
        transcript_root,
        "aaa-first.jsonl",
        [_assistant_line(text_blocks=["Settled on keeping the build script single-threaded for now."])],
    )

    proposal = scan_transcripts(transcript_root, memory_root)

    assert len(proposal.candidates) == 2
    assert proposal.candidates[0].source_file.name == "aaa-first.jsonl"
    assert proposal.candidates[1].source_file.name == "zzz-second.jsonl"


# --- Story 3.3: bounded scan (caps / timeout / cache) ------------------------


def _set_mtime(path: Path, mtime_s: int) -> None:
    os.utime(path, ns=(mtime_s * 1_000_000_000, mtime_s * 1_000_000_000))


def test_file_count_cap_prefers_newest_files_and_warns(transcript_root: Path, memory_root: Path) -> None:
    oldest = _write_jsonl(
        transcript_root,
        "aaa-oldest.jsonl",
        [_assistant_line(text_blocks=["We decided to archive the oldest ingestion job."])],
    )
    middle = _write_jsonl(
        transcript_root,
        "bbb-middle.jsonl",
        [_assistant_line(text_blocks=["We chose to deprecate the legacy webhook retry queue entirely."])],
    )
    newest = _write_jsonl(
        transcript_root,
        "ccc-newest.jsonl",
        [_assistant_line(text_blocks=["Settled on keeping the build script single-threaded for now."])],
    )
    _set_mtime(oldest, 1_000)
    _set_mtime(middle, 2_000)
    _set_mtime(newest, 3_000)

    proposal = scan_transcripts(transcript_root, memory_root, max_files=2)

    # Newest-first allocation: the OLDEST file loses the budget, not the
    # lexicographically last one.
    assert {c.source_file.name for c in proposal.candidates} == {
        "bbb-middle.jsonl",
        "ccc-newest.jsonl",
    }
    assert len(proposal.warnings) == 1
    assert "capped" in proposal.warnings[0]
    assert "skipped 1 of 3" in proposal.warnings[0]
    assert "max_files=2" in proposal.warnings[0]


def test_byte_budget_skips_files_beyond_it_newest_first(transcript_root: Path, memory_root: Path) -> None:
    older = _write_jsonl(
        transcript_root,
        "aaa-older.jsonl",
        [_assistant_line(text_blocks=["We decided to archive the oldest ingestion job."])],
    )
    newer = _write_jsonl(
        transcript_root,
        "bbb-newer.jsonl",
        [_assistant_line(text_blocks=["Settled on keeping the build script single-threaded for now."])],
    )
    _set_mtime(older, 1_000)
    _set_mtime(newer, 2_000)
    # A budget exactly covering the newest file: the newer file fits, the
    # older one no longer does.
    budget = newer.stat().st_size

    proposal = scan_transcripts(transcript_root, memory_root, max_total_bytes=budget)

    assert {c.source_file.name for c in proposal.candidates} == {"bbb-newer.jsonl"}
    assert len(proposal.warnings) == 1
    assert "capped" in proposal.warnings[0]
    assert f"max_total_bytes={budget}" in proposal.warnings[0]


def test_per_file_timeout_keeps_partial_results_with_warning(transcript_root: Path, memory_root: Path) -> None:
    _write_jsonl(
        transcript_root,
        "session-a.jsonl",
        [_assistant_line(text_blocks=["We decided to use SQLite for the local cache."])],
    )

    # A zero budget fires the deadline at the first line -- zero candidates,
    # one warning, no exception (the never-abort posture of every bound).
    proposal = scan_transcripts(transcript_root, memory_root, per_file_timeout_s=0.0)

    assert proposal.candidates == ()
    assert len(proposal.warnings) == 1
    assert "timed out" in proposal.warnings[0]
    assert "session-a.jsonl" in proposal.warnings[0]


def test_cache_hit_avoids_rereading_unchanged_files(
    transcript_root: Path, memory_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _write_jsonl(
        transcript_root,
        "session-a.jsonl",
        [_assistant_line(text_blocks=["We decided to use SQLite for the local cache."])],
    )
    cache_path = tmp_path / "scan-cache.json"

    first = scan_transcripts(transcript_root, memory_root, cache_path=cache_path)
    assert len(first.candidates) == 1
    assert cache_path.is_file()

    real_read_text = Path.read_text

    def _no_reread(self: Path, *args, **kwargs):
        if self == target:
            raise AssertionError("cached, unchanged transcript must not be re-read")
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _no_reread)

    second = scan_transcripts(transcript_root, memory_root, cache_path=cache_path)

    # Byte-equivalent with or without the cache hit -- the proposal is the
    # same object graph, warnings included.
    assert second.candidates == first.candidates
    assert second.warnings == ()


def test_cache_is_invalidated_when_the_file_changes(transcript_root: Path, memory_root: Path, tmp_path: Path) -> None:
    path = _write_jsonl(
        transcript_root,
        "session-a.jsonl",
        [_assistant_line(text_blocks=["We decided to use SQLite for the local cache."])],
    )
    _set_mtime(path, 1_000)
    cache_path = tmp_path / "scan-cache.json"
    scan_transcripts(transcript_root, memory_root, cache_path=cache_path)

    _write_jsonl(
        transcript_root,
        "session-a.jsonl",
        [_assistant_line(text_blocks=["We chose to deprecate the legacy webhook retry queue entirely."])],
    )
    _set_mtime(path, 2_000)

    proposal = scan_transcripts(transcript_root, memory_root, cache_path=cache_path)

    assert len(proposal.candidates) == 1
    assert "webhook retry queue" in proposal.candidates[0].text


def test_cached_matches_still_dedup_against_newly_curated_memory(
    transcript_root: Path, memory_root: Path, tmp_path: Path
) -> None:
    """Pins the load-bearing cache design point: the cache stores raw
    PRE-dedup matches, and the curated-overlap check re-runs on every scan
    -- so capturing a candidate between two cached scans silences it, and
    re-running stays idempotent exactly as Story 3.1 promised."""
    _write_jsonl(
        transcript_root,
        "session-a.jsonl",
        [_assistant_line(text_blocks=["We decided to use SQLite for the local cache."])],
    )
    cache_path = tmp_path / "scan-cache.json"
    first = scan_transcripts(transcript_root, memory_root, cache_path=cache_path)
    assert len(first.candidates) == 1

    _write_curated(memory_root, "project", "sqlite-cache", "We decided to use SQLite for the local cache.")

    second = scan_transcripts(transcript_root, memory_root, cache_path=cache_path)

    assert second.candidates == ()


def test_malformed_cache_is_ignored_and_replaced(transcript_root: Path, memory_root: Path, tmp_path: Path) -> None:
    _write_jsonl(
        transcript_root,
        "session-a.jsonl",
        [_assistant_line(text_blocks=["We decided to use SQLite for the local cache."])],
    )
    cache_path = tmp_path / "scan-cache.json"
    cache_path.write_text("{not valid json", encoding="utf-8")

    proposal = scan_transcripts(transcript_root, memory_root, cache_path=cache_path)

    assert len(proposal.candidates) == 1
    replaced = json.loads(cache_path.read_text(encoding="utf-8"))
    assert replaced["version"] == 1
    assert len(replaced["files"]) == 1


# --- default_transcript_root() ----------------------------------------------


def test_default_transcript_root_encodes_non_alnum_chars_without_memory_suffix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()
    project_dir = tmp_path / "work" / ".bmad-loop" / "my-repo"
    project_dir.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.chdir(project_dir)

    result = default_transcript_root()

    expected_encoded = re.sub(r"[^A-Za-z0-9]", "-", str(Path.cwd()))
    assert result == fake_home / ".claude" / "projects" / expected_encoded
    # The one point of divergence from its sibling default_user_local_root():
    # no "/memory" suffix -- *.jsonl transcripts live directly in this dir.
    assert result.name != "memory"
    # The '/' immediately before the dotted ".bmad-loop" segment doubles up
    # with the '.' itself -- both become '-', landing as "--bmad-loop-".
    assert "--bmad-loop-" in expected_encoded
