"""Story 19.2: seven more portal shells under /stations/."""

from __future__ import annotations

import ast
import tomllib
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace

import pytest
from config.settings.base import LOCAL_APPS
from django.apps import apps
from django.template.loader import render_to_string
from django.test import Client
from django.test import RequestFactory
from django.urls import resolve
from django_atlas_portal import views as atlas_views
from django_pyforge.context_processors import chrome
from django_pyforge.context_processors import is_switcher_tile
from django_pyforge.discovery import iter_portal_configs
from django_pyforge.roles import IDP_TOKEN_CLAIMS_SESSION_KEY
from django_pyforge.roles import IDP_TOKEN_ROLES_SESSION_KEY
from django_pyforge.roles import prefixed_station
from django_pyforge.workclass_probe import views as infra_views

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLATFORM_ROOT.parents[1]
SHARED_PACKAGES = REPO_ROOT / "src" / "shared" / "packages"

EIGHT_STATIONS = (
    "atlas",
    "doctor",
    "herald",
    "marshal",
    "mason",
    "scribe",
    "steward",
    "warden",
)
NEW_STATIONS = tuple(station for station in EIGHT_STATIONS if station != "warden")
_HTTP_TOPLEVEL = frozenset({"httpx", "requests", "http.client"})


def _portal_tree(station: str) -> Path:
    return SHARED_PACKAGES / f"django-{station}" / "src" / f"django_{station}_portal"


def _iter_py(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if path.is_file())


def _raw_http_imports(tree: ast.AST) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if (
                    top in _HTTP_TOPLEVEL
                    or alias.name in _HTTP_TOPLEVEL
                    or alias.name.startswith("http.client")
                    or alias.name == "urllib.request"
                ):
                    found.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            top = module.split(".")[0]
            if (
                top in _HTTP_TOPLEVEL
                or module in _HTTP_TOPLEVEL
                or module.startswith(("urllib.request", "http.client"))
            ):
                found.append(f"from {module} import ...")
            from_urllib = any(alias.name == "request" for alias in node.names)
            if module == "urllib" and from_urllib:
                found.append("from urllib import request")
            from_http_client = any(alias.name == "client" for alias in node.names)
            if module == "http" and from_http_client:
                found.append("from http import client")
    return found


def _pyforge_package_imports(tree: ast.AST) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(
                f"import {alias.name}"
                for alias in node.names
                if alias.name == "pyforge" or alias.name.startswith("pyforge.")
            )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "pyforge" or module.startswith("pyforge."):
                found.append(f"from {module} import ...")
    return found


def _pyforge_hit_module(hit: str) -> str:
    if hit.startswith("from "):
        return hit.removeprefix("from ").removesuffix(" import ...")
    return hit.removeprefix("import ")


def _atlas_pyforge_allowed(hit: str) -> bool:
    """Atlas may import steward dashboard isolation + existing MCP (21.2).

    ``pyforge.atlas.dashboard`` (Vizro CLI) and other stations stay forbidden.
    """
    module = _pyforge_hit_module(hit)
    allowed = ("pyforge.steward.dashboard", "pyforge.atlas.mcp")
    return any(
        module == prefix or module.startswith(prefix + ".") for prefix in allowed
    )


def _disallowed_pyforge_imports(station: str, tree: ast.AST) -> list[str]:
    hits = _pyforge_package_imports(tree)
    if station != "atlas":
        return hits
    return [hit for hit in hits if not _atlas_pyforge_allowed(hit)]


def _model_subclasses(tree: ast.AST) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for base in node.bases:
            name = ast.unparse(base)
            if name in {"Model", "models.Model"} or name.endswith(".Model"):
                found.append(node.name)
    return found


@pytest.mark.django_db
def test_one_session_eight_station_gets() -> None:
    client = Client()
    session = client.session
    prefixed = [prefixed_station(station) for station in EIGHT_STATIONS]
    session[IDP_TOKEN_ROLES_SESSION_KEY] = prefixed
    session[IDP_TOKEN_CLAIMS_SESSION_KEY] = {
        "sub": "operator",
        "groups": prefixed,
    }
    session.save()

    for station in EIGHT_STATIONS:
        path = f"/stations/{station}/"
        assert path.startswith("/stations/")
        response = client.get(path)
        assert response.status_code == HTTPStatus.OK, (station, response.status_code)
        assert response.status_code != HTTPStatus.FOUND
        location = response.get("Location", "")
        assert "login" not in location.lower()
        match = resolve(path)
        assert match.func.__name__ == "chrome_home"


