"""Meta test -- Story 6.3's own "reporting clean for a check that cannot
fail is a meta-test failure" AC, made structural rather than a convention a
future call site could quietly violate.

Three claims, each proven non-vacuously (mirrors
``test_ad36_projection_mechanism_table.py``'s own self-proving technique):

1. ``core.conformance``'s one passing status
   (``STATUS_LINK_TARGET_CONFIRMED``) is returned if and only if a tree is
   ``desired`` AND its live symlink target genuinely equals the expected
   canonical-relative target -- a full sweep over every OTHER combination of
   ``(desired, previously_projected, live_target, live_exists)`` never
   returns it.
2. When the mechanism cannot be evaluated at all (``mechanism=None``, or any
   mechanism string absent from ``MECHANISM_CHECKERS``), ``evaluate_
   conformance`` NEVER returns the passing status for ANY input -- including
   a ``live_states`` list that WOULD have passed under the ``"symlink"``
   mechanism. The "cannot fail" case is structurally incapable of reporting
   a pass.
3. ``"not-applicable"`` is never a member of ``core.conformance.
   ALL_STATUSES``, and ``core.verdict.LATTICE_ORDER`` (the closed 6-member
   lattice AD-31 declares) has no ``not-applicable`` member either -- the
   AC's own explicit prohibition, checked directly against both modules'
   real, current definitions rather than trusted from memory.
"""

from __future__ import annotations

import itertools

from pyforge.marshal.core import verdict
from pyforge.marshal.core.conformance import (
    ALL_STATUSES,
    STATUS_LINK_TARGET_CONFIRMED,
    TreeLiveState,
    _check_symlink_identity,
    evaluate_conformance,
)

_TREE = ".agents/skills"
_EXPECTED = "../.claude/skills"
_WRONG = "../elsewhere"


def _state(*, desired, previously_projected, live_target, live_exists) -> TreeLiveState:
    return TreeLiveState(
        tree=_TREE,
        adapters=("codex",),
        desired=desired,
        previously_projected=previously_projected,
        live_target=live_target,
        live_exists=live_exists,
        expected_target=_EXPECTED,
    )


def _in_scope_combinations():
    """Every ``(desired, previously_projected, live_target, live_exists)``
    combination ``_check_symlink_identity`` accepts (excludes the
    neither-desired-nor-tracked combinations, which raise ``ValueError`` by
    contract -- proven separately in ``tests/unit/test_conformance.py``)."""
    live_target_options = (None, _EXPECTED, _WRONG)
    live_exists_options = (False, True)
    for desired, previously_projected in itertools.product((False, True), repeat=2):
        if not desired and not previously_projected:
            continue
        for live_target, live_exists in itertools.product(live_target_options, live_exists_options):
            yield desired, previously_projected, live_target, live_exists


def test_confirmed_is_reachable_at_least_once():
    """Non-vacuous: the passing status IS produced somewhere in the sweep --
    otherwise claim 2 below (never produced under an unevaluable mechanism)
    would be trivially true for the wrong reason."""
    confirmed_seen = any(
        _check_symlink_identity(
            _state(
                desired=desired,
                previously_projected=previously_projected,
                live_target=live_target,
                live_exists=live_exists,
            )
        ).status
        == STATUS_LINK_TARGET_CONFIRMED
        for desired, previously_projected, live_target, live_exists in _in_scope_combinations()
    )
    assert confirmed_seen, "the passing status is never reachable at all -- the sweep below would be vacuous"


def test_confirmed_iff_desired_and_target_matches():
    for desired, previously_projected, live_target, live_exists in _in_scope_combinations():
        state = _state(
            desired=desired,
            previously_projected=previously_projected,
            live_target=live_target,
            live_exists=live_exists,
        )
        result = _check_symlink_identity(state)
        expected_confirmed = desired and live_target == _EXPECTED
        actual_confirmed = result.status == STATUS_LINK_TARGET_CONFIRMED
        assert actual_confirmed == expected_confirmed, (
            f"state={state!r} produced status={result.status!r}, expected "
            f"confirmed={expected_confirmed}"
        )


def test_unevaluable_mechanism_never_confirms_even_a_would_pass_state():
    """The would-pass state: desired, live target genuinely matches
    canonical -- under the "symlink" mechanism this confirms (proven above).
    Under `mechanism=None` (or any mechanism absent from
    `MECHANISM_CHECKERS`), it must NEVER confirm -- the check literally
    cannot run, so it must never look like it ran and passed."""
    would_pass_state = _state(desired=True, previously_projected=True, live_target=_EXPECTED, live_exists=True)
    assert _check_symlink_identity(would_pass_state).status == STATUS_LINK_TARGET_CONFIRMED

    for mechanism in (None, "junction", "copy", ""):
        report = evaluate_conformance([would_pass_state], mechanism=mechanism)
        assert report.checks == (), f"mechanism={mechanism!r} produced a check instead of deferring to unevaluated"
        assert would_pass_state.tree in report.unevaluated_trees


def test_unevaluable_mechanism_never_confirms_across_the_full_sweep():
    for desired, previously_projected, live_target, live_exists in _in_scope_combinations():
        state = _state(
            desired=desired,
            previously_projected=previously_projected,
            live_target=live_target,
            live_exists=live_exists,
        )
        report = evaluate_conformance([state], mechanism=None)
        assert report.checks == ()
        assert report.unevaluated_trees == (state.tree,)


def test_not_applicable_is_never_a_conformance_status():
    assert "not-applicable" not in ALL_STATUSES
    assert "clean" not in ALL_STATUSES  # `Verdict.CLEAN` is `core.verdict`'s own reserved vocabulary


def test_verdict_lattice_has_no_not_applicable_member():
    lattice_values = {member.value for member in verdict.LATTICE_ORDER}
    assert "not-applicable" not in lattice_values
    assert len(verdict.LATTICE_ORDER) == 6
