"""Meta test -- Story 28.8's Block-If, extended by Story 28.9 (CAP-6):
``graphify`` must not be imported inside ``pyforge.marshal`` either -- the
planning graph lives behind Scribe's ``compile_surface`` extra; a
marshal-private graph is the story's own Block-If.

The story forbids two imports outright:

- ``cocoindex`` **anywhere** in ``pyforge.marshal``. The incremental
  engine lives behind Scribe's ``compile_surface`` extra; a marshal-private
  cocoindex flow is the story's own "Never" bullet. The whole point of
  binding by grammar is that marshal owns no second freshness engine, and
  the cheapest way for that to rot is for a later story to reach for the
  library directly "just this once".
- ``pyforge.scribe`` (any submodule). The pyforge-scribe SKILL.md's own
  contract is "Do not import pyforge.scribe internals; the CLI is the
  public contract", restated by scribe Story 6.2's Design Notes for this
  exact consumer: bind "to this ``scribe index refresh``-shaped CLI grammar
  only, never to ``pyforge.scribe.extras.cocoindex_flow`` internals".
- ``graphify`` **anywhere** in ``pyforge.marshal``. Story 28.9's Block-If:
  the planning corpus graph is consumed through ``scribe recall`` only.

AST-scans every module in the installed package, the same technique
``test_ad65_no_network_stack_imports.py`` and
``test_p02_copier_sole_ownership.py`` use. Same stated bound as those: a
dynamic ``importlib.import_module("cocoindex")`` is out of scope.
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

#: Exact module names (or dotted prefixes) no marshal module may import.
_FORBIDDEN_PREFIXES: tuple[str, ...] = ("cocoindex", "graphify", "pyforge.scribe")


def _package_modules() -> list[Path]:
    return sorted(PACKAGE_DIR.rglob("*.py"))


def _module_id(path: Path) -> str:
    return str(path.relative_to(PACKAGE_DIR))


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _is_forbidden(module_name: str) -> bool:
    return any(module_name == prefix or module_name.startswith(f"{prefix}.") for prefix in _FORBIDDEN_PREFIXES)


def _violations(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names if _is_forbidden(alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.level != 0 or node.module is None:
                continue
            if _is_forbidden(node.module):
                found.append(node.module)
    return found


@pytest.mark.parametrize("path", _package_modules(), ids=_module_id)
def test_no_engine_or_producer_internals_import(path: Path):
    violations = _violations(_parse(path))
    assert not violations, (
        f"{_module_id(path)} imports {sorted(set(violations))} -- Story 28.8's "
        "Block-If: the incremental engine is consumed through the `scribe "
        "index refresh` CLI grammar only (adapters/scribe_cli.py), never by "
        "importing cocoindex or pyforge.scribe"
    )


@pytest.mark.parametrize(
    "source",
    [
        "import cocoindex\n",
        "import cocoindex.flow as f\n",
        "from cocoindex import memo_fingerprint\n",
        "from pyforge.scribe.extras.cocoindex_flow import refresh_incremental\n",
        "import pyforge.scribe\n",
        "import graphify\n",
        "from graphify import god_nodes\n",
    ],
)
def test_guard_is_alive_on_synthetic_offenders(tmp_path: Path, source: str):
    """Vacuity check: the scanner actually fires on each forbidden shape."""
    offender = tmp_path / "offender.py"
    offender.write_text(source, encoding="utf-8")
    assert _violations(_parse(offender))


def test_guard_does_not_fire_on_the_sanctioned_neighbours():
    """``pyforge.core`` (shared primitives) and marshal's own modules are
    not what this guard is about -- a guard that flags them would be
    quietly disabled by the next contributor."""
    tree = ast.parse(
        "from pyforge.core.process import PosixProcess\nfrom pyforge.marshal.core import derived_context\n"
    )
    assert _violations(tree) == []
