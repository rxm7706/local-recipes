"""``sources/chain.py`` must never import ``pyforge.marshal`` (or any other
station package).

Mirrors ``test_sources_ledger_independence.py`` and
``test_sources_board_independence.py`` exactly, retargeted at Story 6.6's
chain module: Charter §6 ratified 2026-07-28 says *"the Doctor holds the
verdict on the Marshal's conformance — the one station that would otherwise
grade itself,"* and *"the Marshal may not weaken, re-threshold or disable a
check that judges the Marshal."* A chain verdict assembled from Marshal's own
code would be Marshal's self-report wearing Doctor's badge, and would fail in
exactly the case that matters — when Marshal's own machinery is what broke.
Reading the durable artifacts (tracked Dreams, Specs, planning trees, ``git
ls-files``, tracked deferred-work ledgers) instead means the check keeps
working when ``pyforge.marshal`` is absent, broken, or wrong.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SOURCE = (Path(__file__).resolve().parents[2]
          / "src" / "pyforge" / "doctor" / "sources" / "chain.py")

#: ``chain.py``'s own dotted package, used to resolve its relative imports.
SOURCE_PACKAGE = ("pyforge", "doctor", "sources")


def _resolve_relative(level: int, module: str | None) -> str | None:
    """A relative import's ABSOLUTE dotted name, as Python itself would
    resolve it from ``chain.py``'s own package.

    Relative imports used to be skipped outright here ("relative: ..models
    etc, never a station"), which was wrong: from
    ``pyforge/doctor/sources/``, level 3 IS the ``pyforge`` namespace, so
    ``from ...marshal import policy`` reaches the judged station and passed
    every test in this file. The textual test cannot catch it either — a
    relative import produces no ``pyforge.marshal`` string constant. Resolve
    instead of waive."""
    base = SOURCE_PACKAGE[:len(SOURCE_PACKAGE) - (level - 1)]
    if len(base) != len(SOURCE_PACKAGE) - (level - 1) or level - 1 > len(SOURCE_PACKAGE):
        return None
    parts = [*base, *(module.split(".") if module else [])]
    return ".".join(parts) if parts else None


def _imported_modules(tree: ast.AST) -> set[str]:
    """Every module named by an import, including inside function bodies — a lazy
    import in a gather would evade a module-header-only scan, and lazy is exactly
    how ``sources/warden.py`` legitimately imports warden.

    Relative imports are RESOLVED against ``chain.py``'s own package rather
    than skipped (see ``_resolve_relative``), so ``from ..models import`` and
    ``from ...marshal import`` are told apart instead of both being waived."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                resolved = _resolve_relative(node.level, node.module)
                if resolved:
                    names.add(resolved)
            elif node.module:
                names.add(node.module)
    return names


def test_a_relative_import_of_a_station_is_resolved_not_waived() -> None:
    """The guard on the guard: relative imports must be resolved to their
    absolute names, or the whole file's protection is decorative.

    Encoded as a live test rather than a comment because the hole it closes
    was invisible — inserting ``from ...marshal import policy`` into
    ``chain.py`` passed all five of this file's tests before this fix."""
    tree = ast.parse("from ...marshal import policy\nfrom ..models import Finding\n")
    assert _imported_modules(tree) == {"pyforge.marshal", "pyforge.doctor.models"}


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
        "sources/chain.py imports the station it judges: "
        f"{offenders}. Charter §6 — Doctor holds the verdict on the chain "
        "precisely so Marshal cannot grade itself. Read the durable artifacts "
        "(Dreams, Specs, planning trees, git, tracked ledgers), never Marshal's code."
    )


def test_imports_no_station_package_at_all() -> None:
    """Broader than the rule strictly needs, and deliberately so: reaching into ANY
    sibling station would make this verdict depend on the fleet being healthy, when
    its entire job is to report on a fleet that is not.

    ``doctor`` is deliberately absent from the list: it is this module's OWN
    owning station, and ``..models``/``..cli_bridge``/``.`` are exactly the
    dependencies the assertion message below permits. It could stay omitted
    silently while relative imports were waived wholesale; now that they
    resolve (see ``_resolve_relative``), the exclusion has to be explicit."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    stations = ("herald", "marshal", "atlas", "warden",
                "mason", "scribe", "steward")
    offenders = sorted(
        m for m in _imported_modules(tree)
        if any(m == f"pyforge.{s}" or m.startswith(f"pyforge.{s}.") for s in stations)
    )
    assert not offenders, (
        f"sources/chain.py imports station package(s) {offenders}; it must depend "
        "only on the stdlib, PyYAML, and Doctor's own models."
    )


@pytest.mark.parametrize("forbidden", ["pyforge.marshal", "pyforge_marshal"])
def test_no_textual_reference_that_would_execute(forbidden: str) -> None:
    """Catches an import smuggled past the AST scan — ``importlib.import_module``,
    ``__import__``, or a subprocess invoking the CLI. Comments and docstrings are
    stripped first, since this module's own docstring names ``pyforge.marshal``
    repeatedly while explaining why it must not import it."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))

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
                f"a string constant in sources/chain.py contains {forbidden!r}, "
                "which could be used to import or invoke the judged station "
                "dynamically. Charter §6 forbids Marshal grading itself."
            )
