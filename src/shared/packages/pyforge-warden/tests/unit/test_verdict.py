"""Unit tests — C0a directly against the projection (Story 1.1's core AC).

Projection totality over ALL Status members, the locked exit table, the
``warn_is_error`` knob, compose ordering + driver propagation, the
match-level safety rule (unknown/weaker -> indeterminate, never clean), and
the all-clean guard (the socket is proven-total, not dead).
"""

from __future__ import annotations

import pytest

from pyforge.warden.inventory import ResolvedInventory, merge_components
from pyforge.warden.models import (
    AXIS_HYGIENE,
    AXIS_VULNERABILITY,
    CveMatchLevel,
    Status,
    StatusDriver,
)
from pyforge.warden.verdict import (
    EXIT_SIGINT,
    compose,
    exit_code_for,
    match_level_rung,
)

LOCKED_EXIT_TABLE = {
    Status.CLEAN: 0,
    Status.NOT_APPLICABLE: 0,
    Status.BYPASSED: 0,
    Status.WARN: 0,
    Status.POLICY_VIOLATION: 1,
    Status.INDETERMINATE: 1,
    Status.ERROR: 2,
}


@pytest.mark.parametrize("status", list(Status), ids=lambda s: s.value)
def test_projection_is_total_and_locked(status):
    """C0a: every Status member has a defined exit code, per the locked table."""
    assert exit_code_for(status) == LOCKED_EXIT_TABLE[status]


@pytest.mark.parametrize("status", list(Status), ids=lambda s: s.value)
def test_projection_stays_inside_frozen_exit_enum(status):
    assert exit_code_for(status) in {0, 1, 2, 130}
    assert exit_code_for(status, warn_is_error=True) in {0, 1, 2, 130}


def test_indeterminate_exits_one():
    assert exit_code_for(Status.INDETERMINATE) == 1


def test_error_exits_two():
    assert exit_code_for(Status.ERROR) == 2


def test_warn_is_error_knob():
    assert exit_code_for(Status.WARN) == 0
    assert exit_code_for(Status.WARN, warn_is_error=True) == 1
    for status in Status:
        if status is Status.WARN:
            continue
        assert exit_code_for(status, warn_is_error=True) == exit_code_for(status)


def test_exit_sigint_constant():
    assert EXIT_SIGINT == 130


def test_compose_indeterminate_outranks_warn():
    warn_driver = StatusDriver(axis=AXIS_HYGIENE, finding_id="hygiene:DEP002:leftpad")
    ind_driver = StatusDriver(
        axis=AXIS_VULNERABILITY, finding_id="indeterminate:no-version:requests"
    )
    rungs = [(Status.WARN, warn_driver), (Status.INDETERMINATE, ind_driver)]
    assert compose(rungs) == (Status.INDETERMINATE, ind_driver)
    assert compose(reversed(rungs)) == (Status.INDETERMINATE, ind_driver)


def test_compose_error_outranks_policy_violation():
    policy_driver = StatusDriver(
        axis=AXIS_VULNERABILITY, finding_id="vuln:GHSA-x:requests@2.31.0"
    )
    error_driver = StatusDriver(
        axis=AXIS_VULNERABILITY, finding_id="indeterminate:engine-timeout:osv"
    )
    rungs = [(Status.POLICY_VIOLATION, policy_driver), (Status.ERROR, error_driver)]
    assert compose(rungs) == (Status.ERROR, error_driver)


def test_compose_winner_driver_propagates():
    winner_driver = StatusDriver(
        axis=AXIS_VULNERABILITY, finding_id="vuln:GHSA-y:numpy@1.0"
    )
    status, driver = compose(
        [
            (Status.CLEAN, None),
            (Status.POLICY_VIOLATION, winner_driver),
            (Status.WARN, StatusDriver(axis=AXIS_HYGIENE, finding_id="hygiene:DEP003:x")),
        ]
    )
    assert status is Status.POLICY_VIOLATION
    assert driver is winner_driver
    assert driver.axis == AXIS_VULNERABILITY
    assert driver.finding_id == "vuln:GHSA-y:numpy@1.0"


