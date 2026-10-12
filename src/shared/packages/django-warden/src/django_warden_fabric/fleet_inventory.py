"""GitHub.com organisation repo listing for fleet inventory (Story 16.1).

The listing client (``pyforge.warden.fleet_github_rest``) owns the repo,
skipped-entry and listing types; this module reads them structurally, so the
host-side portal can import it without ``pyforge`` installed.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
import tomllib
import traceback
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from typing import Protocol

logger = logging.getLogger(__name__)

ENV_FLEET_TARGET_CONFIG = "WARDEN_FLEET_TARGET_CONFIG"
ENV_FLEET_INVENTORY_PATH = "WARDEN_FLEET_INVENTORY_PATH"

# Repo-relative defaults; ``resolve_*`` anchors them to the checkout root, never the cwd.
DEFAULT_FLEET_TARGET_CONFIG = Path(".warden/fleet-target.toml")
DEFAULT_FLEET_INVENTORY_PATH = Path(".warden/fleet-inventory.json")

GH_AUTH_TOKEN_TIMEOUT_SECONDS = 30.0

# Story 16.1 (iteration 3, P1): the inventory task's own limits, sized for a whole
# organisation's pagination inside the warden queue's general pool (hard limit 300 s,
# ``CELERY_TASK_TIME_LIMIT``; the global soft limit, 60 s, is too short for pagination).
# Every socket operation times out first, so a stalled response fails as a typed
# ``TimeoutError`` long before Celery's ``SoftTimeLimitExceeded`` could fire inside
# urllib: per request 30 s < soft 240 s < hard 300 s. At 1-2 s a page, 240 s covers
# well over 100 pages (10,000+ repos at 100 a page); ``gh auth token`` has its own 30 s.
FLEET_INVENTORY_REQUEST_TIMEOUT_SECONDS = 30.0
FLEET_INVENTORY_SOFT_TIME_LIMIT_SECONDS = 240
FLEET_INVENTORY_TIME_LIMIT_SECONDS = 300


class FleetInventoryError(Exception):
    """Base error for fleet inventory — never carries a token."""


class GhBinaryMissingError(FleetInventoryError):
    def __init__(self) -> None:
        super().__init__("gh binary not found on PATH")


class GhLoginMissingError(FleetInventoryError):
    def __init__(self) -> None:
        super().__init__(
            "no github.com login in gh (gh auth login --hostname github.com)"
        )


class GhTimeoutError(FleetInventoryError):
    def __init__(self, timeout: float) -> None:
        super().__init__(f"gh auth token did not finish within {timeout:g}s")


class GhTokenUnavailableError(FleetInventoryError):
    def __init__(self, failure: str) -> None:
        super().__init__(f"gh auth token failed: {failure}")


class FleetTargetConfigError(FleetInventoryError):
    def __init__(self, config_path: Path, detail: str) -> None:
        self.config_path = config_path
        super().__init__(f"{config_path}: {detail}")


def fleet_checkout_root() -> Path:
    """The checkout this module runs from: its nearest ancestor holding ``.git``.

    A worktree's ``.git`` is a file, so a worktree anchors to itself. Outside a
    checkout (a container image) there is none, and the cwd stands in; set
    ``WARDEN_FLEET_TARGET_CONFIG`` and ``WARDEN_FLEET_INVENTORY_PATH`` there.
    """
    for candidate in Path(__file__).resolve().parents:
        if (candidate / ".git").exists():
            return candidate
    return Path.cwd()


def resolve_fleet_target_config_path() -> Path:
    override = os.environ.get(ENV_FLEET_TARGET_CONFIG, "").strip()
    if override:
        return Path(override)
    return fleet_checkout_root() / DEFAULT_FLEET_TARGET_CONFIG


def resolve_fleet_inventory_export_path() -> Path:
    override = os.environ.get(ENV_FLEET_INVENTORY_PATH, "").strip()
    if override:
        return Path(override)
    return fleet_checkout_root() / DEFAULT_FLEET_INVENTORY_PATH


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
    path = (
        config_path if config_path is not None else resolve_fleet_target_config_path()
    )
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
    path = (
        config_path if config_path is not None else resolve_fleet_target_config_path()
    )
    if not path.is_file():
        return []
    document = _parse_target_toml(path.read_bytes(), path)
    github = document.get("github")
    if not isinstance(github, dict):
        return []
    terms = github.get("leak_guard_terms")
    if terms is None:
        return []
    if not isinstance(terms, list) or not all(isinstance(item, str) for item in terms):
        # A bare string would otherwise be ignored and the guard would run without it.
        msg = "leak_guard_terms under [github] must be a list of strings"
        raise FleetTargetConfigError(path, msg)
    return [item for item in terms if item.strip()]


class CredentialProvider(Protocol):
    def token(self) -> str: ...


class GhRunner(Protocol):
    def __call__(
        self, argv: list[str], *, timeout: float
    ) -> subprocess.CompletedProcess[str]: ...


def _run_gh(argv: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
    """The one place ``gh`` runs: an argv list, no shell, a timeout (tests replace it)."""
    return subprocess.run(  # noqa: S603
        argv,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class GhAuthTokenProvider:
    """Read the operator's github.com token via ``gh auth token`` (no shell)."""

    def __init__(
        self,
        *,
        hostname: str = "github.com",
        runner: GhRunner | None = None,
        timeout: float = GH_AUTH_TOKEN_TIMEOUT_SECONDS,
    ) -> None:
        self._hostname = hostname
        self._runner = runner
        self._timeout = timeout

    def token(self) -> str:
        gh = shutil.which("gh")
        if gh is None:
            raise GhBinaryMissingError
        argv = [gh, "auth", "token", "--hostname", self._hostname]
        run = self._runner if self._runner is not None else _run_gh
        # Every failure is typed ``from None`` with its frames' locals cleared: the
        # subprocess frames may hold partial stdout (a token) when they fail.
        try:
            completed = run(argv, timeout=self._timeout)
        except subprocess.TimeoutExpired as exc:
            exc.output = exc.stderr = None
            traceback.clear_frames(exc.__traceback__)
            raise GhTimeoutError(self._timeout) from None
        except Exception as exc:
            failure = type(exc).__name__
            traceback.clear_frames(exc.__traceback__)
            raise GhTokenUnavailableError(failure) from None
        except BaseException as exc:
            traceback.clear_frames(exc.__traceback__)
            raise
        value = completed.stdout.strip() if completed.returncode == 0 else ""
        # Drop the process result before any raise: a logged traceback renders locals.
        del completed
        if not value:
            raise GhLoginMissingError
        return value


