"""Unit tests for pyforge.scribe.compile -- the nightly projection builder
(Story 2.2/2.3).

Every test builds a throwaway `tmp_path` repo/memory tree -- never the real
repo's `.claude/memory/`/`.git` state.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from pyforge.scribe import compile as compile_module
from pyforge.scribe.capture import _DESCRIPTION_MAX_LEN, _truncate, capture
from pyforge.scribe.compile import compile_graph
from pyforge.scribe.extras import graphify as graphify_module
from pyforge.scribe.graph_store import FlatFileGraphStore

_MEMORY_MD_STARTER = """# Team Memory Index

## Feedback

## Project

## Reference
"""


@pytest.fixture()
def memory_root(tmp_path: Path) -> Path:
    root = tmp_path / ".claude" / "memory"
    root.mkdir(parents=True)
    (root / "MEMORY.md").write_text(_MEMORY_MD_STARTER, encoding="utf-8")
    return root


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(repo_root), check=True, capture_output=True, text=True)


def _init_git_repo_with_commits(repo_root: Path, count: int = 2) -> None:
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "Test")
    for i in range(count):
        (repo_root / f"file{i}.txt").write_text(f"content {i}\n", encoding="utf-8")
        _git(repo_root, "add", "-A")
        _git(repo_root, "commit", "-q", "-m", f"commit {i}")


def _assistant_transcript_line(text: str, *, timestamp: str | None = "2026-08-20T12:00:00.000Z") -> str:
    """`timestamp=None` omits the field entirely -- exercises
    `transcripts.py`'s own `"unknown time"` sentinel for an untimestamped
    entry, which in turn exercises `compile.py`'s mtime-fallback branch."""
    entry: dict = {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": text}]},
    }
    if timestamp is not None:
        entry["timestamp"] = timestamp
    return json.dumps(entry)


def _assistant_transcript_line_with_numeric_timestamp(text: str, timestamp: int) -> str:
    """A transcript entry whose `"timestamp"` field is a raw JSON number
    (e.g. epoch millis) rather than an ISO-8601 string -- `transcripts.py`'s
    `entry.get("timestamp") or "unknown time"` passes a truthy int straight
    through as `candidate.timestamp`, so `datetime.fromisoformat()` sees a
    non-string argument and raises `TypeError`, not `ValueError`."""
    entry: dict = {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": text}]},
        "timestamp": timestamp,
    }
    return json.dumps(entry)


def _write_transcript_jsonl(transcript_root: Path, filename: str, lines: list[str]) -> Path:
    transcript_root.mkdir(parents=True, exist_ok=True)
    path = transcript_root / filename
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_missing_memory_root_raises_before_any_write(tmp_path: Path) -> None:
    store = FlatFileGraphStore(tmp_path / "graph.json")
    with pytest.raises(ValueError, match="does not exist"):
        compile_graph(
            memory_root=tmp_path / "nope",
            repo_root=tmp_path,
            store=store,
            transcript_root=tmp_path / "no-transcripts",
        )
    assert not (tmp_path / "graph.json").exists()


def test_happy_path_produces_traceable_nodes(tmp_path: Path, memory_root: Path) -> None:
    capture(memory_root, "feedback", "Always run tests first.")
    (tmp_path / ".memlog.md").write_text("session log entry\n", encoding="utf-8")
    _init_git_repo_with_commits(tmp_path, count=2)

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    assert result.node_count >= 1 + 1 + 2  # memory + memlog + 2 commits
    nodes = {n.id: n for n in store.iter_nodes()}
    memory_ids = [nid for nid in nodes if nid.startswith("memory:feedback/")]
    assert len(memory_ids) == 1
    memlog_ids = [nid for nid in nodes if nid.startswith("memlog:")]
    assert memlog_ids == ["memlog:.memlog.md"]
    commit_ids = [nid for nid in nodes if nid.startswith("commit:")]
    assert len(commit_ids) == 2

    # Every node's citation resolves to a real file/commit (AD-8 spirit).
    for node in nodes.values():
        if node.citation.startswith("commit:"):
            sha = node.citation.removeprefix("commit:")
            _git(tmp_path, "cat-file", "-e", sha)  # raises if unresolvable
        else:
            assert (tmp_path / node.citation).is_file()


def test_rerun_with_no_source_activity_is_byte_identical(tmp_path: Path, memory_root: Path) -> None:
    capture(memory_root, "feedback", "Always run tests first.")
    (tmp_path / ".memlog.md").write_text("session log entry\n", encoding="utf-8")
    _init_git_repo_with_commits(tmp_path, count=2)
    store_path = tmp_path / "graph.json"
    no_transcripts = tmp_path / "no-transcripts"

    pinned = datetime(2026, 1, 2, tzinfo=timezone.utc)
    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=FlatFileGraphStore(store_path),
        transcript_root=no_transcripts,
        compiled_at=pinned,
    )
    first_bytes = store_path.read_bytes()

    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=FlatFileGraphStore(store_path),
        transcript_root=no_transcripts,
        compiled_at=pinned,
    )
    second_bytes = store_path.read_bytes()

    assert first_bytes == second_bytes


def test_no_optional_surfaces_present_still_succeeds(tmp_path: Path, memory_root: Path) -> None:
    capture(memory_root, "feedback", "Only memory content, nothing else.")

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    assert result.node_count == 1
    # Pin each optional surface's warning count exactly, rather than the
    # weaker `all("git" in w or "transcript" in w)` shape: that predicate
    # holds for essentially any warning either surface could emit, so it
    # would stay green through a real regression in one of them.
    assert len([w for w in result.warnings if "transcript" in w]) == 1
    assert all(("git" in w or "transcript" in w) for w in result.warnings)


def test_git_absent_logs_warning_and_does_not_abort(
    tmp_path: Path, memory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    capture(memory_root, "feedback", "content")
    monkeypatch.setattr("shutil.which", lambda name: None)

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    assert result.node_count == 1
    assert any("git" in w.lower() for w in result.warnings)


def test_malformed_memory_entry_is_skipped_with_warning_not_aborted(tmp_path: Path, memory_root: Path) -> None:
    capture(memory_root, "feedback", "a good entry")
    (memory_root / "feedback" / "broken.md").write_text("not frontmatter at all\n", encoding="utf-8")

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    assert result.node_count == 1  # only the good entry
    assert any("broken.md" in w for w in result.warnings)


def test_non_utf8_commit_message_is_replaced_not_a_crash(tmp_path: Path, memory_root: Path) -> None:
    """Review finding: `text=True` with no `encoding=`/`errors=` decodes
    `git log`'s output with the locale's preferred encoding and
    `errors="strict"` -- a commit authored with non-UTF-8 content used to
    raise an uncaught `UnicodeDecodeError` (a `ValueError` subclass NOT
    caught by the surrounding `except (OSError, subprocess.TimeoutExpired)`),
    crashing the whole compile instead of degrading like every other
    surface."""
    capture(memory_root, "feedback", "content")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "file.txt").write_text("content\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    subprocess.run(
        ["git", "commit", "-q", "-m", "commit \xff\xfe not valid utf-8".encode("latin-1")],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )

    store = FlatFileGraphStore(tmp_path / "graph.json")
    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    commit_ids = [n.id for n in store.iter_nodes() if n.id.startswith("commit:")]
    assert len(commit_ids) == 1


