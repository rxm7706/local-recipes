"""Story 42.1 — MCP transport authorization and a streaming proxy.

Red-team T-4 (every JSON-RPC method was anonymous because ``dispatch_station_mcp``
runs before every middleware), T-5 (the sidecar hop buffered the whole response,
timed out at five seconds, and forwarded every inbound header including the
caller's credential) and X-5 (nothing stopped the rest of the namespace calling
mcp-host directly). Directive R-7.

The chart half of the fix -- the NetworkPolicy that lets only ``web`` reach
mcp-host:8090 -- is an invariant over ``helm template`` in
``test_chart_invariants.py``; everything else is here.

No DB, no ``django_db`` marker and deliberately no Django settings: the gate
reads headers, and this module hands it the golden keys directly (environment
for the verifier, an explicit PEM for the signer). That is not just
convenience -- exercising the gate with Django uninvolved is what proves AC 5's
"one code path, transport-agnostic" claim rather than asserting it.
"""

from __future__ import annotations

import ast
import asyncio
import json
import math
import time
from http import HTTPStatus
from pathlib import Path
from typing import Any
from typing import Self
from unittest.mock import patch

import httpx
import pytest
from django_pyforge import mcp_auth
from django_pyforge import mcp_http
from django_pyforge.assertion.crypto import mint_assertion
from django_pyforge.assertion.golden import GOLDEN_PRIVATE_PEM
from django_pyforge.assertion.golden import GOLDEN_PUBLIC_PEM
from django_pyforge.assertion.schema import MAX_TTL_SECONDS
from django_pyforge.mcp_auth import PUBLIC_KEY_ENV
from django_pyforge.mcp_auth import TransportRefusal
from django_pyforge.mcp_auth import authorize_station_scope
from django_pyforge.mcp_dual_era import asgi_for_station
from django_pyforge.mcp_http import dispatch_station_mcp
from django_pyforge.mcp_http import register_station_mcp_app
from starlette.testclient import TestClient

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
MCP_AUTH_PATH = CHROME_ROOT / "mcp_auth.py"
VERIFY_PATH = CHROME_ROOT / "assertion" / "verify.py"
CRYPTO_PATH = CHROME_ROOT / "assertion" / "crypto.py"
BASE_SETTINGS_PATH = PLATFORM_ROOT / "config" / "settings" / "base.py"

# HAProxy governs an idle stream by `timeout client`, which OpenShift fixes at
# 30s with no per-route annotation (BS-2 revised).
INGRESS_IDLE_TIMEOUT_SECONDS = 30.0
FIRST_BYTE_BUDGET_SECONDS = 1.0
# A relay that cannot terminate must fail the test, never hang the suite.
RELAY_DEADLINE_SECONDS = 10.0

JSONRPC_METHODS = ("initialize", "tools/list", "tools/call")


def _request(method: str) -> dict[str, Any]:
    payload: dict[str, Any] = {"jsonrpc": "2.0", "id": 1, "method": method}
    if method == "initialize":
        payload["params"] = {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "fixture-client", "version": "0"},
        }
    else:
        payload["params"] = {}
    return payload


def _scope(
    station: str = "atlas",
    *,
    assertion: str | None = None,
    method: str = "POST",
    extra_headers: tuple[tuple[bytes, bytes], ...] = (),
) -> dict[str, Any]:
    headers: list[tuple[bytes, bytes]] = [(b"content-type", b"application/json")]
    if assertion is not None:
        headers.append((b"authorization", f"Bearer {assertion}".encode("latin-1")))
    headers.extend(extra_headers)
    return {
        "type": "http",
        "path": f"/stations/{station}/mcp",
        "method": method,
        "headers": headers,
    }


async def _receive() -> dict[str, Any]:
    return {"type": "http.request", "body": b"{}", "more_body": False}


def _receiver(body: bytes):
    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


def _run_dispatch(
    scope: dict[str, Any],
    *,
    body: bytes = b"{}",
) -> list[dict[str, Any]]:
    sent: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    async def _go() -> bool:
        return await dispatch_station_mcp(scope, _receiver(body), send)

    assert asyncio.run(_go()) is True
    return sent


def _status(sent: list[dict[str, Any]]) -> int:
    start = next(m for m in sent if m["type"] == "http.response.start")
    return int(start["status"])


def _mint(station: str, *, sub: str = "agent-42-1", iat: int | None = None) -> str:
    """Sign with the golden key directly -- no Django settings involved."""
    return mint_assertion(
        sub=sub,
        roles=[f"pyforge:station:{station}"],
        station=station,
        private_pem=GOLDEN_PRIVATE_PEM,
        iat=iat,
    )


