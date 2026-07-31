"""FR-7 regression test — the host-scoped credential resolver (Story 1.2).

Guards against a regression to the pre-`skip_auth` unconditional-injection
shape: if host gating in `keys.resolve_headers` is ever removed or bypassed,
these fail loudly rather than leaking credentials cross-host silently again.
"""

from __future__ import annotations

import pytest

from pyforge.steward.keys import HostScopedCredential, resolve_headers

ARTIFACTORY = HostScopedCredential(hosts=("artifactory.example.com",))
IN_ALLOWLIST_URL = "https://artifactory.example.com/artifactory/api/pypi/pypi/simple/"
OUT_OF_ALLOWLIST_URL = "https://pypi.org/simple/somepkg/"

_CREDENTIAL_ENV_VARS = (
    "JFROG_API_KEY",
    "JFROG_USERNAME",
    "JFROG_PASSWORD",
    "GITHUB_TOKEN",
    "GH_TOKEN",
)


@pytest.fixture(autouse=True)
def _isolated_credential_environment(monkeypatch, tmp_path):
    """Clear ambient credential env vars and point NETRC at a file that does
    not exist, so a real `~/.netrc` on the machine running the suite can
    never make these tests flaky.
    """
    for var in _CREDENTIAL_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NETRC", str(tmp_path / "netrc-does-not-exist"))


def test_out_of_allowlist_host_returns_no_headers_even_with_env_var_set(monkeypatch):
    monkeypatch.setenv("JFROG_API_KEY", "synthetic-test-token")
    assert resolve_headers(ARTIFACTORY, OUT_OF_ALLOWLIST_URL) == {}


def test_in_allowlist_host_returns_the_header_http_py_would_produce(monkeypatch):
    monkeypatch.setenv("JFROG_API_KEY", "synthetic-test-token")
    assert resolve_headers(ARTIFACTORY, IN_ALLOWLIST_URL) == {
        "X-JFrog-Art-Api": "synthetic-test-token"
    }


def test_in_allowlist_host_with_no_credential_env_var_set_returns_empty():
    assert resolve_headers(ARTIFACTORY, IN_ALLOWLIST_URL) == {}


def test_port_qualified_and_trailing_dot_allowlist_entries_still_match(monkeypatch):
    monkeypatch.setenv("JFROG_API_KEY", "synthetic-test-token")
    credential = HostScopedCredential(hosts=("artifactory.example.com:8081",))
    assert resolve_headers(credential, "https://artifactory.example.com./x") == {
        "X-JFrog-Art-Api": "synthetic-test-token"
    }


def test_bare_string_hosts_is_rejected_rather_than_iterated_per_character():
    with pytest.raises(TypeError):
        HostScopedCredential(hosts="artifactory.example.com")


def test_empty_hosts_is_rejected_rather_than_silently_never_matching():
    with pytest.raises(ValueError):
        HostScopedCredential(hosts=())


def test_subdomain_and_suffix_lookalike_hosts_do_not_match(monkeypatch):
    monkeypatch.setenv("JFROG_API_KEY", "synthetic-test-token")
    assert resolve_headers(ARTIFACTORY, "https://mirror.artifactory.example.com/x") == {}
    assert (
        resolve_headers(ARTIFACTORY, "https://artifactory.example.com.evil.example/x")
        == {}
    )


def test_multi_entry_allowlist_matches_each_declared_host_exactly(monkeypatch):
    monkeypatch.setenv("JFROG_API_KEY", "synthetic-test-token")
    credential = HostScopedCredential(hosts=("a.example.com", "b.example.com"))
    assert resolve_headers(credential, "https://b.example.com/x") == {
        "X-JFrog-Art-Api": "synthetic-test-token"
    }
    assert resolve_headers(credential, "https://c.example.com/x") == {}


def test_distinct_ipv6_hosts_do_not_collide_and_bracketed_entries_match(monkeypatch):
    monkeypatch.setenv("JFROG_API_KEY", "synthetic-test-token")
    credential = HostScopedCredential(hosts=("[2001:db8::1]:8081",))
    assert resolve_headers(credential, "https://[2001:db8::1]/x") == {
        "X-JFrog-Art-Api": "synthetic-test-token"
    }
    assert resolve_headers(credential, "https://[2001:db8::2]/x") == {}


def test_url_shaped_and_empty_canonicalizing_hosts_entries_are_rejected():
    for bad_entry in ("https://artifactory.example.com", ":8081", "", "."):
        with pytest.raises(ValueError):
            HostScopedCredential(hosts=(bad_entry,))


def test_entries_that_could_never_match_a_parsed_hostname_are_rejected():
    # A non-numeric single-colon suffix would either mis-canonicalize into a
    # hostname the author never wrote ("https:host" -> "https") or silently
    # never match; characters urlparse strips or splits on (@ ? # * space)
    # can never appear in a parsed hostname at all.
    for bad_entry in (
        "https:artifactory.example.com",
        "artifactory.example.com:8081x",
        "user@host.example.com",
        "a?b.example.com",
        "*.example.com",
        "two words.example.com",
    ):
        with pytest.raises(ValueError):
            HostScopedCredential(hosts=(bad_entry,))


def test_port_qualified_url_matches_a_portless_allowlist_entry(monkeypatch):
    # The mirror image of the entry-side port test above — and the direction
    # real Artifactory deployments (default port 8081) actually hit.
    monkeypatch.setenv("JFROG_API_KEY", "synthetic-test-token")
    assert resolve_headers(ARTIFACTORY, "https://artifactory.example.com:8081/x") == {
        "X-JFrog-Art-Api": "synthetic-test-token"
    }


def test_scheme_less_url_has_no_parseable_host_and_fails_closed(monkeypatch):
    # urlparse reads "artifactory.example.com/x" as all-path (hostname None),
    # so even an in-allowlist-looking string gets no credentials.
    monkeypatch.setenv("JFROG_API_KEY", "synthetic-test-token")
    assert resolve_headers(ARTIFACTORY, "artifactory.example.com/x") == {}


def test_malformed_ipv6_url_raises_value_error_rather_than_being_swallowed():
    with pytest.raises(ValueError):
        resolve_headers(ARTIFACTORY, "https://[::1")
