"""Story 91.1 — stations index at /stations/ behind pyforge.steward.stations_index."""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import textwrap
from http import HTTPStatus
from pathlib import Path

import pytest
from django.conf import settings
from django.db import connection
from django.test import Client
from django.test import RequestFactory
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django_pyforge.context_processors import is_switcher_tile
from django_pyforge.discovery import iter_portal_configs
from django_pyforge.events.constants import STATION_TOKENS
from django_pyforge.flags import configure_file_provider
from django_pyforge.roles import IDP_TOKEN_CLAIMS_SESSION_KEY
from django_pyforge.roles import IDP_TOKEN_ROLES_SESSION_KEY
from django_pyforge.roles import prefixed_station
from django_pyforge.roles import prefixed_tenant
from django_pyforge.roles import roles_from_request
from openfeature import api
from wagtail.models import Page

from config import optional_components
from config.stations_index import STATIONS_INDEX_FLAG

_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
_REMEDY = "Install pyforge-herald on this host to enable herald routes."
_FORBIDDEN_BODY_FRAGMENTS = (_REMEDY, "Traceback", sys.prefix, str(settings.BASE_DIR))


def _stations_index_flagd_tree(default_variant: str) -> bytes:
    return json.dumps(
        {
            "flags": {
                STATIONS_INDEX_FLAG: {
                    "state": "ENABLED",
                    "variants": {"on": True, "off": False},
                    "defaultVariant": default_variant,
                },
            },
        },
    ).encode()


@pytest.fixture
def flag_off_tree(tmp_path: Path) -> Path:
    path = tmp_path / "stations-index-off.json"
    path.write_bytes(_stations_index_flagd_tree("off"))
    return path


@pytest.fixture
def flag_on_tree(tmp_path: Path) -> Path:
    path = tmp_path / "stations-index-on.json"
    path.write_bytes(_stations_index_flagd_tree("on"))
    return path


@pytest.fixture(autouse=True)
def _clear_flag_providers():
    yield
    api.clear_providers()


def _configure_flags(path: Path) -> None:
    configure_file_provider(path)


def _save_session_roles(client: Client, groups: list[str]) -> None:
    session = client.session
    session[IDP_TOKEN_ROLES_SESSION_KEY] = groups
    session[IDP_TOKEN_CLAIMS_SESSION_KEY] = {"sub": "operator", "groups": groups}
    session.save()


def _assert_no_forbidden_fragments(body: bytes) -> None:
    text = body.decode()
    for fragment in _FORBIDDEN_BODY_FRAGMENTS:
        assert fragment not in text


@pytest.mark.django_db
def test_flag_off_matches_urlconf_without_index_anonymous(
    client: Client,
    flag_off_tree: Path,
) -> None:
    _configure_flags(flag_off_tree)
    with_index = client.get("/stations/")
    with override_settings(ROOT_URLCONF="tests._urls_without_stations_index"):
        without_index = client.get("/stations/")
    assert with_index.status_code == without_index.status_code
    assert with_index["Content-Type"] == without_index["Content-Type"]
    assert with_index.content == without_index.content


@pytest.mark.django_db
def test_flag_off_matches_urlconf_without_index_admin(
    client: Client,
    flag_off_tree: Path,
) -> None:
    _configure_flags(flag_off_tree)
    _save_session_roles(client, ["pyforge:admin"])
    with_index = client.get("/stations/")
    with override_settings(ROOT_URLCONF="tests._urls_without_stations_index"):
        without_index = client.get("/stations/")
    assert with_index.content == without_index.content


@pytest.mark.django_db
def test_flag_off_options_byte_identical(
    client: Client,
    flag_off_tree: Path,
) -> None:
    _configure_flags(flag_off_tree)
    with_index = client.options("/stations/")
    with override_settings(ROOT_URLCONF="tests._urls_without_stations_index"):
        without_index = client.options("/stations/")
    assert with_index.status_code == without_index.status_code
    assert with_index.content == without_index.content


@pytest.mark.django_db
def test_flag_off_does_not_import_station_api(
    client: Client,
    flag_off_tree: Path,
) -> None:
    sys.modules.pop("config.station_api", None)
    _configure_flags(flag_off_tree)
    records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = _Capture()
    logger = logging.getLogger("config.optional_components")
    logger.addHandler(handler)
    try:
        client.get("/stations/")
        assert "config.station_api" not in sys.modules
        assert records == []
    finally:
        logger.removeHandler(handler)


