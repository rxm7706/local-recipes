"""Durable PostgreSQL/pgvector GraphStore (Story 28.1) — isolation, concurrency, anti-JSON.

Story 41.3 (CAP-9 / red-team S-4) moved this driver's DDL into the governed
Liquibase changelog: the runtime path is assert-only and works as a DML-only
role.
"""

from __future__ import annotations

import ast
import re
import secrets
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import pytest
from pyforge.core.hooks import PluginError, PluginRegistry

from pyforge.scribe.graph_store import (
    GRAPHSTORE_HOOK_SPEC,
    PG_GRAPHSTORE_OWNER,
    FlatFileGraphStore,
    FlatFileGraphStorePlugin,
)
from pyforge.scribe.graph_store_pg import (
    GRANTS_CHANGESET_ID,
    GRAPH_CHANGESET_ID,
    SCRIBE_SCHEMA,
    GraphSchemaMissing,
    PostgresGraphStore,
    PostgresGraphStorePlugin,
)
from pyforge.scribe.graph_store_plugins import open_graph_store
from pyforge.scribe.models import GraphNode

_SCRIBE_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = Path(__file__).resolve().parents[6]
_ADAPTER = _SCRIBE_ROOT / "src" / "pyforge" / "scribe" / "graph_store_pg.py"
_DDL_STATEMENT = re.compile(
    r"\b(CREATE|ALTER|DROP|TRUNCATE)\s+"
    r"(EXTENSION|SCHEMA|TABLE|INDEX|VIEW|SEQUENCE|TYPE|ROLE)\b",
    re.IGNORECASE,
)


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
    src = _ADAPTER.read_text(encoding="utf-8")
    assert "scribe_schema" in src
    assert "FlatFileGraphStore" not in src
    assert "json.dumps" not in src


def test_driver_emits_no_ddl() -> None:
    """Story 41.3: the DML-only role cannot run DDL, so the driver has none."""
    src = _ADAPTER.read_text(encoding="utf-8")
    statements = [
        line.strip() for line in src.splitlines() if _DDL_STATEMENT.search(line) and not line.lstrip().startswith("#")
    ]
    assert statements == [], f"runtime DDL in the scribe driver: {statements}"
    assert "CREATE EXTENSION" not in src
    assert "to_regclass" in src, "the driver must assert the relation instead"
    assert GRAPH_CHANGESET_ID == "pyforge-scribe:2"
    assert GRANTS_CHANGESET_ID == "pyforge-scribe:3"


def test_nodes_live_only_in_scribe_schema(tmp_path: Path, pg_dsn: str) -> None:
    import psycopg

    store = PostgresGraphStore(pg_dsn, tmp_path / "ignored")
    store.reset()
    store.upsert_node(_node("memory:feedback/iso"))
    store.commit()
    with psycopg.connect(pg_dsn) as conn:
        ext = conn.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'").fetchone()
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


def test_absent_relation_raises_a_named_error(tmp_path: Path, pg_dsn: str) -> None:
    """Story 41.3: fail loudly and name the changeset, never create it."""
    absent = f"scribe_absent_{secrets.token_hex(4)}"
    with pytest.raises(GraphSchemaMissing) as error:
        PostgresGraphStore(pg_dsn, tmp_path / "ignored", schema=absent)
    message = str(error.value)
    assert absent in message
    assert GRAPH_CHANGESET_ID in message
    assert isinstance(error.value, PluginError)


def test_legacy_table_without_stale_is_back_filled_by_the_changeset(
    tmp_path: Path, pg_dsn: str, apply_changesets: Callable[[str], None]
) -> None:
    """`pyforge-scribe:4`: a pre-6.3 table has no `stale`, and `:2` is a no-op on it."""
    import psycopg
    from psycopg import sql

    table = sql.SQL("{}.{}").format(sql.Identifier(SCRIBE_SCHEMA), sql.Identifier("graph_nodes"))
    admin = psycopg.connect(pg_dsn)
    admin.autocommit = True
    try:
        admin.execute(sql.SQL("ALTER TABLE {} DROP COLUMN IF EXISTS stale").format(table))
        # Not vacuous: without :4 the driver cannot recover -- it holds DML
        # only, and `CREATE TABLE IF NOT EXISTS` does not add a column.
        with pytest.raises(psycopg.errors.UndefinedColumn):
            PostgresGraphStore(pg_dsn, tmp_path / "ignored")

        apply_changesets(pg_dsn)

        columns = [
            row[0]
            for row in admin.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = 'graph_nodes'",
                (SCRIBE_SCHEMA,),
            ).fetchall()
        ]
        assert "stale" in columns
        store = PostgresGraphStore(pg_dsn, tmp_path / "ignored")
        store.reset()
        store.upsert_node(_node("memory:feedback/back-filled"))
        store.commit()
        reopened = PostgresGraphStore(pg_dsn, tmp_path / "ignored")
        assert [n.stale for n in reopened.iter_nodes()] == [False]
    finally:
        admin.execute(
            sql.SQL("ALTER TABLE {} ADD COLUMN IF NOT EXISTS stale BOOLEAN NOT NULL DEFAULT FALSE").format(table)
        )
        admin.close()


