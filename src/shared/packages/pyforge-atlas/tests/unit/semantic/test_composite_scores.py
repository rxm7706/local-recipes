"""Composite-score columns stay PASS-THROUGHS of their producing node's output.

Story 27.3, closing DW-FU-20-5-5 / DW-FU-20-5-12. DESIGN.md gives a handful of
pages a multi-signal composite score — ``find-alternative``'s weighted-Jaccard
``similarity_score``, ``mapping-gap``/``inventory-match``'s ``match_confidence``,
``library-futures``/``recommend-2027``'s ``futures_score`` — that needs row-to-row
comparison or set operations over the whole catalog. Each is computed UPSTREAM and
read here as an ordinary column (AD-8: the BSL layer translates metrics, it never
re-implements one).

That was a docstring claim with no gate. Reimplementing any of these as an Ibis
expression would have passed every existing test, so this module pins the shape:
no composite column may acquire a derived formula, and none may be registered as a
BSL metric.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from pyforge.atlas.semantic import metrics

MODELS_PY = Path(metrics.__file__).with_name("models.py")

# column -> (the model that exposes it, how it is exposed, the legacy producer the
# model's own docstring names as its source).
COMPOSITE_COLUMNS: dict[str, tuple[str, str, str]] = {
    "similarity_score": ("build_alternative_candidates_model", "Measure", "find_alternative.py"),
    "match_confidence": ("build_mapping_gap_model", "Dimension", ""),
    "freshness_percentile": ("build_inventory_match_report_model", "Dimension", ""),
    "futures_score": ("build_library_futures_report_model", "Measure", ""),
    "py314_readiness": ("build_library_futures_report_model", "Dimension", ""),
    "futures_tier": ("build_library_futures_report_model", "Dimension", ""),
}

# A pass-through declaration, in the two shapes models.py uses.
_PASSTHROUGH = {
    "Dimension": "lambda t: t.{column}",
    "Measure": "lambda t: t.{column}.mean()",
}


def _declarations() -> dict[tuple[str, str], tuple[str, str]]:
    """(model fn, column) -> (wrapper class name, unparsed lambda) for every
    Dimension/Measure entry declared anywhere in models.py."""
    tree = ast.parse(MODELS_PY.read_text(encoding="utf-8"))
    found: dict[tuple[str, str], tuple[str, str]] = {}
    for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        for node in ast.walk(fn):
            if not isinstance(node, ast.Dict):
                continue
            for key, value in zip(node.keys, node.values):
                if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                    continue
                if not isinstance(value, ast.Call) or not isinstance(value.func, ast.Name):
                    continue
                if value.func.id not in {"Dimension", "Measure"}:
                    continue
                expr = next((kw.value for kw in value.keywords if kw.arg == "expr"), None)
                if expr is None:
                    continue
                found[(fn.name, key.value)] = (value.func.id, ast.unparse(expr))
    return found


DECLARATIONS = _declarations()


def test_the_ast_scan_found_the_models() -> None:
    """A scan that matched nothing would make every case below vacuous."""
    assert len(DECLARATIONS) > 50, len(DECLARATIONS)
    assert ("build_packages_model", "conda_name") in DECLARATIONS


@pytest.mark.parametrize("column", sorted(COMPOSITE_COLUMNS))
def test_a_composite_score_is_never_a_registered_bsl_metric(column: str) -> None:
    """``METRIC_PROVENANCE`` is the registry of columns the BSL layer DERIVES, each
    with its cited legacy formula. A composite score must not appear there: it is
    read, not computed."""
    assert column not in metrics.METRIC_PROVENANCE


@pytest.mark.parametrize("column", sorted(COMPOSITE_COLUMNS))
def test_a_composite_score_is_declared_as_a_bare_pass_through(column: str) -> None:
    model_fn, kind, _producer = COMPOSITE_COLUMNS[column]
    key = (model_fn, column)
    assert key in DECLARATIONS, f"{model_fn} no longer declares {column!r}"
    declared_kind, expr = DECLARATIONS[key]
    assert declared_kind == kind
    assert expr == _PASSTHROUGH[kind].format(column=column), (
        f"{model_fn}'s {column!r} has grown a derived expression ({expr}). A composite "
        "score is computed upstream and passed through here -- re-deriving it in Ibis "
        "would be a second implementation of the algorithm (AD-8)."
    )


def test_the_model_docstring_still_names_the_legacy_producer() -> None:
    """``similarity_score``'s weighted-Jaccard scorer is the clearest case, and the
    only one whose legacy source the model names verbatim; keep that citation."""
    text = MODELS_PY.read_text(encoding="utf-8")
    assert "find_alternative.py" in text
    assert "pre-computed composite" in text


@pytest.mark.parametrize("column", sorted(COMPOSITE_COLUMNS))
def test_no_composite_column_is_computed_anywhere_in_the_metrics_module(column: str) -> None:
    """The other place a re-implementation could land: a new ``metrics.py`` function."""
    tree = ast.parse(Path(metrics.__file__).read_text(encoding="utf-8"))
    names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert column not in names
