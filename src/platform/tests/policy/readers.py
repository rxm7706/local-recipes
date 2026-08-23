# Copyright (c) 2026 Kevin Mills
# Portions adapted from millsks/django-15-factor-base (MIT License).
"""Shared declaration readers for the platform policy suite.

One place to load pyproject / pixi / workflow surfaces so each policy module
asserts against the same parse. Shape borrowed from the django-15-factor-base
coverage/typing policy readers (closed declaration tables + named accessors);
not a vendor of that repo's megatests.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import yaml

POLICY_DIR = Path(__file__).resolve().parent
PLATFORM_ROOT = POLICY_DIR.parents[1]
REPO_ROOT = POLICY_DIR.parents[3]

PLATFORM_PYPROJECT = PLATFORM_ROOT / "pyproject.toml"
PIXI_TOML = REPO_ROOT / "pixi.toml"
PLATFORM_CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "platform-ci.yml"
PLATFORM_TEST_SETUP_ACTION = (
    REPO_ROOT / ".github" / "actions" / "platform-test-setup" / "action.yml"
)
PRODUCTION_SETTINGS = PLATFORM_ROOT / "config" / "settings" / "production.py"
ROOT_GITIGNORE = REPO_ROOT / ".gitignore"
REQUIREMENTS_CHECKER = (
    REPO_ROOT / "scripts" / "platform_ci_test_requirements_check.py"
)


def load_toml(path: Path) -> dict[str, Any]:
    """Parse a TOML file into a dict."""
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_yaml(path: Path) -> Any:
    """Parse a YAML file."""
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def platform_pyproject() -> dict[str, Any]:
    """Return the parsed ``src/platform/pyproject.toml``."""
    return load_toml(PLATFORM_PYPROJECT)


def pixi_manifest() -> dict[str, Any]:
    """Return the parsed repo-root ``pixi.toml``."""
    return load_toml(PIXI_TOML)


def platform_ci_workflow() -> dict[str, Any]:
    """Return the parsed Platform CI workflow."""
    return load_yaml(PLATFORM_CI_WORKFLOW)


def platform_ci_workflow_text() -> str:
    """Return the raw Platform CI workflow text (for step-command greps)."""
    return PLATFORM_CI_WORKFLOW.read_text(encoding="utf-8")


def coverage_run_table(pyproject: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return ``[tool.coverage.run]``."""
    doc = pyproject if pyproject is not None else platform_pyproject()
    table: dict[str, Any] = doc.get("tool", {}).get("coverage", {}).get("run", {})
    return table


def coverage_report_table(
    pyproject: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Return ``[tool.coverage.report]``, or None when undeclared."""
    doc = pyproject if pyproject is not None else platform_pyproject()
    table: dict[str, Any] | None = (
        doc.get("tool", {}).get("coverage", {}).get("report")
    )
    return table


def mypy_table(pyproject: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return ``[tool.mypy]`` (including ``overrides`` when present)."""
    doc = pyproject if pyproject is not None else platform_pyproject()
    table: dict[str, Any] = doc.get("tool", {}).get("mypy", {})
    return table


def declared_include(pyproject: dict[str, Any] | None = None) -> list[str]:
    """Return coverage ``include`` (measurement bound)."""
    return list(coverage_run_table(pyproject).get("include", []))


def declared_omit(pyproject: dict[str, Any] | None = None) -> list[str]:
    """Return coverage ``omit``."""
    return list(coverage_run_table(pyproject).get("omit", []))


def declared_fail_under(pyproject: dict[str, Any] | None = None) -> float | int | None:
    """Return coverage ``fail_under``, or None when undeclared."""
    report = coverage_report_table(pyproject)
    if report is None:
        return None
    value = report.get("fail_under")
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    msg = f"fail_under must be numeric, got {type(value).__name__}"
    raise TypeError(msg)


def count_fail_under_declarations(pyproject_text: str | None = None) -> int:
    """Count ``fail_under`` assignment lines in the platform pyproject text."""
    text = (
        pyproject_text
        if pyproject_text is not None
        else PLATFORM_PYPROJECT.read_text(encoding="utf-8")
    )
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("fail_under") and "=" in stripped:
            count += 1
    return count
