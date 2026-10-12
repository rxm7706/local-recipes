"""Story 16.5 — fleet project-item inventory from github.com Projects.

Fixture organisation only.

No test reaches GitHub or runs ``gh``: the real GraphQL client runs against a stub
transport (``github_wire``: ``http.client``'s ``connect`` is patched by dotted name, as
Story 16.1's tests do, because this tree adds no raw-HTTP import), and the root
conftest's autouse ``real_gh_attempts`` guard fails any test that reaches the real
``gh`` runner. The platform host reaches no pyforge package, so the query-only guard
itself is driven in pyforge-warden's own unit tests; here the real task, client and
urllib run end to end. Every identifier is fictional: ``example-org``, invented
project numbers, titles and repositories.
"""

from __future__ import annotations

import ast
import io
import json
import logging
import os
import subprocess
import traceback
from dataclasses import dataclass
from dataclasses import field
from http import HTTPStatus
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.test.utils import override_settings
from django_pyforge.flags import evaluate_from_source
from django_pyforge.roles import IDP_TOKEN_CLAIMS_SESSION_KEY
from django_warden_fabric.fleet import FLEET_PROJECT_ITEMS_FLAG
from django_warden_fabric.fleet_inventory import ENV_FLEET_INVENTORY_PATH
from django_warden_fabric.fleet_inventory import ENV_FLEET_TARGET_CONFIG
from django_warden_fabric.fleet_inventory import FLEET_INVENTORY_REQUEST_TIMEOUT_SECONDS
from django_warden_fabric.fleet_inventory import FLEET_INVENTORY_SOFT_TIME_LIMIT_SECONDS
from django_warden_fabric.fleet_inventory import FLEET_INVENTORY_TIME_LIMIT_SECONDS
from django_warden_fabric.fleet_inventory import FleetTargetConfigError
from django_warden_fabric.fleet_inventory import GhBinaryMissingError
from django_warden_fabric.fleet_inventory import GhLoginMissingError
from django_warden_fabric.fleet_inventory import fleet_checkout_root
from django_warden_fabric.fleet_project_items import DEFAULT_FLEET_PROJECT_ITEMS_PATH
from django_warden_fabric.fleet_project_items import ENV_FLEET_PROJECT_ITEMS_PATH
from django_warden_fabric.fleet_project_items import export_document
from django_warden_fabric.fleet_project_items import load_project_numbers_from_config
from django_warden_fabric.fleet_project_items import (
    resolve_fleet_project_items_export_path,
)
from django_warden_fabric.fleet_project_items import run_fleet_project_items_sync
from django_warden_fabric.tasks import run_fleet_project_items
from django_warden_fabric.views import FLEET_PROJECT_ITEMS_CONFIG_REFUSAL

_EXAMPLE_ORG = "example-org"
_PROJECT_A = 11  # invented project numbers
_PROJECT_B = 22
_EXIT_REFUSED = 2
_SENTINEL = "sentinel-token-must-not-leak-16-5"
_GH = "/opt/example/bin/gh"
_SRC_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _SRC_ROOT.parent
_PLATFORM_DIR = Path(__file__).resolve().parents[1]
_FLAGS_JSON = _PLATFORM_DIR / "config" / "flags.json"
_OVERLAYS_JSON = _PLATFORM_DIR / "config" / "flag-overlays.json"
_FABRIC_ROOT = (
    _SRC_ROOT / "shared" / "packages" / "django-warden" / "src" / "django_warden_fabric"
)
_TASKS_PATH = _FABRIC_ROOT / "tasks.py"
_PORTAL_START = "/stations/warden/fleet/project-items/start/"
_GRAPHQL = "https://api.github.com/graphql"


# --- a fake GitHub at the socket: the real client, urllib and http.client all run ---


@dataclass(frozen=True)
class _Exchange:
    method: str
    url: str
    authorization: str | None
    timeout: float | None
    body: dict[str, Any]


def _http_response(status: int, *, body: bytes = b"") -> bytes:
    phrase = HTTPStatus(status).phrase
    head = f"HTTP/1.1 {status} {phrase}\r\nContent-Length: {len(body)}\r\n\r\n"
    return head.encode("latin-1") + body


def _json_reply(payload: object, status: int = HTTPStatus.OK) -> bytes:
    return _http_response(status, body=json.dumps(payload).encode())


