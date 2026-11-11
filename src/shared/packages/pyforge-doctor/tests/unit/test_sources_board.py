"""Unit tests for ``pyforge.doctor.sources.board`` helpers and invariants
(Story 21.1 — ``DEFERRED_SPECS`` live-status reconciliation). The checks
against this repository's own Specs run in ``test_live_sources_board.py``."""

from __future__ import annotations

from pyforge.doctor.sources import board

# Doctor Story 58.1 (spec-pyforge-doctor:CAP-97): no test here reads this repository, so the module runs in the
# package half; the tests that do run in test_live_sources_board.py.


def test_deferred_specs_story_21_1_reconciliation() -> None:
    """Pin Story 21.1 de-registrations and registrations against silent regression."""
    assert "spec-intelligence-hub" not in board.DEFERRED_SPECS
    assert "spec-artifact-chain-reconciliation" not in board.DEFERRED_SPECS
    assert "spec-chain-currency-sweep" not in board.DEFERRED_SPECS
    assert "spec-bmad-cursor-interactive-routing" not in board.DEFERRED_SPECS
    assert "spec-golden-path-conda-blind-spot" not in board.DEFERRED_SPECS
    assert "spec-agentic-sdlc-autonomy" not in board.DEFERRED_SPECS
    assert "spec-pyforge-charter" in board.DEFERRED_SPECS
    assert board.DEFERRED_SPECS["spec-pyforge-charter"] == (
        "a constitutive Spec whose CAP-1/4/5/6/8 are document-integrity properties "
        "no story can pick up; CAP-3 mechanism shipped as doctor 21.4; CAP-7/AUT-3 "
        "wait on the Guildhall referent — do not mint a Charter epic"
    )
