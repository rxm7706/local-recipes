#!/usr/bin/env python3
"""
Recipe Optimization Linter for conda-forge recipes.

This script goes beyond basic validation and checks for common anti-patterns,
suggesting improvements related to dependency placement, redundant selectors,
and other conda-forge best practices.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, NamedTuple

try:
    from ruamel.yaml import YAML
    RUAMEL_AVAILABLE = True
except ImportError:
    YAML = None  # type: ignore[assignment,misc]
    RUAMEL_AVAILABLE = False

class OptimizationSuggestion(NamedTuple):
    """A single suggestion for improving a recipe."""
    code: str
    message: str
    suggestion: str
    confidence: float # A score from 0.0 to 1.0

# A list of packages that are typically test or dev dependencies
# and should not be in the 'run' requirements.
DEV_DEPENDENCIES = {
    "pytest", "pytest-cov", "pytest-mock", "black", "ruff", "mypy",
    "flake8", "pre-commit", "tox", "nox", "twine", "wheel", "build"
}

def analyze_dependencies(data: Dict) -> List[OptimizationSuggestion]:
    """Analyzes dependency sections for common issues."""
    suggestions = []
    
    run_reqs = data.get("requirements", {}).get("run", [])
    if not run_reqs:
        return suggestions

    # Flatten the list to handle if/then selectors
    flat_run_reqs = []
    for item in run_reqs:
        if isinstance(item, str):
            flat_run_reqs.append(item)
        elif isinstance(item, dict):
            if "then" in item and isinstance(item["then"], str): flat_run_reqs.append(item["then"])
            if "else" in item and isinstance(item["else"], str): flat_run_reqs.append(item["else"])

    for req in flat_run_reqs:
        pkg_name = req.split()[0]
        if pkg_name in DEV_DEPENDENCIES:
            suggestions.append(OptimizationSuggestion(
                code="DEP-001",
                message=f"'{pkg_name}' is a development dependency found in the 'run' requirements.",
                suggestion=f"Consider moving '{pkg_name}' to the 'test' requirements section.",
                confidence=0.95
            ))
            
    return suggestions

def analyze_build_script(recipe_dir: Path) -> List[OptimizationSuggestion]:
    """Analyzes build scripts (e.g., build.sh) for anti-patterns."""
    suggestions = []
    build_script_path = recipe_dir / "build.sh"
    if not build_script_path.exists():
        return suggestions
        
    content = build_script_path.read_text()
    
    if "sudo " in content:
        suggestions.append(OptimizationSuggestion(
            code="SCRIPT-001",
            message="'sudo' found in build.sh. Builds must not require root privileges.",
            suggestion="Remove 'sudo' and ensure all operations are performed with user permissions.",
            confidence=1.0
        ))
        
    if "pip install --upgrade" in content:
        suggestions.append(OptimizationSuggestion(
            code="SCRIPT-002",
            message="'pip install --upgrade' found. This can lead to non-reproducible builds.",
            suggestion="Remove the '--upgrade' flag. Pin dependencies in the recipe instead.",
            confidence=0.9
        ))

    return suggestions

def analyze_selectors(data: Dict) -> List[OptimizationSuggestion]:
    """Analyzes skip conditions and platform selectors for redundancy."""
    suggestions = []

    build_section = data.get("build", {}) or {}
    skip_value = build_section.get("skip", None)
    if skip_value is None:
        return suggestions

    sole_platform: str | None = None

    # recipe.yaml v1: skip is a list of condition strings like ['not linux', 'not win']
    if isinstance(skip_value, list):
        not_conditions = [
            str(s).strip() for s in skip_value
            if re.match(r"^not\s+\w+$", str(s).strip())
        ]
        # Single "not X" → recipe only targets platform X
        if len(not_conditions) == 1:
            sole_platform = not_conditions[0].split()[-1]

    if sole_platform:
        suggestions.append(OptimizationSuggestion(
            code="SEL-001",
            message=f"Recipe is restricted to '{sole_platform}'. if/then conditions scoped to this platform may be redundant.",
            suggestion=f"Review if/then conditionals already limited to '{sole_platform}' — they may be removable.",
            confidence=0.7
        ))

    # CFEP-25: noarch: python packages must pin python_min
    noarch = build_section.get("noarch", None)
    if noarch == "python":
        context = data.get("context", {}) or {}
        run_reqs = data.get("requirements", {}).get("run", [])
        has_python_pin = any(
            isinstance(r, str) and "python_min" in r
            for r in run_reqs
        )
        has_python_min_ctx = "python_min" in context
        if not has_python_pin and not has_python_min_ctx:
            suggestions.append(OptimizationSuggestion(
                code="SEL-002",
                message="noarch: python recipe does not use 'python_min' context variable (CFEP-25).",
                suggestion=(
                    "Add 'python_min: \"3.9\"' to context, then use "
                    "'python >=${{ python_min }}' in run requirements."
                ),
                confidence=0.9
            ))

    return suggestions

def optimize_recipe(recipe_path: Path) -> List[OptimizationSuggestion]:
    """
    Runs all optimization checks on a given recipe file.
    """
    if not RUAMEL_AVAILABLE:
        return [OptimizationSuggestion("OPT-000", "ruamel.yaml not found.", "Install ruamel.yaml.", 1.0)]
    assert YAML is not None

    yaml = YAML()
    try:
        with open(recipe_path) as f:
            data = yaml.load(f)
    except Exception:
        return [] # If we can't parse it, we can't optimize it.

    all_suggestions = []
    all_suggestions.extend(analyze_dependencies(data))
    all_suggestions.extend(analyze_build_script(recipe_path.parent))
    all_suggestions.extend(analyze_selectors(data))
    
    return all_suggestions

def main():
    parser = argparse.ArgumentParser(description="Lint a conda recipe for optimizations and best practices.")
    parser.add_argument("recipe_path", type=Path, help="Path to the recipe file (meta.yaml or recipe.yaml).")
    
    args = parser.parse_args()

    if not args.recipe_path.exists():
        print(json.dumps({"success": False, "error": f"File not found: {args.recipe_path}"}))
        sys.exit(1)

    suggestions = optimize_recipe(args.recipe_path)
    
    output = {
        "success": True,
        "suggestions_found": len(suggestions),
        "suggestions": [s._asdict() for s in suggestions]
    }
    
    print(json.dumps(output, indent=2))
    
    # Exit with a non-zero code if suggestions are found, useful for CI
    sys.exit(1 if suggestions else 0)

if __name__ == "__main__":
    main()
