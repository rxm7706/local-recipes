"""Story 37.1 — django_herald_portal must not import pyforge.herald at module scope from urls."""

from __future__ import annotations

import ast
from pathlib import Path

_PORTAL_PKG = "django_herald_portal"


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (
            candidate / "src" / "shared" / "packages" / "django-herald"
        ).is_dir():
            return candidate
    raise AssertionError("could not locate repo root")


def _portal_root(root: Path) -> Path:
    return root / "src" / "shared" / "packages" / "django-herald" / "src" / _PORTAL_PKG


def _module_level_pyforge_herald_imports(body: list[ast.stmt]) -> list[str]:
    found: list[str] = []
    for node in body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name == "pyforge.herald" or name.startswith("pyforge.herald."):
                    found.append(f"import {name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "pyforge.herald" or module.startswith("pyforge.herald."):
                found.append(f"from {module} import ...")
        elif isinstance(node, ast.Try):
            found.extend(_module_level_pyforge_herald_imports(node.body))
            found.extend(_module_level_pyforge_herald_imports(node.orelse))
            found.extend(_module_level_pyforge_herald_imports(node.finalbody))
            for handler in node.handlers:
                found.extend(_module_level_pyforge_herald_imports(handler.body))
        elif isinstance(node, ast.If):
            found.extend(_module_level_pyforge_herald_imports(node.body))
            found.extend(_module_level_pyforge_herald_imports(node.orelse))
        elif isinstance(node, ast.With):
            found.extend(_module_level_pyforge_herald_imports(node.body))
    return found


def _iter_module_level_stmts(body: list[ast.stmt]):
    for node in body:
        yield node
        if isinstance(node, ast.Try):
            yield from _iter_module_level_stmts(node.body)
            yield from _iter_module_level_stmts(node.orelse)
            yield from _iter_module_level_stmts(node.finalbody)
            for handler in node.handlers:
                yield from _iter_module_level_stmts(handler.body)
        elif isinstance(node, ast.If):
            yield from _iter_module_level_stmts(node.body)
            yield from _iter_module_level_stmts(node.orelse)
        elif isinstance(node, ast.With):
            yield from _iter_module_level_stmts(node.body)


def _portal_path_for_module(root: Path, dotted: str) -> Path | None:
    if not dotted.startswith(_PORTAL_PKG):
        return None
    rel = dotted.removeprefix(f"{_PORTAL_PKG}.").replace(".", "/")
    if not rel:
        init = _portal_root(root) / "__init__.py"
        return init if init.is_file() else None
    path = _portal_root(root) / f"{rel}.py"
    if path.is_file():
        return path
    init = _portal_root(root) / rel / "__init__.py"
    return init if init.is_file() else None


def _follow_imports(root: Path, path: Path) -> list[Path]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    discovered: list[Path] = []
    for node in _iter_module_level_stmts(tree.body):
        if isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                if node.module == _PORTAL_PKG:
                    for alias in node.names:
                        if alias.name == "*":
                            continue
                        sub = _portal_root(root) / f"{alias.name}.py"
                        if sub.is_file():
                            discovered.append(sub)
                else:
                    resolved = _portal_path_for_module(root, node.module)
                    if resolved is not None:
                        discovered.append(resolved)
            elif node.level >= 1:
                base = path.parent
                for _ in range(node.level - 1):
                    base = base.parent
                if node.module:
                    resolved = _portal_path_for_module(root, f"{_PORTAL_PKG}.{node.module}")
                    if resolved is not None:
                        discovered.append(resolved)
                else:
                    for alias in node.names:
                        if alias.name == "*":
                            continue
                        candidate = base / f"{alias.name}.py"
                        if candidate.is_file():
                            discovered.append(candidate)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                resolved = _portal_path_for_module(root, alias.name)
                if resolved is not None:
                    discovered.append(resolved)
    return discovered


def test_portal_urlconf_reach_has_no_module_level_pyforge_herald_import() -> None:
    root = _repo_root()
    urls = _portal_root(root) / "urls.py"
    queue = [urls]
    seen: set[Path] = set()
    offenders: list[str] = []
    while queue:
        path = queue.pop(0)
        if path in seen:
            continue
        seen.add(path)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        hits = _module_level_pyforge_herald_imports(tree.body)
        if hits:
            offenders.extend(f"{path.relative_to(root)}: {hit}" for hit in hits)
        for nxt in _follow_imports(root, path):
            if nxt not in seen:
                queue.append(nxt)
    assert offenders == []
