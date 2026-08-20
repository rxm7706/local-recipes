"""Regression guard: dependency-checker.py's own `_auth_headers` must be
host-gated, matching `_http.auth_headers_for`'s gate.

Rule-2 retro (Story 5.5, follow-up patch): `_auth_headers` never delegated to
`_http.py` and had its own independent, unconditional credential-injection
implementation (with a broader `ARTIFACTORY_*`/`JFROG_TOKEN`/`JFROG_USER`
alias vocabulary `_http.py` does not cover) — so `_http.py`'s host-gating fix
did not close this sibling copy of the identical cross-resolver leak.
"""
from __future__ import annotations

import os
import sys

import pytest

_CRED_VARS = (
    "JFROG_API_KEY", "ARTIFACTORY_API_KEY",
    "JFROG_TOKEN", "ARTIFACTORY_TOKEN", "CONDA_TOKEN",
    "JFROG_USER", "ARTIFACTORY_USER",
    "JFROG_PASSWORD", "ARTIFACTORY_PASSWORD",
    "CONDA_CHANNEL_URL",
)


@pytest.fixture(autouse=True)
def _clean_cred_env(monkeypatch):
    """Start from no credentials and no mirror vars.

    Without this, a developer or CI shell that already exports (say)
    `JFROG_API_KEY` makes the `api_key` branch win before the branch a test
    is actually exercising, so the test fails against correct code.
    """
    for key in _CRED_VARS:
        monkeypatch.delenv(key, raising=False)
    for key in list(os.environ):
        if key.endswith("_BASE_URL"):
            monkeypatch.delenv(key, raising=False)


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

    def test_explicitly_configured_channel_host_is_authorized(
        self, load_module, monkeypatch
    ):
        """The operator's OWN channel must still get its credential.

        `--channel` / `CONDA_CHANNEL_URL` / the enterprise config are how this
        tool is pointed at an Artifactory channel, and NONE of them is a
        `*_BASE_URL`. Gating on `_http`'s allowlist alone therefore withheld
        the credential from the one channel the operator configured — a
        silent 401/404 on every lookup, and the reason `CONDA_TOKEN` (an
        anaconda.org channel token, not a JFrog one) reached nothing at all.
        """
        monkeypatch.setenv("CONDA_TOKEN", "anaconda-channel-token")
        monkeypatch.setenv("CONDA_CHANNEL_URL", "https://conda.anaconda.org/myprivateorg")
        checker = load_module("dependency-checker.py")
        channels = checker.get_configured_channels()
        assert channels == ["https://conda.anaconda.org/myprivateorg"]
        headers = checker._auth_headers(channels[0] + "/linux-64/repodata.json")
        assert headers.get("Authorization") == "Bearer anaconda-channel-token"

    def test_public_fallback_channel_is_not_authorized(self, load_module, monkeypatch):
        """The step-4 fallback can land on a public default nobody chose, so
        it is deliberately NOT remembered as an explicit channel."""
        monkeypatch.setenv("CONDA_TOKEN", "anaconda-channel-token")
        checker = load_module("dependency-checker.py")
        checker.get_configured_channels()  # falls through to the public default
        headers = checker._auth_headers(
            "https://conda.anaconda.org/conda-forge/linux-64/repodata.json"
        )
        assert headers == {}

    def test_no_credential_when_http_unimportable_and_nothing_explicit(
        self, load_module, monkeypatch
    ):
        """When `_http` can't be imported the gate must NOT degrade to "yes,
        unconditionally" — that reinstated the exact leak this gate exists to
        close for everyone in that state. With no explicit channel either,
        the answer is no credential."""
        checker = load_module("dependency-checker.py")
        monkeypatch.setitem(sys.modules, "_http", None)  # forces ImportError
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        assert checker._is_configured_enterprise_host("https://anything.example.com/x") is False
        headers = checker._auth_headers("https://anything.example.com/x")
        assert headers == {}

    def test_explicit_channel_still_authorized_when_http_unimportable(
        self, load_module, monkeypatch
    ):
        """...but an explicitly-named channel still gates correctly on its
        own, with no `_http` at all — the offline / external-clone case."""
        monkeypatch.setenv("CONDA_CHANNEL_URL", "https://artifactory.corp.com/api/conda/cf")
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        checker = load_module("dependency-checker.py")
        channels = checker.get_configured_channels()
        monkeypatch.setitem(sys.modules, "_http", None)  # forces ImportError
        headers = checker._auth_headers(channels[0] + "/linux-64/repodata.json")
        assert headers.get("X-JFrog-Art-Api") == "secret-key"

    def test_host_gate_strips_userinfo_and_port(self, load_module, monkeypatch):
        """Same `urlparse().hostname` contract as `_http._host_of`: a
        `https://user:token@host/` channel (a routine Artifactory form) must
        resolve to the host, not to the username."""
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        monkeypatch.setenv(
            "CONDA_CHANNEL_URL", "https://svc:tok@artifactory.corp.com:8081/api/conda/cf"
        )
        checker = load_module("dependency-checker.py")
        checker.get_configured_channels()
        assert checker._EXPLICIT_CHANNEL_HOSTS == {"artifactory.corp.com"}
        headers = checker._auth_headers("https://artifactory.corp.com/api/conda/cf/repodata.json")
        assert headers.get("X-JFrog-Art-Api") == "secret-key"

    def test_sys_path_does_not_grow_per_call(self, load_module, monkeypatch):
        """The gate used to `sys.path.insert(0, ...)` on every invocation, and
        it sits on the per-request path — a long-lived process (the MCP
        server) grew sys.path by one duplicate entry per request, taxing
        every later import."""
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        checker = load_module("dependency-checker.py")
        before = len(sys.path)
        for _ in range(50):
            checker._auth_headers("https://conda.anaconda.org/conda-forge/repodata.json")
        assert len(sys.path) == before


