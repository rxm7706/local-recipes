"""Recapture-tooling tests (Story B4, AC-5 / DW-B1-1 part a).

B4 ships the capture tool; the actual recapture from a real legacy run happens at
the attended event. These tests exercise the tool against a SYNTHETIC capture
source (no real DB), verify it writes harness-compatible fixtures stamped with the
credentialed-capture provenance, and confirm the B1/B2 shape-only seeds stay
flagged (recapture pending).
"""

from __future__ import annotations

import json
from pathlib import Path

from .capture_fixtures import (
    CREDENTIALED_PROVENANCE_PREFIX,
    capture_legacy_fixtures,
    is_credentialed_capture,
    is_shape_only_seed,
)

_FIXTURES_DIR = Path(__file__).parent / "fixtures"


class _SyntheticCaptureSource:
    """Stands in for the credentialed cf_atlas.db capture at the event — no DB."""

    def node_names(self):
        return ["attribute_feedstocks"]

    def capture(self, node: str) -> dict:
        return {
            "phase": "B.5",
            "inputs": {
                "core_feedstock_outputs_raw": [
                    {"conda_name": "numpy", "feedstocks": ["numpy"]},
                ]
            },
            "expected": {
                "core_feedstock_attribution": [
                    {"conda_name": "numpy", "feedstock_name": "numpy"},
                ]
            },
        }


def test_capture_writes_harness_compatible_fixture(tmp_path):
    written = capture_legacy_fixtures(
        _SyntheticCaptureSource(), tmp_path, captured_at="2026-07-17"
    )
    assert len(written) == 1
    data = json.loads(written[0].read_text())
    # harness fixture shape
    assert data["node"] == "attribute_feedstocks"
    assert data["phase"] == "B.5"
    assert "inputs" in data and "expected" in data
    # stamped credentialed-capture, NOT shape-only
    assert data["provenance"] == f"{CREDENTIALED_PROVENANCE_PREFIX}-2026-07-17"
    assert is_credentialed_capture(written[0])
    assert not is_shape_only_seed(written[0])


def test_capture_defaults_to_source_node_list(tmp_path):
    written = capture_legacy_fixtures(_SyntheticCaptureSource(), tmp_path)
    assert [p.stem for p in written] == ["attribute_feedstocks"]


def test_b2_b3_seeds_still_flagged_shape_only():
    """Until the attended recapture runs, the pypi/vulnerability seeds MUST stay
    flagged shape-only (a green parity-diff is not legacy parity)."""
    pypi_and_vuln = sorted(
        (_FIXTURES_DIR / "pypi_intelligence").glob("*.json")
    ) + sorted((_FIXTURES_DIR / "vulnerability").glob("*.json"))
    assert pypi_and_vuln, "expected shape-only seed fixtures to exist"
    for f in pypi_and_vuln:
        assert is_shape_only_seed(f), f"{f.name} lost its shape-only-seed flag"


def test_recaptured_fixture_is_distinguishable_from_seed(tmp_path):
    """The provenance marker lets the harness tell recaptured fixtures from
    still-pending seeds — the mechanism DW-B1-1 part a needs at the event."""
    written = capture_legacy_fixtures(_SyntheticCaptureSource(), tmp_path)
    seed = next((_FIXTURES_DIR / "pypi_intelligence").glob("*.json"))
    assert is_credentialed_capture(written[0])
    assert is_shape_only_seed(seed)
    assert not is_credentialed_capture(seed)
