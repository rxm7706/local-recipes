"""GitHub-trending discovery dataset tests (Story 13.1 — CAP-1, FR-64).

Mirrors ``tests/datasets/test_refresh_assets.py``'s taxonomy for
``TrendingSnapshotDataset`` (subclasses ``ExternalRefreshDataset``, so the cadence/force
freshness + AD-13 keep-last-good/never-crash/atomic-write machinery is proven there;
these tests cover CAP-1's OWN contract: the 3-period fetch + fallback orchestration, the
malformed-column rejection, and the two pure parser functions). All IO is via injected
stubs — never a real network call.
"""

from __future__ import annotations

import pandas as pd
import pytest

from pyforge.atlas.datasets import (
    RefreshRequest,
    TrendingSnapshotDataset,
    parse_search_api_response,
    parse_trending_html,
)

DAILY_URL = "https://github.com/trending/python?since=daily"
WEEKLY_URL = "https://github.com/trending/python?since=weekly"
MONTHLY_URL = "https://github.com/trending/python?since=monthly"
SEARCH_URL = "https://api.github.com/search/repositories?q=language:python&sort=stars&order=desc"

# A captured-shape fixture (two repo cards) mirroring github.com/trending/python's real
# markup closely enough to exercise every extracted field, incl. one card WITHOUT a
# "stars today" span (stars_today must come out None, not crash).
GOOD_HTML = """
<html><body>
<article class="Box-row">
  <h2 class="h3 lh-condensed">
    <a href="/psf/requests">
      <span class="text-normal">psf /</span>
      requests
    </a>
  </h2>
  <p class="col-9 color-fg-muted my-1 pr-4">A simple, yet elegant, HTTP library.</p>
  <div class="f6 color-fg-muted mt-2">
    <span itemprop="programmingLanguage">Python</span>
    <a href="/psf/requests/stargazers" class="Link--muted">
      <svg class="octicon octicon-star"></svg>
      50,123
    </a>
    <a href="/psf/requests/forks" class="Link--muted">
      <svg class="octicon octicon-repo-forked"></svg>
      9,001
    </a>
    <span class="d-inline-block float-sm-right">
      <svg class="octicon octicon-star"></svg>
      120 stars today
    </span>
  </div>
</article>
<article class="Box-row">
  <h2 class="h3 lh-condensed">
    <a href="/pallets/flask">
      <span class="text-normal">pallets /</span>
      flask
    </a>
  </h2>
  <p class="col-9 color-fg-muted my-1 pr-4">The Python micro framework for building web applications.</p>
  <div class="f6 color-fg-muted mt-2">
    <span itemprop="programmingLanguage">Python</span>
    <a href="/pallets/flask/stargazers" class="Link--muted">
      <svg class="octicon octicon-star"></svg>
      68,000
    </a>
    <a href="/pallets/flask/forks" class="Link--muted">
      <svg class="octicon octicon-repo-forked"></svg>
      16,000
    </a>
  </div>
</article>
</body></html>
"""

# A "broken layout" fixture — no `article.Box-row` cards at all (simulates an upstream
# markup change / a scrape layout break).
BROKEN_HTML = "<html><body><div class='completely-different-layout'>nothing here</div></body></html>"

# Weekly/monthly cards phrase the stars delta differently than "today" -- pins the
# review-pass regex fix (Story 13.1) so a future edit narrowing the pattern back to
# "today" only is caught here instead of only in production.
GOOD_HTML_WEEKLY = GOOD_HTML.replace("120 stars today", "340 stars this week")
GOOD_HTML_MONTHLY = GOOD_HTML.replace("120 stars today", "9,001 stars this month")

# One card with no h2>a[href] title link (an ad slot / layout variant) mixed with one
# well-formed card -- the missing-link card must be skipped, not crash or drop the page.
MIXED_HTML = """
<html><body>
<article class="Box-row">
  <h2 class="h3 lh-condensed">No title link here</h2>
</article>
<article class="Box-row">
  <h2 class="h3 lh-condensed">
    <a href="/psf/requests">
      <span class="text-normal">psf /</span>
      requests
    </a>
  </h2>
  <p class="col-9 color-fg-muted my-1 pr-4">A simple, yet elegant, HTTP library.</p>
</article>
</body></html>
"""


def _make_html_fetcher(mapping: dict):
    def _fetcher(url: str):
        if url not in mapping:
            raise KeyError(url)
        return mapping[url]

    return _fetcher


def _seed_trending(path) -> None:
    """Write a last-good snapshot on disk via a wired fetcher (store absent => due)."""
    fetcher = _make_html_fetcher({DAILY_URL: GOOD_HTML, WEEKLY_URL: "", MONTHLY_URL: ""})
    TrendingSnapshotDataset(
        filepath=str(path),
        daily_url=DAILY_URL,
        weekly_url=WEEKLY_URL,
        monthly_url=MONTHLY_URL,
        search_api_url=SEARCH_URL,
        fetcher=fetcher,
    ).save(RefreshRequest(store="trending_candidates"))


def _ds(path, *, fetcher=None) -> TrendingSnapshotDataset:
    return TrendingSnapshotDataset(
        filepath=str(path),
        daily_url=DAILY_URL,
        weekly_url=WEEKLY_URL,
        monthly_url=MONTHLY_URL,
        search_api_url=SEARCH_URL,
        fetcher=fetcher,
    )


# ---------------------------------------------------------------------------
# parse_trending_html — fixture-pinned parser tests
# ---------------------------------------------------------------------------


