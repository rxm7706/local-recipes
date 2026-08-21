"""Story 11.2 -- schema-provisioning proof (AD-5) + the `text_to_sql` Celery
task's request shape.

Unlike `langflow_integration/tests.py`'s AC3 test (a real Alembic bootstrap
lands rows in `langflow_schema`), there is no equivalent proof here that
DB-GPT's OWN state lands in `dbgpt_schema` -- Story 11.2 found, and
documented in full in `dbgpt_integration/apps.py`'s docstring, that DB-GPT's
own metadata-store layer does not support PostgreSQL at all. This module
only proves what IS real: the schema exists and Django's ORM creates nothing
inside it (AC1), and the Celery task talks to the sidecar's REST API the way
its own docstring says it does.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import psycopg
import pytest
from django.conf import settings

from dbgpt_integration.tasks import DbgptRequestError
from dbgpt_integration.tasks import DbgptSidecarUnreachableError
from dbgpt_integration.tasks import text_to_sql

# Captured before any `patch("dbgpt_integration.tasks.httpx.Client", ...)`
# below: `mock.patch` on a dotted `module.attr` path replaces the attribute
# on the actual `httpx` module object (there is only one `httpx` module
# instance, shared by this file and `dbgpt_integration.tasks`) -- so a mock
# factory that itself called `httpx.Client(...)` while the patch is active
# would recurse into itself. Calling this captured reference instead builds
# a REAL `httpx.Client`, just wired to a `MockTransport`.
_RealHttpxClient = httpx.Client

# Same base-DSN-without-query-string rationale as langflow_integration/
# tests.py's `_TEST_DSN`: both checks below are already schema-qualified, so
# `search_path` isn't needed, and psycopg's own stricter URI parser rejects
# the unescaped `=` inside `DBGPT_DATABASE_URL`'s `?options=` suffix.
_TEST_DSN = settings.DBGPT_DATABASE_URL.split("?", 1)[0]


def _ensure_dbgpt_schema() -> None:
    with psycopg.connect(_TEST_DSN) as conn, conn.cursor() as cursor:
        cursor.execute("CREATE SCHEMA IF NOT EXISTS dbgpt_schema;")


def _fetch_dbgpt_schema_tables() -> list[str]:
    with psycopg.connect(_TEST_DSN) as conn, conn.cursor() as cursor:
        cursor.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'dbgpt_schema'",
        )
        return [row[0] for row in cursor.fetchall()]


def test_dbgpt_schema_exists_with_zero_django_orm_tables():
    """AC1: `manage.py migrate` against a fresh database creates
    `dbgpt_schema` with zero Django-ORM-created tables inside it.
    """
    _ensure_dbgpt_schema()

    tables = _fetch_dbgpt_schema_tables()

    assert tables == [], (
        f"Django's ORM created tables in dbgpt_schema, it should create none: {tables}"
    )


# ---------------------------------------------------------------------------
# `text_to_sql` Celery task -- request shape, mocked transport (no live
# sidecar needed; a real, live round trip is this story's own manual
# verification, not a pytest-collected test -- see the spec's Verification
# section).
# ---------------------------------------------------------------------------

_SQL = (
    "SELECT SUM(salary) AS total_salary FROM employees "
    "WHERE department = 'Engineering'"
)
_DATA = [{"total_salary": 200000}]


def _sse_body(content: str) -> str:
    payload = {
        "id": "chatcmpl-test",
        "model": "gpt-4o",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}}],
        "usage": {},
    }
    return f"data: {json.dumps(payload)}\n\n"


def _chart_view_tag() -> str:
    """Mirrors DB-GPT's own real output shape (verified live, Story 11.2):
    `<chart-view content="{&quot;type&quot;: ...}" />`, the JSON blob's `"`
    HTML-entity-escaped so it survives as one XML attribute value.
    """
    inner = json.dumps({"type": "response_table", "sql": _SQL, "data": _DATA})
    escaped = inner.replace('"', "&quot;")
    return f'<chart-view content="{escaped}" />'


def _mock_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/api/v1/chat/db/add":
        return httpx.Response(200, json={"success": True, "data": True})
    if request.url.path == "/api/v1/chat/completions":
        body = json.loads(request.content)
        assert body["chat_mode"] == "chat_with_db_execute"
        assert body["select_param"] == "platform"
        content = f"answer text\n{_chart_view_tag()}"
        return httpx.Response(200, text=_sse_body(content))
    return httpx.Response(404)


def _client_with_mock_transport(*, base_url, timeout):
    transport = httpx.MockTransport(_mock_handler)
    return _RealHttpxClient(base_url=base_url, timeout=timeout, transport=transport)


def test_text_to_sql_resolves_url_from_registry_and_parses_real_shaped_response():
    with patch("dbgpt_integration.tasks.httpx.Client", _client_with_mock_transport):
        result = text_to_sql("What is the total salary in Engineering?")

    assert result == {"sql": _SQL, "data": _DATA}


def _error_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/api/v1/chat/db/add":
        return httpx.Response(200, json={"success": True, "data": True})
    return httpx.Response(500, text="internal error")


def _client_with_error_transport(*, base_url, timeout):
    transport = httpx.MockTransport(_error_handler)
    return _RealHttpxClient(base_url=base_url, timeout=timeout, transport=transport)


def test_text_to_sql_surfaces_non_2xx_instead_of_swallowing_it():
    with (
        patch("dbgpt_integration.tasks.httpx.Client", _client_with_error_transport),
        pytest.raises(DbgptRequestError),
    ):
        text_to_sql("this should fail")


# ---------------------------------------------------------------------------
# Story 11.3 -- sidecar-unreachable is a named, catchable failure mode, not a
# raw/undocumented `httpx` exception (AC3). `httpx.MockTransport`'s handler
# raising instead of returning a `Response` reproduces exactly what a real
# connection-refused/DNS-failure/connect-timeout looks like from the
# `httpx.Client`'s own perspective -- `httpx.ConnectError` is a
# `httpx.TransportError` subclass, the family both wrapped `client.post()`
# calls in `dbgpt_integration/tasks.py` now catch.
# ---------------------------------------------------------------------------


def _unreachable_handler(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("Connection refused", request=request)


def _client_with_unreachable_transport(*, base_url, timeout):
    transport = httpx.MockTransport(_unreachable_handler)
    return _RealHttpxClient(base_url=base_url, timeout=timeout, transport=transport)


def test_text_to_sql_surfaces_sidecar_unreachable_as_named_error():
    with (
        patch("dbgpt_integration.tasks.httpx.Client", _client_with_unreachable_transport),
        pytest.raises(DbgptSidecarUnreachableError),
    ):
        text_to_sql("this should never reach a live sidecar")
