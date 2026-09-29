"""Steward 41.2: query-plane process boundary (BS-5, red-team S-3 / R-11).

The ``.duckdb`` file is never shared across pods: one writer process on RWO
storage; readers use ``read_only=True`` or ``:memory:``; Parquet is the shared
artifact. This module is the estate-wide policy gate — every production
``duckdb.connect(`` outside the single declared writer module must comply.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from pyforge.atlas.duckdb_writer import DUCKDB_WRITER_MODULE

REPO_ROOT = Path(__file__).resolve().parents[6]
PACKAGES_SRC = REPO_ROOT / "src" / "shared" / "packages"
PLATFORM_SRC = REPO_ROOT / "src" / "platform"
WRITER_MODULE = PACKAGES_SRC / "pyforge-atlas" / "src" / "pyforge" / "atlas" / "duckdb_writer.py"
ATLAS_SRC = PACKAGES_SRC / "pyforge-atlas" / "src" / "pyforge" / "atlas"
_ESTATE_SCAN_ROOTS = (PACKAGES_SRC, PLATFORM_SRC)
_SKIP_PARTS = frozenset({"tests", "__pycache__"})


def _estate_python_sources() -> list[Path]:
    out: list[Path] = []
    for root in _ESTATE_SCAN_ROOTS:
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            if any(part in _SKIP_PARTS for part in path.parts):
                continue
            out.append(path)
    return sorted(out)


def _duckdb_connect_calls(tree: ast.Module) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "connect":
            if isinstance(func.value, ast.Name) and func.value.id == "duckdb":
                calls.append(node)
    return calls


def _keyword_bool(call: ast.Call, name: str) -> bool | None:
    for kw in call.keywords:
        if kw.arg == name and isinstance(kw.value, ast.Constant):
            if isinstance(kw.value.value, bool):
                return kw.value.value
    return None


def _first_path_arg(call: ast.Call) -> ast.expr | None:
    if call.args:
        return call.args[0]
    for kw in call.keywords:
        if kw.arg in {"database", "db"}:
            return kw.value
    return None


def _is_memory_target(arg: ast.expr | None) -> bool:
    if arg is None:
        return True
    if isinstance(arg, ast.Constant) and arg.value in {":memory:", "", None}:
        return True
    if isinstance(arg, ast.JoinedStr):
        joined = "".join(
            part.value for part in arg.values if isinstance(part, ast.Constant) and isinstance(part.value, str)
        )
        return joined == ":memory:"
    return False


def _connect_is_compliant(call: ast.Call) -> bool:
    if _is_memory_target(_first_path_arg(call)):
        return True
    return _keyword_bool(call, "read_only") is True


def _violations_for_file(path: Path) -> list[str]:
    try:
        rel = path.relative_to(REPO_ROOT)
    except ValueError:
        rel = path
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []
    for call in _duckdb_connect_calls(tree):
        if path.resolve() == WRITER_MODULE.resolve():
            continue
        if not _connect_is_compliant(call):
            line = getattr(call, "lineno", "?")
            violations.append(f"{rel}:{line} duckdb.connect must use read_only=True or :memory:")
    return violations


def _writer_modules_in_atlas() -> list[Path]:
    hits: list[Path] = []
    for path in ATLAS_SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for call in _duckdb_connect_calls(tree):
            if _keyword_bool(call, "read_only") is False:
                hits.append(path)
                break
    return hits


def test_duckdb_boundary_writer_module_is_declared_once() -> None:
    assert WRITER_MODULE.is_file(), "duckdb_writer.py must exist"
    text = WRITER_MODULE.read_text(encoding="utf-8")
    assert f'DUCKDB_WRITER_MODULE = "{DUCKDB_WRITER_MODULE}"' in text
    writers = _writer_modules_in_atlas()
    assert writers == [WRITER_MODULE], f"expected exactly one atlas writer module, got {[p.name for p in writers]}"


def test_duckdb_boundary_estate_connect_policy() -> None:
    violations: list[str] = []
    for path in _estate_python_sources():
        violations.extend(_violations_for_file(path))
    assert not violations, "duckdb.connect policy violations:\n" + "\n".join(violations)


def test_duckdb_boundary_guard_detects_bare_file_connect(tmp_path: Path) -> None:
    bad = tmp_path / "bad_module.py"
    bad.write_text("import duckdb\ncon = duckdb.connect('/data/atlas.duckdb')\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="read_only=True or :memory:"):
        assert not _violations_for_file(bad)


def test_duckdb_boundary_guard_rejects_string_read_only_false(tmp_path: Path) -> None:
    bad = tmp_path / "bad_string_read_only.py"
    bad.write_text(
        "import duckdb\ncon = duckdb.connect('/data/atlas.duckdb', read_only=\"false\")\n",
        encoding="utf-8",
    )
    with pytest.raises(AssertionError, match="read_only=True or :memory:"):
        assert not _violations_for_file(bad)
