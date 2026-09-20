"""``webhook_host.py``'s ASGI host wiring (Story 13.6): the lazy
``application`` attribute, the bounded timeout, and the dedicated executor
closing DW-FU-13-4-3.

No test opens a real socket or starts daphne -- these hand-construct a
``scope``/``receive``/``send`` triple exactly like ``test_webhook.py``'s
own ASGI-level tests, so this module never trips the package's autouse
``deny_network`` fixture. The one genuinely-live-socket proof is
``tests/test_webhook_live_smoke.py``, the opt-in ``HERALD_LIVE_WEBHOOK``
marked test."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from pyforge.herald import webhook, webhook_host
from pyforge.herald.errors import HeraldError

# --- shared ASGI test helpers (mirrors test_webhook.py's own) ----------------


def _sign(secret: bytes, timestamp: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret, timestamp.encode("ascii") + b"." + body, hashlib.sha256).hexdigest()


def _timestamp() -> str:
    return str(int(time.time()))


def _signed_headers(secret: bytes, body: bytes) -> list[tuple[bytes, bytes]]:
    ts = _timestamp()
    return [
        (b"x-hub-signature-256", _sign(secret, ts, body).encode()),
        (b"x-hub-timestamp", ts.encode()),
    ]


def _scope(path: str, *, headers: list[tuple[bytes, bytes]] | None = None) -> dict[str, Any]:
    return {"type": "http", "method": "POST", "path": path, "headers": headers or []}


def _receive_once(body: bytes):
    sent = False

    async def receive() -> dict[str, Any]:
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


class _Recorder:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    async def __call__(self, message: dict[str, Any]) -> None:
        self.messages.append(message)

    @property
    def status(self) -> int:
        return next(m["status"] for m in self.messages if m["type"] == "http.response.start")

    @property
    def json_body(self) -> Any:
        body = b"".join(m["body"] for m in self.messages if m["type"] == "http.response.body")
        return json.loads(body)


# --- module-level `application`: lazy, cached, env-var-driven ----------------


@pytest.fixture(autouse=True)
def _reset_application_cache():
    """``webhook_host._application`` is a module-level cache -- reset it
    before AND after every test in this file so one test's real construction
    never leaks into the next (a plain ``monkeypatch.setattr`` would only
    restore whatever value happened to exist when THIS test started, which
    could already be another test's leftover)."""
    webhook_host._application = None
    yield
    webhook_host._application = None


def test_plain_import_never_touches_the_environment_or_constructs_anything():
    """The whole point of the PEP 562 ``__getattr__`` design (module
    docstring): merely importing this module -- which
    ``tests/test_bridge.py``'s bridge-core sweep does, with no
    ``HERALD_WEBHOOK_SECRET``/``HERALD_REPO_ROOT`` configured anywhere in
    this suite -- must never raise. Collecting this very test file already
    proved the import half; this asserts the cache is still empty, i.e.
    nothing was built as an import side effect."""
    assert webhook_host._application is None


def test_application_attribute_raises_when_repo_root_env_is_unset(monkeypatch):
    monkeypatch.delenv(webhook_host.REPO_ROOT_ENV_VAR, raising=False)
    monkeypatch.delenv(webhook.SECRET_ENV_VAR, raising=False)
    with pytest.raises(HeraldError, match=webhook_host.REPO_ROOT_ENV_VAR):
        webhook_host.application


def test_application_attribute_raises_when_secret_env_is_unset(monkeypatch, tmp_path):
    monkeypatch.setenv(webhook_host.REPO_ROOT_ENV_VAR, str(tmp_path))
    monkeypatch.delenv(webhook.SECRET_ENV_VAR, raising=False)
    with pytest.raises(HeraldError, match=webhook.SECRET_ENV_VAR):
        webhook_host.application


def test_application_attribute_builds_once_and_caches(monkeypatch, tmp_path):
    monkeypatch.setenv(webhook_host.REPO_ROOT_ENV_VAR, str(tmp_path))
    monkeypatch.setenv(webhook.SECRET_ENV_VAR, "shared-secret")
    calls = 0
    real_build = webhook_host.build_application

    def counting_build(*args, **kwargs):
        nonlocal calls
        calls += 1
        return real_build(*args, **kwargs)

    monkeypatch.setattr(webhook_host, "build_application", counting_build)
    first = webhook_host.application
    second = webhook_host.application
    assert first is second
    assert calls == 1


def test_application_attribute_is_a_working_asgi_callable_end_to_end(monkeypatch, tmp_path):
    """Proves the whole env-var-driven wiring, not just `build_application`
    in isolation: a real signed request through `webhook_host.application`
    creates a Progress record in the env-configured repo root."""
    monkeypatch.setenv(webhook_host.REPO_ROOT_ENV_VAR, str(tmp_path))
    monkeypatch.setenv(webhook.SECRET_ENV_VAR, "shared-secret")
    secret = b"shared-secret"
    body = json.dumps({"station": "warden"}).encode("utf-8")
    scope = _scope(webhook.ON_SHIP_PATH, headers=_signed_headers(secret, body))
    recorder = _Recorder()
    asyncio.run(webhook_host.application(scope, _receive_once(body), recorder))
    assert recorder.status == 201
    from pyforge.herald import progress

    records = progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH)
    assert len(records) == 1
    assert records[0].station == "warden"


