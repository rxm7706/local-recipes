"""Regression guard: inventory_channel.py's `_make_request` fallback path
(used when `_http` isn't importable) must be host-gated, matching
`_http.auth_headers_for`'s gate.

Rule-2 retro (Story 5.5, follow-up patch): the primary path (`_HTTP_AVAILABLE`)
already delegates to `_http.make_request`, which is fixed. But the fallback
duplicated the OLD unconditional-injection logic rather than delegating, so
it carried the identical cross-resolver leak whenever `_http` itself could
not be imported ("offline / external clones", per the module's own comment).
"""
from __future__ import annotations


class TestInventoryChannelFallbackAuthHostGate:
    def test_jfrog_api_key_not_sent_to_unconfigured_host(self, load_module, monkeypatch):
        for key in ("CONDA_FORGE_BASE_URL", "PYPI_BASE_URL"):
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        mod = load_module("inventory_channel.py")
        monkeypatch.setattr(mod, "_HTTP_AVAILABLE", False)
        request = mod._make_request("https://conda.anaconda.org/conda-forge/linux-64/repodata.json")
        assert "X-jfrog-art-api" not in request.headers

    def test_jfrog_api_key_sent_to_configured_host(self, load_module, monkeypatch):
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        monkeypatch.setenv(
            "CONDA_FORGE_BASE_URL",
            "https://mycompany.jfrog.io/artifactory/conda-forge-remote",
        )
        mod = load_module("inventory_channel.py")
        monkeypatch.setattr(mod, "_HTTP_AVAILABLE", False)
        request = mod._make_request(
            "https://mycompany.jfrog.io/artifactory/conda-forge-remote/linux-64/repodata.json"
        )
        assert request.headers.get("X-jfrog-art-api") == "secret-key"

    def test_primary_path_delegates_to_http_make_request_when_available(
        self, load_module, monkeypatch
    ):
        """When `_http` IS importable, the fallback's own gate never runs —
        `_http.make_request` (already host-gated) is used instead."""
        mod = load_module("inventory_channel.py")
        called = {}

        def _fake_http_make_request(url, user_agent=""):
            called["url"] = url
            return "sentinel-request"

        monkeypatch.setattr(mod, "_HTTP_AVAILABLE", True)
        monkeypatch.setattr(mod, "_http_make_request", _fake_http_make_request)
        result = mod._make_request("https://conda.anaconda.org/conda-forge/linux-64/repodata.json")
        assert result == "sentinel-request"
        assert called["url"] == "https://conda.anaconda.org/conda-forge/linux-64/repodata.json"
