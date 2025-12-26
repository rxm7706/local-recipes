#!/usr/bin/env python3
"""
Check if recipe dependencies exist on conda-forge.

Usage:
    python dependency-checker.py recipes/my-package
    python dependency-checker.py recipes/my-package --verbose
    python dependency-checker.py recipes/my-package --suggest
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

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


# Common PyPI to conda-forge name mappings
PYPI_CONDA_MAPPINGS = {
    "pillow": "pillow",
    "pyyaml": "pyyaml",
    "scikit-learn": "scikit-learn",
    "scikit-image": "scikit-image",
    "opencv-python": "opencv",
    "opencv-python-headless": "opencv",
    "beautifulsoup4": "beautifulsoup4",
    "msgpack-python": "msgpack-python",
    "attrs": "attrs",
    "dateutil": "python-dateutil",
    "python-dateutil": "python-dateutil",
}


@dataclass
class DependencyCheck:
    """Result of checking a dependency."""
    name: str
    found: bool
    channel: Optional[str] = None
    versions: list[str] = None
    suggestion: Optional[str] = None


def normalize_package_name(name: str) -> str:
    """Normalize package name for comparison."""
    return name.lower().replace("_", "-")


def check_conda_forge(package_name: str) -> DependencyCheck:
    """Check if package exists on conda-forge."""
    if not REQUESTS_AVAILABLE:
        return DependencyCheck(name=package_name, found=False,
                               suggestion="Install requests to check online")

    normalized = normalize_package_name(package_name)

    # Check noarch first (most common for Python)
    for subdir in ["noarch", "linux-64"]:
        url = f"https://conda.anaconda.org/conda-forge/{subdir}/repodata.json"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Search in packages
            for pkg_file, info in data.get("packages", {}).items():
                if normalize_package_name(info["name"]) == normalized:
                    return DependencyCheck(
                        name=package_name,
                        found=True,
                        channel="conda-forge",
                        versions=[info["version"]]
                    )

            for pkg_file, info in data.get("packages.conda", {}).items():
                if normalize_package_name(info["name"]) == normalized:
                    return DependencyCheck(
                        name=package_name,
                        found=True,
                        channel="conda-forge",
                        versions=[info["version"]]
                    )

        except Exception:
            continue

    # Check if there's a known mapping
    mapped_name = PYPI_CONDA_MAPPINGS.get(normalized)
    if mapped_name and mapped_name != normalized:
        return DependencyCheck(
            name=package_name,
            found=False,
            suggestion=f"Try '{mapped_name}' instead of '{package_name}'"
        )

    return DependencyCheck(name=package_name, found=False)


def extract_dependencies_v1(recipe_path: Path) -> list[str]:
    """Extract dependencies from recipe.yaml."""
    if not YAML_AVAILABLE:
        print("Warning: PyYAML not available, using basic parsing")
        return extract_dependencies_basic(recipe_path)

    content = recipe_path.read_text()
    # Handle ${{ }} syntax by converting to safe placeholders
    content = re.sub(r'\$\{\{[^}]+\}\}', 'PLACEHOLDER', content)

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError:
        return extract_dependencies_basic(recipe_path)

    deps = set()
    requirements = data.get("requirements", {})

    for section in ["build", "host", "run"]:
        section_deps = requirements.get(section, [])
        if isinstance(section_deps, list):
            for dep in section_deps:
                if isinstance(dep, str):
                    # Extract package name (remove version spec)
                    name = dep.split()[0].split(">")[0].split("<")[0].split("=")[0]
                    if name and name != "PLACEHOLDER" and not name.startswith("$"):
                        deps.add(name)
                elif isinstance(dep, dict):
                    # Handle if/then/else
                    for key in ["then", "else"]:
                        val = dep.get(key)
                        if isinstance(val, str):
                            name = val.split()[0].split(">")[0].split("<")[0].split("=")[0]
                            if name and name != "PLACEHOLDER":
                                deps.add(name)
                        elif isinstance(val, list):
                            for v in val:
                                if isinstance(v, str):
                                    name = v.split()[0].split(">")[0].split("<")[0].split("=")[0]
                                    if name and name != "PLACEHOLDER":
                                        deps.add(name)

    return sorted(deps)


def extract_dependencies_legacy(recipe_path: Path) -> list[str]:
    """Extract dependencies from meta.yaml."""
    content = recipe_path.read_text()

    deps = set()

    # Find requirements section
    in_requirements = False
    in_section = False

    for line in content.split("\n"):
        stripped = line.strip()

        if stripped.startswith("requirements:"):
            in_requirements = True
            continue

        if in_requirements:
            if stripped and not stripped.startswith("#") and not stripped.startswith("-"):
                if not line.startswith(" "):
                    break  # End of requirements

            if stripped.startswith("- "):
                # Extract package name
                dep_line = stripped[2:].split("#")[0].strip()
                # Remove Jinja
                dep_line = re.sub(r'\{\{[^}]+\}\}', '', dep_line).strip()
                if dep_line:
                    name = dep_line.split()[0].split(">")[0].split("<")[0].split("=")[0]
                    if name:
                        deps.add(name)

    return sorted(deps)


def extract_dependencies_basic(recipe_path: Path) -> list[str]:
    """Basic dependency extraction without YAML parser."""
    content = recipe_path.read_text()
    deps = set()

    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- "):
            # Clean up the line
            dep_line = stripped[2:].split("#")[0].strip()
            dep_line = re.sub(r'[\$\{].*?[\}]', '', dep_line).strip()
            dep_line = re.sub(r'\{\{.*?\}\}', '', dep_line).strip()
            if dep_line:
                name = dep_line.split()[0].split(">")[0].split("<")[0].split("=")[0]
                # Filter out likely not-packages
                if name and len(name) > 1 and not name.startswith(("if", "then", "else")):
                    deps.add(name)

    return sorted(deps)


def check_recipe(recipe_path: Path, verbose: bool = False, suggest: bool = False) -> tuple[list, list]:
    """Check all dependencies in a recipe."""
    # Find recipe file
    if recipe_path.is_dir():
        if (recipe_path / "recipe.yaml").exists():
            recipe_file = recipe_path / "recipe.yaml"
            is_v1 = True
        elif (recipe_path / "meta.yaml").exists():
            recipe_file = recipe_path / "meta.yaml"
            is_v1 = False
        else:
            raise FileNotFoundError(f"No recipe file in {recipe_path}")
    else:
        recipe_file = recipe_path
        is_v1 = recipe_file.name == "recipe.yaml"

    # Extract dependencies
    if is_v1:
        deps = extract_dependencies_v1(recipe_file)
    else:
        deps = extract_dependencies_legacy(recipe_file)

    # Filter out special packages
    skip_packages = {
        "python", "pip", "setuptools", "wheel",
        "compiler", "stdlib",  # Jinja functions
    }
    deps = [d for d in deps if d.lower() not in skip_packages]

    if verbose:
        print(f"Found {len(deps)} dependencies to check")

    # Check each dependency
    found = []
    missing = []

    for dep in deps:
        if verbose:
            print(f"Checking {dep}...", end=" ")

        result = check_conda_forge(dep)

        if result.found:
            found.append(result)
            if verbose:
                print(f"OK ({result.channel})")
        else:
            missing.append(result)
            if verbose:
                print("NOT FOUND")
                if suggest and result.suggestion:
                    print(f"  Suggestion: {result.suggestion}")

    return found, missing


def main():
    parser = argparse.ArgumentParser(
        description="Check if recipe dependencies exist on conda-forge"
    )
    parser.add_argument("recipe", type=Path,
                        help="Recipe path (directory or file)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose output")
    parser.add_argument("--suggest", "-s", action="store_true",
                        help="Suggest fixes for missing dependencies")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")

    args = parser.parse_args()

    try:
        found, missing = check_recipe(args.recipe, args.verbose, args.suggest)

        if args.json:
            print(json.dumps({
                "found": [{"name": r.name, "channel": r.channel} for r in found],
                "missing": [{"name": r.name, "suggestion": r.suggestion} for r in missing]
            }, indent=2))
        else:
            print(f"\n{'='*50}")
            print(f"Dependencies found: {len(found)}")
            print(f"Dependencies missing: {len(missing)}")

            if missing:
                print(f"\nMissing packages:")
                for dep in missing:
                    msg = f"  - {dep.name}"
                    if dep.suggestion:
                        msg += f" ({dep.suggestion})"
                    print(msg)

            if missing:
                print(f"\n[FAIL] {len(missing)} dependencies not found on conda-forge")
                sys.exit(1)
            else:
                print(f"\n[OK] All dependencies found")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