def test_getattr_raises_attribute_error_for_any_other_name():
    with pytest.raises(AttributeError, match="bogus_name"):
        webhook_host.bogus_name


def test_resolve_repo_root_reads_the_injected_env():
    assert webhook_host._resolve_repo_root({"HERALD_REPO_ROOT": "/tmp/x"}) == Path("/tmp/x")


def test_resolve_repo_root_raises_when_unset():
    with pytest.raises(HeraldError, match=webhook_host.REPO_ROOT_ENV_VAR):
        webhook_host._resolve_repo_root({})


def test_resolve_repo_root_raises_when_whitespace_only():
    """A bare ``if not value`` misses this: a non-empty, whitespace-only
    string is truthy, so it would otherwise sail past the "is it set" guard
    and construct a literal space-named directory instead of raising the
    intended not-configured error (2026-08-13 review pass)."""
    with pytest.raises(HeraldError, match=webhook_host.REPO_ROOT_ENV_VAR):
        webhook_host._resolve_repo_root({"HERALD_REPO_ROOT": "   "})


# --- build_application: the daphne-mounted callable, end to end --------------


def test_build_application_valid_signed_request_creates_a_record(tmp_path: Path):
    app = webhook_host.build_application(tmp_path, b"shared-secret")
    body = json.dumps({"station": "warden"}).encode("utf-8")
    scope = _scope(webhook.ON_SHIP_PATH, headers=_signed_headers(b"shared-secret", body))
    recorder = _Recorder()
    asyncio.run(app(scope, _receive_once(body), recorder))
    assert recorder.status == 201
    from pyforge.herald import progress

    assert len(progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH)) == 1


# --- _wrap: the bounded timeout ------------------------------------------


def test_wrap_bounds_a_hanging_request_with_a_timeout(caplog):
    """A request that never completes (simulating DW-FU-13-4-3's ~93s
    legitimate worst case, or a genuinely stuck storage call) is bounded --
    the I/O matrix's own "Request exceeds the bounded timeout" row: "host
    returns the same non-2xx the existing alert path returns... Logged,
    non-2xx, no indefinite hang". A real `asyncio.sleep` (not a thread
    sleep) keeps this test fast and deterministic: `wait_for` cancels it
    cleanly with no dangling background thread."""

    async def hanging_inner(scope, receive, send) -> None:
        await asyncio.sleep(1000)

    executor = ThreadPoolExecutor(max_workers=1)
    app = webhook_host._wrap(hanging_inner, executor=executor, timeout_seconds=0.05)
    body = b"{}"
    scope = _scope(webhook.ON_SHIP_PATH)
    recorder = _Recorder()
    started = time.monotonic()
    with caplog.at_level("ERROR", logger=webhook_host.logger.name):
        asyncio.run(app(scope, _receive_once(body), recorder))
    elapsed = time.monotonic() - started
    assert elapsed < 2.0, f"the timeout did not bound the request ({elapsed:.1f}s)"
    assert recorder.status == 500
    assert "timed out" in recorder.json_body["error"]
    error_records = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(error_records) == 1
    logged = json.loads(error_records[0].message)
    assert logged["event"] == "herald.webhook_host.request_timeout"