@pytest.mark.django_db
def test_flag_off_with_wagtail_page_at_slug_stations(
    client: Client,
    flag_off_tree: Path,
) -> None:
    root = Page.get_first_root_node()
    if root is None:
        root = Page.add_root(title="Root", slug="root")
    page = Page(title="Stations landing", slug="stations")
    root.add_child(instance=page)
    page.save_revision().publish()
    _configure_flags(flag_off_tree)
    with_index = client.get("/stations/")
    with override_settings(ROOT_URLCONF="tests._urls_without_stations_index"):
        without_index = client.get("/stations/")
    assert with_index.content == without_index.content


@pytest.mark.django_db
def test_flag_on_anonymous_get_forbidden_empty_body(
    client: Client,
    flag_on_tree: Path,
) -> None:
    _configure_flags(flag_on_tree)
    index = client.get("/stations/")
    warden = client.get("/stations/warden/")
    assert index.status_code == HTTPStatus.FORBIDDEN
    assert warden.status_code == HTTPStatus.FORBIDDEN
    assert index.content == b""
    assert warden.content == b""


@pytest.mark.django_db
def test_flag_on_tenant_only_role_forbidden(
    client: Client,
    flag_on_tree: Path,
) -> None:
    _configure_flags(flag_on_tree)
    _save_session_roles(client, [prefixed_tenant("t1")])
    response = client.get("/stations/")
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.content == b""


@pytest.mark.django_db
def test_flag_on_herald_only_one_mounted_row(
    client: Client,
    flag_on_tree: Path,
) -> None:
    _configure_flags(flag_on_tree)
    _save_session_roles(client, [prefixed_station("herald")])
    response = client.get("/stations/")
    assert response.status_code == HTTPStatus.OK
    body = response.content.decode()
    assert body.count("mounted") == 1
    assert "/stations/herald/" in body
    assert "absent" not in body
    _assert_no_forbidden_fragments(response.content)


@pytest.mark.django_db
def test_flag_on_admin_lists_switcher_tiles(
    client: Client,
    flag_on_tree: Path,
) -> None:
    _configure_flags(flag_on_tree)
    _save_session_roles(client, ["pyforge:admin"])
    admin_request = RequestFactory().get("/stations/")
    admin_request.idp_roles = ["pyforge:admin"]  # type: ignore[attr-defined]
    roles = roles_from_request(admin_request)
    expected_names = sorted(
        portal.station_name
        for portal in iter_portal_configs()
        if is_switcher_tile(portal, roles)
    )
    response = client.get("/stations/")
    assert response.status_code == HTTPStatus.OK
    body = response.content.decode()
    for station in STATION_TOKENS:
        assert station in body
        assert f"/stations/{station}/" in body
    assert "infra-probe" not in body
    for name in expected_names:
        assert name in body
    assert body.count("mounted") == len(expected_names)
    tbody_match = re.search(r"<tbody>(.*?)</tbody>", body, re.DOTALL)
    assert tbody_match is not None
    listed = re.findall(r"<tr>\s*<td>([^<]+)</td>", tbody_match.group(1))
    assert listed == expected_names
    _assert_no_forbidden_fragments(response.content)


@pytest.mark.django_db
def test_flag_on_admin_post_returns_405(
    client: Client,
    flag_on_tree: Path,
) -> None:
    _configure_flags(flag_on_tree)
    _save_session_roles(client, ["pyforge:admin"])
    index = client.post("/stations/")
    warden = client.post("/stations/warden/")
    assert index.status_code == warden.status_code == HTTPStatus.METHOD_NOT_ALLOWED


@pytest.mark.django_db
def test_flag_on_admin_read_only_queries(
    client: Client,
    flag_on_tree: Path,
) -> None:
    _configure_flags(flag_on_tree)
    _save_session_roles(client, ["pyforge:admin"])
    with CaptureQueriesContext(connection) as captured:
        client.get("/stations/")
    for query in captured.captured_queries:
        sql = query["sql"].upper()
        assert "INSERT" not in sql
        assert "UPDATE" not in sql
        assert "DELETE" not in sql


@pytest.mark.django_db
def test_flag_on_herald_present_no_absent_rows(
    client: Client,
    flag_on_tree: Path,
) -> None:
    _configure_flags(flag_on_tree)
    _save_session_roles(client, ["pyforge:admin"])
    response = client.get("/stations/")
    assert response.status_code == HTTPStatus.OK
    assert "absent" not in response.content.decode()
    assert optional_components.absent_reason("herald") is None


