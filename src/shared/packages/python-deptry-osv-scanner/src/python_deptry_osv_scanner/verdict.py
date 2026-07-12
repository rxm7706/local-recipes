"""Sole owner of the verdict lattice + exit projection (Story 1.1, C0a).

Lattice order (fixed, strongest first):
``error > policy-violation > indeterminate > warn > bypassed > clean >
not-applicable``. Exit projection (locked): ``{clean, not-applicable,
bypassed} -> 0``; ``warn -> 0`` (the ``warn_is_error`` knob makes it
non-zero); ``policy-violation -> 1``; ``indeterminate -> 1``; ``error -> 2``;
SIGINT constant ``130`` (a signal-path constant for the CLI boundary, not a
lattice rung).

Every other module *feeds* rungs; only this module *projects* them to exit
codes — enforced by the sole-ownership meta-test. The projection is TOTAL
over all 7 rungs, and an unknown/weaker ``cve_match_level`` projects toward
``indeterminate``, never ``clean`` (the additive-growth safety rule).
"""

from __future__ import annotations

from collections.abc import Iterable

from .models import CveMatchLevel, Status, StatusDriver

_RUNG_ORDER: tuple[Status, ...] = (
    Status.ERROR,
    Status.POLICY_VIOLATION,
    Status.INDETERMINATE,
    Status.WARN,
    Status.BYPASSED,
    Status.CLEAN,
    Status.NOT_APPLICABLE,
)

_RANK: dict[Status, int] = {status: rank for rank, status in enumerate(_RUNG_ORDER)}

EXIT_SIGINT = 130

_EXIT_BY_STATUS: dict[Status, int] = {
    Status.ERROR: 2,
    Status.POLICY_VIOLATION: 1,
    Status.INDETERMINATE: 1,
    Status.WARN: 0,
    Status.BYPASSED: 0,
    Status.CLEAN: 0,
    Status.NOT_APPLICABLE: 0,
}

_EXIT_WARN_AS_ERROR = 1


def compose(
    rungs: Iterable[tuple[Status | str, StatusDriver | None]],
) -> tuple[Status, StatusDriver | None]:
    """Compose fed rungs: the highest rung wins and its driver propagates.

    Each fed status is coerced via ``Status(status)`` — an unknown value
    raises ``ValueError`` (fail-loud, never a silent downgrade). Empty input
    -> ``(not-applicable, None)`` — nothing existed to scan.

    Equal-rank tie-break (feed-order independent): a rung carrying a driver
    beats a ``None``-driver rung; among drivers, the smallest
    ``(axis, finding_id)`` wins. A non-clean winner with a ``None`` driver is
    not an error HERE — it is caught at report construction
    (``ComplianceReport.__post_init__``), where the driver requirement lives.
    """
    winner: tuple[Status, StatusDriver | None] | None = None
    for raw_status, driver in rungs:
        status = Status(raw_status)
        if winner is None or _RANK[status] < _RANK[winner[0]]:
            winner = (status, driver)
        elif _RANK[status] == _RANK[winner[0]] and _driver_beats(driver, winner[1]):
            winner = (status, driver)
    if winner is None:
        return (Status.NOT_APPLICABLE, None)
    return winner


def _driver_beats(candidate: StatusDriver | None, incumbent: StatusDriver | None) -> bool:
    """Deterministic driver preference for equal-rank rungs: any driver beats
    ``None``; among drivers, the smallest ``(axis, finding_id)`` wins."""
    if candidate is None:
        return False
    if incumbent is None:
        return True
    return (candidate.axis, candidate.finding_id) < (
        incumbent.axis,
        incumbent.finding_id,
    )


def exit_code_for(status: Status | str, *, warn_is_error: bool = False) -> int:
    """Project a status to its exit code — TOTAL over all 7 rungs (C0a).

    The input is coerced via ``Status(status)`` first, so a raw ``"warn"``
    string respects ``warn_is_error`` and an unknown string raises
    ``ValueError`` instead of silently projecting.
    """
    status = Status(status)
    if status is Status.WARN and warn_is_error:
        return _EXIT_WARN_AS_ERROR
    return _EXIT_BY_STATUS[status]


def match_level_rung(level: CveMatchLevel | str) -> Status:
    """Rung for a CVE-match level: ``exact`` -> ``clean``; ``name-only``,
    ``none``, and ANY unrecognized future value -> ``indeterminate``."""
    if level == CveMatchLevel.EXACT:
        return Status.CLEAN
    return Status.INDETERMINATE
