"""Story 93.1 — live django [tool.ruff] tables and NOT_YET_CLEAN ceiling (AC2, AC4)."""

from __future__ import annotations

import importlib.util
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
PACKAGES = ROOT / "src" / "shared" / "packages"
SCRIPTS = ROOT / "scripts"

EXPECTED_RUFF = {
    "target-version": "py312",
    "line-length": 120,
    "extend-exclude": ["*/migrations/*.py"],
}

EXPECTED_LINT = {
    "select": ["E", "F", "W", "I"],
    "ignore": ["E501"],
}

EXPECTED_PER_FILE = {
    "__init__.py": ["F401"],
    "**/tests/**": ["E402"],
}

SEEDED_NOT_YET_CLEAN: dict[str, frozenset[str]] = {
    "django-atlas": frozenset({"ruff", "ruff-format"}),
    "django-doctor": frozenset({"ruff"}),
    "django-herald": frozenset({"ruff", "ruff-format"}),
    "django-marshal": frozenset({"ruff", "ruff-format"}),
    "django-mason": frozenset({"ruff"}),
    "django-pyforge": frozenset({"ruff", "ruff-format"}),
    "django-scribe": frozenset({"ruff"}),
    "django-steward": frozenset({"ruff", "ruff-format"}),
    "django-warden": frozenset({"ruff", "ruff-format"}),
}


def _load_lint_types():
    name = "_lint_types_meta"
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / "lint_types.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def test_django_pyproject_ruff_tables_match_ac2() -> None:
    django_dirs = sorted(p for p in PACKAGES.glob("django-*") if (p / "pyproject.toml").is_file())
    assert len(django_dirs) == 9
    for pkg in django_dirs:
        data = tomllib.loads((pkg / "pyproject.toml").read_text(encoding="utf-8"))
        ruff = data["tool"]["ruff"]
        assert ruff["target-version"] == EXPECTED_RUFF["target-version"]
        assert ruff["line-length"] == EXPECTED_RUFF["line-length"]
        assert ruff["extend-exclude"] == EXPECTED_RUFF["extend-exclude"]
        lint = ruff["lint"]
        assert lint["select"] == EXPECTED_LINT["select"]
        assert lint["ignore"] == EXPECTED_LINT["ignore"]
        assert lint["per-file-ignores"] == EXPECTED_PER_FILE


def test_not_yet_clean_matches_ceiling_and_seeded_map() -> None:
    """Mutation: re-add a NOT_YET_CLEAN package or verb — this test fails."""
    mod = _load_lint_types()
    assert mod.NOT_YET_CLEAN == mod.NOT_YET_CLEAN_CEILING
    assert mod.NOT_YET_CLEAN == SEEDED_NOT_YET_CLEAN
    live_django = {p.name for p in PACKAGES.glob("django-*") if (p / "pyproject.toml").is_file()}
    assert set(mod.NOT_YET_CLEAN) <= live_django


def test_lint_types_workflow_paths_include_shared_packages() -> None:
    text = (ROOT / ".github/workflows/lint-types.yml").read_text(encoding="utf-8")
    assert "src/shared/packages/**" in text