def test_parse_trending_html_extracts_expected_rows():
    rows = parse_trending_html(GOOD_HTML, period="daily")
    assert len(rows) == 2

    r0 = rows[0]
    assert r0["repo_full_name"] == "psf/requests"
    assert r0["repo_url"] == "https://github.com/psf/requests"
    assert r0["description"] == "A simple, yet elegant, HTTP library."
    assert r0["language"] == "Python"
    assert r0["stars_total"] == 50123
    assert r0["stars_today"] == 120
    assert r0["forks_total"] == 9001
    assert r0["period"] == "daily"
    assert r0["source"] == "html_scrape"
    assert isinstance(r0["fetched_at"], int)

    r1 = rows[1]
    assert r1["repo_full_name"] == "pallets/flask"
    assert r1["stars_total"] == 68000
    assert r1["stars_today"] is None  # no "stars today" span on this card


def test_parse_trending_html_layout_break_returns_empty_never_raises():
    # A scrape layout break (no article.Box-row cards) degrades to [] — CAP-1's whole point.
    assert parse_trending_html(BROKEN_HTML, period="daily") == []
    assert parse_trending_html("", period="weekly") == []
    assert parse_trending_html(None, period="monthly") == []  # never raises on None


@pytest.mark.parametrize(
    ("html", "period", "expected_stars_today"),
    [
        (GOOD_HTML, "daily", 120),
        (GOOD_HTML_WEEKLY, "weekly", 340),
        (GOOD_HTML_MONTHLY, "monthly", 9001),
    ],
)
def test_parse_trending_html_stars_delta_matches_all_three_period_phrasings(html, period, expected_stars_today):
    rows = parse_trending_html(html, period=period)
    assert rows[0]["stars_today"] == expected_stars_today


def test_parse_trending_html_skips_card_with_no_title_link():
    rows = parse_trending_html(MIXED_HTML, period="daily")
    assert len(rows) == 1
    assert rows[0]["repo_full_name"] == "psf/requests"


def test_parse_trending_html_skips_card_with_absolute_href():
    # If GitHub's markup ever emits an absolute URL instead of the expected relative
    # `/owner/repo` href, `.strip("/")` alone doesn't clean it up -- guard the shape
    # explicitly rather than persist a garbled repo_full_name/repo_url.
    html = GOOD_HTML.replace('href="/psf/requests"', 'href="https://github.com/psf/requests"')
    rows = parse_trending_html(html, period="daily")
    assert len(rows) == 1
    assert rows[0]["repo_full_name"] == "pallets/flask"


def test_parse_trending_html_empty_language_tag_normalizes_to_none():
    html = GOOD_HTML.replace(">Python</span>", "></span>", 1)
    rows = parse_trending_html(html, period="daily")
    assert rows[0]["language"] is None


# ---------------------------------------------------------------------------
# parse_search_api_response — fixture-pinned parser tests
# ---------------------------------------------------------------------------


def test_parse_search_api_response_extracts_expected_rows():
    payload = {
        "items": [
            {
                "full_name": "django/django",
                "html_url": "https://github.com/django/django",
                "description": "The web framework for perfectionists.",
                "language": "Python",
                "stargazers_count": 80000,
                "forks_count": 30000,
            },
            {"full_name": None},  # malformed item, skipped
            "not-a-dict",  # malformed item, skipped
        ]
    }
    rows = parse_search_api_response(payload)
    assert len(rows) == 1
    row = rows[0]
    assert row["repo_full_name"] == "django/django"
    assert row["repo_url"] == "https://github.com/django/django"
    assert row["stars_total"] == 80000
    assert row["stars_today"] is None
    assert row["forks_total"] == 30000
    assert row["period"] == "all"
    assert row["source"] == "search_api_fallback"
    assert isinstance(row["fetched_at"], int)


def test_parse_search_api_response_malformed_payload_returns_empty():
    assert parse_search_api_response(None) == []
    assert parse_search_api_response("nope") == []
    assert parse_search_api_response({}) == []
    assert parse_search_api_response({"items": "nope"}) == []
    assert parse_search_api_response({"items": [1, 2, 3]}) == []


def test_parse_search_api_response_accepts_raw_json_text():
    # The injected fetcher is Callable[[str], str] -- it returns response TEXT for
    # every URL, the search endpoint included. parse_search_api_response must do its
    # own json.loads rather than assume a caller pre-parsed it into a dict.
    import json as _json

    text = _json.dumps({"items": [{"full_name": "django/django", "stargazers_count": 80000}]})
    rows = parse_search_api_response(text)
    assert len(rows) == 1
    assert rows[0]["repo_full_name"] == "django/django"
    assert rows[0]["source"] == "search_api_fallback"


# ---------------------------------------------------------------------------
# offline / lazy construction (kedro-catalog-check compatibility)
# ---------------------------------------------------------------------------


def test_constructs_offline_no_refresher(tmp_path):
    ds = _ds(tmp_path / "trending")
    assert ds._describe()["refresher_wired"] is False


# ---------------------------------------------------------------------------
# I/O matrix — happy path
# ---------------------------------------------------------------------------


def test_happy_path_all_periods_persist_and_not_stale(tmp_path):
    fetcher = _make_html_fetcher({DAILY_URL: GOOD_HTML, WEEKLY_URL: GOOD_HTML, MONTHLY_URL: GOOD_HTML})
    ds = _ds(tmp_path / "trending", fetcher=fetcher)
    ds.save(RefreshRequest(store="trending_candidates", force=True))
    assert ds.is_stale() is False
    out = ds.load()
    assert not out.empty
    assert set(out["period"]) == {"daily", "weekly", "monthly"}
    assert len(out) == 6  # 2 rows x 3 periods
    assert set(out["repo_full_name"]) == {"psf/requests", "pallets/flask"}


