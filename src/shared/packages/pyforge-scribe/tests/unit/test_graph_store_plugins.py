"""Unit tests for GraphStore CAP-18 plugins (Story 4.1).

Covers every I/O matrix row in
spec-4-1-register-graphstore-as-cap-18-plugins.md. An in-process
steward-owner double still proves compile/recall stay protocol-only;
the real PostgreSQL plugin is covered in test_graph_store_pg.py.
"""

from __future__ import annotations

import ast
import tomllib
from collections.abc import Iterator, MutableMapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from pyforge.core.hooks import (
    ENTRY_POINT_GROUP,
    HookSpec,
    PluginError,
    PluginRegistry,
    SecondVerdictError,
    publish_verdict,
)

from pyforge.scribe.capture import capture
from pyforge.scribe.compile import compile_graph
from pyforge.scribe.graph_store import (
    GRAPHSTORE_HOOK_SPEC,
    PG_GRAPHSTORE_OWNER,
    FlatFileGraphStore,
    FlatFileGraphStorePlugin,
    GraphStore,
)
from pyforge.scribe.graph_store_plugins import open_graph_store
from pyforge.scribe.models import GraphNode
from pyforge.scribe.recall import answer as recall_answer

_SCRIBE_ROOT = Path(__file__).resolve().parents[2]
_PYPROJECT = _SCRIBE_ROOT / "pyproject.toml"

_MEMORY_MD_STARTER = """# Team Memory Index

## Feedback

## Project

## Reference
"""


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


class _RecordingStore:
    """In-memory GraphStore stand-in used only as the steward-owner double."""

    def __init__(self, store_path: Path) -> None:
        self.store_path = store_path
        self._nodes: dict[str, GraphNode] = {}

    def reset(self) -> None:
        self._nodes = {}

    def upsert_node(self, node: GraphNode) -> None:
        self._nodes[node.id] = node

    def invalidate_edge(self, node_id: str, *, ended_at: datetime, superseded_by: str) -> None:
        existing = self._nodes[node_id]
        self._nodes[node_id] = existing.model_copy(update={"valid_until": ended_at, "superseded_by": superseded_by})

    def query_by_citation(self, citation: str) -> list[GraphNode]:
        return [n for n in self._nodes.values() if n.citation == citation]

    def iter_nodes(self) -> Iterator[GraphNode]:
        return iter(sorted(self._nodes.values(), key=lambda n: n.id))

    def commit(self) -> None:
        return None


class _StewardGraphStorePlugin:
    """Test double for the reserved steward (S-28.1) plugin slot -- not PG."""

    hook_spec: str = GRAPHSTORE_HOOK_SPEC.name
    owner: str = PG_GRAPHSTORE_OWNER

    def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
        if point == "around":
            context["store"] = _RecordingStore(context["store_path"])
        return context


def _scaffold_memory(repo_root: Path) -> Path:
    root = repo_root / ".claude" / "memory"
    (root / "feedback").mkdir(parents=True)
    (root / "MEMORY.md").write_text(_MEMORY_MD_STARTER, encoding="utf-8")
    return root


# --- Default plugin ----------------------------------------------------------


def test_default_plugin_returns_flatfile_at_given_path(tmp_path: Path) -> None:
    store_path = tmp_path / "graph.json"
    registry = PluginRegistry()
    store = open_graph_store(store_path, registry=registry)
    assert isinstance(store, FlatFileGraphStore)
    assert store.store_path == store_path
    store.reset()
    store.upsert_node(_node())
    store.commit()
    reopened = FlatFileGraphStore(store_path)
    assert [n.id for n in reopened.iter_nodes()] == ["memory:feedback/x"]


def test_default_plugin_compile_behaves_as_today(tmp_path: Path) -> None:
    memory_root = _scaffold_memory(tmp_path)
    store_path = tmp_path / "graph.json"
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store_path=store_path,
        transcript_root=tmp_path / "empty-transcripts",
    )
    assert result.store_path == store_path
    assert store_path.is_file()
    assert isinstance(json_load_nodes(store_path), dict)


def json_load_nodes(store_path: Path) -> dict:
    import json

    return json.loads(store_path.read_text(encoding="utf-8")).get("nodes", {})


