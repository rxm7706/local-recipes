"""Bundled conda→pypi identity-map plumbing (Story 1.2).

Ownership decisions recorded:

* This module owns only the ASSET PLUMBING — packaged-JSON loading via
  ``importlib.resources`` (the same pattern the 1.1 schema tests use;
  never repo-relative paths). The map's real shape, confidence-tier
  vocabulary, and generation pipeline are Story 2.1's.
* The stub asset ``data/conda_pypi_map.json`` ships an EMPTY mapping object
  (``{}``) so E1 never smuggles E2's identity map into scope; 1.2's two
  fixtures are both PyPI by design.

This module reads a packaged asset only: no network, no subprocess.
"""

from __future__ import annotations

import json
from importlib import resources

_CONDA_PYPI_MAP_ASSET = "conda_pypi_map.json"


def _packaged_json(asset_name: str) -> object:
    """Load one packaged ``data/`` JSON asset from the installed package."""
    asset = resources.files("python_deptry_osv_scanner") / "data" / asset_name
    return json.loads(asset.read_text(encoding="utf-8"))


def load_conda_pypi_map() -> dict[str, object]:
    """The bundled conda→pypi identity map (a stub ``{}`` until Story 2.1)."""
    mapping = _packaged_json(_CONDA_PYPI_MAP_ASSET)
    if not isinstance(mapping, dict):
        raise ValueError(
            f"packaged {_CONDA_PYPI_MAP_ASSET} must be a JSON object, "
            f"got {type(mapping).__name__}"
        )
    return mapping
