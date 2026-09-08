"""Story 21.6 (CAP-3, Phase D identity join) — the fixed parity fixture corpus
(identity-contract.md Parity test corpus), loaded from the tracked JSON fixture
under ``tests/parity/fixtures/upstream_discovery/`` and run through
``build_identity_packages_primary`` end to end.

This is a SEPARATE, literal fixture-file exercise of the same join
``test_nodes.py``'s per-scenario unit tests already cover with inline
``DataFrame`` fixtures — the JSON corpus is a reviewable, tracked artifact of
the exact input/expected-output contract (identity-contract.md's own named
scenarios: associator hit, inventory-derived fallback, board-only extra,
unmapped none, conda_purl only when CondaForge_Verified, overlay URLs from
feedstock map + staged PR + local recipes), independent of how the pure join
helpers happen to be organized inside ``nodes.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from pyforge.atlas.pipelines.upstream_discovery.nodes import build_identity_packages_primary

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2] / "parity" / "fixtures" / "upstream_discovery" / "identity_join_corpus.json"
)

_COLUMNS = {
    "purl_associator_mappings_raw": ["assoc_key", "purl", "type", "status", "alternative_purls", "cpes", "fetched_at"],
    "openteams_project_1_board_raw": ["number", "title", "url", "state", "milestone", "fetched_at"],
    "discovery_staged_recipes_prs_raw": ["number", "state", "merged_at", "url", "title", "file_paths", "fetched_at"],
    "discovery_local_recipes_raw": ["dir_name", "names", "url", "build_status"],
    "core_feedstock_attribution": ["conda_name", "feedstock_name"],
    "enterprise_jfrog_names": ["pypi_name", "conda_name", "is_internal"],
    "enterprise_conda_maintainers": ["core_python_package_name", "role", "feedstock_slug", "repository_source"],
    "pypi_universe": ["pypi_name"],
    "core_packages_enumerated": ["conda_name"],
}


def _load_corpus() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _frame(inputs: dict, key: str) -> pd.DataFrame:
    return pd.DataFrame(inputs.get(key, []), columns=_COLUMNS[key])


def test_fixture_file_exists_and_parses():
    corpus = _load_corpus()
    assert "inputs" in corpus and "expected_rows" in corpus


def test_identity_join_corpus_matches_expected_rows_exactly():
    corpus = _load_corpus()
    inputs = corpus["inputs"]
    out = build_identity_packages_primary(
        _frame(inputs, "purl_associator_mappings_raw"),
        _frame(inputs, "openteams_project_1_board_raw"),
        _frame(inputs, "discovery_staged_recipes_prs_raw"),
        _frame(inputs, "discovery_local_recipes_raw"),
        _frame(inputs, "core_feedstock_attribution"),
        _frame(inputs, "enterprise_jfrog_names"),
        _frame(inputs, "enterprise_conda_maintainers"),
        _frame(inputs, "pypi_universe"),
        _frame(inputs, "core_packages_enumerated"),
    )
    by_name = {name: row for name, row in out.set_index("Core_Python_Package_Name", drop=False).iterrows()}
    expected_rows = corpus["expected_rows"]
    assert set(expected_rows) <= set(by_name), (
        f"missing expected names in join output: {set(expected_rows) - set(by_name)}"
    )
    mismatches: dict[str, dict] = {}
    for name, expected_cols in expected_rows.items():
        row = by_name[name]
        bad = {
            col: {"expected": expected, "actual": row[col]}
            for col, expected in expected_cols.items()
            if row[col] != expected
        }
        if bad:
            mismatches[name] = bad
    assert not mismatches, f"parity corpus mismatches: {mismatches}"


def test_identity_join_corpus_row_count_matches_universe_plus_board_only():
    corpus = _load_corpus()
    inputs = corpus["inputs"]
    out = build_identity_packages_primary(
        _frame(inputs, "purl_associator_mappings_raw"),
        _frame(inputs, "openteams_project_1_board_raw"),
        _frame(inputs, "discovery_staged_recipes_prs_raw"),
        _frame(inputs, "discovery_local_recipes_raw"),
        _frame(inputs, "core_feedstock_attribution"),
        _frame(inputs, "enterprise_jfrog_names"),
        _frame(inputs, "enterprise_conda_maintainers"),
        _frame(inputs, "pypi_universe"),
        _frame(inputs, "core_packages_enumerated"),
    )
    # 3 CDO-ENT-JFROG names + 3 CDO-ENT-CONDA names + 1 board-only extra = 7 rows,
    # never a silent drop.
    assert len(out) == 7
