"""Story 15.1 `kedro-test` gate -- the injectable Artifactory AQL adapter (CAP-1).

Proves the whole CAP-1 success signal offline against an IN-MEMORY mock transport (no
network, no real Artifactory instance named or contacted): topology resolution then
name+version download aggregation, counts summed across backing repos and duplicate raw
rows, the default transport refuses loudly with no transport injected, and a non-2xx
response raises a clear error. One test per I/O & Edge-Case Matrix row in the story spec."""

from __future__ import annotations

from urllib.parse import urlparse

import pytest

from pyforge.atlas.artifactory import (
    AqlRequest,
    AqlResponse,
    ArtifactoryAqlAdapter,
    ArtifactoryAqlError,
    ArtifactoryConfig,
    ConsumptionRow,
    DownloadRow,
)


class MockArtifactory:
    """An in-memory Artifactory AQL API -- the injected ``transport``. Routes on method + URL
    path, like ``MockWagtail`` in ``tests/factory/test_lasuite.py``. Records every call so a
    test can assert the two round trips (topology, then aggregation) stay separate."""

    def __init__(
        self,
        *,
        topology: dict[str, list[str]],
        download_rows: dict[str, list[dict]] | None = None,
        consumption_rows: dict[str, list[dict]] | None = None,
    ) -> None:
        self.topology = topology
        self.download_rows = download_rows or {}
        self.consumption_rows = consumption_rows or {}
        self.calls: list[tuple[str, str]] = []

    def __call__(self, request: AqlRequest) -> AqlResponse:
        self.calls.append((request.method, request.url))
        full_path = urlparse(request.url).path
        path = full_path.removeprefix("/api")
        if request.method == "GET" and path.startswith("/repositories/"):
            virtual_repo = path.rsplit("/", 1)[-1]
            repos = self.topology.get(virtual_repo)
            if repos is None:
                return AqlResponse(404, {"detail": f"unknown virtual repo {virtual_repo}"})
            return AqlResponse(200, {"repositories": repos})
        if request.method == "POST" and path == "/search/aql":
            virtual_repo = (request.body or {}).get("virtual_repo")
            rows = self.download_rows.get(virtual_repo, [])
            return AqlResponse(200, {"results": rows})
        if request.method == "POST" and path == "/consumption/rollup":
            virtual_repo = (request.body or {}).get("virtual_repo")
            rows = self.consumption_rows.get(virtual_repo, [])
            return AqlResponse(200, {"results": rows})
        return AqlResponse(400, {"detail": f"unrouted {request.method} {path}"})


def _cfg() -> ArtifactoryConfig:
    return ArtifactoryConfig(base_url="https://artifactory.example/")


# --- happy path: topology resolution + name+version aggregation ------------------------


def test_happy_path_resolves_topology_and_aggregates_by_name_and_version():
    mock = MockArtifactory(
        topology={"libs-virtual": ["libs-local", "libs-remote-cache"]},
        download_rows={
            "libs-virtual": [
                {"name": "pkg-a", "version": "1.0", "repo": "libs-local", "count": 10},
                {"name": "pkg-a", "version": "1.0", "repo": "libs-remote-cache", "count": 5},
                {"name": "pkg-a", "version": "2.0", "repo": "libs-local", "count": 3},
                {"name": "pkg-b", "version": "1.0", "repo": "libs-remote-cache", "count": 7},
            ]
        },
    )
    adapter = ArtifactoryAqlAdapter(_cfg(), transport=mock)

    rows = adapter.fetch_download_rows("libs-virtual")

    assert rows == [
        DownloadRow(name="pkg-a", version="1.0", download_count=15),
        DownloadRow(name="pkg-a", version="2.0", download_count=3),
        DownloadRow(name="pkg-b", version="1.0", download_count=7),
    ]
    # topology resolution and download aggregation are two SEPARATE round trips, never one.
    assert [m for m, _ in mock.calls] == ["GET", "POST"]


