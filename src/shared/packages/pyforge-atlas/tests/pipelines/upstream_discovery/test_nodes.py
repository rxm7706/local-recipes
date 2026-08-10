"""``upstream_discovery`` node unit tests (Story 13.1 CAP-1 / FR-64 + Story 13.2 CAP-2 /
FR-65).

Pure trigger-node test mirroring ``tests/pipelines/vulnerability/test_nodes.py``'s style
(there is no equivalent trigger-node test file there — the closest precedent is
``refresh_vdb_store``'s cadence coercion, exercised indirectly via
``tests/pipelines/test_refresh_schedule_fixtures.py``; here it is tested directly against
a ``ttls`` dict, present / missing / non-numeric).

The CAP-2 classifier tests below mirror ``tests/pipelines/seed_gaps/test_nodes.py``'s
style: small hand-built fixture ``DataFrame``s, one test per I/O & Edge-Case Matrix row
(spec-13-2-tier-classification.md)."""

from __future__ import annotations

import pandas as pd
import pytest

from pyforge.atlas.datasets.refresh import RefreshRequest
from pyforge.atlas.pipelines.upstream_discovery import nodes as N
from pyforge.atlas.pipelines.upstream_discovery.nodes import (
    DAILY_SECONDS,
    refresh_trending_candidates,
)


def test_refresh_trending_candidates_reads_the_ttls_cadence():
    req = refresh_trending_candidates({"trending_candidates": 86400})
    assert isinstance(req, RefreshRequest)
    assert req.store == "trending_candidates"
    assert req.cadence_seconds == 86400
    assert req.force is False


def test_refresh_trending_candidates_missing_key_falls_back_to_daily_default():
    assert refresh_trending_candidates({}).cadence_seconds == DAILY_SECONDS
    assert refresh_trending_candidates(None).cadence_seconds == DAILY_SECONDS


def test_refresh_trending_candidates_non_numeric_value_falls_back_to_daily_default():
    assert refresh_trending_candidates({"trending_candidates": "nope"}).cadence_seconds == DAILY_SECONDS
    assert refresh_trending_candidates({"trending_candidates": None}).cadence_seconds == DAILY_SECONDS


# ---------------------------------------------------------------------------
# classify_trending_candidates (Story 13.2, CAP-2 / FR-65) — helper unit tests
# ---------------------------------------------------------------------------

_TC_COLS = ["repo_full_name", "description"]
_OUT_COLS = _TC_COLS + ["pypi_name", "tier", "reason"]


def _tc(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=_TC_COLS)


def _universe(names: list[str]) -> pd.DataFrame:
    return pd.DataFrame({"pypi_name": names})


def _mapping(names: list[str]) -> pd.DataFrame:
    return pd.DataFrame({"conda_name": [f"conda-{n}" for n in names], "pypi_name": names})


def _intel(rows: list[dict]) -> pd.DataFrame:
    cols = ["pypi_name", "packaging_shape", "license_spdx", "license_raw", "notes"]
    return pd.DataFrame(rows, columns=cols)


def test_normalize_pypi_name_lowercases_and_collapses_separators():
    assert N._normalize_pypi_name("Foo_Bar.Baz") == "foo-bar-baz"
    assert N._normalize_pypi_name("scikit--learn") == "scikit-learn"
    assert N._normalize_pypi_name("already-normal") == "already-normal"


def test_resolve_pypi_name_exact_normalized_match():
    universe = _universe(["cool.Pkg_Name"])
    assert N._resolve_pypi_name("someone/cool-pkg-name", universe) == "cool.Pkg_Name"


def test_resolve_pypi_name_no_match_returns_none():
    universe = _universe(["other-package"])
    assert N._resolve_pypi_name("someone/coolpkg", universe) is None


@pytest.mark.parametrize(
    "repo_full_name",
    ["", "no-slash-here", "/", None],
)
def test_resolve_pypi_name_malformed_repo_full_name_returns_none(repo_full_name):
    universe = _universe(["coolpkg"])
    assert N._resolve_pypi_name(repo_full_name, universe) is None


@pytest.mark.parametrize(
    "universe",
    [None, pd.DataFrame(), pd.DataFrame({"other_col": ["x"]})],
)
def test_resolve_pypi_name_empty_or_malformed_universe_returns_none(universe):
    assert N._resolve_pypi_name("someone/coolpkg", universe) is None


def test_is_awesome_list_repo_prefix():
    assert N._is_awesome_list("someone/awesome-python", None) is True
    assert N._is_awesome_list("someone/AWESOME-things", None) is True


