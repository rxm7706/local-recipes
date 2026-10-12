"""Story 16.1 — fleet inventory from github.com (fixture organisation only).

No test reaches GitHub or runs ``gh``: the real listing client runs against a
stub urllib transport (``github_wire``), and the root conftest's autouse
``real_gh_attempts`` guard fails any test that reaches the real ``gh`` runner.
"""

from __future__ import annotations

import ast
import contextlib
import io
import json
import logging
import os
import re
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from dataclasses import field
from http import HTTPStatus
from io import StringIO
from pathlib import Path
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from typing import Any
from unittest.mock import patch

import pytest
import structlog
from celery.exceptions import SoftTimeLimitExceeded
from celery.signals import after_task_publish
from celery.signals import before_task_publish
from celery.signals import task_failure
from celery.signals import task_prerun
from celery.signals import task_rejected
from celery.signals import task_retry
from celery.signals import task_revoked
from celery.signals import task_success
from celery.signals import task_unknown
from django.core.management import call_command
from django.test import Client
from django.test.utils import override_settings
from django_pyforge.flags import evaluate_from_source
from django_pyforge.roles import IDP_TOKEN_CLAIMS_SESSION_KEY
from django_structlog.celery.receivers import CeleryReceiver
from django_warden_fabric.fleet import FLEET_INVENTORY_FLAG
from django_warden_fabric.fleet_inventory import DEFAULT_FLEET_INVENTORY_PATH
from django_warden_fabric.fleet_inventory import DEFAULT_FLEET_TARGET_CONFIG
from django_warden_fabric.fleet_inventory import ENV_FLEET_INVENTORY_PATH
from django_warden_fabric.fleet_inventory import ENV_FLEET_TARGET_CONFIG
from django_warden_fabric.fleet_inventory import FLEET_INVENTORY_REQUEST_TIMEOUT_SECONDS
from django_warden_fabric.fleet_inventory import FLEET_INVENTORY_SOFT_TIME_LIMIT_SECONDS
from django_warden_fabric.fleet_inventory import FLEET_INVENTORY_TIME_LIMIT_SECONDS
from django_warden_fabric.fleet_inventory import GH_AUTH_TOKEN_TIMEOUT_SECONDS
from django_warden_fabric.fleet_inventory import FleetTargetConfigError
from django_warden_fabric.fleet_inventory import GhAuthTokenProvider
from django_warden_fabric.fleet_inventory import GhBinaryMissingError
from django_warden_fabric.fleet_inventory import GhLoginMissingError
from django_warden_fabric.fleet_inventory import GhTimeoutError
from django_warden_fabric.fleet_inventory import GhTokenUnavailableError
from django_warden_fabric.fleet_inventory import _run_gh as real_run_gh
from django_warden_fabric.fleet_inventory import atomic_write_json
from django_warden_fabric.fleet_inventory import fleet_checkout_root
from django_warden_fabric.fleet_inventory import load_leak_guard_terms
from django_warden_fabric.fleet_inventory import load_organisation_from_config
from django_warden_fabric.fleet_inventory import resolve_fleet_inventory_export_path
from django_warden_fabric.fleet_inventory import resolve_fleet_target_config_path
from django_warden_fabric.fleet_inventory import run_fleet_inventory_sync
from django_warden_fabric.models import FleetRepo
from django_warden_fabric.tasks import run_fleet_inventory
from django_warden_fabric.views import FLEET_INVENTORY_CONFIG_REFUSAL

from config.observability.logging import JSON
from config.observability.logging import build_logging_config
from config.observability.logging import configure_structlog
from tests.gh_guard import refuse_real_gh

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterator
    from collections.abc import Sequence
    from types import FrameType

_EXAMPLE_ORG = "example-org"
_FIXTURE_REPO_COUNT = 3
_EXIT_REFUSED = 2
_SENTINEL = "sentinel-token-must-not-leak-16-1"
_GH = "/opt/example/bin/gh"
_TWO_WRITES = 2
_HTTPS_PORT = 443
_SLEEPER_SECONDS = 5
_SRC_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _SRC_ROOT.parent
_PLATFORM_DIR = Path(__file__).resolve().parents[1]
_FLAGS_JSON = _PLATFORM_DIR / "config" / "flags.json"
_PACKAGES = _SRC_ROOT / "shared" / "packages"
_FABRIC_ROOT = _PACKAGES / "django-warden" / "src" / "django_warden_fabric"
_TASKS_PATH = _FABRIC_ROOT / "tasks.py"
_PROJECTS = _REPO_ROOT / "_bmad-output" / "projects"
_SPECS = "planning-artifacts/specs"
# Story 18.1: the warden-owned set, declared once (Rule O's whole-file unit). Each entry
# is a ``PurePosixPath.full_match`` pattern: ``/**`` names a directory, ``*`` matches
# within one path segment, and an entry with no wildcard names one file. The guard and
# ``test_leak_guard_scan_roots_exist`` both read this tuple. Listed terms (Rule T)
# apply everywhere in the scan set (all tracked files plus branch changed files).
_LEAK_WARDEN_OWNED = (
    "src/shared/packages/pyforge-warden/**",
    "src/shared/packages/django-warden/**",
    "_bmad-output/projects/pyforge-warden/**",
    ".claude/skills/pyforge-warden/**",
    ".claude/skills/bmad-agent-warden/**",
    "presentations/pyforge-warden/**",
    "docs/dreams/pyforge-warden.md",
    "src/platform/tests/test_warden_*.py",
)
_WARDEN_NAME = re.compile(r"(?<![a-z])warden(?![a-z])")
_TEAM_MEMORY_ENTRY = re.compile(r"^\.claude/memory/[^/]+/[^/]+\.md$")
_WARDEN_PROJECT_MEMLOG_PREFIX = "_bmad-output/projects/pyforge-warden/"
_STEWARD_SPEC_X_DIR = (
    "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-x"
)
_EMPTY_CHANGED: frozenset[str] = frozenset()
_API = "https://api.github.com"
_FIRST_PAGE = f"{_API}/orgs/{_EXAMPLE_ORG}/repos?type=all&per_page=100"
_SECOND_PAGE = f"{_FIRST_PAGE}&page=2"


# --- fixture listing (no pyforge import: the platform host never imports pyforge.*) ---


@dataclass(frozen=True)
class _FixtureRepo:
    full_name: str
    default_branch: str
    clone_url: str
    archived: bool


@dataclass(frozen=True)
class _FixtureSkipped:
    page: int
    position: int
    full_name: str | None
    reason: str


@dataclass(frozen=True)
class _FixtureListing:
    repos: tuple[_FixtureRepo, ...]
    skipped: tuple[_FixtureSkipped, ...]


@dataclass
class _FixtureListingClient:
    """Answers from memory and records which organisation it was asked for."""

    repos_by_org: dict[str, tuple[_FixtureRepo, ...]]
    skipped: tuple[_FixtureSkipped, ...] = ()
    organisations_asked: list[str] = field(default_factory=list)

    def list_org_repos(self, organisation: str) -> _FixtureListing:
        self.organisations_asked.append(organisation)
        return _FixtureListing(
            repos=self.repos_by_org.get(organisation, ()),
            skipped=self.skipped,
        )


def _fixture_repo(name: str, *, branch: str = "main", archived: bool = False):
    return _FixtureRepo(
        full_name=f"{_EXAMPLE_ORG}/{name}",
        default_branch=branch,
        clone_url=f"https://github.com/{_EXAMPLE_ORG}/{name}.git",
        archived=archived,
    )


def _fixture_repos() -> tuple[_FixtureRepo, ...]:
    return (
        _fixture_repo("alpha"),
        _fixture_repo("beta", branch="develop"),
        _fixture_repo("archived-one", archived=True),
    )


def _fixture_client() -> _FixtureListingClient:
    return _FixtureListingClient(repos_by_org={_EXAMPLE_ORG: _fixture_repos()})


# --- a fake GitHub at the socket: the real client, urllib and http.client all run ---


def _http_response(
    status: int, *, body: bytes = b"", headers: dict[str, str] | None = None
) -> bytes:
    lines = [f"HTTP/1.1 {status} {HTTPStatus(status).phrase}"]
    lines.extend(f"{key}: {value}" for key, value in (headers or {}).items())
    lines.append(f"Content-Length: {len(body)}")
    return ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1") + body


def _api_repo(name: str, *, branch: str = "main", archived: bool = False) -> dict:
    return {
        "full_name": f"{_EXAMPLE_ORG}/{name}",
        "default_branch": branch,
        "clone_url": f"https://github.com/{_EXAMPLE_ORG}/{name}.git",
        "archived": archived,
    }


def _page(repos: list[dict], *, next_url: str | None = None) -> bytes:
    headers = {"Content-Type": "application/json"}
    if next_url is not None:
        headers["Link"] = f'<{next_url}>; rel="next"'
    return _http_response(
        HTTPStatus.OK, body=json.dumps(repos).encode(), headers=headers
    )


