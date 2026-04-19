#!/usr/bin/env python3
"""
PyPI-to-Conda Name Resolver.

Implements a tiered, cache-first strategy to find the correct conda-forge
package name for a given PyPI package name.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Path to the local mapping cache
DATA_DIR = Path(__file__).parent.parent.parent / "data"
MAPPING_CACHE_FILE = DATA_DIR / "pypi_conda_map.json"

# Path to the local repodata cache (used as a fallback)
REPODATA_DIR = Path(__file__).parent.parent.parent / "data" / "repodata"

def normalize_name(name: str) -> str:
    """Normalize a package name for consistent lookups."""
    return name.lower().replace("_", "-")

def search_local_cache(pypi_name: str) -> str | None:
    """Tier 1: Search the fast, local JSON cache."""
    if not MAPPING_CACHE_FILE.exists():
        return None
    
    with open(MAPPING_CACHE_FILE) as f:
        cache = json.load(f)
        
    return cache.get(normalize_name(pypi_name))

def search_repodata_fallback(pypi_name: str) -> str | None:
    """Tier 2: Search the repodata.json files directly.
    
    This is the ultimate source of truth but is slower. It checks for common
    naming variations.
    """
    if not REPODATA_DIR.exists():
        return None

    normalized = normalize_name(pypi_name)
    search_variations = [
        normalized,
        f"py-{normalized}",
        f"python-{normalized}",
    ]

    # We only need to check one repodata file, as package names are consistent
    # across subdirs. noarch is a good candidate.
    repodata_file = REPODATA_DIR / "conda-forge" / "noarch" / "repodata.json"
    if not repodata_file.exists():
        return None

    with open(repodata_file) as f:
        repodata = json.load(f)
    
    # Create a set of all package names for fast lookups
    package_names = {normalize_name(info["name"]) for info in repodata.get("packages", {}).values()}
    
    for variation in search_variations:
        if variation in package_names:
            return variation
            
    return None

def resolve_name(pypi_name: str) -> dict:
    """
    Resolves a PyPI package name to a conda-forge name using a tiered strategy.
    """
    # Tier 1: Local Cache
    conda_name = search_local_cache(pypi_name)
    if conda_name:
        return {
            "pypi_name": pypi_name,
            "conda_name": conda_name,
            "source": "local-cache",
            "success": True,
        }

    # Tier 2: Repodata Fallback
    conda_name = search_repodata_fallback(pypi_name)
    if conda_name:
        # Let's cache this result for next time
        if MAPPING_CACHE_FILE.exists():
            with open(MAPPING_CACHE_FILE, "r+") as f:
                cache = json.load(f)
                cache[normalize_name(pypi_name)] = conda_name
                f.seek(0)
                json.dump(cache, f, indent=2)

        return {
            "pypi_name": pypi_name,
            "conda_name": conda_name,
            "source": "repodata-fallback",
            "success": True,
        }

    # All tiers failed
    return {
        "pypi_name": pypi_name,
        "conda_name": None,
        "source": "not-found",
        "success": False,
        "message": f"Could not resolve '{pypi_name}'. Please check the name or add a manual mapping.",
    }

def main():
    parser = argparse.ArgumentParser(description="Resolve a PyPI package name to its conda-forge equivalent.")
    parser.add_argument("pypi_name", help="The PyPI package name to resolve.")
    
    args = parser.parse_args()

    # First, ensure the cache exists. If not, prompt the user to create it.
    if not MAPPING_CACHE_FILE.exists():
        print(json.dumps({
            "success": False,
            "error": "Mapping cache not found.",
            "fix": "Please run 'pixi run update-mapping-cache' to build the local cache."
        }))
        sys.exit(1)

    result = resolve_name(args.pypi_name)
    print(json.dumps(result, indent=2))
    
    sys.exit(0 if result["success"] else 1)

if __name__ == "__main__":
    main()
