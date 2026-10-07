"""CAP-54: the base herald package never imports Django or the host ``config`` package."""

from __future__ import annotations

import ast
from pathlib import Path

_HERE = Path(__file__).resolve()
ROOT = next(p for p in _HERE.parents if (p / "pixi.toml").is_file() and (p / "AGENTS.md").is_file())
HERALD_SRC = ROOT / "src" / "shared" / "packages" / "pyforge-herald" / "src" / "pyforge" / "herald"
_FORBIDDEN = frozenset({"django", "config"})


def _imported_modules(py_file: Path) -> list[tuple[int, str]]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append((node.lineno, node.module))
    return found


def _is_forbidden(module: str) -> bool:
    return module in _FORBIDDEN or module.startswith("django.") or module.startswith("config.")


def test_base_herald_package_has_no_django_or_config_imports():
    offenders: list[str] = []
    for py_file in sorted(HERALD_SRC.rglob("*.py")):
        if "dashboard" in py_file.parts:
            continue
        for line, module in _imported_modules(py_file):
            if _is_forbidden(module):
                rel = py_file.relative_to(ROOT).as_posix()
                offenders.append(f"{rel}:{line}: imports {module}")
    assert offenders == []
