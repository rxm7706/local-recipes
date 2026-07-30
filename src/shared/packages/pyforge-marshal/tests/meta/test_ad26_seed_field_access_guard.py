"""Meta test -- the AD-26 "seed fields have exactly one reader" guard
(Story 1.3). Mirrors ``tests/meta/test_ad23_inline_key_format_guard.py``'s
AST-scan technique exactly, adapted to a different structural signature.

AST-scan every module in the installed package EXCEPT ``core/policy.py``
and fail if any of them accesses the attribute name ``_seed`` -- an
``ast.Attribute`` node with ``.attr == "_seed"``. ``EffectivePolicy``'s 5
seed-tagged fields (``gate_mode``, ``frozen_surfaces``, ``max_dev_attempts``,
``max_review_cycles``, ``max_followup_reviews``) live ONLY in a private
``_seed`` mapping; ``EffectivePolicy.seed_view()`` is the sole whitelisted
accessor (AD-26, closing review finding F-8). Reading ``_seed`` directly
from any other module -- even for display or validation, the two carve-outs
``seed_view()`` exists to satisfy -- is exactly the failure this guard
exists to catch: "read for display" quietly becoming "read as the live
value" AD-26 reserves for ``core/journal``'s fold.

Positively asserts ``core/policy.py`` itself defines ``seed_view`` (a
simple introspection check, not AST -- that module is the one place this
attribute access is legitimate and is excluded from the scan).

Bounds (stated, not aspirational): this is a best-effort STATIC check, like
the AD-23/AD-7 guards it mirrors. It only recognizes a literal ``.attr ==
"_seed"`` attribute access; it cannot catch ``getattr(obj, "_seed")``
(dynamic attribute access via a string) or attribute access on an object
smuggled through an intermediate alias that itself never spells ``_seed``
literally. ``tests/unit/test_policy.py``'s own tests (seed_view() isolation,
``hasattr(effective, "gate_mode")`` being False) are the behavioral
backstop for ``EffectivePolicy``'s own correctness.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import pyforge.marshal
from pyforge.marshal.core import policy

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent

_POLICY_MODULE = PACKAGE_DIR / "core" / "policy.py"


def _package_modules() -> list[Path]:
    return sorted(PACKAGE_DIR.rglob("*.py"))


def _non_policy_modules() -> list[Path]:
    # Full-path comparison, not basename -- mirrors the AD-23/AD-7 guards'
    # own rationale: only core/policy.py is exempt, not any future
    # same-named file elsewhere in the tree.
    return [path for path in _package_modules() if path != _POLICY_MODULE]


def _module_id(path: Path) -> str:
    return str(path.relative_to(PACKAGE_DIR))


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _seed_attribute_violations(tree: ast.Module) -> list[int]:
    return sorted(
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr == "_seed"
    )


def test_package_scan_surface_is_not_empty():
    modules = _non_policy_modules()
    assert modules, "AD-26 seed-field-access guard found no modules to scan"
    names = {path.name for path in _package_modules()}
    assert "policy.py" in names, "policy.py missing from the installed package"


@pytest.mark.parametrize("module_path", _non_policy_modules(), ids=_module_id)
def test_no_seed_attribute_access_outside_policy(module_path: Path):
    violations = _seed_attribute_violations(_parse(module_path))
    assert not violations, (
        f"{module_path.name} accesses the private `_seed` attribute at "
        f"line(s) {violations} -- only core/policy.py may; every other "
        "module must go through EffectivePolicy.seed_view() (AD-26)"
    )


def test_policy_module_defines_seed_view():
    assert hasattr(policy, "EffectivePolicy"), "core/policy.py is missing EffectivePolicy"
    assert hasattr(policy.EffectivePolicy, "seed_view"), (
        "core/policy.py's EffectivePolicy is missing seed_view"
    )


# --- detector self-test: non-vacuous proof ----------------------------------


def test_guard_is_alive_synthetic_violation_fires_and_policy_defines_seed_view():
    """Non-vacuous proof, mirroring the AD-23/AD-7 guards' own final test:
    (1) the detector demonstrably fires on a synthetic violation, and (2)
    ``core/policy.py`` itself structurally defines ``EffectivePolicy`` with
    a ``seed_view`` method -- the one place this attribute access is
    legitimate."""
    synthetic_violation = "def f(obj):\n    return obj._seed\n"
    assert _seed_attribute_violations(ast.parse(synthetic_violation)) == [2]

    tree = _parse(_POLICY_MODULE)
    class_methods: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_methods[node.name] = {
                item.name for item in node.body if isinstance(item, ast.FunctionDef)
            }
    assert "EffectivePolicy" in class_methods
    assert "seed_view" in class_methods["EffectivePolicy"]
