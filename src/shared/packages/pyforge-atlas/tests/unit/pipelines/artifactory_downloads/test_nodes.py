"""``artifactory_downloads`` pipeline node unit tests (Story 15.3, CAP-4; Epic 15).

Hand-built ``pd.DataFrame`` fixtures, no catalog -- mirrors
``tests/pipelines/upstream_discovery/test_nodes.py``'s style. One test per I/O &
Edge-Case Matrix row in the story spec, plus a test proving the exported TSV row/header
content matches ``export_purls.py::mapped_tsv_lines``'s shape exactly for a resolved row.

The mock transport shape (routes on method + URL path, records calls) mirrors
``tests/artifactory/test_aql_adapter.py``'s ``MockArtifactory``.
"""

from __future__ import annotations

from urllib.parse import urlparse

import pandas as pd
import pytest

from pyforge.atlas.artifactory import AqlRequest, AqlResponse
from pyforge.atlas.pipelines.artifactory_downloads import nodes as N


class MockArtifactory:
    """An in-memory Artifactory AQL API -- the injected ``transport`` (test-only, never
    present in the committed ``conf/base/parameters.yml``). Routes on method + URL path,
    like ``tests/artifactory/test_aql_adapter.py``'s ``MockArtifactory``."""

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
        path = urlparse(request.url).path.removeprefix("/api")
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


# ---------------------------------------------------------------------------
# fetch_artifactory_downloads -- I/O Matrix row 1: default (no repos configured)
# ---------------------------------------------------------------------------


def _boom(*args, **kwargs):
    raise AssertionError("ArtifactoryConfig/ArtifactoryAqlAdapter must not be constructed")


def test_default_empty_virtual_repos_returns_empty_frame_with_no_construction(monkeypatch):
    """The committed default (``params:artifactory.virtual_repos: []``): the fetch node
    must construct ZERO ``ArtifactoryConfig``/``ArtifactoryAqlAdapter`` -- no live
    instance is named, selected, or contacted anywhere in the default run path. Patched
    to raise on construction so any regression fails loudly rather than silently."""
    monkeypatch.setattr(N, "ArtifactoryConfig", _boom)
    monkeypatch.setattr(N, "ArtifactoryAqlAdapter", _boom)

    result = N.fetch_artifactory_downloads({"virtual_repos": []})

    assert list(result.columns) == ["name", "version", "download_count"]
    assert result.empty


def test_missing_virtual_repos_key_also_short_circuits(monkeypatch):
    monkeypatch.setattr(N, "ArtifactoryConfig", _boom)
    monkeypatch.setattr(N, "ArtifactoryAqlAdapter", _boom)
    assert N.fetch_artifactory_downloads({}).empty
    assert N.fetch_artifactory_downloads(None).empty


def test_non_list_virtual_repos_raises_clear_error():
    """A bare string is truthy and iterable -- without a type guard it would silently
    iterate per-character, issuing bogus per-character AQL calls."""
    with pytest.raises(ValueError, match="must be a list"):
        N.fetch_artifactory_downloads({"virtual_repos": "repo-a"})


def test_explicit_null_base_url_does_not_pass_none_through():
    """``base_url: null`` (key present, value ``None``) must fall back to ``''`` just like
    an absent key -- ``dict.get(key, default)`` only applies its default when the key is
    ABSENT, so this needs the same ``or`` fallback ``virtual_repos`` already uses."""
    captured = {}
    real_config = N.ArtifactoryConfig

    def _spy_config(*, base_url):
        captured["base_url"] = base_url
        return real_config(base_url=base_url)

    mock = MockArtifactory(topology={"repo-a": ["repo-a-local"]}, download_rows={"repo-a": []})
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(N, "ArtifactoryConfig", _spy_config)
        result = N.fetch_artifactory_downloads({"virtual_repos": ["repo-a"], "base_url": None, "transport": mock})

    assert captured["base_url"] == ""
    assert result.empty
    assert list(result.columns) == ["name", "version", "download_count"]


# ---------------------------------------------------------------------------
# fetch_artifactory_downloads -- I/O Matrix row 2: configured repos, injected transport
# ---------------------------------------------------------------------------


