"""Unit tests for `detail_cf_atlas.py`.

Covers the v6.1.0 air-gap-friendly improvements:

- ``fetch_repodata_build_matrix`` (URL-chain fallback when api.anaconda.org
  is unreachable) — verifies shape parity with ``fetch_anaconda_files`` so
  the renderer doesn't care which source produced the data.
- ``--version`` override on ``fetch_vdb_data`` (purl substitution).

All tests are offline: ``urllib.request.urlopen`` is mocked so no real
network traffic happens. The repodata-fallback tests also stub
``_http.resolve_conda_forge_urls`` so the test doesn't depend on whatever
mirrors / pixi config the developer happens to have configured.
"""
from __future__ import annotations

import io
import json
from typing import Any
from unittest.mock import MagicMock, patch


def _fake_repodata(name: str, *, version: str = "5.2.12", build: str = "pyhd8ed1ab_0",
                   subdir: str = "noarch", timestamp: int = 1712534400000,
                   depends: list[str] | None = None) -> dict[str, Any]:
    """Minimal current_repodata.json shape with one matching package + filler."""
    return {
        "info": {"subdir": subdir},
        "packages": {
            f"{name}-{version}-{build}.tar.bz2": {
                "name": name,
                "version": version,
                "build": build,
                "build_number": 0,
                "depends": depends or ["python >=3.10"],
                "license": "BSD-3-Clause",
                "size": 3_869_000,
                "md5": "09770adaeaa1ef255e68e1b53581ec3a",
                "subdir": subdir,
                "timestamp": timestamp,
            },
            "some-other-pkg-1.0.0-py_0.tar.bz2": {
                "name": "some-other-pkg",
                "version": "1.0.0",
                "build": "py_0",
                "subdir": subdir,
            },
        },
        "packages.conda": {},
    }


# ── fetch_repodata_build_matrix ─────────────────────────────────────────────

class TestRepodataBuildMatrix:
    """Verify the air-gap fallback that reads current_repodata.json."""

    def test_returns_shape_matching_files_api(self, load_module):
        """Output records must use the same keys the renderer reads from
        the anaconda.org files API path: attrs.subdir, attrs.version,
        attrs.build, attrs.depends, top-level version, size, md5,
        upload_time, basename. Drift here breaks the build-matrix render."""
        mod = load_module("detail_cf_atlas.py")
        payload = _fake_repodata("django", subdir="noarch")

        with patch.object(mod, "_http_make_request", return_value=MagicMock()), \
             patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())), \
             patch("_http.resolve_conda_forge_urls",
                   return_value=["https://repo.prefix.dev/conda-forge"], create=True):
            records, base_used, err = mod.fetch_repodata_build_matrix(
                "django", subdir_filter="noarch", atlas_subdirs=["noarch"],
            )

        assert err is None
        assert base_used == "https://repo.prefix.dev/conda-forge"
        assert len(records) == 1
        rec = records[0]
        # Top-level keys the renderer reads
        assert rec["version"] == "5.2.12"
        assert rec["size"] == 3_869_000
        assert rec["md5"] == "09770adaeaa1ef255e68e1b53581ec3a"
        assert rec["upload_time"] == ""  # repodata has no upload_time
        assert rec["basename"].startswith("noarch/django-")
        # attrs.* keys the renderer reads
        assert rec["attrs"]["subdir"] == "noarch"
        assert rec["attrs"]["version"] == "5.2.12"
        assert rec["attrs"]["build"] == "pyhd8ed1ab_0"
        assert rec["attrs"]["depends"] == ["python >=3.10"]

    def test_filters_by_subdir(self, load_module):
        """`subdir_filter` must reduce the work — only one HTTP fetch."""
        mod = load_module("detail_cf_atlas.py")
        payload = _fake_repodata("django", subdir="noarch")
        urlopen_mock = MagicMock(return_value=io.BytesIO(json.dumps(payload).encode()))

        with patch.object(mod, "_http_make_request", return_value=MagicMock()), \
             patch("urllib.request.urlopen", urlopen_mock), \
             patch("_http.resolve_conda_forge_urls",
                   return_value=["https://repo.prefix.dev/conda-forge"], create=True):
            records, _, err = mod.fetch_repodata_build_matrix(
                "django", subdir_filter="noarch",
                atlas_subdirs=["linux-64", "noarch", "osx-64"],
            )

        assert err is None
        # Only the noarch subdir was probed
        assert urlopen_mock.call_count == 1

    def test_walks_candidate_chain(self, load_module):
        """When the first candidate base 502s, the second should be tried."""
        mod = load_module("detail_cf_atlas.py")
        payload = _fake_repodata("django", subdir="noarch")
        good = io.BytesIO(json.dumps(payload).encode())

        # First call raises (simulating prefix.dev down), second returns body.
        import urllib.error
        urlopen_mock = MagicMock(side_effect=[
            urllib.error.HTTPError("https://broken/", 502, "Bad Gateway", {}, None),  # type: ignore[arg-type]
            good,
        ])

        with patch.object(mod, "_http_make_request", return_value=MagicMock()), \
             patch("urllib.request.urlopen", urlopen_mock), \
             patch("_http.resolve_conda_forge_urls",
                   return_value=["https://broken.example",
                                 "https://conda.anaconda.org/conda-forge"], create=True):
            records, base_used, err = mod.fetch_repodata_build_matrix(
                "django", subdir_filter="noarch", atlas_subdirs=["noarch"],
            )

        assert err is None
        assert len(records) == 1
        assert base_used == "https://conda.anaconda.org/conda-forge"
        assert urlopen_mock.call_count == 2

    def test_handles_no_match(self, load_module):
        """When the package is truly absent, return error msg, not crash."""
        mod = load_module("detail_cf_atlas.py")
        empty = {"info": {"subdir": "noarch"}, "packages": {}, "packages.conda": {}}

        with patch.object(mod, "_http_make_request", return_value=MagicMock()), \
             patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(empty).encode())), \
             patch("_http.resolve_conda_forge_urls",
                   return_value=["https://repo.prefix.dev/conda-forge"], create=True):
            records, base_used, err = mod.fetch_repodata_build_matrix(
                "no-such-pkg", subdir_filter="noarch", atlas_subdirs=["noarch"],
            )

        assert records == []
        assert err is not None
        assert "no-such-pkg" in err

    def test_returns_error_when_http_helper_missing(self, load_module):
        """Without _http, the function can't resolve URLs — surface that clearly."""
        mod = load_module("detail_cf_atlas.py")
        with patch.object(mod, "_http_make_request", None):
            records, base_used, err = mod.fetch_repodata_build_matrix(
                "django", subdir_filter=None, atlas_subdirs=["noarch"],
            )
        assert records == []
        assert base_used is None
        assert err is not None
        assert "_http" in err

    def test_uses_standard_subdirs_when_atlas_empty(self, load_module):
        """Falls back to the canonical 7-subdir set for PyPI-only / new packages."""
        mod = load_module("detail_cf_atlas.py")
        # _STANDARD_CONDA_FORGE_SUBDIRS has 7 entries
        assert len(mod._STANDARD_CONDA_FORGE_SUBDIRS) == 7
        assert "noarch" in mod._STANDARD_CONDA_FORGE_SUBDIRS
        assert "linux-64" in mod._STANDARD_CONDA_FORGE_SUBDIRS
        assert "osx-arm64" in mod._STANDARD_CONDA_FORGE_SUBDIRS
        # win-32 deliberately omitted
        assert "win-32" not in mod._STANDARD_CONDA_FORGE_SUBDIRS


