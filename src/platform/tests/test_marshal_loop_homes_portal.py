"""Story 27.2: /stations/marshal/ lists provisioned loop homes via PortalClient."""

from __future__ import annotations

import ast
from http import HTTPStatus
from pathlib import Path

import pytest
from django.test import RequestFactory
from django_marshal_portal import views as marshal_views
from django_pyforge.assertion.client import PortalClient

PORTAL = (
    Path(__file__).resolve().parents[2]
    / "shared"
    / "packages"
    / "django-marshal"
    / "src"
    / "django_marshal_portal"
)
_HTTP_TOPLEVEL = frozenset({"httpx", "requests", "http.client"})


def _provision(root: Path, slug: str, marker: str | None = None) -> None:
    home = root / slug
    marker_path = home / "_bmad" / "custom" / ".active-project"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(marker if marker is not None else slug, encoding="utf-8")


def test_portal_client_lists_only_marked_homes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path))
    _provision(tmp_path, "pyforge-herald")
    (tmp_path / "scratch.txt").write_text("no", encoding="utf-8")
    (tmp_path / "not-provisioned").mkdir()
    homes = PortalClient().list_loop_homes()
    assert [row["slug"] for row in homes] == ["pyforge-herald"]
    assert homes[0]["active_project"] == "pyforge-herald"


def test_portal_client_empty_root_is_empty_list(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "missing"))
    assert PortalClient().list_loop_homes() == []


def test_authenticated_marshal_role_sees_homes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path))
    _provision(tmp_path, "pyforge-atlas")
    request = RequestFactory().get("/stations/marshal/")
    request.idp_roles = ["marshal"]
    response = marshal_views.chrome_home(request)
    assert response.status_code == HTTPStatus.OK
    body = response.content.decode()
    assert 'id="marshal-loop-homes"' in body
    assert 'data-loop-home-slug="pyforge-atlas"' in body
    assert "pyforge-atlas" in body


def test_authenticated_marshal_role_empty_homes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path))
    request = RequestFactory().get("/stations/marshal/")
    request.idp_roles = ["marshal"]
    response = marshal_views.chrome_home(request)
    assert response.status_code == HTTPStatus.OK
    assert b'id="marshal-loop-homes-empty"' in response.content


def test_marshal_role_required() -> None:
    denied = RequestFactory().get("/stations/marshal/")
    denied.idp_roles = ["steward"]
    response = marshal_views.chrome_home(denied)
    assert response.status_code == HTTPStatus.FORBIDDEN


def test_view_uses_portal_client_only() -> None:
    source = (PORTAL / "views.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert "PortalClient" in source
    assert "list_loop_homes" in source
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if (
                    top in _HTTP_TOPLEVEL
                    or top == "pyforge"
                    or alias.name.startswith("pyforge.")
                ):
                    hits.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            top = module.split(".")[0]
            if top in _HTTP_TOPLEVEL or top == "pyforge":
                hits.append(module)
    assert hits == []