class TestCredentialKindIsGatedSeparatelyFromHost:
    """Story 5.5, third review pass.

    `_EXPLICIT_CHANNEL_HOSTS` deliberately authorizes the channel the operator
    NAMED, and that channel is routinely public — `--channel
    https://conda.anaconda.org/myprivateorg` is a supported setup. Answering
    only "is this host authorized?" therefore sent the JFrog API key to
    anaconda.org (the leak this retro exists to close) and, because the JFrog
    branch is checked first, shadowed the `CONDA_TOKEN` that channel needs.
    """

    def test_jfrog_key_is_never_sent_to_an_explicitly_named_public_channel(
        self, load_module, monkeypatch
    ):
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        monkeypatch.setenv(
            "CONDA_CHANNEL_URL", "https://conda.anaconda.org/myprivateorg"
        )
        checker = load_module("dependency-checker.py")
        checker.get_configured_channels()
        headers = checker._auth_headers(
            "https://conda.anaconda.org/myprivateorg/linux-64/repodata.json"
        )
        assert "X-JFrog-Art-Api" not in headers

    def test_conda_token_still_reaches_the_named_public_channel(
        self, load_module, monkeypatch
    ):
        """The previous pass's fix — CONDA_TOKEN reaching the operator's own
        org channel — must survive the credential-kind split. It is an
        anaconda.org channel token; that host is exactly its destination."""
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        monkeypatch.setenv("CONDA_TOKEN", "conda-org-token")
        monkeypatch.setenv(
            "CONDA_CHANNEL_URL", "https://conda.anaconda.org/myprivateorg"
        )
        checker = load_module("dependency-checker.py")
        checker.get_configured_channels()
        headers = checker._auth_headers(
            "https://conda.anaconda.org/myprivateorg/linux-64/repodata.json"
        )
        assert headers.get("Authorization") == "Bearer conda-org-token"
        assert "X-JFrog-Art-Api" not in headers

    def test_enterprise_host_still_gets_the_jfrog_key_first(
        self, load_module, monkeypatch
    ):
        """The split must not disturb the enterprise case: a non-public
        configured host keeps the original credential priority."""
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        monkeypatch.setenv("CONDA_TOKEN", "conda-org-token")
        monkeypatch.setenv(
            "CONDA_CHANNEL_URL", "https://mycompany.jfrog.io/api/conda/cf"
        )
        checker = load_module("dependency-checker.py")
        checker.get_configured_channels()
        headers = checker._auth_headers(
            "https://mycompany.jfrog.io/api/conda/cf/linux-64/repodata.json"
        )
        assert headers.get("X-JFrog-Art-Api") == "secret-key"

    def test_explicit_channel_authorization_does_not_accumulate_across_calls(
        self, load_module, monkeypatch
    ):
        """The remembered set is the authorization scope for the channels
        resolved by THIS call. Accumulating leaked scope across calls in a
        long-lived process: a host named by one `check_dependencies` request's
        `--channel` stayed credential-authorized for every later request."""
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        checker = load_module("dependency-checker.py")

        checker.get_configured_channels("https://first.corp.example/api/conda/cf")
        assert checker._auth_headers(
            "https://first.corp.example/api/conda/cf/repodata.json"
        ).get("X-JFrog-Art-Api") == "secret-key"

        checker.get_configured_channels("https://second.corp.example/api/conda/cf")
        assert checker._EXPLICIT_CHANNEL_HOSTS == {"second.corp.example"}
        assert checker._auth_headers(
            "https://first.corp.example/api/conda/cf/repodata.json"
        ) == {}
