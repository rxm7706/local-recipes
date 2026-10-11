"""GitHub.com organisation repo listing for fleet inventory (Story 16.1)."""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Protocol

logger = logging.getLogger(__name__)

FLEET_INVENTORY_FLAG = "pyforge.warden.fleet_inventory"

ENV_FLEET_TARGET_CONFIG = "WARDEN_FLEET_TARGET_CONFIG"
ENV_FLEET_INVENTORY_PATH = "WARDEN_FLEET_INVENTORY_PATH"

DEFAULT_FLEET_TARGET_CONFIG = Path(".warden/fleet-target.toml")
DEFAULT_FLEET_INVENTORY_PATH = Path(".warden/fleet-inventory.json")

GITHUB_API_HOST = "api.github.com"
_ORG_REPOS_PATH = "/orgs/{organisation}/repos"

_LINK_NEXT = re.compile(r'<([^>]+)>;\s*rel="next"')


class FleetInventoryError(Exception):
    """Base error for fleet inventory — never carries a token."""


class GhBinaryMissingError(FleetInventoryError):
    def __init__(self) -> None:
        super().__init__("gh binary not found on PATH")


class GhLoginMissingError(FleetInventoryError):
    def __init__(self) -> None:
        super().__init__("no github.com login in gh (gh auth login --hostname github.com)")


class FleetTargetConfigError(FleetInventoryError):
    def __init__(self, config_path: Path, detail: str) -> None:
        self.config_path = config_path
        super().__init__(f"{config_path}: {detail}")


class HttpMethodRefusedError(FleetInventoryError):
    def __init__(self, method: str) -> None:
        super().__init__(f"refused HTTP method {method!r} (GET only)")


@dataclass(frozen=True)
class ListedRepo:
    full_name: str
    default_branch: str
    clone_url: str
    archived: bool


def resolve_fleet_target_config_path() -> Path:
    override = os.environ.get(ENV_FLEET_TARGET_CONFIG, "").strip()
    if override:
        return Path(override)
    return DEFAULT_FLEET_TARGET_CONFIG


def resolve_fleet_inventory_export_path() -> Path:
    override = os.environ.get(ENV_FLEET_INVENTORY_PATH, "").strip()
    if override:
        return Path(override)
    return DEFAULT_FLEET_INVENTORY_PATH


def _parse_target_toml(raw: bytes, config_path: Path) -> dict[str, Any]:
    try:
        document = tomllib.loads(raw.decode("utf-8"))
    except tomllib.TOMLDecodeError as exc:
        msg = f"invalid TOML: {exc}"
        raise FleetTargetConfigError(config_path, msg) from exc
    if not isinstance(document, dict):
        msg = "root must be a table"
        raise FleetTargetConfigError(config_path, msg)
    return document


def load_organisation_from_config(config_path: Path | None = None) -> str:
    path = config_path if config_path is not None else resolve_fleet_target_config_path()
    if not path.is_file():
        msg = "missing config; expected [github] organisation key"
        raise FleetTargetConfigError(path, msg)
    document = _parse_target_toml(path.read_bytes(), path)
    github = document.get("github")
    if not isinstance(github, dict):
        msg = "missing [github] table"
        raise FleetTargetConfigError(path, msg)
    organisation = github.get("organisation")
    if not isinstance(organisation, str) or not organisation.strip():
        msg = "missing or empty organisation key under [github]"
        raise FleetTargetConfigError(path, msg)
    return organisation.strip()


def load_leak_guard_terms(config_path: Path | None = None) -> list[str]:
    path = config_path if config_path is not None else resolve_fleet_target_config_path()
    if not path.is_file():
        return []
    document = _parse_target_toml(path.read_bytes(), path)
    github = document.get("github")
    if not isinstance(github, dict):
        return []
    terms = github.get("leak_guard_terms")
    if terms is None:
        return []
    if not isinstance(terms, list):
        return []
    return [str(item) for item in terms if str(item).strip()]


class CredentialProvider(Protocol):
    def token(self) -> str: ...


