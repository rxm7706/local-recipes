"""VcsHostSeedDataset / RegistryUpstreamDataset tests (Story 21.2).

Proves the I/O matrix for the GitLab/Codeberg + 8-registry live-fetch sources that
replaced the ``cf_atlas.db`` seed: request-path construction (percent-encoding,
unknown-host/registry guards, blank-identifier guards), the per-registry extractor
shapes (``_REGISTRY_SPECS``, including the luarocks sorted-version-keys fix), the
rate-limit scheduler wired into ``fetch_one``, and the AD-13 last-good + staleness
persistence — including the clobber-safety fix: a batch where every identifier's
fetch fails must NOT overwrite last-good with an all-null result.
"""

from __future__ import annotations

import pytest
from kedro.io.core import DatasetError

from pyforge.atlas.datasets.rate_limit import RateLimitedScheduler
from pyforge.atlas.datasets.refresh import RefreshRequest
from pyforge.atlas.datasets.vcs_sources import (
    _REGISTRY_SPECS,
    RegistryUpstreamDataset,
    VcsHostSeedDataset,
    _luarocks_extract,
)

# -- VcsHostSeedDataset: construction + request-path -------------------------


def test_unknown_host_raises_at_construction(tmp_path):
    with pytest.raises(ValueError, match="unknown VCS host"):
        VcsHostSeedDataset(url="https://gitlab.com/api/v4", host="bitbucket", filepath=str(tmp_path))


def test_gitlab_request_path_percent_encodes_the_project_slug(tmp_path):
    ds = VcsHostSeedDataset(url="https://gitlab.com/api/v4", host="gitlab", filepath=str(tmp_path))
    path = ds.request_path("gitlab-org/gitlab")
    assert "gitlab-org%2Fgitlab" in path
    assert "order_by=updated" in path


def test_codeberg_request_path_percent_encodes_owner_and_repo(tmp_path):
    ds = VcsHostSeedDataset(url="https://codeberg.org/api/v1", host="codeberg", filepath=str(tmp_path))
    path = ds.request_path("some owner/some repo")
    assert "some%20owner" in path
    assert "some%20repo" in path
    assert "sort=updated" in path


def test_codeberg_request_path_requires_owner_and_repo(tmp_path):
    ds = VcsHostSeedDataset(url="https://codeberg.org/api/v1", host="codeberg", filepath=str(tmp_path))
    with pytest.raises(ValueError):
        ds.request_path("just-a-name")  # no '/' separator


def test_codeberg_request_path_rejects_more_than_one_slash(tmp_path):
    """Review fix #11: "owner/repo/sub" must raise rather than silently
    percent-encoding the extra segment into a malformed request path."""
    ds = VcsHostSeedDataset(url="https://codeberg.org/api/v1", host="codeberg", filepath=str(tmp_path))
    with pytest.raises(ValueError, match="exactly one"):
        ds.request_path("owner/repo/sub")


@pytest.mark.parametrize("blank", ["", "/", "//"])
def test_gitlab_request_path_rejects_blank_identifier(blank, tmp_path):
    """Guard against a malformed double-slash URL — an empty/slashes-only identifier
    must raise, never silently build a broken request path."""
    ds = VcsHostSeedDataset(url="https://gitlab.com/api/v4", host="gitlab", filepath=str(tmp_path))
    with pytest.raises(ValueError):
        ds.request_path(blank)


# -- VcsHostSeedDataset: fetch_one / load_many / persistence -----------------


def test_fetch_one_acquires_a_rate_limit_token(tmp_path):
    calls = []
    sched = RateLimitedScheduler(rps=100.0, bucket_capacity=5)
    orig_acquire = sched.acquire

    def spy_acquire(n=1):
        calls.append(n)
        return orig_acquire(n)

    sched.acquire = spy_acquire
    ds = VcsHostSeedDataset(url="https://gitlab.com/api/v4", host="gitlab", filepath=str(tmp_path), scheduler=sched)
    ds.fetch_one("group/project", fetcher=lambda ident: [{"name": "v1.0"}])
    assert calls == [1]


def test_fetch_one_retries_acquire_a_token_on_every_attempt_with_backoff(tmp_path):
    """Review fix #3: the rate-limit token is acquired on EVERY retry attempt (not
    just the first), and a backoff delay runs between retries. Injects a no-op
    sleep so the test never actually waits."""
    calls = []
    sleeps = []
    sched = RateLimitedScheduler(rps=100.0, bucket_capacity=5)
    orig_acquire = sched.acquire

    def spy_acquire(n=1):
        calls.append(n)
        return orig_acquire(n)

    sched.acquire = spy_acquire
    ds = VcsHostSeedDataset(
        url="https://gitlab.com/api/v4",
        host="gitlab",
        filepath=str(tmp_path),
        scheduler=sched,
        sleep=lambda secs: sleeps.append(secs),
    )
    attempts = {"n": 0}

    def flaky(ident):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RuntimeError("transient")
        return [{"name": "v1.0"}]

    out = ds.fetch_one("group/project", fetcher=flaky)
    assert out == [{"name": "v1.0"}]
    assert attempts["n"] == 3
    assert calls == [1, 1, 1]  # acquired on every attempt, not just the first
    assert len(sleeps) == 2  # a backoff between attempts 1->2 and 2->3
    assert all(s > 0 for s in sleeps)


