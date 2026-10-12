"""GitHub Projects (v2) item inventory for the fleet (Story 16.5).

Story 16.1's pieces are reused, never copied: the same gitignored config
(``.warden/fleet-target.toml``, here its ``[github] projects`` list beside
``organisation``), the same ``gh`` credential provider and the same atomic export
writer. The query-only GraphQL client lives in ``pyforge.warden.fleet_github_graphql``
(the platform refuses raw HTTP imports here); this module reads its items
structurally, so the host-side portal can import it without ``pyforge`` installed.

There is no model and no migration: the JSON export is this inventory's one face.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from typing import Protocol

from .fleet_inventory import FleetInventoryError
from .fleet_inventory import FleetTargetConfigError
from .fleet_inventory import _parse_target_toml
from .fleet_inventory import atomic_write_json
from .fleet_inventory import fleet_checkout_root
from .fleet_inventory import resolve_fleet_target_config_path

ENV_FLEET_PROJECT_ITEMS_PATH = "WARDEN_FLEET_PROJECT_ITEMS_PATH"

# Repo-relative default; anchored to the checkout root, never the cwd (as Story 16.1's paths).
DEFAULT_FLEET_PROJECT_ITEMS_PATH = Path(".warden/fleet-project-items.json")

PROJECTS_CONFIG_KEY = "projects"


class FleetProjectItemsRunError(FleetInventoryError):
    """A project-items run failed outside the typed paths (a soft time limit, an I/O error).

    Names only the failure's type: its text, and the frames it passed through, may
    carry the operator's item titles.
    """

    def __init__(self, failure: str) -> None:
        self.failure = failure
        super().__init__(f"fleet project items run failed: {failure}")

    def __reduce__(self) -> tuple[type[FleetProjectItemsRunError], tuple[str]]:
        # Celery stores a task's exception by pickling it: rebuild it from its own part.
        return type(self), (self.failure,)


def resolve_fleet_project_items_export_path() -> Path:
    override = os.environ.get(ENV_FLEET_PROJECT_ITEMS_PATH, "").strip()
    if override:
        return Path(override)
    return fleet_checkout_root() / DEFAULT_FLEET_PROJECT_ITEMS_PATH


def load_project_numbers_from_config(config_path: Path | None = None) -> list[int]:
    """The project numbers under ``[github] projects``, in config order (a typed error if none)."""
    path = config_path if config_path is not None else resolve_fleet_target_config_path()
    if not path.is_file():
        msg = f"missing config; expected [github] {PROJECTS_CONFIG_KEY} key"
        raise FleetTargetConfigError(path, msg)
    document = _parse_target_toml(path.read_bytes(), path)
    github = document.get("github")
    if not isinstance(github, dict):
        msg = "missing [github] table"
        raise FleetTargetConfigError(path, msg)
    projects = github.get(PROJECTS_CONFIG_KEY)
    if not isinstance(projects, list) or not projects:
        msg = f"missing or empty {PROJECTS_CONFIG_KEY} key under [github] (a list of project numbers)"
        raise FleetTargetConfigError(path, msg)
    numbers: list[int] = []
    for position, entry in enumerate(projects, start=1):
        # bool is an int subclass: ``projects = [true]`` is not a project number.
        if not isinstance(entry, int) or isinstance(entry, bool) or entry < 1:
            msg = f"{PROJECTS_CONFIG_KEY} entry {position} is not a positive integer project number"
            raise FleetTargetConfigError(path, msg)
        numbers.append(entry)
    return numbers


class ListedProjectItemFields(Protocol):
    @property
    def project_number(self) -> int: ...
    @property
    def id(self) -> str: ...
    @property
    def content_type(self) -> str: ...
    @property
    def title(self) -> str | None: ...
    @property
    def state(self) -> str | None: ...
    @property
    def repository(self) -> str | None: ...
    @property
    def status(self) -> str | None: ...
    @property
    def updated_at(self) -> str | None: ...


class ProjectItemsListingClient(Protocol):
    def list_projects_items(
        self, organisation: str, project_numbers: Sequence[int]
    ) -> Sequence[ListedProjectItemFields]: ...


def export_document(
    items: Sequence[ListedProjectItemFields],
) -> dict[str, list[dict[str, Any]]]:
    """One entry per (project number, item id), first listing wins; a redacted item is type only."""
    seen: set[tuple[int, str]] = set()
    entries: list[dict[str, Any]] = []
    for item in items:
        key = (item.project_number, item.id)
        if key in seen:
            continue
        seen.add(key)
        entries.append(
            {
                "project_number": item.project_number,
                "id": item.id,
                "content_type": item.content_type,
                "title": item.title,
                "state": item.state,
                "repository": item.repository,
                "status": item.status,
                "updated_at": item.updated_at,
            }
        )
    return {"items": entries}


def run_fleet_project_items_sync(
    *,
    organisation: str,
    project_numbers: Sequence[int],
    listing_client: ProjectItemsListingClient,
    export_path: Path | None = None,
) -> dict[str, Any]:
    """List every designated project's items, then write the export whole and atomically.

    The client returns only after every page of every project is read, so a failure
    anywhere raises before this function writes anything: no partial export.
    """
    items = listing_client.list_projects_items(organisation, project_numbers)
    document = export_document(items)
    destination = export_path if export_path is not None else resolve_fleet_project_items_export_path()
    atomic_write_json(destination, document)
    return document
