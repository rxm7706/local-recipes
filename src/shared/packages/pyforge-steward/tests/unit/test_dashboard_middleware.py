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
    AmbiguousIdentityHeaderError,
    DashboardIdentityMiddleware,
    UntrustedIngressError,
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
        "headers": [(name.lower().encode("latin-1"), value.encode("latin-1")) for name, value in headers],
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
            ("X-Forwarded-User", "eve"),
            ("X-Forwarded-Role", "admin"),
            ("X-Forwarded-User", "alice"),
            ("X-Forwarded-Role", "viewer"),
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
            ("X-Forwarded-Role", "admin"),
            ("X-Forwarded-Role", "viewer"),
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
        "203.0.113.9",
        headers=[],
        dashboard_identity="planted",
        dashboard_role="admin",
    )

    asyncio.run(middleware(scope, _receive, _fake_send(events)))

    assert len(calls) == 1
    assert "dashboard_identity" not in calls[0], "a planted identity must be cleared, not inherited"
    assert "dashboard_role" not in calls[0]


@pytest.mark.parametrize(
    "peer,headers",
    [
        # Untrusted peer -> UntrustedIngressError.
        ("203.0.113.9", [("X-Forwarded-User", "eve")]),
        # Trusted peer, duplicated identity -> AmbiguousIdentityHeaderError.
        ("10.0.0.1", [("X-Forwarded-User", "eve"), ("X-Forwarded-User", "alice")]),
    ],
)
def test_a_planted_identity_is_cleared_on_the_refusal_paths_too(peer, headers):
    """Review pass 3: pass 2's `_clear_identity` fix covered only the two
    pass-through paths, so a planted identity SURVIVED both refusals.

    That matters because `UntrustedIngressError`'s own docstring invites an
    adopter to catch it (and `AmbiguousIdentityHeaderError` subclasses it
    precisely so one `except` covers both) — a handler that then rendered
    anything from the scope would read `dashboard_identity='planted-admin'`
    and see it as vouched for by this middleware.
    """
    events: list[dict] = []
    calls: list[dict] = []
    middleware = DashboardIdentityMiddleware(_fake_app(calls), TRUSTED)
    scope = _scope(
        peer,
        headers=headers,
        dashboard_identity="planted-admin",
        dashboard_role="admin",
    )

    with pytest.raises(UntrustedIngressError):
        asyncio.run(middleware(scope, _receive, _fake_send(events)))

    assert "dashboard_identity" not in scope, "a refused request must not leave a planted identity on the scope"
    assert "dashboard_role" not in scope
    assert events == []


def test_an_empty_role_header_value_sets_no_role():
    """Review pass 3: pass 2 fixed the present-but-empty IDENTITY header but
    left the same shape on the field that carries privilege — an empty
    `X-Forwarded-Role` set `dashboard_role=''`, the exact falsy-but-present
    state the identity fix existed to eliminate.

    It is also a value the declaration layer forbids: `AccessDeclaration`
    raises on an empty role name, so the middleware was manufacturing a role
    an adopter cannot declare.
    """
    events: list[dict] = []
    calls: list[dict] = []
    middleware = DashboardIdentityMiddleware(_fake_app(calls), TRUSTED)
    scope = _scope("10.0.0.1", headers=[("X-Forwarded-User", "alice"), ("X-Forwarded-Role", "")])

    asyncio.run(middleware(scope, _receive, _fake_send(events)))

    assert len(calls) == 1
    assert calls[0]["dashboard_identity"] == "alice"
    assert calls[0]["dashboard_role"] is None, "an empty role header value is not a role"


def test_the_refusal_message_never_discloses_the_declared_ingress():
    """Review pass 3: the message embedded the full declared address tuple,
    and per this module's own docstring an ASGI server may render a propagated
    exception as a DEBUG 500 — handing the internal trust topology to the very
    caller that was just refused. The peer host stays (the operator does not
    already have it); the declaration does not (they do).
    """
    ingress = TrustedIngress(
        addresses=("10.42.7.11", "internal-edge-proxy-01"),
        identity_header="X-Forwarded-User",
        role_header="X-Forwarded-Role",
    )
    middleware = DashboardIdentityMiddleware(_fake_app([]), ingress)
    scope = _scope("203.0.113.9", headers=[("X-Forwarded-User", "eve")])

    with pytest.raises(UntrustedIngressError) as excinfo:
        asyncio.run(middleware(scope, _receive, _fake_send([])))

    message = str(excinfo.value)
    assert "203.0.113.9" in message, "the operator needs the offending peer"
    for declared in ingress.addresses:
        assert declared not in message, f"the declared ingress {declared!r} must not be disclosed"


