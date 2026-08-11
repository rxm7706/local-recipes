"""Story 9.1 — `AccessDeclaration`/`TrustedIngress` construction-time validation."""

from __future__ import annotations

import pytest

from pyforge.steward.dashboard.declarations import AccessDeclaration, TrustedIngress


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
        TrustedIngress(
            addresses="10.0.0.1", identity_header="X-Forwarded-User", role_header="X-Forwarded-Role"
        )


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
        TrustedIngress(
            addresses=(b"10.0.0.1",), identity_header="X-Forwarded-User", role_header="X-Forwarded-Role"
        )


def test_trusted_ingress_rejects_an_empty_address_element():
    with pytest.raises(ValueError, match=r"addresses\[1\]"):
        TrustedIngress(
            addresses=("10.0.0.1", ""), identity_header="X-Forwarded-User", role_header="X-Forwarded-Role"
        )


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
        "X-Forwarded-User ",     # trailing space out of a config file / env var
        " X-Forwarded-User",     # leading space
        "X-Forwarded-User:",     # the colon, pasted along with the name
        "X-Forwarded\nUser",     # embedded newline
        "X Forwarded User",      # spaces instead of hyphens
        "X-Forwarded-User-🚀",   # non-ASCII (the pass-2 latin-1 case, subsumed)
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
        TrustedIngress(
            addresses=("10.0.0.1",), identity_header=bad_header, role_header="X-Forwarded-Role"
        )


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
