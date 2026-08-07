"""Typer CliRunner smoke tests for the `scribe` CLI (FR-14 contract proof).

Every test that touches the filesystem `monkeypatch.chdir()`s into a fresh
`tmp_path` first — never the real repo `.claude/memory/` tree — matching
the I/O & Edge-Case Matrix in
spec-1-1-package-scaffold-direct-capture-into-team-memory.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from pyforge.scribe.cli import app

runner = CliRunner()

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