@pytest.fixture(autouse=True)
def _transport_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """In-process path by default (the proxy tests opt in), verifier keyed by
    the environment (so the gate resolves its key with Django uninvolved).
    """
    monkeypatch.delenv(mcp_http.MCP_HOST_SIDECAR_URL_ENV, raising=False)
    monkeypatch.delenv(mcp_http.MCP_PROXY_TIMEOUT_ENV, raising=False)
    monkeypatch.setenv(PUBLIC_KEY_ENV, GOLDEN_PUBLIC_PEM)


@pytest.fixture
def atlas_assertion() -> str:
    return _mint("atlas")


# ---------------------------------------------------------------------------
# AC 1 -- no anonymous JSON-RPC method, and the audience is the station
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method", JSONRPC_METHODS)
def test_no_assertion_is_401_for_every_jsonrpc_method(method: str) -> None:
    """AC: with no assertion, ANY JSON-RPC method is 401 -- `initialize` and
    `tools/list` are not a pre-auth handshake, they are the anonymous surface
    T-4 found.
    """
    sent = _run_dispatch(_scope(), body=json.dumps(_request(method)).encode())

    assert _status(sent) == HTTPStatus.UNAUTHORIZED
    body = b"".join(
        m.get("body", b"") for m in sent if m["type"] == "http.response.body"
    )
    assert b"assertion required" in body


def test_assertion_for_another_station_is_403_on_this_route(
    atlas_assertion: str,
) -> None:
    """AC: a valid assertion whose audience is `mcp:warden` is 403 on the atlas
    route -- refused as the wrong audience, not merely unauthenticated.
    """
    warden = _mint("warden")

    assert _status(_run_dispatch(_scope("atlas", assertion=warden))) == (
        HTTPStatus.FORBIDDEN
    )
    # ...and the same subject's atlas assertion is not refused for audience.
    outcome = authorize_station_scope(
        _scope("atlas", assertion=atlas_assertion),
        "atlas",
    )
    assert not isinstance(outcome, TransportRefusal)


def test_a_tampered_or_unsigned_token_is_401(atlas_assertion: str) -> None:
    """AC: possession of a JWT-shaped string is not authorization."""
    header, payload, signature = atlas_assertion.split(".")
    tampered = f"{header}.{payload}.{signature[:-4]}xxxx"

    assert _status(_run_dispatch(_scope(assertion=tampered))) == (
        HTTPStatus.UNAUTHORIZED
    )
    assert _status(_run_dispatch(_scope(assertion="not-a-jwt"))) == (
        HTTPStatus.UNAUTHORIZED
    )
    assert _status(_run_dispatch(_scope(assertion=""))) == HTTPStatus.UNAUTHORIZED


def test_an_expired_assertion_is_401() -> None:
    """AC: the five-minute TTL is enforced at the transport, not only in tools."""
    stale = _mint("atlas", iat=int(time.time()) - (MAX_TTL_SECONDS * 2))

    assert _status(_run_dispatch(_scope(assertion=stale))) == HTTPStatus.UNAUTHORIZED


def test_an_unconfigured_verifier_refuses_rather_than_passes(
    monkeypatch: pytest.MonkeyPatch,
    atlas_assertion: str,
) -> None:
    """AC (fail closed): with no public key from either source, the route is
    503 -- never an open door.
    """
    monkeypatch.delenv(PUBLIC_KEY_ENV, raising=False)
    monkeypatch.setattr(mcp_auth, "_settings_public_pem", lambda: "")

    assert _status(_run_dispatch(_scope(assertion=atlas_assertion))) == (
        HTTPStatus.SERVICE_UNAVAILABLE
    )


def test_a_non_post_method_is_405_without_needing_an_assertion() -> None:
    """Streamable HTTP is POST-only; a GET can carry no call, so it is refused
    before the gate and never reaches a station or the sidecar.
    """
    sent = _run_dispatch(_scope(method="GET"))

    assert _status(sent) == HTTPStatus.METHOD_NOT_ALLOWED
    start = next(m for m in sent if m["type"] == "http.response.start")
    assert (b"allow", b"POST") in start["headers"]


def test_a_verified_assertion_reaches_the_in_process_station(
    atlas_assertion: str,
) -> None:
    """AC: the gate refuses; it does not block a legitimate call, and the body
    reaches the station unread.
    """
    mcp_app = asgi_for_station("atlas")
    register_station_mcp_app("atlas", mcp_app)

    async def application(scope, receive, send) -> None:
        if scope["type"] == "lifespan":
            await mcp_app(scope, receive, send)
            return
        if await dispatch_station_mcp(scope, receive, send):
            return
        await send(
            {
                "type": "http.response.start",
                "status": 404,
                "headers": [(b"content-type", b"text/plain")],
            },
        )
        await send({"type": "http.response.body", "body": b"not mcp"})

    with TestClient(application) as client:
        response = client.post(
            "/stations/atlas/mcp",
            json=_request("initialize"),
            headers={
                "accept": "application/json, text/event-stream",
                "content-type": "application/json",
                "authorization": f"Bearer {atlas_assertion}",
            },
        )

    assert response.status_code == HTTPStatus.OK, response.text
    assert (response.json().get("result") or {}).get("protocolVersion") == "2025-06-18"


