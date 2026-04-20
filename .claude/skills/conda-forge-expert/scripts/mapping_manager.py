#!/usr/bin/env python3
"""
PyPI-to-Conda Name Mapping Manager.

This script fetches the canonical package name mapping from the Grayskull
repository and maintains a local cache for fast lookups.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# The location of our local data cache
DATA_DIR = Path(__file__).parent.parent.parent / "data"
MAPPING_CACHE_FILE = DATA_DIR / "pypi_conda_map.json"

# The canonical source of truth from the Grayskull project
GRAYSKULL_MAPPING_URL = "https://raw.githubusercontent.com/conda/grayskull/main/src/grayskull/pypi/pypi_name_mapping.yaml"

def fetch_grayskull_mapping() -> dict:
    """Downloads and parses the YAML mapping file from Grayskull's GitHub."""
    if not REQUESTS_AVAILABLE:
        raise ImportError("'requests' is required to fetch the mapping.")
    if not YAML_AVAILABLE:
        raise ImportError("'PyYAML' or 'ruamel.yaml' is required to parse the mapping.")

    print(f"Fetching latest mapping from {GRAYSKULL_MAPPING_URL}...")
    try:
        response = requests.get(GRAYSKULL_MAPPING_URL, timeout=30)
        response.raise_for_status()
        # The Grayskull file has a structure like:
        # pypi_name:
        #   conda_name: the_conda_name
        raw_mapping = yaml.safe_load(response.text)
        
        # We want to flatten this to a simple {pypi_name: conda_name} dict
        processed_mapping = {}
        for pypi_name, details in raw_mapping.items():
            if "conda_name" in details:
                processed_mapping[pypi_name.lower()] = details["conda_name"]
        return processed_mapping

    except requests.RequestException as e:
        print(f"Error: Failed to download mapping file: {e}", file=sys.stderr)
        return {}
    except yaml.YAMLError as e:
        print(f"Error: Failed to parse YAML from mapping file: {e}", file=sys.stderr)
        return {}

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

    grayskull_mapping = fetch_grayskull_mapping()
    if not grayskull_mapping:
        print("Could not fetch upstream mapping. Aborting update.", file=sys.stderr)
        return

    # Merge the new mapping into the local cache. Grayskull is the authority.
    # We can also add custom/manual mappings here in the future if needed.
    local_cache.update(grayskull_mapping)
    
    save_to_local_cache(local_cache)
    print(f"Successfully updated cache with {len(local_cache)} mappings.")
    print(f"Cache saved to: {MAPPING_CACHE_FILE}")

def main():
    parser = argparse.ArgumentParser(description="Manage the local PyPI-to-Conda name mapping cache.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force a refresh of the cache from the upstream Grayskull repository."
    )
    args = parser.parse_args()

    if not (REQUESTS_AVAILABLE and YAML_AVAILABLE):
        print("Error: This script requires 'requests' and 'PyYAML'.", file=sys.stderr)
        print("Please install them into your environment.", file=sys.stderr)
        sys.exit(1)

    update_mapping_cache(force=args.force)

if __name__ == "__main__":
    main()
