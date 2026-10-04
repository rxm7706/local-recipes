"""``scripts/fleet_scan.py`` keeps every name its importers use (marshal Story 86.5).

Story 86.5 deleted the retired console generator ``_generate()`` and the readers only it
called (DW-marshal-75-1-2). The script's live importers are Doctor's chain-layers audit
(``sources/board.py``, which loads it as ``gen``), ``scripts/promote_sprint_status.py`` (also
``gen``) and every ``from fleet_scan import ...`` under ``scripts/``. The names they reach are
read from their source here, not listed by hand, so a later deletion that breaks one of them
fails this test.

Loaded the way ``test_fleet_scan_archive.py`` loads it (inline, because this directory runs in
the ``pyforge-ci`` env, where ``pyforge.doctor`` is not importable).
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCAN = _REPO_ROOT / "scripts" / "fleet_scan.py"
_ROSTER = _REPO_ROOT / "docs" / "governance" / "guild-roster.json"
# The importers that hold the loaded script in a variable named `gen`.
_GEN_IMPORTERS = (
    _REPO_ROOT / "src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py",
    _REPO_ROOT / "scripts" / "promote_sprint_status.py",
)
# Deleted by Story 86.5; none may come back without a caller.
_DELETED = (
    "_generate",
    "scan_dreams",
    "scan_specs",
    "build_archived",
    "scan_guild",
    "scan_backlog",
    "dream_chain",
    "DREAM_PROGRAM",
    "_git_date",
    "_decomposed_satellites",
)

pytestmark = pytest.mark.skipif(
    not (_SCAN.is_file() and _ROSTER.is_file() and all(p.is_file() for p in _GEN_IMPORTERS)),
    reason="scripts/fleet_scan.py, its importers and docs/governance/guild-roster.json required",
)


def _load(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    name = "_fleet_scan_consumers"
    spec = importlib.util.spec_from_file_location(name, _SCAN)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # The script prepends its own scripts/ dir to sys.path at import time.
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


def _gen_names(path: Path) -> set[str]:
    """Every ``gen.<name>`` and ``getattr``/``hasattr(gen, "<name>")`` in ``path``."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "gen":
            names.add(node.attr)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"getattr", "hasattr"}
            and len(node.args) >= 2
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == "gen"
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)
        ):
            names.add(node.args[1].value)
    return names


def _imported_names() -> dict[str, set[str]]:
    """``{importer: names}`` for every ``from fleet_scan import ...`` under ``scripts/``."""
    out: dict[str, set[str]] = {}
    for path in sorted((_REPO_ROOT / "scripts").glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module == "fleet_scan":
                out.setdefault(path.name, set()).update(alias.name for alias in node.names)
    return out


def test_every_name_doctor_and_promote_sprint_status_reach_still_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fs = _load(monkeypatch)
    used = {path.name: _gen_names(path) for path in _GEN_IMPORTERS}
    used.update(_imported_names())
    # The scan really found the importers' reach (an empty set would pass vacuously).
    assert {"scan_fleet", "_stage_globs", "_resolve", "REPO_ROOT"} <= used["board.py"]
    assert {"PROJECT_SOURCES", "parse_sprint_status"} <= used["promote_sprint_status.py"]
    assert "parse_sprint_status" in used["deck_facts.py"]
    missing = {importer: sorted(n for n in names if not hasattr(fs, n)) for importer, names in used.items()}
    assert not any(missing.values()), missing


def test_the_retired_generator_and_its_only_caller_readers_are_gone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fs = _load(monkeypatch)
    assert [name for name in _DELETED if hasattr(fs, name)] == []
    assert fs.main() == 2  # the retired write CLI still refuses, nonzero
