"""dlt source for GitHub Projects V2 → `github_metrics`."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterator

import dlt
from pyforge.steward.keys import HostScopedCredential
from pyforge.steward.sync import TransportFn

from .graphql import (
    DEFAULT_PAGE_SIZE,
    ProjectSnapshotPage,
    iter_project_snapshot_pages,
)


def _parse_content(content: object) -> dict[str, object | None]:
    if not isinstance(content, dict):
        return {
            "content_type": None,
            "content_number": None,
            "content_title": None,
            "repository_owner": None,
            "repository_name": None,
        }
    repository = content.get("repository")
    owner_login = None
    repo_name = None
    if isinstance(repository, dict):
        owner = repository.get("owner")
        if isinstance(owner, dict) and isinstance(owner.get("login"), str):
            owner_login = owner["login"]
        if isinstance(repository.get("name"), str):
            repo_name = repository["name"]
    number = content.get("number")
    content_type = None
    if "number" in content and isinstance(number, int):
        content_type = "issue_or_pull_request"
    elif "title" in content:
        content_type = "draft_issue"
    title = content.get("title")
    return {
        "content_type": content_type,
        "content_number": number if isinstance(number, int) else None,
        "content_title": title if isinstance(title, str) else None,
        "repository_owner": owner_login,
        "repository_name": repo_name,
    }


def _flatten_field_values(item: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    item_id = item.get("id")
    if not isinstance(item_id, str):
        return rows
    field_values = item.get("fieldValues") or {}
    nodes = field_values.get("nodes") if isinstance(field_values, dict) else []
    for entry in nodes or []:
        if not isinstance(entry, dict):
            continue
        field = entry.get("field") or {}
        field_id = field.get("id") if isinstance(field, dict) else None
        field_name = field.get("name") if isinstance(field, dict) else None
        text_value = entry.get("text")
        option_value = entry.get("name")
        if field_id is None:
            continue
        rows.append(
            {
                "item_id": item_id,
                "field_id": field_id,
                "field_name": field_name,
                "value_text": text_value if isinstance(text_value, str) else None,
                "value_option_name": option_value if isinstance(option_value, str) else None,
            }
        )
    return rows


def _flatten_fields(project_id: str, fields: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for field in fields:
        field_id = field.get("id")
        if not isinstance(field_id, str):
            continue
        options = field.get("options")
        option_names: list[str] | None = None
        if isinstance(options, list):
            option_names = [
                opt.get("name")
                for opt in options
                if isinstance(opt, dict) and isinstance(opt.get("name"), str)
            ]
        rows.append(
            {
                "project_id": project_id,
                "field_id": field_id,
                "field_name": field.get("name") if isinstance(field.get("name"), str) else None,
                "data_type": field.get("dataType") if isinstance(field.get("dataType"), str) else None,
                "option_names": option_names,
            }
        )
    return rows


def _flatten_items(project_id: str, items: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in items:
        item_id = item.get("id")
        if not isinstance(item_id, str):
            continue
        content_fields = _parse_content(item.get("content"))
        rows.append(
            {
                "id": item_id,
                "project_id": project_id,
                "updated_at": item.get("updatedAt")
                if isinstance(item.get("updatedAt"), str)
                else None,
                **content_fields,
            }
        )
    return rows


@dataclass
class _SnapshotCache:
    pages: list[ProjectSnapshotPage] = field(default_factory=list)
    loaded: bool = False


def _ensure_pages(
    cache: _SnapshotCache,
    project_id: str,
    *,
    credential: HostScopedCredential,
    transport: TransportFn,
    page_size: int,
    max_pages: int | None,
    on_page: Callable[[ProjectSnapshotPage, int], None] | None,
) -> list[ProjectSnapshotPage]:
    if not cache.loaded:
        cache.pages = list(
            iter_project_snapshot_pages(
                project_id,
                credential=credential,
                transport=transport,
                page_size=page_size,
                max_pages=max_pages,
                on_page=on_page,
            )
        )
        cache.loaded = True
    return cache.pages


@dlt.source(name="github_projects")
def github_projects_source(
    project_id: str,
    *,
    credential: HostScopedCredential,
    transport: TransportFn,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_pages: int | None = None,
    on_page: Callable[[ProjectSnapshotPage, int], None] | None = None,
):
    """Custom dlt source — Projects V2 items, fields, and status values."""
    cache = _SnapshotCache()

    @dlt.resource(name="project_v2_fields", write_disposition="replace", primary_key="field_id")
    def project_v2_fields() -> Iterator[dict[str, object]]:
        for page in _ensure_pages(
            cache,
            project_id,
            credential=credential,
            transport=transport,
            page_size=page_size,
            max_pages=max_pages,
            on_page=on_page,
        ):
            yield from _flatten_fields(page.project_id, page.fields)

    @dlt.resource(name="project_v2_items", write_disposition="merge", primary_key="id")
    def project_v2_items() -> Iterator[dict[str, object]]:
        for page in _ensure_pages(
            cache,
            project_id,
            credential=credential,
            transport=transport,
            page_size=page_size,
            max_pages=max_pages,
            on_page=on_page,
        ):
            yield from _flatten_items(page.project_id, page.items)

    @dlt.resource(
        name="project_v2_item_field_values",
        write_disposition="merge",
        primary_key=["item_id", "field_id"],
    )
    def project_v2_item_field_values() -> Iterator[dict[str, object]]:
        for page in _ensure_pages(
            cache,
            project_id,
            credential=credential,
            transport=transport,
            page_size=page_size,
            max_pages=max_pages,
            on_page=on_page,
        ):
            for item in page.items:
                yield from _flatten_field_values(item)

    return project_v2_fields, project_v2_items, project_v2_item_field_values
