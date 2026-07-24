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

from pyforge.warden.currency import currency_rung
from pyforge.warden.license import license_rung
from pyforge.warden.models import (
    AXIS_CURRENCY,
    AXIS_LICENSE,
    CurrencyInfo,
    CurrencyVerdict,
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
    (
        "currency",
        currency_rung,
        (
            Finding(
                id="currency:eol:legacy-django@1.11.29",
                axis=AXIS_CURRENCY,
                message="legacy-django: reached end-of-life 2020-04-01 (endoflife-date)",
                subject="legacy-django",
                severity=None,
                currency=CurrencyInfo(
                    verdict=CurrencyVerdict.EOL,
                    latest="5.2",
                    lag=9,
                    eol_date="2020-04-01",
                    tier="endoflife-date",
                ),
            ),
            Finding(
                id="currency:over-lag:requests@2.0.0",
                axis=AXIS_CURRENCY,
                message="requests: 1 release(s) behind latest '2.31.0' (endoflife-date)",
                subject="requests",
                severity=None,
                currency=CurrencyInfo(
                    verdict=CurrencyVerdict.SUPPORTED,
                    latest="2.31.0",
                    lag=1,
                    eol_date="2099-01-01",
                    tier="endoflife-date",
                ),
            ),
            Finding(
                id="currency:unknown:mystery-pkg@2.0.0",
                axis=AXIS_CURRENCY,
                message="mystery-pkg: currency could not be resolved (no usable registry/feed data)",
                subject="mystery-pkg",
                severity=None,
                currency=CurrencyInfo(verdict=CurrencyVerdict.UNKNOWN),
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


def test_currency_ceiling_table_covers_all_three_reason_eligible_verdicts():
    """Story 6.3's own non-vacuous coverage check, mirroring the license one
    above: the currency axis's fixture set exercises all THREE reason-
    eligible id-prefixes (eol/over-lag/unknown) — a fully-current
    (supported, zero-lag) resolution never reaches a Finding at all, so it
    is never a candidate here."""
    currency_entry = next(e for e in _CEILING_FIXTURES if e[0] == "currency")
    reasons = {f.id.split(":")[1] for f in currency_entry[2]}
    assert reasons == {"eol", "over-lag", "unknown"}


# --- Story 6.5: the ceiling guards ONLY the default (no-policy) call ---------
#
# The parametrized ceiling above proves the WARN cap for the no-arg
# ``rung_fn(finding)`` call. These companions prove the OTHER half: a HANDED
# gating policy DOES escalate the very same fixtures -- so the ceiling is
# understood as "the unconfigured default never exceeds warn", NOT "the rung
# can never escalate at all" (which Story 6.5 makes false).


def test_gating_license_policy_escalates_every_ceiling_fixture():
    license_entry = next(e for e in _CEILING_FIXTURES if e[0] == "license")
    policy = {
        LicenseVerdict.DENIED: Status.POLICY_VIOLATION,
        LicenseVerdict.UNKNOWN: Status.INDETERMINATE,
    }
    for finding in license_entry[2]:
        status, _driver = license_rung(finding, policy=policy)
        assert status is not Status.WARN
        expected = (
            Status.POLICY_VIOLATION
            if finding.license.verdict is LicenseVerdict.DENIED
            else Status.INDETERMINATE
        )
        assert status is expected


def test_gating_currency_policy_escalates_every_ceiling_fixture():
    currency_entry = next(e for e in _CEILING_FIXTURES if e[0] == "currency")
    policy = {
        CurrencyVerdict.EOL: Status.POLICY_VIOLATION,
        CurrencyVerdict.UNKNOWN: Status.INDETERMINATE,
    }
    for finding in currency_entry[2]:
        # max_lag=0 so the over-lag fixture (SUPPORTED, lag=1) escalates via
        # the numeric threshold check too -- none of the three stays warn.
        status, _driver = currency_rung(finding, policy=policy, max_lag=0)
        assert status is not Status.WARN
        # Exact-status half, mirroring the license companion above: the
        # ESCALATED semantics (not merely "not warn") are what exit
        # projection rides on.
        reason = finding.id.split(":")[1]
        expected = {
            "eol": Status.POLICY_VIOLATION,
            "over-lag": Status.POLICY_VIOLATION,
            "unknown": Status.INDETERMINATE,
        }[reason]
        assert status is expected
