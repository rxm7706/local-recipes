"""``upstream_discovery`` node unit tests (Story 13.1 CAP-1 / FR-64 + Story 13.2 CAP-2 /
FR-65 + Story 13.4 CAP-4 / FR-67).

Pure trigger-node test mirroring ``tests/pipelines/vulnerability/test_nodes.py``'s style
(there is no equivalent trigger-node test file there — the closest precedent is
``refresh_vdb_store``'s cadence coercion, exercised indirectly via
``tests/pipelines/test_refresh_schedule_fixtures.py``; here it is tested directly against
a ``ttls`` dict, present / missing / non-numeric).

The CAP-2 classifier tests below mirror ``tests/pipelines/seed_gaps/test_nodes.py``'s
style: small hand-built fixture ``DataFrame``s, one test per I/O & Edge-Case Matrix row
(spec-13-2-tier-classification.md).

The CAP-4 ``load_org_audit_candidates`` tests (Story 13.4) follow the same style: one
test per I/O & Edge-Case Matrix row, plus a reuse/drop test proving
``classify_trending_candidates`` tolerates the narrower ``org_audit_candidates`` schema
and reproduces the shipped-since-drop behavior (spec-13-4-fixed-source-audit-track.md)."""

from __future__ import annotations

import pandas as pd
import pytest

