"""Story 16.1 — fleet inventory from github.com (fixture organisation only)."""

from __future__ import annotations

import ast
import json
import logging
import subprocess
from http import HTTPStatus
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.test.utils import override_settings
from django_pyforge.flags import evaluate_from_source
from django_pyforge.roles import IDP_TOKEN_CLAIMS_SESSION_KEY
from django_warden_fabric.fleet import FLEET_INVENTORY_FLAG
from django_warden_fabric.fleet_inventory import DEFAULT_FLEET_TARGET_CONFIG
from django_warden_fabric.fleet_inventory import ENV_FLEET_INVENTORY_PATH
from django_warden_fabric.fleet_inventory import ENV_FLEET_TARGET_CONFIG
from django_warden_fabric.fleet_inventory import FleetInventoryError
from django_warden_fabric.fleet_inventory import FleetTargetConfigError
from django_warden_fabric.fleet_inventory import GhAuthTokenProvider
from django_warden_fabric.fleet_inventory import GhBinaryMissingError
from django_warden_fabric.fleet_inventory import GhLoginMissingError
from django_warden_fabric.fleet_inventory import ListedRepo
from django_warden_fabric.fleet_inventory import RecordingOrgReposClient
from django_warden_fabric.fleet_inventory import atomic_write_json
from django_warden_fabric.fleet_inventory import load_leak_guard_terms
from django_warden_fabric.fleet_inventory import load_organisation_from_config
from django_warden_fabric.fleet_inventory import run_fleet_inventory_sync
from django_warden_fabric.models import FleetRepo
from django_warden_fabric.tasks import run_fleet_inventory
from pyforge.warden.fleet_github_rest import GitHubRestOrgReposClient
from pyforge.warden.fleet_github_rest import HttpMethodRefusedError

_EXAMPLE_ORG = "example-org"
_FIXTURE_REPO_COUNT = 3
_PAGINATED_REPO_COUNT = 2
_EXIT_REFUSED = 2
_SENTINEL = "sentinel-token-must-not-leak-16-1"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_PLATFORM_DIR = Path(__file__).resolve().parents[1]
_FLAGS_JSON = _PLATFORM_DIR / "config" / "flags.json"
_FABRIC_ROOT = (
    _REPO_ROOT
    / "shared"
    / "packages"
    / "django-warden"
    / "src"
    / "django_warden_fabric"
)
_TASKS_PATH = _FABRIC_ROOT / "tasks.py"
_LEAK_SCAN_ROOTS = (
    _REPO_ROOT / "_bmad-output/projects/pyforge-warden",
    _FABRIC_ROOT,
    _REPO_ROOT / "shared/packages/pyforge-warden",
    _PLATFORM_DIR,
    _REPO_ROOT / "docs/dreams/pyforge-warden.md",
    _REPO_ROOT / ".gitignore",
)


def _fixture_repos() -> list[ListedRepo]:
    return [
        ListedRepo(
            full_name=f"{_EXAMPLE_ORG}/alpha",
            default_branch="main",
            clone_url=f"https://github.com/{_EXAMPLE_ORG}/alpha.git",
            archived=False,
        ),
        ListedRepo(
            full_name=f"{_EXAMPLE_ORG}/beta",
            default_branch="develop",
            clone_url=f"https://github.com/{_EXAMPLE_ORG}/beta.git",
            archived=False,
        ),
        ListedRepo(
            full_name=f"{_EXAMPLE_ORG}/archived-one",
            default_branch="main",
            clone_url=f"https://github.com/{_EXAMPLE_ORG}/archived-one.git",
            archived=True,
        ),
    ]


def _recording_client() -> RecordingOrgReposClient:
    return RecordingOrgReposClient(repos_by_org={_EXAMPLE_ORG: _fixture_repos()})


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


@pytest.mark.django_db
def test_inventory_three_repos(inventory_paths: tuple[Path, Path]) -> None:
    _config, export = inventory_paths
    client = _recording_client()
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
    assert client.calls == [("GET", f"/orgs/{_EXAMPLE_ORG}/repos")]


