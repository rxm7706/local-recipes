"""External-refresh assets for the three § 3.4 separately-built stores (Story B5).

The migration's boundary (spec §3.4 / §5.2 / §5.4) brings three out-of-pipeline stores
into scope as **scheduled external-refresh assets** in their domain pipelines:

- AppThreat vdb (``vulnerability_vdb_store``, FLIP(B5)) — refreshed by the ``vdb-refresh``
  task in the **vuln-db env** (``appthreat-vulnerability-db``); read by Phases G / G',
  ``scan-project``.
- offline OSV CVE store (``vulnerability_osv_offline_store``) — refreshed by
  ``update-cve-db`` → ``cve_manager.py`` from the osv.dev GCS bucket; read by the offline
  vulnerability scanner.
- the flat ``pypi_conda_map.json`` mapping cache (``pypi_conda_map_store``,
  :class:`MappingCacheDataset`) — Q6-consolidated to a thin flat-cache EXPORT of the
  migrated Phase C mapping (produced by the ``export_pypi_conda_map`` node; the dataset
  MERGES onto the last-good cache and keeps-last-good on an empty export).

**Design invariants (the whole reason this module is shaped the way it is):**

1. **Dataset-owned IO, node stays pure (AD-2/AD-6).** The fetch/refresh is a DATASET
   concern; the pipeline node is a pure ``trigger -> store`` transform. The vuln-db-env
   invocation is an **INJECTED** ``refresher`` (stubbed in fixtures, supplied by the
   Dagster resource at C1 / attended runs — DW-B5-2) — the exact ``BigQueryDownloadsDataset``
   injected-client precedent. **No** ``subprocess`` / HTTP client is imported here (the
   whole ``datasets/`` subpackage is scanned by ``tests/catalog/test_no_inline_io.py``;
   ``subprocess`` is on the denylist — a shell-out would be caught).

2. **Declared resource requirement + retry/observability budget, not a shell-out (AD-6).**
   The vuln-db env is modeled as a :class:`RequiredResource` declaration; the per-asset
   retry/timeout budget is declared metadata (``_describe``) a Dagster resource reads at
   C1, never an implicit ``os.system``.

3. **Air-gapped degradation: skip-and-mark-stale, never fail (AD-13).** When a refresh is
   DUE (store missing / older than the cadence, or ``force``) but cannot complete (no
   refresher / unreachable / empty result / write failure), the refresh **keeps the
   last-good store intact** (writes are atomic — a failed write never clobbers last-good)
   and stamps a machine-readable staleness marker; it never raises. A store still FRESH
   within its cadence is a no-op and is NOT marked stale (the operator's out-of-band cron
   keeps it fresh). ``load()`` surfaces the marker (``is_stale()`` / ``staleness()``).

4. **Schedule is DECLARATIVE only; Dagster wiring is C1 (AD-1/AD-6).** The cadence lives in
   ``params:refresh_cadences`` (== the legacy TTLs, :data:`LEGACY_REFRESH_TTLS`, and
   cross-checked against the independent ``ttls`` block) and is fixture-tested here;
   ``dagster`` is NEVER imported (AD-1 denylist). The ``dagster-dryrun`` gate + the concrete
   refresher injection both land at C1 (DW-B5-2).

5. **Single-writer (AD-3/AD-10).** Each store is written by exactly ONE node (its refresh
   asset); Phases G / G' and ``scan-project`` consume it read-only. Enforced by
   ``tests/pipelines/test_refresh_single_writer.py``.

Imports are restricted to ``pandas`` / ``kedro`` / ``pathlib`` / ``os`` / ``json`` /
``time`` / ``dataclasses`` / ``logging`` / stdlib-non-IO — NO ``IO_DENYLIST`` HTTP/DB/
process client and no ``dagster`` / ``kedro_mcp``.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import pandas as pd
from kedro.io import AbstractDataset

from .vdb_boundary import coerce_cvss_score

logger = logging.getLogger(__name__)

# One week in seconds — the cadence all three refresh assets share (spec §5.4:
# "vdb-refresh / update-cve-db / update-mapping-cache weekly").
WEEKLY_SECONDS = 604_800

# Default per-asset retry/observability budget (AD-6 "every node carries its own
# timeout/retry budget"). Declarative metadata a Dagster resource reads at C1 (DW-B5-2);
# NOT enforced in-loop (the injected refresher / Dagster retry policy applies it).
DEFAULT_REFRESH_TIMEOUT_SECONDS = 900
DEFAULT_REFRESH_MAX_RETRIES = 3

# The legacy tasks' TTLs the declarative cadence MUST match (schedule-as-fixture,
# AC-1). Keyed by the catalog store dataset name; values in seconds with the legacy
# source cited. ``params:refresh_cadences`` is asserted == this table AND (for the two
# stores that also carry a `ttls` entry) cross-checked against the independent `ttls`
# block by tests/pipelines/test_refresh_schedule_fixtures.py.
LEGACY_REFRESH_TTLS: dict[str, int] = {
    # vdb-refresh: the AppThreat vdb is rebuilt on the weekly bootstrap cadence
    # (spec §5.4; conda-forge-expert `vdb-refresh` pixi task, vuln-db env).
    "vulnerability_vdb_store": WEEKLY_SECONDS,
    # update-cve-db: cve_manager.CVE_TTL_DAYS = 7 (spec §5.4; conf `ttls` mirror).
    "vulnerability_osv_offline_store": WEEKLY_SECONDS,
    # update-mapping-cache: mapping_manager.MAPPING_TTL_DAYS = 7 (spec §5.4).
    "pypi_conda_map_store": WEEKLY_SECONDS,
}


@dataclass(frozen=True)
class RequiredResource:
    """A declared resource requirement for a refresh asset (AD-6).

    This is METADATA — a declaration a Dagster resource reads at C1 to provision the
    environment/tool. It is NEVER an implicit shell-out: the actual invocation is the
    injected ``refresher`` callable, kept out of the node body entirely.
    """

    name: str
    tool: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "tool": self.tool}


# The vuln-db env resource the vdb refresh declares (AC-3): the `vdb-refresh` pixi task
# runs `appthreat-vulnerability-db` inside the separate vuln-db conda env.
VULN_DB_ENV_RESOURCE = RequiredResource(name="vuln-db", tool="appthreat-vulnerability-db")


@dataclass(frozen=True)
class RefreshRequest:
    """The pure NODE output → the store dataset's ``save`` input (a trigger, not data).

    The node computes this from ``params:refresh_cadences``; the dataset's ``save``
    consumes it — honoring ``force`` and using ``cadence_seconds`` for the freshness (TTL)
    check — and invokes its OWN injected refresher (the IO). Keeping the node's output a
    small declarative trigger (never the fetched bytes) is what keeps the node pure.
    """

    store: str
    cadence_seconds: int = WEEKLY_SECONDS
    force: bool = False
    resource: RequiredResource | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "store": self.store,
            "cadence_seconds": self.cadence_seconds,
            "force": self.force,
            "resource": self.resource.to_dict() if self.resource else None,
        }


@dataclass
class StalenessMarker:
    """Machine-readable staleness marker (AD-13). Written next to the store when a refresh
    could not complete; surfaced by ``load()`` so a consumer degrades the affected axis to
    ``indeterminate`` (never a silent pass)."""

    stale: bool
    reason: str
    marked_at: int = field(default_factory=lambda: int(time.time()))
    last_good_exists: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "stale": self.stale,
            "reason": self.reason,
            "marked_at": self.marked_at,
            "last_good_exists": self.last_good_exists,
        }


class ExternalRefreshDataset(AbstractDataset):
    """Base for the § 3.4 external-refresh store datasets.

    Owns the AD-13 skip-and-mark-stale discipline (with a cadence/force freshness check +
    atomic writes) + the declared-resource + retry/observability budget metadata.
    Subclasses implement the store-specific ``_write`` / ``load`` / ``_store_exists`` /
    ``_store_mtime`` using ONLY the injected ``refresher`` for fetch IO — never a
    denylisted client.

    Construction is offline (no network / no fetch at ``__init__``) so the entries
    materialize under the ``kedro-catalog-check`` resolution gate with stub config; the
    injected ``refresher`` defaults to ``None`` (offline: a DUE refresh keeps last-good and
    marks stale; a fresh store is a no-op).
    """

    #: sidecar filename for the staleness marker, written alongside the store path.
    STALENESS_FILENAME = ".staleness.json"

    def __init__(
        self,
        *,
        filepath: str,
        refresher: Callable[[], Any] | None = None,
        cadence_seconds: int | None = None,
        required_resource: RequiredResource | None = None,
        timeout_seconds: int = DEFAULT_REFRESH_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_REFRESH_MAX_RETRIES,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._filepath = str(filepath)
        # Injected IO. None == offline (no live fetch): a DUE refresh keeps last-good and
        # marks stale, exactly like an unreachable endpoint (AD-13). The real refresher is
        # supplied by the Dagster resource at C1 / an attended run (DW-B5-2) — NEVER
        # imported here.
        self._refresher = refresher
        self._cadence_seconds = int(cadence_seconds) if cadence_seconds is not None else WEEKLY_SECONDS
        self._required_resource = required_resource
        self._timeout_seconds = int(timeout_seconds)
        self._max_retries = int(max_retries)
        self.metadata = metadata

    # -- AD-13 staleness sidecar -------------------------------------------

    @property
    def _staleness_path(self) -> Path:
        return Path(self._filepath) / self.STALENESS_FILENAME

    def _store_exists(self) -> bool:
        raise NotImplementedError

    def _store_mtime(self) -> float:
        """Modification time of the persisted store (for the cadence/TTL check). Raises
        ``OSError`` if absent — callers treat that as 'refresh due'."""
        raise NotImplementedError

    def _mark_stale(self, reason: str, *, only_if_absent: bool = False) -> StalenessMarker:
        """Keep last-good; stamp a staleness marker. Never raises (AD-13 never-fail).
        ``only_if_absent`` skips rewriting an existing marker (read-path idempotence)."""
        marker = StalenessMarker(stale=True, reason=reason, last_good_exists=self._store_exists())
        if only_if_absent and self._staleness_path.is_file():
            return marker
        try:
            # atomic (tmp + os.replace) so a crash/ENOSPC mid-write can't leave a
            # truncated marker that a later is_stale() chokes on (B5 follow-up review)
            self._atomic_write(
                self._staleness_path,
                lambda p: p.write_text(
                    json.dumps(marker.to_dict(), indent=2), encoding="utf-8"
                ),
            )
        except OSError as exc:  # marker write must itself never take the run down
            logger.warning("could not write staleness marker for %s: %s", self._filepath, exc)
        return marker

    def _clear_stale(self) -> None:
        try:
            self._staleness_path.unlink(missing_ok=True)
        except OSError:  # pragma: no cover - best-effort
            pass

    def staleness(self) -> StalenessMarker | None:
        """Read the staleness marker if present (surfaced to consumers, AD-13). Robust to a
        malformed marker file (non-dict JSON / non-numeric ``marked_at``) — returns ``None``
        rather than crashing a consumer's ``is_stale()`` check."""
        path = self._staleness_path
        if not path.is_file():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):  # ValueError covers JSONDecodeError AND UnicodeDecodeError (invalid-UTF-8 corrupt store) — AD-13 never-fail
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

    # -- cadence / freshness -----------------------------------------------

    def _refresh_due(self, cadence_seconds: int, now: float | None = None) -> bool:
        """A refresh is DUE when the store is missing OR older than the cadence."""
        if not self._store_exists():
            return True
        try:
            age = (time.time() if now is None else now) - self._store_mtime()
        except OSError:
            return True
        return age >= cadence_seconds

    # -- refresh orchestration (single writer; AD-13 keep-last-good) --------

    def save(self, data: Any) -> None:
        """Refresh the store (the SINGLE write path). ``data`` is the pure node's
        :class:`RefreshRequest` trigger — the dataset HONORS its ``force`` + ``cadence_seconds``
        and invokes its OWN injected refresher (the IO). Behavior:

        - store still FRESH within cadence (and not ``force``) → no-op, NOT stale.
        - refresh DUE (or ``force``) with no refresher wired → keep last-good + mark stale
          (offline / unattended — the concrete refresher lands at C1, DW-B5-2).
        - refresh DUE with a refresher → fetch; on failure / empty / write error keep
          last-good + mark stale (never raise, never clobber — writes are atomic).
        """
        request = data if isinstance(data, RefreshRequest) else None
        force = bool(request.force) if request is not None else False
        cadence = int(request.cadence_seconds) if request is not None else self._cadence_seconds

        if not force and not self._refresh_due(cadence):
            # Fresh within cadence — the operator's out-of-band refresh keeps it current.
            self._clear_stale()
            return

        if self._refresher is None:
            # Due (or forced) but no refresher wired here — offline / unattended run.
            self._mark_stale("refresh due but no refresher wired (offline / unattended run)")
            return
        try:
            fetched = self._refresher()
        except Exception as exc:  # AD-13: an unreachable endpoint never fails the run.
            logger.warning("refresh of %s failed, keeping last-good: %s", self._filepath, exc)
            self._mark_stale(f"refresh failed: {type(exc).__name__}: {exc}")
            return
        if self._is_empty(fetched):
            # Never write an empty store over a good one (AD-13).
            self._mark_stale("refresh returned no data")
            return
        try:
            self._write(fetched)
        except Exception as exc:  # a write failure must never crash the run OR clobber.
            logger.warning("write of %s failed, keeping last-good: %s", self._filepath, exc)
            self._mark_stale(f"write failed: {type(exc).__name__}: {exc}")
            return
        self._clear_stale()

    # -- atomic write helper (never clobber last-good on a partial write) ---

    @staticmethod
    def _atomic_write(target: Path, write_fn: Callable[[Path], None]) -> None:
        """Write via a unique sibling temp then ``os.replace`` (AUD-ATLAS-029)."""
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(target.parent), suffix=".tmp", prefix=f".{target.name}."
        )
        os.close(fd)
        tmp = Path(tmp_name)
        try:
            write_fn(tmp)
            with open(tmp, "rb") as fh:
                os.fsync(fh.fileno())
            os.replace(tmp, target)
        except Exception:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    # -- subclass hooks ----------------------------------------------------

    @staticmethod
    def _is_empty(fetched: Any) -> bool:
        if fetched is None:
            return True
        if isinstance(fetched, pd.DataFrame):
            return fetched.empty
        try:
            return len(fetched) == 0
        except TypeError:
            # An unsized object is not a supported refresher return (the contract is a
            # DataFrame / list / dict) — treat as EMPTY so it can never clobber last-good.
            return True

    def _write(self, fetched: Any) -> None:
        raise NotImplementedError

    def load(self) -> Any:
        raise NotImplementedError

    def _describe(self) -> dict[str, Any]:
        return {
            "filepath": self._filepath,
            "refresh_cadence_seconds": self._cadence_seconds,
            "required_resource": self._required_resource.to_dict() if self._required_resource else None,
            # AD-6 retry/observability budget — declarative metadata C1's Dagster resource
            # reads (per-node timeout + retry); not enforced in-loop.
            "retry_budget": {"timeout_seconds": self._timeout_seconds, "max_retries": self._max_retries},
            "refresher_wired": self._refresher is not None,
            "asset": type(self).__name__,
        }


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class VDBStoreDataset(ExternalRefreshDataset):
    """The AppThreat vdb store — FLIP(B5) of ``vulnerability_vdb_store`` (was a path-only
    ``MemoryDataset``). Owns the vdb file format + the ``coerce_cvss_score`` read boundary
    (DW-B2-2), and declares the vuln-db env as a required resource (AC-3).

    - ``save`` (the vdb refresh, single writer): the injected refresher runs the vuln-db-env
      ``appthreat-vulnerability-db`` build and returns a normalized per-CVE frame with at
      least ``package_name`` + ``cve_id``; the dataset persists it as the store's normalized
      parquet (atomically). A malformed refresh (missing key columns) is rejected → keep
      last-good + mark stale. AD-13 on failure.
    - ``load`` (read-only, what Phases G / G' consume): reads the normalized store frame
      and applies ``coerce_cvss_score`` to the ``cvss_score`` column at THIS boundary
      (DW-B2-2) — so the node receives already-unwrapped floats (an unknown score stays
      ``None``, never a raw pydantic ``ScoreType`` and never NaN; a real ``0.0`` is kept).
      Missing / unreadable store → empty frame + staleness surfaced (AD-13).

    The store's "vdb file format" is the normalized per-CVE parquet at
    ``<filepath>/vdb_parsed.parquet``: the raw ~2.5 GB AppThreat vdb parse lives in the
    injected refresher (attended/scheduled, DW-B5-2), so the lean gate + air-gapped read
    never touch the raw format. This dataset is NOT ``pickle`` (the honest-format fix from
    A2's P2). A real operator's raw vdb is parsed into the normalized parquet by the
    injected refresher on the first scheduled/attended refresh.
    """

    STORE_FILENAME = "vdb_parsed.parquet"
    _CVSS_COLUMN = "cvss_score"
    _REQUIRED_COLUMNS = ("package_name", "cve_id")

    def __init__(
        self,
        *,
        filepath: str,
        refresher: Callable[[], Any] | None = None,
        cadence_seconds: int | None = None,
        timeout_seconds: int = DEFAULT_REFRESH_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_REFRESH_MAX_RETRIES,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            filepath=filepath,
            refresher=refresher,
            cadence_seconds=cadence_seconds if cadence_seconds is not None else WEEKLY_SECONDS,
            required_resource=VULN_DB_ENV_RESOURCE,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            metadata=metadata,
        )

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
            # A malformed refresh must not silently persist a store the G/G' consumers read
            # as "no vulnerabilities" — reject it so save() keeps last-good + marks stale.
            raise ValueError(f"vdb refresh frame missing required columns: {missing}")
        self._atomic_write(self._store_path, lambda p: frame.to_parquet(p, index=False))

    def load(self) -> pd.DataFrame:
        if not self._store_exists():
            # Air-gapped / never-refreshed: return an empty frame + surface a marker so a
            # consumer degrades gracefully (AD-13). Read-path idempotence: don't rewrite an
            # existing marker (avoids churn when both G and G' load the store).
            self._mark_stale("vdb store absent (never refreshed / air-gapped)", only_if_absent=True)
            return pd.DataFrame()
        try:
            frame = pd.read_parquet(self._store_path)
        except Exception as exc:
            # AUD-ATLAS-024: a corrupt/unreadable store must NOT degrade to an empty
            # frame that nodes treat as "no vulns". Absent (never refreshed) keeps the
            # AD-13 empty+stale path above; corrupt fails closed.
            logger.warning("vdb store unreadable (%s): %s", self._store_path, exc)
            self._mark_stale("vdb store unreadable", only_if_absent=True)
            from kedro.io.core import DatasetError

            raise DatasetError(
                f"vdb store unreadable at {self._store_path}: {exc}"
            ) from exc
        # DW-B2-2: coerce the CVSS ScoreType at the read boundary — the node gets floats.
        # Assign as OBJECT dtype so an unknown score stays ``None`` (never re-coerced to NaN
        # by pandas float inference) — the coerce contract is "None for unknown, never NaN
        # and never 0.0" (a real 0.0 is preserved).
        if self._CVSS_COLUMN in frame.columns:
            frame[self._CVSS_COLUMN] = pd.Series(
                [coerce_cvss_score(v) for v in frame[self._CVSS_COLUMN]],
                dtype=object,
                index=frame.index,
            )
        return frame


