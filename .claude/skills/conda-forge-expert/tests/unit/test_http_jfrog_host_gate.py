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
    """Every test starts with no JFrog / mirror env vars AND an empty pixi
    config.

    Stubbing `read_pixi_config` is not optional hygiene: without it the
    allowlist reads the DEVELOPER'S real pixi config chain (`./.pixi/
    config.toml`, `~/.pixi/config.toml`, `/etc/pixi/config.toml`), so every
    set-equality assertion below would fail on exactly the enterprise machine
    this feature exists for — the suite would be green here and red for the
    operator. Tests that need pixi hosts re-stub it themselves.
    """
    for key in list(os.environ):
        if key.endswith("_BASE_URL") or key.startswith("JFROG_"):
            monkeypatch.delenv(key, raising=False)
    for key in _http._EXTRA_MIRROR_ENV_VARS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(_http, "read_pixi_config", lambda: {})


class TestHostOf:
    """`_host_of` — the single host-derivation used by both halves of the
    allowlist and by `auth_headers_for` itself. It parses with
    `urlparse().hostname`; the `netloc.split(":")[0]` it replaced was wrong
    on two shapes that decide whether a credential is withheld or leaked."""

    def test_strips_port(self):
        assert _http._host_of("https://mirror.example.com:8081/cf") == "mirror.example.com"

    def test_strips_userinfo(self):
        """`https://user:token@host/` is a routine Artifactory form.
        `netloc.split(":")[0]` returns the USERNAME, so the real mirror never
        enters the allowlist and its own credential is silently withheld."""
        assert (
            _http._host_of("https://svc:tok@artifactory.corp.com/api/conda/cf")
            == "artifactory.corp.com"
        )

    def test_strips_userinfo_and_port_together(self):
        assert (
            _http._host_of("https://svc:tok@artifactory.corp.com:8081/api/conda/cf")
            == "artifactory.corp.com"
        )

    def test_ipv6_literals_are_distinguished(self):
        """`netloc.split(":")[0]` collapsed EVERY IPv6 host to `[2001`, so an
        unrelated address sharing that prefix matched the allowlist and
        received the credential — the leak class this gate exists to close."""
        a = _http._host_of("https://[2001:db8::1]:8081/x")
        b = _http._host_of("https://[2001:db8::2]/y")
        assert a == "2001:db8::1"
        assert b == "2001:db8::2"
        assert a != b

    def test_lowercases(self):
        assert _http._host_of("https://MIRROR.Example.COM/cf") == "mirror.example.com"


class TestPublicDefaultHosts:
    """Public fallback hosts can never enter the enterprise allowlist."""

    def test_derived_from_module_defaults_not_a_hand_kept_list(self):
        hosts = _http._public_default_hosts()
        # Sampled across several resolver families — all come from the
        # `_DEFAULT_*` globals, so adding a resolver extends this for free.
        assert {"pypi.org", "conda.anaconda.org", "repo.prefix.dev",
                "registry.npmjs.org", "github.com"} <= hosts

    def test_base_url_pinned_to_a_public_default_contributes_no_host(self, monkeypatch):
        """A merely redundant `PYPI_BASE_URL=https://pypi.org/simple` would
        otherwise mark the public host "configured" and re-open the leak."""
        monkeypatch.setenv("PYPI_BASE_URL", "https://pypi.org/simple")
        assert "pypi.org" not in _http._configured_enterprise_hosts()

    def test_jfrog_credential_not_sent_to_a_public_default_named_by_a_base_url(
        self, monkeypatch
    ):
        monkeypatch.setenv("PYPI_BASE_URL", "https://pypi.org/simple")
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        assert _http.auth_headers_for("https://pypi.org/simple/example/") == {}


class TestExtraMirrorEnvVars:
    def test_npm_native_registry_var_is_allowlisted(self, monkeypatch):
        """`resolve_npm_urls` honours npm's own `npm_config_registry`/
        `NPM_CONFIG_REGISTRY`, neither of which ends in `_BASE_URL`. An
        operator routing npm at Artifactory the npm-native way must still
        clear the gate, or their mirror 401s."""
        monkeypatch.setenv("npm_config_registry", "https://npm.corp.internal/repo")
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        headers = _http.auth_headers_for("https://npm.corp.internal/repo/example")
        assert headers.get("X-JFrog-Art-Api") == "secret-key"


class TestGateShortCircuit:
    def test_allowlist_not_derived_when_no_jfrog_credential_is_set(self, monkeypatch):
        """The allowlist gates a JFrog credential and nothing else, so with no
        credential set there is nothing to gate. Deriving it anyway costs an
        os.environ walk plus stat+TOML-parse of the pixi chain on EVERY
        outbound request."""
        calls = []
        monkeypatch.setattr(
            _http,
            "_configured_enterprise_hosts",
            lambda: calls.append(1) or set(),
        )
        _http.auth_headers_for("https://example.com/x")
        assert calls == []

    def test_allowlist_still_derived_when_a_credential_is_set(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            _http,
            "_configured_enterprise_hosts",
            lambda: calls.append(1) or {"example.com"},
        )
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        _http.auth_headers_for("https://example.com/x")
        assert calls == [1]


