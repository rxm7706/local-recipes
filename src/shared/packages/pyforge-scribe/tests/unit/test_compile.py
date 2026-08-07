"""Unit tests for pyforge.scribe.compile -- the nightly projection builder
(Story 2.2/2.3).

Every test builds a throwaway `tmp_path` repo/memory tree -- never the real
repo's `.claude/memory/`/`.git` state.
"""

from __future__ import annotations

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


def test_missing_memory_root_raises_before_any_write(tmp_path: Path) -> None:
    store = FlatFileGraphStore(tmp_path / "graph.json")
    with pytest.raises(ValueError, match="does not exist"):
        compile_graph(memory_root=tmp_path / "nope", repo_root=tmp_path, store=store)
    assert not (tmp_path / "graph.json").exists()


def test_happy_path_produces_traceable_nodes(tmp_path: Path, memory_root: Path) -> None:
    capture(memory_root, "feedback", "Always run tests first.")
    (tmp_path / ".memlog.md").write_text("session log entry\n", encoding="utf-8")
    _init_git_repo_with_commits(tmp_path, count=2)

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(memory_root=memory_root, repo_root=tmp_path, store=store)

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

    compile_graph(memory_root=memory_root, repo_root=tmp_path, store=FlatFileGraphStore(store_path))
    first_bytes = store_path.read_bytes()

    compile_graph(memory_root=memory_root, repo_root=tmp_path, store=FlatFileGraphStore(store_path))
    second_bytes = store_path.read_bytes()

    assert first_bytes == second_bytes


def test_no_optional_surfaces_present_still_succeeds(tmp_path: Path, memory_root: Path) -> None:
    capture(memory_root, "feedback", "Only memory content, nothing else.")

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(memory_root=memory_root, repo_root=tmp_path, store=store)

    assert result.node_count == 1
    assert result.warnings == () or all("git" in w for w in result.warnings)


def test_git_absent_logs_warning_and_does_not_abort(
    tmp_path: Path, memory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    capture(memory_root, "feedback", "content")
    monkeypatch.setattr("shutil.which", lambda name: None)

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(memory_root=memory_root, repo_root=tmp_path, store=store)

    assert result.node_count == 1
    assert any("git" in w.lower() for w in result.warnings)


def test_malformed_memory_entry_is_skipped_with_warning_not_aborted(
    tmp_path: Path, memory_root: Path
) -> None:
    capture(memory_root, "feedback", "a good entry")
    (memory_root / "feedback" / "broken.md").write_text("not frontmatter at all\n", encoding="utf-8")

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(memory_root=memory_root, repo_root=tmp_path, store=store)

    assert result.node_count == 1  # only the good entry
    assert any("broken.md" in w for w in result.warnings)


def test_compile_never_prompts(tmp_path: Path, memory_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Unattended (FR-11): patch builtins.input to raise if ever called."""
    capture(memory_root, "feedback", "content")

    def _raise_on_input(*args, **kwargs):
        raise AssertionError("compile_graph must never call input()")

    monkeypatch.setattr("builtins.input", _raise_on_input)
    store = FlatFileGraphStore(tmp_path / "graph.json")
    compile_graph(memory_root=memory_root, repo_root=tmp_path, store=store)  # must not raise
