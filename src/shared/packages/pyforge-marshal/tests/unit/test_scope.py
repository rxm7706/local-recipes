"""Unit tests for ``pyforge.marshal.core.gate``'s Story 2.3 additions
(frozen-surface scope check, narrowing only -- AD-4/AD-26/AD-27):
``compute_effective_surface``/``check_scope``, the AD-27 intersection-only
meta-test, and the AD-26 direct-read-fails-a-meta-test guard.

Named ``test_scope.py`` per epics.md's own ``Surface:`` field for this
story, even though both functions under test live in ``core/gate.py`` --
their own home module's tests live in ``test_gate.py``, but this story's
own surface gets its own file per the spec's explicit Code Map.
"""

from __future__ import annotations

import ast
import inspect

import pytest

from pyforge.marshal.core import gate
from pyforge.marshal.core.journal import FrozenPath
from pyforge.marshal.core.model import Finding, Severity, Verdict
from pyforge.marshal.core.verdict import classify

# --- compute_effective_surface: the AD-27 combinator --------------------------


def test_no_spec_surface_effective_is_policy_surface_unchanged():
    policy_surface = ("recipes/x/**", "recipes/y/**")
    assert gate.compute_effective_surface(policy_surface, None) == policy_surface


def test_spec_surface_narrower_than_policy_intersects():
    policy_surface = ("recipes/x/**", "recipes/y/**", "recipes/z/**")
    spec_surface = ("recipes/x/**",)
    assert gate.compute_effective_surface(policy_surface, spec_surface) == (
        "recipes/x/**",
    )


def test_spec_surface_wider_than_policy_never_expands():
    """A spec-declared glob outside the policy surface is silently excluded
    from the effective surface -- never admitted, never itself a finding
    here (a later changed file matching only that glob is what turns into
    a finding, via check_scope)."""
    policy_surface = ("recipes/x/**",)
    spec_surface = ("recipes/x/**", "recipes/outside/**")
    assert gate.compute_effective_surface(policy_surface, spec_surface) == (
        "recipes/x/**",
    )


def test_spec_surface_disjoint_from_policy_intersects_to_empty():
    policy_surface = ("recipes/x/**",)
    spec_surface = ("recipes/outside/**",)
    assert gate.compute_effective_surface(policy_surface, spec_surface) == ()


def test_spec_surface_empty_tuple_intersects_to_empty():
    """An explicit ``surface: []`` narrows to NOTHING -- distinct from
    ``None`` (no declared surface, which leaves policy_surface unchanged)."""
    policy_surface = ("recipes/x/**",)
    assert gate.compute_effective_surface(policy_surface, ()) == ()


def test_compute_effective_surface_is_deterministic_regardless_of_input_order():
    a = gate.compute_effective_surface(("b/**", "a/**"), ("a/**", "b/**"))
    b = gate.compute_effective_surface(("a/**", "b/**"), ("b/**", "a/**"))
    assert a == b


def test_compute_effective_surface_rejects_non_tuple_policy_surface():
    with pytest.raises(TypeError):
        gate.compute_effective_surface(["a/**"], None)  # type: ignore[arg-type]


def test_compute_effective_surface_rejects_non_tuple_spec_surface():
    with pytest.raises(TypeError):
        gate.compute_effective_surface((), ["a/**"])  # type: ignore[arg-type]


# --- AD-27 meta-test: no other combinator is ever used ------------------------


#: Method names that would let a rewrite silently smuggle a union/
#: difference combinator PAST the operator-only scan below (review finding,
#: Blind Hunter): ``set(a).union(b)``/``set(a).difference(b)`` (and their
#: symmetric/in-place siblings) achieve the exact same WIDENING the
#: ``BinOp(BitOr)``/``BinOp(Sub)`` scan already catches, but as an
#: ``ast.Call`` rather than an ``ast.BinOp`` -- invisible to a scan that
#: only inspects binary operators.
_FORBIDDEN_SET_METHODS = frozenset(
    {"union", "difference", "symmetric_difference", "update", "difference_update"}
)


def test_meta_compute_effective_surface_uses_only_set_intersection():
    """AD-27's own text: "a meta-test asserts no other combinator is used."
    AST-scans ``compute_effective_surface``'s source for a ``BinOp`` whose
    operator is ``|`` (union) or ``-`` (difference) applied to a ``set(...)``
    call -- the two combinators that would silently WIDEN or otherwise
    mis-shape the allowlist -- AND for a ``Call`` invoking one of
    ``_FORBIDDEN_SET_METHODS`` anywhere in the function body (review
    finding, Blind Hunter: a rewrite using ``.union(...)``/
    ``.difference(...)`` instead of ``|``/``-`` would silently widen the
    effective surface while sailing past an operator-only scan
    undetected). A simpler behavioral check (asserting the output never
    contains a spec-only glob) cannot distinguish "correctly implemented as
    intersection" from "coincidentally produces the same result for these
    fixtures" -- this inspects the actual operator/method.

    Scans only the function BODY's statements, not the ``def`` line's own
    parameter annotations (``tuple[str, ...] | None`` is itself a
    ``BinOp(BitOr)`` at the AST level -- a naive whole-source walk would
    flag the function's own type hint as a violation)."""
    source = inspect.getsource(gate.compute_effective_surface)
    tree = ast.parse(source)
    (func_def,) = tree.body
    assert isinstance(func_def, ast.FunctionDef)
    body_nodes = [node for stmt in func_def.body for node in ast.walk(stmt)]
    forbidden_ops = (ast.BitOr, ast.Sub)
    violations = [
        node.op
        for node in body_nodes
        if isinstance(node, ast.BinOp) and isinstance(node.op, forbidden_ops)
    ]
    assert not violations, (
        "compute_effective_surface must combine policy_surface/spec_surface "
        "via set intersection (&) only -- found a union/difference operator "
        "in the function body"
    )
    method_violations = [
        node.func.attr
        for node in body_nodes
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in _FORBIDDEN_SET_METHODS
    ]
    assert not method_violations, (
        "compute_effective_surface must combine policy_surface/spec_surface "
        "via set intersection (&) only -- found a "
        f"{method_violations!r} method call in the function body, which "
        "achieves the same widening a union/difference OPERATOR would"
    )
    intersections = [
        node
        for node in body_nodes
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitAnd)
    ]
    assert intersections, (
        "compute_effective_surface must use set intersection (&) to combine "
        "policy_surface and spec_surface when spec_surface is not None"
    )