class TestPixiConfigReadFailure:
    def test_read_pixi_config_raising_does_not_break_every_request(self, monkeypatch):
        """`read_pixi_config` builds its candidate list with `Path.home()`,
        which raises RuntimeError when neither HOME nor a passwd entry
        resolves (rootless / arbitrary-UID containers). Before the gate,
        that was confined to the resolver paths; the gate put it on every
        outbound request, so an unguarded raise would take down all HTTP."""
        def _boom():
            raise RuntimeError("Could not determine home directory.")

        monkeypatch.setattr(_http, "read_pixi_config", _boom)
        monkeypatch.setenv("CONDA_FORGE_BASE_URL", "https://mirror.example.com/cf")
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        headers = _http.auth_headers_for("https://mirror.example.com/cf/repodata.json")
        assert headers.get("X-JFrog-Art-Api") == "secret-key"


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

    def test_env_var_host_with_port_matches_request_host_without_port(self, monkeypatch):
        """Regression guard: netloc includes the port, so an unstripped
        comparison would treat `mirror.example.com:8081` (from the env var)
        and `mirror.example.com` (from the request URL) as different hosts —
        matches `netrc_credentials`'s own port-stripping convention."""
        monkeypatch.setenv("CONDA_FORGE_BASE_URL", "https://mirror.example.com:8081/cf")
        assert "mirror.example.com" in _http._configured_enterprise_hosts()


class TestPixiConfiguredHosts:
    """`_pixi_configured_hosts` / `_configured_enterprise_hosts`'s pixi-config
    half. `docs/reference/pixi-config-jfrog.example.toml` documents
    project-local `.pixi/config.toml` (no env vars at all) as the recommended
    enterprise setup for this repo — an env-var-only allowlist would silently
    stop attaching JFrog credentials for that documented, real setup path."""

    def test_empty_config_contributes_no_hosts(self):
        assert _http._pixi_configured_hosts(config={}) == set()

    def test_derives_host_from_mirrors_targets(self):
        cfg = {
            "mirrors": {
                "https://conda.anaconda.org/conda-forge": [
                    "https://mycompany.jfrog.io/artifactory/conda-forge-remote",
                ]
            }
        }
        assert _http._pixi_configured_hosts(config=cfg) == {"mycompany.jfrog.io"}

    def test_derives_host_from_default_channels(self):
        cfg = {"default-channels": ["https://mycompany.jfrog.io/artifactory/conda-forge-remote"]}
        assert _http._pixi_configured_hosts(config=cfg) == {"mycompany.jfrog.io"}

    def test_derives_host_from_pypi_index_url_and_extra_index_urls(self):
        cfg = {
            "pypi-config": {
                "index-url": "https://mycompany.jfrog.io/artifactory/api/pypi/pypi/simple",
                "extra-index-urls": ["https://other.example.com/simple"],
            }
        }
        assert _http._pixi_configured_hosts(config=cfg) == {
            "mycompany.jfrog.io",
            "other.example.com",
        }

    def test_malformed_pixi_url_contributes_no_host_and_does_not_crash(self):
        cfg = {"default-channels": ["https://[oops", "https://good.example.com/cf"]}
        assert _http._pixi_configured_hosts(config=cfg) == {"good.example.com"}

    def test_public_default_fallbacks_are_not_pixi_configured(self):
        """The resolvers' own public-default fallbacks (repo.prefix.dev,
        pypi.org, ...) must never appear here — mixing them in would always
        mark the public host "configured" and defeat the allowlist.

        The config below NAMES those public hosts explicitly; asserting
        against an empty `config={}` (as this test first did) could not fail
        no matter what the implementation returned."""
        cfg = {
            "default-channels": ["https://repo.prefix.dev/conda-forge"],
            "pypi-config": {"index-url": "https://pypi.org/simple"},
            "mirrors": {
                "https://conda.anaconda.org/conda-forge": [
                    "https://conda.anaconda.org/conda-forge",
                    "https://mycompany.jfrog.io/artifactory/conda-forge-remote",
                ]
            },
        }
        hosts = _http._pixi_configured_hosts(config=cfg)
        assert "repo.prefix.dev" not in hosts
        assert "pypi.org" not in hosts
        assert "conda.anaconda.org" not in hosts
        # ...while the genuinely enterprise host alongside them survives.
        assert hosts == {"mycompany.jfrog.io"}

    def test_configured_enterprise_hosts_unions_env_and_pixi_derived_hosts(self, monkeypatch):
        monkeypatch.setenv("CONDA_FORGE_BASE_URL", "https://env-configured.example.com/cf")
        monkeypatch.setattr(
            _http,
            "read_pixi_config",
            lambda: {"default-channels": ["https://pixi-configured.example.com/cf"]},
        )
        hosts = _http._configured_enterprise_hosts()
        assert hosts == {"env-configured.example.com", "pixi-configured.example.com"}

    def test_jfrog_credential_attaches_to_pixi_only_configured_host_with_no_base_url_var(
        self, monkeypatch
    ):
        """The actual regression this closes: a pure pixi-config enterprise
        setup (no `*_BASE_URL` env vars at all — the documented, recommended
        setup) must still receive the JFrog credential, not silently lose
        it."""
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        monkeypatch.setattr(
            _http,
            "read_pixi_config",
            lambda: {
                "default-channels": ["https://mycompany.jfrog.io/artifactory/conda-forge-remote"]
            },
        )
        headers = _http.auth_headers_for(
            "https://mycompany.jfrog.io/artifactory/conda-forge-remote/linux-64/repodata.json"
        )
        assert headers.get("X-JFrog-Art-Api") == "secret-key"


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

    def test_jfrog_credential_never_shadows_github_token_even_if_a_base_url_resolves_to_github(
        self, monkeypatch
    ):
        """Regression guard: `is_configured_host` used to check ONLY "is this
        host in the derived set", not "was it specifically configured for
        JFrog" — so an operator with an unrelated `*_BASE_URL` var that
        happens to resolve to github.com/api.github.com, plus JFROG_API_KEY
        set for a DIFFERENT mirror, would have the JFrog branch win the
        if/elif chain for github.com requests, sending the JFrog credential
        to GitHub and silencing GITHUB_TOKEN entirely. github.com/
        api.github.com must always take the dedicated GitHub branch.

        The env-var route into the allowlist cannot express this premise:
        `_public_default_hosts()` already contains github.com/api.github.com
        and is subtracted from both halves, so `SOME_MIRROR_BASE_URL=
        https://github.com/...` yields an EMPTY allowlist and the assertions
        below would hold with or without the `not is_github_host` clause they
        exist to guard. Force the host into the allowlist directly instead, so
        removing that clause actually reds this test."""
        monkeypatch.setenv("JFROG_API_KEY", "unrelated-jfrog-secret")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_dummy")
        monkeypatch.setattr(
            _http,
            "_configured_enterprise_hosts",
            lambda: {"api.github.com", "github.com"},
        )

        headers = _http.auth_headers_for("https://api.github.com/repos/foo/bar")

        assert "X-JFrog-Art-Api" not in headers
        assert headers.get("Authorization") == "Bearer ghp_dummy"


