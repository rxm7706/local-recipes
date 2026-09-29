"""Story 33.12 CAP-2 — marshal station role gates assertion mint."""

from __future__ import annotations

import json
from datetime import UTC
from datetime import datetime
from http import HTTPStatus
from typing import TYPE_CHECKING

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from django.test import RequestFactory
from django_pyforge.assertion.jwks import reset_jwks_cache
from django_pyforge.assertion.views import mint
from django_pyforge.roles import prefixed_station
from jwt.algorithms import RSAAlgorithm

if TYPE_CHECKING:
    from pathlib import Path

_TEST_ISSUER = "https://issuer.test/"
_TEST_AUDIENCE = "pyforge-platform"


@pytest.fixture
def idp_test_keys(tmp_path: Path) -> dict[str, object]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    kid = "test-idp-signing-key"
    jwk = RSAAlgorithm.to_jwk(public_key, as_dict=True)
    jwk.update({"kid": kid, "use": "sig", "alg": "RS256"})
    jwks_path = tmp_path / "jwks.json"
    jwks_path.write_text(json.dumps({"keys": [jwk]}), encoding="utf-8")
    return {
        "kid": kid,
        "private_pem": private_pem,
        "jwks_url": jwks_path.as_uri(),
    }


@pytest.fixture(autouse=True)
def _idp_verifier_settings(
    idp_test_keys: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_jwks_cache()
    monkeypatch.setattr(
        settings, "OIDC_JWKS_URL", idp_test_keys["jwks_url"], raising=False
    )
    monkeypatch.setattr(settings, "OIDC_ISSUER", _TEST_ISSUER, raising=False)
    monkeypatch.setattr(settings, "OIDC_AUDIENCE", _TEST_AUDIENCE, raising=False)


def _mint_request(bearer: str, station: str = "marshal"):
    request = RequestFactory().post(
        "/assertion/mint/",
        data=json.dumps({"station": station}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {bearer}",
    )
    return mint(request)


def _idp_bearer(
    sub: str,
    roles: list[str],
    *,
    private_pem: bytes,
    kid: str,
) -> str:
    now = int(datetime.now(tz=UTC).timestamp())
    return jwt.encode(
        {
            "sub": sub,
            "groups": roles,
            "iss": "https://issuer.test/",
            "aud": "pyforge-platform",
            "iat": now,
            "exp": now + 300,
        },
        private_pem,
        algorithm="RS256",
        headers={"kid": kid, "alg": "RS256"},
    )


def test_marshal_role_mints_200(idp_test_keys: dict[str, object]) -> None:
    bearer = _idp_bearer(
        "marshal-operator",
        [prefixed_station("marshal")],
        private_pem=idp_test_keys["private_pem"],
        kid=idp_test_keys["kid"],
    )
    assert _mint_request(bearer).status_code == HTTPStatus.OK


def test_missing_marshal_role_mints_403(idp_test_keys: dict[str, object]) -> None:
    bearer = _idp_bearer(
        "editor-only",
        ["platform-staff"],
        private_pem=idp_test_keys["private_pem"],
        kid=idp_test_keys["kid"],
    )
    assert _mint_request(bearer).status_code == HTTPStatus.FORBIDDEN