@dataclass
class _GitHubWire:
    """Answers each ``POST /graphql`` by its ``number`` and ``after`` variables."""

    replies: dict[tuple[int, str | None], bytes] = field(default_factory=dict)
    exchanges: list[_Exchange] = field(default_factory=list)

    def serve(self, number: int, pages: list[list[dict[str, Any]]]) -> None:
        """``pages[n]`` answers the cursor ``cursor-n`` (page 0 answers no cursor)."""
        for index, nodes in enumerate(pages):
            cursor = f"cursor-{index}" if index else None
            following = f"cursor-{index + 1}" if index + 1 < len(pages) else None
            self.replies[(number, cursor)] = _json_reply(
                _page(nodes, next_cursor=following)
            )

    def answer(self, body: dict[str, Any]) -> bytes:
        variables = body["variables"]
        fallback = _http_response(HTTPStatus.NOT_FOUND, body=b"{}")
        return self.replies.get((variables["number"], variables["after"]), fallback)

    def connect(self, connection: Any) -> None:
        connection.sock = _WireSocket(self, connection)


class _WireSocket:
    def __init__(self, wire: _GitHubWire, connection: Any) -> None:
        self._wire = wire
        self._origin = f"https://{connection.host}"
        self._timeout = connection.timeout
        self._sent = bytearray()

    def sendall(self, data: bytes, *args: object) -> None:
        self._sent += bytes(data)

    def makefile(self, mode: str, *args: object, **kwargs: object) -> io.BytesIO:
        head, _, raw = bytes(self._sent).partition(b"\r\n\r\n")
        lines = head.decode("latin-1").split("\r\n")
        method, target, _version = lines[0].split(" ", 2)
        headers = {
            n.strip().lower(): v.strip()
            for n, _, v in (line.partition(":") for line in lines[1:])
        }
        body = json.loads(raw.decode("utf-8")) if raw else {}
        self._wire.exchanges.append(
            _Exchange(
                method=method,
                url=f"{self._origin}{target}",
                authorization=headers.get("authorization"),
                timeout=self._timeout,
                body=body,
            )
        )
        return io.BytesIO(self._wire.answer(body))

    def close(self) -> None:
        pass


@pytest.fixture
def github_wire(monkeypatch: pytest.MonkeyPatch) -> _GitHubWire:
    wire = _GitHubWire()

    def _connect(connection: Any) -> None:
        wire.connect(connection)

    monkeypatch.setattr("http.client.HTTPSConnection.connect", _connect)
    monkeypatch.setattr("http.client.HTTPConnection.connect", _connect)
    return wire


# --- fixture project data ---


def _issue(
    item_id: str, *, state: str = "OPEN", status: str | None = "Todo"
) -> dict[str, Any]:
    return {
        "id": item_id,
        "type": "ISSUE",
        "updatedAt": "2026-10-01T10:00:00Z",
        "fieldValueByName": {"name": status} if status else None,
        "content": {
            "title": f"Issue {item_id}",
            "state": state,
            "repository": {"nameWithOwner": f"{_EXAMPLE_ORG}/alpha"},
        },
    }


def _pull_request(item_id: str) -> dict[str, Any]:
    return {
        "id": item_id,
        "type": "PULL_REQUEST",
        "updatedAt": "2026-10-02T10:00:00Z",
        "fieldValueByName": {"name": "In review"},
        "content": {
            "title": f"PR {item_id}",
            "state": "MERGED",
            "repository": {"nameWithOwner": f"{_EXAMPLE_ORG}/beta"},
        },
    }


def _draft(item_id: str) -> dict[str, Any]:
    return {
        "id": item_id,
        "type": "DRAFT_ISSUE",
        "updatedAt": "2026-10-03T10:00:00Z",
        "fieldValueByName": {"name": "Backlog"},
        "content": {"title": f"Draft {item_id}"},
    }


def _redacted(item_id: str) -> dict[str, Any]:
    return {
        "id": item_id,
        "type": "REDACTED",
        "updatedAt": "2026-10-04T10:00:00Z",
        "fieldValueByName": None,
        "content": None,
    }


def _page(nodes: list[dict[str, Any]], *, next_cursor: str | None) -> dict[str, Any]:
    page_info = {"hasNextPage": next_cursor is not None, "endCursor": next_cursor}
    return {
        "data": {
            "organization": {
                "projectV2": {"items": {"pageInfo": page_info, "nodes": nodes}}
            }
        }
    }