def test_the_ambiguity_message_reports_a_count_not_the_identity_values():
    """Same reasoning one step further: the duplicated values are
    attacker-supplied, and this text reaches logs (and a DEBUG error page).
    """
    middleware = DashboardIdentityMiddleware(_fake_app([]), TRUSTED)
    scope = _scope(
        "10.0.0.1",
        headers=[("X-Forwarded-User", "eve"), ("X-Forwarded-User", "alice")],
    )

    with pytest.raises(AmbiguousIdentityHeaderError) as excinfo:
        asyncio.run(middleware(scope, _receive, _fake_send([])))

    message = str(excinfo.value)
    assert "2 times" in message
    assert "eve" not in message and "alice" not in message


def test_the_middleware_refuses_an_ingress_that_is_not_a_trusted_ingress():
    """Review pass 3: `declarations.py` exists so a misconfigured adopter
    fails loudly at config time, but its only consumer accepted any
    duck-typed object — so an object carrying `addresses="10.0.0.100"` (a
    bare string) restored the substring-membership hole `TrustedIngress`
    validates against, and a peer of `10.0.0.1` was ACCEPTED because
    `"10.0.0.1" in "10.0.0.100"`. Reproduced before the fix.
    """
    from types import SimpleNamespace

    look_alike = SimpleNamespace(
        addresses="10.0.0.100",
        identity_header="X-Forwarded-User",
        role_header="X-Forwarded-Role",
    )

    with pytest.raises(TypeError, match="TrustedIngress"):
        DashboardIdentityMiddleware(_fake_app([]), look_alike)

    # And the trivial mistake fails at wiring time rather than on the first
    # live request.
    with pytest.raises(TypeError, match="TrustedIngress"):
        DashboardIdentityMiddleware(_fake_app([]), None)


def test_header_names_are_matched_case_insensitively_on_the_wire():
    """`_header_values` compares case-insensitively on both sides. Pass 3
    found its docstring justified that with a claim about this suite that was
    false (`_scope` lowercases every name), so the branch had no coverage —
    this supplies it by building the raw header pairs directly.
    """
    events: list[dict] = []
    calls: list[dict] = []
    middleware = DashboardIdentityMiddleware(_fake_app(calls), TRUSTED)
    scope = {
        "type": "http",
        "client": ("10.0.0.1", 54321),
        # Deliberately NOT lowercased, unlike `_scope`.
        "headers": [(b"X-Forwarded-User", b"alice"), (b"X-FORWARDED-ROLE", b"admin")],
    }

    asyncio.run(middleware(scope, _receive, _fake_send(events)))

    assert calls[0]["dashboard_identity"] == "alice"
    assert calls[0]["dashboard_role"] == "admin"


def test_whitespace_only_identity_header_establishes_no_identity():
    """Review pass 4: passes 2 and 3 closed the present-but-EMPTY identity
    header, but the guard they used was truthiness — and `"   "` is truthy.
    So a whitespace-only header landed on the scope as a real identity
    (reproduced: `dashboard_identity == '   '`), which is worse than `''`:
    it also sails past the downstream `if identity:` check those passes
    assumed would catch a blank one.

    Only the BLANK test widens here. A real identity value is still stored
    verbatim — trimming or normalizing one is the identity-model decision
    deferred to Story 9.3's audit rows.
    """
    events: list[dict] = []
    calls: list[dict] = []
    middleware = DashboardIdentityMiddleware(_fake_app(calls), TRUSTED)
    scope = _scope("10.0.0.1", headers=[("X-Forwarded-User", "   ")])

    asyncio.run(middleware(scope, _receive, _fake_send(events)))

    assert calls, "a blank identity degrades to no identity — it is not a refusal"
    assert "dashboard_identity" not in scope
    assert "dashboard_role" not in scope


def test_whitespace_only_role_header_establishes_no_role():
    """Review pass 4: the same shape on the field that carries PRIVILEGE.
    Pass 3 fixed the empty role; `"\\t"` stayed truthy and was set verbatim —
    and `AccessDeclaration` raises on a whitespace-only role name, so the
    middleware was manufacturing a role an adopter cannot declare.
    """
    events: list[dict] = []
    calls: list[dict] = []
    middleware = DashboardIdentityMiddleware(_fake_app(calls), TRUSTED)
    scope = _scope(
        "10.0.0.1",
        headers=[("X-Forwarded-User", "alice"), ("X-Forwarded-Role", "  ")],
    )

    asyncio.run(middleware(scope, _receive, _fake_send(events)))

    assert scope["dashboard_identity"] == "alice"
    assert scope["dashboard_role"] is None