# --- no transport injected --------------------------------------------------------------


def test_default_transport_refuses_without_injection():
    adapter = ArtifactoryAqlAdapter(_cfg())  # no transport injected

    with pytest.raises(ArtifactoryAqlError) as exc:
        adapter.resolve_backing_repos("libs-virtual")
    msg = str(exc.value)
    assert "no Artifactory transport injected" in msg
    assert "GET" in msg and "libs-virtual" in msg

    with pytest.raises(ArtifactoryAqlError) as exc2:
        adapter.fetch_download_rows("libs-virtual")
    assert "no Artifactory transport injected" in str(exc2.value)


# --- non-2xx response --------------------------------------------------------------------


def test_non_2xx_response_raises_with_status_and_body():
    adapter = ArtifactoryAqlAdapter(_cfg(), transport=lambda req: AqlResponse(500, {"detail": "boom"}))
    with pytest.raises(ArtifactoryAqlError) as exc:
        adapter.resolve_backing_repos("libs-virtual")
    msg = str(exc.value)
    assert "GET" in msg and "500" in msg and "boom" in msg


# --- single backing repo -----------------------------------------------------------------


def test_single_backing_repo_resolves_to_one_element_list():
    mock = MockArtifactory(
        topology={"libs-virtual-single": ["libs-local"]},
        download_rows={"libs-virtual-single": [{"name": "pkg-a", "version": "1.0", "count": 4}]},
    )
    adapter = ArtifactoryAqlAdapter(_cfg(), transport=mock)

    assert adapter.resolve_backing_repos("libs-virtual-single") == ["libs-local"]
    rows = adapter.fetch_download_rows("libs-virtual-single")
    assert rows == [DownloadRow(name="pkg-a", version="1.0", download_count=4)]


# --- mock-only package (no public counterpart) --------------------------------------------


def test_mock_only_package_passes_through_unflagged():
    mock = MockArtifactory(
        topology={"libs-virtual": ["libs-local"]},
        download_rows={"libs-virtual": [{"name": "internal-only-pkg", "version": "9.9", "count": 1}]},
    )
    adapter = ArtifactoryAqlAdapter(_cfg(), transport=mock)

    rows = adapter.fetch_download_rows("libs-virtual")

    # CAP-1 does not classify or flag rows -- a mock-only package flows through into an
    # ordinary DownloadRow exactly like any other package (no exclusion, no special-casing).
    # The internal/private flag itself is Story 15.2's job, not this adapter's.
    assert rows == [DownloadRow(name="internal-only-pkg", version="9.9", download_count=1)]


# --- duplicate name+version rows across backing repos ---------------------------------------


def test_duplicate_name_version_rows_across_repos_sum_into_one_row():
    mock = MockArtifactory(
        topology={"libs-virtual": ["repo-a", "repo-b"]},
        download_rows={
            "libs-virtual": [
                {"name": "dupe-pkg", "version": "1.2.3", "repo": "repo-a", "count": 20},
                {"name": "dupe-pkg", "version": "1.2.3", "repo": "repo-b", "count": 30},
            ]
        },
    )
    adapter = ArtifactoryAqlAdapter(_cfg(), transport=mock)

    rows = adapter.fetch_download_rows("libs-virtual")

    assert rows == [DownloadRow(name="dupe-pkg", version="1.2.3", download_count=50)]


# --- malformed responses raise a clear ArtifactoryAqlError, never a raw KeyError/TypeError ---


def test_malformed_download_row_raises_clear_error():
    mock = MockArtifactory(
        topology={"libs-virtual": ["libs-local"]},
        download_rows={"libs-virtual": [{"name": "pkg-a", "version": "1.0"}]},  # no 'count'
    )
    adapter = ArtifactoryAqlAdapter(_cfg(), transport=mock)

    with pytest.raises(ArtifactoryAqlError) as exc:
        adapter.fetch_download_rows("libs-virtual")
    assert "malformed download row" in str(exc.value)


