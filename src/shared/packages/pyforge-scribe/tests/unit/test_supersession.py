"""End-to-end fact-supersession tests (Story 2.3, AD-4): capture -> compile
-> query. The mechanism (`invalidate_edge`, `_apply_supersession`) was
written alongside Stories 2.1/2.2; this file proves the full contract.
"""

from __future__ import annotations

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


def test_superseded_record_stays_present_and_marked_ended(tmp_path: Path, memory_root: Path) -> None:
    old = capture(memory_root, "project", "Original plan: use engine X.", slug="plan-x")
    new = capture(
        memory_root,
        "project",
        "Revised plan: use engine Y instead.",
        slug="plan-y",
        supersedes="project/plan-x",
    )

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(memory_root=memory_root, repo_root=tmp_path, store=store)

    assert result.invalidated_count == 1
    nodes = {n.id: n for n in store.iter_nodes()}
    old_node = nodes["memory:project/plan-x"]
    new_node = nodes["memory:project/plan-y"]

    assert old_node.valid_until is not None
    assert old_node.is_current is False
    assert old_node.superseded_by == "memory:project/plan-y"
    assert new_node.is_current is True
    assert new_node.superseded_by is None
    # Both filenames matter -- fixture used explicit slugs.
    assert old.path.stem == "plan-x"
    assert new.path.stem == "plan-y"


def test_query_by_citation_resolves_superseded_record_distinguishing_current(
    tmp_path: Path, memory_root: Path
) -> None:
    capture(memory_root, "project", "Original plan.", slug="plan-x")
    capture(memory_root, "project", "Revised plan.", slug="plan-y", supersedes="project/plan-x")

    store = FlatFileGraphStore(tmp_path / "graph.json")
    compile_graph(memory_root=memory_root, repo_root=tmp_path, store=store)

    old_citation = ".claude/memory/project/plan-x.md"
    matches = store.query_by_citation(old_citation)
    assert len(matches) == 1
    assert matches[0].is_current is False

    new_citation = ".claude/memory/project/plan-y.md"
    new_matches = store.query_by_citation(new_citation)
    assert len(new_matches) == 1
    assert new_matches[0].is_current is True


def test_dangling_supersedes_reference_is_skipped_not_raised(tmp_path: Path, memory_root: Path) -> None:
    capture(memory_root, "project", "Stands alone.", slug="standalone", supersedes="project/ghost")

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(memory_root=memory_root, repo_root=tmp_path, store=store)

    assert result.invalidated_count == 0
    assert any("ghost" in w for w in result.warnings)
    node = next(iter(store.iter_nodes()))
    assert node.is_current is True


def test_recompile_after_supersession_is_still_idempotent(tmp_path: Path, memory_root: Path) -> None:
    capture(memory_root, "project", "Original plan.", slug="plan-x")
    capture(memory_root, "project", "Revised plan.", slug="plan-y", supersedes="project/plan-x")
    store_path = tmp_path / "graph.json"

    compile_graph(memory_root=memory_root, repo_root=tmp_path, store=FlatFileGraphStore(store_path))
    first_bytes = store_path.read_bytes()

    compile_graph(memory_root=memory_root, repo_root=tmp_path, store=FlatFileGraphStore(store_path))
    second_bytes = store_path.read_bytes()

    assert first_bytes == second_bytes


def test_chained_supersession_each_hop_has_its_own_distinct_pointer(
    tmp_path: Path, memory_root: Path
) -> None:
    capture(memory_root, "project", "Plan A.", slug="plan-a")
    capture(memory_root, "project", "Plan B.", slug="plan-b", supersedes="project/plan-a")
    capture(memory_root, "project", "Plan C.", slug="plan-c", supersedes="project/plan-b")

    store = FlatFileGraphStore(tmp_path / "graph.json")
    result = compile_graph(memory_root=memory_root, repo_root=tmp_path, store=store)

    assert result.invalidated_count == 2
    nodes = {n.id: n for n in store.iter_nodes()}
    assert nodes["memory:project/plan-a"].is_current is False
    assert nodes["memory:project/plan-a"].superseded_by == "memory:project/plan-b"
    assert nodes["memory:project/plan-b"].is_current is False
    assert nodes["memory:project/plan-b"].superseded_by == "memory:project/plan-c"
    assert nodes["memory:project/plan-c"].is_current is True