def test_meta_guard_method_scan_detects_a_synthetic_union_call():
    """Proves the ``_FORBIDDEN_SET_METHODS`` scan above actually fires --
    without this, the new guard clause could be dead code that never
    executes on any real input (mirrors ``core/findings.py``'s/
    ``core/verdict.py``'s own "mechanism proven synthetically" precedent
    for an otherwise-never-exercised guard)."""
    synthetic_source = (
        "def fake(policy_surface, spec_surface):\n"
        "    return tuple(set(policy_surface).union(set(spec_surface)))\n"
    )
    tree = ast.parse(synthetic_source)
    (func_def,) = tree.body
    body_nodes = [node for stmt in func_def.body for node in ast.walk(stmt)]
    method_violations = [
        node.func.attr
        for node in body_nodes
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in _FORBIDDEN_SET_METHODS
    ]
    assert method_violations == ["union"]


# --- check_scope ---------------------------------------------------------------


def test_check_scope_no_changed_files_no_findings():
    assert gate.check_scope(("a/**",), (), ()) == ()


def test_check_scope_changed_file_inside_effective_surface_passes():
    findings = gate.check_scope(("recipes/x/**",), (), ("recipes/x/recipe.yaml",))
    assert findings == ()


def test_check_scope_changed_file_outside_effective_surface_is_mrs_gate_007():
    findings = gate.check_scope(("recipes/x/**",), (), ("recipes/y/recipe.yaml",))
    assert len(findings) == 1
    finding = findings[0]
    assert finding.code == "MRS-GATE-007"
    assert finding.severity is Severity.ERROR
    assert "recipes/y/recipe.yaml" in finding.message
    assert finding.path == "recipes/y/recipe.yaml"
    assert classify(finding.code) is Verdict.SCOPE_VIOLATION


def test_check_scope_every_offending_path_gets_its_own_finding():
    findings = gate.check_scope(
        ("recipes/x/**",),
        (),
        ("recipes/y/a.yaml", "recipes/z/b.yaml"),
    )
    assert len(findings) == 2
    paths = {finding.path for finding in findings}
    assert paths == {"recipes/y/a.yaml", "recipes/z/b.yaml"}


def test_check_scope_frozen_path_is_mrs_gate_008_naming_the_freezing_story():
    frozen = (FrozenPath(path="recipes/x/recipe.yaml", story_key="6.1"),)
    findings = gate.check_scope(("recipes/x/**",), frozen, ("recipes/x/recipe.yaml",))
    assert len(findings) == 1
    finding = findings[0]
    assert finding.code == "MRS-GATE-008"
    assert "recipes/x/recipe.yaml" in finding.message
    assert "6.1" in finding.message
    assert finding.path == "recipes/x/recipe.yaml"
    assert classify(finding.code) is Verdict.SCOPE_VIOLATION


def test_check_scope_policy_seeded_frozen_path_names_policy_not_a_story():
    frozen = (FrozenPath(path="recipes/x/recipe.yaml", story_key=None),)
    findings = gate.check_scope(("recipes/x/**",), frozen, ("recipes/x/recipe.yaml",))
    assert len(findings) == 1
    assert "policy" in findings[0].message


def test_check_scope_frozen_takes_precedence_over_outside_surface():
    """A path that is BOTH frozen AND outside the effective surface reports
    only the frozen finding -- one finding per offending path, never two
    for the same path."""
    frozen = (FrozenPath(path="recipes/y/recipe.yaml", story_key="6.1"),)
    findings = gate.check_scope(("recipes/x/**",), frozen, ("recipes/y/recipe.yaml",))
    assert len(findings) == 1
    assert findings[0].code == "MRS-GATE-008"


def test_check_scope_glob_matching_uses_fnmatch_semantics():
    """``fnmatch`` semantics (not a path-aware ``pathlib``/``glob`` match):
    ``*`` matches ANY character including ``/`` -- so a shallow glob still
    matches a deeper path. Confirms the real matcher, rather than assuming
    a path-aware recursive-glob library this module does not use."""
    findings = gate.check_scope(
        ("recipes/x/*.yaml",), (), ("recipes/x/sub/deep.yaml",)
    )
    assert findings == ()


def test_check_scope_exact_literal_path_with_no_wildcard_matches_only_itself():
    findings = gate.check_scope(
        ("recipes/x/recipe.yaml",), (), ("recipes/x/other.yaml",)
    )
    assert len(findings) == 1
    assert findings[0].code == "MRS-GATE-007"


def test_check_scope_rejects_non_tuple_frozen_paths():
    with pytest.raises(TypeError):
        gate.check_scope((), [FrozenPath(path="a", story_key=None)], ())  # type: ignore[arg-type]


def test_check_scope_rejects_non_tuple_changed_files():
    with pytest.raises(TypeError):
        gate.check_scope((), (), ["a"])  # type: ignore[arg-type]


def test_check_scope_returns_finding_instances():
    findings = gate.check_scope((), (), ("a",))
    assert all(isinstance(finding, Finding) for finding in findings)