@pytest.mark.django_db
def test_inventory_rerun_updates_not_duplicates(
    inventory_paths: tuple[Path, Path],
) -> None:
    _config, export = inventory_paths
    client = _recording_client()
    run_fleet_inventory_sync(
        organisation=_EXAMPLE_ORG,
        listing_client=client,
        export_path=export,
    )
    run_fleet_inventory_sync(
        organisation=_EXAMPLE_ORG,
        listing_client=client,
        export_path=export,
    )
    assert (
        FleetRepo.objects.filter(organisation=_EXAMPLE_ORG).count()
        == _FIXTURE_REPO_COUNT
    )


def test_pagination_reads_link_next() -> None:
    page_one = [
        {
            "full_name": f"{_EXAMPLE_ORG}/page-one",
            "default_branch": "main",
            "clone_url": "https://example.com/one.git",
            "archived": False,
        },
    ]
    page_two = [
        {
            "full_name": f"{_EXAMPLE_ORG}/page-two",
            "default_branch": "main",
            "clone_url": "https://example.com/two.git",
            "archived": False,
        },
    ]
    client = GitHubRestOrgReposClient(token="fixture-token")  # noqa: S106
    link = '<https://api.github.com/orgs/example-org/repos?page=2>; rel="next"'
    with patch.object(
        client,
        "_get_json",
        side_effect=[
            (page_one, link),
            (page_two, None),
        ],
    ):
        repos = client.list_org_repos(_EXAMPLE_ORG)
    assert len(repos) == _PAGINATED_REPO_COUNT


def test_http_client_refuses_non_get() -> None:
    client = GitHubRestOrgReposClient(token="fixture-token")  # noqa: S106
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        with pytest.raises(HttpMethodRefusedError):
            client.request(method, "https://api.github.com/orgs/example-org/repos")


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


def test_missing_gh_binary(inventory_paths: tuple[Path, Path]) -> None:
    with (
        patch("django_warden_fabric.fleet_inventory.shutil.which", return_value=None),
        pytest.raises(GhBinaryMissingError),
    ):
        GhAuthTokenProvider().token()


def test_missing_gh_login(inventory_paths: tuple[Path, Path]) -> None:
    gh_path = "/usr/bin/gh"
    failed = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="")
    which_patch = "django_warden_fabric.fleet_inventory.shutil.which"
    run_patch = "django_warden_fabric.fleet_inventory.subprocess.run"
    with (
        patch(which_patch, return_value=gh_path),
        patch(run_patch, return_value=failed),
        pytest.raises(GhLoginMissingError),
    ):
        GhAuthTokenProvider().token()


def test_missing_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing = tmp_path / "missing.toml"
    monkeypatch.setenv(ENV_FLEET_TARGET_CONFIG, str(missing))
    with pytest.raises(FleetTargetConfigError) as exc:
        load_organisation_from_config()
    assert "organisation" in str(exc.value).lower()


def test_gitignore_pins_warden_paths() -> None:
    for path in (".warden/fleet-target.toml", ".warden/fleet-inventory.json"):
        result = subprocess.run(  # noqa: S603
            ["git", "check-ignore", "-q", path],  # noqa: S607
            cwd=_REPO_ROOT,
            check=False,
        )
        assert result.returncode == 0, path


def test_leak_guard_skips_when_config_absent() -> None:
    if DEFAULT_FLEET_TARGET_CONFIG.is_file():
        pytest.skip("local .warden/fleet-target.toml present — operator machine only")


@pytest.mark.skipif(
    not DEFAULT_FLEET_TARGET_CONFIG.is_file(),
    reason="local gitignored fleet-target.toml absent (CI)",
)
def test_leak_guard_no_operator_terms_in_tracked_tree() -> None:
    organisation = load_organisation_from_config()
    terms = [organisation.lower()] + [t.lower() for t in load_leak_guard_terms()]
    for root in _LEAK_SCAN_ROOTS:
        if root.is_file():
            paths = [root]
        else:
            paths = [p for p in root.rglob("*") if p.is_file()]
        for path in paths:
            if ".git" in path.parts:
                continue
            rel = (
                path.relative_to(_REPO_ROOT)
                if path.is_relative_to(_REPO_ROOT)
                else path
            )
            tracked = subprocess.run(  # noqa: S603
                ["git", "ls-files", "--error-unmatch", str(rel)],  # noqa: S607
                cwd=_REPO_ROOT,
                check=False,
                capture_output=True,
            )
            if tracked.returncode != 0:
                continue
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            for term in terms:
                assert term not in text, f"{rel} contains forbidden term"