class OSVOfflineStoreDataset(ExternalRefreshDataset):
    """The offline OSV CVE store — FLIP(B5) of ``vulnerability_osv_offline_store`` (was a
    ``partitions.PartitionedDataset``). Refreshed by ``update-cve-db`` from the osv.dev GCS
    bucket; read by the offline vulnerability scanner / ``scan-project`` offline mode.

    - ``save`` (the OSV refresh, single writer): the injected fetcher downloads OSV records
      from ``bucket_url`` (``${globals:extra_overrides.OSV_VULNS_BUCKET_URL}``, routed AD-2
      style — the endpoint is dataset-level config, never a hardcoded host) and returns a
      **list** of records; the dataset persists them as the offline store (atomically). A
      non-list return is rejected → keep last-good + mark stale. AD-13 on failure.
    - ``load`` (read-only): reads the offline store (always a list). Missing / unreadable /
      non-list on disk → empty list + staleness surfaced (AD-13 — the offline scanner keeps
      working with the last-good CVE data).

    The ``bucket_url`` is stored as endpoint config; the fetcher (which actually reaches it,
    and which writes the operator-consumed store format at C1) is injected — no HTTP client
    is imported here.
    """

    STORE_FILENAME = "osv_records.json"

    def __init__(
        self,
        *,
        filepath: str,
        bucket_url: str = "",
        refresher: Callable[[], Any] | None = None,
        cadence_seconds: int | None = None,
        timeout_seconds: int = DEFAULT_REFRESH_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_REFRESH_MAX_RETRIES,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            filepath=filepath,
            refresher=refresher,
            cadence_seconds=cadence_seconds if cadence_seconds is not None else WEEKLY_SECONDS,
            required_resource=None,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            metadata=metadata,
        )
        # AD-2: the endpoint base is dataset-level config; NO host is hardcoded and no HTTP
        # client is imported — the injected fetcher uses this base when supplied.
        self._bucket_url = bucket_url

    @property
    def _store_path(self) -> Path:
        return Path(self._filepath) / self.STORE_FILENAME

    def _store_exists(self) -> bool:
        return self._store_path.is_file()

    def _store_mtime(self) -> float:
        return self._store_path.stat().st_mtime

    def _write(self, fetched: Any) -> None:
        if not isinstance(fetched, list):
            # The OSV store is a list of records; a dict/scalar refresh return is malformed
            # (list(dict) would persist only keys) — reject so save() keeps last-good.
            raise TypeError(f"OSV refresh must return a list of records, got {type(fetched).__name__}")
        self._atomic_write(
            self._store_path, lambda p: p.write_text(json.dumps(fetched), encoding="utf-8")
        )

    def load(self) -> list[dict[str, Any]]:
        if not self._store_exists():
            self._mark_stale("OSV offline store absent (never refreshed / air-gapped)", only_if_absent=True)
            return []
        try:
            data = json.loads(self._store_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):  # ValueError covers JSONDecodeError AND UnicodeDecodeError (invalid-UTF-8 corrupt store) — AD-13 never-fail
            self._mark_stale("OSV offline store unreadable", only_if_absent=True)
            return []
        if not isinstance(data, list):
            self._mark_stale("OSV offline store is not a list", only_if_absent=True)
            return []
        return data

    def _describe(self) -> dict[str, Any]:
        out = super()._describe()
        out["bucket_url"] = self._bucket_url
        return out


