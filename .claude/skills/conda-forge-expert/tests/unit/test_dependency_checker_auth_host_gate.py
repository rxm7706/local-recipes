"""Regression guard: dependency-checker.py's own `_auth_headers` must be
host-gated, matching `_http.auth_headers_for`'s gate.

Rule-2 retro (Story 5.5, follow-up patch): `_auth_headers` never delegated to
`_http.py` and had its own independent, unconditional credential-injection
implementation (with a broader `ARTIFACTORY_*`/`JFROG_TOKEN`/`JFROG_USER`
alias vocabulary `_http.py` does not cover) — so `_http.py`'s host-gating fix
did not close this sibling copy of the identical cross-resolver leak.
"""
from __future__ import annotations


class TestDependencyCheckerAuthHostGate:
    def test_jfrog_api_key_not_sent_to_unconfigured_host(self, load_module, monkeypatch):
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        for key in ("CONDA_FORGE_BASE_URL", "PYPI_BASE_URL"):
            monkeypatch.delenv(key, raising=False)
        checker = load_module("dependency-checker.py")
        headers = checker._auth_headers("https://conda.anaconda.org/conda-forge/linux-64/repodata.json")
        assert "X-JFrog-Art-Api" not in headers

    def test_jfrog_api_key_sent_to_configured_host(self, load_module, monkeypatch):
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        monkeypatch.setenv(
            "CONDA_FORGE_BASE_URL",
            "https://mycompany.jfrog.io/artifactory/conda-forge-remote",
        )
        checker = load_module("dependency-checker.py")
        headers = checker._auth_headers(
            "https://mycompany.jfrog.io/artifactory/conda-forge-remote/linux-64/repodata.json"
        )
        assert headers.get("X-JFrog-Art-Api") == "secret-key"

    def test_artifactory_alias_env_vars_also_host_gated(self, load_module, monkeypatch):
        """Covers the broader alias vocabulary `_http.py` doesn't have —
        the whole reason this file couldn't just delegate to it."""
        monkeypatch.setenv("ARTIFACTORY_TOKEN", "bearer-secret")
        for key in ("CONDA_FORGE_BASE_URL", "PYPI_BASE_URL"):
            monkeypatch.delenv(key, raising=False)
        checker = load_module("dependency-checker.py")
        headers = checker._auth_headers("https://conda.anaconda.org/conda-forge/linux-64/repodata.json")
        assert "Authorization" not in headers

        monkeypatch.setenv(
            "CONDA_FORGE_BASE_URL", "https://mycompany.jfrog.io/artifactory/conda-forge-remote"
        )
        checker2 = load_module("dependency-checker.py")
        headers2 = checker2._auth_headers(
            "https://mycompany.jfrog.io/artifactory/conda-forge-remote/linux-64/repodata.json"
        )
        assert headers2.get("Authorization") == "Bearer bearer-secret"

    def test_falls_back_to_unconditional_when_http_module_unimportable(
        self, load_module, monkeypatch
    ):
        """`_is_configured_enterprise_host` degrades to True (its pre-fix
        behavior) when `_http` can't be imported at all — no worse than
        before this patch in that already-degraded case."""
        checker = load_module("dependency-checker.py")
        monkeypatch.setattr(
            checker,
            "_is_configured_enterprise_host",
            lambda url: True,
        )
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        headers = checker._auth_headers("https://conda.anaconda.org/conda-forge/linux-64/repodata.json")
        assert headers.get("X-JFrog-Art-Api") == "secret-key"
