"""Builds Langflow's FastAPI app once, exported for `config/asgi.py`'s dispatcher.

Story 11.1 (spec-python-agent-platform CAP-2, AD-4/AD-14 Pattern A): Langflow
lives in-process as a mounted ASGI app, not a sidecar. `langflow.main.create_app()`
reads Langflow's own settings (`LANGFLOW_DATABASE_URL`, `LANGFLOW_CACHE_TYPE`,
`LANGFLOW_CONFIG_DIR`, `LANGFLOW_KNOWLEDGE_BASES_DIR`, ...) from the process
environment at call time via its own pydantic-settings service -- so this module
must be imported only AFTER Django's settings have executed and exported those
derived values into `os.environ` (`config/settings/base.py`). `config/asgi.py`
guarantees that ordering the same way it already does for
`config.fastapi_app`/`config.websocket`: it imports this module only after
`django_application = get_asgi_application()` has triggered `django.setup()`.

`create_app()` only constructs the FastAPI app object (routes, middleware, the
`lifespan` context manager) -- it does not open a database connection or run
Langflow's own Alembic migrations. Those happen when the ASGI server actually
sends this app a `lifespan.startup` message, which `config/asgi.py`'s dispatcher
drives explicitly alongside the platform's own FastAPI stub's lifespan (Design
Notes: "Dual-lifespan ASGI startup").

`_LifespanManager` (below) is the ONE shared, queue-driven ASGI
lifespan-protocol implementation, used by BOTH `config/asgi.py`'s dual-app
dispatch and this app's own tests (`langflow_integration/tests.py`) --
corrected here 2026-08-20 (spec's Spec Change Log) after a HIGH bug: a naive
single-shot `receive()` replay (returning the same hardcoded message on
every call) is broken, because Starlette's `Router.lifespan()` calls
`await receive()` TWICE per invocation -- once to start, once (after
sending `startup.complete`) purely as the "now shut down" gate -- and never
inspects that second message's `type`. A lone `_run_lifespan(app,
"startup")`-shaped call therefore runs an app's full startup AND its
shutdown teardown before returning, silently tearing down its DB/cache
services immediately after boot. `_LifespanManager` drives the protocol the
way a real ASGI server does instead: a long-lived task fed through a queue,
so `lifespan.shutdown` is only delivered when the caller actually wants
shutdown to happen.
"""

import asyncio
from typing import Self

from langflow.main import create_app

langflow_application = create_app()


class _LifespanManager:
    """Drive one ASGI app's lifespan protocol correctly (see module docstring).

    Async-context-manager usage (`async with _LifespanManager(app): ...`)
    keeps the app's services live for the duration of the `with` block and
    shuts down cleanly on exit -- used by `langflow_integration/tests.py`
    for both the schema-isolation check and the live flow-run test.
    `config/asgi.py`'s dual dispatch instead enters two instances (platform
    stub, then Langflow) into a shared `contextlib.AsyncExitStack`, since it
    needs to hold both open across two independent lifespan events
    (`lifespan.startup` now, `lifespan.shutdown` whenever the real server
    actually sends it) rather than a single `with` block's lifetime.
    """

    def __init__(self, app) -> None:
        self._app = app
        self._receive_queue: asyncio.Queue = asyncio.Queue()
        self._send_queue: asyncio.Queue = asyncio.Queue()
        self._task: asyncio.Task | None = None

    async def _receive(self):
        return await self._receive_queue.get()

    async def _send(self, message) -> None:
        await self._send_queue.put(message)

    async def __aenter__(self) -> Self:
        self._task = asyncio.create_task(
            self._app({"type": "lifespan"}, self._receive, self._send),
        )
        await self._receive_queue.put({"type": "lifespan.startup"})
        message = await self._send_queue.get()
        if message["type"] == "lifespan.startup.failed":
            msg = f"startup failed: {message.get('message')}"
            raise RuntimeError(msg)
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self._receive_queue.put({"type": "lifespan.shutdown"})
        message = await self._send_queue.get()
        if message["type"] == "lifespan.shutdown.failed":
            msg = f"shutdown failed: {message.get('message')}"
            raise RuntimeError(msg)
        await self._task
