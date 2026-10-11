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
import time
import traceback
import urllib.error
import urllib.response
from dataclasses import dataclass
from dataclasses import field
from email.message import Message
from http import HTTPStatus
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Protocol
from unittest.mock import patch

import pytest
import structlog
from django.core.management import call_command
from django.test import Client
from django.test.utils import override_settings
from django_pyforge.flags import evaluate_from_source
from django_pyforge.roles import IDP_TOKEN_CLAIMS_SESSION_KEY
from django_warden_fabric.fleet import FLEET_INVENTORY_FLAG
from django_warden_fabric.fleet_inventory import DEFAULT_FLEET_INVENTORY_PATH
from django_warden_fabric.fleet_inventory import DEFAULT_FLEET_TARGET_CONFIG
from django_warden_fabric.fleet_inventory import ENV_FLEET_INVENTORY_PATH
from django_warden_fabric.fleet_inventory import ENV_FLEET_TARGET_CONFIG
from django_warden_fabric.fleet_inventory import GH_AUTH_TOKEN_TIMEOUT_SECONDS
from django_warden_fabric.fleet_inventory import FleetTargetConfigError
from django_warden_fabric.fleet_inventory import GhAuthTokenProvider
from django_warden_fabric.fleet_inventory import GhBinaryMissingError
from django_warden_fabric.fleet_inventory import GhLoginMissingError
from django_warden_fabric.fleet_inventory import GhTimeoutError
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
from tests.gh_guard import refuse_real_gh

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Sequence

_EXAMPLE_ORG = "example-org"
_FIXTURE_REPO_COUNT = 3
_EXIT_REFUSED = 2
_SENTINEL = "sentinel-token-must-not-leak-16-1"
_GH = "/opt/example/bin/gh"
_TWO_WRITES = 2
_SLEEPER_SECONDS = 5
_SRC_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _SRC_ROOT.parent
_PLATFORM_DIR = Path(__file__).resolve().parents[1]
_FLAGS_JSON = _PLATFORM_DIR / "config" / "flags.json"
_PACKAGES = _SRC_ROOT / "shared" / "packages"
_FABRIC_ROOT = _PACKAGES / "django-warden" / "src" / "django_warden_fabric"
_TASKS_PATH = _FABRIC_ROOT / "tasks.py"
# AC9: the tracked paths the fleet stories write.
_LEAK_SCAN_ROOTS = (
    _REPO_ROOT / "_bmad-output" / "projects" / "pyforge-warden",
    _PACKAGES / "django-warden",
    _PACKAGES / "pyforge-warden",
    _PLATFORM_DIR,
    _REPO_ROOT / "docs" / "dreams" / "pyforge-warden.md",
    _REPO_ROOT / ".gitignore",
)
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


# --- stub GitHub transport for the real client (stdlib handlers patched) ---


class _OutgoingRequest(Protocol):
    """What the stub transport reads off urllib's request object."""

    full_url: str

    def get_method(self) -> str: ...

    def get_header(self, header_name: str) -> str | None: ...


class _StubResponse(urllib.response.addinfourl):
    msg = "stub"  # urllib's HTTP handlers set .msg on a response; addinfourl has none


def _reply(
    req: _OutgoingRequest,
    status: int,
    *,
    body: bytes = b"",
    headers: dict[str, str] | None = None,
) -> _StubResponse:
    message = Message()
    for key, value in (headers or {}).items():
        message[key] = value
    return _StubResponse(io.BytesIO(body), message, req.full_url, status)


def _api_repo(name: str, *, branch: str = "main", archived: bool = False) -> dict:
    return {
        "full_name": f"{_EXAMPLE_ORG}/{name}",
        "default_branch": branch,
        "clone_url": f"https://github.com/{_EXAMPLE_ORG}/{name}.git",
        "archived": archived,
    }


def _page(
    req: _OutgoingRequest, repos: list[dict], *, next_url: str | None = None
) -> _StubResponse:
    headers = {"Content-Type": "application/json"}
    if next_url is not None:
        headers["Link"] = f'<{next_url}>; rel="next"'
    return _reply(req, HTTPStatus.OK, body=json.dumps(repos).encode(), headers=headers)


@dataclass(frozen=True)
class _Exchange:
    method: str
    url: str
    authorization: str | None


