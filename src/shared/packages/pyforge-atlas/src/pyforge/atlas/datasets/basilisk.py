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
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Any, Callable

import pandas as pd
from kedro.io import AbstractDataset

from .rate_limit import (
    RETRY_AFTER_CAP_SECONDS,
    RETRY_AFTER_JITTER,
    FetchError,
    RateLimitedScheduler,
    parse_retry_after,
    resolve_worker_count,
)
from .refresh import StalenessMarker, _safe_int

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
        return [v for v in value if v is not None]
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
        """Write via a sibling ``.tmp`` then ``os.replace`` — an interrupted write leaves
        the last-good file untouched (AD-13 never-clobber)."""
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".tmp")
        try:
            tmp.write_text(text, encoding="utf-8")
            os.replace(tmp, target)
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:  # pragma: no cover - best-effort cleanup
                pass

    def _mark_stale(self, reason: str) -> StalenessMarker:
        """Keep last-good; stamp a staleness marker. Never raises (AD-13 never-fail)."""
        marker = StalenessMarker(
            stale=True, reason=reason, last_good_exists=self._last_good_path.is_file()
        )
        try:
            self._atomic_write(
                self._staleness_path, json.dumps(marker.to_dict(), indent=2)
            )
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
        except (OSError, ValueError):
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
        except (OSError, ValueError):
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
        except OSError as exc:
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

    def query_population(
        self, purls: Any, *, fetcher: Callable[[list[Any]], Any] | None = None
    ) -> list[Any]:
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
                            wait = min(float(2 ** attempt), RETRY_AFTER_CAP_SECONDS)
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