class _ScriptedReader(io.BytesIO):
    """Serves ``head``, then raises ``then`` (or reports EOF) once it runs dry."""

    def __init__(
        self, head: bytes, then: BaseException | None, wire: _GitHubWire | None = None
    ) -> None:
        super().__init__(head)
        self._then = then
        self._wire = wire

    def _dry(self, data: bytes) -> bytes:
        if not data and self._then is not None:
            if self._wire is not None:
                self._wire.stack_leaks.extend(_stack_leaks("read"))
            raise self._then
        return data

    def readline(self, size: int | None = -1) -> bytes:
        return self._dry(super().readline(size))

    def read(self, size: int | None = -1) -> bytes:
        return self._dry(super().read(size))


def _holds_sentinel(value: object) -> bool:
    header_items = getattr(value, "header_items", None)
    if callable(header_items) and any(_SENTINEL in str(v) for _, v in header_items()):
        return True  # a urllib Request carrying the token as a header
    try:
        text = repr(value)
    except Exception:  # noqa: BLE001 -- an object whose repr fails shows nothing
        return False
    return _SENTINEL in text


def _stack_leaks(where: str) -> list[str]:
    """Locals holding the token in the library frames between the fake and this test."""
    frame: FrameType | None = sys._getframe(1)  # noqa: SLF001 -- the stack is under test
    while frame is not None and frame.f_code.co_filename == __file__:
        frame = frame.f_back
    leaks: list[str] = []
    while frame is not None and frame.f_code.co_filename != __file__:
        leaks.extend(
            f"{where}: {frame.f_code.co_qualname} local {name!r}"
            for name, value in frame.f_locals.items()
            if _holds_sentinel(value)
        )
        frame = frame.f_back
    return leaks


@dataclass(frozen=True)
class _Exchange:
    method: str
    url: str
    authorization: str | None
    timeout: float | None


@dataclass
class _GitHubWire:
    """Answers the real client by URL from what really reached the wire.

    ``connect`` on http.client's connections is replaced (by dotted name: this
    module adds no raw-HTTP import under src/platform) with one that hands the
    connection a scripted socket, so urllib, http.client and the client's own
    pinned connection and credential splice all run for real.
    """

    routes: dict[str, bytes | Callable[[], io.BytesIO]] = field(default_factory=dict)
    connect_error: BaseException | None = None
    send_error: BaseException | None = None
    send_error_call: int = 1
    exchanges: list[_Exchange] = field(default_factory=list)
    # Every connect, send and response read walks the live stack: no library frame
    # (urllib, http.client, the client) may hold the token, failure or not.
    stack_leaks: list[str] = field(default_factory=list)

    def serve_fixture_org(self) -> None:
        self.routes[_FIRST_PAGE] = _page(
            [_api_repo("alpha"), _api_repo("beta", branch="develop")],
            next_url=_SECOND_PAGE,
        )
        self.routes[_SECOND_PAGE] = _page([_api_repo("archived-one", archived=True)])

    def script(self, url: str, head: bytes, then: BaseException | None) -> None:
        self.routes[url] = lambda: _ScriptedReader(head, then, self)

    def connect(self, connection: Any) -> None:
        self.stack_leaks.extend(_stack_leaks("connect"))
        if self.connect_error is not None:
            raise self.connect_error
        connection.sock = _WireSocket(self, connection)


class _WireSocket:
    def __init__(self, wire: _GitHubWire, connection: Any) -> None:
        self._wire = wire
        scheme = "https" if connection.default_port == _HTTPS_PORT else "http"
        port = (
            "" if connection.port == connection.default_port else f":{connection.port}"
        )
        self._origin = f"{scheme}://{connection.host}{port}"
        self._timeout = connection.timeout
        self._sent = bytearray()
        self._calls = 0

    def sendall(self, data: bytes, *args: object) -> None:
        self._calls += 1
        self._wire.stack_leaks.extend(_stack_leaks("send"))
        error = self._wire.send_error
        if error is not None and self._calls == self._wire.send_error_call:
            raise error
        self._sent += bytes(data)

    def makefile(self, mode: str, *args: object, **kwargs: object) -> io.BytesIO:
        self._wire.stack_leaks.extend(_stack_leaks("getresponse"))
        head = bytes(self._sent).split(b"\r\n\r\n", 1)[0].decode("latin-1")
        lines = head.split("\r\n")
        method, target, _version = lines[0].split(" ", 2)
        auth = [
            value.strip()
            for name, _, value in (line.partition(":") for line in lines[1:])
            if name.strip().lower() == "authorization"
        ]
        url = f"{self._origin}{target}"
        self._wire.exchanges.append(
            _Exchange(
                method=method,
                url=url,
                authorization=auth[0] if auth else None,
                timeout=self._timeout,
            )
        )
        route = self._wire.routes.get(
            url, _http_response(HTTPStatus.NOT_FOUND, body=b"{}")
        )
        return io.BytesIO(route) if isinstance(route, bytes) else route()

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


class _SentinelProvider:
    def token(self) -> str:
        return _SENTINEL


@pytest.fixture
def inventory_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path]:
    config = tmp_path / "fleet-target.toml"
    export = tmp_path / "fleet-inventory.json"
    config.write_text(
        f'[github]\norganisation = "{_EXAMPLE_ORG}"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv(ENV_FLEET_TARGET_CONFIG, str(config))
    monkeypatch.setenv(ENV_FLEET_INVENTORY_PATH, str(export))
    return config, export


# --- AC1, AC2: rows and export ---


@pytest.mark.django_db
def test_inventory_three_repos(inventory_paths: tuple[Path, Path]) -> None:
    _config, export = inventory_paths
    client = _fixture_client()
    document = run_fleet_inventory_sync(
        organisation=_EXAMPLE_ORG,
        listing_client=client,
        export_path=export,
    )
    assert (
        FleetRepo.objects.filter(organisation=_EXAMPLE_ORG).count()
        == _FIXTURE_REPO_COUNT
    )
    assert len(document["repos"]) == _FIXTURE_REPO_COUNT
    payload = json.loads(export.read_text(encoding="utf-8"))
    assert payload == document
    for entry in payload["repos"]:
        assert {"full_name", "default_branch", "clone_url", "archived"} <= set(entry)
    archived = next(
        e for e in payload["repos"] if e["full_name"].endswith("/archived-one")
    )
    assert archived["archived"] is True
    assert payload["skipped"] == []
    assert client.organisations_asked == [_EXAMPLE_ORG]


@pytest.mark.django_db
def test_inventory_rerun_updates_not_duplicates(
    inventory_paths: tuple[Path, Path],
) -> None:
    _config, export = inventory_paths
    run_fleet_inventory_sync(
        organisation=_EXAMPLE_ORG,
        listing_client=_fixture_client(),
        export_path=export,
    )
    renamed_branch = (
        _fixture_repo("alpha"),
        _fixture_repo("beta", branch="trunk"),
        _fixture_repo("archived-one", archived=True),
    )
    second = _FixtureListingClient(repos_by_org={_EXAMPLE_ORG: renamed_branch})
    document = run_fleet_inventory_sync(
        organisation=_EXAMPLE_ORG,
        listing_client=second,
        export_path=export,
    )
    rows = FleetRepo.objects.filter(organisation=_EXAMPLE_ORG)
    assert rows.count() == _FIXTURE_REPO_COUNT
    assert rows.get(full_name=f"{_EXAMPLE_ORG}/beta").default_branch == "trunk"
    assert json.loads(export.read_text(encoding="utf-8")) == document


@pytest.mark.django_db
def test_incomplete_listing_entries_are_named_in_the_export(
    inventory_paths: tuple[Path, Path],
) -> None:
    _config, export = inventory_paths
    skipped = (
        _FixtureSkipped(
            page=1,
            position=4,
            full_name=f"{_EXAMPLE_ORG}/no-branch",
            reason="missing default_branch",
        ),
    )
    client = _FixtureListingClient(
        repos_by_org={_EXAMPLE_ORG: _fixture_repos()}, skipped=skipped
    )
    run_fleet_inventory_sync(
        organisation=_EXAMPLE_ORG, listing_client=client, export_path=export
    )
    payload = json.loads(export.read_text(encoding="utf-8"))
    assert payload["skipped"] == [
        {
            "page": 1,
            "position": 4,
            "full_name": f"{_EXAMPLE_ORG}/no-branch",
            "reason": "missing default_branch",
        },
    ]
    assert not FleetRepo.objects.filter(full_name=f"{_EXAMPLE_ORG}/no-branch").exists()


# --- AC4: keys-not-blobs ---


def test_celery_message_keys_not_blobs() -> None:
    tree = ast.parse(_TASKS_PATH.read_text(encoding="utf-8"))
    fn = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "run_fleet_inventory"
    )
    arg_names = [a.arg for a in fn.args.args]
    assert arg_names == ["self", "inventory_run_id", "organisation"]
    sig = run_fleet_inventory.s("00000000-0000-0000-0000-000000000001", _EXAMPLE_ORG)
    serialized = json.dumps(sig.args)
    assert "token" not in serialized.lower()
    assert "authorization" not in serialized.lower()


