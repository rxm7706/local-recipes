"""Story 9.1 — `DashboardIdentityMiddleware`: CAP-1 + AD-4's refuse-the-start rule.

A raw ASGI3 callable (no Django/Channels middleware base class needed — the
ASGI3 signature IS the contract): extracts identity/role from the
`TrustedIngress`-declared proxy headers on the ASGI `scope`, and when an
identity header arrives on a connection whose peer address (`scope["client"]`)
is outside the declared `TrustedIngress`, raises `UntrustedIngressError`
*before* the wrapped application — and therefore `send()` — is ever invoked.
The ASGI response cycle only becomes real once `send()` is called with
`http.response.start`; refusing before that call means the connection is
aborted rather than completing an ordinary (e.g. 403) response cycle. See
the story spec's Design Notes ("Refuse the start, not the request") for the
full rationale.

When the identity header is absent, this middleware passes through with no
identity set — the ingress check never triggers at all, matching CAP-1's
"degrades to a single known-unprivileged identity rather than to an error".
Any pre-existing identity/role key on the incoming `scope` is cleared on
that path rather than inherited, so an upstream middleware cannot plant an
identity this one then appears to have vouched for (review pass 2).

A *duplicated* identity or role header is refused outright (review pass 2).
ASGI preserves duplicate headers in arrival order, so a proxy that only
appends its own `X-Forwarded-User` — rather than replacing a client-supplied
one — leaves the client's value first in the list, and reading "the first
match" would hand the attacker's chosen identity and role straight through a
passing ingress check. There is no safe way to guess which copy the proxy
meant, so the ambiguity is fail-closed, on the same refuse-the-start path as
an untrusted peer.

Imports nothing from `django`/`channels` — the ASGI3 callable shape is
protocol, not framework, per AD-8, so this module works standalone even
without the `[dashboard]` extra installed (it still lives under `dashboard/`
and ships only with the rest of the package by convention, not because it
needs the extra itself).
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from .declarations import TrustedIngress

Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


class UntrustedIngressError(Exception):
    """AD-4: an identity header arrived from outside the declared `TrustedIngress`.

    Raised before `send()` is ever called for the connection it names — the
    ASGI response never starts, which is the property this module owns and
    its tests assert directly. What the surrounding ASGI *server* then does
    with an exception propagating out of the application is that server's
    policy, not this module's: some abort the connection, others render a
    generic 500. Guaranteeing a specific on-the-wire outcome end-to-end is
    the deployment perimeter's job (Story 9.5) and the proof suite's to
    demonstrate (Story 9.6); see `deferred-work.md`.
    """


def _header_values(scope: Scope, header_name: str) -> list[str]:
    """Case-insensitively read ALL copies of one header from `scope["headers"]`.

    ASGI headers are a list of ``(name: bytes, value: bytes)`` pairs, names
    conventionally lowercased by the server but not guaranteed to be by
    every caller (including this module's own tests), so comparison is
    explicitly case-insensitive on both sides. Every match is returned, not
    just the first: a duplicated identity header is a trust-boundary
    ambiguity the caller must refuse rather than silently resolve.
    """
    target = header_name.lower().encode("latin-1")
    return [
        raw_value.decode("latin-1")
        for raw_name, raw_value in scope.get("headers") or ()
        if raw_name.lower() == target
    ]


class AmbiguousIdentityHeaderError(UntrustedIngressError):
    """AD-4: the identity or role header arrived more than once on one request.

    A subclass so `except UntrustedIngressError` still catches it: both are
    the same refusal on the same refuse-the-start path, and both mean the
    declared header cannot be trusted to say who the caller is.
    """


def _clear_identity(scope: Scope) -> None:
    """Drop any identity/role keys this middleware did not itself just set.

    Only this middleware may vouch for `scope["dashboard_identity"]`. On
    every path that does NOT establish an identity, a value planted upstream
    is removed rather than inherited.
    """
    scope.pop("dashboard_identity", None)
    scope.pop("dashboard_role", None)


class DashboardIdentityMiddleware:
    """ASGI3 callable wrapping an inner ASGI app with `ingress`-gated identity extraction."""

    def __init__(self, app: ASGIApp, ingress: TrustedIngress) -> None:
        self.app = app
        self.ingress = ingress

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        identities = _header_values(scope, self.ingress.identity_header)

        if len(identities) > 1:
            # A duplicated identity header means one copy is the proxy's and
            # one is the client's, with no way to tell which is which. Refuse
            # on the same pre-`send` path as an untrusted peer.
            raise AmbiguousIdentityHeaderError(
                f"identity header {self.ingress.identity_header!r} arrived "
                f"{len(identities)} times ({identities!r}) — a duplicated "
                "identity header cannot be attributed to the trusted proxy; "
                "refusing to start the response"
            )

        if not identities:
            # No identity header at all: pass through with no identity. The
            # ingress check never triggers -- there is nothing to trust or
            # distrust.
            _clear_identity(scope)
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        peer_host = client[0] if client else None
        if peer_host not in self.ingress.addresses:
            # AD-4: refuse the START, not the request -- raise before `send`
            # (and therefore before the wrapped app) is ever invoked. Note
            # this fires for a PRESENT header regardless of its value: an
            # empty one still asserts identity from an undeclared path.
            raise UntrustedIngressError(
                f"identity header {self.ingress.identity_header!r} arrived "
                f"from {peer_host!r}, outside the declared trusted ingress "
                f"{self.ingress.addresses!r} — refusing to start the "
                "response"
            )

        roles = _header_values(scope, self.ingress.role_header)
        if len(roles) > 1:
            raise AmbiguousIdentityHeaderError(
                f"role header {self.ingress.role_header!r} arrived "
                f"{len(roles)} times ({roles!r}) — a duplicated role header "
                "cannot be attributed to the trusted proxy; refusing to "
                "start the response"
            )

        identity = identities[0]
        if not identity:
            # Header present but carrying no identity. CAP-1 degrades to a
            # known-unprivileged identity, which is the no-identity-set state
            # -- never an empty-string identity a downstream consumer has to
            # remember is falsy-but-present.
            _clear_identity(scope)
            await self.app(scope, receive, send)
            return

        scope["dashboard_identity"] = identity
        scope["dashboard_role"] = roles[0] if roles else None
        await self.app(scope, receive, send)
