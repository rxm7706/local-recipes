"""Gate check 6 (AC-4): per-host credential scoping — the FR-1 fix-not-port.

The legacy `_http.py` defect (JFrog branch evaluated first, host computed
but never consulted — L211-218 at b18cbb5) attached X-JFrog-Art-Api to
EVERY outbound request when JFROG_API_KEY was set. The catalog inverts
this: a credential exists ONLY where a dataset's destination host requires
it, and a JFrog key is never reachable from a non-JFrog host entry.
"""

from __future__ import annotations

from urllib.parse import urlparse

from .conftest import CREDENTIAL_ALLOWLIST

_JFROG_HOST_MARKERS = ("jfrog", "artifactory")


def _entries_with_credentials(catalog_config):
    return {
        name: spec["credentials"]
        for name, spec in catalog_config.items()
        if "credentials" in spec
    }


def test_credentials_attach_only_where_the_host_requires_them(catalog_config):
    """No global credential injection: the credentialed-entry set is EXACTLY
    the per-host allowlist."""
    assert _entries_with_credentials(catalog_config) == CREDENTIAL_ALLOWLIST


def test_github_token_scopes_to_the_github_api_host(catalog_config):
    url = catalog_config["vcs_github_api_raw"]["url"]
    host = urlparse(url).netloc.lower()
    assert host == "api.github.com", (
        "github_token may only attach to the GitHub API destination host "
        f"(got {host})"
    )


def test_jfrog_key_never_reachable_from_a_non_jfrog_host(catalog_config):
    """The AC-4 defect-fix assertion. With the shipped public defaults NO
    entry carries the jfrog key at all; if one ever does, its resolved
    endpoint host MUST be an Artifactory host."""
    offenders = {}
    for name, spec in catalog_config.items():
        if spec.get("credentials") != "jfrog":
            continue
        host = urlparse(str(spec.get("url", spec.get("filepath", "")))).netloc.lower()
        if not any(marker in host for marker in _JFROG_HOST_MARKERS):
            offenders[name] = host
    assert not offenders, (
        f"jfrog credential attached to non-JFrog destination host(s): {offenders}"
    )


def test_skip_auth_hosts_carry_no_credentials(catalog_config):
    """endoflife.date has skip_auth semantics in the legacy chain — no
    credential is ever attached to it."""
    assert "credentials" not in catalog_config["pypi_endoflife_raw"]


def test_no_credential_material_in_tracked_config():
    """Nothing credential-bearing is ever committed: conf/base carries no
    credentials file and no secret-looking keys (the live per-host file is
    conf/local/credentials.yml, gitignored)."""
    from .conftest import CONF_SOURCE

    base = CONF_SOURCE / "base"
    assert not list(base.glob("*credentials*")), (
        "conf/base must not carry a credentials file (conf/local only, gitignored)"
    )