def test_default_plugin_recall_reads_factory_store(tmp_path: Path) -> None:
    (tmp_path / ".claude" / "memory" / "feedback").mkdir(parents=True)
    cited = tmp_path / ".claude" / "memory" / "feedback" / "x.md"
    cited.write_text("body", encoding="utf-8")
    store = open_graph_store(tmp_path / "graph.json", registry=PluginRegistry())
    store.reset()
    store.upsert_node(_node())
    store.commit()
    result = recall_answer("captured text", store, repo_root=tmp_path)
    assert result.grounded is True
    assert result.citation == ".claude/memory/feedback/x.md"


# --- Reserved PG slot (test double) ------------------------------------------


def test_reserved_steward_slot_factory_selects_registered_double(tmp_path: Path) -> None:
    registry = PluginRegistry()
    registry.register(FlatFileGraphStorePlugin())
    registry.register(_StewardGraphStorePlugin())
    store = open_graph_store(
        tmp_path / "graph.json",
        registry=registry,
        owner=PG_GRAPHSTORE_OWNER,
    )
    assert isinstance(store, _RecordingStore)
    assert not isinstance(store, FlatFileGraphStore)


def test_reserved_steward_slot_compile_and_recall_use_protocol_only(tmp_path: Path) -> None:
    memory_root = _scaffold_memory(tmp_path)
    capture(memory_root, "feedback", "Always run tests first.")
    registry = PluginRegistry()
    registry.register(_StewardGraphStorePlugin())
    store = open_graph_store(
        tmp_path / "graph.json",
        registry=registry,
        owner=PG_GRAPHSTORE_OWNER,
    )
    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "empty-transcripts",
    )
    assert isinstance(store, _RecordingStore)
    assert any(n.kind == "memory" for n in store.iter_nodes())
    recall_answer("tests first", store, repo_root=tmp_path)


def test_unknown_owner_raises_plugin_error(tmp_path: Path) -> None:
    registry = PluginRegistry()
    registry.register(FlatFileGraphStorePlugin())
    with pytest.raises(PluginError, match="no graph-store plugin"):
        open_graph_store(tmp_path / "graph.json", registry=registry, owner="unknown")


def test_factory_source_has_no_engine_client_imports() -> None:
    path = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "scribe" / "graph_store_plugins.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert "psycopg" not in imported
    assert "pgvector" not in imported
    assert "sqlite3" not in imported


# --- Injected store ----------------------------------------------------------


def test_compile_without_store_calls_open_graph_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    memory_root = _scaffold_memory(tmp_path)
    store_path = tmp_path / "graph.json"
    calls: list[Path] = []
    real = open_graph_store

    def _spy(path: Path, **kwargs: object) -> GraphStore:
        calls.append(path)
        return real(path, **kwargs)

    monkeypatch.setattr("pyforge.scribe.graph_store_plugins.open_graph_store", _spy)
    compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store_path=store_path,
        transcript_root=tmp_path / "empty-transcripts",
    )
    assert calls == [store_path]


def test_recall_cmd_calls_open_graph_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from typer.testing import CliRunner

    from pyforge.scribe.cli import app

    monkeypatch.chdir(tmp_path)
    calls: list[Path] = []
    real = open_graph_store

    def _spy(path: Path, **kwargs: object) -> GraphStore:
        calls.append(path)
        return real(path, **kwargs)

    monkeypatch.setattr("pyforge.scribe.cli.open_graph_store", _spy)
    result = CliRunner().invoke(app, ["recall", "anything"])
    assert result.exit_code == 0
    assert calls == [tmp_path / ".claude" / "data" / "pyforge-scribe" / "graph.json"]


def test_plugin_around_without_store_path_raises_plugin_error() -> None:
    with pytest.raises(PluginError, match="store_path"):
        FlatFileGraphStorePlugin().call("around", {})


