"""Unit tests for pyforge.scribe.compile -- the nightly projection builder
(Story 2.2/2.3).

Every test builds a throwaway `tmp_path` repo/memory tree -- never the real
repo's `.claude/memory/`/`.git` state.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from pyforge.scribe.capture import capture
from pyforge.scribe.compile import compile_graph
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
    subprocess.run(
        ["git", *args], cwd=str(repo_root), check=True, capture_output=True, text=True
    )


def _init_git_repo_with_commits(repo_root: Path, count: int = 2) -> None:
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "Test")
    for i in range(count):
        (repo_root / f"file{i}.txt").write_text(f"content {i}\n", encoding="utf-8")
        _git(repo_root, "add", "-A")
        _git(repo_root, "commit", "-q", "-m", f"commit {i}")


def _assistant_transcript_line(text: str, *, timestamp: str = "2026-08-20T12:00:00.000Z") -> str:
    entry = {
        "type": "assistant",
        "timestamp": timestamp,
        "message": {"content": [{"type": "text", "text": text}]},
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

    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=FlatFileGraphStore(store_path),
        transcript_root=no_transcripts,
    )
    first_bytes = store_path.read_bytes()

    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=FlatFileGraphStore(store_path),
        transcript_root=no_transcripts,
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
    assert result.warnings == () or all(
        ("git" in w or "transcript" in w) for w in result.warnings
    )


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


def test_malformed_memory_entry_is_skipped_with_warning_not_aborted(
    tmp_path: Path, memory_root: Path
) -> None:
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
    result = compile_graph(
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


def test_data_named_directory_outside_dot_claude_is_not_excluded(
    tmp_path: Path, memory_root: Path
) -> None:
    """Review finding: `_EXCLUDED_DIR_NAMES` matched the bare name "data"
    ANYWHERE in a path, silently dropping a legitimate CHANGELOG.md/
    .memlog.md/*retro*.md under any directory literally named "data" --
    "data" is only meant to exclude THIS repo's own `.claude/data`."""
    capture(memory_root, "feedback", "content")
    other_data_dir = tmp_path / "src" / "mypackage" / "data"
    other_data_dir.mkdir(parents=True)
    (other_data_dir / "CHANGELOG.md").write_text("# Changes\n\nsomething\n", encoding="utf-8")

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(
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
    assert len(transcript_nodes) == 1
    node = transcript_nodes[0]
    assert node.text == "We decided to use SQLite for the local cache."
    assert node.citation == "session-a.jsonl:L1"
    assert node.id == "transcript:session-a.jsonl:L1"


def test_transcript_surface_curated_covered_content_is_not_double_indexed(
    tmp_path: Path, memory_root: Path
) -> None:
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


def test_transcript_surface_missing_root_warns_and_contributes_zero_nodes(
    tmp_path: Path, memory_root: Path
) -> None:
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


def test_transcript_surface_two_candidates_on_one_line_get_distinct_ids(
    tmp_path: Path, memory_root: Path
) -> None:
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


def test_transcript_surface_idempotent_rerun_is_byte_identical(
    tmp_path: Path, memory_root: Path
) -> None:
    transcript_root = tmp_path / "transcripts"
    _write_transcript_jsonl(
        transcript_root,
        "session-a.jsonl",
        [_assistant_transcript_line("We decided to use SQLite for the local cache.")],
    )
    store_path = tmp_path / "graph.json"

    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=FlatFileGraphStore(store_path),
        transcript_root=transcript_root,
    )
    first_bytes = store_path.read_bytes()

    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=FlatFileGraphStore(store_path),
        transcript_root=transcript_root,
    )
    second_bytes = store_path.read_bytes()

    assert first_bytes == second_bytes