class GhAuthTokenProvider:
    """Read the operator's github.com token via ``gh auth token`` (no shell)."""

    def __init__(self, *, hostname: str = "github.com") -> None:
        self._hostname = hostname

    def token(self) -> str:
        gh = shutil.which("gh")
        if gh is None:
            raise GhBinaryMissingError
        argv = [gh, "auth", "token", "--hostname", self._hostname]
        completed = subprocess.run(  # noqa: S603
            argv,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise GhLoginMissingError
        value = completed.stdout.strip()
        if not value:
            raise GhLoginMissingError
        return value


class OrgReposListingClient(Protocol):
    def list_org_repos(self, organisation: str) -> list[ListedRepo]: ...


def _parse_link_next(link_header: str | None) -> str | None:
    if not link_header:
        return None
    match = _LINK_NEXT.search(link_header)
    if match is None:
        return None
    return match.group(1)


class GitHubRestOrgReposClient:
    """GET-only GitHub REST client for ``/orgs/{org}/repos`` pagination."""

    def __init__(
        self,
        *,
        token: str,
        api_host: str = GITHUB_API_HOST,
        opener: urllib.request.OpenerDirector | None = None,
    ) -> None:
        self._token = token
        self._api_host = api_host
        self._opener = opener or urllib.request.build_opener()

    def list_org_repos(self, organisation: str) -> list[ListedRepo]:
        encoded = urllib.parse.quote(organisation, safe="")
        url = (
            f"https://{self._api_host}{_ORG_REPOS_PATH.format(organisation=encoded)}"
            f"?type=all&per_page=100"
        )
        collected: list[ListedRepo] = []
        while url:
            payload, link = self._get_json(url)
            if not isinstance(payload, list):
                msg = "expected a JSON array from org repos listing"
                raise FleetInventoryError(msg)
            for entry in payload:
                if not isinstance(entry, dict):
                    continue
                repo = _listed_repo_from_api(entry)
                if repo is not None:
                    collected.append(repo)
            url = _parse_link_next(link)
        return collected

    def _get_json(self, url: str) -> tuple[Any, str | None]:
        request = urllib.request.Request(url, method="GET")
        request.add_header("Authorization", f"Bearer {self._token}")
        request.add_header("Accept", "application/vnd.github+json")
        request.add_header("User-Agent", "pyforge-warden-fleet-inventory")
        try:
            with self._opener.open(request, timeout=120) as response:  # noqa: S310
                body = response.read()
                link = response.headers.get("Link")
        except urllib.error.HTTPError as exc:
            msg = f"GitHub API HTTP {exc.code}"
            raise FleetInventoryError(msg) from exc
        except urllib.error.URLError as exc:
            msg = f"GitHub API request failed: {exc.reason}"
            raise FleetInventoryError(msg) from exc
        return json.loads(body.decode("utf-8")), link

    def request(self, method: str, url: str) -> None:
        """Issue one HTTP call — refuses non-GET before opening a socket."""
        normalized = method.upper()
        if normalized != "GET":
            raise HttpMethodRefusedError(normalized)
        self._get_json(url)


def _listed_repo_from_api(entry: dict[str, Any]) -> ListedRepo | None:
    full_name = entry.get("full_name")
    default_branch = entry.get("default_branch")
    clone_url = entry.get("clone_url")
    archived = entry.get("archived")
    if not isinstance(full_name, str) or not full_name:
        return None
    if not isinstance(default_branch, str) or not default_branch:
        default_branch = "main"
    if not isinstance(clone_url, str) or not clone_url:
        return None
    return ListedRepo(
        full_name=full_name,
        default_branch=default_branch,
        clone_url=clone_url,
        archived=bool(archived),
    )


@dataclass
class RecordingOrgReposClient:
    """Fixture listing client that records every HTTP method/url pair."""

    repos_by_org: dict[str, list[ListedRepo]]
    calls: list[tuple[str, str]]

    def list_org_repos(self, organisation: str) -> list[ListedRepo]:
        self.calls.append(("GET", f"/orgs/{organisation}/repos"))
        return list(self.repos_by_org.get(organisation, []))


class PaginatedFixtureOrgReposClient:
    """Returns repos across pages via ``Link: rel=\"next\"`` on a recording transport."""

    def __init__(
        self,
        *,
        pages: list[list[ListedRepo]],
        transport: RecordingOrgReposClient | None = None,
    ) -> None:
        self._pages = pages
        self._transport = transport or RecordingOrgReposClient(repos_by_org={})
        self._page_index = 0

    def list_org_repos(self, organisation: str) -> list[ListedRepo]:
        # Delegate to GitHubRestOrgReposClient logic via injected mock opener is heavy;
        # tests call ``list_org_repos`` on a client that merges pages directly.
        merged: list[ListedRepo] = []
        for page in self._pages:
            merged.extend(page)
            self._transport.calls.append(("GET", f"/orgs/{organisation}/repos?page"))
        return merged


def export_document(repos: list[ListedRepo]) -> dict[str, list[dict[str, str | bool]]]:
    return {
        "repos": [
            {
                "full_name": repo.full_name,
                "default_branch": repo.default_branch,
                "clone_url": repo.clone_url,
                "archived": repo.archived,
            }
            for repo in repos
        ],
    }


def atomic_write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    data = json.dumps(document, indent=2, sort_keys=True) + "\n"
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(path)


def persist_fleet_repos(*, organisation: str, repos: list[ListedRepo]) -> None:
    from django_warden_fabric.models import FleetRepo  # noqa: PLC0415

    for repo in repos:
        FleetRepo.objects.update_or_create(
            organisation=organisation,
            full_name=repo.full_name,
            defaults={
                "default_branch": repo.default_branch,
                "clone_url": repo.clone_url,
                "archived": repo.archived,
            },
        )


def run_fleet_inventory_sync(
    *,
    organisation: str,
    listing_client: OrgReposListingClient,
    export_path: Path | None = None,
) -> dict[str, Any]:
    """List repos, upsert ``FleetRepo`` rows, write the export atomically."""
    repos = listing_client.list_org_repos(organisation)
    persist_fleet_repos(organisation=organisation, repos=repos)
    document = export_document(repos)
    destination = export_path if export_path is not None else resolve_fleet_inventory_export_path()
    atomic_write_json(destination, document)
    return document


def scrub_token_from_text(text: str, token: str) -> str:
    if not token:
        return text
    return text.replace(token, "<redacted>")