def test_fetch_one_exhausts_retries_and_raises(tmp_path):
    ds = VcsHostSeedDataset(
        url="https://gitlab.com/api/v4",
        host="gitlab",
        filepath=str(tmp_path),
        max_retries=2,
        sleep=lambda secs: None,
    )

    def always_fails(ident):
        raise RuntimeError("down")

    with pytest.raises(RuntimeError, match="down"):
        ds.fetch_one("group/project", fetcher=always_fails)


def test_load_many_success_persists_and_load_reads_it_back(tmp_path):
    ds = VcsHostSeedDataset(url="https://gitlab.com/api/v4", host="gitlab", filepath=str(tmp_path))
    out = ds.load_many([("numpy", "group/numpy")], fetcher=lambda ident: [{"name": "v1.26.0"}])
    assert out.loc[0, "upstream_version"] == "v1.26.0"
    assert not ds.is_stale()
    loaded = ds.load()
    assert loaded.loc[0, "conda_name"] == "numpy"
    assert loaded.loc[0, "upstream_version"] == "v1.26.0"


def test_load_many_total_failure_does_not_clobber_last_good(tmp_path):
    """AD-13 clobber-safety fix: a batch where every identifier's fetch fails (or
    yields no version) is treated as EMPTY for persistence — last-good is preserved
    and staleness is marked, never overwritten with an all-null result."""
    ds = VcsHostSeedDataset(url="https://gitlab.com/api/v4", host="gitlab", filepath=str(tmp_path))
    ds.load_many([("numpy", "group/numpy")], fetcher=lambda ident: [{"name": "v1.26.0"}])
    assert not ds.is_stale()

    def always_fails(ident):
        raise RuntimeError("upstream unreachable")

    ds.load_many([("numpy", "group/numpy")], fetcher=always_fails)
    still_good = ds.load()
    assert still_good.loc[0, "upstream_version"] == "v1.26.0"  # NOT clobbered
    assert ds.is_stale()


def test_load_many_no_version_in_response_is_also_treated_as_failure(tmp_path):
    ds = VcsHostSeedDataset(url="https://gitlab.com/api/v4", host="gitlab", filepath=str(tmp_path))
    ds.load_many([("numpy", "group/numpy")], fetcher=lambda ident: [{"name": "v1.26.0"}])
    ds.load_many([("numpy", "group/numpy")], fetcher=lambda ident: [])  # no tags
    still_good = ds.load()
    assert still_good.loc[0, "upstream_version"] == "v1.26.0"
    assert ds.is_stale()


def test_load_on_absent_store_returns_empty_correctly_columned_frame(tmp_path):
    ds = VcsHostSeedDataset(url="https://gitlab.com/api/v4", host="gitlab", filepath=str(tmp_path))
    out = ds.load()
    assert out.empty
    assert list(out.columns) == ["conda_name", "upstream_version", "last_error"]
    assert ds.is_stale()


def test_save_only_accepts_refresh_request(tmp_path):
    ds = VcsHostSeedDataset(url="https://gitlab.com/api/v4", host="gitlab", filepath=str(tmp_path))
    with pytest.raises(DatasetError, match="RefreshRequest"):
        ds.save({"not": "a-refresh-request"})


def test_save_rejects_a_refresh_request_for_a_different_store(tmp_path):
    """Review fix #8: a RefreshRequest.store that does not match this instance's own
    host raises loudly — catches a pipeline-wiring drift (e.g. a positional mismatch
    between _HOST_SPECS and the trigger node's outputs=[...] list) rather than
    silently persisting into the wrong instance's store."""
    ds = VcsHostSeedDataset(url="https://gitlab.com/api/v4", host="gitlab", filepath=str(tmp_path))
    with pytest.raises(DatasetError, match="drifted out of sync"):
        ds.save(RefreshRequest(store="vcs_codeberg_api_raw"))


def test_save_with_refresh_request_honors_cadence(tmp_path):
    ds = VcsHostSeedDataset(url="https://gitlab.com/api/v4", host="gitlab", filepath=str(tmp_path))
    ds.load_many([("numpy", "group/numpy")], fetcher=lambda ident: [{"name": "v1.0"}])
    assert not ds.is_stale()
    # fresh within cadence -> save() is a no-op (does not re-fetch / mark stale)
    ds.save(RefreshRequest(store="vcs_gitlab_api_raw", cadence_seconds=10_000_000))
    assert not ds.is_stale()


