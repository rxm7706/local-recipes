"""Story 37.7 (CAP-69): the find-alternative candidates and the cf-graph about text they read.

Expected values are hand-derived from legacy ``find_alternative.py``'s rules (weights 3/2/4/1, the 0.10 floor, the
recency and download factors, the tokenizer) -- not imported, since that module lives in a separate tree,
``.claude/skills/conda-forge-expert/scripts/``. No network.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pyforge.atlas.datasets import core_sources as CS
from pyforge.atlas.pipelines.derived_artifacts.alternatives import (
    COLUMNS,
    jaccard,
    keyword_set,
    score_alternative_candidates,
    tokenize,
)

NOW = 1_800_000_000
DAY = 86_400


def _graph(rows: list[tuple[str, str, bool]], *, keywords: dict[str, list[str]] | None = None) -> pd.DataFrame:
    """One anchor row per (name, summary, archived); the feedstock is the name."""
    keywords = keywords or {}
    return pd.DataFrame(
        {
            "feedstock_name": [n for n, _, _ in rows],
            "conda_name": [n for n, _, _ in rows],
            "depends_on": [None] * len(rows),
            "feedstock_archived": [a for _, _, a in rows],
            "summary": [s for _, s, _ in rows],
            "keywords": [keywords.get(n, []) for n, _, _ in rows],
        }
    )


def _packages(names: list[str], **columns: list) -> pd.DataFrame:
    return pd.DataFrame({"conda_name": names, "latest_status": ["active"] * len(names), **columns})


def _score(graph, packages, dependencies=None, maintainers=None, attribution=None) -> pd.DataFrame:
    """Each graph package attributed to its own feedstock, unless ``attribution`` is given."""
    if attribution is None:
        attribution = graph[["conda_name", "feedstock_name"]]
    return score_alternative_candidates(graph, attribution, packages, dependencies, maintainers, now=NOW)


def _pairs(out: pd.DataFrame) -> dict[tuple[str, str], float]:
    return dict(
        zip(zip(out["archived_name"], out["candidate_name"], strict=True), out["similarity_score"], strict=True)
    )


# --------------------------------------------------------------------------- #
# legacy helpers
# --------------------------------------------------------------------------- #


def test_tokenize_lowercases_and_drops_stopwords_and_short_words() -> None:
    assert tokenize("A Python library to Parse YAML for ML, via C") == {"parse", "yaml"}  # "ML": two letters
    assert tokenize(None) == tokenize("") == frozenset()


def test_keywords_are_a_list_or_nothing() -> None:
    assert keyword_set(["YAML", "", "Parser"]) == {"yaml", "parser"}
    assert keyword_set("yaml") == keyword_set(None) == keyword_set(float("nan")) == frozenset()


def test_jaccard_is_zero_when_either_side_is_empty() -> None:
    assert jaccard(frozenset(), frozenset({"a"})) == 0.0
    assert jaccard(frozenset({"a", "b"}), frozenset({"b", "c"})) == pytest.approx(1 / 3)


# --------------------------------------------------------------------------- #
# the scorer
# --------------------------------------------------------------------------- #


def test_the_composite_follows_legacys_weights() -> None:
    graph = _graph(
        [("old", "parse yaml files", True), ("new", "parse yaml quickly", False)],
        keywords={"old": ["yaml", "config"], "new": ["yaml"]},
    )
    deps = pd.DataFrame({"conda_name": ["app", "app", "tool"], "depends_on": ["old", "new", "old"]})
    maints = pd.DataFrame({"conda_name": ["old", "new"], "maintainer": ["ann", "ann"]})

    out = _score(graph, _packages(["old", "new"], downloads_total=[1, 5]), deps, maints)

    # kw 1/2, terms {parse, yaml, files} vs {parse, yaml, quickly} 2/4, dependents {app, tool} vs {app} 1/2, maint 1
    expected = 3 * 0.5 + 2 * 0.5 + 4 * 0.5 + 1 * 1.0
    (row,) = out.to_dict("records")
    assert (row["archived_name"], row["candidate_name"], row["rank"]) == ("old", "new", 1)
    assert row["similarity_score"] == pytest.approx(round(expected, 3))
    assert (row["kw_score"], row["term_score"], row["dep_score"], row["maint_score"]) == (0.5, 0.5, 0.5, 1.0)
    assert row["downloads_total"] == 5 and row["summary"] == "parse yaml quickly"


def test_recency_and_downloads_scale_the_composite() -> None:
    graph = _graph([("old", "parse yaml", True), ("fresh", "parse yaml", False), ("aged", "parse yaml", False)])
    packages = _packages(
        ["old", "fresh", "aged"],
        latest_conda_upload=[None, None, NOW - 365 * DAY],
        downloads_total=[0, 0, 10],
    )

    pairs = _pairs(_score(graph, packages))

    # term Jaccard 1 -> score 2; no upload is recency 1.0, no downloads halves it
    assert pairs[("old", "fresh")] == pytest.approx(2 * 1.0 * 0.5)
    # a year old: recency 1 - 365/1825 = 0.8, factor 0.5 + 0.4 = 0.9; with downloads
    assert pairs[("old", "aged")] == pytest.approx(round(2 * 0.9, 3))


def test_a_candidate_needs_a_keyword_or_summary_overlap() -> None:
    graph = _graph([("old", "parse yaml", True), ("dep-only", "render html", False)])
    deps = pd.DataFrame({"conda_name": ["app", "app"], "depends_on": ["old", "dep-only"]})

    assert _score(graph, _packages(["old", "dep-only"]), deps).empty


def test_a_score_under_the_floor_is_dropped() -> None:
    words = " ".join(f"word{i:02d}" for i in range(30))
    graph = _graph([("old", words, True), ("thin", "word00 other", False), ("near", "word00 word01 word02", False)])

    pairs = _pairs(_score(graph, _packages(["old", "thin", "near"], downloads_total=[1, 1, 1])))

    assert ("old", "thin") not in pairs  # 2 * 1/31 < 0.10
    assert pairs[("old", "near")] == pytest.approx(round(2 * 3 / 30, 3))


@pytest.mark.parametrize(
    ("graph_archived", "row_archived", "scored"),
    [(True, 0, True), (False, 1, True), (False, 0, False)],
    ids=["cf-graph-flag", "semantic-packages-flag", "neither"],
)
def test_the_archived_set_reads_both_sources(graph_archived, row_archived, scored) -> None:
    graph = _graph([("old", "parse yaml", graph_archived), ("new", "parse yaml", False)])
    packages = _packages(["old", "new"], feedstock_archived=[row_archived, 0])

    out = _score(graph, packages)

    assert ("old" in set(out["archived_name"])) is scored
    assert "new" not in set(out["archived_name"])


def test_only_an_active_unarchived_other_package_is_a_candidate() -> None:
    graph = _graph(
        [
            ("old", "parse yaml", True),
            ("gone", "parse yaml", True),
            ("inactive", "parse yaml", False),
            ("new", "parse yaml", False),
        ]
    )
    packages = pd.DataFrame(
        {
            "conda_name": ["old", "gone", "inactive", "new"],
            "latest_status": ["active", "active", "inactive", "active"],
        }
    )

    out = _score(graph, packages)

    assert set(out["candidate_name"]) == {"new"}
    assert set(out["archived_name"]) == {"old", "gone"}


def test_a_package_off_the_channel_is_never_scored() -> None:
    graph = _graph([("old", "parse yaml", True), ("new", "parse yaml", False), ("off", "parse yaml", True)])

    assert set(_score(graph, _packages(["old", "new"]))["archived_name"]) == {"old"}


def test_the_top_ten_rank_by_composite_then_name() -> None:
    names = [f"cand{i:02d}" for i in range(12)]
    graph = _graph([("old", "parse yaml", True), *((n, "parse yaml", False) for n in names)])
    downloads = [1] * 13
    downloads[12] = 0  # cand11 has no downloads: half the composite, last

    out = _score(graph, _packages(["old", *names], downloads_total=downloads))

    assert list(out["candidate_name"]) == names[:10]
    assert list(out["rank"]) == list(range(1, 11))


def test_the_summary_and_keywords_reach_each_attributed_output() -> None:
    graph = _graph([("old-feedstock", "parse yaml", True), ("new-feedstock", "parse yaml", False)])
    attribution = pd.DataFrame({"conda_name": ["old", "new"], "feedstock_name": ["old-feedstock", "new-feedstock"]})

    out = _score(graph, _packages(["old", "new"]), attribution=attribution)

    assert _pairs(out) == {("old", "new"): pytest.approx(1.0)}


def test_an_unattributed_package_gets_no_text_and_no_flag() -> None:
    """Legacy's Phase E and E.5 reach a package only through its feedstock attribution (Phase B.5); a package
    attribution does not list gets neither, so it is never scored and never a candidate."""
    graph = _graph(
        [
            ("old", "parse yaml", True),
            ("new", "parse yaml", False),
            ("stray", "parse yaml", True),
            ("loose", "parse yaml", False),
        ]
    )
    attribution = pd.DataFrame({"conda_name": ["old", "new"], "feedstock_name": ["old", "new"]})

    out = _score(graph, _packages(["old", "new", "stray", "loose"]), attribution=attribution)

    assert _pairs(out) == {("old", "new"): pytest.approx(1.0)}


def test_a_keyword_overlap_alone_makes_a_candidate() -> None:
    graph = _graph(
        [("old", "parse yaml", True), ("kw", "render html", False)], keywords={"old": ["markup"], "kw": ["markup"]}
    )

    (row,) = _score(graph, _packages(["old", "kw"], downloads_total=[1, 1])).to_dict("records")

    assert (row["candidate_name"], row["kw_score"], row["term_score"], row["similarity_score"]) == ("kw", 1.0, 0.0, 3.0)


def test_the_floor_reads_the_score_not_the_composite() -> None:
    words = " ".join(f"word{i:02d}" for i in range(40))
    # term Jaccard 3/40: score 0.15, composite 0.075 with no downloads, kept; 2/40: score exactly 0.10, kept
    graph = _graph([("old", words, True), ("thin", "word00 word01 word02", False), ("edge", "word00 word01", False)])

    pairs = _pairs(_score(graph, _packages(["old", "thin", "edge"], downloads_total=[1, 0, 1])))

    assert pairs[("old", "thin")] == pytest.approx(0.075)
    assert pairs[("old", "edge")] == pytest.approx(0.1)


@pytest.mark.parametrize(
    ("upload", "factor"),
    [
        (0, 1.0),  # legacy reads 0 as no upload time
        (NOW - 6 * 365 * DAY, 0.5),  # past five years: recency 0, not negative
        (NOW + 10 * DAY, 1.0 + 0.5 * 10 / 1825),  # a future upload is not clamped above 1, as in legacy
    ],
    ids=["zero", "older-than-five-years", "future"],
)
def test_recency_follows_legacys_edges(upload, factor) -> None:
    graph = _graph([("old", "parse yaml", True), ("new", "parse yaml", False)])

    pairs = _pairs(_score(graph, _packages(["old", "new"], latest_conda_upload=[None, upload], downloads_total=[1, 1])))

    assert pairs[("old", "new")] == pytest.approx(round(2 * factor, 3))


def test_recency_reads_fractional_days_over_a_1825_day_span() -> None:
    graph = _graph(
        [("old", "parse yaml files", True), ("new", "parse yaml quickly", False)],
        keywords={"old": ["yaml", "config"], "new": ["yaml"]},
    )
    deps = pd.DataFrame({"conda_name": ["app", "app", "tool"], "depends_on": ["old", "new", "old"]})
    maints = pd.DataFrame({"conda_name": ["old", "new"], "maintainer": ["ann", "ann"]})
    upload = NOW - int(1000.5 * DAY)

    out = _score(
        graph, _packages(["old", "new"], latest_conda_upload=[None, upload], downloads_total=[1, 1]), deps, maints
    )

    # score 5.5; 1000.5 days: 3.992 (whole days would give 3.993, a 1826.25-day span 3.994)
    assert out["similarity_score"].tolist() == [round(5.5 * (0.5 + 0.5 * (1 - 1000.5 / 1825)), 3)] == [3.992]


def test_a_missing_status_is_not_active() -> None:
    graph = _graph([("old", "parse yaml", True), ("none", "parse yaml", False), ("new", "parse yaml", False)])
    packages = pd.DataFrame({"conda_name": ["old", "none", "new"], "latest_status": ["active", None, "active"]})

    assert set(_score(graph, packages)["candidate_name"]) == {"new"}


def test_ranking_reads_the_rounded_composite() -> None:
    graph = _graph([("old", "parse yaml", True), ("b-cand", "parse yaml", False), ("a-cand", "parse yaml", False)])
    # a-cand is half a day old: composite 1.99973, which rounds to b-cand's 2.0, so the tie falls to the name
    packages = _packages(
        ["old", "b-cand", "a-cand"], latest_conda_upload=[None, None, NOW - DAY // 2], downloads_total=[1, 1, 1]
    )

    out = _score(graph, packages)

    assert out["candidate_name"].tolist() == ["a-cand", "b-cand"] and out["similarity_score"].tolist() == [2.0, 2.0]


def test_the_component_scores_are_rounded() -> None:
    graph = _graph([("old", "parse yaml files", True), ("new", "parse yaml", False)])

    (row,) = _score(graph, _packages(["old", "new"], downloads_total=[1, 1])).to_dict("records")

    assert row["term_score"] == 0.667 and row["similarity_score"] == 1.333


def test_a_kept_graph_without_about_text_gives_no_rows() -> None:
    graph = _graph([("old", "parse yaml", True), ("new", "parse yaml", False)]).drop(columns=["summary", "keywords"])

    out = _score(graph, _packages(["old", "new"]))

    assert out.empty and list(out.columns) == COLUMNS


def test_nothing_in_gives_a_typed_empty_frame(tmp_path: Path) -> None:
    out = score_alternative_candidates(None, None, None, None, None, now=NOW)

    assert out.empty and list(out.columns) == COLUMNS
    out.to_parquet(tmp_path / "e.parquet", index=False)
    back = pd.read_parquet(tmp_path / "e.parquet")
    assert str(back["latest_upload_age_days"].dtype) == "Int64" and str(back["similarity_score"].dtype) == "float64"


def test_the_stage_inputs_pass_through() -> None:
    graph = _graph([("old", "parse yaml", True), ("new", "parse yaml", False)])
    packages = _packages(
        ["old", "new"], latest_upload_age_days=[None, 12], releases_30d=[None, 2], total_versions=[1, 9]
    )

    (row,) = _score(graph, packages).to_dict("records")

    assert (row["latest_upload_age_days"], row["releases_30d"], row["total_versions"]) == (12, 2, 9)


# --------------------------------------------------------------------------- #
# the cf-graph about text
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("about", "summary", "keywords"),
    [
        ({"summary": "Parse YAML", "keywords": ["yaml", "", "parser"]}, "Parse YAML", ["yaml", "parser"]),
        ({"summary": ["one", "", "two"], "keywords": "yaml"}, "one, two", []),
        ({"summary": 3.14}, "3.14", []),  # legacy's _str stringifies any other value
        ({}, None, []),
    ],
    ids=["text", "list-summary-string-keywords", "number-summary", "none"],
)
def test_the_frame_reads_legacy_phase_es_about_text(about, summary, keywords) -> None:
    payload = {
        "name": "foo",
        "meta_yaml": {"about": about, "requirements": {"run": ["python"]}},
    }

    frame = CS._cf_graph_frame([("foo", payload)], {}, {}, {})

    anchor = frame[(frame["conda_name"] == "foo") & frame["depends_on"].isna()].iloc[0]
    edge = frame[frame["depends_on"] == "python"].iloc[0]
    assert anchor["keywords"] == keywords
    assert anchor["summary"] == summary if summary else pd.isna(anchor["summary"])  # an all-null column is NaN
    assert pd.isna(edge["summary"]) and not isinstance(edge["keywords"], list)


def test_a_kept_graph_reads_its_keywords_back_as_lists(tmp_path: Path) -> None:
    payload = {"name": "foo", "meta_yaml": {"about": {"keywords": ["yaml"]}, "requirements": {"run": ["python"]}}}
    path = tmp_path / "last_good.parquet"
    CS._cf_graph_frame([("foo", payload)], {}, {}, {}).to_parquet(path, index=False)

    kept = CS._read_last_good(path)

    assert kept is not None
    anchor, edge = kept[kept["depends_on"].isna()].iloc[0], kept[kept["depends_on"] == "python"].iloc[0]
    # a list, as the fresh frame holds it -- Parquet hands back a numpy array
    assert isinstance(anchor["keywords"], list) and anchor["keywords"] == ["yaml"] and edge["keywords"] is None
    fields = CS.package_recipe_fields(kept, None, CS.ABOUT_FIELDS)
    assert fields.to_dict("records") == [{"conda_name": "foo", "summary": None, "keywords": ["yaml"]}]
