"""Meta test -- the "no bare `Exception`/`SystemExit` under `seed/`" guard
(Story 7.2). Mirrors ``tests/meta/test_ad23_inline_key_format_guard.py``'s
AST-scan technique exactly, adapted to a different structural signature.

The epics AC for this story ("no module raises a bare `Exception` or
`SystemExit` outside `cli.py`") and FR-126's closed exit-code taxonomy
only mean something if every failure under `seed/` is one of the six
`SeedError` leaves `errors.py` pins -- a stray ``raise Exception(...)`` or
``raise SystemExit`` would bypass that taxonomy entirely, reaching a
caller with no `exit_code`/`remedy` at all. This guard AST-scans EVERY
module under ``src/pyforge/marshal/seed/`` (the whole package is in scope
-- there is no carve-out module here, unlike the AD-23/AD-26 guards this
file mirrors) and fails if any of them raises a bare ``Exception``
(``Exception(...)``/bare ``Exception`` name) or any ``SystemExit`` usage
(``SystemExit(...)``/bare ``SystemExit`` name) as a ``Raise`` node's
exception expression.

Bounds (stated, not aspirational): this is a best-effort STATIC check,
like the AD-23/AD-26/AD-7 guards it mirrors. It only recognizes a literal
bare ``Exception``/``SystemExit`` name or call as a ``Raise`` node's own
exception expression; it does not flag a bare re-raise (``raise`` with no
expression -- that re-raises whatever is already in flight, not a freshly
constructed bare exception) or an exception constructed once and raised
through an intermediate variable (``exc = Exception(...); raise exc``).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import pyforge.marshal.seed

_SEED_PACKAGE_FILE = pyforge.marshal.seed.__file__
if _SEED_PACKAGE_FILE is None:
    raise ValueError("installed pyforge.marshal.seed package has no __file__")
SEED_DIR = Path(_SEED_PACKAGE_FILE).resolve().parent

_BARE_NAMES = frozenset({"Exception", "SystemExit"})


def _seed_modules() -> list[Path]:
    return sorted(SEED_DIR.rglob("*.py"))


def _module_id(path: Path) -> str:
    return str(path.relative_to(SEED_DIR))


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _is_bare_exception_expr(node: ast.expr) -> bool:
    """Whether ``node`` (a ``Raise`` node's ``exc``) is a bare
    ``Exception``/``SystemExit`` call or name -- ``Exception("msg")``,
    ``Exception``, ``SystemExit(1)``, or ``SystemExit``."""
    if isinstance(node, ast.Call):
        func = node.func
        return isinstance(func, ast.Name) and func.id in _BARE_NAMES
    if isinstance(node, ast.Name):
        return node.id in _BARE_NAMES
    return False


def _bare_exception_violations(tree: ast.Module) -> list[int]:
    violations: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise):
            continue
        # `node.exc` is `None` for a bare re-raise (`raise` with no
        # expression) -- that propagates whatever exception is already in
        # flight, not a freshly constructed bare `Exception`/`SystemExit`,
        # so it is never a violation on its own.
        if node.exc is not None and _is_bare_exception_expr(node.exc):
            violations.append(node.lineno)
    return sorted(violations)


def test_seed_scan_surface_is_not_empty():
    modules = _seed_modules()
    assert modules, "bare-Exception/SystemExit guard found no modules under seed/ to scan"


@pytest.mark.parametrize("module_path", _seed_modules(), ids=_module_id)
def test_no_bare_exception_or_system_exit_under_seed(module_path: Path):
    violations = _bare_exception_violations(_parse(module_path))
    assert not violations, (
        f"{_module_id(module_path)} raises a bare Exception/SystemExit at "
        f"line(s) {violations} -- every seed/ failure must be one of the "
        "six SeedError leaves in seed/errors.py (FR-126)"
    )


# --- detector self-test: non-vacuous proof ----------------------------------


def test_guard_is_alive_synthetic_violations_fire():
    """Non-vacuous proof, mirroring the AD-23/AD-26 guards' own final test:
    the detector demonstrably fires on synthetic violations for both the
    call form and the bare-name form, for both `Exception` and
    `SystemExit`, and does not fire on an ordinary typed raise or a bare
    re-raise."""
    assert _bare_exception_violations(ast.parse('raise Exception("boom")\n')) == [1]
    assert _bare_exception_violations(ast.parse("raise Exception\n")) == [1]
    assert _bare_exception_violations(ast.parse("raise SystemExit(1)\n")) == [1]
    assert _bare_exception_violations(ast.parse("raise SystemExit\n")) == [1]
    assert _bare_exception_violations(ast.parse('raise ValueError("boom")\n')) == []
    assert _bare_exception_violations(ast.parse("try:\n    pass\nexcept Exception:\n    raise\n")) == []