# --- AC5: typed errors for gh and the config (M5: the gh call is time-bounded) ---


def _fake_runner(
    result: subprocess.CompletedProcess[str] | BaseException,
    calls: list[tuple[list[str], float]],
):
    def _run(argv: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
        calls.append((list(argv), timeout))
        if isinstance(result, BaseException):
            raise result
        return result

    return _run


def test_missing_gh_binary(inventory_paths: tuple[Path, Path]) -> None:
    with (
        patch("django_warden_fabric.fleet_inventory.shutil.which", return_value=None),
        pytest.raises(GhBinaryMissingError, match="gh binary"),
    ):
        GhAuthTokenProvider().token()


def _library_frame_locals(exc: BaseException) -> str:
    """Each shown frame's locals outside this test module, as a renderer prints them."""
    parts: list[str] = []
    rendered: traceback.TracebackException | None = (
        traceback.TracebackException.from_exception(exc, capture_locals=True)
    )
    while rendered is not None:
        parts.extend(
            f"{frame.filename}:{frame.lineno} {frame.locals!r}"
            for frame in rendered.stack
            if frame.filename != __file__
        )
        rendered = rendered.__cause__ or (
            None if rendered.__suppress_context__ else rendered.__context__
        )
    return "\n".join(parts)


def test_missing_gh_login(inventory_paths: tuple[Path, Path]) -> None:
    calls: list[tuple[list[str], float]] = []
    # A failing gh's stdout is never trusted, kept as a local, or echoed.
    failed = subprocess.CompletedProcess(
        args=[], returncode=1, stdout=_SENTINEL, stderr=""
    )
    provider = GhAuthTokenProvider(runner=_fake_runner(failed, calls))
    with (
        patch("django_warden_fabric.fleet_inventory.shutil.which", return_value=_GH),
        pytest.raises(GhLoginMissingError, match=r"github\.com login") as caught,
    ):
        provider.token()
    assert _SENTINEL not in str(caught.value)
    provider_frames = _library_frame_locals(caught.value)
    assert "fleet_inventory.py" in provider_frames
    assert _SENTINEL not in provider_frames
    assert calls == [
        (
            [_GH, "auth", "token", "--hostname", "github.com"],
            GH_AUTH_TOKEN_TIMEOUT_SECONDS,
        ),
    ]


def test_gh_token_is_read_with_a_timeout() -> None:
    calls: list[tuple[list[str], float]] = []
    ok = subprocess.CompletedProcess(args=[], returncode=0, stdout=f"{_SENTINEL}\n")
    provider = GhAuthTokenProvider(runner=_fake_runner(ok, calls), timeout=7.5)
    with patch("django_warden_fabric.fleet_inventory.shutil.which", return_value=_GH):
        assert provider.token() == _SENTINEL
    assert calls == [([_GH, "auth", "token", "--hostname", "github.com"], 7.5)]


def test_gh_timeout_is_typed_and_drops_partial_output() -> None:
    calls: list[tuple[list[str], float]] = []
    expired = subprocess.TimeoutExpired(
        cmd=[_GH], timeout=7.5, output=_SENTINEL, stderr=_SENTINEL
    )
    provider = GhAuthTokenProvider(runner=_fake_runner(expired, calls), timeout=7.5)
    with (
        patch("django_warden_fabric.fleet_inventory.shutil.which", return_value=_GH),
        pytest.raises(GhTimeoutError, match=r"within 7\.5s") as caught,
    ):
        provider.token()
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True
    assert _SENTINEL not in str(caught.value)
    assert _SENTINEL not in repr(caught.value)
    # N4-1: the suppressed TimeoutExpired keeps no partial output.
    suppressed = caught.value.__context__
    assert isinstance(suppressed, subprocess.TimeoutExpired)
    assert suppressed.output is None
    assert suppressed.stdout is None
    assert suppressed.stderr is None


def _leaky_runner(error: BaseException) -> Any:
    """A runner that fails while a local holds stdout, as a failing communicate does."""

    def _run(argv: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
        partial_stdout = _SENTINEL  # noqa: F841 -- held by the frame when the run fails
        raise error

    return _run


def _runner_frame_locals(exc: BaseException) -> list[dict[str, object]]:
    found = []
    tb = exc.__traceback__
    while tb is not None:
        if tb.tb_frame.f_code.co_name == "_run":
            found.append(dict(tb.tb_frame.f_locals))
        tb = tb.tb_next
    return found


@pytest.mark.parametrize(
    "error",
    [SoftTimeLimitExceeded(), RuntimeError("runner failed")],
    ids=["soft-time-limit", "runtime-error"],
)
def test_gh_provider_types_any_runner_failure_and_clears_its_frames(
    error: Exception,
) -> None:
    """The provider types any failure ``from None`` and clears the failed frames."""
    provider = GhAuthTokenProvider(runner=_leaky_runner(error))
    with (
        patch("django_warden_fabric.fleet_inventory.shutil.which", return_value=_GH),
        pytest.raises(GhTokenUnavailableError, match=type(error).__name__) as caught,
    ):
        provider.token()
    assert caught.value.__context__ is None
    assert caught.value.__cause__ is None
    assert _runner_frame_locals(error) == [{}]
    assert _SENTINEL not in str(caught.value)


def _chain(exc: BaseException) -> list[BaseException]:
    """Every exception linked from ``exc``, suppressed context included."""
    found: list[BaseException] = []
    pending: list[BaseException] = [exc]
    while pending:
        current = pending.pop()
        if any(current is seen for seen in found):
            continue
        found.append(current)
        pending.extend(e for e in (current.__cause__, current.__context__) if e)
    return found


def test_gh_output_that_will_not_decode_leaves_no_trace(tmp_path: Path) -> None:
    """N4-3: the real runner fails to decode gh's stdout; nothing in the chain keeps it.

    A ``UnicodeDecodeError`` holds the raw bytes it could not decode, so the typed
    error is raised outside the handler and has no ``__context__`` at all.
    """
    gh = tmp_path / "gh"
    gh.write_text(f"#!/bin/sh\nexec printf '{_SENTINEL}\\377\\n'\n", encoding="utf-8")
    gh.chmod(0o755)
    provider = GhAuthTokenProvider(runner=real_run_gh, timeout=5)
    with (
        patch(
            "django_warden_fabric.fleet_inventory.shutil.which", return_value=str(gh)
        ),
        pytest.raises(GhTokenUnavailableError, match="UnicodeDecodeError") as caught,
    ):
        provider.token()
    assert caught.value.__context__ is None
    assert caught.value.__cause__ is None
    for link in _chain(caught.value):
        assert _SENTINEL not in str(link)
        assert _SENTINEL not in repr(link)
        assert _SENTINEL.encode() not in repr(vars(link)).encode()


def test_gh_provider_clears_frames_of_a_base_exception() -> None:
    interrupt = KeyboardInterrupt()
    provider = GhAuthTokenProvider(runner=_leaky_runner(interrupt))
    with (
        patch("django_warden_fabric.fleet_inventory.shutil.which", return_value=_GH),
        pytest.raises(KeyboardInterrupt) as caught,
    ):
        provider.token()
    assert caught.value is interrupt
    assert _runner_frame_locals(interrupt) == [{}]


def test_guard_refuses_the_real_gh_runner(real_gh_attempts: list[list[str]]) -> None:
    """M7: the root conftest's autouse guard stands between every test and ``gh``."""
    with (
        patch("django_warden_fabric.fleet_inventory.shutil.which", return_value=_GH),
        pytest.raises(GhTokenUnavailableError, match="RealGhInvokedError"),
    ):
        GhAuthTokenProvider().token()
    assert real_gh_attempts == [["auth", "token", "--hostname", "github.com"]]
    real_gh_attempts.clear()


def test_gh_guard_still_fails_a_test_that_swallowed_the_refusal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """N3: the guard's teardown fails a test whose broad ``except`` ate the refusal."""
    guard = refuse_real_gh(monkeypatch)
    attempts = next(guard)
    with (
        patch("django_warden_fabric.fleet_inventory.shutil.which", return_value=_GH),
        contextlib.suppress(Exception),
    ):
        GhAuthTokenProvider().token()
    assert attempts == [["auth", "token", "--hostname", "github.com"]]
    with pytest.raises(
        pytest.fail.Exception, match="reached the real gh token provider"
    ):
        next(guard)


def test_real_gh_runner_enforces_its_timeout(tmp_path: Path) -> None:
    """N2: the real ``_run_gh`` seam stops a hung ``gh`` (a harmless sleeper here)."""
    sleeper = tmp_path / "gh"
    sleeper.write_text("#!/bin/sh\nexec sleep 5\n", encoding="utf-8")
    sleeper.chmod(0o755)
    provider = GhAuthTokenProvider(runner=real_run_gh, timeout=0.2)
    started = time.monotonic()
    with (
        patch(
            "django_warden_fabric.fleet_inventory.shutil.which",
            return_value=str(sleeper),
        ),
        pytest.raises(GhTimeoutError, match=r"within 0\.2s"),
    ):
        provider.token()
    assert time.monotonic() - started < _SLEEPER_SECONDS


def test_missing_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing = tmp_path / "missing.toml"
    monkeypatch.setenv(ENV_FLEET_TARGET_CONFIG, str(missing))
    with pytest.raises(FleetTargetConfigError) as exc:
        load_organisation_from_config()
    assert str(missing) in str(exc.value)
    assert "organisation" in str(exc.value).lower()


def test_config_without_organisation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "fleet-target.toml"
    config.write_text("[github]\n", encoding="utf-8")
    monkeypatch.setenv(ENV_FLEET_TARGET_CONFIG, str(config))
    with pytest.raises(FleetTargetConfigError, match="organisation") as exc:
        load_organisation_from_config()
    assert str(config) in str(exc.value)


# --- AC8: gitignored paths; F2: defaults anchor to the checkout, not the cwd ---


def _git_env() -> dict[str, str]:
    """The environment minus ``GIT_*`` (a git hook exports GIT_DIR / GIT_INDEX_FILE)."""
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def test_gitignore_pins_warden_paths() -> None:
    for path in (
        DEFAULT_FLEET_TARGET_CONFIG,
        DEFAULT_FLEET_INVENTORY_PATH,
        Path(".warden/.fleet-inventory.json.example.tmp"),
    ):
        result = subprocess.run(  # noqa: S603
            ["git", "check-ignore", "-q", str(path)],  # noqa: S607
            cwd=_REPO_ROOT,
            env=_git_env(),
            check=False,
        )
        assert result.returncode == 0, path


def test_default_paths_anchor_to_the_checkout_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(ENV_FLEET_TARGET_CONFIG, raising=False)
    monkeypatch.delenv(ENV_FLEET_INVENTORY_PATH, raising=False)
    monkeypatch.chdir(tmp_path)
    assert fleet_checkout_root() == _REPO_ROOT
    assert resolve_fleet_target_config_path() == (
        _REPO_ROOT / DEFAULT_FLEET_TARGET_CONFIG
    )
    assert resolve_fleet_inventory_export_path() == (
        _REPO_ROOT / DEFAULT_FLEET_INVENTORY_PATH
    )


# --- AC9 / Story 18.1: the leak guard ---


def _leak_guard_target() -> tuple[str | None, list[str] | None, Path]:
    """Organisation and listed terms from the configured target, or None when absent."""
    config = resolve_fleet_target_config_path()
    if not config.is_file():
        return None, None, config
    organisation = load_organisation_from_config(config).lower()
    terms = [term.lower() for term in load_leak_guard_terms(config)]
    return organisation, terms, config


def _repo_relative_posix(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def _names_warden(text: str) -> bool:
    return _WARDEN_NAME.search(text.lower()) is not None


def _is_warden_owned_whole_file(rel: str) -> bool:
    path = PurePosixPath(rel)
    return any(path.full_match(entry) for entry in _LEAK_WARDEN_OWNED)


def _is_external_memlog(rel: str) -> bool:
    if not rel.endswith(".memlog.md"):
        return False
    return not rel.startswith(_WARDEN_PROJECT_MEMLOG_PREFIX)


def _in_warden_target_dir(rel: str) -> bool:
    """A path under a ``.warden/`` directory: the target's names live there."""
    return "/.warden/" in f"/{rel}"


def _all_tracked_files(repo_root: Path) -> list[Path]:
    """Every tracked file except under ``.warden/``, which is never opened (N4)."""
    listed = subprocess.run(
        ["git", "ls-files", "-z"],  # noqa: S607
        cwd=repo_root,
        env=_git_env(),
        check=True,
        capture_output=True,
    )
    names = listed.stdout.decode("utf-8", errors="replace").split("\0")
    return [
        repo_root / name for name in names if name and not _in_warden_target_dir(name)
    ]


def _leak_guard_violations(
    repo_root: Path,
    files: Sequence[Path],
    *,
    organisation: str,
    terms: Sequence[str],
    changed_rel: frozenset[str] = _EMPTY_CHANGED,
) -> list[str]:
    """Rule T everywhere; Rule O for the organisation in warden-scoped places only."""
    org = organisation.lower()
    term_list = [term.lower() for term in terms]
    hits: set[str] = set()
    for path in files:
        if not path.is_file():
            continue
        rel = _repo_relative_posix(path, repo_root)
        text = path.read_bytes().decode("utf-8", errors="replace")
        lower = text.lower()
        if term_list and any(term in lower for term in term_list):
            hits.add(rel)
            continue
        if org not in lower:
            continue
        if _is_warden_owned_whole_file(rel):
            hits.add(rel)
            continue
        if _TEAM_MEMORY_ENTRY.match(rel) and _names_warden(text):
            hits.add(rel)
            continue
        line_scoped = (
            rel == ".claude/memory/MEMORY.md"
            or _is_external_memlog(rel)
            or rel in changed_rel
        )
        if line_scoped:
            for line in text.splitlines():
                if _names_warden(line) and org in line.lower():
                    hits.add(rel)
                    break
    return sorted(hits)


def _leak_scan_file_set(
    repo_root: Path, extra_files: Sequence[Path] = ()
) -> list[Path]:
    seen: set[Path] = set(_all_tracked_files(repo_root))
    seen.update(extra_files)
    return sorted(seen)


def _git_names(repo_root: Path, *argv: str) -> list[str]:
    listed = subprocess.run(  # noqa: S603
        ["git", *argv],  # noqa: S607
        cwd=repo_root,
        env=_git_env(),
        check=False,
        capture_output=True,
    )
    if listed.returncode != 0:
        return []
    return [n for n in listed.stdout.decode("utf-8", errors="replace").split("\0") if n]


def _story_changed_files(repo_root: Path, base: str = "origin/main") -> list[Path]:
    """Every file the branch changes against ``base``: committed, staged, unstaged, new.

    ``.warden/`` is never read (it holds the target names; ``.gitignore`` excludes it
    from the untracked list, and it is dropped here too). An unresolvable ``base`` (a
    shallow CI checkout) leaves the working-tree changes only.
    """
    names = set(_git_names(repo_root, "diff", "--name-only", "-z", f"{base}...HEAD"))
    names |= set(_git_names(repo_root, "diff", "--name-only", "-z", "HEAD"))
    names |= set(
        _git_names(repo_root, "ls-files", "-z", "--others", "--exclude-standard")
    )
    return sorted(repo_root / name for name in names if not _in_warden_target_dir(name))


def _tracked_owned_matches(repo_root: Path, entry: str) -> list[str]:
    """Tracked files one warden-owned ``entry`` covers, by the guard's own matcher."""
    listed_dir = entry.split("*", 1)[0].rsplit("/", 1)[0]
    names = _git_names(repo_root, "ls-files", "-z", "--", listed_dir)
    return [name for name in names if PurePosixPath(name).full_match(entry)]


def _fixture_leak_config(tmp_path: Path) -> Path:
    config = tmp_path / "fleet-target.toml"
    config.write_text(
        '[github]\norganisation = "example-org"\n'
        'leak_guard_terms = ["example-repo", "example-project"]\n',
        encoding="utf-8",
    )
    return config


@pytest.fixture
def leak_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An empty directory for a fixture repository; the guard reads its target from env.

    The fixture config is named through ``WARDEN_FLEET_TARGET_CONFIG`` (AC1-AC4) and
    sits beside the repository, so it is never one of that repository's files.
    """
    monkeypatch.setenv(ENV_FLEET_TARGET_CONFIG, str(_fixture_leak_config(tmp_path)))
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo


def _init_git_repo(tmp_path: Path) -> list[str]:
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    git += ["-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false"]
    for argv in (["git", "init", "-q"],):
        subprocess.run(argv, cwd=tmp_path, env=_git_env(), check=True)  # noqa: S603
    return git


def _git_add_all(repo_root: Path) -> None:
    subprocess.run(
        ["git", "add", "-A"],  # noqa: S607
        cwd=repo_root,
        env=_git_env(),
        check=True,
    )


def _git_run(repo_root: Path, *argv: str) -> None:
    subprocess.run(  # noqa: S603
        ["git", *argv],  # noqa: S607
        cwd=repo_root,
        env=_git_env(),
        check=True,
    )


def _git_commit(repo_root: Path, git: list[str], message: str) -> None:
    subprocess.run(  # noqa: S603
        [*git, "commit", "-q", "-m", message],
        cwd=repo_root,
        env=_git_env(),
        check=True,
    )


def _guard_scan(repo_root: Path, *, base: str = "origin/main") -> list[str]:
    """Both rules over the tracked files plus the branch's changed files.

    The organisation and the listed terms come from the configured target
    (``WARDEN_FLEET_TARGET_CONFIG``, through ``_leak_guard_target()``). They live in
    this frame only, which has returned before any caller reports a path.
    """
    organisation, terms, config = _leak_guard_target()
    if organisation is None:
        msg = f"fleet target config absent at {config}"
        raise FileNotFoundError(msg)
    changed = _story_changed_files(repo_root, base=base)
    changed_rel = frozenset(_repo_relative_posix(p, repo_root) for p in changed)
    violations = _leak_guard_violations(
        repo_root,
        _leak_scan_file_set(repo_root, changed),
        organisation=organisation,
        terms=terms or [],
        changed_rel=changed_rel,
    )
    # A tracked ``.warden/`` file publishes the target: named, never opened (N4).
    tracked_targets = _git_names(
        repo_root, "ls-files", "-z", "--", ":(glob)**/.warden/**"
    )
    return sorted({*violations, *tracked_targets})


def _live_guard_failure() -> str | None:
    """The live guard's failure text, or None: paths, a refusal, or an error's type.

    A refusal names its key and the config path, never a value (AC5); any other error
    is reported by type alone. The frames that held the organisation and the terms
    are gone before the caller fails, so ``pytest -l`` has no local to print.
    """
    try:
        paths = _guard_scan(_REPO_ROOT)
    except FleetTargetConfigError as exc:
        return str(exc)
    except Exception as exc:  # noqa: BLE001 - its message or locals may hold a term
        return f"{type(exc).__name__} during the leak-guard scan"
    return "\n".join(paths) or None


@pytest.mark.parametrize(
    ("text", "names_warden"),
    [
        ("pyforge-warden", True),
        ("django_warden_fabric", True),
        ("Warden", True),
        ("vaultwarden", False),
    ],
)
def test_leak_guard_warden_name_boundary(text: str, *, names_warden: bool) -> None:
    """F5: ``-`` and ``_`` bound the name warden; a letter beside it does not."""
    assert _names_warden(text) is names_warden


def test_leak_guard_scan_roots_exist() -> None:
    """AC7: each entry of the one warden-owned set exists and has a tracked file."""
    for entry in _LEAK_WARDEN_OWNED:
        if "*" in entry:
            assert _tracked_owned_matches(_REPO_ROOT, entry), entry
            continue
        unmatched = subprocess.run(  # noqa: S603
            ["git", "ls-files", "--error-unmatch", "--", entry],  # noqa: S607
            cwd=_REPO_ROOT,
            env=_git_env(),
            check=False,
            capture_output=True,
        )
        assert unmatched.returncode == 0, entry
        assert (_REPO_ROOT / entry).is_file(), entry


def test_leak_guard_reads_the_configured_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "fleet-target.toml"
    config.write_text(
        '[github]\norganisation = "Example-Org"\n'
        'leak_guard_terms = ["  Example-Project\\t"]\n',
        encoding="utf-8",
    )
    monkeypatch.setenv(ENV_FLEET_TARGET_CONFIG, str(config))
    # N3: a listed term is stripped, so padding never hides it from Rule T.
    assert _leak_guard_target() == ("example-org", ["example-project"], config)


def test_leak_guard_skips_when_config_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "absent" / "fleet-target.toml"
    monkeypatch.setenv(ENV_FLEET_TARGET_CONFIG, str(missing))
    assert _leak_guard_target() == (None, None, missing)


def test_leak_guard_terms_must_be_a_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """N5: a bare string is refused, never silently dropped from the guard."""
    config = tmp_path / "fleet-target.toml"
    config.write_text(
        '[github]\norganisation = "example-org"\nleak_guard_terms = "example-term"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv(ENV_FLEET_TARGET_CONFIG, str(config))
    with pytest.raises(FleetTargetConfigError, match="leak_guard_terms"):
        load_leak_guard_terms(config)
    with pytest.raises(FleetTargetConfigError, match="leak_guard_terms"):
        _leak_guard_target()


def test_leak_guard_finds_a_planted_term(tmp_path: Path) -> None:
    """Rule T is not vacuous: listed terms in tracked files are found."""
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "hit.txt").write_text("see EXAMPLE-REPO here\n", encoding="utf-8")
    (package / "clean.txt").write_text("nothing to see\n", encoding="utf-8")
    (package / "untracked.txt").write_text("example-repo\n", encoding="utf-8")
    for argv in (["git", "init", "-q"], ["git", "add", "pkg/hit.txt", "pkg/clean.txt"]):
        subprocess.run(argv, cwd=tmp_path, env=_git_env(), check=True)  # noqa: S603
    files = _leak_scan_file_set(tmp_path)
    assert _leak_guard_violations(
        tmp_path, files, organisation="example-org", terms=["example-repo"]
    ) == ["pkg/hit.txt"]


def test_leak_guard_ac1_org_in_non_warden_files_passes(leak_repo: Path) -> None:
    """AC1: the organisation may appear outside warden-scoped places."""
    repo = leak_repo
    _init_git_repo(repo)
    (repo / "docs/dreams").mkdir(parents=True)
    (repo / "docs/dreams/other.md").write_text(
        "Example-Org public link\n", encoding="utf-8"
    )
    (repo / "src/platform/tests").mkdir(parents=True)
    (repo / "src/platform/tests/test_other.py").write_text(
        "# Example-Org\n", encoding="utf-8"
    )
    (repo / ".claude/memory/project").mkdir(parents=True)
    (repo / ".claude/memory/project/old-note.md").write_text(
        "Example-Org note\n", encoding="utf-8"
    )
    (repo / ".claude/memory/MEMORY.md").write_text(
        "- Example-Org index line\n", encoding="utf-8"
    )
    spec_x = repo / _STEWARD_SPEC_X_DIR
    spec_x.mkdir(parents=True)
    (spec_x / ".memlog.md").write_text("- Example-Org reconcile\n", encoding="utf-8")
    (repo / "split.txt").write_text(
        "pyforge-warden owns this\nExample-Org on another line\n", encoding="utf-8"
    )
    _git_add_all(repo)
    assert _guard_scan(repo) == []


def test_leak_guard_ac2_org_in_warden_files_fails(leak_repo: Path) -> None:
    """AC2: the organisation is forbidden in warden-owned and warden-named places."""
    repo = leak_repo
    _init_git_repo(repo)
    hits: list[str] = []
    owned_samples = (
        "src/shared/packages/pyforge-warden/pkg.txt",
        "src/shared/packages/django-warden/pkg.txt",
        # N2: nested and hidden, so a one-segment ``**`` (``match``) misses it.
        (
            "_bmad-output/projects/pyforge-warden/planning-artifacts/specs/"
            "spec-pyforge-warden/.memlog.md"
        ),
        "docs/dreams/pyforge-warden.md",
        "src/platform/tests/test_warden_sample.py",
        ".claude/skills/pyforge-warden/note.txt",
        ".claude/skills/bmad-agent-warden/note.txt",
        "presentations/pyforge-warden/slide.txt",
    )
    for entry in _LEAK_WARDEN_OWNED:
        covering = [s for s in owned_samples if PurePosixPath(s).full_match(entry)]
        assert len(covering) == 1, entry
    for rel in owned_samples:
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Example-Org\n", encoding="utf-8")
        hits.append(rel)
    warden_mem = repo / ".claude/memory/project"
    warden_mem.mkdir(parents=True, exist_ok=True)
    (warden_mem / "warden-note.md").write_text(
        "pyforge-warden\nExample-Org\n", encoding="utf-8"
    )
    hits.append(".claude/memory/project/warden-note.md")
    (repo / ".claude/memory/MEMORY.md").write_text(
        "- pyforge-warden and Example-Org\n", encoding="utf-8"
    )
    hits.append(".claude/memory/MEMORY.md")
    spec_x = repo / _STEWARD_SPEC_X_DIR
    spec_x.mkdir(parents=True)
    memlog_rel = f"{_STEWARD_SPEC_X_DIR}/.memlog.md"
    (spec_x / ".memlog.md").write_text(
        "- pyforge-warden Example-Org\n", encoding="utf-8"
    )
    hits.append(memlog_rel)
    _git_add_all(repo)
    reported = _guard_scan(repo)
    assert reported == sorted(hits)
    joined = "\n".join(reported)
    assert "example-org" not in joined
    assert "example-repo" not in joined


def test_leak_guard_ac3_listed_terms_fail_anywhere(leak_repo: Path) -> None:
    """AC3: Rule T applies in every scanned file."""
    repo = leak_repo
    _init_git_repo(repo)
    (repo / "docs").mkdir()
    (repo / "docs/other.md").write_text("EXAMPLE-REPO\n", encoding="utf-8")
    (repo / "src/shared/packages/pyforge-warden/w.txt").parent.mkdir(parents=True)
    (repo / "src/shared/packages/pyforge-warden/w.txt").write_text(
        "example-project\n", encoding="utf-8"
    )
    (repo / "recipes/x").mkdir(parents=True)
    (repo / "recipes/x/recipe.yaml").write_text("example-repo\n", encoding="utf-8")
    _git_add_all(repo)
    assert _guard_scan(repo) == sorted(
        [
            "docs/other.md",
            "recipes/x/recipe.yaml",
            "src/shared/packages/pyforge-warden/w.txt",
        ]
    )


@pytest.mark.parametrize(
    "gitignore",
    [".warden/\n", "*.pyc\n"],
    ids=["warden-ignored", "warden-not-ignored"],
)
def test_leak_guard_ac4_changed_files_carry_both_rules(
    leak_repo: Path, gitignore: str
) -> None:
    """AC4: changed files get both rules; ``.warden/`` is never read.

    ``edited.txt`` and ``split.txt`` are in the base commit; their new lines are
    unstaged edits, so only the ``git diff HEAD`` leg names them. Without the
    ``.warden/`` ignore line (N4) the untracked leg lists the target file, and only
    the guard's own ``.warden/`` filter keeps it out.
    """
    repo = leak_repo
    base_text = "a line from the base commit\n"
    (repo / ".gitignore").write_text(gitignore, encoding="utf-8")
    (repo / "edited.txt").write_text(base_text, encoding="utf-8")
    (repo / "split.txt").write_text(base_text, encoding="utf-8")
    git = _init_git_repo(repo)
    _git_add_all(repo)
    _git_commit(repo, git, "base")
    _git_run(repo, "tag", "base")
    # 1: committed after the base, outside the warden-owned set, naming a term.
    (repo / "committed.txt").write_text("example-repo\n", encoding="utf-8")
    _git_run(repo, "add", "committed.txt")
    _git_commit(repo, git, "after the base")
    # 2: untracked under the warden-owned set, naming the organisation.
    owned_new = repo / "src/shared/packages/pyforge-warden/new.txt"
    owned_new.parent.mkdir(parents=True)
    owned_new.write_text("example-org\n", encoding="utf-8")
    # 3: an unstaged added line naming warden and the organisation.
    (repo / "edited.txt").write_text(
        f"{base_text}pyforge-warden example-org\n", encoding="utf-8"
    )
    # 4: untracked, not warden-owned, naming the organisation and not warden.
    (repo / "plain.txt").write_text("example-org only\n", encoding="utf-8")
    # 5: unstaged added lines, warden on one and the organisation on another.
    (repo / "split.txt").write_text(
        f"{base_text}pyforge-warden\nexample-org\n", encoding="utf-8"
    )
    # 6: the target directory, ignored and never read.
    (repo / ".warden").mkdir()
    (repo / ".warden/fleet-target.toml").write_text(
        "example-org\nexample-repo\n", encoding="utf-8"
    )
    changed = _story_changed_files(repo, base="base")
    assert [_repo_relative_posix(p, repo) for p in changed] == [
        "committed.txt",
        "edited.txt",
        "plain.txt",
        "split.txt",
        "src/shared/packages/pyforge-warden/new.txt",
    ]
    assert _guard_scan(repo, base="base") == [
        "committed.txt",
        "edited.txt",
        "src/shared/packages/pyforge-warden/new.txt",
    ]


def test_leak_guard_ac5_empty_terms_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC5: empty term lists are refused unless explicitly opted in."""
    for body in (
        '[github]\norganisation = "example-org"\n',
        '[github]\norganisation = "example-org"\nleak_guard_terms = []\n',
        '[github]\norganisation = "example-org"\nleak_guard_terms = ["  "]\n',
    ):
        config = tmp_path / "fleet-target.toml"
        config.write_text(body, encoding="utf-8")
        with pytest.raises(FleetTargetConfigError, match="leak_guard_terms") as exc:
            load_leak_guard_terms(config)
        assert str(config) in str(exc.value)
        assert "example-org" not in str(exc.value)

    allow = tmp_path / "allow-empty.toml"
    allow.write_text(
        '[github]\norganisation = "example-org"\nallow_empty_leak_guard_terms = true\n',
        encoding="utf-8",
    )
    assert load_leak_guard_terms(allow) == []
    monkeypatch.setenv(ENV_FLEET_TARGET_CONFIG, str(allow))
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    (repo / "src/shared/packages/pyforge-warden/hit.txt").parent.mkdir(parents=True)
    (repo / "src/shared/packages/pyforge-warden/hit.txt").write_text(
        "example-org\n", encoding="utf-8"
    )
    (repo / "other.txt").write_text("example-repo\n", encoding="utf-8")
    _git_add_all(repo)
    assert _guard_scan(repo) == ["src/shared/packages/pyforge-warden/hit.txt"]

    bad_bodies = (
        (
            '[github]\norganisation = "example-org"\n'
            'allow_empty_leak_guard_terms = "true"\n'
        ),
        '[github]\norganisation = "example-org"\nallow_empty_leak_guard_terms = 1\n',
    )
    for body in bad_bodies:
        bad = tmp_path / "bad.toml"
        bad.write_text(body, encoding="utf-8")
        with pytest.raises(
            FleetTargetConfigError, match="allow_empty_leak_guard_terms"
        ):
            load_leak_guard_terms(bad)


def test_leak_guard_never_opens_a_tracked_warden_file(
    leak_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """N4: a force-added ``.warden/`` file is reported by name and never opened."""
    repo = leak_repo
    (repo / ".gitignore").write_text(".warden/\n", encoding="utf-8")
    (repo / ".warden").mkdir()
    (repo / ".warden/fleet-target.toml").write_text(
        "example-org\nexample-repo\n", encoding="utf-8"
    )
    git = _init_git_repo(repo)
    _git_add_all(repo)
    _git_run(repo, "add", "-f", ".warden/fleet-target.toml")
    _git_commit(repo, git, "base")
    opened: list[Path] = []
    real_read_bytes = Path.read_bytes

    def spy_read_bytes(self: Path) -> bytes:
        opened.append(self)
        return real_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", spy_read_bytes)
    assert _guard_scan(repo) == [".warden/fleet-target.toml"]
    assert opened
    assert not [path for path in opened if ".warden" in path.parts]


def _live_fixture_repo(repo: Path) -> list[str]:
    """A base commit with ``refs/remotes/origin/main`` at it, as the live scan reads."""
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    git = _init_git_repo(repo)
    _git_add_all(repo)
    _git_commit(repo, git, "base")
    _git_run(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    return git


def test_leak_guard_live_test_fails_with_paths_only(
    leak_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """N1: the live test fails, naming exactly the paths and no term.

    ``committed.txt`` names warden and the organisation on one line; it is reported
    only because the scan compares against ``origin/main``.
    """
    git = _live_fixture_repo(leak_repo)
    (leak_repo / "committed.txt").write_text(
        "pyforge-warden example-org\n", encoding="utf-8"
    )
    (leak_repo / "docs").mkdir()
    (leak_repo / "docs/term.md").write_text("EXAMPLE-PROJECT\n", encoding="utf-8")
    _git_add_all(leak_repo)
    _git_commit(leak_repo, git, "after the base")
    monkeypatch.setattr(sys.modules[__name__], "_REPO_ROOT", leak_repo)
    with pytest.raises(pytest.fail.Exception) as failed:
        test_leak_guard_no_operator_terms_in_tracked_tree()
    message = str(failed.value)
    assert message == "committed.txt\ndocs/term.md"
    for secret in ("example-org", "example-repo", "example-project"):
        assert secret not in message.lower()


def test_leak_guard_live_test_passes_on_a_clean_repo(
    leak_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """N1: the live test passes when no rule fires (the organisation, no warden)."""
    git = _live_fixture_repo(leak_repo)
    (leak_repo / "other.md").write_text("example-org only\n", encoding="utf-8")
    _git_add_all(leak_repo)
    _git_commit(leak_repo, git, "after the base")
    monkeypatch.setattr(sys.modules[__name__], "_REPO_ROOT", leak_repo)
    test_leak_guard_no_operator_terms_in_tracked_tree()


def test_leak_guard_live_test_reports_errors_without_values(
    leak_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """N1: a scan error fails by type alone; a config refusal names key and path."""
    _live_fixture_repo(leak_repo)
    module = sys.modules[__name__]
    monkeypatch.setattr(module, "_REPO_ROOT", leak_repo)

    def raising_scan(repo_root: Path, *, base: str = "origin/main") -> list[str]:
        msg = f"example-repo under {repo_root} at {base}"
        raise RuntimeError(msg)

    with monkeypatch.context() as patched:
        patched.setattr(module, "_guard_scan", raising_scan)
        with pytest.raises(pytest.fail.Exception) as failed:
            test_leak_guard_no_operator_terms_in_tracked_tree()
    assert str(failed.value) == "RuntimeError during the leak-guard scan"

    no_terms = leak_repo.parent / "no-terms.toml"
    no_terms.write_text('[github]\norganisation = "example-org"\n', encoding="utf-8")
    monkeypatch.setenv(ENV_FLEET_TARGET_CONFIG, str(no_terms))
    with pytest.raises(pytest.fail.Exception) as refused:
        test_leak_guard_no_operator_terms_in_tracked_tree()
    assert str(no_terms) in str(refused.value)
    assert "leak_guard_terms" in str(refused.value)
    assert "example-org" not in str(refused.value)


def test_leak_guard_no_operator_terms_in_tracked_tree() -> None:
    """AC7: every tracked file and the branch's changed files, through both rules.

    A failure prints paths only (F6): no traceback, and no local that holds a term.
    """
    config = resolve_fleet_target_config_path()
    if not config.is_file():
        pytest.skip(f"fleet target config absent at {config} (CI): nothing to guard")
    failure = _live_guard_failure()
    if failure is not None:
        pytest.fail(failure, pytrace=False)


# --- AC6, AC7: the real client path, GET only, no sentinel anywhere (F3, F4) ---


@pytest.mark.django_db
def test_real_client_run_is_get_only_and_never_persists_the_token(
    inventory_paths: tuple[Path, Path],
    github_wire: _GitHubWire,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _config, export = inventory_paths
    caplog.set_level(logging.DEBUG)
    github_wire.serve_fixture_org()
    with patch("django_warden_fabric.tasks.GhAuthTokenProvider", _SentinelProvider):
        run_fleet_inventory("run-id", _EXAMPLE_ORG)
    assert [e.url for e in github_wire.exchanges] == [_FIRST_PAGE, _SECOND_PAGE]
    assert {e.method for e in github_wire.exchanges} == {"GET"}
    assert {e.authorization for e in github_wire.exchanges} == {f"Bearer {_SENTINEL}"}
    assert {e.timeout for e in github_wire.exchanges} == {
        FLEET_INVENTORY_REQUEST_TIMEOUT_SECONDS
    }
    assert github_wire.stack_leaks == []
    payload = json.loads(export.read_text(encoding="utf-8"))
    assert len(payload["repos"]) == _FIXTURE_REPO_COUNT
    assert _SENTINEL not in export.read_text(encoding="utf-8")
    assert _SENTINEL not in caplog.text
    for row in FleetRepo.objects.filter(organisation=_EXAMPLE_ORG):
        blob = f"{row.full_name}{row.clone_url}{row.default_branch}"
        assert _SENTINEL not in blob


@pytest.mark.django_db
@pytest.mark.parametrize(
    "case",
    [("http-503", "HTTP 503", 1), ("connect-refused", "request failed", 0)],
    ids=["http-error", "url-error"],
)
def test_real_client_failure_never_carries_the_token(
    inventory_paths: tuple[Path, Path],
    github_wire: _GitHubWire,
    caplog: pytest.LogCaptureFixture,
    case: tuple[str, str, int],
) -> None:
    fault, message, requests = case
    _config, export = inventory_paths
    caplog.set_level(logging.DEBUG)
    if fault == "http-503":
        github_wire.routes[_FIRST_PAGE] = _http_response(
            HTTPStatus.SERVICE_UNAVAILABLE, body=b'{"message": "down"}'
        )
    else:
        github_wire.connect_error = ConnectionRefusedError(111, "Connection refused")
    with (
        patch("django_warden_fabric.tasks.GhAuthTokenProvider", _SentinelProvider),
        pytest.raises(Exception, match=message) as caught,
    ):
        run_fleet_inventory("run-id", _EXAMPLE_ORG)
    assert type(caught.value).__name__ == "FleetInventoryApiError"
    assert [e.method for e in github_wire.exchanges] == ["GET"] * requests
    assert not export.exists()
    assert "fleet inventory run-id failed" in caplog.text
    assert _SENTINEL not in caplog.text
    current: BaseException | None = caught.value
    while current is not None:
        assert _SENTINEL not in str(current)
        assert _SENTINEL not in repr(current)
        current = current.__cause__ or current.__context__
    assert not FleetRepo.objects.filter(organisation=_EXAMPLE_ORG).exists()


def _platform_json_log_handler(stream: StringIO) -> logging.Handler:
    """A handler rendering exactly as a deployed platform does (JSON, frame locals)."""
    structured = build_logging_config(debug=False, log_format=JSON)["formatters"][
        "structured"
    ]
    handler = logging.StreamHandler(stream)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processors=structured["processors"],
            foreign_pre_chain=structured["foreign_pre_chain"],
        )
    )
    return handler


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_connection_failure_log_lines_never_carry_the_token(
    inventory_paths: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real urllib path fails at connect; every rendered log line stays token-free.

    The platform's JSON renderer prints each traceback frame's locals; urllib's
    ``do_open`` holds the request headers (Authorization) as one.
    """
    _config, export = inventory_paths

    def _refused(_connection: object) -> None:
        raise ConnectionRefusedError(111, "Connection refused")

    monkeypatch.setattr("http.client.HTTPSConnection.connect", _refused)
    stream = StringIO()
    handler = _platform_json_log_handler(stream)
    root = logging.getLogger()
    root.addHandler(handler)
    try:
        with (
            patch("django_warden_fabric.tasks.GhAuthTokenProvider", _SentinelProvider),
            pytest.raises(Exception, match="request failed"),
        ):
            run_fleet_inventory.delay("run-id", _EXAMPLE_ORG)
    finally:
        root.removeHandler(handler)
    rendered = stream.getvalue()
    assert "fleet inventory run-id failed" in rendered
    assert '"locals"' in rendered
    assert _SENTINEL not in rendered
    assert not export.exists()


_PARTIAL_BODY = (
    b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
    b"Content-Length: 100\r\n\r\n"
    b'[{"full_name": "example-org/alpha"'
)


@pytest.mark.django_db
@pytest.mark.usefixtures("inventory_flags_on")
@pytest.mark.parametrize(
    "case",
    [
        (b"", TimeoutError("timed out"), "TimeoutError"),
        (b"", ConnectionResetError(104, "Connection reset by peer"), "ConnectionReset"),
        (_PARTIAL_BODY, None, "IncompleteRead"),
    ],
    ids=["read-timeout", "reset-in-getresponse", "incomplete-read"],
)
def test_unwrapped_transport_error_never_reaches_logs_or_the_debug_page(
    inventory_paths: tuple[Path, Path],
    github_wire: _GitHubWire,
    settings,
    case: tuple[bytes, BaseException | None, str],
) -> None:
    """N1: a failure urllib does not wrap (in ``getresponse()`` or ``read()``) is typed.

    Driven from the portal in eager mode with DEBUG on: the task's own per-run log
    fires, and neither the production JSON log lines (``django.request`` and the
    rest, with frame locals) nor the DEBUG 500 page carries the token.
    """
    head, then, kind = case
    _config, export = inventory_paths
    github_wire.script(_FIRST_PAGE, head, then)
    portal = Client(raise_request_exception=False)
    _authed(portal, settings)
    stream = StringIO()
    handler = _platform_json_log_handler(stream)
    root = logging.getLogger()
    root.addHandler(handler)
    try:
        with (
            patch("django_warden_fabric.tasks.GhAuthTokenProvider", _SentinelProvider),
            override_settings(DEBUG=True, CELERY_TASK_ALWAYS_EAGER=True),
        ):
            response = portal.post("/stations/warden/fleet/inventory/start/")
    finally:
        root.removeHandler(handler)
    body = response.content.decode("utf-8", errors="replace")
    rendered = stream.getvalue()
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert '"locals"' in rendered
    assert _SENTINEL not in body
    assert _SENTINEL not in rendered
    # Typed: the DEBUG page names the client's error, and the task's per-run log fired.
    assert "FleetInventoryApiError at /stations/warden/fleet/inventory/start/" in body
    assert f"transport failed: {kind}" in body
    assert re.search(r"fleet inventory [0-9a-f-]{36} failed", rendered)
    assert not export.exists()


@pytest.fixture
def structlog_celery_receiver() -> Iterator[CeleryReceiver]:
    """django_structlog's worker receivers, connected as the worker bootstep does.

    structlog is put back on the platform's own configuration for the test (another
    test may have left a print-logger configuration behind), then restored.
    """
    previous = structlog.get_config()
    configure_structlog()
    receiver = CeleryReceiver()
    receiver.connect_worker_signals()
    yield receiver
    for signal, handler in (
        (before_task_publish, receiver.receiver_before_task_publish),
        (after_task_publish, receiver.receiver_after_task_publish),
        (task_prerun, receiver.receiver_task_prerun),
        (task_retry, receiver.receiver_task_retry),
        (task_success, receiver.receiver_task_success),
        (task_failure, receiver.receiver_task_failure),
        (task_revoked, receiver.receiver_task_revoked),
        (task_unknown, receiver.receiver_task_unknown),
        (task_rejected, receiver.receiver_task_rejected),
    ):
        signal.disconnect(handler)
    structlog.configure(**previous)


@pytest.mark.django_db
@pytest.mark.usefixtures("structlog_celery_receiver")
@pytest.mark.parametrize("phase", ["connect", "send", "getresponse"])
@pytest.mark.parametrize(
    "error",
    [SoftTimeLimitExceeded(), RuntimeError("an untyped error inside urllib")],
    ids=["soft-time-limit", "runtime-error"],
)
def test_worker_task_failed_line_never_carries_the_token(
    inventory_paths: tuple[Path, Path],
    github_wire: _GitHubWire,
    phase: str,
    error: Exception,
) -> None:
    """P1: an error raised inside urllib, rendered by the worker's ``task_failed`` line.

    ``run_fleet_inventory.apply()`` with django_structlog's Celery receiver connected
    and the production JSON renderer (frame locals on). Before the fix, the token
    sat in urllib ``do_open``'s ``headers`` local, which ``task_failed`` printed.
    """
    _config, export = inventory_paths
    if phase == "connect":
        github_wire.connect_error = error
    elif phase == "send":
        # The second write is the first credential fragment, spliced in by the client.
        github_wire.send_error, github_wire.send_error_call = error, 2
    else:
        github_wire.script(_FIRST_PAGE, b"", error)
    stream = StringIO()
    handler = _platform_json_log_handler(stream)
    root = logging.getLogger()
    root.addHandler(handler)
    try:
        with patch("django_warden_fabric.tasks.GhAuthTokenProvider", _SentinelProvider):
            result = run_fleet_inventory.apply(
                args=("run-1", _EXAMPLE_ORG), throw=False
            )
    finally:
        root.removeHandler(handler)
    rendered = stream.getvalue()
    events = [
        json.loads(line) for line in rendered.splitlines() if line.startswith("{")
    ]
    assert any(event.get("event") == "task_failed" for event in events)
    assert '"locals"' in rendered
    assert _SENTINEL not in rendered
    assert _SENTINEL not in repr(result.result)
    assert _SENTINEL not in str(result.traceback)
    # Typed: the client's own error, and the task's per-run log fired.
    assert type(result.result).__name__ == "FleetInventoryApiError"
    assert f"transport failed: {type(error).__name__}" in str(result.result)
    assert "fleet inventory run-1 failed" in rendered
    assert github_wire.stack_leaks == []
    assert not export.exists()


def test_inventory_task_limits_bound_full_pagination(settings) -> None:
    """P1: request timeout < soft limit < hard limit <= the general pool's limit."""
    assert (
        run_fleet_inventory.soft_time_limit == FLEET_INVENTORY_SOFT_TIME_LIMIT_SECONDS
    )
    assert run_fleet_inventory.time_limit == FLEET_INVENTORY_TIME_LIMIT_SECONDS
    assert (
        FLEET_INVENTORY_REQUEST_TIMEOUT_SECONDS
        < FLEET_INVENTORY_SOFT_TIME_LIMIT_SECONDS
        < FLEET_INVENTORY_TIME_LIMIT_SECONDS
        <= settings.CELERY_TASK_TIME_LIMIT
    )


@pytest.mark.django_db
def test_task_missing_gh_binary_leaves_no_export(
    inventory_paths: tuple[Path, Path],
) -> None:
    _config, export = inventory_paths
    with (
        patch("django_warden_fabric.fleet_inventory.shutil.which", return_value=None),
        pytest.raises(GhBinaryMissingError),
    ):
        run_fleet_inventory("run-id", _EXAMPLE_ORG)
    assert not export.exists()


# --- AC11: the flag ---


def _story_flagd_tree(tmp_path: Path, flags: dict[str, str]) -> Path:
    """Write a minimal OpenFeature file tree.

    The platform host reaches no pyforge package, the testing kit included.
    """
    tree: dict[str, object] = {"flags": {}}
    flag_map = tree["flags"]
    assert isinstance(flag_map, dict)
    for key, variant in flags.items():
        flag_map[key] = {
            "state": "ENABLED",
            "variants": {"on": True, "off": False},
            "defaultVariant": variant,
        }
    path = tmp_path / "flags-gate.json"
    path.write_text(json.dumps(tree, indent=2) + "\n", encoding="utf-8")
    return path


def test_fleet_inventory_flagd_tree_on(tmp_path: Path) -> None:
    source = _story_flagd_tree(tmp_path, {"pyforge.warden.fleet_inventory": "on"})
    assert evaluate_from_source(key=FLEET_INVENTORY_FLAG, source=source) is True


def test_fleet_inventory_flagd_tree_off(tmp_path: Path) -> None:
    source = _story_flagd_tree(tmp_path, {"pyforge.warden.fleet_inventory": "off"})
    assert evaluate_from_source(key=FLEET_INVENTORY_FLAG, source=source) is False


def _flag_tree(*, on: bool) -> dict:
    tree = json.loads(_FLAGS_JSON.read_text(encoding="utf-8"))
    entry = tree["flags"][FLEET_INVENTORY_FLAG]
    entry["defaultVariant"] = "on" if on else "off"
    return tree


@pytest.fixture
def inventory_flags_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    tree = tmp_path / "flags-on.json"
    tree.write_text(json.dumps(_flag_tree(on=True)), encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    assert evaluate_from_source(key=FLEET_INVENTORY_FLAG, source=tree) is True
    return tree


@pytest.fixture
def inventory_flags_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    tree = tmp_path / "flags-off.json"
    tree.write_text(json.dumps(_flag_tree(on=False)), encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    assert evaluate_from_source(key=FLEET_INVENTORY_FLAG, source=tree) is False
    return tree


@pytest.mark.django_db
def test_flag_off_refuses_exit_2(
    inventory_flags_off: Path, inventory_paths: tuple[Path, Path]
) -> None:
    stderr = StringIO()
    with pytest.raises(SystemExit) as exc:
        call_command("warden_fleet_inventory", stderr=stderr)
    assert exc.value.code == _EXIT_REFUSED


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_flag_on_runs_inventory(
    inventory_flags_on: Path,
    inventory_paths: tuple[Path, Path],
    github_wire: _GitHubWire,
) -> None:
    _config, export = inventory_paths
    github_wire.serve_fixture_org()
    with patch("django_warden_fabric.tasks.GhAuthTokenProvider", _SentinelProvider):
        call_command("warden_fleet_inventory")
    payload = json.loads(export.read_text(encoding="utf-8"))
    assert len(payload["repos"]) == _FIXTURE_REPO_COUNT


def _authed(client, settings, *, sub: str = "op-1"):
    claims: dict[str, object] = {
        "sub": sub,
        "groups": ["pyforge:station:warden"],
    }
    settings.IDP_CLAIMS_SNAPSHOT = claims
    session = client.session
    session[IDP_TOKEN_CLAIMS_SESSION_KEY] = claims
    session.save()
    return client


@pytest.mark.django_db
def test_portal_fleet_inventory_refuses_when_flag_off(
    client,
    settings,
    inventory_flags_off: Path,
) -> None:
    _authed(client, settings)
    response = client.post("/stations/warden/fleet/inventory/start/")
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert b"disabled" in response.content.lower()


@pytest.mark.django_db
@pytest.mark.usefixtures("inventory_flags_on")
def test_portal_config_refusal_names_no_path(
    client,
    settings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """N6a: the portal shows a fixed message; the config path goes to the server log."""
    missing = tmp_path / "absent" / "fleet-target.toml"
    monkeypatch.setenv(ENV_FLEET_TARGET_CONFIG, str(missing))
    _authed(client, settings)
    caplog.set_level(logging.WARNING)
    response = client.post("/stations/warden/fleet/inventory/start/")
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.content.decode() == FLEET_INVENTORY_CONFIG_REFUSAL
    assert str(missing) not in response.content.decode()
    assert str(missing) in caplog.text


@pytest.mark.django_db
def test_portal_chrome_lists_inventory_disabled_when_flag_off(
    client,
    settings,
    inventory_flags_off: Path,
) -> None:
    _authed(client, settings)
    home = client.get("/stations/warden/")
    assert home.status_code == HTTPStatus.OK
    body = home.content.decode()
    assert "disabled" in body
    assert "flag off" in body.lower()


# --- M9: the export goes through a unique temp file, then an atomic rename ---


def test_atomic_write_leaves_no_partial_on_failure(tmp_path: Path) -> None:
    target = tmp_path / "out.json"
    with (
        patch.object(Path, "replace", side_effect=OSError("disk full")),
        pytest.raises(OSError, match="disk full"),
    ):
        atomic_write_json(target, {"repos": []})
    assert list(tmp_path.iterdir()) == []


def test_atomic_write_uses_a_unique_temp_file_beside_the_export(tmp_path: Path) -> None:
    target = tmp_path / "out.json"
    sources: list[Path] = []
    real_replace = Path.replace

    def _recording_replace(self: Path, destination: Path) -> Path:
        sources.append(self)
        return real_replace(self, destination)

    with patch.object(Path, "replace", _recording_replace):
        atomic_write_json(target, {"repos": [1]})
        atomic_write_json(target, {"repos": [2]})
    assert len(sources) == len(set(sources)) == _TWO_WRITES
    assert all(source.parent == tmp_path for source in sources)
    assert all(source.name.startswith(".out.json.") for source in sources)
    assert json.loads(target.read_text(encoding="utf-8")) == {"repos": [2]}
    assert [path.name for path in tmp_path.iterdir()] == ["out.json"]