class _SentinelProvider:
    def token(self) -> str:
        return _SENTINEL


def _write_config(path: Path, body: str) -> None:
    path.write_text(
        f'[github]\norganisation = "{_EXAMPLE_ORG}"\n{body}', encoding="utf-8"
    )


@pytest.fixture
def project_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    config = tmp_path / "fleet-target.toml"
    export = tmp_path / "fleet-project-items.json"
    _write_config(config, f"projects = [{_PROJECT_A}, {_PROJECT_B}]\n")
    monkeypatch.setenv(ENV_FLEET_TARGET_CONFIG, str(config))
    monkeypatch.setenv(ENV_FLEET_PROJECT_ITEMS_PATH, str(export))
    return config, export


def _run_task() -> str:
    with patch("django_warden_fabric.tasks.GhAuthTokenProvider", _SentinelProvider):
        return run_fleet_project_items("run-id", _EXAMPLE_ORG)


def _fail_text(caught: pytest.ExceptionInfo[BaseException]) -> str:
    rendered = "".join(
        traceback.TracebackException.from_exception(
            caught.value, capture_locals=True
        ).format()
    )
    return f"{caught.value!s} {caught.value!r} {rendered}"


# --- AC1: two projects, every item type, each item once ---


def test_export_lists_each_item_once(
    project_paths: tuple[Path, Path], github_wire: _GitHubWire
) -> None:
    _config, export = project_paths
    github_wire.serve(
        _PROJECT_A, [[_issue("i-1"), _pull_request("p-1"), _issue("i-1")]]
    )
    github_wire.serve(
        _PROJECT_B,
        [[_draft("d-1"), _redacted("r-1"), _issue("i-2", state="CLOSED", status=None)]],
    )
    assert _run_task() == "run-id"
    payload = json.loads(export.read_text(encoding="utf-8"))
    assert list(payload) == ["items"]
    by_key = {(e["project_number"], e["id"]): e for e in payload["items"]}
    assert len(payload["items"]) == len(by_key) == 5  # noqa: PLR2004 -- each item once
    assert by_key[(_PROJECT_A, "i-1")] == {
        "project_number": _PROJECT_A,
        "id": "i-1",
        "content_type": "ISSUE",
        "title": "Issue i-1",
        "state": "OPEN",
        "repository": f"{_EXAMPLE_ORG}/alpha",
        "status": "Todo",
        "updated_at": "2026-10-01T10:00:00Z",
    }
    pull_request = by_key[(_PROJECT_A, "p-1")]
    assert (
        pull_request["content_type"],
        pull_request["state"],
        pull_request["status"],
    ) == ("PULL_REQUEST", "MERGED", "In review")
    draft = by_key[(_PROJECT_B, "d-1")]
    assert (
        draft["content_type"],
        draft["title"],
        draft["state"],
        draft["repository"],
        draft["status"],
    ) == (
        "DRAFT_ISSUE",
        "Draft d-1",
        None,
        None,
        "Backlog",
    )
    assert by_key[(_PROJECT_B, "r-1")] == {
        "project_number": _PROJECT_B,
        "id": "r-1",
        "content_type": "REDACTED",
        "title": None,
        "state": None,
        "repository": None,
        "status": None,
        "updated_at": None,
    }
    assert by_key[(_PROJECT_B, "i-2")]["status"] is None


def test_export_document_lists_a_repeated_item_once() -> None:
    @dataclass(frozen=True)
    class _Item:
        project_number: int
        id: str
        content_type: str = "DRAFT_ISSUE"
        title: str | None = "t"
        state: str | None = None
        repository: str | None = None
        status: str | None = None
        updated_at: str | None = None

    document = export_document([_Item(1, "a"), _Item(1, "a"), _Item(2, "a")])
    assert [(e["project_number"], e["id"]) for e in document["items"]] == [
        (1, "a"),
        (2, "a"),
    ]


# --- AC2: pagination ---


def test_every_page_is_read(
    project_paths: tuple[Path, Path], github_wire: _GitHubWire
) -> None:
    _config, export = project_paths
    github_wire.serve(
        _PROJECT_A, [[_issue("i-1")], [_pull_request("p-1")], [_draft("d-1")]]
    )
    github_wire.serve(_PROJECT_B, [[_issue("i-2")]])
    _run_task()
    afters = [
        (e.body["variables"]["number"], e.body["variables"]["after"])
        for e in github_wire.exchanges
    ]
    assert afters == [
        (_PROJECT_A, None),
        (_PROJECT_A, "cursor-1"),
        (_PROJECT_A, "cursor-2"),
        (_PROJECT_B, None),
    ]
    ids = [e["id"] for e in json.loads(export.read_text(encoding="utf-8"))["items"]]
    assert ids == ["i-1", "p-1", "d-1", "i-2"]