def test_is_awesome_list_description_heuristic():
    assert N._is_awesome_list("someone/pylist", "A curated list of things") is True
    assert N._is_awesome_list("someone/pylist", "An Awesome List of things") is True
    assert N._is_awesome_list("someone/pylist", "just a normal package") is False


def test_is_awesome_list_missing_or_nan_description_never_raises():
    assert N._is_awesome_list("someone/pylist", None) is False
    assert N._is_awesome_list("someone/pylist", float("nan")) is False


# ---------------------------------------------------------------------------
# classify_trending_candidates — one test per I/O & Edge-Case Matrix row
# ---------------------------------------------------------------------------


def test_tier1_pure_python_osi_licensed_not_on_cf():
    """Tier-1 happy path."""
    tc = _tc([{"repo_full_name": "someone/coolpkg", "description": "a cool package"}])
    universe = _universe(["coolpkg"])
    mapping = _mapping(["unrelated-pkg"])
    intel = _intel(
        [{"pypi_name": "coolpkg", "packaging_shape": "pure-python", "license_spdx": "MIT",
          "license_raw": "MIT", "notes": None}]
    )
    out = N.classify_trending_candidates(tc, universe, mapping, intel)
    assert list(out.columns) == _OUT_COLS
    row = out.iloc[0]
    assert row["pypi_name"] == "coolpkg"
    assert row["tier"] == "1"
    assert row["reason"]


@pytest.mark.parametrize("shape", ["c-extension", "cython", "rust-pyo3"])
def test_tier2_compiled_shape_not_on_cf(shape):
    """Tier-2 happy path."""
    tc = _tc([{"repo_full_name": "someone/fastpkg", "description": "a fast package"}])
    universe = _universe(["fastpkg"])
    mapping = _mapping(["unrelated-pkg"])
    intel = _intel(
        [{"pypi_name": "fastpkg", "packaging_shape": shape, "license_spdx": "Apache-2.0",
          "license_raw": "Apache-2.0", "notes": None}]
    )
    out = N.classify_trending_candidates(tc, universe, mapping, intel)
    row = out.iloc[0]
    assert row["pypi_name"] == "fastpkg"
    assert row["tier"] == "2"
    assert shape in row["reason"]


def test_already_on_conda_forge_skip():
    tc = _tc([{"repo_full_name": "someone/existingpkg", "description": None}])
    universe = _universe(["existingpkg"])
    mapping = _mapping(["existingpkg"])
    intel = _intel(
        [{"pypi_name": "existingpkg", "packaging_shape": "pure-python", "license_spdx": "MIT",
          "license_raw": "MIT", "notes": None}]
    )
    out = N.classify_trending_candidates(tc, universe, mapping, intel)
    row = out.iloc[0]
    assert row["tier"] == "skip"
    assert row["reason"] == "already-on-conda-forge"


def test_awesome_list_skip():
    tc = _tc([{"repo_full_name": "someone/awesome-python", "description": None}])
    universe = _universe(["unrelated-package"])
    mapping = pd.DataFrame(columns=["conda_name", "pypi_name"])
    intel = _intel([])
    out = N.classify_trending_candidates(tc, universe, mapping, intel)
    row = out.iloc[0]
    assert row["pypi_name"] is None
    assert row["tier"] == "skip"
    assert row["reason"] == "awesome-list"


def test_generic_no_pypi_artifact_skip():
    tc = _tc([{"repo_full_name": "someone/some-app", "description": "just an app"}])
    universe = _universe(["unrelated-package"])
    mapping = pd.DataFrame(columns=["conda_name", "pypi_name"])
    intel = _intel([])
    out = N.classify_trending_candidates(tc, universe, mapping, intel)
    row = out.iloc[0]
    assert row["pypi_name"] is None
    assert row["tier"] == "skip"
    assert row["reason"] == "no-pypi-artifact"


def test_missing_intelligence_row_is_unclassified_needs_human():
    tc = _tc([{"repo_full_name": "someone/newpkg", "description": None}])
    universe = _universe(["newpkg"])
    mapping = _mapping(["unrelated-pkg"])
    # intel table is non-empty (has data for an unrelated package) but lacks a row
    # for "newpkg" specifically.
    intel = _intel(
        [{"pypi_name": "unrelated", "packaging_shape": "pure-python", "license_spdx": "MIT",
          "license_raw": "MIT", "notes": None}]
    )
    out = N.classify_trending_candidates(tc, universe, mapping, intel)
    row = out.iloc[0]
    assert row["pypi_name"] == "newpkg"
    assert row["tier"] == "skip"
    assert row["reason"] == "unclassified-needs-human"


