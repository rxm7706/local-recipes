"""Meta test -- the exception-root sole-ownership guard (Story 14.3, CAP-7).

AST-scan every ``*.py`` file under every SIBLING station's ``src/pyforge``
tree (mirrors ``test_atomic_write_sole_ownership.py``'s identical station
enumeration -- derived from the filesystem, never hardcoded) for a class
definition whose base list includes one of a stated, bounded stdlib
-exception allowlist (``Exception``, ``ValueError``, ``RuntimeError``,
``OSError``, ``TypeError``, ``KeyError``, ``LookupError``) but does NOT also
include ``PyforgeError`` -- either by name directly, or by inheriting (same
file only) from a local class whose own bases already include it (a
same-file fixpoint: ``class A(PyforgeError, Exception)`` then
``class B(A):`` -- ``B`` satisfies transitively through ``A``, no edit
needed for ``B`` itself, matching CAP-5's "children re-parent transitively"
rule for classes like ``DirectoryAlreadyExistsError(FsError)``).

Only ROOT classes (whose base list literally names one of the seven
allowlisted stdlib types) are ever flagged -- a child class whose only base
is another custom exception class (not itself one of the seven) is out of
scope by construction, since re-parenting the root already covers it via
the MRO.

Scans SOURCE trees (reads files from disk), not installed packages -- same
convention as every other pyforge-core meta test.

Bounded (stated, not aspirational, mirrors ``test_leaf_constraint.py``'s own
convention): cross-file base resolution beyond one hop is out of scope --
same-file resolution is a full fixpoint (any chain length), but a class
whose PyforgeError-bearing ancestor lives in a DIFFERENT file is not
tracked here. The runtime ``issubclass`` pins in each station's own test
suites (named in the story's Boundaries) are the behavioral backstop for
that case.

Scan surface is bounded to the stations Story 14.3's CAP-5 roster actually
covers -- ``pyforge-warden``/``pyforge-marshal``/``pyforge-atlas`` (the 37
scattered family roots) plus ``pyforge-herald``/``pyforge-mason`` (their own
roots). ``pyforge-doctor`` and ``pyforge-steward`` are DELIBERATELY excluded
here, mirroring CAP-3's own precedent of an explicit, documented station
exclusion (there, atlas): both stations carry real, un-reparented exception
roots today (``doctor/cli_bridge.py::CliBridgeError``,
``doctor/sources/atlas.py::_FetchFailed``, and seven roots across
``steward/budget.py``/``dashboard/cache.py``/``dashboard/export.py``/
``dashboard/middleware.py``/``deploy.py``/``keys.py``/``sync.py``) that this
story's Boundaries roster does not name and that this story does not touch
-- confirmed by running the detector fleet-wide before adding this
exclusion: every hit outside these two stations corresponds exactly, 1:1,
to a class in the Boundaries roster, and every roster class is covered.
A future story extending CAP-5 to doctor/steward removes this exclusion
list in the same change that re-parents their roots.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from conftest import PACKAGES_ROOT, parse_module, station_source_files

_parse = parse_module

_STDLIB_ALLOWLIST = frozenset(
    {"Exception", "ValueError", "RuntimeError", "OSError", "TypeError", "KeyError", "LookupError"}
)
_ROOT_MARKER = "PyforgeError"

# Deliberately excluded (see module docstring): real, un-reparented roots
# exist in both today, but Story 14.3's CAP-5 Boundaries roster does not
# name them -- not this story's scope, mirrors CAP-3's own atlas exclusion.
_OUT_OF_SCOPE_STATIONS = frozenset({"pyforge-doctor", "pyforge-steward"})


def _station_source_files() -> list[Path]:
    return station_source_files(exclude=_OUT_OF_SCOPE_STATIONS)


def _base_name(base: ast.expr) -> str | None:
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    return None


def _base_names(node: ast.ClassDef) -> set[str]:
    names = {_base_name(base) for base in node.bases}
    names.discard(None)
    return names  # type: ignore[return-value]


def _classes_satisfying_pyforge_error(class_defs: list[ast.ClassDef]) -> set[str]:
    """Same-file fixpoint: a class satisfies CAP-5 if ``PyforgeError`` is a
    literal base name, or one of its bases names a LOCAL class that already
    satisfies (any chain length, within this one file)."""
    satisfies: set[str] = set()
    changed = True
    while changed:
        changed = False
        for node in class_defs:
            if node.name in satisfies:
                continue
            bases = _base_names(node)
            if _ROOT_MARKER in bases or bases & satisfies:
                satisfies.add(node.name)
                changed = True
    return satisfies


def _root_violations(tree: ast.Module) -> list[tuple[str, int]]:
    class_defs = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    satisfies = _classes_satisfying_pyforge_error(class_defs)
    violations: list[tuple[str, int]] = []
    for node in class_defs:
        bases = _base_names(node)
        if bases & _STDLIB_ALLOWLIST and node.name not in satisfies:
            violations.append((node.name, node.lineno))
    return violations


def test_scan_surface_is_not_empty():
    files = _station_source_files()
    assert files, "exception-root sole-ownership guard found no sibling station source files to scan"


@pytest.mark.parametrize("module_path", _station_source_files(), ids=lambda p: str(p.relative_to(PACKAGES_ROOT)))
def test_no_unreparented_exception_root(module_path: Path):
    violations = _root_violations(_parse(module_path))
    assert not violations, (
        f"{module_path} defines exception root class(es) {violations} whose base "
        f"list names a bare stdlib exception type but not PyforgeError -- CAP-5 "
        f"requires every family-root exception to gain PyforgeError as an "
        f"additional base (e.g. `class FooError(PyforgeError, Exception)`)"
    )


def test_guard_fires_on_a_synthetic_violation():
    """Non-vacuous proof (positive): a plain ``class FooError(Exception):
    pass`` with no PyforgeError base IS flagged."""
    synthetic = "class FooError(Exception):\n    pass\n"
    violations = _root_violations(ast.parse(synthetic))
    assert violations == [("FooError", 1)]


def test_guard_fires_on_every_allowlisted_stdlib_base():
    synthetic = "\n".join(f"class E{i}({base}):\n    pass" for i, base in enumerate(sorted(_STDLIB_ALLOWLIST)))
    violations = _root_violations(ast.parse(synthetic))
    assert len(violations) == len(_STDLIB_ALLOWLIST)


def test_guard_does_not_fire_on_a_real_reparented_class():
    """Non-vacuous proof (negative): a real re-parented root
    (``class FsError(PyforgeError, Exception)``, this story's own fix
    shape) must NOT be flagged."""
    synthetic = "class FsError(PyforgeError, Exception):\n    pass\n"
    assert _root_violations(ast.parse(synthetic)) == []


def test_guard_does_not_fire_on_ValueError_variant_reparented():
    synthetic = "class WaiverError(PyforgeError, ValueError):\n    pass\n"
    assert _root_violations(ast.parse(synthetic)) == []


def test_guard_treats_same_file_transitive_child_as_satisfied():
    """A child whose only base is a local, already-reparented class (not
    itself one of the seven stdlib names) is never flagged -- it re-parents
    transitively through its parent's MRO, mirroring
    ``DirectoryAlreadyExistsError(FsError)``."""
    synthetic = (
        "class FsError(PyforgeError, Exception):\n    pass\nclass DirectoryAlreadyExistsError(FsError):\n    pass\n"
    )
    assert _root_violations(ast.parse(synthetic)) == []


def test_guard_does_not_fire_on_a_non_exception_class():
    synthetic = "class Widget:\n    pass\n"
    assert _root_violations(ast.parse(synthetic)) == []
