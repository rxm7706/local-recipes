#!/usr/bin/env python3
"""
Recipe validation script for conda-forge recipes.

Validates both meta.yaml and recipe.yaml formats against conda-forge best practices.
Designed to be portable and work in enterprise/air-gapped environments.

Usage:
    python validate_recipe.py recipes/my-package
    python validate_recipe.py recipes/my-package/recipe.yaml
    python validate_recipe.py --strict recipes/my-package
    python validate_recipe.py --json recipes/my-package
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    yaml = None  # type: ignore[assignment]
    YAML_AVAILABLE = False


class ValidationResult(NamedTuple):
    """Result of recipe validation."""
    passed: bool
    errors: list[str]
    warnings: list[str]
    info: list[str]
    rattler_lint_ran: bool = False


def normalize_path(path: Path) -> Path:
    """Find the recipe file from a path (file or directory)."""
    if path.is_file():
        return path

    # Check for recipe files in order of preference
    for name in ["recipe.yaml", "meta.yaml"]:
        recipe_path = path / name
        if recipe_path.exists():
            return recipe_path

    raise FileNotFoundError(f"No recipe file found in {path}")


def run_rattler_lint(recipe_path: Path) -> tuple[list[str], list[str], bool]:
    """
    Run 'rattler-build lint <dir>' if rattler-build is on PATH.

    Returns (errors, warnings, ran).
    'ran' is False when rattler-build is absent or doesn't support the lint
    subcommand (versions prior to ~0.30).

    Output format handling:
      - JSON array/object (--json flag or newer versions)
      - Plain text lines prefixed with [error]/[warning]/error:/warning:
    """
    rattler = shutil.which("rattler-build")
    if not rattler:
        return [], [], False

    recipe_dir = recipe_path.parent if recipe_path.is_file() else recipe_path

    try:
        proc = subprocess.run(
            [rattler, "lint", str(recipe_dir)],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return [], [], False

    combined = proc.stdout + proc.stderr

    # Detect "unrecognized subcommand" — older rattler-build without lint
    combined_lower = combined.lower()
    if any(
        phrase in combined_lower
        for phrase in ("unrecognized subcommand", "unknown subcommand",
                       "no such subcommand", "error: 'lint'")
    ):
        return [], [], False

    errors: list[str] = []
    warnings: list[str] = []

    # Try JSON output first (some rattler-build versions emit JSON)
    try:
        data = json.loads(proc.stdout)
        if isinstance(data, list):
            for item in data:
                level = str(item.get("level", "")).lower()
                msg = item.get("message") or item.get("msg") or str(item)
                (errors if "error" in level else warnings).append(f"rattler-build: {msg}")
        elif isinstance(data, dict):
            for e in data.get("errors", []):
                errors.append(f"rattler-build: {e}")
            for w in data.get("warnings", []):
                warnings.append(f"rattler-build: {w}")
        return errors, warnings, True
    except (json.JSONDecodeError, ValueError, AttributeError):
        pass

    # Plain-text fallback — parse [error]/[warning]/error:/warning: prefixes
    _ERROR_RE = re.compile(r"^\[?error\]?:?\s*", re.IGNORECASE)
    _WARN_RE = re.compile(r"^\[?warning\]?:?\s*", re.IGNORECASE)
    _SKIP_RE = re.compile(r"^(linting|checking|info:|note:|$)", re.IGNORECASE)

    for line in combined.splitlines():
        line = line.strip()
        if not line or _SKIP_RE.match(line):
            continue
        ll = line.lower()
        if ll.startswith("[error]") or ll.startswith("error:"):
            errors.append("rattler-build: " + _ERROR_RE.sub("", line))
        elif ll.startswith("[warning]") or ll.startswith("warning:"):
            warnings.append("rattler-build: " + _WARN_RE.sub("", line))
        elif proc.returncode != 0:
            # Non-zero exit with unstructured output — surface as error
            errors.append(f"rattler-build: {line}")

    return errors, warnings, True


def validate_recipe_yaml(path: Path) -> ValidationResult:
    """Validate recipe.yaml against v1 format rules and best practices."""
    errors: list[str] = []
    warnings: list[str] = []
    info: list[str] = []

    if not YAML_AVAILABLE:
        return ValidationResult(False, ["PyYAML not installed - cannot validate"], [], [])
    assert yaml is not None

    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        return ValidationResult(False, [f"YAML parse error: {e}"], [], [])
    except Exception as e:
        return ValidationResult(False, [f"File read error: {e}"], [], [])

    if content is None:
        return ValidationResult(False, ["Empty recipe file"], [], [])

    # Check schema_version
    schema_version = content.get("schema_version")
    if schema_version != 1:
        errors.append(f"Missing or incorrect schema_version (got {schema_version}, expected 1)")
    else:
        info.append("schema_version: 1 (v1 format)")

    # Check context section
    context = content.get("context", {})
    if not context:
        warnings.append("No context section - consider using variables for version, name")
    else:
        if "version" not in context:
            warnings.append("Consider adding 'version' to context section")

    # Check package section
    package = content.get("package", {})
    if not package:
        errors.append("Missing package section")
    else:
        if "name" not in package:
            errors.append("Missing package.name")
        if "version" not in package:
            errors.append("Missing package.version")

    # Check source section
    source = content.get("source", {})
    if isinstance(source, dict):
        sources = [source]
    elif isinstance(source, list):
        sources = source
    else:
        sources = []

    for i, src in enumerate(sources):
        if isinstance(src, dict):
            if "url" in src:
                url = src.get("url", "")
                if "pypi.io" in url:
                    warnings.append(f"Source {i}: Prefer pypi.org over pypi.io (pypi.io redirects but pypi.org is canonical)")
                if "sha256" not in src and "sha1" not in src and "md5" not in src:
                    errors.append(f"Source {i}: Missing checksum (sha256 recommended)")
            elif "git" in src or "git_url" in src:
                warnings.append(f"Source {i}: Using git source - prefer URL with checksum for reproducibility")

    # Check requirements section
    reqs = content.get("requirements", {})
    build_reqs = reqs.get("build", [])
    host_reqs = reqs.get("host", [])
    run_reqs = reqs.get("run", [])

    # Flatten requirements (handle if/then structures)
    def flatten_reqs(req_list):
        """Extract requirement strings from potentially nested structures."""
        result = []
        for item in req_list if req_list else []:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                # Handle if/then/else
                if "then" in item:
                    then_val = item["then"]
                    if isinstance(then_val, str):
                        result.append(then_val)
                    elif isinstance(then_val, list):
                        result.extend(flatten_reqs(then_val))
                if "else" in item:
                    else_val = item["else"]
                    if isinstance(else_val, str):
                        result.append(else_val)
                    elif isinstance(else_val, list):
                        result.extend(flatten_reqs(else_val))
        return result

    flat_build = flatten_reqs(build_reqs)
    flat_host = flatten_reqs(host_reqs)
    flat_run = flatten_reqs(run_reqs)

    # Check for compiler without stdlib
    has_compiler = any("compiler" in str(r) for r in flat_build)
    has_stdlib = any("stdlib" in str(r) for r in flat_build)
    if has_compiler and not has_stdlib:
        errors.append("Missing ${{ stdlib('c') }} - required for compiled packages with compilers")

    # Check for python_min in noarch packages
    build = content.get("build", {})
    if build.get("noarch") == "python":
        has_python_min_host = any("python_min" in str(r) for r in flat_host)
        has_python_min_run = any("python_min" in str(r) for r in flat_run)
        if not has_python_min_host:
            warnings.append("CFEP-25: noarch:python host should use python ${{ python_min }}.*")
        if not has_python_min_run:
            warnings.append("CFEP-25: noarch:python run should use python >=${{ python_min }}")
        info.append("noarch: python detected")

    # Check tests section
    tests = content.get("tests", [])
    if not tests:
        warnings.append("No tests section defined - add tests for quality assurance")
    else:
        has_pip_check = any(
            isinstance(t, dict) and t.get("python", {}).get("pip_check") for t in tests
        )
        if not has_pip_check:
            warnings.append("Consider adding pip_check: true to python tests")
        info.append(f"{len(tests)} test(s) defined")

    # Check about section
    about = content.get("about", {})
    if "license" not in about:
        errors.append("Missing license in about section")
    else:
        license_val = about.get("license", "")
        # Check for common SPDX issues
        if license_val.upper() != license_val and not re.match(r"^[A-Z][a-z]", license_val):
            if license_val.lower() in ["apache 2.0", "apache2", "apache-2"]:
                warnings.append(f"License '{license_val}' should be 'Apache-2.0' (SPDX format)")

    if "license_file" not in about:
        errors.append("Missing license_file in about section")

    if "summary" not in about and "description" not in about:
        warnings.append("Missing summary/description in about section")

    # Check extra section
    extra = content.get("extra", {})
    maintainers = extra.get("recipe-maintainers", [])
    if not maintainers:
        errors.append("Missing recipe-maintainers in extra section")

    # ── rattler-build lint pass ───────────────────────────────────────────────
    rb_errors, rb_warnings, rb_ran = run_rattler_lint(path)
    errors.extend(rb_errors)
    warnings.extend(rb_warnings)
    if rb_ran:
        rb_status = "passed" if not rb_errors else f"{len(rb_errors)} error(s)"
        info.append(f"rattler-build lint: {rb_status}")
    else:
        info.append("rattler-build lint: not available (install rattler-build ≥0.30 for schema validation)")

    return ValidationResult(
        passed=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        info=info,
        rattler_lint_ran=rb_ran,
    )


def validate_meta_yaml(path: Path) -> ValidationResult:
    """Validate meta.yaml against conda-forge rules (basic checks)."""
    errors: list[str] = []
    warnings: list[str] = []
    info: list[str] = []

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return ValidationResult(False, [f"File read error: {e}"], [], [])

    info.append("meta.yaml (legacy format) detected")

    # Check for license_file
    if "license_file" not in content:
        errors.append("Missing license_file")

    # Check for deprecated pypi.io
    if "pypi.io" in content:
        errors.append("Use pypi.org instead of deprecated pypi.io")

    # Check for git_url usage
    if "git_url" in content and "git_tag" in content:
        warnings.append("Prefer URL source with SHA256 over git_url for reproducibility")

    # Check for noarch:python and python_min
    if re.search(r"noarch:\s*python", content):
        info.append("noarch: python detected")
        if "python_min" not in content:
            warnings.append("CFEP-25: noarch:python should use python_min variable")

    # Check for compiler without stdlib (basic check)
    if "compiler(" in content:
        if "stdlib(" not in content:
            # Could be false positive due to comment selectors, so warn instead of error
            warnings.append("Compiled package may need stdlib('c') - verify requirements")

    # Check for recipe-maintainers
    if "recipe-maintainers" not in content:
        errors.append("Missing recipe-maintainers in extra section")

    # Check for common selector issues
    if "# [py>" in content or "# [py<" in content:
        info.append("Python version selectors detected - ensure syntax is correct")

    # Check for skip: True vs skip: true
    if "skip: True" in content:
        warnings.append("Use 'skip: true' (lowercase) for YAML boolean consistency")

    return ValidationResult(
        passed=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        info=info
    )


def validate_recipe(path: Path) -> ValidationResult:
    """Validate a recipe file (auto-detect format)."""
    recipe_path = normalize_path(path)

    if recipe_path.name == "recipe.yaml":
        return validate_recipe_yaml(recipe_path)
    elif recipe_path.name == "meta.yaml":
        return validate_meta_yaml(recipe_path)
    else:
        return ValidationResult(
            False,
            [f"Unknown recipe format: {recipe_path.name}"],
            [],
            []
        )


def print_result(result: ValidationResult, use_json: bool = False) -> None:
    """Print validation result."""
    if use_json:
        print(json.dumps({
            "passed": result.passed,
            "errors": result.errors,
            "warnings": result.warnings,
            "info": result.info,
            "rattler_lint_ran": result.rattler_lint_ran,
        }, indent=2))
        return

    # Print info
    if result.info:
        print("INFO:")
        for item in result.info:
            print(f"  [i] {item}")

    # Print errors
    if result.errors:
        print("\nERRORS:")
        for error in result.errors:
            print(f"  [x] {error}")

    # Print warnings
    if result.warnings:
        print("\nWARNINGS:")
        for warning in result.warnings:
            print(f"  [!] {warning}")

    # Summary
    print()
    if result.passed and not result.warnings:
        print("[OK] Recipe validation passed")
    elif result.passed:
        print(f"[OK] Recipe validation passed with {len(result.warnings)} warning(s)")
    else:
        print(f"[FAIL] Recipe validation failed with {len(result.errors)} error(s)")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate conda-forge recipes against best practices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s recipes/my-package
  %(prog)s recipes/my-package/recipe.yaml
  %(prog)s --strict recipes/my-package
  %(prog)s --json recipes/my-package

This script checks for:
  - Schema version and structure (recipe.yaml)
  - License file presence and SPDX format
  - CFEP-25 compliance (python_min for noarch:python)
  - stdlib requirement for compiled packages
  - Source checksums and URL format
  - Tests and pip_check presence
  - Maintainer information
        """
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to recipe file or directory"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only show errors (suppress info and warnings)"
    )

    args = parser.parse_args()

    try:
        result = validate_recipe(args.path)
    except FileNotFoundError as e:
        if args.json:
            print(json.dumps({"passed": False, "errors": [str(e)], "warnings": [], "info": []}))
        else:
            print(f"[FAIL] {e}")
        return 1

    if args.quiet:
        # Only show if there are errors
        if not result.passed:
            result = ValidationResult(
                passed=result.passed,
                errors=result.errors,
                warnings=[],
                info=[]
            )

    print_result(result, use_json=args.json)

    # Exit code
    if args.strict and result.warnings:
        return 1
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
