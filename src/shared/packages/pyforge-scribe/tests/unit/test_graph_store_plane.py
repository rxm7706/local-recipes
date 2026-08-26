"""Steward 34.5: plane GraphStore refusals (FR-50) — no duckdb required."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from pyforge.core.hooks import PluginError
from pyforge.scribe.graph_store_plane import PlaneGraphStore
from pyforge.scribe.graph_store_plane import PlaneGraphStorePlugin
from pyforge.scribe.recall import _answer_semantic
from pyforge.scribe.recall import answer


def test_chroma_and_memory_paths_fail(tmp_path: Path) -> None:
    with pytest.raises(PluginError, match="atlas.duckdb"):
        PlaneGraphStore(tmp_path / "chroma.sqlite3", tmp_path / "graph.json")
    plugin = PlaneGraphStorePlugin()
    with pytest.raises(PluginError, match="Chroma"):
        plugin.call(
            "around",
            {"store_path": tmp_path / "g.json", "plane_path": tmp_path / "chroma"},
        )


def test_recall_callers_do_not_isinstance_the_driver() -> None:
    recall = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "scribe" / "recall.py"
    tree = ast.parse(recall.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = getattr(func, "id", None) or getattr(func, "attr", None)
            assert name != "isinstance"
    assert "query_similar" in answer.__code__.co_names or "query_similar" in (
        _answer_semantic.__code__.co_names
    )
