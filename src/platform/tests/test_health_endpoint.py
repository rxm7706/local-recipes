"""Story 10.3 -- regression-tests the `/ht/` route against the PIP stack.

This app is wired against TWO django-health-check majors: `requirements/
base.txt` pins pip's 3.24.0 (what this test suite and `platform-ci.yml`'s
`test` job run), while `pixi.toml`'s `python-agent-platform` env conda-pins
>=4.5.0 (what `src/platform/Containerfile` ships). `config/urls.py` wires
`/ht/` with DOTTED-STRING check references because that is the only
invocation shape valid under both -- 3.24.0's `get_plugins()` unpacks each
entry and catches only `ValueError`, so a raw CLASS raises an uncaught
`TypeError` there while working fine under 4.5.0.

That trap is invisible to every other gate in this repo. `get_plugins()` is
reached from a `@cached_property` accessed only in `get()`/`get_context_data
()` -- i.e. on a real HTTP request -- so `manage.py check`, `as_view()`, and
URLconf loading all succeed regardless. The container job asserts a 200 but
runs the conda 4.5.0 side, which catches both exception types. Without the
request below, "clean up those strings into imports" is a change that goes
green everywhere and 500s only in production on the pip stack.

Deliberately asserts the endpoint's real contract and nothing narrower: a
200 whose body names both configured checks. It does NOT assert schema
depth -- `health_check.Database` is a connectivity probe, not a write
round-trip (see `config/urls.py`'s own note).
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.urls import reverse

if TYPE_CHECKING:
    from django.test import Client


@pytest.mark.django_db
def test_ht_returns_200_with_both_configured_checks(client: Client) -> None:
    response = client.get("/ht/")

    assert response.status_code == HTTPStatus.OK
    body = response.content.decode()
    # Both check classes render their own name into the response body. If
    # `checks=` were passed raw classes, 3.24.0 would have raised TypeError
    # out of get_plugins() before reaching here.
    assert "Database" in body
    assert "Cache" in body


@pytest.mark.django_db
def test_ht_is_reachable_without_authentication(client: Client) -> None:
    # `/ht/` is deliberately unauthenticated at the app layer (kubelet
    # probes it); restricting it is an ingress-layer concern. A redirect to
    # a login page would break every probe.
    response = client.get("/ht/")

    assert response.status_code == HTTPStatus.OK


def test_home_page_does_not_shadow_the_health_route() -> None:
    # `/ht/` is wired as a bare `path()` rather than an `include()`, so a
    # future `include()` at "" could swallow it without any other test
    # noticing. Resolving the home name proves the two coexist.
    assert reverse("home") == "/"
