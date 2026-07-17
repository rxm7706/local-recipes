"""pypi_intelligence node unit tests (Story B2, Task 5 / AC-1, AC-2, AC-5)."""

from __future__ import annotations

import pandas as pd

from pyforge.atlas.pipelines.pypi_intelligence.nodes import (
    apply_readiness_scores,
    enumerate_pypi_universe,
    fetch_pypi_downloads,
    flag_cross_channel,
    map_pypi_conda,
    match_source_urls,
    phase_r_upsert_one,
    score_pypi_readiness,
    snapshot_pypi_serials,
    v_pypi_intelligence_valid,
)


# -- Phase C (parselmouth mapping; g10_spelling tier survives, no-clobber) ---

def test_map_pypi_conda_preserves_g10_spelling_tier():
    parselmouth = pd.DataFrame(
        {
            "pypi_name": ["numpy", "altk", "orphan"],
            "conda_name": ["numpy", "altk-conda", "orphan"],
            "match_source": [pd.NA, "g10_spelling", pd.NA],
        }
    )
    enumerated = pd.DataFrame({"conda_name": ["numpy", "altk-conda"]})
    out = map_pypi_conda(parselmouth, enumerated)
    src = dict(zip(out["pypi_name"], out["match_source"]))
    assert src["altk"] == "g10_spelling"  # tier survives as a valid match_source
    assert src["numpy"] == "parselmouth"  # missing -> default
    assert "orphan" not in set(out["pypi_name"])  # not in enumerated -> dropped


def test_map_pypi_conda_empty_is_columned():
    out = map_pypi_conda(pd.DataFrame(), pd.DataFrame())
    assert list(out.columns) == ["pypi_name", "conda_name", "match_source"]


# -- Phase C.5 (source-url extend; no-clobber discipline) --------------------

def test_match_source_urls_no_clobber_of_protected_tier():
    base = pd.DataFrame(
        {
            "pypi_name": ["numpy", "altk"],
            "conda_name": ["numpy", "altk-conda"],
            "match_source": ["parselmouth", "g10_spelling"],
        }
    )
    # source-url candidates: numpy already protected (skip); newpkg is new (add).
    candidates = pd.DataFrame(
        {"pypi_name": ["numpy", "newpkg"], "conda_name": ["numpy-wrong", "newpkg-conda"]}
    )
    out = match_source_urls(base, candidates)
    m = out.set_index("pypi_name")
    assert m.loc["numpy", "conda_name"] == "numpy"  # protected, NOT clobbered
    assert m.loc["numpy", "match_source"] == "parselmouth"
    assert m.loc["newpkg", "match_source"] == "recipe_source_url"  # new candidate added
    assert m.loc["altk", "match_source"] == "g10_spelling"  # preserved


# -- Phase D (universe enumeration; skippable) -------------------------------

def test_enumerate_pypi_universe_normalizes_and_dedups():
    idx = pd.DataFrame({"pypi_name": ["a", "a", "b"], "last_serial": [10, 10, 20]})
    out = enumerate_pypi_universe(idx)
    assert set(out["pypi_name"]) == {"a", "b"}


def test_enumerate_pypi_universe_disabled_degrades_cleanly():
    # PHASE_D_UNIVERSE_DISABLED -> dataset yields nothing -> node no-ops (AD-13)
    out = enumerate_pypi_universe(pd.DataFrame())
    assert out.empty and list(out.columns) == ["pypi_name", "last_serial"]


# -- Phase O (activity band from snapshot deltas) ----------------------------

def test_snapshot_pypi_serials_activity_band():
    idx = pd.DataFrame(
        {
            "pypi_name": ["hot", "warm", "cold", "new"],
            "last_serial": [1000, 105, 100, 5],
            "prev_serial": [800, 100, 100, pd.NA],  # deltas 200/5/0/NA
        }
    )
    out = snapshot_pypi_serials(idx)
    band = dict(zip(out["pypi_name"], out["activity_band"]))
    assert band["hot"] == "high"      # >=100
    assert band["warm"] == "low"      # 5 -> 1..9
    assert band["cold"] == "dormant"  # 0
    assert band["new"] == "dormant"   # NA delta


# -- Phase P (pure normalization; INSERT OR IGNORE idempotency) --------------

def test_fetch_pypi_downloads_idempotent_dedup():
    df = pd.DataFrame(
        {
            "pypi_name": ["numpy", "numpy", "pandas"],
            "month": ["2026-01", "2026-01", "2026-01"],
            "downloads": [100, 999, 50],
        }
    )
    out = fetch_pypi_downloads(df)
    assert len(out) == 2  # (numpy,2026-01) deduped, first wins
    assert out.set_index("pypi_name").loc["numpy", "downloads"] == 100


