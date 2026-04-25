#!/usr/bin/env python3
"""
PyPI-to-Conda Name Mapping Manager.

Fetches the canonical PyPI→conda name mapping from
``conda_forge_metadata.autotick_bot.get_pypi_name_mapping()`` and maintains a
local JSON cache for fast lookups by ``name_resolver.py``.

Historically this script pulled a YAML file from the conda/grayskull repo
(``src/grayskull/pypi/pypi_name_mapping.yaml``). That file was removed when
the mapping data moved to ``regro/cf-graph-countyfair`` / ``parselmouth`` and
is now exposed through the ``conda-forge-metadata`` Python package — which is
already pinned in this project's pixi env.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

try:
    from conda_forge_metadata.autotick_bot.pypi_to_conda import get_pypi_name_mapping
    METADATA_AVAILABLE = True
except ImportError:
    get_pypi_name_mapping = None  # type: ignore[assignment]
    METADATA_AVAILABLE = False

# The location of our local data cache
DATA_DIR = Path(__file__).parent.parent.parent / "data"
MAPPING_CACHE_FILE = DATA_DIR / "pypi_conda_map.json"

def fetch_conda_forge_metadata_mapping() -> dict:
    """Fetch the PyPI→conda name mapping via ``conda-forge-metadata``.

    Returns a flat ``{pypi_name: conda_name}`` dict (lowercased keys), the
    same shape ``name_resolver.py`` expects.
    """
    if not METADATA_AVAILABLE or get_pypi_name_mapping is None:
        raise ImportError("'conda-forge-metadata' is required to fetch the mapping.")

    print("Fetching latest mapping from conda-forge-metadata.autotick_bot...")
    try:
        entries = get_pypi_name_mapping()
    except Exception as e:
        print(f"Error: Failed to fetch mapping: {e}", file=sys.stderr)
        return {}

    processed_mapping: dict = {}
    for entry in entries:
        pypi_name = entry.get("pypi_name")
        conda_name = entry.get("conda_name")
        if pypi_name and conda_name:
            processed_mapping[pypi_name.lower()] = conda_name
    return processed_mapping

def load_local_cache() -> dict:
    """Loads the existing local mapping cache, if it exists."""
    if not MAPPING_CACHE_FILE.exists():
        return {}
    with open(MAPPING_CACHE_FILE) as f:
        return json.load(f)

def save_to_local_cache(mapping: dict):
    """Saves the combined mapping to the local cache file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(MAPPING_CACHE_FILE, "w") as f:
        json.dump(mapping, f, indent=2, sort_keys=True)

def update_mapping_cache(force: bool = False):
    """
    Updates the local cache by fetching the latest from Grayskull and merging it.
    """
    print("Updating PyPI-to-Conda name mapping cache...")
    
    MAPPING_TTL_DAYS = 7
    local_cache = load_local_cache()
    if local_cache and not force:
        if MAPPING_CACHE_FILE.exists():
            age_days = (time.time() - MAPPING_CACHE_FILE.stat().st_mtime) / 86400
            if age_days < MAPPING_TTL_DAYS:
                print(f"Cache is {age_days:.1f} days old (TTL={MAPPING_TTL_DAYS}d). Use --force to refresh.")
                return
        else:
            print("Cache already exists. Use --force to refresh from upstream.")
            return

    upstream_mapping = fetch_conda_forge_metadata_mapping()
    if not upstream_mapping:
        print("Could not fetch upstream mapping. Aborting update.", file=sys.stderr)
        return

    # Merge the new mapping into the local cache. The upstream is the authority.
    # We can also add custom/manual mappings here in the future if needed.
    local_cache.update(upstream_mapping)
    
    save_to_local_cache(local_cache)
    print(f"Successfully updated cache with {len(local_cache)} mappings.")
    print(f"Cache saved to: {MAPPING_CACHE_FILE}")

def main():
    parser = argparse.ArgumentParser(description="Manage the local PyPI-to-Conda name mapping cache.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force a refresh of the cache from conda-forge-metadata."
    )
    args = parser.parse_args()

    if not METADATA_AVAILABLE:
        print("Error: This script requires the 'conda-forge-metadata' package.", file=sys.stderr)
        print("Install it via the local-recipes pixi env (already pinned in pixi.toml).", file=sys.stderr)
        sys.exit(1)

    update_mapping_cache(force=args.force)

if __name__ == "__main__":
    main()