def test_not_osi_license_skip():
    tc = _tc([{"repo_full_name": "someone/proprietarypkg", "description": None}])
    universe = _universe(["proprietarypkg"])
    mapping = _mapping(["unrelated-pkg"])
    intel = _intel(
        [{"pypi_name": "proprietarypkg", "packaging_shape": "pure-python",
          "license_spdx": "Proprietary", "license_raw": "Proprietary", "notes": None}]
    )
    out = N.classify_trending_candidates(tc, universe, mapping, intel)
    row = out.iloc[0]
    assert row["tier"] == "skip"
    assert row["reason"] == "not-osi-license"


def test_missing_license_spdx_is_also_not_osi_license():
    tc = _tc([{"repo_full_name": "someone/nolicensepkg", "description": None}])
    universe = _universe(["nolicensepkg"])
    mapping = _mapping(["unrelated-pkg"])
    intel = _intel(
        [{"pypi_name": "nolicensepkg", "packaging_shape": "pure-python",
          "license_spdx": None, "license_raw": None, "notes": None}]
    )
    out = N.classify_trending_candidates(tc, universe, mapping, intel)
    row = out.iloc[0]
    assert row["tier"] == "skip"
    assert row["reason"] == "not-osi-license"


def test_ambiguous_packaging_shape_is_unclassified_needs_human():
    tc = _tc([{"repo_full_name": "someone/mysterypkg", "description": None}])
    universe = _universe(["mysterypkg"])
    mapping = _mapping(["unrelated-pkg"])
    intel = _intel(
        [{"pypi_name": "mysterypkg", "packaging_shape": "unknown", "license_spdx": "MIT",
          "license_raw": "MIT", "notes": None}]
    )
    out = N.classify_trending_candidates(tc, universe, mapping, intel)
    row = out.iloc[0]
    assert row["tier"] == "skip"
    assert row["reason"] == "unclassified-needs-human"


def test_empty_trending_candidates_degrades_to_empty_output_schema():
    tc = pd.DataFrame(columns=_TC_COLS)
    out = N.classify_trending_candidates(tc, _universe(["x"]), _mapping(["x"]), _intel([]))
    assert out.empty
    assert list(out.columns) == _OUT_COLS


def test_malformed_trending_candidates_missing_repo_full_name_degrades_to_empty():
    tc = pd.DataFrame({"description": ["no repo_full_name column"]})
    out = N.classify_trending_candidates(tc, _universe(["x"]), _mapping(["x"]), _intel([]))
    assert out.empty
    assert "pypi_name" in out.columns and "tier" in out.columns and "reason" in out.columns


def test_none_trending_candidates_degrades_to_empty():
    out = N.classify_trending_candidates(None, _universe(["x"]), _mapping(["x"]), _intel([]))
    assert out.empty
    assert list(out.columns) == ["pypi_name", "tier", "reason"]


def test_nan_repo_full_name_cell_does_not_raise():
    """A NaN ``repo_full_name`` cell (e.g. a partially-malformed row surviving the
    dataset write) must not crash the classifier — degrades to unresolved ->
    no-pypi-artifact, never a TypeError from a non-string ``in`` check."""
    tc = pd.DataFrame({"repo_full_name": [float("nan")], "description": [None]})
    out = N.classify_trending_candidates(tc, _universe(["x"]), _mapping(["x"]), _intel([]))
    assert len(out) == 1
    row = out.iloc[0]
    assert row["pypi_name"] is None
    assert row["tier"] == "skip"
    assert row["reason"] == "no-pypi-artifact"


def test_cold_start_all_three_signal_tables_empty_still_detects_awesome_list():
    """Review finding (Story 13.2): the awesome-list heuristic depends on no join
    table, so it must still fire even when every signal table is unusable — a
    blanket cold-start override that discarded this free signal was a real defect."""
    tc = _tc(
        [
            {"repo_full_name": "someone/coolpkg", "description": "a cool package"},
            {"repo_full_name": "someone/awesome-python", "description": None},
        ]
    )
    empty_universe = pd.DataFrame(columns=["pypi_name"])
    empty_mapping = pd.DataFrame(columns=["conda_name", "pypi_name"])
    empty_intel = _intel([])
    out = N.classify_trending_candidates(tc, empty_universe, empty_mapping, empty_intel)
    assert len(out) == 2
    coolpkg_row = out[out["repo_full_name"] == "someone/coolpkg"].iloc[0]
    assert coolpkg_row["tier"] == "skip"
    assert coolpkg_row["reason"] == "unclassified-needs-human"
    assert coolpkg_row["pypi_name"] is None
    awesome_row = out[out["repo_full_name"] == "someone/awesome-python"].iloc[0]
    assert awesome_row["tier"] == "skip"
    assert awesome_row["reason"] == "awesome-list"


