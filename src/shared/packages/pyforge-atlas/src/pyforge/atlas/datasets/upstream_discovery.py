"""GitHub-trending discovery ingest — CAP-1's dataset (Story 13.1, FR-64).

Epic 13 (Upstream discovery) starts with CAP-1: nothing today ingests GitHub-trending
Python repos into the shipped Kedro/Dagster/DuckDB dataflow — the legacy
``docs/specs/trendshift-conda-forge.md`` "Phase T" never shipped. This module owns the
whole IO/degradation contract for the ``trending_candidates`` catalog entry:

- :class:`TrendingSnapshotDataset` — subclasses :class:`ExternalRefreshDataset` (the same
  base B5 used for ``vulnerability_vdb_store``) to get the cadence-check / atomic-write /
  never-clobber / :class:`StalenessMarker` machinery for free (AD-13). It owns the
  injected fetch of the 3 ``github.com/trending/python?since=<period>`` HTML pages
  (daily/weekly/monthly) + a GitHub Search API fallback/corroboration source.
- :func:`parse_trending_html` / :func:`parse_search_api_response` — the two PURE parser
  functions (colocated with the dataset class, mirroring ``migration_status.py``'s
  ``migration_names()`` precedent). Neither ever raises: a scrape layout break (the parser
  matches zero repo cards) or a malformed Search API payload degrades to ``[]``, never a
  crash — this is what makes CAP-1's "layout break -> WARN + keep-last-good" contract hold.

**Dataset-owned IO, node stays pure (AD-2).** All fetch + HTML/JSON parsing lives HERE;
``pipelines/upstream_discovery/nodes.py`` is a pure ``params -> RefreshRequest`` trigger,
mirroring ``pipelines/vulnerability/nodes.py::refresh_vdb_store`` exactly — no HTTP/parse
imports there. This module parses with ``beautifulsoup4`` + the stdlib ``html.parser``
backend only — no ``lxml`` / ``requests`` / ``httpx`` dependency is added.

**Deliberately UNAUTHENTICATED.** Neither the scrape nor the Search API fallback carries a
``credentials:`` key — both route through the EXISTING ``GITHUB_BASE_URL`` /
``GITHUB_API_BASE_URL`` override points (no new override point). Staying uncredentialed
(rate-limited but functional) keeps this pipeline schedule-eligible without triggering
AD-11's attended-only-credentialed-run rule.
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Callable

import pandas as pd
from bs4 import BeautifulSoup

from .refresh import (
    DAILY_SECONDS,
    DEFAULT_REFRESH_MAX_RETRIES,
    DEFAULT_REFRESH_TIMEOUT_SECONDS,
    ExternalRefreshDataset,
)

logger = logging.getLogger(__name__)

# The Search API fallback has no daily/weekly/monthly time window (it is a plain
# stars-sorted query) — rows from it are stamped this period value rather than
# misrepresenting a window that was never applied.
_SEARCH_API_FALLBACK_PERIOD = "all"

# GitHub's trending page phrases the period delta differently per view — "N stars
# today" (daily), "N stars this week" (weekly), "N stars this month" (monthly). Matching
# only "today" left stars_today permanently None for 2 of the 3 fetched periods (review
# finding, Story 13.1) — match all three phrasings, not just the daily one.
_STARS_DELTA_RE = re.compile(r"([\d,]+)\s+stars?\s+(?:today|this\s+week|this\s+month)", re.IGNORECASE)
_DIGITS_RE = re.compile(r"[\d,]+")

# The title link's href is expected to be the site-relative `owner/repo` form (after
# stripping slashes). An absolute URL or a multi-segment path doesn't get cleaned up by
# `.strip("/")` alone and would otherwise persist a garbled repo_full_name/repo_url
# instead of degrading gracefully (review finding, Story 13.1).
_REPO_FULL_NAME_RE = re.compile(r"[^/]+/[^/]+")


def _parse_count(text: str | None) -> int | None:
    """Extract the first integer (comma-grouped digits allowed) from ``text``; ``None``
    when absent/unparseable — never raises."""
    if not text:
        return None
    m = _DIGITS_RE.search(text)
    if not m:
        return None
    try:
        return int(m.group(0).replace(",", ""))
    except ValueError:  # pragma: no cover - _DIGITS_RE only matches digit/comma runs
        return None


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_trending_html(html: str, *, period: str) -> list[dict]:
    """Parse one ``github.com/trending/python?since=<period>`` page (BeautifulSoup + the
    stdlib ``html.parser`` backend — NO ``lxml``). One row per trending repo card
    (``article.Box-row``): ``repo_full_name`` / ``repo_url`` / ``description`` / ``language``
    / ``stars_total`` / ``stars_today`` / ``forks_total``, tagged ``period`` and
    ``source="html_scrape"``.

    Returns ``[]`` — NEVER raises — when the expected repo-card structure isn't found (a
    malformed document, an empty page, or an upstream markup change): a scrape layout
    break must degrade gracefully, not crash the run (CAP-1's whole point)."""
    if not html:
        return []
    try:
        soup = BeautifulSoup(html, "html.parser")
        articles = soup.select("article.Box-row")
    except Exception as exc:  # a malformed document must never crash the run (AD-13)
        logger.warning("trending HTML parse failed for period=%s: %s", period, exc)
        return []

    fetched_at = int(time.time())
    rows: list[dict[str, Any]] = []
    for article in articles:
        h2 = article.find("h2")
        link = h2.find("a", href=True) if h2 is not None else None
        if link is None:
            continue
        repo_full_name = (link.get("href") or "").strip("/").strip()
        if not repo_full_name or not _REPO_FULL_NAME_RE.fullmatch(repo_full_name):
            continue

        desc_tag = article.find("p")
        description = desc_tag.get_text(strip=True) if desc_tag is not None else None

        lang_tag = article.find(attrs={"itemprop": "programmingLanguage"})
        language = (lang_tag.get_text(strip=True) if lang_tag is not None else None) or None

        stars_tag = article.select_one('a[href$="/stargazers"]')
        forks_tag = article.select_one('a[href$="/forks"]')
        article_text = article.get_text(" ", strip=True)
        today_match = _STARS_DELTA_RE.search(article_text)

        rows.append(
            {
                "repo_full_name": repo_full_name,
                # Derived from the scraped relative href, not a new fetch endpoint (the
                # actual fetch always routes through the injected fetcher + the
                # GITHUB_BASE_URL/GITHUB_API_BASE_URL catalog config — AD-2).
                "repo_url": f"https://github.com/{repo_full_name}",
                "description": description or None,
                "language": language,
                "stars_total": _parse_count(stars_tag.get_text() if stars_tag is not None else None),
                "stars_today": _parse_count(today_match.group(0)) if today_match else None,
                "forks_total": _parse_count(forks_tag.get_text() if forks_tag is not None else None),
                "period": period,
                "source": "html_scrape",
                "fetched_at": fetched_at,
            }
        )
    return rows


def parse_search_api_response(payload: Any) -> list[dict]:
    """Parse the GitHub Search API's ``{"items": [...]}`` shape (the CAP-1 fallback,
    tried only when the HTML scrape yields zero rows across all 3 periods). Each item
    carries ``full_name`` / ``html_url`` / ``description`` / ``language`` /
    ``stargazers_count`` / ``forks_count``. ``stars_today`` is always ``None`` (the
    Search API has no daily-delta signal); ``period`` is stamped ``"all"`` (see
    :data:`_SEARCH_API_FALLBACK_PERIOD` — a plain stars-sorted query has no
    daily/weekly/monthly window to report).

    ``payload`` may be an already-parsed ``dict`` OR a raw JSON ``str`` — the injected
    ``fetcher`` is declared ``Callable[[str], str]`` (it returns response TEXT for every
    URL it fetches, scrape pages included), so the search endpoint's response arrives
    here as text too; this function does its own ``json.loads`` rather than assuming a
    caller pre-parsed it. Robust to a malformed/non-dict/non-JSON payload or a non-list
    ``items`` — returns ``[]`` rather than raising."""
    if isinstance(payload, (str, bytes)):
        try:
            payload = json.loads(payload)
        except (TypeError, ValueError):
            return []
    if not isinstance(payload, dict):
        return []
    items = payload.get("items")
    if not isinstance(items, list):
        return []

    fetched_at = int(time.time())
    rows: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        full_name = item.get("full_name")
        if not full_name:
            continue
        rows.append(
            {
                "repo_full_name": str(full_name),
                "repo_url": item.get("html_url"),
                "description": item.get("description"),
                "language": item.get("language"),
                "stars_total": _safe_int(item.get("stargazers_count")),
                "stars_today": None,
                "forks_total": _safe_int(item.get("forks_count")),
                "period": _SEARCH_API_FALLBACK_PERIOD,
                "source": "search_api_fallback",
                "fetched_at": fetched_at,
            }
        )
    return rows


class TrendingSnapshotDataset(ExternalRefreshDataset):
    """The GitHub-trending candidate snapshot — CAP-1's ``trending_candidates`` dataset.

    Subclasses :class:`ExternalRefreshDataset` (the same base B5 used for
    ``vulnerability_vdb_store``) to get the cadence-check / atomic-write / never-clobber /
    :class:`StalenessMarker` machinery for free — see that class + :class:`VDBStoreDataset`
    for the shape this mirrors.

    - ``save`` (inherited, the SINGLE writer): when a refresh is DUE, invokes
      :meth:`_do_refresh` (dataset-owned IO — the fetch/parse never lives in node code).
    - :meth:`_do_refresh`: for each of the 3 ``daily``/``weekly``/``monthly`` period URLs,
      fetches via the injected low-level ``fetcher: Callable[[str], str]`` and parses with
      :func:`parse_trending_html`; a per-period fetch/parse failure is WARNed and treated
      as zero rows for THAT period only (never aborts the whole run). If the COMBINED
      result across all 3 periods is empty (a scrape layout break), falls back to the
      GitHub Search API (:func:`parse_search_api_response`). An empty combined+fallback
      result is handled by the INHERITED ``_is_empty`` check in ``save()`` — keep last-good
      + mark stale, never write (no duplicate empty-check needed here).
    - :meth:`_write`: validates ``repo_full_name``/``period``/``fetched_at`` are present
      (rejects a malformed frame — mirrors ``VDBStoreDataset._write``'s malformed-column
      rejection), then atomic-writes Parquet to ``STORE_FILENAME`` under ``filepath``.
    - :meth:`load`: reads the persisted parquet; a missing/unreadable store degrades to an
      empty frame + a staleness marker (mirrors ``VDBStoreDataset.load``).
    """

    STORE_FILENAME = "trending_candidates.parquet"
    _REQUIRED_COLUMNS = ("repo_full_name", "period", "source", "fetched_at")

    def __init__(
        self,
        *,
        filepath: str,
        daily_url: str,
        weekly_url: str,
        monthly_url: str,
        search_api_url: str,
        fetcher: Callable[[str], str] | None = None,
        cadence_seconds: int | None = None,
        timeout_seconds: int = DEFAULT_REFRESH_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_REFRESH_MAX_RETRIES,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._daily_url = str(daily_url)
        self._weekly_url = str(weekly_url)
        self._monthly_url = str(monthly_url)
        self._search_api_url = str(search_api_url)
        # Low-level "GET this URL, return response text" callable (injected IO). None ==
        # offline (no live fetch) — a DUE refresh keeps last-good and marks stale, exactly
        # like every other ExternalRefreshDataset subclass. NEVER imported here; the
        # concrete fetcher is supplied by the Dagster resource / an attended run (mirrors
        # DW-B5-2) — this dataset only ever calls the injected seam.
        self._fetcher = fetcher
        super().__init__(
            filepath=filepath,
            # Wrap the low-level per-URL fetcher into OUR OWN bound zero-arg refresh
            # method — only when a fetcher is actually wired, so construction stays
            # offline (kedro-catalog-check resolves this entry with no fetcher at all).
            refresher=self._do_refresh if fetcher is not None else None,
            cadence_seconds=cadence_seconds if cadence_seconds is not None else DAILY_SECONDS,
            required_resource=None,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            metadata=metadata,
        )

    # -- refresh (dataset-owned IO; the injected fetcher is the ONLY seam) --

    def _do_refresh(self) -> pd.DataFrame:
        """Fetch + parse the 3 period pages; fall back to the Search API when the
        combined result is empty (a scrape layout break). Never raises — a per-period
        fetch/parse failure is WARNed and treated as zero rows for that period only."""
        rows: list[dict[str, Any]] = []
        for period, url in (
            ("daily", self._daily_url),
            ("weekly", self._weekly_url),
            ("monthly", self._monthly_url),
        ):
            try:
                html = self._fetcher(url)
            except Exception as exc:  # AD-13: one bad period never aborts the run.
                logger.warning("trending scrape fetch failed for period=%s: %s", period, exc)
                continue
            period_rows = parse_trending_html(html, period=period)
            if not period_rows:
                # A per-period layout break (fetch succeeded, parser matched zero repo
                # cards) is otherwise silent unless ALL 3 periods break together — log it
                # here so a single broken period doesn't vanish untracked (review finding,
                # Story 13.1).
                logger.warning("trending scrape parsed zero rows for period=%s", period)
            rows.extend(period_rows)

        if not rows:
            logger.warning(
                "trending scrape yielded zero rows across daily/weekly/monthly "
                "(scrape layout break) — falling back to the GitHub Search API"
            )
            payload = None
            try:
                payload = self._fetcher(self._search_api_url)
            except Exception as exc:  # AD-13: fallback failure keeps last-good, never raises.
                logger.warning("Search API fallback fetch failed: %s", exc)
            if payload is not None:
                rows = parse_search_api_response(payload)

        return pd.DataFrame(rows)

    # -- store (Parquet under filepath/STORE_FILENAME) -----------------------

    @property
    def _store_path(self) -> Path:
        return Path(self._filepath) / self.STORE_FILENAME

    def _store_exists(self) -> bool:
        return self._store_path.is_file()

    def _store_mtime(self) -> float:
        return self._store_path.stat().st_mtime

    def _write(self, fetched: Any) -> None:
        frame = fetched if isinstance(fetched, pd.DataFrame) else pd.DataFrame(fetched)
        missing = [c for c in self._REQUIRED_COLUMNS if c not in frame.columns]
        if missing:
            # A malformed refresh must not silently persist a store that reads as "no
            # candidates" downstream — reject it so save() keeps last-good + marks stale.
            raise ValueError(f"trending refresh frame missing required columns: {missing}")
        self._atomic_write(self._store_path, lambda p: frame.to_parquet(p, index=False))

    def load(self) -> pd.DataFrame:
        if not self._store_exists():
            self._mark_stale(
                "trending candidates store absent (never refreshed / offline)",
                only_if_absent=True,
            )
            return pd.DataFrame()
        try:
            return pd.read_parquet(self._store_path)
        except Exception as exc:  # corrupt/truncated store must not crash the consumer.
            logger.warning(
                "trending candidates store unreadable (%s), degrading to empty: %s",
                self._store_path,
                exc,
            )
            self._mark_stale("trending candidates store unreadable", only_if_absent=True)
            return pd.DataFrame()
