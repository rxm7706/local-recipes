"""Shared GraphStore operations vs local JSON and PostgreSQL/pgvector (FR-35).

The same protocol suite must pass against both drivers. A missing durable
backend fails the suite; it is not skipped green.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

import pytest

from pyforge.scribe.graph_store import GraphStore
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


StoreFactory = Callable[[], GraphStore]


def test_fresh_store_is_empty(graph_store_factory: StoreFactory) -> None:
    store = graph_store_factory()
    store.reset()
    store.commit()
    reopened = graph_store_factory()
    assert list(reopened.iter_nodes()) == []
    assert reopened.query_by_citation(".claude/memory/feedback/x.md") == []


def test_upsert_commit_reopen_round_trips(graph_store_factory: StoreFactory) -> None:
    store = graph_store_factory()
    store.reset()
    store.upsert_node(_node())
    store.commit()

    reopened = graph_store_factory()
    nodes = list(reopened.iter_nodes())
    assert [n.id for n in nodes] == ["memory:feedback/x"]
    assert nodes[0].text == "some captured text"
    assert nodes[0].is_current


def test_upsert_stale_commit_reopen_round_trips(graph_store_factory: StoreFactory) -> None:
    store = graph_store_factory()
    store.reset()
    store.upsert_node(_node(stale=True))
    store.commit()

    reopened = graph_store_factory()
    nodes = list(reopened.iter_nodes())
    assert [n.id for n in nodes] == ["memory:feedback/x"]
    assert nodes[0].stale is True


def test_query_by_citation_finds_matching_node(graph_store_factory: StoreFactory) -> None:
    store = graph_store_factory()
    store.reset()
    store.upsert_node(_node())
    store.commit()

    matches = store.query_by_citation(".claude/memory/feedback/x.md")
    assert [m.id for m in matches] == ["memory:feedback/x"]
    assert store.query_by_citation("does/not/exist.md") == []


def test_upsert_same_id_twice_last_write_wins(graph_store_factory: StoreFactory) -> None:
    store = graph_store_factory()
    store.reset()
    store.upsert_node(_node(text="first"))
    store.upsert_node(_node(text="second"))
    store.commit()

    nodes = list(graph_store_factory().iter_nodes())
    assert len(nodes) == 1
    assert nodes[0].text == "second"


def test_invalidate_edge_on_unknown_id_raises_before_persist(
    graph_store_factory: StoreFactory,
) -> None:
    store = graph_store_factory()
    store.reset()
    store.commit()
    with pytest.raises(ValueError, match="unknown node id"):
        store.invalidate_edge(
            "memory:feedback/nope",
            ended_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
            superseded_by="memory:feedback/newer",
        )
    assert list(graph_store_factory().iter_nodes()) == []


def test_invalidate_edge_marks_ended_but_keeps_node_present(
    graph_store_factory: StoreFactory,
) -> None:
    store = graph_store_factory()
    store.reset()
    store.upsert_node(_node())
    ended_at = datetime(2026, 8, 2, tzinfo=timezone.utc)
    store.invalidate_edge("memory:feedback/x", ended_at=ended_at, superseded_by="memory:feedback/newer")
    store.commit()

    nodes = list(graph_store_factory().iter_nodes())
    assert len(nodes) == 1
    node = nodes[0]
    assert node.valid_until == ended_at
    assert node.superseded_by == "memory:feedback/newer"
    assert not node.is_current
    assert store.query_by_citation(".claude/memory/feedback/x.md")[0].id == "memory:feedback/x"


def test_reset_clears_memory_without_touching_durable_until_commit(
    graph_store_factory: StoreFactory,
) -> None:
    store = graph_store_factory()
    store.reset()
    store.upsert_node(_node())
    store.commit()

    store.reset()
    assert list(store.iter_nodes()) == []
    still = list(graph_store_factory().iter_nodes())
    assert [n.id for n in still] == ["memory:feedback/x"]
