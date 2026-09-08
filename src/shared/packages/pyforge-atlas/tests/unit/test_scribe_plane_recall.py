"""Steward 34.5: scribe semantic recall on the plane (FR-50)."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[6]
SCRIBE_SRC = REPO_ROOT / "src" / "shared" / "packages" / "pyforge-scribe" / "src"
if str(SCRIBE_SRC) not in sys.path:
    sys.path.insert(0, str(SCRIBE_SRC))

from pyforge.scribe.graph_store import FlatFileGraphStore  # noqa: E402
from pyforge.scribe.graph_store_plane import PlaneGraphStore  # noqa: E402
from pyforge.scribe.models import GraphNode  # noqa: E402
from pyforge.scribe.recall import answer  # noqa: E402


def _node(node_id: str, text: str, citation: str) -> GraphNode:
    return GraphNode(
        id=node_id,
        kind="memory",
        title=node_id.rsplit("/", 1)[-1],
        text=text,
        citation=citation,
        valid_from=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )


@pytest.fixture()
def cited_repo(tmp_path: Path) -> Path:
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "dog.md").write_text("the family dog", encoding="utf-8")
    (notes / "physics.md").write_text("unrelated", encoding="utf-8")
    return tmp_path


def test_semantic_recall_on_plane_hits_no_overlap(tmp_path: Path, cited_repo: Path) -> None:
    plane = tmp_path / "atlas.duckdb"
    store = PlaneGraphStore(plane, tmp_path / "graph.json")
    try:
        store.reset()
        store.upsert_node(_node("memory:project/dog", "dog", "notes/dog.md"))
        store.upsert_node(
            _node(
                "memory:project/physics",
                "quantum chromodynamics scattering amplitudes",
                "notes/physics.md",
            )
        )
        store.commit()
        lexical = answer("canine", store, repo_root=cited_repo, mode="lexical")
        semantic = answer("canine", store, repo_root=cited_repo, mode="semantic")
        assert lexical.grounded is False
        assert semantic.grounded is True
        assert semantic.node_id == "memory:project/dog"
        assert semantic.citation == "notes/dog.md"
    finally:
        store.close()


def test_lexical_recall_unchanged_on_flatfile(cited_repo: Path) -> None:
    store = FlatFileGraphStore(cited_repo / "graph.json")
    store.reset()
    store.upsert_node(_node("memory:project/dog", "dog", "notes/dog.md"))
    store.commit()
    hit = answer("dog", store, repo_root=cited_repo, mode="lexical")
    miss = answer("canine", store, repo_root=cited_repo, mode="lexical")
    assert hit.grounded is True
    assert miss.grounded is False
