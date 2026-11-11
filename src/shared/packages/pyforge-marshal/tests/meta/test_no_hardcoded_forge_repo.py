"""Story 115.4 (CAP-208) -- marshal holds no repository slug, in code or comment.

The forge repository marshal addresses is the root of record's, read at each use through
``adapters/forge_root.py`` from core's slug table (``pyforge.core.cutover_root.FORGE_SLUGS``). This
guard reads every text file of this package's own sources and names each line that spells one of
that table's slugs, docstrings and comments included. The pattern is built from the table, so a
root added there is guarded here with no edit, and this file spells no slug itself.

The planted-literal tests are its proof that it can fail: a slug in a temp module's code line, and
the same slug in a comment, are each one offender; a module without one is none.

This is the package half: it reads only this package's own sources and ``tmp_path``.
"""

from __future__ import annotations

import re
from pathlib import Path

from pyforge.core.cutover_root import FORGE_SLUGS

import pyforge.marshal

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
MARSHAL_SRC = Path(_PACKAGE_FILE).resolve().parent
_SLUG = re.compile("|".join(re.escape(slug) for slug in sorted(FORGE_SLUGS.values())))


def _scan_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    return [
        f"{path}:{number}: {line.strip()}" for number, line in enumerate(text.splitlines(), 1) if _SLUG.search(line)
    ]


def _scan_tree(root: Path) -> list[str]:
    offenders: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            offenders.extend(_scan_file(path))
    return offenders


def test_the_slug_table_is_non_empty_so_the_guard_is_not_vacuous() -> None:
    assert len(FORGE_SLUGS) >= 2
    assert all("/" in slug for slug in FORGE_SLUGS.values())


def test_the_scan_surface_is_this_package() -> None:
    sources = [path for path in MARSHAL_SRC.rglob("*.py") if "__pycache__" not in path.parts]
    assert MARSHAL_SRC / "adapters" / "forge_root.py" in sources
    assert len(sources) > 100


def test_no_repository_slug_in_marshal_src() -> None:
    assert _scan_tree(MARSHAL_SRC) == []


def test_the_guard_fails_on_a_planted_slug_literal(tmp_path: Path) -> None:
    for root, slug in sorted(FORGE_SLUGS.items()):
        module = tmp_path / root / "planted.py"
        module.parent.mkdir()
        module.write_text(f'_FORGE_REPO = "{slug}"\n', encoding="utf-8")
        assert _scan_tree(module.parent) == [f'{module}:1: _FORGE_REPO = "{slug}"']


def test_the_guard_fails_on_a_slug_in_a_comment(tmp_path: Path) -> None:
    slug = FORGE_SLUGS["local-recipes"]
    module = tmp_path / "commented.py"
    module.write_text(f"# gh pr create needs --repo {slug}\nVALUE = 1\n", encoding="utf-8")
    assert _scan_tree(tmp_path) == [f"{module}:1: # gh pr create needs --repo {slug}"]


def test_a_module_without_a_slug_is_clean(tmp_path: Path) -> None:
    (tmp_path / "clean.py").write_text("from .adapters.forge_root import forge_repo\nREPO = forge_repo()\n")
    assert _scan_tree(tmp_path) == []