# ---------------------------------------------------------------------------
# AC 5 -- one verifier, transport-agnostic
# ---------------------------------------------------------------------------


def test_the_same_verifier_runs_on_both_transports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC: the laptop (in-process) path and the sidecar path are gated by the
    same call, so an anonymous request is refused identically on both -- the
    refusal cannot be produced by the sidecar, which is never reached.
    """
    in_process = _run_dispatch(_scope())
    monkeypatch.setenv(mcp_http.MCP_HOST_SIDECAR_URL_ENV, "http://mcp-host:8090")
    with patch("httpx.AsyncClient") as client:
        proxied = _run_dispatch(_scope())
    assert client.call_count == 0, "a refused request must not reach the sidecar"

    assert _status(in_process) == _status(proxied) == HTTPStatus.UNAUTHORIZED


def _module_scope_imports(path: Path) -> list[str]:
    """Dotted module names imported at MODULE scope (never inside a function).

    Module scope is not the same as ``tree.body``: an import nested in a
    top-level ``try:``/``if:``/``with:`` still runs on import, so scanning only
    the outermost statements would let ``try: import django`` past the guard.
    Function and lambda bodies are the real exclusion -- ``mcp_auth`` imports
    Django inside ``_settings_public_pem`` BY DESIGN, which is exactly what
    makes the module chrome.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    stack: list[ast.AST] = list(tree.body)
    while stack:
        node = stack.pop()
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
            continue
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
            continue
        if isinstance(node, ast.ImportFrom):
            if node.level == 0:
                names.append(node.module or "")
            continue
        stack.extend(ast.iter_child_nodes(node))
    return names


def _chrome_module_paths(dotted: str) -> list[Path]:
    """Files Python executes to import ``dotted``, when it is chrome.

    Importing ``django_pyforge.assertion.schema`` also executes
    ``django_pyforge/__init__.py`` and ``django_pyforge/assertion/__init__.py``,
    so a Django import in either would break the guarantee just as surely --
    they are part of the closure, not decoration.
    """
    parts = dotted.split(".")
    if not parts or parts[0] != "django_pyforge":
        return []
    found: list[Path] = []
    package = CHROME_ROOT
    if (package / "__init__.py").is_file():
        found.append(package / "__init__.py")
    for part in parts[1:]:
        candidate = package / f"{part}.py"
        if candidate.is_file():
            found.append(candidate)
            break
        package = package / part
        init = package / "__init__.py"
        if init.is_file():
            found.append(init)
    return found


def _django_free_closure(seeds: tuple[Path, ...]) -> list[Path]:
    """Every chrome file executed by importing ``seeds``, transitively."""
    seen: dict[Path, None] = {}
    queue = list(seeds)
    while queue:
        path = queue.pop()
        if path in seen:
            continue
        seen[path] = None
        for dotted in _module_scope_imports(path):
            queue.extend(_chrome_module_paths(dotted))
    return list(seen)


def test_the_verifier_is_django_free_and_the_only_rule_set() -> None:
    """AC: one code path. ``mcp_auth`` and the rules it calls import no Django
    at module scope (so the same module verifies wherever it runs), and the
    Django-settings wrapper delegates to those rules instead of copying them.

    Scanning only the two seed modules would leave the guarantee open: they
    import ``assertion/schema.py`` and ``assertion/exceptions.py`` at module
    scope, so a Django import added to either breaks it silently. The scan
    therefore walks the whole import closure.
    """
    closure = _django_free_closure((MCP_AUTH_PATH, VERIFY_PATH))
    scanned = {path.name for path in closure}
    assert {"mcp_auth.py", "verify.py", "schema.py", "exceptions.py"} <= scanned, (
        f"the closure walk missed a module the verifier imports: {sorted(scanned)}"
    )
    for path in closure:
        offenders = [
            name
            for name in _module_scope_imports(path)
            if name.split(".")[0] == "django"
        ]
        assert not offenders, (
            f"{path.relative_to(CHROME_ROOT.parent)} imports Django at module "
            f"scope: {offenders} -- the transport verifier must import in an "
            f"interpreter with no Django at all"
        )

    crypto_source = CRYPTO_PATH.read_text(encoding="utf-8")
    assert "verify_assertion_claims" in crypto_source, (
        "crypto.verify_assertion must delegate to the shared rules, "
        "not re-implement them"
    )
    assert "jwt.decode" not in crypto_source, (
        "a second jwt.decode in crypto is a second verifier"
    )


