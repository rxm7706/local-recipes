"""Typer CliRunner smoke tests for the `scribe` CLI (FR-14 contract proof).

Every test that touches the filesystem `monkeypatch.chdir()`s into a fresh
`tmp_path` first — never the real repo `.claude/memory/` tree — matching
the I/O & Edge-Case Matrix in
spec-1-1-package-scaffold-direct-capture-into-team-memory.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import pyforge.scribe.cli as cli_module
from pyforge.scribe.cli import app
from pyforge.scribe.extras import graphify as graphify_module

runner = CliRunner()


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
    def __init__(self, nodes: dict[str, dict], god: list[dict] | None = None) -> None:
        self._nodes = nodes
        self._god = god or []

    def collect_files(self, target, root=None):
        return [Path(target) / "a.py"]

    def extract(self, files, cache_root=None, root=None, parallel=True):
        return {"nodes": [], "edges": [], "hyperedges": []}

    def build_from_json(self, extraction, root=None):
        return _FakeGraph(self._nodes)

    def god_nodes(self, graph, top_n=10):
        return self._god

_MEMORY_MD_STARTER = """# Team Memory Index

## Feedback

## Project

## Reference
"""


def _scaffold_memory_root(cwd: Path) -> Path:
    root = cwd / ".claude" / "memory"
    for capture_type in ("feedback", "project", "reference"):
        (root / capture_type).mkdir(parents=True)
    (root / "MEMORY.md").write_text(_MEMORY_MD_STARTER, encoding="utf-8")
    return root


def _combined_output(result) -> str:
    """stdout+stderr regardless of the installed Click's stream-mixing default."""
    text = result.output
    try:
        text += result.stderr
    except (ValueError, AttributeError):
        pass
    return text


def test_version_flag_prints_version_and_exits_0() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    from pyforge.scribe import __version__

    assert f"scribe {__version__}" in _combined_output(result)


def test_capture_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)

    result = runner.invoke(
        app,
        ["capture", "--type", "project", "--text", "ADR-005b: in-house gateway replaces LiteLLM"],
    )

    assert result.exit_code == 0
    project_dir = tmp_path / ".claude" / "memory" / "project"
    written = list(project_dir.glob("*.md"))
    assert len(written) == 1
    assert "ADR-005b" in written[0].read_text(encoding="utf-8")


def test_capture_invalid_type_writes_nothing_and_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)

    result = runner.invoke(app, ["capture", "--type", "decision", "--text", "some text"])

    assert result.exit_code == 2
    for capture_type in ("feedback", "project", "reference"):
        assert list((tmp_path / ".claude" / "memory" / capture_type).glob("*.md")) == []


def test_capture_missing_text_writes_nothing_and_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)

    result = runner.invoke(app, ["capture", "--type", "feedback"])

    assert result.exit_code == 2
    assert list((tmp_path / ".claude" / "memory" / "feedback").glob("*.md")) == []


def test_capture_blank_text_writes_nothing_and_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)

    result = runner.invoke(app, ["capture", "--type", "feedback", "--text", "   "])

    assert result.exit_code == 2
    assert list((tmp_path / ".claude" / "memory" / "feedback").glob("*.md")) == []


def test_capture_slug_collision_writes_second_distinct_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)

    args = ["capture", "--type", "feedback", "--text", "repeat capture text"]
    first = runner.invoke(app, args)
    second = runner.invoke(app, args)

    assert first.exit_code == 0
    assert second.exit_code == 0
    written = sorted((tmp_path / ".claude" / "memory" / "feedback").glob("*.md"))
    assert len(written) == 2


def _scaffold_source_entry(source_root: Path, filename: str, content: str) -> Path:
    path = source_root / filename
    path.write_text(content, encoding="utf-8")
    return path


def test_capture_promote_confirm_yes_writes_file_and_prints_proposal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)
    source_root = tmp_path / "source"
    source_root.mkdir()
    _scaffold_source_entry(
        source_root,
        "feedback_run_tests_first.md",
        "---\n"
        "name: run-tests-first\n"
        "description: I prefer running the tests before opening a PR.\n"
        "type: feedback\n"
        "---\n"
        "I prefer that contributors run the full test suite before opening a PR.\n",
    )

    result = runner.invoke(
        app, ["capture", "--promote", "--source", str(source_root)], input="y\n"
    )

    assert result.exit_code == 0
    written = list((tmp_path / ".claude" / "memory" / "feedback").glob("*.md"))
    assert len(written) == 1
    assert written[0].name == "run-tests-first.md"
    content = written[0].read_text(encoding="utf-8")
    assert "I prefer" not in content

    output = _combined_output(result)
    assert "team-relevant" in output
    assert "run-tests-first" in output
    assert "pointer-stub:" in output

    memory_md = (tmp_path / ".claude" / "memory" / "MEMORY.md").read_text(encoding="utf-8")
    assert "run-tests-first" in memory_md

    # Source is rewritten to a pointer stub (Story 1.4, FR-5), not left untouched.
    source_content = (source_root / "feedback_run_tests_first.md").read_text(encoding="utf-8")
    assert "promoted: true" in source_content
    assert "I prefer that contributors run the full test suite" not in source_content
    assert ".claude/memory/feedback/run-tests-first.md" in source_content


