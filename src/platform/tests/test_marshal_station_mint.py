"""Story 33.12 CAP-2 — marshal station role gates assertion mint."""

from __future__ import annotations

import json
from datetime import UTC
from datetime import datetime
from http import HTTPStatus

import jwt
import pytest
from django.test import RequestFactory
from django_pyforge.assertion.views import mint
from django_pyforge.roles import prefixed_station


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
