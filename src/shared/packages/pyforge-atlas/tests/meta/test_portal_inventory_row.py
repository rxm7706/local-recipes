"""Story 19.2 — PortalClient only; no raw HTTP; no chrome copy."""

from __future__ import annotations

import ast
from pathlib import Path

STATION_PORTAL = Path("src/shared/packages/django-atlas/src/django_atlas_portal")
VIEWS = STATION_PORTAL / "views.py"
CHROME_COPY_NAMES = frozenset({"base.html", "switcher.html", "theme.css"})
_HTTP_TOPLEVEL = frozenset({"httpx", "requests", "http.client"})


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (
            (candidate / "pixi.toml").is_file()
            and (candidate / ".claude" / "skills" / "conda-forge-expert").is_dir()
            and (candidate / "src" / "shared" / "packages").is_dir()
        ):
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + .claude/skills)")


def _iter_py(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if path.is_file())


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
                    or alias.name == "urllib"
                    or alias.name.startswith("urllib.")
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
            from_urllib = any(alias.name == "request" for alias in node.names)
            if module == "urllib" and from_urllib:
                found.append("from urllib import request")
            from_http_client = any(alias.name == "client" for alias in node.names)
            if module == "http" and from_http_client:
                found.append("from http import client")
    return found


def _imports_portal_client(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "django_pyforge.assertion.client" and any(
                alias.name == "PortalClient" for alias in node.names
            ):
                return True
        if isinstance(node, ast.Import) and any(
            alias.name == "django_pyforge.assertion.client" for alias in node.names
        ):
            return True
    return False


def test_portal_client_import_is_present() -> None:
    root = _repo_root()
    source = (root / VIEWS).read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert _imports_portal_client(tree)
    assert "PortalClient().emit(" in source


def test_atlas_portal_has_no_raw_http() -> None:
    root = _repo_root()
    offenders: list[str] = []
    for path in _iter_py(root / STATION_PORTAL):
        hits = _raw_http_imports(ast.parse(path.read_text(encoding="utf-8")))
        offenders.extend(f"{path}: {hit}" for hit in hits)
    assert offenders == []


def test_atlas_portal_does_not_copy_chrome() -> None:
    root = _repo_root()
    copied = [
        str(path.relative_to(root))
        for path in (root / STATION_PORTAL).rglob("*")
        if path.is_file() and path.name in CHROME_COPY_NAMES
    ]
    assert copied == []