def test_fetch_pypi_downloads_disabled_no_op():
    # Phase P off / dry-run abort -> dataset yields empty -> node no-ops (AD-6)
    out = fetch_pypi_downloads(pd.DataFrame())
    assert out.empty and list(out.columns) == ["pypi_name", "month", "downloads"]


# -- Phase Q (cross-channel BOOL pivot) --------------------------------------

def test_flag_cross_channel_pivots_per_channel_bools():
    df = pd.DataFrame(
        {
            "conda_name": ["torch", "torch", "numpy"],
            "channel": ["pytorch", "nvidia", "bioconda"],
        }
    )
    out = flag_cross_channel(df)
    m = out.set_index("conda_name")
    assert bool(m.loc["torch", "in_pytorch"]) is True
    assert bool(m.loc["torch", "in_nvidia"]) is True
    assert bool(m.loc["torch", "in_bioconda"]) is False
    assert bool(m.loc["numpy", "in_bioconda"]) is True
    assert bool(m.loc["numpy", "in_robostack"]) is False


# -- Phase R/S (readiness + template; view discipline) -----------------------

def test_score_pypi_readiness_emits_score_and_template():
    enriched = pd.DataFrame(
        {
            "pypi_name": ["clean", "rusty", "murky"],
            "packaging_shape": ["pure-python", "rust-pyo3", "unknown"],
            "license_spdx": ["MIT", "Apache-2.0", None],
            "license_raw": [None, None, None],
            "notes": [None, None, None],
        }
    )
    out = score_pypi_readiness(enriched)
    m = out.set_index("pypi_name")
    assert m.loc["clean", "conda_forge_readiness"] == 100  # pure+licensed
    assert m.loc["clean", "recommended_template"] == "python/noarch-recipe.yaml"
    assert m.loc["rusty", "recommended_template"] == "python/maturin-recipe.yaml"
    assert m.loc["murky", "conda_forge_readiness"] == 40   # unknown+unlicensed


def test_v_pypi_intelligence_valid_filters_view():
    scored = pd.DataFrame(
        {
            "pypi_name": ["a", "b"],
            "packaging_shape": ["pure-python", "unknown"],
            "conda_forge_readiness": [80, 40],
            "recommended_template": ["python/noarch-recipe.yaml", "python/noarch-recipe.yaml"],
            "notes": [None, None],
        }
    )
    view = v_pypi_intelligence_valid(scored)
    assert set(view["pypi_name"]) == {"a"}  # unknown shape excluded from the view


# -- single-write-path (add-handoff re-score routes through the SAME helper) --

def test_add_handoff_rescore_routes_through_apply_readiness_scores():
    # a full Phase-S pass...
    enriched = pd.DataFrame(
        {
            "pypi_name": ["pkg"],
            "packaging_shape": ["pure-python"],
            "license_spdx": ["MIT"],
            "license_raw": [None],
            "notes": ["operator override note"],
        }
    )
    full = apply_readiness_scores(enriched)
    # ...and a one-package add-handoff re-score through the SAME helper yields
    # the identical row (single-write-path property, AC-2).
    one = apply_readiness_scores(enriched.iloc[[0]])
    assert one.iloc[0]["conda_forge_readiness"] == full.iloc[0]["conda_forge_readiness"]
    assert one.iloc[0]["recommended_template"] == full.iloc[0]["recommended_template"]


def test_phase_r_upsert_one_replaces_by_pypi_name():
    base = pd.DataFrame(
        {
            "pypi_name": ["a"],
            "packaging_shape": ["unknown"],
            "license_spdx": [None],
            "license_raw": [None],
            "notes": [None],
        }
    )
    out = phase_r_upsert_one(base, {"pypi_name": "a", "packaging_shape": "pure-python", "license_spdx": "MIT"})
    assert len(out) == 1
    assert out.iloc[0]["packaging_shape"] == "pure-python"  # replaced, not appended


# -- notes operator overrides survive Phase S re-runs (AC-5) ------------------

def test_notes_operator_override_survives_rescore():
    enriched = pd.DataFrame(
        {
            "pypi_name": ["pkg"],
            "packaging_shape": ["pure-python"],
            "license_spdx": ["MIT"],
            "license_raw": [None],
            "notes": [None],  # this run's enrichment carries no note
        }
    )
    prior = pd.DataFrame({"pypi_name": ["pkg"], "notes": ["do-not-package: license review pending"]})
    out = apply_readiness_scores(enriched, prior_scored=prior)
    assert out.iloc[0]["notes"] == "do-not-package: license review pending"  # NOT clobbered