def test_memory_file_removed_between_the_two_read_passes_is_skipped_not_a_crash(
    tmp_path: Path, memory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review finding: `.claude/memory/<type>/*.md` is globbed and parsed
    TWICE -- once in `_read_memory_surface`, again in
    `_apply_supersession`. The second pass's `parse_capture_file` call
    only caught `ValueError`, so a file that existed during the first scan
    but was removed before the second (a real race an unattended nightly
    compile can hit) used to raise an uncaught `FileNotFoundError` and
    crash the whole compile."""
    import pyforge.scribe.compile as compile_module
    from pyforge.scribe.models import parse_capture_file as real_parse_capture_file

    capture(memory_root, "feedback", "content")
    call_count = {"n": 0}

    def _flaky_parse(path):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise FileNotFoundError(f"simulated: {path} vanished between scans")
        return real_parse_capture_file(path)

    monkeypatch.setattr(compile_module, "parse_capture_file", _flaky_parse)

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    assert result.node_count == 1
    assert any("supersession" in w for w in result.warnings)


def test_data_named_directory_outside_dot_claude_is_not_excluded(tmp_path: Path, memory_root: Path) -> None:
    """Review finding: `_EXCLUDED_DIR_NAMES` matched the bare name "data"
    ANYWHERE in a path, silently dropping a legitimate CHANGELOG.md/
    .memlog.md/*retro*.md under any directory literally named "data" --
    "data" is only meant to exclude THIS repo's own `.claude/data`."""
    capture(memory_root, "feedback", "content")
    other_data_dir = tmp_path / "src" / "mypackage" / "data"
    other_data_dir.mkdir(parents=True)
    (other_data_dir / "CHANGELOG.md").write_text("# Changes\n\nsomething\n", encoding="utf-8")

    store = FlatFileGraphStore(tmp_path / "graph.json")
    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    doc_ids = [n.id for n in store.iter_nodes() if n.id.startswith("doc:")]
    assert doc_ids == ["doc:src/mypackage/data/CHANGELOG.md"]


def test_compile_never_prompts(tmp_path: Path, memory_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Unattended (FR-11): patch builtins.input to raise if ever called."""
    capture(memory_root, "feedback", "content")

    def _raise_on_input(*args, **kwargs):
        raise AssertionError("compile_graph must never call input()")

    monkeypatch.setattr("builtins.input", _raise_on_input)
    store = FlatFileGraphStore(tmp_path / "graph.json")
    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )  # must not raise


# --- surface: session transcripts (Story 3.2, CAP-2) --------------------------


def test_transcript_surface_happy_path_produces_one_node(tmp_path: Path, memory_root: Path) -> None:
    # Deliberately > 120 chars (the truncation boundary, matching
    # test_transcripts.py's own truncation-boundary fixture) so
    # `candidate.snippet` (title) and `candidate.text` (text) are NOT
    # byte-identical -- a title/text field swap in `_read_transcript_surface`
    # would otherwise pass unnoticed with a short sentence.
    long_sentence = (
        "We decided to migrate the entire ingestion pipeline from the legacy REST "
        "polling architecture to a fully event-driven Kafka-based system after "
        "benchmarking showed a forty percent reduction in end-to-end latency "
        "during peak load testing."
    )
    assert len(long_sentence) > 120
    expected_snippet = _truncate(long_sentence, _DESCRIPTION_MAX_LEN)
    assert expected_snippet != long_sentence  # sanity: truncation actually occurred

    transcript_root = tmp_path / "transcripts"
    _write_transcript_jsonl(
        transcript_root,
        "session-a.jsonl",
        [_assistant_transcript_line(long_sentence)],
    )

    store = FlatFileGraphStore(tmp_path / "graph.json")
    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=transcript_root,
    )

    transcript_nodes = [n for n in store.iter_nodes() if n.kind == "transcript"]
    assert len(transcript_nodes) == 1
    node = transcript_nodes[0]
    assert node.text == long_sentence
    assert node.title == expected_snippet
    assert node.title != node.text
    assert node.citation == "session-a.jsonl:L1"
    assert node.id == "transcript:session-a.jsonl:L1"
    # Pin the PRIMARY `_transcript_valid_from()` branch -- the entry's own
    # ISO-8601 timestamp, not the file's mtime. Without this, killing the
    # `fromisoformat()` branch outright left the whole suite green (review
    # finding): the only two `valid_from` assertions both *expect* the mtime
    # fallback, and the fixture's mtime is "now", so every transcript node
    # could silently be dated by its session file instead of by the moment
    # the decision was stated.
    assert node.valid_from == datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    assert node.valid_from != datetime.fromtimestamp(
        (transcript_root / "session-a.jsonl").stat().st_mtime, tz=timezone.utc
    )


def test_transcript_surface_missing_timestamp_falls_back_to_file_mtime(tmp_path: Path, memory_root: Path) -> None:
    """`transcripts.py` substitutes its own `"unknown time"` sentinel for an
    entry with no `timestamp` field at all; `datetime.fromisoformat()` on
    that sentinel raises `ValueError`, exercising `_transcript_valid_from()`'s
    mtime-fallback branch."""
    transcript_root = tmp_path / "transcripts"
    path = _write_transcript_jsonl(
        transcript_root,
        "session-a.jsonl",
        [_assistant_transcript_line("We decided to use SQLite for the local cache.", timestamp=None)],
    )
    expected_valid_from = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)

    store = FlatFileGraphStore(tmp_path / "graph.json")
    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=transcript_root,
    )

    transcript_nodes = [n for n in store.iter_nodes() if n.kind == "transcript"]
    assert len(transcript_nodes) == 1
    assert transcript_nodes[0].valid_from == expected_valid_from


def test_transcript_surface_non_string_timestamp_falls_back_to_file_mtime_without_raising(
    tmp_path: Path, memory_root: Path
) -> None:
    """Review finding: a transcript entry whose `"timestamp"` is a JSON
    number (e.g. epoch millis) made `datetime.fromisoformat()` raise
    `TypeError` (not `ValueError`), which was uncaught and crashed the whole
    `compile_graph()` run -- contradicting `_transcript_valid_from()`'s own
    docstring promise to degrade rather than abort. Mirrors
    `test_transcript_surface_missing_timestamp_falls_back_to_file_mtime`."""
    transcript_root = tmp_path / "transcripts"
    path = _write_transcript_jsonl(
        transcript_root,
        "session-a.jsonl",
        [
            _assistant_transcript_line_with_numeric_timestamp(
                "We decided to use SQLite for the local cache.", 1755683400000
            )
        ],
    )
    expected_valid_from = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)

    store = FlatFileGraphStore(tmp_path / "graph.json")
    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=transcript_root,
    )  # must not raise

    transcript_nodes = [n for n in store.iter_nodes() if n.kind == "transcript"]
    assert len(transcript_nodes) == 1
    assert transcript_nodes[0].valid_from == expected_valid_from


def test_transcript_surface_curated_covered_content_is_not_double_indexed(tmp_path: Path, memory_root: Path) -> None:
    capture(memory_root, "project", "We decided to use SQLite for the local cache.")
    transcript_root = tmp_path / "transcripts"
    _write_transcript_jsonl(
        transcript_root,
        "session-a.jsonl",
        [_assistant_transcript_line("We decided to use SQLite for the local cache.")],
    )

    store = FlatFileGraphStore(tmp_path / "graph.json")
    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=transcript_root,
    )

    transcript_nodes = [n for n in store.iter_nodes() if n.kind == "transcript"]
    assert transcript_nodes == []
    memory_nodes = [n for n in store.iter_nodes() if n.kind == "memory"]
    assert len(memory_nodes) == 1


def test_transcript_surface_missing_root_warns_and_contributes_zero_nodes(tmp_path: Path, memory_root: Path) -> None:
    capture(memory_root, "feedback", "content")

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "does-not-exist",
    )

    transcript_nodes = [n for n in store.iter_nodes() if n.kind == "transcript"]
    assert transcript_nodes == []
    assert result.node_count == 1  # only the memory entry
    transcript_warnings = [w for w in result.warnings if "transcript" in w]
    assert len(transcript_warnings) == 1


def test_transcript_surface_two_candidates_on_one_line_get_distinct_ids(tmp_path: Path, memory_root: Path) -> None:
    transcript_root = tmp_path / "transcripts"
    _write_transcript_jsonl(
        transcript_root,
        "session-a.jsonl",
        [
            _assistant_transcript_line(
                "We decided to use SQLite for the local cache. "
                "We chose to deprecate the legacy webhook retry queue entirely."
            )
        ],
    )

    store = FlatFileGraphStore(tmp_path / "graph.json")
    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=transcript_root,
    )

    transcript_nodes = [n for n in store.iter_nodes() if n.kind == "transcript"]
    assert len(transcript_nodes) == 2
    ids = {n.id for n in transcript_nodes}
    assert ids == {"transcript:session-a.jsonl:L1", "transcript:session-a.jsonl:L1:1"}
    citations = {n.citation for n in transcript_nodes}
    assert citations == {"session-a.jsonl:L1"}


def test_transcript_surface_idempotent_rerun_is_byte_identical(tmp_path: Path, memory_root: Path) -> None:
    transcript_root = tmp_path / "transcripts"
    _write_transcript_jsonl(
        transcript_root,
        "session-a.jsonl",
        [_assistant_transcript_line("We decided to use SQLite for the local cache.")],
    )
    store_path = tmp_path / "graph.json"

    pinned = datetime(2026, 1, 2, tzinfo=timezone.utc)
    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=FlatFileGraphStore(store_path),
        transcript_root=transcript_root,
        compiled_at=pinned,
    )
    first_bytes = store_path.read_bytes()

    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=FlatFileGraphStore(store_path),
        transcript_root=transcript_root,
        compiled_at=pinned,
    )
    second_bytes = store_path.read_bytes()

    assert first_bytes == second_bytes


def test_transcript_surface_naive_timestamp_is_normalized_to_utc(tmp_path: Path, memory_root: Path) -> None:
    """Review finding: a transcript timestamp with no UTC offset parses to a
    NAIVE datetime, while every other surface's `valid_from` is tz-aware
    UTC. Mixing the two on one graph made any cross-node comparison raise
    `TypeError: can't compare offset-naive and offset-aware datetimes` --
    reproduced directly before the fix."""
    capture(memory_root, "feedback", "Some curated content, for a tz-aware node.")
    transcript_root = tmp_path / "transcripts"
    _write_transcript_jsonl(
        transcript_root,
        "session-a.jsonl",
        [
            _assistant_transcript_line(
                "We decided to use SQLite for the local cache.",
                timestamp="2026-08-20T12:00:00",  # no offset -> naive
            )
        ],
    )

    store = FlatFileGraphStore(tmp_path / "graph.json")
    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=transcript_root,
    )

    nodes = list(store.iter_nodes())
    transcript_nodes = [n for n in nodes if n.kind == "transcript"]
    assert len(transcript_nodes) == 1
    assert transcript_nodes[0].valid_from == datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    assert all(n.valid_from.tzinfo is not None for n in nodes)
    sorted(nodes, key=lambda n: n.valid_from)  # must not raise TypeError


@pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason=(
        "chmod(0o000) does not deny listing to root (DAC is bypassed) and is "
        "inert on Windows, so the unreadable-root condition cannot be staged "
        "-- the surface would contribute a node and this test would red on a "
        "root CI container rather than on a real regression (review finding)"
    ),
)
def test_transcript_surface_unreadable_root_warns_and_contributes_zero_nodes(tmp_path: Path, memory_root: Path) -> None:
    """Review finding: this story's contract says a "missing/UNREADABLE"
    transcript root degrades to a warning and zero nodes, but
    `scan_transcripts()` swallows the `OSError` from its own glob -- so an
    existing-but-unreadable root produced zero nodes AND zero warnings,
    indistinguishable from "nothing decision-shaped was said"."""
    capture(memory_root, "feedback", "content")
    transcript_root = tmp_path / "transcripts"
    _write_transcript_jsonl(
        transcript_root,
        "session-a.jsonl",
        [_assistant_transcript_line("We decided to use SQLite for the local cache.")],
    )
    transcript_root.chmod(0o000)
    try:
        store = FlatFileGraphStore(tmp_path / "graph.json")
        result = compile_graph(
            memory_root=memory_root,
            repo_root=tmp_path,
            store=store,
            transcript_root=transcript_root,
        )
    finally:
        transcript_root.chmod(0o700)

    assert [n for n in store.iter_nodes() if n.kind == "transcript"] == []
    assert result.node_count == 1  # only the memory entry
    transcript_warnings = [w for w in result.warnings if "transcript" in w]
    assert len(transcript_warnings) == 1
    assert "is not readable" in transcript_warnings[0]


def test_transcript_surface_warning_does_not_advertise_a_flag_compile_lacks(tmp_path: Path, memory_root: Path) -> None:
    """Review finding: the warning forwarded `scan_transcripts()`'s own
    `ValueError`, whose text ends "pass --source to point at the correct
    user-local session-transcript directory". `--source` exists on `scribe
    capture --transcripts`, NOT on `scribe graph compile` (which this
    story's contract forbids giving one), so the unattended path told
    operators to reach for a flag that command does not accept."""
    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "does-not-exist",
    )

    transcript_warnings = [w for w in result.warnings if "transcript" in w]
    assert len(transcript_warnings) == 1
    assert "--source" not in transcript_warnings[0]
    # still diagnosable: names the root and why it was unusable
    assert "does-not-exist" in transcript_warnings[0]
    assert "does not exist" in transcript_warnings[0]


def test_transcript_surface_ids_are_keyed_by_file_and_line_not_a_global_index(
    tmp_path: Path, memory_root: Path
) -> None:
    """Review finding: every existing id test used ONE file with ONE line,
    for which a global running index (`enumerate(proposal.candidates)`)
    yields identical ids -- so the documented `(source_file, line_number)`
    keying was unpinned, and that mutation kept the whole suite green. With
    two files, a global index would mint `transcript:session-b.jsonl:L1:1`
    -- a spurious duplicate suffix for a non-duplicate."""
    transcript_root = tmp_path / "transcripts"
    _write_transcript_jsonl(
        transcript_root,
        "session-a.jsonl",
        [_assistant_transcript_line("We decided to use SQLite for the local cache.")],
    )
    _write_transcript_jsonl(
        transcript_root,
        "session-b.jsonl",
        [_assistant_transcript_line("We chose to deprecate the legacy webhook retry queue.")],
    )

    store = FlatFileGraphStore(tmp_path / "graph.json")
    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=transcript_root,
    )

    ids = {n.id for n in store.iter_nodes() if n.kind == "transcript"}
    assert ids == {"transcript:session-a.jsonl:L1", "transcript:session-b.jsonl:L1"}


def test_transcript_surface_citation_carries_the_real_line_number(tmp_path: Path, memory_root: Path) -> None:
    """Review finding: every transcript fixture in this package put its
    decision on line 1 of a one-line file, so the `:L<line>` component of
    the citation and the id was entirely unpinned -- hardcoding
    `f"{name}:L1"` in `compile.py` kept the whole suite green. Production
    transcripts are long multi-turn sessions, and under that mutation every
    decision after the first in a file collapses onto one id and is
    silently overwritten by `upsert_node()` (node loss, not an error), while
    `scribe recall`'s `[source: <file>:L<line>]` provenance points at the
    wrong line and still passes the format-only resolvability check."""
    transcript_root = tmp_path / "transcripts"
    _write_transcript_jsonl(
        transcript_root,
        "session-a.jsonl",
        [
            _assistant_transcript_line("Here is a summary of the current state."),
            _assistant_transcript_line("Let me look at the failing test first."),
            _assistant_transcript_line("We decided to use SQLite for the local cache."),
            _assistant_transcript_line("We chose to deprecate the legacy webhook retry queue."),
        ],
    )

    store = FlatFileGraphStore(tmp_path / "graph.json")
    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=transcript_root,
    )

    transcript_nodes = [n for n in store.iter_nodes() if n.kind == "transcript"]
    # Both decisions survive as distinct nodes, each carrying its OWN line.
    assert {n.citation for n in transcript_nodes} == {
        "session-a.jsonl:L3",
        "session-a.jsonl:L4",
    }
    assert {n.id for n in transcript_nodes} == {
        "transcript:session-a.jsonl:L3",
        "transcript:session-a.jsonl:L4",
    }
    # Two candidates on two DIFFERENT lines are not "repeats" -- neither may
    # pick up the `:N` occurrence suffix reserved for same-line duplicates.
    assert not any(n.id.endswith(":1") for n in transcript_nodes)


def test_transcript_surface_source_file_rotated_before_stat_does_not_abort_compile(
    tmp_path: Path, memory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review finding: `_transcript_valid_from()`'s mtime `stat()` is
    wrapped in `except (OSError, OverflowError)` precisely so a transcript
    pruned or rotated between `scan_transcripts()` returning and the stat
    cannot abort the whole compile -- but nothing exercised it. Narrowing
    that clause to `except ():` kept the suite green, so the never-abort
    contract for the transcript surface could be regressed back to the crash
    an earlier pass patched."""
    transcript_root = tmp_path / "transcripts"
    _write_transcript_jsonl(
        transcript_root,
        "session-a.jsonl",
        # No timestamp -> forces the mtime-fallback branch, which is the one
        # that stats the (by then deleted) source file.
        [_assistant_transcript_line("We decided to use SQLite for the local cache.", timestamp=None)],
    )

    real_scan = compile_module.scan_transcripts

    def scan_then_rotate(root: Path, curated_root: Path, **kwargs):
        proposal = real_scan(root, curated_root)
        for candidate in proposal.candidates:
            candidate.source_file.unlink()
        return proposal

    monkeypatch.setattr(compile_module, "scan_transcripts", scan_then_rotate)

    store = FlatFileGraphStore(tmp_path / "graph.json")
    before = datetime.now(timezone.utc)
    result = compile_graph(  # must not raise FileNotFoundError
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=transcript_root,
    )

    transcript_nodes = [n for n in store.iter_nodes() if n.kind == "transcript"]
    assert len(transcript_nodes) == 1
    assert result.node_count == 1
    # Dated by the final `datetime.now(timezone.utc)` fallback, still tz-aware.
    assert transcript_nodes[0].valid_from.tzinfo is not None
    assert before <= transcript_nodes[0].valid_from <= datetime.now(timezone.utc)


def test_transcript_surface_scanned_candidates_survive_a_root_pruned_mid_compile(
    tmp_path: Path, memory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review finding: the unreadable-root probe ran unconditionally AFTER
    `scan_transcripts()`, so a root removed in between (the same
    rotate-mid-compile race the mtime fallback guards) made
    `iterdir()` raise, threw away candidates that had already been read
    successfully, and reported them as "does not exist -- expected when this
    machine has no session transcripts". Candidates are proof the root was
    listable, so the probe now runs only when the scan came back empty."""
    transcript_root = tmp_path / "transcripts"
    _write_transcript_jsonl(
        transcript_root,
        "session-a.jsonl",
        [_assistant_transcript_line("We decided to use SQLite for the local cache.")],
    )

    real_scan = compile_module.scan_transcripts

    def scan_then_prune(root: Path, curated_root: Path, **kwargs):
        proposal = real_scan(root, curated_root)
        shutil.rmtree(root)
        return proposal

    monkeypatch.setattr(compile_module, "scan_transcripts", scan_then_prune)

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=transcript_root,
    )

    transcript_nodes = [n for n in store.iter_nodes() if n.kind == "transcript"]
    assert len(transcript_nodes) == 1
    assert transcript_nodes[0].citation == "session-a.jsonl:L1"
    # ...and no warning claiming the surface was unavailable, because it wasn't.
    assert [w for w in result.warnings if "transcript" in w] == []


def test_worktree_homes_are_not_compile_surfaces(tmp_path: Path, memory_root: Path) -> None:
    """Story 3.3 review finding: the dot-prefixed worktree homes
    (`.worktrees/`, and `worktrees/` under `.cursor`/`.claude`) hold full
    duplicate checkouts -- indexing them mints duplicate doc/memlog nodes
    citing throwaway trees, and traversing them is most of what made the
    live nightly compile non-terminating."""
    capture(memory_root, "feedback", "content")
    dot_worktree = tmp_path / ".worktrees" / "story-x"
    dot_worktree.mkdir(parents=True)
    (dot_worktree / "CHANGELOG.md").write_text("# Changes\n\nduplicate checkout\n", encoding="utf-8")
    nested_worktree = tmp_path / ".cursor" / "worktrees" / "story-y"
    nested_worktree.mkdir(parents=True)
    (nested_worktree / ".memlog.md").write_text("duplicate memlog\n", encoding="utf-8")
    # A real one at the repo root still compiles.
    (tmp_path / "CHANGELOG.md").write_text("# Changes\n\nreal\n", encoding="utf-8")

    store = FlatFileGraphStore(tmp_path / "graph.json")
    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    doc_ids = [n.id for n in store.iter_nodes() if n.id.startswith(("doc:", "memlog:"))]
    assert doc_ids == ["doc:CHANGELOG.md"]


# --- Story 3.3: overlap lock + bounded-scan cache -----------------------------


def test_second_compile_against_a_locked_store_is_refused_not_queued(tmp_path: Path, memory_root: Path) -> None:
    """An overlapping compile is pure waste (each run is a full rebuild of
    the same derived store), so the lock skips rather than waits -- unlike
    `capture.py::_locked`, which polls because two captures are both meant
    to land."""
    capture(memory_root, "feedback", "content")
    store_path = tmp_path / "graph.json"

    with compile_module._compile_lock(store_path):
        with pytest.raises(compile_module.CompileInProgressError, match="already holds the lock"):
            compile_graph(
                memory_root=memory_root,
                repo_root=tmp_path,
                store=FlatFileGraphStore(store_path),
                transcript_root=tmp_path / "no-transcripts",
            )
        # Refused BEFORE any store mutation -- nothing was reset or written.
        assert not store_path.exists()

    # Lock released with its holder -- the next compile proceeds normally.
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=FlatFileGraphStore(store_path),
        transcript_root=tmp_path / "no-transcripts",
    )
    assert result.node_count == 1
    assert store_path.is_file()


def test_compile_writes_the_transcript_scan_cache_beside_the_store(tmp_path: Path, memory_root: Path) -> None:
    """Story 3.3's mtime-incremental pass: `compile_graph()` points the
    scanner's cache at the graph store's own directory (gitignored,
    derived-artifact home), so an unattended nightly re-run over an
    unchanged transcript surface is cheap."""
    transcript_root = tmp_path / "transcripts"
    _write_transcript_jsonl(
        transcript_root,
        "session-a.jsonl",
        [_assistant_transcript_line("We decided to use SQLite for the local cache.")],
    )
    store_path = tmp_path / "graph.json"

    pinned = datetime(2026, 1, 2, tzinfo=timezone.utc)
    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=FlatFileGraphStore(store_path),
        transcript_root=transcript_root,
        compiled_at=pinned,
    )

    cache_path = tmp_path / "transcript-scan-cache.json"
    assert cache_path.is_file()
    cached = json.loads(cache_path.read_text(encoding="utf-8"))
    assert cached["version"] == 1
    assert str(transcript_root / "session-a.jsonl") in cached["files"]
    # The idempotency contract survives the cache being in play: a second
    # compile (now cache-served) produces byte-identical store output.
    first_bytes = store_path.read_bytes()
    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=FlatFileGraphStore(store_path),
        transcript_root=transcript_root,
        compiled_at=pinned,
    )
    assert store_path.read_bytes() == first_bytes


def test_transcript_surface_root_that_is_a_regular_file_warns_as_not_a_directory(
    tmp_path: Path, memory_root: Path
) -> None:
    """Review finding: `_transcript_unavailable_warning()`'s
    `is not a directory` branch was unexercised -- deleting it outright kept
    the suite green, after which a regular file at `transcript_root` is
    misreported as `is not readable (ValueError)`, sending an operator
    looking at permissions instead of at the path they configured."""
    transcript_root = tmp_path / "transcripts"
    transcript_root.write_text("not a directory\n", encoding="utf-8")

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=transcript_root,
    )

    assert [n for n in store.iter_nodes() if n.kind == "transcript"] == []
    transcript_warnings = [w for w in result.warnings if "transcript" in w]
    assert len(transcript_warnings) == 1
    assert "is not a directory" in transcript_warnings[0]
    assert "is not readable" not in transcript_warnings[0]


# --- Story 6.1: the optional graphify compile_surface extra -----------------


class _FakeGraph:
    def __init__(self, nodes: dict[str, dict]) -> None:
        self._nodes = nodes

    def nodes(self, data: bool = False):
        items = list(self._nodes.items())
        return items if data else [nid for nid, _ in items]

    def number_of_nodes(self) -> int:
        return len(self._nodes)

    def number_of_edges(self) -> int:
        return 0


class _FakeGraphifyModule:
    def __init__(self, nodes: dict[str, dict]) -> None:
        self._nodes = nodes

    def collect_files(self, target, root=None):
        return [Path(target) / "a.py"]

    def extract(self, files, cache_root=None, root=None, parallel=True):
        return {"nodes": [], "edges": [], "hyperedges": []}

    def build_from_json(self, extraction, root=None):
        return _FakeGraph(self._nodes)

    def god_nodes(self, graph, top_n=10):
        return []


def test_graphify_extra_off_by_default_is_a_no_op(
    tmp_path: Path, memory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC1: absent or off (default) -- a compile is identical to today's
    six builtins, and produces zero graphify-related noise."""
    monkeypatch.delenv("SCRIBE_GRAPHIFY_EXTRA", raising=False)
    (tmp_path / "src" / "shared" / "packages").mkdir(parents=True)
    (tmp_path / "src" / "shared" / "packages" / "example.py").write_text("x = 1\n", encoding="utf-8")
    capture(memory_root, "feedback", "content")

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    assert result.node_count == 1
    assert [n for n in store.iter_nodes() if n.kind == "code"] == []
    assert all(("git" in w or "transcript" in w) for w in result.warnings)


def test_graphify_extra_on_writes_code_nodes_through_the_same_store(
    tmp_path: Path, memory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC2: with the extra on, folder ingest writes GraphNodes through the
    SAME `GraphStore` the six builtins already use -- never a parallel
    store."""
    monkeypatch.setenv("SCRIBE_GRAPHIFY_EXTRA", "1")
    (tmp_path / "src" / "shared" / "packages").mkdir(parents=True)
    (tmp_path / "src" / "shared" / "packages" / "example.py").write_text("x = 1\n", encoding="utf-8")
    fake_nodes = {
        "python:example": {
            "label": "example",
            "type": "module",
            "source_file": "src/shared/packages/example.py",
            "source_location": "L1",
        }
    }
    monkeypatch.setattr(graphify_module, "_import_graphify", lambda: _FakeGraphifyModule(fake_nodes))
    capture(memory_root, "feedback", "content")

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    code_nodes = [n for n in store.iter_nodes() if n.kind == "code"]
    assert len(code_nodes) == 1
    assert code_nodes[0].citation == "src/shared/packages/example.py:L1"
    assert result.node_count == 2  # the memory node + the one code node


def test_graphify_extra_on_but_unavailable_degrades_to_warning_not_abort(
    tmp_path: Path, memory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    try:
        import graphify  # noqa: F401
    except ImportError:
        pass
    else:
        pytest.skip("graphifyy is installed in this environment")

    monkeypatch.setenv("SCRIBE_GRAPHIFY_EXTRA", "1")
    (tmp_path / "src" / "shared" / "packages").mkdir(parents=True)
    (tmp_path / "src" / "shared" / "packages" / "example.py").write_text("x = 1\n", encoding="utf-8")
    capture(memory_root, "feedback", "content")

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    assert result.node_count == 1
    assert any("graphify" in w for w in result.warnings)


# --- Story 6.2: cocoindex extra does not hook into compile_graph() ----------


def test_compile_graph_is_unaffected_by_the_cocoindex_extra_env_var(
    tmp_path: Path, memory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC1: `compile_graph()` deliberately does not consult
    `SCRIBE_COCOINDEX_EXTRA` at all (see this module's own docstring for
    why) -- a compile is byte-for-byte identical whether the extra is off
    or on."""
    monkeypatch.setenv("SCRIBE_GRAPHIFY_EXTRA", "1")
    (tmp_path / "src" / "shared" / "packages").mkdir(parents=True)
    (tmp_path / "src" / "shared" / "packages" / "example.py").write_text("x = 1\n", encoding="utf-8")
    fake_nodes = {
        "python:example": {
            "label": "example",
            "source_file": "src/shared/packages/example.py",
            "source_location": "L1",
        }
    }
    monkeypatch.setattr(graphify_module, "_import_graphify", lambda: _FakeGraphifyModule(fake_nodes))
    capture(memory_root, "feedback", "content")

    monkeypatch.delenv("SCRIBE_COCOINDEX_EXTRA", raising=False)
    off_store = FlatFileGraphStore(tmp_path / "graph-off.json")
    off_result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=off_store,
        transcript_root=tmp_path / "no-transcripts",
    )

    monkeypatch.setenv("SCRIBE_COCOINDEX_EXTRA", "1")
    on_store = FlatFileGraphStore(tmp_path / "graph-on.json")
    on_result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=on_store,
        transcript_root=tmp_path / "no-transcripts",
    )

    assert off_result.node_count == on_result.node_count == 2
    assert [n.id for n in off_store.iter_nodes()] == [n.id for n in on_store.iter_nodes()]
    index_path = tmp_path / ".claude" / "data" / "pyforge-scribe" / "cocoindex-index.json"
    assert not index_path.exists()


def test_compile_module_does_not_import_the_cocoindex_extra() -> None:
    """The cocoindex incremental extra lives entirely in `cli.py`'s `index
    refresh` verb (see this module's own docstring) -- `compile.py` has no
    import of it at all."""
    import ast

    tree = ast.parse(compile_module.__file__ and Path(compile_module.__file__).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert "cocoindex_flow" not in node.module


# --- Story 6.3: the graph-node staleness flag (CAP-13) -----------------------


def _init_git_and_commit_everything(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "commit touching the current tree")


def test_stale_flag_set_when_source_commit_postdates_compile_clock(tmp_path: Path, memory_root: Path) -> None:
    """AC1 / Story 8.4: stale when the source commit is authored after
    this compile's `compiled_at` — not when working-tree mtime is old."""
    capture(memory_root, "project", "Original plan.", slug="plan-x")
    _init_git_and_commit_everything(tmp_path)

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
        compiled_at=datetime(2019, 1, 1, tzinfo=timezone.utc),
    )

    node = next(n for n in store.iter_nodes() if n.id == "memory:project/plan-x")
    assert node.stale is True
    assert result.stale_count == 1


def test_stale_flag_not_set_when_source_has_no_git_history(tmp_path: Path, memory_root: Path) -> None:
    """AC2 ("unchanged source"): a source with no git history at all (never
    committed) has nothing to compare against -- never flagged stale."""
    capture(memory_root, "project", "Original plan.", slug="plan-x")
    # No git repo at all -- `_git_latest_commit_time` degrades to None.

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    node = next(n for n in store.iter_nodes() if n.id == "memory:project/plan-x")
    assert node.stale is False
    assert result.stale_count == 0


def test_stale_flag_not_set_when_valid_from_postdates_the_commit(tmp_path: Path, memory_root: Path) -> None:
    """AC2 ("unchanged source"): a source WITH git history, but whose
    `valid_from` is already at or after that history's latest commit (the
    ordinary post-checkout steady state -- nothing has moved since), is
    never flagged stale."""
    result_capture = capture(memory_root, "project", "Original plan.", slug="plan-x")
    _init_git_and_commit_everything(tmp_path)
    future_mtime = (datetime.now(timezone.utc) + timedelta(days=1)).timestamp()
    os.utime(result_capture.path, (future_mtime, future_mtime))

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    node = next(n for n in store.iter_nodes() if n.id == "memory:project/plan-x")
    assert node.stale is False
    assert result.stale_count == 0


def test_superseded_node_is_never_flagged_stale_even_with_a_newer_commit(tmp_path: Path, memory_root: Path) -> None:
    """AC2 (second clause): a node with a declared `supersedes:` edge
    pointing at it is never flagged stale, regardless of git timestamps --
    Story 2.3's supersession already took it out of `is_current`."""
    old = capture(memory_root, "project", "Original plan.", slug="plan-x")
    new = capture(memory_root, "project", "Revised plan.", slug="plan-y", supersedes="project/plan-x")
    old_mtime = datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp()
    os.utime(old.path, (old_mtime, old_mtime))
    future_mtime = (datetime.now(timezone.utc) + timedelta(days=1)).timestamp()
    os.utime(new.path, (future_mtime, future_mtime))

    _init_git_and_commit_everything(tmp_path)  # postdates plan-x's 2020 mtime

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    nodes = {n.id: n for n in store.iter_nodes()}
    assert nodes["memory:project/plan-x"].is_current is False
    assert nodes["memory:project/plan-x"].stale is False
    assert nodes["memory:project/plan-y"].stale is False
    assert result.stale_count == 0


def test_full_rebuild_does_not_flag_stale_when_mtime_is_older_than_commit(tmp_path: Path, memory_root: Path) -> None:
    """Story 8.4: a just-read file whose mtime predates its last commit is
    still current on this compile — that used to false-positive ~1k nodes."""
    result_capture = capture(memory_root, "project", "Original plan.", slug="plan-x")
    old_mtime = datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp()
    os.utime(result_capture.path, (old_mtime, old_mtime))
    _init_git_and_commit_everything(tmp_path)

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    node = next(n for n in store.iter_nodes() if n.id == "memory:project/plan-x")
    assert node.stale is False
    assert result.stale_count == 0


def test_stale_flag_applies_to_memlog_and_doc_surfaces_too(tmp_path: Path, memory_root: Path) -> None:
    """Design Notes: this is compile.py's general surface, not
    graphify-specific -- a `.memlog.md`/CHANGELOG.md node gets the same
    signal as a memory node."""
    memlog_path = tmp_path / ".memlog.md"
    memlog_path.write_text("session log entry\n", encoding="utf-8")
    _init_git_and_commit_everything(tmp_path)

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
        compiled_at=datetime(2019, 1, 1, tzinfo=timezone.utc),
    )

    node = next(n for n in store.iter_nodes() if n.id == "memlog:.memlog.md")
    assert node.stale is True
    assert result.stale_count == 1


def test_transcript_and_commit_nodes_are_never_staleness_candidates(tmp_path: Path, memory_root: Path) -> None:
    """`commit:`/`transcript:` citations have no git-trackable source-file
    counterpart (mirrors `recall.py::_citation_is_resolvable`'s own split)
    -- neither kind is ever a staleness candidate, however old its
    `valid_from`."""
    transcript_root = tmp_path / "transcripts"
    _write_transcript_jsonl(
        transcript_root,
        "session-a.jsonl",
        [_assistant_transcript_line("We decided to use SQLite for the local cache.")],
    )
    _init_git_and_commit_everything(tmp_path)  # produces at least one commit node

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=transcript_root,
    )

    non_memory_nodes = [n for n in store.iter_nodes() if n.kind in ("commit", "transcript")]
    assert non_memory_nodes  # sanity: both kinds are present in this fixture
    assert all(n.stale is False for n in non_memory_nodes)
    assert result.stale_count == 0


def test_staleness_check_makes_zero_network_calls(
    tmp_path: Path, memory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC4: the staleness check is a git-timestamp comparison only -- no
    LLM call, and by extension no network call at all (AD-6)."""
    capture(memory_root, "project", "Original plan.", slug="plan-x")
    _init_git_and_commit_everything(tmp_path)

    def _blocked_socket(*args, **kwargs):
        raise AssertionError("network socket construction attempted -- AD-6 violation")

    monkeypatch.setattr(socket, "socket", _blocked_socket)

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(  # must not raise
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
        compiled_at=datetime(2019, 1, 1, tzinfo=timezone.utc),
    )

    assert result.stale_count == 1  # the check still ran and found the expected result


def test_git_absent_staleness_check_degrades_to_warning_not_abort(
    tmp_path: Path, memory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    capture(memory_root, "project", "Original plan.", slug="plan-x")
    monkeypatch.setattr("shutil.which", lambda name: None)

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    assert result.stale_count == 0
    assert any("staleness" in w.lower() for w in result.warnings)


def test_facts_ledger_becomes_one_doc_node(tmp_path: Path, memory_root: Path) -> None:
    capture(memory_root, "feedback", "content")
    ledger = tmp_path / "presentations" / "pyforge-scribe" / "facts.yaml"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        '# GENERATED\ndeck: pyforge-scribe\nfacts:\n  - id: n\n    value: "1"\n',
        encoding="utf-8",
    )
    (tmp_path / "presentations" / "pyforge-scribe" / "project").mkdir()
    (tmp_path / "presentations" / "pyforge-scribe" / "project" / "deck.dc.html").write_text(
        "<html></html>\n", encoding="utf-8"
    )
    (tmp_path / "presentations" / "pyforge-scribe" / "src" / "deck").mkdir(parents=True)
    (tmp_path / "presentations" / "pyforge-scribe" / "src" / "deck" / "engine.js").write_text(
        "export {}\n", encoding="utf-8"
    )
    (tmp_path / "facts.yaml").write_text("deck: ignored-root\n", encoding="utf-8")
    nested = tmp_path / "presentations" / "pyforge-scribe" / "nested" / "facts.yaml"
    nested.parent.mkdir(parents=True)
    nested.write_text("deck: ignored-nested\n", encoding="utf-8")

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    fact_nodes = [n for n in store.iter_nodes() if n.citation.endswith("facts.yaml")]
    assert [n.citation for n in fact_nodes] == ["presentations/pyforge-scribe/facts.yaml"]
    assert fact_nodes[0].kind == "doc"
    assert fact_nodes[0].id == "doc:presentations/pyforge-scribe/facts.yaml"
    assert fact_nodes[0].title == "facts:pyforge-scribe"
    assert 'value: "1"' in fact_nodes[0].text
    assert not any("facts.yaml" in w or "fact ledger" in w.lower() for w in result.warnings)


def test_missing_presentations_dir_adds_no_facts_nodes_or_warning(tmp_path: Path, memory_root: Path) -> None:
    capture(memory_root, "feedback", "content")
    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    assert not any(n.citation.endswith("facts.yaml") for n in store.iter_nodes())
    assert not any("facts.yaml" in w or "fact ledger" in w.lower() for w in result.warnings)


def test_compile_hygiene_skips_archive_tests_impl_and_retro_filename_glob(tmp_path: Path, memory_root: Path) -> None:
    capture(memory_root, "feedback", "content")
    (tmp_path / "archive" / "old").mkdir(parents=True)
    (tmp_path / "archive" / "old" / ".memlog.md").write_text("archived\n", encoding="utf-8")
    (tmp_path / "pkg" / "tests").mkdir(parents=True)
    (tmp_path / "pkg" / "tests" / ".memlog.md").write_text("fixture\n", encoding="utf-8")
    impl = tmp_path / "_bmad-output" / "projects" / "demo" / "implementation-artifacts"
    impl.mkdir(parents=True)
    (impl / "epic-1-retro-2026-01-01.md").write_text("impl retro\n", encoding="utf-8")
    specs = tmp_path / "_bmad-output" / "projects" / "demo" / "planning-artifacts" / "specs"
    specs.mkdir(parents=True)
    (specs / "spec-12-1-landed-retros-are-mirrored.md").write_text("story spec about retros\n", encoding="utf-8")
    retros = tmp_path / "_bmad-output" / "projects" / "demo" / "planning-artifacts" / "retros"
    retros.mkdir(parents=True)
    (retros / "retro-demo-2026-09-01.md").write_text("# real retro\n", encoding="utf-8")

    store = FlatFileGraphStore(tmp_path / "graph.json")
    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    citations = {n.citation for n in store.iter_nodes()}
    assert "archive/old/.memlog.md" not in citations
    assert "pkg/tests/.memlog.md" not in citations
    assert not any("implementation-artifacts" in c for c in citations)
    assert not any("spec-12-1-landed-retros" in c for c in citations)
    assert "_bmad-output/projects/demo/planning-artifacts/retros/retro-demo-2026-09-01.md" in citations


def test_active_dreams_and_specs_compile_inactive_are_skipped(tmp_path: Path, memory_root: Path) -> None:
    capture(memory_root, "feedback", "content")
    dreams = tmp_path / "docs" / "dreams"
    dreams.mkdir(parents=True)
    (dreams / "README.md").write_text("# Dreams\n", encoding="utf-8")
    (dreams / "live.md").write_text("---\nstatus: specified\n---\n# Live dream\n", encoding="utf-8")
    (dreams / "done.md").write_text("---\nstatus: realized\n---\n# Done dream\n", encoding="utf-8")
    spec_dir = tmp_path / "_bmad-output" / "projects" / "demo" / "planning-artifacts" / "specs" / "spec-demo"
    spec_dir.mkdir(parents=True)
    (spec_dir / "SPEC.md").write_text("---\nstatus: ready\n---\n# Demo spec\n", encoding="utf-8")
    shipped = tmp_path / "_bmad-output" / "projects" / "demo" / "planning-artifacts" / "specs" / "spec-old"
    shipped.mkdir(parents=True)
    (shipped / "SPEC.md").write_text("---\nstatus: shipped\n---\n# Old spec\n", encoding="utf-8")

    store = FlatFileGraphStore(tmp_path / "graph.json")
    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    citations = {n.citation for n in store.iter_nodes() if n.kind == "doc"}
    assert "docs/dreams/live.md" in citations
    assert "docs/dreams/done.md" not in citations
    assert "docs/dreams/README.md" not in citations
    assert "_bmad-output/projects/demo/planning-artifacts/specs/spec-demo/SPEC.md" in citations
    assert "_bmad-output/projects/demo/planning-artifacts/specs/spec-old/SPEC.md" not in citations


def test_in_flight_story_spec_compiles_done_and_stale_frontmatter_do_not(tmp_path: Path, memory_root: Path) -> None:
    capture(memory_root, "feedback", "content")
    specs = tmp_path / "_bmad-output" / "projects" / "demo" / "planning-artifacts" / "specs"
    specs.mkdir(parents=True)
    flying = "---\nstatus: ready-for-dev\n---\n# In flight\nuniqueinflighttoken\n"
    landed = "---\nstatus: ready-for-dev\n---\n# Landed\nuniquehistorictoken\n"
    (specs / "spec-10-1-in-flight-story-specs-join-the-compile.md").write_text(flying, encoding="utf-8")
    (specs / "spec-2-1-graphstore-port-flat-file-adapter.md").write_text(landed, encoding="utf-8")
    (specs / "spec-10-2-backlog-only.md").write_text("---\nstatus: ready-for-dev\n---\n# Backlog\n", encoding="utf-8")
    ledger = tmp_path / "_bmad-output" / "projects" / "demo" / "planning-artifacts" / "sprint-status-ledger.yaml"
    ledger.write_text(
        "development_status:\n"
        "  10-1-in-flight-story-specs-join-the-compile: in-progress\n"
        "  2-1-graphstore-port-flat-file-adapter: done\n"
        "  10-2-backlog-only: backlog\n"
        "  epic-10: in-progress\n",
        encoding="utf-8",
    )

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    citations = {n.citation for n in store.iter_nodes() if n.kind == "doc"}
    assert (
        "_bmad-output/projects/demo/planning-artifacts/specs/"
        "spec-10-1-in-flight-story-specs-join-the-compile.md" in citations
    )
    assert not any("spec-2-1-graphstore" in c for c in citations)
    assert not any("spec-10-2-backlog" in c for c in citations)
    assert not any("story spec" in w.lower() or "in-flight" in w.lower() for w in result.warnings)


def test_missing_ledger_adds_no_story_spec_nodes_or_warning(tmp_path: Path, memory_root: Path) -> None:
    capture(memory_root, "feedback", "content")
    specs = tmp_path / "_bmad-output" / "projects" / "demo" / "planning-artifacts" / "specs"
    specs.mkdir(parents=True)
    (specs / "spec-10-1-in-flight-story-specs-join-the-compile.md").write_text(
        "---\nstatus: in-progress\n---\n# Would compile if ledger said so\n",
        encoding="utf-8",
    )

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    assert not any("spec-10-1-in-flight" in n.citation for n in store.iter_nodes())
    assert not any("story spec" in w.lower() for w in result.warnings)


def test_planning_pointers_extract_ids_and_omit_wholesale_body(tmp_path: Path, memory_root: Path) -> None:
    capture(memory_root, "feedback", "content")
    planning = tmp_path / "_bmad-output" / "projects" / "demo" / "planning-artifacts"
    prd = planning / "prds" / "prd-demo" / "prd.md"
    brief = planning / "briefs" / "brief-demo" / "brief.md"
    spine = planning / "architecture" / "architecture-demo" / "ARCHITECTURE-SPINE.md"
    epics = planning / "epics.md"
    prd.parent.mkdir(parents=True)
    brief.parent.mkdir(parents=True)
    spine.parent.mkdir(parents=True)
    marker = "WHOLESALEBODYMARKERUNIQUE"
    prd.write_text(
        f"---\nstatus: final\n---\n# PRD: demo\n\n{marker} " + ("lorem " * 4000) + "\n\nFR-1 and later FR-2.\n",
        encoding="utf-8",
    )
    brief.write_text(
        "---\nstatus: complete\n---\n# Product Brief: demo\n\nintro only\n",
        encoding="utf-8",
    )
    spine.write_text(
        "---\nstatus: final\n---\n# Architecture Spine\n\nAD-1 holds. AD-2 follows.\n",
        encoding="utf-8",
    )
    epics.write_text(
        "---\nstatus: canonical\n---\n# demo epics\n\n"
        "## Epic 1: First slice\n\n### Story 1.1: Land it\n\nlong story body\n",
        encoding="utf-8",
    )
    (planning / "epics-deckcraft.md").write_text("# Chain epics novel\n" + marker + "\n", encoding="utf-8")
    (planning / "architecture-cf-atlas.md").write_text("# Architecture novel\nAD-99\n", encoding="utf-8")
    (planning / "prds" / "prd-demo" / "addendum.md").write_text("# Addendum\nFR-99\n", encoding="utf-8")
    (planning / "research").mkdir()
    (planning / "research" / "note.md").write_text("# Research\nFR-88\n", encoding="utf-8")

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    pointers = {
        n.citation: n
        for n in store.iter_nodes()
        if n.kind == "doc" and n.citation.startswith("_bmad-output/projects/demo/")
    }
    prd_cite = "_bmad-output/projects/demo/planning-artifacts/prds/prd-demo/prd.md"
    assert prd_cite in pointers
    assert marker not in pointers[prd_cite].text
    assert "FR-1" in pointers[prd_cite].text
    assert "FR-2" in pointers[prd_cite].text
    assert "pointer:prd" in pointers[prd_cite].text
    assert pointers[prd_cite].text.startswith("pointer:")
    assert "status:final" in pointers[prd_cite].text
    assert len(pointers[prd_cite].text) <= 4_000

    brief_cite = "_bmad-output/projects/demo/planning-artifacts/briefs/brief-demo/brief.md"
    assert brief_cite in pointers
    assert "pointer:brief" in pointers[brief_cite].text
    assert "status:complete" in pointers[brief_cite].text

    spine_cite = "_bmad-output/projects/demo/planning-artifacts/architecture/architecture-demo/ARCHITECTURE-SPINE.md"
    assert spine_cite in pointers
    assert "AD-1" in pointers[spine_cite].text
    assert "pointer:architecture" in pointers[spine_cite].text

    epics_cite = "_bmad-output/projects/demo/planning-artifacts/epics.md"
    assert epics_cite in pointers
    assert "Epic 1: First slice" in pointers[epics_cite].text
    assert "Story 1.1: Land it" in pointers[epics_cite].text
    assert "long story body" not in pointers[epics_cite].text

    citations = set(pointers)
    assert not any("epics-deckcraft" in c for c in citations)
    assert not any("architecture-cf-atlas" in c for c in citations)
    assert not any("addendum.md" in c for c in citations)
    assert not any("/research/" in c for c in citations)
    assert not any("planning pointer" in w.lower() for w in result.warnings)


def test_missing_planning_tree_adds_no_pointer_nodes_or_warning(tmp_path: Path, memory_root: Path) -> None:
    capture(memory_root, "feedback", "content")
    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )
    assert not any(
        "planning-artifacts/epics.md" in n.citation or "ARCHITECTURE-SPINE" in n.citation or "/prd.md" in n.citation
        for n in store.iter_nodes()
    )
    assert not any("pointer" in w.lower() and "planning" in w.lower() for w in result.warnings)


def test_named_docs_compile_how_tos_and_catalog_extract_not_docs_tree(tmp_path: Path, memory_root: Path) -> None:
    capture(memory_root, "feedback", "content")
    how_to = tmp_path / "docs" / "how-to"
    how_to.mkdir(parents=True)
    (how_to / "pixi-tasks.md").write_text("# Pixi tasks\nhowtopixiuniquetoken\n", encoding="utf-8")
    (how_to / "README.md").write_text("# How-to index\n", encoding="utf-8")
    (tmp_path / "docs" / "explanation").mkdir(parents=True)
    (tmp_path / "docs" / "explanation" / "why.md").write_text("# Why\nexplanationuniquetoken\n", encoding="utf-8")
    (tmp_path / "docs" / "tutorials").mkdir(parents=True)
    (tmp_path / "docs" / "tutorials" / "getting-started.md").write_text(
        "# Start\ntutorialuniquetoken\n", encoding="utf-8"
    )
    catalog = tmp_path / "docs" / "reference" / "library-llms-full.md"
    catalog.parent.mkdir(parents=True)
    marker = "CATALOGBODYMARKERUNIQUE"
    catalog.write_text(
        "# Library catalog\n\n## 1. Core runtime\n\n"
        f"{marker} " + ("lorem " * 2000) + "\n\n## 16. Explicitly NOT available\n",
        encoding="utf-8",
    )

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )

    citations = {n.citation: n for n in store.iter_nodes() if n.kind == "doc"}
    assert "docs/how-to/pixi-tasks.md" in citations
    assert "howtopixiuniquetoken" in citations["docs/how-to/pixi-tasks.md"].text
    assert "docs/how-to/README.md" not in citations
    assert "docs/explanation/why.md" not in citations
    assert "docs/tutorials/getting-started.md" not in citations
    catalog_cite = "docs/reference/library-llms-full.md"
    assert catalog_cite in citations
    assert "pointer:library-catalog" in citations[catalog_cite].text
    assert "1. Core runtime" in citations[catalog_cite].text
    assert "16. Explicitly NOT available" in citations[catalog_cite].text
    assert marker not in citations[catalog_cite].text
    assert not any("named docs" in w.lower() or "library-llms" in w.lower() for w in result.warnings)


def test_missing_named_docs_adds_no_nodes_or_warning(tmp_path: Path, memory_root: Path) -> None:
    capture(memory_root, "feedback", "content")
    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "no-transcripts",
    )
    assert not any(
        n.citation.startswith("docs/how-to/") or n.citation.endswith("library-llms-full.md") for n in store.iter_nodes()
    )
    assert not any("named docs" in w.lower() or "library-llms" in w.lower() for w in result.warnings)
