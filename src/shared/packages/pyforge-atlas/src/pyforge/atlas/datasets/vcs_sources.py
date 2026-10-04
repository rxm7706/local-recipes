"""VCS + registry raw-source datasets (Story 21.2 — cf_atlas.db seed removal).

Two catalog families own the Phase K/L live-fetch shape (mechanically repeated, not
10 bespoke designs — GET the wired base URL + a per-package identifier, extract one
version string, wrap in the AD-13 last-good + staleness pattern):

- :class:`VcsHostSeedDataset` — GitLab / Codeberg (``vcs_gitlab_api_raw`` /
  ``vcs_codeberg_api_raw``): latest tag per repository.
- :class:`RegistryUpstreamDataset` — the 8 cross-ecosystem registries
  (``vcs_registry_*_raw``): latest version per package.

Both subclass :class:`_ParquetRefreshStore` (the shared last-good Parquet +
staleness-marker persistence this module hoists out of the two near-identical
implementations, review finding) and compose ``kedro_datasets.api.APIDataset`` for
the physical HTTP fetch (dataset-owned IO, AD-2 — no ``requests``/``sqlite3`` import
here; ``tests/catalog/test_no_inline_io.py`` bans both across the package).

Neither class fetches on a bare Kedro ``load()`` — ``load()`` is a read-only
projection of the persisted store. The live fetch is driven by ``save()``, which
ONLY accepts a :class:`~pyforge.atlas.datasets.refresh.RefreshRequest` trigger
(mirrors ``ExternalRefreshDataset``'s cadence/force honoring) — the pipeline's
refresh-trigger nodes (``pipelines/vcs_health/pipeline.py``) are each entry's SINGLE
writer, mirroring ``refresh_vdb_store``/``refresh_osv_offline_store``. A batch where
every identifier's fetch fails (or the batch is empty — Story 21.2 does not yet wire a
production identifier source; see the module Design Note below) degrades to "no data"
for persistence purposes: last-good is preserved and staleness is marked, never
clobbered with an all-null result.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import pandas as pd
from kedro.io import AbstractDataset
from kedro_datasets.api import APIDataset

from .rate_limit import DEFAULT_RPS, RateLimitedScheduler
from .refresh import (
    DEFAULT_REFRESH_MAX_RETRIES,
    DEFAULT_REFRESH_TIMEOUT_SECONDS,
    RefreshRequest,
    _ParquetRefreshStore,
    fetch_one_with_retry,
)

logger = logging.getLogger(__name__)

_VERSION_SEGMENT_RE = re.compile(r"\d+|\D+")


def _version_sort_key(version: str) -> tuple:
    """Natural / numeric-aware sort key: splits a version string into alternating
    digit/non-digit runs so a multi-digit numeric segment compares NUMERICALLY
    (e.g. ``"1.10-1"`` > ``"1.2-1"``) rather than lexicographically, where "1.10-1"
    would sort BELOW "1.2-1" as raw strings (review fix #1 — a plain ``sorted()`` on
    the version strings mis-ranks multi-digit components)."""
    return tuple((0, int(part)) if part.isdigit() else (1, part) for part in _VERSION_SEGMENT_RE.findall(version))


# Shared row shape for BOTH VcsHostSeedDataset and RegistryUpstreamDataset — the
# review finding added ``last_error`` to the registry side to match the host side.
_VERSION_COLUMNS: tuple[str, ...] = ("conda_name", "upstream_version", "last_error")


def _coerce_json(raw: Any) -> Any:
    """Normalize an ``APIDataset.load()`` return value to parsed JSON (dict OR list —
    the GitLab/Codeberg tag endpoints return a JSON list, unlike the dict-shaped
    registry payloads)."""
    if hasattr(raw, "json") and callable(raw.json):
        try:
            return raw.json()
        except ValueError, TypeError:
            return None
    if isinstance(raw, (dict, list)):
        return raw
    if isinstance(raw, (bytes, str)):
        try:
            return json.loads(raw)
        except json.JSONDecodeError, TypeError, UnicodeDecodeError:
            return None
    return None


# ---------------------------------------------------------------------------
# Per-host / per-registry request-path builders + response extractors.
# Percent-encode every interpolated identifier (urllib.parse.quote) — a package name
# or repo slug may legitimately contain '/', '@', or other path-special characters.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _EndpointSpec:
    build_path: Callable[[str, str], str]
    extract: Callable[[Any], str | None]


def _require_identifier(kind: str, identifier: str) -> str:
    ident = (identifier or "").strip("/")
    if not ident:
        raise ValueError(f"{kind} request path requires a non-empty identifier")
    return ident


def _first_list_item_field(payload: Any, field: str) -> str | None:
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        value = payload[0].get(field)
        return str(value) if value else None
    return None


def _gitlab_path(base: str, identifier: str) -> str:
    ident = _require_identifier("gitlab", identifier)
    return f"{base.rstrip('/')}/projects/{quote(ident, safe='')}/repository/tags?order_by=updated&per_page=1"


def _codeberg_path(base: str, identifier: str) -> str:
    ident = _require_identifier("codeberg", identifier)
    # Exactly one '/' — an identifier like "owner/repo/sub" would otherwise silently
    # percent-encode the extra segment into the `repo` slot, building a malformed
    # request path (review fix #11).
    parts = ident.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(
            f"codeberg request path requires a clean 'owner/repo' identifier (exactly one '/'), got {identifier!r}"
        )
    owner, repo = parts
    return f"{base.rstrip('/')}/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/tags?sort=updated&limit=1"


_HOST_SPECS: dict[str, _EndpointSpec] = {
    "gitlab": _EndpointSpec(_gitlab_path, lambda p: _first_list_item_field(p, "name")),
    "codeberg": _EndpointSpec(_codeberg_path, lambda p: _first_list_item_field(p, "name")),
}


def _npm_path(base: str, name: str) -> str:
    ident = _require_identifier("npm", name)
    return f"{base.rstrip('/')}/{quote(ident, safe='@')}"


def _npm_extract(payload: Any) -> str | None:
    if isinstance(payload, dict):
        tags = payload.get("dist-tags")
        if isinstance(tags, dict):
            v = tags.get("latest")
            return str(v) if v else None
    return None


def _cran_path(base: str, name: str) -> str:
    ident = _require_identifier("cran", name)
    return f"{base.rstrip('/')}/{quote(ident, safe='')}"


def _cran_extract(payload: Any) -> str | None:
    if isinstance(payload, dict):
        v = payload.get("Version")
        return str(v) if v else None
    return None


def _cpan_path(base: str, name: str) -> str:
    ident = _require_identifier("cpan", name)
    return f"{base.rstrip('/')}/v1/release/{quote(ident, safe='')}"


def _cpan_extract(payload: Any) -> str | None:
    if isinstance(payload, dict):
        v = payload.get("version")
        return str(v) if v else None
    return None


def _luarocks_path(base: str, name: str) -> str:
    ident = _require_identifier("luarocks", name)
    return f"{base.rstrip('/')}/m/{quote(ident, safe='')}.json"


def _luarocks_extract(payload: Any) -> str | None:
    """LuaRocks' per-module JSON is keyed by version string (``{"versions": {...}}``);
    dict iteration order is not the release order, so pick the genuinely latest version
    via a NUMERIC-AWARE comparator (never ``next(iter(versions))`` on unordered dict
    iteration, and never a raw lexicographic ``sorted()`` — review fix #1: a plain
    string sort mis-ranks multi-digit components, e.g. "1.10-1" sorting below
    "1.2-1")."""
    if isinstance(payload, dict):
        versions = payload.get("versions")
        if isinstance(versions, dict) and versions:
            return str(max(versions.keys(), key=_version_sort_key))
    return None


def _crates_path(base: str, name: str) -> str:
    ident = _require_identifier("crates", name)
    return f"{base.rstrip('/')}/api/v1/crates/{quote(ident, safe='')}"


def _crates_extract(payload: Any) -> str | None:
    if isinstance(payload, dict):
        crate = payload.get("crate")
        if isinstance(crate, dict):
            v = crate.get("newest_version") or crate.get("max_stable_version")
            return str(v) if v else None
    return None


def _rubygems_path(base: str, name: str) -> str:
    ident = _require_identifier("rubygems", name)
    return f"{base.rstrip('/')}/api/v1/gems/{quote(ident, safe='')}.json"


def _rubygems_extract(payload: Any) -> str | None:
    if isinstance(payload, dict):
        v = payload.get("version")
        return str(v) if v else None
    return None


def _maven_path(base: str, name: str) -> str:
    ident = _require_identifier("maven", name)
    return f"{base.rstrip('/')}/solrsearch/select?q=a:{quote(ident, safe='')}&rows=1&wt=json"


def _maven_extract(payload: Any) -> str | None:
    if isinstance(payload, dict):
        resp = payload.get("response")
        if isinstance(resp, dict):
            docs = resp.get("docs")
            if isinstance(docs, list) and docs and isinstance(docs[0], dict):
                v = docs[0].get("latestVersion")
                return str(v) if v else None
    return None


def _nuget_path(base: str, name: str) -> str:
    ident = _require_identifier("nuget", name)
    return f"{base.rstrip('/')}/v3-flatcontainer/{quote(ident.lower(), safe='')}/index.json"


def _nuget_extract(payload: Any) -> str | None:
    if isinstance(payload, dict):
        versions = payload.get("versions")
        if isinstance(versions, list) and versions:
            return str(versions[-1])
    return None


_REGISTRY_SPECS: dict[str, _EndpointSpec] = {
    "npm": _EndpointSpec(_npm_path, _npm_extract),
    "cran": _EndpointSpec(_cran_path, _cran_extract),
    "cpan": _EndpointSpec(_cpan_path, _cpan_extract),
    "luarocks": _EndpointSpec(_luarocks_path, _luarocks_extract),
    "crates": _EndpointSpec(_crates_path, _crates_extract),
    "rubygems": _EndpointSpec(_rubygems_path, _rubygems_extract),
    "maven": _EndpointSpec(_maven_path, _maven_extract),
    "nuget": _EndpointSpec(_nuget_path, _nuget_extract),
}


class VcsHostSeedDataset(_ParquetRefreshStore, AbstractDataset):
    """GitLab or Codeberg latest-tag source (``vcs_gitlab_api_raw`` / ``vcs_codeberg_api_raw``).

    ``load()`` is a read-only projection of the persisted store; the live fetch runs
    only via ``save(RefreshRequest(...))`` (the pipeline's refresh-trigger node is the
    single writer, mirroring ``refresh_vdb_store``) — any other payload raises (this
    is still a read-only request source from every OTHER node's perspective).
    """

    _COLUMNS = _VERSION_COLUMNS

    def __init__(
        self,
        *,
        url: str,
        host: str,
        filepath: str,
        credentials: dict[str, Any] | None = None,
        timeout_seconds: int = DEFAULT_REFRESH_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_REFRESH_MAX_RETRIES,
        rps: float = DEFAULT_RPS,
        scheduler: RateLimitedScheduler | None = None,
        sleep: Callable[[float], None] = time.sleep,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if host not in _HOST_SPECS:
            raise ValueError(f"unknown VCS host {host!r}; expected one of {sorted(_HOST_SPECS)}")
        self._base_url = str(url)
        self._host = host
        self._filepath = str(filepath)
        self._credentials = credentials
        self._timeout_seconds = int(timeout_seconds)
        self._max_retries = int(max_retries)
        self.scheduler = scheduler if scheduler is not None else RateLimitedScheduler(rps=rps)
        self._sleep = sleep
        self.metadata = metadata
        # review fix #8: the single-source-of-truth store name this instance may
        # legitimately write — validated in save() against the incoming
        # RefreshRequest.store so a future positional drift between
        # _HOST_SPECS/the pipeline's outputs=[...] list can't silently misroute a
        # refresh into the wrong catalog entry.
        self._expected_store = f"vcs_{host}_api_raw"

    def request_path(self, identifier: str) -> str:
        return _HOST_SPECS[self._host].build_path(self._base_url, identifier)

    def fetch_one(self, identifier: str, *, fetcher: Callable[[str], Any] | None = None) -> Any:
        """One bounded fetch via :func:`~pyforge.atlas.datasets.refresh.fetch_one_with_retry`."""
        url = None if fetcher is not None else self.request_path(identifier)

        def _do_fetch() -> Any:
            if fetcher is not None:
                return fetcher(identifier)
            inner = APIDataset(
                url=url,
                load_args={"timeout": self._timeout_seconds},
                credentials=self._credentials,
            )
            return _coerce_json(inner.load())

        return fetch_one_with_retry(
            acquire=self.scheduler.acquire,
            fetch=_do_fetch,
            max_retries=self._max_retries,
            sleep=self._sleep,
        )

    def load_many(
        self,
        identifiers: Sequence[tuple[str, str]],
        *,
        fetcher: Callable[[str], Any] | None = None,
    ) -> pd.DataFrame:
        """Fetch every ``(conda_name, identifier)`` pair, then persist (AD-13
        skip-on-failure: a batch where every fetch failed / yielded no version is
        treated as EMPTY for persistence — never clobbers last-good with an all-null
        result)."""
        rows: list[dict[str, Any]] = []
        for conda_name, identifier in identifiers:
            try:
                payload = self.fetch_one(identifier, fetcher=fetcher)
                version = _HOST_SPECS[self._host].extract(payload)
                rows.append(
                    {
                        "conda_name": conda_name,
                        "upstream_version": version,
                        "last_error": None if version else "no version found in response",
                    }
                )
            except Exception as exc:
                rows.append({"conda_name": conda_name, "upstream_version": None, "last_error": str(exc)})
        frame = pd.DataFrame(rows, columns=list(self._COLUMNS))
        has_success = bool(rows) and frame["upstream_version"].notna().any()
        self._persist(frame if has_success else pd.DataFrame(columns=list(self._COLUMNS)))
        return frame

    def load(self) -> pd.DataFrame:
        return self._read_store(self._COLUMNS)

    def save(self, data: Any) -> None:
        if not isinstance(data, RefreshRequest):
            raise NotImplementedError(
                f"{type(self).__name__} only accepts a RefreshRequest trigger; it is "
                "otherwise a read-only request source."
            )
        if data.store != self._expected_store:
            # review fix #8: catch a pipeline-wiring drift (e.g. _HOST_SPECS vs. the
            # trigger node's positional outputs=[...] list falling out of sync)
            # loudly rather than silently persisting into the wrong instance's store.
            raise ValueError(
                f"{type(self).__name__} (host={self._host!r}) is configured for store "
                f"{self._expected_store!r} but received a RefreshRequest for "
                f"{data.store!r} — pipeline wiring has drifted out of sync."
            )
        if not data.force and not self._refresh_due(data.cadence_seconds):
            self._clear_stale()
            return
        self.load_many(data.vcs_pairs)

    def _describe(self) -> dict[str, Any]:
        return {
            "parameterization": type(self).__name__,
            "host": self._host,
            "filepath": self._filepath,
            "rps": self.scheduler.rps,
            "timeout_seconds": self._timeout_seconds,
            "max_retries": self._max_retries,
        }


class RegistryUpstreamDataset(_ParquetRefreshStore, AbstractDataset):
    """Cross-ecosystem registry latest-version source (Phase L ``vcs_registry_*_raw``).

    Same shape as :class:`VcsHostSeedDataset` (see its docstring) — one
    ``_REGISTRY_SPECS`` extractor table parameterized per registry.
    """

    _COLUMNS = _VERSION_COLUMNS

    def __init__(
        self,
        *,
        url: str,
        registry: str,
        filepath: str,
        credentials: dict[str, Any] | None = None,
        timeout_seconds: int = DEFAULT_REFRESH_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_REFRESH_MAX_RETRIES,
        rps: float = DEFAULT_RPS,
        scheduler: RateLimitedScheduler | None = None,
        sleep: Callable[[float], None] = time.sleep,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if registry not in _REGISTRY_SPECS:
            raise ValueError(f"unknown registry {registry!r}; expected one of {sorted(_REGISTRY_SPECS)}")
        self._base_url = str(url)
        self._registry = registry
        self._filepath = str(filepath)
        self._credentials = credentials
        self._timeout_seconds = int(timeout_seconds)
        self._max_retries = int(max_retries)
        self.scheduler = scheduler if scheduler is not None else RateLimitedScheduler(rps=rps)
        self._sleep = sleep
        self.metadata = metadata
        # review fix #8: see VcsHostSeedDataset.__init__ — validated in save().
        self._expected_store = f"vcs_registry_{registry}_raw"

    def request_path(self, identifier: str) -> str:
        return _REGISTRY_SPECS[self._registry].build_path(self._base_url, identifier)

    def fetch_one(self, identifier: str, *, fetcher: Callable[[str], Any] | None = None) -> Any:
        """See :class:`VcsHostSeedDataset.fetch_one` (shared :func:`fetch_one_with_retry`)."""
        url = None if fetcher is not None else self.request_path(identifier)

        def _do_fetch() -> Any:
            if fetcher is not None:
                return fetcher(identifier)
            inner = APIDataset(
                url=url,
                load_args={"timeout": self._timeout_seconds},
                credentials=self._credentials,
            )
            return _coerce_json(inner.load())

        return fetch_one_with_retry(
            acquire=self.scheduler.acquire,
            fetch=_do_fetch,
            max_retries=self._max_retries,
            sleep=self._sleep,
        )

    def load_many(
        self,
        identifiers: Sequence[tuple[str, str]],
        *,
        fetcher: Callable[[str], Any] | None = None,
    ) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        for conda_name, identifier in identifiers:
            try:
                payload = self.fetch_one(identifier, fetcher=fetcher)
                version = _REGISTRY_SPECS[self._registry].extract(payload)
                rows.append(
                    {
                        "conda_name": conda_name,
                        "upstream_version": version,
                        "last_error": None if version else "no version found in response",
                    }
                )
            except Exception as exc:
                rows.append({"conda_name": conda_name, "upstream_version": None, "last_error": str(exc)})
        frame = pd.DataFrame(rows, columns=list(self._COLUMNS))
        has_success = bool(rows) and frame["upstream_version"].notna().any()
        self._persist(frame if has_success else pd.DataFrame(columns=list(self._COLUMNS)))
        return frame

    def load(self) -> pd.DataFrame:
        return self._read_store(self._COLUMNS)

    def save(self, data: Any) -> None:
        if not isinstance(data, RefreshRequest):
            raise NotImplementedError(
                f"{type(self).__name__} only accepts a RefreshRequest trigger; it is "
                "otherwise a read-only request source."
            )
        if data.store != self._expected_store:
            # review fix #8: see VcsHostSeedDataset.save.
            raise ValueError(
                f"{type(self).__name__} (registry={self._registry!r}) is configured for "
                f"store {self._expected_store!r} but received a RefreshRequest for "
                f"{data.store!r} — pipeline wiring has drifted out of sync."
            )
        if not data.force and not self._refresh_due(data.cadence_seconds):
            self._clear_stale()
            return
        self.load_many(data.vcs_pairs)

    def _describe(self) -> dict[str, Any]:
        return {
            "parameterization": type(self).__name__,
            "registry": self._registry,
            "filepath": self._filepath,
            "rps": self.scheduler.rps,
            "timeout_seconds": self._timeout_seconds,
            "max_retries": self._max_retries,
        }