def test_non_string_backing_repo_entry_raises_clear_error():
    mock = MockArtifactory(
        topology={"libs-virtual": ["libs-local", None]},  # a malformed topology entry
        download_rows={"libs-virtual": []},
    )
    adapter = ArtifactoryAqlAdapter(_cfg(), transport=mock)

    with pytest.raises(ArtifactoryAqlError) as exc:
        adapter.resolve_backing_repos("libs-virtual")
    assert "no valid 'repositories' list" in str(exc.value)


# --- fetch_consumption_rows (Story 23.2) -------------------------------------------------


def test_fetch_consumption_rows_happy_path_resolves_topology_and_aggregates_by_name():
    mock = MockArtifactory(
        topology={"libs-virtual": ["libs-local", "libs-remote-cache"]},
        consumption_rows={
            "libs-virtual": [
                {
                    "name": "pkg-a",
                    "platform_env_count": 10,
                    "internal_app_count": 2,
                    "internal_component_count": 1,
                    "internal_lob_count": 3,
                },
                {
                    "name": "pkg-a",
                    "platform_env_count": 5,
                    "internal_app_count": 1,
                    "internal_component_count": 0,
                    "internal_lob_count": 1,
                },
                {
                    "name": "pkg-b",
                    "platform_env_count": 7,
                    "internal_app_count": 0,
                    "internal_component_count": 2,
                    "internal_lob_count": 0,
                },
            ]
        },
    )
    adapter = ArtifactoryAqlAdapter(_cfg(), transport=mock)

    rows = adapter.fetch_consumption_rows("libs-virtual")

    assert rows == [
        ConsumptionRow(
            name="pkg-a",
            platform_env_count=15,
            internal_app_count=3,
            internal_component_count=1,
            internal_lob_count=4,
        ),
        ConsumptionRow(
            name="pkg-b",
            platform_env_count=7,
            internal_app_count=0,
            internal_component_count=2,
            internal_lob_count=0,
        ),
    ]
    assert [m for m, _ in mock.calls] == ["GET", "POST"]


def test_fetch_consumption_rows_missing_optional_fields_default_to_zero():
    mock = MockArtifactory(
        topology={"libs-virtual": ["libs-local"]},
        consumption_rows={"libs-virtual": [{"name": "pkg-a"}]},
    )
    adapter = ArtifactoryAqlAdapter(_cfg(), transport=mock)

    rows = adapter.fetch_consumption_rows("libs-virtual")

    assert rows == [
        ConsumptionRow(
            name="pkg-a",
            platform_env_count=0,
            internal_app_count=0,
            internal_component_count=0,
            internal_lob_count=0,
        )
    ]


def test_fetch_consumption_rows_malformed_row_raises_clear_error():
    mock = MockArtifactory(
        topology={"libs-virtual": ["libs-local"]},
        consumption_rows={"libs-virtual": [{"platform_env_count": 1}]},  # no 'name'
    )
    adapter = ArtifactoryAqlAdapter(_cfg(), transport=mock)

    with pytest.raises(ArtifactoryAqlError) as exc:
        adapter.fetch_consumption_rows("libs-virtual")
    assert "malformed consumption row" in str(exc.value)


def test_fetch_consumption_rows_reuses_resolve_backing_repos_not_duplicated_in_adapter():
    """Topology resolution is one GET per virtual repo per fetch call."""
    mock = MockArtifactory(
        topology={"libs-virtual": ["libs-local"]},
        consumption_rows={"libs-virtual": [{"name": "pkg-a", "platform_env_count": 1}]},
    )
    adapter = ArtifactoryAqlAdapter(_cfg(), transport=mock)

    adapter.fetch_consumption_rows("libs-virtual")

    assert mock.calls[0][0] == "GET"
    assert "/repositories/libs-virtual" in mock.calls[0][1]
    assert mock.calls[1][0] == "POST"
    assert mock.calls[1][1].endswith("/api/consumption/rollup")
