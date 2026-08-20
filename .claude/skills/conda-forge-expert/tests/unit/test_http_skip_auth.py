"""Unit tests for `_http.auth_headers_for(..., skip_auth=True)` + `make_request`.

The `skip_auth` kwarg is the v8.14.0 call-site opt-out for known-public
endpoints (e.g. dev.azure.com's public conda-forge feedstock-builds
project). As of the Rule-2 retro (Story 5.5), the JFrog credential branches
are additionally host-gated against `_configured_enterprise_hosts()` — see
`test_http_jfrog_host_gate.py` — so `skip_auth=True` is now defense in
depth for a configured host rather than the only way to avoid the leak.
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
        # The host must be a *configured* one for the baseline (no skip_auth)
        # injection to fire post-retro — see test_http_jfrog_host_gate.py for
        # the un-configured-host case.
        #
        # It must also be a genuinely ENTERPRISE host. This example was
        # `anaconda.org` until the third review pass, which encoded "the JFrog
        # credential IS sent to a public host" as expected behaviour in the
        # very file pair meant to pin that leak closed; it was repointed at
        # `dev.azure.com`, which is public too, so the fourth pass's public-host
        # floor correctly stopped the baseline firing. Use a host that could
        # only ever be an operator's own mirror.
        monkeypatch.setenv(
            "CONDA_FORGE_BASE_URL", "https://mycorp.jfrog.io/artifactory/conda-forge"
        )
        url = "https://mycorp.jfrog.io/artifactory/conda-forge/noarch/repodata.json"
        baseline = _http.auth_headers_for(url)
        assert baseline.get("X-JFrog-Art-Api") == "dummy-key-12345"
        # With skip_auth=True → empty, even though the host is configured.
        skipped = _http.auth_headers_for(url, skip_auth=True)
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

    def test_make_request_default_injects_auth_for_configured_host(self, monkeypatch):
        """Regression guard: skip_auth defaults to False; injection still fires
        for a host the operator actually configured a mirror at.

        The mirror host must be a genuinely enterprise one. Using a public
        default here (this test named `anaconda.org`) asserts that the JFrog
        credential IS sent to a public host — a green test pinning the very
        leak the surrounding suite exists to close."""
        monkeypatch.setenv("JFROG_API_KEY", "dummy-key-12345")
        monkeypatch.setenv(
            "CONDA_FORGE_BASE_URL", "https://mycompany.jfrog.io/artifactory/conda-forge"
        )
        req = _http.make_request("https://mycompany.jfrog.io/artifactory/conda-forge/repodata.json")
        headers = dict(req.headers)
        keys_lower = {k.lower(): v for k, v in headers.items()}
        assert keys_lower.get("x-jfrog-art-api") == "dummy-key-12345"
