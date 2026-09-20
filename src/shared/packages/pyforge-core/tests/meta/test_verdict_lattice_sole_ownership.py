"""Meta test -- the verdict-lattice sole-ownership guard (Story 14.3, CAP-7).

AST-scan every ``*.py`` file under every SIBLING station's ``src/pyforge``
tree (mirrors ``test_atomic_write_sole_ownership.py``'s identical station
enumeration -- derived from the filesystem, never hardcoded) for the
rank-dict-comprehension shape every pre-Story-14.3 verdict lattice
hand-rolled: ``{member: rank for rank, member in enumerate(order)}`` -- a
``DictComp`` with exactly one generator, no ``if`` filters, whose ``iter``
is a single-argument ``enumerate(...)`` call, whose loop target is a
2-element name tuple ``(index_name, element_name)``, whose comprehension KEY
is the element name and whose VALUE is the index name.

This story's own edits retire every real occurrence of this shape (warden's
and marshal's ``_RANK`` dict-comprehensions both delegate to
``pyforge.core.verdict.Lattice`` instead), so the real-station scan is
expected to find NOTHING -- the non-vacuous proof is a synthetic fixture
fed directly to the detector function, the same convention
``test_leaf_constraint.py`` and ``test_atomic_write_sole_ownership.py``
both already use for a primitive with no real positive left to scan.

Scans SOURCE trees (reads files from disk), not installed packages -- same
convention as every other pyforge-core meta test.

Bounds (stated, not aspirational): AST ``DictComp`` nodes matching this
EXACT shape only -- a rank table built any other way (a plain ``for`` loop,
``dict(zip(order, range(len(order))))``, etc.) is out of scope, matching
every sibling meta-test's stated static-analysis limitation. Also requires
the comprehension to be bound to a top-level name spelled EXACTLY ``_RANK``
-- both real pre-Story-14.3 occurrences (warden's and marshal's) used that
exact name; without this narrowing the bare structural shape also matches
``marshal/core/status.py``'s ``_PHASE_RANK`` (a same-story-key lifecycle
-phase tie-break, an entirely different primitive that coincidentally
shares the enumerate-rank idiom -- confirmed by reading its real body, not
a verdict/exit-code lattice at all, and not named anywhere in this story's
Boundaries roster). This mirrors ``test_atomic_write_sole_ownership.py``'s
own precedent of a narrow, name-shaped heuristic (there, "does the
``.replace()`` receiver look temp-path-shaped") added specifically to keep
a structural detector from firing on an unrelated real pattern.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from conftest import PACKAGES_ROOT, parse_module, station_source_files

_station_source_files = station_source_files
_parse = parse_module


def _is_rank_comprehension(node: ast.DictComp) -> bool:
    if len(node.generators) != 1:
        return False
    generator = node.generators[0]
    if generator.ifs or generator.is_async:
        return False
    iter_call = generator.iter
    if not (
        isinstance(iter_call, ast.Call)
        and isinstance(iter_call.func, ast.Name)
        and iter_call.func.id == "enumerate"
        and len(iter_call.args) == 1
        and not iter_call.keywords
    ):
        return False
    target = generator.target
    if not (
        isinstance(target, ast.Tuple)
        and len(target.elts) == 2
        and all(isinstance(elt, ast.Name) for elt in target.elts)
    ):
        return False
    index_name, element_name = target.elts[0].id, target.elts[1].id
    key, value = node.key, node.value
    return (
        isinstance(key, ast.Name) and key.id == element_name and isinstance(value, ast.Name) and value.id == index_name
    )


_RANK_BINDING_NAME = "_RANK"


def _is_bound_to_rank_name(assign_target: ast.expr) -> bool:
    return isinstance(assign_target, ast.Name) and assign_target.id == _RANK_BINDING_NAME


def _rank_comprehensions(tree: ast.Module) -> list[int]:
    violations: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1 or not _is_bound_to_rank_name(node.targets[0]):
                continue
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            if node.value is None or not _is_bound_to_rank_name(node.target):
                continue
            value = node.value
        else:
            continue
        if isinstance(value, ast.DictComp) and _is_rank_comprehension(value):
            violations.append(node.lineno)
    return violations


def test_scan_surface_is_not_empty():
    files = _station_source_files()
    assert files, "verdict-lattice sole-ownership guard found no sibling station source files to scan"


@pytest.mark.parametrize("module_path", _station_source_files(), ids=lambda p: str(p.relative_to(PACKAGES_ROOT)))
def test_no_second_rank_comprehension_implementation(module_path: Path):
    violations = _rank_comprehensions(_parse(module_path))
    assert not violations, (
        f"{module_path} defines a rank dict-comprehension at line(s) "
        f"{violations} -- a second verdict-lattice rank implementation "
        f"outside pyforge-core (CAP-7: the floor stays a floor; delegate "
        f"to pyforge.core.verdict.Lattice instead)"
    )


def test_guard_fires_on_a_synthetic_rank_comprehension():
    """Non-vacuous proof (positive): this story retires every real
    occurrence, so the detector is proven alive against a synthetic
    fixture reproducing the exact retired shape."""
    synthetic = (
        "from enum import StrEnum\n"
        "class Status(StrEnum):\n"
        "    A = 'a'\n"
        "    B = 'b'\n"
        "_ORDER = (Status.A, Status.B)\n"
        "_RANK = {status: rank for rank, status in enumerate(_ORDER)}\n"
    )
    violations = _rank_comprehensions(ast.parse(synthetic))
    assert violations == [6]


def test_guard_fires_on_marshals_pre_story_shape_too():
    """Marshal's own pre-Story-14.3 shape used different variable names
    (``verdict``/``LATTICE_ORDER``) -- proves the detector matches by
    STRUCTURE, not by the specific names warden happened to use."""
    synthetic = "_RANK = {verdict: rank for rank, verdict in enumerate(LATTICE_ORDER)}\n"
    violations = _rank_comprehensions(ast.parse(synthetic))
    assert violations == [1]


def test_guard_does_not_fire_on_an_unrelated_dict_comprehension():
    synthetic = "_DOUBLED = {k: v * 2 for k, v in some_mapping.items()}\n"
    assert _rank_comprehensions(ast.parse(synthetic)) == []


def test_guard_does_not_fire_on_a_lattice_rank_call():
    """The RETIRED shape's replacement -- a plain attribute/method call --
    must never be flagged as if it were still the old comprehension."""
    synthetic = "_LATTICE = Lattice(order=_ORDER, exit_by_member=_EXIT_BY_STATUS)\n"
    assert _rank_comprehensions(ast.parse(synthetic)) == []