def test_compose_empty_is_not_applicable():
    assert compose([]) == (Status.NOT_APPLICABLE, None)


def test_compose_coerces_raw_status_strings():
    assert compose([("warn", None), ("clean", None)]) == (Status.WARN, None)


def test_compose_unknown_status_raises():
    """Fail-loud coercion: an unknown fed status is a ValueError, never a
    silent rung."""
    with pytest.raises(ValueError):
        compose([("warnings", None)])
    with pytest.raises(ValueError):
        compose([(Status.CLEAN, None), ("totally-unknown", None)])


def test_exit_code_for_coerces_raw_strings_and_fails_loud():
    assert exit_code_for("warn") == 0
    assert exit_code_for("warn", warn_is_error=True) == 1
    with pytest.raises(ValueError):
        exit_code_for("warnings")


def test_compose_equal_rank_tie_break_is_feed_order_independent():
    """Equal-rank ties resolve to the smallest (axis, finding_id) driver,
    regardless of feed order."""
    small = StatusDriver(axis=AXIS_HYGIENE, finding_id="hygiene:DEP001:aaa")
    big = StatusDriver(
        axis=AXIS_VULNERABILITY, finding_id="vuln:GHSA-zzzz:zlib@1.3"
    )
    rungs = [(Status.POLICY_VIOLATION, big), (Status.POLICY_VIOLATION, small)]
    assert compose(rungs) == (Status.POLICY_VIOLATION, small)
    assert compose(reversed(rungs)) == (Status.POLICY_VIOLATION, small)


def test_compose_equal_rank_driver_beats_none_driver():
    driver = StatusDriver(axis=AXIS_HYGIENE, finding_id="hygiene:DEP002:leftpad")
    rungs = [(Status.WARN, None), (Status.WARN, driver)]
    assert compose(rungs) == (Status.WARN, driver)
    assert compose(reversed(rungs)) == (Status.WARN, driver)


def test_match_level_exact_is_clean():
    assert match_level_rung(CveMatchLevel.EXACT) is Status.CLEAN


@pytest.mark.parametrize(
    "level",
    [CveMatchLevel.NAME_ONLY, CveMatchLevel.NONE, "name-only", "none"],
    ids=str,
)
def test_weaker_match_levels_are_indeterminate(level):
    assert match_level_rung(level) is Status.INDETERMINATE


@pytest.mark.parametrize(
    "level",
    ["version-range", "fuzzy", "", "EXACT-v2", "totally-unknown-future-level"],
    ids=str,
)
def test_unknown_match_level_is_indeterminate_never_clean(level):
    """The additive-growth safety rule: unrecognized never projects to clean."""
    rung = match_level_rung(level)
    assert rung is Status.INDETERMINATE
    assert rung is not Status.CLEAN


def test_only_exact_reaches_clean_across_current_members():
    for level in CveMatchLevel:
        expected = Status.CLEAN if level is CveMatchLevel.EXACT else Status.INDETERMINATE
        assert match_level_rung(level) is expected


def test_all_clean_guard_socket_proven_total_not_dead(component_factory):
    """A fully-resolved all-exact inventory composes to clean with ZERO
    indeterminate rungs — and it exits 0."""
    inventory = ResolvedInventory(
        components=merge_components(
            [
                component_factory(name="requests", version="2.31.0"),
                component_factory(name="numpy", version="1.26.4"),
                component_factory(name="packaging", version="24.0"),
            ]
        ),
        resolved_scan_set=(),
    )
    assert inventory.count == 3
    rungs = [
        (match_level_rung(component.cve_match_level), None)
        for component in inventory.components
    ]
    assert all(status is Status.CLEAN for status, _ in rungs)
    assert not any(status is Status.INDETERMINATE for status, _ in rungs)
    status, driver = compose(rungs)
    assert status is Status.CLEAN
    assert driver is None
    assert exit_code_for(status) == 0
