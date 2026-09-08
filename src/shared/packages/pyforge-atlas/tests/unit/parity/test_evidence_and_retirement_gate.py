"""Parity-evidence + retirement-gate tests (Story B4, AC-3).

The retirement gate is the machine encoding of AD-19/FR-4: the legacy orchestrator
may be marked for retirement ONLY after every legacy-surface view has a
credentialed, zero-material-drift, human-signed parity record. In-loop (no
credentialed records, no sign-off) the gate MUST refuse — the honest state until
the attended event.
"""

from __future__ import annotations

from pyforge.atlas.parity import (
    ParityEvidenceRecord,
    legacy_surface_view_names,
    may_retire_legacy,
)
from pyforge.atlas.parity.evidence import RUN_MODE_CREDENTIALED, RUN_MODE_FIXTURE

_VIEWS = list(legacy_surface_view_names())


def _rec(view, *, mode=RUN_MODE_CREDENTIALED, drift=False, signed=True):
    return ParityEvidenceRecord(
        view=view,
        legacy_row_count=10,
        kedro_row_count=10,
        material_drift=drift,
        run_mode=mode,
        human_sign_off="operator@example" if signed else None,
    )


def _full(**kw):
    return [_rec(v, **kw) for v in _VIEWS]


def test_gate_blocks_with_no_records():
    d = may_retire_legacy([], required_views=_VIEWS)
    assert not d.allowed
    assert set(d.missing_views) == set(_VIEWS)


def test_gate_blocks_on_fixture_only_records():
    """A green fixture-mode run is NOT parity evidence — the gate must refuse."""
    d = may_retire_legacy(_full(mode=RUN_MODE_FIXTURE), required_views=_VIEWS)
    assert not d.allowed
    assert set(d.non_credentialed_views) == set(_VIEWS)


def test_gate_blocks_on_credentialed_but_unsigned():
    d = may_retire_legacy(_full(signed=False), required_views=_VIEWS)
    assert not d.allowed
    assert set(d.unsigned_views) == set(_VIEWS)


def test_gate_blocks_on_material_drift_even_if_signed():
    d = may_retire_legacy(_full(drift=True), required_views=_VIEWS)
    assert not d.allowed
    assert set(d.drifted_views) == set(_VIEWS)


def test_gate_blocks_when_one_view_missing():
    recs = _full()[:-1]  # drop the last view
    d = may_retire_legacy(recs, required_views=_VIEWS)
    assert not d.allowed
    assert d.missing_views == (_VIEWS[-1],)


def test_gate_allows_only_when_all_credentialed_clean_signed():
    """The ONLY path to allowed=True: every view credentialed + zero drift +
    signed. This is DEFERRED to the attended event — in-loop we assemble the
    hypothetical records to prove the gate opens correctly, not to retire."""
    d = may_retire_legacy(_full(), required_views=_VIEWS)
    assert d.allowed
    assert set(d.covered_views) == set(_VIEWS)


def test_evidence_record_roundtrips():
    rec = _rec("v_actionable_packages", drift=False, signed=True)
    rt = ParityEvidenceRecord.from_dict(rec.to_dict())
    assert rt == rec
    assert rt.is_credentialed and rt.is_signed and not rt.material_drift


def test_gate_stays_closed_on_empty_required_views():
    """Fail-closed: an empty required-view set must NEVER vacuously allow
    retirement (review finding — a vacuous allowed=True would open the gate with
    zero evidence)."""
    # even with plausible-looking signed records present, no required views == block
    d = may_retire_legacy(_full(), required_views=[])
    assert not d.allowed
    assert "no required" in d.reason.lower()


def test_gate_stays_closed_when_clean_record_masks_a_drifted_one():
    """Fail-closed: a coexisting clean+signed credentialed record must NOT mask a
    credentialed record that showed material drift for the same view (review
    finding — masking would open the gate despite recorded drift)."""
    view = _VIEWS[0]
    drifted = _rec(view, drift=True, signed=True)
    clean = _rec(view, drift=False, signed=True)
    # both records for the same view; the rest of the views fully covered
    records = [drifted, clean] + [_rec(v) for v in _VIEWS[1:]]
    d = may_retire_legacy(records, required_views=_VIEWS)
    assert not d.allowed
    assert view in d.drifted_views


def test_in_loop_state_is_honest_block():
    """The state B4 actually produces in the loop — fixture-mode records only —
    yields a BLOCK, never a retirement."""
    from .parity_runner import run_parity

    records = run_parity()  # fixture mode
    d = may_retire_legacy(records, required_views=_VIEWS)
    assert not d.allowed, "in-loop fixture evidence must NEVER allow retirement"
