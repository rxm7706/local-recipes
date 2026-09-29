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

**Deployment precondition (review pass 3).** `scope["client"]` is whatever
the ASGI *server* reports, which is not always the TCP peer. daphne run with
`--proxy-headers` and uvicorn with `proxy_headers=True` (its DEFAULT) both
overwrite `scope["client"]` with the leftmost `X-Forwarded-For` entry and
perform no trusted-hop validation — verified against the installed daphne's
`daphne.utils.parse_x_forwarded_for`. Under a proxy that APPENDS to
`X-Forwarded-For` (the standard nginx `$proxy_add_x_forwarded_for`), that
leftmost entry is client-supplied, which both refuses legitimate traffic and
lets a caller name any address it likes. So AD-4's check is only as sound as
the server's client-address reporting: the deployment must either leave
proxy-header parsing OFF (so `scope["client"]` is the real TCP peer) or
terminate `X-Forwarded-For` at a hop it controls. Enforcing that is the
deployment perimeter's job (Story 9.5) and the proof suite's to demonstrate
end-to-end (Story 9.6); this module cannot see its server's configuration.
See the deferred-work ledger.

When the identity header is absent, this middleware passes through with no
identity set — the ingress check never triggers at all, matching CAP-1's
"degrades to a single known-unprivileged identity rather than to an error".
Any pre-existing identity/role key on the incoming `scope` is cleared up
front, on every path including the refusals, so an upstream middleware
cannot plant an identity this one then appears to have vouched for (review
pass 2; extended to the refusal paths in pass 3, since the adopter error
handler those exceptions invite would otherwise read a planted identity off
the scope).