def test_capture_promote_reinvocation_after_confirm_reports_nothing_to_promote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)
    source_root = tmp_path / "source"
    source_root.mkdir()
    _scaffold_source_entry(
        source_root,
        "feedback_run_tests_first.md",
        "---\nname: run-tests-first\ndescription: Run tests first.\ntype: feedback\n---\n"
        "Run the full test suite before opening a PR.\n",
    )

    first = runner.invoke(
        app, ["capture", "--promote", "--source", str(source_root)], input="y\n"
    )
    assert first.exit_code == 0
    written_after_first = list((tmp_path / ".claude" / "memory" / "feedback").glob("*.md"))
    assert len(written_after_first) == 1

    # Re-invocation: no input needed -- if the code still called
    # typer.confirm() here (nothing promotable), CliRunner would abort.
    second = runner.invoke(app, ["capture", "--promote", "--source", str(source_root)])

    assert second.exit_code == 0
    assert "Nothing to promote" in _combined_output(second)
    written_after_second = list((tmp_path / ".claude" / "memory" / "feedback").glob("*.md"))
    assert written_after_second == written_after_first


def test_capture_promote_confirm_no_writes_nothing_and_exits_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)
    source_root = tmp_path / "source"
    source_root.mkdir()
    _scaffold_source_entry(
        source_root,
        "feedback_run_tests_first.md",
        "---\nname: run-tests-first\ndescription: Run tests first.\ntype: feedback\n---\n"
        "Run the full test suite before opening a PR.\n",
    )

    result = runner.invoke(
        app, ["capture", "--promote", "--source", str(source_root)], input="n\n"
    )

    assert result.exit_code == 0
    assert "Cancelled" in _combined_output(result)
    assert list((tmp_path / ".claude" / "memory" / "feedback").glob("*.md")) == []


def test_capture_promote_mixed_classifications_only_writes_team_relevant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)
    source_root = tmp_path / "source"
    source_root.mkdir()
    _scaffold_source_entry(
        source_root,
        "feedback_relevant.md",
        "---\nname: relevant\ndescription: A rule worth sharing.\ntype: feedback\n---\n"
        "Always rerender after a feedstock push.\n",
    )
    _scaffold_source_entry(
        source_root,
        "feedback_tone.md",
        "---\nname: tone\ndescription: Keep responses terse.\ntype: feedback\n---\n"
        "Personal tone preference.\n",
    )
    _scaffold_source_entry(
        source_root,
        "feedback_done.md",
        "---\nname: done\ndescription: Already done.\ntype: feedback\npromoted: true\n---\n"
        "Promoted to .claude/memory/feedback/done.md.\n",
    )
    _scaffold_source_entry(
        source_root,
        "feedback_stale.md",
        "---\nname: stale\ndescription: References a dead path.\ntype: feedback\n---\n"
        "See `src/pyforge/scribe/nope.py` for details.\n",
    )

    result = runner.invoke(
        app, ["capture", "--promote", "--source", str(source_root)], input="y\n"
    )

    assert result.exit_code == 0
    written = list((tmp_path / ".claude" / "memory" / "feedback").glob("*.md"))
    assert len(written) == 1
    assert written[0].name == "relevant.md"


def test_capture_promote_nothing_to_promote_skips_confirm_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)
    source_root = tmp_path / "source"
    source_root.mkdir()
    _scaffold_source_entry(
        source_root,
        "feedback_tone.md",
        "---\nname: tone\ndescription: Keep responses terse.\ntype: feedback\n---\nBody.\n",
    )

    # No input provided -- if the code incorrectly still called typer.confirm()
    # for an empty proposal, CliRunner would raise/abort for lack of stdin.
    result = runner.invoke(app, ["capture", "--promote", "--source", str(source_root)])

    assert result.exit_code == 0
    assert "Nothing to promote" in _combined_output(result)