def test_configured_repos_with_injected_transport_aggregates_across_repos():
    mock = MockArtifactory(
        topology={"repo-a": ["repo-a-local"], "repo-b": ["repo-b-local"]},
        download_rows={
            "repo-a": [{"name": "pkg-a", "version": "1.0", "count": 10}],
            "repo-b": [{"name": "pkg-a", "version": "1.0", "count": 5}],
        },
    )

    result = N.fetch_artifactory_downloads({"virtual_repos": ["repo-a", "repo-b"], "transport": mock})

    assert list(result.columns) == ["name", "version", "download_count"]
    # summed ACROSS repos -- 10 + 5 = 15 -- matching Story 15.1's own within-repo
    # aggregation extended across the fetch node's per-virtual-repo loop.
    assert result.to_dict("records") == [{"name": "pkg-a", "version": "1.0", "download_count": 15}]
    # two separate repos -> two separate topology+aggregation round trips each.
    assert len(mock.calls) == 4  # (GET+POST) x 2 virtual repos
    assert [m for m, _ in mock.calls] == ["GET", "POST", "GET", "POST"]


def test_single_repo_with_injected_transport_passes_rows_through():
    mock = MockArtifactory(
        topology={"repo-a": ["repo-a-local"]},
        download_rows={
            "repo-a": [
                {"name": "pkg-a", "version": "1.0", "count": 10},
                {"name": "pkg-b", "version": "2.0", "count": 3},
            ]
        },
    )

    result = N.fetch_artifactory_downloads({"virtual_repos": ["repo-a"], "transport": mock})

    assert sorted(result.to_dict("records"), key=lambda r: r["name"]) == [
        {"name": "pkg-a", "version": "1.0", "download_count": 10},
        {"name": "pkg-b", "version": "2.0", "download_count": 3},
    ]


# ---------------------------------------------------------------------------
# join_artifactory_identity -- thin DataFrame<->dataclass adapter over join_identity
# ---------------------------------------------------------------------------


def _raw(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=N._RAW_COLS)


def test_join_artifactory_identity_resolves_conda_name_and_flags_internal():
    raw = _raw(
        [
            {"name": "requests", "version": "2.31.0", "download_count": 100},
            {"name": "acme-internal-tool", "version": "1.0.0", "download_count": 5},
        ]
    )
    mapping = pd.DataFrame({"pypi_name": ["requests"], "conda_name": ["requests"], "match_source": ["parselmouth"]})
    universe = pd.DataFrame({"pypi_name": ["requests"]})

    result = N.join_artifactory_identity(raw, mapping, universe)

    assert list(result.columns) == N._JOINED_COLS
    records = result.to_dict("records")
    assert records[0] == {
        "pypi_name": "requests",
        "version": "2.31.0",
        "download_count": 100,
        "conda_name": "requests",
        "match_source": "parselmouth",
        "is_internal": False,
    }
    assert records[1]["conda_name"] is None
    assert records[1]["is_internal"] is True


def test_join_artifactory_identity_empty_raw_returns_empty_joined_schema():
    result = N.join_artifactory_identity(_raw([]), pd.DataFrame(), pd.DataFrame())
    assert result.empty
    assert list(result.columns) == N._JOINED_COLS


def test_join_artifactory_identity_malformed_raw_degrades_to_empty_schema():
    malformed = pd.DataFrame({"name": ["pkg-a"]})  # missing version/download_count
    result = N.join_artifactory_identity(malformed, pd.DataFrame(), pd.DataFrame())
    assert result.empty
    assert list(result.columns) == N._JOINED_COLS


def test_join_artifactory_identity_skips_rows_with_nan_download_count():
    """A ``NaN`` ``download_count`` cell (columns present, value missing) must be
    SKIPPED, not crash ``int(nan)`` -- the docstring's "never raises" claim covers
    value-level malformation, not just missing columns."""
    raw = _raw(
        [
            {"name": "requests", "version": "2.31.0", "download_count": float("nan")},
            {"name": "good-pkg", "version": "1.0.0", "download_count": 7},
        ]
    )
    result = N.join_artifactory_identity(raw, pd.DataFrame(), pd.DataFrame())
    assert result.to_dict("records") == [
        {
            "pypi_name": "good-pkg",
            "version": "1.0.0",
            "download_count": 7,
            "conda_name": None,
            "match_source": None,
            "is_internal": False,
        }
    ]


def test_join_artifactory_identity_skips_rows_with_missing_name_or_version():
    raw = _raw(
        [
            {"name": None, "version": "1.0", "download_count": 1},
            {"name": "pkg-a", "version": float("nan"), "download_count": 2},
            {"name": "good-pkg", "version": "1.0.0", "download_count": 7},
        ]
    )
    result = N.join_artifactory_identity(raw, pd.DataFrame(), pd.DataFrame())
    assert result.to_dict("records") == [
        {
            "pypi_name": "good-pkg",
            "version": "1.0.0",
            "download_count": 7,
            "conda_name": None,
            "match_source": None,
            "is_internal": False,
        }
    ]


