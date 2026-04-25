#!/usr/bin/env python3
"""
Programmatic Recipe Editor for conda-forge recipes.

This script uses ruamel.yaml to safely modify recipe files while preserving
comments and formatting. It supports actions like updating values, adding to
lists, and automatically calculating source hashes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

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

def get_nested_item(data: Dict, path: str):
    """Access a nested dictionary item using a dot-separated path."""
    keys = path.split('.')
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key)
        elif isinstance(data, list):
            try:
                data = data[int(key)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return data

def set_nested_item(data: Dict, path: str, value: Any):
    """Set a nested dictionary item using a dot-separated path."""
    keys = path.split('.')
    d = data
    for key in keys[:-1]:
        if key.isdigit() and isinstance(d, list):
            d = d[int(key)]
        else:
            d = d.setdefault(key, {})
    d[keys[-1]] = value

def calculate_sha256_from_url(url: str) -> str:
    """Download a file and calculate its SHA256 hash."""
    if not REQUESTS_AVAILABLE:
        raise ImportError("The 'requests' library is required for hash calculation.")
    
    print(f"  Downloading {url} to calculate SHA256...")
    try:
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        
        hasher = hashlib.sha256()
        for chunk in response.iter_content(chunk_size=8192):
            hasher.update(chunk)
            
        sha256 = hasher.hexdigest()
        print(f"  Calculated SHA256: {sha256}")
        return sha256
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to download source for hash calculation: {e}") from e

def _validate_recipe_path(recipe_path: Path) -> None:
    """Raise ValueError if the path is not a YAML file (prevents obvious misuse at CLI boundary)."""
    if recipe_path.suffix not in (".yaml", ".yml"):
        raise ValueError(f"Recipe path must be a .yaml/.yml file, got: {recipe_path}")


def execute_actions(recipe_path: Path, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Execute a list of modification actions on a recipe file."""
    if not RUAMEL_AVAILABLE:
        return {"success": False, "error": "ruamel.yaml is not installed."}

    try:
        _validate_recipe_path(recipe_path)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)

    try:
        with open(recipe_path) as f:
            data = yaml.load(f)
    except Exception as e:
        return {"success": False, "error": f"Failed to read or parse recipe: {e}"}

    for i, action in enumerate(actions):
        action_type = action.get("action")
        path = action.get("path")
        
        try:
            if action_type == "update":
                set_nested_item(data, path, action["value"])
            
            elif action_type == "add_to_list":
                item = get_nested_item(data, path)
                if isinstance(item, list):
                    item.append(action["value"])
                else:
                    raise TypeError(f"Target for 'add_to_list' is not a list at path: {path}")

            elif action_type == "remove_from_list":
                item = get_nested_item(data, path)
                if isinstance(item, list):
                    item.remove(action["value"])
                else:
                    raise TypeError(f"Target for 'remove_from_list' is not a list at path: {path}")

            elif action_type == "calculate_hash":
                source_block = get_nested_item(data, path)
                if not isinstance(source_block, dict) or "url" not in source_block:
                    raise ValueError(f"Invalid source block at path: {path}")

                url = str(source_block["url"])
                # Resolve rattler-build context variables (e.g. ${{ version }}) before downloading
                context = data.get("context", {})
                for var_name, var_value in context.items():
                    url = url.replace(f"${{{{ {var_name} }}}}", str(var_value))

                sha256 = calculate_sha256_from_url(url)
                source_block["sha256"] = sha256
            
            else:
                raise ValueError(f"Unknown action type: {action_type}")

        except (KeyError, ValueError, TypeError, RuntimeError) as e:
            return {"success": False, "error": f"Action {i} failed: {e}"}

    try:
        with open(recipe_path, "w") as f:
            yaml.dump(data, f)
    except Exception as e:
        return {"success": False, "error": f"Failed to write updated recipe: {e}"}
        
    return {"success": True, "message": f"Successfully applied {len(actions)} actions to {recipe_path.name}."}

def main():
    parser = argparse.ArgumentParser(description="Programmatically edit conda recipes.")
    parser.add_argument("recipe_path", type=Path, help="Path to the recipe file.")
    parser.add_argument(
        "actions_json",
        type=str,
        help="A JSON string representing a list of actions to perform."
    )
    
    args = parser.parse_args()

    try:
        actions = json.loads(args.actions_json)
        if not isinstance(actions, list):
            raise ValueError("Actions JSON must be a list of objects.")
    except (json.JSONDecodeError, ValueError) as e:
        print(json.dumps({"success": False, "error": f"Invalid actions JSON: {e}"}))
        sys.exit(1)

    result = execute_actions(args.recipe_path, actions)
    print(json.dumps(result, indent=2))
    
    sys.exit(0 if result["success"] else 1)

if __name__ == "__main__":
    main()