def test_capture_promote_missing_source_dir_writes_nothing_and_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)

    result = runner.invoke(
        app, ["capture", "--promote", "--source", str(tmp_path / "does-not-exist")]
    )

    assert result.exit_code == 2
    for capture_type in ("feedback", "project", "reference"):
        assert list((tmp_path / ".claude" / "memory" / capture_type).glob("*.md")) == []


def test_capture_promote_mutually_exclusive_with_type_and_text_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)

    result = runner.invoke(
        app,
        ["capture", "--promote", "--type", "feedback", "--text", "some text"],
    )

    assert result.exit_code == 2
    assert list((tmp_path / ".claude" / "memory" / "feedback").glob("*.md")) == []


def _assistant_transcript_line(text: str, *, timestamp: str = "2026-08-20T12:00:00.000Z") -> str:
    entry = {
        "type": "assistant",
        "timestamp": timestamp,
        "message": {"content": [{"type": "text", "text": text}]},
    }
    return json.dumps(entry)


def _scaffold_transcript_entry(transcript_root: Path, filename: str, lines: list[str]) -> Path:
    path = transcript_root / filename
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_capture_transcripts_confirm_yes_writes_file_and_prints_proposal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)
    transcript_root = tmp_path / "transcripts"
    transcript_root.mkdir()
    source_path = _scaffold_transcript_entry(
        transcript_root,
        "session-a.jsonl",
        [_assistant_transcript_line("We decided to use SQLite for the local cache.")],
    )
    original_bytes = source_path.read_bytes()

    result = runner.invoke(
        app, ["capture", "--transcripts", "--source", str(transcript_root)], input="y\n"
    )

    assert result.exit_code == 0
    written = list((tmp_path / ".claude" / "memory" / "project").glob("*.md"))
    assert len(written) == 1
    content = written[0].read_text(encoding="utf-8")
    assert "We decided to use SQLite for the local cache." in content

    output = _combined_output(result)
    assert "session-a.jsonl:L1" in output
    assert "captured:" in output

    memory_md = (tmp_path / ".claude" / "memory" / "MEMORY.md").read_text(encoding="utf-8")
    assert "SQLite" in memory_md

    # No pointer-stub write-back (unlike --promote): the source transcript
    # is left byte-for-byte unmodified -- it's a historical log, not a
    # directory Scribe owns.
    assert source_path.read_bytes() == original_bytes


def test_capture_transcripts_confirm_no_writes_nothing_and_exits_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)
    transcript_root = tmp_path / "transcripts"
    transcript_root.mkdir()
    _scaffold_transcript_entry(
        transcript_root,
        "session-a.jsonl",
        [_assistant_transcript_line("We decided to use SQLite for the local cache.")],
    )

    result = runner.invoke(
        app, ["capture", "--transcripts", "--source", str(transcript_root)], input="n\n"
    )

    assert result.exit_code == 0
    assert "Cancelled" in _combined_output(result)
    assert list((tmp_path / ".claude" / "memory" / "project").glob("*.md")) == []


def test_capture_transcripts_nothing_to_promote_skips_confirm_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)
    transcript_root = tmp_path / "transcripts"
    transcript_root.mkdir()
    _scaffold_transcript_entry(
        transcript_root,
        "session-a.jsonl",
        [_assistant_transcript_line("Nothing decision-shaped happened in this turn.")],
    )

    # No input provided -- if the code incorrectly still called typer.confirm()
    # for an empty proposal, CliRunner would raise/abort for lack of stdin.
    result = runner.invoke(app, ["capture", "--transcripts", "--source", str(transcript_root)])

    assert result.exit_code == 0
    assert "Nothing to promote" in _combined_output(result)


def test_capture_transcripts_missing_source_dir_writes_nothing_and_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)

    result = runner.invoke(
        app, ["capture", "--transcripts", "--source", str(tmp_path / "does-not-exist")]
    )

    assert result.exit_code == 2
    for capture_type in ("feedback", "project", "reference"):
        assert list((tmp_path / ".claude" / "memory" / capture_type).glob("*.md")) == []


def test_capture_transcripts_mutually_exclusive_with_promote_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)

    result = runner.invoke(app, ["capture", "--transcripts", "--promote"])

    assert result.exit_code == 2
    for capture_type in ("feedback", "project", "reference"):
        assert list((tmp_path / ".claude" / "memory" / capture_type).glob("*.md")) == []


def test_capture_transcripts_mutually_exclusive_with_type_and_text_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)

    result = runner.invoke(
        app,
        ["capture", "--transcripts", "--type", "feedback", "--text", "some text"],
    )

    assert result.exit_code == 2
    assert list((tmp_path / ".claude" / "memory" / "feedback").glob("*.md")) == []


