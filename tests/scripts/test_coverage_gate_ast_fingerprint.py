"""Steward Story 66.1 (2026-09-20): the touched-module coverage floor measures
code changes, not the formatter. ``ast_fingerprint`` is invariant under what a
lint/format landing changes and moves on any statement-level change.

Moved from pyforge-marshal's own test suite the same day (doctor Story 24.1,
spec-coverage-gate-independence CAP-1): the module under test moved to
scripts/coverage_gate.py, outside every pyforge.<station> package.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COVERAGE_GATE_PATH = REPO_ROOT / "scripts" / "coverage_gate.py"


def _load_coverage_gate():
    spec = importlib.util.spec_from_file_location("coverage_gate_ast_fingerprint_test", COVERAGE_GATE_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_coverage_gate = _load_coverage_gate()
ast_fingerprint = _coverage_gate.ast_fingerprint
format_only_paths = _coverage_gate.format_only_paths

ORIGINAL = (
    '''"""Module docstring with   trailing spaces'''
    + "   "
    + '''
and odd indentation."""
import sys
import os
from typing import Any, Dict


def f(a, b):
    'single-quoted docstring'
    x = {'k': 1,
         'j': 2}
    return a+b
'''
)

FORMATTED = '''"""Module docstring with trailing spaces
and odd indentation."""

import os
import sys
from typing import Any, Dict


def f(a, b):
    """single-quoted docstring"""
    x = {"k": 1, "j": 2}
    return a + b
'''


def test_format_and_import_sort_do_not_move_the_fingerprint() -> None:
    assert ast_fingerprint(ORIGINAL) == ast_fingerprint(FORMATTED)


def test_a_statement_change_moves_it() -> None:
    renamed = FORMATTED.replace("    x = {", "    y = {")
    removed = FORMATTED.replace('    x = {"k": 1, "j": 2}\n', "")
    base = ast_fingerprint(FORMATTED)
    assert ast_fingerprint(renamed) != base
    assert ast_fingerprint(removed) != base


def test_import_only_changes_do_not_move_it() -> None:
    """F401 removal, I001 merges and a type-only import carry no behaviour."""
    base = ast_fingerprint(FORMATTED)
    unused_removed = FORMATTED.replace("from typing import Any, Dict\n", "from typing import Any\n")
    merged = FORMATTED.replace("import os\nimport sys\n", "import os, sys\n")
    type_only = FORMATTED.replace(
        "import sys\n",
        "import sys\nfrom typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    from typing import Protocol\n",
    )
    assert ast_fingerprint(unused_removed) == base
    assert ast_fingerprint(merged) == base
    assert ast_fingerprint(type_only) != base  # a new `if` block is a statement; its import body is empty


def test_unparseable_source_is_none_and_never_format_only() -> None:
    assert ast_fingerprint("def (:\n") is None
    assert format_only_paths({"a.py": ("def (:\n", "def (:\n")}) == frozenset()


def test_format_only_paths_keeps_added_deleted_and_changed_files() -> None:
    pairs = {
        "fmt.py": (ORIGINAL, FORMATTED),
        "added.py": (None, FORMATTED),
        "deleted.py": (FORMATTED, None),
        "changed.py": (FORMATTED, FORMATTED.replace("return a + b", "return a - b")),
    }
    assert format_only_paths(pairs) == frozenset({"fmt.py"})
