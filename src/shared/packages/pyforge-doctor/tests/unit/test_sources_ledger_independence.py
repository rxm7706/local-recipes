"""``sources/ledger.py`` must never import ``pyforge.marshal`` (or any other
station package).

Mirrors ``test_sources_marshal_independence.py`` exactly, retargeted at the
second Story 6.4 module: Charter §6 ratified 2026-07-28 says *"the Doctor
holds the verdict on the Marshal's conformance — the one station that would
otherwise grade itself,"* and *"the Marshal may not weaken, re-threshold or
disable a check that judges the Marshal."* A ledger-regression verdict
assembled from Marshal's own code would be Marshal's self-report wearing
Doctor's badge, and would fail in exactly the case that matters — when
Marshal's own machinery is what broke. Reading the durable artifacts
(tracked ledgers at two revisions, via git) instead means the check keeps
working when ``pyforge.marshal`` is absent, broken, or wrong.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SOURCE = (Path(__file__).resolve().parents[2]
          / "src" / "pyforge" / "doctor" / "sources" / "ledger.py")


def _imported_modules(tree: ast.AST) -> set[str]:
    """Every module named by an import, including inside function bodies — a lazy
    import in ``gather()`` would evade a module-header-only scan, and lazy is exactly
    how ``sources/warden.py`` legitimately imports warden."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:                     # relative: ..models etc, never a station
                continue
            if node.module:
                names.add(node.module)
    return names


def test_source_exists() -> None:
    assert SOURCE.is_file(), f"{SOURCE} is missing"


def test_never_imports_pyforge_marshal() -> None:
    """The judged station's package must not be reachable from the judging module."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    offenders = sorted(
        m for m in _imported_modules(tree)
        if m == "pyforge.marshal" or m.startswith("pyforge.marshal.")
    )
    assert not offenders, (
        "sources/ledger.py imports the station it judges: "
        f"{offenders}. Charter §6 — Doctor holds the verdict on Marshal's own row "
        "precisely so Marshal cannot grade itself. Read the durable artifacts "
        "(tracked ledgers + git), never Marshal's code."
    )


def test_imports_no_station_package_at_all() -> None:
    """Broader than the rule strictly needs, and deliberately so: reaching into ANY
    sibling station would make this verdict depend on the fleet being healthy, when
    its entire job is to report on a fleet that is not."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    stations = ("herald", "marshal", "atlas", "warden",
                "mason", "doctor", "scribe", "steward")
    offenders = sorted(
        m for m in _imported_modules(tree)
        if any(m == f"pyforge.{s}" or m.startswith(f"pyforge.{s}.") for s in stations)
    )
    assert not offenders, (
        f"sources/ledger.py imports station package(s) {offenders}; it must depend "
        "only on the stdlib and Doctor's own models."
    )


@pytest.mark.parametrize("forbidden", ["pyforge.marshal", "pyforge_marshal"])
def test_no_textual_reference_that_would_execute(forbidden: str) -> None:
    """Catches an import smuggled past the AST scan — ``importlib.import_module``,
    ``__import__``, or a subprocess invoking the CLI. Comments and docstrings are
    stripped first, since this module's own docstring names ``pyforge.marshal``
    repeatedly while explaining why it must not import it."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))

    # Collect docstring nodes so they can be excluded: this module's own docstring
    # names the judged package repeatedly while explaining why it must not import it,
    # and the first cut of this test failed on exactly that. A docstring cannot
    # execute; only a non-docstring string constant could be fed to import_module.
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef,
                             ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                docstrings.add(id(body[0].value))

    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in docstrings):
            assert forbidden not in node.value, (
                f"a string constant in sources/ledger.py contains {forbidden!r}, "
                "which could be used to import or invoke the judged station "
                "dynamically. Charter §6 forbids Marshal grading itself."
            )
