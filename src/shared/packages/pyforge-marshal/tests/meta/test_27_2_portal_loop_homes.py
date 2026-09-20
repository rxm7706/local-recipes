"""Story 27.2: station-owned gates for the marshal portal loop-home list."""

from __future__ import annotations

import ast
from pathlib import Path

from pyforge.testing_kit import changed_paths_since, pyforge_import_offenders

_HTTP_TOPLEVEL = frozenset({"httpx", "requests", "http.client"})
_INGEST_MARKERS = ("supervisor ingest", "bmad-loop ingest")


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + .claude/skills)")


def _portal_tree(root: Path) -> Path:
    return root / "src" / "shared" / "packages" / "django-marshal" / "src" / "django_marshal_portal"


def _iter_py(tree: Path) -> list[Path]:
    return sorted(path for path in tree.rglob("*.py") if path.is_file())


def test_marshal_portal_lists_via_portal_client_only():
    views = _portal_tree(_repo_root()) / "views.py"
    text = views.read_text(encoding="utf-8")
    assert "from django_pyforge.assertion.client import PortalClient" in text
    assert "PortalClient().list_loop_homes()" in text
    assert "urllib.request" not in text
    assert "httpx" not in text
    assert "requests" not in text


def test_marshal_portal_does_not_import_pyforge_or_raw_http():
    offenders: list[str] = []
    for path in _iter_py(_portal_tree(_repo_root())):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if (
                        top in _HTTP_TOPLEVEL
                        or alias.name.startswith("http.client")
                        or alias.name == "urllib.request"
                        or alias.name == "pyforge"
                        or alias.name.startswith("pyforge.")
                    ):
                        offenders.append(f"{path}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                top = module.split(".")[0]
                if top in _HTTP_TOPLEVEL or top == "pyforge" or module.startswith(("urllib.request", "http.client")):
                    offenders.append(f"{path}: from {module}")
    assert offenders == []


def test_marshal_portal_does_not_copy_chrome():
    home = _portal_tree(_repo_root()) / "templates" / "marshal_portal" / "home.html"
    text = home.read_text(encoding="utf-8")
    assert '{% extends "django_pyforge/base.html" %}' in text
    assert 'id="pyforge-chrome"' not in text
    assert "django_pyforge/switcher.html" not in text


def test_diff_does_not_add_bmad_loop_ingest():
    root = _repo_root()
    changed = changed_paths_since(root)
    offenders: list[str] = []
    for rel in changed:
        path = root / rel
        if not path.is_file() or path.suffix not in {".py", ".md"}:
            continue
        if "test_" in rel:
            continue
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        prohibits = "do not implement" in lowered or "never" in lowered or "no bmad-loop ingest" in lowered
        if any(marker in text for marker in _INGEST_MARKERS) and not prohibits:
            offenders.append(rel)
        if rel.endswith(".py") and "supervisor" in rel and "src/platform" in rel:
            offenders.append(rel)
    assert not offenders, f"bmad-loop ingest appeared: {offenders}"


def test_src_platform_diff_has_no_pyforge_import():
    root = _repo_root()
    changed = changed_paths_since(root, pathspec="src/platform")
    assert not pyforge_import_offenders(changed, root)
