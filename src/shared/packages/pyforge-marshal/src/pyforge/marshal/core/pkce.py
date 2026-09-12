"""Pure PKCE helpers (RFC 7636, Story 33.14, CAP-5)."""

from __future__ import annotations

import base64
import hashlib
import secrets


def generate_verifier() -> str:
    """Return a URL-safe verifier within RFC 7636 length bounds."""
    return secrets.token_urlsafe(64)


def challenge_for(verifier: str) -> str:
    """Return the S256 code challenge for ``verifier`` (base64url, no padding)."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
