"""Meta test -- the P-07 "hash guards are checked in detect, never in
apply" guard (Story 9.3). Mirrors ``test_ad19_no_adapter_branch.py``'s
AST-scan-plus-self-test technique, adapted to a different structural
signature: an IMPORT, rather than an equality comparison.

AST-scan every module under ``pyforge.marshal.seed.apply`` and fail if any
of them imports ``pyforge.marshal.seed.detect.hashes`` (this story's own
module, in any of its ``import``/``from ... import``/relative-import forms)
or ``hashlib`` directly. P-07's rule is that apply TRUSTS the plan -- a
hash comparison recomputed inside ``apply/`` would be exactly the
TOCTUU/double-checking-drift class P-07 exists to prevent, whether it goes
through this story's own comparison functions or reimplements one ad hoc
via a bare ``hashlib`` import.

Bounds (stated, not aspirational): this is a best-effort STATIC check, like
the AD-19/AD-23 guards it mirrors. It only recognizes a direct import of
the banned module/package by name (``import hashlib``, ``from hashlib
import ...``, ``import pyforge.marshal.seed.detect.hashes``, ``from
pyforge.marshal.seed.detect import hashes``, ``from
pyforge.marshal.seed.detect.hashes import ...``, and the equivalent
relative-import forms, e.g. ``from ..detect import hashes`` or ``from
..detect.hashes import ...``) -- an indirect reach (e.g. importing the
``detect`` package under a different bound name and later attribute-
accessing ``.hashes`` off it) is out of scope, the same class of bound this
package's other AST-scan meta-tests already accept. The detector's own
aliveness is proven via synthetic violations it is asserted to catch,
mirroring the AD-19/AD-23 guards' own "fires on a synthetic violation"
proof.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import pyforge.marshal

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent

# The scan surface: exactly `seed/apply/`, the one package P-07 constrains --
# never the whole installed tree (detect/hashes.py itself, and every real
# consumer of it, live outside this surface entirely).
_APPLY_DIR = PACKAGE_DIR / "seed" / "apply"


def _apply_modules() -> list[Path]:
    return sorted(_APPLY_DIR.rglob("*.py"))


def _module_id(path: Path) -> str:
    return str(path.relative_to(PACKAGE_DIR))


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _ends_with_dotted_segment(dotted: str, segment: str) -> bool:
    """``True`` iff ``dotted`` IS ``segment``, or ends with ``segment``
    preceded by a ``.`` package-boundary -- never a bare substring match.
    Without the boundary check, a module merely ENDING in the same
    characters (e.g. ``"mypkg.underdetect.hashes"``, whose last segment is
    ``hashes`` under an unrelated ``underdetect`` package) would
    false-positive on ``str.endswith("detect.hashes")``, which has no
    boundary requirement on its own leading edge."""
    return dotted == segment or dotted.endswith(f".{segment}")


def _is_type_checking_test(test: ast.expr) -> bool:
    """``True`` for an ``if`` test of ``TYPE_CHECKING`` or
    ``<module>.TYPE_CHECKING`` -- the two shapes ``typing.TYPE_CHECKING`` is
    conventionally spelled. An import nested in such a block never executes
    at runtime, so it carries none of the risk P-07 guards against."""
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    return isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"


def _hash_import_violations(tree: ast.Module) -> list[int]:
    """Every ``Import``/``ImportFrom`` node that reaches ``hashlib`` or
    this story's ``detect.hashes`` module, by any of the import shapes this
    module's own docstring names -- absolute or relative, ``import X`` or
    ``from X import Y`` -- including a wildcard ``from ..detect import *``,
    which cannot statically be ruled out as reaching ``hashes``. Skips
    imports nested inside an ``if TYPE_CHECKING:`` block: those never run,
    so flagging them would be a false positive on legitimate annotation-only
    code, not a real P-07 violation."""
    violations: list[int] = []

    def check(node: ast.AST, guarded: bool) -> None:
        if guarded:
            return
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "hashlib" or _ends_with_dotted_segment(alias.name, "detect.hashes"):
                    violations.append(node.lineno)
                    break
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            reaches_hashes = _ends_with_dotted_segment(module, "detect") and any(
                alias.name in ("hashes", "*") for alias in node.names
            )
            if module == "hashlib" or _ends_with_dotted_segment(module, "detect.hashes") or reaches_hashes:
                violations.append(node.lineno)

    def visit(node: ast.AST, guarded: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.If) and _is_type_checking_test(child.test):
                for stmt in child.body:
                    check(stmt, True)
                    visit(stmt, True)
                for stmt in child.orelse:
                    check(stmt, guarded)
                    visit(stmt, guarded)
                continue
            check(child, guarded)
            visit(child, guarded)

    visit(tree, False)
    return violations


def test_apply_package_scan_surface_is_not_empty():
    modules = _apply_modules()
    assert modules, "P-07 hash-comparison guard found no modules under seed/apply/ to scan"


@pytest.mark.parametrize("module_path", _apply_modules(), ids=_module_id)
def test_apply_never_imports_hashes_or_hashlib(module_path: Path):
    violations = _hash_import_violations(_parse(module_path))
    assert not violations, (
        f"{_module_id(module_path)} imports detect.hashes or hashlib at line(s) "
        f"{violations} -- P-07 requires hash guards to be checked in detect, never "
        "in apply; apply must trust the plan it is handed"
    )


# --- detector self-test: non-vacuous proof -----------------------------------


def test_detector_fires_on_bare_hashlib_import():
    tree = ast.parse("import hashlib\n")
    assert _hash_import_violations(tree) == [1]


def test_detector_fires_on_from_hashlib_import():
    tree = ast.parse("from hashlib import sha256\n")
    assert _hash_import_violations(tree) == [1]


def test_detector_fires_on_absolute_dotted_import_of_hashes_module():
    tree = ast.parse("import pyforge.marshal.seed.detect.hashes\n")
    assert _hash_import_violations(tree) == [1]


def test_detector_fires_on_absolute_from_import_of_hashes_module():
    tree = ast.parse("from pyforge.marshal.seed.detect.hashes import check_managed_file\n")
    assert _hash_import_violations(tree) == [1]


def test_detector_fires_on_absolute_from_import_of_hashes_submodule_name():
    tree = ast.parse("from pyforge.marshal.seed.detect import hashes\n")
    assert _hash_import_violations(tree) == [1]


def test_detector_fires_on_relative_from_import_of_hashes_module():
    tree = ast.parse("from ..detect.hashes import check_managed_file\n")
    assert _hash_import_violations(tree) == [1]


def test_detector_fires_on_relative_from_import_of_hashes_submodule_name():
    tree = ast.parse("from ..detect import hashes\n")
    assert _hash_import_violations(tree) == [1]


def test_detector_does_not_fire_on_an_unrelated_stdlib_import():
    tree = ast.parse("import json\n")
    assert _hash_import_violations(tree) == []


def test_detector_does_not_fire_on_an_unrelated_detect_import():
    tree = ast.parse("from ..detect.findings import Finding\n")
    assert _hash_import_violations(tree) == []


def test_detector_does_not_fire_on_an_unrelated_sibling_module_named_similarly():
    tree = ast.parse("from ..detect import inventory\n")
    assert _hash_import_violations(tree) == []


def test_detector_does_not_fire_on_a_module_whose_name_merely_ends_with_the_same_characters():
    """A module ending in the same characters as ``detect.hashes`` without a
    ``.`` package boundary in front of them (e.g. an unrelated
    ``underdetect`` package's own ``hashes`` submodule) is not this story's
    module -- a bare ``str.endswith`` with no boundary check would
    false-positive here."""
    tree = ast.parse("from mypkg.underdetect.hashes import x\n")
    assert _hash_import_violations(tree) == []


def test_detector_fires_on_a_wildcard_import_of_the_detect_package():
    """A wildcard ``from ..detect import *`` cannot be statically ruled out
    as reaching ``hashes`` -- the prior alias-name-only check
    (``alias.name == "hashes"``) missed this shape entirely, since a
    wildcard's alias name is ``"*"``, not ``"hashes"``."""
    tree = ast.parse("from ..detect import *\n")
    assert _hash_import_violations(tree) == [1]


def test_detector_does_not_fire_on_a_hashlib_import_guarded_by_type_checking():
    tree = ast.parse("from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import hashlib\n")
    assert _hash_import_violations(tree) == []


def test_detector_does_not_fire_on_a_hashes_import_guarded_by_dotted_type_checking():
    tree = ast.parse("import typing\nif typing.TYPE_CHECKING:\n    from ..detect.hashes import check_managed_file\n")
    assert _hash_import_violations(tree) == []


def test_detector_still_fires_on_a_hashlib_import_in_the_type_checking_else_branch():
    """Only the ``if TYPE_CHECKING:`` body is guarded -- an import placed in
    its ``else:`` branch runs unconditionally at runtime and is a real
    violation."""
    tree = ast.parse("from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    pass\nelse:\n    import hashlib\n")
    assert _hash_import_violations(tree) == [5]
