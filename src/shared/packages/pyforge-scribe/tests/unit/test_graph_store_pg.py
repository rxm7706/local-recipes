"""Durable PostgreSQL/pgvector GraphStore (Story 28.1) — isolation, concurrency, anti-JSON."""

from __future__ import annotations

import ast
import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pyforge.core.hooks import PluginError, PluginRegistry
from pyforge.scribe.graph_store import (
    GRAPHSTORE_HOOK_SPEC,
    PG_GRAPHSTORE_OWNER,
    FlatFileGraphStore,
    FlatFileGraphStorePlugin,
)
from pyforge.scribe.graph_store_pg import (
    SCRIBE_SCHEMA,
    PostgresGraphStore,
    PostgresGraphStorePlugin,
)
from pyforge.scribe.graph_store_plugins import open_graph_store
from pyforge.scribe.models import GraphNode

_SCRIBE_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = Path(__file__).resolve().parents[6]


def _node(node_id: str, text: str = "body") -> GraphNode:
    return GraphNode(
        id=node_id,
        kind="memory",
        title=node_id,
        text=text,
        citation=f".claude/memory/feedback/{node_id}.md",
        valid_from=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )


def test_postgres_commit_does_not_write_json_document(tmp_path: Path, pg_dsn: str) -> None:
    store_path = tmp_path / "graph.json"
    store = PostgresGraphStore(pg_dsn, store_path)
    store.reset()
    store.upsert_node(_node("memory:feedback/a"))
    store.commit()
    assert not store_path.is_file()
    assert not isinstance(store, FlatFileGraphStore)
    reopened = PostgresGraphStore(pg_dsn, store_path)
    assert [n.id for n in reopened.iter_nodes()] == ["memory:feedback/a"]


def test_durable_driver_is_not_flatfile_wrapper() -> None:
    src = (_SCRIBE_ROOT / "src" / "pyforge" / "scribe" / "graph_store_pg.py").read_text(
        encoding="utf-8"
    )
    assert "CREATE EXTENSION" in src
    assert "scribe_schema" in src
    assert "FlatFileGraphStore" not in src
    assert "json.dumps" not in src


def test_nodes_live_only_in_scribe_schema(tmp_path: Path, pg_dsn: str) -> None:
    import psycopg

    store = PostgresGraphStore(pg_dsn, tmp_path / "ignored")
    store.reset()
    store.upsert_node(_node("memory:feedback/iso"))
    store.commit()
    with psycopg.connect(pg_dsn) as conn:
        ext = conn.execute(
            "SELECT extname FROM pg_extension WHERE extname = 'vector'"
        ).fetchone()
        assert ext == ("vector",)
        schemas = conn.execute(
            """
            SELECT n.nspname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relname = 'graph_nodes' AND n.nspname NOT LIKE 'pg_%%'
            ORDER BY 1
            """
        ).fetchall()
        assert schemas == [(SCRIBE_SCHEMA,)]
        forbidden = conn.execute(
            """
            SELECT n.nspname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relname = 'graph_nodes'
              AND n.nspname IN ('public', 'langflow_schema', 'dbgpt_schema')
            """
        ).fetchall()
        assert forbidden == []


def test_concurrent_commits_do_not_corrupt_durable_store(tmp_path: Path, pg_dsn: str) -> None:
    path = tmp_path / "ignored"
    errors: list[BaseException] = []

    def _writer(node_id: str) -> None:
        try:
            store = PostgresGraphStore(pg_dsn, path)
            store.reset()
            store.upsert_node(_node(node_id, text=node_id))
            store.commit()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [
        threading.Thread(target=_writer, args=("memory:feedback/t0",)),
        threading.Thread(target=_writer, args=("memory:feedback/t1",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []

    final = list(PostgresGraphStore(pg_dsn, path).iter_nodes())
    ids = {node.id for node in final}
    assert ids in (
        {"memory:feedback/t0"},
        {"memory:feedback/t1"},
    )
    assert len(final) == 1
    assert all(node.text == node.id for node in final)


def test_steward_plugin_returns_postgres_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pg_dsn: str
) -> None:
    monkeypatch.setenv("SCRIBE_GRAPH_DSN", pg_dsn)
    registry = PluginRegistry()
    registry.register(FlatFileGraphStorePlugin())
    registry.register(PostgresGraphStorePlugin())
    store = open_graph_store(
        tmp_path / "graph.json",
        registry=registry,
        owner=PG_GRAPHSTORE_OWNER,
    )
    assert isinstance(store, PostgresGraphStore)
    assert not isinstance(store, FlatFileGraphStore)
    store.reset()
    store.upsert_node(_node("memory:feedback/plug"))
    store.commit()
    assert not (tmp_path / "graph.json").is_file()


def test_steward_plugin_without_dsn_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SCRIBE_GRAPH_DSN", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    registry = PluginRegistry()
    registry.register(PostgresGraphStorePlugin())
    with pytest.raises(PluginError, match="SCRIBE_GRAPH_DSN"):
        open_graph_store(
            tmp_path / "graph.json",
            registry=registry,
            owner=PG_GRAPHSTORE_OWNER,
        )


def test_callers_do_not_import_engine_or_postgres_adapter() -> None:
    forbidden = {"psycopg", "pgvector", "psycopg2"}
    adapter_name = "graph_store_pg"
    for rel in ("compile.py", "recall.py", "cli.py", "graph_store_plugins.py"):
        path = _SCRIBE_ROOT / "src" / "pyforge" / "scribe" / rel
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
                if "graph_store_pg" in node.module:
                    imported.add(adapter_name)
        assert forbidden.isdisjoint(imported), f"{rel} imports {imported & forbidden}"
        assert adapter_name not in imported, f"{rel} imports the PG adapter directly"


def test_compile_recall_cli_have_no_driver_isinstance_branch() -> None:
    for rel in ("compile.py", "recall.py", "cli.py"):
        src = (_SCRIBE_ROOT / "src" / "pyforge" / "scribe" / rel).read_text(encoding="utf-8")
        assert "PostgresGraphStore" not in src
        assert "isinstance(store" not in src


def test_no_pyforge_package_under_src_platform() -> None:
    platform = _REPO_ROOT / "src" / "platform"
    if not platform.is_dir():
        pytest.fail("src/platform must exist; refusing a vacuum pass")
    py_files = list(platform.rglob("*.py"))
    offenders: list[str] = []
    for path in py_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        if "graph_store_pg" in text or "PostgresGraphStore" in text:
            offenders.append(str(path.relative_to(_REPO_ROOT)))
    assert offenders == []
    # Adapter module itself must live in the scribe package, not platform.
    adapter = _SCRIBE_ROOT / "src" / "pyforge" / "scribe" / "graph_store_pg.py"
    assert adapter.is_file()
    assert "src/platform" not in adapter.as_posix()


def test_hook_constants_still_name_steward_owner() -> None:
    assert GRAPHSTORE_HOOK_SPEC.owner == "scribe"
    plugin = PostgresGraphStorePlugin()
    assert plugin.owner == PG_GRAPHSTORE_OWNER == "steward"
    assert plugin.hook_spec == GRAPHSTORE_HOOK_SPEC.name
