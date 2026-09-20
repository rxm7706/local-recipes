"""Story 11.2 — last diagnose on /stations/mason/ via PortalClient only."""

from __future__ import annotations

import ast
from pathlib import Path

from pyforge.testing_kit import (
    changed_paths_since,
    commit_files,
    commits_since,
    pyforge_import_offenders,
    unsanctioned_commits,
)

_CFE_CHANGELOG = ".claude/skills/conda-forge-expert/CHANGELOG.md"

STATION = "mason"
PORTAL_PKG = "django-mason"
PORTAL_MOD = "django_mason_portal"
_HTTP_TOPLEVEL = frozenset({"httpx", "requests", "http.client"})

#: Story 49.14 (CAP-10): boot reconciliation is a real, eager production
#: caller of pyforge.mason.boot at MasonPortalConfig.ready() time -- the
#: capability that story exists to prove is live, not test-only. Same shape
#: as the platform-side boundary exception
#: (test_station_portal_shells.py::_STATION_PYFORGE_ALLOWED["mason"]) --
#: kept here too since this file enforces the identical invariant from
#: mason's own package and was not updated when that one was.
_ALLOWED_PYFORGE_IMPORTS = ("pyforge.mason.boot",)


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


def _pyforge_import_allowed(module: str) -> bool:
    return any(module == prefix or module.startswith(prefix + ".") for prefix in _ALLOWED_PYFORGE_IMPORTS)


def _pyforge_imports(tree: ast.AST) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(
                f"import {alias.name}"
                for alias in node.names
                if (alias.name == "pyforge" or alias.name.startswith("pyforge."))
                and not _pyforge_import_allowed(alias.name)
            )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if (module == "pyforge" or module.startswith("pyforge.")) and not _pyforge_import_allowed(module):
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
    html = (_portal_root(root) / "templates" / "mason_portal" / "home.html").read_text(encoding="utf-8")
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
    # Per commit, not whole-branch: a sanctioned `retro:` CFE commit and a
    # fleet branch's own context-file work are not this story replacing CFE
    # or editing CLAUDE.md/AGENTS.md (2026-09-04, PR #1043).
    root = _repo_root()
    unsanctioned = unsanctioned_commits(
        root, pathspec=".claude/skills/conda-forge-expert", changelog_path=_CFE_CHANGELOG
    )
    assert not unsanctioned, f"must not replace CFE: {unsanctioned}"
    mason_source = "src/shared/packages/pyforge-mason/src"
    docs = ("CLAUDE.md", "AGENTS.md")
    named_docs = [
        f"{sha[:10]} {f}"
        for sha in commits_since(root, pathspec=mason_source, no_merges=True)
        for f in commit_files(root, sha)
        if f in docs
    ]
    assert not named_docs, f"must not edit CLAUDE.md/AGENTS.md: {named_docs}"


def test_story_does_not_add_pyforge_under_src_platform():
    root = _repo_root()
    changed = changed_paths_since(root, pathspec="src/platform")
    offenders = pyforge_import_offenders(changed, root)
    assert not offenders, f"src/platform pyforge imports: {changed} {offenders}"
