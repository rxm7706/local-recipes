"""Steward 21.1: supervisor tables in public, replica-safe, no laptop scrape."""

from __future__ import annotations

import ast
import secrets
import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from django.db import connection
from django.db import connections
from django.db import transaction
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.operations.models import CreateModel
from django.db.utils import IntegrityError
from django.utils import timezone
from django_pyforge.models import McpHandle
from django_pyforge.models import RunState

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLATFORM_ROOT.parents[1]
CHROME_ROOT = (
    REPO_ROOT
    / "src"
    / "shared"
    / "packages"
    / "django-pyforge"
    / "src"
    / "django_pyforge"
)
FRONT_DOOR_ROOT = PLATFORM_ROOT / "platformapp" / "front_door"
MCP_URL_MODULES = (
    PLATFORM_ROOT / "config" / "urls.py",
    CHROME_ROOT / "urls.py",
)
LANGFLOW_SCHEMA_MIGRATION = (
    PLATFORM_ROOT
    / "langflow_integration"
    / "migrations"
    / "0001_create_langflow_schema.py"
)
DBGPT_SCHEMA_MIGRATION = (
    PLATFORM_ROOT / "dbgpt_integration" / "migrations" / "0001_create_dbgpt_schema.py"
)
ALLOWED_EXTRA_SCHEMAS = frozenset(
    {"langflow_schema", "dbgpt_schema", "liquibase"},
)
MISSING_HANDLE = "missing-handle-not-on-disk"
HANDLE_BYTES = 32
TTL_MINUTES = 5
SYSTEM_PG_PREFIX = "pg_"
INFORMATION_SCHEMA = "information_schema"


def _opaque_handle() -> str:
    return secrets.token_urlsafe(HANDLE_BYTES)


def _expires_at():
    return timezone.now() + timedelta(minutes=TTL_MINUTES)


