"""Review-hardening regression tests for pypi_intelligence nodes (Story B2 review pass).

Locks in the edge-case fixes surfaced by the adversarial review: malformed/list/NaN
cells, non-numeric serial/timestamp stamps, missing-key upsert, mis-shaped view frames,
and the notes-survive-Phase-S-re-run behavior (AC-5) demonstrated at the pipeline level.
"""

from __future__ import annotations

import pandas as pd

from pyforge.atlas.pipelines.pypi_intelligence.nodes import (
    apply_readiness_scores,
    enrich_pypi_intelligence,
    fetch_pypi_current_versions,
    flag_cross_channel,
    match_source_urls,
    phase_r_upsert_one,
    score_pypi_readiness,
    snapshot_pypi_serials,
    v_pypi_intelligence_valid,
)


def test_apply_readiness_scores_nan_shape_becomes_unknown():
    enriched = pd.DataFrame(
        {"pypi_name": ["x"], "packaging_shape": [float("nan")], "license_spdx": [None], "license_raw": [None], "notes": [None]}
    )
    out = apply_readiness_scores(enriched)
    # NaN shape must NOT leak (NaN is truthy) — coerced to "unknown".
    assert out.iloc[0]["packaging_shape"] == "unknown"
    assert out.iloc[0]["recommended_template"] == "python/noarch-recipe.yaml"


def test_match_source_urls_skips_malformed_list_conda_name():
    base = pd.DataFrame({"pypi_name": ["a"], "conda_name": ["a"], "match_source": ["parselmouth"]})
    # a list-valued conda_name is malformed: it must NOT crash pd.isna (ambiguous truth)
    # and must be SKIPPED (not appended as an invalid mapping).
    cand = pd.DataFrame({"pypi_name": ["b", "c"], "conda_name": [["not", "scalar"], "c-conda"]})
    out = match_source_urls(base, cand)
    assert "b" not in set(out["pypi_name"])  # malformed list cell skipped
    assert "c" in set(out["pypi_name"])      # valid string candidate added, no crash


def test_flag_cross_channel_skips_malformed_list_conda_name():
    df = pd.DataFrame({"conda_name": [["x"], "numpy"], "channel": ["bioconda", "bioconda"]})
    out = flag_cross_channel(df)  # must not raise on the list cell (unhashable key)
    assert set(out["conda_name"]) == {"numpy"}  # list cell skipped


def test_phase_h_non_numeric_fetched_at_does_not_crash():
    df = pd.DataFrame(
        {
            "pypi_name": ["p"],
            "version": ["1"],
            "pypi_last_serial": [5],
            "pypi_version_serial_at_fetch": [5],  # equal -> not never/moved
            "fetched_at": ["not-a-timestamp"],    # unparseable -> treated as stale
        }
    )
    uni = pd.DataFrame({"pypi_name": ["p"], "last_serial": [5]})
    out = fetch_pypi_current_versions(df, uni, now=1_800_000_000)
    # unparseable stamp -> safety_recheck True -> eligible (fail-safe), no crash
    assert set(out["pypi_name"]) == {"p"}


def test_snapshot_non_numeric_serial_degrades_to_dormant():
    idx = pd.DataFrame({"pypi_name": ["p"], "last_serial": ["x"], "prev_serial": [10]})
    out = snapshot_pypi_serials(idx)  # int("x") would crash without the fix
    assert out.iloc[0]["activity_band"] == "dormant"


def test_phase_r_upsert_one_missing_key_replaces_prior_missing_row():
    base = pd.DataFrame(
        {"pypi_name": [None], "packaging_shape": ["unknown"], "license_spdx": [None], "license_raw": [None], "notes": [None]}
    )
    out = phase_r_upsert_one(base, {"pypi_name": None, "packaging_shape": "pure-python"})
    assert len(out) == 1  # prior None-key row replaced, not duplicated


def test_v_pypi_intelligence_valid_missing_columns_no_keyerror():
    df = pd.DataFrame({"pypi_name": ["a"], "other": [1]})  # lacks scored columns
    out = v_pypi_intelligence_valid(df)  # must not KeyError
    assert out.empty


# -- AC-5: notes survive a Phase S re-run via the enriched->scored carry --------

def test_notes_survive_phase_s_rerun_via_enriched_carry():
    # operator note lives on the enriched table; Phase S READS enriched and carries the
    # note into scored, so a Phase S re-run preserves it (the pipeline-level mechanism).
    pypi_json = pd.DataFrame(
        {"pypi_name": ["pkg"], "pure_python": [True], "license_spdx": ["MIT"], "license_raw": ["MIT"],
         "notes": ["operator: hold - license review"]}
    )
    enriched = enrich_pypi_intelligence(pypi_json)
    assert enriched.iloc[0]["notes"] == "operator: hold - license review"  # R carries it
    scored_run1 = score_pypi_readiness(enriched)
    scored_run2 = score_pypi_readiness(enriched)  # a re-run reads the SAME enriched
    assert scored_run1.iloc[0]["notes"] == "operator: hold - license review"
    assert scored_run2.iloc[0]["notes"] == "operator: hold - license review"  # survives
