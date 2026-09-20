"""ASGI host wiring for ``webhook.py`` (Story 13.6): a stable,
daphne-pointable ``application`` object, plus the bounded timeout and
dedicated executor DW-FU-13-4-3 named as whoever mounts ``webhook.py``'s
job to add. Neither existed anywhere before this module -- ``webhook.py``
(Story 13.4) and ``scheduler.py`` (Story 13.5) were both built and fully
unit-tested but never run as a real, listening process; this module (plus
``.github/workflows/herald-live-demo.yml``) is what actually starts one.

**Why a separate module, not more of webhook.py.** AD-8 (Steward's
``spec-secure-live-dashboards`` architecture: "the library binds at the ASGI
application boundary ... no adopter may be asked to change frameworks to
adopt") requires ``webhook.py`` to stay a zero-framework-dependency ASGI3
callable -- Boundaries & Constraints' explicit "Never": add Django/Channels
to ``pyforge-herald``'s own dependencies, or change ``webhook.py``'s shape
away from a plain ASGI3 callable. Only this module and the new
``webhook-host`` optional extra (``pyproject.toml``) know that ``daphne``
exists; this module itself never imports it either -- daphne is a
*process*, invoked from the command line as ``daphne
pyforge.herald.webhook_host:application``, and resolves that target the
same way any WSGI/ASGI ``module:variable`` convention does (gunicorn,
uvicorn, Django's own generated ``asgi.py``): ``importlib.import_module``
the module, then ``getattr`` the named attribute.

**``application`` is built lazily, on first attribute access, not at plain
import time.** ``webhook.resolve_webhook_secret()`` raises
``errors.HeraldError`` when ``HERALD_WEBHOOK_SECRET`` is unset -- exactly
the fail-fast behavior a real deployment wants (daphne dies loudly at
startup rather than quietly answering every request with a 500), but
exactly the behavior a plain ``import pyforge.herald.webhook_host`` must
NOT have: ``tests/test_bridge.py``'s bridge-core determinism sweep (Story
13.4/13.5 precedent) imports every bridge-core module by name to enumerate
the package, and this repo's own test suite must stay green with no
``HERALD_WEBHOOK_SECRET``/``HERALD_REPO_ROOT`` configured anywhere. A
module-level ``__getattr__`` (PEP 562) resolves the tension: ``import
pyforge.herald.webhook_host`` alone never touches the environment or
constructs anything; ``getattr(module, "application")`` -- exactly what
daphne's own target resolution does, and what reading
``webhook_host.application`` triggers -- builds it on demand, caches the
result on the module (so a second lookup is a plain attribute read, never a
second construction), and still fails exactly as loudly as eager
construction would have for the one caller, daphne, that actually needs it
to.

**The bounded timeout + dedicated executor (narrowing DW-FU-13-4-3).**
``webhook.create_app``'s own ``app()`` dispatches each matched handler via
``asyncio.to_thread`` -- off the event-loop thread, but with no bound on how
long that may run (its module docstring: up to ~93s of legitimate SQLite
write-lock contention across 3 retries) and no bound on how many requests
can each claim a worker thread at once (the DEFAULT executor is
``min(32, cpu + 4)``, sized for the whole process, not for this one route).
Rather than changing ``webhook.py``'s own dispatch -- which would mean this
host-wiring concern leaking into the framework-neutral module AD-8 governs
-- ``_wrap`` wraps the WHOLE returned ASGI callable in one outer layer here:
every HTTP request is bounded by ``asyncio.wait_for(...,
timeout=REQUEST_TIMEOUT_SECONDS)`` (120s -- comfortably above the ~93s
legitimate worst case), and the running loop's default executor -- what
``asyncio.to_thread`` actually submits work to -- is pointed, on every
call, at a dedicated ``concurrent.futures.ThreadPoolExecutor`` capped at
``EXECUTOR_MAX_WORKERS`` (4) workers: a small, NAMED bound an operator can
reason about, rather than an implicit CPU-derived one. A request that hits
the timeout gets the same non-2xx shape the module's own retries-exhausted
alert path already returns (this story's I/O matrix: "the host returns the
same non-2xx the existing alert path returns"), logged the same
structured-JSON way, so CI's own webhook-delivery retry can re-fire it
later exactly like any other transient failure.

**This bounds how long a CALLER waits, not how long a genuinely-hung
handler occupies its worker thread.** ``asyncio.wait_for`` cancels the
*awaiting* coroutine; it cannot force-terminate a
``concurrent.futures.Future`` whose work already started running on a
thread (``Future.cancel()`` is a documented no-op past that point). Every
job in ``herald-live-demo.yml`` starts one throwaway process for exactly
one request, so this residual is currently inert -- it becomes live risk
only under a future persistent, multi-request deployment. Tracked as
``deferred-work.md``'s ``DW-FU-13-6-2``, not re-litigated here."""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import webhook
from .errors import HeraldError

logger = logging.getLogger(__name__)

REPO_ROOT_ENV_VAR = "HERALD_REPO_ROOT"
"""Where the env-var-driven ``application`` construction (``__getattr__``
below) reads ``repo_root`` from -- required, no default fallback, mirroring
``webhook.resolve_webhook_secret``'s own "never a literal or default" rule
for the secret: an operator forgetting to set this must not silently start
writing a live deployment's records into wherever the process happened to
be launched from."""

REQUEST_TIMEOUT_SECONDS = 120
"""Boundaries & Constraints: comfortably above DW-FU-13-4-3's documented
~93s legitimate worst case (3 retry attempts, each capable of blocking up
to ``db._BUSY_TIMEOUT_MS`` on SQLite's write lock, plus the retry backoff
sleeps between them)."""

