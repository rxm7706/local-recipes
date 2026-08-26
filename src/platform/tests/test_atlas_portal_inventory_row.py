"""Story 19.2: GET /stations/atlas/ renders one inventory or run-state row."""

from __future__ import annotations

import re
from datetime import timedelta
from http import HTTPStatus

import pytest
from django.test import Client
from django.test import RequestFactory
from django.utils import timezone
from django_atlas_portal import views as atlas_views
from django_pyforge.models import RunState
from django_pyforge.roles import IDP_TOKEN_CLAIMS_SESSION_KEY

_ROW_ID = re.compile(r'id="atlas-inventory-row"')


def _atlas_client(*, groups: list[str], sub: str = "atlas-op") -> Client:
    client = Client()
    session = client.session
    session[IDP_TOKEN_CLAIMS_SESSION_KEY] = {"sub": sub, "groups": groups}
    session.save()
    return client


@pytest.mark.django_db
def test_authenticated_atlas_get_renders_one_idle_row() -> None:
    response = _atlas_client(groups=["atlas"]).get("/stations/atlas/")
    assert response.status_code == HTTPStatus.OK
    html = response.content.decode()
    assert len(_ROW_ID.findall(html)) == 1
    assert "hx-get" in html
    assert 'data-station="atlas"' in html
    assert "idle" in html


@pytest.mark.django_db
def test_authenticated_atlas_get_renders_latest_run_row() -> None:
    older = timezone.now() - timedelta(hours=2)
    newer = timezone.now() - timedelta(minutes=5)
    RunState.objects.create(
        station="warden",
        status=RunState.Status.SUCCEEDED,
        started_at=newer,
    )
    RunState.objects.create(
        station="atlas",
        status=RunState.Status.FAILED,
        started_at=older,
    )
    latest = RunState.objects.create(
        station="atlas",
        status=RunState.Status.RUNNING,
        started_at=newer,
    )

    response = _atlas_client(groups=["atlas"]).get("/stations/atlas/")
    assert response.status_code == HTTPStatus.OK
    html = response.content.decode()
    assert len(_ROW_ID.findall(html)) == 1
    assert str(latest.id) in html
    assert "running" in html


def test_warden_role_is_forbidden_and_has_no_row() -> None:
    denied = RequestFactory().get("/stations/atlas/")
    denied.idp_roles = ["warden"]
    response = atlas_views.chrome_home(denied)
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert b"atlas-inventory-row" not in response.content


@pytest.mark.django_db
def test_warden_session_get_is_forbidden() -> None:
    response = _atlas_client(groups=["warden"]).get("/stations/atlas/")
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert b"atlas-inventory-row" not in response.content
