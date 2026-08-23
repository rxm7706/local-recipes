"""Story 12.8 — github_metrics dlt ingest tests (mocked GraphQL)."""

from __future__ import annotations

import json

import dlt
import pytest
from pyforge.steward.keys import HostScopedCredential
from pyforge.steward.sync import TransportResponse

from github_projects.graphql import (
    DEFAULT_PAGE_SIZE,
    fetch_project_snapshot_page,
    iter_project_snapshot_pages,
)
from github_projects.pipeline import run_pipeline
from github_projects.source import github_projects_source


def _graphql_response(project_id: str, *, has_next: bool = False) -> bytes:
    payload = {
        "data": {
            "rateLimit": {"cost": 1, "remaining": 4999, "resetAt": "2030-01-01T00:00:00Z"},
            "node": {
                "id": project_id,
                "title": "PyForge Board",
                "fields": {
                    "nodes": [
                        {
                            "id": "FIELD_STATUS",
                            "name": "Status",
                            "dataType": "SINGLE_SELECT",
                            "options": [{"id": "OPT_TODO", "name": "Todo"}],
                        }
                    ]
                },
                "items": {
                    "nodes": [
                        {
                            "id": "ITEM_1",
                            "updatedAt": "2026-08-23T00:00:00Z",
                            "fieldValues": {
                                "nodes": [
                                    {
                                        "name": "In Progress",
                                        "field": {"id": "FIELD_STATUS", "name": "Status"},
                                    },
                                    {
                                        "text": "PROJ-1",
                                        "field": {"id": "FIELD_LINK", "name": "Jira Link"},
                                    },
                                ]
                            },
                            "content": {
                                "number": 42,
                                "title": "Example issue",
                                "repository": {"owner": {"login": "rxm7706"}, "name": "local-recipes"},
                            },
                        }
                    ],
                    "pageInfo": {"hasNextPage": has_next, "endCursor": "CURSOR_1"},
                },
            },
        }
    }
    return json.dumps(payload).encode()


def _fake_transport(project_id: str):
    calls = {"count": 0}

    def transport(request):
        calls["count"] += 1
        body = json.loads(request.data)
        assert body["variables"]["projectId"] == project_id
        page_size = body["variables"].get("pageSize", DEFAULT_PAGE_SIZE)
        assert 1 <= page_size <= DEFAULT_PAGE_SIZE
        return TransportResponse(status=200, body=_graphql_response(project_id, has_next=False))

    transport.calls = calls
    return transport


def test_fetch_project_snapshot_page_parses_fields_and_status():
    credential = HostScopedCredential(hosts=("api.github.com",))
    transport = _fake_transport("PVT_test")

    page = fetch_project_snapshot_page(
        "PVT_test",
        credential=credential,
        transport=transport,
    )

    assert page.project_id == "PVT_test"
    assert page.project_title == "PyForge Board"
    assert len(page.fields) == 1
    assert page.items[0]["id"] == "ITEM_1"
    assert page.rate_limit.remaining == 4999


def test_iter_project_snapshot_pages_stops_on_budget():
    credential = HostScopedCredential(hosts=("api.github.com",))

    def transport(_request):
        return TransportResponse(
            status=200,
            body=_graphql_response("PVT_budget", has_next=True),
        )

    pages = list(
        iter_project_snapshot_pages(
            "PVT_budget",
            credential=credential,
            transport=transport,
            min_remaining_points=5000,
        )
    )
    assert len(pages) == 1


def test_github_projects_source_dry_run_normalizes_three_tables():
    credential = HostScopedCredential(hosts=("api.github.com",))
    transport = _fake_transport("PVT_dry")

    source = github_projects_source(
        "PVT_dry",
        credential=credential,
        transport=transport,
        max_pages=1,
    )
    pipeline = dlt.pipeline(
        pipeline_name="github_projects_metrics_test",
        destination="duckdb",
        dataset_name="github_metrics",
        dev_mode=True,
    )
    pipeline.run(source)

    assert pipeline.last_trace.last_normalize_info.row_counts


def test_run_pipeline_dry_run_does_not_require_postgres(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token_for_dry_run")
    credential = HostScopedCredential(hosts=("api.github.com",))
    transport = _fake_transport("PVT_cli")

    pipeline = run_pipeline(
        "PVT_cli",
        credential=credential,
        transport=transport,
        dry_run=True,
        max_pages=1,
    )
    assert pipeline.dataset_name.startswith("github_metrics")


def test_page_size_out_of_range_rejected():
    credential = HostScopedCredential(hosts=("api.github.com",))
    transport = _fake_transport("PVT_test")
    with pytest.raises(ValueError, match="page_size"):
        fetch_project_snapshot_page(
            "PVT_test",
            credential=credential,
            transport=transport,
            page_size=101,
        )