def test_none_signal_tables_do_not_raise():
    """None (rather than an empty DataFrame) for every join-signal table must not
    raise — same per-signal degradation as the all-empty-tables case."""
    tc = _tc([{"repo_full_name": "someone/coolpkg", "description": None}])
    out = N.classify_trending_candidates(tc, None, None, None)
    assert len(out) == 1
    assert out.iloc[0]["tier"] == "skip"
    assert out.iloc[0]["reason"] == "unclassified-needs-human"


def test_pypi_universe_alone_unusable_degrades_to_unclassified_not_no_pypi_artifact():
    """Review finding (Story 13.2): when ONLY `pypi_universe` fails to materialize
    (the other two tables are fine), a non-awesome-list row must not confidently
    claim `no-pypi-artifact` — we never actually searched."""
    tc = _tc([{"repo_full_name": "someone/some-app", "description": "just an app"}])
    empty_universe = pd.DataFrame(columns=["pypi_name"])
    out = N.classify_trending_candidates(tc, empty_universe, _mapping(["other"]), _intel([]))
    row = out.iloc[0]
    assert row["pypi_name"] is None
    assert row["tier"] == "skip"
    assert row["reason"] == "unclassified-needs-human"


def test_pypi_conda_mapping_alone_unusable_degrades_resolved_row_to_unclassified():
    """Review finding (Story 13.2): when `pypi_universe` resolves a name but
    `pypi_conda_mapping` is unusable, we cannot confirm not-on-cf — must not fall
    through to a confident tier/license decision."""
    tc = _tc([{"repo_full_name": "someone/coolpkg", "description": None}])
    universe = _universe(["coolpkg"])
    empty_mapping = pd.DataFrame(columns=["conda_name", "pypi_name"])
    intel = _intel(
        [{"pypi_name": "coolpkg", "packaging_shape": "pure-python", "license_spdx": "MIT",
          "license_raw": "MIT", "notes": None}]
    )
    out = N.classify_trending_candidates(tc, universe, empty_mapping, intel)
    row = out.iloc[0]
    assert row["pypi_name"] == "coolpkg"
    assert row["tier"] == "skip"
    assert row["reason"] == "unclassified-needs-human"


def test_join_key_case_and_separator_mismatch_across_tables_still_resolves():
    """Review finding (Story 13.2): `pypi_universe` and `pypi_conda_mapping` /
    `pypi_intelligence_enriched` are independently-sourced tables that can carry
    the same package under different casing/separators. All three joins must be
    PEP-503-normalized consistently, not just the repo->pypi_universe match."""
    tc = _tc([{"repo_full_name": "someone/Cool-Pkg", "description": None}])
    universe = _universe(["Cool_Pkg"])  # canonical form differs in case/separator
    mapping = _mapping(["cool.pkg"])  # on-cf table spells it differently again
    out = N.classify_trending_candidates(tc, universe, mapping, _intel([]))
    row = out.iloc[0]
    assert row["pypi_name"] == "Cool_Pkg"
    assert row["tier"] == "skip"
    assert row["reason"] == "already-on-conda-forge"


def test_non_string_license_spdx_does_not_raise():
    """Review finding (Story 13.2): a non-string `license_spdx` (e.g. a list from a
    malformed upstream record) must not raise from the frozenset `in` check."""
    tc = _tc([{"repo_full_name": "someone/weirdlicensepkg", "description": None}])
    universe = _universe(["weirdlicensepkg"])
    mapping = _mapping(["unrelated-pkg"])
    intel = _intel(
        [{"pypi_name": "weirdlicensepkg", "packaging_shape": "pure-python",
          "license_spdx": ["MIT"], "license_raw": None, "notes": None}]
    )
    out = N.classify_trending_candidates(tc, universe, mapping, intel)
    row = out.iloc[0]
    assert row["tier"] == "skip"
    assert row["reason"] == "not-osi-license"


