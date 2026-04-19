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
from typing import Dict, Any, List, NamedTuple

try:
    from ruamel.yaml import YAML
    RUAMEL_AVAILABLE = True
except ImportError:
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
    """Analyzes selectors for redundancy."""
    suggestions = []
    
    # Check for redundant selectors if the recipe is skipped on all but one platform
    build_section = data.get("build", {})
    skip_line = build_section.get("skip", "")
    
    # Example: skip: true  # [not linux]
    match = re.search(r"skip:\s*true\s*#\s*\[\s*not\s*(\w+)\s*\]", str(build_section))
    if match:
        sole_platform = match.group(1)
        
        # Now search for selectors that are redundant
        # This requires walking the whole data structure, which is complex.
        # For now, we'll just add a note that this is a potential area.
        # A full implementation would use ruamel.yaml's AST capabilities.
        suggestions.append(OptimizationSuggestion(
            code="SEL-001",
            message=f"Recipe appears to be only for '{sole_platform}'. Selectors for this platform may be redundant.",
            suggestion=f"Review any '# [{sole_platform}]' selectors to see if they can be removed.",
            confidence=0.7
        ))
        
    return suggestions

def optimize_recipe(recipe_path: Path) -> List[OptimizationSuggestion]:
    """
    Runs all optimization checks on a given recipe file.
    """
    if not RUAMEL_AVAILABLE:
        return [OptimizationSuggestion("OPT-000", "ruamel.yaml not found.", "Install ruamel.yaml.", 1.0)]

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
