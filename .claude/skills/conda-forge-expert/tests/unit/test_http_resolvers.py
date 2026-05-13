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
        "NPM_BASE_URL",
        "npm_config_registry",
        "NPM_CONFIG_REGISTRY",
        "CRAN_BASE_URL",
        "CPAN_BASE_URL",
        "LUAROCKS_BASE_URL",
        "CRATES_BASE_URL",
        "RUBYGEMS_BASE_URL",
        "MAVEN_BASE_URL",
        "NUGET_BASE_URL",
        "GITHUB_API_BASE_URL",
        "GITLAB_API_BASE_URL",
        "CODEBERG_API_BASE_URL",
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


class TestResolveNpmUrls:
    def test_external_default(self, monkeypatch):
        _clean_env(monkeypatch)
        chain = _http.resolve_npm_urls("codex")
        assert chain == ["https://registry.npmjs.org/codex"]

    def test_npm_base_url_env_var(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("NPM_BASE_URL", "https://jfrog/api/npm/npm-mirror")
        chain = _http.resolve_npm_urls("codex")
        assert chain[0] == "https://jfrog/api/npm/npm-mirror/codex"
        assert chain[-1] == "https://registry.npmjs.org/codex"

    def test_npm_config_registry_env_var(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("npm_config_registry", "https://jfrog/api/npm/npm/")
        chain = _http.resolve_npm_urls("codex")
        # Trailing slash is stripped; npm_config_registry is the npm CLI standard.
        assert chain[0] == "https://jfrog/api/npm/npm/codex"

    def test_npm_base_url_outranks_npm_config_registry(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("NPM_BASE_URL", "https://jfrog/api/npm/cfe")
        monkeypatch.setenv("npm_config_registry", "https://jfrog/api/npm/npm/")
        chain = _http.resolve_npm_urls("codex")
        assert chain[0] == "https://jfrog/api/npm/cfe/codex"
        assert chain[1] == "https://jfrog/api/npm/npm/codex"

    def test_scoped_package_name_preserved(self, monkeypatch):
        _clean_env(monkeypatch)
        # Caller pre-encodes scoped names; resolver appends verbatim.
        chain = _http.resolve_npm_urls("@openai%2Fcodex")
        assert chain == ["https://registry.npmjs.org/@openai%2Fcodex"]


# ═══════════════════════════════════════════════════════════════════════════
# Phase L registry resolvers — cran / cpan / luarocks / crates / rubygems /
# maven / nuget — same shape as resolve_npm_urls
# ═══════════════════════════════════════════════════════════════════════════

class TestResolveCranUrls:
    def test_external_default(self, monkeypatch):
        _clean_env(monkeypatch)
        assert _http.resolve_cran_urls("ggplot2") == [
            "https://crandb.r-pkg.org/ggplot2",
        ]

    def test_env_var_redirect(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("CRAN_BASE_URL", "https://jfrog/api/cran/cran-mirror")
        chain = _http.resolve_cran_urls("ggplot2")
        assert chain[0] == "https://jfrog/api/cran/cran-mirror/ggplot2"
        assert chain[-1] == "https://crandb.r-pkg.org/ggplot2"


class TestResolveCpanUrls:
    def test_external_default(self, monkeypatch):
        _clean_env(monkeypatch)
        assert _http.resolve_cpan_urls("Moose") == [
            "https://fastapi.metacpan.org/v1/release/Moose",
        ]

    def test_env_var_redirect(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("CPAN_BASE_URL", "https://jfrog/cpan")
        chain = _http.resolve_cpan_urls("Moose")
        assert chain[0] == "https://jfrog/cpan/v1/release/Moose"


class TestResolveLuarocksUrls:
    def test_external_default(self, monkeypatch):
        _clean_env(monkeypatch)
        assert _http.resolve_luarocks_urls("lua-cjson") == [
            "https://luarocks.org/m/lua-cjson",
        ]

    def test_env_var_redirect(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("LUAROCKS_BASE_URL", "https://jfrog/luarocks")
        chain = _http.resolve_luarocks_urls("lua-cjson")
        assert chain[0] == "https://jfrog/luarocks/m/lua-cjson"


class TestResolveCratesUrls:
    def test_external_default(self, monkeypatch):
        _clean_env(monkeypatch)
        assert _http.resolve_crates_urls("serde") == [
            "https://crates.io/api/v1/crates/serde",
        ]

    def test_env_var_redirect(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("CRATES_BASE_URL", "https://jfrog/cargo")
        chain = _http.resolve_crates_urls("serde")
        assert chain[0] == "https://jfrog/cargo/api/v1/crates/serde"


class TestResolveRubygemsUrls:
    def test_external_default(self, monkeypatch):
        _clean_env(monkeypatch)
        assert _http.resolve_rubygems_urls("rails") == [
            "https://rubygems.org/api/v1/gems/rails.json",
        ]

    def test_env_var_redirect(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("RUBYGEMS_BASE_URL", "https://jfrog/gems")
        chain = _http.resolve_rubygems_urls("rails")
        assert chain[0] == "https://jfrog/gems/api/v1/gems/rails.json"


class TestResolveMavenUrls:
    def test_external_default(self, monkeypatch):
        _clean_env(monkeypatch)
        chain = _http.resolve_maven_urls("solrsearch/select?q=foo&wt=json")
        assert chain == ["https://search.maven.org/solrsearch/select?q=foo&wt=json"]

    def test_env_var_redirect(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("MAVEN_BASE_URL", "https://jfrog/maven")
        chain = _http.resolve_maven_urls("solrsearch/select?q=foo")
        assert chain[0] == "https://jfrog/maven/solrsearch/select?q=foo"


class TestResolveNugetUrls:
    def test_external_default_lowercases_name(self, monkeypatch):
        _clean_env(monkeypatch)
        # NuGet's flat-container requires lowercase package ids
        chain = _http.resolve_nuget_urls("Newtonsoft.Json")
        assert chain == [
            "https://api.nuget.org/v3-flatcontainer/newtonsoft.json/index.json",
        ]

    def test_env_var_redirect(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("NUGET_BASE_URL", "https://jfrog/nuget")
        chain = _http.resolve_nuget_urls("Newtonsoft.Json")
        assert chain[0] == "https://jfrog/nuget/v3-flatcontainer/newtonsoft.json/index.json"


# ═══════════════════════════════════════════════════════════════════════════
# resolve_github_api_urls / resolve_gitlab_api_urls / resolve_codeberg_api_urls
# Phase K REST tail + GraphQL endpoint. Each takes an optional path suffix.
# ═══════════════════════════════════════════════════════════════════════════

class TestResolveGithubApiUrls:
    def test_base_default_no_suffix(self, monkeypatch):
        _clean_env(monkeypatch)
        assert _http.resolve_github_api_urls() == ["https://api.github.com"]

    def test_suffix_appended(self, monkeypatch):
        _clean_env(monkeypatch)
        chain = _http.resolve_github_api_urls("repos/conda-forge/numpy/releases/latest")
        assert chain == [
            "https://api.github.com/repos/conda-forge/numpy/releases/latest",
        ]

    def test_graphql_suffix(self, monkeypatch):
        _clean_env(monkeypatch)
        chain = _http.resolve_github_api_urls("graphql")
        assert chain == ["https://api.github.com/graphql"]

    def test_ghes_env_redirect(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("GITHUB_API_BASE_URL", "https://ghes.example.com/api")
        chain = _http.resolve_github_api_urls("graphql")
        assert chain[0] == "https://ghes.example.com/api/graphql"
        assert chain[-1] == "https://api.github.com/graphql"

    def test_leading_slash_in_suffix_tolerated(self, monkeypatch):
        _clean_env(monkeypatch)
        # Callers may or may not include a leading slash; both should produce
        # the same URL.
        assert _http.resolve_github_api_urls("/graphql") == _http.resolve_github_api_urls("graphql")


class TestResolveGitlabApiUrls:
    def test_base_default(self, monkeypatch):
        _clean_env(monkeypatch)
        assert _http.resolve_gitlab_api_urls() == ["https://gitlab.com/api/v4"]

    def test_suffix_appended(self, monkeypatch):
        _clean_env(monkeypatch)
        chain = _http.resolve_gitlab_api_urls("projects/foo%2Fbar/releases?per_page=1")
        assert chain == [
            "https://gitlab.com/api/v4/projects/foo%2Fbar/releases?per_page=1",
        ]

    def test_self_hosted_env_redirect(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("GITLAB_API_BASE_URL", "https://gitlab.internal/api/v4")
        chain = _http.resolve_gitlab_api_urls("projects/1234")
        assert chain[0] == "https://gitlab.internal/api/v4/projects/1234"


class TestResolveCodebergApiUrls:
    def test_base_default(self, monkeypatch):
        _clean_env(monkeypatch)
        assert _http.resolve_codeberg_api_urls() == ["https://codeberg.org/api/v1"]

    def test_suffix_appended(self, monkeypatch):
        _clean_env(monkeypatch)
        chain = _http.resolve_codeberg_api_urls("repos/forgejo/forgejo/releases/latest")
        assert chain == [
            "https://codeberg.org/api/v1/repos/forgejo/forgejo/releases/latest",
        ]

    def test_gitea_self_hosted_env_redirect(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("CODEBERG_API_BASE_URL", "https://gitea.internal/api/v1")
        chain = _http.resolve_codeberg_api_urls("repos/x/y")
        assert chain[0] == "https://gitea.internal/api/v1/repos/x/y"


# ═══════════════════════════════════════════════════════════════════════════
# atomic_writer / atomic_write_bytes / atomic_write_text
# Prevents truncated files when a SIGINT/OOM hits mid-write — was a real
# failure mode for cve_manager (corrupt CVE DB) and mapping_manager
# (corrupt PyPI→conda mapping cache).
# ═══════════════════════════════════════════════════════════════════════════

import json as _json


class TestAtomicWriter:
    def test_success_replaces_target(self, tmp_path):
        target = tmp_path / "out.json"
        target.write_text('{"prior": "contents"}')
        with _http.atomic_writer(target, "w") as f:
            _json.dump({"new": "value"}, f)
        assert _json.loads(target.read_text()) == {"new": "value"}

    def test_creates_parent_dir(self, tmp_path):
        target = tmp_path / "nested" / "sub" / "out.txt"
        with _http.atomic_writer(target, "w") as f:
            f.write("hello")
        assert target.read_text() == "hello"

    def test_exception_preserves_prior_contents(self, tmp_path):
        target = tmp_path / "out.txt"
        target.write_text("original")
        with pytest.raises(RuntimeError):
            with _http.atomic_writer(target, "w") as f:
                f.write("partial")
                raise RuntimeError("simulated interrupt")
        # Prior contents intact
        assert target.read_text() == "original"
        # Tmp sibling cleaned up
        tmp_path_sibling = target.with_suffix(target.suffix + ".tmp")
        assert not tmp_path_sibling.exists()

    def test_exception_when_target_didnt_exist_leaves_no_file(self, tmp_path):
        target = tmp_path / "out.txt"
        assert not target.exists()
        with pytest.raises(RuntimeError):
            with _http.atomic_writer(target, "w") as f:
                f.write("partial")
                raise RuntimeError("boom")
        assert not target.exists()
        assert not target.with_suffix(target.suffix + ".tmp").exists()

    def test_binary_mode(self, tmp_path):
        target = tmp_path / "out.bin"
        with _http.atomic_writer(target, "wb") as f:
            f.write(b"\x00\x01\x02\xff")
        assert target.read_bytes() == b"\x00\x01\x02\xff"


class TestAtomicWriteBytes:
    def test_writes_then_replaces(self, tmp_path):
        target = tmp_path / "cache.bin"
        target.write_bytes(b"old")
        _http.atomic_write_bytes(target, b"new\x00bytes")
        assert target.read_bytes() == b"new\x00bytes"

    def test_creates_parent_dir(self, tmp_path):
        target = tmp_path / "nested" / "cache.bin"
        _http.atomic_write_bytes(target, b"hello")
        assert target.read_bytes() == b"hello"


class TestAtomicWriteText:
    def test_writes_text_with_default_utf8(self, tmp_path):
        target = tmp_path / "out.txt"
        _http.atomic_write_text(target, "café ☕")
        assert target.read_text(encoding="utf-8") == "café ☕"

    def test_custom_encoding(self, tmp_path):
        target = tmp_path / "out.txt"
        _http.atomic_write_text(target, "hello", encoding="ascii")
        assert target.read_bytes() == b"hello"


# ═══════════════════════════════════════════════════════════════════════════
# fetch_to_file_resumable — streaming download with Range/resume
# Primary use: cve_manager's 4 GB OSV all.zip. Tests cover the four key
# branches: fresh 200, resume 206, server-ignores-Range restart, 416 retry.
# ═══════════════════════════════════════════════════════════════════════════


class _FakeResponse:
    """Mimics urllib HTTPResponse: chunked .read() + .status + ctx manager."""

    def __init__(self, status: int, body: bytes):
        self.status = status
        self._body = body
        self._pos = 0

    def read(self, n: int | None = None) -> bytes:
        if n is None or n < 0:
            chunk = self._body[self._pos:]
            self._pos = len(self._body)
        else:
            chunk = self._body[self._pos: self._pos + n]
            self._pos += len(chunk)
        return chunk

    def getcode(self) -> int:  # back-compat with pre-3.9 HTTPResponse
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class TestFetchToFileResumable:
    def test_fresh_download_writes_target(self, tmp_path, monkeypatch):
        target = tmp_path / "out.bin"
        payload = b"hello world" * 1000  # 11 KB

        def fake_urlopen(req, timeout=None):
            # No prior .part → no Range header expected
            assert req.headers.get("Range") is None
            return _FakeResponse(200, payload)

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        result = _http.fetch_to_file_resumable(target, ["https://example.com/out.bin"])
        assert result == target
        assert target.read_bytes() == payload
        # .part file removed via os.replace
        assert not target.with_suffix(target.suffix + ".part").exists()

    def test_resume_appends_from_existing_part(self, tmp_path, monkeypatch):
        target = tmp_path / "out.bin"
        part = target.with_suffix(target.suffix + ".part")
        # Simulate a previous interrupted run: 500 bytes already on disk
        partial = b"A" * 500
        part.write_bytes(partial)
        # The server "knows" the remaining bytes
        remaining = b"B" * 1500

        captured_range: dict[str, str | None] = {}

        def fake_urlopen(req, timeout=None):
            captured_range["value"] = req.headers.get("Range")
            return _FakeResponse(206, remaining)

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        result = _http.fetch_to_file_resumable(target, ["https://example.com/out.bin"])
        assert result == target
        # Range request was sent
        assert captured_range["value"] == "bytes=500-"
        # Final file is partial + remaining
        assert target.read_bytes() == partial + remaining

    def test_server_ignores_range_restarts_from_zero(self, tmp_path, monkeypatch):
        target = tmp_path / "out.bin"
        part = target.with_suffix(target.suffix + ".part")
        # Previous .part claims 500 bytes downloaded
        part.write_bytes(b"STALE" * 100)
        # Server returns 200 (full body) instead of 206
        full_body = b"FRESH" * 500

        def fake_urlopen(req, timeout=None):
            # The Range header was sent — but the server is ignoring it
            assert req.headers.get("Range") == "bytes=500-"
            return _FakeResponse(200, full_body)

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        result = _http.fetch_to_file_resumable(target, ["https://example.com/out.bin"])
        assert result == target
        # Final file is the FULL body, NOT stale-prefix + full
        assert target.read_bytes() == full_body

    def test_416_discards_stale_part_and_retries(self, tmp_path, monkeypatch):
        import urllib.error
        target = tmp_path / "out.bin"
        part = target.with_suffix(target.suffix + ".part")
        # .part is bigger than the actual server file (stale / corrupt)
        part.write_bytes(b"X" * 10_000)
        # First attempt: 416 (Range Not Satisfiable). Second attempt:
        # fresh 200 since we should have discarded the .part by then.
        full_body = b"CLEAN" * 200
        call_count = {"n": 0}

        def fake_urlopen(req, timeout=None):
            call_count["n"] += 1
            if call_count["n"] == 1:
                # First call: Range header from stale .part → 416
                assert req.headers.get("Range") == "bytes=10000-"
                raise urllib.error.HTTPError(
                    req.full_url, 416, "Range Not Satisfiable", req.headers, None
                )
            # Second call: no Range header (stale .part was deleted)
            assert req.headers.get("Range") is None
            return _FakeResponse(200, full_body)

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        result = _http.fetch_to_file_resumable(target, ["https://example.com/out.bin"])
        assert result == target
        assert target.read_bytes() == full_body
        assert call_count["n"] == 2

    def test_parent_directory_created(self, tmp_path, monkeypatch):
        target = tmp_path / "nested" / "sub" / "out.bin"
        assert not target.parent.exists()

        def fake_urlopen(req, timeout=None):
            return _FakeResponse(200, b"data")

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        result = _http.fetch_to_file_resumable(target, ["https://example.com/out.bin"])
        assert result == target
        assert target.read_bytes() == b"data"

    def test_all_urls_exhausted_raises(self, tmp_path, monkeypatch):
        import urllib.error
        target = tmp_path / "out.bin"

        def fake_urlopen(req, timeout=None):
            raise urllib.error.HTTPError(
                req.full_url, 503, "Service Unavailable", req.headers, None
            )

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        with pytest.raises(RuntimeError, match="exhausted"):
            _http.fetch_to_file_resumable(
                target, ["https://example.com/out.bin"], max_retries=1
            )

    def test_chunked_read_assembles_full_body(self, tmp_path, monkeypatch):
        """Confirm a body larger than one chunk reads cleanly across iterations."""
        target = tmp_path / "out.bin"
        # 5 MB body, default chunk is 1 MB → 5 read() calls minimum
        payload = bytes(range(256)) * 20_000  # ~5 MB
        assert len(payload) > 1024 * 1024 * 4

        def fake_urlopen(req, timeout=None):
            return _FakeResponse(200, payload)

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        result = _http.fetch_to_file_resumable(target, ["https://example.com/out.bin"])
        assert result == target
        assert target.read_bytes() == payload


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
# auth_headers_for — shared with make_request, used by requests-based callers
# ═══════════════════════════════════════════════════════════════════════════

class TestAuthHeadersFor:
    def test_unauthenticated_returns_empty(self, monkeypatch):
        _clean_env(monkeypatch)
        # No netrc lookup in CI — point NETRC at a non-existent path
        monkeypatch.setenv("NETRC", "/nonexistent/.netrc")
        assert _http.auth_headers_for("https://registry.npmjs.org/codex") == {}

    def test_jfrog_api_key_wins(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("NETRC", "/nonexistent/.netrc")
        monkeypatch.setenv("JFROG_API_KEY", "secret-token")
        monkeypatch.setenv("JFROG_USERNAME", "ignored")
        monkeypatch.setenv("JFROG_PASSWORD", "ignored")
        headers = _http.auth_headers_for("https://artifactory/api/npm/npm/codex")
        assert headers == {"X-JFrog-Art-Api": "secret-token"}

    def test_jfrog_username_password_basic_auth(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("NETRC", "/nonexistent/.netrc")
        monkeypatch.setenv("JFROG_USERNAME", "alice")
        monkeypatch.setenv("JFROG_PASSWORD", "hunter2")
        headers = _http.auth_headers_for("https://artifactory/api/npm/npm/codex")
        # Basic base64('alice:hunter2') == 'YWxpY2U6aHVudGVyMg=='
        assert headers == {"Authorization": "Basic YWxpY2U6aHVudGVyMg=="}

    def test_github_token_only_attaches_to_github_hosts(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("NETRC", "/nonexistent/.netrc")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_xyz")
        assert _http.auth_headers_for("https://api.github.com/repos/x/y") == {
            "Authorization": "Bearer ghp_xyz"
        }
        # Non-GitHub host with GITHUB_TOKEN set and no other auth → empty
        assert _http.auth_headers_for("https://registry.npmjs.org/codex") == {}

    def test_make_request_inherits_auth_headers(self, monkeypatch):
        """make_request and auth_headers_for share the same chain."""
        _clean_env(monkeypatch)
        monkeypatch.setenv("NETRC", "/nonexistent/.netrc")
        monkeypatch.setenv("JFROG_API_KEY", "k")
        req = _http.make_request("https://artifactory/x")
        assert req.headers.get("X-jfrog-art-api") == "k"

    def test_make_request_extra_headers_win(self, monkeypatch):
        """Caller-supplied headers in make_request should not be clobbered."""
        _clean_env(monkeypatch)
        monkeypatch.setenv("NETRC", "/nonexistent/.netrc")
        monkeypatch.setenv("JFROG_API_KEY", "auto-token")
        req = _http.make_request(
            "https://artifactory/x",
            extra_headers={"X-JFrog-Art-Api": "caller-token"},
        )
        assert req.headers.get("X-jfrog-art-api") == "caller-token"


# ═══════════════════════════════════════════════════════════════════════════
# End-to-end: external + internal scenario, via resolver chain composition
# ═══════════════════════════════════════════════════════════════════════════

class TestEndToEnd:
    """Full external vs internal scenarios — chain composition only, no HTTP."""

    def test_external_baseline_complete(self, monkeypatch):
        """External clone: all 6 resolvers return public defaults only."""
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
        assert _http.resolve_npm_urls("codex") == ["https://registry.npmjs.org/codex"]

    def test_internal_jfrog_routing(self, monkeypatch):
        """Air-gapped JFrog setup: every resolver puts JFrog URL first."""
        _clean_env(monkeypatch)
        monkeypatch.setenv("CONDA_FORGE_BASE_URL", "https://jfrog/api/conda/cf")
        monkeypatch.setenv("PYPI_BASE_URL", "https://jfrog/api/pypi/pypi/simple")
        monkeypatch.setenv("PYPI_JSON_BASE_URL", "https://jfrog/api/pypi/pypi")
        monkeypatch.setenv("GITHUB_BASE_URL", "https://jfrog/github-mirror")
        monkeypatch.setenv("GITHUB_RAW_BASE_URL", "https://jfrog/github-raw-mirror")
        monkeypatch.setenv("NPM_BASE_URL", "https://jfrog/api/npm/npm")

        cf = _http.resolve_conda_forge_urls(config={})
        pypi_simple = _http.resolve_pypi_simple_urls(config={})
        pypi_json = _http.resolve_pypi_json_urls("requests", config={})
        github = _http.resolve_github_urls("foo/bar", "/x")
        github_raw = _http.resolve_github_raw_urls("foo/bar", "main", "x")
        npm = _http.resolve_npm_urls("codex")

        assert cf[0] == "https://jfrog/api/conda/cf"
        assert pypi_simple[0] == "https://jfrog/api/pypi/pypi/simple"
        assert pypi_json[0].startswith("https://jfrog/api/pypi/pypi/pypi/requests")
        assert github[0].startswith("https://jfrog/github-mirror/foo/bar")
        assert github_raw[0].startswith("https://jfrog/github-raw-mirror/foo/bar")
        assert npm[0] == "https://jfrog/api/npm/npm/codex"

        # Public fallbacks still present for graceful degradation
        assert any("anaconda.org" in u for u in cf)
        assert any("pypi.org" in u for u in pypi_simple)
        assert any("github.com" in u for u in github)
        assert any("registry.npmjs.org" in u for u in npm)
