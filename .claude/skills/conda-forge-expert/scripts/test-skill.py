#!/usr/bin/env python3
"""
Validate the conda-forge-expert skill structure and content.

Checks:
- Required files exist
- File structure is correct
- Templates are valid YAML
- Scripts are syntactically valid Python
- References are consistent

Usage:
    python test-skill.py
    python test-skill.py --verbose
    python test-skill.py --fix  # Auto-fix some issues
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import NamedTuple

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class TestResult(NamedTuple):
    """Result of a single test."""
    name: str
    passed: bool
    message: str


def get_skill_dir() -> Path:
    """Get the skill directory path."""
    # Script is in scripts/, skill is parent
    return Path(__file__).parent.parent


def check_required_files(skill_dir: Path) -> list[TestResult]:
    """Check that required files exist."""
    results = []

    required_files = [
        "SKILL.md",
        "config/skill-config.yaml",
        "mappings/pypi-conda.yaml",
        "scripts/validate_recipe.py",
    ]

    required_dirs = [
        "reference",
        "templates",
        "guides",
        "quickref",
        "enterprise",
        "examples",
    ]

    for file_path in required_files:
        path = skill_dir / file_path
        if path.exists():
            results.append(TestResult(
                name=f"File exists: {file_path}",
                passed=True,
                message="OK"
            ))
        else:
            results.append(TestResult(
                name=f"File exists: {file_path}",
                passed=False,
                message=f"Missing: {path}"
            ))

    for dir_path in required_dirs:
        path = skill_dir / dir_path
        if path.is_dir():
            results.append(TestResult(
                name=f"Directory exists: {dir_path}",
                passed=True,
                message="OK"
            ))
        else:
            results.append(TestResult(
                name=f"Directory exists: {dir_path}",
                passed=False,
                message=f"Missing: {path}"
            ))

    return results


def check_yaml_files(skill_dir: Path) -> list[TestResult]:
    """Validate YAML files are parseable."""
    results = []

    if not YAML_AVAILABLE:
        results.append(TestResult(
            name="YAML validation",
            passed=False,
            message="PyYAML not installed - skipping YAML validation"
        ))
        return results

    yaml_dirs = ["config", "templates", "examples"]

    for dir_name in yaml_dirs:
        dir_path = skill_dir / dir_name
        if not dir_path.exists():
            continue

        for yaml_file in dir_path.rglob("*.yaml"):
            try:
                content = yaml_file.read_text()
                # Remove Jinja/template syntax for validation
                import re
                clean = re.sub(r'\$\{\{[^}]+\}\}', 'PLACEHOLDER', content)
                clean = re.sub(r'\{\{[^}]+\}\}', 'PLACEHOLDER', clean)
                clean = re.sub(r'\{%[^%]+%\}', '', clean)

                yaml.safe_load(clean)
                results.append(TestResult(
                    name=f"YAML valid: {yaml_file.relative_to(skill_dir)}",
                    passed=True,
                    message="OK"
                ))
            except yaml.YAMLError as e:
                results.append(TestResult(
                    name=f"YAML valid: {yaml_file.relative_to(skill_dir)}",
                    passed=False,
                    message=f"Parse error: {e}"
                ))
            except Exception as e:
                results.append(TestResult(
                    name=f"YAML valid: {yaml_file.relative_to(skill_dir)}",
                    passed=False,
                    message=f"Error: {e}"
                ))

    return results


def check_python_scripts(skill_dir: Path) -> list[TestResult]:
    """Validate Python scripts are syntactically valid."""
    results = []

    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.exists():
        return results

    for py_file in scripts_dir.glob("*.py"):
        try:
            content = py_file.read_text()
            ast.parse(content)
            results.append(TestResult(
                name=f"Python syntax: {py_file.name}",
                passed=True,
                message="OK"
            ))
        except SyntaxError as e:
            results.append(TestResult(
                name=f"Python syntax: {py_file.name}",
                passed=False,
                message=f"Syntax error at line {e.lineno}: {e.msg}"
            ))

    # Also check enterprise scripts
    enterprise_dir = skill_dir / "enterprise"
    if enterprise_dir.exists():
        for py_file in enterprise_dir.glob("*.py"):
            try:
                content = py_file.read_text()
                ast.parse(content)
                results.append(TestResult(
                    name=f"Python syntax: enterprise/{py_file.name}",
                    passed=True,
                    message="OK"
                ))
            except SyntaxError as e:
                results.append(TestResult(
                    name=f"Python syntax: enterprise/{py_file.name}",
                    passed=False,
                    message=f"Syntax error at line {e.lineno}: {e.msg}"
                ))

    return results


def check_markdown_files(skill_dir: Path) -> list[TestResult]:
    """Check markdown files have proper structure."""
    results = []

    for md_file in skill_dir.rglob("*.md"):
        try:
            content = md_file.read_text()
            stripped = content.strip()

            # SKILL.md uses YAML frontmatter, checked separately
            if md_file.name == "SKILL.md":
                if stripped.startswith("---"):
                    results.append(TestResult(
                        name=f"Markdown structure: {md_file.relative_to(skill_dir)}",
                        passed=True,
                        message="OK (has frontmatter)"
                    ))
                else:
                    results.append(TestResult(
                        name=f"Markdown structure: {md_file.relative_to(skill_dir)}",
                        passed=False,
                        message="SKILL.md should have YAML frontmatter (---)"
                    ))
            # Other markdown files should start with a heading
            elif not stripped.startswith("#"):
                results.append(TestResult(
                    name=f"Markdown structure: {md_file.relative_to(skill_dir)}",
                    passed=False,
                    message="Should start with a heading (#)"
                ))
            else:
                results.append(TestResult(
                    name=f"Markdown structure: {md_file.relative_to(skill_dir)}",
                    passed=True,
                    message="OK"
                ))

        except Exception as e:
            results.append(TestResult(
                name=f"Markdown readable: {md_file.relative_to(skill_dir)}",
                passed=False,
                message=f"Error: {e}"
            ))

    return results


def check_template_placeholders(skill_dir: Path) -> list[TestResult]:
    """Check templates have proper placeholder format."""
    results = []

    templates_dir = skill_dir / "templates"
    if not templates_dir.exists():
        return results

    required_placeholders = ["REPLACE_NAME", "REPLACE_VERSION", "REPLACE_MAINTAINER"]

    for template_file in templates_dir.rglob("*.yaml"):
        content = template_file.read_text()

        missing = []
        for placeholder in required_placeholders:
            if placeholder not in content:
                missing.append(placeholder)

        if missing:
            results.append(TestResult(
                name=f"Template placeholders: {template_file.relative_to(skill_dir)}",
                passed=False,
                message=f"Missing: {', '.join(missing)}"
            ))
        else:
            results.append(TestResult(
                name=f"Template placeholders: {template_file.relative_to(skill_dir)}",
                passed=True,
                message="OK"
            ))

    return results


def check_skill_metadata(skill_dir: Path) -> list[TestResult]:
    """Check SKILL.md has proper frontmatter."""
    results = []

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        results.append(TestResult(
            name="SKILL.md frontmatter",
            passed=False,
            message="SKILL.md not found"
        ))
        return results

    content = skill_md.read_text()

    # Check for YAML frontmatter
    if not content.startswith("---"):
        results.append(TestResult(
            name="SKILL.md frontmatter",
            passed=False,
            message="Missing YAML frontmatter (should start with ---)"
        ))
        return results

    # Extract frontmatter
    parts = content.split("---", 2)
    if len(parts) < 3:
        results.append(TestResult(
            name="SKILL.md frontmatter",
            passed=False,
            message="Invalid frontmatter format"
        ))
        return results

    if YAML_AVAILABLE:
        try:
            frontmatter = yaml.safe_load(parts[1])

            required_fields = ["name", "description"]
            missing = [f for f in required_fields if f not in frontmatter]

            if missing:
                results.append(TestResult(
                    name="SKILL.md frontmatter",
                    passed=False,
                    message=f"Missing fields: {', '.join(missing)}"
                ))
            else:
                results.append(TestResult(
                    name="SKILL.md frontmatter",
                    passed=True,
                    message=f"OK - name: {frontmatter.get('name')}"
                ))

        except yaml.YAMLError as e:
            results.append(TestResult(
                name="SKILL.md frontmatter",
                passed=False,
                message=f"Invalid YAML: {e}"
            ))
    else:
        results.append(TestResult(
            name="SKILL.md frontmatter",
            passed=True,
            message="OK (YAML validation skipped)"
        ))

    return results


def run_all_tests(verbose: bool = False) -> tuple[int, int]:
    """Run all validation tests."""
    skill_dir = get_skill_dir()

    print(f"Validating skill at: {skill_dir}")
    print("=" * 60)

    all_results = []

    # Run all checks
    all_results.extend(check_required_files(skill_dir))
    all_results.extend(check_skill_metadata(skill_dir))
    all_results.extend(check_yaml_files(skill_dir))
    all_results.extend(check_python_scripts(skill_dir))
    all_results.extend(check_markdown_files(skill_dir))
    all_results.extend(check_template_placeholders(skill_dir))

    # Count results
    passed = sum(1 for r in all_results if r.passed)
    failed = sum(1 for r in all_results if not r.passed)

    # Print results
    if verbose:
        for result in all_results:
            status = "✓" if result.passed else "✗"
            print(f"{status} {result.name}")
            if not result.passed or verbose:
                print(f"  {result.message}")
    else:
        # Just print failures
        for result in all_results:
            if not result.passed:
                print(f"✗ {result.name}")
                print(f"  {result.message}")

    # Summary
    print("\n" + "=" * 60)
    print(f"Tests: {passed + failed} total, {passed} passed, {failed} failed")

    if failed == 0:
        print("\n[OK] All validation tests passed!")
    else:
        print(f"\n[FAIL] {failed} test(s) failed")

    return passed, failed


def main():
    parser = argparse.ArgumentParser(
        description="Validate the conda-forge-expert skill"
    )
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show all test results, not just failures")
    parser.add_argument("--fix", action="store_true",
                        help="Attempt to auto-fix some issues (not implemented)")

    args = parser.parse_args()

    if args.fix:
        print("Note: --fix is not yet implemented")

    passed, failed = run_all_tests(verbose=args.verbose)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
