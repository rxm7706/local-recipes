"""Story 9.1/9.3 — `AccessDeclaration`/`TrustedIngress`/`AuditRetention` construction-time validation."""

from __future__ import annotations

import pytest

from pyforge.steward.dashboard.declarations import (
    _MAX_RETENTION_DAYS,
    AccessDeclaration,
    AuditRetention,
    TrustedIngress,
)


def test_access_declaration_accepts_a_column_and_a_role_vocabulary():
    decl = AccessDeclaration(access_column="region", roles=("admin", "viewer"))
    assert decl.access_column == "region"
    assert decl.roles == ("admin", "viewer")


def test_access_declaration_rejects_an_empty_access_column():
    with pytest.raises(ValueError, match="access_column"):
        AccessDeclaration(access_column="", roles=("admin",))


def test_access_declaration_rejects_empty_roles():
    with pytest.raises(ValueError, match="roles"):
        AccessDeclaration(access_column="region", roles=())


def test_trusted_ingress_accepts_addresses_and_header_names():
    ingress = TrustedIngress(
        addresses=("10.0.0.1", "10.0.0.2"),
        identity_header="X-Forwarded-User",
        role_header="X-Forwarded-Role",
    )
    assert ingress.addresses == ("10.0.0.1", "10.0.0.2")
    assert ingress.identity_header == "X-Forwarded-User"
    assert ingress.role_header == "X-Forwarded-Role"


def test_trusted_ingress_rejects_empty_addresses():
    with pytest.raises(ValueError, match="addresses"):
        TrustedIngress(addresses=(), identity_header="X-Forwarded-User", role_header="X-Forwarded-Role")


def test_trusted_ingress_rejects_an_empty_identity_header():
    with pytest.raises(ValueError, match="identity_header"):
        TrustedIngress(addresses=("10.0.0.1",), identity_header="", role_header="X-Forwarded-Role")


def test_trusted_ingress_rejects_an_empty_role_header():
    with pytest.raises(ValueError, match="role_header"):
        TrustedIngress(addresses=("10.0.0.1",), identity_header="X-Forwarded-User", role_header="")


def test_access_declaration_rejects_a_bare_string_for_roles():
    """A bare string is iterable, so truthiness alone would pass it -- it
    must be rejected by type, since iterating it later would silently
    produce one-character "roles" instead of the intended role names.
    """
    with pytest.raises(TypeError, match="roles"):
        AccessDeclaration(access_column="region", roles="admin")


def test_trusted_ingress_rejects_a_bare_string_for_addresses():
    """A bare string passes truthiness too, and would silently turn the
    middleware's `peer_host not in self.ingress.addresses` membership check
    into a substring match -- e.g. declaring "10.0.0.100" would then also
    trust a peer whose address is any substring of it. Must be rejected by
    type at construction time, not discovered as a live trust-boundary leak.
    """
    with pytest.raises(TypeError, match="addresses"):
        TrustedIngress(addresses="10.0.0.1", identity_header="X-Forwarded-User", role_header="X-Forwarded-Role")


def test_trusted_ingress_rejects_a_non_latin1_header_name():
    """ASGI header names must be latin-1-encodable; failing at declaration
    time here means a malformed header name never reaches live traffic,
    where the middleware would otherwise raise on the first real request.
    """
    with pytest.raises(ValueError, match="identity_header"):
        TrustedIngress(addresses=("10.0.0.1",), identity_header="X-Forwarded-User-🚀", role_header="X-Forwarded-Role")


def test_trusted_ingress_rejects_a_non_string_address():
    """Review pass 2 (reproduced by execution): `addresses=(b"10.0.0.1",)`
    passed both the tuple check and the emptiness check, then silently
    matched no peer at all -- the middleware compares against
    `scope["client"][0]`, which is always a `str`. A one-character typo
    became "refuse every request", with no diagnostic anywhere.
    """
    with pytest.raises(TypeError, match=r"addresses\[0\]"):
        TrustedIngress(addresses=(b"10.0.0.1",), identity_header="X-Forwarded-User", role_header="X-Forwarded-Role")


def test_trusted_ingress_rejects_an_empty_address_element():
    with pytest.raises(ValueError, match=r"addresses\[1\]"):
        TrustedIngress(addresses=("10.0.0.1", ""), identity_header="X-Forwarded-User", role_header="X-Forwarded-Role")


def test_trusted_ingress_rejects_a_non_string_header_name():
    """Previously raised `AttributeError` from the latin-1 check's `.encode`
    rather than the loud, named error this module exists to produce.
    """
    with pytest.raises(TypeError, match="identity_header"):
        TrustedIngress(addresses=("10.0.0.1",), identity_header=123, role_header="X-Forwarded-Role")


