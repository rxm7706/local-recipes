"""Story 91.1 — stations index at /stations/ behind pyforge.steward.stations_index."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from html.parser import HTMLParser
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from urllib.parse import quote

import environ
import pytest
from django.conf import settings
from django.db import connection
from django.db.backends.base.creation import TEST_DATABASE_PREFIX
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
from wagtail.models import Site

from config import optional_components
from config.stations_index import STATIONS_INDEX_FLAG

if TYPE_CHECKING:
    from collections.abc import Mapping

_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
_REMEDY = "Install pyforge-herald on this host to enable herald routes."
_FORBIDDEN_BODY_FRAGMENTS = (_REMEDY, "Traceback", sys.prefix, str(settings.BASE_DIR))
_URLCONF_WITHOUT_INDEX = "tests._urls_without_stations_index"
# Session groups per role case; None is an anonymous client.
_ROLE_CASES: dict[str, list[str] | None] = {
    "anonymous": None,
    "admin": ["pyforge:admin"],
}


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


def _apply_role(client: Client, role: str) -> None:
    groups = _ROLE_CASES[role]
    if groups is not None:
        _save_session_roles(client, groups)


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


# --- Fresh-interpreter children (AC2's sys.modules check, AC4) ----------------

_CHILD_PAYLOAD_MARKER = "STATIONS_INDEX_CHILD "
_OPTIONAL_COMPONENTS_LOGGER = "config.optional_components"

# argv: flagd tree path, "herald-present" | "herald-absent", payload marker.
# Story 87.1's finder refuses pyforge.herald and every pyforge.herald.* when
# herald is absent. The child only gathers facts; the parent asserts.
_CHILD_PRELUDE = textwrap.dedent(
    """
    import json
    import sys
    from pathlib import Path

    import django
    from django.test import Client
    from django_pyforge.flags import configure_file_provider
    from django_pyforge.roles import IDP_TOKEN_CLAIMS_SESSION_KEY
    from django_pyforge.roles import IDP_TOKEN_ROLES_SESSION_KEY

    FLAGD_PATH = Path(sys.argv[1])
    HERALD_ABSENT = sys.argv[2] == "herald-absent"
    MARKER = sys.argv[3]


    class _HeraldAbsentFinder:
        def find_spec(self, fullname, path, target=None):
            if fullname == "pyforge.herald" or fullname.startswith("pyforge.herald."):
                raise ModuleNotFoundError(name=fullname)
            return None


    if HERALD_ABSENT:
        sys.meta_path.insert(0, _HeraldAbsentFinder())


    def _boot():
        django.setup()
        from django.conf import settings

        if "testserver" not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, "testserver"]
        configure_file_provider(FLAGD_PATH)


    def _emit(payload):
        from django.db import connection

        payload["database"] = connection.settings_dict["NAME"]
        print(MARKER + json.dumps(payload))
    """,
)

# AC2: after django.setup() and one flag-OFF GET, nothing loaded config.station_api
# and nothing logged on 87.1's logger (captured from before setup, at every level).
_FLAG_OFF_CHILD = _CHILD_PRELUDE + textwrap.dedent(
    """
    import logging

    oc_records = []


    class _Capture(logging.Handler):
        def emit(self, record):
            oc_records.append(record.getMessage())


    oc_logger = logging.getLogger("config.optional_components")
    oc_logger.setLevel(logging.DEBUG)
    oc_logger.addHandler(_Capture())

    _boot()
    response = Client().get("/stations/")
    _emit(
        {
            "status": response.status_code,
            "station_api_loaded": "config.station_api" in sys.modules,
            "optional_components_records": oc_records,
        }
    )
    """,
)

# AC4: two admin GETs with the flag ON, config.asgi never imported.
_FLAG_ON_ADMIN_CHILD = _CHILD_PRELUDE + textwrap.dedent(
    """
    _boot()
    from config import optional_components

    client = Client()
    session = client.session
    session[IDP_TOKEN_ROLES_SESSION_KEY] = ["pyforge:admin"]
    session[IDP_TOKEN_CLAIMS_SESSION_KEY] = {
        "sub": "operator",
        "groups": ["pyforge:admin"],
    }
    session.save()

    responses = [client.get("/stations/"), client.get("/stations/")]
    _emit(
        {
            "statuses": [response.status_code for response in responses],
            "bodies": [response.content.decode() for response in responses],
            "reason": optional_components.absent_reason("herald"),
            "asgi_imported": "config.asgi" in sys.modules,
        }
    )
    """,
)


def _test_database_url(db: Mapping[str, Any]) -> str:
    """A PostgreSQL test database's settings as a URL, or a loud failure.

    The child never falls back to the environment's ``DATABASE_URL``: it writes a
    session row, which must only ever land in the test database.
    """
    name = str(db.get("NAME") or "")
    test_name = (db.get("TEST") or {}).get("NAME")
    is_test_database = bool(name) and (
        name.startswith(TEST_DATABASE_PREFIX) or name == test_name
    )
    if "postgresql" not in str(db.get("ENGINE", "")) or not is_test_database:
        pytest.fail(
            "the child interpreter needs this run's PostgreSQL test database; "
            f"got engine {db.get('ENGINE')!r}, database {name!r}",
        )
    user = quote(str(db.get("USER") or ""), safe="")
    password = quote(str(db.get("PASSWORD") or ""), safe="")
    host = str(db.get("HOST") or "")
    port = str(db.get("PORT") or "")
    auth = f"{user}:{password}@" if password else (f"{user}@" if user else "")
    database = quote(name, safe="")
    if host.startswith("/"):
        return f"postgres://{auth}/{database}?host={quote(host, safe='')}"
    port_part = f":{port}" if port else ""
    return f"postgres://{auth}{quote(host, safe='')}{port_part}/{database}"


def _child_env() -> dict[str, str]:
    child_env = dict(os.environ)
    child_env["DJANGO_SETTINGS_MODULE"] = "config.settings.test"
    child_env.setdefault("COMPONENT_RUNTIME", "local")
    child_env["DATABASE_URL"] = _test_database_url(connection.settings_dict)
    # Pin the host's log shape so one record is one parseable JSON line.
    child_env["DJANGO_LOG_FORMAT"] = "json"
    child_env["DJANGO_LOG_LEVEL"] = "WARNING"
    child_env["PYTHONPATH"] = os.pathsep.join(
        [str(_PLATFORM_ROOT), *(entry for entry in sys.path if entry)],
    )
    return child_env


def _child_payload(stdout: str) -> dict[str, Any]:
    lines = [
        line for line in stdout.splitlines() if line.startswith(_CHILD_PAYLOAD_MARKER)
    ]
    assert len(lines) == 1, stdout
    payload: dict[str, Any] = json.loads(lines[0].removeprefix(_CHILD_PAYLOAD_MARKER))
    return payload


def _run_child(
    script: str,
    flagd_path: Path,
    *,
    herald: str,
) -> tuple[dict[str, Any], subprocess.CompletedProcess[str]]:
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script, str(flagd_path), herald, _CHILD_PAYLOAD_MARKER],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
        cwd=_PLATFORM_ROOT,
        env=_child_env(),
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    payload = _child_payload(proc.stdout)
    # F8: the child used this run's test database, never another one.
    assert payload["database"] == connection.settings_dict["NAME"]
    return payload, proc


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


_POSTGRES = "django.db.backends.postgresql"


@pytest.mark.parametrize(
    "db",
    [
        {"ENGINE": "django.db.backends.sqlite3", "NAME": "test_platform"},
        {"ENGINE": _POSTGRES, "NAME": "platform"},
        {"ENGINE": _POSTGRES, "NAME": ""},
        {"ENGINE": _POSTGRES, "NAME": "platform", "TEST": {"NAME": "ci_platform"}},
    ],
    ids=["not-postgresql", "not-a-test-database", "no-name", "not-the-test-name"],
)
def test_child_database_url_refuses_anything_but_the_test_database(
    db: dict[str, Any],
) -> None:
    """F8: no test database to derive is a loud failure, never a fallback."""
    with pytest.raises(pytest.fail.Exception, match="test database"):
        _test_database_url(db)


@pytest.mark.parametrize(
    "db",
    [
        {
            "ENGINE": _POSTGRES,
            "NAME": "test_platform",
            "USER": "postgres",
            "PASSWORD": "p@ss:word/",
            "HOST": "localhost",
            "PORT": 15432,
        },
        {"ENGINE": _POSTGRES, "NAME": "test_platform_gw1", "HOST": "127.0.0.1"},
        {"ENGINE": _POSTGRES, "NAME": "ci_platform", "TEST": {"NAME": "ci_platform"}},
    ],
    ids=["tcp-with-credentials", "xdist-suffix", "custom-test-name"],
)
def test_child_database_url_round_trips_the_test_database(db: dict[str, Any]) -> None:
    parsed = environ.Env.db_url_config(_test_database_url(db))
    for key in ("NAME", "USER", "PASSWORD", "HOST"):
        assert parsed[key] == (db.get(key) or "")
    assert str(parsed["PORT"] or "") == str(db.get("PORT") or "")


def test_child_database_url_keeps_a_socket_host() -> None:
    url = _test_database_url(
        {"ENGINE": _POSTGRES, "NAME": "test_platform", "HOST": "/run/pg sock"},
    )
    parsed = environ.Env.db_url_config(url)
    assert parsed["NAME"] == "test_platform"
    assert parsed["OPTIONS"] == {"host": "/run/pg sock"}


# --- AC2: with the flag OFF, nothing changes ------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("method", ["get", "options"])
@pytest.mark.parametrize("role", list(_ROLE_CASES))
def test_flag_off_matches_urlconf_without_index(
    client: Client,
    flag_off_tree: Path,
    role: str,
    method: str,
) -> None:
    _configure_flags(flag_off_tree)
    _apply_role(client, role)
    send = getattr(client, method)
    with_index = send("/stations/")
    with override_settings(ROOT_URLCONF=_URLCONF_WITHOUT_INDEX):
        without_index = send("/stations/")
    assert with_index.status_code == without_index.status_code == HTTPStatus.NOT_FOUND
    assert with_index["Content-Type"] == without_index["Content-Type"]
    assert with_index.content == without_index.content


@pytest.mark.django_db
def test_flag_off_with_wagtail_page_at_slug_stations(
    client: Client,
    flag_off_tree: Path,
) -> None:
    site_root = Site.objects.get(is_default_site=True).root_page
    page = Page(title="Stations landing", slug="stations")
    site_root.add_child(instance=page)
    page.save_revision().publish()
    _configure_flags(flag_off_tree)
    with_index = client.get("/stations/")
    with override_settings(ROOT_URLCONF=_URLCONF_WITHOUT_INDEX):
        without_index = client.get("/stations/")
    assert with_index.status_code == without_index.status_code == HTTPStatus.OK
    assert "Stations landing" in with_index.content.decode()
    assert with_index["Content-Type"] == without_index["Content-Type"]
    assert with_index.content == without_index.content


@pytest.mark.django_db
@pytest.mark.parametrize("herald", ["herald-present", "herald-absent"])
def test_flag_off_fresh_interpreter_loads_no_station_api(
    flag_off_tree: Path,
    herald: str,
) -> None:
    """AC2's third bullet, in a fresh interpreter as AC2 says.

    With herald absent, a load of ``config.station_api`` would also log 87.1's
    record, so the logger check has teeth as well as the ``sys.modules`` one.
    """
    payload, _ = _run_child(_FLAG_OFF_CHILD, flag_off_tree, herald=herald)
    assert payload["status"] == HTTPStatus.NOT_FOUND
    assert payload["station_api_loaded"] is False
    assert payload["optional_components_records"] == []


# --- AC3: who may see it -----------------------------------------------------


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
    assert _index_rows(response.content.decode()) == [
        _IndexRow("herald", "mounted", "/stations/herald/", ("/stations/herald/",)),
    ]
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
@pytest.mark.parametrize("role", list(_ROLE_CASES))
def test_flag_on_post_answers_what_warden_answers(
    client: Client,
    flag_on_tree: Path,
    role: str,
) -> None:
    """I/O matrix: POST, any role, gets what POST /stations/warden/ gets (405)."""
    _configure_flags(flag_on_tree)
    _apply_role(client, role)
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


# --- AC4 and AC5: an absent station reads absent, and nothing leaks -----------


@pytest.mark.django_db
def test_flag_on_herald_absent_lists_reason_once(flag_on_tree: Path) -> None:
    """AC4 and AC5 with herald refused at import in a fresh interpreter.

    The page shows 87.1's reason once, in herald's row. The host log carries
    87.1's own record (logger ``config.optional_components``) exactly once, and
    may also carry herald 37.1's portal record (logger ``django_herald_portal``):
    both records end with 87.1's remedy by design, so AC5's remedy check is
    scoped to the response bodies, as AC5 says, never to the log.
    """
    payload, proc = _run_child(
        _FLAG_ON_ADMIN_CHILD, flag_on_tree, herald="herald-absent"
    )

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
def test_flag_on_absent_reason_renders_escaped(
    client: Client,
    flag_on_tree: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC5 regression: the reason is page text, never markup."""
    hostile = "herald is not installed on this host: <script>alert('index')</script>"
    recorded = optional_components.absent_reason

    def _absent_reason(component: str) -> str | None:
        return hostile if component == "herald" else recorded(component)

    monkeypatch.setattr(optional_components, "absent_reason", _absent_reason)
    _configure_flags(flag_on_tree)
    _save_session_roles(client, ["pyforge:admin"])
    response = client.get("/stations/")
    assert response.status_code == HTTPStatus.OK
    body = response.content.decode()
    assert "<script>alert(" not in body
    assert "&lt;script&gt;alert(" in body
    herald_rows = [row for row in _index_rows(body) if row.station == "herald"]
    assert herald_rows == [_IndexRow("herald", "absent", hostile, ())]


# --- AC8: both flag states through the FILE provider --------------------------


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
