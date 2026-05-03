"""Unit tests for `_http.py` URL resolvers and `fetch_with_fallback`.

Covers both modes:
- **External**: no env vars, no pixi config — public defaults only.
- **Internal (mocked JFrog)**: env vars + pixi config inject JFrog URLs at
  the head of the chain.

These tests do NOT make real HTTP calls. They mock `read_pixi_config` and
manipulate `os.environ` via `monkeypatch`. The fallback-fetch tests use
`urllib.request.urlopen` mocking.
"""
from __future__ import annotations

import importlib.util
import sys
import urllib.error
from pathlib import Path

import pytest


# Import _http directly from the skill scripts dir (it's underscore-prefixed
# so not importable as a normal package member; load via spec).
_HTTP_PATH = Path(__file__).resolve().parent.parent.parent / "scripts" / "_http.py"
spec = importlib.util.spec_from_file_location("_http", _HTTP_PATH)
assert spec is not None and spec.loader is not None
_http = importlib.util.module_from_spec(spec)
sys.modules["_http"] = _http
spec.loader.exec_module(_http)


# ── helpers ─────────────────────────────────────────────────────────────────

def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip every env var the resolvers consult so tests start from a known state."""
    for var in (
        "CONDA_FORGE_BASE_URL",
        "PYPI_BASE_URL",
        "PYPI_JSON_BASE_URL",
        "GITHUB_BASE_URL",
        "GITHUB_RAW_BASE_URL",
        "JFROG_API_KEY",
        "JFROG_USERNAME",
        "JFROG_PASSWORD",
        "GITHUB_TOKEN",
        "GH_TOKEN",
    ):
        monkeypatch.delenv(var, raising=False)


# ═══════════════════════════════════════════════════════════════════════════
# resolve_conda_forge_urls
# ═══════════════════════════════════════════════════════════════════════════

class TestResolveCondaForgeUrls:
    """conda-forge channel resolver — env, pixi config, public fallbacks."""

    def test_external_no_config_returns_public_defaults(self, monkeypatch):
        _clean_env(monkeypatch)
        chain = _http.resolve_conda_forge_urls(config={})
        assert chain == [
            "https://repo.prefix.dev/conda-forge",
            "https://conda.anaconda.org/conda-forge",
        ]

    def test_env_var_takes_precedence(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv(
            "CONDA_FORGE_BASE_URL",
            "https://artifactory.example.com/artifactory/api/conda/conda-forge-virtual",
        )
        chain = _http.resolve_conda_forge_urls(config={})
        assert chain[0] == "https://artifactory.example.com/artifactory/api/conda/conda-forge-virtual"
        assert "https://repo.prefix.dev/conda-forge" in chain
        assert "https://conda.anaconda.org/conda-forge" in chain

    def test_pixi_mirrors_picked_up(self, monkeypatch):
        _clean_env(monkeypatch)
        cfg = {
            "mirrors": {
                "https://conda.anaconda.org/conda-forge": [
                    "https://artifactory.example.com/artifactory/api/conda/cf-virtual",
                ],
            },
        }
        chain = _http.resolve_conda_forge_urls(config=cfg)
        assert chain[0] == "https://artifactory.example.com/artifactory/api/conda/cf-virtual"

    def test_pixi_default_channels_picked_up(self, monkeypatch):
        """default-channels entries containing 'conda-forge' join the chain.

        The substring filter is intentional — only conda-forge mirrors should
        be appended to the conda-forge resolver chain. Other channels like
        bioconda must NOT pollute it.
        """
        _clean_env(monkeypatch)
        cfg = {
            "default-channels": [
                "https://artifactory.example.com/artifactory/api/conda/conda-forge-external-virtual",
                "https://prefix.dev/bioconda",  # not conda-forge — should be filtered
                "https://artifactory.example.com/artifactory/api/conda/internal-only",  # no 'conda-forge' substring
            ],
        }
        chain = _http.resolve_conda_forge_urls(config=cfg)
        assert chain[0] == "https://artifactory.example.com/artifactory/api/conda/conda-forge-external-virtual"
        assert "https://prefix.dev/bioconda" not in chain
        assert "https://artifactory.example.com/artifactory/api/conda/internal-only" not in chain

    def test_dedup_across_sources(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv(
            "CONDA_FORGE_BASE_URL",
            "https://primary.jfrog/artifactory/api/conda/cf",
        )
        cfg = {
            "mirrors": {
                "https://conda.anaconda.org/conda-forge": [
                    "https://primary.jfrog/artifactory/api/conda/cf",  # duplicate of env
                    "https://secondary.jfrog/artifactory/api/conda/cf",  # new
                ],
            },
            "default-channels": [
                "https://primary.jfrog/artifactory/api/conda/cf",  # duplicate again
            ],
        }
        chain = _http.resolve_conda_forge_urls(config=cfg)
        assert chain.count("https://primary.jfrog/artifactory/api/conda/cf") == 1
        assert chain == [
            "https://primary.jfrog/artifactory/api/conda/cf",
            "https://secondary.jfrog/artifactory/api/conda/cf",
            "https://repo.prefix.dev/conda-forge",
            "https://conda.anaconda.org/conda-forge",
        ]

    def test_trailing_slash_stripped(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("CONDA_FORGE_BASE_URL", "https://jfrog.example.com/cf/")
        chain = _http.resolve_conda_forge_urls(config={})
        assert chain[0] == "https://jfrog.example.com/cf"

    def test_external_chain_always_includes_public_defaults(self, monkeypatch):
        """External clones must always have a usable fallback even with config."""
        _clean_env(monkeypatch)
        chain = _http.resolve_conda_forge_urls(config={"unrelated": "key"})
        assert "https://conda.anaconda.org/conda-forge" in chain


# ═══════════════════════════════════════════════════════════════════════════
# resolve_pypi_simple_urls
# ═══════════════════════════════════════════════════════════════════════════

class TestResolvePypiSimpleUrls:
    """PyPI Simple v1 index resolver."""

    def test_external_no_config_returns_pypi_org(self, monkeypatch):
        _clean_env(monkeypatch)
        assert _http.resolve_pypi_simple_urls(config={}) == ["https://pypi.org/simple"]

    def test_env_var_takes_precedence(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv(
            "PYPI_BASE_URL",
            "https://artifactory.example.com/artifactory/api/pypi/pypi/simple",
        )
        chain = _http.resolve_pypi_simple_urls(config={})
        assert chain[0] == "https://artifactory.example.com/artifactory/api/pypi/pypi/simple"
        assert chain[-1] == "https://pypi.org/simple"

    def test_pixi_pypi_config_index_url(self, monkeypatch):
        _clean_env(monkeypatch)
        cfg = {
            "pypi-config": {
                "index-url": "https://jfrog/artifactory/api/pypi/pypi/simple",
            },
        }
        chain = _http.resolve_pypi_simple_urls(config=cfg)
        assert chain[0] == "https://jfrog/artifactory/api/pypi/pypi/simple"

    def test_extra_index_urls_appended(self, monkeypatch):
        _clean_env(monkeypatch)
        cfg = {
            "pypi-config": {
                "index-url": "https://jfrog/api/pypi/primary/simple",
                "extra-index-urls": [
                    "https://jfrog/api/pypi/curated/simple",
                ],
            },
        }
        chain = _http.resolve_pypi_simple_urls(config=cfg)
        assert chain == [
            "https://jfrog/api/pypi/primary/simple",
            "https://jfrog/api/pypi/curated/simple",
            "https://pypi.org/simple",
        ]


# ═══════════════════════════════════════════════════════════════════════════
# resolve_pypi_json_urls
# ═══════════════════════════════════════════════════════════════════════════

class TestResolvePypiJsonUrls:
    """PyPI JSON metadata resolver."""

    def test_external_unversioned(self, monkeypatch):
        _clean_env(monkeypatch)
        chain = _http.resolve_pypi_json_urls("requests", config={})
        assert chain == ["https://pypi.org/pypi/requests/json"]

    def test_external_versioned(self, monkeypatch):
        _clean_env(monkeypatch)
        chain = _http.resolve_pypi_json_urls("requests", "2.31.0", config={})
        assert chain == ["https://pypi.org/pypi/requests/2.31.0/json"]

    def test_env_var_used(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("PYPI_JSON_BASE_URL", "https://jfrog.example.com/api/pypi/pypi")
        chain = _http.resolve_pypi_json_urls("flask", config={})
        assert chain[0] == "https://jfrog.example.com/api/pypi/pypi/pypi/flask/json"

    def test_pixi_index_url_strips_simple_suffix(self, monkeypatch):
        """`pypi-config.index-url` ends in /simple — must strip it for JSON API."""
        _clean_env(monkeypatch)
        cfg = {
            "pypi-config": {
                "index-url": "https://jfrog/artifactory/api/pypi/pypi/simple",
            },
        }
        chain = _http.resolve_pypi_json_urls("flask", config=cfg)
        # /simple stripped; pypi/<pkg>/json appended
        assert chain[0] == "https://jfrog/artifactory/api/pypi/pypi/pypi/flask/json"
        # Public default still in chain as last resort
        assert chain[-1] == "https://pypi.org/pypi/flask/json"

    def test_pixi_index_url_with_trailing_slash(self, monkeypatch):
        _clean_env(monkeypatch)
        cfg = {
            "pypi-config": {
                "index-url": "https://jfrog/api/pypi/pypi/simple/",
            },
        }
        chain = _http.resolve_pypi_json_urls("flask", config=cfg)
        assert chain[0] == "https://jfrog/api/pypi/pypi/pypi/flask/json"


# ═══════════════════════════════════════════════════════════════════════════
# resolve_github_urls + resolve_github_raw_urls
# ═══════════════════════════════════════════════════════════════════════════

class TestResolveGithubUrls:
    def test_external_default(self, monkeypatch):
        _clean_env(monkeypatch)
        chain = _http.resolve_github_urls("conda-forge/foo", "/archive/main.zip")
        assert chain == ["https://github.com/conda-forge/foo/archive/main.zip"]

    def test_env_var_redirect(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("GITHUB_BASE_URL", "https://jfrog/artifactory/github-mirror")
        chain = _http.resolve_github_urls("conda-forge/foo", "/archive/main.zip")
        assert chain[0] == "https://jfrog/artifactory/github-mirror/conda-forge/foo/archive/main.zip"
        assert chain[-1] == "https://github.com/conda-forge/foo/archive/main.zip"


class TestResolveGithubRawUrls:
    def test_external_default(self, monkeypatch):
        _clean_env(monkeypatch)
        chain = _http.resolve_github_raw_urls("regro/cf-graph", "master", "mappings/x.yaml")
        assert chain == [
            "https://raw.githubusercontent.com/regro/cf-graph/master/mappings/x.yaml",
        ]

    def test_env_var_redirect(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("GITHUB_RAW_BASE_URL", "https://jfrog/raw-mirror")
        chain = _http.resolve_github_raw_urls("regro/cf-graph", "master", "mappings/x.yaml")
        assert chain[0] == "https://jfrog/raw-mirror/regro/cf-graph/master/mappings/x.yaml"


# ═══════════════════════════════════════════════════════════════════════════
# fetch_with_fallback — fault injection (no real HTTP)
# ═══════════════════════════════════════════════════════════════════════════

class _FakeResp:
    """Minimal stand-in for http.client.HTTPResponse usable as context manager."""

    def __init__(self, body: bytes):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self) -> bytes:
        return self._body


def _make_404(url: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url, 404, "Not Found", {}, None)  # type: ignore[arg-type]


def _make_500(url: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url, 500, "Internal Error", {}, None)  # type: ignore[arg-type]


class TestFetchWithFallback:
    def test_first_url_succeeds(self, monkeypatch):
        _clean_env(monkeypatch)
        urls = ["https://a.example", "https://b.example"]

        def fake_open_url(req, timeout):
            return _FakeResp(b'{"ok": true}')

        monkeypatch.setattr(_http, "open_url", fake_open_url)
        result = _http.fetch_with_fallback(urls, return_json=True)
        assert result == {"ok": True}

    def test_404_falls_through_immediately(self, monkeypatch):
        _clean_env(monkeypatch)
        urls = ["https://a.example", "https://b.example"]
        attempts: list[str] = []

        def fake_open_url(req, timeout):
            attempts.append(req.full_url)
            if req.full_url == "https://a.example":
                raise _make_404(req.full_url)
            return _FakeResp(b'{"ok": true}')

        monkeypatch.setattr(_http, "open_url", fake_open_url)
        # retries=2 but 404 should NOT retry — only one attempt at the bad URL
        result = _http.fetch_with_fallback(urls, return_json=True, retries=2)
        assert result == {"ok": True}
        assert attempts == ["https://a.example", "https://b.example"]

    def test_500_retries_then_falls_through(self, monkeypatch):
        _clean_env(monkeypatch)
        urls = ["https://a.example", "https://b.example"]
        attempts: list[str] = []

        def fake_open_url(req, timeout):
            attempts.append(req.full_url)
            if req.full_url == "https://a.example":
                raise _make_500(req.full_url)
            return _FakeResp(b'{"ok": true}')

        # Skip the sleep so the test is fast.
        monkeypatch.setattr(_http, "open_url", fake_open_url)
        monkeypatch.setattr(_http._time, "sleep", lambda s: None)
        result = _http.fetch_with_fallback(urls, return_json=True, retries=2)
        # Retried 2x at first URL, then succeeded at second.
        assert attempts.count("https://a.example") == 2
        assert attempts.count("https://b.example") == 1
        assert result == {"ok": True}

    def test_all_sources_fail_raises(self, monkeypatch):
        _clean_env(monkeypatch)
        urls = ["https://a.example", "https://b.example"]

        def fake_open_url(req, timeout):
            raise _make_500(req.full_url)

        monkeypatch.setattr(_http, "open_url", fake_open_url)
        monkeypatch.setattr(_http._time, "sleep", lambda s: None)
        with pytest.raises(RuntimeError, match="2 source"):
            _http.fetch_with_fallback(urls, retries=1)

    def test_returns_bytes_when_return_json_false(self, monkeypatch):
        _clean_env(monkeypatch)

        def fake_open_url(req, timeout):
            return _FakeResp(b"raw bytes here")

        monkeypatch.setattr(_http, "open_url", fake_open_url)
        result = _http.fetch_with_fallback(["https://a.example"], return_json=False)
        assert result == b"raw bytes here"

    def test_single_string_url_accepted(self, monkeypatch):
        _clean_env(monkeypatch)

        def fake_open_url(req, timeout):
            return _FakeResp(b"ok")

        monkeypatch.setattr(_http, "open_url", fake_open_url)
        result = _http.fetch_with_fallback("https://a.example")
        assert result == b"ok"

    def test_empty_url_list_raises_value_error(self, monkeypatch):
        _clean_env(monkeypatch)
        with pytest.raises(ValueError):
            _http.fetch_with_fallback([])

    def test_429_treated_as_transient(self, monkeypatch):
        """429 (rate-limit) and 408 (timeout) should retry, not skip immediately."""
        _clean_env(monkeypatch)
        urls = ["https://a.example"]
        attempts: list[int] = []

        def fake_open_url(req, timeout):
            attempts.append(1)
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many", {}, None)  # type: ignore[arg-type]

        monkeypatch.setattr(_http, "open_url", fake_open_url)
        monkeypatch.setattr(_http._time, "sleep", lambda s: None)
        with pytest.raises(RuntimeError):
            _http.fetch_with_fallback(urls, retries=3)
        assert len(attempts) == 3  # retried 3x, didn't skip after first 429


# ═══════════════════════════════════════════════════════════════════════════
# read_pixi_config (smoke — actual file read)
# ═══════════════════════════════════════════════════════════════════════════

class TestReadPixiConfig:
    def test_no_config_returns_empty_dict(self, monkeypatch, tmp_path):
        # Point HOME at an empty dir so user config doesn't exist
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        cfg = _http.read_pixi_config()
        assert cfg == {}

    def test_project_local_config_loaded(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        monkeypatch.chdir(tmp_path)
        pixi_dir = tmp_path / ".pixi"
        pixi_dir.mkdir()
        (pixi_dir / "config.toml").write_text(
            'default-channels = ["https://jfrog/api/conda/cf-virtual"]\n'
            'tls-root-certs = "all"\n'
            "[pypi-config]\n"
            'index-url = "https://jfrog/api/pypi/pypi/simple"\n'
        )
        cfg = _http.read_pixi_config()
        assert cfg["default-channels"] == ["https://jfrog/api/conda/cf-virtual"]
        assert cfg["tls-root-certs"] == "all"
        assert cfg["pypi-config"]["index-url"] == "https://jfrog/api/pypi/pypi/simple"

    def test_malformed_config_returns_empty(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        monkeypatch.chdir(tmp_path)
        pixi_dir = tmp_path / ".pixi"
        pixi_dir.mkdir()
        (pixi_dir / "config.toml").write_text("this is not [valid toml")
        cfg = _http.read_pixi_config()
        assert cfg == {}


# ═══════════════════════════════════════════════════════════════════════════
# End-to-end: external + internal scenario, via resolver chain composition
# ═══════════════════════════════════════════════════════════════════════════

class TestEndToEnd:
    """Full external vs internal scenarios — chain composition only, no HTTP."""

    def test_external_baseline_complete(self, monkeypatch):
        """External clone: all 5 resolvers return public defaults only."""
        _clean_env(monkeypatch)
        cfg = {}
        assert _http.resolve_conda_forge_urls(config=cfg) == [
            "https://repo.prefix.dev/conda-forge",
            "https://conda.anaconda.org/conda-forge",
        ]
        assert _http.resolve_pypi_simple_urls(config=cfg) == ["https://pypi.org/simple"]
        assert _http.resolve_pypi_json_urls("requests", config=cfg) == [
            "https://pypi.org/pypi/requests/json"
        ]
        assert _http.resolve_github_urls("foo/bar", "/x") == ["https://github.com/foo/bar/x"]
        assert _http.resolve_github_raw_urls("foo/bar", "main", "x") == [
            "https://raw.githubusercontent.com/foo/bar/main/x"
        ]

    def test_internal_jfrog_routing(self, monkeypatch):
        """Air-gapped JFrog setup: every resolver puts JFrog URL first."""
        _clean_env(monkeypatch)
        monkeypatch.setenv("CONDA_FORGE_BASE_URL", "https://jfrog/api/conda/cf")
        monkeypatch.setenv("PYPI_BASE_URL", "https://jfrog/api/pypi/pypi/simple")
        monkeypatch.setenv("PYPI_JSON_BASE_URL", "https://jfrog/api/pypi/pypi")
        monkeypatch.setenv("GITHUB_BASE_URL", "https://jfrog/github-mirror")
        monkeypatch.setenv("GITHUB_RAW_BASE_URL", "https://jfrog/github-raw-mirror")

        cf = _http.resolve_conda_forge_urls(config={})
        pypi_simple = _http.resolve_pypi_simple_urls(config={})
        pypi_json = _http.resolve_pypi_json_urls("requests", config={})
        github = _http.resolve_github_urls("foo/bar", "/x")
        github_raw = _http.resolve_github_raw_urls("foo/bar", "main", "x")

        assert cf[0] == "https://jfrog/api/conda/cf"
        assert pypi_simple[0] == "https://jfrog/api/pypi/pypi/simple"
        assert pypi_json[0].startswith("https://jfrog/api/pypi/pypi/pypi/requests")
        assert github[0].startswith("https://jfrog/github-mirror/foo/bar")
        assert github_raw[0].startswith("https://jfrog/github-raw-mirror/foo/bar")

        # Public fallbacks still present for graceful degradation
        assert any("anaconda.org" in u for u in cf)
        assert any("pypi.org" in u for u in pypi_simple)
        assert any("github.com" in u for u in github)
