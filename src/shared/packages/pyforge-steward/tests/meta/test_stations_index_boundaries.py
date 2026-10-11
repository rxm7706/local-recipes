"""Story 91.1 AC7: module-scope import boundaries for the stations index gate."""

from __future__ import annotations

import ast
from pathlib import Path

_HERE = Path(__file__).resolve()
ROOT = next(p for p in _HERE.parents if (p / "pixi.toml").is_file() and (p / "AGENTS.md").is_file())
PLATFORM = ROOT / "src" / "platform"
GUARDED_FILES = (
    PLATFORM / "config" / "stations_index.py",
    PLATFORM / "config" / "urls.py",
)
_SETTINGS_BASE = PLATFORM / "config" / "settings" / "base.py"


def _portal_module_names() -> frozenset[str]:
    tree = ast.parse(_SETTINGS_BASE.read_text(encoding="utf-8"), filename=str(_SETTINGS_BASE))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_STATION_PORTAL_PACKAGES":
                    value = ast.literal_eval(node.value)
                    return frozenset(module for _, module in value)
    msg = "_STATION_PORTAL_PACKAGES not found in settings base"
    raise AssertionError(msg)


def _forbidden_module(module: str, portal_modules: frozenset[str]) -> bool:
    if module == "pyforge" or module.startswith("pyforge."):
        return True
    if module in portal_modules:
        return True
    return module == "config.station_api" or module.startswith("config.station_api.")


def _iter_module_level_imports(tree: ast.Module) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []

    def walk_stmt(stmt: ast.stmt) -> None:
        if isinstance(stmt, ast.Import):
            found.extend((stmt.lineno, alias.name) for alias in stmt.names)
        elif isinstance(stmt, ast.ImportFrom) and stmt.level == 0 and stmt.module:
            found.append((stmt.lineno, stmt.module))
        elif isinstance(stmt, (ast.If, ast.Try, ast.With)):
            body = getattr(stmt, "body", [])
            orelse = getattr(stmt, "orelse", [])
            handlers = getattr(stmt, "handlers", [])
            finalbody = getattr(stmt, "finalbody", [])
            for nested in (*body, *orelse, *finalbody):
                if isinstance(nested, ast.stmt):
                    walk_stmt(nested)
            for handler in handlers:
                for nested in handler.body:
                    if isinstance(nested, ast.stmt):
                        walk_stmt(nested)

    for top in tree.body:
        if isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        walk_stmt(top)
    return found


def test_stations_index_files_import_nothing_forbidden_at_module_scope() -> None:
    portal_modules = _portal_module_names()
    findings: list[str] = []
    for path in GUARDED_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        rel = path.relative_to(ROOT).as_posix()
        for line, module in _iter_module_level_imports(tree):
            if _forbidden_module(module, portal_modules):
                findings.append(f"{rel}:{line}: forbidden module-scope import {module!r}")
    assert not findings, "\n".join(findings)
