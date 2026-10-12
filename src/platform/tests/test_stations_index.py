"""Story 91.1 — stations index at /stations/ behind pyforge.steward.stations_index."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from html.parser import HTMLParser
from http import HTTPStatus
from pathlib import Path
from typing import Any

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


@dataclass(frozen=True)
class _IndexRow:
    station: str
    state: str
    detail: str
    hrefs: tuple[str, ...]


class _IndexTableParser(HTMLParser):
    """Collect each ``<tbody>`` row's cell text and the link targets in that row."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[tuple[list[str], list[str]]] = []
        self._in_tbody = False
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tbody":
            self._in_tbody = True
        elif self._in_tbody and tag == "tr":
            self.rows.append(([], []))
        elif self._in_tbody and tag == "td":
            self._cell = []
        elif self._cell is not None and tag == "a":
            self.rows[-1][1].extend(
                value for key, value in attrs if key == "href" and value
            )

    def handle_endtag(self, tag: str) -> None:
        if tag == "tbody":
            self._in_tbody = False
        elif tag == "td" and self._cell is not None:
            self.rows[-1][0].append("".join(self._cell).strip())
            self._cell = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)


def _index_rows(body: str) -> list[_IndexRow]:
    """The index table's rows, in page order: station, state, detail, links."""
    parser = _IndexTableParser()
    parser.feed(body)
    parser.close()
    rows: list[_IndexRow] = []
    for cells, hrefs in parser.rows:
        station, state, detail = cells
        rows.append(_IndexRow(station, state, detail, tuple(hrefs)))
    return rows


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
    rows = _index_rows(response.content.decode())
    listed = [row.station for row in rows]
    # AC3: exactly the rows is_switcher_tile admits, ordered by station_name.
    assert listed == expected_names
    assert set(STATION_TOKENS) <= set(listed)
    assert "infra-probe" not in listed
    for row in rows:
        assert row.state == "mounted"
        assert row.hrefs == (f"/stations/{row.station}/",)
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


_CHILD_PAYLOAD_MARKER = "STATIONS_INDEX_CHILD "
_OPTIONAL_COMPONENTS_LOGGER = "config.optional_components"


def _build_herald_absent_index_child(flagd_path: str) -> str:
    """AC4's child: herald refused at import, two admin GETs, one payload line.

    The child only gathers facts; every assertion runs in the parent, so a
    failure names the exact check rather than a bare child exit status.
    """
    return textwrap.dedent(
        f"""
        import json
        import sys
        from pathlib import Path

        import django
        from django.test import Client
        from django_pyforge.flags import configure_file_provider
        from django_pyforge.roles import IDP_TOKEN_CLAIMS_SESSION_KEY
        from django_pyforge.roles import IDP_TOKEN_ROLES_SESSION_KEY

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

        responses = [client.get("/stations/"), client.get("/stations/")]
        payload = {{
            "statuses": [response.status_code for response in responses],
            "bodies": [response.content.decode() for response in responses],
            "reason": optional_components.absent_reason("herald"),
            "asgi_imported": "config.asgi" in sys.modules,
        }}
        print({_CHILD_PAYLOAD_MARKER!r} + json.dumps(payload))
        """
    )


def _child_payload(stdout: str) -> dict[str, Any]:
    lines = [
        line for line in stdout.splitlines() if line.startswith(_CHILD_PAYLOAD_MARKER)
    ]
    assert len(lines) == 1, stdout
    payload: dict[str, Any] = json.loads(lines[0].removeprefix(_CHILD_PAYLOAD_MARKER))
    return payload


def _json_log_records(output: str) -> list[dict[str, Any]]:
    """The structured (JSON) log records in a child's combined output."""
    records: list[dict[str, Any]] = []
    for line in output.splitlines():
        if not line.startswith("{"):
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


@pytest.mark.django_db
def test_flag_on_herald_absent_lists_reason_once(flag_on_tree: Path) -> None:
    """AC4 and AC5 with herald refused at import in a fresh interpreter.

    The page shows 87.1's reason once, in herald's row. The host log carries
    87.1's own record (logger ``config.optional_components``) exactly once, and
    may also carry herald 37.1's portal record (logger ``django_herald_portal``):
    both records end with 87.1's remedy by design, so AC5's remedy check is
    scoped to the response bodies, as AC5 says, never to the log.
    """
    child_env = dict(os.environ)
    child_env["DJANGO_SETTINGS_MODULE"] = "config.settings.test"
    child_env.setdefault("COMPONENT_RUNTIME", "local")
    # Pin the host's log shape so the record count reads one JSON line per record.
    child_env["DJANGO_LOG_FORMAT"] = "json"
    child_env["DJANGO_LOG_LEVEL"] = "WARNING"
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
    payload = _child_payload(proc.stdout)

    # AC4 precondition: the view itself loaded config.station_api.
    assert payload["asgi_imported"] is False
    # AC4: 200, and no response in this child is a 5xx.
    assert payload["statuses"] == [HTTPStatus.OK, HTTPStatus.OK]
    reason = payload["reason"]
    assert isinstance(reason, str)
    assert "herald" in reason
    assert "pyforge.herald" in reason
    # AC5: no response body carries the remedy, a traceback or a path.
    for body in payload["bodies"]:
        _assert_no_forbidden_fragments(body.encode())

    rows = _index_rows(payload["bodies"][0])
    herald_rows = [row for row in rows if row.station == "herald"]
    # AC4: herald's row reads absent, shows exactly the reason, and has no link.
    assert herald_rows == [_IndexRow("herald", "absent", reason, ())]
    # AC4: every other row reads mounted, with its link.
    others = [row for row in rows if row.station != "herald"]
    assert set(STATION_TOKENS) - {"herald"} <= {row.station for row in others}
    for row in others:
        assert row.state == "mounted"
        assert row.hrefs == (f"/stations/{row.station}/",)

    # AC4: after two GETs, 87.1's reason record appears exactly once.
    reason_records = [
        record
        for record in _json_log_records(proc.stdout + proc.stderr)
        if record.get("logger") == _OPTIONAL_COMPONENTS_LOGGER
        and reason in str(record.get("event", ""))
    ]
    assert len(reason_records) == 1, proc.stderr


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
