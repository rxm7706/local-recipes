"""Story 11.2 (spec-python-agent-platform CAP-3, AD-17 Pattern B): a real
text-to-SQL round trip against the Story 10.5 DB-GPT sidecar's own REST API,
driven over Celery/Redis -- never an ASGI mount (see `dbgpt_integration/
apps.py` for why this app is migration-only).

Endpoint choice, investigated empirically against the installed
`dbgpt-sidecar` pixi environment's own `dbgpt_app`/`dbgpt_serve` packages
(not assumed from memory): the newer AgenticData router
(`dbgpt_app/openapi/api_v1/agentic_data_api.py`, mounted at `/api/v1/...`)
exposes skills/agent-file management and a full multi-turn ReAct-agent
endpoint (`/api/v1/chat/react-agent`) -- not a bare text-to-SQL
request/response. DB-GPT's classic "Chat" API
(`dbgpt_app/openapi/api_v1/api_v1.py`, mounted at `/api/...`) is what
actually takes a natural-language question against a registered datasource
and returns a generated SQL query plus its real result set, via its
`chat_with_db_execute` scene (`dbgpt_app/scene/chat_db/auto_execute/
chat.py`). Verified live end-to-end (2026-08-21) against a real local
`dbgpt start webserver` process, a real PostgreSQL datasource, and a real
Gemini-backed LLM (`proxy/openai` pointed at Google's OpenAI-compatible
endpoint): the round trip produced a real generated SQL statement and a
real, correct result set.

`POST /api/v1/chat/db/add` registers (or re-registers -- confirmed live,
idempotent: re-adding the same `db_name` succeeds with no error) the
datasource; `POST /api/v1/chat/completions` drives the actual chat turn.
Both are DB-GPT's OWN public REST surface -- nothing here imports
`dbgpt_app`/`dbgpt_serve` into this process (that is exactly the ASGI-mount
approach AD-14/AD-17 moved away from; see `config/asgi.py`'s own
registry-consult touchpoint).
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from html import unescape
from typing import Any

import httpx
from celery import shared_task
from django.conf import settings

from config.engine_patterns import get_sidecar_base_url

logger = logging.getLogger(__name__)

# `chat_with_db_execute`'s final answer embeds its SQL + real result rows as
# an HTML-entity-escaped JSON blob inside a `<chart-view content="...">` tag
# (`dbgpt_app/scene/chat_db/auto_execute/out_parser.py::parse_view_response`)
# -- verified live against a real response, not guessed from source alone.
_CHART_VIEW_CONTENT_RE = re.compile(r'<chart-view content="(?P<content>[^"]*)"\s*/?>')

_DEFAULT_MODEL_NAME = "gpt-4o"


class DbgptRequestError(RuntimeError):
    """A non-2xx sidecar response, or a response with no usable SQL/result
    payload -- surfaced, not silently swallowed (I/O & Edge-Case Matrix,
    spec-11-2: "Non-2xx sidecar response is surfaced, not silently
    swallowed"). Full timeout/partial-result/sidecar-unreachable handling is
    Story 11.3's own scope (CAP-4), not this one's (CAP-3) -- this is a bare,
    working call, per spec-11-2's Boundaries & Constraints.
    """


class DbgptSidecarUnreachableError(DbgptRequestError):
    """Story 11.3 (CAP-4): the sidecar itself never answered -- connection
    refused, DNS failure, or a connect timeout (`httpx.TransportError`),
    raised while OPENING or WRITING the request, as opposed to
    `DbgptRequestError`'s own non-2xx-response/malformed-body cases (which
    all require a response to have come back at all). A subclass, not a
    sibling `RuntimeError`, so any existing `except DbgptRequestError` site
    keeps working unmodified (Design Notes) while a caller that cares can
    `except DbgptSidecarUnreachableError` distinctly.
    """


def _json_or_raise(text: str, *, context: str) -> Any:
    """`json.loads`, with a malformed body surfaced as `DbgptRequestError`
    (this module's own documented contract) instead of a raw
    `json.JSONDecodeError` escaping to the Celery task's caller.
    """
    try:
        return json.loads(text)
    except ValueError as exc:
        msg = f"malformed JSON from sidecar ({context}): {text!r}"
        raise DbgptRequestError(msg) from exc


def _register_datasource(client: httpx.Client, db_name: str) -> None:
    """Register `db_name` (a real database in Django's OWN PostgreSQL,
    `DATABASES["default"]`) as a DB-GPT datasource. Idempotent -- see this
    module's docstring.
    """
    db = settings.DATABASES["default"]
    payload = {
        "db_name": db_name,
        "db_type": "postgresql",
        "db_host": db.get("HOST") or "localhost",
        "db_port": int(db.get("PORT") or 5432),
        "db_user": db.get("USER", ""),
        "db_pwd": db.get("PASSWORD", ""),
        "file_path": "",
        "comment": (
            "Story 11.2 (AD-17 Pattern B) -- Django's own PostgreSQL, "
            "registered for the text-to-SQL round trip."
        ),
    }
    try:
        response = client.post("/api/v1/chat/db/add", json=payload)
    except httpx.TransportError as exc:
        msg = f"dbgpt sidecar unreachable while registering datasource {db_name!r}: {exc}"
        raise DbgptSidecarUnreachableError(msg) from exc
    body = (
        _json_or_raise(response.text, context="db/add") if response.is_success else {}
    )
    if not response.is_success or not body.get("success"):
        msg = f"failed to register datasource {db_name!r}: {response.status_code}"
        logger.error(msg)
        raise DbgptRequestError(msg)
    logger.info("registered dbgpt datasource %r", db_name)


def _last_sse_data_line(body: str) -> str:
    """`chat_completions` streams `data: {...}\\n\\n` chunks where each chunk
    carries the FULL accumulated answer so far (verified live -- this scene
    is not token-incremental), so the last one is the complete, final turn.
    """
    lines = [line for line in body.splitlines() if line.startswith("data:")]
    if not lines:
        msg = f"no SSE data lines in sidecar response: {body!r}"
        raise DbgptRequestError(msg)
    return lines[-1][len("data:") :].strip()


def _extract_chart_view(content: str) -> dict[str, Any]:
    match = _CHART_VIEW_CONTENT_RE.search(content)
    if not match:
        msg = f"no <chart-view> payload in sidecar answer: {content!r}"
        raise DbgptRequestError(msg)
    return _json_or_raise(unescape(match.group("content")), context="chart-view")


# Story 11.3 (CAP-4): a per-task override, not a change to the global
# `CELERY_TASK_SOFT_TIME_LIMIT = 60` (`config/settings/base.py`) -- that
# default is an unedited cookiecutter-django placeholder other tasks may
# still rely on. This task's own client-side `httpx.Client(timeout=120.0)`
# below covers the `/api/v1/chat/completions` call alone; `soft_time_limit`
# needs headroom ABOVE that (the `/api/v1/chat/db/add` registration call and
# the network hop through `platform`->`dbgpt` both add on top of it), and
# `time_limit` (the hard `SIGKILL` bound) needs headroom above
# `soft_time_limit` so `SoftTimeLimitExceeded` has a real chance to be
# caught/logged before the process is killed outright.
@shared_task(soft_time_limit=130, time_limit=150)
def text_to_sql(
    user_input: str,
    db_name: str = "platform",
    conv_uid: str | None = None,
    model_name: str = _DEFAULT_MODEL_NAME,
) -> dict[str, Any]:
    """Real text-to-SQL round trip against the Story 10.5 DB-GPT sidecar.

    AD-17 (registry-driven): the sidecar's base URL is resolved from
    `config.engine_patterns.get_sidecar_base_url("dbgpt")`, never hardcoded
    -- flipping that registry entry is genuinely the only change a future
    revert would need.

    Args:
        user_input: the natural-language question.
        db_name: the DB-GPT datasource to query -- defaults to `"platform"`,
            Django's own database (see `compose.yml`'s `POSTGRES_DB`), so a
            zero-argument call queries real, already-existing tables (e.g.
            `django_migrations`).
        conv_uid: DB-GPT conversation id; a fresh one is minted if omitted.
        model_name: must match a `name` configured in the sidecar's own
            `[[models.llms]]` (`src/platform/compose/dbgpt/Containerfile`);
            the sidecar's own baked-in default is `"gpt-4o"`, overridable at
            `docker compose` time via `DBGPT_LLM_MODEL_NAME`.

    Returns:
        `{"sql": <generated SQL>, "data": <real result rows>}`.
    """
    base_url = get_sidecar_base_url("dbgpt")
    conv_uid = conv_uid or f"dbgpt-integration-{uuid.uuid4()}"
    logger.info("text_to_sql starting: db_name=%r conv_uid=%s", db_name, conv_uid)

    # 120s, not 60s: verified live (Story 11.2) that a real chat_with_db_execute
    # round trip -- schema-linking + an actual LLM generation -- took ~27s
    # end-to-end hitting the sidecar directly, and noticeably longer through
    # the extra platform->dbgpt network hop; 60s occasionally wasn't enough.
    # Still a bare client-side timeout, not the graduated timeout/retry
    # discipline that is Story 11.3's own scope (CAP-4).
    with httpx.Client(base_url=base_url, timeout=120.0) as client:
        _register_datasource(client, db_name)

        try:
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "conv_uid": conv_uid,
                    "chat_mode": "chat_with_db_execute",
                    "select_param": db_name,
                    "model_name": model_name,
                    "user_input": user_input,
                },
            )
        except httpx.TransportError as exc:
            msg = f"dbgpt sidecar unreachable during chat/completions: {exc}"
            raise DbgptSidecarUnreachableError(msg) from exc

    if not response.is_success:
        msg = f"sidecar returned {response.status_code}"
        logger.error(msg)
        raise DbgptRequestError(msg)

    final_chunk = _json_or_raise(
        _last_sse_data_line(response.text),
        context="chat/completions",
    )
    choices = final_chunk.get("choices") or []
    if not choices or "content" not in choices[0].get("message", {}):
        msg = f"no choices/message/content in sidecar answer: {final_chunk!r}"
        raise DbgptRequestError(msg)
    chart_view = _extract_chart_view(choices[0]["message"]["content"])

    logger.info("text_to_sql round trip complete for conv_uid=%s", conv_uid)
    return {"sql": chart_view.get("sql", ""), "data": chart_view.get("data", [])}