from pyforge.atlas.datasets.refresh import RefreshRequest
from pyforge.atlas.pipelines.upstream_discovery import nodes as N
from pyforge.atlas.pipelines.upstream_discovery.nodes import (
    DAILY_SECONDS,
    load_org_audit_candidates,
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
        [
            {
                "pypi_name": "coolpkg",
                "packaging_shape": "pure-python",
                "license_spdx": "MIT",
                "license_raw": "MIT",
                "notes": None,
            }
        ]
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
        [
            {
                "pypi_name": "fastpkg",
                "packaging_shape": shape,
                "license_spdx": "Apache-2.0",
                "license_raw": "Apache-2.0",
                "notes": None,
            }
        ]
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
        [
            {
                "pypi_name": "existingpkg",
                "packaging_shape": "pure-python",
                "license_spdx": "MIT",
                "license_raw": "MIT",
                "notes": None,
            }
        ]
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
        [
            {
                "pypi_name": "unrelated",
                "packaging_shape": "pure-python",
                "license_spdx": "MIT",
                "license_raw": "MIT",
                "notes": None,
            }
        ]
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
        [
            {
                "pypi_name": "proprietarypkg",
                "packaging_shape": "pure-python",
                "license_spdx": "Proprietary",
                "license_raw": "Proprietary",
                "notes": None,
            }
        ]
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
        [
            {
                "pypi_name": "nolicensepkg",
                "packaging_shape": "pure-python",
                "license_spdx": None,
                "license_raw": None,
                "notes": None,
            }
        ]
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
        [
            {
                "pypi_name": "mysterypkg",
                "packaging_shape": "unknown",
                "license_spdx": "MIT",
                "license_raw": "MIT",
                "notes": None,
            }
        ]
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
        [
            {
                "pypi_name": "coolpkg",
                "packaging_shape": "pure-python",
                "license_spdx": "MIT",
                "license_raw": "MIT",
                "notes": None,
            }
        ]
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
        [
            {
                "pypi_name": "weirdlicensepkg",
                "packaging_shape": "pure-python",
                "license_spdx": ["MIT"],
                "license_raw": None,
                "notes": None,
            }
        ]
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
    assert N._normalized_pypi_index(pd.DataFrame({"pypi_name": [pd.NA, "realpkg"]})) == {"realpkg": "realpkg"}
    assert N._is_missing(pd.NA) is True
    assert N._is_missing(["MIT"]) is False


def test_all_null_mapping_keys_degrade_resolved_row_to_unclassified():
    """The same rule on the on-conda-forge side: an unsearchable mapping table cannot
    confirm not-on-cf, so a resolved row must not fall through to a confident tier."""
    tc = _tc([{"repo_full_name": "someone/coolpkg", "description": None}])
    universe = _universe(["coolpkg"])
    null_mapping = pd.DataFrame({"conda_name": ["conda-x"], "pypi_name": [None]})
    intel = _intel(
        [
            {
                "pypi_name": "coolpkg",
                "packaging_shape": "pure-python",
                "license_spdx": "MIT",
                "license_raw": "MIT",
                "notes": None,
            }
        ]
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
        [
            {
                "pypi_name": "oddshapepkg",
                "packaging_shape": "nim-nimpy",
                "license_spdx": "MIT",
                "license_raw": "MIT",
                "notes": None,
            }
        ]
    )
    out = N.classify_trending_candidates(tc, universe, mapping, intel)
    row = out.iloc[0]
    assert row["tier"] == "skip"
    assert row["reason"] == "unclassified-needs-human"


# ---------------------------------------------------------------------------
# load_org_audit_candidates (Story 13.4, CAP-4 / FR-67) — one test per I/O &
# Edge-Case Matrix row, plus a reuse/drop test against classify_trending_candidates.
# ---------------------------------------------------------------------------


def test_load_org_audit_candidates_happy_path_builds_repo_full_name_column():
    out = load_org_audit_candidates(
        [
            {"repo_full_name": "microsoft/edit"},
            {"repo_full_name": "microsoft/qlib"},
        ]
    )
    assert list(out.columns) == ["repo_full_name"]
    assert list(out["repo_full_name"]) == ["microsoft/edit", "microsoft/qlib"]


def test_load_org_audit_candidates_malformed_entries_produce_a_none_row_not_excluded():
    """Review finding, Story 13.4: a malformed entry must still produce a row (never a
    silent drop, matching classify_trending_candidates's own invariant) — its
    repo_full_name degrades to None rather than the row vanishing."""
    out = load_org_audit_candidates(
        [
            {"repo_full_name": "microsoft/edit"},  # valid
            {"description": "no repo_full_name key"},  # missing repo_full_name -> None
            "not-a-dict",  # non-dict entry -> None
            {"repo_full_name": 12345},  # non-string repo_full_name -> None
            {"repo_full_name": None},  # non-string (None) repo_full_name -> None
        ]
    )
    assert len(out) == 5
    values = list(out["repo_full_name"])
    assert values[0] == "microsoft/edit"
    assert all(v is None or (isinstance(v, float) and pd.isna(v)) for v in values[1:])


def test_load_org_audit_candidates_empty_list_degrades_to_empty_schema():
    out = load_org_audit_candidates([])
    assert out.empty
    assert list(out.columns) == ["repo_full_name"]


@pytest.mark.parametrize("bad_input", [None, "not-a-list", 42, {"repo_full_name": "x"}])
def test_load_org_audit_candidates_none_or_non_list_degrades_to_empty_never_raises(bad_input):
    out = load_org_audit_candidates(bad_input)
    assert out.empty
    assert list(out.columns) == ["repo_full_name"]


def test_load_org_audit_candidates_all_invalid_entries_still_produce_one_row_each():
    out = load_org_audit_candidates(["not-a-dict", {"no": "repo_full_name"}, {"repo_full_name": 1}])
    assert len(out) == 3
    values = list(out["repo_full_name"])
    assert all(v is None or (isinstance(v, float) and pd.isna(v)) for v in values)


def test_load_org_audit_candidates_dedups_case_insensitive_keeping_first_occurrence():
    out = load_org_audit_candidates(
        [
            {"repo_full_name": "microsoft/edit"},
            {"repo_full_name": "Microsoft/Edit"},
            {"repo_full_name": "microsoft/qlib"},
        ]
    )
    assert list(out["repo_full_name"]) == ["microsoft/edit", "microsoft/qlib"]


def test_load_org_audit_candidates_distinct_malformed_entries_are_not_deduped_together():
    """Two DIFFERENT malformed entries must not collapse into one row — only real,
    repeated repo_full_name values are deduped."""
    out = load_org_audit_candidates(["not-a-dict", {"no": "repo_full_name"}])
    assert len(out) == 2


def test_org_audit_candidates_reuse_drops_already_shipped_candidate():
    """FR-67's literal contract: classify_trending_candidates, run against an
    org_audit_candidates-shaped frame (repo_full_name only — no description/stars_total/
    etc. that trending_candidates normally carries), drops a candidate that has since
    shipped independently to conda-forge — tier="skip"/reason="already-on-conda-forge"
    — proving both FR-67's re-verification contract and that the classifier tolerates a
    narrower input schema than trending_candidates."""
    org_audit_candidates = load_org_audit_candidates([{"repo_full_name": "microsoft/promptflow"}])
    universe = _universe(["promptflow"])
    mapping = _mapping(["promptflow"])  # already shipped to conda-forge since the list was written
    intel = _intel(
        [
            {
                "pypi_name": "promptflow",
                "packaging_shape": "pure-python",
                "license_spdx": "MIT",
                "license_raw": "MIT",
                "notes": None,
            }
        ]
    )
    out = N.classify_trending_candidates(org_audit_candidates, universe, mapping, intel)
    assert len(out) == 1
    row = out.iloc[0]
    assert row["tier"] == "skip"
    assert row["reason"] == "already-on-conda-forge"


def test_org_audit_candidates_malformed_entry_reaches_classifier_as_a_visible_skip_row():
    """Review finding, Story 13.4: a malformed parameters.yml entry (e.g. a hand-edit
    typo) must not vanish — it reaches classify_trending_candidates as a None
    repo_full_name and comes back as a visible skip row, never silently dropped."""
    org_audit_candidates = load_org_audit_candidates([{"no": "repo_full_name"}])
    universe = _universe(["promptflow"])
    mapping = _mapping(["promptflow"])
    intel = _intel(
        [
            {
                "pypi_name": "promptflow",
                "packaging_shape": "pure-python",
                "license_spdx": "MIT",
                "license_raw": "MIT",
                "notes": None,
            }
        ]
    )
    out = N.classify_trending_candidates(org_audit_candidates, universe, mapping, intel)
    assert len(out) == 1
    row = out.iloc[0]
    assert row["tier"] == "skip"
    assert row["reason"] == "no-pypi-artifact"


# ---------------------------------------------------------------------------
# Story 21.4 — the three Tier-1 external-refresh triggers (mirror
# refresh_trending_candidates: params:ttls -> RefreshRequest, weekly default)
# ---------------------------------------------------------------------------

from pyforge.atlas.datasets.refresh import WEEKLY_SECONDS  # noqa: E402
from pyforge.atlas.pipelines.upstream_discovery.nodes import (  # noqa: E402
    refresh_anaconda_dist_2026x,
    refresh_aoss_premium_python,
    refresh_basilisk_packages,
)

# (trigger, ttls key, store) — the ttls key IS the catalog entry name (kedro-catalog-check
# rejects any ttls key that is not a catalog entry).
_TIER_1_TRIGGERS = [
    (refresh_anaconda_dist_2026x, "discovery_anaconda_dist_2026x_raw", "discovery_anaconda_dist_2026x_raw"),
    (refresh_basilisk_packages, "discovery_basilisk_packages_raw", "discovery_basilisk_packages_raw"),
    (refresh_aoss_premium_python, "discovery_aoss_premium_python_raw", "discovery_aoss_premium_python_raw"),
]


@pytest.mark.parametrize(("trigger", "ttl_key", "store"), _TIER_1_TRIGGERS)
def test_tier_1_trigger_reads_its_own_ttls_cadence(trigger, ttl_key, store):
    req = trigger({ttl_key: 12345})
    assert isinstance(req, RefreshRequest)
    assert req.store == store
    assert req.cadence_seconds == 12345
    assert req.force is False
    assert req.resource is None


@pytest.mark.parametrize(("trigger", "ttl_key", "store"), _TIER_1_TRIGGERS)
def test_tier_1_trigger_missing_or_non_numeric_falls_back_to_weekly(trigger, ttl_key, store):
    # weekly — NOT the daily default refresh_trending_candidates falls back to
    assert trigger({}).cadence_seconds == WEEKLY_SECONDS
    assert trigger(None).cadence_seconds == WEEKLY_SECONDS
    assert trigger({ttl_key: "nope"}).cadence_seconds == WEEKLY_SECONDS
    assert trigger({ttl_key: None}).cadence_seconds == WEEKLY_SECONDS
    assert trigger("not-a-dict").cadence_seconds == WEEKLY_SECONDS


def test_tier_1_triggers_read_the_shipped_parameters_yml_ttls():
    import pathlib

    import yaml

    params = yaml.safe_load(
        (pathlib.Path(__file__).resolve().parents[4] / "conf" / "base" / "parameters.yml").read_text(encoding="utf-8")
    )
    ttls = params["ttls"]
    for trigger, ttl_key, _store in _TIER_1_TRIGGERS:
        assert ttl_key in ttls, ttl_key
        assert trigger(ttls).cadence_seconds == ttls[ttl_key] == WEEKLY_SECONDS
    assert "discovery_aoss_free_python_raw" not in ttls  # tracked seed: config, no ttl


def test_coerce_cadence_default_is_still_daily_for_the_existing_caller():
    assert N._coerce_cadence({}, "trending_candidates") == DAILY_SECONDS
    assert N._coerce_cadence({}, "x", WEEKLY_SECONDS) == WEEKLY_SECONDS


# ---------------------------------------------------------------------------
# Story 21.5 — Tier 2 catalog sources (spec-21-5-tier-2-sources.md)
# ---------------------------------------------------------------------------

from pyforge.atlas.pipelines.upstream_discovery.nodes import (  # noqa: E402
    join_enterprise_conda_maintainers,
    refresh_about_maintainers,
)


def test_refresh_about_maintainers_reads_its_own_ttls_cadence():
    req = refresh_about_maintainers({"discovery_about_maintainers_raw": 12345})
    assert isinstance(req, RefreshRequest)
    assert req.store == "discovery_about_maintainers_raw"
    assert req.cadence_seconds == 12345
    assert req.force is False


def test_refresh_about_maintainers_missing_or_non_numeric_falls_back_to_weekly():
    # weekly — NOT the daily default refresh_trending_candidates falls back to
    assert refresh_about_maintainers({}).cadence_seconds == WEEKLY_SECONDS
    assert refresh_about_maintainers(None).cadence_seconds == WEEKLY_SECONDS
    assert refresh_about_maintainers({"discovery_about_maintainers_raw": "nope"}).cadence_seconds == WEEKLY_SECONDS


def test_refresh_about_maintainers_reads_the_shipped_parameters_yml_ttl():
    import pathlib

    import yaml

    params = yaml.safe_load(
        (pathlib.Path(__file__).resolve().parents[4] / "conf" / "base" / "parameters.yml").read_text(encoding="utf-8")
    )
    ttls = params["ttls"]
    assert "discovery_about_maintainers_raw" in ttls
    assert refresh_about_maintainers(ttls).cadence_seconds == ttls["discovery_about_maintainers_raw"] == WEEKLY_SECONDS


# -- join_enterprise_conda_maintainers ----------------------------------------

_ABOUT_COLS = ["feedstock_slug", "role", "source", "fetched_at"]
_ATTRIBUTION_COLS = ["conda_name", "feedstock_name"]
_ENTERPRISE_COLS = ["core_python_package_name", "role", "feedstock_slug", "repository_source"]


def _about_raw(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=_ABOUT_COLS)


def _attribution(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=_ATTRIBUTION_COLS)


def test_join_enterprise_conda_maintainers_matched_feedstock():
    about = _about_raw(
        [
            {
                "feedstock_slug": "conda-forge/numpy-feedstock",
                "role": "Maintainer",
                "source": "about_readme",
                "fetched_at": 1,
            }
        ]
    )
    attribution = _attribution([{"conda_name": "numpy", "feedstock_name": "numpy"}])
    out = join_enterprise_conda_maintainers(about, attribution)
    assert list(out.columns) == _ENTERPRISE_COLS
    assert len(out) == 1
    row = out.iloc[0]
    assert row["core_python_package_name"] == "numpy"
    assert row["role"] == "Maintainer"
    assert row["feedstock_slug"] == "conda-forge/numpy-feedstock"
    assert row["repository_source"] == "CDO-ENT-CONDA"


def test_join_enterprise_conda_maintainers_strips_prefix_and_suffix_before_matching():
    """feedstock_name in core_feedstock_attribution is a BARE name (e.g.
    "dbt-bigquery", per the core pipeline's _pick_feedstock) — the about-parsed
    feedstock_slug carries the full "conda-forge/<x>-feedstock" form and must be
    stripped before comparing."""
    about = _about_raw(
        [
            {
                "feedstock_slug": "conda-forge/dbt-bigquery-feedstock",
                "role": "Co-Maintainer",
                "source": "about_readme",
                "fetched_at": 1,
            }
        ]
    )
    attribution = _attribution([{"conda_name": "dbt-bigquery", "feedstock_name": "dbt-bigquery"}])
    out = join_enterprise_conda_maintainers(about, attribution)
    assert len(out) == 1
    assert out.iloc[0]["core_python_package_name"] == "dbt-bigquery"


def test_join_enterprise_conda_maintainers_unmatched_feedstock_is_dropped_never_fabricated():
    about = _about_raw(
        [
            {
                "feedstock_slug": "conda-forge/numpy-feedstock",
                "role": "Maintainer",
                "source": "about_readme",
                "fetched_at": 1,
            },
            {
                "feedstock_slug": "conda-forge/retired-pkg-feedstock",
                "role": "Maintainer",
                "source": "about_readme",
                "fetched_at": 1,
            },
        ]
    )
    attribution = _attribution([{"conda_name": "numpy", "feedstock_name": "numpy"}])
    out = join_enterprise_conda_maintainers(about, attribution)
    assert len(out) == 1
    assert list(out["core_python_package_name"]) == ["numpy"]


def test_join_enterprise_conda_maintainers_empty_attribution_degrades_to_empty_schema():
    about = _about_raw(
        [
            {
                "feedstock_slug": "conda-forge/numpy-feedstock",
                "role": "Maintainer",
                "source": "about_readme",
                "fetched_at": 1,
            }
        ]
    )
    out = join_enterprise_conda_maintainers(about, pd.DataFrame(columns=_ATTRIBUTION_COLS))
    assert out.empty
    assert list(out.columns) == _ENTERPRISE_COLS


def test_join_enterprise_conda_maintainers_none_attribution_never_raises():
    about = _about_raw(
        [
            {
                "feedstock_slug": "conda-forge/numpy-feedstock",
                "role": "Maintainer",
                "source": "about_readme",
                "fetched_at": 1,
            }
        ]
    )
    out = join_enterprise_conda_maintainers(about, None)
    assert out.empty
    assert list(out.columns) == _ENTERPRISE_COLS


def test_join_enterprise_conda_maintainers_empty_about_raw_degrades_to_empty_schema():
    out = join_enterprise_conda_maintainers(
        pd.DataFrame(columns=_ABOUT_COLS), _attribution([{"conda_name": "numpy", "feedstock_name": "numpy"}])
    )
    assert out.empty
    assert list(out.columns) == _ENTERPRISE_COLS


def test_join_enterprise_conda_maintainers_none_about_raw_never_raises():
    out = join_enterprise_conda_maintainers(None, _attribution([{"conda_name": "numpy", "feedstock_name": "numpy"}]))
    assert out.empty
    assert list(out.columns) == _ENTERPRISE_COLS


def test_join_enterprise_conda_maintainers_malformed_slug_never_raises():
    about = _about_raw(
        [
            {"feedstock_slug": None, "role": "Maintainer", "source": "about_readme", "fetched_at": 1},
            {"feedstock_slug": 12345, "role": "Maintainer", "source": "about_readme", "fetched_at": 1},
        ]
    )
    attribution = _attribution([{"conda_name": "numpy", "feedstock_name": "numpy"}])
    out = join_enterprise_conda_maintainers(about, attribution)
    assert out.empty


def test_strip_feedstock_slug_variants():
    assert N._strip_feedstock_slug("conda-forge/numpy-feedstock") == "numpy"
    assert N._strip_feedstock_slug("numpy") == "numpy"
    assert N._strip_feedstock_slug("conda-forge/dbt-bigquery-feedstock") == "dbt-bigquery"
    assert N._strip_feedstock_slug(None) is None
    assert N._strip_feedstock_slug("") is None
    assert N._strip_feedstock_slug(123) is None


# -- load_org_audit_candidates + discovery_curated_groups_seed ---------------


def test_load_org_audit_candidates_unions_curated_groups_seed():
    out = load_org_audit_candidates(
        [{"repo_full_name": "microsoft/edit"}],
        {"groups": [{"org": "example", "repos": ["exampleorg/repo-one", "exampleorg/repo-two"]}]},
    )
    assert list(out["repo_full_name"]) == ["microsoft/edit", "exampleorg/repo-one", "exampleorg/repo-two"]


def test_load_org_audit_candidates_dedups_across_both_sources_keeping_first_seen():
    out = load_org_audit_candidates(
        [{"repo_full_name": "microsoft/edit"}],
        {"groups": [{"org": "example", "repos": ["Microsoft/Edit", "exampleorg/repo-one"]}]},
    )
    assert list(out["repo_full_name"]) == ["microsoft/edit", "exampleorg/repo-one"]


def test_load_org_audit_candidates_missing_curated_groups_seed_contributes_zero_rows():
    out = load_org_audit_candidates([{"repo_full_name": "microsoft/edit"}], None)
    assert list(out["repo_full_name"]) == ["microsoft/edit"]


def test_load_org_audit_candidates_malformed_curated_groups_seed_never_raises():
    for malformed in (
        None,
        {},
        {"groups": "not-a-list"},
        {"groups": ["not-a-dict"]},
        {"groups": [{"org": "x", "repos": "not-a-list"}]},
        "not-a-dict",
        42,
    ):
        out = load_org_audit_candidates([{"repo_full_name": "microsoft/edit"}], malformed)
        assert list(out["repo_full_name"]) == ["microsoft/edit"]


def test_load_org_audit_candidates_curated_groups_seed_alone_with_no_org_audit_candidates():
    out = load_org_audit_candidates(None, {"groups": [{"org": "example", "repos": ["exampleorg/repo-one"]}]})
    assert list(out["repo_full_name"]) == ["exampleorg/repo-one"]


def test_load_org_audit_candidates_curated_groups_malformed_repo_entry_is_a_visible_none_row():
    out = load_org_audit_candidates(None, {"groups": [{"org": "example", "repos": [123, "exampleorg/repo-one"]}]})
    assert len(out) == 2
    values = list(out["repo_full_name"])
    assert values[1] == "exampleorg/repo-one"
    assert values[0] is None or (isinstance(values[0], float) and pd.isna(values[0]))


def test_load_org_audit_candidates_both_sources_empty_degrades_to_empty_schema():
    out = load_org_audit_candidates(None, None)
    assert out.empty
    assert list(out.columns) == ["repo_full_name"]


# ---------------------------------------------------------------------------
# Story 21.6 (CAP-3, Phase D identity join)
# ---------------------------------------------------------------------------

from pyforge.atlas.pipelines.upstream_discovery.nodes import (  # noqa: E402
    build_identity_export_parquet,
    build_identity_packages_primary,
    refresh_openteams_board,
    refresh_purl_associator_mappings,
    refresh_staged_recipes_prs,
)

_ID_TIER_1_TRIGGERS = [
    (refresh_purl_associator_mappings, "purl_associator_mappings_raw", "purl_associator_mappings_raw"),
    (refresh_openteams_board, "openteams_project_1_board_raw", "openteams_project_1_board_raw"),
    (refresh_staged_recipes_prs, "discovery_staged_recipes_prs_raw", "discovery_staged_recipes_prs_raw"),
]


@pytest.mark.parametrize(("trigger", "ttl_key", "store"), _ID_TIER_1_TRIGGERS)
def test_identity_join_trigger_reads_its_own_ttls_cadence(trigger, ttl_key, store):
    req = trigger({ttl_key: 12345})
    assert isinstance(req, RefreshRequest)
    assert req.store == store
    assert req.cadence_seconds == 12345
    assert req.force is False


@pytest.mark.parametrize(("trigger", "ttl_key", "store"), _ID_TIER_1_TRIGGERS)
def test_identity_join_trigger_missing_or_non_numeric_falls_back_to_weekly(trigger, ttl_key, store):
    assert trigger({}).cadence_seconds == WEEKLY_SECONDS
    assert trigger(None).cadence_seconds == WEEKLY_SECONDS
    assert trigger({ttl_key: "nope"}).cadence_seconds == WEEKLY_SECONDS


def test_identity_join_triggers_read_the_shipped_parameters_yml_ttls():
    import pathlib

    import yaml

    params = yaml.safe_load(
        (pathlib.Path(__file__).resolve().parents[4] / "conf" / "base" / "parameters.yml").read_text(encoding="utf-8")
    )
    ttls = params["ttls"]
    for trigger, ttl_key, _store in _ID_TIER_1_TRIGGERS:
        assert ttl_key in ttls, ttl_key
        assert trigger(ttls).cadence_seconds == ttls[ttl_key] == WEEKLY_SECONDS
    assert "discovery_local_recipes_raw" not in ttls  # plain filesystem read: no ttl


# -- build_identity_packages_primary / build_identity_export_parquet ---------
# One test per I/O & Edge-Case Matrix row (spec-21-6-upstream-discovery-identity-
# join-and-export-parquet.md), hand-derived by tracing the legacy script's
# lookup_assoc/from_assoc/from_inventory/from_board_only/attach_packaging_urls/
# overlay_live_local against the fixed fixture corpus below (identity-contract.md
# Parity test corpus).

_ASSOC_COLS = ["assoc_key", "purl", "type", "status", "alternative_purls", "cpes", "fetched_at"]
_BOARD_COLS = ["number", "title", "url", "state", "milestone", "fetched_at"]
_STAGED_COLS = ["number", "state", "merged_at", "url", "title", "file_paths", "fetched_at"]
_LOCAL_COLS = ["dir_name", "names", "url", "build_status"]
_ATTRIBUTION_COLS_ID = ["conda_name", "feedstock_name"]
_JFROG_NAMES_COLS = ["pypi_name", "conda_name", "is_internal"]
_CONDA_MAINTAINERS_COLS = ["core_python_package_name", "role", "feedstock_slug", "repository_source"]


def _assoc_raw(rows=()):
    return pd.DataFrame(list(rows), columns=_ASSOC_COLS)


def _board_raw(rows=()):
    return pd.DataFrame(list(rows), columns=_BOARD_COLS)


def _staged_raw(rows=()):
    return pd.DataFrame(list(rows), columns=_STAGED_COLS)


def _local_raw(rows=()):
    return pd.DataFrame(list(rows), columns=_LOCAL_COLS)


def _attribution_raw(rows=()):
    return pd.DataFrame(list(rows), columns=_ATTRIBUTION_COLS_ID)


def _jfrog_names(rows=()):
    return pd.DataFrame(list(rows), columns=_JFROG_NAMES_COLS)


def _conda_maintainers(rows=()):
    return pd.DataFrame(list(rows), columns=_CONDA_MAINTAINERS_COLS)


def _pypi_universe(names=()):
    return pd.DataFrame({"pypi_name": list(names)})


def _packages_enumerated(names=()):
    return pd.DataFrame({"conda_name": list(names)})


_EMPTY_ASSOC = _assoc_raw()
_EMPTY_BOARD = _board_raw()
_EMPTY_STAGED = _staged_raw()
_EMPTY_LOCAL = _local_raw()
_EMPTY_ATTRIBUTION = _attribution_raw()


def _build_primary(
    *,
    assoc=None,
    board=None,
    staged=None,
    local=None,
    attribution=None,
    jfrog_names=None,
    conda_maintainers=None,
    universe_names=(),
    enumerated_names=(),
):
    return build_identity_packages_primary(
        assoc if assoc is not None else _EMPTY_ASSOC,
        board if board is not None else _EMPTY_BOARD,
        staged if staged is not None else _EMPTY_STAGED,
        local if local is not None else _EMPTY_LOCAL,
        attribution if attribution is not None else _EMPTY_ATTRIBUTION,
        jfrog_names if jfrog_names is not None else _jfrog_names(),
        conda_maintainers if conda_maintainers is not None else _conda_maintainers(),
        _pypi_universe(universe_names),
        _packages_enumerated(enumerated_names),
    )


def _row_for(out, name):
    matches = out[out["Core_Python_Package_Name"] == name]
    assert len(matches) == 1, f"expected exactly one row for {name!r}, got {len(matches)}"
    return matches.iloc[0]


def test_identity_associator_hit():
    """Matrix row: Associator hit."""
    assoc = _assoc_raw(
        [
            {
                "assoc_key": "cool-pkg",
                "purl": "pkg:pypi/cool-pkg",
                "type": "pypi",
                "status": "confirmed",
                "alternative_purls": "pkg:github/someone/cool-pkg",
                "cpes": "cpe:2.3:a:someone:cool-pkg",
                "fetched_at": 1,
            }
        ]
    )
    out = _build_primary(
        assoc=assoc,
        conda_maintainers=_conda_maintainers(
            [
                {
                    "core_python_package_name": "cool-pkg",
                    "role": "Maintainer",
                    "feedstock_slug": "conda-forge/cool-pkg-feedstock",
                    "repository_source": "CDO-ENT-CONDA",
                }
            ]
        ),
        enumerated_names=["cool-pkg"],
    )
    row = _row_for(out, "cool-pkg")
    assert row["identity_source"] == "purl-associator"
    assert row["associator_key"] == "cool-pkg"
    assert row["primary_purl"] == "pkg:pypi/cool-pkg"
    assert row["primary_type"] == "pypi"
    assert row["alternative_purls"] == "pkg:github/someone/cool-pkg"
    assert row["cpes"] == "cpe:2.3:a:someone:cool-pkg"
    assert row["conda_purl"] == "pkg:conda/cool-pkg?channel=conda-forge"


def test_identity_associator_hit_via_alias_fallback():
    """lookup_assoc's -/./_ alias fallback."""
    assoc = _assoc_raw(
        [
            {
                "assoc_key": "cool.pkg",
                "purl": "pkg:pypi/cool-pkg",
                "type": "pypi",
                "status": "ok",
                "alternative_purls": "",
                "cpes": "",
                "fetched_at": 1,
            }
        ]
    )
    out = _build_primary(
        assoc=assoc,
        conda_maintainers=_conda_maintainers(
            [
                {
                    "core_python_package_name": "cool-pkg",
                    "role": "Maintainer",
                    "feedstock_slug": "x",
                    "repository_source": "CDO-ENT-CONDA",
                }
            ]
        ),
    )
    row = _row_for(out, "cool-pkg")
    assert row["identity_source"] == "purl-associator"
    assert row["associator_key"] == "cool.pkg"


def test_identity_inventory_derived_fallback_pypi_only():
    """Matrix row: Inventory-derived fallback (PyPI verified, no associator hit)."""
    out = _build_primary(
        conda_maintainers=_conda_maintainers(
            [
                {
                    "core_python_package_name": "newpkg",
                    "role": "Maintainer",
                    "feedstock_slug": "x",
                    "repository_source": "CDO-ENT-CONDA",
                }
            ]
        ),
        universe_names=["newpkg"],
    )
    row = _row_for(out, "newpkg")
    assert row["identity_source"] == "inventory"
    assert row["associator_status"] == "inventory-derived"
    assert row["primary_purl"] == "pkg:pypi/newpkg"
    assert row["primary_type"] == "pypi"


def test_identity_unmapped_none():
    """Matrix row: Unmapped (none) — no associator hit, no PyPI/conda verification."""
    out = _build_primary(
        conda_maintainers=_conda_maintainers(
            [
                {
                    "core_python_package_name": "ghostpkg",
                    "role": "Maintainer",
                    "feedstock_slug": "x",
                    "repository_source": "CDO-ENT-CONDA",
                }
            ]
        ),
    )
    row = _row_for(out, "ghostpkg")
    assert row["identity_source"] == "none"
    assert row["associator_status"] == "unmapped"
    assert row["primary_purl"] == ""
    # row is still emitted, never dropped


def test_identity_board_only_extra_appended():
    """Matrix row: Board-only extra."""
    board = _board_raw(
        [
            {
                "number": 1,
                "title": "[Conda-Forge Packaging] board-only-pkg",
                "url": "https://x/1",
                "state": "OPEN",
                "milestone": None,
                "fetched_at": 1,
            }
        ]
    )
    out = _build_primary(board=board)
    row = _row_for(out, "board-only-pkg")
    assert row["identity_source"] == "openteams-board"
    assert row["OpenTeams_Issue_URL"] == "https://x/1"


def test_identity_board_only_associator_rechecked():
    """from_board_only re-checks the associator for a board-only name too."""
    assoc = _assoc_raw(
        [
            {
                "assoc_key": "board-assoc-pkg",
                "purl": "pkg:pypi/board-assoc-pkg",
                "type": "pypi",
                "status": "ok",
                "alternative_purls": "",
                "cpes": "",
                "fetched_at": 1,
            }
        ]
    )
    board = _board_raw(
        [
            {
                "number": 2,
                "title": "[Conda-Forge Packaging] board-assoc-pkg",
                "url": "https://x/2",
                "state": "OPEN",
                "milestone": None,
                "fetched_at": 1,
            }
        ]
    )
    out = _build_primary(assoc=assoc, board=board)
    row = _row_for(out, "board-assoc-pkg")
    assert row["identity_source"] == "openteams-board"
    assert row["primary_purl"] == "pkg:pypi/board-assoc-pkg"


def test_identity_board_duplicate_name_keeps_first_issue_url():
    """A duplicate board name (same PEP-503 key) across multiple issues keeps
    the FIRST issue URL seen, never overwritten."""
    board = _board_raw(
        [
            {
                "number": 1,
                "title": "[Conda-Forge Packaging] dup-pkg",
                "url": "https://x/first",
                "state": "OPEN",
                "milestone": None,
                "fetched_at": 1,
            },
            {
                "number": 2,
                "title": "[Conda-Forge Packaging] dup-pkg",
                "url": "https://x/second",
                "state": "OPEN",
                "milestone": None,
                "fetched_at": 1,
            },
        ]
    )
    out = _build_primary(board=board)
    row = _row_for(out, "dup-pkg")
    assert row["OpenTeams_Issue_URL"] == "https://x/first"


def test_identity_conda_purl_only_when_conda_forge_verified():
    """Matrix row: conda_purl only when CondaForge_Verified."""
    out = _build_primary(
        conda_maintainers=_conda_maintainers(
            [
                {
                    "core_python_package_name": "verified-pkg",
                    "role": "Maintainer",
                    "feedstock_slug": "x",
                    "repository_source": "CDO-ENT-CONDA",
                },
                {
                    "core_python_package_name": "unverified-pkg",
                    "role": "Maintainer",
                    "feedstock_slug": "y",
                    "repository_source": "CDO-ENT-CONDA",
                },
            ]
        ),
        enumerated_names=["verified-pkg"],
    )
    assert _row_for(out, "verified-pkg")["conda_purl"] == "pkg:conda/verified-pkg?channel=conda-forge"
    assert _row_for(out, "unverified-pkg")["conda_purl"] == ""


def test_identity_overlay_urls_feedstock_metadata_staged_local():
    """Matrix row: Overlay URLs — feedstock + metadata + staged PR + local recipes."""
    attribution = _attribution_raw([{"conda_name": "overlay-pkg", "feedstock_name": "overlay-pkg"}])
    staged = _staged_raw(
        [
            {
                "number": 10,
                "state": "open",
                "merged_at": None,
                "url": "https://x/10",
                "title": "Add recipe for overlay-pkg",
                "file_paths": "",
                "fetched_at": 1,
            }
        ]
    )
    local = _local_raw(
        [
            {
                "dir_name": "overlay-pkg",
                "names": "overlay-pkg",
                "url": "https://github.com/rxm7706/local-recipes/tree/main/recipes/overlay-pkg",
                "build_status": "success",
            }
        ]
    )
    out = _build_primary(
        attribution=attribution,
        staged=staged,
        local=local,
        conda_maintainers=_conda_maintainers(
            [
                {
                    "core_python_package_name": "overlay-pkg",
                    "role": "Maintainer",
                    "feedstock_slug": "x",
                    "repository_source": "CDO-ENT-CONDA",
                }
            ]
        ),
    )
    row = _row_for(out, "overlay-pkg")
    assert row["Conda-Forge_FeedStock_URL"] == "https://github.com/conda-forge/overlay-pkg-feedstock"
    assert row["Conda-Forge_Metadata_URL"] == "https://conda-metadata-app.streamlit.app/?q=conda-forge/overlay-pkg"
    assert row["Staged_Recipes_PR_URL"] == "https://x/10"
    assert row["Local_Recipes_URL"] == "https://github.com/rxm7706/local-recipes/tree/main/recipes/overlay-pkg"
    assert row["Local_Build_Status"] == "success"


def test_identity_staged_pr_file_path_match_ranks_above_title_match():
    """load_staged_prs ranking: a file-path match on an open PR outranks a
    title-parse match on a different (also open) PR."""
    staged = _staged_raw(
        [
            {
                "number": 5,
                "state": "open",
                "merged_at": None,
                "url": "https://x/title-match",
                "title": "Add recipe for rank-pkg",
                "file_paths": "",
                "fetched_at": 1,
            },
            {
                "number": 6,
                "state": "open",
                "merged_at": None,
                "url": "https://x/file-match",
                "title": "unrelated title",
                "file_paths": "recipes/rank-pkg/recipe.yaml",
                "fetched_at": 1,
            },
        ]
    )
    out = _build_primary(
        staged=staged,
        conda_maintainers=_conda_maintainers(
            [
                {
                    "core_python_package_name": "rank-pkg",
                    "role": "Maintainer",
                    "feedstock_slug": "x",
                    "repository_source": "CDO-ENT-CONDA",
                }
            ]
        ),
    )
    assert _row_for(out, "rank-pkg")["Staged_Recipes_PR_URL"] == "https://x/file-match"


def test_identity_no_local_build_status_stays_blank_never_fabricated():
    """A malformed/absent CFE cfe-local-build-status stamp leaves
    Local_Build_Status blank, never fabricated."""
    local = _local_raw(
        [{"dir_name": "blank-status-pkg", "names": "blank-status-pkg", "url": "https://x", "build_status": ""}]
    )
    out = _build_primary(
        local=local,
        conda_maintainers=_conda_maintainers(
            [
                {
                    "core_python_package_name": "blank-status-pkg",
                    "role": "Maintainer",
                    "feedstock_slug": "x",
                    "repository_source": "CDO-ENT-CONDA",
                }
            ]
        ),
    )
    assert _row_for(out, "blank-status-pkg")["Local_Build_Status"] == ""


def test_identity_associator_fetch_fully_unavailable_falls_through_to_inventory():
    """Matrix row: PURL Associator fetch fails — every universe row falls
    through to from_inventory/from_board_only (an always-empty associator index
    behaves identically)."""
    out = _build_primary(
        assoc=_EMPTY_ASSOC,
        conda_maintainers=_conda_maintainers(
            [
                {
                    "core_python_package_name": "assoc-down-pkg",
                    "role": "Maintainer",
                    "feedstock_slug": "x",
                    "repository_source": "CDO-ENT-CONDA",
                }
            ]
        ),
        universe_names=["assoc-down-pkg"],
    )
    row = _row_for(out, "assoc-down-pkg")
    assert row["identity_source"] == "inventory"
    assert row["primary_purl"] == "pkg:pypi/assoc-down-pkg"


def test_identity_board_totally_unavailable_join_still_proceeds():
    """Matrix row: OpenTeams board fetch fails / paginates incompletely — the
    universe-row join still proceeds using inventory/associator data alone."""
    out = _build_primary(
        board=_EMPTY_BOARD,
        conda_maintainers=_conda_maintainers(
            [
                {
                    "core_python_package_name": "board-down-pkg",
                    "role": "Maintainer",
                    "feedstock_slug": "x",
                    "repository_source": "CDO-ENT-CONDA",
                }
            ]
        ),
    )
    row = _row_for(out, "board-down-pkg")
    assert row["OpenTeams_Issue_URL"] == ""
    assert row["identity_source"] in {"none", "inventory"}


def test_identity_export_parquet_full_gist_schema_shape():
    """Matrix row: identity_export_parquet shape — full GIST_SCHEMA column order,
    18 core columns populated, every ranking/JFROG column present as null."""
    primary = _build_primary(
        conda_maintainers=_conda_maintainers(
            [
                {
                    "core_python_package_name": "export-pkg",
                    "role": "Maintainer",
                    "feedstock_slug": "x",
                    "repository_source": "CDO-ENT-CONDA",
                }
            ]
        ),
        enumerated_names=["export-pkg"],
    )
    out = build_identity_export_parquet(primary)
    assert list(out.columns) == [
        "P",
        "Rank",
        "Score",
        "Package",
        "Work",
        "Platforms",
        "Apps",
        "Downloads",
        "Versions",
        "Vuln",
        "Core_Python_Package_Name",
        "OpenTeams_Title",
        "identity_source",
        "associator_key",
        "associator_status",
        "primary_purl",
        "primary_type",
        "alternative_purls",
        "cpes",
        "conda_purl",
        "source_repository_url",
        "OpenTeams_Issue_URL",
        "Conda-Forge_FeedStock_URL",
        "Conda-Forge_Metadata_URL",
        "Staged_Recipes_PR_URL",
        "Local_Recipes_URL",
        "Local_Build_Status",
        "Verification_Timestamp_UTC",
        "Priority_Bucket_Description",
        "Priority_Source",
        "Priority_Reason",
        "JFROG_risk_level",
        "JFROG_latest_vuln_count",
        "internal_component_count",
        "internal_lob_count",
    ]
    row = out.iloc[0]
    assert row["Package"] == "export-pkg"
    assert row["Core_Python_Package_Name"] == "export-pkg"
    for col in ("P", "Rank", "Score", "Work", "Platforms", "JFROG_risk_level"):
        assert pd.isna(row[col])


def test_identity_export_parquet_empty_primary_yields_empty_full_schema():
    """An empty identity_packages_primary yields an empty frame carrying the
    full schema, not a missing/absent file."""
    out = build_identity_export_parquet(pd.DataFrame(columns=[]))
    assert out.empty
    assert "P" in out.columns and "Core_Python_Package_Name" in out.columns
    out_none = build_identity_export_parquet(None)
    assert out_none.empty


def test_identity_join_never_raises_on_all_empty_inputs():
    out = build_identity_packages_primary(None, None, None, None, None, None, None, None, None)
    assert out.empty
    assert list(out.columns) == [
        "Core_Python_Package_Name",
        "OpenTeams_Title",
        "identity_source",
        "associator_key",
        "associator_status",
        "primary_purl",
        "primary_type",
        "alternative_purls",
        "cpes",
        "conda_purl",
        "source_repository_url",
        "OpenTeams_Issue_URL",
        "Conda-Forge_FeedStock_URL",
        "Conda-Forge_Metadata_URL",
        "Staged_Recipes_PR_URL",
        "Local_Recipes_URL",
        "Local_Build_Status",
        "Verification_Timestamp_UTC",
    ]
