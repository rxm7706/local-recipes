"""Meta test — pyforge-core is provably a leaf (Story 14.1, CAP-1).

AST-scan every module in `pyforge.core`'s source tree and fail the build if
any of them:

(a) imports `pyforge.<X>` (via `import pyforge.<X>`, `import pyforge.<X> as
    y`, `from pyforge.<X> import ...`, `from pyforge import <X>`, or a
    RELATIVE import that resolves to one of those forms once its dots are
    walked against the importing module's own package path) for any
    `X != "core"` — the general form of "for any of the eight stations"
    (SPEC-pyforge-core Design Notes: a strict superset of enumerating eight
    literal names, and correct regardless of whether a ninth station is ever
    added, deliberately not taking a position on SPEC.md's Q1 station-roster
    question);
(b) imports anything that is neither in `sys.stdlib_module_names` nor the
    `pyforge` namespace itself — pyforge-core declares zero third-party
    runtime dependencies, structurally, not just in its manifest.

Both detectors are proven non-vacuous against synthetic-violation fixtures
(`from pyforge.warden import ...`, `import requests`) — this story ships an
empty `pyforge.core`, so there is nothing in the real package yet for either
scanner to legitimately flag; without the synthetic proof this file would be
vacuously green whether or not the detector logic actually works (the same
failure `pyforge-warden`'s `test_verdict_sole_ownership.py` guards against).

Relative-import resolution (review-pass fix): a naive guard that skips every
`node.level > 0` import is NOT safe here, unlike guards whose only concern is
imports *within* one package. Reproduced directly: `from .. import warden`
placed in `pyforge/core/__init__.py` resolves at runtime to `pyforge.warden`
and imports it successfully whenever both are installed into the same
environment (e.g. `pyforge-container`) — because `pyforge` is a merged PEP
420 namespace package shared by every station. `_resolved_module` below
walks the dots against each scanned file's own package path (mirrors
`pyforge-steward`'s `_find_banned_dashboard_imports._resolved_module`) so
this class of import is resolved to its real absolute target instead of
being waved through.

A further guard mirrors `pyforge-steward`'s `test_namespace_stays_implicit`
(PEP 420): no `src/pyforge/__init__.py` may exist, since it would shadow
every sibling station's install.

All scanning reads the SOURCE tree (not the installed package) so results
never depend on whether the environment happens to be freshly rebuilt —
matches `pyforge-steward`'s `tests/meta/test_invariants.py` convention
throughout.

Bounds (stated, not aspirational): this is a best-effort STATIC check, AST
`Import`/`ImportFrom` nodes only — dynamic import (`importlib.import_module`,
`__import__`) is out of scope, matching every sibling meta-test's stated
limitation. A relative import that climbs past the top-level package is
unresolvable and is itself reported as a violation rather than silently
dropped, mirroring `pyforge-steward`'s identical rule.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

# tests/meta/test_leaf_constraint.py -> parents[2] is the pyforge-core
# package root (mirrors pyforge-steward/tests/meta/test_invariants.py).
PKG_ROOT = Path(__file__).resolve().parents[2] / "src" / "pyforge"

_STDLIB_MODULES = sys.stdlib_module_names
_UNRESOLVABLE_RELATIVE = "<unresolvable-relative-import>"


def _package_modules() -> list[Path]:
    return sorted((PKG_ROOT / "core").rglob("*.py"))


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _own_package_parts(path: Path) -> tuple[str, ...]:
    """The dotted package `path` itself lives in, e.g. `("pyforge", "core")`
    for both `core/__init__.py` and `core/sub/mod.py` alike -- dropping only
    the filename stem gives the containing package either way."""
    return path.relative_to(PKG_ROOT.parent).with_suffix("").parts[:-1]


def _resolved_module(node: ast.ImportFrom, own_package_parts: tuple[str, ...]) -> str | None:
    """Absolute dotted target of an `ImportFrom`, walking relative dots
    against `own_package_parts`. Returns `_UNRESOLVABLE_RELATIVE` when the
    level climbs past the top-level package -- reported as a violation by
    the caller, never silently truncated into something that looks benign."""
    if node.level == 0:
        return node.module
    keep = len(own_package_parts) - (node.level - 1)
    if keep <= 0:
        return _UNRESOLVABLE_RELATIVE
    parts = list(own_package_parts[:keep])
    if node.module:
        parts += node.module.split(".")
    return ".".join(parts) if parts else None


def _station_import_violations(tree: ast.Module, own_package_parts: tuple[str, ...] = ("pyforge", "core")) -> list[str]:
    """Flag every import of `pyforge.<X>` for any `X != "core"`, including
    relative imports that resolve to one. `own_package_parts` defaults to
    `pyforge.core` itself for the synthetic-fixture tests below, which parse
    bare source strings with no real file location.

    A bare `import pyforge` (no station named) is not itself a violation —
    nothing about it names another station.
    """
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if len(parts) >= 2 and parts[0] == "pyforge" and parts[1] != "core":
                    violations.append(f"{node.lineno}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            resolved = _resolved_module(node, own_package_parts)
            if resolved == _UNRESOLVABLE_RELATIVE:
                violations.append(
                    f"{node.lineno}: relative import climbs past the top-level "
                    f"package (level {node.level}) -- unresolvable, so it cannot "
                    f"be cleared of importing another station"
                )
                continue
            module_parts = resolved.split(".") if resolved else []
            if not module_parts or module_parts[0] != "pyforge":
                continue
            if len(module_parts) >= 2:
                if module_parts[1] != "core":
                    violations.append(f"{node.lineno}: from {resolved} import ...")
            else:
                # Resolved to bare "pyforge" -- the station name is carried
                # by each imported alias instead (`from pyforge import <X>`,
                # or a relative import resolving to the same shape).
                for alias in node.names:
                    if alias.name != "core":
                        violations.append(f"{node.lineno}: from {resolved or '<relative>'} import {alias.name}")
    return violations


def _non_stdlib_import_violations(tree: ast.Module) -> list[str]:
    """Flag every import whose top-level name is neither stdlib nor
    `pyforge`. Relative imports (`node.level > 0`) can only ever resolve
    within the `pyforge` namespace by construction -- a leading-dot import
    cannot syntactically name an unrelated top-level distribution such as
    `requests` -- so, unlike the station-import guard above, skipping them
    here is safe and does not need dot-walking."""
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top != "pyforge" and top not in _STDLIB_MODULES:
                    violations.append(f"{node.lineno}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            module = node.module or ""
            top = module.split(".")[0] if module else ""
            if top and top != "pyforge" and top not in _STDLIB_MODULES:
                violations.append(f"{node.lineno}: from {module} import ...")
    return violations


def test_package_scan_surface_is_not_empty():
    modules = _package_modules()
    assert modules, "leaf-constraint guard found no modules to scan"
    names = {path.name for path in modules}
    assert "__init__.py" in names, "__init__.py missing from the installed package"


@pytest.mark.parametrize("module_path", _package_modules(), ids=lambda p: p.name)
def test_no_module_imports_another_station(module_path: Path):
    violations = _station_import_violations(_parse(module_path), _own_package_parts(module_path))
    assert not violations, (
        f"{module_path.name} imports from another pyforge station at {violations} — pyforge-core must be a leaf"
    )


@pytest.mark.parametrize("module_path", _package_modules(), ids=lambda p: p.name)
def test_no_module_imports_a_non_stdlib_package(module_path: Path):
    violations = _non_stdlib_import_violations(_parse(module_path))
    assert not violations, (
        f"{module_path.name} imports a non-stdlib, non-pyforge package at "
        f"{violations} — pyforge-core declares zero third-party runtime deps"
    )


def test_station_import_detector_fires_on_a_synthetic_station_import():
    """Non-vacuous proof: every import shape the docstring claims to cover
    IS flagged -- unaliased `import`, aliased `import ... as`, `from ...
    import`, and the bare `from pyforge import <X>` form."""
    assert _station_import_violations(ast.parse("from pyforge.warden import something\n"))
    assert _station_import_violations(ast.parse("import pyforge.warden\n"))
    assert _station_import_violations(ast.parse("import pyforge.warden as w\n"))
    assert _station_import_violations(ast.parse("from pyforge import warden\n"))


def test_station_import_detector_fires_on_a_relative_import_reaching_a_station():
    """Non-vacuous proof of the review-pass fix: reproduced directly against
    a real import (see module docstring) -- `from .. import warden` inside
    `pyforge/core/__init__.py` resolves to `pyforge.warden` and must be
    flagged, not waved through as "relative, therefore safe"."""
    own_package_parts = ("pyforge", "core")
    assert _station_import_violations(ast.parse("from .. import warden\n"), own_package_parts)
    assert _station_import_violations(ast.parse("from ..warden import something\n"), own_package_parts)


def test_station_import_detector_flags_an_unresolvable_relative_import():
    """A relative import climbing past the top-level package cannot execute
    at all (Python raises ImportError), so the point is not that it is
    dangerous but that a guard must never resolve an import it cannot
    account for into something that looks innocent -- mirrors
    pyforge-steward's identical rule for the same failure mode."""
    violations = _station_import_violations(ast.parse("from ... import warden\n"), ("pyforge", "core"))
    assert violations
    assert "unresolvable" in violations[0]