class TestNetrcHostDerivation:
    """Story 5.5, third review pass.

    `netrc_credentials` was the third host-parse in this file and the one the
    previous pass did not migrate — still `urlparse().netloc.split(":")[0]`,
    the exact form the retro's own new constraint bans.
    """

    def test_userinfo_bearing_url_matches_the_real_machine_entry(
        self, monkeypatch, tmp_path
    ):
        """`https://svc:tok@artifactory.corp/...` is a routine Artifactory
        form. The old parse yielded `svc` — the USERNAME — which matches no
        `machine` line, so `netrc.authenticators` fell through to `default`
        and sent an unrelated credential to the mirror the operator had a
        correct entry for."""
        netrc_path = tmp_path / ".netrc"
        netrc_path.write_text(
            "machine artifactory.corp login REALUSER password REALPASS\n"
            "default login DEFAULTUSER password DEFAULTPASS\n"
        )
        monkeypatch.setenv("NETRC", str(netrc_path))

        creds = _http.netrc_credentials(
            "https://svc:tok@artifactory.corp/api/conda/cf/repodata.json"
        )

        assert creds == ("REALUSER", "REALPASS")

    def test_port_is_stripped_when_matching_a_machine_entry(
        self, monkeypatch, tmp_path
    ):
        netrc_path = tmp_path / ".netrc"
        netrc_path.write_text(
            "machine artifactory.corp login REALUSER password REALPASS\n"
        )
        monkeypatch.setenv("NETRC", str(netrc_path))

        creds = _http.netrc_credentials("https://artifactory.corp:8081/api/conda/cf")

        assert creds == ("REALUSER", "REALPASS")

    def test_uppercase_machine_line_still_matches_the_host(
        self, monkeypatch, tmp_path
    ):
        """Fourth-pass regression. `_host_of` is `urlparse().hostname`, which
        LOWERCASES; `netrc.authenticators` is an exact dict lookup over the
        `machine` tokens as spelled in the file and folds nothing. So moving
        this function to `_host_of` silently stopped matching a perfectly
        legal `machine ARTIFACTORY.CORP.COM` and fell through to `default` —
        reintroducing, by a different route, the exact
        wrong-credential-to-the-mirror failure the move was made to fix.
        Reproduced before the fix: returned ('DEFAULTUSER', 'DEFAULTPASS')."""
        netrc_path = tmp_path / ".netrc"
        netrc_path.write_text(
            "machine ARTIFACTORY.CORP.COM login REALUSER password REALPASS\n"
            "default login DEFAULTUSER password DEFAULTPASS\n"
        )
        monkeypatch.setenv("NETRC", str(netrc_path))

        creds = _http.netrc_credentials("https://artifactory.corp.com/api/conda/cf")

        assert creds == ("REALUSER", "REALPASS")

    def test_default_entry_still_applies_when_no_machine_line_matches(
        self, monkeypatch, tmp_path
    ):
        """The case-insensitive match must not cost `default` its documented
        meaning ("any machine not named above")."""
        netrc_path = tmp_path / ".netrc"
        netrc_path.write_text(
            "machine artifactory.corp login REALUSER password REALPASS\n"
            "default login DEFAULTUSER password DEFAULTPASS\n"
        )
        monkeypatch.setenv("NETRC", str(netrc_path))

        creds = _http.netrc_credentials("https://unrelated.example/x")

        assert creds == ("DEFAULTUSER", "DEFAULTPASS")

    def test_no_resolvable_home_directory_does_not_raise(self, monkeypatch):
        """Fourth-pass regression. `Path.home()` raises RuntimeError when
        neither HOME nor a passwd entry resolves (rootless / arbitrary-UID
        containers) and it sits OUTSIDE the try. Before the host gate this
        branch was unreachable whenever a JFrog credential was set (step 1
        matched unconditionally); gating step 1 handed its traffic here, so
        the raise landed on EVERY request to an unconfigured host. Reproduced
        before the fix: RuntimeError propagated out of `auth_headers_for`.
        Same shape, same reason, as the `read_pixi_config` guard."""
        monkeypatch.delenv("NETRC", raising=False)
        monkeypatch.setattr(
            Path, "home",
            staticmethod(lambda: (_ for _ in ()).throw(RuntimeError("no home"))),
        )
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")

        # Must degrade to "no credential", never take the process down.
        assert _http.netrc_credentials("https://pypi.org/simple/x") is None
        assert _http.auth_headers_for("https://pypi.org/simple/x") == {}


