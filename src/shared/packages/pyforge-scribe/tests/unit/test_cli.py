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


def test_graph_compile_stub_touches_nothing_and_exits_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["graph", "compile", "--nightly"])

    assert result.exit_code == 0
    assert "not yet implemented" in _combined_output(result)
    assert not (tmp_path / ".claude").exists()


def test_recall_stub_touches_nothing_and_exits_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["recall", "why did we pick X"])

    assert result.exit_code == 0
    assert "not yet implemented" in _combined_output(result)
    assert not (tmp_path / ".claude").exists()