@dataclass
class _GitHubWire:
    """Answers the real client by URL and records each request it really sends."""

    routes: dict[str, Callable[[_OutgoingRequest], _StubResponse]] = field(
        default_factory=dict
    )
    exchanges: list[_Exchange] = field(default_factory=list)

    def answer(self, req: _OutgoingRequest) -> _StubResponse:
        self.exchanges.append(
            _Exchange(
                method=req.get_method(),
                url=req.full_url,
                authorization=req.get_header("Authorization"),
            )
        )
        responder = self.routes.get(req.full_url)
        if responder is None:
            return _reply(req, HTTPStatus.NOT_FOUND, body=b"{}")
        return responder(req)

    def serve_fixture_org(self) -> None:
        self.routes[_FIRST_PAGE] = lambda req: _page(
            req,
            [_api_repo("alpha"), _api_repo("beta", branch="develop")],
            next_url=_SECOND_PAGE,
        )
        self.routes[_SECOND_PAGE] = lambda req: _page(
            req, [_api_repo("archived-one", archived=True)]
        )


@pytest.fixture
def github_wire(monkeypatch: pytest.MonkeyPatch) -> _GitHubWire:
    wire = _GitHubWire()

    def _open(_handler: object, req: _OutgoingRequest) -> _StubResponse:
        return wire.answer(req)

    # By dotted name: this module adds no raw-HTTP import under src/platform
    # (doctor's test_story_does_not_add_pyforge_under_src_platform).
    monkeypatch.setattr("urllib.request.HTTPSHandler.https_open", _open)
    monkeypatch.setattr("urllib.request.HTTPHandler.http_open", _open)
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
    expired = subprocess.TimeoutExpired(cmd=[_GH], timeout=7.5, output=_SENTINEL)
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


def test_guard_refuses_the_real_gh_runner(real_gh_attempts: list[list[str]]) -> None:
    """M7: the root conftest's autouse guard stands between every test and ``gh``."""
    with (
        patch("django_warden_fabric.fleet_inventory.shutil.which", return_value=_GH),
        pytest.raises(AssertionError, match="real gh token provider"),
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
        contextlib.suppress(AssertionError),
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


# --- AC9: the leak guard ---


def _leak_guard_terms() -> tuple[list[str] | None, Path]:
    """The forbidden terms from the configured target, or None when it is absent."""
    config = resolve_fleet_target_config_path()
    if not config.is_file():
        return None, config
    organisation = load_organisation_from_config(config)
    extra = [term.lower() for term in load_leak_guard_terms(config)]
    return [organisation.lower(), *extra], config


def _tracked_files(repo_root: Path, roots: Sequence[Path]) -> list[Path]:
    relative = [str(root.relative_to(repo_root)) for root in roots]
    listed = subprocess.run(  # noqa: S603
        ["git", "ls-files", "-z", "--", *relative],  # noqa: S607
        cwd=repo_root,
        env=_git_env(),
        check=True,
        capture_output=True,
    )
    names = listed.stdout.decode("utf-8", errors="replace").split("\0")
    return [repo_root / name for name in names if name]


def _leak_hits(repo_root: Path, roots: Sequence[Path], terms: list[str]) -> list[str]:
    """Tracked files under ``roots`` naming any term (case-insensitive, fixed string).

    Reports paths only, never the term, so a failure prints no target name.
    """
    hits: list[str] = []
    for path in _tracked_files(repo_root, roots):
        if not path.is_file():
            continue
        text = path.read_bytes().decode("utf-8", errors="replace").lower()
        if any(term in text for term in terms):
            hits.append(str(path.relative_to(repo_root)))
    return hits


def test_leak_guard_scan_roots_exist() -> None:
    missing = [str(root) for root in _LEAK_SCAN_ROOTS if not root.exists()]
    assert missing == []
    assert _tracked_files(_REPO_ROOT, _LEAK_SCAN_ROOTS)


def test_leak_guard_reads_the_configured_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "fleet-target.toml"
    config.write_text(
        '[github]\norganisation = "Example-Org"\n'
        'leak_guard_terms = ["Example-Project"]\n',
        encoding="utf-8",
    )
    monkeypatch.setenv(ENV_FLEET_TARGET_CONFIG, str(config))
    assert _leak_guard_terms() == (["example-org", "example-project"], config)


def test_leak_guard_skips_when_config_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "absent" / "fleet-target.toml"
    monkeypatch.setenv(ENV_FLEET_TARGET_CONFIG, str(missing))
    assert _leak_guard_terms() == (None, missing)


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
        _leak_guard_terms()


def test_leak_guard_finds_a_planted_term(tmp_path: Path) -> None:
    """The guard is not vacuous: tracked hits are found, untracked files ignored."""
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "hit.txt").write_text("see EXAMPLE-ORG here\n", encoding="utf-8")
    (package / "clean.txt").write_text("nothing to see\n", encoding="utf-8")
    (package / "untracked.txt").write_text("example-org\n", encoding="utf-8")
    for argv in (["git", "init", "-q"], ["git", "add", "pkg/hit.txt", "pkg/clean.txt"]):
        subprocess.run(argv, cwd=tmp_path, env=_git_env(), check=True)  # noqa: S603
    assert _leak_hits(tmp_path, [package], ["example-org"]) == ["pkg/hit.txt"]


