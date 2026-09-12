"""Story 33.12 CAP-2 — marshal station role gates assertion mint."""

from __future__ import annotations

import json
from http import HTTPStatus

import pytest
from django.test import RequestFactory
from django_pyforge.assertion.views import mint
from django_pyforge.roles import prefixed_station

from test_django_pyforge_assertion import _idp_bearer


def _mint_request(bearer: str, station: str = "marshal"):
    request = RequestFactory().post(
        "/assertion/mint/",
        data=json.dumps({"station": station}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {bearer}",
    )
    return mint(request)


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