def test_capture_transcripts_confirm_yes_writes_full_sentence_at_truncation_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)
    transcript_root = tmp_path / "transcripts"
    transcript_root.mkdir()
    long_sentence = (
        "We decided to migrate the entire ingestion pipeline from the legacy REST "
        "polling architecture to a fully event-driven Kafka-based system after "
        "benchmarking showed a forty percent reduction in end-to-end latency "
        "during peak load testing."
    )
    assert len(long_sentence) > 120
    _scaffold_transcript_entry(
        transcript_root, "session-a.jsonl", [_assistant_transcript_line(long_sentence)]
    )

    result = runner.invoke(
        app, ["capture", "--transcripts", "--source", str(transcript_root)], input="y\n"
    )

    assert result.exit_code == 0
    written = list((tmp_path / ".claude" / "memory" / "project").glob("*.md"))
    assert len(written) == 1
    content = written[0].read_text(encoding="utf-8")
    assert long_sentence in content

    # The printed proposal shows only the truncated snippet -- never the
    # full sentence (Boundaries & Constraints: "quote only a truncated
    # snippet... never the full message"). The permanent captured file
    # (asserted above) is the only place the full sentence appears.
    assert long_sentence not in _combined_output(result)


def test_capture_transcripts_confirm_yes_capture_failure_exits_2_cleanly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)
    transcript_root = tmp_path / "transcripts"
    transcript_root.mkdir()
    _scaffold_transcript_entry(
        transcript_root,
        "session-a.jsonl",
        [_assistant_transcript_line("We decided to use SQLite for the local cache.")],
    )

    def _boom(*args, **kwargs):
        raise ValueError("simulated capture failure")

    monkeypatch.setattr(cli_module, "capture_write", _boom)

    result = runner.invoke(
        app, ["capture", "--transcripts", "--source", str(transcript_root)], input="y\n"
    )

    assert result.exit_code == 2
    assert "simulated capture failure" in _combined_output(result)


def test_graph_compile_missing_memory_root_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["graph", "compile", "--nightly"])

    assert result.exit_code == 2
    assert not (tmp_path / ".claude" / "data").exists()


def test_graph_compile_happy_path_is_unattended_and_reports_node_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)
    (tmp_path / ".claude" / "memory" / "feedback" / "one.md").write_text(
        '---\nname: "one"\ndescription: "d"\nmetadata:\n  type: feedback\n---\nBody text.\n',
        encoding="utf-8",
    )

    # No input provided -- if compile ever prompted, CliRunner would abort
    # for lack of stdin (the unattended AC).
    result = runner.invoke(app, ["graph", "compile", "--nightly"])

    assert result.exit_code == 0
    assert "compiled 1 node(s)" in _combined_output(result)
    assert (tmp_path / ".claude" / "data" / "pyforge-scribe" / "graph.json").is_file()


def test_graph_compile_overlapping_run_skips_with_exit_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Story 3.3: an overlapping cron firing (or a manual run while the
    nightly is still going) must be a clean exit-0 skip -- never a
    corrupted double-write, never red cron mail."""
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)
    from pyforge.scribe import compile as compile_module

    store_path = tmp_path / ".claude" / "data" / "pyforge-scribe" / "graph.json"
    with compile_module._compile_lock(store_path):
        result = runner.invoke(app, ["graph", "compile", "--nightly"])

    assert result.exit_code == 0
    assert "skipped" in _combined_output(result)
    assert not store_path.exists()


def test_recall_no_compiled_graph_yet_reports_no_grounded_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["recall", "why did we pick X"])

    assert result.exit_code == 0
    assert "no grounded answer found" in _combined_output(result)
    assert not (tmp_path / ".claude").exists()


def test_recall_after_compile_returns_grounded_cited_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)
    (tmp_path / ".claude" / "memory" / "project" / "kuzu-drop.md").write_text(
        '---\nname: "kuzu-drop"\ndescription: "d"\nmetadata:\n  type: project\n---\n'
        "We dropped Kuzu because it was archived upstream after an acquisition.\n",
        encoding="utf-8",
    )
    compile_result = runner.invoke(app, ["graph", "compile", "--nightly"])
    assert compile_result.exit_code == 0

    result = runner.invoke(app, ["recall", "why did we drop Kuzu"])

    assert result.exit_code == 0
    output = _combined_output(result)
    assert "archived upstream" in output
    assert "[source: .claude/memory/project/kuzu-drop.md]" in output


def test_graph_compile_registers_transcript_surface_and_recall_finds_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end proof of Story 3.2 (CAP-2): an un-curated transcript
    decision, present only in a raw session transcript, is registered as a
    compile source and is actually queryable via `scribe recall` --
    exercises `compile_graph()`'s real `default_transcript_root()` default
    wiring through the CLI, not an injected `transcript_root` override."""
    monkeypatch.chdir(tmp_path)
    _scaffold_memory_root(tmp_path)
    transcript_root = tmp_path / "transcripts"
    transcript_root.mkdir()
    _scaffold_transcript_entry(
        transcript_root,
        "session-a.jsonl",
        [_assistant_transcript_line("We decided to use SQLite for the local cache.")],
    )
    monkeypatch.setattr(
        "pyforge.scribe.compile.default_transcript_root", lambda: transcript_root
    )

    compile_result = runner.invoke(app, ["graph", "compile", "--nightly"])

    assert compile_result.exit_code == 0
    assert "compiled 1 node(s)" in _combined_output(compile_result)

    result = runner.invoke(app, ["recall", "why sqlite for the cache"])

    assert result.exit_code == 0
    output = _combined_output(result)
    assert "We decided to use SQLite for the local cache." in output
    assert "[source: session-a.jsonl:L1]" in output