class _SentinelProvider:
    def token(self) -> str:
        return _SENTINEL


@pytest.mark.django_db
def test_sentinel_token_never_persisted_on_success(
    inventory_paths: tuple[Path, Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    _config, export = inventory_paths
    caplog.set_level(logging.DEBUG)
    recording = _recording_client()

    def _client_factory(*, token: str, **kwargs: object) -> RecordingOrgReposClient:
        assert token == _SENTINEL
        return recording

    with (
        patch(
            "django_warden_fabric.tasks.GhAuthTokenProvider",
            _SentinelProvider,
        ),
        patch(
            "pyforge.warden.fleet_github_rest.GitHubRestOrgReposClient",
            _client_factory,
        ),
        override_settings(CELERY_TASK_ALWAYS_EAGER=True),
    ):
        run_fleet_inventory("run-id", _EXAMPLE_ORG)
    assert _SENTINEL not in export.read_text(encoding="utf-8")
    assert _SENTINEL not in caplog.text
    for row in FleetRepo.objects.filter(organisation=_EXAMPLE_ORG):
        blob = f"{row.full_name}{row.clone_url}{row.default_branch}"
        assert _SENTINEL not in blob


@pytest.mark.django_db
def test_sentinel_token_never_persisted_on_failure(
    inventory_paths: tuple[Path, Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    _config, export = inventory_paths
    caplog.set_level(logging.DEBUG)

    class _FailClient:
        def list_org_repos(self, organisation: str) -> list[ListedRepo]:
            msg = "GitHub API HTTP 503"
            raise FleetInventoryError(msg)

    with (
        patch("django_warden_fabric.tasks.GhAuthTokenProvider", _SentinelProvider),
        patch(
            "pyforge.warden.fleet_github_rest.GitHubRestOrgReposClient",
            lambda token: _FailClient(),
        ),
        override_settings(CELERY_TASK_ALWAYS_EAGER=True),
        pytest.raises(FleetInventoryError),
    ):
        run_fleet_inventory("run-id", _EXAMPLE_ORG)
    assert not export.exists()
    assert _SENTINEL not in caplog.text


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_api_failure_leaves_no_export(inventory_paths: tuple[Path, Path]) -> None:
    _config, export = inventory_paths

    class _FailClient:
        def list_org_repos(self, organisation: str) -> list[ListedRepo]:
            msg = "GitHub API HTTP 503"
            raise FleetInventoryError(msg)

    with (
        patch(
            "django_warden_fabric.tasks.GhAuthTokenProvider",
            _SentinelProvider,
        ),
        patch(
            "pyforge.warden.fleet_github_rest.GitHubRestOrgReposClient",
            lambda token: _FailClient(),
        ),
        pytest.raises(FleetInventoryError),
    ):
        run_fleet_inventory("run-id", _EXAMPLE_ORG)
    assert not export.exists()


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
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = tmp_path / "fleet-target.toml"
    export = tmp_path / "fleet-inventory.json"
    config.write_text(f'[github]\norganisation = "{_EXAMPLE_ORG}"\n', encoding="utf-8")
    monkeypatch.setenv(ENV_FLEET_TARGET_CONFIG, str(config))
    monkeypatch.setenv(ENV_FLEET_INVENTORY_PATH, str(export))
    client = _recording_client()
    with (
        patch("django_warden_fabric.tasks.GhAuthTokenProvider", _SentinelProvider),
        patch(
            "pyforge.warden.fleet_github_rest.GitHubRestOrgReposClient",
            lambda token: client,
        ),
    ):
        call_command("warden_fleet_inventory")
    assert export.exists()


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


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
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


def test_atomic_write_leaves_no_partial_on_failure(tmp_path: Path) -> None:
    target = tmp_path / "out.json"
    with (
        patch.object(Path, "replace", side_effect=OSError("disk full")),
        pytest.raises(OSError, match="disk full"),
    ):
        atomic_write_json(target, {"repos": []})
    assert not target.exists()
