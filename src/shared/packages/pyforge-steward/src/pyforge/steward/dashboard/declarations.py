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

import re
from dataclasses import dataclass

# RFC 9110 §5.1 `token`: the grammar a header *name* must satisfy to exist on
# the wire at all. Validated because a name that is merely latin-1-encodable
# but not a token (a trailing space from a config file, an embedded ":" or
# newline) silently matches NO header -- which switches AD-4's refusal off
# rather than failing, since the middleware only checks the ingress for a
# header it actually found (review pass 3).
_HTTP_TOKEN_RE = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")


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
        if not isinstance(self.access_column, str):
            raise TypeError(
                f"AccessDeclaration.access_column must be a string, got "
                f"{type(self.access_column).__name__}"
            )
        if not self.access_column.strip():
            raise ValueError(
                "AccessDeclaration.access_column must not be empty or "
                "whitespace-only — a dashboard cannot declare row-level "
                "access without naming the column that carries it"
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
        # Element types, not just the container's (review pass 2): the tuple
        # check above closed the bare-string hazard, but `roles=(1, None)`
        # still constructed and would only fail in whichever later story
        # finally consumes the vocabulary.
        for index, role in enumerate(self.roles):
            if not isinstance(role, str):
                raise TypeError(
                    f"AccessDeclaration.roles[{index}] must be a string, got "
                    f"{type(role).__name__} — a non-string role can never "
                    f"match an extracted role header"
                )
            if not role.strip():
                raise ValueError(
                    f"AccessDeclaration.roles[{index}] must not be empty or "
                    f"whitespace-only — an unnamed role cannot be filtered by"
                )


@dataclass(frozen=True)
class TrustedIngress:
    """AD-4: the trusted ingress and the identity/role header names.

    ``addresses`` is the declared set of peer addresses the proxy connects
    from, matched against whatever the ASGI server reports as
    ``scope["client"]``; an identity header arriving on a connection from
    outside this set is what `middleware.py`'s `DashboardIdentityMiddleware`
    refuses. Note that ``scope["client"]`` is the *server's* claim about the
    peer, not necessarily the TCP peer — see `middleware.py`'s module
    docstring for the deployment precondition that claim depends on.
    ``identity_header``/``role_header`` name the proxy headers that carry
    identity and role — adopter-declared, never hardcoded, so the same
    dashboard runs behind two proxies that use different header names by
    configuration alone (CAP-1). They must be different names.
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
        # Element types (review pass 2): `addresses=(b"10.0.0.1",)` passed
        # both checks above, then silently matched no peer at all -- the
        # middleware compares against `scope["client"][0]`, always a `str` --
        # turning a typo into "refuse every request" with no diagnostic.
        for index, address in enumerate(self.addresses):
            if not isinstance(address, str):
                raise TypeError(
                    f"TrustedIngress.addresses[{index}] must be a string, got "
                    f"{type(address).__name__} — the ASGI peer host it is "
                    f"compared against is always a string, so a non-string "
                    f"declaration can never match and would refuse every "
                    f"request"
                )
            if not address:
                raise ValueError(
                    f"TrustedIngress.addresses[{index}] must not be empty — an "
                    f"empty address can never match a peer host"
                )
        for field_name, header in (
            ("identity_header", self.identity_header),
            ("role_header", self.role_header),
        ):
            if not isinstance(header, str):
                raise TypeError(
                    f"TrustedIngress.{field_name} must be a string, got "
                    f"{type(header).__name__}"
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
        # Header NAME form, not just encodability (review pass 3). The
        # latin-1 check this replaces caught only non-latin-1 names; a name
        # that is latin-1 but not an RFC 9110 token -- `"X-Forwarded-User "`
        # with a trailing space out of a config file or env var, or one
        # carrying a ":" or newline -- constructed cleanly and then matched no
        # header at all. That does not degrade to "no identity": it switches
        # AD-4's refusal OFF, because the middleware only checks the ingress
        # for a header it actually found, so an identity header from an
        # UNTRUSTED peer stops being refused. A name that cannot exist on the
        # wire must fail here, loudly, not silently disarm the trust boundary.
        for field_name, header in (
            ("identity_header", self.identity_header),
            ("role_header", self.role_header),
        ):
            if not _HTTP_TOKEN_RE.match(header):
                raise ValueError(
                    f"TrustedIngress.{field_name} {header!r} is not a valid "
                    f"HTTP header name (RFC 9110 token: letters, digits and "
                    f"!#$%&'*+-.^_`|~ only — no spaces, colons, newlines or "
                    f"non-ASCII) — such a name matches no header on the wire, "
                    f"which would silently disable AD-4's ingress refusal "
                    f"instead of failing here"
                )

        # The two headers must be DIFFERENT (review pass 3). Declaring one
        # name for both makes the role a copy of the identity: a single
        # `X-Forwarded-User: admin` then yields identity='admin' AND
        # role='admin', so a caller whose name happens to match a privileged
        # role in the adopter's vocabulary is granted it -- from a
        # copy-paste typo, with nothing anywhere reporting it. Prior passes
        # rejected cross-field validation as speculative hardening; this one
        # has a demonstrated privilege consequence, which is the same
        # consequence-driven rationale that admitted the element-type checks
        # above.
        if self.identity_header.lower() == self.role_header.lower():
            raise ValueError(
                f"TrustedIngress.identity_header and role_header must name "
                f"different headers (both are {self.identity_header!r}) — one "
                f"name for both makes the extracted role a copy of the "
                f"identity, silently granting a caller any role that matches "
                f"their own name"
            )
