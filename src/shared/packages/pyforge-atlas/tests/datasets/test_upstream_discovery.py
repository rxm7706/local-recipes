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
def test_parse_trending_html_stars_delta_matches_all_three_period_phrasings(
    html, period, expected_stars_today
):
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
