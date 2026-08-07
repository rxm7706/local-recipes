"""Unit tests for pyforge.scribe.recall -- the grounded, cited query path
(Story 2.4, AD-8).
"""

from __future__ import annotations

import socket
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pyforge.scribe.graph_store import FlatFileGraphStore
from pyforge.scribe.models import GraphNode
from pyforge.scribe.recall import answer


def _node(**overrides) -> GraphNode:
    defaults = dict(
        id="memory:project/kuzu-drop",
        kind="memory",
        title="kuzu-drop",
        text="We dropped Kuzu because it was archived upstream after an acquisition.",
        citation="notes/kuzu-drop.md",
        valid_from=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return GraphNode(**defaults)


@pytest.fixture()
def repo_with_citation(tmp_path: Path) -> Path:
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "kuzu-drop.md").write_text("content", encoding="utf-8")
    return tmp_path


def test_grounded_match_returns_citation(repo_with_citation: Path) -> None:
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(_node())
    store.commit()

    result = answer("why did we drop Kuzu?", store, repo_root=repo_with_citation)

    assert result.grounded is True
    assert result.citation == "notes/kuzu-drop.md"
    assert "archived" in result.text


def test_no_coverage_returns_explicit_no_grounded_answer(repo_with_citation: Path) -> None:
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(_node())
    store.commit()

    result = answer("what is the capital of France", store, repo_root=repo_with_citation)

    assert result.grounded is False
    assert result.text == "no grounded answer found"
    assert result.citation is None


def test_blank_query_returns_no_grounded_answer(repo_with_citation: Path) -> None:
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    result = answer("   ", store, repo_root=repo_with_citation)
    assert result.grounded is False


def test_superseded_node_is_excluded_from_default_answer(repo_with_citation: Path) -> None:
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(_node())
    store.invalidate_edge(
        "memory:project/kuzu-drop",
        ended_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        superseded_by="memory:project/kuzu-drop-v2",
    )
    store.commit()

    result = answer("why did we drop Kuzu?", store, repo_root=repo_with_citation)

    assert result.grounded is False


def test_unresolvable_citation_is_skipped_falls_through(repo_with_citation: Path) -> None:
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(_node(citation="notes/does-not-exist.md"))
    store.commit()

    result = answer("why did we drop Kuzu?", store, repo_root=repo_with_citation)

    assert result.grounded is False


def test_unresolvable_citation_falls_through_to_next_candidate(repo_with_citation: Path) -> None:
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(
        _node(
            id="memory:project/kuzu-drop-ghost",
            citation="notes/does-not-exist.md",
            text="Kuzu was dropped, ghost citation edition.",
        )
    )
    store.upsert_node(_node())  # real, resolvable citation
    store.commit()

    result = answer("why did we drop Kuzu?", store, repo_root=repo_with_citation)

    assert result.grounded is True
    assert result.citation == "notes/kuzu-drop.md"


def test_commit_citation_is_resolvable_if_well_formed_sha(repo_with_citation: Path) -> None:
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(
        _node(
            id="commit:abc1234",
            kind="commit",
            citation="commit:abc1234",
            text="Dropped Kuzu in this commit.",
        )
    )
    store.commit()

    result = answer("why did we drop Kuzu?", store, repo_root=repo_with_citation)

    assert result.grounded is True
    assert result.citation == "commit:abc1234"


def test_determinism_two_independent_store_instances_same_file_same_answer(
    repo_with_citation: Path,
) -> None:
    store_path = repo_with_citation / "graph.json"
    seed_store = FlatFileGraphStore(store_path)
    seed_store.reset()
    seed_store.upsert_node(_node())
    seed_store.upsert_node(
        _node(id="memory:project/other", citation="notes/kuzu-drop.md", text="Kuzu, unrelated note.")
    )
    seed_store.commit()

    result_one = answer("why did we drop Kuzu?", FlatFileGraphStore(store_path), repo_root=repo_with_citation)
    result_two = answer("why did we drop Kuzu?", FlatFileGraphStore(store_path), repo_root=repo_with_citation)

    assert result_one == result_two


def test_recall_makes_zero_network_calls(
    repo_with_citation: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = FlatFileGraphStore(repo_with_citation / "graph.json")
    store.reset()
    store.upsert_node(_node())
    store.commit()

    def _blocked_socket(*args, **kwargs):
        raise AssertionError("network socket construction attempted -- AD-6 violation")

    monkeypatch.setattr(socket, "socket", _blocked_socket)

    result = answer("why did we drop Kuzu?", FlatFileGraphStore(repo_with_citation / "graph.json"), repo_root=repo_with_citation)
    assert result.grounded is True