def test_injected_store_skips_plugin_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    memory_root = _scaffold_memory(tmp_path)
    store = FlatFileGraphStore(tmp_path / "injected.json")

    def _must_not_run(*_args: object, **_kwargs: object) -> GraphStore:
        raise AssertionError("open_graph_store must not run when store= is injected")

    monkeypatch.setattr("pyforge.scribe.graph_store_plugins.open_graph_store", _must_not_run)
    result = compile_graph(
        memory_root=memory_root,
        repo_root=tmp_path,
        store=store,
        transcript_root=tmp_path / "empty-transcripts",
    )
    assert result.store_path == store.store_path


# --- Second verdict ----------------------------------------------------------


def test_publish_verdict_for_unowned_warden_spec_raises() -> None:
    plugin = FlatFileGraphStorePlugin()
    warden_spec = HookSpec(name="pyforge.warden.gate", owner="warden")
    with pytest.raises(SecondVerdictError):
        publish_verdict(warden_spec, plugin, {"complete": True})


def test_steward_double_cannot_publish_scribe_owned_spec() -> None:
    plugin = _StewardGraphStorePlugin()
    with pytest.raises(SecondVerdictError):
        publish_verdict(GRAPHSTORE_HOOK_SPEC, plugin, {"complete": True})


# --- No competing gate -------------------------------------------------------


def test_factory_and_recall_do_not_publish_verdict_as_pr_gate(tmp_path: Path) -> None:
    (tmp_path / ".claude" / "memory" / "feedback").mkdir(parents=True)
    cited = tmp_path / ".claude" / "memory" / "feedback" / "x.md"
    cited.write_text("body", encoding="utf-8")
    with patch("pyforge.core.hooks.publish_verdict") as mocked:
        store = open_graph_store(tmp_path / "graph.json", registry=PluginRegistry())
        store.reset()
        store.upsert_node(_node())
        store.commit()
        recall_answer("captured text", store, repo_root=tmp_path)
        mocked.assert_not_called()


def test_factory_and_recall_source_never_call_publish_verdict() -> None:
    factory_src = (
        Path(__file__).resolve().parents[2] / "src" / "pyforge" / "scribe" / "graph_store_plugins.py"
    ).read_text(encoding="utf-8")
    recall_src = (Path(__file__).resolve().parents[2] / "src" / "pyforge" / "scribe" / "recall.py").read_text(
        encoding="utf-8"
    )
    cli_src = (Path(__file__).resolve().parents[2] / "src" / "pyforge" / "scribe" / "cli.py").read_text(
        encoding="utf-8"
    )
    compile_src = (Path(__file__).resolve().parents[2] / "src" / "pyforge" / "scribe" / "compile.py").read_text(
        encoding="utf-8"
    )
    graph_store_src = (Path(__file__).resolve().parents[2] / "src" / "pyforge" / "scribe" / "graph_store.py").read_text(
        encoding="utf-8"
    )
    assert "publish_verdict" not in factory_src
    assert "publish_verdict" not in recall_src
    assert "publish_verdict" not in cli_src
    assert "publish_verdict" not in compile_src
    assert "publish_verdict" not in graph_store_src


# --- Parallel group forbidden ------------------------------------------------


def test_pyproject_declares_flatfile_on_canonical_core_hooks_group_only() -> None:
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    groups = data["project"]["entry-points"]
    assert ENTRY_POINT_GROUP in groups
    assert groups[ENTRY_POINT_GROUP]["scribe-graphstore-flatfile"] == (
        "pyforge.scribe.graph_store:FlatFileGraphStorePlugin"
    )
    assert "pyforge.scribe.hooks" not in groups
    assert "pyforge.scribe.plugins" not in groups
    for key in groups:
        assert not key.startswith("pyforge.scribe."), key
    assert groups[ENTRY_POINT_GROUP]["scribe-graphstore-pg"] == (
        "pyforge.scribe.graph_store_pg:PostgresGraphStorePlugin"
    )


def test_hook_constants_reserve_steward_owner() -> None:
    assert GRAPHSTORE_HOOK_SPEC.name == "pyforge.scribe.graph_store"
    assert GRAPHSTORE_HOOK_SPEC.owner == "scribe"
    assert PG_GRAPHSTORE_OWNER == "steward"
    plugin = FlatFileGraphStorePlugin()
    assert plugin.hook_spec == GRAPHSTORE_HOOK_SPEC.name
    assert plugin.owner == "scribe"