def test_wrap_does_not_bound_a_request_that_completes_in_time():
    async def fast_inner(scope, receive, send) -> None:
        await send({"type": "http.response.start", "status": 201, "headers": []})
        await send({"type": "http.response.body", "body": b"{}"})

    executor = ThreadPoolExecutor(max_workers=1)
    app = webhook_host._wrap(fast_inner, executor=executor, timeout_seconds=5)
    recorder = _Recorder()
    asyncio.run(app(_scope(webhook.ON_SHIP_PATH), _receive_once(b"{}"), recorder))
    assert recorder.status == 201


def test_wrap_never_double_sends_when_a_response_already_started_before_a_timeout():
    """Defensive: if `inner` had already sent `http.response.start` before
    the timeout fired, the wrapper must not attempt a second one (the ASGI
    contract webhook.py's own `fail()` guards against identically)."""

    async def partially_sent_then_hangs(scope, receive, send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await asyncio.sleep(1000)

    executor = ThreadPoolExecutor(max_workers=1)
    app = webhook_host._wrap(partially_sent_then_hangs, executor=executor, timeout_seconds=0.05)
    recorder = _Recorder()
    asyncio.run(app(_scope(webhook.ON_SHIP_PATH), _receive_once(b"{}"), recorder))
    starts = [m for m in recorder.messages if m["type"] == "http.response.start"]
    assert len(starts) == 1
    assert starts[0]["status"] == 200


def test_wrap_passes_a_non_http_scope_straight_through():
    seen = []

    async def recording_inner(scope, receive, send) -> None:
        seen.append(scope["type"])

    executor = ThreadPoolExecutor(max_workers=1)
    app = webhook_host._wrap(recording_inner, executor=executor)
    asyncio.run(app({"type": "lifespan"}, _receive_once(b""), _Recorder()))
    assert seen == ["lifespan"]


# --- _wrap: the dedicated executor (closing DW-FU-13-4-3) --------------------


def test_wrap_points_asyncio_to_thread_at_the_dedicated_executor():
    """Proves the executor DW-FU-13-4-3 asks for is actually the one
    servicing `asyncio.to_thread` calls made from inside the wrapped app --
    not merely constructed and ignored. `ThreadPoolExecutor`'s own
    `thread_name_prefix` names every worker thread it spawns, so the name
    observed from inside the wrapped request is the signal."""
    observed_thread_names: list[str] = []

    async def inner_using_to_thread(scope, receive, send) -> None:
        name = await asyncio.to_thread(lambda: threading.current_thread().name)
        observed_thread_names.append(name)
        await send({"type": "http.response.start", "status": 201, "headers": []})
        await send({"type": "http.response.body", "body": b"{}"})

    executor = ThreadPoolExecutor(max_workers=webhook_host.EXECUTOR_MAX_WORKERS, thread_name_prefix="herald-webhook")
    app = webhook_host._wrap(inner_using_to_thread, executor=executor)
    recorder = _Recorder()
    asyncio.run(app(_scope(webhook.ON_SHIP_PATH), _receive_once(b"{}"), recorder))
    assert recorder.status == 201
    assert len(observed_thread_names) == 1
    assert observed_thread_names[0].startswith("herald-webhook")


def test_build_application_uses_a_4_worker_executor():
    """`EXECUTOR_MAX_WORKERS` is the named bound Boundaries & Constraints
    calls for -- "not the default `min(32, cpu + 4)`"."""
    assert webhook_host.EXECUTOR_MAX_WORKERS == 4


def test_request_timeout_is_comfortably_above_dw_fu_13_4_3s_worst_case():
    """DW-FU-13-4-3: ~93s legitimate worst case (3 retry attempts, each
    capable of blocking up to `db._BUSY_TIMEOUT_MS` (30s) on SQLite's write
    lock). 120s leaves real headroom rather than cutting it close."""
    assert webhook_host.REQUEST_TIMEOUT_SECONDS == 120
    assert webhook_host.REQUEST_TIMEOUT_SECONDS > 93
