"""JWKS key-set loader for IdP bearer verification."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import jwt
from jwt.algorithms import RSAAlgorithm
from jwt.exceptions import PyJWTError

from django_pyforge.assertion.exceptions import AssertionRefusedError

_ALLOWED_SCHEMES = frozenset({"https", "file"})
_JWT_COMPACT_SEGMENTS = 3


class JWKSKeySet:
    """Load signing keys from ``https://`` or ``file://`` JWKS documents."""

    def __init__(self, jwks_url: str) -> None:
        parsed = urlparse(jwks_url)
        if parsed.scheme not in _ALLOWED_SCHEMES:
            msg = "JWKS URL scheme is not allowed"
            raise ValueError(msg)
        self._jwks_url = jwks_url
        self._keys_by_kid: dict[str, Any] = {}
        self._loaded = False
        self._refreshed_after_miss = False

    def resolve_key(self, token: str) -> Any:
        parts = token.split(".")
        if len(parts) != _JWT_COMPACT_SEGMENTS:
            msg = "IdP bearer is not a compact JWT"
            raise AssertionRefusedError(msg)
        try:
            header = jwt.get_unverified_header(token)
        except PyJWTError as exc:
            raise AssertionRefusedError(msg="IdP bearer header is invalid") from exc
        alg = header.get("alg")
        if not isinstance(alg, str) or not alg:
            msg = "IdP bearer is missing alg"
            raise AssertionRefusedError(msg)
        kid = header.get("kid")
        if not isinstance(kid, str) or not kid:
            msg = "IdP bearer is missing kid"
            raise AssertionRefusedError(msg)
        if not self._loaded:
            self._load_keys()
        key = self._keys_by_kid.get(kid)
        if key is not None:
            return key
        if not self._refreshed_after_miss:
            self._refreshed_after_miss = True
            self._load_keys()
            key = self._keys_by_kid.get(kid)
            if key is not None:
                return key
        msg = "IdP bearer signing key is unknown"
        raise AssertionRefusedError(msg)

    def _load_keys(self) -> None:
        document = self._fetch_document()
        keys: dict[str, Any] = {}
        for jwk in document.get("keys", []):
            if not isinstance(jwk, dict):
                continue
            kid = jwk.get("kid")
            if not isinstance(kid, str) or not kid:
                continue
            try:
                keys[kid] = RSAAlgorithm.from_jwk(json.dumps(jwk))
            except (PyJWTError, ValueError, TypeError):
                continue
        if not keys:
            msg = "JWKS document has no usable keys"
            raise AssertionRefusedError(msg)
        self._keys_by_kid = keys
        self._loaded = True

    def _fetch_document(self) -> dict[str, Any]:
        parsed = urlparse(self._jwks_url)
        if parsed.scheme == "file":
            try:
                raw = Path(parsed.path).read_text(encoding="utf-8")
            except OSError as exc:
                msg = "JWKS fetch failed"
                raise AssertionRefusedError(msg) from exc
        else:
            raw = self._fetch_https()
        document = json.loads(raw)
        if not isinstance(document, dict):
            msg = "JWKS document is not JSON object"
            raise AssertionRefusedError(msg)
        return document

    def _fetch_https(self) -> str:
        try:
            import truststore  # type: ignore[import-not-found]

            truststore.inject_into_ssl()
        except ImportError:
            pass
        request = urllib.request.Request(  # noqa: S310
            self._jwks_url,
            headers={"Accept": "application/json"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
                return response.read().decode("utf-8")
        except (OSError, urllib.error.URLError, TimeoutError, UnicodeDecodeError) as exc:
            msg = "JWKS fetch failed"
            raise AssertionRefusedError(msg) from exc


_cache: dict[str, JWKSKeySet] = {}


def get_jwks_key_set(jwks_url: str) -> JWKSKeySet:
    existing = _cache.get(jwks_url)
    if existing is not None:
        return existing
    key_set = JWKSKeySet(jwks_url)
    _cache[jwks_url] = key_set
    return key_set


def reset_jwks_cache() -> None:
    """Clear cached key sets (test hook only)."""
    _cache.clear()
