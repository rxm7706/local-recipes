"""Story 21.6 (CAP-3, Phase D identity join) — the four NEW dataset-owned source
classes that replace the legacy ``scripts/conda-forge-packaging-inventory-
operations_openteams_identity.py``'s live-fetch/parse surfaces: the PURL
Associator mappings index, the OpenTeams project 1 GraphQL board, the
conda-forge/staged-recipes PR REST API, and a local ``recipes/`` filesystem scan.

**AD-2**: all fetch/parse/rate-limit/fallback IO for the three LIVE sources lives
HERE; ``pipelines/upstream_discovery/nodes.py::build_identity_packages_primary``
stays a pure ``DataFrame -> DataFrame`` join over the already-fetched frames these
classes persist.

- :class:`PurlAssociatorMappingsDataset` (``purl_associator_mappings_raw``) —
  mirrors :class:`~.upstream_discovery.TrendingSnapshotDataset`'s
  ``ExternalRefreshDataset`` shape: fetches ``mappings-index.json`` once (the
  "index required at bootstrap" half of identity-contract.md's two-tier
  contract) and persists ONE row per associator package, with
  ``alternative_purls``/``cpes`` already ``; ``-joined the same way the legacy
  script's own ``from_assoc``/``alt_purls`` emit them onto the output row — the
  live ``mappings-index.json`` payload embeds these fields inline per record
  (verified against the legacy script's own working ``lookup_assoc``/
  ``from_assoc`` call sites, which never perform a second fetch either).
  :meth:`PurlAssociatorMappingsDataset.fetch_shard` is exposed as a
  forward-compatible per-package enrichment seam for the "shards fetched on
  demand" half of identity-contract.md's contract, callable by a future attended
  enrichment pass, but is **not** invoked by the default
  ``build_identity_packages_primary`` join (which stays pure per AD-2 and
  consumes only the already-persisted inline fields) — a deliberate, documented
  v1 scope decision, not a defect.
- :class:`OpenTeamsBoardDataset` (``openteams_project_1_board_raw``) —
  cursor-paginated GraphQL fetch of ``organization(login: "OpenTeams-WFT-CDO")
  { projectV2(number: 1) { items } }`` (mirrors the legacy
  ``fetch_project_issues``), credentialed (``github_token``); a
  partial-pagination failure keeps whatever pages already succeeded (mirrors
  :class:`~.upstream_discovery.TrendingSnapshotDataset`'s own per-period
  degrade — a genuine, if incomplete, result is persisted rather than
  discarded; only a fully-empty fetch triggers the inherited AD-13
  keep-last-good path).
- :class:`StagedRecipesPRDataset` (``discovery_staged_recipes_prs_raw``) — REST
  fetch of ``conda-forge/staged-recipes`` PRs (paginated, mirrors the legacy
  ``STAGED_PR_API``) plus a bounded per-open-PR ``files()`` fan-out (mirrors the
  legacy ``load_staged_prs``'s file-path ranking tier), credentialed
  (``github_token``).
- :class:`LocalRecipesOverlayDataset` (``discovery_local_recipes_raw``) — a
  plain, uncredentialed filesystem walk over ``${globals:paths.local_recipes_dir}``
  (no cadence/staleness — a local repo-tree walk is cheap and always current),
  combining the legacy ``load_local_recipes`` + ``load_local_build_status`` into
  one row-per-recipe-dir frame.

Every class NEVER raises on a fetch/parse failure — AD-13 last-good +
:class:`~.refresh.StalenessMarker` degrade for the three external-refresh
classes; :class:`LocalRecipesOverlayDataset` degrades to an empty frame on a
missing/unreadable ``recipes/`` directory.
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Callable

import pandas as pd
from kedro.io import AbstractDataset

from .refresh import (
    DEFAULT_REFRESH_MAX_RETRIES,
    DEFAULT_REFRESH_TIMEOUT_SECONDS,
    WEEKLY_SECONDS,
    ExternalRefreshDataset,
)
from .upstream_discovery import _as_text

logger = logging.getLogger(__name__)


def _join_list(values) -> str:
    """``; ``-join non-empty string values (mirrors the legacy script's
    ``join_list``)."""
    if not isinstance(values, (list, tuple)):
        return ""
    return "; ".join(str(v) for v in values if v)


# ---------------------------------------------------------------------------
# PurlAssociatorMappingsDataset (purl_associator_mappings_raw)
# ---------------------------------------------------------------------------

_PURL_ASSOC_COLUMNS: tuple[str, ...] = (
    "assoc_key",
    "purl",
    "type",
    "status",
    "alternative_purls",
    "cpes",
    "fetched_at",
)


def _alt_purls(rec: dict) -> list[str]:
    """Mirrors the legacy script's ``alt_purls``: each entry is either a bare
    PURL string or a ``{"purl": ...}`` dict. ``rec["alternative_purls"]`` must
    itself be a ``list`` — a malformed payload where it is instead a non-empty
    STRING would otherwise iterate its individual characters (each passing the
    ``isinstance(item, str) and item`` check) and fabricate garbage
    single-character purl entries (review finding, patch); degrades to ``[]``
    for any non-list value instead."""
    values = rec.get("alternative_purls")
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for item in values:
        if isinstance(item, str) and item:
            out.append(item)
        elif isinstance(item, dict) and item.get("purl"):
            out.append(item["purl"])
    return out


def parse_purl_associator_index(payload: Any) -> list[dict]:
    """PURE parser for the PURL Associator ``mappings-index.json`` payload
    (``{"packages": {<key>: {"purl":..., "type":..., "status":...,
    "alternative_purls": [...], "cpes": [...]}}}``) into one row per package.
    ``[]`` — NEVER raises — on a malformed/non-dict payload or a missing/non-dict
    ``packages`` key (a layout break degrades to zero rows, matching every other
    parser in this package). ``payload`` may be an already-parsed ``dict`` OR raw
    JSON text/bytes."""
    data = payload
    if isinstance(data, (str, bytes)):
        try:
            data = json.loads(data)
        except TypeError, ValueError:
            return []
    if not isinstance(data, dict):
        return []
    packages = data.get("packages")
    if not isinstance(packages, dict):
        return []
    fetched_at = int(time.time())
    rows: list[dict[str, Any]] = []
    for key, rec in packages.items():
        if not isinstance(key, str) or not isinstance(rec, dict):
            continue
        rows.append(
            {
                "assoc_key": key,
                "purl": rec.get("purl") or "",
                "type": rec.get("type") or "",
                "status": rec.get("status") or "",
                "alternative_purls": _join_list(_alt_purls(rec)),
                # rec["cpes"] must itself be a list — the same non-list-string
                # fabrication hazard _alt_purls guards against above (review
                # finding, patch): a malformed non-list value degrades to [].
                "cpes": _join_list(rec.get("cpes") if isinstance(rec.get("cpes"), list) else []),
                "fetched_at": fetched_at,
            }
        )
    return rows


class PurlAssociatorMappingsDataset(ExternalRefreshDataset):
    """The ``purl_associator_mappings_raw`` bootstrap index (identity-contract.md
    Source datasets: "Index required at bootstrap; shards fetched on demand").

    Mirrors :class:`~.upstream_discovery.AboutMaintainersDataset`'s shape exactly:
    a SINGLE injected-fetch live doc (an unauthenticated GitHub Pages JSON GET, no
    credential) parsed by :func:`parse_purl_associator_index`. On a fetch failure /
    layout break the INHERITED ``ExternalRefreshDataset.save()`` keep-last-good +
    mark-stale behavior applies unchanged (AD-13). ``fetcher=None`` == offline:
    construction is network-free; a DUE refresh keeps last-good + marks stale.
    """

    STORE_FILENAME = "purl_associator_mappings.parquet"
    _REQUIRED_COLUMNS = ("assoc_key", "fetched_at")

    def __init__(
        self,
        *,
        filepath: str,
        url: str,
        fetcher: Callable[[str], Any] | None = None,
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
        """Fetch + parse the index once. Never raises — a fetch failure WARNs and
        returns an empty frame (which ``save()`` turns into keep-last-good + mark
        stale)."""
        try:
            payload = self._fetcher(self._url)
        except Exception as exc:  # AD-13
            logger.warning("purl associator index fetch failed: %s", exc)
            return pd.DataFrame(columns=list(_PURL_ASSOC_COLUMNS))
        rows = parse_purl_associator_index(payload)
        if not rows:
            logger.warning("purl associator index parsed zero packages (layout break?) — keeping last-good")
        return pd.DataFrame(rows, columns=list(_PURL_ASSOC_COLUMNS))

    def fetch_shard(self, key: str, *, fetcher: Callable[[str], Any] | None = None) -> dict:
        """On-demand per-package shard fetch for ``alternative_purls``/``cpes``
        (identity-contract.md: "shards fetched on demand") — a forward-compatible
        enrichment seam for a future attended pass; the default
        ``build_identity_packages_primary`` join does NOT call this (it stays pure
        per AD-2 and consumes the inline index fields :meth:`_do_refresh` already
        persists). Never raises: a fetch/parse failure degrades to ``{}``."""
        active = fetcher if fetcher is not None else self._fetcher
        if active is None:
            return {}
        shard_url = f"{self._url.rsplit('/', 1)[0]}/packages/{key}.json"
        try:
            payload = active(shard_url)
        except Exception as exc:  # never raise: an enrichment seam degrades to {}.
            logger.warning("purl associator shard fetch failed for %s: %s", key, exc)
            return {}
        if isinstance(payload, (str, bytes)):
            try:
                payload = json.loads(payload)
            except TypeError, ValueError:
                return {}
        return payload if isinstance(payload, dict) else {}

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
            raise ValueError(f"purl associator refresh frame missing required columns: {missing}")
        self._atomic_write(self._store_path, lambda p: frame.to_parquet(p, index=False))

    def load(self) -> pd.DataFrame:
        if not self._store_exists():
            self._mark_stale(
                "purl associator mappings store absent (never refreshed / offline)",
                only_if_absent=True,
            )
            return pd.DataFrame(columns=list(_PURL_ASSOC_COLUMNS))
        try:
            return pd.read_parquet(self._store_path)
        except Exception as exc:
            logger.warning(
                "purl associator mappings store unreadable (%s), degrading to empty: %s",
                self._store_path,
                exc,
            )
            self._mark_stale("purl associator mappings store unreadable", only_if_absent=True)
            return pd.DataFrame(columns=list(_PURL_ASSOC_COLUMNS))

    def _describe(self) -> dict[str, Any]:
        base = super()._describe()
        base.update({"url": self._url})
        return base


# ---------------------------------------------------------------------------
# OpenTeamsBoardDataset (openteams_project_1_board_raw)
# ---------------------------------------------------------------------------

_BOARD_COLUMNS: tuple[str, ...] = ("number", "title", "url", "state", "milestone", "fetched_at")

# Hard safety cap against a lying/looping pageInfo.hasNextPage — mirrors the
# bounded-fan-out discipline every per-item loop in this package follows
# (e.g. PyPIJsonFanOutDataset's PYPI_JSON_FANOUT_LIMIT).
_OPENTEAMS_BOARD_MAX_PAGES = 500

# Mirrors the legacy script's fetch_project_issues query verbatim (org
# "OpenTeams-WFT-CDO", project number 1, page size 100).
OPENTEAMS_BOARD_QUERY = """
query($cursor: String) {
  organization(login: "OpenTeams-WFT-CDO") {
    projectV2(number: 1) {
      items(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          content {
            __typename
            ... on Issue {
              number
              title
              url
              state
              milestone { title }
            }
          }
        }
      }
    }
  }
}
"""


def _as_json(payload: Any) -> dict | None:
    if isinstance(payload, dict):
        return payload
    text = _as_text(payload)
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except TypeError, ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def parse_openteams_board_nodes(nodes: Any) -> list[dict]:
    """One row per GraphQL ``Issue``-typed project item
    (``content.__typename == "Issue"``); a non-Issue item (e.g. a draft item) is
    skipped. ``[]`` — never raises — on a non-list/malformed ``nodes``."""
    if not isinstance(nodes, list):
        return []
    fetched_at = int(time.time())
    rows: list[dict[str, Any]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        content = node.get("content")
        if not isinstance(content, dict) or content.get("__typename") != "Issue":
            continue
        milestone = content.get("milestone")
        rows.append(
            {
                "number": content.get("number"),
                "title": content.get("title") or "",
                "url": content.get("url") or "",
                "state": content.get("state") or "",
                "milestone": milestone.get("title") if isinstance(milestone, dict) else None,
                "fetched_at": fetched_at,
            }
        )
    return rows


class OpenTeamsBoardDataset(ExternalRefreshDataset):
    """The ``openteams_project_1_board_raw`` cursor-paginated GraphQL board fetch
    (identity-contract.md Source datasets; mirrors the legacy
    ``fetch_project_issues``). Credentialed: ``credentials: github_token`` (the
    ONE existing per-host GitHub credential, ``vcs_github_api_raw``'s own —
    Kedro resolves the catalog's ``credentials: github_token`` key into the
    ``credentials`` kwarg below at catalog-load time).

    ``fetcher`` is a **2-arg** ``Callable[[str, dict], Any]`` — ``(url,
    graphql_body) -> a parsed JSON dict or JSON text`` — deliberately NOT the
    1-arg ``Callable[[str], str]`` GET convention every other dataset in this
    package uses: a GraphQL POST needs a request body, and pagination needs
    multiple calls with a changing ``cursor`` variable.

    A mid-pagination fetch/parse failure keeps whatever pages already succeeded
    (mirrors :class:`~.upstream_discovery.TrendingSnapshotDataset`'s own
    per-period degrade: a genuine, if incomplete, result is persisted rather
    than discarded) — only a fully-empty combined result (zero pages ever
    succeeded) triggers the inherited AD-13 keep-last-good + mark-stale path via
    ``save()``'s existing empty-check.
    """

    STORE_FILENAME = "openteams_project_1_board.parquet"
    _REQUIRED_COLUMNS = ("number", "url", "fetched_at")

    def __init__(
        self,
        *,
        filepath: str,
        url: str,
        fetcher: Callable[[str, dict[str, Any]], Any] | None = None,
        credentials: dict[str, Any] | None = None,
        cadence_seconds: int | None = None,
        timeout_seconds: int = DEFAULT_REFRESH_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_REFRESH_MAX_RETRIES,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._url = str(url)
        self._fetcher = fetcher
        # Accepted so Kedro's `credentials: github_token` catalog key resolves
        # without raising; the real attended credentialed fetch is wired into
        # `fetcher` externally (mirrors GitHubRequestDataset's construction-is-
        # offline contract — no HTTP client is composed here).
        self._credentials = credentials
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
        rows: list[dict[str, Any]] = []
        cursor: str | None = None
        for _ in range(_OPENTEAMS_BOARD_MAX_PAGES):
            variables = {"cursor": cursor} if cursor else {}
            body = {"query": OPENTEAMS_BOARD_QUERY, "variables": variables}
            try:
                payload = self._fetcher(self._url, body)
            except Exception as exc:  # AD-13: keep whatever pages already succeeded.
                logger.warning(
                    "OpenTeams board GraphQL fetch failed (cursor=%r), keeping accumulated rows: %s",
                    cursor,
                    exc,
                )
                break
            parsed = _as_json(payload)
            if parsed is None:
                logger.warning(
                    "OpenTeams board GraphQL response unparseable (cursor=%r) — stopping pagination",
                    cursor,
                )
                break
            conn = (((parsed.get("data") or {}).get("organization") or {}).get("projectV2") or {}).get("items")
            if not isinstance(conn, dict):
                logger.warning(
                    "OpenTeams board GraphQL response missing items connection (cursor=%r) — stopping pagination",
                    cursor,
                )
                break
            rows.extend(parse_openteams_board_nodes(conn.get("nodes")))
            page_info = conn.get("pageInfo") or {}
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")
            if not cursor:
                break
        else:
            # The loop exhausted _OPENTEAMS_BOARD_MAX_PAGES without a natural
            # break (every page still reported hasNextPage) — the board is
            # larger than the hard safety cap; silently truncating would hide
            # real, missing rows (review finding, patch).
            logger.warning(
                "OpenTeams board pagination hit the %s-page safety cap — the board "
                "may have more pages than fetched; truncating",
                _OPENTEAMS_BOARD_MAX_PAGES,
            )
        return pd.DataFrame(rows, columns=list(_BOARD_COLUMNS))

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
            raise ValueError(f"OpenTeams board refresh frame missing required columns: {missing}")
        self._atomic_write(self._store_path, lambda p: frame.to_parquet(p, index=False))

    def load(self) -> pd.DataFrame:
        if not self._store_exists():
            self._mark_stale("OpenTeams board store absent (never refreshed / offline)", only_if_absent=True)
            return pd.DataFrame(columns=list(_BOARD_COLUMNS))
        try:
            return pd.read_parquet(self._store_path)
        except Exception as exc:
            logger.warning(
                "OpenTeams board store unreadable (%s), degrading to empty: %s",
                self._store_path,
                exc,
            )
            self._mark_stale("OpenTeams board store unreadable", only_if_absent=True)
            return pd.DataFrame(columns=list(_BOARD_COLUMNS))

    def _describe(self) -> dict[str, Any]:
        base = super()._describe()
        base.update({"url": self._url})
        return base


# ---------------------------------------------------------------------------
# StagedRecipesPRDataset (discovery_staged_recipes_prs_raw)
# ---------------------------------------------------------------------------

_STAGED_PR_COLUMNS: tuple[str, ...] = (
    "number",
    "state",
    "merged_at",
    "url",
    "title",
    "file_paths",
    "fetched_at",
)

# 200 pages * 100/page = 20,000 PRs — a realistic ceiling for staged-recipes'
# full PR history (mirrors the OpenTeams board's own hard pagination cap).
_STAGED_PR_MAX_PAGES = 200
# Bounded per-open-PR files() fan-out (mirrors PyPIJsonFanOutDataset's
# PYPI_JSON_FANOUT_LIMIT bounded-fetch discipline) — staged-recipes rarely has
# more than a few hundred open PRs at once.
_STAGED_PR_OPEN_FILES_FANOUT_LIMIT = 500


def parse_staged_pr_page(payload: Any) -> list[dict]:
    """One row per PR from a ``GET /repos/conda-forge/staged-recipes/pulls?state=all``
    page (``[{number, state, merged_at, html_url, title}, ...]``). ``[]`` — never
    raises — on a non-list/malformed payload."""
    data = payload
    if isinstance(data, (str, bytes)):
        try:
            data = json.loads(data)
        except TypeError, ValueError:
            return []
    if not isinstance(data, list):
        return []
    fetched_at = int(time.time())
    rows: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        number = item.get("number")
        if number is None:
            continue
        rows.append(
            {
                "number": number,
                "state": item.get("state") or "",
                "merged_at": item.get("merged_at"),
                "url": item.get("html_url") or item.get("url") or "",
                "title": item.get("title") or "",
                "file_paths": "",
                "fetched_at": fetched_at,
            }
        )
    return rows


def parse_pr_files_response(payload: Any) -> list[str]:
    """File paths from a ``GET /pulls/{number}/files`` page
    (``[{"filename": ...}, ...]``). ``[]`` — never raises."""
    data = payload
    if isinstance(data, (str, bytes)):
        try:
            data = json.loads(data)
        except TypeError, ValueError:
            return []
    if not isinstance(data, list):
        return []
    return [item["filename"] for item in data if isinstance(item, dict) and isinstance(item.get("filename"), str)]


class StagedRecipesPRDataset(ExternalRefreshDataset):
    """The ``discovery_staged_recipes_prs_raw`` REST source (identity-contract.md
    Source datasets; mirrors the legacy ``load_staged_prs``). Credentialed:
    ``credentials: github_token`` (same host/key as ``vcs_github_api_raw`` /
    ``openteams_project_1_board_raw`` — no second GitHub credential key).

    ``fetcher`` is the standard 1-arg ``Callable[[str], Any]`` GET convention
    (a full URL in, a parsed JSON list or JSON text out). :meth:`_do_refresh`
    paginates ``GET /repos/conda-forge/staged-recipes/pulls?state=all`` (mirrors
    the legacy ``STAGED_PR_API``), then does a BOUNDED per-open-PR
    ``GET /pulls/{number}/files`` fan-out (mirrors the legacy
    ``load_staged_prs``'s file-path ranking tier, restricted to open PRs only —
    the same scope the legacy script's own ``gh pr list --state open --json
    ...,files`` call covered). A per-page or per-PR fetch/parse failure keeps
    whatever was already accumulated for that call, never aborting the whole
    refresh (AD-13).
    """

    STORE_FILENAME = "discovery_staged_recipes_prs.parquet"
    _REQUIRED_COLUMNS = ("number", "state", "url", "fetched_at")

    def __init__(
        self,
        *,
        filepath: str,
        url: str,
        fetcher: Callable[[str], Any] | None = None,
        credentials: dict[str, Any] | None = None,
        cadence_seconds: int | None = None,
        timeout_seconds: int = DEFAULT_REFRESH_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_REFRESH_MAX_RETRIES,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._url = str(url)
        self._fetcher = fetcher
        self._credentials = credentials
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
        rows: list[dict[str, Any]] = []
        base = self._url.rstrip("/")
        for page in range(1, _STAGED_PR_MAX_PAGES + 1):
            page_url = f"{base}/repos/conda-forge/staged-recipes/pulls?state=all&per_page=100&page={page}"
            try:
                payload = self._fetcher(page_url)
            except Exception as exc:  # AD-13: keep whatever pages already succeeded.
                logger.warning(
                    "staged-recipes PR list fetch failed at page=%s, keeping accumulated rows: %s",
                    page,
                    exc,
                )
                break
            page_rows = parse_staged_pr_page(payload)
            if not page_rows:
                break
            rows.extend(page_rows)
            if len(page_rows) < 100:
                break
        else:
            # The loop exhausted _STAGED_PR_MAX_PAGES without a natural break
            # (every page was a full 100-row page) — staged-recipes has more PRs
            # than the hard safety cap; silently truncating would hide real,
            # missing rows (review finding, patch).
            logger.warning(
                "staged-recipes PR pagination hit the %s-page safety cap — there "
                "may be more PRs than fetched; truncating",
                _STAGED_PR_MAX_PAGES,
            )

        # Bounded per-open-PR files() fan-out — never raises: a per-PR failure
        # degrades that PR's file_paths to empty, never drops the PR row.
        open_numbers = [r["number"] for r in rows if r.get("state") == "open"]
        if len(open_numbers) > _STAGED_PR_OPEN_FILES_FANOUT_LIMIT:
            logger.warning(
                "staged-recipes open-PR files() fan-out hit the %s-PR cap (%s open "
                "PRs found) — the file-path ranking tier is skipped for the rest",
                _STAGED_PR_OPEN_FILES_FANOUT_LIMIT,
                len(open_numbers),
            )
        for number in open_numbers[:_STAGED_PR_OPEN_FILES_FANOUT_LIMIT]:
            files_url = f"{base}/repos/conda-forge/staged-recipes/pulls/{number}/files?per_page=100"
            try:
                payload = self._fetcher(files_url)
            except Exception as exc:
                logger.warning("staged-recipes PR #%s files fetch failed: %s", number, exc)
                continue
            paths = parse_pr_files_response(payload)
            if paths:
                file_paths = _join_list(paths)
                for row in rows:
                    if row["number"] == number:
                        row["file_paths"] = file_paths
        return pd.DataFrame(rows, columns=list(_STAGED_PR_COLUMNS))

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
            raise ValueError(f"staged-recipes PR refresh frame missing required columns: {missing}")
        self._atomic_write(self._store_path, lambda p: frame.to_parquet(p, index=False))

    def load(self) -> pd.DataFrame:
        if not self._store_exists():
            self._mark_stale("staged-recipes PR store absent (never refreshed / offline)", only_if_absent=True)
            return pd.DataFrame(columns=list(_STAGED_PR_COLUMNS))
        try:
            return pd.read_parquet(self._store_path)
        except Exception as exc:
            logger.warning(
                "staged-recipes PR store unreadable (%s), degrading to empty: %s",
                self._store_path,
                exc,
            )
            self._mark_stale("staged-recipes PR store unreadable", only_if_absent=True)
            return pd.DataFrame(columns=list(_STAGED_PR_COLUMNS))

    def _describe(self) -> dict[str, Any]:
        base = super()._describe()
        base.update({"url": self._url})
        return base


# ---------------------------------------------------------------------------
# LocalRecipesOverlayDataset (discovery_local_recipes_raw)
# ---------------------------------------------------------------------------

_LOCAL_RECIPES_COLUMNS: tuple[str, ...] = ("dir_name", "names", "url", "build_status")

# Hardcoded to THIS repo's own local-recipes tree (mirrors the legacy script's
# own LOCAL_RECIPES_URL / ISSUE_CREATE_REPO / PROJECT_OWNER constants, all of
# which are similarly this-repo-specific — this story ports the legacy
# semantics exactly, not a generalized multi-repo overlay).
_LOCAL_RECIPES_TREE_URL_TEMPLATE = "https://github.com/rxm7706/local-recipes/tree/main/recipes/{dir}"

# Mirrors the legacy script's CFE_BUILD_STATUS_RE / RECIPE_NAME_RE / TITLE_STOP
# verbatim.
_CFE_BUILD_STATUS_RE = re.compile(r"(?m)^  cfe-local-build-status:\s*(\S+)")
_RECIPE_NAME_RE = re.compile(
    r"(?m)^(?:package:\s*\n(?:[ \t].*\n)*?[ \t]+name:\s*|"
    r"[ \t]+- name:\s*|"
    r"[ \t]+name:\s*)[\"']?([A-Za-z0-9][A-Za-z0-9._+-]*)"
)
_TITLE_STOP = {
    "recipe",
    "recipes",
    "package",
    "packages",
    "python",
    "conda",
    "forge",
    "meta",
    "yaml",
    "example",
    "new",
    "the",
    "a",
    "an",
    "for",
    "and",
    "with",
    "using",
    "from",
    "initial",
    "commit",
    "support",
    "fix",
    "update",
    "bump",
    "r",
}


def _pep503(value: Any) -> str | None:
    """Mirrors the legacy script's ``pep503_name`` (incl. the trailing
    ``.strip("-")``)."""
    if not isinstance(value, str):
        return None
    v = re.sub(r"[-_.]+", "-", value.strip().lower()).strip("-")
    return v or None


def parse_recipe_dir(dir_name: str, files: dict[str, str]) -> dict:
    """PURE parser: given a recipe dir's name + its ``{filename: text}`` contents
    (``recipe.yaml``/``meta.yaml``), returns the one-row dict ``{dir_name, names,
    url, build_status}`` — ``names`` is the ``; ``-joined set of PEP-503 aliases
    (the dir name itself + every name parsed out of the recipe files);
    ``build_status`` is the CFE ``cfe-local-build-status`` stamp from
    ``recipe.yaml`` only (blank if absent). NEVER raises."""
    names: set[str] = set()
    dir_key = _pep503(dir_name)
    if dir_key:
        names.add(dir_key)
    for fname in ("recipe.yaml", "meta.yaml"):
        text = files.get(fname)
        if not text:
            continue
        for m in _RECIPE_NAME_RE.finditer(text):
            token = _pep503(m.group(1))
            if token and token not in _TITLE_STOP:
                names.add(token)
    build_status = ""
    recipe_text = files.get("recipe.yaml") or ""
    m = _CFE_BUILD_STATUS_RE.search(recipe_text)
    if m:
        build_status = m.group(1).strip().strip("'\"")
    return {
        "dir_name": dir_name,
        "names": _join_list(sorted(names)),
        "url": _LOCAL_RECIPES_TREE_URL_TEMPLATE.format(dir=dir_name),
        "build_status": build_status,
    }


class LocalRecipesOverlayDataset(AbstractDataset):
    """The ``discovery_local_recipes_raw`` live ``recipes/`` filesystem scan
    (identity-contract.md Source datasets: "Local recipes overlay ... none
    (repo-local)"). No cadence/staleness — a local repo-tree walk is cheap and
    always current, mirroring
    :class:`~.upstream_discovery.TrackedSeedDataset`'s no-trigger-node shape.
    Read-only: ``save()`` raises ``NotImplementedError`` like every other
    read-only source in this package.
    """

    def __init__(self, *, filepath: str, metadata: dict[str, Any] | None = None) -> None:
        # No **kwargs sink: an unrecognized catalog key must raise loudly.
        self._filepath = str(filepath)
        self.metadata = metadata

    def load(self) -> pd.DataFrame:
        recipes_dir = Path(self._filepath)
        try:
            if not recipes_dir.is_dir():
                return pd.DataFrame(columns=list(_LOCAL_RECIPES_COLUMNS))
            dirs = sorted(p for p in recipes_dir.iterdir() if p.is_dir() and not p.name.startswith("."))
        except OSError as exc:  # never raise: a permission-denied/exotic fs error
            # degrades to empty exactly like a missing directory (AD-13-style).
            logger.warning(
                "local recipes directory walk failed (%s), degrading to empty: %s",
                recipes_dir,
                exc,
            )
            return pd.DataFrame(columns=list(_LOCAL_RECIPES_COLUMNS))
        rows: list[dict[str, Any]] = []
        for d in dirs:
            files: dict[str, str] = {}
            for fname in ("recipe.yaml", "meta.yaml"):
                fpath = d / fname
                try:
                    if not fpath.is_file():
                        continue
                    files[fname] = fpath.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
            rows.append(parse_recipe_dir(d.name, files))
        return pd.DataFrame(rows, columns=list(_LOCAL_RECIPES_COLUMNS))

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is read-only (live recipes/ filesystem scan)")

    def _describe(self) -> dict[str, Any]:
        return {"filepath": self._filepath}
