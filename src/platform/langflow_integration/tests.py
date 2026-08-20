"""Story 11.1 -- schema-isolation proof (AD-5, "real not conventional").

Not just "does `langflow_schema` exist" -- drives Langflow's own ASGI
lifespan startup (its real Alembic bootstrap) against a real PostgreSQL and
asserts its tables land ONLY in `langflow_schema`, never `public`.
`manage.py migrate`'s own `RunSQL` schema-creation path (AC1) is exercised
separately, for real, as part of this story's manual verification -- see the
spec's "Manual checks" section; this test only needs the schema to exist
(idempotent either way) so it opens it directly.

Requires the `langflow` package (`python-agent-platform` conda env -- see
`tests/test_langflow_mount.py`'s module docstring for why this isn't the
pip-only CI `test` job) plus a real, reachable `DATABASE_URL`.

Deliberately does NOT go through `django.db.connection` (or the `db`/
`django_db` fixture that provisions it): any OTHER test in the same session
that used `@pytest.mark.django_db` already triggers pytest-django's
`django_db_setup`, which mutates `connections["default"].settings_dict
["NAME"]` to a "test_"-prefixed database for the REST OF THE PROCESS
(session-global, confirmed live -- order-dependent, so `django_db_blocker`
does not protect against a swap that already happened elsewhere). But
`LANGFLOW_DATABASE_URL` (`config/settings/base.py`) was derived once, as a
plain string, at settings-module load time -- never mutated afterward -- and
that is also exactly what Langflow's own engine connects to. Opening a
direct `psycopg` connection against that same string, instead of through
Django's mutable connection object, is what makes this test's two halves
(the schema check and Langflow's own bootstrap) provably agree on which
physical database they're looking at, regardless of test execution order.
"""

from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("langflow")

import psycopg
from django.conf import settings


async def _run_lifespan(app, event: str) -> None:
    """Replay a single lifespan event into `app` (mirrors config/asgi.py)."""
    sent = []

    async def receive():
        return {"type": f"lifespan.{event}"}

    async def send(message):
        sent.append(message)

    await app({"type": "lifespan"}, receive, send)
    if sent and sent[-1]["type"].endswith(".failed"):
        raise RuntimeError(sent[-1].get("message", f"{event} failed"))


# `LANGFLOW_DATABASE_URL`'s literal `?options=-c%20search_path=langflow_schema`
# suffix (spec-11-1's own contract) parses fine through SQLAlchemy's URL
# parser -- what Langflow's own engine actually uses -- but psycopg's OWN
# native URI parser is stricter and rejects the unescaped `=` inside the
# `options` value ("extra key/value separator '=' in URI query parameter"),
# verified live. Neither of these two connections needs `search_path` at
# all: both are schema-qualified already (`CREATE SCHEMA ...` / `WHERE
# schemaname IN (...)`), so the base DSN without the query string is both
# sufficient and sidesteps the parser mismatch entirely.
_TEST_DSN = settings.LANGFLOW_DATABASE_URL.split("?", 1)[0]


def _ensure_langflow_schema() -> None:
    with psycopg.connect(_TEST_DSN) as conn, conn.cursor() as cursor:
        cursor.execute("CREATE SCHEMA IF NOT EXISTS langflow_schema;")


def _fetch_pg_tables() -> list[tuple[str, str]]:
    with psycopg.connect(_TEST_DSN) as conn, conn.cursor() as cursor:
        cursor.execute(
            "SELECT schemaname, tablename FROM pg_tables "
            "WHERE schemaname IN ('public', 'langflow_schema')",
        )
        return cursor.fetchall()


async def _lifecycle() -> list[tuple[str, str]]:
    from langflow_integration.asgi import langflow_application  # noqa: PLC0415

    await _run_lifespan(langflow_application, "startup")
    try:
        # Django's sync DB-API cursor is `@async_unsafe`-guarded, and even a
        # plain psycopg connection opened directly from a running event loop
        # is bad practice -- `asyncio.to_thread` runs it in a plain OS thread
        # with no loop of its own.
        return await asyncio.to_thread(_fetch_pg_tables)
    finally:
        await _run_lifespan(langflow_application, "shutdown")


def test_langflow_schema_owns_langflows_tables_public_owns_none():
    _ensure_langflow_schema()
    rows = asyncio.run(_lifecycle())

    public_tables = {name for schema, name in rows if schema == "public"}
    langflow_tables = {name for schema, name in rows if schema == "langflow_schema"}

    assert langflow_tables, (
        "Langflow's own Alembic bootstrap created no tables in langflow_schema"
    )
    overlap = langflow_tables & public_tables
    assert not overlap, f"Langflow-owned tables leaked into public: {overlap}"