def _database_url_for_child() -> str | None:
    db = settings.DATABASES["default"]
    engine = db.get("ENGINE", "")
    if "postgresql" not in engine:
        return None
    name = db.get("NAME")
    if not name:
        return None
    user = db.get("USER") or ""
    password = db.get("PASSWORD") or ""
    host = db.get("HOST") or ""
    port = db.get("PORT") or ""
    if host.startswith("/"):
        return f"postgres:///{name}?host={host}"
    auth = ""
    if user:
        auth = f"{user}:{password}@" if password else f"{user}@"
    host_part = host or "localhost"
    port_part = f":{port}" if port else ""
    return f"postgres://{auth}{host_part}{port_part}/{name}"


def _build_herald_absent_index_child(flagd_path: str) -> str:
    return textwrap.dedent(
        f"""
        import django
        import html
        import json
        import logging
        import re
        import sys
        from pathlib import Path
        from django.test import Client
        from django_pyforge.flags import configure_file_provider
        from django_pyforge.roles import IDP_TOKEN_CLAIMS_SESSION_KEY
        from django_pyforge.roles import IDP_TOKEN_ROLES_SESSION_KEY

        records: list[logging.LogRecord] = []

        class _CaptureHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record)

        cap = _CaptureHandler()
        cap.setLevel(logging.WARNING)
        logging.getLogger("config.optional_components").addHandler(cap)
        logging.getLogger("config.optional_components").setLevel(logging.WARNING)

        class _HeraldAbsentFinder:
            def find_spec(self, fullname, path, target=None):
                if fullname == "pyforge.herald" or fullname.startswith(
                    "pyforge.herald."
                ):
                    raise ModuleNotFoundError(name=fullname)
                return None

        sys.meta_path.insert(0, _HeraldAbsentFinder())

        django.setup()
        from django.conf import settings
        from config import optional_components

        if "testserver" not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, "testserver"]

        configure_file_provider(Path({flagd_path!r}))

        client = Client()
        session = client.session
        session[IDP_TOKEN_ROLES_SESSION_KEY] = ["pyforge:admin"]
        session[IDP_TOKEN_CLAIMS_SESSION_KEY] = {{
            "sub": "operator",
            "groups": ["pyforge:admin"],
        }}
        session.save()

        first = client.get("/stations/")
        second = client.get("/stations/")
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.status_code < 500
        body = first.content.decode()
        reason = optional_components.absent_reason("herald")
        assert reason is not None
        assert reason in html.unescape(body)
        tbody_match = re.search(r"<tbody>(.*?)</tbody>", body, re.DOTALL)
        assert tbody_match is not None
        tbody = tbody_match.group(1)
        assert "absent" in tbody
        assert '<a href="/stations/herald/">' not in tbody
        assert "herald" in tbody
        for station in (
            "atlas", "doctor", "marshal", "mason", "scribe", "steward", "warden"
        ):
            assert f"/stations/{{station}}/" in body
        oc_records = [r for r in records if r.name == "config.optional_components"]
        assert len(oc_records) == 1
        print("OK", reason)
        """
    )


@pytest.mark.django_db
def test_flag_on_herald_absent_lists_reason_once(
    client: Client,
    flag_on_tree: Path,
    tmp_path: Path,
) -> None:
    flag_on_tree.write_bytes(_stations_index_flagd_tree("on"))
    child_env = dict(os.environ)
    child_env["DJANGO_SETTINGS_MODULE"] = "config.settings.test"
    child_env.setdefault("COMPONENT_RUNTIME", "local")
    child_env["PYTHONPATH"] = os.pathsep.join(
        [str(_PLATFORM_ROOT), *(entry for entry in sys.path if entry)],
    )
    db_url = _database_url_for_child()
    if db_url is not None:
        child_env["DATABASE_URL"] = db_url
    script = _build_herald_absent_index_child(str(flag_on_tree))
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
        cwd=_PLATFORM_ROOT,
        env=child_env,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "OK" in proc.stdout
    combined = proc.stdout + proc.stderr
    assert _REMEDY not in combined


@pytest.mark.django_db
def test_pyforge_steward_stations_index_flag_two_states(
    client: Client,
    flag_on_tree: Path,
    flag_off_tree: Path,
) -> None:
    """AC8: one flagd tree on, one off — index 200 vs legacy 404 on fresh DB."""
    _save_session_roles(client, ["pyforge:admin"])
    _configure_flags(flag_on_tree)
    on = client.get("/stations/")
    assert on.status_code == HTTPStatus.OK
    _configure_flags(flag_off_tree)
    off = client.get("/stations/")
    assert off.status_code == HTTPStatus.NOT_FOUND
