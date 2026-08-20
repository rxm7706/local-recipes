"""Unit tests for `_http._configured_enterprise_hosts` + the JFrog host gate.

Rule-2 retro (Story 5.5): `_http.auth_headers_for` used to attach
`JFROG_API_KEY`/`JFROG_USERNAME`+`PASSWORD` to EVERY outbound request
whenever the env var was set, regardless of the target host — a
cross-resolver credential leak documented in `_http.py`'s own docstring
since v8.14.0 ("the documented cross-resolver leak ... until a host
allowlist lands"). These tests prove the allowlist: the JFrog credential
now only attaches to a host named by some currently-set `*_BASE_URL` env
var, derived at call time rather than hardcoded.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

_HTTP_PATH = Path(__file__).resolve().parent.parent.parent / "scripts" / "_http.py"
spec = importlib.util.spec_from_file_location("_http", _HTTP_PATH)
assert spec is not None and spec.loader is not None
_http = importlib.util.module_from_spec(spec)
sys.modules["_http"] = _http
spec.loader.exec_module(_http)


@pytest.fixture(autouse=True)
def _clean_enterprise_env(monkeypatch):
    """Every test starts with no JFrog / *_BASE_URL vars set."""
    for key in list(os.environ):
        if key.endswith("_BASE_URL") or key.startswith("JFROG_"):
            monkeypatch.delenv(key, raising=False)


class TestConfiguredEnterpriseHosts:
    def test_empty_when_no_base_url_vars_set(self):
        assert _http._configured_enterprise_hosts() == set()

    def test_derives_host_from_any_base_url_suffixed_var(self, monkeypatch):
        """Not a hardcoded name list — any `*_BASE_URL` var counts."""
        monkeypatch.setenv("SOME_NEW_RESOLVER_BASE_URL", "https://mirror.example.com/x")
        assert "mirror.example.com" in _http._configured_enterprise_hosts()

    def test_ignores_non_base_url_vars(self, monkeypatch):
        monkeypatch.setenv("JFROG_API_KEY", "secret")
        assert _http._configured_enterprise_hosts() == set()

    def test_malformed_url_contributes_no_host(self, monkeypatch):
        monkeypatch.setenv("CONDA_FORGE_BASE_URL", "not-a-url")
        assert _http._configured_enterprise_hosts() == set()

    def test_urlparse_raising_value_error_does_not_crash_the_derivation(self, monkeypatch):
        """An unclosed IPv6-bracket literal makes urlparse() raise ValueError
        (verified: urlparse("https://[oops") raises "Invalid IPv6 URL") --
        one bad *_BASE_URL value must not crash the whole allowlist scan,
        and other, well-formed entries must still be collected."""
        monkeypatch.setenv("CONDA_FORGE_BASE_URL", "https://[oops")
        monkeypatch.setenv("PYPI_BASE_URL", "https://good.example.com/simple")
        assert _http._configured_enterprise_hosts() == {"good.example.com"}

    def test_collects_hosts_from_multiple_vars(self, monkeypatch):
        monkeypatch.setenv("CONDA_FORGE_BASE_URL", "https://a.example.com/cf")
        monkeypatch.setenv("PYPI_BASE_URL", "https://b.example.com/simple")
        hosts = _http._configured_enterprise_hosts()
        assert hosts == {"a.example.com", "b.example.com"}


class TestJfrogHostGate:
    def test_jfrog_api_key_not_sent_to_unconfigured_public_host(self, monkeypatch):
        """The original cross-resolver leak: JFROG_API_KEY set, no matching
        *_BASE_URL, request falls through to a public default host."""
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        headers = _http.auth_headers_for("https://conda.anaconda.org/conda-forge/linux-64/repodata.json")
        assert "X-JFrog-Art-Api" not in headers

    def test_jfrog_api_key_sent_to_configured_host(self, monkeypatch):
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        monkeypatch.setenv(
            "CONDA_FORGE_BASE_URL",
            "https://mycompany.jfrog.io/artifactory/conda-forge-remote",
        )
        headers = _http.auth_headers_for(
            "https://mycompany.jfrog.io/artifactory/conda-forge-remote/linux-64/repodata.json"
        )
        assert headers.get("X-JFrog-Art-Api") == "secret-key"

    def test_jfrog_api_key_not_sent_when_configured_elsewhere(self, monkeypatch):
        """A JFrog mirror configured for one resolver must not leak the
        credential to a DIFFERENT, unconfigured public host."""
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        monkeypatch.setenv(
            "CONDA_FORGE_BASE_URL",
            "https://mycompany.jfrog.io/artifactory/conda-forge-remote",
        )
        headers = _http.auth_headers_for("https://pypi.org/pypi/example/json")
        assert "X-JFrog-Art-Api" not in headers

    def test_jfrog_basic_auth_gated_the_same_way(self, monkeypatch):
        monkeypatch.setenv("JFROG_USERNAME", "svc-account")
        monkeypatch.setenv("JFROG_PASSWORD", "hunter2")
        unconfigured = _http.auth_headers_for("https://registry.npmjs.org/example")
        assert "Authorization" not in unconfigured

        monkeypatch.setenv("NPM_BASE_URL", "https://mycompany.jfrog.io/artifactory/api/npm/npm-remote")
        configured = _http.auth_headers_for(
            "https://mycompany.jfrog.io/artifactory/api/npm/npm-remote/example"
        )
        assert configured.get("Authorization", "").startswith("Basic ")

    def test_configured_host_with_no_jfrog_credential_falls_through_to_netrc(
        self, monkeypatch, tmp_path
    ):
        """A configured host with no JFROG_* env set must still reach the
        generic .netrc branch — the host gate must not swallow that
        fallback (regression guard for the gate's own control flow)."""
        netrc_path = tmp_path / ".netrc"
        netrc_path.write_text(
            "machine mycompany.jfrog.io\nlogin bot\npassword swordfish\n"
        )
        monkeypatch.setenv("NETRC", str(netrc_path))
        monkeypatch.setenv(
            "CONDA_FORGE_BASE_URL",
            "https://mycompany.jfrog.io/artifactory/conda-forge-remote",
        )
        headers = _http.auth_headers_for(
            "https://mycompany.jfrog.io/artifactory/conda-forge-remote/linux-64/repodata.json"
        )
        assert headers.get("Authorization", "").startswith("Basic ")

    def test_github_token_path_unaffected_by_host_gate(self, monkeypatch):
        """GitHub auth was already host-scoped; the new gate must not
        interfere with it either way."""
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_dummy")
        headers = _http.auth_headers_for("https://api.github.com/repos/foo/bar")
        assert headers.get("Authorization") == "Bearer ghp_dummy"
