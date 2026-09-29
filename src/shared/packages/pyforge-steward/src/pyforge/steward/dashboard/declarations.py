"""Story 9.1/9.3 — the "declared, not implemented" half of CAP-2, AD-4, and AD-7.

Three frozen dataclasses an adopter fills in instead of hand-writing
filtering, hand-wiring a trust boundary, or hand-picking an audit retention
policy. None of them performs any filtering, request handling, ingress
checking, or purging itself — that is `middleware.py` (AD-4) and `audit.py`
(AD-7)'s job. This module's only job is the declaration schema plus
construction-time validation, so a misconfigured adopter fails loudly at
config time rather than serving unfiltered rows, trusting an undeclared
network path, or running an unbounded audit trail.

Deliberately import-free of `django`/`channels` — plain `dataclasses`, so
this module (and its tests) work with or without the `[dashboard]` extra
installed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

# Story 9.3: the widest gap any two representable datetimes can have, so a
# `days` value above this could not be turned into a cutoff from ANY `now`
# whatsoever.
#
# Review pass 2 corrected this from `timedelta.max.days` (999,999,999): a
# `timedelta` of that size constructs fine, but the operation
# `purge_expired_entries` actually performs is `now - timedelta(days=...)`,
# which overflows the DATETIME range, not the timedelta range -- so the
# previous bound admitted values that still crashed with the bare
# `OverflowError` this guard exists to replace (verified by execution).
# This bound is time-independent and can never be wrong; the residual band
# (values a *specific* `now` cannot span, e.g. 3,000,000 days from 2026)
# cannot be judged without a `now`, so `purge_expired_entries` catches that
# case at the point of computation and raises its own named error there.
_MAX_RETENTION_DAYS = (datetime.max - datetime.min).days

# RFC 9110 §5.1 `token`: the grammar a header *name* must satisfy to exist on
# the wire at all. Validated because a name that is merely latin-1-encodable
# but not a token (a trailing space from a config file, an embedded ":" or
# newline) silently matches NO header -- which switches AD-4's refusal off
# rather than failing, since the middleware only checks the ingress for a
# header it actually found (review pass 3).
#
# Anchored with `\Z`, not `$` (review pass 4). Python's `$` also matches
# immediately BEFORE a trailing newline, so `"X-Forwarded-User\n"` satisfied
# the `^...$` form of this check and constructed cleanly -- and a trailing
# newline is the single likeliest artifact of the config-file/env-var
# provenance this guard was written for (`read_text()`, `readline()`, a
# mounted secret file). Reproduced end-to-end: an identity header from an
# UNDECLARED peer was passed straight through to the wrapped app with no
# refusal, which is verbatim the failure the paragraph above says this
# regex exists to prevent. The suite's cases pinned an EMBEDDED newline,
# which the character class already rejected -- which is why the trailing
# one survived three passes.
_HTTP_TOKEN_RE = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+\Z")


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
                f"AccessDeclaration.access_column must be a string, got {type(self.access_column).__name__}"
            )
        if not self.access_column.strip():
            raise ValueError(
                "AccessDeclaration.access_column must not be empty or "
                "whitespace-only — a dashboard cannot declare row-level "
                "access without naming the column that carries it"
            )
        # Padding too (review pass 4): `" region "` passed the emptiness
        # check above and would only fail in whichever later story compares
        # it against a real dataset column. Rejected rather than trimmed, so
        # the declaration means exactly what it says.
        if self.access_column != self.access_column.strip():
            raise ValueError(
                f"AccessDeclaration.access_column {self.access_column!r} "
                f"carries leading/trailing whitespace — a padded column name "
                f"matches no column in the master dataset"
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
            if role != role.strip():
                raise ValueError(
                    f"AccessDeclaration.roles[{index}] {role!r} carries "
                    f"leading/trailing whitespace — the role value extracted "
                    f"from a header never does, so it can never match"
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
            # Blank and whitespace-PADDED elements too (review pass 4), not
            # just `""`. `("   ",)` and `("10.0.0.1 ",)` both constructed and
            # then matched no peer, so the legitimate proxy's every
            # identity-bearing request was refused with a message naming the
            # peer and no hint that the DECLARATION is what is malformed --
            # the same "a typo becomes 'refuse every request' with no
            # diagnostic" consequence cited for the element-type check above,
            # from the same config-file provenance as the header-name check
            # below. This constrains only surrounding whitespace, never the
            # address FORM (CIDR/hostname/IPv6 spellings), which stays with
            # Story 9.5's ingress model on the deferred-work ledger.
            if not address.strip():
                raise ValueError(
                    f"TrustedIngress.addresses[{index}] must not be empty or "
                    f"whitespace-only — such an address can never match a peer "
                    f"host, so it would refuse every identified request while "
                    f"appearing to declare a trusted ingress"
                )
            if address != address.strip():
                raise ValueError(
                    f"TrustedIngress.addresses[{index}] {address!r} carries "
                    f"leading/trailing whitespace — the ASGI peer host it is "
                    f"compared against never does, so it can never match"
                )
        for field_name, header in (
            ("identity_header", self.identity_header),
            ("role_header", self.role_header),
        ):
            if not isinstance(header, str):
                raise TypeError(f"TrustedIngress.{field_name} must be a string, got {type(header).__name__}")
        if not self.identity_header:
            raise ValueError(
                "TrustedIngress.identity_header must not be empty — the "
                "middleware has no header to extract identity from"
            )
        if not self.role_header:
            raise ValueError(
                "TrustedIngress.role_header must not be empty — the middleware has no header to extract role from"
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


@dataclass(frozen=True)
class AuditRetention:
    """AD-7: the adopter-declared audit retention period; the pattern refuses a default.

    ``days`` is how many days an ``AuditEntry`` row is retained before
    `audit.py`'s `purge_expired_entries` deletes it. There is deliberately no
    default value for this field and no module-level fallback constant
    anywhere in this package — `purge_expired_entries` takes a required
    `AuditRetention` argument, so a deployment that has not made this
    declaration cannot purge at all, rather than purging on an assumed
    policy nobody actually chose (AD-7: "refused rather than run
    unbounded").
    """

    days: int

    def __post_init__(self) -> None:
        # `bool` excluded explicitly, same as `cache.py`'s `lock_timeout`
        # guard: `isinstance(True, int)` is `True` in Python, so
        # `AuditRetention(days=True)` would otherwise construct cleanly and
        # silently retain the audit trail for exactly one day -- a
        # retention policy nobody typed.
        if not isinstance(self.days, int) or isinstance(self.days, bool):
            raise TypeError(
                f"AuditRetention.days must be an int, got "
                f"{type(self.days).__name__} — a retention period the "
                f"pattern can compute a cutoff from"
            )
        if self.days <= 0:
            raise ValueError(
                f"AuditRetention.days must be a positive number of days, "
                f"got {self.days} — zero or negative retention describes no "
                f"real policy: a deployment that wants no retention at all "
                f"declares that by never calling purge_expired_entries, not "
                f"by declaring a value that means nothing"
            )
        # A `days` value past the widest representable datetime gap
        # constructs cleanly here but then crashes `purge_expired_entries`
        # with a bare, unhelpful `OverflowError` -- caught here instead, with
        # this module's own clear, named error, consistent with every other
        # refusal in this file. See `_MAX_RETENTION_DAYS` for why this bound
        # is the datetime range and not `timedelta`'s (review pass 2).
        if self.days > _MAX_RETENTION_DAYS:
            raise ValueError(
                f"AuditRetention.days must not exceed {_MAX_RETENTION_DAYS} "
                f"(the widest gap any two representable datetimes can have), "
                f"got {self.days} — no reference time whatsoever could turn "
                f"a larger value into a cutoff"
            )
