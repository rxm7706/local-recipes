"""Story 9.1 — `DashboardIdentityMiddleware` proves AD-4's refuse-the-start
rule by execution: a fake ASGI `send` records every event it is called
with, so "no ASGI response event was ever sent" is asserted directly against
an empty list, not inferred from reading the middleware's source.
"""

from __future__ import annotations

import asyncio

import pytest

from pyforge.steward.dashboard.declarations import TrustedIngress
from pyforge.steward.dashboard.middleware import (
    DashboardIdentityMiddleware, UntrustedIngressError,
)

TRUSTED = TrustedIngress(
    addresses=("10.0.0.1",),
    identity_header="X-Forwarded-User",
    role_header="X-Forwarded-Role",
)


def _scope(client_host, headers=()):
    return {
        "type": "http",
        "client": (client_host, 54321),
        "headers": [
            (name.lower().encode("latin-1"), value.encode("latin-1"))
            for name, value in headers
        ],
    }


async def _receive():
    return {"type": "http.disconnect"}


def _fake_send(events):
    async def send(event):
        events.append(event)
    return send


def _fake_app(calls):
    async def app(scope, receive, send):
        calls.append(scope)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})
    return app


def test_trusted_ingress_with_identity_header_passes_through_and_sets_scope():
    events: list[dict] = []
    calls: list[dict] = []
    middleware = DashboardIdentityMiddleware(_fake_app(calls), TRUSTED)
    scope = _scope(
        "10.0.0.1",
        headers=[("X-Forwarded-User", "alice"), ("X-Forwarded-Role", "admin")],
    )

    asyncio.run(middleware(scope, _receive, _fake_send(events)))

    assert len(calls) == 1
    assert calls[0]["dashboard_identity"] == "alice"
    assert calls[0]["dashboard_role"] == "admin"
    assert events == [
        {"type": "http.response.start", "status": 200, "headers": []},
        {"type": "http.response.body", "body": b"ok"},
    ]


def test_untrusted_ingress_with_identity_header_raises_before_any_send():
    events: list[dict] = []
    calls: list[dict] = []
    middleware = DashboardIdentityMiddleware(_fake_app(calls), TRUSTED)
    # Peer address 203.0.113.9 is outside TRUSTED.addresses.
    scope = _scope("203.0.113.9", headers=[("X-Forwarded-User", "eve")])

    with pytest.raises(UntrustedIngressError):
        asyncio.run(middleware(scope, _receive, _fake_send(events)))

    assert calls == [], "the wrapped app must never be invoked for an untrusted-ingress identity header"
    assert events == [], "no ASGI response event may ever be sent -- the response cycle must never start"


def test_no_identity_header_passes_through_untouched_and_never_checks_ingress():
    events: list[dict] = []
    calls: list[dict] = []
    middleware = DashboardIdentityMiddleware(_fake_app(calls), TRUSTED)
    # Peer address is OUTSIDE the trusted ingress too -- proves the ingress
    # check never triggers at all when there is no identity header.
    scope = _scope("203.0.113.9", headers=[])

    asyncio.run(middleware(scope, _receive, _fake_send(events)))

    assert len(calls) == 1
    assert "dashboard_identity" not in calls[0]
    assert "dashboard_role" not in calls[0]
    assert events, "the wrapped app must run normally when no identity header arrives at all"
