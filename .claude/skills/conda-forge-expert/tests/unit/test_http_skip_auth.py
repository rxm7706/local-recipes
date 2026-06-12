"""Unit tests for `_http.auth_headers_for(..., skip_auth=True)` + `make_request`.

The `skip_auth` kwarg is the v8.14.0 call-site opt-out for known-public
endpoints (e.g. dev.azure.com's public conda-forge feedstock-builds
project). With JFROG_API_KEY set in env, the auth chain would otherwise
unconditionally inject `X-JFrog-Art-Api` cross-host — `skip_auth=True`
short-circuits the chain and returns empty headers.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_HTTP_PATH = Path(__file__).resolve().parent.parent.parent / "scripts" / "_http.py"
spec = importlib.util.spec_from_file_location("_http", _HTTP_PATH)
assert spec is not None and spec.loader is not None
_http = importlib.util.module_from_spec(spec)
sys.modules["_http"] = _http
spec.loader.exec_module(_http)


class TestSkipAuth:
    """`skip_auth=True` returns empty regardless of env / netrc state."""

    def test_auth_headers_for_skip_auth_returns_empty_even_with_jfrog_key(
        self, monkeypatch
    ):
        monkeypatch.setenv("JFROG_API_KEY", "dummy-key-12345")
        # Without skip_auth → JFrog header is injected (sanity check).
        baseline = _http.auth_headers_for("https://dev.azure.com/conda-forge/foo")
        assert baseline.get("X-JFrog-Art-Api") == "dummy-key-12345"
        # With skip_auth=True → empty.
        skipped = _http.auth_headers_for(
            "https://dev.azure.com/conda-forge/foo", skip_auth=True
        )
        assert skipped == {}

    def test_auth_headers_for_skip_auth_returns_empty_even_with_github_token(
        self, monkeypatch
    ):
        # GitHub token would inject on api.github.com without skip_auth.
        for var in ("JFROG_API_KEY", "JFROG_USERNAME", "JFROG_PASSWORD"):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_dummy_token")
        baseline = _http.auth_headers_for("https://api.github.com/repos/foo/bar")
        assert baseline.get("Authorization", "").startswith("Bearer ")
        skipped = _http.auth_headers_for(
            "https://api.github.com/repos/foo/bar", skip_auth=True
        )
        assert skipped == {}

    def test_make_request_skip_auth_omits_auth_headers(self, monkeypatch):
        monkeypatch.setenv("JFROG_API_KEY", "dummy-key-12345")
        req = _http.make_request(
            "https://dev.azure.com/conda-forge/feedstock-builds/_apis/build/builds/1/artifacts",
            skip_auth=True,
        )
        # Request only carries User-Agent + any extra_headers; no auth.
        headers = dict(req.headers)
        # urllib normalizes header keys via capitalize() so check case-insensitively.
        keys_lower = {k.lower() for k in headers}
        assert "x-jfrog-art-api" not in keys_lower
        assert "authorization" not in keys_lower
        assert any(k.lower() == "user-agent" for k in headers)

    def test_make_request_default_still_injects_auth(self, monkeypatch):
        """Regression guard: skip_auth defaults to False; existing behaviour preserved."""
        monkeypatch.setenv("JFROG_API_KEY", "dummy-key-12345")
        req = _http.make_request("https://anaconda.org/conda-forge/repodata.json")
        headers = dict(req.headers)
        keys_lower = {k.lower(): v for k, v in headers.items()}
        assert keys_lower.get("x-jfrog-art-api") == "dummy-key-12345"
