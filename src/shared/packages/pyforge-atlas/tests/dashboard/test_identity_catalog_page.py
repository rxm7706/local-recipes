"""Story 22.2 — identity-catalog Vizro page parity with write_canvas output."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

from pyforge.atlas.dashboard import data as dash_data
from pyforge.atlas.semantic import models
from pyforge.atlas.semantic.query_helpers import bsl_query

REPO_ROOT = Path(__file__).resolve().parents[6]
SCRIPTS_DIR = REPO_ROOT / "scripts"

_IDENTITY_CATALOG_DIMENSIONS = [
    "P",
    "Rank",
    "Score",
    "Package",
    "Work",
    "Core_Python_Package_Name",
    "Platforms",
    "Apps",
    "Downloads",
    "Versions",
    "Vuln",
]


def _load_priority_module():
    """Import priority.py by path (mirrors tests/packaging/test_openteams_handoffs.py)."""
    script_path = SCRIPTS_DIR / "conda-forge-packaging-inventory-operations_priority.py"
    assert script_path.is_file(), f"script not found: {script_path}"
    module_name = script_path.stem.replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _decode_data_blob(text: str, prefix: str) -> dict:
    assert text.startswith(prefix)
    remainder = text[len(prefix) :]
    data, _end = json.JSONDecoder().raw_decode(remainder)
    return data


def _hand_built_fixture() -> tuple[list[dict], dict[str, int]]:
    records = [
        {
            "name": "alpha-pkg",
            "bucket": "P1",
            "work": "Already tracked",
            "rank": 1,
            "score100": 95,
            "plat": 3,
            "apps": 1,
            "ic": 2,
            "lob": 0,
            "dl": 100,
            "ver": 5,
            "vuln": 0,
            "src": "manual",
            "why": "high impact",
            "priority_desc": "Critical",
        },
        {
            "name": "beta-pkg",
            "bucket": "P2",
            "work": "Needs PR",
            "rank": 2,
            "score100": 80,
            "plat": 1,
            "apps": 0,
            "ic": 0,
            "lob": 1,
            "dl": 50,
            "ver": 3,
            "vuln": 1,
            "src": "auto",
            "why": "moderate impact",
            "priority_desc": "High",
        },
        {
            "name": "gamma-pkg",
            "bucket": "P2",
            "work": "Needs PR",
            "rank": 3,
            "score100": 70,
            "plat": 2,
            "apps": 2,
            "ic": 1,
            "lob": 0,
            "dl": 25,
            "ver": 2,
            "vuln": 0,
            "src": "auto",
            "why": "lower impact",
            "priority_desc": "High",
        },
    ]
    counts = {"P1": 1, "P2": 2}
    return records, counts


def _records_to_ranked_export_df(records: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "P": [r["bucket"] for r in records],
            "Rank": [r["rank"] for r in records],
            "Score": [r["score100"] for r in records],
            "Package": [r["name"] for r in records],
            "Work": [r["work"] for r in records],
            "Core_Python_Package_Name": [r["name"] for r in records],
            "Platforms": [r["plat"] for r in records],
            "Apps": [r["apps"] for r in records],
            "Downloads": [r["dl"] for r in records],
            "Versions": [r["ver"] for r in records],
            "Vuln": [r["vuln"] for r in records],
        }
    )


def test_identity_catalog_parity_with_write_canvas(tmp_path, write_parquet):
    """Same fixture fed to write_canvas and load_identity_catalog must agree."""
    priority = _load_priority_module()
    records, counts = _hand_built_fixture()

    canvas_path = tmp_path / "catalog.canvas.tsx"
    priority.write_canvas(canvas_path, records, counts, "identity-fixture")
    canvas_text = canvas_path.read_text(encoding="utf-8")
    decoded = _decode_data_blob(canvas_text, priority._CANVAS_PREFIX)

    parquet_path = write_parquet(_records_to_ranked_export_df(records), "identity_complete_export")
    loader_df = dash_data.load_identity_catalog(parquet_path)

    assert len(loader_df) == len(decoded["rows"])

    canvas_by_bucket: dict[str, list] = {}
    for row in decoded["rows"]:
        canvas_by_bucket.setdefault(row[1], []).append(row)

    for bucket, canvas_rows in canvas_by_bucket.items():
        canvas_row = canvas_rows[0]
        loader_row = loader_df.loc[loader_df["P"] == bucket].iloc[0]
        assert loader_row["P"] == canvas_row[1]
        assert loader_row["Work"] == canvas_row[13]
        assert loader_row["Core_Python_Package_Name"] == canvas_row[0]


def test_identity_catalog_page_is_bsl_driven(write_parquet):
    """Loader output equals an independent build_identity_catalog_model query (AD-8)."""
    records, _counts = _hand_built_fixture()
    parquet_path = write_parquet(_records_to_ranked_export_df(records), "identity_complete_export")

    got = dash_data.load_identity_catalog(parquet_path)
    table = models.duckdb_table_from_parquet(parquet_path)
    expected = bsl_query(
        models.build_identity_catalog_model(table),
        dimensions=_IDENTITY_CATALOG_DIMENSIONS,
    )
    pd.testing.assert_frame_equal(
        got.sort_values(["P", "Rank"]).reset_index(drop=True),
        expected.sort_values(["P", "Rank"]).reset_index(drop=True),
    )