# --- Story 6.1: `scribe index build|report|move-list` -----------------------


def test_index_build_missing_target_reports_zero_and_exits_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["index", "build"])

    assert result.exit_code == 0
    assert "indexed 0 code node(s)" in _combined_output(result)


def test_index_build_happy_path_writes_nodes_through_the_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "src" / "shared" / "packages"
    target.mkdir(parents=True)
    (target / "example.py").write_text("x = 1\n", encoding="utf-8")
    fake_nodes = {
        "python:example": {
            "label": "example",
            "source_file": "src/shared/packages/example.py",
            "source_location": "L1",
        }
    }
    monkeypatch.setattr(
        graphify_module, "_import_graphify", lambda: _FakeGraphifyModule(fake_nodes)
    )

    result = runner.invoke(app, ["index", "build"])

    assert result.exit_code == 0
    assert "indexed 1 code node(s)" in _combined_output(result)
    store_path = tmp_path / ".claude" / "data" / "pyforge-scribe" / "graph.json"
    assert store_path.is_file()
    document = json.loads(store_path.read_text(encoding="utf-8"))
    assert "code:python:example" in document["nodes"]


def test_index_build_graphify_unavailable_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    try:
        import graphify  # noqa: F401
    except ImportError:
        pass
    else:
        pytest.skip("graphifyy is installed in this environment")
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "src" / "shared" / "packages"
    target.mkdir(parents=True)
    (target / "example.py").write_text("x = 1\n", encoding="utf-8")

    result = runner.invoke(app, ["index", "build"])

    assert result.exit_code == 2


def test_index_report_writes_derived_gitignored_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "src" / "shared" / "packages"
    target.mkdir(parents=True)
    fake_nodes = {"a": {"label": "A", "source_file": "src/shared/packages/a.py"}}
    god = [{"id": "a", "label": "A", "degree": 3}]
    monkeypatch.setattr(
        graphify_module, "_import_graphify", lambda: _FakeGraphifyModule(fake_nodes, god)
    )

    result = runner.invoke(app, ["index", "report"])

    assert result.exit_code == 0
    report_path = tmp_path / ".claude" / "data" / "pyforge-scribe" / "graph-report.md"
    assert report_path.is_file()
    text = report_path.read_text(encoding="utf-8")
    assert "GRAPH_REPORT" in text
    assert "A (degree=3)" in text


def test_index_report_missing_target_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["index", "report"])

    assert result.exit_code == 2


def test_index_move_list_writes_json_with_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    src = tmp_path / "src" / "platform" / "app.py"
    src.parent.mkdir(parents=True)
    src.write_text(
        "import pyforge.scribe\nimport sys\nsys.path.insert(0, 'x')\n", encoding="utf-8"
    )

    result = runner.invoke(app, ["index", "move-list"])

    assert result.exit_code == 0
    move_list_path = tmp_path / ".claude" / "data" / "pyforge-scribe" / "move-list.json"
    assert move_list_path.is_file()
    document = json.loads(move_list_path.read_text(encoding="utf-8"))
    categories = {f["category"] for f in document["findings"]}
    assert "import_pyforge" in categories
    assert "sys_path_insert" in categories


def test_index_move_list_does_not_require_graphify(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The move-list scan is independent of graphifyy/SCRIBE_GRAPHIFY_EXTRA."""
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["index", "move-list"])

    assert result.exit_code == 0
    assert "0 finding(s)" in _combined_output(result)