# ---------------------------------------------------------------------------
# I/O matrix — layout break (all 3 periods empty, fallback ALSO empty)
# ---------------------------------------------------------------------------


def test_layout_break_all_empty_falls_back_then_keeps_last_good(tmp_path):
    p = tmp_path / "trending"
    _seed_trending(p)  # a prior snapshot exists

    def fetcher(url):
        if url == SEARCH_URL:
            return {"items": []}  # fallback also yields zero rows
        return BROKEN_HTML

    ds = _ds(p, fetcher=fetcher)
    ds.save(RefreshRequest(store="trending_candidates", force=True))  # must not raise
    assert ds.is_stale() is True
    marker = ds.staleness()
    assert marker is not None and marker.last_good_exists is True
    # prior snapshot untouched (still readable, still the seeded content)
    assert ds.load()["repo_full_name"].tolist() == ["psf/requests", "pallets/flask"]


def test_layout_break_search_api_fetch_raises_keeps_last_good(tmp_path):
    # The fallback fetch call itself raising (not just returning an empty payload) must
    # also degrade to keep-last-good, never crash the run.
    p = tmp_path / "trending"
    _seed_trending(p)

    def fetcher(url):
        if url == SEARCH_URL:
            raise ConnectionError("boom")
        return BROKEN_HTML

    ds = _ds(p, fetcher=fetcher)
    ds.save(RefreshRequest(store="trending_candidates", force=True))  # must not raise
    assert ds.is_stale() is True
    assert ds.load()["repo_full_name"].tolist() == ["psf/requests", "pallets/flask"]


def test_layout_break_falls_back_to_search_api_and_persists_when_fallback_has_rows(tmp_path):
    import json as _json

    def fetcher(url):
        # The real fetcher is Callable[[str], str] -- it returns response TEXT for
        # every URL, the search endpoint included (never a pre-parsed dict).
        if url == SEARCH_URL:
            return _json.dumps(
                {
                    "items": [
                        {
                            "full_name": "django/django",
                            "html_url": "https://github.com/django/django",
                            "stargazers_count": 80000,
                        }
                    ]
                }
            )
        return BROKEN_HTML  # all 3 periods yield zero rows

    ds = _ds(tmp_path / "trending", fetcher=fetcher)
    ds.save(RefreshRequest(store="trending_candidates", force=True))
    assert ds.is_stale() is False
    out = ds.load()
    assert out["repo_full_name"].tolist() == ["django/django"]
    assert out["source"].tolist() == ["search_api_fallback"]


# ---------------------------------------------------------------------------
# I/O matrix — partial layout break (2 of 3 periods parse fine; fallback NOT tried)
# ---------------------------------------------------------------------------


def test_partial_layout_break_two_good_periods_persist_no_fallback(tmp_path):
    def fetcher(url):
        if url == DAILY_URL:
            return GOOD_HTML
        if url == WEEKLY_URL:
            return GOOD_HTML
        if url == MONTHLY_URL:
            return BROKEN_HTML  # zero rows for this one period only
        raise AssertionError(f"fallback must not be tried when combined result is non-empty: {url}")

    ds = _ds(tmp_path / "trending", fetcher=fetcher)
    ds.save(RefreshRequest(store="trending_candidates"))
    assert ds.is_stale() is False
    out = ds.load()
    assert set(out["period"]) == {"daily", "weekly"}


# ---------------------------------------------------------------------------
# I/O matrix — a per-period fetch exception never aborts the other periods
# ---------------------------------------------------------------------------


def test_fetch_exception_for_one_period_does_not_abort_the_others(tmp_path):
    def fetcher(url):
        if url == DAILY_URL:
            raise ConnectionError("endpoint unreachable")
        if url == WEEKLY_URL:
            return GOOD_HTML
        if url == MONTHLY_URL:
            return GOOD_HTML
        raise AssertionError(f"fallback must not be reached: {url}")

    ds = _ds(tmp_path / "trending", fetcher=fetcher)
    ds.save(RefreshRequest(store="trending_candidates"))  # must not raise
    assert ds.is_stale() is False
    out = ds.load()
    assert set(out["period"]) == {"weekly", "monthly"}


# ---------------------------------------------------------------------------
# I/O matrix — not due yet (fresh within cadence, force=False): no-op, no fetch
# ---------------------------------------------------------------------------


def test_fresh_store_within_cadence_is_a_noop_no_fetch_attempted(tmp_path):
    p = tmp_path / "trending"
    _seed_trending(p)

    def fetcher(url):
        raise AssertionError("must not fetch when the store is not due for refresh")

    ds = _ds(p, fetcher=fetcher)
    ds.save(RefreshRequest(store="trending_candidates", cadence_seconds=604800, force=False))
    assert ds.is_stale() is False
    assert ds.load()["repo_full_name"].tolist() == ["psf/requests", "pallets/flask"]


# ---------------------------------------------------------------------------
# I/O matrix — offline / no fetcher wired
# ---------------------------------------------------------------------------


def test_offline_no_fetcher_marks_stale_and_keeps_last_good(tmp_path):
    p = tmp_path / "trending"
    _seed_trending(p)
    offline = _ds(p)
    offline.save(RefreshRequest(store="trending_candidates", force=True))
    assert offline.is_stale() is True
    assert offline.load()["repo_full_name"].tolist() == ["psf/requests", "pallets/flask"]


