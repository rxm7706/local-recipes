"""Story 11.2 — last diagnose on /stations/mason/ via PortalClient only."""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

from conftest import exclude_cfe_rebuild_equivalence_tests

STATION = "mason"
PORTAL_PKG = "django-mason"
PORTAL_MOD = "django_mason_portal"
_HTTP_TOPLEVEL = frozenset({"httpx", "requests", "http.client"})


class PortalDiagnoseContractError(AssertionError):
    """django-mason last-diagnose surface violates Story 11.2."""


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    raise AssertionError("could not locate repo root")


def _portal_root(root: Path) -> Path:
    return root / "src" / "shared" / "packages" / PORTAL_PKG / "src" / PORTAL_MOD


def _iter_py(tree: Path) -> list[Path]:
    return sorted(path for path in tree.rglob("*.py") if path.is_file())


def _git_diff_names(*paths: str) -> list[str]:
    root = _repo_root()
    named = subprocess.check_output(
        ["git", "diff", "--name-only", "origin/main", "--", *paths],
        cwd=root,
        text=True,
    )
    return [line for line in named.splitlines() if line.strip()]


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


def test_chrome_home_calls_portal_client_last_diagnose():
    views = (_portal_root(_repo_root()) / "views.py").read_text(encoding="utf-8")
    if "PortalClient" not in views or "last_diagnose" not in views:
        raise PortalDiagnoseContractError("chrome_home must call PortalClient.last_diagnose")
    if "require_station_role" not in views or '"mason"' not in views:
        raise PortalDiagnoseContractError("chrome_home must stay mason-role gated")


def test_home_template_renders_last_diagnose_in_host_chrome():
    root = _repo_root()
    html = (
        _portal_root(root) / "templates" / "mason_portal" / "home.html"
    ).read_text(encoding="utf-8")
    if 'id="mason-last-diagnose"' not in html:
        raise PortalDiagnoseContractError("home template must render #mason-last-diagnose")
    if '{% extends "django_pyforge/base.html" %}' not in html:
        raise PortalDiagnoseContractError("mason must extend host chrome, not copy it")
    chrome = (
        root
        / "src"
        / "shared"
        / "packages"
        / "django-pyforge"
        / "src"
        / "django_pyforge"
        / "templates"
        / "django_pyforge"
        / "base.html"
    ).read_text(encoding="utf-8")
    if "pyforge-chrome" in html and html.count("pyforge-chrome") >= chrome.count(
        "pyforge-chrome",
    ):
        raise PortalDiagnoseContractError("mason copied host chrome into the station template")


def test_django_mason_has_no_raw_http_pyforge_or_minio():
    root = _portal_root(_repo_root())
    offenders: list[str] = []
    for path in _iter_py(root):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        offenders.extend(f"{path.name}: {hit}" for hit in _raw_http_imports(tree))
        offenders.extend(f"{path.name}: {hit}" for hit in _pyforge_imports(tree))
        lowered = text.lower()
        if "import minio" in lowered or "from minio" in lowered:
            offenders.append(f"{path.name}: minio import")
    assert not offenders, offenders


def test_cfe_not_replaced_and_claude_agents_untouched():
    named_cfe = exclude_cfe_rebuild_equivalence_tests(
        _repo_root(), _git_diff_names(".claude/skills/conda-forge-expert")
    )
    named_docs = _git_diff_names("CLAUDE.md", "AGENTS.md")
    assert not named_cfe, f"must not replace CFE: {named_cfe}"
    assert not named_docs, f"must not edit CLAUDE.md/AGENTS.md: {named_docs}"


def test_story_does_not_add_pyforge_under_src_platform():
    root = _repo_root()
    changed = _git_diff_names("src/platform")
    offenders: list[str] = []
    for rel in changed:
        path = root / rel
        if path.suffix != ".py" or not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".", maxsplit=1)[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".", maxsplit=1)[0]]
            if "pyforge" in names:
                offenders.append(f"{rel}:{node.lineno}")
    assert not offenders, f"src/platform pyforge imports: {changed} {offenders}"