def test_the_django_free_scan_sees_imports_nested_at_module_scope(
    tmp_path: Path,
) -> None:
    """Guard removal check for the scan itself: an import inside a top-level
    ``try:``/``if:`` runs on import just like an outermost one, so a scan that
    reads only ``tree.body`` would clear ``try: import django`` -- while an
    import inside a function must still be invisible, because that deferred
    shape is exactly how ``mcp_auth`` reaches Django settings without becoming
    a Django module.
    """
    module = tmp_path / "sample.py"
    module.write_text(
        "import os\n"
        "try:\n"
        "    import django.conf\n"
        "except ImportError:\n"
        "    django = None\n"
        "if os.environ:\n"
        "    from django.core import exceptions\n"
        "\n"
        "def later():\n"
        "    from django.db import models\n"
        "    return models\n",
        encoding="utf-8",
    )

    found = _module_scope_imports(module)

    assert "django.conf" in found, "an import inside a module-scope try: still runs"
    assert "django.core" in found, "an import inside a module-scope if: still runs"
    assert "django.db" not in found, "a function-scope import is not module scope"


# ---------------------------------------------------------------------------
# AC 2 / AC 3 -- the streaming proxy and its header discipline
# ---------------------------------------------------------------------------


class _StubUpstream:
    """A sidecar response that yields its chunks over time."""

    def __init__(  # noqa: PLR0913 -- a stub's knobs, one per behaviour under test
        self,
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        chunks: tuple[bytes, ...] = (b"{}",),
        gap: float = 0.0,
        first_delay: float = 0.0,
        fails_after: BaseException | None = None,
        fails_on_close: bool = False,
        close_failure: BaseException | None = None,
        open_failure: BaseException | None = None,
    ) -> None:
        self.status_code = status_code
        self.headers = (
            headers if headers is not None else {"content-type": "application/json"}
        )
        self._chunks = chunks
        self._gap = gap
        self._first_delay = first_delay
        self._fails_after = fails_after
        self.fails_on_close = fails_on_close
        self.close_failure = close_failure
        self.open_failure = open_failure

    async def aiter_bytes(self):
        if self._first_delay:
            await asyncio.sleep(self._first_delay)
        for index, chunk in enumerate(self._chunks):
            if index and self._gap:
                await asyncio.sleep(self._gap)
            yield chunk
        if self._fails_after is not None:
            raise self._fails_after


class _StubStreamContext:
    def __init__(self, upstream: _StubUpstream) -> None:
        self._upstream = upstream

    async def __aenter__(self) -> _StubUpstream:
        return self._upstream

    async def __aexit__(self, *exc_info: object) -> None:
        if self._upstream.close_failure is not None:
            raise self._upstream.close_failure
        if self._upstream.fails_on_close:
            msg = "upstream connection dropped during teardown"
            raise httpx.ReadError(msg)


class _StubClient:
    def __init__(self, upstream: _StubUpstream, calls: list[dict[str, Any]]) -> None:
        self._upstream = upstream
        self._calls = calls

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None

    def stream(self, method: str, url: str, **kwargs: Any) -> _StubStreamContext:
        if self._upstream.open_failure is not None:
            raise self._upstream.open_failure
        self._calls.append({"method": method, "url": url, **kwargs})
        return _StubStreamContext(self._upstream)


def _proxy(
    upstream: _StubUpstream,
    scope: dict[str, Any],
    *,
    body: bytes = b"{}",
) -> tuple[list[tuple[float, dict[str, Any]]], list[dict[str, Any]], list[Any]]:
    """Drive dispatch through the sidecar path against ``upstream``.

    Bounded by a hard deadline: a relay that cannot terminate is a real failure
    mode of this code (a pump that dies unreported), and it must surface as a
    failing test rather than a hung suite.

    Returns (timed sent messages, recorded upstream calls, client kwargs).
    """
    calls: list[dict[str, Any]] = []
    client_kwargs: list[Any] = []
    timed: list[tuple[float, dict[str, Any]]] = []
    started = time.monotonic()

    async def send(message: dict[str, Any]) -> None:
        timed.append((time.monotonic() - started, message))

    def factory(**kwargs: Any) -> _StubClient:
        client_kwargs.append(kwargs)
        return _StubClient(upstream, calls)

    async def _go() -> bool:
        with patch("httpx.AsyncClient", new=factory):
            return await asyncio.wait_for(
                dispatch_station_mcp(scope, _receiver(body), send),
                timeout=RELAY_DEADLINE_SECONDS,
            )

    assert asyncio.run(_go()) is True
    return timed, calls, client_kwargs


