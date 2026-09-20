"""Story 10.2 — PortalClient-only audit start/get; no raw HTTP / chrome / verdict."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from pyforge.testing_kit import changed_paths_since, pyforge_import_offenders

STATION = "warden"
_HTTP_TOPLEVEL = frozenset({"httpx", "requests", "http.client"})
_CHROME_COPY = re.compile(r"(^|/)(base\.html|switcher\.html|theme\.css)$", re.IGNORECASE)
_SECOND_VERDICT = (
    "verdict",
    "exit_code",
    "policy-violation",
    "ComplianceReport",
    "pr-gate",
    "pr_gate",
)
_ATLAS_TOOL_NAMES = frozenset({"start_run_pipeline", "get_run"})


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + .claude/skills)")


def _warden_fabric(root: Path) -> Path:
    return root / "src" / "shared" / "packages" / "django-warden" / "src" / "django_warden_fabric"


def _client_path(root: Path) -> Path:
    return (
        root / "src" / "shared" / "packages" / "django-pyforge" / "src" / "django_pyforge" / "assertion" / "client.py"
    )


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
            from_urllib = any(alias.name == "request" for alias in node.names)
            if module == "urllib" and from_urllib:
                found.append("from urllib import request")
            from_http_client = any(alias.name == "client" for alias in node.names)
            if module == "http" and from_http_client:
                found.append("from http import client")
    return found


def _pyforge_package_imports(tree: ast.AST) -> list[str]:
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


def _fn(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"missing function {name}")


def _calls_portal_client(fn: ast.FunctionDef, method: str) -> bool:
    saw_client = False
    saw_method = False
    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and node.id == "PortalClient":
            saw_client = True
        if isinstance(node, ast.Attribute) and node.attr == method:
            saw_method = True
    return saw_client and saw_method


def test_portal_views_use_portal_client_only():
    root = _repo_root()
    views = _warden_fabric(root) / "views.py"
    tree = ast.parse(views.read_text(encoding="utf-8"))
    assert _raw_http_imports(tree) == []
    assert "/stations/warden/mcp" not in views.read_text(encoding="utf-8")
    assert _calls_portal_client(_fn(tree, "start_audit"), "start")
    assert _calls_portal_client(_fn(tree, "get_audit"), "get")


def test_portal_client_start_get_do_not_open_http():
    root = _repo_root()
    path = _client_path(root)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assert _raw_http_imports(tree) == []
    names = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
    assert "PortalClient" in names
    client = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "PortalClient")
    methods = {node.name for node in client.body if isinstance(node, ast.FunctionDef)}
    assert {"emit", "start", "get"} <= methods
    source = path.read_text(encoding="utf-8")
    assert "publish_start" in source
    assert "supervisor_get_run" in source or "get_run" in source


def test_warden_mcp_owns_start_audit_get_audit_not_atlas_names():
    root = _repo_root()
    path = _warden_fabric(root) / "mcp_asgi.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    defined = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert "start_audit" in defined
    assert "get_audit" in defined
    assert "run_audit" in defined
    assert not (defined & _ATLAS_TOOL_NAMES)
    apps = (_warden_fabric(root) / "apps.py").read_text(encoding="utf-8")
    assert "build_warden_mcp_asgi" in apps
    assert "asgi_for_station" not in apps


def test_run_audit_is_not_a_second_pr_gate_verdict():
    root = _repo_root()
    path = _warden_fabric(root) / "mcp_asgi.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    fn = _fn(tree, "run_audit")
    source = ast.unparse(fn)
    lowered = source.lower()
    for marker in _SECOND_VERDICT:
        assert marker.lower() not in lowered, marker
    assert _pyforge_package_imports(fn) == []


def test_no_chrome_copy_in_warden_portal():
    root = _repo_root()
    fabric = _warden_fabric(root)
    chrome = fabric / "templates" / "warden_fabric" / "chrome.html"
    text = chrome.read_text(encoding="utf-8")
    assert 'extends "django_pyforge/base.html"' in text
    offenders = [
        str(path.relative_to(root))
        for path in fabric.rglob("*")
        if path.is_file() and _CHROME_COPY.search(path.as_posix())
    ]
    assert offenders == []


def test_src_platform_has_no_pyforge_import():
    root = _repo_root()
    changed = changed_paths_since(
        root,
        pathspec="src/platform",
        include_untracked=True,
        always_include=("src/platform/tests/test_warden_portal_audit_start_get.py",),
    )
    offenders = pyforge_import_offenders(changed, root)
    assert not offenders, f"src/platform pyforge imports in this diff: {changed} {offenders}"