def test_unreadable_schema_names_the_grants_changeset(tmp_path: Path, pg_dsn: str) -> None:
    """Finding 2: `to_regclass` RAISES on a privilege gap; `:3` is onFail:CONTINUE."""
    import psycopg
    from psycopg import sql

    role = f"scribe_nograntx_{secrets.token_hex(4)}"
    password = secrets.token_hex(8)
    role_ident = sql.Identifier(role)
    admin = psycopg.connect(pg_dsn)
    admin.autocommit = True
    try:
        admin.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(role_ident, sql.Literal(password)))
        try:
            # No USAGE on scribe_schema: exactly the state a database is left in
            # when platform_app is created after the first `liquibase update`.
            parsed = urlparse(pg_dsn)
            role_dsn = urlunparse(parsed._replace(netloc=f"{role}:{password}@{parsed.hostname}:{parsed.port or 5432}"))
            with pytest.raises(GraphSchemaMissing) as error:
                PostgresGraphStore(role_dsn, tmp_path / "ignored")
            message = str(error.value)
            assert GRANTS_CHANGESET_ID in message
            assert GRAPH_CHANGESET_ID not in message
        finally:
            admin.execute(sql.SQL("DROP OWNED BY {}").format(role_ident))
            admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(role_ident))
    finally:
        admin.close()


def test_store_works_as_a_ddl_revoked_role(tmp_path: Path, pg_dsn: str) -> None:
    """CAP-9: a role that provably cannot CREATE still reads and writes rows."""
    import psycopg
    from psycopg import sql
    from psycopg.errors import InsufficientPrivilege

    role = f"scribe_dml_{secrets.token_hex(4)}"
    password = secrets.token_hex(8)
    role_ident = sql.Identifier(role)
    admin = psycopg.connect(pg_dsn)
    admin.autocommit = True
    try:
        admin.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(role_ident, sql.Literal(password)))
        schema_ident = sql.Identifier(SCRIBE_SCHEMA)
        try:
            admin.execute(sql.SQL("REVOKE CREATE ON SCHEMA public FROM {}").format(role_ident))
            admin.execute(sql.SQL("REVOKE CREATE ON SCHEMA {} FROM {}").format(schema_ident, role_ident))
            admin.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(schema_ident, role_ident))
            admin.execute(
                sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {} TO {}").format(
                    schema_ident, role_ident
                )
            )

            parsed = urlparse(pg_dsn)
            role_dsn = urlunparse(parsed._replace(netloc=f"{role}:{password}@{parsed.hostname}:{parsed.port or 5432}"))

            # Not vacuous: this role really is refused DDL by PostgreSQL.
            probe = psycopg.connect(role_dsn)
            try:
                with pytest.raises(InsufficientPrivilege):
                    probe.execute(sql.SQL("CREATE TABLE {}.ddl_probe (id integer)").format(schema_ident))
            finally:
                probe.rollback()
                probe.close()

            store = PostgresGraphStore(role_dsn, tmp_path / "ignored")
            store.reset()
            store.upsert_node(_node("memory:feedback/dml-only"))
            store.commit()
            reopened = PostgresGraphStore(role_dsn, tmp_path / "ignored")
            assert [n.id for n in reopened.iter_nodes()] == ["memory:feedback/dml-only"]
        finally:
            admin.execute(sql.SQL("DROP OWNED BY {}").format(role_ident))
            admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(role_ident))
    finally:
        admin.close()


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


def test_steward_plugin_returns_postgres_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pg_dsn: str) -> None:
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