@pytest.fixture
def _sidecar(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv(mcp_http.MCP_HOST_SIDECAR_URL_ENV, "http://mcp-host:8090")
    return "http://mcp-host:8090"


@pytest.mark.usefixtures("_sidecar")
def test_proxy_streams_chunks_instead_of_buffering(atlas_assertion: str) -> None:
    """AC: the client gets the first bytes within a second and every chunk is
    delivered as it arrives -- the shape that makes a 20s tool call work
    instead of buffering to completion behind `response.content`.
    """
    upstream = _StubUpstream(
        chunks=(b"first", b"second", b"third"),
        gap=0.2,
        headers={"content-type": "text/event-stream"},
    )

    timed, _calls, _kwargs = _proxy(upstream, _scope(assertion=atlas_assertion))

    bodies = [
        (at, message)
        for at, message in timed
        if message["type"] == "http.response.body" and message.get("body")
    ]
    assert len(bodies) >= 3, timed  # noqa: PLR2004 -- three chunks, three messages
    assert bodies[0][0] < FIRST_BYTE_BUDGET_SECONDS, (
        f"first bytes took {bodies[0][0]:.3f}s -- the response is being buffered"
    )
    assert bodies[0][1]["body"] == b"first"
    assert bodies[-1][0] > bodies[0][0], "every chunk arrived at once (buffered)"
    assert all(message.get("more_body") for _at, message in bodies)
    last = timed[-1][1]
    assert last["type"] == "http.response.body"
    assert last.get("more_body") is False, "the stream never closed"


@pytest.mark.usefixtures("_sidecar")
def test_proxy_disables_downstream_buffering(atlas_assertion: str) -> None:
    """AC: `X-Accel-Buffering: no` so no intermediary re-buffers the stream."""
    timed, _calls, _kwargs = _proxy(_StubUpstream(), _scope(assertion=atlas_assertion))

    start = next(m for _at, m in timed if m["type"] == "http.response.start")
    assert (b"x-accel-buffering", b"no") in start["headers"]
    names = [name for name, _value in start["headers"]]
    assert names.count(b"x-accel-buffering") == 1


@pytest.mark.usefixtures("_sidecar")
def test_proxy_keeps_an_idle_event_stream_alive_under_thirty_seconds(
    monkeypatch: pytest.MonkeyPatch,
    atlas_assertion: str,
) -> None:
    """AC: comment frames keep an idle stream open. The interval must sit well
    under the 30s ingress client timeout that governs SSE.
    """
    assert mcp_http.KEEPALIVE_INTERVAL_SECONDS < INGRESS_IDLE_TIMEOUT_SECONDS
    monkeypatch.setattr(mcp_http, "KEEPALIVE_INTERVAL_SECONDS", 0.02)
    upstream = _StubUpstream(
        chunks=(b"event: done\n\n",),
        first_delay=0.15,
        headers={"content-type": "text/event-stream"},
    )

    timed, _calls, _kwargs = _proxy(upstream, _scope(assertion=atlas_assertion))

    frames = [m["body"] for _at, m in timed if m["type"] == "http.response.body"]
    assert mcp_http.KEEPALIVE_FRAME in frames, frames
    assert frames.index(mcp_http.KEEPALIVE_FRAME) < frames.index(b"event: done\n\n")


@pytest.mark.usefixtures("_sidecar")
def test_proxy_never_injects_comment_frames_into_a_json_body(
    monkeypatch: pytest.MonkeyPatch,
    atlas_assertion: str,
) -> None:
    """A keep-alive comment in a JSON response would corrupt it."""
    monkeypatch.setattr(mcp_http, "KEEPALIVE_INTERVAL_SECONDS", 0.02)
    upstream = _StubUpstream(chunks=(b'{"jsonrpc":"2.0"}',), first_delay=0.15)

    timed, _calls, _kwargs = _proxy(upstream, _scope(assertion=atlas_assertion))

    body = b"".join(
        m.get("body", b"") for _at, m in timed if m["type"] == "http.response.body"
    )
    assert body == b'{"jsonrpc":"2.0"}'


def _configured_celery_hard_limit() -> float:
    """``CELERY_TASK_TIME_LIMIT`` as the settings module actually assigns it.

    Read from the source rather than from ``settings`` so this stays a real
    coupling: raising the Celery hard limit without raising the proxy floor
    fails here instead of silently re-opening the 502.
    """
    tree = ast.parse(BASE_SETTINGS_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        names = {t.id for t in node.targets if isinstance(t, ast.Name)}
        if "CELERY_TASK_TIME_LIMIT" in names:
            return float(_numeric_literal(node.value))
    msg = "config/settings/base.py assigns no CELERY_TASK_TIME_LIMIT"
    raise AssertionError(msg)


def _numeric_literal(node: ast.expr) -> float:
    """``5 * 60`` is a product of literals, which ``literal_eval`` refuses."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        return _numeric_literal(node.left) * _numeric_literal(node.right)
    return float(ast.literal_eval(node))


@pytest.mark.usefixtures("_sidecar")
def test_proxy_budget_is_at_least_the_celery_hard_limit(
    atlas_assertion: str,
) -> None:
    """AC: a tool call may run as long as Celery lets its task run; five
    seconds is what turned a long call into a 502.
    """
    _timed, _calls, client_kwargs = _proxy(
        _StubUpstream(),
        _scope(assertion=atlas_assertion),
    )

    celery_hard_limit = _configured_celery_hard_limit()
    timeout = client_kwargs[0]["timeout"]
    assert timeout.read >= celery_hard_limit
    assert timeout.read >= mcp_http.CELERY_HARD_LIMIT_SECONDS
    assert mcp_http.proxy_timeout_seconds() >= celery_hard_limit
    assert timeout.connect <= celery_hard_limit, (
        "connect should fail fast; only the read budget is long"
    )


def test_proxy_budget_honours_a_larger_override_and_refuses_a_smaller_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A builds-pool deployment may raise the budget; nothing may lower it
    below the Celery hard limit.
    """
    monkeypatch.setenv(mcp_http.MCP_PROXY_TIMEOUT_ENV, "3600")
    assert mcp_http.proxy_timeout_seconds() == 3600.0  # noqa: PLR2004
    # `nan` and `inf` both parse: max(nan, floor) IS nan, and inf is no budget
    # at all -- a hung sidecar would then pin the worker indefinitely, which is
    # exactly what the floor exists to prevent.
    for rejected in ("5", "0", "-1", "nan", "NaN", "inf", "-inf", "not-a-number"):
        monkeypatch.setenv(mcp_http.MCP_PROXY_TIMEOUT_ENV, rejected)
        budget = mcp_http.proxy_timeout_seconds()
        assert budget == mcp_http.CELERY_HARD_LIMIT_SECONDS, rejected
        assert math.isfinite(budget), rejected


@pytest.mark.usefixtures("_sidecar")
def test_proxy_forwards_only_the_verified_assertion(atlas_assertion: str) -> None:
    """AC: the inbound Authorization is replaced by the verified assertion and
    no other credential header crosses the hop (T-5 / X-5). The forwarded set
    is an allowlist, so a credential the platform has never heard of is
    dropped too.
    """
    scope = _scope(
        assertion=atlas_assertion,
        extra_headers=(
            (b"cookie", b"sessionid=platform-session"),
            (b"x-api-key", b"an-upstream-key"),
            (b"proxy-authorization", b"Basic bm9wZQ=="),
            (b"x-forwarded-user", b"someone"),
            (b"x-vendor-credential", b"never-seen-this-header"),
            (b"mcp-protocol-version", b"2026-07-28"),
        ),
    )

    _timed, calls, _kwargs = _proxy(_StubUpstream(), scope)

    forwarded = {key.lower(): value for key, value in calls[0]["headers"].items()}
    assert forwarded["authorization"] == f"Bearer {atlas_assertion}"
    assert forwarded["mcp-protocol-version"] == "2026-07-28"
    for dropped in (
        "cookie",
        "x-api-key",
        "proxy-authorization",
        "x-forwarded-user",
        "x-vendor-credential",
    ):
        assert dropped not in forwarded, f"{dropped} crossed to the sidecar"


@pytest.mark.usefixtures("_sidecar")
def test_proxy_replaces_an_inbound_credential_that_is_not_an_assertion() -> None:
    """AC: an IdP bearer never reaches the sidecar -- it fails the gate, so the
    request is refused before a hop exists to forward it on.
    """
    idp_shaped = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJhZ2VudCJ9.not-our-signature"

    calls: list[dict[str, Any]] = []

    async def send(_message: dict[str, Any]) -> None:
        return None

    def factory(**_kwargs: Any) -> _StubClient:
        return _StubClient(_StubUpstream(), calls)

    async def _go() -> bool:
        with patch("httpx.AsyncClient", new=factory):
            return await dispatch_station_mcp(
                _scope(assertion=idp_shaped),
                _receive,
                send,
            )

    assert asyncio.run(_go()) is True
    assert calls == [], "an unverified credential was forwarded to the sidecar"


@pytest.mark.usefixtures("_sidecar")
def test_a_mid_stream_failure_closes_the_body_exactly_once(
    atlas_assertion: str,
) -> None:
    """Once the head is sent the only way to signal failure is to close, and
    ASGI allows exactly one closing message -- a second would be a protocol
    violation on top of the failure.
    """
    for upstream in (
        _StubUpstream(chunks=(b"partial",), fails_after=httpx.ReadError("gone")),
        _StubUpstream(chunks=(b"partial",), fails_on_close=True),
    ):
        timed, _calls, _kwargs = _proxy(upstream, _scope(assertion=atlas_assertion))

        starts = [m for _at, m in timed if m["type"] == "http.response.start"]
        closes = [
            m
            for _at, m in timed
            if m["type"] == "http.response.body" and m.get("more_body") is False
        ]
        assert len(starts) == 1, timed
        assert len(closes) == 1, timed
        assert any(m.get("body") == b"partial" for _at, m in timed)


@pytest.mark.usefixtures("_sidecar")
@pytest.mark.parametrize(
    "failure",
    [
        # httpx's failure surface is not one tree. StreamError subclasses
        # RuntimeError and InvalidURL subclasses Exception, so `except
        # httpx.RequestError` -- the obvious catch, and the one the pre-patch
        # code used -- misses both.
        httpx.StreamClosed(),
        httpx.ReadError("gone"),
    ],
    ids=["stream-error", "request-error"],
)
def test_a_teardown_failure_outside_request_error_still_closes_the_body(
    atlas_assertion: str,
    failure: BaseException,
) -> None:
    """A failure raised while unwinding the stream arrives AFTER the head is
    sent, so it can only be answered by closing the body -- and it must be
    answered, whichever branch of httpx's exception surface it comes from.
    Escaping here leaves an unhandled ASGI exception on a response the client
    is still reading.
    """
    upstream = _StubUpstream(chunks=(b"partial",), close_failure=failure)

    timed, _calls, _kwargs = _proxy(upstream, _scope(assertion=atlas_assertion))

    starts = [m for _at, m in timed if m["type"] == "http.response.start"]
    closes = [
        m
        for _at, m in timed
        if m["type"] == "http.response.body" and m.get("more_body") is False
    ]
    assert len(starts) == 1, timed
    assert len(closes) == 1, timed
    assert any(m.get("body") == b"partial" for _at, m in timed)


@pytest.mark.usefixtures("_sidecar")
def test_a_sidecar_url_httpx_rejects_answers_502_rather_than_crashing(
    atlas_assertion: str,
) -> None:
    """`httpx.InvalidURL` is not a RequestError, so a malformed
    MCP_HOST_SIDECAR_BASE_URL would escape as an unhandled ASGI exception --
    no status, no body -- instead of the 502 this proxy answers for every
    other way the hop cannot be made.
    """
    upstream = _StubUpstream(open_failure=httpx.InvalidURL("not a url"))

    timed, calls, _kwargs = _proxy(upstream, _scope(assertion=atlas_assertion))

    assert calls == [], "a rejected URL must not count as a forwarded call"
    start = next(m for _at, m in timed if m["type"] == "http.response.start")
    assert start["status"] == HTTPStatus.BAD_GATEWAY


@pytest.mark.usefixtures("_sidecar")
@pytest.mark.parametrize(
    "failure",
    [
        # httpx.StreamError subclasses RuntimeError, NOT HTTPError -- a relay
        # that only reports HTTPError/OSError never learns this pump died.
        httpx.StreamClosed(),
        RuntimeError("upstream iterator blew up"),
        ValueError("upstream yielded something unusable"),
    ],
    ids=["stream-error", "runtime-error", "value-error"],
)
def test_a_pump_failure_of_any_type_terminates_the_relay(
    monkeypatch: pytest.MonkeyPatch,
    atlas_assertion: str,
    failure: BaseException,
) -> None:
    """A pump that dies for a reason outside httpx's HTTPError tree must still
    end the relay and close the body once -- otherwise the loop waits on a
    queue nothing will fill, emitting keep-alive frames forever on an event
    stream and never closing the ASGI response.
    """
    monkeypatch.setattr(mcp_http, "KEEPALIVE_INTERVAL_SECONDS", 0.05)
    upstream = _StubUpstream(
        chunks=(b"partial",),
        fails_after=failure,
        headers={"content-type": "text/event-stream"},
    )

    timed, _calls, _kwargs = _proxy(upstream, _scope(assertion=atlas_assertion))

    closes = [
        m
        for _at, m in timed
        if m["type"] == "http.response.body" and m.get("more_body") is False
    ]
    assert len(closes) == 1, timed
    frames = [m.get("body") for _at, m in timed if m["type"] == "http.response.body"]
    assert b"partial" in frames
    assert frames.count(mcp_http.KEEPALIVE_FRAME) == 0, (
        "the relay kept the stream alive instead of noticing the dead pump"
    )


@pytest.mark.usefixtures("_sidecar")
def test_a_pump_that_dies_without_reporting_still_closes_the_body(
    monkeypatch: pytest.MonkeyPatch,
    atlas_assertion: str,
) -> None:
    """Belt and braces for the same hazard: even a pump that queues NOTHING at
    all (cancelled, or killed by something it could not report) must not leave
    the relay spinning -- the idle branch notices the finished task and stops.
    """
    monkeypatch.setattr(mcp_http, "KEEPALIVE_INTERVAL_SECONDS", 0.05)

    async def _silent_death(_response: Any, _queue: asyncio.Queue) -> None:
        msg = "died before queuing anything"
        raise RuntimeError(msg)

    monkeypatch.setattr(mcp_http, "_drain_upstream", _silent_death)

    timed, _calls, _kwargs = _proxy(
        _StubUpstream(headers={"content-type": "text/event-stream"}),
        _scope(assertion=atlas_assertion),
    )

    closes = [
        m
        for _at, m in timed
        if m["type"] == "http.response.body" and m.get("more_body") is False
    ]
    assert len(closes) == 1, timed


@pytest.mark.usefixtures("_sidecar")
def test_proxy_forwards_the_request_body_and_the_allowlisted_headers(
    atlas_assertion: str,
) -> None:
    """AC: the allowlist is a pass list, not only a block list -- dropping
    `content-type` from it would 415 every proxied call at the sidecar's own
    transport -- and the JSON-RPC body itself must reach the sidecar.
    """
    inbound = {
        b"content-type": b"application/json",
        b"accept": b"application/json, text/event-stream",
        b"mcp-protocol-version": b"2026-07-28",
        b"traceparent": b"00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
        b"tracestate": b"pyforge=42",
    }
    assert {name.decode() for name in inbound} == {
        name.decode() for name in mcp_http.FORWARDED_REQUEST_HEADERS
    }, "this fixture must cover the whole allowlist, or a gap goes unproven"
    scope = _scope(
        assertion=atlas_assertion,
        extra_headers=tuple(
            (name, value)
            for name, value in inbound.items()
            if name != b"content-type"  # _scope already carries it
        ),
    )
    payload = json.dumps(_request("tools/list")).encode()

    _timed, calls, _kwargs = _proxy(
        _StubUpstream(),
        scope,
        body=payload,
    )

    forwarded = {key.lower(): value for key, value in calls[0]["headers"].items()}
    for name, value in inbound.items():
        assert forwarded.get(name.decode()) == value.decode(), (
            f"{name.decode()} did not survive the hop: {forwarded!r}"
        )
    assert calls[0]["content"] == payload, "the JSON-RPC body never reached the sidecar"
    assert calls[0]["method"] == "POST"
    assert calls[0]["url"] == "http://mcp-host:8090/stations/atlas/mcp"


@pytest.mark.usefixtures("_sidecar")
def test_proxy_passes_the_upstream_status_through(atlas_assertion: str) -> None:
    """A proxy that hardcoded 200 would hide every sidecar refusal."""
    upstream = _StubUpstream(status_code=int(HTTPStatus.SERVICE_UNAVAILABLE))

    timed, _calls, _kwargs = _proxy(upstream, _scope(assertion=atlas_assertion))

    start = next(m for _at, m in timed if m["type"] == "http.response.start")
    assert start["status"] == HTTPStatus.SERVICE_UNAVAILABLE


@pytest.mark.usefixtures("_sidecar")
def test_proxy_drops_response_framing_it_re_frames(atlas_assertion: str) -> None:
    """The sidecar's own content-length/encoding describe ITS wire form, not
    the decoded chunks this proxy re-frames; forwarding them corrupts the
    response.
    """
    upstream = _StubUpstream(
        headers={
            "content-type": "application/json",
            "content-length": "999",
            "content-encoding": "gzip",
            "transfer-encoding": "chunked",
            "set-cookie": "sidecar=1",
            "mcp-protocol-version": "2026-07-28",
        },
    )

    timed, _calls, _kwargs = _proxy(upstream, _scope(assertion=atlas_assertion))

    start = next(m for _at, m in timed if m["type"] == "http.response.start")
    names = {name for name, _value in start["headers"]}
    assert b"content-type" in names
    assert b"mcp-protocol-version" in names
    for dropped in (
        b"content-length",
        b"content-encoding",
        b"transfer-encoding",
        b"set-cookie",
    ):
        assert dropped not in names, f"{dropped!r} survived the hop"
