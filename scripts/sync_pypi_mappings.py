#!/usr/bin/env python3
"""
Sync PyPI to conda-forge package name mappings from multiple sources.

This script fetches mappings from:
1. parselmouth (prefix-dev) - Primary, hourly updates
2. cf-graph-countyfair (regro) - Secondary, comprehensive
3. grayskull config (conda) - Tertiary, curated

Usage:
    python scripts/sync_pypi_mappings.py [--output-dir PATH]

The merged mappings are written to the output directory as JSON files
for fast lookup during recipe generation.

Caching:
    - Files tracked in git: custom.yaml, different_names.json, stats.json
    - Files generated locally (gitignored): unified.json, by_pypi_name.json, by_conda_name.json
    - Cache TTL: 7 days (configurable)
    - Use --force-refresh to bypass cache TTL
"""

import argparse
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# Try to import yaml, fall back to basic parsing if not available
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    print("Warning: PyYAML not installed. YAML sources will use fallback parsing.", file=sys.stderr)


SOURCES = {
    "parselmouth": {
        "url": "https://raw.githubusercontent.com/prefix-dev/parselmouth/main/files/mapping_as_grayskull.json",
        "format": "json",
        "priority": 1,
        "description": "prefix-dev parselmouth - hourly updates",
    },
    "cf_graph": {
        "url": "https://raw.githubusercontent.com/regro/cf-graph-countyfair/master/mappings/pypi/name_mapping.yaml",
        "format": "yaml",
        "priority": 2,
        "description": "regro cf-graph-countyfair - comprehensive",
    },
    "grayskull": {
        "url": "https://raw.githubusercontent.com/conda/grayskull/main/grayskull/strategy/config.yaml",
        "format": "yaml",
        "priority": 3,
        "description": "conda grayskull config - curated",
    },
}

# Files tracked in git (small, essential)
TRACKED_FILES = {"custom.yaml", "different_names.json", "stats.json"}

# Files generated locally but gitignored (large indices)
CACHE_FILES = {"unified.json", "by_pypi_name.json", "by_conda_name.json"}

# Default cache TTL in days
DEFAULT_CACHE_TTL_DAYS = 7

# Default output directory (relative to script location or repo root)
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent / ".claude" / "skills" / "conda-forge-expert" / "pypi_conda_mappings"


