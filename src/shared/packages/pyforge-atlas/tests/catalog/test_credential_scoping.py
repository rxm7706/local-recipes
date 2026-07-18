"""Gate check 6 (AC-4): per-host credential scoping — the FR-1 fix-not-port.

The legacy `_http.py` defect (JFrog branch evaluated first, host computed
but never consulted — L211-218 at b18cbb5) attached X-JFrog-Art-Api to
EVERY outbound request when JFROG_API_KEY was set. The catalog inverts
this: a credential exists ONLY where a dataset's destination host requires
it, and a JFrog-named key is never reachable from a non-JFrog host entry.

Review-pass P4 hardening: hostname matching is suffix-based on the parsed
netloc (a substring match would bless `jfrog.evil.example.com` and
`notjfrog.io`); the JFrog detection triggers on ANY credential key whose
NAME contains `jfrog` or `artifactory` case-insensitively (not just the
literal key `jfrog`); and the tracked-config sweep covers the whole conf/
tree, not only conf/base.
"""

from __future__ import annotations

import subprocess
from urllib.parse import urlparse

from .conftest import CONF_SOURCE, CREDENTIAL_ALLOWLIST, MEMBER_DIR, REPO_ROOT

_JFROG_KEY_TOKENS = ("jfrog", "artifactory")


def _is_artifactory_host(host: str) -> bool:
    """Hostname-suffix match (P4): exact `jfrog.io` / `*.jfrog.io`, or an
    `artifactory` DNS LABEL anywhere in the hostname (artifactory.corp.com,
    mirror.artifactory.corp — but NOT notartifactory.example)."""
    host = host.lower().rstrip(".")
    if host == "jfrog.io" or host.endswith(".jfrog.io"):
        return True
    return "artifactory" in host.split(".")


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


def test_jfrog_named_key_never_reachable_from_a_non_jfrog_host(catalog_config):
    """The AC-4 defect-fix assertion. With the shipped public defaults NO
    entry carries a JFrog-named key at all; if one ever does, its resolved
    endpoint HOSTNAME (suffix-matched, not substring) must be an
    Artifactory host. Detection is by key NAME, case-insensitive (P4):
    `jfrog`, `JFrog_prod`, `corp_artifactory`, ... all count."""
    offenders = {}
    for name, spec in catalog_config.items():
        cred_key = str(spec.get("credentials", ""))
        if not any(tok in cred_key.lower() for tok in _JFROG_KEY_TOKENS):
            continue
        # PartitionedDataset and friends carry the location under `path`, not
        # `url`/`filepath` — include it so a future credentialed partitioned
        # store can't resolve to an empty host and slip the check (Gemini PR-71).
        location = spec.get("url", spec.get("filepath", spec.get("path", "")))
        host = urlparse(str(location)).netloc.lower()
        if not _is_artifactory_host(host):
            offenders[name] = {"credentials": cred_key, "host": host}
    assert not offenders, (
        f"JFrog-named credential attached to non-JFrog destination host(s): {offenders}"
    )


def test_artifactory_host_matcher_rejects_substring_tricks():
    """Pin the matcher semantics (P4): suffix/label matching only."""
    assert _is_artifactory_host("jfrog.io")
    assert _is_artifactory_host("mycorp.jfrog.io")
    assert _is_artifactory_host("artifactory.corp.example")
    assert not _is_artifactory_host("jfrog.evil.example.com")
    assert not _is_artifactory_host("notjfrog.io")
    assert not _is_artifactory_host("jfrog.io.evil.net")
    assert not _is_artifactory_host("notartifactory.example")
    assert not _is_artifactory_host("api.github.com")


def test_skip_auth_hosts_carry_no_credentials(catalog_config):
    """endoflife.date has skip_auth semantics in the legacy chain — no
    credential is ever attached to it."""
    assert "credentials" not in catalog_config["pypi_endoflife_raw"]


def test_local_credentials_file_is_gitignored():
    """P4: assert the ignore mechanism itself, not just the convention —
    conf/local/credentials.yml must be matched by a gitignore rule."""
    target = MEMBER_DIR / "conf" / "local" / "credentials.yml"
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "check-ignore", "-q", str(target)],
        check=False,
        capture_output=True,
    )
    assert result.returncode == 0, (
        "conf/local/credentials.yml is NOT gitignored — the per-host "
        "credential file must never be trackable"
    )


def test_no_credential_material_in_tracked_config():
    """Nothing credential-bearing is ever committed: no *credentials* file
    anywhere under conf/ outside conf/local (P4: rglob over the whole conf
    tree, excluding only path components named `local`)."""
    offenders = [
        str(p.relative_to(CONF_SOURCE))
        for p in CONF_SOURCE.rglob("*credentials*")
        if "local" not in p.relative_to(CONF_SOURCE).parts
    ]
    assert not offenders, (
        f"credential-named file(s) in tracked conf/ (conf/local only, gitignored): {offenders}"
    )
