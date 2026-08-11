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
    AmbiguousIdentityHeaderError, DashboardIdentityMiddleware, UntrustedIngressError,
)

TRUSTED = TrustedIngress(
    addresses=("10.0.0.1",),
    identity_header="X-Forwarded-User",
    role_header="X-Forwarded-Role",
)


def _scope(client_host, headers=(), **extra):
    scope = {
        "type": "http",
        "client": (client_host, 54321),
        "headers": [
            (name.lower().encode("latin-1"), value.encode("latin-1"))
            for name, value in headers
        ],
    }
    scope.update(extra)
    return scope


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


def test_a_duplicated_identity_header_is_refused_before_any_send():
    """Review pass 2 (Blind Hunter + Edge Case Hunter, reproduced by
    execution against the real middleware): ASGI preserves duplicate headers
    in arrival order, and reading only the FIRST match handed a
    client-supplied `X-Forwarded-User` priority over the trusted proxy's own
    appended copy -- identity resolved to 'eve', role to 'admin', while the
    ingress check happily passed because the connection really did come from
    the proxy. Full spoof, from a trusted peer, past every existing test.
    """
    events: list[dict] = []
    calls: list[dict] = []
    middleware = DashboardIdentityMiddleware(_fake_app(calls), TRUSTED)
    # Client's copies first, proxy's appended second -- the nginx
    # `add_header`-style shape rather than `proxy_set_header`.
    scope = _scope(
        "10.0.0.1",
        headers=[
            ("X-Forwarded-User", "eve"), ("X-Forwarded-Role", "admin"),
            ("X-Forwarded-User", "alice"), ("X-Forwarded-Role", "viewer"),
        ],
    )

    with pytest.raises(AmbiguousIdentityHeaderError):
        asyncio.run(middleware(scope, _receive, _fake_send(events)))

    assert calls == [], "the wrapped app must never run on an ambiguous identity"
    assert events == [], "an ambiguous identity must refuse the START, like an untrusted peer"
    assert scope.get("dashboard_identity") is None, "no identity may be vouched for"


def test_a_duplicated_role_header_is_refused_even_from_a_trusted_peer():
    """The role header carries the privilege level, so the same ambiguity is
    the same refusal -- a single identity header with two roles must not
    silently resolve to whichever copy happens to be first.
    """
    events: list[dict] = []
    calls: list[dict] = []
    middleware = DashboardIdentityMiddleware(_fake_app(calls), TRUSTED)
    scope = _scope(
        "10.0.0.1",
        headers=[
            ("X-Forwarded-User", "alice"),
            ("X-Forwarded-Role", "admin"), ("X-Forwarded-Role", "viewer"),
        ],
    )

    with pytest.raises(AmbiguousIdentityHeaderError):
        asyncio.run(middleware(scope, _receive, _fake_send(events)))

    assert calls == []
    assert events == []


def test_ambiguous_identity_is_catchable_as_untrusted_ingress():
    """`AmbiguousIdentityHeaderError` subclasses `UntrustedIngressError` so an
    adopter's single `except UntrustedIngressError` keeps covering every
    refusal this middleware makes.
    """
    assert issubclass(AmbiguousIdentityHeaderError, UntrustedIngressError)


def test_an_empty_identity_header_value_sets_no_identity():
    """Review pass 2: `X-Forwarded-User:` (present, empty) passed the
    `is None` gate and put `''` on the scope -- a falsy-but-present identity
    every downstream consumer would have to remember to special-case.
    CAP-1's degradation is the no-identity state, not an empty-string one.
    """
    events: list[dict] = []
    calls: list[dict] = []
    middleware = DashboardIdentityMiddleware(_fake_app(calls), TRUSTED)
    scope = _scope("10.0.0.1", headers=[("X-Forwarded-User", ""), ("X-Forwarded-Role", "admin")])

    asyncio.run(middleware(scope, _receive, _fake_send(events)))

    assert len(calls) == 1
    assert "dashboard_identity" not in calls[0], "an empty header value is not an identity"
    assert "dashboard_role" not in calls[0], "no role may survive without an identity to attach it to"
    assert events, "an anonymous request still gets a normal response"


def test_an_empty_identity_header_from_an_untrusted_peer_is_still_refused():
    """The ingress check keys on the header being PRESENT, not on it carrying
    a value: an empty `X-Forwarded-User` from an undeclared path is still an
    assertion of identity arriving from somewhere it may not.
    """
    events: list[dict] = []
    calls: list[dict] = []
    middleware = DashboardIdentityMiddleware(_fake_app(calls), TRUSTED)
    scope = _scope("203.0.113.9", headers=[("X-Forwarded-User", "")])

    with pytest.raises(UntrustedIngressError):
        asyncio.run(middleware(scope, _receive, _fake_send(events)))

    assert calls == []
    assert events == []


def test_an_upstream_planted_identity_is_cleared_not_inherited():
    """Review pass 2: the no-identity-header path passed the scope through
    untouched, so a `dashboard_identity` planted by an earlier middleware
    survived and appeared to have been vouched for by this one. Only this
    middleware may vouch for that key.
    """
    events: list[dict] = []
    calls: list[dict] = []
    middleware = DashboardIdentityMiddleware(_fake_app(calls), TRUSTED)
    scope = _scope(
        "203.0.113.9", headers=[],
        dashboard_identity="planted", dashboard_role="admin",
    )

    asyncio.run(middleware(scope, _receive, _fake_send(events)))

    assert len(calls) == 1
    assert "dashboard_identity" not in calls[0], "a planted identity must be cleared, not inherited"
    assert "dashboard_role" not in calls[0]
