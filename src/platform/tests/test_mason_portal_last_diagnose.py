"""Story 11.2: /stations/mason/ renders last diagnose via PortalClient."""

from __future__ import annotations

import ast
from http import HTTPStatus
from pathlib import Path
from unittest.mock import patch

from django.test import RequestFactory
from django_mason_portal import views as mason_views
from django_mason_portal.diagnose import LAST_DIAGNOSE_SUMMARY
from django_pyforge.assertion.client import PortalClient
from django_pyforge.assertion.schema import CLAIM_SUB
from django_pyforge.roles import IDP_TOKEN_CLAIMS_ATTR

REPO_ROOT = Path(__file__).resolve().parents[2]
MASON_PORTAL = (
    REPO_ROOT / "src" / "shared" / "packages" / "django-mason" / "src" / "django_mason_portal"
)
_HTTP_TOPLEVEL = frozenset({"httpx", "requests", "http.client"})


def test_mason_role_get_renders_one_diagnosis() -> None:
    request = RequestFactory().get("/stations/mason/")
    request.idp_roles = ["pyforge:station:mason"]
    setattr(
        request,
        IDP_TOKEN_CLAIMS_ATTR,
        {CLAIM_SUB: "mason-operator", "groups": ["pyforge:station:mason"]},
    )
    response = mason_views.chrome_home(request)
    assert response.status_code == HTTPStatus.OK
    body = response.content.decode("utf-8")
    assert 'id="mason-last-diagnose"' in body
    assert LAST_DIAGNOSE_SUMMARY in body
    assert "mason diagnose" in body
    assert 'id="pyforge-chrome"' in body


def test_mason_view_uses_portal_client_last_diagnose() -> None:
    request = RequestFactory().get("/stations/mason/")
    request.idp_roles = ["pyforge:station:mason"]
    sentinel = {
        "ok": True,
        "tool": "last_diagnose",
        "command": "mason diagnose",
        "summary": LAST_DIAGNOSE_SUMMARY,
        "source": "portal-client",
    }
    with patch.object(PortalClient, "last_diagnose", return_value=sentinel) as mocked:
        response = mason_views.chrome_home(request)
    assert response.status_code == HTTPStatus.OK
    mocked.assert_called_once()
    args, _kwargs = mocked.call_args
    assert args[2] == "mason"
    assert "mason" in args[1]
    assert LAST_DIAGNOSE_SUMMARY in response.content.decode("utf-8")


def test_wrong_role_is_forbidden_without_portal_client() -> None:
    request = RequestFactory().get("/stations/mason/")
    request.idp_roles = ["pyforge:station:warden"]
    with patch.object(PortalClient, "last_diagnose") as mocked:
        response = mason_views.chrome_home(request)
    assert response.status_code == HTTPStatus.FORBIDDEN
    mocked.assert_not_called()


def test_mason_portal_tree_forbids_http_station_import_and_object_store() -> None:
    offenders: list[str] = []
    for path in sorted(MASON_PORTAL.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top in _HTTP_TOPLEVEL or alias.name == "minio":
                        offenders.append(f"{path.name}: import {alias.name}")
                    if alias.name == "pyforge" or alias.name.startswith("pyforge."):
                        offenders.append(f"{path.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                top = node.module.split(".")[0]
                if top in _HTTP_TOPLEVEL or top == "minio" or node.module.startswith("urllib.request"):
                    offenders.append(f"{path.name}: from {node.module}")
                if node.module == "pyforge" or node.module.startswith("pyforge."):
                    offenders.append(f"{path.name}: from {node.module}")
    assert offenders == []
