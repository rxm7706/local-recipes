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

    def test_fallback_host_of_strips_userinfo_and_port(self, load_module):
        """Same `urlparse().hostname` contract as `_http._host_of`. The
        `netloc.split(":")[0]` this replaced returned the USERNAME for
        `https://user:token@host/` (so the real mirror never matched) and
        collapsed every IPv6 literal to a shared `[2001` prefix (so an
        unrelated address did)."""
        mod = load_module("inventory_channel.py")
        assert mod._fallback_host_of("https://mirror.example.com:8081/cf") == "mirror.example.com"
        assert (
            mod._fallback_host_of("https://svc:tok@artifactory.corp.com:8081/api/conda/cf")
            == "artifactory.corp.com"
        )
        assert mod._fallback_host_of("https://[2001:db8::1]:8081/x") == "2001:db8::1"
        assert mod._fallback_host_of("https://[2001:db8::2]/y") == "2001:db8::2"

    def test_fallback_host_of_returns_empty_on_malformed_url(self, load_module):
        """`urlparse("https://[oops")` raises ValueError. The sibling
        allowlist loop guarded that from the start; the request path did not,
        so one malformed channel URL crashed the whole fetch."""
        assert load_module("inventory_channel.py")._fallback_host_of("https://[oops") == ""

    def test_malformed_base_url_does_not_crash_the_allowlist_scan(
        self, load_module, monkeypatch
    ):
        """One malformed `*_BASE_URL` must not take down the whole scan (and
        with it every request), while well-formed entries still collect.

        Scope note: a malformed REQUEST url still raises from
        `urllib.request.Request` itself — unchanged, and correct, since such
        a URL cannot be fetched either way. What this guards is the
        credential gate, which previously raised before Request ever saw it.
        """
        monkeypatch.setenv("CONDA_FORGE_BASE_URL", "https://[oops")
        monkeypatch.setenv("PYPI_BASE_URL", "https://good.example.com/simple")
        mod = load_module("inventory_channel.py")
        assert mod._fallback_configured_enterprise_hosts() == {"good.example.com"}

    def test_userinfo_bearing_configured_mirror_is_authorized(
        self, load_module, monkeypatch
    ):
        """The functional half of the same defect: `https://user:tok@host/`
        is a routine Artifactory `*_BASE_URL` form, and under the old
        parsing its host never entered the allowlist — so the operator's
        mirror silently stopped receiving its credential."""
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        monkeypatch.setenv(
            "CONDA_FORGE_BASE_URL", "https://svc:tok@mycompany.jfrog.io/artifactory/cf"
        )
        mod = load_module("inventory_channel.py")
        monkeypatch.setattr(mod, "_HTTP_AVAILABLE", False)
        request = mod._make_request(
            "https://mycompany.jfrog.io/artifactory/cf/linux-64/repodata.json"
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


class TestFallbackExcludesPublicDefaultHosts:
    """Story 5.5, third review pass.

    `_http._configured_enterprise_hosts()` subtracts its own public fallback
    hosts, so a merely redundant `CONDA_FORGE_BASE_URL=https://conda.anaconda.org/conda-forge`
    cannot mark a public host "configured". This fallback omitted that
    subtraction, making it WIDER than `_http` in the one direction that
    leaks, while its docstring claimed it was deliberately narrower.
    """

    def test_redundant_public_base_url_does_not_authorize_the_public_host(
        self, load_module, monkeypatch
    ):
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        monkeypatch.setenv(
            "CONDA_FORGE_BASE_URL", "https://conda.anaconda.org/conda-forge"
        )
        mod = load_module("inventory_channel.py")
        monkeypatch.setattr(mod, "_HTTP_AVAILABLE", False)
        request = mod._make_request(
            "https://conda.anaconda.org/conda-forge/linux-64/repodata.json"
        )
        assert "X-jfrog-art-api" not in request.headers

    def test_public_hosts_are_subtracted_from_the_allowlist(
        self, load_module, monkeypatch
    ):
        monkeypatch.setenv("PYPI_BASE_URL", "https://pypi.org/simple")
        monkeypatch.setenv(
            "CONDA_FORGE_BASE_URL", "https://mycompany.jfrog.io/api/conda/cf"
        )
        mod = load_module("inventory_channel.py")
        hosts = mod._fallback_configured_enterprise_hosts()
        assert "pypi.org" not in hosts
        assert "mycompany.jfrog.io" in hosts

    def test_public_host_floor_covers_everything_http_subtracts(self, load_module):
        """Fourth-pass regression. This fallback's docstring claims it is
        never WIDER than `_http` in the leaking direction, but its floor is a
        literal list while `_http`'s is derived — so the two drift silently.
        Measured before the fix: the floor held 9 hosts against `_http`'s 18,
        leaving 11 (crates.io, rubygems.org, gitlab.com, codeberg.org,
        endoflife.date, api.nuget.org, search.maven.org, luarocks.org,
        crandb.r-pkg.org, fastapi.metacpan.org, and the anaconda S3 bucket)
        able to receive `X-JFrog-Art-Api` here while `_http` returned `{}`.
        Containment, not equality: the floor may be broader."""
        import _http  # noqa: PLC0415 -- the module under comparison

        mod = load_module("inventory_channel.py")
        missing = _http._public_default_hosts() - mod._PUBLIC_HOST_FLOOR
        assert missing == set(), (
            "hosts _http subtracts from the allowlist but this fallback does "
            f"not, so the fallback is wider in the leaking direction: {sorted(missing)}"
        )

    def test_public_host_named_by_a_base_url_gets_no_credential_on_the_fallback(
        self, load_module, monkeypatch
    ):
        """The concrete leak the containment gap allowed."""
        monkeypatch.setenv("JFROG_API_KEY", "secret-key")
        monkeypatch.setenv("CRATES_BASE_URL", "https://crates.io/api/v1")
        mod = load_module("inventory_channel.py")
        monkeypatch.setattr(mod, "_HTTP_AVAILABLE", False)
        request = mod._make_request("https://crates.io/api/v1/crates/serde")
        assert "X-jfrog-art-api" not in request.headers