def fetch_url(url: str, timeout: int = 30) -> str:
    """Fetch content from a URL."""
    print(f"  Fetching: {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "conda-forge-expert-sync/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except urllib.error.URLError as e:
        print(f"  Error fetching {url}: {e}", file=sys.stderr)
        return ""


def parse_yaml_simple(content: str) -> Any:
    """Simple YAML parser for basic structures (fallback when PyYAML not available)."""
    # This is a very basic parser - only handles simple key-value and lists
    # For full YAML support, install PyYAML

    lines = content.split('\n')
    result = {}
    current_key = None
    current_list = None

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        # Handle list items
        if stripped.startswith('- '):
            if current_list is not None:
                # Try to parse as dict item
                item_content = stripped[2:].strip()
                if ':' in item_content:
                    key, _, value = item_content.partition(':')
                    if current_list and isinstance(current_list[-1], dict):
                        current_list[-1][key.strip()] = value.strip().strip('"\'')
                    else:
                        current_list.append({key.strip(): value.strip().strip('"\'')})
                else:
                    current_list.append(item_content)
            continue

        # Handle key: value
        if ':' in stripped:
            key, _, value = stripped.partition(':')
            key = key.strip()
            value = value.strip().strip('"\'')

            if not value:
                # This might be a list or nested dict
                result[key] = []
                current_list = result[key]
                current_key = key
            else:
                result[key] = value
                current_list = None

    return result


def parse_yaml(content: str) -> Any:
    """Parse YAML content."""
    if HAS_YAML:
        return yaml.safe_load(content)
    else:
        return parse_yaml_simple(content)


def normalize_name(name: str) -> str:
    """Normalize a package name (lowercase, replace special chars with hyphens)."""
    if not name:
        return ""
    return name.lower().replace("_", "-").replace(".", "-")


def fetch_parselmouth(content: str) -> dict[str, dict]:
    """Parse parselmouth JSON mapping."""
    mappings = {}
    try:
        data = json.loads(content)
        for pypi_name, info in data.items():
            if isinstance(info, dict):
                conda_name = info.get("conda_name", info.get("conda_forge", pypi_name))
                mappings[normalize_name(pypi_name)] = {
                    "pypi_name": pypi_name,
                    "conda_name": conda_name,
                    "import_name": info.get("import_name", ""),
                    "source": "parselmouth",
                }
            elif isinstance(info, str):
                # Simple string mapping
                mappings[normalize_name(pypi_name)] = {
                    "pypi_name": pypi_name,
                    "conda_name": info,
                    "import_name": "",
                    "source": "parselmouth",
                }
    except json.JSONDecodeError as e:
        print(f"  Error parsing parselmouth JSON: {e}", file=sys.stderr)

    return mappings


def fetch_cf_graph(content: str) -> dict[str, dict]:
    """Parse cf-graph YAML mapping."""
    mappings = {}
    try:
        data = parse_yaml(content)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    pypi_name = item.get("pypi_name", "")
                    conda_name = item.get("conda_name", "")
                    if pypi_name and conda_name:
                        mappings[normalize_name(pypi_name)] = {
                            "pypi_name": pypi_name,
                            "conda_name": conda_name,
                            "import_name": item.get("import_name", ""),
                            "source": "cf_graph",
                        }
    except Exception as e:
        print(f"  Error parsing cf-graph YAML: {e}", file=sys.stderr)

    return mappings


def fetch_grayskull(content: str) -> dict[str, dict]:
    """Parse grayskull config YAML mapping."""
    mappings = {}
    try:
        data = parse_yaml(content)
        if isinstance(data, dict):
            for pypi_name, info in data.items():
                if isinstance(info, dict):
                    conda_name = info.get("conda_forge", pypi_name)
                    if conda_name != pypi_name:  # Only include if names differ
                        mappings[normalize_name(pypi_name)] = {
                            "pypi_name": pypi_name,
                            "conda_name": conda_name,
                            "import_name": info.get("import_name", ""),
                            "source": "grayskull",
                        }
    except Exception as e:
        print(f"  Error parsing grayskull YAML: {e}", file=sys.stderr)

    return mappings


def load_custom_mappings(custom_file: Path) -> dict[str, dict]:
    """Load custom/override mappings from local YAML file."""
    mappings = {}
    if custom_file.exists():
        try:
            content = custom_file.read_text()
            data = parse_yaml(content)
            if isinstance(data, dict):
                for pypi_name, info in data.items():
                    if isinstance(info, dict):
                        mappings[normalize_name(pypi_name)] = {
                            "pypi_name": pypi_name,
                            "conda_name": info.get("conda_name", pypi_name),
                            "import_name": info.get("import_name", ""),
                            "source": "custom",
                            "reason": info.get("reason", ""),
                        }
            print(f"  Loaded {len(mappings)} custom mappings from {custom_file}")
        except Exception as e:
            print(f"  Error loading custom mappings: {e}", file=sys.stderr)
    return mappings


def merge_mappings(*mapping_dicts: dict[str, dict]) -> dict[str, dict]:
    """
    Merge multiple mapping dictionaries with priority.
    Earlier dictionaries have higher priority (won't be overwritten).
    """
    merged = {}
    for mappings in mapping_dicts:
        for key, value in mappings.items():
            if key not in merged:
                merged[key] = value
    return merged


def create_indices(mappings: dict[str, dict]) -> tuple[dict, dict, dict]:
    """Create lookup indices for fast access."""
    by_pypi = {}
    by_conda = {}
    different_names = {}

    for norm_name, info in mappings.items():
        pypi_name = info.get("pypi_name", "")
        conda_name = info.get("conda_name", "")

        if pypi_name:
            by_pypi[pypi_name] = info
            by_pypi[normalize_name(pypi_name)] = info

        if conda_name:
            by_conda[conda_name] = info
            by_conda[normalize_name(conda_name)] = info

        # Track where names actually differ
        if pypi_name and conda_name and normalize_name(pypi_name) != normalize_name(conda_name):
            different_names[normalize_name(pypi_name)] = info

    return by_pypi, by_conda, different_names


def check_cache_validity(output_dir: Path, ttl_days: int = DEFAULT_CACHE_TTL_DAYS) -> tuple[bool, str]:
    """
    Check if the cache is valid (exists and within TTL).

    Returns:
        (is_valid, reason) - True if cache is valid, False otherwise with reason
    """
    stats_file = output_dir / "stats.json"
    different_names_file = output_dir / "different_names.json"

    # Check if essential files exist
    if not stats_file.exists():
        return False, "stats.json not found"

    if not different_names_file.exists():
        return False, "different_names.json not found"

    # Check TTL
    try:
        stats = json.loads(stats_file.read_text())
        last_updated_str = stats.get("last_updated", "")
        if not last_updated_str:
            return False, "last_updated not found in stats.json"

        # Parse ISO format timestamp
        last_updated = datetime.fromisoformat(last_updated_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age = now - last_updated

        if age > timedelta(days=ttl_days):
            return False, f"cache expired ({age.days} days old, TTL is {ttl_days} days)"

        return True, f"cache valid ({age.days} days old)"
    except Exception as e:
        return False, f"error checking cache: {e}"


def fetch_parselmouth_direct() -> dict[str, dict]:
    """Fetch mappings directly from parselmouth (for on-demand use)."""
    print("Fetching mappings from parselmouth...")
    content = fetch_url(SOURCES["parselmouth"]["url"])
    if content:
        return fetch_parselmouth(content)
    return {}


def get_conda_name(pypi_name: str, output_dir: Path = DEFAULT_OUTPUT_DIR,
                   ttl_days: int = DEFAULT_CACHE_TTL_DAYS) -> str:
    """
    Get the conda-forge name for a PyPI package.

    This function can be imported and used directly for lookups.
    It will:
    1. Check custom.yaml first
    2. Check different_names.json cache
    3. If cache invalid/missing, fetch from parselmouth
    4. Fall back to using pypi_name as-is if no mapping found

    Args:
        pypi_name: The PyPI package name
        output_dir: Path to the mappings directory
        ttl_days: Cache TTL in days

    Returns:
        The conda-forge package name
    """
    normalized = normalize_name(pypi_name)

    # 1. Check custom.yaml
    custom_file = output_dir / "custom.yaml"
    custom = load_custom_mappings(custom_file)
    if normalized in custom:
        return custom[normalized]["conda_name"]

    # 2. Check different_names.json
    different_names_file = output_dir / "different_names.json"
    if different_names_file.exists():
        is_valid, reason = check_cache_validity(output_dir, ttl_days)
        if is_valid:
            try:
                different_names = json.loads(different_names_file.read_text())
                if normalized in different_names:
                    return different_names[normalized]["conda_name"]
                # If not in different_names, the name is the same
                return pypi_name
            except Exception:
                pass

    # 3. Fetch from parselmouth if cache invalid/missing
    print(f"Warning: Cache invalid or missing. Fetching from parselmouth...")
    mappings = fetch_parselmouth_direct()
    if normalized in mappings:
        return mappings[normalized]["conda_name"]

    # 4. Fall back to pypi_name
    return pypi_name


def main():
    parser = argparse.ArgumentParser(description="Sync PyPI to conda-forge package name mappings")
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for mapping files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--custom-file", "-c",
        type=Path,
        default=None,
        help="Path to custom mappings YAML file (default: OUTPUT_DIR/custom.yaml)",
    )
    parser.add_argument(
        "--force-refresh", "-f",
        action="store_true",
        help="Force refresh even if cache is valid",
    )
    parser.add_argument(
        "--check-cache",
        action="store_true",
        help="Only check cache validity, don't sync",
    )
    parser.add_argument(
        "--ttl-days",
        type=int,
        default=DEFAULT_CACHE_TTL_DAYS,
        help=f"Cache TTL in days (default: {DEFAULT_CACHE_TTL_DAYS})",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Minimal output",
    )
    args = parser.parse_args()

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    custom_file = args.custom_file or (output_dir / "custom.yaml")

    # Check cache validity
    is_valid, reason = check_cache_validity(output_dir, args.ttl_days)

    if args.check_cache:
        # Just report cache status and exit
        if is_valid:
            print(f"Cache is valid: {reason}")
            return 0
        else:
            print(f"Cache is invalid: {reason}")
            return 1

    if is_valid and not args.force_refresh:
        if not args.quiet:
            print(f"Cache is valid ({reason}). Use --force-refresh to update anyway.")
        return 0

    if not args.quiet:
        print("=" * 60)
        print("PyPI to conda-forge Package Name Mapping Sync")
        print("=" * 60)
        print(f"Output directory: {output_dir}")
        print(f"Cache status: {reason}")
        print()

    # Fetch from all sources
    all_mappings = []
    source_stats = {}

    # Priority 0: Custom overrides (highest priority)
    if not args.quiet:
        print("Loading custom mappings...")
    custom = load_custom_mappings(custom_file)
    all_mappings.append(custom)
    source_stats["custom"] = len(custom)

    # Priority 1: parselmouth
    if not args.quiet:
        print("\nFetching parselmouth mappings...")
    content = fetch_url(SOURCES["parselmouth"]["url"])
    if content:
        parselmouth = fetch_parselmouth(content)
        all_mappings.append(parselmouth)
        source_stats["parselmouth"] = len(parselmouth)
        if not args.quiet:
            print(f"  Found {len(parselmouth)} mappings")

    # Priority 2: cf-graph
    if not args.quiet:
        print("\nFetching cf-graph mappings...")
    content = fetch_url(SOURCES["cf_graph"]["url"])
    if content:
        cf_graph = fetch_cf_graph(content)
        all_mappings.append(cf_graph)
        source_stats["cf_graph"] = len(cf_graph)
        if not args.quiet:
            print(f"  Found {len(cf_graph)} mappings")

    # Priority 3: grayskull
    if not args.quiet:
        print("\nFetching grayskull mappings...")
    content = fetch_url(SOURCES["grayskull"]["url"])
    if content:
        grayskull = fetch_grayskull(content)
        all_mappings.append(grayskull)
        source_stats["grayskull"] = len(grayskull)
        if not args.quiet:
            print(f"  Found {len(grayskull)} mappings")

    # Merge all mappings
    if not args.quiet:
        print("\nMerging mappings (priority: custom > parselmouth > cf-graph > grayskull)...")
    merged = merge_mappings(*all_mappings)
    if not args.quiet:
        print(f"  Total unique mappings: {len(merged)}")

    # Create indices
    by_pypi, by_conda, different_names = create_indices(merged)

    # Write output files
    if not args.quiet:
        print("\nWriting output files...")

    # === TRACKED FILES (committed to git) ===

    # Different names only (most useful for recipe generation) - TRACKED
    different_file = output_dir / "different_names.json"
    different_file.write_text(json.dumps(different_names, indent=2, sort_keys=True))
    if not args.quiet:
        print(f"  [TRACKED] {different_file.name}: {len(different_names)} mappings where names differ")

    # Statistics - TRACKED
    stats = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_mappings": len(merged),
        "different_names_count": len(different_names),
        "sources": source_stats,
        "source_urls": {name: info["url"] for name, info in SOURCES.items()},
        "cache_ttl_days": args.ttl_days,
    }
    stats_file = output_dir / "stats.json"
    stats_file.write_text(json.dumps(stats, indent=2))
    if not args.quiet:
        print(f"  [TRACKED] {stats_file.name}: sync statistics")

    # === CACHE FILES (gitignored, generated locally) ===

    # Main unified mapping - CACHE
    unified_file = output_dir / "unified.json"
    unified_file.write_text(json.dumps(merged, indent=2, sort_keys=True))
    if not args.quiet:
        print(f"  [CACHE]   {unified_file.name}: {len(merged)} mappings")

    # PyPI name index - CACHE
    by_pypi_file = output_dir / "by_pypi_name.json"
    by_pypi_file.write_text(json.dumps(by_pypi, indent=2, sort_keys=True))
    if not args.quiet:
        print(f"  [CACHE]   {by_pypi_file.name}: {len(by_pypi)} entries")

    # Conda name index - CACHE
    by_conda_file = output_dir / "by_conda_name.json"
    by_conda_file.write_text(json.dumps(by_conda, indent=2, sort_keys=True))
    if not args.quiet:
        print(f"  [CACHE]   {by_conda_file.name}: {len(by_conda)} entries")

    # Create/update custom.yaml template if it doesn't exist - TRACKED
    if not custom_file.exists():
        custom_template = """# Custom PyPI to conda-forge package name mappings
# These override all other sources (highest priority)
#
# Format:
#   pypi-package-name:
#     conda_name: conda-package-name
#     import_name: python_import_name  # optional
#     reason: "Why this override exists"  # optional
#
# Example:
#   my-special-package:
#     conda_name: my_special_package
#     import_name: my_special_package
#     reason: "Custom conda-forge build"

# Add your custom mappings below:
"""
        custom_file.write_text(custom_template)
        if not args.quiet:
            print(f"  [TRACKED] {custom_file.name}: created template")

    if not args.quiet:
        print("\n" + "=" * 60)
        print("Sync complete!")
        print(f"Total mappings: {len(merged)}")
        print(f"Packages with different names: {len(different_names)}")
        print()
        print("Files tracked in git: custom.yaml, different_names.json, stats.json")
        print("Files cached locally: unified.json, by_pypi_name.json, by_conda_name.json")
        print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