# ---------------------------------------------------------------------------
# format_artifactory_purl_export -- I/O Matrix rows 3 + 4
# ---------------------------------------------------------------------------


def _joined(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=N._JOINED_COLS)


def test_mixed_joined_rows_export_only_the_resolved_row():
    joined = _joined(
        [
            {
                "pypi_name": "requests",
                "version": "2.31.0",
                "download_count": 100,
                "conda_name": "requests",
                "match_source": "parselmouth",
                "is_internal": False,
            },
            {
                "pypi_name": "acme-internal-tool",
                "version": "1.0.0",
                "download_count": 5,
                "conda_name": None,
                "match_source": None,
                "is_internal": True,
            },
        ]
    )

    result = N.format_artifactory_purl_export(joined)

    assert result == {
        "artifactory_downloads.tsv": (
            "conda_purl\tpypi_purl\tmatch_source\tmatch_confidence\n"
            "pkg:conda/requests?channel=conda-forge\tpkg:pypi/requests\tparselmouth\t\n"
        )
    }


def test_empty_joined_dataframe_yields_header_only():
    result = N.format_artifactory_purl_export(_joined([]))
    assert result == {"artifactory_downloads.tsv": "conda_purl\tpypi_purl\tmatch_source\tmatch_confidence\n"}


def test_none_joined_dataframe_yields_header_only():
    result = N.format_artifactory_purl_export(None)
    assert result == {"artifactory_downloads.tsv": "conda_purl\tpypi_purl\tmatch_source\tmatch_confidence\n"}


def test_export_matches_export_purls_mapped_tsv_shape_byte_for_byte():
    """Proves the exported row/header shape matches
    ``export_purls.py::MAPPED_TSV_HEADER``/``mapped_tsv_lines``/``g98_pypi_name`` exactly
    for a resolved row -- lowercase + ``_``->``-`` with dots PRESERVED (G98), the
    ``?channel=conda-forge`` qualifier, tab-separated, and a blank trailing
    ``match_confidence`` field (this data source never carried a confidence column)."""
    joined = _joined(
        [
            {
                "pypi_name": "Foo_Bar.Baz",
                "version": "1.2.3",
                "download_count": 42,
                "conda_name": "cool-pkg",
                "match_source": "g10_spelling",
                "is_internal": False,
            }
        ]
    )

    result = N.format_artifactory_purl_export(joined)

    # hand-replicated from export_purls.py's own rules (g98_pypi_name: lower + `_`->`-`,
    # dots preserved; CHANNEL_QUALIFIER; MAPPED_TSV_HEADER) -- not imported, since that
    # module lives in a completely separate tree, `.claude/skills/conda-forge-expert/scripts/`.
    expected_header = "conda_purl\tpypi_purl\tmatch_source\tmatch_confidence"
    expected_row = "pkg:conda/cool-pkg?channel=conda-forge\tpkg:pypi/foo-bar.baz\tg10_spelling\t"
    assert result == {"artifactory_downloads.tsv": f"{expected_header}\n{expected_row}\n"}


def test_g98_pypi_name_preserves_dots_and_folds_underscores():
    assert N.g98_pypi_name("Foo_Bar.Baz") == "foo-bar.baz"
    assert N.g98_pypi_name("already-normal") == "already-normal"


@pytest.mark.parametrize("bad_conda_name", [None, float("nan")])
def test_missing_conda_name_variants_are_excluded(bad_conda_name):
    joined = _joined(
        [
            {
                "pypi_name": "some-pkg",
                "version": "1.0",
                "download_count": 1,
                "conda_name": bad_conda_name,
                "match_source": None,
                "is_internal": True,
            }
        ]
    )
    result = N.format_artifactory_purl_export(joined)
    assert result == {"artifactory_downloads.tsv": "conda_purl\tpypi_purl\tmatch_source\tmatch_confidence\n"}


# ---------------------------------------------------------------------------
# project_artifactory_names -- Story 21.5, Tier 2 (names-only, not telemetry)
# ---------------------------------------------------------------------------


def test_project_artifactory_names_default_empty_input_is_empty_but_correctly_columned():
    """params:artifactory.virtual_repos stays [] (the committed default) ->
    artifactory_downloads_joined is empty -> enterprise_jfrog_names is
    empty-but-correctly-columned, no live call made."""
    out = N.project_artifactory_names(_joined([]))
    assert out.empty
    assert list(out.columns) == ["pypi_name", "conda_name", "is_internal"]


