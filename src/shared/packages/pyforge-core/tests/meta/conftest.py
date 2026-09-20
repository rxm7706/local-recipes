"""Shared helpers for the ``tests/meta/`` sole-ownership guards (review-pass
patch, Story 14.3).

``_sibling_station_dirs``/``_station_source_files``/``_parse`` were
hand-copied identically into ``test_atomic_write_sole_ownership.py`` (Story
14.2), then into both ``test_verdict_lattice_sole_ownership.py`` and
``test_exception_root_sole_ownership.py`` (Story 14.3) -- three copies of
the same station-enumeration/parse logic. Centralized here; each guard
still owns its OWN detection logic (the part that actually differs).
"""

from __future__ import annotations

import ast
from pathlib import Path

# tests/meta/conftest.py -> parents[3] is src/shared/packages/ (mirrors
# every sibling meta test's identical arithmetic: tests/meta/<file>.py also
# has 2 directory levels between it and this file's own containing dir).
PACKAGES_ROOT = Path(__file__).resolve().parents[3]


def sibling_station_dirs(exclude: frozenset[str] = frozenset()) -> list[Path]:
    """Every ``pyforge-*`` package directory under ``PACKAGES_ROOT`` except
    ``pyforge-core`` itself and any station named in ``exclude`` -- derived
    from the filesystem, never a hardcoded roster (a ninth station needs no
    edit here)."""
    return sorted(
        p
        for p in PACKAGES_ROOT.iterdir()
        if p.is_dir() and p.name.startswith("pyforge-") and p.name != "pyforge-core" and p.name not in exclude
    )


def station_source_files(exclude: frozenset[str] = frozenset()) -> list[Path]:
    files: list[Path] = []
    for station_dir in sibling_station_dirs(exclude=exclude):
        src_pyforge = station_dir / "src" / "pyforge"
        if src_pyforge.is_dir():
            files.extend(sorted(src_pyforge.rglob("*.py")))
    return files


def parse_module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
