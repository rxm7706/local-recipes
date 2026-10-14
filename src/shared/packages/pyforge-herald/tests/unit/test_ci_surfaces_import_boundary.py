"""Import boundary: herald dossier tile must not reach steward or gh (Story 39.1 AC7)."""

from __future__ import annotations

import ast
from pathlib import Path


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file():
            return candidate
    raise AssertionError("repo root not found")


def _py_files_under(*roots: Path) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        out.extend(p for p in root.rglob("*.py") if p.is_file())
    return out


def _forbidden_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pyforge.steward" or alias.name.startswith("pyforge.steward."):
                    hits.append(f"{path}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module and (
                node.module == "pyforge.steward" or node.module.startswith("pyforge.steward.")
            ):
                hits.append(f"{path}: from {node.module} import ...")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
                if node.func.attr in ("run", "call", "Popen", "check_output", "check_call"):
                    hits.append(f"{path}: subprocess.{node.func.attr}(...)")
    text = path.read_text(encoding="utf-8")
    if " gh " in text or text.strip().startswith("gh ") or "\ngh " in text:
        hits.append(f"{path}: literal gh invocation")
    return hits


def test_no_steward_import_or_gh_in_herald_package_and_docsite() -> None:
    root = _repo_root()
    herald_src = root / "src/shared/packages/pyforge-herald/src/pyforge/herald"
    docsite_build = root / "docsite/build.py"
    docsite_tools = root / "docsite/tools"
    problems: list[str] = []
    for path in _py_files_under(herald_src, docsite_tools):
        if path.name == "export_ci_surfaces_tile_env.py":
            continue
        problems.extend(_forbidden_imports(path))
    problems.extend(_forbidden_imports(docsite_build))
    assert not problems, "\n".join(problems)