class MappingCacheDataset(ExternalRefreshDataset):
    """The flat ``pypi_conda_map.json`` mapping cache — FLIP(B5) of ``pypi_conda_map_store``
    (Q6-consolidated). Written by the ``export_pypi_conda_map`` node (single writer), which
    passes the ``{pypi_name: conda_name}`` map exported from the migrated Phase C mapping.

    **Q6 semantics (deviation recorded, AD-10):** under consolidation Phase C is the
    AUTHORITATIVE mapping source, so ``g10_spelling`` provenance + no-clobber are honored
    WITHIN the Phase C export (the node's rank-based collapse) — NOT against an independent
    higher-provenance flat-cache entry (that model is superseded by consolidation). To keep
    the compatibility shim byte-continuous for the authoring readers (DW-B5-1 deferred), the
    dataset **MERGES** the export onto the last-good cache: Phase C wins on conflict, and a
    ``pypi_name`` present only in the old cache is RETAINED (never silently dropped — the
    fix for the legacy full-overwrite regression).

    **AD-13:** an EMPTY export (a degenerate/empty Phase C run) is NOT written over a good
    cache — keep last-good + mark stale. The mapping refresh never fetches remotely (it
    reads the local Phase C), so it is offline-safe by construction.
    """

    def __init__(
        self,
        *,
        filepath: str,
        cadence_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        # A plain path to the flat json file (legacy shape). `filepath` here is the FILE,
        # not a dir — the marker sits next to it.
        super().__init__(
            filepath=filepath,
            refresher=None,  # no fetch: the "refresh" is the Phase C export passed to save
            cadence_seconds=cadence_seconds if cadence_seconds is not None else WEEKLY_SECONDS,
            required_resource=None,
            metadata=metadata,
        )

    @property
    def _cache_path(self) -> Path:
        return Path(self._filepath)

    @property
    def _staleness_path(self) -> Path:
        # filepath is a FILE here — put the marker next to it, keyed by name.
        p = self._cache_path
        return p.with_name(p.name + self.STALENESS_FILENAME)

    def _store_exists(self) -> bool:
        return self._cache_path.is_file()

    def _read_existing(self) -> dict[str, str]:
        if not self._cache_path.is_file():
            return {}
        try:
            data = json.loads(self._cache_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):  # ValueError covers JSONDecodeError AND UnicodeDecodeError (invalid-UTF-8 corrupt store) — AD-13 never-fail
            return {}
        return data if isinstance(data, dict) else {}

    def save(self, data: Any) -> None:
        """Merge the exported ``{pypi_name: conda_name}`` map onto the last-good cache
        (Phase C wins on conflict; old-only keys retained). An empty/non-dict export keeps
        last-good + marks stale (AD-13 never-clobber-with-empty). Never raises."""
        new_map = data if isinstance(data, dict) else {}
        if not new_map:
            self._mark_stale("mapping export produced no entries — keeping last-good")
            return
        merged = {**self._read_existing(), **{str(k): v for k, v in new_map.items() if isinstance(v, str)}}
        try:
            self._atomic_write(
                self._cache_path, lambda p: p.write_text(json.dumps(merged, indent=2), encoding="utf-8")
            )
        except Exception as exc:  # never crash / never clobber (AD-13).
            logger.warning("mapping cache write failed, keeping last-good: %s", exc)
            self._mark_stale(f"write failed: {type(exc).__name__}: {exc}")
            return
        self._clear_stale()

    def load(self) -> dict[str, str]:
        if not self._cache_path.is_file():
            self._mark_stale("mapping cache absent (never exported)", only_if_absent=True)
            return {}
        try:
            data = json.loads(self._cache_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):  # ValueError covers JSONDecodeError AND UnicodeDecodeError (invalid-UTF-8 corrupt store) — AD-13 never-fail
            self._mark_stale("mapping cache unreadable", only_if_absent=True)
            return {}
        return data if isinstance(data, dict) else {}
