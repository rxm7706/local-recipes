"""``cli.upstream.run_upstream`` (Story 6.8, FR-58, AD-2) over the tracked upstream-register.json content.

Story 116.1 (spec-pyforge-marshal:CAP-305): the two ``test_upstream_cli.py`` tests that read the tracked tree moved
here, marked ``live_tree``; each fails, never skips, when the register file it reads is absent. The register text is
still round-tripped through ``test_upstream_cli.py``'s ``FakeFs`` (no filesystem write); every other upstream test
stays in ``test_upstream_cli.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_upstream_cli import _REGISTER_PATH, _ROOT, FakeFs, _args, _envelope_from

from pyforge.marshal.cli import upstream as upstream_cli

pytestmark = pytest.mark.live_tree

_TRACKED_REGISTER = (
    Path(__file__).resolve().parents[6]
    / "_bmad-output"
    / "projects"
    / "pyforge-marshal"
    / "planning-artifacts"
    / "upstream-register.json"
)


@pytest.fixture(autouse=True)
def _patch_repo_root(monkeypatch):
    monkeypatch.setattr(upstream_cli, "repo_root", lambda: _ROOT)


def _tracked_register_text() -> str:
    assert _TRACKED_REGISTER.is_file(), f"tracked register file not present in this checkout: {_TRACKED_REGISTER}"
    return _TRACKED_REGISTER.read_text(encoding="utf-8")


def test_the_real_register_content_round_trips(capsys):
    """Reads the ACTUAL tracked register content, round-tripped through a
    FakeFs (not a real filesystem read) -- confirms the committed file parses
    cleanly.

    Asserts the register CONTAINS its founding five and that the landed entry
    is still flagged, rather than pinning an exact set. The exact-set form was
    renamed from `..._five_entry_...` on 2026-08-09, when the seam review added
    three genuine bmad-loop gaps and the test failed for being right about a
    number that was never the contract. A register that must not grow is not a
    register; what must hold is that entries round-trip and a landed gap still
    reports MRS-UPSTREAM-002."""
    real_text = _tracked_register_text()
    fs = FakeFs(texts={_REGISTER_PATH: real_text})
    code = upstream_cli.run_upstream(_args(), fs=fs)
    envelope = _envelope_from(capsys)
    ids = {entry["id"] for entry in envelope["data"]["entries"]}
    assert {
        "idle-strand-detection",
        "per-story-model-tiering",
        "hardcoded-planning-artifacts-composition",
        "acp-evaluation",
        "non-posix-multiplexer-support",
    } <= ids, "the founding five must survive every later addition"
    assert len(envelope["data"]["flagged_for_removal"]) == 1
    assert envelope["data"]["flagged_for_removal"][0]["id"] == "non-posix-multiplexer-support"
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-UPSTREAM-002" in codes
    assert "MRS-UPSTREAM-001" not in codes
    assert code == 0


def test_the_real_register_content_includes_the_parallel_fan_out_entry(capsys):
    """Story 3.13 (FR-184): the 9th tracked register entry -- the gap is
    reused from ``test_the_real_register_content_round_trips``'s own
    register read + FakeFs round-trip shape, but asserted as a
    single subset check (no count-pinning, matching that test's own
    2026-08-09 renaming rationale) so a later 10th entry never breaks this
    one either."""
    real_text = _tracked_register_text()
    fs = FakeFs(texts={_REGISTER_PATH: real_text})
    code = upstream_cli.run_upstream(_args(), fs=fs)
    envelope = _envelope_from(capsys)
    entries_by_id = {entry["id"]: entry for entry in envelope["data"]["entries"]}
    assert "parallel-fan-out" in entries_by_id
    entry = entries_by_id["parallel-fan-out"]
    assert entry["compensating_fr"] == "FR-184"
    assert entry["upstream_status"] == "open"
    assert code == 0
