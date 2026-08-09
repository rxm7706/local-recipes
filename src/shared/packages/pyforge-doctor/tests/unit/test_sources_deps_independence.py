"""``sources/deps.py`` must never import ``pyforge.marshal`` -- NOR ``bmad_loop``.

Mirrors ``test_sources_board_independence.py``, retargeted at Story 6.7's module,
and then goes one step further than any sibling: it also bars the HARNESS.

Charter §6 says *"the Doctor holds the verdict on the Marshal's conformance --
the one station that would otherwise grade itself."* Every other Doctor source
satisfies that by not importing ``pyforge.marshal``. This one has a second,
sharper obligation, because what it judges is the harness's own blindness:
``bmad-loop``'s picker cannot see a dependency that lives in a later epic.

AD-11's rule is about MACHINERY, not package names -- *a verdict assembled from
the judged station's own machinery fails in exactly the case worth checking,
when that machinery is what broke*. ``bmad_loop`` IS that machinery here, so
importing it would be the same defect wearing a different package name, even
though ``bmad_loop`` is an upstream library rather than ``pyforge.marshal``.

AD-13 records the trade: the module restates ``ACTIONABLE_STATUSES`` instead,
and ``.claude/skills/conda-forge-expert/tests/meta/test_actionable_statuses_conformance.py``
holds the *derived, never restated* invariant by asserting set equality against
the installed harness. This file guards the other half -- that the import never
comes back.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SOURCE = (
    Path(__file__).resolve().parents[2]
    / "src" / "pyforge" / "doctor" / "sources" / "deps.py"
)


def _imported_modules(tree: ast.AST) -> set[str]:
    """Every module named by an import, including inside function bodies -- a lazy
    import in a gather would evade a module-header-only scan, and lazy is exactly
    how ``sources/warden.py`` legitimately imports warden."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative: ..models etc, never a station
                continue
            if node.module:
                names.add(node.module)
    return names


def test_source_exists() -> None:
    assert SOURCE.is_file(), f"{SOURCE} is missing"


def test_never_imports_the_harness_it_judges() -> None:
    """The AD-13 rule: no ``bmad_loop`` import, at module scope or lazily.

    This is the one that would silently undo Story 6.7. Re-adding
    ``from bmad_loop.sprintstatus import ACTIONABLE_STATUSES`` looks like a
    tidy-up -- it removes a "duplicated" constant -- and it would reintroduce
    the coupling the story exists to remove, converting one check's dependency
    back into the whole CLI's.
    """
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    offenders = sorted(
        m for m in _imported_modules(tree)
        if m == "bmad_loop" or m.startswith("bmad_loop.")
    )
    assert not offenders, (
        f"sources/deps.py imports the harness it judges: {offenders}. AD-13 "
        "restates ACTIONABLE_STATUSES instead, and the meta-suite's "
        "test_actionable_statuses_conformance.py asserts set equality against "
        "the installed bmad_loop so the invariant survives without the import. "
        "Doctor's verdict on bmad-loop's blindness must not require bmad-loop "
        "to be installed."
    )


def test_never_imports_pyforge_marshal() -> None:
    """The judged station's package must not be reachable from the judging module."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    offenders = sorted(
        m for m in _imported_modules(tree)
        if m == "pyforge.marshal" or m.startswith("pyforge.marshal.")
    )
    assert not offenders, (
        "sources/deps.py imports the station it judges: "
        f"{offenders}. Charter §6 — read the durable artifacts (each station's "
        "tracked epics doc and sprint-status-ledger.yaml), never Marshal's code."
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
        f"sources/deps.py imports station package(s) {offenders}; it must depend "
        "only on the stdlib and Doctor's own models."
    )


@pytest.mark.parametrize(
    "forbidden", ["pyforge.marshal", "pyforge_marshal", "bmad_loop"]
)
def test_no_textual_reference_that_would_execute(forbidden: str) -> None:
    """Catches an import smuggled past the AST scan — ``importlib.import_module``,
    ``__import__``, or a subprocess invoking the CLI. Comments and docstrings are
    stripped first, since this module's own docstring names ``bmad_loop``
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
                f"a string constant in sources/deps.py contains {forbidden!r}, "
                "which could be used to import or invoke the judged machinery "
                "dynamically."
            )
