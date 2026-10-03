#!/usr/bin/env python3
"""Story 27.1 / DW-FU-17-1 — metrics actuator snapshot over fixture catalog."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures/inventory_universe/catalog"
SCRIPT_PATH = Path(__file__).resolve().parent.parent / (
    "conda-forge-packaging-inventory-operations_metrics.py"
)
SNAPSHOT_MD = Path(__file__).resolve().parent / "fixtures/inventory_universe/expected_report.md.sha256"


def _load_metrics():
    spec = importlib.util.spec_from_file_location("cfpio_metrics", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(not FIXTURE_ROOT.is_dir(), reason="fixture catalog missing")
def test_metrics_actuator_matches_committed_md_snapshot(tmp_path: Path):
    metrics = _load_metrics()
    exports = metrics.load_atlas_exports(FIXTURE_ROOT)
    assert not exports.failed
    md_path = tmp_path / "report.md"
    metrics.write_markdown(md_path, exports.verified_rows, len(exports.queue_rows))
    digest = hashlib.sha256(md_path.read_bytes()).hexdigest()
    expected = SNAPSHOT_MD.read_text(encoding="utf-8").strip()
    assert digest == expected
