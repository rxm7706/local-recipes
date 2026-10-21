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
  ``fetch_project_issues``), credentialed (``github_token``, Story 36.2). A
  pagination a failure stops part-way never hides (:class:`_HonestPagination`):
  with a store it keeps last-good; with none it writes the pages read; either
  way the marker names the page and the status, and the next run tries again.
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
import os
import re
import time
from pathlib import Path
from typing import Any, Callable

import pandas as pd
from kedro.io import AbstractDataset
from kedro_datasets.api import APIDataset
from pyforge.core.flags import read_boolean

from . import credentials as credential_switch
from . import public_sources
from .refresh import (
    DEFAULT_REFRESH_MAX_RETRIES,
    DEFAULT_REFRESH_TIMEOUT_SECONDS,
    WEEKLY_SECONDS,
    ExternalRefreshDataset,
    retry_backoff_seconds,
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

    def _refresh_with(self, fetch: Callable[..., Any]) -> pd.DataFrame:
        """Fetch + parse the index once. Never raises — a fetch failure WARNs and
        returns an empty frame (which ``save()`` turns into keep-last-good + mark
        stale)."""
        try:
            payload = fetch(self._url)
        except Exception as exc:  # AD-13
            logger.warning("purl associator index fetch failed: %s", exc)
            return pd.DataFrame(columns=list(_PURL_ASSOC_COLUMNS))
        rows = parse_purl_associator_index(payload)
        if not rows:
            logger.warning("purl associator index parsed zero packages (layout break?) — keeping last-good")
        return pd.DataFrame(rows, columns=list(_PURL_ASSOC_COLUMNS))

    def _do_refresh(self) -> pd.DataFrame:
        assert self._fetcher is not None
        return self._refresh_with(self._fetcher)

    def _live_refresher(self) -> Callable[[], pd.DataFrame] | None:
        # Story 34.6: the store's own public page(s), unauthenticated, when live public sources are
        # on -- read at each refresh, never at construction (a Dagster code location constructs at import)
        return self._refresh_public if public_sources.live() else None

    def _refresh_public(self) -> pd.DataFrame:
        return self._refresh_with(public_sources.fetch_text)

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


#: Story 36.2: the flag that lets the board and the staged-recipes PRs fetch themselves
IDENTITY_FLAG_KEY = "pyforge.atlas.identity_live_sources"
_GITHUB_TIMEOUT_SECONDS = 60


def identity_live() -> bool:
    """Whether the OpenTeams board and the staged-recipes PRs fetch (read at the refresh)."""
    return read_boolean(IDENTITY_FLAG_KEY, default=False)


def _github_graphql(url: str, body: dict[str, Any], auth: credential_switch.BearerAuth) -> Any:
    """Story 36.2: one GraphQL POST with bearer auth, through ``APIDataset.save`` (``load()`` sends
    only GET) and an in-memory ``response_dataset`` (Story 35.1's route)."""
    inner = APIDataset(
        url=url,
        method="POST",
        save_args={"timeout": _GITHUB_TIMEOUT_SECONDS},
        credentials=auth,  # type: ignore[arg-type, unused-ignore]  # a callable auth; requests accepts it
        response_dataset={"type": "kedro.io.MemoryDataset", "copy_mode": "assign"},
    )
    inner.save(body)
    response = inner.get_last_response()
    return response.json() if hasattr(response, "json") else response


def _github_get(url: str, auth: credential_switch.BearerAuth) -> Any:
    """Story 36.2: one REST GET with bearer auth."""
    response = APIDataset(url=url, load_args={"timeout": _GITHUB_TIMEOUT_SECONDS, "auth": auth}).load()
    return response.json() if hasattr(response, "json") else response


def _credentialed_refresher(
    credentials: Any, url: str, refresh: Callable[[credential_switch.BearerAuth], pd.DataFrame]
) -> Callable[[], pd.DataFrame] | None:
    """Story 36.2: with ``pyforge.atlas.identity_live_sources`` on, a refresher that runs only
    with Story 35.1's switch and a GitHub token (``github_auth``); without them it fails with the
    reason, so the store keeps last-good under a marker that names it and nothing is sent."""
    if not identity_live():
        return None
    auth = credential_switch.github_auth(credentials, url)
    if auth is None:
        reason = credential_switch.skip_reason(url)

        def refuse() -> pd.DataFrame:
            raise RuntimeError(reason)

        return refuse
    return lambda: refresh(auth)


#: Story 36.2: GitHub's refusals (Story 35.1's stop statuses): the run stops sending at the first
_STOP_STATUSES = (401, 403, 429)
#: a page GitHub could not answer in time is asked again, ``max_retries`` times
_RETRY_STATUSES = (502, 503, 504)


def _status_of(exc: BaseException) -> int | None:
    """The HTTP status inside kedro's ``DatasetError(..., HTTPError)``, if any."""
    for arg in (exc, *getattr(exc, "args", ())):
        status = getattr(getattr(arg, "response", None), "status_code", None)
        if isinstance(status, int):
            return status
    return None


def _why(exc: BaseException) -> str:
    """A fetch failure as its status, else its type: never its text, which on the credentialed
    path can quote the request (Story 35.1)."""
    status = _status_of(exc)
    return f"HTTP {status}" if status else type(exc).__name__


#: the reasons :class:`_HonestPagination` writes when a refresh stops short
_STOP_MARKER_PREFIXES = ("board stopped", "PR list stopped", "PR files stopped")


class _HonestPagination:
    """Story 36.2 (AD-13): a pagination a failure stops part-way. With a store already written,
    the refresh fails and last-good is kept; with none, the pages read are written. Either way the
    marker names where and why it stopped, and a page GitHub could not answer in time is asked
    again first. A mixin ahead of :class:`ExternalRefreshDataset`."""

    _stopped = ""

    def _stop(self, reason: str) -> None:
        """Record why the refresh stopped short; a second reason is added, never replaces."""
        self._stopped = f"{self._stopped}; {reason}" if self._stopped else reason

    def _refresh_due(self, cadence_seconds: int, now: float | None = None) -> bool:
        """A store whose last refresh stopped short (its marker still stands) is due now: inside
        its cadence it would otherwise read as fresh and the marker be cleared."""
        marker = self.staleness()  # type: ignore[attr-defined]
        if marker is not None and marker.stale and marker.reason.startswith(_STOP_MARKER_PREFIXES):
            return True  # only this mixin's own stop markers: a flag-off or offline marker behaves as before
        return super()._refresh_due(cadence_seconds, now)  # type: ignore[misc, unused-ignore]

    def _fetch_page(self, fetch: Callable[..., Any], *args: Any) -> Any:
        for attempt in range(1, self._max_retries + 2):  # type: ignore[attr-defined]
            try:
                return fetch(*args)
            except Exception as exc:
                if attempt > self._max_retries or _status_of(exc) not in _RETRY_STATUSES:  # type: ignore[attr-defined]
                    raise
                time.sleep(retry_backoff_seconds(attempt))
        raise AssertionError("unreachable")  # pragma: no cover

    def _stopped_at(self, reason: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._stop(reason)
        logger.warning("%s: %s", type(self).__name__, reason)
        if not rows or self._store_exists():  # type: ignore[attr-defined]
            raise RuntimeError(reason)
        return rows

    def save(self, data: Any) -> None:
        self._stopped = ""
        prior = self.staleness()  # type: ignore[attr-defined]
        prior_stop = (
            prior.reason.split(" (since then: ", 1)[0]
            if prior is not None and prior.stale and prior.reason.startswith(_STOP_MARKER_PREFIXES)
            else ""
        )
        super().save(data)  # type: ignore[misc, unused-ignore]
        # The base clears its marker exactly when it writes the store. A prior stop makes the refresh
        # due (`_refresh_due`), so the base never takes its not-due path, which also clears it.
        now = self.staleness()  # type: ignore[attr-defined]
        if prior_stop and now is not None:
            # Story 36.2: a run that wrote nothing (no switch, the flag off, a failed write) never
            # clears a stop: the store is still the short one, so the stop stays first in the
            # marker. A new stop names where this run stopped; a notice or the base's reason
            # follows the stop it did not lift.
            later = self._stopped or (now.reason if now.stale else "")
            if later.startswith(prior_stop):
                later = ""
            if later.startswith(_STOP_MARKER_PREFIXES):
                self._mark_stale(later)  # type: ignore[attr-defined]
            else:
                self._mark_stale(f"{prior_stop} (since then: {later})" if later else prior_stop)  # type: ignore[attr-defined]
            return
        if self._stopped:
            self._mark_stale(self._stopped)  # type: ignore[attr-defined]


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


class OpenTeamsBoardDataset(_HonestPagination, ExternalRefreshDataset):
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

    A pagination a failure stops part-way is :class:`_HonestPagination`'s (Story 36.2): a
    fuller last-good is kept, else the pages read are written; the marker names the page and
    the status, and the next run tries again.
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
        # Kedro resolves the catalog's `credentials: github_token` into this; Story 36.2's live
        # refresher sends it as a bearer, only under the switch. Construction stays offline.
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

    def _live_refresher(self) -> Callable[[], pd.DataFrame] | None:
        # Story 36.2: the board needs a GitHub token (GraphQL is authenticated-only)
        return _credentialed_refresher(
            self._credentials,
            self._url,
            lambda auth: self._do_refresh(fetcher=lambda url, body: _github_graphql(url, body, auth)),
        )

    def _do_refresh(self, fetcher: Callable[[str, dict[str, Any]], Any] | None = None) -> pd.DataFrame:
        fetch = fetcher if fetcher is not None else self._fetcher
        if fetch is None:
            raise RuntimeError("no OpenTeams board fetcher")
        rows: list[dict[str, Any]] = []
        cursor: str | None = None
        for page in range(1, _OPENTEAMS_BOARD_MAX_PAGES + 1):
            variables = {"cursor": cursor} if cursor else {}
            body = {"query": OPENTEAMS_BOARD_QUERY, "variables": variables}
            try:
                payload = self._fetch_page(fetch, self._url, body)
            except Exception as exc:  # AD-13: _HonestPagination keeps last-good or the pages read
                return pd.DataFrame(
                    self._stopped_at(f"board stopped at page {page}: {_why(exc)}", rows), columns=list(_BOARD_COLUMNS)
                )
            parsed = _as_json(payload)
            if parsed is None:
                return pd.DataFrame(
                    self._stopped_at(f"board stopped at page {page}: unparseable response", rows),
                    columns=list(_BOARD_COLUMNS),
                )
            conn = (((parsed.get("data") or {}).get("organization") or {}).get("projectV2") or {}).get("items")
            if not isinstance(conn, dict):
                errors = parsed.get("errors")
                first = (
                    errors[0].get("message")
                    if isinstance(errors, list) and errors and isinstance(errors[0], dict)
                    else None
                )
                return pd.DataFrame(
                    self._stopped_at(f"board stopped at page {page}: GraphQL error: {first or 'no items'}", rows),
                    columns=list(_BOARD_COLUMNS),
                )
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

# 500 pages * 100/page = 50,000 PRs. Story 36.2: the 200-page cap of Story 21.x stopped at PR
# #14,827 when staged-recipes held about 35,000 (2026-10-18); 500 pages read the whole history.
_STAGED_PR_MAX_PAGES = 500
# Bounded per-open-PR files() fan-out (mirrors PyPIJsonFanOutDataset's
# PYPI_JSON_FANOUT_LIMIT bounded-fetch discipline). Story 36.2: staged-recipes had 1,222 open PRs
# on 2026-10-18, so the 500 cap of Story 21.x skipped 722; with the PR pages, about 1,600
# authenticated requests, well inside GitHub's 5,000 an hour.
_STAGED_PR_OPEN_FILES_FANOUT_LIMIT = 2000
# Story 36.2: the files requests stop after this many PRs in a row fail (a lasting 5xx would
# otherwise send up to four requests for each of 2,000 PRs)
_FILES_FAILURES_IN_A_ROW_LIMIT = 10


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


class StagedRecipesPRDataset(_HonestPagination, ExternalRefreshDataset):
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
    ...,files`` call covered). A list stopped part-way is :class:`_HonestPagination`'s
    (Story 36.2); a PR whose files are not read keeps its last-good file paths, and a refusal
    stops every later request.
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

    def _live_refresher(self) -> Callable[[], pd.DataFrame] | None:
        # Story 36.2: some 300 pages of PRs exceed GitHub's 60 unauthenticated requests an hour
        return _credentialed_refresher(
            self._credentials, self._url, lambda auth: self._do_refresh(fetcher=lambda url: _github_get(url, auth))
        )

    def _do_refresh(self, fetcher: Callable[[str], Any] | None = None) -> pd.DataFrame:
        fetch = fetcher if fetcher is not None else self._fetcher
        if fetch is None:
            raise RuntimeError("no staged-recipes fetcher")
        rows: list[dict[str, Any]] = []
        list_refused = False
        base = self._url.rstrip("/")
        for page in range(1, _STAGED_PR_MAX_PAGES + 1):
            page_url = f"{base}/repos/conda-forge/staged-recipes/pulls?state=all&per_page=100&page={page}"
            try:
                payload = self._fetch_page(fetch, page_url)
            except Exception as exc:  # AD-13: _HonestPagination keeps last-good or the pages read
                list_refused = _status_of(exc) in _STOP_STATUSES
                rows = self._stopped_at(f"PR list stopped at page {page}: {_why(exc)}", rows)
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

        # Bounded per-open-PR files() fan-out — never raises: a PR whose files are not read keeps
        # its last-good file paths (Story 36.2), and its row is never dropped.
        open_numbers = [r["number"] for r in rows if r.get("state") == "open"]
        if len(open_numbers) > _STAGED_PR_OPEN_FILES_FANOUT_LIMIT:
            logger.warning(
                "staged-recipes open-PR files() fan-out hit the %s-PR cap (%s open "
                "PRs found) — the file-path ranking tier is skipped for the rest",
                _STAGED_PR_OPEN_FILES_FANOUT_LIMIT,
                len(open_numbers),
            )
        # Story 36.2: a PR whose files are not read keeps its last-good file paths
        last_paths = self._last_good_file_paths()
        refused = list_refused  # a refusal on the list stops the files requests too
        failures_in_a_row = files_failed = 0
        for number in open_numbers[:_STAGED_PR_OPEN_FILES_FANOUT_LIMIT]:
            if refused:
                break
            paths: list[str] = []
            read = True
            page = 1
            while True:
                files_url = f"{base}/repos/conda-forge/staged-recipes/pulls/{number}/files?per_page=100&page={page}"
                try:
                    payload = self._fetch_page(fetch, files_url)
                except Exception as exc:
                    read = False
                    if _status_of(exc) in _STOP_STATUSES:
                        # Story 36.2: a refusal stops every later request (Story 35.1); the marker says so
                        self._stop(f"PR files stopped at PR #{number}: {_why(exc)}")
                        refused = True
                    else:
                        logger.warning("staged-recipes PR #%s files fetch failed: %s", number, _why(exc))
                    break
                batch = parse_pr_files_response(payload)
                if not batch:
                    break
                paths.extend(batch)
                if len(batch) < 100:
                    break
                page += 1
            failures_in_a_row = 0 if read else failures_in_a_row + 1
            files_failed += 0 if read else 1
            if failures_in_a_row >= _FILES_FAILURES_IN_A_ROW_LIMIT and not refused:
                # the breaker fires at the failure that reaches the limit, the last PR's included
                self._stop(f"PR files stopped after PR #{number}: {failures_in_a_row} failures in a row")
                refused = True
            if paths:
                file_paths = _join_list(paths)
                for row in rows:
                    if row["number"] == number:
                        row["file_paths"] = file_paths
        if files_failed and not refused:
            # a one-run notice (not a stop marker): the next refresh inside the cadence clears it
            noun = "PR" if files_failed == 1 else "PRs"
            self._stop(f"PR files failed for {files_failed} {noun} (each keeps its last-good paths, if any)")
        for row in rows:  # every open PR whose files were not read: its last-good paths
            if row.get("state") == "open" and not row.get("file_paths") and last_paths.get(row["number"]):
                row["file_paths"] = last_paths[row["number"]]
        return pd.DataFrame(rows, columns=list(_STAGED_PR_COLUMNS))

    def _last_good_file_paths(self) -> dict[Any, str]:
        """The last-good store's non-empty ``file_paths`` by PR number (``{}`` with no store)."""
        if not self._store_exists():
            return {}
        try:
            frame = pd.read_parquet(self._store_path, columns=["number", "file_paths"])
        except Exception:  # noqa: BLE001 -- an unreadable last-good carries nothing forward
            return {}
        return {n: p for n, p in zip(frame["number"], frame["file_paths"], strict=True) if isinstance(p, str) and p}

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
def _local_recipes_tree_url_template() -> str:
    slug = os.environ.get("PYFORGE_ATLAS_LOCAL_RECIPES_REPO_SLUG", "rxm7706/local-recipes")
    return f"https://github.com/{slug}/tree/main/recipes/{{dir}}"


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
        "url": _local_recipes_tree_url_template().format(dir=dir_name),
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