# ── --version flag (v6.0.1) ─────────────────────────────────────────────────

class TestVdbVersionOverride:
    """Verify `--version VER` substitutes into version-pinned purls."""

    def test_purls_use_override_when_provided(self, load_module):
        mod = load_module("detail_cf_atlas.py")
        record = {
            "pypi_name": "django",
            "conda_name": "django",
            "npm_name": None,
            "latest_conda_version": "6.0.4",
            "conda_repo_url": "https://github.com/django/django",
        }

        # Mock vdb.lib.search.search_by_purl_like to capture which purls are queried.
        called_purls: list[str] = []

        def fake_search(purl, with_data=True):
            called_purls.append(purl)
            return []

        fake_vdb = MagicMock()
        fake_vdb.search.search_by_purl_like = fake_search

        with patch.dict("sys.modules", {"vdb": MagicMock(), "vdb.lib": fake_vdb}):
            data, err = mod.fetch_vdb_data(record, version_override="5.2.12")

        # When override is set, version-pinned purls must use 5.2.12, not 6.0.4
        pinned_pypi = [p for p in called_purls if p.startswith("pkg:pypi/django@")]
        pinned_conda = [p for p in called_purls if p.startswith("pkg:conda/django@")]
        assert pinned_pypi == ["pkg:pypi/django@5.2.12"]
        assert pinned_conda == ["pkg:conda/django@5.2.12"]
        # Un-pinned purls remain (so historical baseline is preserved)
        assert "pkg:pypi/django" in called_purls
        assert "pkg:conda/django" in called_purls

    def test_purls_default_to_latest_conda_version(self, load_module):
        mod = load_module("detail_cf_atlas.py")
        record = {
            "pypi_name": "django",
            "conda_name": "django",
            "npm_name": None,
            "latest_conda_version": "6.0.4",
            "conda_repo_url": "",
        }
        called_purls: list[str] = []

        def fake_search(purl, with_data=True):
            called_purls.append(purl)
            return []

        fake_vdb = MagicMock()
        fake_vdb.search.search_by_purl_like = fake_search

        with patch.dict("sys.modules", {"vdb": MagicMock(), "vdb.lib": fake_vdb}):
            mod.fetch_vdb_data(record, version_override=None)

        pinned_pypi = [p for p in called_purls if p.startswith("pkg:pypi/django@")]
        assert pinned_pypi == ["pkg:pypi/django@6.0.4"]
