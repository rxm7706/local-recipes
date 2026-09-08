"""Q6 mapping-export shim tests (Story B5 — AC-4 / AD-10).

`export_pypi_conda_map` exports the migrated Phase C mapping to the flat
`pypi_conda_map.json` cache (the Q6-consolidated compatibility shim). The `g10_spelling`
provenance tier and the no-clobber writeback rule MUST survive: collapsing to one
`conda_name` per `pypi_name`, a protected tier is never clobbered by a weaker one, and
`g10_spelling` provably survives a collision.
"""

from __future__ import annotations

import pandas as pd

from pyforge.atlas.pipelines.pypi_intelligence.nodes import export_pypi_conda_map


def test_export_collapses_phase_c_to_flat_map():
    df = pd.DataFrame(
        {
            "pypi_name": ["a", "b"],
            "conda_name": ["conda-a", "conda-b"],
            "match_source": ["parselmouth", "g10_spelling"],
        }
    )
    assert export_pypi_conda_map(df) == {"a": "conda-a", "b": "conda-b"}


def test_g10_spelling_survives_and_is_not_clobbered():
    # pypi_name x has a g10_spelling row (conda-A) AND a weaker unknown row (conda-B):
    # g10_spelling MUST win regardless of row order (no-clobber; AC-4 "g10_spelling survives").
    df = pd.DataFrame(
        {
            "pypi_name": ["x", "x"],
            "conda_name": ["conda-A", "conda-B"],
            "match_source": ["g10_spelling", "weak_source"],
        }
    )
    assert export_pypi_conda_map(df)["x"] == "conda-A"
    # order-independent — reversed rows produce the same winner.
    df_rev = df.iloc[::-1].reset_index(drop=True)
    assert export_pypi_conda_map(df_rev)["x"] == "conda-A"


def test_weak_source_never_clobbers_a_protected_tier():
    df = pd.DataFrame(
        {
            "pypi_name": ["y", "y"],
            "conda_name": ["conda-P", "conda-W"],
            "match_source": ["parselmouth", "weak"],
        }
    )
    assert export_pypi_conda_map(df)["y"] == "conda-P"


def test_equal_tier_collision_is_order_independent_deterministic():
    # EC7/BH-5: two SAME-tier rows with different conda_name resolve deterministically
    # (lexicographically smaller wins) regardless of Phase C row order.
    df = pd.DataFrame(
        {
            "pypi_name": ["q", "q"],
            "conda_name": ["conda-zzz", "conda-aaa"],
            "match_source": ["parselmouth", "parselmouth"],
        }
    )
    assert export_pypi_conda_map(df)["q"] == "conda-aaa"
    assert export_pypi_conda_map(df.iloc[::-1].reset_index(drop=True))["q"] == "conda-aaa"


def test_unhashable_match_source_cell_does_not_crash():
    # EC5: a non-string / unhashable match_source cell defaults to rank 1 (never a TypeError).
    df = pd.DataFrame(
        {
            "pypi_name": ["u"],
            "conda_name": ["conda-u"],
            "match_source": [["a", "list"]],
        }
    )
    assert export_pypi_conda_map(df) == {"u": "conda-u"}


def test_empty_and_malformed_inputs_yield_empty_map():
    assert export_pypi_conda_map(pd.DataFrame()) == {}
    assert export_pypi_conda_map(None) == {}
    # a non-string / missing conda_name is skipped (malformed cell — never exported).
    df = pd.DataFrame({"pypi_name": ["z", "w"], "conda_name": [None, ["list"]], "match_source": ["parselmouth", "parselmouth"]})
    assert export_pypi_conda_map(df) == {}


def test_missing_match_source_column_defaults_rank():
    df = pd.DataFrame({"pypi_name": ["a"], "conda_name": ["conda-a"]})
    assert export_pypi_conda_map(df) == {"a": "conda-a"}


def test_flat_format_is_pypi_name_to_conda_name():
    # legacy-compatible {pypi_name: conda_name} shape (the retained authoring-read shim).
    df = pd.DataFrame(
        {"pypi_name": ["numpy"], "conda_name": ["numpy"], "match_source": ["parselmouth"]}
    )
    out = export_pypi_conda_map(df)
    assert out == {"numpy": "numpy"}
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in out.items())
