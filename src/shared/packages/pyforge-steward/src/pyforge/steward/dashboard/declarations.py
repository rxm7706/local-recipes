"""Story 9.1 — the "declared, not implemented" half of CAP-2 and AD-4.

Two frozen dataclasses an adopter fills in instead of hand-writing filtering
or hand-wiring a trust boundary. Neither performs any filtering, request
handling, or ingress checking itself — that is `middleware.py` (AD-4) and a
later story's job (CAP-2's filtering half). This module's only job is the
declaration schema plus construction-time validation, so a misconfigured
adopter fails loudly at config time rather than serving unfiltered rows or
trusting an undeclared network path.

Deliberately import-free of `django`/`channels` — plain `dataclasses`, so
this module (and its tests) work with or without the `[dashboard]` extra
installed.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AccessDeclaration:
    """CAP-2: the column that carries access, and the role vocabulary.

    ``access_column`` names the field of the master dataset that determines
    which rows a role may see; ``roles`` is the closed vocabulary of role
    names the adopter's dashboard recognizes. This class does not perform
    filtering — it is the statement an adopter makes instead of writing one.
    """

    access_column: str
    roles: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.access_column:
            raise ValueError(
                "AccessDeclaration.access_column must not be empty — a "
                "dashboard cannot declare row-level access without naming "
                "the column that carries it"
            )
        if not isinstance(self.roles, tuple):
            raise TypeError(
                f"AccessDeclaration.roles must be a tuple of role names, "
                f"got {type(self.roles).__name__} — a bare string would "
                f"silently be iterated character-by-character instead of "
                f"treated as one role"
            )
        if not self.roles:
            raise ValueError(
                "AccessDeclaration.roles must not be empty — a dashboard "
                "cannot declare row-level access without a role vocabulary "
                "to filter by"
            )


@dataclass(frozen=True)
class TrustedIngress:
    """AD-4: the trusted ingress and the identity/role header names.

    ``addresses`` is the declared set of peer addresses the proxy connects
    from (matched against the ASGI ``scope["client"]`` peer host); an
    identity header arriving on a connection from outside this set is what
    `middleware.py`'s `DashboardIdentityMiddleware` refuses. ``identity_
    header``/``role_header`` name the proxy headers that carry identity and
    role — adopter-declared, never hardcoded, so the same dashboard runs
    behind two proxies that use different header names by configuration
    alone (CAP-1).
    """

    addresses: tuple[str, ...]
    identity_header: str
    role_header: str

    def __post_init__(self) -> None:
        if not isinstance(self.addresses, tuple):
            raise TypeError(
                f"TrustedIngress.addresses must be a tuple of addresses, "
                f"got {type(self.addresses).__name__} — a bare string would "
                f"silently turn the middleware's membership check into a "
                f"substring match, weakening AD-4's trust boundary"
            )
        if not self.addresses:
            raise ValueError(
                "TrustedIngress.addresses must not be empty — an undeclared "
                "trusted ingress leaves AD-4's refusal with nothing to "
                "check against"
            )
        if not self.identity_header:
            raise ValueError(
                "TrustedIngress.identity_header must not be empty — the "
                "middleware has no header to extract identity from"
            )
        if not self.role_header:
            raise ValueError(
                "TrustedIngress.role_header must not be empty — the "
                "middleware has no header to extract role from"
            )
        for field_name, header in (
            ("identity_header", self.identity_header),
            ("role_header", self.role_header),
        ):
            try:
                header.encode("latin-1")
            except UnicodeEncodeError as exc:
                raise ValueError(
                    f"TrustedIngress.{field_name} {header!r} is not a valid "
                    f"ASGI header name (must be latin-1-encodable) — this "
                    f"must fail at declaration time, not on every live "
                    f"request"
                ) from exc
