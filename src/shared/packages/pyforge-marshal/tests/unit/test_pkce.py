"""Story 33.14 — pure PKCE verifier/challenge generation."""

from __future__ import annotations

from pyforge.marshal.core.pkce import challenge_for, generate_verifier

# RFC 7636 appendix B verifier; challenge is derived by S256 (base64url, no pad).
_RFC7636_VERIFIER = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
_RFC7636_CHALLENGE = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def test_challenge_for_rfc7636_vector() -> None:
    assert challenge_for(_RFC7636_VERIFIER) == _RFC7636_CHALLENGE


def test_generate_verifier_is_stable_for_challenge() -> None:
    verifier = generate_verifier()
    assert 43 <= len(verifier) <= 128
    assert challenge_for(verifier) == challenge_for(verifier)
