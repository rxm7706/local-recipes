"""Story 20.3: named-pipeline derivation of the composed dashboard stores (CAP-6).

Mirrors the ``test_query_plane_parquet_cache.py`` precedent (Story 34.2, FR-47): proves
the new pipeline auto-registers, its ``kedro run`` writes the declared catalog Parquet,
and -- the story-specific honesty proof -- that the composed store lets the BSL metrics
whose inputs are ``deferred-input-not-in-migrated-store`` (``metrics.METRIC_PROVENANCE``)
degrade to NULL / "unknown" through the REAL query seam, never crash and never fabricate.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from kedro.framework.project import configure_project
from kedro.io import DataCatalog, MemoryDataset
from kedro.runner import SequentialRunner
from kedro_datasets.pandas import ParquetDataset

from pyforge.atlas.pipeline_registry import register_pipelines
from pyforge.atlas.pipelines.semantic_packages import create_pipeline
from pyforge.atlas.pipelines.semantic_packages.nodes import compose_semantic_packages
from pyforge.atlas.semantic import models

ATLAS_ROOT = Path(__file__).resolve().parents[2]
CATALOG_YML = ATLAS_ROOT / "conf" / "base" / "catalog.yml"
PIPELINE_NAME = "semantic_packages"


def _core_shaped_frames() -> dict[str, pd.DataFrame]:
    """Small frames shaped exactly like the sealed `core` / `vcs_health` pipelines'
    real catalog outputs (see pipelines/core/nodes.py, pipelines/vcs_health/nodes.py)."""
    return {
        "core_packages_enumerated": pd.DataFrame({"conda_name": ["a", "b", "c"]}),
        "core_latest_status": pd.DataFrame(
            {"conda_name": ["a", "b", "c"], "latest_status": ["active", "active", "inactive"]}
        ),
        "core_feedstock_attribution": pd.DataFrame(
            {"conda_name": ["a", "b", "c"], "feedstock_name": ["alpha", "beta", "beta"]}
        ),
        "vcs_archived_feedstocks": pd.DataFrame({"feedstock_name": ["beta"], "archived": pd.array([1], dtype="Int64")}),
        "core_downloads": pd.DataFrame(
            {
                "conda_name": ["a", "b", "c"],
                "downloads_total": pd.array([10, 20, 30], dtype="Int64"),
                "downloads_30d": pd.array([1, 2, 3], dtype="Int64"),
            }
        ),
    }


def test_named_pipeline_is_registered() -> None:
    configure_project("pyforge.atlas")
    pipelines = register_pipelines()
    assert PIPELINE_NAME in pipelines
    assert PIPELINE_NAME != "__default__"


def test_catalog_declares_the_composed_dataset() -> None:
    text = CATALOG_YML.read_text(encoding="utf-8")
    assert "semantic_packages:" in text
    assert "data/primary/semantic_packages/semantic_packages.parquet" in text


def test_kedro_run_composes_and_writes_the_parquet(tmp_path: Path) -> None:
    out_path = tmp_path / "semantic_packages.parquet"
    frames = _core_shaped_frames()
    catalog_entries: dict[str, object] = {name: MemoryDataset(df) for name, df in frames.items()}
    catalog_entries["semantic_packages"] = ParquetDataset(filepath=str(out_path))
    catalog = DataCatalog(catalog_entries)

    SequentialRunner().run(create_pipeline(), catalog)

    assert out_path.is_file()
    composed = pd.read_parquet(out_path)
    assert sorted(composed["conda_name"]) == ["a", "b", "c"]


def test_missing_required_upstream_fails_loud_naming_the_dataset(tmp_path: Path) -> None:
    """MISSING_UPSTREAM (I/O matrix): if a required sealed-seven output has not been
    materialized (so its catalog entry can't resolve), `kedro run` must fail loud
    naming the missing input -- never silently write a fabricated composed row."""
    frames = _core_shaped_frames()
    del frames["core_packages_enumerated"]  # the population input, deliberately absent
    catalog_entries: dict[str, object] = {name: MemoryDataset(df) for name, df in frames.items()}
    catalog_entries["semantic_packages"] = ParquetDataset(filepath=str(tmp_path / "semantic_packages.parquet"))
    catalog = DataCatalog(catalog_entries)

    with pytest.raises(ValueError, match="core_packages_enumerated"):
        SequentialRunner().run(create_pipeline(), catalog)

    assert not (tmp_path / "semantic_packages.parquet").exists()


def test_pipeline_reads_only_sealed_seven_output_names_never_a_raw_source() -> None:
    """DOWNSTREAM ONLY: every declared input is an existing `core`/`vcs_health` catalog
    OUTPUT name (never a `_raw` source this pipeline would have to fetch itself)."""
    pipeline = create_pipeline()
    assert pipeline.inputs() == {
        "core_packages_enumerated",
        "core_latest_status",
        "core_feedstock_attribution",
        "vcs_archived_feedstocks",
        "core_downloads",
    }
    assert pipeline.outputs() == {"semantic_packages"}
    assert not any(name.endswith("_raw") for name in pipeline.inputs())


def test_composed_store_lets_the_deferred_bsl_metrics_degrade_honestly_not_crash(
    tmp_path: Path,
) -> None:
    """The spec's Block-If honesty constraint, proven END TO END through the real BSL
    seam: a query over the composed store's ``staleness_age_days`` / ``adoption_stage``
    (the two metrics whose inputs are ALL `deferred-input-not-in-migrated-store`) must
    not crash and must degrade to NULL / "unknown" -- while ``is_actionable`` /
    ``downloads_total`` (fed by real joined columns) render the actual data. If the
    node ever dropped a deferred column instead of declaring it NULL, this query would
    raise (a missing-column AttributeError, not caught by the loaders' TypeError-only
    degrade) instead of degrading -- so this test would catch that regression.
    """
    frames = _core_shaped_frames()
    composed = compose_semantic_packages(
        frames["core_packages_enumerated"],
        frames["core_latest_status"],
        frames["core_feedstock_attribution"],
        frames["vcs_archived_feedstocks"],
        frames["core_downloads"],
    )
    path = tmp_path / "semantic_packages.parquet"
    composed.to_parquet(path)

    table = models.duckdb_table_from_parquet(str(path))
    model = models.build_packages_model(table, now_unix=1_700_000_000)
    result = model.query(
        dimensions=["conda_name", "is_actionable", "staleness_age_days", "adoption_stage"],
        measures=["downloads_total"],
    ).execute()

    assert set(result["conda_name"]) == {"a", "b", "c"}
    # deferred inputs -> honest NULL / "unknown", never a fabricated value.
    assert result["staleness_age_days"].isna().all()
    assert (result["adoption_stage"] == "unknown").all()

    by_name = dict(zip(result["conda_name"], result.to_dict("records")))
    assert bool(by_name["a"]["is_actionable"]) is True  # active, feedstock alpha not archived
    assert bool(by_name["b"]["is_actionable"]) is False  # active, but feedstock beta IS archived
    assert bool(by_name["c"]["is_actionable"]) is False  # latest_status inactive
    assert int(by_name["a"]["downloads_total"]) == 10
    assert int(by_name["b"]["downloads_total"]) == 20
