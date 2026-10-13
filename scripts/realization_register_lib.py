"""Shared loader and coverage helpers for the realization register (Story 100.5)."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTER_PATH = REPO_ROOT / "docs" / "governance" / "realization-register.yaml"
SCHEMA_PATH = REPO_ROOT / "docs" / "governance" / "realization-register.schema.json"

_KIT_INSTRUMENT_TO_PACKAGE = {
    "caveman": "caveman-installer",
    "headroom-ai": "headroom-ai",
    "codegraph": "codegraph",
}

_ALLOWED_REALIZE_FIRST = frozenset(
    {
        "pyforge",
        "pixi",
        "python",
        "pre-commit",
        "caveman-install",
        "bmad-module-skill-forge",
        "bmad-loop",
        "helm",
        "gh",
        "spec-kit",
        "age",
        "opengrep",
        "osv-scanner",
        "deptry",
        "postgresql",
        "redis-server",
        "silo",
    }
)


def load_register(root: Path = REPO_ROOT) -> dict[str, Any]:
    path = root / "docs" / "governance" / "realization-register.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected mapping")
    return data


def register_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = data.get("rows")
    if not isinstance(rows, list):
        return []
    return [r for r in rows if isinstance(r, dict)]


def register_packages(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(r["package"]): r for r in register_rows(data) if r.get("package")}


def _scribe_pins(root: Path) -> set[str]:
    scribe_src = root / "src" / "shared" / "packages" / "pyforge-scribe" / "src"
    if str(scribe_src) not in sys.path:
        sys.path.insert(0, str(scribe_src))
    from pyforge.scribe.catalog import read_pins  # noqa: PLC0415

    pins = read_pins(root)
    return {name for name in pins if name.startswith("bmad-") or name.startswith("mybmad")}


def _kit_packages(root: Path) -> set[str]:
    marshal_src = root / "src" / "shared" / "packages" / "pyforge-marshal" / "src"
    if str(marshal_src) not in sys.path:
        sys.path.insert(0, str(marshal_src))
    from pyforge.marshal.seed.model.kit import KIT_ITEMS  # noqa: PLC0415

    out: set[str] = set()
    for item in KIT_ITEMS:
        out.add(_KIT_INSTRUMENT_TO_PACKAGE.get(item.instrument, item.instrument))
    return out


def required_coverage_packages(root: Path = REPO_ROOT) -> set[str]:
    return _scribe_pins(root) | _kit_packages(root)


def validate_realize_argv(row: dict[str, Any], root: Path) -> list[str]:
    """Return findings when a realize step's first token is not allowed."""
    findings: list[str] = []
    realize = row.get("realize") or {}
    steps = realize.get("steps") or []
    if not isinstance(steps, list):
        return [f"{row.get('package')}: realize.steps must be a list"]
    pkg = str(row.get("package", ""))
    for step in steps:
        if not step:
            continue
        if not isinstance(step, list):
            findings.append(f"{pkg}: realize step is not argv list")
            continue
        first = str(step[0])
        if first in ("python", sys.executable):
            continue
        if first.startswith("pyforge") or first in _ALLOWED_REALIZE_FIRST:
            continue
        if first.endswith(".py"):
            continue
        # pixi tasks are invoked via python scripts/… in this register
        findings.append(f"{pkg}: realize argv starts with disallowed token {first!r}")
    return findings


def row_by_package(data: dict[str, Any], package: str) -> dict[str, Any] | None:
    return register_packages(data).get(package)
