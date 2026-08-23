"""Meta test -- P-01's write-primitive guard (Story 12.4, architecture AD-61).

AST-scan every module under ``pyforge.marshal.seed`` EXCEPT ``seed/fs.py``
and fail if any of them performs a target-repo write through a forbidden
primitive:

- ``open(..., <write mode>)`` (any mode containing ``w``, ``a``, ``x``, or
  ``+``)
- ``Path.write_text`` / ``Path.write_bytes``
- ``shutil.copy*`` (``copy``, ``copy2``, ``copyfile``, …)
- ``os.remove`` / ``os.rename`` / ``os.replace``

Mirrors ``tests/meta/test_p02_copier_sole_ownership.py``'s AST technique.
``seed/fs.py`` is the sole owner of guarded target-repo writes; every other
``seed/`` module must route through ``fs.write`` / ``fs.replace_span`` /
``fs.remove`` / ``fs.symlink`` instead.

Bounds (stated, not aspirational): ``shutil.rmtree`` on a Copier staging
directory (``seed/engine/copier.py``) is deliberately out of scope -- the
AC names ``shutil.copy*`` only, not every ``shutil`` entry point. Likewise
``plan/build.py::write_plan``'s direct ``atomic_write_bytes`` call for
``.marshal/plan.json`` is out of scope for the same reason the AC lists
explicit call shapes rather than "any byte written anywhere". Dynamic
dispatch and docstring prose mentioning forbidden names are out of scope.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import pyforge.marshal

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent
_SEED_DIR = PACKAGE_DIR / "seed"
_FS_MODULE = _SEED_DIR / "fs.py"

_WRITE_MODES = frozenset("wax+")


def _seed_modules() -> list[Path]:
    return sorted(path for path in _SEED_DIR.rglob("*.py") if path != _FS_MODULE)


def _module_id(path: Path) -> str:
    return str(path.relative_to(PACKAGE_DIR))


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _is_write_open_mode(mode: str | None) -> bool:
    if not mode:
        return False
    return any(ch in mode for ch in _WRITE_MODES)


def _write_primitive_violations(tree: ast.Module) -> list[str]:
    violations: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func

        if isinstance(func, ast.Name) and func.id == "open":
            mode: str | None = None
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                value = node.args[1].value
                mode = value if isinstance(value, str) else None
            for kw in node.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    value = kw.value.value
                    mode = value if isinstance(value, str) else None
            if _is_write_open_mode(mode):
                violations.append(f"open(..., {mode!r}) at line {node.lineno}")

        if isinstance(func, ast.Attribute):
            if func.attr in {"write_text", "write_bytes"}:
                violations.append(f".{func.attr} at line {node.lineno}")
            if isinstance(func.value, ast.Name):
                if func.value.id == "os" and func.attr in {"remove", "rename", "replace"}:
                    violations.append(f"os.{func.attr} at line {node.lineno}")
                if func.value.id == "shutil" and func.attr.startswith("copy"):
                    violations.append(f"shutil.{func.attr} at line {node.lineno}")

    return violations


def test_seed_scan_surface_is_not_empty():
    modules = _seed_modules()
    assert modules, "P-01 guard found no seed modules to scan outside fs.py"
    assert _FS_MODULE.exists(), "seed/fs.py missing from the installed package"


@pytest.mark.parametrize("module_path", _seed_modules(), ids=_module_id)
def test_no_forbidden_write_primitives_outside_fs(module_path: Path):
    violations = _write_primitive_violations(_parse(module_path))
    assert not violations, (
        f"{_module_id(module_path)} uses forbidden write primitive(s): "
        + "; ".join(violations)
        + " -- only seed/fs.py may (P-01)"
    )


def test_guard_is_alive_on_synthetic_violations():
    assert _write_primitive_violations(ast.parse("open('x', 'w')\n"))
    assert _write_primitive_violations(ast.parse("from pathlib import Path\nPath('x').write_text('')\n"))
    assert _write_primitive_violations(ast.parse("import shutil\nshutil.copy2('a', 'b')\n"))
    assert _write_primitive_violations(ast.parse("import os\nos.remove('x')\n"))
    assert _write_primitive_violations(ast.parse("open('x', 'r')\n")) == []
    assert _write_primitive_violations(ast.parse("import shutil\nshutil.rmtree('x')\n")) == []


def test_fs_module_itself_uses_guarded_primitives():
    """fs.py is the sole owner — it *may* use the primitives this scan bans elsewhere."""
    source = _FS_MODULE.read_text(encoding="utf-8")
    assert "atomic_write_bytes" in source
    assert "os.replace" in source
    # Detector must still *see* those primitives when pointed at fs.py (aliveness).
    assert _write_primitive_violations(_parse(_FS_MODULE))
