"""``derived_artifacts`` pipeline nodes (Story B7, AC-3).

``build_universe_sbom`` — the full-universe CycloneDX BOM (§ 5.2 item 7): one conda
component per package (``?channel=conda-forge`` purl, ``cfe:pypi_name`` on mapped rows
for the matcher's universe membership), with ``cfe:atlas_built_at`` stamped in
metadata so consumers can enforce the AD-15 14-day freshness contract (refuse-stale,
exactly as the legacy ``universe_sbom`` gate).

PURE node: pandas + stdlib only; no inline IO; ``dagster``/``kedro_mcp`` never imported
(AD-1). Reuses the ported purl primitives from the ``universal_sbom`` nodes.
"""

from __future__ import annotations

import time
from typing import Any

import pandas as pd

from ..universal_sbom.nodes import conda_purl


def build_universe_sbom(
    core_packages_enumerated: pd.DataFrame,
    pypi_conda_mapping: pd.DataFrame,
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Emit the full-universe CycloneDX BOM (one conda component per package). Stamps
    ``cfe:atlas_built_at`` (from ``params:universe_sbom.now`` if given, else now) so the
    matcher can refuse a stale atlas (AD-15). A mapped conda component carries a
    ``cfe:pypi_name`` property (the universe-membership signal, DW-B7-3)."""
    params = parameters or {}
    now = params.get("universe_sbom", {}).get("now")
    built_at = int(time.time() if now is None else now)

    # conda_name -> pypi_name (one component per mapped pair; legacy universe-sbom rule)
    pypi_by_conda: dict[str, str] = {}
    for _, r in pypi_conda_mapping.iterrows():
        cname, pname = r.get("conda_name"), r.get("pypi_name")
        if cname and not pd.isna(cname) and pname and not pd.isna(pname):
            pypi_by_conda.setdefault(str(cname), str(pname))

    components: list[dict[str, Any]] = []
    for _, r in core_packages_enumerated.iterrows():
        cname = r.get("conda_name")
        if not cname or pd.isna(cname):
            continue
        cname = str(cname)
        version = None if pd.isna(r.get("latest_version")) else r.get("latest_version")
        comp: dict[str, Any] = {
            "type": "library",
            "bom-ref": f"conda-{cname}-{version or 'unknown'}",
            "name": cname,
            "version": version or "",
            "purl": conda_purl(cname, version),
        }
        mapped = pypi_by_conda.get(cname)
        if mapped:
            comp["properties"] = [{"name": "cfe:pypi_name", "value": mapped}]
        components.append(comp)

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "metadata": {
            "component": {"type": "application", "name": "conda-forge-universe", "bom-ref": "conda-forge-universe"},
            "properties": [{"name": "cfe:atlas_built_at", "value": str(built_at)}],
        },
        "components": components,
    }
