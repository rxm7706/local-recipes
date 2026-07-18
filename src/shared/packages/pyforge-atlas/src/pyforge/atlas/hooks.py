"""Project hooks (Story A3, assumption A3-1 — the recommended ttl-wiring mechanism).

Kedro's catalog and parameters are separate config groups, so a flipped catalog
entry cannot natively ``${...}``-reference a ``parameters.yml`` value. Rather than
duplicate the literal ttl into the catalog (a dual source — A2 pinned the ttls in
``parameters.yml``, proven by ``test_every_ttl_gated_entry_has_a_ttl_parameter``),
an ``after_catalog_created`` hook injects each ``IncrementalParquetDataset``'s TTL
from ``params:ttls.<dataset-name>`` at pipeline-build time.

This keeps ``parameters.yml`` the single source of truth, needs zero per-entry
catalog churn beyond A3's ``type:`` flip, and is DECOUPLED from both A3 gates:
- the ``kedro-catalog-check`` resolution test uses ``DataCatalog.from_config``
  directly (hooks do NOT run there, so ``ttl_seconds`` stays ``None`` and
  construction succeeds offline), and
- the dataset unit tests construct the dataset directly with an explicit
  ``ttl_seconds`` (no hook needed).
The hook only matters at real pipeline runtime (Wave B / B1).

The ``after_catalog_created`` spec was verified live against kedro 1.5.0:
``after_catalog_created(self, catalog, conf_catalog, conf_creds, parameters,
save_version, load_versions)`` — ``parameters`` is passed straight in, so the ttl
namespace is available without touching any credentialed or IO surface.

Imports are stdlib + ``kedro.framework.hooks`` only — NO ``IO_DENYLIST`` HTTP/DB
client and no ``dagster`` / ``kedro_mcp`` (this module is scanned by A2's
``test_no_inline_io.py`` too).
"""

from __future__ import annotations

import logging
from typing import Any

from kedro.framework.hooks import hook_impl

from pyforge.atlas.datasets import IncrementalParquetDataset

logger = logging.getLogger(__name__)

# The flipped datasets carry this type suffix in the raw catalog config. Used to
# detect flipped-but-un-TTL'd entries (P6) WITHOUT materializing every dataset.
_INCREMENTAL_TYPE_SUFFIX = "IncrementalParquetDataset"


class ProjectHooks:
    """Injects per-dataset TTLs from ``params:ttls.<name>`` (FR-3/AD-5)."""

    @hook_impl
    def after_catalog_created(
        self,
        catalog: Any,
        conf_catalog: dict[str, Any] | None = None,
        conf_creds: dict[str, Any] | None = None,
        parameters: dict[str, Any] | None = None,
        save_version: str | None = None,
        load_versions: dict[str, str] | None = None,
    ) -> None:
        # P8: guard the catalog interface. kedro 1.5.0 hands a DataCatalog that
        # exposes keys()/__getitem__; a classic pre-1.x catalog (only .list())
        # would silently inject nothing — fail clearly instead.
        if not (callable(getattr(catalog, "keys", None)) and hasattr(catalog, "__getitem__")):
            raise TypeError(
                "after_catalog_created received a catalog without the expected "
                "keys()/__getitem__ interface (kedro 1.5.0 DataCatalog); got "
                f"{type(catalog).__name__}. TTL injection cannot proceed."
            )

        ttls = (parameters or {}).get("ttls") or {}

        # Inject ttls, materializing ONLY the ttl-named entries (P7: short-circuit
        # BEFORE catalog[name] so unrelated datasets stay lazy), and isolate each
        # access so one broken unrelated dataset cannot sink the whole pass (P7).
        for name in catalog.keys():
            if name not in ttls:  # P7: skip before forcing materialization
                continue
            try:
                dataset = catalog[name]
            except Exception:  # noqa: BLE001 - one bad entry must not abort injection
                logger.exception(
                    "could not materialize catalog entry %r for TTL injection", name
                )
                continue
            if isinstance(dataset, IncrementalParquetDataset):
                dataset.ttl_seconds = ttls[name]

        # P6: an IncrementalParquetDataset with no params:ttls.<name> would keep
        # ttl_seconds=None and SILENTLY never re-fetch. The A2 gate
        # (test_every_ttl_gated_entry_has_a_ttl_parameter) guarantees the 15 flips
        # each have a ttl, so any miss is a real regression — fail loud. Detect
        # flipped entries from the RAW config (no materialization needed).
        flipped = {
            name
            for name, cfg in (conf_catalog or {}).items()
            if isinstance(cfg, dict)
            and str(cfg.get("type", "")).endswith(_INCREMENTAL_TYPE_SUFFIX)
        }
        missing = sorted(flipped - set(ttls))
        if missing:
            raise ValueError(
                "IncrementalParquetDataset catalog entries have no "
                f"params:ttls.<name> and would silently never re-fetch: {missing}. "
                "Declare a ttl under `ttls:` in conf/base/parameters.yml (A2 gate "
                "test_every_ttl_gated_entry_has_a_ttl_parameter pins this)."
            )