def test_leak_guard_no_operator_terms_in_tracked_tree() -> None:
    terms, config = _leak_guard_terms()
    if terms is None:
        pytest.skip(f"fleet target config absent at {config} (CI): nothing to guard")
    assert _leak_hits(_REPO_ROOT, _LEAK_SCAN_ROOTS, terms) == []


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
    payload = json.loads(export.read_text(encoding="utf-8"))
    assert len(payload["repos"]) == _FIXTURE_REPO_COUNT
    assert _SENTINEL not in export.read_text(encoding="utf-8")
    assert _SENTINEL not in caplog.text
    for row in FleetRepo.objects.filter(organisation=_EXAMPLE_ORG):
        blob = f"{row.full_name}{row.clone_url}{row.default_branch}"
        assert _SENTINEL not in blob


def _service_unavailable(req: _OutgoingRequest) -> _StubResponse:
    return _reply(req, HTTPStatus.SERVICE_UNAVAILABLE, body=b'{"message": "down"}')


def _connection_reset(req: _OutgoingRequest) -> _StubResponse:
    reason = "connection reset"
    raise urllib.error.URLError(reason)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("responder", "message"),
    [(_service_unavailable, "HTTP 503"), (_connection_reset, "request failed")],
    ids=["http-error", "url-error"],
)
def test_real_client_failure_never_carries_the_token(
    inventory_paths: tuple[Path, Path],
    github_wire: _GitHubWire,
    caplog: pytest.LogCaptureFixture,
    responder: Callable[[_OutgoingRequest], _StubResponse],
    message: str,
) -> None:
    _config, export = inventory_paths
    caplog.set_level(logging.DEBUG)
    github_wire.routes[_FIRST_PAGE] = responder
    with (
        patch("django_warden_fabric.tasks.GhAuthTokenProvider", _SentinelProvider),
        pytest.raises(Exception, match=message) as caught,
    ):
        run_fleet_inventory("run-id", _EXAMPLE_ORG)
    assert type(caught.value).__name__ == "FleetInventoryApiError"
    assert [e.method for e in github_wire.exchanges] == ["GET"]
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


class _ScriptedReader(io.BytesIO):
    """Serves ``head``, then raises ``then`` (or reports EOF) once it runs dry."""

    def __init__(self, head: bytes, then: BaseException | None) -> None:
        super().__init__(head)
        self._then = then

    def _dry(self, data: bytes) -> bytes:
        if not data and self._then is not None:
            raise self._then
        return data

    def readline(self, size: int | None = -1) -> bytes:
        return self._dry(super().readline(size))

    def read(self, size: int | None = -1) -> bytes:
        return self._dry(super().read(size))


class _FakeSocket:
    """Takes the request bytes and answers from a script; never touches the network."""

    def __init__(self, reader: _ScriptedReader) -> None:
        self._reader = reader

    def sendall(self, data: bytes) -> None:
        del data

    def makefile(self, mode: str, *args: object, **kwargs: object) -> _ScriptedReader:
        return self._reader

    def close(self) -> None:
        pass


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
    monkeypatch: pytest.MonkeyPatch,
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

    def _connect(connection: Any) -> None:
        connection.sock = _FakeSocket(_ScriptedReader(head, then))

    monkeypatch.setattr("http.client.HTTPSConnection.connect", _connect)
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