@pytest.mark.django_db
def test_run_state_and_mcp_handles_exist_in_default_schema() -> None:
    table_names = set(connection.introspection.table_names())
    assert RunState._meta.db_table == "run_state"  # noqa: SLF001
    assert McpHandle._meta.db_table == "mcp_handles"  # noqa: SLF001
    assert "run_state" in table_names
    assert "mcp_handles" in table_names
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_schema
                FROM information_schema.tables
                WHERE table_name IN ('run_state', 'mcp_handles')
                """,
            )
            schemas = {row[0] for row in cursor.fetchall()}
        assert schemas == {"public"}


@pytest.mark.django_db
def test_django_pyforge_migrations_are_createmodel_only() -> None:
    loader = MigrationLoader(connection)
    found = False
    for (app_label, _name), migration in loader.disk_migrations.items():
        if app_label != "django_pyforge":
            continue
        found = True
        for operation in migration.operations:
            assert isinstance(operation, CreateModel)
            assert operation.name in {"RunState", "McpHandle"}
            sql = str(operation).upper()
            assert "CREATE SCHEMA" not in sql
    assert found


@pytest.mark.django_db(transaction=True)
def test_handle_points_at_run_and_missing_run_raises() -> None:
    run = RunState.objects.create()
    token = _opaque_handle()
    handle = McpHandle.objects.create(
        handle=token,
        run=run,
        expires_at=_expires_at(),
    )
    assert handle.run_id == run.id
    assert McpHandle.objects.get(handle=token).run == run
    assert list(run.handles.all()) == [handle]
    with pytest.raises(IntegrityError), transaction.atomic():
        McpHandle.objects.create(
            handle=_opaque_handle(),
            run_id=uuid.uuid4(),
            expires_at=_expires_at(),
        )


@pytest.mark.django_db(transaction=True)
def test_second_connection_reads_the_same_handle_row() -> None:
    run = RunState.objects.create(status=RunState.Status.RUNNING)
    token = _opaque_handle()
    McpHandle.objects.create(handle=token, run=run, expires_at=_expires_at())
    replica = connections.create_connection("default")
    try:
        handles = replica.ops.quote_name("mcp_handles")
        runs = replica.ops.quote_name("run_state")
        with replica.cursor() as cursor:
            cursor.execute(
                f"SELECT handle, run_id FROM {handles} WHERE handle = %s",  # noqa: S608
                [token],
            )
            row = cursor.fetchone()
            cursor.execute(
                f"SELECT id FROM {runs} WHERE id = %s",  # noqa: S608
                [run.id],
            )
            run_row = cursor.fetchone()
        assert row is not None
        assert row[0] == token
        assert str(row[1]) == str(run.id)
        assert run_row is not None
        assert str(run_row[0]) == str(run.id)
    finally:
        replica.close()
    with pytest.raises(McpHandle.DoesNotExist):
        McpHandle.objects.get(handle=MISSING_HANDLE)


def _iter_python_files() -> list[Path]:
    files: list[Path] = []
    for root in (FRONT_DOOR_ROOT, CHROME_ROOT):
        files.extend(path for path in root.rglob("*.py") if path.is_file())
    files.extend(path for path in MCP_URL_MODULES if path.is_file())
    return files


def _literal_values(node: ast.AST) -> list[str]:
    values: list[str] = []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        values.append(node.value)
    elif isinstance(node, ast.JoinedStr):
        values.extend(
            part.value
            for part in node.values
            if isinstance(part, ast.Constant) and isinstance(part.value, str)
        )
    return values


def _is_path_home(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "home"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "Path"
    )


def _join_parts(node: ast.AST) -> list[str]:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return [*_join_parts(node.left), *_literal_values(node.right)]
    return _literal_values(node)


def _is_path_scrape_literal(literal: str) -> bool:
    lowered = literal.lower()
    if "bmad-loops" in lowered:
        return True
    pathish = "/" in literal or "~" in literal or "\\" in literal
    if not pathish:
        return False
    return "tmux" in lowered or "journal" in lowered


def _scrape_hits_in_tree(path: Path, tree: ast.AST) -> list[str]:
    hits: list[str] = []
    for node in ast.walk(tree):
        hits.extend(
            f"{path}: {literal!r}"
            for literal in _literal_values(node)
            if _is_path_scrape_literal(literal)
        )
        expand = (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "expanduser"
        )
        if expand:
            hits.extend(
                f"{path}: expanduser({literal!r})"
                for literal in _literal_values(node)
                if _is_path_scrape_literal(literal)
            )
        home_loops = (
            isinstance(node, ast.BinOp)
            and isinstance(node.op, ast.Div)
            and _is_path_home(node.left)
            and any("bmad-loops" in part.lower() for part in _join_parts(node))
        )
        if home_loops:
            hits.append(f"{path}: Path.home()/bmad-loops")
    return hits


def test_front_door_chrome_and_mcp_urls_do_not_scrape_laptop_state() -> None:
    files = _iter_python_files()
    assert files, "scrape roots must yield python files"
    assert any("front_door" in str(path) for path in files)
    hits: list[str] = []
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        hits.extend(_scrape_hits_in_tree(path, tree))
    assert hits == []


def test_supervisor_migrations_do_not_create_a_fifth_schema() -> None:
    chrome_migrations = CHROME_ROOT / "migrations"
    for path in chrome_migrations.glob("*.py"):
        if path.name == "__init__.py":
            continue
        source = path.read_text(encoding="utf-8")
        assert "CREATE SCHEMA" not in source.upper()
    assert LANGFLOW_SCHEMA_MIGRATION.is_file()
    assert DBGPT_SCHEMA_MIGRATION.is_file()
    langflow = LANGFLOW_SCHEMA_MIGRATION.read_text(encoding="utf-8")
    dbgpt = DBGPT_SCHEMA_MIGRATION.read_text(encoding="utf-8")
    assert "CREATE SCHEMA IF NOT EXISTS langflow_schema" in langflow
    assert "CREATE SCHEMA IF NOT EXISTS dbgpt_schema" in dbgpt


@pytest.mark.django_db
def test_postgres_has_no_supervisor_schema() -> None:
    if connection.vendor != "postgresql":
        pytest.skip("schema catalog is PostgreSQL-only")
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT nspname FROM pg_namespace
            WHERE nspname NOT LIKE %s AND nspname <> %s
            """,
            [f"{SYSTEM_PG_PREFIX}%", INFORMATION_SCHEMA],
        )
        names = {row[0] for row in cursor.fetchall()}
    extra = names - {"public"} - ALLOWED_EXTRA_SCHEMAS
    assert "run_state" not in names
    assert "mcp_handles" not in names
    assert extra == set()
