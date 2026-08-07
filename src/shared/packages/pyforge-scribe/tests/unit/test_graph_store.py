"""Unit tests for pyforge.scribe.graph_store -- the GraphStore port + the
flat-file v1 adapter (Story 2.1).

Every test uses `tmp_path` for the store location -- never a real repo path.
"""

from __future__ import annotations

import json
import socket
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pyforge.scribe.graph_store import FlatFileGraphStore
from pyforge.scribe.models import GraphNode


def _node(node_id: str = "memory:feedback/x", **overrides) -> GraphNode:
    defaults = dict(
        id=node_id,
        kind="memory",
        title="x",
        text="some captured text",
        citation=".claude/memory/feedback/x.md",
        valid_from=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return GraphNode(**defaults)


def test_fresh_store_is_empty(tmp_path: Path) -> None:
    store = FlatFileGraphStore(tmp_path / "graph.json")
    assert list(store.iter_nodes()) == []
    assert store.query_by_citation(".claude/memory/feedback/x.md") == []


def test_upsert_commit_reopen_round_trips(tmp_path: Path) -> None:
    store_path = tmp_path / "graph.json"
    store = FlatFileGraphStore(store_path)
    store.reset()
    store.upsert_node(_node())
    store.commit()

    reopened = FlatFileGraphStore(store_path)
    nodes = list(reopened.iter_nodes())
    assert [n.id for n in nodes] == ["memory:feedback/x"]
    assert nodes[0].text == "some captured text"
    assert nodes[0].is_current


def test_query_by_citation_finds_matching_node(tmp_path: Path) -> None:
    store = FlatFileGraphStore(tmp_path / "graph.json")
    store.reset()
    store.upsert_node(_node())
    store.commit()

    matches = store.query_by_citation(".claude/memory/feedback/x.md")
    assert [m.id for m in matches] == ["memory:feedback/x"]
    assert store.query_by_citation("does/not/exist.md") == []


def test_upsert_same_id_twice_last_write_wins(tmp_path: Path) -> None:
    store_path = tmp_path / "graph.json"
    store = FlatFileGraphStore(store_path)
    store.reset()
    store.upsert_node(_node(text="first"))
    store.upsert_node(_node(text="second"))
    store.commit()

    nodes = list(FlatFileGraphStore(store_path).iter_nodes())
    assert len(nodes) == 1
    assert nodes[0].text == "second"


def test_recommit_identical_node_set_is_byte_identical(tmp_path: Path) -> None:
    store_path = tmp_path / "graph.json"

    store_one = FlatFileGraphStore(store_path)
    store_one.reset()
    store_one.upsert_node(_node())
    store_one.commit()
    first_bytes = store_path.read_bytes()

    store_two = FlatFileGraphStore(store_path)
    store_two.reset()
    store_two.upsert_node(_node())
    store_two.commit()
    second_bytes = store_path.read_bytes()

    assert first_bytes == second_bytes


def test_invalidate_edge_on_unknown_id_raises_before_any_write(tmp_path: Path) -> None:
    store_path = tmp_path / "graph.json"
    store = FlatFileGraphStore(store_path)
    store.reset()

    with pytest.raises(ValueError, match="unknown node id"):
        store.invalidate_edge(
            "memory:feedback/nope",
            ended_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
            superseded_by="memory:feedback/newer",
        )
    assert not store_path.exists()


def test_invalidate_edge_marks_ended_but_keeps_node_present(tmp_path: Path) -> None:
    store_path = tmp_path / "graph.json"
    store = FlatFileGraphStore(store_path)
    store.reset()
    store.upsert_node(_node())
    ended_at = datetime(2026, 8, 2, tzinfo=timezone.utc)
    store.invalidate_edge("memory:feedback/x", ended_at=ended_at, superseded_by="memory:feedback/newer")
    store.commit()

    nodes = list(FlatFileGraphStore(store_path).iter_nodes())
    assert len(nodes) == 1
    node = nodes[0]
    assert node.valid_until == ended_at
    assert node.superseded_by == "memory:feedback/newer"
    assert not node.is_current
    # Still resolvable by citation -- traceable, not deleted.
    assert store.query_by_citation(".claude/memory/feedback/x.md")[0].id == "memory:feedback/x"


def test_reset_clears_memory_without_touching_disk_until_commit(tmp_path: Path) -> None:
    store_path = tmp_path / "graph.json"
    store = FlatFileGraphStore(store_path)
    store.reset()
    store.upsert_node(_node())
    store.commit()
    original_bytes = store_path.read_bytes()

    store.reset()
    assert list(store.iter_nodes()) == []
    # Disk untouched until the next commit().
    assert store_path.read_bytes() == original_bytes


def test_commit_output_is_sorted_and_deterministic(tmp_path: Path) -> None:
    store_path = tmp_path / "graph.json"
    store = FlatFileGraphStore(store_path)
    store.reset()
    store.upsert_node(_node(node_id="memory:feedback/z"))
    store.upsert_node(_node(node_id="memory:feedback/a"))
    store.commit()

    document = json.loads(store_path.read_text(encoding="utf-8"))
    assert list(document["nodes"].keys()) == ["memory:feedback/a", "memory:feedback/z"]


# --- offline conformance (AD-6) ----------------------------------------------


def test_flat_file_graph_store_makes_zero_network_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AD-6 offline-conformance: block every socket construction for the
    duration of a full reset/upsert/invalidate/commit/reopen/iter cycle --
    any attempted network call raises immediately instead of silently
    succeeding (or silently no-op-ing) against a real endpoint. Stronger
    than trusting a documented '--offline' flag: it fails on ANY socket
    construction, matching this story's own AC that offline-conformance is a
    dedicated test, not deferred."""

    def _blocked_socket(*args, **kwargs):
        raise AssertionError("network socket construction attempted -- AD-6 violation")

    monkeypatch.setattr(socket, "socket", _blocked_socket)

    store_path = tmp_path / "graph.json"
    store = FlatFileGraphStore(store_path)
    store.reset()
    store.upsert_node(_node())
    store.upsert_node(_node(node_id="memory:feedback/y", citation=".claude/memory/feedback/y.md"))
    store.invalidate_edge(
        "memory:feedback/x",
        ended_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        superseded_by="memory:feedback/y",
    )
    store.commit()

    reopened = FlatFileGraphStore(store_path)
    ids = [n.id for n in reopened.iter_nodes()]
    assert ids == ["memory:feedback/x", "memory:feedback/y"]
    assert reopened.query_by_citation(".claude/memory/feedback/y.md")[0].id == "memory:feedback/y"
