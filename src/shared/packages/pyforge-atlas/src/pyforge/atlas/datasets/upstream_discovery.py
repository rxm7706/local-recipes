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

**Story 21.4 (Tier 1 catalog sources, CAP-2)** adds three more dataset classes here,
co-located with :class:`TrendingSnapshotDataset` because they share its exact shape:

- :class:`AnacondaDist2026Dataset` (``discovery_anaconda_dist_2026x_raw``) — HTML-scrape
  primary (:func:`parse_anaconda_dist_html`, the anaconda.com 2026.x release-notes package
  table) with a LOCAL git-tracked seed fallback on a scrape layout break (not a second
  HTTP call), then the inherited keep-last-good Parquet degrade.
- :class:`AossPremiumPythonDataset` (``discovery_aoss_premium_python_raw``) — the live
  Google Assured OSS premium-tier doc (:func:`parse_aoss_premium_doc`); on failure the
  inherited ``ExternalRefreshDataset.save()`` keep-last-good + mark-stale applies
  unchanged ("Wayback last-good" in catalog-sources.md is read as exactly that — there is
  no Internet Archive integration here; see the story spec's Design Notes).
- :class:`TrackedSeedDataset` (``discovery_aoss_free_python_raw``) — a small, generic,
  read-only reader over a git-tracked JSON-array seed under ``conf/base/seeds/`` (the
  air-gap contract: zero network, survives a fresh clone). No refresh-trigger node:
  its ``load()`` reads the file directly, so there is no ``save()``-gated emptiness to
  be dormant relative to.

The two HTML sources (Anaconda Dist, AOSS premium) parse with the same ``beautifulsoup4``
+ stdlib ``html.parser`` backend already imported above — no new dependency;
``TrackedSeedDataset`` reads plain JSON. Every parser NEVER raises.
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
from kedro.io import AbstractDataset

from .refresh import (
    DAILY_SECONDS,
    DEFAULT_REFRESH_MAX_RETRIES,
    DEFAULT_REFRESH_TIMEOUT_SECONDS,
    WEEKLY_SECONDS,
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
    except TypeError, ValueError:
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
        except TypeError, ValueError:
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


# ---------------------------------------------------------------------------
# Story 21.4 — Tier 1 catalog sources (CAP-2): tracked seeds, Anaconda Dist 2026.x,
# Google AOSS premium Python
# ---------------------------------------------------------------------------

# The `source` stamp every tracked-seed-derived row carries.
TRACKED_SEED_SOURCE = "tracked_seed"

# The package member dir (src/shared/packages/pyforge-atlas) — the second place a
# RELATIVE seed path is resolved against (after the process CWD), so
# `conf/base/seeds/<file>.json` resolves both for the documented `kedro run` from the
# member dir AND for a caller sitting at the repo root / in a test.
_MEMBER_DIR = Path(__file__).resolve().parents[4]


def _resolve_seed_path(seed_path: str | Path) -> Path:
    path = Path(seed_path)
    if path.is_absolute() or path.exists():
        return path
    candidate = _MEMBER_DIR / path
    return candidate if candidate.exists() else path


def read_tracked_seed(seed_path: str | Path) -> list:
    """Read a git-tracked JSON-array seed file. NEVER raises: a missing / unreadable /
    non-JSON / non-array file (none of which should happen in a real clone — the seeds
    are tracked under ``conf/base/seeds/``, not the gitignored ``data/`` root) degrades
    to ``[]`` + a WARN log."""
    path = _resolve_seed_path(seed_path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:  # ValueError covers JSONDecodeError + UnicodeDecodeError
        logger.warning("tracked seed %s unreadable, degrading to empty: %s", path, exc)
        return []
    if not isinstance(raw, list):
        logger.warning("tracked seed %s is not a JSON array, degrading to empty", path)
        return []
    return raw


class TrackedSeedDataset(AbstractDataset):
    """A generic, READ-ONLY git-tracked-JSON-array reader (Story 21.4 — backs
    ``discovery_aoss_free_python_raw``, the "tracked seed" fetch mode).

    ``load()`` returns a ``<name_column>`` / ``source="tracked_seed"`` frame — one row per
    array entry (a bare string, or a dict carrying ``name_column``); blank / non-string /
    duplicate names are dropped. No network, ever. A missing or corrupt file degrades to
    an EMPTY frame + a WARN (never raises); ``save()`` raises ``NotImplementedError``
    like every other read-only dataset in this package (the seed is edited by hand
    under git review, never written by a pipeline).
    """

    def __init__(
        self,
        *,
        filepath: str,
        name_column: str = "pypi_name",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        # No **kwargs sink: an unrecognized catalog key must raise loudly.
        self._filepath = str(filepath)
        self._name_column = str(name_column)
        self.metadata = metadata

    @property
    def _columns(self) -> list[str]:
        return [self._name_column, "source"]

    def load(self) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for entry in read_tracked_seed(self._filepath):
            name = entry.get(self._name_column) if isinstance(entry, dict) else entry
            if not isinstance(name, str):
                continue
            name = name.strip()
            if not name or name in seen:
                continue
            seen.add(name)
            rows.append({self._name_column: name, "source": TRACKED_SEED_SOURCE})
        return pd.DataFrame(rows, columns=self._columns)

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is read-only (git-tracked seed)")

    def _describe(self) -> dict[str, Any]:
        return {
            "filepath": self._filepath,
            "resolved": str(_resolve_seed_path(self._filepath)),
            "name_column": self._name_column,
            "source": TRACKED_SEED_SOURCE,
        }


def _as_text(payload: Any) -> str | None:
    """Normalize an injected-fetcher return value to response TEXT: a ``str``, UTF-8
    ``bytes``, or a Response-like object exposing ``.text`` (str) / ``.content`` (bytes)
    (review-pass 1: such an object used to parse as empty every time, leaving the store
    stale forever with no error). ``None`` when nothing text-like is found."""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, bytes):
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError:
            return None
    text = getattr(payload, "text", None)
    if isinstance(text, str):
        return text
    content = getattr(payload, "content", None)
    if isinstance(content, bytes):
        return _as_text(content)
    return None


# -- Anaconda Distribution 2026.x ---------------------------------------------

# The release-notes page's package table starts with this header cell (live shape
# 2026-08-30: ``Package Name | linux-64 | linux-aarch64 | osx-arm64 | win-64``, 639
# rows; three further per-platform tables follow — the FIRST all-platform table wins).
_ANACONDA_DIST_NAME_HEADER = "package name"
_ANACONDA_DIST_COLUMNS: tuple[str, ...] = ("conda_name", "version", "platforms", "source", "fetched_at")


def parse_anaconda_dist_html(html: Any) -> list[dict]:
    """Parse the anaconda.com Anaconda Distribution 2026.x release-notes page
    (BeautifulSoup + stdlib ``html.parser``). Reads every ``<table>`` whose header row
    begins with ``Package Name`` and returns the LARGEST one (review-pass 1: a small
    changelog table with the same header may precede the full list — the all-platform
    package table is the biggest by construction), one row per package: ``conda_name``,
    ``version`` (the ``linux-64`` column when present, else the first non-empty
    platform cell), ``platforms`` (the header columns carrying a version), tagged
    ``source="html_scrape"`` + ``fetched_at``.

    Returns ``[]`` — NEVER raises — on a layout break (no such table, an empty table, a
    malformed document): the dataset then falls back to its tracked seed. ``html`` may be
    text, bytes, or a Response-like object (see :func:`_as_text`)."""
    text = _as_text(html)
    if not text:
        return []
    try:
        soup = BeautifulSoup(text, "html.parser")
        tables = soup.find_all("table")
    except Exception as exc:  # a malformed document must never crash the run (AD-13)
        logger.warning("anaconda dist HTML parse failed: %s", exc)
        return []

    fetched_at = int(time.time())
    best: list[dict[str, Any]] = []
    for table in tables:
        trs = table.find_all("tr")
        if not trs:
            continue
        header = [c.get_text(strip=True) for c in trs[0].find_all(["th", "td"])]
        if not header or header[0].strip().lower() != _ANACONDA_DIST_NAME_HEADER:
            continue
        platforms = header[1:]
        rows: list[dict[str, Any]] = []
        for tr in trs[1:]:
            cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
            if not cells or not cells[0]:
                continue
            versions = dict(zip(platforms, cells[1:]))
            present = [p for p in platforms if versions.get(p)]
            version = versions.get("linux-64") or (versions[present[0]] if present else None)
            rows.append(
                {
                    "conda_name": cells[0],
                    "version": version or None,
                    "platforms": present,
                    "source": "html_scrape",
                    "fetched_at": fetched_at,
                }
            )
        if len(rows) > len(best):
            best = rows
    return best


class AnacondaDist2026Dataset(ExternalRefreshDataset):
    """Story 21.4 — Anaconda Distribution 2026.x package list
    (``discovery_anaconda_dist_2026x_raw``; catalog-sources.md Tier 1, "HTML extractor +
    seed fallback").

    Mirrors :class:`TrendingSnapshotDataset._do_refresh`'s "try the live source; if it
    yields zero rows, fall back" shape exactly — but the fallback is a LOCAL read of the
    git-tracked ``conf/base/seeds/discovery_anaconda_dist_2026x_seed.json`` file (never a
    second HTTP call). If BOTH the scrape and the seed are empty, the inherited
    ``save()`` keep-last-good + mark-stale applies (AD-13). ``fetcher=None`` == offline:
    construction is network-free; a DUE refresh keeps last-good + marks stale.
    """

    STORE_FILENAME = "anaconda_dist_2026x.parquet"
    _REQUIRED_COLUMNS = ("conda_name", "source", "fetched_at")

    def __init__(
        self,
        *,
        filepath: str,
        url: str,
        seed_path: str,
        fetcher: Callable[[str], str] | None = None,
        cadence_seconds: int | None = None,
        timeout_seconds: int = DEFAULT_REFRESH_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_REFRESH_MAX_RETRIES,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._url = str(url)
        self._seed_path = str(seed_path)
        self._fetcher = fetcher
        super().__init__(
            filepath=filepath,
            refresher=self._do_refresh if fetcher is not None else None,
            cadence_seconds=cadence_seconds if cadence_seconds is not None else WEEKLY_SECONDS,
            required_resource=None,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            metadata=metadata,
        )

    def _seed_rows(self) -> list[dict]:
        """The tracked seed as rows in the SAME shape the scraper emits, tagged
        ``source="tracked_seed"``. Entries may be bare names or
        ``{conda_name, version, platforms}`` dicts; anything else is skipped."""
        fetched_at = int(time.time())
        rows: list[dict[str, Any]] = []
        for entry in read_tracked_seed(self._seed_path):
            if isinstance(entry, str):
                name, version, platforms = entry, None, []
            elif isinstance(entry, dict):
                name = entry.get("conda_name")
                version = entry.get("version")
                platforms = entry.get("platforms") or []
            else:
                continue
            if not isinstance(name, str) or not name.strip():
                continue
            rows.append(
                {
                    "conda_name": name.strip(),
                    "version": version if isinstance(version, str) else None,
                    "platforms": list(platforms) if isinstance(platforms, (list, tuple)) else [],
                    "source": TRACKED_SEED_SOURCE,
                    "fetched_at": fetched_at,
                }
            )
        return rows

    def _do_refresh(self) -> pd.DataFrame:
        """Scrape; on zero rows (fetch failure OR layout break) fall back to the tracked
        seed. Never raises."""
        rows: list[dict] = []
        try:
            html = self._fetcher(self._url)
        except Exception as exc:  # AD-13: a fetch failure degrades, never aborts.
            logger.warning("anaconda dist scrape fetch failed: %s", exc)
            html = None
        if html is not None:
            rows = parse_anaconda_dist_html(html)
        if not rows:
            logger.warning(
                "anaconda dist scrape yielded zero rows (fetch failure / layout break) — "
                "falling back to the tracked seed %s",
                self._seed_path,
            )
            rows = self._seed_rows()
        return pd.DataFrame(rows, columns=list(_ANACONDA_DIST_COLUMNS))

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
            raise ValueError(f"anaconda dist refresh frame missing required columns: {missing}")
        self._atomic_write(self._store_path, lambda p: frame.to_parquet(p, index=False))

    def load(self) -> pd.DataFrame:
        if not self._store_exists():
            self._mark_stale(
                "anaconda dist 2026.x store absent (never refreshed / offline)",
                only_if_absent=True,
            )
            return pd.DataFrame(columns=list(_ANACONDA_DIST_COLUMNS))
        try:
            return pd.read_parquet(self._store_path)
        except Exception as exc:
            logger.warning(
                "anaconda dist 2026.x store unreadable (%s), degrading to empty: %s",
                self._store_path,
                exc,
            )
            self._mark_stale("anaconda dist 2026.x store unreadable", only_if_absent=True)
            return pd.DataFrame(columns=list(_ANACONDA_DIST_COLUMNS))

    def _describe(self) -> dict[str, Any]:
        base = super()._describe()
        base.update({"url": self._url, "seed_path": self._seed_path})
        return base


# -- Google Assured OSS premium-tier Python ------------------------------------

# Both AOSS "supported packages" docs (free tier: assured-open-source-software/docs/
# supported-packages; premium tier: security-command-center/docs/
# aoss-supported-packages-premium) share one shape (live-verified 2026-08-30): an
# ``<h2 id="python">Supported Python packages</h2>`` heading followed by a ``<ul>`` of one
# ``<li>`` per package name (free 1,474 / premium 2,156 incl. 2 duplicates).
_AOSS_PYTHON_HEADING_ID = "python"
_AOSS_PREMIUM_COLUMNS: tuple[str, ...] = ("pypi_name", "tier", "source", "fetched_at")


def parse_aoss_python_package_names(html: Any) -> list[str]:
    """The Python package names an AOSS "supported packages" doc lists: the ``<ul>``
    right after the ``#python`` heading (fallback: any ``h2``/``h3`` mentioning "Python
    packages"), one ``<li>`` per name, de-duplicated in page order. ``[]`` — never
    raises — on a layout break or a non-text payload. Shared by
    :func:`parse_aoss_premium_doc` and the one-off acquisition of the free-tier seed."""
    text = _as_text(html)
    if not text:
        return []
    try:
        soup = BeautifulSoup(text, "html.parser")
        heading = soup.find(id=_AOSS_PYTHON_HEADING_ID)
        if heading is None:
            heading = next(
                (h for h in soup.find_all(["h2", "h3"]) if "python packages" in h.get_text(" ", strip=True).lower()),
                None,
            )
        listing = heading.find_next("ul") if heading is not None else None
        items = listing.find_all("li") if listing is not None else []
    except Exception as exc:  # AD-13: a malformed document never crashes the run.
        logger.warning("AOSS supported-packages HTML parse failed: %s", exc)
        return []
    names: list[str] = []
    seen: set[str] = set()
    for li in items:
        name = li.get_text(" ", strip=True)
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def parse_aoss_premium_doc(payload: Any) -> list[dict]:
    """PURE parser for the live AOSS premium-tier Python doc -> one row per package:
    ``pypi_name`` / ``tier="premium"`` / ``source="html_scrape"`` / ``fetched_at``.
    ``[]`` (never raises) on a layout break."""
    fetched_at = int(time.time())
    return [
        {"pypi_name": name, "tier": "premium", "source": "html_scrape", "fetched_at": fetched_at}
        for name in parse_aoss_python_package_names(payload)
    ]


class AossPremiumPythonDataset(ExternalRefreshDataset):
    """Story 21.4 — Google Assured OSS premium-tier Python catalog
    (``discovery_aoss_premium_python_raw``; catalog-sources.md Tier 1, "Live doc").

    One live-doc fetch via the injected ``fetcher`` + :func:`parse_aoss_premium_doc`. On
    a fetch failure / layout break the INHERITED ``ExternalRefreshDataset.save()``
    keep-last-good-Parquet + mark-stale behavior applies unchanged — no extra fallback
    tier (the "Wayback last-good" note is read as this same AD-13 degrade; a literal
    Internet Archive fetch is NOT built here — story spec Design Notes).
    """

    STORE_FILENAME = "aoss_premium_python.parquet"
    _REQUIRED_COLUMNS = ("pypi_name", "source", "fetched_at")

    def __init__(
        self,
        *,
        filepath: str,
        url: str,
        fetcher: Callable[[str], str] | None = None,
        cadence_seconds: int | None = None,
        timeout_seconds: int = DEFAULT_REFRESH_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_REFRESH_MAX_RETRIES,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._url = str(url)
        self._fetcher = fetcher
        super().__init__(
            filepath=filepath,
            refresher=self._do_refresh if fetcher is not None else None,
            cadence_seconds=cadence_seconds if cadence_seconds is not None else WEEKLY_SECONDS,
            required_resource=None,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            metadata=metadata,
        )

    def _do_refresh(self) -> pd.DataFrame:
        """Fetch + parse the live doc. Never raises — a fetch failure WARNs and returns
        an empty frame (which ``save()`` turns into keep-last-good + mark stale)."""
        try:
            payload = self._fetcher(self._url)
        except Exception as exc:  # AD-13
            logger.warning("AOSS premium doc fetch failed: %s", exc)
            return pd.DataFrame(columns=list(_AOSS_PREMIUM_COLUMNS))
        rows = parse_aoss_premium_doc(payload)
        if not rows:
            logger.warning("AOSS premium doc parsed zero packages (layout break?) — keeping last-good")
        return pd.DataFrame(rows, columns=list(_AOSS_PREMIUM_COLUMNS))

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
            raise ValueError(f"AOSS premium refresh frame missing required columns: {missing}")
        self._atomic_write(self._store_path, lambda p: frame.to_parquet(p, index=False))

    def load(self) -> pd.DataFrame:
        if not self._store_exists():
            self._mark_stale(
                "AOSS premium python store absent (never refreshed / offline)",
                only_if_absent=True,
            )
            return pd.DataFrame(columns=list(_AOSS_PREMIUM_COLUMNS))
        try:
            return pd.read_parquet(self._store_path)
        except Exception as exc:
            logger.warning(
                "AOSS premium python store unreadable (%s), degrading to empty: %s",
                self._store_path,
                exc,
            )
            self._mark_stale("AOSS premium python store unreadable", only_if_absent=True)
            return pd.DataFrame(columns=list(_AOSS_PREMIUM_COLUMNS))

    def _describe(self) -> dict[str, Any]:
        base = super()._describe()
        base.update({"url": self._url})
        return base


# ---------------------------------------------------------------------------
# Story 21.5 — Tier 2 catalog sources (spec-21-5-tier-2-sources.md, CDO-ENT-CONDA):
# rxm7706/about maintainer + co-maintainer feedstock lists
# ---------------------------------------------------------------------------

_ABOUT_MAINTAINERS_COLUMNS: tuple[str, ...] = ("feedstock_slug", "role", "source", "fetched_at")
_ABOUT_MAINTAINERS_SOURCE = "about_readme"

# The two numbered-list section headers rxm7706/about's README.md carries (live
# snapshot 2026-07-11 — Block If: re-confirm against the live file before trusting
# this regex if the shape has since drifted). Matched by ``str.startswith`` (mirrors
# the legacy ``parse_feedstocks_from_about``) so a trailing anchor/punctuation change
# doesn't break the match.
_ABOUT_SECTION_HEADERS: tuple[tuple[str, str], ...] = (
    ("List Of FeedStocks - As Maintainer", "Maintainer"),
    ("List Of FeedStocks - As Co-Maintainer", "Co-Maintainer"),
)

# Captures the FULL ``conda-forge/<feedstock>-feedstock`` slug (not just the bare
# name) — join_enterprise_conda_maintainers (pipelines/upstream_discovery/nodes.py)
# strips the prefix/suffix at JOIN time, per the story spec's explicit "strip before
# comparing" contract.
_ABOUT_FEEDSTOCK_LINE_RE = re.compile(r"^\d+\.\s+(conda-forge/[a-zA-Z0-9._-]+-feedstock)\s*$")


def parse_about_readme(markdown: str) -> list[dict]:
    """Parse ``rxm7706/about``'s ``README.md`` two numbered feedstock lists
    ("List Of FeedStocks - As Maintainer" / "... - As Co-Maintainer") into
    ``feedstock_slug``/``role`` rows. PURE — mirrors :func:`parse_trending_html`'s
    degrade contract exactly: a missing/renamed section header, a malformed
    ``N. conda-forge/<x>-feedstock`` line, or an empty README all degrade the
    AFFECTED list to zero rows for that role — NEVER raises.

    A non-blank line that is neither a recognized section header nor a matching
    numbered feedstock line ENDS the current section (mirrors the legacy
    ``parse_feedstocks_from_about``'s "line and not digit -> reset" rule) so a
    trailing note/paragraph after a list doesn't get misread as belonging to it.
    """
    if not markdown:
        return []
    fetched_at = int(time.time())
    rows: list[dict[str, Any]] = []
    try:
        current_role: str | None = None
        for raw_line in markdown.splitlines():
            line = raw_line.strip()
            matched_header = False
            for header, role in _ABOUT_SECTION_HEADERS:
                if line.startswith(header):
                    current_role = role
                    matched_header = True
                    break
            if matched_header:
                continue
            if current_role is None:
                continue
            m = _ABOUT_FEEDSTOCK_LINE_RE.match(line)
            if m:
                rows.append(
                    {
                        "feedstock_slug": m.group(1),
                        "role": current_role,
                        "source": _ABOUT_MAINTAINERS_SOURCE,
                        "fetched_at": fetched_at,
                    }
                )
                continue
            if line and not line[0].isdigit():
                current_role = None
    except Exception as exc:  # pragma: no cover - defensive; AD-13 never-raise
        logger.warning("about README parse failed: %s", exc)
        return []
    return rows


class AboutMaintainersDataset(ExternalRefreshDataset):
    """Story 21.5 (Tier 2, CDO-ENT-CONDA) — ``rxm7706/about``'s README maintainer +
    co-maintainer feedstock lists (``discovery_about_maintainers_raw``).

    Mirrors :class:`AossPremiumPythonDataset`'s shape exactly: a SINGLE injected-fetch
    live doc (no 3-period fan-out, no fallback tier — a plain unauthenticated GitHub-raw
    GET) parsed by :func:`parse_about_readme`. On a fetch failure / layout break the
    INHERITED ``ExternalRefreshDataset.save()`` keep-last-good-Parquet + mark-stale
    behavior applies unchanged (AD-13). ``fetcher=None`` == offline: construction is
    network-free; a DUE refresh keeps last-good + marks stale.
    """

    STORE_FILENAME = "about_maintainers.parquet"
    _REQUIRED_COLUMNS = _ABOUT_MAINTAINERS_COLUMNS

    def __init__(
        self,
        *,
        filepath: str,
        readme_url: str,
        fetcher: Callable[[str], str] | None = None,
        cadence_seconds: int | None = None,
        timeout_seconds: int = DEFAULT_REFRESH_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_REFRESH_MAX_RETRIES,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._readme_url = str(readme_url)
        self._fetcher = fetcher
        super().__init__(
            filepath=filepath,
            refresher=self._do_refresh if fetcher is not None else None,
            cadence_seconds=cadence_seconds if cadence_seconds is not None else WEEKLY_SECONDS,
            required_resource=None,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            metadata=metadata,
        )

    def _do_refresh(self) -> pd.DataFrame:
        """Fetch + parse the README once. Never raises — a fetch failure WARNs and
        returns an empty frame (which ``save()`` turns into keep-last-good + mark
        stale)."""
        try:
            payload = self._fetcher(self._readme_url)
        except Exception as exc:  # AD-13
            logger.warning("about README fetch failed: %s", exc)
            return pd.DataFrame(columns=list(_ABOUT_MAINTAINERS_COLUMNS))
        text = _as_text(payload)
        rows = parse_about_readme(text) if text else []
        if not rows:
            logger.warning("about README parsed zero maintainer rows (layout break / empty fetch) — keeping last-good")
        return pd.DataFrame(rows, columns=list(_ABOUT_MAINTAINERS_COLUMNS))

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
            raise ValueError(f"about maintainers refresh frame missing required columns: {missing}")
        self._atomic_write(self._store_path, lambda p: frame.to_parquet(p, index=False))

    def load(self) -> pd.DataFrame:
        if not self._store_exists():
            self._mark_stale(
                "about maintainers store absent (never refreshed / offline)",
                only_if_absent=True,
            )
            return pd.DataFrame(columns=list(_ABOUT_MAINTAINERS_COLUMNS))
        try:
            return pd.read_parquet(self._store_path)
        except Exception as exc:
            logger.warning(
                "about maintainers store unreadable (%s), degrading to empty: %s",
                self._store_path,
                exc,
            )
            self._mark_stale("about maintainers store unreadable", only_if_absent=True)
            return pd.DataFrame(columns=list(_ABOUT_MAINTAINERS_COLUMNS))

    def _describe(self) -> dict[str, Any]:
        base = super()._describe()
        base.update({"readme_url": self._readme_url})
        return base