class ListedRepoFields(Protocol):
    @property
    def full_name(self) -> str: ...
    @property
    def default_branch(self) -> str: ...
    @property
    def clone_url(self) -> str: ...
    @property
    def archived(self) -> bool: ...


class SkippedEntryFields(Protocol):
    @property
    def page(self) -> int: ...
    @property
    def position(self) -> int: ...
    @property
    def full_name(self) -> str | None: ...
    @property
    def reason(self) -> str: ...


class OrgReposListingFields(Protocol):
    @property
    def repos(self) -> Sequence[ListedRepoFields]: ...
    @property
    def skipped(self) -> Sequence[SkippedEntryFields]: ...


class OrgReposListingClient(Protocol):
    def list_org_repos(self, organisation: str) -> OrgReposListingFields: ...


def export_document(listing: OrgReposListingFields) -> dict[str, list[dict[str, Any]]]:
    return {
        "repos": [
            {
                "full_name": repo.full_name,
                "default_branch": repo.default_branch,
                "clone_url": repo.clone_url,
                "archived": repo.archived,
            }
            for repo in listing.repos
        ],
        "skipped": [
            {
                "page": entry.page,
                "position": entry.position,
                "full_name": entry.full_name,
                "reason": entry.reason,
            }
            for entry in listing.skipped
        ],
    }


def atomic_write_json(path: Path, document: dict[str, Any]) -> None:
    """Write ``document`` through a uniquely named temp file beside ``path``, then rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(document, indent=2, sort_keys=True) + "\n"
    descriptor, name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    tmp = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(data)
        tmp.replace(path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def persist_fleet_repos(
    *, organisation: str, repos: Sequence[ListedRepoFields]
) -> None:
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
    """List repos, upsert ``FleetRepo`` rows, write the export atomically.

    Entries the listing could not inventory are never upserted; the export
    names each one under ``skipped`` with its reason.
    """
    listing = listing_client.list_org_repos(organisation)
    persist_fleet_repos(organisation=organisation, repos=listing.repos)
    document = export_document(listing)
    if listing.skipped:
        logger.warning(
            "fleet inventory skipped %d incomplete listing entries (see the export)",
            len(listing.skipped),
        )
    destination = (
        export_path
        if export_path is not None
        else resolve_fleet_inventory_export_path()
    )
    atomic_write_json(destination, document)
    return document