def test_naming_triples() -> None:
    warden_pyproject = tomllib.loads(
        (SHARED_PACKAGES / "django-warden" / "pyproject.toml").read_text(
            encoding="utf-8",
        ),
    )
    assert warden_pyproject["project"]["name"] == "django-warden"
    warden = apps.get_app_config("warden_fabric")
    assert warden.name == "django_warden_fabric"
    assert warden.label == "warden_fabric"

    for station in NEW_STATIONS:
        pkg = SHARED_PACKAGES / f"django-{station}"
        data = tomllib.loads((pkg / "pyproject.toml").read_text(encoding="utf-8"))
        assert data["project"]["name"] == f"django-{station}"
        wheel = data["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
        assert wheel == [f"src/django_{station}_portal"]
        cfg = apps.get_app_config(f"{station}_portal")
        assert cfg.name == f"django_{station}_portal"
        assert cfg.label == f"{station}_portal"
        assert cfg.station_name == station
        module_root = pkg / "src" / f"django_{station}_portal"
        assert module_root.joinpath("models.py").is_file() is False
        assert not list(module_root.rglob("migrations/*.py"))


def test_new_portals_are_client_only_and_projection() -> None:
    offenders: list[str] = []
    for station in NEW_STATIONS:
        root = _portal_tree(station)
        for path in _iter_py(root):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            offenders.extend(
                f"{path}: {hit}" for hit in _disallowed_pyforge_imports(station, tree)
            )
            offenders.extend(f"{path}: {hit}" for hit in _raw_http_imports(tree))
            offenders.extend(
                f"{path}: Model subclass {hit}" for hit in _model_subclasses(tree)
            )
    assert offenders == []


def test_work_class_01_and_02_are_not_switcher_tiles() -> None:
    roles = frozenset({"infra-probe", "cache-probe", "warden"})
    hidden_01 = SimpleNamespace(station_name="infra-probe", work_class="01")
    hidden_02 = SimpleNamespace(station_name="cache-probe", work_class="02")
    visible = SimpleNamespace(station_name="warden", work_class="03")
    missing_class = SimpleNamespace(station_name="warden")
    assert is_switcher_tile(hidden_01, roles) is False
    assert is_switcher_tile(hidden_02, roles) is False
    assert is_switcher_tile(visible, roles) is True
    assert is_switcher_tile(missing_class, roles) is True


def test_work_class_01_is_omitted_from_switcher_but_url_resolves() -> None:
    request = RequestFactory().get("/stations/infra-probe/")
    request.idp_roles = ["pyforge:station:infra-probe", "pyforge:station:warden"]
    listed = {portal.station_name for portal in chrome(request)["pyforge_portals"]}
    assert "infra-probe" not in listed
    assert "warden" in listed
    html = render_to_string("django_pyforge/switcher.html", chrome(request))
    assert "/stations/infra-probe/" not in html
    assert "/stations/warden/" in html
    mounts = [portal.mount_token for portal in chrome(request)["pyforge_portals"]]
    assert "/stations/infra-probe/" not in mounts
    assert "/stations/warden/" in mounts

    match = resolve("/stations/infra-probe/")
    assert match.func.__name__ == "chrome_home"
    allowed = RequestFactory().get("/stations/infra-probe/")
    allowed.idp_roles = ["pyforge:station:infra-probe"]
    response = infra_views.chrome_home(allowed)
    assert response.status_code == HTTPStatus.OK
    assert b'id="infra-probe-body"' in response.content

    by_name = {portal.station_name: portal for portal in iter_portal_configs()}
    assert by_name["infra-probe"].work_class == "01"
    assert "infra-probe" in {portal.station_name for portal in iter_portal_configs()}


@pytest.mark.django_db
def test_new_shell_without_role_is_forbidden() -> None:
    denied = RequestFactory().get("/stations/atlas/")
    denied.idp_roles = ["pyforge:station:warden"]
    response = atlas_views.chrome_home(denied)
    assert response.status_code == HTTPStatus.FORBIDDEN
    allowed = RequestFactory().get("/stations/atlas/")
    allowed.idp_roles = ["atlas"]
    ok = atlas_views.chrome_home(allowed)
    assert ok.status_code == HTTPStatus.OK


def test_fixtures_are_not_production_installed_apps() -> None:
    assert "django_pyforge.probe_portal" not in LOCAL_APPS
    assert "django_pyforge.workclass_probe" not in LOCAL_APPS