A *duplicated* identity or role header is refused outright (review pass 2).
ASGI preserves duplicate headers in arrival order, so a proxy that only
appends its own `X-Forwarded-User` — rather than replacing a client-supplied
one — leaves the client's value first in the list, and reading "the first
match" would hand the attacker's chosen identity and role straight through a
passing ingress check. There is no safe way to guess which copy the proxy
meant, so the ambiguity is fail-closed, on the same refuse-the-start path as
an untrusted peer. This detects duplication as ASGI represents it: separate
`(name, value)` pairs. A duplicate that reached the server already folded
into one comma-separated field line is indistinguishable here from a single
value that legitimately contains a comma (an LDAP DN, say), so it is not
refused — see the deferred-work ledger.

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
    demonstrate (Story 9.6); see the deferred-work ledger — drafted run-local
    and promoted into
    ``_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md``
    when this story lands, as this package's `__init__` docstring explains
    (review pass 4: naming only the tracked path asserted the entries were
    already there, and they are not yet).

    The message names the offending peer but deliberately NOT the declared
    ingress list, and the ambiguity subclass reports a count rather than the
    identity values it saw (review pass 3): an ASGI server that renders a
    propagated exception as a DEBUG 500 would otherwise disclose the internal
    trust topology to the very caller that was refused, and push identity
    values into every log line.
    """


def _header_values(scope: Scope, header_name: str) -> list[str]:
    """Case-insensitively read ALL copies of one header from `scope["headers"]`.

    ASGI headers are a list of ``(name: bytes, value: bytes)`` pairs. Servers
    lowercase the names by convention, but the ASGI spec does not require it
    of anything that constructs a scope, so comparison is explicitly
    case-insensitive on both sides rather than trusting the convention.
    (Corrected in review pass 3: this previously justified itself by claiming
    "this module's own tests" send non-lowercased names, which they do not —
    `_scope` lowercases every one. The mixed-case path is covered by a test
    added in that pass instead.) Every match is returned, not just the first:
    a duplicated identity header is a trust-boundary ambiguity the caller
    must refuse rather than silently resolve.
    """
    target = header_name.lower().encode("latin-1")
    return [
        raw_value.decode("latin-1") for raw_name, raw_value in scope.get("headers") or () if raw_name.lower() == target
    ]


class AmbiguousIdentityHeaderError(UntrustedIngressError):
    """AD-4: the identity or role header arrived more than once on one request.

    A subclass so `except UntrustedIngressError` still catches it: both are
    the same refusal on the same refuse-the-start path, and both mean the
    declared header cannot be trusted to say who the caller is.
    """


def _clear_identity(scope: Scope) -> None:
    """Drop any identity/role keys this middleware did not itself just set.

    Only this middleware may vouch for `scope["dashboard_identity"]`. Called
    up front on EVERY request (review pass 3), so a value planted upstream is
    removed rather than inherited on the refusal paths too — not only on the
    pass-through paths, which is all pass 2's version covered. It matters on
    a refusal precisely because `UntrustedIngressError`'s own docstring
    invites an adopter to catch it: a handler that then rendered anything
    from the scope would have read the planted identity.
    """
    scope.pop("dashboard_identity", None)
    scope.pop("dashboard_role", None)


class DashboardIdentityMiddleware:
    """ASGI3 callable wrapping an inner ASGI app with `ingress`-gated identity extraction."""

    def __init__(self, app: ASGIApp, ingress: TrustedIngress) -> None:
        # Checked by type, at wiring time (review pass 3). `declarations.py`
        # exists so a misconfigured adopter fails loudly at config time, but
        # its sole consumer accepted any duck-typed object -- so passing
        # something with `addresses="10.0.0.100"` (a bare string) restored
        # exactly the substring-membership hole `TrustedIngress` validates
        # against, and `ingress=None` failed only on the first live request
        # instead of here.
        if not isinstance(ingress, TrustedIngress):
            raise TypeError(
                f"DashboardIdentityMiddleware requires a TrustedIngress, got "
                f"{type(ingress).__name__} — its construction-time validation "
                f"is what keeps AD-4's membership check from degrading into a "
                f"substring match, so it cannot be bypassed by a look-alike"
            )
        self.app = app
        self.ingress = ingress

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Before anything else, and on every path including the refusals:
        # only this middleware may vouch for these keys.
        _clear_identity(scope)

        identities = _header_values(scope, self.ingress.identity_header)

        if len(identities) > 1:
            # A duplicated identity header means one copy is the proxy's and
            # one is the client's, with no way to tell which is which. Refuse
            # on the same pre-`send` path as an untrusted peer. The count is
            # reported, not the values -- they are attacker-supplied and this
            # text can reach a log or a DEBUG 500 page.
            raise AmbiguousIdentityHeaderError(
                f"identity header {self.ingress.identity_header!r} arrived "
                f"{len(identities)} times — a duplicated identity header "
                "cannot be attributed to the trusted proxy; refusing to start "
                "the response"
            )

        if not identities:
            # No identity header at all: pass through with no identity. The
            # ingress check never triggers -- there is nothing to trust or
            # distrust.
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        peer_host = client[0] if client else None
        if peer_host not in self.ingress.addresses:
            # AD-4: refuse the START, not the request -- raise before `send`
            # (and therefore before the wrapped app) is ever invoked. Note
            # this fires for a PRESENT header regardless of its value: an
            # empty one still asserts identity from an undeclared path.
            #
            # The declared ingress list is deliberately NOT in the message:
            # a server that renders this as a DEBUG 500 would hand the
            # internal trust topology to the caller it just refused. The
            # operator already has the declaration; the peer host is the
            # datum they do not.
            raise UntrustedIngressError(
                f"identity header {self.ingress.identity_header!r} arrived "
                f"from {peer_host!r}, outside the declared trusted ingress "
                f"({len(self.ingress.addresses)} declared address(es)) — "
                "refusing to start the response"
            )

        roles = _header_values(scope, self.ingress.role_header)
        if len(roles) > 1:
            raise AmbiguousIdentityHeaderError(
                f"role header {self.ingress.role_header!r} arrived "
                f"{len(roles)} times — a duplicated role header cannot be "
                "attributed to the trusted proxy; refusing to start the "
                "response"
            )

        identity = identities[0]
        if not identity.strip():
            # Header present but carrying no identity. CAP-1 degrades to a
            # known-unprivileged identity, which is the no-identity-set state
            # -- never an empty-string identity a downstream consumer has to
            # remember is falsy-but-present.
            #
            # `.strip()`, not truthiness (review pass 4): pass 2/3 closed the
            # `''` case, but `'   '` is TRUTHY, so a whitespace-only header
            # sailed past a truthiness gate and landed on the scope -- worse
            # than `''`, because it also sails past the downstream `if
            # identity:` guard those passes assumed. Only the BLANK test is
            # widened here; the value itself is still stored verbatim, since
            # trimming/normalizing a real identity is the identity-model
            # decision deferred to Story 9.3's audit rows.
            await self.app(scope, receive, send)
            return

        scope["dashboard_identity"] = identity
        # A blank role establishes no role, for the same reason and by the
        # same `.strip()` test as the identity above (review pass 3 for `''`,
        # widened to whitespace-only in pass 4): a falsy-but-present role is
        # the exact state the identity path was changed to avoid -- and one
        # `AccessDeclaration` forbids declaring, since it raises on both an
        # empty and a whitespace-only role name, so the middleware would
        # otherwise manufacture a role an adopter is not allowed to declare.
        role = roles[0] if roles else ""
        scope["dashboard_role"] = role if role.strip() else None
        await self.app(scope, receive, send)
