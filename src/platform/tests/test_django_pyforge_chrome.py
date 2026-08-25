"""Story 18.1: django-pyforge is the only chrome."""

from __future__ import annotations

import ast
import re
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.conf import settings
from django.core.checks import run_checks
from django.template import Context
from django.template import Engine
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.urls import resolve
from django_pyforge.checks import validate_portal_config
from django_pyforge.context_processors import chrome
from django_pyforge.discovery import iter_portal_configs
from django_pyforge.portals import PortalConfig

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
COMPLIANCE_TEMPLATES = PLATFORM_ROOT / "compliance_face" / "templates"
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
PORTAL_STATIC_AND_TEMPLATES = (
    PLATFORM_ROOT / "compliance_face",
    REPO_ROOT
    / "src"
    / "shared"
    / "packages"
    / "django-pyforge"
    / "src"
    / "django_pyforge"
    / "probe_portal",
)
EXPECTED_PORTALS = frozenset({"warden", "chrome-probe"})


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
    warden_html = render_to_string("compliance_face/chrome.html", ctx)
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
            "urlconf": "compliance_face.urls",
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
            "urlconf": "compliance_face.urls",
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
        dirs=[str(COMPLIANCE_TEMPLATES), str(PROBE_TEMPLATES)],
        app_dirs=False,
        libraries={},
    )
    missing: list[object] = []
    for name in ("compliance_face/chrome.html", "probe_portal/home.html"):
        with pytest.raises(TemplateDoesNotExist) as caught:
            engine.get_template(name).render(Context({}))
        missing.append(caught.value.args[0])
    assert missing[0] == missing[1]
    assert "django_pyforge/base.html" in str(missing[0])