def test_project_artifactory_names_selects_only_the_three_identity_columns():
    joined = _joined(
        [
            {
                "pypi_name": "requests",
                "version": "2.31.0",
                "download_count": 999,
                "conda_name": "requests",
                "match_source": "g10_spelling",
                "is_internal": False,
            }
        ]
    )
    out = N.project_artifactory_names(joined)
    assert list(out.columns) == ["pypi_name", "conda_name", "is_internal"]
    assert "download_count" not in out.columns
    assert "version" not in out.columns
    assert "match_source" not in out.columns
    row = out.iloc[0]
    assert row["pypi_name"] == "requests"
    assert row["conda_name"] == "requests"
    assert bool(row["is_internal"]) is False


def test_project_artifactory_names_dedupes_distinct_pypi_conda_pairs():
    joined = _joined(
        [
            {
                "pypi_name": "foo",
                "version": "1.0",
                "download_count": 1,
                "conda_name": "foo",
                "match_source": "x",
                "is_internal": False,
            },
            {
                "pypi_name": "foo",
                "version": "2.0",
                "download_count": 2,
                "conda_name": "foo",
                "match_source": "x",
                "is_internal": False,
            },
            {
                "pypi_name": "bar",
                "version": "1.0",
                "download_count": 3,
                "conda_name": None,
                "match_source": None,
                "is_internal": True,
            },
        ]
    )
    out = N.project_artifactory_names(joined)
    assert len(out) == 2
    pairs = set(zip(out["pypi_name"], out["conda_name"].apply(lambda v: v if isinstance(v, str) else None)))
    assert pairs == {("foo", "foo"), ("bar", None)}


def test_project_artifactory_names_includes_internal_only_rows():
    """A mock-only (internal) package with no resolved conda_name still carries its
    is_internal flag through -- this projection is names-only, not "resolved only"
    (unlike format_artifactory_purl_export, which excludes unresolved rows)."""
    joined = _joined(
        [
            {
                "pypi_name": "internal-pkg",
                "version": "1.0",
                "download_count": 5,
                "conda_name": None,
                "match_source": None,
                "is_internal": True,
            },
        ]
    )
    out = N.project_artifactory_names(joined)
    assert len(out) == 1
    assert out.iloc[0]["pypi_name"] == "internal-pkg"
    assert bool(out.iloc[0]["is_internal"]) is True


def test_project_artifactory_names_none_input_never_raises():
    out = N.project_artifactory_names(None)
    assert out.empty
    assert list(out.columns) == ["pypi_name", "conda_name", "is_internal"]


def test_project_artifactory_names_malformed_input_missing_columns_degrades_to_empty():
    out = N.project_artifactory_names(pd.DataFrame({"pypi_name": ["x"]}))
    assert out.empty
    assert list(out.columns) == ["pypi_name", "conda_name", "is_internal"]


# ---------------------------------------------------------------------------
# fetch_artifactory_consumption + build_enterprise_jfrog_consumption (Story 23.2)
# ---------------------------------------------------------------------------


def test_fetch_artifactory_consumption_empty_virtual_repos_short_circuits(monkeypatch):
    monkeypatch.setattr(N, "ArtifactoryConfig", _boom)
    monkeypatch.setattr(N, "ArtifactoryAqlAdapter", _boom)

    result = N.fetch_artifactory_consumption({"virtual_repos": []})

    assert list(result.columns) == N._CONSUMPTION_COLS
    assert result.empty


def test_fetch_artifactory_consumption_non_list_virtual_repos_raises():
    with pytest.raises(ValueError, match="must be a list"):
        N.fetch_artifactory_consumption({"virtual_repos": "repo-a"})


def test_fetch_artifactory_consumption_sums_across_virtual_repos():
    mock = MockArtifactory(
        topology={"repo-a": ["repo-a-local"], "repo-b": ["repo-b-local"]},
        consumption_rows={
            "repo-a": [{"name": "pkg-a", "platform_env_count": 10, "internal_app_count": 1}],
            "repo-b": [{"name": "pkg-a", "platform_env_count": 5, "internal_app_count": 2}],
        },
    )

    result = N.fetch_artifactory_consumption({"virtual_repos": ["repo-a", "repo-b"], "transport": mock})

    assert result.to_dict("records") == [
        {
            "name": "pkg-a",
            "platform_env_count": 15,
            "internal_app_count": 3,
            "internal_component_count": 0,
            "internal_lob_count": 0,
        }
    ]


