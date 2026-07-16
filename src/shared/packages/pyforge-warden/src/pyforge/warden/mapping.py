"""Bundled conda→pypi identity-map plumbing (Story 1.2; populated 2.1).

Ownership decisions recorded:

* This module owns only the ASSET PLUMBING — packaged-JSON loading via
  ``importlib.resources`` (the same pattern the 1.1 schema tests use;
  never repo-relative paths). The map's real shape (per-entry
  ``pypi_name``/``match_source``/``match_confidence``), confidence-tier
  vocabulary, and generation pipeline (``scripts/generate_conda_pypi_map.py``,
  consuming the conda-forge-expert atlas ``export-purls`` TSV) are 2.1's.
* ``data/conda_pypi_map.json`` ships the real bundled map (Story 2.1);
  entries exist only for conda packages with a discovered pypi_purl — an
  absent key is already the correct "no candidate" signal.

This module reads a packaged asset only: no network, no subprocess.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources

_CONDA_PYPI_MAP_ASSET = "conda_pypi_map.json"


def _packaged_json(asset_name: str) -> object:
    """Load one packaged ``data/`` JSON asset from the installed package."""
    asset = resources.files("pyforge.warden") / "data" / asset_name
    return json.loads(asset.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_conda_pypi_map() -> dict[str, object]:
    """The bundled conda→pypi identity map (Story 2.1).

    Cached (the asset is immutable for the process lifetime and, at
    ~12K entries, re-parsing it per conda component built during a scan
    would be a real cost — Story 2.1 replaced the 1.2 stub with the real,
    populated map)."""
    mapping = _packaged_json(_CONDA_PYPI_MAP_ASSET)
    if not isinstance(mapping, dict):
        raise ValueError(
            f"packaged {_CONDA_PYPI_MAP_ASSET} must be a JSON object, "
            f"got {type(mapping).__name__}"
        )
    return mapping
