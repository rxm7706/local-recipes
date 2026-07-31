"""Meta test -- AD-3/AD-4 import-linter contracts (Story 1.1).

Invokes the real ``lint-imports`` CLI (import-linter, provisioned in the
root ``pixi.toml``'s ``[feature.pyforge-marshal.dependencies]``) against
this package's own ``pyproject.toml`` and asserts both contracts are KEPT
against the installed package. Separately parses the same
``pyproject.toml`` to assert the two contracts' declared
``source_modules``/``forbidden_modules`` are exactly what AD-3/AD-4
require -- so a future edit that silently narrows or widens either
contract's scope is caught even if the tree at the time still happens to
pass the live check.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_PYPROJECT = _PACKAGE_ROOT / "pyproject.toml"
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _contracts() -> list[dict]:
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    return data["tool"]["importlinter"]["contracts"]


def _contract_forbidding(forbidden_module: str) -> dict:
    # .get: a future contract of another import-linter type (e.g. "layers")
    # has no forbidden_modules key -- skip it instead of KeyError-ing and
    # masking the real assertion.
    for contract in _contracts():
        if forbidden_module in contract.get("forbidden_modules", []):
            return contract
    raise AssertionError(f"no contract forbids {forbidden_module!r}")


def test_pyproject_declares_exactly_two_contracts():
    assert len(_contracts()) == 2


def test_ad4_core_purity_contract_shape():
    contract = _contract_forbidding("subprocess")
    assert contract["type"] == "forbidden"
    assert contract["source_modules"] == ["pyforge.marshal.core"]
    assert set(contract["forbidden_modules"]) == {
        "subprocess",
        "os",
        "time",
        "pyforge.marshal.adapters",
    }


def test_ad3_harness_seam_contract_shape():
    contract = _contract_forbidding("bmad_loop")
    assert contract["type"] == "forbidden"
    assert set(contract["source_modules"]) == {
        "pyforge.marshal.cli",
        "pyforge.marshal.core",
        "pyforge.marshal.ports",
        "pyforge.marshal.supervisor",
    }
    assert contract["forbidden_modules"] == ["bmad_loop"]
    # AD-3's own documented scope gap (architecture.md Design Notes): the
    # whole `adapters` package is deliberately excluded from source_modules
    # -- including it would also forbid harness_bmadloop.py, the one module
    # this contract must allow to import bmad_loop.
    assert "pyforge.marshal.adapters" not in contract["source_modules"]


def _installed_package_dir() -> Path:
    import pyforge.marshal

    package_file = pyforge.marshal.__file__
    assert package_file is not None
    return Path(package_file).resolve().parent


def test_ad3_source_modules_cover_every_submodule_except_adapters():
    """The AD-3 contract is enumerative, so a NEW submodule added without
    extending ``source_modules`` would silently sit outside the ``bmad_loop``
    prohibition with every gate green. This complement check derives the
    installed package's importable children itself and makes the omission
    build-breaking: everything except ``adapters`` (the one deliberate
    exclusion -- see test_ad3_harness_seam_contract_shape) must appear.

    Children are ANY directory containing a ``*.py`` anywhere below it (a
    PEP 420 namespace subpackage has no ``__init__.py`` yet still imports --
    keying on ``__init__.py`` would let one slip the net) plus any top-level
    ``*.py`` module beside ``__init__.py`` (e.g. a future
    ``pyforge/marshal/util.py``)."""
    package_dir = _installed_package_dir()
    subpackages = {
        f"pyforge.marshal.{entry.name}"
        for entry in package_dir.iterdir()
        if entry.is_dir() and any(entry.rglob("*.py"))
    }
    top_level_modules = {
        f"pyforge.marshal.{path.stem}"
        for path in package_dir.glob("*.py")
        if path.name != "__init__.py"
    }
    contract = _contract_forbidding("bmad_loop")
    assert set(contract["source_modules"]) == (
        subpackages | top_level_modules
    ) - {"pyforge.marshal.adapters"}


def test_root_package_init_carries_no_imports():
    """``pyforge/marshal/__init__.py`` is the one importable module the AD-3
    complement check above cannot cover: listing ``pyforge.marshal`` itself
    in ``source_modules`` would forbid ``bmad_loop`` for its descendants too,
    ``adapters`` included. The sibling convention keeps the root
    ``__init__.py`` empty -- this makes that convention build-breaking, so
    code (and with it a ``bmad_loop`` import) can never quietly accumulate in
    the seam contract's one blind file."""
    import ast

    init_path = _installed_package_dir() / "__init__.py"
    tree = ast.parse(init_path.read_text(encoding="utf-8"), filename=str(init_path))
    imports = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    assert not imports, (
        f"pyforge/marshal/__init__.py imports at line(s) {imports} -- the "
        "root __init__ sits outside the AD-3 contract's source_modules and "
        "must stay empty (extend the contract before adding code here)"
    )


def test_harness_bmadloop_imports_bmad_loop_lazily_only():
    """``adapters/harness_bmadloop.py``'s module docstring promises
    ``marshal config``/``init``/``homes`` keep working when the installed
    ``bmad_loop`` is broken or absent -- which requires every ``bmad_loop``
    import in that module to live INSIDE a function body, never at module
    top level (``cli/init.py`` imports the module at its own import time).
    The AD-3 contract cannot enforce this (``allow_indirect_imports`` aside,
    it governs WHO may import ``bmad_loop``, not WHEN), so a future
    top-level import would pass import-linter and brick every CLI command at
    import time (review finding, second pass). AST check: no ``Import``/
    ``ImportFrom`` naming ``bmad_loop`` in the module body's top level."""
    import ast

    module_path = _installed_package_dir() / "adapters" / "harness_bmadloop.py"
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    offenders = []
    for node in tree.body:  # top-level statements only -- nested defs are the lazy path
        if isinstance(node, ast.Import):
            if any(alias.name.split(".")[0] == "bmad_loop" for alias in node.names):
                offenders.append(node.lineno)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None and node.module.split(".")[0] == "bmad_loop":
                offenders.append(node.lineno)
    assert not offenders, (
        f"harness_bmadloop.py imports bmad_loop at module top level at "
        f"line(s) {offenders} -- every bmad_loop import must stay lazy "
        "(inside the method that needs it) so the marshal CLI keeps working "
        "when bmad_loop is broken or absent"
    )


def test_lint_imports_passes_against_the_installed_package():
    if shutil.which("lint-imports") is None:
        pytest.fail(
            "lint-imports not on PATH -- run this suite via the env that "
            "provisions import-linter: "
            "`pixi run -e pyforge-marshal pyforge-marshal-test`"
        )
    result = subprocess.run(
        ["lint-imports", "--config", str(_PYPROJECT), "--no-cache"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    stdout = _strip_ansi(result.stdout)
    assert result.returncode == 0, (
        f"lint-imports failed (exit {result.returncode}):\n"
        f"stdout:\n{stdout}\nstderr:\n{_strip_ansi(result.stderr)}"
    )
    # A loose regex, not an exact-substring match on the whole summary line:
    # a future import-linter release reformatting its report (spacing,
    # wording) should not break this test over something unrelated to the
    # contracts themselves. The "2 kept" contract COUNT is separately
    # enforced by test_pyproject_declares_exactly_two_contracts (which reads
    # the config, not lint-imports' stdout) -- this only needs to confirm
    # nothing broke.
    assert re.search(r"\b0\s+broken\b", stdout), (
        f"expected a '0 broken' summary in lint-imports output:\n{stdout}"
    )
