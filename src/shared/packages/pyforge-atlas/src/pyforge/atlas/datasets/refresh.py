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
   concern; the pipeline node is a pure ``trigger -> store`` transform. Story 34.7: with
   ``pyforge.atlas.live_public_sources`` on, the vdb store runs the vuln-db env itself through
   ``pyforge.core.process`` (a ``ProcessPort``), and the OSV store fetches through
   ``public_sources``; an injected ``refresher`` (fixtures) still wins. **No** ``subprocess`` /
   HTTP client is imported here (the whole ``datasets/`` subpackage is scanned by
   ``tests/catalog/test_no_inline_io.py``; ``subprocess`` is on the denylist).

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

Imports are restricted to ``pandas`` / ``kedro`` / ``pathlib`` / ``json`` /
``time`` / ``dataclasses`` / ``logging`` / ``pyforge.core`` (Story 14.2, CAP-2's
pure-stdlib atomic-write leaf) / stdlib-non-IO — NO ``IO_DENYLIST`` HTTP/DB/
process client and no ``dagster`` / ``kedro_mcp``.
"""

from __future__ import annotations

import io
import json
import logging
import tempfile
import time
import zipfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
from kedro.io import AbstractDataset
from pyforge.core.atomic_write import atomic_write
from pyforge.core.process import PosixProcess, ProcessPort

from . import public_sources
from .vdb_boundary import coerce_cvss_score

logger = logging.getLogger(__name__)

# One week in seconds — the cadence all three refresh assets share (spec §5.4:
# "vdb-refresh / update-cve-db / update-mapping-cache weekly").
WEEKLY_SECONDS = 604_800

# One day in seconds — the discovery cadence added by Story 13.1 (``trending_candidates``
# has no legacy weekly equivalent to inherit). Shared here rather than duplicated as a
# local literal in both the dataset and its trigger node (review finding, Story 13.1).
DAILY_SECONDS = 86_400

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

    Story 27.2: optional ``vcs_pairs`` / ``github_repos`` carry identifier batches from
    the identity join (never raw fetch payloads). Story 34.2: optional ``pypi_pairs``
    carries ``(pypi_name, conda_name)`` pairs from the same run's Phase C mapping.
    Story 34.10: optional ``pypi_serials`` carries ``(pypi_name, last_serial)`` from the
    same run's Phase D serial snapshot, for the candidates only -- the serial gate.
    """

    store: str
    cadence_seconds: int = WEEKLY_SECONDS
    force: bool = False
    resource: RequiredResource | None = None
    vcs_pairs: tuple[tuple[str, str], ...] = ()
    github_repos: tuple[tuple[str, str], ...] = ()
    pypi_pairs: tuple[tuple[str, str], ...] = ()
    pypi_serials: tuple[tuple[str, int], ...] = ()
    # Story 34.7: (conda_name, pypi_name, version, npm_name, github_repo) per package the vdb scan covers
    vdb_targets: tuple[tuple[str, ...], ...] = ()
    # Story 34.7: (conda_name, version) per version with download history (legacy Phase G')
    vdb_versions: tuple[tuple[str, str], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "store": self.store,
            "cadence_seconds": self.cadence_seconds,
            "force": self.force,
            "resource": self.resource.to_dict() if self.resource else None,
            "vcs_pairs": list(self.vcs_pairs),
            "github_repos": list(self.github_repos),
            "pypi_pairs": list(self.pypi_pairs),
            "pypi_serials": list(self.pypi_serials),
            "vdb_targets": list(self.vdb_targets),
            "vdb_versions": list(self.vdb_versions),
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
                lambda p: p.write_text(json.dumps(marker.to_dict(), indent=2), encoding="utf-8"),
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
        except (
            OSError,
            ValueError,
        ):  # ValueError covers JSONDecodeError AND UnicodeDecodeError (invalid-UTF-8 corrupt store) — AD-13 never-fail
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

        # Story 34.5: a store that owns a public refresher is asked for it now, at the moment of
        # the refresh -- never at construction, which a Dagster code location runs at import.
        refresher = self._refresher if self._refresher is not None else self._live_refresher()
        if refresher is None:
            # Due (or forced) but no refresher wired here — offline / unattended run.
            self._mark_stale("refresh due but no refresher wired (offline / unattended run)")
            return
        try:
            fetched = refresher()
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
        """Delegates to ``pyforge.core.atomic_write`` (Story 14.2, CAP-2 --
        the one shared temp-file-then-``os.replace`` primitive,
        mkstemp-based; this method's own ``write_fn: Callable[[Path], None]``
        callback shape maps directly onto the primitive's own): an
        interrupted/failed write leaves the last-good file untouched (AD-13
        never-clobber)."""
        atomic_write(target, write_fn)

    # -- subclass hooks ----------------------------------------------------

    def _live_refresher(self) -> Callable[[], Any] | None:
        """The store's own public refresher, when it has one and live public sources are on
        (Story 34.5); ``None`` keeps today's behaviour. Asked by :meth:`save` each refresh, so
        the flag is read at the moment of the fetch. An injected ``refresher`` always wins."""
        return None

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
    except TypeError, ValueError:
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
    ``<filepath>/vdb_parsed.parquet``: the raw AppThreat vdb (about 10 GB, ``<filepath>/home``)
    is built and scanned by the live refresher (Story 34.7), so the lean gate + air-gapped read
    never touch the raw format. This dataset is NOT ``pickle`` (the honest-format fix from
    A2's P2).
    """

    STORE_FILENAME = "vdb_parsed.parquet"
    _CVSS_COLUMN = "cvss_score"
    _REQUIRED_COLUMNS = ("package_name", "cve_id")
    #: Story 34.7: the standalone extractor the ``vuln-db`` env runs (no pyforge import)
    EXTRACTOR = Path(__file__).with_name("vdb_extract.py")
    VDB_ENV = "vuln-db"
    # Story 34.7, measured 2026-10-18: a cold build 16 min (10 GB), the full per-version scan
    # 5 min 28 s; age + build + extract stay inside refresh_vdb_store's 5,400 s node budget
    AGE_TIMEOUT_SECONDS = 120
    VDB_REFRESH_TIMEOUT_SECONDS = 3600
    VDB_REFRESH_CODE = "import truststore; truststore.inject_into_ssl(); from vdb.cli import main; main()"
    EXTRACT_TIMEOUT_SECONDS = 1500

    def __init__(
        self,
        *,
        filepath: str,
        refresher: Callable[[], Any] | None = None,
        cadence_seconds: int | None = None,
        timeout_seconds: int = 5400,  # Story 34.7: refresh_vdb_store's node budget (build + scan)
        max_retries: int = DEFAULT_REFRESH_MAX_RETRIES,
        metadata: dict[str, Any] | None = None,
        process: ProcessPort | None = None,
        pixi_project: str | None = None,
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
        self._process = process
        self._pixi_project = Path(pixi_project) if pixi_project else None
        self._targets: tuple[tuple[str, ...], ...] = ()
        self._versions: tuple[tuple[str, str], ...] = ()
        self._rebuild_after = self._cadence_seconds

    # -- Story 34.7: the live refresher, through the vuln-db env --------------------

    def save(self, data: Any) -> None:
        """The trigger carries the packages to scan (``RefreshRequest.vdb_targets``); the base
        save decides whether a refresh is due and runs the refresher."""
        self._targets = tuple(data.vdb_targets) if isinstance(data, RefreshRequest) else ()
        self._versions = tuple(data.vdb_versions) if isinstance(data, RefreshRequest) else ()
        # the vdb's own age is judged against the request's cadence (params:refresh_cadences)
        self._rebuild_after = int(data.cadence_seconds) if isinstance(data, RefreshRequest) else self._cadence_seconds
        super().save(data)

    def _live_refresher(self) -> Callable[[], Any] | None:
        return self._build_from_vdb if public_sources.live() else None

    def _project(self) -> Path:
        if self._pixi_project is not None:
            return self._pixi_project
        for parent in self.EXTRACTOR.resolve().parents:
            if (parent / "pixi.toml").is_file():
                return parent
        raise FileNotFoundError("no pixi project above the atlas package; the vuln-db env is unreachable")

    @property
    def vdb_home(self) -> Path:
        """The atlas's own vdb, beside its store: never the ``vuln-db`` env's default
        ``$PIXI_PROJECT_ROOT/.claude/data/...``, which legacy rebuilds on its own schedule
        (legacy Phase G scanned a vdb mid-rebuild on 2026-10-18) and which a worktree lacks."""
        return Path(self._filepath) / "home"

    def _in_env(self, argv: list[str], timeout_s: float) -> str:
        """``pixi run --frozen -e vuln-db env VDB_HOME=... VDB_CACHE=... <argv>`` from the project
        root; its stdout. The ``env`` prefix sets the vdb paths after pixi's activation, which
        would otherwise point them at the shared copy. A non-zero exit raises, so save() keeps
        last-good under the marker (AD-13)."""
        process = self._process if self._process is not None else PosixProcess()
        paths = [f"VDB_HOME={self.vdb_home}", f"VDB_CACHE={Path(self._filepath) / 'cache'}"]
        full = ["pixi", "run", "--frozen", "-e", self.VDB_ENV, "env", *paths, *argv]
        result = process.run(full, cwd=self._project(), timeout_s=timeout_s)
        if result.returncode != 0:
            tail = (result.stderr or result.stdout or "").strip().splitlines()[-1:] or [""]
            raise RuntimeError(
                f"`{' '.join(argv[:3])}` in the {self.VDB_ENV} env exited {result.returncode}: {tail[0][:200]}"
            )
        return result.stdout

    def _build_from_vdb(self) -> pd.DataFrame:
        """Rebuild the vdb when it is older than the store's cadence (``vdb-refresh``), then scan
        every target's purls with the extractor and return its per-vulnerability frame."""
        if not self._targets:
            raise ValueError("the trigger carried no packages to scan")
        extractor = str(self.EXTRACTOR)
        age_lines = self._in_env(["python", "-I", extractor, "age"], self.AGE_TIMEOUT_SECONDS).strip().splitlines()
        age = int(age_lines[-1]) if age_lines and age_lines[-1].lstrip("-").isdigit() else -1
        cadence = self._rebuild_after
        if age < 0 or age >= cadence:
            logger.info("vdb is %s s old (cadence %s s): rebuilding it", age, cadence)
            self.vdb_home.mkdir(parents=True, exist_ok=True)
            # the env's `vdb-refresh` task, run with this store's paths (pixi.toml, vuln-db)
            self._in_env(["python", "-c", self.VDB_REFRESH_CODE, "--cache"], self.VDB_REFRESH_TIMEOUT_SECONDS)
        with tempfile.TemporaryDirectory(prefix="atlas-vdb-") as scratch:
            targets = Path(scratch) / "targets.json"
            versions = Path(scratch) / "versions.json"
            out = Path(scratch) / "vdb_parsed.parquet"
            targets.write_text(json.dumps([list(t) for t in self._targets]), encoding="utf-8")
            by_package: dict[str, list[str]] = {}
            for conda, version in self._versions:
                by_package.setdefault(conda, []).append(version)
            versions.write_text(json.dumps(by_package), encoding="utf-8")
            argv = ["python", "-I", extractor, "extract", "--targets", str(targets), "--versions", str(versions)]
            summary = self._in_env([*argv, "--out", str(out)], self.EXTRACT_TIMEOUT_SECONDS)
            logger.info("vdb extract: %s", summary.strip().splitlines()[-1:] or "")
            return pd.read_parquet(out)

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
        except Exception as exc:  # corrupt/truncated store must not crash the consumer.
            logger.warning("vdb store unreadable (%s), degrading to empty: %s", self._store_path, exc)
            self._mark_stale("vdb store unreadable", only_if_absent=True)
            return pd.DataFrame()
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

    The ``bucket_url`` is stored as endpoint config. Story 34.7: with
    ``pyforge.atlas.live_public_sources`` on, the store fetches each ecosystem's ``all.zip``
    through ``public_sources.fetch_bytes`` (no HTTP client is imported here); an injected
    fetcher (fixtures) still wins.
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

    #: Story 34.7: legacy ``update-cve-db`` fetches these OSV ecosystems (``ECOSYSTEMS_TO_FETCH``)
    ECOSYSTEMS = ("PyPI",)
    ARCHIVE_TIMEOUT_SECONDS = 600  # PyPI's all.zip was 36 MB on 2026-10-18

    def _live_refresher(self) -> Callable[[], Any] | None:
        """Story 34.7: the public bucket's per-ecosystem ``all.zip``, while live public sources
        are on and a bucket is configured."""
        return self._fetch_public if public_sources.live() and self._bucket_url else None

    def _fetch_public(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for ecosystem in self.ECOSYSTEMS:
            url = f"{self._bucket_url.rstrip('/')}/{ecosystem}/all.zip"
            records.extend(
                osv_records(public_sources.fetch_bytes(url, timeout=self.ARCHIVE_TIMEOUT_SECONDS), ecosystem)
            )
        return records

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
        self._atomic_write(self._store_path, lambda p: p.write_text(json.dumps(fetched), encoding="utf-8"))

    def load(self) -> list[dict[str, Any]]:
        if not self._store_exists():
            self._mark_stale("OSV offline store absent (never refreshed / air-gapped)", only_if_absent=True)
            return []
        try:
            data = json.loads(self._store_path.read_text(encoding="utf-8"))
        except (
            OSError,
            ValueError,
        ):  # ValueError covers JSONDecodeError AND UnicodeDecodeError (invalid-UTF-8 corrupt store) — AD-13 never-fail
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
        except (
            OSError,
            ValueError,
        ):  # ValueError covers JSONDecodeError AND UnicodeDecodeError (invalid-UTF-8 corrupt store) — AD-13 never-fail
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
            self._atomic_write(self._cache_path, lambda p: p.write_text(json.dumps(merged, indent=2), encoding="utf-8"))
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
        except (
            OSError,
            ValueError,
        ):  # ValueError covers JSONDecodeError AND UnicodeDecodeError (invalid-UTF-8 corrupt store) — AD-13 never-fail
            self._mark_stale("mapping cache unreadable", only_if_absent=True)
            return {}
        return data if isinstance(data, dict) else {}


# Minimum cadence when params:ttls carries zero or negative (Story 27.2, DW-FU-21-2-3).
_MIN_TTL_CADENCE_SECONDS = 60

_RETRY_BACKOFF_STEP_SECONDS = 0.05
_RETRY_BACKOFF_CAP_SECONDS = 0.5


def retry_backoff_seconds(attempt: int) -> float:
    return min(_RETRY_BACKOFF_STEP_SECONDS * attempt, _RETRY_BACKOFF_CAP_SECONDS)


def clamp_ttl_cadence(raw: Any, *, key: str, log: logging.Logger | None = None) -> int:
    """Read a cadence from ``params:ttls``; clamp zero/negative to a floor."""
    try:
        value = int(raw)
    except TypeError, ValueError:
        return WEEKLY_SECONDS
    if value <= 0:
        if log is not None:
            log.warning(
                "params:ttls.%s=%r is non-positive; clamping to %ss",
                key,
                raw,
                _MIN_TTL_CADENCE_SECONDS,
            )
        return _MIN_TTL_CADENCE_SECONDS
    return value


def fetch_one_with_retry(
    *,
    acquire: Callable[[], None],
    fetch: Callable[[], Any],
    max_retries: int,
    sleep: Callable[[float], None],
) -> Any:
    """Shared retry-with-backoff for VCS/registry seed fetches (DW-FU-21-2-5)."""
    attempt = 0
    while True:
        acquire()
        try:
            return fetch()
        except Exception:
            attempt += 1
            if attempt > max_retries:
                raise
            sleep(retry_backoff_seconds(attempt))


class _ParquetRefreshStore:
    """Shared last-good Parquet + staleness-marker persistence (AD-13).

    Lives beside :class:`StalenessMarker` / :class:`RefreshRequest` (DW-FU-21-2-6).
    """

    _filepath: str
    STORE_FILENAME = "store.parquet"
    STALENESS_FILENAME = ".staleness.json"
    merge_on: tuple[str, ...] = ("conda_name",)

    @property
    def _store_path(self) -> Path:
        return Path(self._filepath) / self.STORE_FILENAME

    @property
    def _staleness_path(self) -> Path:
        return Path(self._filepath) / self.STALENESS_FILENAME

    def _store_exists(self) -> bool:
        return self._store_path.is_file()

    def _store_mtime(self) -> float:
        return self._store_path.stat().st_mtime

    def _refresh_due(self, cadence_seconds: int, now: float | None = None) -> bool:
        if not self._store_exists():
            return True
        try:
            age = (time.time() if now is None else now) - self._store_mtime()
        except OSError:
            return True
        return age >= cadence_seconds

    @staticmethod
    def _atomic_write(target: Path, write_fn: Callable[[Path], None]) -> None:
        atomic_write(target, write_fn)

    def _mark_stale(self, reason: str, *, only_if_absent: bool = False) -> StalenessMarker:
        marker = StalenessMarker(stale=True, reason=reason, last_good_exists=self._store_exists())
        if only_if_absent and self._staleness_path.is_file():
            return marker
        try:
            self._atomic_write(
                self._staleness_path,
                lambda p: p.write_text(json.dumps(marker.to_dict(), indent=2), encoding="utf-8"),
            )
        except OSError as exc:
            logger.warning("could not write staleness marker for %s: %s", self._filepath, exc)
        return marker

    def _clear_stale(self) -> None:
        try:
            self._staleness_path.unlink(missing_ok=True)
        except OSError:
            pass

    def staleness(self) -> StalenessMarker | None:
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

    def _read_store(self, columns: Sequence[str]) -> pd.DataFrame:
        cols = list(columns)
        if not self._store_exists():
            self._mark_stale("store absent (never refreshed)", only_if_absent=True)
            return pd.DataFrame(columns=cols)
        try:
            frame = pd.read_parquet(self._store_path)
        except Exception as exc:
            logger.warning("store %s unreadable, degrading to empty: %s", self._store_path, exc)
            self._mark_stale("store unreadable", only_if_absent=True)
            return pd.DataFrame(columns=cols)
        for c in cols:
            if c not in frame.columns:
                frame[c] = pd.NA
        return frame[cols].reset_index(drop=True)

    def _persist(self, frame: pd.DataFrame) -> None:
        """Merge batch rows onto the persisted store by ``merge_on`` (Story 27.2)."""
        if frame is None or frame.empty:
            self._mark_stale("fetch returned no data — keeping last-good")
            return
        keys = list(self.merge_on)
        if not all(k in frame.columns for k in keys):
            self._mark_stale("fetch batch missing merge keys — keeping last-good")
            return
        to_write = frame
        if self._store_exists():
            try:
                existing = pd.read_parquet(self._store_path)
                for c in frame.columns:
                    if c not in existing.columns:
                        existing[c] = pd.NA
                batch = frame.copy()
                for c in existing.columns:
                    if c not in batch.columns:
                        batch[c] = pd.NA
                combined = pd.concat([existing, batch], ignore_index=True)
                to_write = combined.drop_duplicates(subset=keys, keep="last")
            except Exception as exc:
                logger.warning("could not merge onto %s, writing batch only: %s", self._store_path, exc)
        try:
            self._atomic_write(self._store_path, lambda p: to_write.to_parquet(p, index=False))
        except Exception as exc:
            logger.warning("write of %s failed, keeping last-good: %s", self._store_path, exc)
            self._mark_stale(f"write failed: {type(exc).__name__}: {exc}")
            return
        self._clear_stale()


def osv_records(archive: bytes, ecosystem: str) -> list[dict[str, Any]]:
    """Story 34.7: one record per (affected package, OSV entry) from an OSV ``all.zip``, the
    fields legacy ``update-cve-db`` keeps (``process_vulnerabilities``): withdrawn entries are
    skipped, and the package name is lower-cased with ``_`` as ``-``. A member that is not
    JSON is skipped; a body that is not a zip raises (the refresh keeps last-good, AD-13)."""
    records: list[dict[str, Any]] = []
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        for member in zf.namelist():
            if not member.endswith(".json"):
                continue
            try:
                entry = json.loads(zf.read(member))
            except ValueError:
                logger.warning("OSV %s: %s is not JSON, skipped", ecosystem, member)
                continue
            if not isinstance(entry, dict) or entry.get("withdrawn"):
                continue
            for affected in entry.get("affected") or []:
                name = ((affected or {}).get("package") or {}).get("name")
                if not name:
                    continue
                records.append(
                    {
                        "ecosystem": ecosystem,
                        "package_name": str(name).lower().replace("_", "-"),
                        "id": entry.get("id"),
                        "summary": entry.get("summary", "No summary available."),
                        "details": entry.get("details", ""),
                        "published": entry.get("published"),
                        "modified": entry.get("modified"),
                        "affected_versions": [e for r in affected.get("ranges") or [] for e in r.get("events") or []],
                        "aliases": entry.get("aliases") or [],
                    }
                )
    return records
