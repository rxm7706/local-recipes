"""Story 18.1: django-pyforge is the only chrome."""

from __future__ import annotations

import ast
import re
from datetime import date
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.conf import settings
from django.core.checks import run_checks
from django.http import HttpRequest
from django.http import HttpResponse
from django.template import Context
from django.template import Engine
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.urls import resolve
from django_pyforge.checks import validate_portal_config
from django_pyforge.context_processors import chrome
from django_pyforge.discovery import iter_portal_configs
from django_pyforge.middleware import TokenRolesMiddleware
from django_pyforge.portals import PortalConfig
from django_pyforge.probe_portal import views as probe_views
from django_pyforge.roles import IDP_TOKEN_ROLES_SESSION_KEY
from django_warden_fabric import views as warden_views

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLATFORM_ROOT.parents[1]
CHROME_DIV = re.compile(
    r'<div id="pyforge-chrome">.*?</div>',
    re.DOTALL,
)
CHROME_COPY_NAMES = re.compile(
    r"(^|/)(base\.html|switcher\.html|theme\.css)$",
    re.IGNORECASE,
)
URLCONF_PATH = PLATFORM_ROOT / "config" / "urls.py"
WARDEN_TEMPLATES = (
    REPO_ROOT
    / "src"
    / "shared"
    / "packages"
    / "django-warden"
    / "src"
    / "django_warden_fabric"
    / "templates"
)
PROBE_TEMPLATES = (
    REPO_ROOT
    / "src"
    / "shared"
    / "packages"
    / "django-pyforge"
    / "src"
    / "django_pyforge"
    / "probe_portal"
    / "templates"
)
_SHARED = REPO_ROOT / "src" / "shared" / "packages"
PORTAL_STATIC_AND_TEMPLATES = (
    _SHARED / "django-warden" / "src" / "django_warden_fabric",
    _SHARED / "django-atlas" / "src" / "django_atlas_portal",
    _SHARED / "django-doctor" / "src" / "django_doctor_portal",
    _SHARED / "django-herald" / "src" / "django_herald_portal",
    _SHARED / "django-marshal" / "src" / "django_marshal_portal",
    _SHARED / "django-mason" / "src" / "django_mason_portal",
    _SHARED / "django-scribe" / "src" / "django_scribe_portal",
    _SHARED / "django-steward" / "src" / "django_steward_portal",
    _SHARED / "django-pyforge" / "src" / "django_pyforge" / "probe_portal",
    _SHARED / "django-pyforge" / "src" / "django_pyforge" / "workclass_probe",
)
EXPECTED_PORTALS = frozenset(
    {
        "atlas",
        "doctor",
        "herald",
        "marshal",
        "mason",
        "scribe",
        "steward",
        "warden",
        "chrome-probe",
        "infra-probe",
    },
)
SWITCHER_PORTALS = EXPECTED_PORTALS - {"infra-probe"}


def _portal_ns(fields: dict[str, object]) -> SimpleNamespace:
    cfg = SimpleNamespace()
    for key, value in fields.items():
        setattr(cfg, key, value)
    return cfg


def test_two_portals_render_byte_identical_chrome() -> None:
    warden_match = resolve("/stations/warden/")
    probe_match = resolve("/stations/chrome-probe/")
    assert warden_match.func.__name__ == "chrome_home"
    assert probe_match.func.__name__ == "chrome_home"
    ctx = chrome(RequestFactory().get("/stations/warden/"))
    warden_html = render_to_string("warden_fabric/chrome.html", ctx)
    probe_html = render_to_string("probe_portal/home.html", ctx)
    chrome_w = CHROME_DIV.search(warden_html)
    chrome_p = CHROME_DIV.search(probe_html)
    assert chrome_w is not None
    assert chrome_p is not None
    assert chrome_w.group(0) == chrome_p.group(0)
    origin = Path(apps.get_app_config("django_pyforge").path)
    assert origin.name == "django_pyforge"
    assert "django_pyforge/theme.css" in warden_html
    assert "django_pyforge/theme.css" in probe_html
    processors = settings.TEMPLATES[0]["OPTIONS"]["context_processors"]
    assert "django_pyforge.context_processors.chrome" in processors


def test_registered_system_checks_are_loaded() -> None:
    apps.get_app_config("django_pyforge").ready()
    chrome_ids = {
        message.id
        for message in run_checks()
        if isinstance(message.id, str) and message.id.startswith("django_pyforge.")
    }
    assert not chrome_ids


def test_portal_dirs_must_not_ship_chrome_copies() -> None:
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for root in PORTAL_STATIC_AND_TEMPLATES
        for path in root.rglob("*")
        if path.is_file()
        and (
            "/templates/django_pyforge/" in path.as_posix()
            or "/static/django_pyforge/" in path.as_posix()
            or CHROME_COPY_NAMES.search(path.name)
        )
    ]
    assert offenders == [], (
        "portals must not ship chrome copies: " + ", ".join(offenders)
    )


def test_host_urlconf_has_no_station_roster() -> None:
    source = URLCONF_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    roster = [
        value
        for value in literals
        if value.startswith("stations/") and value != "stations/"
    ]
    assert roster == [], roster
    assert "django_pyforge.urls" in literals
    names = {cfg.station_name for cfg in iter_portal_configs()}
    assert names == EXPECTED_PORTALS


def test_outside_prefix_registration_fails() -> None:
    bad = _portal_ns(
        {
            "name": "tests.bad_portal",
            "station_name": "warden",
            "mount_token": "/compliance/",
            "mcp_token": "mcp:warden",
            "chrome_hooks": (),
            "owner_slug": "warden",
            "backup": "pyforge-steward",
            "work_class": "03",
            "promotion_date": date(2026, 8, 22),
            "urlconf": "django_warden_fabric.urls",
        },
    )
    errors = validate_portal_config(bad)  # type: ignore[arg-type]
    assert any(err.id == "django_pyforge.E001" for err in errors)