def test_save_with_refresh_request_due_marks_stale_when_no_identifiers_known(tmp_path):
    """Story 21.2 scope: no production identifier source is wired yet, so a due
    refresh degrades cleanly to keep-last-good + mark stale rather than crashing."""
    ds = VcsHostSeedDataset(url="https://gitlab.com/api/v4", host="gitlab", filepath=str(tmp_path))
    ds.save(RefreshRequest(store="vcs_gitlab_api_raw", cadence_seconds=0, force=True))
    assert ds.is_stale()


# -- RegistryUpstreamDataset: unknown registry + last_error column -----------


def test_unknown_registry_raises_at_construction(tmp_path):
    with pytest.raises(ValueError, match="unknown registry"):
        RegistryUpstreamDataset(url="https://registry.npmjs.org", registry="pypi", filepath=str(tmp_path))


def test_registry_columns_include_last_error(tmp_path):
    ds = RegistryUpstreamDataset(url="https://registry.npmjs.org", registry="npm", filepath=str(tmp_path))
    assert "last_error" in ds._COLUMNS


def test_registry_save_rejects_a_refresh_request_for_a_different_store(tmp_path):
    """Review fix #8: see the VcsHostSeedDataset equivalent above."""
    ds = RegistryUpstreamDataset(url="https://registry.npmjs.org", registry="npm", filepath=str(tmp_path))
    with pytest.raises(DatasetError, match="drifted out of sync"):
        ds.save(RefreshRequest(store="vcs_registry_cran_raw"))


def test_registry_total_failure_does_not_clobber_last_good(tmp_path):
    def always_fails(ident):
        raise RuntimeError("down")

    ds = RegistryUpstreamDataset(url="https://registry.npmjs.org", registry="npm", filepath=str(tmp_path))
    ds.load_many([("numpy", "numpy")], fetcher=lambda ident: {"dist-tags": {"latest": "1.26.0"}})
    assert not ds.is_stale()
    ds.load_many([("numpy", "numpy")], fetcher=always_fails)
    still_good = ds.load()
    assert still_good.loc[0, "upstream_version"] == "1.26.0"
    assert ds.is_stale()


# -- per-registry extractor shapes (_REGISTRY_SPECS) --------------------------

_REGISTRY_FIXTURES = {
    "npm": ({"dist-tags": {"latest": "1.2.3"}}, "1.2.3"),
    "cran": ({"Version": "2.0.0"}, "2.0.0"),
    "cpan": ({"version": "0.42"}, "0.42"),
    # review fix #1: "1.10-1" is the genuinely latest (1.10 > 1.2) — a plain
    # lexicographic sort would have picked "1.2-1" (the ORIGINAL, WRONG fixture
    # answer this replaces).
    "luarocks": ({"versions": {"1.0-1": {}, "1.2-1": {}, "1.10-1": {}}}, "1.10-1"),
    "crates": ({"crate": {"newest_version": "3.1.4"}}, "3.1.4"),
    "rubygems": ({"version": "9.9.9"}, "9.9.9"),
    "maven": ({"response": {"docs": [{"latestVersion": "4.5.6"}]}}, "4.5.6"),
    "nuget": ({"versions": ["1.0.0", "1.1.0", "2.0.0"]}, "2.0.0"),
}


@pytest.mark.parametrize("registry", sorted(_REGISTRY_FIXTURES))
def test_registry_extractor_shapes(registry, tmp_path):
    payload, expected = _REGISTRY_FIXTURES[registry]
    ds = RegistryUpstreamDataset(url="https://example.invalid", registry=registry, filepath=str(tmp_path / registry))
    out = ds.load_many([("pkg", "pkg")], fetcher=lambda ident: payload)
    assert out.loc[0, "upstream_version"] == expected


def test_luarocks_extract_picks_genuinely_latest_by_numeric_aware_max():
    """Review finding: dict iteration order is not release order — pick the max via
    a numeric-aware comparator rather than next(iter(...))."""
    payload = {"versions": {"2.0-1": {}, "1.0-1": {}, "1.5-1": {}}}
    assert _luarocks_extract(payload) == "2.0-1"


def test_luarocks_extract_is_numeric_not_lexicographic_on_multi_digit_components():
    """Review fix #1: a raw string sort mis-ranks multi-digit components — e.g.
    "1.9-1" > "1.10-1" lexicographically (since '9' > '1' as the first differing
    character) even though 1.10 is the genuinely newer release."""
    payload = {"versions": {"1.9-1": {}, "1.10-1": {}}}
    assert _luarocks_extract(payload) == "1.10-1"


def test_all_ten_endpoint_specs_percent_encode(tmp_path):
    """A slash-bearing identifier never produces a raw '/' in the built path (every
    builder routes the identifier through urllib.parse.quote)."""
    from pyforge.atlas.datasets.vcs_sources import _HOST_SPECS

    for host, spec in _HOST_SPECS.items():
        if host == "codeberg":
            continue  # codeberg splits owner/repo by design — tested separately above
        path = spec.build_path("https://example.invalid", "weird/slug")
        assert "weird/slug" not in path

    for spec in _REGISTRY_SPECS.values():
        path = spec.build_path("https://example.invalid", "weird name")
        assert " " not in path
