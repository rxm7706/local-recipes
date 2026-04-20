#!/usr/bin/env python3
"""
Automated Recipe Updater ("Autotick" Bot).

This script checks for new upstream versions of a package on PyPI and, if found,
updates the recipe file by leveraging the existing recipe_editor.py script.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

try:
    from ruamel.yaml import YAML
    RUAMEL_AVAILABLE = True
except ImportError:
    RUAMEL_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from packaging.version import Version as PkgVersion
    PACKAGING_AVAILABLE = True
except ImportError:
    PACKAGING_AVAILABLE = False

# Path to the recipe editor script
RECIPE_EDITOR_SCRIPT = Path(__file__).parent / "recipe_editor.py"

def get_latest_pypi_version(package_name: str) -> str | None:
    """Queries the PyPI API to get the latest version of a package."""
    if not REQUESTS_AVAILABLE:
        raise ImportError("'requests' is required to check for new versions.")
    
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("info", {}).get("version")
    except requests.RequestException:
        return None

def get_current_recipe_info(recipe_path: Path) -> Dict[str, Any]:
    """Parses a recipe to get its current name and version."""
    if not RUAMEL_AVAILABLE:
        raise ImportError("'ruamel.yaml' is required to parse the recipe.")
        
    yaml = YAML()
    with open(recipe_path) as f:
        data = yaml.load(f)
    
    context = data.get("context", {})
    package_name = context.get("name")
    current_version = context.get("version")
    
    if not package_name or not current_version:
        raise ValueError("Could not determine package name and version from recipe context.")
        
    return {"name": package_name, "version": str(current_version)}

def update_recipe(recipe_path: Path, dry_run: bool = False) -> Dict[str, Any]:
    """
    Checks for a new version and, if found, constructs and executes the
    necessary actions to update the recipe file.
    """
    try:
        recipe_info = get_current_recipe_info(recipe_path)
        package_name = recipe_info["name"]
        current_version = recipe_info["version"]
        
        print(f"Checking for updates to '{package_name}' (current version: {current_version})...")
        
        latest_version = get_latest_pypi_version(package_name)
        
        if not latest_version:
            return {"success": False, "message": f"Could not fetch latest version for '{package_name}' from PyPI."}

        if PACKAGING_AVAILABLE:
            try:
                if PkgVersion(latest_version) <= PkgVersion(current_version):
                    return {"success": True, "updated": False, "message": "Recipe is already up-to-date."}
            except Exception:
                if latest_version == current_version:
                    return {"success": True, "updated": False, "message": "Recipe is already up-to-date."}
        elif latest_version == current_version:
            return {"success": True, "updated": False, "message": "Recipe is already up-to-date."}

        print(f"New version found: {latest_version}. Preparing update...")

        # Construct the list of actions for the recipe editor
        actions = [
            {"action": "update", "path": "context.version", "value": latest_version},
            {"action": "update", "path": "build.number", "value": 0},
            {"action": "calculate_hash", "path": "source.0"}
        ]
        
        if dry_run:
            return {
                "success": True,
                "updated": True,
                "dry_run": True,
                "actions": actions,
                "message": f"Dry run: Would update recipe to version {latest_version}."
            }

        # Call the recipe_editor script as a subprocess
        import subprocess
        cmd = ["python", str(RECIPE_EDITOR_SCRIPT), str(recipe_path), json.dumps(actions)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            return {"success": False, "error": "recipe_editor.py failed.", "details": result.stderr}
            
        return {"success": True, "updated": True, "new_version": latest_version, "message": "Recipe updated successfully."}

    except (ImportError, ValueError, FileNotFoundError) as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred: {e}"}

def main():
    parser = argparse.ArgumentParser(description="Automatically update a conda recipe to the latest version from PyPI.")
    parser.add_argument("recipe_path", type=Path, help="Path to the recipe file (e.g., recipes/numpy/recipe.yaml).")
    parser.add_argument("--dry-run", action="store_true", help="Check for updates but do not modify the file.")
    
    args = parser.parse_args()

    result = update_recipe(args.recipe_path, dry_run=args.dry_run)
    
    print(json.dumps(result, indent=2))
    
    sys.exit(0 if result["success"] else 1)

if __name__ == "__main__":
    main()