def test_access_declaration_rejects_non_string_role_elements():
    """Review pass 1's tuple check closed the bare-string hazard for the
    CONTAINER; review pass 2 found the elements still unchecked, so
    `roles=(1, None)` constructed cleanly and would only fail in whichever
    later story finally consumes the vocabulary.
    """
    with pytest.raises(TypeError, match=r"roles\[0\]"):
        AccessDeclaration(access_column="region", roles=(1, None))


def test_access_declaration_rejects_an_empty_role_element():
    with pytest.raises(ValueError, match=r"roles\[1\]"):
        AccessDeclaration(access_column="region", roles=("admin", ""))


def test_access_declaration_rejects_a_non_string_access_column():
    with pytest.raises(TypeError, match="access_column"):
        AccessDeclaration(access_column=123, roles=("admin",))


@pytest.mark.parametrize(
    "bad_header",
    [
        "X-Forwarded-User ",  # trailing space out of a config file / env var
        " X-Forwarded-User",  # leading space
        "X-Forwarded-User:",  # the colon, pasted along with the name
        "X-Forwarded\nUser",  # embedded newline
        "X Forwarded User",  # spaces instead of hyphens
        "X-Forwarded-User-🚀",  # non-ASCII (the pass-2 latin-1 case, subsumed)
    ],
)
def test_trusted_ingress_rejects_a_header_name_that_is_not_an_http_token(bad_header):
    """Review pass 3: a header name that is merely latin-1-encodable but not
    an RFC 9110 token constructed cleanly and then matched NO header — which
    does not degrade to "no identity", it switches AD-4's refusal OFF, since
    the ingress check only runs for a header actually found. Reproduced: with
    `identity_header="X-Forwarded-User "`, an identity header arriving from an
    UNTRUSTED peer was passed straight through to the wrapped app with no
    exception at all.

    A trailing space is the realistic trigger — header names routinely come
    from config files and environment variables.
    """
    with pytest.raises(ValueError, match="identity_header"):
        TrustedIngress(addresses=("10.0.0.1",), identity_header=bad_header, role_header="X-Forwarded-Role")


def test_trusted_ingress_rejects_the_same_name_for_both_headers():
    """Review pass 3: declaring one name for both made the role a copy of the
    identity — a single `X-Forwarded-User: admin` from the trusted proxy
    yielded identity='admin' AND role='admin' (reproduced), so a caller whose
    name matches a privileged role in the adopter's vocabulary is granted it.

    Passes 1 and 2 rejected cross-field validation as speculative hardening;
    this is the same check with a demonstrated privilege consequence, which is
    the rationale that admitted the element-type checks in pass 2.
    """
    with pytest.raises(ValueError, match="different headers"):
        TrustedIngress(
            addresses=("10.0.0.1",),
            identity_header="X-Forwarded-User",
            role_header="X-Forwarded-User",
        )

    # Header names are case-insensitive on the wire, so a case variant is the
    # same header, not a different one.
    with pytest.raises(ValueError, match="different headers"):
        TrustedIngress(
            addresses=("10.0.0.1",),
            identity_header="X-Forwarded-User",
            role_header="x-forwarded-user",
        )


def test_access_declaration_rejects_whitespace_only_fields():
    """Review pass 3: `"   "` passed the emptiness checks for both the access
    column and a role element, so a whitespace-only declaration was accepted
    and would only fail in whichever later story consumes it.
    """
    with pytest.raises(ValueError, match="access_column"):
        AccessDeclaration(access_column="   ", roles=("admin",))

    with pytest.raises(ValueError, match=r"roles\[1\]"):
        AccessDeclaration(access_column="region", roles=("admin", "  "))


@pytest.mark.parametrize(
    "bad_name",
    ["X-Forwarded-User\n", "X-Forwarded-User\r\n", "X-Forwarded-User\r"],
)
def test_trusted_ingress_rejects_a_header_name_with_a_trailing_newline(bad_name):
    """Review pass 4: the RFC-token guard was anchored with `$`, and Python's
    `$` also matches immediately BEFORE a trailing newline — so
    `"X-Forwarded-User\\n"` satisfied it, matched no header on the wire, and
    therefore switched AD-4's refusal OFF (the ingress check only runs for a
    header actually found). Reproduced end-to-end before the fix: an identity
    header from an UNDECLARED peer reached the wrapped app with no exception.

    A trailing newline is the likeliest artifact of the config-file/env-var
    provenance the guard was written for. The pass-3 cases pinned an
    *embedded* newline, which the character class already rejected — which is
    exactly why the trailing one survived three passes.
    """
    with pytest.raises(ValueError, match="not a valid HTTP header name"):
        TrustedIngress(
            addresses=("10.0.0.1",),
            identity_header=bad_name,
            role_header="X-Forwarded-Role",
        )


@pytest.mark.parametrize("bad_address", ["   ", "\t", "\n"])
def test_trusted_ingress_rejects_a_whitespace_only_address(bad_address):
    """Review pass 4: only `""` was rejected, so `("   ",)` declared a trusted
    ingress that can never match any peer — every identity-bearing request
    from the legitimate proxy refused, with a message naming the peer and no
    hint that the DECLARATION is what is wrong.
    """
    with pytest.raises(ValueError, match=r"addresses\[0\]"):
        TrustedIngress(
            addresses=(bad_address,),
            identity_header="X-Forwarded-User",
            role_header="X-Forwarded-Role",
        )


