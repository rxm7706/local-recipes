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

When the identity header is absent, this middleware passes through
untouched — the ingress check never triggers at all, matching CAP-1's
"degrades to a single known-unprivileged identity rather than to an error".

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
    ASGI response never starts. Never caught and converted into an ordinary
    response by this module; the wrapping ASGI server sees the connection
    abort.
    """


def _header_value(scope: Scope, header_name: str) -> str | None:
    """Case-insensitively read one header from an ASGI `scope["headers"]` list.

    ASGI headers are a list of ``(name: bytes, value: bytes)`` pairs, names
    conventionally lowercased by the server but not guaranteed to be by
    every caller (including this module's own tests), so comparison is
    explicitly case-insensitive on both sides.
    """
    target = header_name.lower().encode("latin-1")
    for raw_name, raw_value in scope.get("headers") or ():
        if raw_name.lower() == target:
            return raw_value.decode("latin-1")
    return None


class DashboardIdentityMiddleware:
    """ASGI3 callable wrapping an inner ASGI app with `ingress`-gated identity extraction."""

    def __init__(self, app: ASGIApp, ingress: TrustedIngress) -> None:
        self.app = app
        self.ingress = ingress

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        identity = _header_value(scope, self.ingress.identity_header)
        if identity is None:
            # No identity header at all: pass through untouched. The ingress
            # check never triggers -- there is nothing to trust or distrust.
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        peer_host = client[0] if client else None
        if peer_host not in self.ingress.addresses:
            # AD-4: refuse the START, not the request -- raise before `send`
            # (and therefore before the wrapped app) is ever invoked.
            raise UntrustedIngressError(
                f"identity header {self.ingress.identity_header!r} arrived "
                f"from {peer_host!r}, outside the declared trusted ingress "
                f"{self.ingress.addresses!r} — refusing to start the "
                "response"
            )

        scope["dashboard_identity"] = identity
        scope["dashboard_role"] = _header_value(scope, self.ingress.role_header)
        await self.app(scope, receive, send)