def test_sla_body_is_not_a_chrome_field() -> None:
    sneaky = _portal_ns(
        {
            "name": "tests.sla_portal",
            "sla_body": "must not live on chrome",
            "station_name": "warden",
            "mount_token": "/stations/warden/",
            "mcp_token": "mcp:warden",
            "chrome_hooks": (),
            "owner_slug": "warden",
            "backup": "pyforge-steward",
            "work_class": "03",
            "promotion_date": date(2026, 8, 22),
            "urlconf": "django_warden_fabric.urls",
        },
    )
    errors = validate_portal_config(sneaky)  # type: ignore[arg-type]
    assert any(err.id == "django_pyforge.E003" for err in errors)


def test_portal_configs_carry_operating_model_fields() -> None:
    portals = list(iter_portal_configs())
    assert {portal.station_name for portal in portals} == EXPECTED_PORTALS
    for portal in portals:
        assert isinstance(portal, PortalConfig)
        assert portal.owner_slug
        assert portal.backup
        assert portal.work_class
        assert isinstance(portal.promotion_date, date)
        assert not hasattr(portal, "sla_body")
        assert portal.mount_token == f"/stations/{portal.station_name}/"


def test_removing_chrome_breaks_both_portals_identically() -> None:
    engine = Engine(
        dirs=[str(WARDEN_TEMPLATES), str(PROBE_TEMPLATES)],
        app_dirs=False,
        libraries={},
    )
    missing: list[object] = []
    for name in ("warden_fabric/chrome.html", "probe_portal/home.html"):
        with pytest.raises(TemplateDoesNotExist) as caught:
            engine.get_template(name).render(Context({}))
        missing.append(caught.value.args[0])
    assert missing[0] == missing[1]
    assert "django_pyforge/base.html" in str(missing[0])


def _switcher_html(request: HttpRequest) -> str:
    return render_to_string("django_pyforge/switcher.html", chrome(request))


def test_missing_station_role_omits_that_station_from_the_switcher() -> None:
    request = RequestFactory().get("/stations/warden/")
    request.idp_roles = ["warden"]
    html = _switcher_html(request)
    assert "/stations/warden/" in html
    for name in EXPECTED_PORTALS - {"warden"}:
        assert f"/stations/{name}/" not in html
    assert {cfg.station_name for cfg in iter_portal_configs()} == EXPECTED_PORTALS


def test_direct_url_is_refused_by_the_station_not_the_switcher() -> None:
    hidden_req = RequestFactory().get("/stations/chrome-probe/")
    hidden_req.idp_roles = ["warden"]
    hidden = probe_views.chrome_home(hidden_req)
    assert hidden.status_code == HTTPStatus.FORBIDDEN
    visible_req = RequestFactory().get("/stations/warden/")
    visible_req.idp_roles = ["warden"]
    visible = warden_views.chrome_home(visible_req)
    assert visible.status_code == HTTPStatus.OK
    body = visible.content.decode()
    assert "/stations/chrome-probe/" not in body
    assert "/stations/warden/" in body


def test_switcher_uses_token_roles_not_django_groups() -> None:
    class BoomGroups:
        def __contains__(self, item: object) -> bool:
            raise AssertionError

        def __iter__(self):
            raise AssertionError

        def all(self) -> list[object]:
            raise AssertionError

        def values_list(self, *args: object, **kwargs: object) -> list[object]:
            raise AssertionError

    request = RequestFactory().get("/stations/warden/")
    request.user = SimpleNamespace(groups=BoomGroups())
    request.idp_roles = []
    html = _switcher_html(request)
    assert "/stations/warden/" not in html
    assert "/stations/chrome-probe/" not in html


def test_empty_token_roles_on_the_next_request_list_no_stations() -> None:
    first = RequestFactory().get("/stations/warden/")
    first.idp_roles = list(EXPECTED_PORTALS)
    first_names = {portal.station_name for portal in chrome(first)["pyforge_portals"]}
    assert first_names == SWITCHER_PORTALS
    assert "infra-probe" not in first_names
    second = RequestFactory().get("/stations/warden/")
    second.idp_roles = []
    assert list(chrome(second)["pyforge_portals"]) == []
    html = _switcher_html(second)
    assert "/stations/warden/" not in html
    assert "/stations/chrome-probe/" not in html


def test_token_roles_middleware_copies_session_when_unset() -> None:
    request = RequestFactory().get("/stations/warden/")
    request.session = {IDP_TOKEN_ROLES_SESSION_KEY: ["warden"]}
    seen: dict[str, object] = {}

    def inner(req: HttpRequest) -> HttpResponse:
        seen["roles"] = req.idp_roles
        return HttpResponse()

    TokenRolesMiddleware(inner)(request)
    assert seen["roles"] == ["warden"]
    preset = RequestFactory().get("/")
    preset.idp_roles = ["chrome-probe"]
    preset.session = {IDP_TOKEN_ROLES_SESSION_KEY: ["warden"]}
    TokenRolesMiddleware(inner)(preset)
    assert seen["roles"] == ["chrome-probe"]
    string_session = RequestFactory().get("/")
    string_session.session = {IDP_TOKEN_ROLES_SESSION_KEY: "warden"}
    TokenRolesMiddleware(inner)(string_session)
    assert seen["roles"] == ["warden"]
    html = _switcher_html(string_session)
    assert "/stations/warden/" in html
    assert "/stations/chrome-probe/" not in html