def test_trusted_ingress_rejects_a_whitespace_padded_address():
    """Review pass 4: `"10.0.0.1 "` constructed cleanly and then matched
    nothing, because the ASGI peer host it is compared against never carries
    padding. Same config-file provenance as the header-name case; rejected
    rather than trimmed so the declaration means what it says.

    This constrains only surrounding whitespace — never the address FORM
    (CIDR, hostname, IPv6 spellings), which stays with Story 9.5 on the
    deferred-work ledger.
    """
    with pytest.raises(ValueError, match="leading/trailing whitespace"):
        TrustedIngress(
            addresses=("10.0.0.1 ",),
            identity_header="X-Forwarded-User",
            role_header="X-Forwarded-Role",
        )

    # The forms that story may still choose to support are NOT forbidden here.
    for tolerated in ("10.0.0.0/24", "proxy.internal", "::ffff:10.0.0.1"):
        TrustedIngress(
            addresses=(tolerated,),
            identity_header="X-Forwarded-User",
            role_header="X-Forwarded-Role",
        )


def test_access_declaration_rejects_whitespace_padded_fields():
    """Review pass 4: pass 3 rejected whitespace-ONLY values but left padding,
    so `" region "` and `"admin\\n"` constructed and would only fail in
    whichever later story compares them against a real column or an extracted
    role header — neither of which carries padding.
    """
    with pytest.raises(ValueError, match="leading/trailing whitespace"):
        AccessDeclaration(access_column=" region ", roles=("admin",))

    with pytest.raises(ValueError, match=r"roles\[1\]"):
        AccessDeclaration(access_column="region", roles=("admin", "viewer\n"))


def test_audit_retention_accepts_a_positive_day_count():
    retention = AuditRetention(days=30)
    assert retention.days == 30


def test_audit_retention_rejects_zero_days():
    """AD-7: zero describes no real policy -- a deployment that wants no
    retention at all declares that by never calling `purge_expired_entries`,
    not by declaring a value that means nothing.
    """
    with pytest.raises(ValueError, match="days"):
        AuditRetention(days=0)


def test_audit_retention_rejects_negative_days():
    with pytest.raises(ValueError, match="days"):
        AuditRetention(days=-5)


def test_audit_retention_rejects_a_non_int_days():
    with pytest.raises(TypeError, match="days"):
        AuditRetention(days="30")


def test_audit_retention_rejects_a_bool_days():
    """`bool` is a subclass of `int` in Python, so `isinstance(True, int)`
    is `True` -- `AuditRetention(days=True)` would otherwise construct
    cleanly and silently retain the trail for exactly one day, a retention
    policy nobody actually typed. Mirrors `cache.py`'s identical `bool`
    exclusion for `lock_timeout`.
    """
    with pytest.raises(TypeError, match="days"):
        AuditRetention(days=True)
    with pytest.raises(TypeError, match="days"):
        AuditRetention(days=False)


def test_audit_retention_rejects_a_days_value_no_cutoff_could_ever_span():
    """A `days` value wider than the whole representable datetime range
    would otherwise construct cleanly here and only fail later, inside
    `purge_expired_entries`, with a bare `OverflowError` -- caught here
    instead, with this module's own named error.

    Review pass 2 corrected the bound: it used to be `timedelta.max.days`
    (999,999,999), but the operation that actually overflows is
    `now - timedelta(days=...)`, which is limited by the DATETIME range, not
    the timedelta range. `AuditRetention(days=timedelta.max.days)` therefore
    constructed happily and `purge_expired_entries` then raised the exact
    bare `OverflowError` this guard exists to replace.
    """
    import datetime

    with pytest.raises(ValueError, match="days"):
        AuditRetention(days=_MAX_RETENTION_DAYS + 1)
    with pytest.raises(ValueError, match="days"):
        AuditRetention(days=datetime.timedelta.max.days)


def test_audit_retention_accepts_a_days_value_at_the_representable_ceiling():
    """The accepted boundary.

    The previous version of this test is why the wrong bound survived a
    review pass: it asserted only that the object CONSTRUCTED, so the
    `OverflowError` waiting one call downstream went unnoticed. The
    consumer half — that `purge_expired_entries` refuses this value in
    NAMED terms rather than crashing on it — is pinned by
    `test_purge_expired_entries_names_a_retention_this_now_cannot_span` in
    `test_dashboard_audit.py`, which is where the django settings and
    database that call needs are set up. This file stays django-free so it
    keeps importing without the `[dashboard]` extra.
    """
    retention = AuditRetention(days=_MAX_RETENTION_DAYS)
    assert retention.days == _MAX_RETENTION_DAYS
