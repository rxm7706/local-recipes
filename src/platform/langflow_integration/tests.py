"""Story 11.1 -- schema-isolation proof (AD-5, "real not conventional").

Not just "does `langflow_schema` exist" -- drives Langflow's own ASGI
lifespan startup (its real Alembic bootstrap) against a real PostgreSQL and
asserts its tables land ONLY in `langflow_schema`, never `public`.
`manage.py migrate`'s own `RunSQL` schema-creation path (AC1) is exercised
separately, for real, as part of this story's manual verification -- see the
spec's "Manual checks" section; this test only needs the schema to exist
(idempotent either way) so it opens it directly.

AC3 (a flow executed end-to-end through the mounted app writes every row
into `langflow_schema` only) is proven below by
`test_run_flow_writes_land_only_in_langflow_schema`: a real
`POST /api/v1/run/<flow-id>` call against a deterministic, LLM-free
TextInput->TextOutput flow, then a row-level check of what it wrote.

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
from http import HTTPStatus

import pytest

pytest.importorskip("langflow")

import psycopg
from django.conf import settings

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
    from langflow_integration.asgi import _LifespanManager  # noqa: PLC0415
    from langflow_integration.asgi import langflow_application  # noqa: PLC0415

    async with _LifespanManager(langflow_application):
        # Django's sync DB-API cursor is `@async_unsafe`-guarded, and even a
        # plain psycopg connection opened directly from a running event loop
        # is bad practice -- `asyncio.to_thread` runs it in a plain OS thread
        # with no loop of its own.
        return await asyncio.to_thread(_fetch_pg_tables)


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


# ---------------------------------------------------------------------------
# AC3 -- a real POST /api/v1/run/<flow-id> write-path, schema-isolated
# ---------------------------------------------------------------------------
#
# A single call per lifespan event (what `_lifecycle()` above also used to
# do, before sharing `_LifespanManager` below) is fine for the
# schema-existence check but fatal here: Starlette's own ASGI lifespan
# handler calls `receive()` TWICE per invocation -- once to start, once
# (after sending `startup.complete`) purely as the trigger to run the
# `@asynccontextmanager`'s post-`yield` cleanup -- and does NOT check that
# second message's type. A naive single-shot replay of the SAME hardcoded
# message therefore runs Langflow's full startup AND its shutdown teardown
# before returning (verified live: the console shows "Stopping Server" /
# "Cleaning Up Services" immediately after startup, and a subsequent request
# fails with `NoFactoryRegisteredError: ... 'DATABASE_SERVICE'` -- the DB
# service was already torn down). This was originally fixed only here, then
# back-ported to `config/asgi.py`'s production dispatcher and to
# `_lifecycle()` above as the SAME shared `_LifespanManager`
# (`langflow_integration.asgi`) 2026-08-20 -- see the spec's Spec Change Log.
# `_LifespanManager` drives the protocol the way a real ASGI server does:
# one long-lived task fed `lifespan.startup` now and `lifespan.shutdown`
# only when the caller is done, via a queue, so Langflow's services stay up
# for the whole `async with` block.


def _build_text_only_flow_data(seed_text: str) -> dict:
    """A deterministic, zero-external-dependency flow: no LLM/API key needed.

    `TextInputComponent` -> `TextOutputComponent` (`lfx.components.input_output`)
    is a plain pass-through -- proving the write path this AC cares about
    doesn't require a live model endpoint (AD-16's local-first posture).
    """
    from lfx.components.input_output.text import TextInputComponent  # noqa: PLC0415
    from lfx.components.input_output.text_output import (  # noqa: PLC0415
        TextOutputComponent,
    )
    from lfx.graph import Graph  # noqa: PLC0415

    text_input = TextInputComponent()
    text_input.set(input_value=seed_text)
    text_output = TextOutputComponent()
    text_output.set(input_value=text_input.text_response)

    graph = Graph(start=text_input, end=text_output)
    return graph.dump(name="ac3-schema-isolation-probe")["data"]


async def _run_flow_over_http() -> str:
    """Drive a real `/api/v1/run/<flow-id>` call through Langflow's own ASGI
    app and return the flow id, so the caller can inspect what it wrote.

    Auth: `LANGFLOW_AUTO_LOGIN` defaults to `True` (dev-mode bootstrap), so
    `GET /api/v1/auto_login` mints a real bearer token for the default
    superuser with no password needed -- used to create the flow and mint a
    real API key, which is what `/api/v1/run/<flow-id>` itself requires
    (it's API-key-secured, a different dependency than the cookie/bearer
    session auth the rest of the API uses).
    """
    from httpx import ASGITransport  # noqa: PLC0415
    from httpx import AsyncClient  # noqa: PLC0415

    from langflow_integration.asgi import _LifespanManager  # noqa: PLC0415
    from langflow_integration.asgi import langflow_application  # noqa: PLC0415

    seed_text = "AC3 schema-isolation probe"
    async with _LifespanManager(langflow_application):
        transport = ASGITransport(app=langflow_application)
        base_url = "http://testserver"
        async with AsyncClient(transport=transport, base_url=base_url) as client:
            login = await client.get("/api/v1/auto_login")
            assert login.status_code == HTTPStatus.OK, login.text
            access_token = login.json()["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}

            flow_data = _build_text_only_flow_data(seed_text)
            created = await client.post(
                "/api/v1/flows/",
                json={"name": "ac3-schema-isolation-probe", "data": flow_data},
                headers=headers,
            )
            assert created.status_code == HTTPStatus.CREATED, created.text
            flow_id = created.json()["id"]

            key_resp = await client.post(
                "/api/v1/api_key/",
                json={"name": "ac3-schema-isolation-probe-key"},
                headers=headers,
            )
            assert key_resp.status_code == HTTPStatus.OK, key_resp.text
            api_key = key_resp.json()["api_key"]

            run_payload = {
                "input_value": seed_text,
                "input_type": "text",
                "output_type": "text",
            }
            run_resp = await client.post(
                f"/api/v1/run/{flow_id}",
                json=run_payload,
                headers={"x-api-key": api_key},
            )
            assert run_resp.status_code == HTTPStatus.OK, run_resp.text
            first_output = run_resp.json()["outputs"][0]["outputs"][0]
            assert first_output["outputs"]["text"]["message"] == seed_text

    return flow_id


def _fetch_flow_write_path_rows(flow_id: str) -> dict[str, int]:
    """Count the rows this flow's run wrote, per `langflow_schema` table."""
    queries = {
        "flow": "SELECT count(*) FROM langflow_schema.flow WHERE id = %s",
        "vertex_build": (
            "SELECT count(*) FROM langflow_schema.vertex_build WHERE flow_id = %s"
        ),
        "transaction": (
            "SELECT count(*) FROM langflow_schema.transaction WHERE flow_id = %s"
        ),
    }
    with psycopg.connect(_TEST_DSN) as conn, conn.cursor() as cursor:
        counts = {}
        for table, query in queries.items():
            cursor.execute(query, (flow_id,))
            counts[table] = cursor.fetchone()[0]
        return counts


