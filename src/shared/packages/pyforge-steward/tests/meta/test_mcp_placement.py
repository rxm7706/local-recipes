"""Where a station's MCP code lives (steward Story 143.2, canopy:AD-5 as amended 2026-11-26).

The mounted face is the portal's ``mcp_asgi.py``, in every station. A base package holds MCP server code
only in the two declared cases: atlas (``pyforge.atlas.mcp``, the tool logic the portal's face builds its
server from) and marshal (``pyforge.marshal.mcp``, a stdio server for a local agent). No other portal face
imports its station's package. This reads the repository outside steward's package, so it runs in the
live-tree half.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from pyforge.core.roster import STATIONS

pytestmark = pytest.mark.live_tree

#: station -> why its base package ships MCP server code (canopy:AD-5, the placement clause)
BASE_PACKAGE_SERVERS = {
    "atlas": "the tool logic the portal's face builds its server from",
    "marshal": "a stdio server for a local agent; the portal face does not import it",
}
#: the one portal face that imports its station's package
PORTAL_IMPORTS_STATION = {"atlas"}


def _packages() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pixi.toml").is_file() and (parent / ".claude").is_dir():
            return parent / "src" / "shared" / "packages"
    raise AssertionError("repository root not found")


def _faces(station: str) -> list[Path]:
    return sorted((_packages() / f"django-{station}" / "src").rglob("mcp_asgi.py"))


def _imports_of_pyforge(path: Path) -> set[str]:
    """Every ``pyforge.<x>`` package the module names in an import, at any depth: ``import pyforge.x``,
    ``from pyforge.x import y``, ``from pyforge import x``, and a string literal ``"pyforge.x..."`` (the argument
    of ``importlib.import_module``). It reads this one file: an import a sibling portal module makes is not seen."""
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        names: list[str] = []
        if isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
            if node.module == "pyforge":
                names += [f"pyforge.{alias.name}" for alias in node.names]
        elif isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("pyforge."):
            names.append(node.value)
        for name in names:
            parts = name.split(".")
            if parts[0] == "pyforge" and len(parts) > 1 and parts[1].isidentifier():
                found.add(parts[1])
    return found


def test_the_import_reader_sees_each_form(tmp_path: Path) -> None:
    probe = tmp_path / "probe.py"
    probe.write_text(
        "import pyforge.alpha\nfrom pyforge.beta import x\nfrom pyforge import gamma\n"
        "import importlib\nimportlib.import_module('pyforge.delta.mcp')\n",
        encoding="utf-8",
    )
    assert _imports_of_pyforge(probe) == {"alpha", "beta", "gamma", "delta"}


@pytest.mark.parametrize("station", STATIONS)
def test_every_station_has_exactly_one_portal_face(station: str) -> None:
    assert len(_faces(station)) == 1, f"django-{station} must ship one mcp_asgi.py"


def test_only_the_declared_base_packages_ship_mcp_server_code() -> None:
    shipping = {
        station
        for station in STATIONS
        if (_packages() / f"pyforge-{station}" / "src" / "pyforge" / station / "mcp").is_dir()
    }
    assert shipping == set(BASE_PACKAGE_SERVERS)


@pytest.mark.parametrize("station", STATIONS)
def test_a_portal_face_imports_its_station_only_where_declared(station: str) -> None:
    imported = _imports_of_pyforge(_faces(station)[0]) - {"core"}
    assert imported == ({station} if station in PORTAL_IMPORTS_STATION else set())