class TestPublicHostFloor:
    """Fourth-pass regression: `_public_default_hosts()` derives from the
    module's own `_DEFAULT_*` globals, which cannot see a public host this
    module reaches from an inline-built URL, as a CDN/redirect target, or
    under a vendor's second domain. Each of these was reproduced receiving
    `JFROG_API_KEY` under a `*_BASE_URL` naming it."""

    @pytest.mark.parametrize(
        "env_var,base,request_url",
        [
            ("PYPI_FILES_BASE_URL", "https://files.pythonhosted.org/packages",
             "https://files.pythonhosted.org/packages/aa/bb/pkg.tar.gz"),
            ("AZURE_BASE_URL", "https://dev.azure.com/conda-forge",
             "https://dev.azure.com/conda-forge/feedstock-builds/_apis/build/builds"),
            ("ANACONDA_BASE_URL", "https://anaconda.org/conda-forge",
             "https://anaconda.org/conda-forge/pkg"),
            ("REPO_ANACONDA_BASE_URL", "https://repo.anaconda.com/pkgs",
             "https://repo.anaconda.com/pkgs/main/linux-64/repodata.json"),
        ],
    )
    def test_undeclared_public_host_named_by_a_base_url_gets_no_credential(
        self, monkeypatch, env_var, base, request_url
    ):
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        monkeypatch.setenv(env_var, base)
        assert _http.auth_headers_for(request_url) == {}

    def test_a_genuine_enterprise_mirror_still_receives_its_credential(
        self, monkeypatch
    ):
        """The floor must not be so broad it defeats the allowlist."""
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        monkeypatch.setenv("CORP_BASE_URL", "https://mycorp.jfrog.io/artifactory/conda")
        assert _http.auth_headers_for(
            "https://mycorp.jfrog.io/artifactory/conda/noarch/repodata.json"
        ) == {"X-JFrog-Art-Api": "secret-key"}

    def test_an_empty_public_host_set_is_never_cached(self, monkeypatch):
        """The set is SUBTRACTED from the allowlist, so caching an empty one
        would silently re-open the gate for the life of the process. Empty can
        only mean the `_DEFAULT_*` globals were not in place when the first
        call ran (they are declared below the function) — a load-order bug,
        not a real answer."""
        monkeypatch.setattr(_http, "_PUBLIC_DEFAULT_HOSTS", frozenset())
        assert "pypi.org" in _http._public_default_hosts()
