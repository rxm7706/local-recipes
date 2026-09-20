"""Meta test -- Story 28.6 (CAP-8) compression-only seam guard.

The graduated compression ladder must never become a second model-selection
mechanism or a gate/review skip path. This static scan mirrors
``test_ad19_no_adapter_branch.py``'s technique: read the owning modules and
fail on forbidden identifiers inside the compression-ladder surface.
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

_FORBIDDEN_IN_COMPRESSION_SURFACE = frozenset(
    {
        "model_tier",
        "model_map",
        "model_passthrough",
        "resolve_model",
        "declared_difficulty",
        "skip_review",
        "review_cycle",
        "gate_mode",
    }
)

_COMPRESSION_OWNERS = (
    PACKAGE_DIR / "core" / "supervise.py",
    PACKAGE_DIR / "supervisor" / "__main__.py",
)


def _compression_function_defs(tree: ast.Module) -> list[ast.FunctionDef]:
    names = {"evaluate_compression_ladder", "_maybe_escalate_compression"}
    return [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name in names]


def _function_forbidden_hits(function: ast.FunctionDef) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for node in ast.walk(function):
        if isinstance(node, ast.Name) and node.id in _FORBIDDEN_IN_COMPRESSION_SURFACE:
            hits.append((node.lineno, node.id))
        elif isinstance(node, ast.Attribute) and node.attr in _FORBIDDEN_IN_COMPRESSION_SURFACE:
            hits.append((node.lineno, node.attr))
    return hits


@pytest.mark.parametrize("module_path", _COMPRESSION_OWNERS, ids=lambda p: p.name)
def test_compression_ladder_functions_never_reference_model_or_gate_seams(
    module_path: Path,
):
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    functions = _compression_function_defs(tree)
    assert functions, f"{module_path.name} must define a compression-ladder function"
    violations: list[str] = []
    for function in functions:
        for lineno, name in _function_forbidden_hits(function):
            violations.append(f"{function.name} line {lineno}: {name}")
    assert not violations, (
        f"CAP-8 compression ladder must not reference model selection or gate/review skip seams: {violations}"
    )


def test_supervise_compression_section_documents_wire_only_surface():
    source = (PACKAGE_DIR / "core" / "supervise.py").read_text(encoding="utf-8")
    assert "Story 28.6" in source
    assert "wire-layer aggressiveness" in source
    assert "never names or changes a model tier" in source
