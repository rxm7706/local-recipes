"""Meta — only ``preserve_refs`` may embed the ``refs/tags/preserve/`` grammar (Story 87.3)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[6]
_SCAN_ROOTS = (_REPO_ROOT / "src", _REPO_ROOT / "scripts")
_SOLE_MODULE = _REPO_ROOT / "src/shared/packages/pyforge-core/src/pyforge/core/preserve_refs.py"
_PATTERN = re.compile(r"refs/tags/preserve/")


def _py_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    paths: list[Path] = []
    for p in root.rglob("*.py"):
        if not p.is_file():
            continue
        if any(part == "tests" for part in p.relative_to(root).parts):
            continue
        paths.append(p)
    return sorted(paths)


@pytest.mark.parametrize("root", _SCAN_ROOTS)
def test_no_foreign_preserve_ref_grammar(root: Path):
    violations: list[str] = []
    for path in _py_files(root):
        if path.resolve() == _SOLE_MODULE.resolve():
            continue
        text = path.read_text(encoding="utf-8")
        if _PATTERN.search(text):
            violations.append(str(path.relative_to(_REPO_ROOT)))
    assert not violations, "refs/tags/preserve/ grammar outside preserve_refs:\n  " + "\n  ".join(violations)


def test_sole_grammar_detector_fires_on_synthetic_violation():
    assert _PATTERN.search('x = "refs/tags/preserve/foo"')


def test_preserve_refs_imports_only_stdlib_and_pyforge_core():
    import ast
    import sys

    tree = ast.parse(_SOLE_MODULE.read_text(encoding="utf-8"), filename=str(_SOLE_MODULE))
    stdlib = sys.stdlib_module_names
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".", 1)[0]
                assert top in stdlib or top == "pyforge", alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            assert node.module is not None
            top = node.module.split(".", 1)[0]
            assert top in stdlib or top == "pyforge", node.module
            if top == "pyforge":
                assert node.module is not None and node.module.startswith("pyforge.core.")