def test_station_import_detector_does_not_fire_on_a_self_import():
    """Legitimate self-import: pyforge.core importing its own submodules
    must never be flagged — a false positive here would block every future
    extraction story (14.2-14.4)."""
    own_package_parts = ("pyforge", "core")
    assert not _station_import_violations(ast.parse("from pyforge.core import something\n"), own_package_parts)
    assert not _station_import_violations(ast.parse("import pyforge.core\n"), own_package_parts)
    assert not _station_import_violations(ast.parse("from pyforge import core\n"), own_package_parts)
    assert not _station_import_violations(ast.parse("import pyforge\n"), own_package_parts)
    assert not _station_import_violations(ast.parse("from . import something\n"), own_package_parts)
    assert not _station_import_violations(ast.parse("from .sibling import something\n"), own_package_parts)


def test_stdlib_detector_fires_on_a_synthetic_third_party_import():
    """Non-vacuous proof: a real third-party import IS flagged."""
    assert _non_stdlib_import_violations(ast.parse("import requests\n"))
    assert _non_stdlib_import_violations(ast.parse("from requests import Session\n"))


def test_stdlib_detector_does_not_fire_on_stdlib_or_self_imports():
    assert not _non_stdlib_import_violations(ast.parse("import ast\nimport sys\n"))
    assert not _non_stdlib_import_violations(ast.parse("from pathlib import Path\n"))
    assert not _non_stdlib_import_violations(ast.parse("import pyforge.core\n"))


def test_namespace_stays_implicit():
    """PEP 420: shipping src/pyforge/__init__.py would shadow the sibling
    stations. Nothing errors at build time -- it only surfaces when two
    pyforge packages are installed together, which is precisely when it is
    most expensive to find. Mirrors pyforge-steward's identical guard.
    """
    assert not (PKG_ROOT / "__init__.py").exists()
    assert (PKG_ROOT / "core" / "__init__.py").exists()
