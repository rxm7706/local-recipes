#!/usr/bin/env python3
"""
Recipe Optimization Linter for conda-forge recipes.

Goes beyond basic validation and checks for common anti-patterns, suggesting
improvements for dependency placement, redundant selectors, security, and
conda-forge best practices.

Check codes (14 total):
  DEP-001  Dev dependency in run requirements
  DEP-002  noarch:python Python upper bound in run (should be run_constrained)
  PIN-001  Exact version pin in run requirements
  ABT-001  Missing license_file in about section
  ABT-002  v0/meta.yaml about-field names used in v1 recipe.yaml (silently ignored)
  SCRIPT-001  sudo used in build.sh
  SCRIPT-002  pip install --upgrade in build.sh
  SEL-001  Redundant platform skip conditions
  SEL-002  Incomplete CFEP-25 python_min triad for noarch:python
  SEL-003  Bare `py < N` selector in v1 recipe.yaml build.skip (use match(python, ...))
  STD-001  compiler() used without stdlib() — CRITICAL, causes CI rejection
  STD-002  Both meta.yaml and recipe.yaml present — format mixing is rejected
  SEC-001  Source URL without sha256 checksum
  TEST-001  Missing tests section
  MAINT-001  Missing recipe-maintainers in extra section
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


_V0_TO_V1_ABOUT_FIELDS = {
    "home": "homepage",
    "dev_url": "repository",
    "doc_url": "documentation",
    "doc_source_url": "documentation",
    "license_family": None,  # removed in v1; not replaced
}


def analyze_about_section(data: Dict) -> List[OptimizationSuggestion]:
    """Check about section for conda-forge required fields and v0/v1 field-name mismatches.

    ABT-001  Missing license_file
    ABT-002  v0 (meta.yaml) about-field names used in v1 recipe.yaml — rattler-build
             silently accepts unknown keys, so these become a data-loss bug rather than
             a validation error. Verified against prefix-dev/recipe-format $defs.About.
    """
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

    # ABT-002 only applies to v1 recipes — v0 meta.yaml legitimately uses these names.
    if data.get("schema_version") == 1:
        for v0_name, v1_name in _V0_TO_V1_ABOUT_FIELDS.items():
            if v0_name in about:
                if v1_name is None:
                    msg = (
                        f"'about.{v0_name}' is a v0 (meta.yaml) field with no v1 equivalent — "
                        "rattler-build silently ignores it."
                    )
                    sug = f"Remove 'about.{v0_name}'."
                else:
                    msg = (
                        f"'about.{v0_name}' is the v0 (meta.yaml) field name; "
                        f"v1 recipe.yaml expects '{v1_name}'. rattler-build silently ignores "
                        "unknown keys, so the value is lost in the built package."
                    )
                    sug = f"Rename 'about.{v0_name}' → 'about.{v1_name}'."
                suggestions.append(OptimizationSuggestion(
                    code="ABT-002",
                    message=msg,
                    suggestion=sug,
                    confidence=1.0,
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

_PY_SELECTOR_RE = re.compile(r"^\s*py\s*[<>=!]+\s*\d+\s*$")


def analyze_selectors(data: Dict) -> List[OptimizationSuggestion]:
    """Analyzes platform selectors (SEL-001), CFEP-25 python_min compliance (SEL-002),
    and v0-style `py < N` selectors in v1 recipes (SEL-003).
    """
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

    # --- SEL-003: v0-style `py < N` selector in v1 recipe (silently ignored) ---
    # Empirical: rattler-build v0.64 does not inject a `py` integer variable from the
    # `python` variant string in staged-recipes-style builds, so `py < 311` evaluates
    # against an undefined symbol and never fires. cocoindex PR #33231 case study.
    # Use `match(python, "<3.11")` instead.
    if data.get("schema_version") == 1 and isinstance(skip_value, list):
        for entry in skip_value:
            if isinstance(entry, str) and _PY_SELECTOR_RE.match(entry):
                suggestions.append(OptimizationSuggestion(
                    code="SEL-003",
                    message=(
                        f"v1 recipe.yaml uses bare '{entry.strip()}' selector — this is "
                        "conda-build (meta.yaml v0) form and is silently ignored by rattler-build."
                    ),
                    suggestion=(
                        f"Replace '{entry.strip()}' with the rattler-build form, e.g. "
                        "'match(python, \"<3.11\")'. See reference/selectors-reference.md."
                    ),
                    confidence=1.0,
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

def analyze_stdlib_compliance(data: Dict) -> List[OptimizationSuggestion]:
    """Check that recipes using compiler() also declare stdlib() (STD-001).

    This is a CRITICAL check — omitting stdlib() causes automatic rejection by
    conda-forge CI for all compiled packages (see SKILL.md Critical Constraints
    and reference/recipe-yaml-reference.md § Requirements).
    """
    suggestions = []
    build_reqs = _flatten_reqs(data.get("requirements", {}).get("build", []))

    # go-nocgo (pure Go, no CGO) does not link against C stdlib — exclude it.
    # go-cgo DOES link against C stdlib, so it must be paired with stdlib("c").
    # Legacy compiler("go") is treated the same as go-nocgo (no stdlib needed).
    _NO_STDLIB_COMPILERS = {
        'compiler("go-nocgo")', "compiler('go-nocgo')",
        'compiler("go")', "compiler('go')",
    }

    def _is_c_abi_compiler(r: str) -> bool:
        if "compiler(" not in r and "${{ compiler" not in r and "{{ compiler" not in r:
            return False
        return not any(pat in r for pat in _NO_STDLIB_COMPILERS)

    has_compiler = any(_is_c_abi_compiler(r) for r in build_reqs)
    has_stdlib = any(
        "stdlib(" in r or "${{ stdlib" in r or "{{ stdlib" in r
        for r in build_reqs
    )

    if has_compiler and not has_stdlib:
        suggestions.append(OptimizationSuggestion(
            code="STD-001",
            message="Recipe uses compiler() but is missing stdlib() in build requirements.",
            suggestion=(
                "Add '${{ stdlib(\"c\") }}' immediately after '${{ compiler(\"c\") }}' "
                "in requirements.build. conda-forge CI enforces this for all compiled "
                "packages — omitting stdlib() causes automatic rejection."
            ),
            confidence=1.0,
        ))
    return suggestions


def analyze_format_mixing(recipe_path: Path) -> List[OptimizationSuggestion]:
    """Check that both meta.yaml and recipe.yaml do not coexist (STD-002).

    Mixed formats in the same directory are rejected by the tooling and can
    cause silent double-builds. Remove meta.yaml only after a successful build
    with the new recipe.yaml (deprecation-and-migration: Strangler pattern).
    """
    suggestions = []
    recipe_dir = recipe_path.parent
    has_meta = (recipe_dir / "meta.yaml").exists()
    has_recipe = (recipe_dir / "recipe.yaml").exists()

    if has_meta and has_recipe:
        suggestions.append(OptimizationSuggestion(
            code="STD-002",
            message="Both meta.yaml and recipe.yaml exist in the same directory.",
            suggestion=(
                "Remove meta.yaml after verifying that recipe.yaml builds successfully. "
                "Mixed formats in a single build run are rejected by the tooling."
            ),
            confidence=1.0,
        ))
    return suggestions


def analyze_source_security(data: Dict) -> List[OptimizationSuggestion]:
    """Check that source entries with URLs have sha256 checksums (SEC-001).

    Missing checksums allow supply-chain substitution attacks and fail
    conda-forge CI validation (security-and-hardening: Always Do).
    """
    suggestions = []
    sources = data.get("source")
    if sources is None:
        return suggestions

    sources_list: list = [sources] if isinstance(sources, dict) else (
        sources if isinstance(sources, list) else []
    )

    for i, src in enumerate(sources_list):
        if not isinstance(src, dict):
            continue
        if not src.get("url"):
            continue  # git or local path sources don't require sha256
        sha256 = str(src.get("sha256", "")).strip()
        if not sha256:
            label = f"source[{i}]" if len(sources_list) > 1 else "source"
            suggestions.append(OptimizationSuggestion(
                code="SEC-001",
                message=f"'{label}' has a URL but no sha256 checksum.",
                suggestion=(
                    "Add 'sha256: <hash>' to the source block. "
                    "Use edit_recipe with action=calculate_hash to compute it automatically, "
                    "or run: curl -sL <url> | sha256sum"
                ),
                confidence=0.95,
            ))
    return suggestions


def analyze_tests_section(data: Dict) -> List[OptimizationSuggestion]:
    """Check that a tests section exists (TEST-001).

    Recipes with no tests slip through validation but fail conda-forge review.
    A minimal test (import + pip_check) takes five lines and prevents regression
    (test-driven-development: tests are proof, not afterthoughts).
    """
    suggestions = []
    has_tests_v1 = bool(data.get("tests"))
    has_test_v0 = bool(data.get("test"))

    if not has_tests_v1 and not has_test_v0:
        suggestions.append(OptimizationSuggestion(
            code="TEST-001",
            message="Recipe has no tests section.",
            suggestion=(
                "Add at minimum an import test and pip_check. Example (recipe.yaml v1):\n"
                "tests:\n"
                "  - python:\n"
                "      imports: [mypackage]\n"
                "      pip_check: true\n"
                "      python_version: ${{ python_min }}.*"
            ),
            confidence=0.85,
        ))
    return suggestions


def analyze_maintainers(data: Dict) -> List[OptimizationSuggestion]:
    """Check that recipe-maintainers is populated (MAINT-001).

    conda-forge requires at least one maintainer per recipe. Recipes without
    maintainers are rejected at staged-recipes review.
    """
    suggestions = []
    extra = data.get("extra") or {}
    maintainers = extra.get("recipe-maintainers") or extra.get("recipe_maintainers")

    if not maintainers:
        suggestions.append(OptimizationSuggestion(
            code="MAINT-001",
            message="Recipe has no maintainers listed in extra.recipe-maintainers.",
            suggestion=(
                "Add your GitHub username to extra.recipe-maintainers. "
                "conda-forge requires at least one maintainer per recipe.\n"
                "Example:\nextra:\n  recipe-maintainers:\n    - rxm7706"
            ),
            confidence=0.9,
        ))
    return suggestions


def optimize_recipe(recipe_path: Path) -> List[OptimizationSuggestion]:
    """Runs all optimization checks on a given recipe file."""
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
    # Critical constraints first (confidence 1.0 — will block CI)
    all_suggestions.extend(analyze_stdlib_compliance(data))
    all_suggestions.extend(analyze_format_mixing(recipe_path))
    # Security checks
    all_suggestions.extend(analyze_source_security(data))
    # Completeness checks
    all_suggestions.extend(analyze_maintainers(data))
    all_suggestions.extend(analyze_tests_section(data))
    all_suggestions.extend(analyze_about_section(data))
    # Quality and style checks
    all_suggestions.extend(analyze_dependencies(data))
    all_suggestions.extend(analyze_noarch_python_constraints(data))
    all_suggestions.extend(analyze_pinning(data))
    all_suggestions.extend(analyze_build_script(recipe_path.parent))
    all_suggestions.extend(analyze_selectors(data))

    return all_suggestions

def main():
    parser = argparse.ArgumentParser(description="Lint a conda recipe for optimizations and best practices.")
    parser.add_argument("recipe_path", type=Path, help="Path to a recipe file (recipe.yaml/meta.yaml) or its directory.")

    args = parser.parse_args()

    recipe_path: Path = args.recipe_path
    if not recipe_path.exists():
        print(json.dumps({"success": False, "error": f"Path not found: {recipe_path}"}))
        sys.exit(1)

    # Accept a directory and resolve to recipe.yaml or meta.yaml inside it.
    # Without this, callers passing a directory got a silent 0-suggestions
    # response — the file_format detection in optimize_recipe() needs a real file.
    if recipe_path.is_dir():
        for candidate in ("recipe.yaml", "meta.yaml"):
            if (recipe_path / candidate).exists():
                recipe_path = recipe_path / candidate
                break
        else:
            print(json.dumps({"success": False, "error": f"No recipe.yaml or meta.yaml in {recipe_path}"}))
            sys.exit(1)

    suggestions = optimize_recipe(recipe_path)
    
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
