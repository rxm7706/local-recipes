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

# Virtual packages and special names that should never trigger PIN-001.
_VIRTUAL_PACKAGES = {"__osx", "__glibc", "__linux", "__unix", "__cuda", "__archspec"}


def _flatten_reqs(items: list | None) -> List[str]:
    """Recursively flatten requirement lists that may contain if/then/else dicts."""
    result: List[str] = []
    for item in (items or []):
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            for key in ("then", "else"):
                val = item.get(key)
                if isinstance(val, str):
                    result.append(val)
                elif isinstance(val, list):
                    result.extend(_flatten_reqs(val))
    return result


def analyze_dependencies(data: Dict) -> List[OptimizationSuggestion]:
    """Analyzes dependency sections for common issues."""
    suggestions = []

    run_reqs = data.get("requirements", {}).get("run", [])
    if not run_reqs:
        return suggestions

    for req in _flatten_reqs(run_reqs):
        pkg_name = req.split()[0]
        if pkg_name in DEV_DEPENDENCIES:
            suggestions.append(OptimizationSuggestion(
                code="DEP-001",
                message=f"'{pkg_name}' is a development dependency found in the 'run' requirements.",
                suggestion=f"Consider moving '{pkg_name}' to the 'test' requirements section.",
                confidence=0.95
            ))

    return suggestions


def analyze_noarch_python_constraints(data: Dict) -> List[OptimizationSuggestion]:
    """Check noarch:python recipes for Python constraint best practices (DEP-002)."""
    suggestions = []
    build = data.get("build", {}) or {}
    if build.get("noarch") != "python":
        return suggestions

    reqs = data.get("requirements", {}) or {}
    flat_run = _flatten_reqs(reqs.get("run", []))
    flat_constrained = _flatten_reqs(reqs.get("run_constrained", []))

    # Detect Python entry in run that carries an upper bound.
    python_run_with_upper: str | None = None
    for req in flat_run:
        parts = req.strip().split()
        if not parts or parts[0].lower() != "python":
            continue
        if len(parts) > 1 and "<" in " ".join(parts[1:]):
            python_run_with_upper = req
            break

    # Check whether Python already appears in run_constrained.
    python_in_constrained = any(
        c.strip().split()[0].lower() == "python"
        for c in flat_constrained
        if c.strip()
    )

    if python_run_with_upper and not python_in_constrained:
        suggestions.append(OptimizationSuggestion(
            code="DEP-002",
            message=f"noarch:python recipe pins Python upper bound in run: '{python_run_with_upper}'.",
            suggestion=(
                "Move the upper bound to run_constrained (e.g. 'python <X') and keep only "
                "the lower bound in run. Hard upper bounds in run block installation with "
                "newer Python; run_constrained is a softer constraint that warns without blocking."
            ),
            confidence=0.85,
        ))

    return suggestions


def analyze_pinning(data: Dict) -> List[OptimizationSuggestion]:
    """Detect over-pinned (exact ==) run dependencies (PIN-001)."""
    suggestions = []

    run_reqs = data.get("requirements", {}).get("run", [])

    for req in _flatten_reqs(run_reqs):
        req = req.strip()
        # Skip template expressions — version is resolved at build time.
        if not req or "${{" in req or "{{" in req:
            continue
        parts = req.split()
        if len(parts) < 2:
            continue
        pkg = parts[0]
        if pkg.lower() == "python" or pkg.lower() in _VIRTUAL_PACKAGES:
            continue
        constraint = " ".join(parts[1:])
        # Flag == (exact match) pins; allow >= or ~= or *.
        if re.search(r"(?<![<>!])={2}", constraint):
            version_m = re.search(r"==\s*([^\s,]+)", constraint)
            version = version_m.group(1) if version_m else "X.Y.Z"
            suggestions.append(OptimizationSuggestion(
                code="PIN-001",
                message=f"Run dependency '{pkg}' is pinned to an exact version: '{req}'.",
                suggestion=(
                    f"Prefer '>={version}' or '>={version},<next_major'. "
                    "Exact pins block security updates and make co-installation harder."
                ),
                confidence=0.9,
            ))

    return suggestions


def analyze_about_section(data: Dict) -> List[OptimizationSuggestion]:
    """Check about section for conda-forge required fields (ABT-001)."""
    suggestions = []
    about = data.get("about", {}) or {}

    if "license_file" not in about:
        suggestions.append(OptimizationSuggestion(
            code="ABT-001",
            message="Missing 'license_file' in about section.",
            suggestion=(
                "Add 'license_file: LICENSE' (adjust filename to match the repo: "
                "LICENSE.md, LICENSE.txt, etc.). "
                "conda-forge requires all packages to bundle the license file."
            ),
            confidence=0.95,
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
    """Analyzes platform selectors (SEL-001) and CFEP-25 python_min compliance (SEL-002)."""
    suggestions = []

    build_section = data.get("build", {}) or {}

    # --- SEL-001: Redundant platform skip conditions ---
    skip_value = build_section.get("skip", None)
    if skip_value is not None:
        sole_platform: str | None = None
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
                confidence=0.7,
            ))

    # --- SEL-002: CFEP-25 python_min for noarch:python ---
    # Checks all three required locations: context, host, run, and tests python block.
    # Note: SEL-001 early-return was removed so this check runs even when skip is absent.
    if build_section.get("noarch") == "python":
        context = data.get("context", {}) or {}
        reqs = data.get("requirements", {}) or {}
        flat_run = _flatten_reqs(reqs.get("run", []))
        flat_host = _flatten_reqs(reqs.get("host", []))

        has_python_min_ctx = "python_min" in context
        has_python_min_run = any("python_min" in r for r in flat_run if isinstance(r, str))
        has_python_min_host = any("python_min" in r for r in flat_host if isinstance(r, str))

        # v1 recipes: tests[n].python.python_version anchors CI to python_min
        tests = data.get("tests", []) or []
        has_python_version_test = any(
            isinstance(t, dict)
            and isinstance(t.get("python"), dict)
            and "python_version" in t["python"]
            for t in tests
        )

        if not has_python_min_ctx and not has_python_min_run:
            suggestions.append(OptimizationSuggestion(
                code="SEL-002",
                message="noarch: python recipe does not use 'python_min' context variable (CFEP-25).",
                suggestion=(
                    "Add 'python_min: \"3.10\"' to context (current conda-forge floor), then use "
                    "'python >=${{ python_min }}' in run requirements."
                ),
                confidence=0.9,
            ))
        else:
            # python_min is in use — check for incomplete CFEP-25 triad coverage
            missing: List[str] = []
            if not has_python_min_host:
                missing.append("host (python ${{ python_min }}.*)")
            if not has_python_version_test:
                missing.append("tests python block (python_version: ${{ python_min }}.*)")
            if missing:
                suggestions.append(OptimizationSuggestion(
                    code="SEL-002",
                    message=(
                        "Incomplete CFEP-25 python_min coverage: "
                        f"missing from {', '.join(missing)}."
                    ),
                    suggestion=(
                        "Full CFEP-25 triad: "
                        "(1) context: python_min: '3.10', "
                        "(2) host: python ${{ python_min }}.*, "
                        "(3) run: python >=${{ python_min }}, "
                        "(4) tests python block: python_version: ${{ python_min }}.*"
                    ),
                    confidence=0.75,
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
    all_suggestions.extend(analyze_noarch_python_constraints(data))
    all_suggestions.extend(analyze_pinning(data))
    all_suggestions.extend(analyze_about_section(data))
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
