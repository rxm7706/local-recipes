"""Story 52.1: mybmad chrome tile is a sidecar, never a station or /console/."""

from __future__ import annotations

from django.test import RequestFactory
from django.urls import get_resolver
from django_pyforge.context_processors import chrome
from django_pyforge.roles import prefixed_station
from django_pyforge.sidecars import MYBMAD_SCHEMA
from django_pyforge.sidecars import mybmad_public_url
from django_pyforge.sidecars import mybmad_sidecar


def test_mybmad_schema_name_is_mybmad() -> None:
    assert MYBMAD_SCHEMA == "mybmad"


def test_switcher_lists_mybmad_after_oidc_roles(monkeypatch) -> None:
    monkeypatch.setenv("MYBMAD_PUBLIC_URL", "https://mybmad.example.test")
    request = RequestFactory().get("/stations/steward/")
    request.idp_roles = [prefixed_station("steward")]
    ctx = chrome(request)
    names = [s.name for s in ctx["pyforge_sidecars"]]
    assert names == ["mybmad"]
    assert ctx["pyforge_sidecars"][0].href == "https://mybmad.example.test"
    html = __import__("django.template.loader", fromlist=["render_to_string"]).render_to_string(
        "django_pyforge/switcher.html",
        ctx,
    )
    assert "https://mybmad.example.test" in html
    assert "/stations/mybmad/" not in html
    assert 'href="/console/"' not in html


def test_unauthenticated_request_omits_mybmad_tile() -> None:
    request = RequestFactory().get("/stations/steward/")
    request.idp_roles = []
    assert chrome(request)["pyforge_sidecars"] == []


def test_no_urlconf_mounts_mybmad_at_console_or_stations() -> None:
    dumped = str(get_resolver().url_patterns)
    assert "mybmad" not in dumped.lower()


def test_sidecar_href_refuses_forbidden_mounts(monkeypatch) -> None:
    monkeypatch.setenv("MYBMAD_PUBLIC_URL", "http://127.0.0.1:8000/console/")
    try:
        mybmad_sidecar()
    except ValueError as exc:
        assert "/console/" in str(exc)
    else:
        raise AssertionError("expected ValueError for /console/ href")
    assert mybmad_public_url() == "http://127.0.0.1:8000/console"