def test_offline_missing_store_load_returns_empty_and_marks_stale(tmp_path):
    ds = _ds(tmp_path / "never")
    out = ds.load()
    assert isinstance(out, pd.DataFrame) and out.empty
    assert ds.is_stale() is True


def test_unreadable_store_degrades_to_empty(tmp_path):
    p = tmp_path / "trending"
    _seed_trending(p)
    (p / TrendingSnapshotDataset.STORE_FILENAME).write_bytes(b"not a parquet")
    ds = _ds(p)
    out = ds.load()
    assert out.empty
    assert ds.is_stale() is True


# ---------------------------------------------------------------------------
# _write malformed-column rejection (mirrors VDBStoreDataset._write)
# ---------------------------------------------------------------------------


def test_write_rejects_frame_missing_required_columns(tmp_path):
    ds = _ds(tmp_path / "trending")
    with pytest.raises(ValueError):
        ds._write(pd.DataFrame({"nonsense": [1, 2]}))


def test_malformed_refresh_is_rejected_and_keeps_last_good(tmp_path, monkeypatch):
    p = tmp_path / "trending"
    _seed_trending(p)

    def bad_refresh(self):
        return pd.DataFrame({"nonsense": [1, 2]})

    monkeypatch.setattr(TrendingSnapshotDataset, "_do_refresh", bad_refresh)
    ds = _ds(p, fetcher=lambda url: "")
    ds.save(RefreshRequest(store="trending_candidates", force=True))  # must not raise
    assert ds.is_stale() is True
    assert ds.load()["repo_full_name"].tolist() == ["psf/requests", "pallets/flask"]


# ===========================================================================
# Story 21.4 — Tier 1 catalog sources: TrackedSeedDataset / AnacondaDist2026Dataset /
# AossPremiumPythonDataset (+ their pure parsers)
# ===========================================================================

import json as _json  # noqa: E402
from pathlib import Path  # noqa: E402

from kedro.io.core import DatasetError  # noqa: E402

from pyforge.atlas.datasets import (  # noqa: E402
    AnacondaDist2026Dataset,
    AossPremiumPythonDataset,
    TrackedSeedDataset,
    parse_anaconda_dist_html,
    parse_aoss_premium_doc,
    parse_aoss_python_package_names,
    read_tracked_seed,
)

_MEMBER = Path(__file__).resolve().parents[3]
_SEEDS = _MEMBER / "conf" / "base" / "seeds"
AOSS_FREE_SEED = _SEEDS / "discovery_aoss_free_python_seed.json"
ANACONDA_DIST_SEED = _SEEDS / "discovery_anaconda_dist_2026x_seed.json"

DIST_URL = "https://www.anaconda.com/docs/getting-started/anaconda/release/2026.x"
AOSS_PREMIUM_URL = "https://docs.cloud.google.com/security-command-center/docs/aoss-supported-packages-premium"

# Captured-shape fixtures mirroring the live pages closely enough to exercise every
# extracted field (live 2026-08-30).
DIST_HTML = """
<html><body>
<h1>Anaconda Distribution 2026.x release notes</h1>
<p>Packages</p>
<table>
  <tr><th>Package Name</th><th>linux-64</th><th>linux-aarch64</th><th>osx-arm64</th><th>win-64</th></tr>
  <tr><td>_anaconda_depends</td><td>2026.07</td><td>2026.07</td><td>2026.07</td><td>2026.07</td></tr>
  <tr><td>_libgcc_mutex</td><td>0.1</td><td>0.1</td><td></td><td></td></tr>
  <tr><td>aiodns</td><td></td><td></td><td>3.6.1</td><td>3.6.1</td></tr>
  <tr><td></td><td>x</td><td></td><td></td><td></td></tr>
</table>
<table>
  <tr><th>Package Name</th><th>linux-64</th></tr>
  <tr><td>only-in-second-table</td><td>9.9</td></tr>
</table>
</body></html>
"""
DIST_BROKEN_HTML = "<html><body><table><tr><th>Something else</th></tr><tr><td>x</td></tr></table></body></html>"

AOSS_HTML = """
<html><body>
<h2 id="java">Supported Java packages</h2>
<ul><li>com.google.guava:guava</li></ul>
<h2 id="python" data-text="Supported Python packages">Supported Python packages</h2>
<p>The premium tier of Assured Open Source Software supports the following Python packages:</p>
<ul>
  <li>APScheduler</li>
  <li>Adafruit-Blinka</li>
  <li>zope.interface</li>
  <li>APScheduler</li>
  <li></li>
</ul>
</body></html>
"""
AOSS_BROKEN_HTML = "<html><body><div>no python heading here</div></body></html>"


# -- read_tracked_seed / TrackedSeedDataset ----------------------------------


