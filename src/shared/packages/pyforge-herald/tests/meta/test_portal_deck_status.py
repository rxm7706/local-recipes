"""Story 17.2: /stations/herald/ renders one slug via PortalClient only."""

from __future__ import annotations

import ast
from pathlib import Path

STATION = "herald"
PORTAL_SLUG = "pyforge-herald"
_HTTP_TOPLEVEL = frozenset({"httpx", "requests", "http.client"})


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (
            candidate / "src" / "shared" / "packages" / "django-herald"
        ).is_dir():
            return candidate
    raise AssertionError("could not locate repo root")


def _portal_root(root: Path) -> Path:
    return root / "src" / "shared" / "packages" / "django-herald" / "src" / "django_herald_portal"


def _iter_py(tree: Path) -> list[Path]:
    return sorted(path for path in tree.rglob("*.py") if path.is_file())


def _raw_http_imports(tree: ast.AST) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if (
                    top in _HTTP_TOPLEVEL
                    or alias.name in _HTTP_TOPLEVEL
                    or alias.name.startswith("http.client")
                    or alias.name == "urllib.request"
                ):
                    found.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            top = module.split(".")[0]
            if (
                top in _HTTP_TOPLEVEL
                or module in _HTTP_TOPLEVEL
                or module.startswith(("urllib.request", "http.client"))
            ):
                found.append(f"from {module} import ...")
    return found


def _pyforge_imports(tree: ast.AST) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(
                f"import {alias.name}"
                for alias in node.names
                if alias.name == "pyforge" or alias.name.startswith("pyforge.")
            )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "pyforge" or module.startswith("pyforge."):
                found.append(f"from {module} import ...")
    return found


def test_portal_uses_portal_client_invoke_only() -> None:
    root = _repo_root()
    views = (_portal_root(root) / "views.py").read_text(encoding="utf-8")
    assert "from django_pyforge.assertion.client import PortalClient" in views
    assert "PortalClient().invoke(" in views
    assert PORTAL_SLUG in views
    assert "deck" in views and "status" in views
    offenders: list[str] = []
    for path in _iter_py(_portal_root(root)):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        offenders.extend(f"{path}: {hit}" for hit in _pyforge_imports(tree))
        offenders.extend(f"{path}: {hit}" for hit in _raw_http_imports(tree))
    assert offenders == []


def test_home_template_is_chrome_projection() -> None:
    root = _repo_root()
    html = (_portal_root(root) / "templates" / "herald_portal" / "home.html").read_text(encoding="utf-8")
    assert '{% extends "django_pyforge/base.html" %}' in html
    assert "herald-deck-status" in html
    assert "herald deck status" in html
    assert "deck_status.slug" in html
    assert "<html" not in html.lower()


def test_this_story_platform_delta_does_not_import_pyforge() -> None:
    root = _repo_root()
    path = root / "src" / "platform" / "tests" / "test_herald_portal_deck_status.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assert _pyforge_imports(tree) == []
