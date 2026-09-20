"""Basilisk conda-native vulnerability source datasets (Story B8, FR-19 / AD-2 / AD-13).

The Vulnerability pipeline gains a second, conda-native identity axis: Basilisk
(``api.basilisk.prefix.dev``) — a live, no-auth, OSV-compatible REST API matched against
the conda-forge PURL (``pkg:conda/conda-forge/<name>@<version>``, the in-flight CEP-63 draft
form; purl itself is ECMA-427). Two source datasets own the fetch IO (THE A2 CRUX — the pure
node bodies never touch a client; ``tests/catalog/test_no_inline_io.py`` AST-scans the whole
package and bans ``subprocess``/HTTP imports):

- :class:`BasiliskBatchDataset` — ``POST /v1/querybatch`` with the documented **≤1,000
  queries/request** chunking (:func:`chunk_queries`, pure + fixture-tested). One request per
  chunk of conda PURLs; writes the lightweight batch shape (``conda_name``, ``advisory_id``,
  ``modified``) via the pure ``ingest_basilisk_advisories`` node.
- :class:`BasiliskDetailDataset` — the bounded ``GET /v1/vulns/{id}`` detail fetch binding the
  standard atlas rate-limit discipline (concurrency cap via :func:`resolve_worker_count`,
  ``Retry-After`` honored via :func:`parse_retry_after` with a hard cap + ±25% jitter, one
  :class:`RateLimitedScheduler` token per request). The zero-error live run (85×250 batch +
  765 detail IDs in one pass) is NOT load evidence (Gemini PR-#64 fold) — the discipline is
  exercised structurally regardless.

**AD-13 (offline degradation).** Basilisk is **pre-announcement** (no public docs/repo as of
2026-07-16; API live-validated 2026-07-15). Both datasets take an **injected** ``fetcher``
(default ``None`` == OFFLINE / consumer profile). Offline — or on any fetch/write failure — the
dataset SKIPS GRACEFULLY: it keeps the last-good store intact, stamps a machine-readable
:class:`StalenessMarker` (reusing the B5 ``ExternalRefreshDataset`` atomic-write / never-clobber
/ never-raise shape), and ``load()`` returns the last-good (or empty) payload while surfacing the
marker. It NEVER hard-fails the run. No live Basilisk call in any test (AD-11).

**AD-2 (``BASILISK_BASE_URL`` routing).** Both datasets resolve their endpoint from
``${{globals:endpoint_bases.BASILISK_BASE_URL}}`` (the reserved 20th ``resolve_*_urls`` override
point A2 pre-declared; ``env_or`` custom resolver). No network at ``__init__`` — the entries
materialize under ``kedro-catalog-check`` with stub config.

**Story 21.4 (Tier 1 catalog source, CAP-2).** :class:`BasiliskPackagesDataset` is the THIRD
Basilisk dataset — the ``GET /v1/packages`` package CATALOG (``discovery_basilisk_packages_raw``,
``upstream_discovery`` pipeline), distinct from the two ``vulnerability_basilisk_*`` advisory
sources above. It is co-located here for cohesion but built on
:class:`~pyforge.atlas.datasets.refresh.ExternalRefreshDataset` (the base those two do NOT use):
``/v1/packages`` is a plain paginated GET over the whole catalog, not the ≤1,000-query-chunked
batch shape. Same ``BASILISK_BASE_URL`` override point — no new global.
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd
from kedro.io import AbstractDataset
from pyforge.core.atomic_write import atomic_write_text

from .rate_limit import (
    RETRY_AFTER_CAP_SECONDS,
    RETRY_AFTER_JITTER,
    FetchError,
    RateLimitedScheduler,
    parse_retry_after,
    resolve_worker_count,
)
from .refresh import (
    DEFAULT_REFRESH_MAX_RETRIES,
    DEFAULT_REFRESH_TIMEOUT_SECONDS,
    WEEKLY_SECONDS,
    ExternalRefreshDataset,
    StalenessMarker,
    _safe_int,
)

logger = logging.getLogger(__name__)

# Basilisk's documented ``POST /v1/querybatch`` cap: 1,000 queries per request
# (live run: 85 requests of 250 over the 21,163-package population, zero errors —
# NOT load evidence). The chunking lives HERE (dataset), never in a node body.
BASILISK_QUERYBATCH_MAX = 1000

# Default bounded-detail-fetch retry budget (the standard rate-limit discipline).
DEFAULT_DETAIL_MAX_RETRIES = 3

# The conda PURL form Basilisk is queried against — the in-flight CEP-63 draft
# (purl itself is the ECMA-427 standard).
CONDA_PURL_PREFIX = "pkg:conda/conda-forge"


def chunk_queries(purls: Any, size: int = BASILISK_QUERYBATCH_MAX) -> list[list[Any]]:
    """Split query keys into ``≤ size`` chunks — the ``POST /v1/querybatch`` ≤1,000-query
    discipline (AC-1). Pure list-math (no IO): ``None`` entries are dropped; the order is
    preserved; every chunk is ``≤ size`` and no key is dropped or duplicated.

    Raises ``ValueError`` for a non-positive ``size`` (a batch of 0 could never be sent).
    """
    if size <= 0:
        raise ValueError(f"chunk size must be > 0; got {size!r}")
    items = _as_item_list(purls)
    return [items[i : i + size] for i in range(0, len(items), size)]


def _as_item_list(value: Any) -> list[Any]:
    """Coerce a query-key input to a plain list, dropping ``None`` — robust to ``None``, a
    bare ``str`` (never per-character), a pandas Series / numpy array (NEVER ``value or []``,
    which raises "truth value ambiguous"), and non-iterables. AD-13: never crash the run."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    try:
        # Drop None AND scalar NaN/NA (a NaN from a pandas Series would otherwise become a "nan"
        # query key downstream). ``is_scalar`` guards pd.isna so a nested container element — which
        # pd.isna would reject with an ambiguous-truth error — is still passed through (Gemini #81).
        return [v for v in value if not (v is None or (pd.api.types.is_scalar(v) and pd.isna(v)))]
    except TypeError:
        return []


