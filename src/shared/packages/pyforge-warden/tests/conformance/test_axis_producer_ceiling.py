"""Conformance — the axis-producer-ceiling meta-test (Story 6.2; Story 6.3
appends the currency axis's own entry to the SAME parametrized table rather
than duplicating this suite).

Some axes are v1-scoped WARN-ONLY: real escalation (denied/unknown ->
policy-violation/indeterminate) is a LATER story's sole ownership, and the
axis's own ``*_rung`` function is a hard cap, oblivious to any policy table.
This suite mechanically proves that ceiling never regresses — a future edit
that lets ``license_rung`` consult ``config.license_policy`` (Story 6.5's own
job) would fail this test immediately if it forgot to also raise this
ceiling deliberately.

Never touches ``verdict.py``'s lattice/exit-code logic (the sole-ownership
guard already scans this module too, like every non-``verdict.py`` module in
the package)."""

from __future__ import annotations

import pytest

from pyforge.warden.license import license_rung
from pyforge.warden.models import (
    AXIS_LICENSE,
    Finding,
    LicenseInfo,
    LicenseVerdict,
    Status,
)

# (axis-name, rung-function, (Finding, ...)) — one entry per WARN-only v1
# axis. Story 6.3 appends its own currency-axis tuple here; the
# parametrization below stays generic over however many entries exist.
_CEILING_FIXTURES: tuple[tuple[str, object, tuple[Finding, ...]], ...] = (
    (
        "license",
        license_rung,
        (
            Finding(
                id="license:GPL-3.0-only:copyleft-pkg@1.0.0",
                axis=AXIS_LICENSE,
                message="copyleft-pkg: license 'GPL-3.0-only' is denied",
                subject="copyleft-pkg",
                severity=None,
                license=LicenseInfo(
                    expression="GPL-3.0-only",
                    family="GPL3",
                    verdict=LicenseVerdict.DENIED,
                ),
            ),
            Finding(
                id="license:unknown:mystery-pkg@2.0.0",
                axis=AXIS_LICENSE,
                message="mystery-pkg: license could not be resolved",
                subject="mystery-pkg",
                severity=None,
                license=LicenseInfo(
                    expression="unknown", family=None, verdict=LicenseVerdict.UNKNOWN
                ),
            ),
            Finding(
                id="license:unknown:bare-pkg@unspecified",
                axis=AXIS_LICENSE,
                message="bare-pkg: license could not be resolved",
                subject="bare-pkg",
                severity=None,
                license=LicenseInfo(
                    expression="unknown", family=None, verdict=LicenseVerdict.UNKNOWN
                ),
            ),
        ),
    ),
)


@pytest.mark.parametrize(
    "axis_name,rung_fn,findings",
    _CEILING_FIXTURES,
    ids=[entry[0] for entry in _CEILING_FIXTURES],
)
def test_axis_producer_never_exceeds_warn(axis_name, rung_fn, findings):
    for finding in findings:
        status, driver = rung_fn(finding)
        assert status is Status.WARN, (
            f"{axis_name} axis producer fed {status!r} for {finding.id!r} — "
            "this axis is v1-scoped WARN-only until its own escalation story"
        )
        assert driver.axis == axis_name
        assert driver.finding_id == finding.id


def test_ceiling_table_covers_every_finding_eligible_verdict():
    """Non-vacuous proof: the license axis's fixture set exercises BOTH
    Finding-eligible verdicts (denied, unknown) — allowed never reaches a
    Finding, so it is never a candidate here."""
    license_entry = next(e for e in _CEILING_FIXTURES if e[0] == "license")
    verdicts = {f.license.verdict for f in license_entry[2] if f.license is not None}
    assert verdicts == {LicenseVerdict.DENIED, LicenseVerdict.UNKNOWN}