EXECUTOR_MAX_WORKERS = 4
"""Boundaries & Constraints: "not the default ``min(32, cpu + 4)``" -- a
small, explicit, operator-legible bound on how many requests may
simultaneously occupy a worker thread, rather than an implicit
CPU-count-derived one."""

_TIMEOUT_ALERT_EVENT = "herald.webhook_host.request_timeout"


def _resolve_repo_root(env: Mapping[str, str] | None = None) -> Path:
    """``HERALD_REPO_ROOT`` as a ``Path`` -- injectable ``env``, mirroring
    ``webhook.resolve_webhook_secret``'s own injectable-env shape so a test
    never touches the real process environment. Raises ``HeraldError``
    naming the env var when it is unset or empty."""
    source = os.environ if env is None else env
    value = source.get(REPO_ROOT_ENV_VAR)
    if not value or not value.strip():
        raise HeraldError(
            f"{REPO_ROOT_ENV_VAR} is not set -- the webhook host needs a repo root to write .herald/herald.db under"
        )
    return Path(value)


def _wrap(
    inner: webhook.ASGIApp,
    *,
    executor: concurrent.futures.ThreadPoolExecutor,
    timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
) -> webhook.ASGIApp:
    """``inner`` (whatever ``webhook.create_app`` returned), wrapped in the
    bounded timeout + dedicated executor this module exists to add. A
    private, directly-testable seam (``tests/test_webhook_host.py`` injects
    a hand-built fake ``inner`` and a short ``timeout_seconds`` rather than
    waiting on a real hang) -- ``build_application`` below is the thin,
    env-var-driven wiring around this same call that daphne actually
    mounts."""

    async def app(scope: Mapping[str, Any], receive, send) -> None:
        # Cheap and idempotent -- just an attribute assignment on the
        # running loop -- so doing it on every call is simpler than adding
        # ASGI lifespan-protocol handling `webhook.py` does not have today
        # (its own `app()` already just no-ops a `lifespan` scope; see its
        # "Uncaught exceptions" section). `asyncio.to_thread` resolves its
        # executor as `loop.run_in_executor(None, ...)`, and `None` means
        # "the loop's own default executor" -- pointing that at our
        # dedicated pool is what makes `inner`'s own `asyncio.to_thread`
        # dispatch actually use it, with no change to `webhook.py` itself.
        asyncio.get_running_loop().set_default_executor(executor)
        if scope.get("type") != "http":
            await inner(scope, receive, send)
            return

        response_started = False

        async def tracking_send(message: Mapping[str, Any]) -> None:
            nonlocal response_started
            if message.get("type") == "http.response.start":
                response_started = True
            await send(message)

        try:
            await asyncio.wait_for(inner(scope, receive, tracking_send), timeout=timeout_seconds)
        except TimeoutError:
            # `inner`'s own last-resort guard (webhook.py's "Uncaught
            # exceptions" section) catches every exception ITS `app()` can
            # raise -- but `asyncio.wait_for` cancels the awaited coroutine
            # from OUTSIDE it, and `asyncio.CancelledError` is a
            # `BaseException` (Python 3.8+), not an `Exception`, so that
            # guard's `except Exception` never sees it: it propagates
            # straight out of `inner`, and `wait_for` re-raises it as
            # `TimeoutError` here. By construction this can only happen
            # while `inner` is blocked inside its own
            # `asyncio.to_thread(handler, ...)` call -- every response send
            # that can happen BEFORE that point (404/405/401/413/400)
            # completes well within the timeout -- so `response_started` is
            # always still `False` in practice; the guard is kept anyway
            # rather than assumed, the same defensive discipline
            # `webhook.py`'s own `fail()` applies to its own sends.
            logger.error(
                json.dumps(
                    {
                        "event": _TIMEOUT_ALERT_EVENT,
                        "path": scope.get("path"),
                        "timeout_seconds": timeout_seconds,
                    }
                )
            )
            if not response_started:
                await send(
                    {
                        "type": "http.response.start",
                        "status": 500,
                        "headers": [(b"content-type", b"application/json")],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": json.dumps({"error": "request timed out"}).encode(),
                    }
                )

    return app


def build_application(repo_root: Path, secret: bytes) -> webhook.ASGIApp:
    """``webhook.create_app(repo_root, secret)``, wrapped by ``_wrap`` in
    the bounded timeout + dedicated executor this module exists to add.
    Builds one fresh ``ThreadPoolExecutor`` per call -- the module-level
    ``application`` (below) calls this exactly once, ever, per process."""
    inner = webhook.create_app(repo_root, secret)
    executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=EXECUTOR_MAX_WORKERS, thread_name_prefix="herald-webhook"
    )
    return _wrap(inner, executor=executor)


_application: webhook.ASGIApp | None = None
"""The cache ``__getattr__`` below reads/writes -- module-private, never
imported directly; ``tests/test_webhook_host.py`` resets it between cases
for isolation (see that file's own fixture)."""


def __getattr__(name: str) -> webhook.ASGIApp:
    """PEP 562 module ``__getattr__`` -- see the module docstring's
    "``application`` is built lazily" section for why this exists instead
    of a plain module-level assignment. ``repo_root`` is resolved before
    ``secret`` (argument evaluation order): if both env vars are unset, the
    error names ``HERALD_REPO_ROOT`` first, deterministically."""
    if name != "application":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    global _application
    if _application is None:
        _application = build_application(_resolve_repo_root(), webhook.resolve_webhook_secret())
    return _application