def build_conda_purl(conda_name: str, version: Any = None) -> str:
    """Build the conda PURL query key ``pkg:conda/conda-forge/<name>[@<version>]`` (CEP-63
    draft form). Pure; ``version`` optional (Basilisk matches name-first)."""
    name = str(conda_name).strip("/")
    if version is None or (isinstance(version, float) and pd.isna(version)):
        return f"{CONDA_PURL_PREFIX}/{name}"
    return f"{CONDA_PURL_PREFIX}/{name}@{version}"


def _apply_jitter(wait: float, rng: random.Random) -> float:
    """±``RETRY_AFTER_JITTER`` jitter on a backoff wait (prevents synchronized retry
    storms — the Phase-K contract). Never negative."""
    if wait <= 0:
        return 0.0
    factor = 1.0 + rng.uniform(-RETRY_AFTER_JITTER, RETRY_AFTER_JITTER)
    return max(0.0, wait * factor)


class _StaleAwareBasiliskSource(AbstractDataset):
    """Shared AD-13 base for the two Basilisk source datasets.

    Owns the ``BASILISK_BASE_URL``-resolved endpoint, the injected ``fetcher`` (default
    ``None`` == OFFLINE), a :class:`RateLimitedScheduler`, and the keep-last-good + staleness
    sidecar discipline (reused from the B5 ``ExternalRefreshDataset`` shape — atomic write,
    never clobber, never raise). ``__init__`` does NO network (materializes offline under
    ``kedro-catalog-check``).
    """

    STALENESS_FILENAME = ".staleness.json"
    LAST_GOOD_FILENAME = "last_good.json"

    def __init__(
        self,
        *,
        url: str,
        filepath: str,
        fetcher: Callable[..., Any] | None = None,
        rps: float | None = None,
        scheduler: RateLimitedScheduler | None = None,
        sleep: Callable[[float], None] = time.sleep,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._url = str(url)
        self._filepath = str(filepath)
        # Injected IO. None == OFFLINE (consumer profile): a due fetch keeps last-good +
        # marks stale, exactly like an unreachable endpoint (AD-13). The concrete Basilisk
        # fetcher is supplied by the Dagster resource / an attended run (DW-B8-1) — NEVER
        # imported here (subprocess/HTTP are on the A2 no-inline-IO denylist).
        self._fetcher = fetcher
        if scheduler is not None:
            self.scheduler = scheduler
        elif rps is not None:
            self.scheduler = RateLimitedScheduler(rps=rps)
        else:
            self.scheduler = RateLimitedScheduler()
        self._sleep = sleep
        # The concurrency cap (single-worker default; PHASE_K_AGGRESSIVE=1 restores 8).
        self._concurrency = resolve_worker_count(os.environ.get("PHASE_K_AGGRESSIVE"))
        self.metadata = metadata

    # -- AD-13 staleness sidecar (reused ExternalRefreshDataset shape) ------

    @property
    def _staleness_path(self) -> Path:
        return Path(self._filepath) / self.STALENESS_FILENAME

    @property
    def _last_good_path(self) -> Path:
        return Path(self._filepath) / self.LAST_GOOD_FILENAME

    @staticmethod
    def _atomic_write(target: Path, text: str) -> None:
        """Delegates to ``pyforge.core.atomic_write_text`` (Story 14.2, CAP-2
        -- the one shared temp-file-then-``os.replace`` primitive,
        mkstemp-based): an interrupted write leaves the last-good file
        untouched (AD-13 never-clobber)."""
        atomic_write_text(target, text)

    def _mark_stale(self, reason: str) -> StalenessMarker:
        """Keep last-good; stamp a staleness marker. Never raises (AD-13 never-fail)."""
        marker = StalenessMarker(stale=True, reason=reason, last_good_exists=self._last_good_path.is_file())
        try:
            self._atomic_write(self._staleness_path, json.dumps(marker.to_dict(), indent=2))
        except OSError as exc:  # a marker write must never take the run down
            logger.warning("could not write staleness marker for %s: %s", self._filepath, exc)
        return marker

    def _clear_stale(self) -> None:
        try:
            self._staleness_path.unlink(missing_ok=True)
        except OSError:  # pragma: no cover - best-effort
            pass

    def staleness(self) -> StalenessMarker | None:
        """Read the staleness marker if present (surfaced to consumers, AD-13). Robust to a
        malformed marker (non-dict JSON / non-numeric ``marked_at``) — returns ``None``
        rather than crashing a consumer's ``is_stale()`` check."""
        path = self._staleness_path
        if not path.is_file():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except OSError, ValueError:
            return None
        if not isinstance(raw, dict):
            return None
        return StalenessMarker(
            stale=bool(raw.get("stale", True)),
            reason=str(raw.get("reason", "")),
            marked_at=_safe_int(raw.get("marked_at", 0)),
            last_good_exists=bool(raw.get("last_good_exists", False)),
        )

    def is_stale(self) -> bool:
        marker = self.staleness()
        return bool(marker and marker.stale)

    # -- last-good store (keep-last-good; never write empty over good) ------

    def _read_last_good(self) -> list[Any]:
        """Read the last-good payload (a JSON list) — ``[]`` when absent/unreadable."""
        path = self._last_good_path
        if not path.is_file():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except OSError, ValueError:
            return []
        return raw if isinstance(raw, list) else []

    def _write_last_good(self, payload: list[Any]) -> None:
        self._atomic_write(self._last_good_path, json.dumps(payload))

    def _persist(self, payload: list[Any]) -> None:
        """Persist a non-empty fetch as last-good + clear stale; an empty fetch keeps the
        last-good store and marks stale (AD-13 never-write-empty-over-good)."""
        if not payload:
            self._mark_stale("fetch returned no data")
            return
        try:
            self._write_last_good(payload)
        except (OSError, TypeError, ValueError) as exc:
            # OSError = disk/write failure; TypeError/ValueError = a non-JSON-serializable
            # fetcher payload (datetime/set/numpy scalar) reaching json.dumps. Both are a
            # write failure of the last-good store — degrade to keep-last-good + mark stale
            # rather than propagate (AD-13 never-fail; module docstring keep-last-good contract).
            logger.warning("write of %s failed, keeping last-good: %s", self._filepath, exc)
            self._mark_stale(f"write failed: {type(exc).__name__}: {exc}")
            return
        self._clear_stale()

    # -- kedro AbstractDataset ---------------------------------------------

    def save(self, data: Any) -> None:
        raise NotImplementedError(
            f"{type(self).__name__} is a read-only Basilisk source; it is never saved to "
            "(the pipeline node writes the derived parquet output)."
        )

    def _describe(self) -> dict[str, Any]:
        return {
            "url": self._url,
            "filepath": self._filepath,
            "rps": self.scheduler.rps,
            "concurrency": self._concurrency,
            "fetcher_wired": self._fetcher is not None,
            "querybatch_max": BASILISK_QUERYBATCH_MAX,
            "source": type(self).__name__,
        }


class BasiliskBatchDataset(_StaleAwareBasiliskSource):
    """``POST /v1/querybatch`` batch source — FLIP(B8) of ``vulnerability_basilisk_raw``.

    Owns the ≤1,000-query chunking (:func:`chunk_queries`) and, per chunk, one POST via the
    injected ``fetcher``, acquiring a :class:`RateLimitedScheduler` token per request. The pure
    ``ingest_basilisk_advisories`` node consumes what ``load()`` resolves — a list of per-query
    records ``{"conda_name", "advisories": [{"id", "modified", "affected": [...]}]}`` — it NEVER
    reaches the fan-out (THE CRUX). Offline (``fetcher=None``) ``load()`` keeps last-good + marks
    stale + returns the last-good (or ``[]``) — never crashes/hangs.
    """

    def query_population(self, purls: Any, *, fetcher: Callable[[list[Any]], Any] | None = None) -> list[Any]:
        """Fan out the population over ``POST /v1/querybatch`` in ≤1,000-query chunks (AC-1).

        Chunks via :func:`chunk_queries`, acquires ONE rate-limit token per chunk-request, and
        delegates the physical POST to the injected ``fetcher`` (a chunk of purls -> a list of
        per-query records). Returns the concatenated records. ``fetcher=None`` (offline) ->
        keep-last-good + mark stale + return last-good. Any fetcher exception -> AD-13 stale
        (never propagates). This is the DATASET-owned fan-out an attended/Dagster run drives
        (DW-B8-1); the pure node never calls it.
        """
        fetcher = fetcher if fetcher is not None else self._fetcher
        if fetcher is None:
            self._mark_stale("offline: no Basilisk fetcher wired (consumer profile)")
            return self._read_last_good()
        out: list[Any] = []
        try:
            for chunk in chunk_queries(purls):
                self.scheduler.acquire()
                got = fetcher(chunk)
                if got:
                    out.extend(got)
        except Exception as exc:  # AD-13: an unreachable endpoint never fails the run.
            logger.warning("Basilisk querybatch failed, keeping last-good: %s", exc)
            self._mark_stale(f"querybatch failed: {type(exc).__name__}: {exc}")
            return self._read_last_good()
        self._persist(out)
        return out

    def load(self) -> list[Any]:
        """OFFLINE-safe entry (consumer profile): with no fetcher wired, keep last-good + mark
        stale + return the last-good (or ``[]``). The credentialed population fan-out is
        attended/Dagster-driven via :meth:`query_population` (DW-B8-1, AD-11)."""
        if self._fetcher is None:
            self._mark_stale("offline: no Basilisk fetcher wired (consumer profile)")
            return self._read_last_good()
        # A wired fetcher with no population at load-time cannot self-parameterize; the
        # attended path drives query_population. Return last-good so the DAG never crashes —
        # but if the store was never populated, SURFACE staleness (a wired-but-empty store
        # must not present "zero advisories, healthy" — the AD-13 false-negative guard).
        last_good = self._read_last_good()
        if not last_good:
            self._mark_stale("wired fetcher but store not yet populated (attended fan-out pending)")
        return last_good


class BasiliskDetailDataset(_StaleAwareBasiliskSource):
    """``GET /v1/vulns/{id}`` bounded detail source (Story B8, AC-1 rate-limit discipline).

    A separate follow-up pass over the unique advisory IDs (live: all 765 in one pass — NOT
    load evidence). :meth:`fetch_details` binds the standard atlas rate-limit discipline:
    a concurrency cap (single-worker default), one :class:`RateLimitedScheduler` token per
    request, and ``Retry-After`` honored (:func:`parse_retry_after`, hard-capped at
    ``RETRY_AFTER_CAP_SECONDS``) with ±25% jittered exponential backoff on a
    :class:`FetchError`. Offline / on failure -> AD-13 keep-last-good + mark stale.
    """

    def __init__(
        self,
        *,
        url: str,
        filepath: str,
        fetcher: Callable[..., Any] | None = None,
        rps: float | None = None,
        scheduler: RateLimitedScheduler | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_retries: int = DEFAULT_DETAIL_MAX_RETRIES,
        rng_seed: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            url=url,
            filepath=filepath,
            fetcher=fetcher,
            rps=rps,
            scheduler=scheduler,
            sleep=sleep,
            metadata=metadata,
        )
        self._max_retries = int(max_retries)
        # Deterministic jitter under test (seeded) — real runs use the default RNG.
        self._rng = random.Random(rng_seed)

    def fetch_details(
        self,
        advisory_ids: Any,
        *,
        fetcher: Callable[[str], Any] | None = None,
    ) -> list[Any]:
        """Bounded per-advisory ``GET /v1/vulns/{id}`` fetch under the rate-limit discipline.

        For each ID: acquire ONE token, call the injected ``fetcher(id)``. On a
        :class:`FetchError` (e.g. 429/503) back off — ``Retry-After`` via
        :func:`parse_retry_after` (a ``retry_after`` attribute on the exception is honored),
        else jittered exponential — and retry up to ``max_retries`` before re-raising. Offline
        (``fetcher=None``) -> keep-last-good + mark stale + return last-good. This is the
        DATASET-owned fan-out (DW-B8-1); the pure node consumes its resolved records.
        """
        fetcher = fetcher if fetcher is not None else self._fetcher
        if fetcher is None:
            self._mark_stale("offline: no Basilisk detail fetcher wired (consumer profile)")
            return self._read_last_good()
        # Robust to a Series/array/str/None input (AD-13 never-crash), and dedupe preserving
        # order — one advisory ID can appear for many conda packages; the bounded detail fetch
        # issues ONE GET per UNIQUE id (matches the docstring; saves rate-limit tokens).
        ids: list[Any] = []
        _seen: set = set()
        for i in _as_item_list(advisory_ids):
            if i not in _seen:
                _seen.add(i)
                ids.append(i)
        out: list[Any] = []
        try:
            for aid in ids:
                attempt = 0
                while True:
                    self.scheduler.acquire()
                    try:
                        rec = fetcher(aid)
                        if rec is not None:
                            out.append(rec)
                        break
                    except FetchError as exc:
                        attempt += 1
                        if attempt > self._max_retries:
                            raise
                        wait = parse_retry_after(getattr(exc, "retry_after", None))
                        if wait <= 0:
                            wait = min(float(2**attempt), RETRY_AFTER_CAP_SECONDS)
                        # Hard-cap the FINAL wait (post-jitter) at the cap — jitter must never
                        # push a Retry-After / backoff past the ceiling ("never hang").
                        self._sleep(min(_apply_jitter(wait, self._rng), RETRY_AFTER_CAP_SECONDS))
        except Exception as exc:  # AD-13: never fail the run on an unreachable endpoint.
            logger.warning("Basilisk detail fetch failed, keeping last-good: %s", exc)
            self._mark_stale(f"detail fetch failed: {type(exc).__name__}: {exc}")
            return self._read_last_good()
        self._persist(out)
        return out

    def load(self) -> list[Any]:
        """OFFLINE-safe entry (consumer profile): keep last-good + mark stale + return the
        last-good (or ``[]``). The bounded detail fan-out is attended-driven via
        :meth:`fetch_details` (DW-B8-1, AD-11)."""
        if self._fetcher is None:
            self._mark_stale("offline: no Basilisk detail fetcher wired (consumer profile)")
            return self._read_last_good()
        last_good = self._read_last_good()
        if not last_good:
            self._mark_stale("wired fetcher but store not yet populated (attended fan-out pending)")
        return last_good


# ---------------------------------------------------------------------------
# Story 21.4 — GET /v1/packages package catalog (discovery_basilisk_packages_raw)
# ---------------------------------------------------------------------------

# ``GET /v1/packages`` is PAGINATED: ``{"total", "offset", "limit", "items": [...]}``.
# Live-verified 2026-08-30: the server clamps ``limit`` to 200 regardless of the value
# requested (``?limit=1000`` still returns 200 items) and reported ``total`` = 34,105 —
# so the full catalog is ~171 sequential pages, never one bulk GET. Both constants are
# constructor-overridable; the page cap is the "never hang" guard (a server that keeps
# returning full pages past ``total`` can never spin this loop forever).
BASILISK_PACKAGES_PAGE_SIZE = 200
BASILISK_PACKAGES_MAX_PAGES = 1000

# The catalog columns projected from each ``/v1/packages`` item. ``name`` is renamed to
# ``conda_name`` (the identity column every other conda-side dataset carries);
# ``browse_ecosystem`` (e.g. ``conda-forge``) is the channel the package was matched in.
_BASILISK_PACKAGE_FIELDS: tuple[tuple[str, str], ...] = (
    ("name", "conda_name"),
    ("browse_ecosystem", "ecosystem"),
    ("latest_version", "latest_version"),
    ("version_count", "version_count"),
    ("status", "status"),
    ("mapping_state", "mapping_state"),
    ("coverage_status", "coverage_status"),
    ("highest_cvss", "highest_cvss"),
)
_BASILISK_PACKAGE_COLUMNS: tuple[str, ...] = tuple(dst for _, dst in _BASILISK_PACKAGE_FIELDS) + (
    "source",
    "fetched_at",
)


def _coerce_payload(payload: Any) -> Any:
    """Normalize an injected-fetcher return value to parsed JSON (dict / list). The
    fetcher contract is "GET this URL, return the response" — text, bytes, an
    already-parsed object, OR a Response-like object with a callable ``.json()``
    (mirrors ``core_sources._api_json``; review-pass 1: such an object used to parse
    as empty every time, leaving the store stale forever with no error). Anything
    unparseable -> ``None``."""
    if isinstance(payload, (bytes, str)):
        try:
            return json.loads(payload)
        except TypeError, ValueError:
            return None
    if hasattr(payload, "json") and callable(payload.json):
        try:
            return payload.json()
        except ValueError, TypeError:
            return None
    return payload


def parse_basilisk_packages_response(payload: Any) -> pd.DataFrame:
    """PURE parser for ONE ``GET /v1/packages`` page -> a ``conda_name``-keyed frame
    (:data:`_BASILISK_PACKAGE_COLUMNS`). Accepts the documented
    ``{"items": [...]}`` envelope OR a bare list of items, as JSON text/bytes or
    already-parsed. NEVER raises: a malformed / non-JSON / non-list ``items`` payload,
    or items without a ``name``, degrade to an EMPTY (but correctly-columned) frame —
    the same "layout break -> empty, never a crash" contract
    :func:`~pyforge.atlas.datasets.upstream_discovery.parse_trending_html` carries."""
    data = _coerce_payload(payload)
    if isinstance(data, dict):
        items = data.get("items")
    elif isinstance(data, list):
        items = data
    else:
        items = None
    if not isinstance(items, list):
        return pd.DataFrame(columns=_BASILISK_PACKAGE_COLUMNS)

    fetched_at = int(time.time())
    rows: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        row = {dst: item.get(src) for src, dst in _BASILISK_PACKAGE_FIELDS}
        row["conda_name"] = name.strip()
        row["source"] = "basilisk_packages"
        row["fetched_at"] = fetched_at
        rows.append(row)
    if not rows:
        return pd.DataFrame(columns=_BASILISK_PACKAGE_COLUMNS)
    return pd.DataFrame(rows, columns=_BASILISK_PACKAGE_COLUMNS)


def _envelope_int(payload: Any, key: str) -> int | None:
    data = _coerce_payload(payload)
    if not isinstance(data, dict):
        return None
    value = data.get(key)
    try:
        return int(value) if value is not None else None
    except TypeError, ValueError:
        return None


def _payload_total(payload: Any) -> int | None:
    """The ``total`` the page envelope reports (``None`` when absent/malformed)."""
    return _envelope_int(payload, "total")


def _payload_limit(payload: Any) -> int | None:
    """The ``limit`` the server ACTUALLY served (it clamps a larger request to 200 —
    live 2026-08-30); ``None`` when absent/malformed."""
    return _envelope_int(payload, "limit")


class BasiliskPackagesDataset(ExternalRefreshDataset):
    """Story 21.4 — the Basilisk ``GET /v1/packages`` package catalog
    (``discovery_basilisk_packages_raw``; catalog-sources.md Tier 1, "Distinct from
    ``vulnerability_basilisk_*``").

    Subclasses :class:`ExternalRefreshDataset` (the same base ``TrendingSnapshotDataset``
    / ``VDBStoreDataset`` use) to get the cadence-check / atomic-write / never-clobber /
    :class:`StalenessMarker` machinery for free (AD-13):

    - ``save`` (inherited, the SINGLE writer — the ``refresh_basilisk_packages`` trigger
      node): when a refresh is DUE, invokes :meth:`_do_refresh`.
    - :meth:`_do_refresh`: walks the paginated endpoint via the injected low-level
      ``fetcher: Callable[[str], Any]`` (``GET {BASILISK_BASE_URL}/v1/packages?limit=N&offset=M``,
      one :class:`RateLimitedScheduler` token per page — the standard atlas rate-limit
      discipline the two advisory datasets above bind too) and parses each page with
      :func:`parse_basilisk_packages_response`. The offset advances by the rows ACTUALLY
      returned and a page is "short" only against the limit the server actually served
      (it clamps larger requests to 200), so a ``page_size`` above the clamp still walks
      the whole catalog. Never raises.
    - **Partial walks never overwrite a fuller catalog** (review-pass 1): a walk that
      ends by a page-fetch failure or by the ``max_pages`` cap is PARTIAL. With a
      last-good store already on disk, ``_do_refresh`` returns an EMPTY frame so the
      inherited ``save()`` keeps last-good (a 200-row partial must never replace a
      34k catalog); with NO last-good, the partial is persisted (better than nothing)
      and :meth:`save` then marks the store stale with a ``partial catalog walk:
      <collected>/<total>`` reason so it is visibly incomplete.
    - :meth:`_write` / :meth:`load`: Parquet at ``<filepath>/basilisk_packages.parquet``;
      a missing / unreadable store degrades to an empty frame + staleness marker.

    ``fetcher=None`` (the shipped default) == OFFLINE: construction is network-free
    (``kedro-catalog-check``), and a DUE refresh keeps last-good + marks stale.
    """

    STORE_FILENAME = "basilisk_packages.parquet"
    _REQUIRED_COLUMNS = ("conda_name", "source", "fetched_at")

    def __init__(
        self,
        *,
        url: str,
        filepath: str,
        fetcher: Callable[[str], Any] | None = None,
        page_size: int = BASILISK_PACKAGES_PAGE_SIZE,
        max_pages: int = BASILISK_PACKAGES_MAX_PAGES,
        scheduler: RateLimitedScheduler | None = None,
        cadence_seconds: int | None = None,
        timeout_seconds: int = DEFAULT_REFRESH_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_REFRESH_MAX_RETRIES,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._url = str(url).rstrip("/")
        # Injected IO (None == offline) — NEVER imported here; supplied by the Dagster
        # resource / an attended run (DW-B8-1), exactly like the two datasets above.
        self._fetcher = fetcher
        self._page_size = max(1, int(page_size))
        self._max_pages = max(1, int(max_pages))
        self.scheduler = scheduler if scheduler is not None else RateLimitedScheduler()
        # Set by _do_refresh when a walk ends early (page failure / page cap); read by
        # save() to mark a persisted partial catalog stale. None == the last walk was
        # complete (or never ran).
        self._partial_walk: str | None = None
        super().__init__(
            filepath=filepath,
            # Bind our own zero-arg refresh ONLY when a fetcher is wired, so construction
            # stays offline and ``refresher_wired`` reports the truth.
            refresher=self._do_refresh if fetcher is not None else None,
            cadence_seconds=cadence_seconds if cadence_seconds is not None else WEEKLY_SECONDS,
            required_resource=None,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            metadata=metadata,
        )

    # -- refresh (dataset-owned IO; the injected fetcher is the ONLY seam) --

    def page_url(self, offset: int) -> str:
        """The ``?limit=&offset=`` page URL — built HERE (a node never builds one, AC-2).
        A base URL that already carries a query string is extended with ``&``."""
        sep = "&" if "?" in self._url else "?"
        return f"{self._url}{sep}limit={self._page_size}&offset={int(offset)}"

    def _do_refresh(self) -> pd.DataFrame:
        """Walk every page until ``total`` is reached or a short/empty page arrives (a
        COMPLETE walk). A page-fetch failure or the ``max_pages`` cap ends the walk
        PARTIAL: with a last-good store on disk an empty frame is returned so
        ``save()`` keeps last-good; with none, the partial rows are returned and
        :meth:`save` marks the store stale. Never raises."""
        frames: list[pd.DataFrame] = []
        collected = 0
        offset = 0
        pages = 0
        total: int | None = None
        served_limit: int | None = None
        partial_reason: str | None = None
        self._partial_walk = None
        while True:
            if total is not None and offset >= total:
                break  # complete: every row the server reported has been read
            if pages >= self._max_pages:
                partial_reason = f"page cap ({self._max_pages} pages) reached"
                break  # the never-hang guard
            try:
                self.scheduler.acquire()
                payload = self._fetcher(self.page_url(offset))
            except Exception as exc:  # AD-13: an unreachable endpoint never fails the run.
                partial_reason = f"page fetch failed at offset={offset}: {type(exc).__name__}: {exc}"
                break
            pages += 1
            if total is None:
                total = _payload_total(payload)
            if served_limit is None:
                served_limit = _payload_limit(payload)
            frame = parse_basilisk_packages_response(payload)
            if frame.empty:
                if pages == 1:
                    logger.warning("Basilisk /v1/packages first page parsed zero rows (layout break?)")
                break  # complete: nothing more to read
            frames.append(frame)
            collected += len(frame)
            offset += len(frame)  # advance by rows ACTUALLY served, not by page_size
            effective_page = min(self._page_size, served_limit) if served_limit else self._page_size
            if len(frame) < effective_page:
                break  # complete: a short page (against the limit actually served) is the last page

        if partial_reason is not None and frames:
            summary = f"partial catalog walk: {collected}/{total if total is not None else '?'} ({partial_reason})"
            self._partial_walk = summary
            if self._store_exists():
                # Never overwrite a fuller last-good catalog with a partial one.
                logger.warning("Basilisk /v1/packages %s — keeping the existing last-good store", summary)
                return pd.DataFrame(columns=_BASILISK_PACKAGE_COLUMNS)
            logger.warning("Basilisk /v1/packages %s — persisting the partial (no last-good exists)", summary)
        elif partial_reason is not None:
            logger.warning("Basilisk /v1/packages walk collected nothing (%s) — keeping last-good", partial_reason)

        if not frames:
            return pd.DataFrame(columns=_BASILISK_PACKAGE_COLUMNS)
        out = pd.concat(frames, ignore_index=True)
        return out.drop_duplicates(subset=["conda_name", "ecosystem"]).reset_index(drop=True)

    def save(self, data: Any) -> None:
        """The inherited single write path, plus: a PERSISTED partial walk (no last-good
        existed, so the partial was written) is marked stale with its
        ``partial catalog walk`` reason — a partial catalog must never read as fresh.
        A partial walk that was NOT persisted (last-good kept) carries the same reason
        instead of the base class's generic "refresh returned no data"."""
        self._partial_walk = None
        super().save(data)
        if self._partial_walk:
            self._mark_stale(self._partial_walk)

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
            # A malformed refresh must not persist a store that reads as "no packages"
            # downstream — reject it so save() keeps last-good + marks stale.
            raise ValueError(f"basilisk packages refresh frame missing required columns: {missing}")
        self._atomic_write(self._store_path, lambda p: frame.to_parquet(p, index=False))

    def load(self) -> pd.DataFrame:
        if not self._store_exists():
            self._mark_stale(
                "basilisk packages store absent (never refreshed / offline)",
                only_if_absent=True,
            )
            return pd.DataFrame(columns=_BASILISK_PACKAGE_COLUMNS)
        try:
            return pd.read_parquet(self._store_path)
        except Exception as exc:  # corrupt/truncated store must not crash the consumer.
            logger.warning(
                "basilisk packages store unreadable (%s), degrading to empty: %s",
                self._store_path,
                exc,
            )
            self._mark_stale("basilisk packages store unreadable", only_if_absent=True)
            return pd.DataFrame(columns=_BASILISK_PACKAGE_COLUMNS)

    def _describe(self) -> dict[str, Any]:
        base = super()._describe()
        base.update(
            {
                "url": self._url,
                "page_size": self._page_size,
                "max_pages": self._max_pages,
                "rps": self.scheduler.rps,
                "fetcher_wired": self._fetcher is not None,
            }
        )
        return base
