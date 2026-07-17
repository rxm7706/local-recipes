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

from typing import Any

from kedro.framework.hooks import hook_impl

from pyforge.atlas.datasets import IncrementalParquetDataset


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
        ttls = (parameters or {}).get("ttls") or {}
        for name in catalog.keys():
            dataset = catalog[name]
            if isinstance(dataset, IncrementalParquetDataset) and name in ttls:
                dataset.ttl_seconds = ttls[name]
