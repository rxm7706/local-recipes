"""Sole owner of Doctor's exit-code projection (Story 1.1, architecture spine
AD-2).

Domain (frozen, closed): ``{0, 2, 130}`` — deliberately a *subset* of
``pyforge.warden``'s frozen ``{0, 1, 2, 130}``, permanently omitting ``1``
(warden's policy-gate rung), because Doctor reports *operability, not
policy*. Projection: any ``fail``-status ``Finding`` -> exit ``2``; else
(only ``ok``/``warn`` present, including the empty-findings case) -> exit
``0``. A ``warn`` Finding NEVER changes the exit code. ``130`` is the SIGINT
signal-path constant for the CLI boundary, not something this module derives
from a Finding list.

Warden's own exit code (from ``run_doctor_checks``, when a later story calls
it) is consumed as *data* — folded into a Doctor ``Finding.status`` — and
never re-exposed as Doctor's own process exit code. Every other module
*feeds* Findings; only this module *projects* them to an exit code —
enforced by the sole-ownership meta-test.
"""

from __future__ import annotations

from collections.abc import Iterable

from pyforge.core.exit_domains import exit_code
from pyforge.core.verdict import Lattice

from .models import DoctorReport, DoctorStatus, Finding

# Doctor Story 63.1, spec-pyforge-steward:CAP-184: the numbers come from the
# `doctor` domain of the one exit-code declaration (`docs/governance/guild-roster.json`
# `exit_code_domains`, mirrored in process by `pyforge.core.exit_domains`), never
# spelled here; `tests/meta/test_verdict_reads_the_exit_declaration.py` holds this
# module's domain to it.
EXIT_SIGINT = exit_code("doctor", "interrupted")

_EXIT_OK = exit_code("doctor", "ok")
_EXIT_FAIL = exit_code("doctor", "fail")

# Story 14.3, SPEC-pyforge-core CAP-3: the shared domain-declaration
# mechanism -- `exit_code_for`'s own any-fail predicate below is UNCHANGED
# (it is not rank-based; see the story's Design Notes), but `.exit_codes`
# turns the "subset of warden's frozen {0, 1, 2, 130}" docstring claim into
# a computed fact (`tests/meta/test_verdict_narrows_warden.py`). PUBLIC (not
# `_LATTICE`): that test imports this name from outside the module.
LATTICE = Lattice(
    order=(DoctorStatus.FAIL, DoctorStatus.WARN, DoctorStatus.OK),
    exit_by_member={status: exit_code("doctor", status.value) for status in DoctorStatus},
)


def exit_code_for(findings: Iterable[Finding] | DoctorReport) -> int:
    """Project a collection of ``Finding``\\ s (or a whole ``DoctorReport``)
    to Doctor's exit code — total over the closed ``{0, 2, 130}`` domain (the
    130 SIGINT constant is never produced here; it lives at the CLI
    boundary). Any ``fail``-status finding makes the whole run exit ``2``;
    otherwise (including zero findings) it exits ``0`` — a ``warn`` finding
    never changes this.
    """
    if isinstance(findings, DoctorReport):
        findings = findings.findings
    if any(finding.status is DoctorStatus.FAIL for finding in findings):
        return _EXIT_FAIL
    return _EXIT_OK