def test_run_flow_writes_land_only_in_langflow_schema():
    """AC3: a flow executed end-to-end through `POST /api/v1/run/<flow-id>`
    writes every row it produces into `langflow_schema`, never `public`.
    """
    _ensure_langflow_schema()
    # `asyncio.run` returns to plain sync code once it completes, so the
    # DB checks below (unlike `_lifecycle`'s) run with no event loop active --
    # no `asyncio.to_thread` needed for the psycopg calls that follow.
    flow_id = asyncio.run(_run_flow_over_http())

    counts = _fetch_flow_write_path_rows(flow_id)
    assert counts["flow"] == 1, (
        "the run's own flow row is missing from langflow_schema.flow"
    )
    assert counts["vertex_build"] >= 1, (
        "no vertex_build rows in langflow_schema -- the flow didn't actually execute"
    )
    assert counts["transaction"] >= 1, (
        "no transaction rows in langflow_schema -- the flow didn't actually execute"
    )

    # Same schema-ownership check as the test above, re-affirmed after a live
    # write (not just after Alembic's own bootstrap DDL): still zero overlap.
    rows = _fetch_pg_tables()
    public_tables = {name for schema, name in rows if schema == "public"}
    langflow_tables = {name for schema, name in rows if schema == "langflow_schema"}
    assert not (langflow_tables & public_tables)