def _consumption(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=N._CONSUMPTION_COLS)


def test_build_enterprise_jfrog_consumption_happy_path_outer_join():
    joined = _joined(
        [
            {
                "pypi_name": "Requests",
                "version": "1.0",
                "download_count": 10,
                "conda_name": "requests",
                "match_source": "x",
                "is_internal": False,
            },
            {
                "pypi_name": "Requests",
                "version": "2.0",
                "download_count": 5,
                "conda_name": "requests",
                "match_source": "x",
                "is_internal": False,
            },
        ]
    )
    consumption = _consumption(
        [
            {
                "name": "requests",
                "platform_env_count": 3,
                "internal_app_count": 1,
                "internal_component_count": 2,
                "internal_lob_count": 4,
            }
        ]
    )

    result = N.build_enterprise_jfrog_consumption(joined, consumption)

    assert list(result.columns) == N._JFROG_COLS
    assert len(result) == 1
    row = result.iloc[0]
    assert row["core_python_package_name"] == "requests"
    assert row["repository_source"] == "CDO-ENT-JFROG"
    assert row["artifactory_downloads"] == 15
    assert row["artifactory_version_count"] == 2
    assert row["platform_env_count"] == 3
    assert row["internal_app_count"] == 1
    assert row["internal_component_count"] == 2
    assert row["internal_lob_count"] == 4
    assert row["packaging_tier"] is None
    assert row["verification_timestamp_utc"] is not None


def test_build_enterprise_jfrog_consumption_downloads_only_defaults_telemetry_to_zero():
    joined = _joined(
        [
            {
                "pypi_name": "foo",
                "version": "1.0",
                "download_count": 7,
                "conda_name": None,
                "match_source": None,
                "is_internal": True,
            }
        ]
    )
    result = N.build_enterprise_jfrog_consumption(joined, _consumption([]))
    row = result.iloc[0]
    assert row["core_python_package_name"] == "foo"
    assert row["artifactory_downloads"] == 7
    assert row["platform_env_count"] == 0


def test_build_enterprise_jfrog_consumption_consumption_only_defaults_downloads_to_zero():
    consumption = _consumption(
        [
            {
                "name": "bar",
                "platform_env_count": 2,
                "internal_app_count": 0,
                "internal_component_count": 0,
                "internal_lob_count": 1,
            }
        ]
    )
    result = N.build_enterprise_jfrog_consumption(_joined([]), consumption)
    row = result.iloc[0]
    assert row["core_python_package_name"] == "bar"
    assert row["artifactory_downloads"] == 0
    assert row["artifactory_version_count"] == 0
    assert row["platform_env_count"] == 2


def test_build_enterprise_jfrog_consumption_drops_pep503_too_short_names():
    joined = _joined(
        [
            {
                "pypi_name": "a",
                "version": "1.0",
                "download_count": 1,
                "conda_name": None,
                "match_source": None,
                "is_internal": True,
            }
        ]
    )
    result = N.build_enterprise_jfrog_consumption(joined, _consumption([]))
    assert result.empty
    assert list(result.columns) == N._JFROG_COLS


def test_build_enterprise_jfrog_consumption_both_inputs_empty():
    result = N.build_enterprise_jfrog_consumption(None, None)
    assert result.empty
    assert list(result.columns) == N._JFROG_COLS


def test_build_enterprise_jfrog_consumption_never_raises_on_malformed():
    result = N.build_enterprise_jfrog_consumption(pd.DataFrame({"bad": [1]}), pd.DataFrame({"bad": [1]}))
    assert result.empty
    assert list(result.columns) == N._JFROG_COLS


def test_pep503_parity_with_priority_script():
    """Local ``_pep503`` must match ``priority.py::pep503`` on shared fixtures."""
    import re
    from datetime import datetime

    def reference_pep503(raw):
        if raw is None or isinstance(raw, datetime):
            return None
        s = str(raw).strip().lower().replace("_", "-").replace(".", "-")
        s = re.sub(r"-+", "-", s).strip("-")
        return s if len(s) >= 2 else None

    fixtures = [
        ("Requests", "requests"),
        ("Foo_Bar.Baz", "foo-bar-baz"),
        ("already-normal", "already-normal"),
        ("a", None),
        ("", None),
        (None, None),
    ]
    for raw, expected in fixtures:
        assert N._pep503(raw) == reference_pep503(raw) == expected
