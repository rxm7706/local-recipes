"""Import boundary: herald's dossier tile and status pages never reach steward or gh (Story 39.1 AC7; Story 42.1).

Since Story 43.7 the tile and the status pages are shaped in ``docs-site/`` (``src/lib/status.ts``), reading steward's
JSON as data; the herald package keeps the flag readers. Neither imports a station nor runs ``gh``.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[6]


def _forbidden(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            hits += [f"{path}: import {a.name}" for a in node.names if a.name.split(".")[:2] == ["pyforge", "steward"]]
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[:2] == ["pyforge", "steward"]:
            hits.append(f"{path}: from {node.module} import ...")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
                first = node.args[0] if node.args else None
                words = [e.value for e in getattr(first, "elts", []) if isinstance(e, ast.Constant)]
                if words[:1] == ["gh"]:
                    hits.append(f"{path}: subprocess.{node.func.attr} invokes gh")
    return hits


def test_no_steward_import_or_gh_in_the_herald_package() -> None:
    herald_src = REPO_ROOT / "src/shared/packages/pyforge-herald/src/pyforge/herald"
    problems = [hit for path in sorted(herald_src.rglob("*.py")) for hit in _forbidden(path)]
    assert not problems, "\n".join(problems)


def test_no_process_and_no_station_in_the_docs_site_status_code() -> None:
    docs_site = REPO_ROOT / "docs-site"
    for rel in (
        "src/lib/status.ts",
        "src/lib/flags.ts",
        "src/pages/status/[...index].astro",
        "src/pages/status/ci/[...index].astro",
    ):
        text = (docs_site / rel).read_text(encoding="utf-8")
        assert "child_process" not in text and not re.search(r"['\"]gh['\"]", text), rel