def test_resolve_pypi_name_is_the_production_resolution_path():
    """Review finding (Story 13.2): ``_resolve_pypi_name`` was dead code — the node
    re-implemented resolution inline, so the nine helper tests above exercised a copy
    that never shipped and the two could drift apart silently. Monkeypatching the
    helper must therefore change the node's output."""
    tc = _tc([{"repo_full_name": "someone/coolpkg", "description": None}])
    universe = _universe(["coolpkg"])
    calls: list[str] = []

    def _spy(repo_full_name, pypi_universe, *, index=None):
        calls.append(repo_full_name)
        return None

    original = N._resolve_pypi_name
    N._resolve_pypi_name = _spy
    try:
        out = N.classify_trending_candidates(tc, universe, _mapping(["other"]), _intel([]))
    finally:
        N._resolve_pypi_name = original

    assert calls == ["someone/coolpkg"]
    assert out.iloc[0]["pypi_name"] is None


def test_resolve_pypi_name_accepts_a_prebuilt_index():
    universe = _universe(["cool.Pkg_Name"])
    index = N._normalized_pypi_index(universe)
    # The prebuilt index is authoritative — an unrelated frame is not consulted.
    assert N._resolve_pypi_name("someone/cool-pkg-name", pd.DataFrame(), index=index) == "cool.Pkg_Name"


@pytest.mark.parametrize("null_value", [None, float("nan"), pd.NA])
def test_all_null_join_keys_are_not_a_usable_signal(null_value):
    """Review finding (Story 13.2): a signal table that is non-empty and carries the
    column but whose every ``pypi_name`` cell is missing was never searchable — it must
    degrade like an empty table, not license a confident ``no-pypi-artifact`` call.
    ``pd.NA`` is included because the string dtypes this project targets under pandas
    3.0 produce it for a null cell (it is neither ``None`` nor a ``float``)."""
    tc = _tc([{"repo_full_name": "someone/some-app", "description": "just an app"}])
    null_universe = pd.DataFrame({"pypi_name": [null_value]})
    out = N.classify_trending_candidates(tc, null_universe, _mapping(["other"]), _intel([]))
    row = out.iloc[0]
    assert row["pypi_name"] is None
    assert row["tier"] == "skip"
    assert row["reason"] == "unclassified-needs-human"


def test_pd_na_join_key_is_never_inserted_as_a_live_index_entry():
    """``pd.NA`` must not survive as the literal join key ``"<na>"`` — a repo actually
    named ``<NA>`` would otherwise false-match it."""
    assert N._normalized_pypi_index(pd.DataFrame({"pypi_name": [pd.NA, "realpkg"]})) == {
        "realpkg": "realpkg"
    }
    assert N._is_missing(pd.NA) is True
    assert N._is_missing(["MIT"]) is False


def test_all_null_mapping_keys_degrade_resolved_row_to_unclassified():
    """The same rule on the on-conda-forge side: an unsearchable mapping table cannot
    confirm not-on-cf, so a resolved row must not fall through to a confident tier."""
    tc = _tc([{"repo_full_name": "someone/coolpkg", "description": None}])
    universe = _universe(["coolpkg"])
    null_mapping = pd.DataFrame({"conda_name": ["conda-x"], "pypi_name": [None]})
    intel = _intel(
        [{"pypi_name": "coolpkg", "packaging_shape": "pure-python", "license_spdx": "MIT",
          "license_raw": "MIT", "notes": None}]
    )
    out = N.classify_trending_candidates(tc, universe, null_mapping, intel)
    row = out.iloc[0]
    assert row["tier"] == "skip"
    assert row["reason"] == "unclassified-needs-human"


def test_malformed_packaging_shape_degrades_to_unclassified_not_confident_tier2():
    """Review finding (Story 13.2): an unexpected `packaging_shape` value (typo,
    new/unhandled shape) must not silently earn a confident tier "2" — only the
    three known compiled shapes do."""
    tc = _tc([{"repo_full_name": "someone/oddshapepkg", "description": None}])
    universe = _universe(["oddshapepkg"])
    mapping = _mapping(["unrelated-pkg"])
    intel = _intel(
        [{"pypi_name": "oddshapepkg", "packaging_shape": "nim-nimpy", "license_spdx": "MIT",
          "license_raw": "MIT", "notes": None}]
    )
    out = N.classify_trending_candidates(tc, universe, mapping, intel)
    row = out.iloc[0]
    assert row["tier"] == "skip"
    assert row["reason"] == "unclassified-needs-human"