# --- AC3: re-run rewrites whole ---


def test_rerun_rewrites_the_export_whole(
    project_paths: tuple[Path, Path], github_wire: _GitHubWire
) -> None:
    config, export = project_paths
    _write_config(
        config, f"projects = [{_PROJECT_A}, {_PROJECT_A}]\n"
    )  # the same project listed twice
    github_wire.serve(_PROJECT_A, [[_issue("i-1"), _issue("i-2")]])
    _run_task()
    first = json.loads(export.read_text(encoding="utf-8"))
    assert [e["id"] for e in first["items"]] == ["i-1", "i-2"]
    assert len(github_wire.exchanges) == 1  # the repeated entry is read once
    _run_task()
    assert json.loads(export.read_text(encoding="utf-8")) == first
    github_wire.serve(_PROJECT_A, [[_issue("i-3")]])
    _run_task()
    assert [
        e["id"] for e in json.loads(export.read_text(encoding="utf-8"))["items"]
    ] == ["i-3"]


# --- AC4: POST /graphql, one query, nothing edited ---


def test_every_request_is_a_post_to_graphql_with_one_query(
    project_paths: tuple[Path, Path],
    github_wire: _GitHubWire,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    github_wire.serve(_PROJECT_A, [[_issue("i-1")], [_draft("d-1")]])
    github_wire.serve(_PROJECT_B, [[_issue("i-2")]])
    _run_task()
    assert len(github_wire.exchanges) == 3  # noqa: PLR2004
    for exchange in github_wire.exchanges:
        assert (exchange.method, exchange.url) == ("POST", _GRAPHQL)
        assert exchange.authorization == f"Bearer {_SENTINEL}"
        assert exchange.timeout == FLEET_INVENTORY_REQUEST_TIMEOUT_SECONDS
        assert set(exchange.body) == {"query", "variables"}
        query = exchange.body["query"]
        assert query.lstrip().startswith("query ")
        assert "mutation" not in query.lower()
        assert "subscription" not in query.lower()
        assert exchange.body["variables"]["login"] == _EXAMPLE_ORG


# --- AC5: typed errors, no partial export ---


@pytest.mark.parametrize(
    "case",
    [
        (
            "errors",
            _json_reply(
                {
                    "errors": [{"type": "NOT_FOUND", "message": "secret-detail"}],
                    "data": None,
                }
            ),
        ),
        ("project-null", _json_reply({"data": {"organization": {"projectV2": None}}})),
        ("http-503", _http_response(HTTPStatus.SERVICE_UNAVAILABLE, body=b"{}")),
        ("rate-limit", _http_response(HTTPStatus.TOO_MANY_REQUESTS, body=b"{}")),
        ("forbidden", _http_response(HTTPStatus.FORBIDDEN, body=b"{}")),
    ],
    ids=lambda case: case[0],
)
def test_a_failing_entry_is_typed_and_leaves_no_export(
    project_paths: tuple[Path, Path],
    github_wire: _GitHubWire,
    caplog: pytest.LogCaptureFixture,
    case: tuple[str, bytes],
) -> None:
    _fault, reply = case
    _config, export = project_paths
    caplog.set_level(logging.DEBUG)
    github_wire.serve(_PROJECT_A, [[_issue("i-1")]])
    github_wire.replies[(_PROJECT_B, None)] = reply
    with pytest.raises(Exception, match="config key projects, entry 2 of 2") as caught:
        _run_task()
    assert type(caught.value).__name__ == "ProjectEntryError"
    assert not export.exists()
    assert list(export.parent.glob(".fleet-project-items.json.*")) == []
    for secret in (_SENTINEL, "secret-detail", str(_PROJECT_B)):
        assert secret not in _fail_text(caught)
        assert secret not in caplog.text


def test_task_missing_gh_binary_leaves_no_export(
    project_paths: tuple[Path, Path],
) -> None:
    _config, export = project_paths
    with (
        patch("django_warden_fabric.fleet_inventory.shutil.which", return_value=None),
        pytest.raises(GhBinaryMissingError),
    ):
        run_fleet_project_items("run-id", _EXAMPLE_ORG)
    assert not export.exists()


def test_task_without_a_gh_login_leaves_no_export(
    project_paths: tuple[Path, Path],
) -> None:
    _config, export = project_paths

    def _no_login(
        argv: list[str], *, timeout: float
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="not logged in")

    with (
        patch("django_warden_fabric.fleet_inventory.shutil.which", return_value=_GH),
        patch("django_warden_fabric.fleet_inventory._run_gh", _no_login),
        pytest.raises(GhLoginMissingError, match=r"github\.com login"),
    ):
        run_fleet_project_items("run-id", _EXAMPLE_ORG)
    assert not export.exists()


@pytest.mark.parametrize(
    ("body", "detail"),
    [
        ("", "projects"),
        ("projects = []\n", "projects"),
        ('projects = "11"\n', "projects"),
        ('projects = [11, "22"]\n', "entry 2"),
        ("projects = [11, true]\n", "entry 2"),
        ("projects = [0]\n", "entry 1"),
        ("projects = [-3]\n", "entry 1"),
        ("projects = [1.5]\n", "entry 1"),
    ],
)
def test_a_config_without_usable_projects_is_a_typed_error(
    project_paths: tuple[Path, Path], body: str, detail: str
) -> None:
    config, export = project_paths
    _write_config(config, body)
    with pytest.raises(FleetTargetConfigError, match=detail) as caught:
        load_project_numbers_from_config()
    assert str(config) in str(caught.value)
    with pytest.raises(FleetTargetConfigError, match=detail):
        run_fleet_project_items("run-id", _EXAMPLE_ORG)
    assert not export.exists()


def test_missing_config_names_the_path_and_the_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "absent.toml"
    monkeypatch.setenv(ENV_FLEET_TARGET_CONFIG, str(missing))
    with pytest.raises(FleetTargetConfigError, match="projects") as caught:
        load_project_numbers_from_config()
    assert str(missing) in str(caught.value)


def test_config_without_a_github_table_or_with_bad_toml(tmp_path: Path) -> None:
    config = tmp_path / "fleet-target.toml"
    config.write_text("[other]\nprojects = [1]\n", encoding="utf-8")
    with pytest.raises(FleetTargetConfigError, match=r"\[github\]"):
        load_project_numbers_from_config(config)
    config.write_text("projects = [", encoding="utf-8")
    with pytest.raises(FleetTargetConfigError, match="invalid TOML"):
        load_project_numbers_from_config(config)


def test_projects_load_in_config_order(project_paths: tuple[Path, Path]) -> None:
    assert load_project_numbers_from_config() == [_PROJECT_A, _PROJECT_B]


# --- AC6: the token is nowhere ---


def test_the_token_is_in_no_log_message_or_export_on_success(
    project_paths: tuple[Path, Path],
    github_wire: _GitHubWire,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _config, export = project_paths
    caplog.set_level(logging.DEBUG)
    github_wire.serve(_PROJECT_A, [[_issue("i-1")]])
    github_wire.serve(_PROJECT_B, [[_draft("d-1")]])
    _run_task()
    assert _SENTINEL not in caplog.text
    assert _SENTINEL not in export.read_text(encoding="utf-8")
    assert {e.authorization for e in github_wire.exchanges} == {f"Bearer {_SENTINEL}"}


# --- AC7: keys-not-blobs ---


def test_celery_message_keys_not_blobs() -> None:
    tree = ast.parse(_TASKS_PATH.read_text(encoding="utf-8"))
    fn = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "run_fleet_project_items"
    )
    assert [a.arg for a in fn.args.args] == [
        "self",
        "project_items_run_id",
        "organisation",
    ]
    signature = run_fleet_project_items.s(
        "00000000-0000-0000-0000-000000000001", _EXAMPLE_ORG
    )
    serialized = json.dumps(signature.args).lower()
    assert "token" not in serialized
    assert "authorization" not in serialized
    assert "bearer" not in serialized


def test_task_limits_bound_full_pagination(settings) -> None:
    assert (
        run_fleet_project_items.soft_time_limit
        == FLEET_INVENTORY_SOFT_TIME_LIMIT_SECONDS
    )
    assert run_fleet_project_items.time_limit == FLEET_INVENTORY_TIME_LIMIT_SECONDS
    assert (
        FLEET_INVENTORY_REQUEST_TIMEOUT_SECONDS
        < FLEET_INVENTORY_SOFT_TIME_LIMIT_SECONDS
        < FLEET_INVENTORY_TIME_LIMIT_SECONDS
        <= settings.CELERY_TASK_TIME_LIMIT
    )


# --- AC8: the default export path is gitignored and anchored to the checkout ---


def _git_env() -> dict[str, str]:
    """The environment minus ``GIT_*`` (a git hook exports GIT_DIR / GIT_INDEX_FILE)."""
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def test_gitignore_pins_the_default_export_path() -> None:
    assert Path(".warden/fleet-project-items.json") == DEFAULT_FLEET_PROJECT_ITEMS_PATH
    for path in (
        DEFAULT_FLEET_PROJECT_ITEMS_PATH,
        Path(".warden/.fleet-project-items.json.example.tmp"),
    ):
        result = subprocess.run(  # noqa: S603
            ["git", "check-ignore", "-q", str(path)],  # noqa: S607
            cwd=_REPO_ROOT,
            env=_git_env(),
            check=False,
        )
        assert result.returncode == 0, path


def test_default_export_path_anchors_to_the_checkout_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(ENV_FLEET_PROJECT_ITEMS_PATH, raising=False)
    monkeypatch.chdir(tmp_path)
    assert (
        resolve_fleet_project_items_export_path()
        == fleet_checkout_root() / DEFAULT_FLEET_PROJECT_ITEMS_PATH
    )


def test_the_export_path_env_overrides_the_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    override = tmp_path / "elsewhere.json"
    monkeypatch.setenv(ENV_FLEET_PROJECT_ITEMS_PATH, str(override))
    assert resolve_fleet_project_items_export_path() == override


def test_the_export_is_its_own_file_not_the_repo_inventory(
    project_paths: tuple[Path, Path], monkeypatch
) -> None:
    """Story 16.1's export path does not move this one (and the other way round)."""
    _config, export = project_paths
    monkeypatch.setenv(
        ENV_FLEET_INVENTORY_PATH, str(export.parent / "fleet-inventory.json")
    )
    assert resolve_fleet_project_items_export_path() == export


def test_a_failed_write_leaves_no_partial_export(
    project_paths: tuple[Path, Path],
) -> None:
    _config, export = project_paths

    @dataclass(frozen=True)
    class _Client:
        def list_projects_items(
            self, organisation: str, project_numbers: list[int]
        ) -> list[object]:
            msg = "listing failed"
            raise RuntimeError(msg)

    with pytest.raises(RuntimeError, match="listing failed"):
        run_fleet_project_items_sync(
            organisation=_EXAMPLE_ORG,
            project_numbers=[_PROJECT_A],
            listing_client=_Client(),
            export_path=export,
        )
    assert not export.exists()


# --- AC10: the flag ---


def _flag_tree(*, on: bool) -> dict:
    tree = json.loads(_FLAGS_JSON.read_text(encoding="utf-8"))
    tree["flags"][FLEET_PROJECT_ITEMS_FLAG]["defaultVariant"] = "on" if on else "off"
    return tree


@pytest.fixture
def flags_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    tree = tmp_path / "flags-on.json"
    tree.write_text(json.dumps(_flag_tree(on=True)), encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    assert evaluate_from_source(key=FLEET_PROJECT_ITEMS_FLAG, source=tree) is True
    return tree


@pytest.fixture
def flags_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    tree = tmp_path / "flags-off.json"
    tree.write_text(json.dumps(_flag_tree(on=False)), encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    assert evaluate_from_source(key=FLEET_PROJECT_ITEMS_FLAG, source=tree) is False
    return tree


def test_the_flag_ships_off_by_default_and_on_in_dev_and_staging() -> None:
    entry = json.loads(_FLAGS_JSON.read_text(encoding="utf-8"))["flags"][
        FLEET_PROJECT_ITEMS_FLAG
    ]
    assert entry["defaultVariant"] == "off"
    assert entry["metadata"]["owner"] == "warden"
    assert entry["metadata"]["story"].startswith("16-5-")
    overlays = json.loads(_OVERLAYS_JSON.read_text(encoding="utf-8"))
    assert {env: overlays[env][FLEET_PROJECT_ITEMS_FLAG] for env in overlays} == {
        "dev": "on",
        "staging": "on",
        "production": "off",
    }


@pytest.mark.django_db
def test_flag_off_refuses_exit_2(
    flags_off: Path, project_paths: tuple[Path, Path]
) -> None:
    stderr = StringIO()
    with pytest.raises(SystemExit) as exc:
        call_command("warden_fleet_project_items", stderr=stderr)
    assert exc.value.code == _EXIT_REFUSED
    assert FLEET_PROJECT_ITEMS_FLAG in stderr.getvalue()
    assert not project_paths[1].exists()


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_flag_on_runs_the_inventory(
    flags_on: Path, project_paths: tuple[Path, Path], github_wire: _GitHubWire
) -> None:
    _config, export = project_paths
    github_wire.serve(_PROJECT_A, [[_issue("i-1")]])
    github_wire.serve(_PROJECT_B, [[_draft("d-1")]])
    stdout = StringIO()
    with patch("django_warden_fabric.tasks.GhAuthTokenProvider", _SentinelProvider):
        call_command("warden_fleet_project_items", stdout=stdout)
    assert stdout.getvalue().strip()
    assert [
        e["id"] for e in json.loads(export.read_text(encoding="utf-8"))["items"]
    ] == ["i-1", "d-1"]


@pytest.mark.django_db
def test_flag_on_with_a_bad_config_exits_1(
    flags_on: Path, project_paths: tuple[Path, Path]
) -> None:
    config, export = project_paths
    _write_config(config, "")
    stderr = StringIO()
    with pytest.raises(SystemExit) as exc:
        call_command("warden_fleet_project_items", stderr=stderr)
    assert exc.value.code == 1
    assert "projects" in stderr.getvalue()
    assert not export.exists()


def _authed(client, settings, *, sub: str = "op-1"):
    claims: dict[str, object] = {"sub": sub, "groups": ["pyforge:station:warden"]}
    settings.IDP_CLAIMS_SNAPSHOT = claims
    session = client.session
    session[IDP_TOKEN_CLAIMS_SESSION_KEY] = claims
    session.save()
    return client


@pytest.mark.django_db
def test_portal_refuses_when_flag_off(client, settings, flags_off: Path) -> None:
    _authed(client, settings)
    response = client.post(_PORTAL_START)
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert b"disabled" in response.content.lower()


@pytest.mark.django_db
def test_portal_chrome_lists_the_action_disabled_when_flag_off(
    client, settings, flags_off: Path
) -> None:
    _authed(client, settings)
    home = client.get("/stations/warden/")
    assert home.status_code == HTTPStatus.OK
    body = home.content.decode()
    assert "warden-fleet-project-items-start" in body
    assert "Fleet project items are disabled (flag off)" in body


@pytest.mark.django_db
def test_portal_chrome_enables_the_action_when_flag_on(
    client, settings, flags_on: Path
) -> None:
    _authed(client, settings)
    body = client.get("/stations/warden/").content.decode()
    assert "warden-fleet-project-items-start" in body
    assert "Fleet project items are disabled" not in body


@pytest.mark.django_db
@pytest.mark.usefixtures("flags_on")
def test_portal_config_refusal_names_no_path(
    client,
    settings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    missing = tmp_path / "absent" / "fleet-target.toml"
    monkeypatch.setenv(ENV_FLEET_TARGET_CONFIG, str(missing))
    _authed(client, settings)
    caplog.set_level(logging.WARNING)
    response = client.post(_PORTAL_START)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.content.decode() == FLEET_PROJECT_ITEMS_CONFIG_REFUSAL
    assert str(missing) not in response.content.decode()
    assert str(missing) in caplog.text


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_portal_runs_the_inventory_when_flag_on(
    client,
    settings,
    flags_on: Path,
    project_paths: tuple[Path, Path],
    github_wire: _GitHubWire,
) -> None:
    _config, export = project_paths
    github_wire.serve(_PROJECT_A, [[_issue("i-1")]])
    github_wire.serve(_PROJECT_B, [[_redacted("r-1")]])
    _authed(client, settings)
    with patch("django_warden_fabric.tasks.GhAuthTokenProvider", _SentinelProvider):
        response = client.post(_PORTAL_START)
    assert response.status_code == HTTPStatus.OK
    assert b"warden-fleet-project-items-started" in response.content
    assert [
        e["id"] for e in json.loads(export.read_text(encoding="utf-8"))["items"]
    ] == ["i-1", "r-1"]
