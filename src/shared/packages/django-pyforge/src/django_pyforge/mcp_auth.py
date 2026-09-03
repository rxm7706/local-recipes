"""Transport authorization for ``/stations/<name>/mcp`` (CAP-4, red-team T-4).

``dispatch_station_mcp`` runs first in the host's ASGI dispatch -- before
sessions, CSRF, allauth and every other middleware -- so no middleware can
authorize an MCP call. This module IS that gate, and it runs for every JSON-RPC
method: ``initialize`` and ``tools/list`` are authorized exactly like
``tools/call``, because the gate reads headers only and never inspects the
body. A tool reachable without an assertion is the bug this closes.

Django-free by construction (module scope imports ``jwt`` transitively through
``assertion.verify``, nothing else), so the same verifier runs in front of the
in-process laptop path and in front of the sidecar proxy -- one code path,
transport-agnostic. The public key resolves from ``PYFORGE_ASSERTION_PUBLIC_KEY``
in the environment, falling back to the Django setting of the same name when a
configured Django happens to be importable.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

from django_pyforge.assertion.exceptions import AssertionRefusedError
from django_pyforge.assertion.exceptions import WrongAudienceError
from django_pyforge.assertion.schema import audience_for
from django_pyforge.assertion.verify import verify_assertion_claims

PUBLIC_KEY_ENV = "PYFORGE_ASSERTION_PUBLIC_KEY"
AUTHORIZATION_HEADER = b"authorization"
BEARER_SCHEME = "bearer "


@dataclass(frozen=True)
class AuthorizedCall:
    """A verified assertion: the raw token plus the claims it carried."""

    token: str
    claims: dict[str, Any]


@dataclass(frozen=True)
class TransportRefusal:
    """A refusal the caller must send instead of routing the request.

    ``retry_after`` is seconds and defaults to 0, meaning "retrying will not
    help" — an unsigned token stays unsigned. Story 42.2's rate limiter is the
    one refusal a caller *should* retry, so it is the one that sets it.
    """

    status: HTTPStatus
    error: str
    reason: str
    retry_after: int = 0

    def body(self) -> bytes:
        payload: dict[str, Any] = {"error": self.error}
        if self.retry_after > 0:
            payload["retry_after"] = int(self.retry_after)
        return json.dumps(payload).encode("utf-8")

    def headers(self) -> list[tuple[bytes, bytes]]:
        """``Retry-After``, only when there is a wait worth naming."""
        if self.retry_after <= 0:
            return []
        return [(b"retry-after", str(int(self.retry_after)).encode("ascii"))]


def bearer_from_headers(headers: Any) -> str | None:
    """The bearer token on an ASGI header list, or ``None``."""
    for key, value in headers or ():
        if bytes(key).lower() != AUTHORIZATION_HEADER:
            continue
        raw = bytes(value).decode("latin-1").strip()
        if raw.lower().startswith(BEARER_SCHEME):
            return raw[len(BEARER_SCHEME) :].strip() or None
        return None
    return None


def resolve_public_pem() -> str:
    """The assertion public key: environment first, Django setting second."""
    raw = os.environ.get(PUBLIC_KEY_ENV, "")
    pem = raw.strip() if isinstance(raw, str) else ""
    if pem:
        return pem
    return _settings_public_pem()


def _settings_public_pem() -> str:
    """The Django setting, when a *configured* Django is importable.

    Imported lazily and guarded on both failure modes so this module stays
    importable in an interpreter with no Django at all, and an unconfigured
    Django reads as "no key" (a 503 refusal) rather than raising out of the
    transport gate.
    """
    try:
        from django.conf import settings
        from django.core.exceptions import ImproperlyConfigured
    except ImportError:
        return ""
    try:
        raw = getattr(settings, PUBLIC_KEY_ENV, "")
    except ImproperlyConfigured:
        return ""
    return raw.strip() if isinstance(raw, str) else ""


def authorize_station_scope(
    scope: dict[str, Any],
    station: str,
    *,
    public_pem: str | None = None,
) -> AuthorizedCall | TransportRefusal:
    """Authorize one station MCP request from its ASGI ``scope``.

    Returns the verified call when the request may be routed and a
    ``TransportRefusal`` when it may not -- never ``None``, so a caller cannot
    read "nothing went wrong" as "authorized". An assertion minted for another
    station is 403; everything else that fails is 401; an unconfigured verifier
    is 503, never a pass.
    """
    token = bearer_from_headers(scope.get("headers"))
    if token is None:
        return TransportRefusal(
            HTTPStatus.UNAUTHORIZED,
            "assertion required",
            "no bearer assertion on the request",
        )
    pem = public_pem if public_pem is not None else resolve_public_pem()
    if not pem:
        return TransportRefusal(
            HTTPStatus.SERVICE_UNAVAILABLE,
            "verifier not configured",
            f"{PUBLIC_KEY_ENV} is not configured",
        )
    try:
        claims = verify_assertion_claims(
            token,
            audience=audience_for(station),
            public_pem=pem,
        )
    except WrongAudienceError as exc:
        return TransportRefusal(
            HTTPStatus.FORBIDDEN,
            "wrong audience",
            _reason(exc),
        )
    except (AssertionRefusedError, TypeError, ValueError) as exc:
        return TransportRefusal(
            HTTPStatus.UNAUTHORIZED,
            "assertion refused",
            _reason(exc),
        )
    return AuthorizedCall(token=token, claims=dict(claims))


def _reason(exc: BaseException) -> str:
    name = type(exc).__name__
    message = str(exc).strip()
    return f"{name}: {message}" if message else name