def test_read_tracked_seed_missing_or_corrupt_degrades_to_empty(tmp_path, caplog):
    assert read_tracked_seed(tmp_path / "missing.json") == []
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{not json", encoding="utf-8")
    assert read_tracked_seed(corrupt) == []
    not_array = tmp_path / "obj.json"
    not_array.write_text('{"a": 1}', encoding="utf-8")
    assert read_tracked_seed(not_array) == []
    assert "degrading to empty" in caplog.text


def test_read_tracked_seed_resolves_member_relative_path_from_any_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # a CWD where conf/base/seeds/... does not exist
    seed = read_tracked_seed("conf/base/seeds/discovery_aoss_free_python_seed.json")
    assert len(seed) >= 1_000


def test_tracked_seed_dataset_loads_the_real_committed_aoss_free_seed():
    ds = TrackedSeedDataset(filepath=str(AOSS_FREE_SEED))
    out = ds.load()
    assert list(out.columns) == ["pypi_name", "source"]
    assert len(out) >= 1_000
    assert out["pypi_name"].is_unique
    assert (out["source"] == "tracked_seed").all()
    assert "APScheduler" in set(out["pypi_name"])


def test_tracked_seed_dataset_missing_file_degrades_to_empty_never_raises(tmp_path):
    out = TrackedSeedDataset(filepath=str(tmp_path / "nope.json")).load()
    assert out.empty and list(out.columns) == ["pypi_name", "source"]


def test_tracked_seed_dataset_dict_entries_blank_and_duplicates(tmp_path):
    seed = tmp_path / "seed.json"
    seed.write_text(_json.dumps(["a", {"pypi_name": "b"}, {"other": "c"}, "", "  a ", 7, None]))
    out = TrackedSeedDataset(filepath=str(seed)).load()
    assert out["pypi_name"].tolist() == ["a", "b"]


def test_tracked_seed_dataset_custom_name_column(tmp_path):
    seed = tmp_path / "seed.json"
    seed.write_text(_json.dumps([{"conda_name": "numpy"}]))
    out = TrackedSeedDataset(filepath=str(seed), name_column="conda_name").load()
    assert list(out.columns) == ["conda_name", "source"]
    assert out["conda_name"].tolist() == ["numpy"]


def test_tracked_seed_dataset_is_read_only(tmp_path):
    with pytest.raises(DatasetError, match="read-only"):
        TrackedSeedDataset(filepath=str(tmp_path / "x.json")).save(["a"])


def test_tracked_seed_dataset_rejects_unexpected_kwargs():
    with pytest.raises(TypeError):
        TrackedSeedDataset(filepath="x", url="https://example.invalid")


# -- parse_anaconda_dist_html --------------------------------------------------


def test_parse_anaconda_dist_html_reads_the_first_package_table():
    rows = parse_anaconda_dist_html(DIST_HTML)
    by_name = {r["conda_name"]: r for r in rows}
    assert set(by_name) == {"_anaconda_depends", "_libgcc_mutex", "aiodns"}  # blank name skipped
    assert by_name["_libgcc_mutex"]["version"] == "0.1"
    assert by_name["_libgcc_mutex"]["platforms"] == ["linux-64", "linux-aarch64"]
    # no linux-64 cell -> first non-empty platform's version
    assert by_name["aiodns"]["version"] == "3.6.1"
    assert by_name["aiodns"]["platforms"] == ["osx-arm64", "win-64"]
    assert all(r["source"] == "html_scrape" and isinstance(r["fetched_at"], int) for r in rows)
    assert "only-in-second-table" not in by_name


def test_parse_anaconda_dist_html_layout_break_returns_empty_never_raises():
    assert parse_anaconda_dist_html(DIST_BROKEN_HTML) == []
    assert parse_anaconda_dist_html("") == []
    assert parse_anaconda_dist_html(None) == []


# -- AnacondaDist2026Dataset -----------------------------------------------------


def _dist(path, *, fetcher=None, seed_path=str(ANACONDA_DIST_SEED)) -> AnacondaDist2026Dataset:
    return AnacondaDist2026Dataset(filepath=str(path), url=DIST_URL, seed_path=seed_path, fetcher=fetcher)


def test_dist_constructs_offline_no_refresher(tmp_path):
    ds = _dist(tmp_path / "dist")
    desc = ds._describe()
    assert desc["refresher_wired"] is False
    assert desc["url"] == DIST_URL and desc["seed_path"].endswith("discovery_anaconda_dist_2026x_seed.json")


def test_dist_scrape_success_persists_and_not_stale(tmp_path):
    ds = _dist(tmp_path / "dist", fetcher=lambda url: DIST_HTML)
    ds.save(RefreshRequest(store="discovery_anaconda_dist_2026x_raw", force=True))
    assert ds.is_stale() is False
    out = ds.load()
    assert set(out["conda_name"]) == {"_anaconda_depends", "_libgcc_mutex", "aiodns"}
    assert set(out["source"]) == {"html_scrape"}


def test_dist_scrape_empty_falls_back_to_the_real_tracked_seed(tmp_path):
    calls: list[str] = []

    def fetcher(url):
        calls.append(url)
        return DIST_BROKEN_HTML  # layout break: zero rows

    ds = _dist(tmp_path / "dist", fetcher=fetcher)
    ds.save(RefreshRequest(store="discovery_anaconda_dist_2026x_raw", force=True))
    assert calls == [DIST_URL]  # ONE fetch; the fallback is a LOCAL read, never a second HTTP call
    assert ds.is_stale() is False
    out = ds.load()
    assert len(out) >= 600  # the real committed 2026.x seed (639 rows live 2026-08-30)
    assert set(out["source"]) == {"tracked_seed"}
    assert "numpy" in set(out["conda_name"])


def test_dist_fetch_exception_falls_back_to_seed_never_raises(tmp_path):
    def boom(url):
        raise ConnectionError("down")

    ds = _dist(tmp_path / "dist", fetcher=boom)
    ds.save(RefreshRequest(store="discovery_anaconda_dist_2026x_raw", force=True))
    assert set(ds.load()["source"]) == {"tracked_seed"}


def test_dist_both_scrape_and_seed_empty_keeps_last_good_and_marks_stale(tmp_path):
    p = tmp_path / "dist"
    _dist(p, fetcher=lambda url: DIST_HTML).save(RefreshRequest(store="discovery_anaconda_dist_2026x_raw", force=True))
    ds = _dist(p, fetcher=lambda url: DIST_BROKEN_HTML, seed_path=str(tmp_path / "missing-seed.json"))
    ds.save(RefreshRequest(store="discovery_anaconda_dist_2026x_raw", force=True))  # must not raise
    assert ds.is_stale() is True
    assert ds.staleness().last_good_exists is True
    assert set(ds.load()["conda_name"]) == {"_anaconda_depends", "_libgcc_mutex", "aiodns"}


def test_dist_seed_rows_accept_bare_names_and_dicts(tmp_path):
    seed = tmp_path / "seed.json"
    seed.write_text(
        _json.dumps(["bare", {"conda_name": "full", "version": "1.2", "platforms": ["linux-64"]}, {"nope": 1}, 3])
    )
    ds = _dist(tmp_path / "dist", fetcher=lambda url: "", seed_path=str(seed))
    ds.save(RefreshRequest(store="discovery_anaconda_dist_2026x_raw", force=True))
    out = ds.load().set_index("conda_name")
    assert set(out.index) == {"bare", "full"}
    assert out.loc["full", "version"] == "1.2"
    assert out.loc["bare", "version"] is None or pd.isna(out.loc["bare", "version"])


def test_dist_offline_missing_store_load_returns_empty_and_marks_stale(tmp_path):
    ds = _dist(tmp_path / "never")
    out = ds.load()
    assert out.empty and "conda_name" in out.columns
    assert ds.is_stale() is True


def test_dist_write_rejects_frame_missing_required_columns(tmp_path):
    with pytest.raises(ValueError):
        _dist(tmp_path / "dist")._write(pd.DataFrame({"nonsense": [1]}))


# -- parse_aoss_python_package_names / parse_aoss_premium_doc -----------------


def test_parse_aoss_python_package_names_reads_the_python_ul_deduped():
    names = parse_aoss_python_package_names(AOSS_HTML)
    assert names == ["APScheduler", "Adafruit-Blinka", "zope.interface"]  # java <ul> skipped, dupe + blank dropped
    assert parse_aoss_python_package_names(AOSS_HTML.encode("utf-8")) == names  # bytes accepted


def test_parse_aoss_python_package_names_falls_back_to_heading_text_without_id():
    html = AOSS_HTML.replace('id="python" ', "")
    assert parse_aoss_python_package_names(html) == ["APScheduler", "Adafruit-Blinka", "zope.interface"]


def test_parse_aoss_premium_doc_rows_and_layout_break():
    rows = parse_aoss_premium_doc(AOSS_HTML)
    assert [r["pypi_name"] for r in rows] == ["APScheduler", "Adafruit-Blinka", "zope.interface"]
    assert all(
        r["tier"] == "premium" and r["source"] == "html_scrape" and isinstance(r["fetched_at"], int) for r in rows
    )
    assert parse_aoss_premium_doc(AOSS_BROKEN_HTML) == []
    assert parse_aoss_premium_doc("") == []
    assert parse_aoss_premium_doc(None) == []
    assert parse_aoss_premium_doc({"not": "text"}) == []


def test_free_seed_was_sourced_with_the_same_parser_shape():
    """The committed free-tier seed is the free doc's <ul> under #python — the SAME
    shape parse_aoss_python_package_names reads for the premium tier. Pin that the seed
    still looks like that parser's output (unique, non-blank, no whitespace)."""
    seed = read_tracked_seed(AOSS_FREE_SEED)
    assert len(seed) >= 1_000
    assert all(isinstance(n, str) and n == n.strip() and n for n in seed)
    assert len(set(seed)) == len(seed)


# -- AossPremiumPythonDataset --------------------------------------------------


def _aoss(path, *, fetcher=None) -> AossPremiumPythonDataset:
    return AossPremiumPythonDataset(filepath=str(path), url=AOSS_PREMIUM_URL, fetcher=fetcher)


def test_aoss_premium_constructs_offline_no_refresher(tmp_path):
    ds = _aoss(tmp_path / "aoss")
    assert ds._describe()["refresher_wired"] is False
    assert ds._describe()["url"] == AOSS_PREMIUM_URL


def test_aoss_premium_fetch_success_persists_and_not_stale(tmp_path):
    ds = _aoss(tmp_path / "aoss", fetcher=lambda url: AOSS_HTML)
    ds.save(RefreshRequest(store="discovery_aoss_premium_python_raw", force=True))
    assert ds.is_stale() is False
    out = ds.load()
    assert out["pypi_name"].tolist() == ["APScheduler", "Adafruit-Blinka", "zope.interface"]
    assert set(out["tier"]) == {"premium"}


def test_aoss_premium_first_run_no_last_good_fetch_failure_marks_stale_empty(tmp_path):
    def boom(url):
        raise ConnectionError("4xx/5xx")

    ds = _aoss(tmp_path / "aoss", fetcher=boom)
    ds.save(RefreshRequest(store="discovery_aoss_premium_python_raw", force=True))  # never raises
    assert ds.is_stale() is True
    assert ds.staleness().last_good_exists is False
    out = ds.load()
    assert out.empty and "pypi_name" in out.columns


def test_aoss_premium_fetch_failure_keeps_last_good_and_marks_stale(tmp_path):
    p = tmp_path / "aoss"
    _aoss(p, fetcher=lambda url: AOSS_HTML).save(RefreshRequest(store="discovery_aoss_premium_python_raw", force=True))

    def boom(url):
        raise ConnectionError("unreachable")

    ds = _aoss(p, fetcher=boom)
    ds.save(RefreshRequest(store="discovery_aoss_premium_python_raw", force=True))
    assert ds.is_stale() is True
    assert ds.staleness().last_good_exists is True
    assert len(ds.load()) == 3  # last-good never clobbered with empty


def test_aoss_premium_layout_break_keeps_last_good(tmp_path):
    p = tmp_path / "aoss"
    _aoss(p, fetcher=lambda url: AOSS_HTML).save(RefreshRequest(store="discovery_aoss_premium_python_raw", force=True))
    ds = _aoss(p, fetcher=lambda url: AOSS_BROKEN_HTML)
    ds.save(RefreshRequest(store="discovery_aoss_premium_python_raw", force=True))
    assert ds.is_stale() is True
    assert len(ds.load()) == 3


def test_aoss_premium_offline_no_fetcher_marks_stale_and_keeps_last_good(tmp_path):
    p = tmp_path / "aoss"
    _aoss(p, fetcher=lambda url: AOSS_HTML).save(RefreshRequest(store="discovery_aoss_premium_python_raw", force=True))
    offline = _aoss(p)
    offline.save(RefreshRequest(store="discovery_aoss_premium_python_raw", force=True))
    assert offline.is_stale() is True
    assert len(offline.load()) == 3


def test_aoss_premium_write_rejects_frame_missing_required_columns(tmp_path):
    with pytest.raises(ValueError):
        _aoss(tmp_path / "aoss")._write(pd.DataFrame({"nonsense": [1]}))


# -- review-pass 1: Response-like payloads + largest-table selection -----------


class _StubTextResponse:
    def __init__(self, *, text=None, content=None):
        if text is not None:
            self.text = text
        if content is not None:
            self.content = content


@pytest.mark.parametrize(
    "payload",
    [
        _StubTextResponse(text=AOSS_HTML),
        _StubTextResponse(content=AOSS_HTML.encode("utf-8")),
        AOSS_HTML.encode("utf-8"),
    ],
)
def test_parse_aoss_accepts_response_like_objects(payload):
    assert parse_aoss_python_package_names(payload) == ["APScheduler", "Adafruit-Blinka", "zope.interface"]


def test_parse_aoss_response_like_without_text_or_content_is_empty():
    assert parse_aoss_python_package_names(_StubTextResponse()) == []
    assert parse_aoss_python_package_names(_StubTextResponse(content=b"\\xff\\xfe")) == []


def test_parse_anaconda_dist_html_prefers_the_largest_matching_table():
    """A small changelog table with the same `Package Name` header precedes the full
    list: the LARGEST matching table wins, not the first."""
    html = """
    <html><body>
    <table>
      <tr><th>Package Name</th><th>linux-64</th></tr>
      <tr><td>changelog-only</td><td>1.0</td></tr>
    </table>
    <table>
      <tr><th>Package Name</th><th>linux-64</th><th>win-64</th></tr>
      <tr><td>numpy</td><td>2.0</td><td>2.0</td></tr>
      <tr><td>pandas</td><td>3.0</td><td></td></tr>
      <tr><td>scipy</td><td>1.15</td><td>1.15</td></tr>
    </table>
    </body></html>
    """
    rows = parse_anaconda_dist_html(html)
    assert [r["conda_name"] for r in rows] == ["numpy", "pandas", "scipy"]
    assert rows[1]["platforms"] == ["linux-64"]


def test_dist_dataset_accepts_response_like_fetcher_payload(tmp_path):
    ds = _dist(tmp_path / "dist", fetcher=lambda url: _StubTextResponse(text=DIST_HTML))
    ds.save(RefreshRequest(store="discovery_anaconda_dist_2026x_raw", force=True))
    assert set(ds.load()["source"]) == {"html_scrape"}


# ===========================================================================
# Story 21.5 — Tier 2 catalog sources: parse_about_readme / AboutMaintainersDataset
# ===========================================================================

from pyforge.atlas.datasets import (  # noqa: E402
    AboutMaintainersDataset,
    parse_about_readme,
)

README_URL = "https://raw.githubusercontent.com/rxm7706/about/main/README.md"

# A captured-shape fixture mirroring rxm7706/about's README.md (live snapshot
# 2026-07-11): two numbered feedstock lists under distinct headers, with an
# unrelated paragraph in between (must not leak into either list) and a trailing
# non-numbered line ending the second list.
ABOUT_README_MD = """
About

Some intro text.

List Of FeedStocks - As Maintainer

1. conda-forge/numpy-feedstock
2. conda-forge/dbt-bigquery-feedstock

Some unrelated paragraph here.

List Of FeedStocks - As Co-Maintainer

1. conda-forge/requests-feedstock
2. conda-forge/flask-feedstock

Thanks for reading.
"""

ABOUT_README_BROKEN_MD = "About\n\nNo maintainer lists here at all.\n"


def test_parse_about_readme_extracts_maintainer_and_co_maintainer_rows():
    rows = parse_about_readme(ABOUT_README_MD)
    assert [r["feedstock_slug"] for r in rows] == [
        "conda-forge/numpy-feedstock",
        "conda-forge/dbt-bigquery-feedstock",
        "conda-forge/requests-feedstock",
        "conda-forge/flask-feedstock",
    ]
    assert [r["role"] for r in rows] == [
        "Maintainer",
        "Maintainer",
        "Co-Maintainer",
        "Co-Maintainer",
    ]
    assert all(r["source"] == "about_readme" and isinstance(r["fetched_at"], int) for r in rows)


def test_parse_about_readme_unrelated_paragraph_does_not_leak_into_either_list():
    rows = parse_about_readme(ABOUT_README_MD)
    maint_slugs = {r["feedstock_slug"] for r in rows if r["role"] == "Maintainer"}
    assert maint_slugs == {"conda-forge/numpy-feedstock", "conda-forge/dbt-bigquery-feedstock"}


def test_parse_about_readme_layout_break_no_headers_returns_empty_never_raises():
    assert parse_about_readme(ABOUT_README_BROKEN_MD) == []


@pytest.mark.parametrize("markdown", ["", None])
def test_parse_about_readme_empty_or_none_returns_empty(markdown):
    assert parse_about_readme(markdown) == []


def test_parse_about_readme_renamed_header_degrades_that_list_to_zero_rows():
    """A single-list layout break (one header renamed/removed) degrades ONLY the
    affected list — the other list's rows are unaffected."""
    md = ABOUT_README_MD.replace("List Of FeedStocks - As Maintainer", "List Of FeedStocks - RENAMED")
    rows = parse_about_readme(md)
    assert {r["feedstock_slug"] for r in rows} == {
        "conda-forge/requests-feedstock",
        "conda-forge/flask-feedstock",
    }
    assert all(r["role"] == "Co-Maintainer" for r in rows)


def test_parse_about_readme_malformed_numbered_line_is_skipped_not_crashed():
    md = """
List Of FeedStocks - As Maintainer

1. conda-forge/numpy-feedstock
2. not-a-feedstock-line-at-all
3. conda-forge/pandas-feedstock
"""
    rows = parse_about_readme(md)
    assert [r["feedstock_slug"] for r in rows] == [
        "conda-forge/numpy-feedstock",
        "conda-forge/pandas-feedstock",
    ]


# -- AboutMaintainersDataset --------------------------------------------------


def _about(path, *, fetcher=None) -> AboutMaintainersDataset:
    return AboutMaintainersDataset(filepath=str(path), readme_url=README_URL, fetcher=fetcher)


def test_about_constructs_offline_no_refresher(tmp_path):
    ds = _about(tmp_path / "about")
    assert ds._describe()["refresher_wired"] is False
    assert ds._describe()["readme_url"] == README_URL


def test_about_fetch_success_persists_and_not_stale(tmp_path):
    ds = _about(tmp_path / "about", fetcher=lambda url: ABOUT_README_MD)
    ds.save(RefreshRequest(store="discovery_about_maintainers_raw", force=True))
    assert ds.is_stale() is False
    out = ds.load()
    assert len(out) == 4
    assert set(out["role"]) == {"Maintainer", "Co-Maintainer"}


def test_about_first_run_no_last_good_fetch_failure_marks_stale_empty(tmp_path):
    def boom(url):
        raise ConnectionError("4xx/5xx")

    ds = _about(tmp_path / "about", fetcher=boom)
    ds.save(RefreshRequest(store="discovery_about_maintainers_raw", force=True))  # never raises
    assert ds.is_stale() is True
    assert ds.staleness().last_good_exists is False
    out = ds.load()
    assert out.empty and "feedstock_slug" in out.columns


def test_about_fetch_failure_keeps_last_good_and_marks_stale(tmp_path):
    p = tmp_path / "about"
    _about(p, fetcher=lambda url: ABOUT_README_MD).save(
        RefreshRequest(store="discovery_about_maintainers_raw", force=True)
    )

    def boom(url):
        raise ConnectionError("unreachable")

    ds = _about(p, fetcher=boom)
    ds.save(RefreshRequest(store="discovery_about_maintainers_raw", force=True))
    assert ds.is_stale() is True
    assert ds.staleness().last_good_exists is True
    assert len(ds.load()) == 4  # last-good never clobbered with empty


def test_about_layout_break_keeps_last_good(tmp_path):
    p = tmp_path / "about"
    _about(p, fetcher=lambda url: ABOUT_README_MD).save(
        RefreshRequest(store="discovery_about_maintainers_raw", force=True)
    )
    ds = _about(p, fetcher=lambda url: ABOUT_README_BROKEN_MD)
    ds.save(RefreshRequest(store="discovery_about_maintainers_raw", force=True))
    assert ds.is_stale() is True
    assert len(ds.load()) == 4


def test_about_offline_no_fetcher_marks_stale_and_keeps_last_good(tmp_path):
    p = tmp_path / "about"
    _about(p, fetcher=lambda url: ABOUT_README_MD).save(
        RefreshRequest(store="discovery_about_maintainers_raw", force=True)
    )
    offline = _about(p)
    offline.save(RefreshRequest(store="discovery_about_maintainers_raw", force=True))
    assert offline.is_stale() is True
    assert len(offline.load()) == 4


def test_about_offline_missing_store_load_returns_empty_and_marks_stale(tmp_path):
    ds = _about(tmp_path / "never")
    out = ds.load()
    assert out.empty and "feedstock_slug" in out.columns
    assert ds.is_stale() is True


def test_about_write_rejects_frame_missing_required_columns(tmp_path):
    with pytest.raises(ValueError):
        _about(tmp_path / "about")._write(pd.DataFrame({"nonsense": [1]}))


def test_about_dataset_accepts_response_like_fetcher_payload(tmp_path):
    ds = _about(tmp_path / "about", fetcher=lambda url: _StubTextResponse(text=ABOUT_README_MD))
    ds.save(RefreshRequest(store="discovery_about_maintainers_raw", force=True))
    assert len(ds.load()) == 4
