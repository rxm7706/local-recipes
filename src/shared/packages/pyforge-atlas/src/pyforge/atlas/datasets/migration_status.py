"""conda-forge-bot-data migration-status source datasets (Story B10, FR-21 / AD-2 / AD-13).

The VCS & Health pipeline gains the data behind ``conda-forge.org/status/#migrations`` —
the ``conda-forge/conda-forge-bot-data`` repo's ``status/`` tree. Two source-dataset kinds
own the fetch IO (THE A2 CRUX — the pure classification node never touches a client;
``tests/catalog/test_no_inline_io.py`` AST-scans the whole package and bans
``subprocess``/HTTP imports):

- :class:`MigrationCategoryDataset` — one of the **category-list** files
  ``status/{regular,longterm,closed,paused,total}_status.json``. They enumerate the
  active/closed/paused migrations and **drive the partitioning** (:func:`migration_names`),
  so the surface generalizes with ZERO code change when a new migration appears upstream
  (python314 today → python315 tomorrow). The active set = ``regular`` + ``longterm`` (the
  open migrations the status page renders; :data:`ACTIVE_CATEGORIES`).
- :class:`MigrationDetailDataset` — the per-migration ``status/migration_json/<name>.json``
  detail, **partitioned by active migration** (one partition per migration name the category
  lists surface — mirrors the catalog ``partitions.PartitionedDataset`` shape, with the AD-13
  offline-safety a stock ``PartitionedDataset`` has no way to provide). Each partition carries
  the per-feedstock buckets the status page renders: ``done``, ``in-pr``, ``awaiting-pr``,
  ``awaiting-parents``, ``not-solvable``, ``bot-error`` (:data:`MIGRATION_BUCKETS`).

**DELIBERATELY EXCLUDED — ``version_status.v2.json``** (the bot's version-update queue): the
atlas measures version currency itself (Phases H/K, ``behind-upstream``) and does not mirror
the bot's view of the same signal (spec § FR-21). :data:`EXCLUDED_STATUS_FILES` is the guard
a fetch never routes through; ``tests/datasets/test_migration_status.py`` asserts the exclusion.

**AD-13 (offline degradation).** Both dataset kinds take an **injected** ``fetcher`` (default
``None`` == OFFLINE / consumer profile). Offline — or on any fetch/write failure — the dataset
SKIPS GRACEFULLY: it keeps the last-good store intact, stamps a machine-readable
:class:`StalenessMarker` (reusing the B5 ``ExternalRefreshDataset`` atomic-write / never-clobber
/ never-raise shape, exactly like the B8 Basilisk sources), and ``load()`` returns the last-good
(or empty) payload while surfacing the marker. It NEVER hard-fails the run. No live GitHub call
in any test (AD-11).

**AD-2 (``GITHUB_RAW_BASE_URL`` routing).** Both datasets resolve their endpoint from the
EXISTING ``${globals:endpoint_bases.GITHUB_RAW_BASE_URL}`` override point (no new
``resolve_*_urls`` helper; enterprise/JFrog mirror routing inherited). No network at
``__init__`` — the entries materialize under ``kedro-catalog-check`` with stub config.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Callable

from kedro.io import AbstractDataset

from .refresh import StalenessMarker, _safe_int

logger = logging.getLogger(__name__)

# The status-page per-feedstock buckets a per-migration detail JSON renders (spec § FR-21).
# `done` is the migrated set; the remaining five are the pending/blocker buckets.
MIGRATION_BUCKETS = (
    "done",
    "in-pr",
    "awaiting-pr",
    "awaiting-parents",
    "not-solvable",
    "bot-error",
)

# The pending/blocker buckets in the precedence order a feedstock's blocker label is
# resolved when it appears in more than one (in-pr wins over awaiting-*, then the two
# error buckets). `done` is NOT here — it is the migrated (rebuild-done) set.
BLOCKER_BUCKETS = (
    "in-pr",
    "awaiting-pr",
    "awaiting-parents",
    "not-solvable",
    "bot-error",
)

# The category-list files (spec § FR-21). `regular` + `longterm` are the ACTIVE
# (open) migrations that drive the partitioning; `closed`/`paused` are inactive;
# `total` is the summary.
CATEGORY_FILES = {
    "regular": "regular_status.json",
    "longterm": "longterm_status.json",
    "closed": "closed_status.json",
    "paused": "paused_status.json",
    "total": "total_status.json",
}

# The categories whose migrations are ACTIVE (drive which detail partitions exist).
ACTIVE_CATEGORIES = ("regular", "longterm")

# The bot's version-update queue — DELIBERATELY EXCLUDED (spec § FR-21): the atlas
# measures version currency itself (Phases H/K). A fetch never routes through it.
EXCLUDED_STATUS_FILES = frozenset({"version_status.v2.json"})

# The status subtree under the conda-forge-bot-data repo (raw-content path prefix).
STATUS_PATH = "status"
MIGRATION_JSON_PATH = "status/migration_json"


def migration_names(payload: Any) -> list[str]:
    """Extract the migration names a category-list payload enumerates — the pure
    partition-key derivation (NO IO). This is what makes the surface generalize with
    zero code change: a new migration added upstream flows straight to a new partition.

    Robust to the several shapes the status files take (defensive, AD-13 never-crash):
    a ``dict`` keyed by migration name (meta keys starting with ``_`` are dropped), a
    ``dict`` with a ``"migrations"`` sub-collection, or a plain ``list`` of names / of
    ``{"name": ...}`` dicts. Order preserved; duplicates and blanks dropped; a name
    matching :data:`EXCLUDED_STATUS_FILES` (defensive) is never surfaced.
    """
    names: list[str] = []
    seen: set[str] = set()

    def _add(value: Any) -> None:
        if isinstance(value, dict):
            value = value.get("name")
        if value is None:
            return
        name = str(value).strip()
        # drop blanks, meta keys, the excluded queue, and the `.json` form of it.
        if not name or name.startswith("_") or name in EXCLUDED_STATUS_FILES:
            return
        if name in seen:
            return
        seen.add(name)
        names.append(name)

    if isinstance(payload, dict):
        inner = payload.get("migrations")
        if isinstance(inner, dict):
            for key in inner:
                _add(key)
        elif isinstance(inner, list):
            for item in inner:
                _add(item)
        else:
            for key in payload:
                _add(key)
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            _add(item)
    return names


class _StaleAwareStatusSource(AbstractDataset):
    """Shared AD-13 base for the two migration-status source datasets.

    Owns the ``GITHUB_RAW_BASE_URL``-resolved endpoint, the injected ``fetcher`` (default
    ``None`` == OFFLINE), and the keep-last-good + staleness sidecar discipline (reused from
    the B5 ``ExternalRefreshDataset`` / B8 Basilisk shape — atomic write, never clobber,
    never raise). ``__init__`` does NO network (materializes offline under
    ``kedro-catalog-check``).
    """

    STALENESS_FILENAME = ".staleness.json"

    def __init__(
        self,
        *,
        url: str,
        filepath: str,
        fetcher: Callable[..., Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._url = str(url)
        self._filepath = str(filepath)
        # Injected IO. None == OFFLINE (consumer profile): a due fetch keeps last-good +
        # marks stale, exactly like an unreachable endpoint (AD-13). The concrete GitHub-raw
        # fetcher is supplied by the Dagster resource / an attended run — NEVER imported here
        # (subprocess/HTTP are on the A2 no-inline-IO denylist).
        self._fetcher = fetcher
        self.metadata = metadata

    # -- AD-13 staleness sidecar (reused ExternalRefreshDataset shape) ------

    @property
    def _staleness_path(self) -> Path:
        return Path(self._filepath) / self.STALENESS_FILENAME

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

    def _mark_stale(self, reason: str, *, last_good_exists: bool) -> StalenessMarker:
        """Keep last-good; stamp a staleness marker. Never raises (AD-13 never-fail)."""
        marker = StalenessMarker(stale=True, reason=reason, last_good_exists=last_good_exists)
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

    def save(self, data: Any) -> None:
        raise NotImplementedError(
            f"{type(self).__name__} is a read-only migration-status source; it is never "
            "saved to (the pipeline classification node writes the derived output)."
        )


class MigrationCategoryDataset(_StaleAwareStatusSource):
    """A ``status/`` category-list source (regular / longterm / closed / paused / total).

    Fetches ONE ``status/<category>_status.json`` via the injected ``fetcher`` (GET of the
    ``GITHUB_RAW_BASE_URL``-resolved ``url``) and persists the parsed payload as last-good
    JSON. :func:`migration_names` turns a loaded payload into the partition keys. Offline
    (``fetcher=None``) — or on any fetch/write failure — keep last-good + mark stale +
    return the last-good (or ``{}``); never crashes.
    """

    LAST_GOOD_FILENAME = "category.json"

    @property
    def _store_path(self) -> Path:
        return Path(self._filepath) / self.LAST_GOOD_FILENAME

    def _read_last_good(self) -> Any:
        path = self._store_path
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def refresh(self, *, fetcher: Callable[[str], Any] | None = None) -> Any:
        """Fetch the category list via the injected ``fetcher`` (attended / Dagster-driven).
        Offline / on failure / empty → keep last-good + mark stale + return last-good (AD-13).
        Never raises. This is the DATASET-owned fetch; the pure node consumes :meth:`load`."""
        fetcher = fetcher if fetcher is not None else self._fetcher
        last_good_exists = self._store_path.is_file()
        if fetcher is None:
            self._mark_stale(
                "offline: no GitHub-raw fetcher wired (consumer profile)",
                last_good_exists=last_good_exists,
            )
            return self._read_last_good()
        try:
            payload = fetcher(self._url)
        except Exception as exc:  # AD-13: an unreachable endpoint never fails the run.
            logger.warning("migration category fetch failed, keeping last-good: %s", exc)
            self._mark_stale(
                f"category fetch failed: {type(exc).__name__}: {exc}",
                last_good_exists=last_good_exists,
            )
            return self._read_last_good()
        if not payload:  # never write an empty/None payload over a good one (AD-13).
            self._mark_stale("category fetch returned no data", last_good_exists=last_good_exists)
            return self._read_last_good()
        try:
            self._atomic_write(self._store_path, json.dumps(payload))
        except (OSError, TypeError, ValueError) as exc:  # write failure → keep last-good.
            logger.warning("category write failed, keeping last-good: %s", exc)
            self._mark_stale(
                f"category write failed: {type(exc).__name__}: {exc}",
                last_good_exists=last_good_exists,
            )
            return self._read_last_good()
        self._clear_stale()
        return payload

    def load(self) -> Any:
        """OFFLINE-safe entry: with no fetcher wired, keep last-good + mark stale + return
        the last-good (or ``None``). The credentialed refresh is attended-driven via
        :meth:`refresh` (AD-11)."""
        if self._fetcher is None:
            self._mark_stale(
                "offline: no GitHub-raw fetcher wired (consumer profile)",
                last_good_exists=self._store_path.is_file(),
            )
            return self._read_last_good()
        last_good = self._read_last_good()
        if last_good is None:
            self._mark_stale(
                "wired fetcher but category not yet populated (attended fetch pending)",
                last_good_exists=False,
            )
        return last_good

    def _describe(self) -> dict[str, Any]:
        return {
            "url": self._url,
            "filepath": self._filepath,
            "fetcher_wired": self._fetcher is not None,
            "excluded_status_files": sorted(EXCLUDED_STATUS_FILES),
            "source": type(self).__name__,
        }


class MigrationDetailDataset(_StaleAwareStatusSource):
    """The per-migration ``status/migration_json/<name>.json`` detail — PARTITIONED by
    active migration (mirrors the catalog ``partitions.PartitionedDataset`` shape, with the
    AD-13 offline-safety a stock ``PartitionedDataset`` cannot provide).

    :meth:`fetch_partitions` takes the active migration names the CATEGORY LISTS surface and
    fetches one ``migration_json/<name>.json`` per name via the injected ``fetcher`` (GET of
    ``<url>/<name>.json``), writing one ``<name>.json`` partition each. ``load()`` returns
    ``{migration_name: detail_dict}`` — the resolved partitions the pure classification node
    consumes. Because the partition set is DERIVED from the category lists (never a hardcoded
    migration name), a new migration upstream flows straight through to a new partition with
    NO code change. Offline (``fetcher=None``) / on failure → keep last-good partitions + mark
    stale; never crashes. ``version_status.v2.json`` can never be a partition — a name matching
    :data:`EXCLUDED_STATUS_FILES` is dropped by :func:`migration_names` before it reaches here,
    and :meth:`fetch_partitions` guards it again.
    """

    STALENESS_FILENAME = ".staleness.json"

    @property
    def _partitions_dir(self) -> Path:
        return Path(self._filepath)

    @staticmethod
    def _partition_filename(name: str) -> str:
        # A migration name is a plain conda-forge migrator slug (e.g. python314); keep the
        # partition file basename == the name (mirrors PartitionedDataset partition ids).
        return f"{name}.json"

    def _detail_url(self, name: str) -> str:
        return f"{self._url}/{name}.json"

    def fetch_partitions(
        self,
        active_migrations: Any,
        *,
        fetcher: Callable[[str], Any] | None = None,
    ) -> dict[str, Any]:
        """Fetch one detail partition per ACTIVE migration name (attended / Dagster-driven).

        ``active_migrations`` is the list the category lists surface (via
        :func:`migration_names`); one ``GET migration_json/<name>.json`` per name, each
        persisted as a ``<name>.json`` partition. A per-migration 404 / empty / write failure
        is skipped (that partition keeps its last-good, if any) and does not abort the sweep —
        the whole run is marked stale if ANY partition could not refresh (AD-13). Offline
        (``fetcher=None``) → keep last-good + mark stale + return last-good. Never raises.
        Returns the resolved ``{name: detail}`` map. The pure node consumes :meth:`load`.
        """
        fetcher = fetcher if fetcher is not None else self._fetcher
        names = [n for n in _as_name_list(active_migrations) if n not in EXCLUDED_STATUS_FILES]
        if fetcher is None:
            self._mark_stale(
                "offline: no GitHub-raw fetcher wired (consumer profile)",
                last_good_exists=self._partitions_dir.is_dir(),
            )
            return self._load_partitions()
        any_failure = False
        for name in names:
            try:
                payload = fetcher(self._detail_url(name))
            except Exception as exc:  # AD-13: a per-migration failure never aborts the sweep.
                logger.warning("migration detail fetch failed for %s, keeping last-good: %s", name, exc)
                any_failure = True
                continue
            if not payload:  # 404 / empty → keep this partition's last-good (AD-13).
                any_failure = True
                continue
            try:
                self._atomic_write(
                    self._partitions_dir / self._partition_filename(name), json.dumps(payload)
                )
            except (OSError, TypeError, ValueError) as exc:  # write failure → keep last-good.
                logger.warning("migration detail write failed for %s, keeping last-good: %s", name, exc)
                any_failure = True
        if any_failure:
            self._mark_stale(
                "one or more migration detail partitions could not refresh",
                last_good_exists=self._partitions_dir.is_dir(),
            )
        else:
            self._clear_stale()
        return self._load_partitions()

    def _load_partitions(self) -> dict[str, Any]:
        """Resolve every persisted ``<name>.json`` partition → ``{name: detail}``. Robust to a
        missing dir (returns ``{}``) and to a single unreadable partition (skipped, never
        crashes the whole load — AD-13)."""
        out: dict[str, Any] = {}
        d = self._partitions_dir
        if not d.is_dir():
            return out
        for path in sorted(d.glob("*.json")):
            if path.name == self.STALENESS_FILENAME:  # defensive (marker is hidden)
                continue
            try:
                out[path.stem] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):  # a corrupt partition is skipped, not fatal (AD-13).
                logger.warning("migration detail partition unreadable, skipping: %s", path)
                continue
        return out

    def load(self) -> dict[str, Any]:
        """OFFLINE-safe entry: return the resolved ``{name: detail}`` partitions (or ``{}``).
        With no fetcher wired AND no partitions yet, surface staleness (a never-populated
        store must not present 'no migrations' as healthy — the AD-13 false-negative guard).
        The credentialed sweep is attended-driven via :meth:`fetch_partitions` (AD-11)."""
        partitions = self._load_partitions()
        if self._fetcher is None:
            self._mark_stale(
                "offline: no GitHub-raw fetcher wired (consumer profile)",
                last_good_exists=bool(partitions),
            )
        elif not partitions:
            self._mark_stale(
                "wired fetcher but no detail partitions yet (attended sweep pending)",
                last_good_exists=False,
            )
        return partitions

    def _describe(self) -> dict[str, Any]:
        return {
            "url": self._url,
            "filepath": self._filepath,
            "fetcher_wired": self._fetcher is not None,
            "partitioned_by": "active_migration",
            "excluded_status_files": sorted(EXCLUDED_STATUS_FILES),
            "source": type(self).__name__,
        }


def _as_name_list(value: Any) -> list[str]:
    """Coerce a migration-name input to a plain list of stripped strings, dropping blanks /
    ``None`` — robust to ``None``, a bare ``str`` (never per-character), a pandas Series /
    list / tuple (NEVER ``value or []`` — ambiguous truth value on a Series). AD-13 never-crash."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    try:
        out: list[str] = []
        for v in value:
            if v is None:
                continue
            s = str(v).strip()
            if s:
                out.append(s)
        return out
    except TypeError:
        return []
