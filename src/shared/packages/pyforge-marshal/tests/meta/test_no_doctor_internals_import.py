"""Story 115.2 (spec-pyforge-marshal CAP-261 (b)): no marshal module imports ``pyforge.doctor``.

Doctor is reached through its command, ``python -m pyforge.doctor.sources ...``, run by
``adapters/doctor_cli.py`` through a ``ProcessPort`` -- never through an import of its internals
(AGENTS.md: reach another station through its CLI grammar). There is no exempt module: the adapter
runs Doctor's command in a child process and imports nothing of Doctor's either.

AST-scans every module in the installed package, the technique ``test_no_steward_internals_import.py``
and ``test_no_engine_or_scribe_internals_import.py`` use, so a function-local import (the shape the
landing's in-process read had) is caught as well as a module-level one. Same stated bound as those: a
dynamic ``importlib.import_module("pyforge.doctor...")`` is out of scope.
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

_DOCTOR = "pyforge.doctor"


def _package_modules() -> list[Path]:
    return sorted(PACKAGE_DIR.rglob("*.py"))


def _module_id(path: Path) -> str:
    return str(path.relative_to(PACKAGE_DIR))


def _is_doctor(module_name: str) -> bool:
    return module_name == _DOCTOR or module_name.startswith(f"{_DOCTOR}.")


def _doctor_imports(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names if _is_doctor(alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.level != 0 or node.module is None:
                continue
            if _is_doctor(node.module):
                found.append(node.module)
    return found


def _offenders(paths: list[Path], root: Path) -> list[str]:
    """Every module under ``root`` that imports Doctor, named as ``<relative path>: <module>``."""
    named: list[str] = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        named.extend(f"{path.relative_to(root)}: {module}" for module in _doctor_imports(tree))
    return named


def test_the_scan_surface_is_the_whole_package_and_holds_the_landing_and_its_adapter() -> None:
    modules = {_module_id(path) for path in _package_modules()}
    assert "dispatch_land.py" in modules
    assert str(Path("adapters") / "doctor_cli.py") in modules


@pytest.mark.parametrize("path", _package_modules(), ids=_module_id)
def test_no_marshal_module_imports_pyforge_doctor(path: Path) -> None:
    offenders = _offenders([path], PACKAGE_DIR)
    assert not offenders, (
        f"{offenders} -- reach Doctor through its command (adapters/doctor_cli.py), never an import of pyforge.doctor"
    )


def test_a_synthetic_module_importing_doctors_chain_is_named(tmp_path: Path) -> None:
    """The failing fixture: the guard names the module that imports Doctor, not just that one does."""
    clean = tmp_path / "clean.py"
    clean.write_text("from pyforge.core.process import ProcessPort\n", encoding="utf-8")
    offender = tmp_path / "offender.py"
    offender.write_text(
        "def read(worktree):\n    from pyforge.doctor.sources.chain import x\n    return x(worktree)\n",
        encoding="utf-8",
    )

    assert _offenders([clean, offender], tmp_path) == ["offender.py: pyforge.doctor.sources.chain"]


@pytest.mark.parametrize(
    "source",
    [
        "import pyforge.doctor\n",
        "import pyforge.doctor.sources.chain as chain\n",
        "from pyforge.doctor import models\n",
        "from pyforge.doctor.sources.chain import gather_spec_surface\n",
    ],
)
def test_the_guard_fires_on_every_import_shape(source: str) -> None:
    assert _doctor_imports(ast.parse(source))


def test_the_guard_does_not_fire_on_the_sanctioned_neighbours() -> None:
    """Doctor's command module named in an argv string, ``pyforge.core`` and a look-alike name are not imports."""
    tree = ast.parse(
        "from pyforge.core.process import ProcessPort\n"
        "import pyforge.doctorish\n"
        "ARGV = ('python', '-m', 'pyforge.doctor.sources', 'spec-surface', '--json')\n"
    )
    assert _doctor_imports(tree) == []
