"""Unit tests — the strategy seam: Protocols, registry, null engine,
``DefaultPolicy`` (Story 1.2).

The seam's contract, unit-proven: the registry holds exactly the null
engine; ``NullEngine.run`` returns the empty ``EngineResult``;
``DefaultPolicy`` derives the withheld→indeterminate finding (id grammar
``indeterminate:<reason>:<pkg>``, driver axis+finding_id), passes engine
findings through, and never feeds a driverless non-clean rung.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from pyforge.warden import engines as engines_module
from pyforge.warden.config import EffectiveConfig
from pyforge.warden.engines import (
    NullEngine,
    register_engine,
    registered_engines,
)
from pyforge.warden.interfaces import (
    DefaultPolicy,
    Engine,
    EngineResult,
    Extractor,
    Policy,
    Router,
    VulnStrategy,
)
from pyforge.warden.inventory import ResolvedInventory, merge_components
from pyforge.warden.models import (
    AXIS_CURRENCY,
    AXIS_HYGIENE,
    AXIS_INGESTION,
    AXIS_LICENSE,
    AXIS_VULNERABILITY,
    CurrencyInfo,
    CurrencyVerdict,
    CveMatchLevel,
    Ecosystem,
    Epss,
    ErrorKind,
    ErrorRecord,
    Finding,
    LicenseInfo,
    LicenseVerdict,
    ScannedManifest,
    Severity,
    SeverityTier,
    Status,
    StatusDriver,
    WithholdReason,
)

MANIFEST = ScannedManifest(path="pyproject.toml", kind="pyproject.toml")
EMPTY_RESULT = EngineResult(
    findings=(), errors=(), coverage=(), axis=AXIS_VULNERABILITY
)


def make_inventory(*components) -> ResolvedInventory:
    return ResolvedInventory(
        components=merge_components(components),
        resolved_scan_set=(MANIFEST,),
    )


# --- registry + null engine --------------------------------------------------


def test_registry_holds_the_null_deptry_and_osv_engines():
    """Story 1.3 registers the real deptry engine, Story 1.5 the osv-scanner
    engine, Story 6.2 the license engine, Story 6.3 the currency engine,
    alongside the retained no-op null engine, in deterministic registration
    order."""
    engines = registered_engines()
    assert [engine.name for engine in engines] == [
        "null",
        "deptry",
        "osv-scanner",
        "license",
        "currency",
    ]
    assert isinstance(engines[0], NullEngine)


def test_registered_engines_returns_fresh_instances():
    first = registered_engines()
    second = registered_engines()
    assert first[0] is not second[0]


def test_register_engine_appends_in_deterministic_order(monkeypatch):
    monkeypatch.setattr(
        engines_module, "_ENGINE_FACTORIES", [*engines_module._ENGINE_FACTORIES]
    )

    class DummyEngine:
        name = "dummy"

        def run(self, target: Path, inventory: ResolvedInventory) -> EngineResult:
            return EMPTY_RESULT

    returned = register_engine(DummyEngine)
    assert returned is DummyEngine  # decorator-friendly
    names = [engine.name for engine in registered_engines()]
    assert names == [
        "null",
        "deptry",
        "osv-scanner",
        "license",
        "currency",
        "dummy",
    ]


def test_register_engine_is_idempotent_for_the_same_factory(monkeypatch):
    """Re-registering the SAME factory (module re-import/reload) must not
    make the engine run twice."""
    monkeypatch.setattr(
        engines_module, "_ENGINE_FACTORIES", [*engines_module._ENGINE_FACTORIES]
    )
    before = len(registered_engines())
    register_engine(NullEngine)
    assert len(registered_engines()) == before


def test_null_engine_run_returns_the_empty_result(tmp_path):
    result = NullEngine().run(tmp_path, make_inventory())
    assert result.findings == ()
    assert result.errors == ()
    assert result.coverage == ()
    assert result.axis == AXIS_INGESTION


def test_engine_result_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        EMPTY_RESULT.findings = ()  # type: ignore[misc]


# --- protocol conformance (structural) ---------------------------------------


def test_null_engine_conforms_to_the_engine_protocol():
    assert isinstance(NullEngine(), Engine)


def test_default_policy_conforms_to_the_policy_protocol():
    assert isinstance(DefaultPolicy(), Policy)


def test_stub_implementations_conform_to_the_remaining_protocols():
    class StubExtractor:
        def extract(self, manifest_path: Path, manifest: ScannedManifest):
            return ()

    class StubRouter:
        def route(self, manifest_kind: str, section: str) -> Ecosystem:
            return Ecosystem.PYPI

    class StubVulnStrategy:
        def match(self, inventory: ResolvedInventory) -> EngineResult:
            return EMPTY_RESULT

    assert isinstance(StubExtractor(), Extractor)
    assert isinstance(StubRouter(), Router)
    assert isinstance(StubVulnStrategy(), VulnStrategy)


# --- DefaultPolicy -----------------------------------------------------------


def test_withheld_component_derives_the_indeterminate_finding(component_factory):
    inventory = make_inventory(
        component_factory(
            name="leftpad",
            version=None,
            indeterminate_reason=WithholdReason.NO_VERSION,
        )
    )
    findings, rungs = DefaultPolicy().evaluate(inventory, [EMPTY_RESULT])
    assert len(findings) == 1
    finding = findings[0]
    assert finding.id == "indeterminate:no-version:leftpad@unspecified"
    assert finding.axis == AXIS_VULNERABILITY
    assert finding.subject == "leftpad"
    assert len(rungs) == 1
    status, driver = rungs[0]
    assert status is Status.INDETERMINATE
    assert driver is not None
    assert driver.axis == AXIS_VULNERABILITY
    assert driver.finding_id == finding.id


def test_range_only_reason_appears_in_the_finding_id(component_factory):
    inventory = make_inventory(
        component_factory(
            name="requests",
            version=None,
            indeterminate_reason=WithholdReason.RANGE_ONLY,
        )
    )
    findings, _ = DefaultPolicy().evaluate(inventory, [])
    assert findings[0].id == "indeterminate:range-only:requests@unspecified"


def test_engine_findings_pass_through(component_factory):
    engine_finding = Finding(
        id="hygiene:DEP002:leftpad",
        axis=AXIS_HYGIENE,
        message="unused dependency",
        subject="leftpad",
        severity=None,
    )
    result = EngineResult(findings=(engine_finding,), errors=(), coverage=(), axis=AXIS_HYGIENE)
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    findings, rungs = DefaultPolicy().evaluate(inventory, [result])
    assert engine_finding in findings
    # Story 1.3: a hygiene DEP002 finding now feeds a WARN rung — the real
    # default hygiene mapping replaced the 1.2 indeterminate backstop for the
    # hygiene axis (DEP002 -> warn), carrying the finding's axis and id.
    assert (
        Status.WARN,
        StatusDriver(axis=AXIS_HYGIENE, finding_id="hygiene:DEP002:leftpad"),
    ) in rungs


# --- Story 1.6: vulnerability-axis severity -> rung composition -------------


def test_critical_vuln_finding_feeds_a_policy_violation_rung(component_factory):
    engine_finding = Finding(
        id="vuln:GHSA-xxxx:foo@1.0.0",
        axis=AXIS_VULNERABILITY,
        message="foo: GHSA-xxxx (severity critical)",
        subject="foo",
        severity=Severity(
            tier=SeverityTier.CRITICAL,
            raw="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        ),
    )
    result = EngineResult(findings=(engine_finding,), errors=(), coverage=(), axis=AXIS_VULNERABILITY)
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    findings, rungs = DefaultPolicy().evaluate(inventory, [result])
    assert engine_finding in findings
    assert (
        Status.POLICY_VIOLATION,
        StatusDriver(axis=AXIS_VULNERABILITY, finding_id=engine_finding.id),
    ) in rungs


@pytest.mark.parametrize(
    "tier",
    [SeverityTier.HIGH, SeverityTier.MEDIUM, SeverityTier.LOW, SeverityTier.NONE],
)
def test_non_critical_vuln_finding_feeds_a_warn_rung(component_factory, tier):
    engine_finding = Finding(
        id="vuln:GHSA-yyyy:foo@1.0.0",
        axis=AXIS_VULNERABILITY,
        message="foo: GHSA-yyyy",
        subject="foo",
        severity=Severity(tier=tier, raw=None),
    )
    result = EngineResult(findings=(engine_finding,), errors=(), coverage=(), axis=AXIS_VULNERABILITY)
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    findings, rungs = DefaultPolicy().evaluate(inventory, [result])
    assert engine_finding in findings
    assert (
        Status.WARN,
        StatusDriver(axis=AXIS_VULNERABILITY, finding_id=engine_finding.id),
    ) in rungs


def test_unknown_tier_vuln_finding_still_feeds_indeterminate(component_factory):
    """UNKNOWN is deliberately absent from the default policy table -- an
    unassessable severity must never silently downgrade to warn (the
    backstop preserved for this case)."""
    engine_finding = Finding(
        id="vuln:GHSA-zzzz:foo@1.0.0",
        axis=AXIS_VULNERABILITY,
        message="foo: GHSA-zzzz",
        subject="foo",
        severity=Severity(tier=SeverityTier.UNKNOWN, raw=None),
    )
    result = EngineResult(findings=(engine_finding,), errors=(), coverage=(), axis=AXIS_VULNERABILITY)
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    findings, rungs = DefaultPolicy().evaluate(inventory, [result])
    assert engine_finding in findings
    assert (
        Status.INDETERMINATE,
        StatusDriver(axis=AXIS_VULNERABILITY, finding_id=engine_finding.id),
    ) in rungs


def test_severity_less_vuln_axis_finding_still_feeds_indeterminate(
    component_factory,
):
    """The vulnerability axis's own indeterminate: withhold findings
    (severity=None) still route to indeterminate through vuln_rung -- the
    pre-1.6 backstop's result is preserved for this case even though a real
    severity mapping now governs the axis."""
    engine_finding = Finding(
        id="indeterminate:offline-db-unavailable:foo@1.0.0",
        axis=AXIS_VULNERABILITY,
        message="foo: not checked",
        subject="foo",
        severity=None,
    )
    result = EngineResult(findings=(engine_finding,), errors=(), coverage=(), axis=AXIS_VULNERABILITY)
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    findings, rungs = DefaultPolicy().evaluate(inventory, [result])
    assert engine_finding in findings
    assert (
        Status.INDETERMINATE,
        StatusDriver(axis=AXIS_VULNERABILITY, finding_id=engine_finding.id),
    ) in rungs


# --- Story 3.1: EffectiveConfig threading ------------------------------------


def test_default_policy_no_config_arg_is_unchanged(component_factory):
    """DefaultPolicy() (no config) reproduces every pre-3.1 caller's
    behavior byte-for-byte -- CRITICAL still blocks, HIGH still warns."""
    engine_finding = Finding(
        id="vuln:GHSA-xxxx:foo@1.0.0",
        axis=AXIS_VULNERABILITY,
        message="foo: GHSA-xxxx",
        subject="foo",
        severity=Severity(tier=SeverityTier.HIGH, raw=None),
    )
    result = EngineResult(
        findings=(engine_finding,), errors=(), coverage=(), axis=AXIS_VULNERABILITY
    )
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    _, rungs = DefaultPolicy().evaluate(inventory, [result])
    assert (
        Status.WARN,
        StatusDriver(axis=AXIS_VULNERABILITY, finding_id=engine_finding.id),
    ) in rungs


def test_default_policy_with_fail_on_high_escalates_a_high_severity_finding(
    component_factory,
):
    """Story 3.1: EffectiveConfig(fail_on=HIGH) escalates a HIGH-severity
    finding to policy-violation (default: warn)."""
    engine_finding = Finding(
        id="vuln:GHSA-xxxx:foo@1.0.0",
        axis=AXIS_VULNERABILITY,
        message="foo: GHSA-xxxx",
        subject="foo",
        severity=Severity(tier=SeverityTier.HIGH, raw=None),
    )
    result = EngineResult(
        findings=(engine_finding,), errors=(), coverage=(), axis=AXIS_VULNERABILITY
    )
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    config = EffectiveConfig(fail_on=SeverityTier.HIGH)
    _, rungs = DefaultPolicy(config).evaluate(inventory, [result])
    assert (
        Status.POLICY_VIOLATION,
        StatusDriver(axis=AXIS_VULNERABILITY, finding_id=engine_finding.id),
    ) in rungs


# --- Story 6.5: license/currency escalation threaded through evaluate --------


def _license_denied_result():
    finding = Finding(
        id="license:GPL-3.0-only:foo@1.0.0",
        axis=AXIS_LICENSE,
        message="foo: license 'GPL-3.0-only' is denied",
        subject="foo",
        severity=None,
        license=LicenseInfo(
            expression="GPL-3.0-only", family="GPL3", verdict=LicenseVerdict.DENIED
        ),
    )
    return finding, EngineResult(
        findings=(finding,), errors=(), coverage=(), axis=AXIS_LICENSE
    )


def test_default_policy_with_deny_licenses_escalates_a_denied_finding(
    component_factory,
):
    """Story 6.5: EffectiveConfig(deny_licenses=…) makes config.license_policy
    escalate, and DefaultPolicy threads it into license_rung -- a denied
    finding feeds policy-violation (default: warn)."""
    finding, result = _license_denied_result()
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    config = EffectiveConfig(deny_licenses=("GPL-3.0-only",))
    _, rungs = DefaultPolicy(config).evaluate(inventory, [result])
    assert (
        Status.POLICY_VIOLATION,
        StatusDriver(axis=AXIS_LICENSE, finding_id=finding.id),
    ) in rungs


def test_default_policy_unconfigured_keeps_a_denied_finding_at_warn(component_factory):
    """The two-mode contrast: with no license flag, the SAME denied finding
    feeds warn (the axis is invisible-as-enforcement but honest)."""
    finding, result = _license_denied_result()
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    _, rungs = DefaultPolicy().evaluate(inventory, [result])
    assert (
        Status.WARN,
        StatusDriver(axis=AXIS_LICENSE, finding_id=finding.id),
    ) in rungs


def _currency_eol_result():
    finding = Finding(
        id="currency:eol:foo@1.0.0",
        axis=AXIS_CURRENCY,
        message="foo: reached end-of-life 2020-01-01 (endoflife-date)",
        subject="foo",
        severity=None,
        currency=CurrencyInfo(
            verdict=CurrencyVerdict.EOL,
            latest="2.0",
            lag=3,
            eol_date="2020-01-01",
            tier="endoflife-date",
        ),
    )
    return finding, EngineResult(
        findings=(finding,), errors=(), coverage=(), axis=AXIS_CURRENCY
    )


def test_default_policy_with_fail_on_eol_escalates_an_eol_finding(component_factory):
    """Story 6.5: EffectiveConfig(fail_on_eol=True) makes config.
    currency_policy escalate, threaded into currency_rung -- an eol finding
    feeds policy-violation (default: warn)."""
    finding, result = _currency_eol_result()
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    config = EffectiveConfig(fail_on_eol=True)
    _, rungs = DefaultPolicy(config).evaluate(inventory, [result])
    assert (
        Status.POLICY_VIOLATION,
        StatusDriver(axis=AXIS_CURRENCY, finding_id=finding.id),
    ) in rungs


def test_default_policy_unconfigured_keeps_an_eol_finding_at_warn(component_factory):
    finding, result = _currency_eol_result()
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    _, rungs = DefaultPolicy().evaluate(inventory, [result])
    assert (
        Status.WARN,
        StatusDriver(axis=AXIS_CURRENCY, finding_id=finding.id),
    ) in rungs


def _currency_over_lag_result():
    finding = Finding(
        id="currency:over-lag:foo@1.0.0",
        axis=AXIS_CURRENCY,
        message="foo: 5 release(s) behind latest '6.0' (endoflife-date)",
        subject="foo",
        severity=None,
        currency=CurrencyInfo(
            verdict=CurrencyVerdict.SUPPORTED,
            latest="6.0",
            lag=5,
            eol_date="2099-01-01",
            tier="endoflife-date",
        ),
    )
    return finding, EngineResult(
        findings=(finding,), errors=(), coverage=(), axis=AXIS_CURRENCY
    )


def test_default_policy_with_max_lag_escalates_an_over_threshold_over_lag(
    component_factory,
):
    """Story 6.5: EffectiveConfig(max_lag=…) threads config.max_lag into
    currency_rung's numeric check -- an over-lag finding whose lag EXCEEDS
    the threshold feeds policy-violation. Pins the max_lag=self._config.
    max_lag threading itself (the table threading alone cannot prove it:
    over-lag never consults the table)."""
    finding, result = _currency_over_lag_result()
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    config = EffectiveConfig(max_lag=3)
    _, rungs = DefaultPolicy(config).evaluate(inventory, [result])
    assert (
        Status.POLICY_VIOLATION,
        StatusDriver(axis=AXIS_CURRENCY, finding_id=finding.id),
    ) in rungs


def test_default_policy_with_max_lag_keeps_an_under_threshold_over_lag_at_warn(
    component_factory,
):
    """The contrasting half: lag at or below the configured threshold stays
    warn (visible, not blocking) even though max_lag activates the gate."""
    finding, result = _currency_over_lag_result()
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    config = EffectiveConfig(max_lag=8)
    _, rungs = DefaultPolicy(config).evaluate(inventory, [result])
    assert (
        Status.WARN,
        StatusDriver(axis=AXIS_CURRENCY, finding_id=finding.id),
    ) in rungs


def _vuln_epss_result(score: float) -> tuple[Finding, EngineResult]:
    finding = Finding(
        id="vuln:PDOS-KEV-FIXTURE-0001:pdos-kev-fixture@1.0.0",
        axis=AXIS_VULNERABILITY,
        message="pdos-kev-fixture: PDOS-KEV-FIXTURE-0001 (severity medium)",
        subject="pdos-kev-fixture",
        severity=Severity(tier=SeverityTier.MEDIUM, raw=None),
        epss=Epss(score=score, percentile=0.9),
    )
    return finding, EngineResult(
        findings=(finding,), errors=(), coverage=(), axis=AXIS_VULNERABILITY
    )


def test_default_policy_with_min_epss_escalates_an_at_or_above_threshold_finding(
    component_factory,
):
    """Story 6.7: EffectiveConfig(min_epss=…) threads config.min_epss into
    vuln_rung's threshold check -- a MEDIUM-tier (normally warn) finding
    whose EPSS score is at or above the threshold feeds policy-violation.
    Pins the min_epss=self._config.min_epss threading itself."""
    finding, result = _vuln_epss_result(score=0.7)
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    config = EffectiveConfig(min_epss=0.5)
    _, rungs = DefaultPolicy(config).evaluate(inventory, [result])
    assert (
        Status.POLICY_VIOLATION,
        StatusDriver(axis=AXIS_VULNERABILITY, finding_id=finding.id),
    ) in rungs


def test_default_policy_with_min_epss_keeps_a_below_threshold_finding_at_warn(
    component_factory,
):
    """The contrasting half: a score below the configured threshold stays
    warn (visible, not blocking) even though min_epss activates the gate."""
    finding, result = _vuln_epss_result(score=0.2)
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    config = EffectiveConfig(min_epss=0.5)
    _, rungs = DefaultPolicy(config).evaluate(inventory, [result])
    assert (
        Status.WARN,
        StatusDriver(axis=AXIS_VULNERABILITY, finding_id=finding.id),
    ) in rungs


def test_default_policy_unconfigured_min_epss_never_escalates(component_factory):
    """The two-mode contrast: with no --min-epss flag, the SAME high-scoring
    finding feeds warn (default config.min_epss is None)."""
    finding, result = _vuln_epss_result(score=0.99)
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    _, rungs = DefaultPolicy().evaluate(inventory, [result])
    assert (
        Status.WARN,
        StatusDriver(axis=AXIS_VULNERABILITY, finding_id=finding.id),
    ) in rungs


def test_default_policy_with_dep001_block_confidence_likely_keeps_dep001_blocking(
    component_factory,
):
    """Story 3.1: EffectiveConfig(dep001_block_confidence="likely") keeps
    DEP001 at policy-violation with a "likely"-confidence component present
    (the default "verified" threshold downgrades it to warn instead)."""
    engine_finding = Finding(
        id="hygiene:DEP001:leftpad",
        axis=AXIS_HYGIENE,
        message="missing",
        subject="leftpad",
        severity=None,
    )
    result = EngineResult(
        findings=(engine_finding,), errors=(), coverage=(), axis=AXIS_HYGIENE
    )
    inventory = make_inventory(
        component_factory(name="pytorch", version="2.1.0", mapping_confidence="likely")
    )
    config = EffectiveConfig(dep001_block_confidence="likely")
    _, rungs = DefaultPolicy(config).evaluate(inventory, [result])
    assert (
        Status.POLICY_VIOLATION,
        StatusDriver(axis=AXIS_HYGIENE, finding_id="hygiene:DEP001:leftpad"),
    ) in rungs


def test_default_policy_default_confidence_threshold_downgrades_on_a_likely_component(
    component_factory,
):
    """The default (dep001_block_confidence="verified") reproduces today's
    exact behavior: a "likely"-confidence component anywhere downgrades
    DEP001 to warn."""
    engine_finding = Finding(
        id="hygiene:DEP001:leftpad",
        axis=AXIS_HYGIENE,
        message="missing",
        subject="leftpad",
        severity=None,
    )
    result = EngineResult(
        findings=(engine_finding,), errors=(), coverage=(), axis=AXIS_HYGIENE
    )
    inventory = make_inventory(
        component_factory(name="pytorch", version="2.1.0", mapping_confidence="likely")
    )
    _, rungs = DefaultPolicy().evaluate(inventory, [result])
    assert (
        Status.WARN,
        StatusDriver(axis=AXIS_HYGIENE, finding_id="hygiene:DEP001:leftpad"),
    ) in rungs


def test_hypothetical_future_axis_still_hits_the_backstop(component_factory):
    """Now that hygiene, vulnerability, AND license (Story 6.2) all have real
    mappings, the generic backstop is reachable only by a finding whose axis
    is none of the three — a hypothetical future axis (e.g. a SAST axis;
    see ``report.py``'s own "a further SAST axis would still land
    additively" precedent) with no mapping of its own yet. Without this test
    that branch would be completely unexercised by the suite (a regression
    there, e.g. mapping it to clean, would go undetected)."""
    engine_finding = Finding(
        id="indeterminate:sast-issue:foo",
        axis="sast",  # AXIS_HYGIENE/AXIS_VULNERABILITY/AXIS_LICENSE is an
        # OPEN string mechanism (see models.py) — a future axis lands
        # additively.
        message="a hypothetical future axis",
        subject="foo",
        severity=None,
    )
    result = EngineResult(findings=(engine_finding,), errors=(), coverage=(), axis="sast")
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    findings, rungs = DefaultPolicy().evaluate(inventory, [result])
    assert engine_finding in findings
    assert (
        Status.INDETERMINATE,
        StatusDriver(axis="sast", finding_id=engine_finding.id),
    ) in rungs


def test_findings_only_engine_result_never_feeds_only_clean(component_factory):
    """A findings-only EngineResult (no errors) over an otherwise-clean
    inventory must produce at least one NON-CLEAN rung — a finding-carrying
    report composing clean/exit 0 is the exact false-green class C0
    forbids, and ``register_engine`` makes this input publicly reachable
    today (the gap both prior review passes documented at the seam)."""
    engine_finding = Finding(
        id="hygiene:DEP002:requests",
        axis=AXIS_HYGIENE,
        message="unused dependency",
        subject="requests",
        severity=None,
    )
    result = EngineResult(findings=(engine_finding,), errors=(), coverage=(), axis=AXIS_HYGIENE)
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    findings, rungs = DefaultPolicy().evaluate(inventory, [result])
    assert engine_finding in findings
    non_clean = [
        (status, driver) for status, driver in rungs if status is not Status.CLEAN
    ]
    assert non_clean, "findings-only engine result fed only clean rungs"
    assert all(driver is not None for _, driver in non_clean)
    assert any(
        driver.finding_id == engine_finding.id for _, driver in non_clean
    )


def test_assessable_exact_component_feeds_a_clean_rung(component_factory):
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    findings, rungs = DefaultPolicy().evaluate(inventory, [EMPTY_RESULT])
    assert findings == ()
    assert rungs == ((Status.CLEAN, None),)


def test_assessable_weak_match_level_feeds_a_driver_carrying_rung(
    component_factory,
):
    """An assessable (no withhold reason) component whose match level cannot
    prove cleanliness must still land non-clean WITH a driver."""
    inventory = make_inventory(
        component_factory(
            name="weak",
            version="1.0",
            cve_match_level=CveMatchLevel.NAME_ONLY,
        )
    )
    findings, rungs = DefaultPolicy().evaluate(inventory, [EMPTY_RESULT])
    assert len(findings) == 1
    assert findings[0].id == "indeterminate:name-only:weak@1.0"
    ((status, driver),) = rungs
    assert status is Status.INDETERMINATE
    assert driver is not None
    assert driver.finding_id == "indeterminate:name-only:weak@1.0"


def test_every_non_clean_rung_carries_a_driver(component_factory):
    inventory = make_inventory(
        component_factory(name="pinned", version="1.0.0"),
        component_factory(
            name="bare",
            version=None,
            indeterminate_reason=WithholdReason.NO_VERSION,
        ),
        component_factory(
            name="weak", version="1.0", cve_match_level=CveMatchLevel.NAME_ONLY
        ),
    )
    _, rungs = DefaultPolicy().evaluate(inventory, [EMPTY_RESULT])
    assert len(rungs) == 3
    for status, driver in rungs:
        if status is not Status.CLEAN:
            assert driver is not None, f"driverless non-clean rung: {status}"


def test_derived_id_colliding_with_an_engine_finding_is_not_duplicated(
    component_factory,
):
    """Finding-id uniqueness is a report construction invariant: when an
    engine already emitted the id, the rung's driver references it by id
    instead of duplicating the finding."""
    engine_finding = Finding(
        id="indeterminate:no-version:leftpad@unspecified",
        axis=AXIS_VULNERABILITY,
        message="engine-side withhold record",
        subject="leftpad",
        severity=None,
    )
    result = EngineResult(findings=(engine_finding,), errors=(), coverage=(), axis=AXIS_VULNERABILITY)
    inventory = make_inventory(
        component_factory(
            name="leftpad",
            version=None,
            indeterminate_reason=WithholdReason.NO_VERSION,
        )
    )
    findings, rungs = DefaultPolicy().evaluate(inventory, [result])
    assert [f.id for f in findings] == ["indeterminate:no-version:leftpad@unspecified"]
    assert findings[0].message == "engine-side withhold record"
    assert rungs[0][1].finding_id == engine_finding.id


def test_empty_inventory_feeds_nothing():
    findings, rungs = DefaultPolicy().evaluate(make_inventory(), [EMPTY_RESULT])
    assert findings == ()
    assert rungs == ()


# --- engine errors feed the verdict (P1) --------------------------------------


def test_engine_error_records_feed_error_rungs():
    """An engine ErrorRecord must reach the verdict: one (error, driver)
    rung per record, driver id in the error:<kind>:<owner> grammar, and the
    driver's axis is the PRODUCING engine's own axis (Story 1.7) — not a
    blanket vulnerability default (this result's owner is "deptry", a
    hygiene-axis engine)."""
    record = ErrorRecord(
        kind=ErrorKind.ENGINE_EXECUTION_FAILED, owner="deptry", message="boom"
    )
    result = EngineResult(
        findings=(), errors=(record,), coverage=(), axis=AXIS_HYGIENE
    )
    findings, rungs = DefaultPolicy().evaluate(make_inventory(), [result])
    assert findings == ()
    ((status, driver),) = rungs
    assert status is Status.ERROR
    assert driver == StatusDriver(
        axis=AXIS_HYGIENE,
        finding_id="error:engine-execution-failed:deptry",
    )


def test_engine_error_rungs_ride_alongside_component_rungs(component_factory):
    """The error rung's driver carries the producing engine's own axis
    (this result's owner is "osv", a vulnerability-axis engine) — not a
    blanket vulnerability default asserted merely by coincidence."""
    record = ErrorRecord(
        kind=ErrorKind.ENGINE_TIMEOUT, owner="osv", message="timed out"
    )
    result = EngineResult(
        findings=(), errors=(record,), coverage=(), axis=AXIS_VULNERABILITY
    )
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    _, rungs = DefaultPolicy().evaluate(inventory, [result])
    assert (Status.CLEAN, None) in rungs
    error_rung = next((r for r in rungs if r[0] is Status.ERROR), None)
    assert error_rung is not None
    assert error_rung[1] is not None
    assert error_rung[1].axis == AXIS_VULNERABILITY


# --- engine-vs-engine duplicate ids (P16) -------------------------------------


def test_engine_vs_engine_duplicate_ids_dedupe_first_wins():
    """Duplicate ids ACROSS EngineResults must never reach the report (a
    construction crash): the first occurrence in engine-registration order
    wins, deterministically."""
    first = Finding(
        id="hygiene:DEP002:leftpad",
        axis=AXIS_HYGIENE,
        message="from engine one",
        subject="leftpad",
        severity=None,
    )
    second = Finding(
        id="hygiene:DEP002:leftpad",
        axis=AXIS_HYGIENE,
        message="from engine two",
        subject="leftpad",
        severity=None,
    )
    results = [
        EngineResult(findings=(first,), errors=(), coverage=(), axis=AXIS_HYGIENE),
        EngineResult(findings=(second,), errors=(), coverage=(), axis=AXIS_HYGIENE),
    ]
    findings, _ = DefaultPolicy().evaluate(make_inventory(), results)
    assert [f.id for f in findings] == ["hygiene:DEP002:leftpad"]
    assert findings[0].message == "from engine one"


# --- coverage booleans gate the clean rung (P6) --------------------------------


def test_unmatchable_component_without_reason_never_feeds_clean(
    component_factory,
):
    """vuln_matchable=False with indeterminate_reason=None is constructible
    by future producers — it must derive indeterminate, never clean."""
    inventory = make_inventory(
        component_factory(name="oddball", version="1.0.0", vuln_matchable=False)
    )
    findings, rungs = DefaultPolicy().evaluate(inventory, [EMPTY_RESULT])
    assert [f.id for f in findings] == ["indeterminate:unmatchable:oddball@1.0.0"]
    assert findings[0].axis == AXIS_VULNERABILITY
    ((status, driver),) = rungs
    assert status is Status.INDETERMINATE
    assert driver == StatusDriver(
        axis=AXIS_VULNERABILITY, finding_id="indeterminate:unmatchable:oddball@1.0.0"
    )


def test_uncovered_component_without_reason_never_feeds_clean(
    component_factory,
):
    inventory = make_inventory(
        component_factory(name="oddball", version="1.0.0", hygiene_covered=False)
    )
    findings, rungs = DefaultPolicy().evaluate(inventory, [EMPTY_RESULT])
    assert [f.id for f in findings] == ["indeterminate:uncovered:oddball@1.0.0"]
    assert findings[0].axis == AXIS_HYGIENE
    ((status, driver),) = rungs
    assert status is Status.INDETERMINATE
    assert driver == StatusDriver(
        axis=AXIS_HYGIENE, finding_id="indeterminate:uncovered:oddball@1.0.0"
    )


def test_doubly_deficient_component_derives_both_axis_findings(
    component_factory,
):
    inventory = make_inventory(
        component_factory(
            name="oddball",
            version="1.0.0",
            vuln_matchable=False,
            hygiene_covered=False,
        )
    )
    findings, rungs = DefaultPolicy().evaluate(inventory, [EMPTY_RESULT])
    assert sorted(f.id for f in findings) == [
        "indeterminate:uncovered:oddball@1.0.0",
        "indeterminate:unmatchable:oddball@1.0.0",
    ]
    assert len(rungs) == 2
    assert all(status is Status.INDETERMINATE for status, _ in rungs)
    assert all(driver is not None for _, driver in rungs)


# --- Story 6.1: license/currency coverage (axis-qualified tokens) --------------


def test_license_uncovered_component_derives_axis_qualified_finding(
    component_factory,
):
    """A license_covered=False component (producer path; inert in 6.1's own
    fixtures where it defaults True) derives an axis-qualified
    ``uncovered-license`` finding on AXIS_LICENSE."""
    inventory = make_inventory(
        component_factory(name="oddball", version="1.0.0", license_covered=False)
    )
    findings, rungs = DefaultPolicy().evaluate(inventory, [EMPTY_RESULT])
    assert [f.id for f in findings] == ["indeterminate:uncovered-license:oddball@1.0.0"]
    assert findings[0].axis == AXIS_LICENSE
    ((status, driver),) = rungs
    assert status is Status.INDETERMINATE
    assert driver == StatusDriver(
        axis=AXIS_LICENSE, finding_id="indeterminate:uncovered-license:oddball@1.0.0"
    )


def test_currency_uncovered_component_derives_axis_qualified_finding(
    component_factory,
):
    inventory = make_inventory(
        component_factory(name="oddball", version="1.0.0", currency_covered=False)
    )
    findings, rungs = DefaultPolicy().evaluate(inventory, [EMPTY_RESULT])
    assert [f.id for f in findings] == ["indeterminate:uncovered-currency:oddball@1.0.0"]
    assert findings[0].axis == AXIS_CURRENCY
    ((status, driver),) = rungs
    assert status is Status.INDETERMINATE
    assert driver == StatusDriver(
        axis=AXIS_CURRENCY, finding_id="indeterminate:uncovered-currency:oddball@1.0.0"
    )


def test_triple_uncovered_component_keeps_three_distinct_axis_ids(
    component_factory,
):
    """The three uncovered tokens MUST stay distinct — a bare "uncovered"
    for all three axes would collide onto one id and silently swallow two
    axes via the id-dedupe. Axis-qualifying license/currency closes it."""
    inventory = make_inventory(
        component_factory(
            name="oddball",
            version="1.0.0",
            hygiene_covered=False,
            license_covered=False,
            currency_covered=False,
        )
    )
    findings, rungs = DefaultPolicy().evaluate(inventory, [EMPTY_RESULT])
    by_id = {f.id: f.axis for f in findings}
    assert by_id == {
        "indeterminate:uncovered:oddball@1.0.0": AXIS_HYGIENE,
        "indeterminate:uncovered-license:oddball@1.0.0": AXIS_LICENSE,
        "indeterminate:uncovered-currency:oddball@1.0.0": AXIS_CURRENCY,
    }
    assert len(rungs) == 3
    assert all(status is Status.INDETERMINATE for status, _ in rungs)


def test_fully_covered_component_derives_no_uncovered_findings(component_factory):
    """The default (6.1-era) component is license/currency-covered=True, so
    the new blocks stay inert — behavior-neutral."""
    inventory = make_inventory(component_factory(name="ok", version="1.0.0"))
    findings, rungs = DefaultPolicy().evaluate(inventory, [EMPTY_RESULT])
    assert findings == ()
    assert rungs == ((Status.CLEAN, None),)


# --- driver axis mirrors the referenced finding (P10) --------------------------


def test_reused_engine_finding_id_keeps_that_findings_axis(component_factory):
    """When the derived id already exists among engine findings, the rung
    driver's axis is THAT finding's axis — never hardcoded vulnerability."""
    engine_finding = Finding(
        id="indeterminate:no-version:leftpad@unspecified",
        axis=AXIS_HYGIENE,  # the indeterminate: id family is axis-free
        message="engine-side withhold record",
        subject="leftpad",
        severity=None,
    )
    result = EngineResult(findings=(engine_finding,), errors=(), coverage=(), axis=AXIS_HYGIENE)
    inventory = make_inventory(
        component_factory(
            name="leftpad",
            version=None,
            indeterminate_reason=WithholdReason.NO_VERSION,
        )
    )
    _, rungs = DefaultPolicy().evaluate(inventory, [result])
    # Two rungs reference the one finding: the engine finding's backstop
    # rung and the withheld component's rung reusing the id — BOTH drivers
    # must carry THAT finding's axis.
    assert len(rungs) == 2
    for _, driver in rungs:
        assert driver is not None
        assert driver.finding_id == engine_finding.id
        assert driver.axis == AXIS_HYGIENE


# --- id sanitization (P2) ------------------------------------------------------


def test_component_name_with_newline_sanitizes_in_the_id(component_factory):
    """A name embedding a newline must not crash Finding construction: the
    id embeds %0A, the subject keeps the raw name."""
    inventory = make_inventory(
        component_factory(
            name="foo\nbar",
            version=None,
            indeterminate_reason=WithholdReason.NO_VERSION,
        )
    )
    findings, rungs = DefaultPolicy().evaluate(inventory, [EMPTY_RESULT])
    assert findings[0].id == "indeterminate:no-version:foo%0Abar@unspecified"
    assert findings[0].subject == "foo\nbar"
    assert rungs[0][1].finding_id == "indeterminate:no-version:foo%0Abar@unspecified"


def test_component_name_with_crlf_sanitizes_deterministically(
    component_factory,
):
    inventory = make_inventory(
        component_factory(
            name="bad\r\nname",
            version=None,
            indeterminate_reason=WithholdReason.NO_VERSION,
        )
    )
    findings, _ = DefaultPolicy().evaluate(inventory, [EMPTY_RESULT])
    assert findings[0].id == "indeterminate:no-version:bad%0D%0Aname@unspecified"
    assert findings[0].subject == "bad\r\nname"


def test_sanitization_is_injective_for_literal_escape_sequences(
    component_factory,
):
    """'foo\\nbar' and a literal 'foo%0Abar' are DISTINCT components and
    must mint distinct finding ids (% escapes itself first) — otherwise
    the second silently dedupes into the first and waiving one waives
    both."""
    inventory = make_inventory(
        component_factory(
            name="foo\nbar",
            version=None,
            pypi_identity=None,
            indeterminate_reason=WithholdReason.NO_VERSION,
        ),
        component_factory(
            name="foo%0Abar",
            version=None,
            pypi_identity=None,
            indeterminate_reason=WithholdReason.NO_VERSION,
        ),
    )
    findings, rungs = DefaultPolicy().evaluate(inventory, [EMPTY_RESULT])
    assert sorted(f.id for f in findings) == [
        "indeterminate:no-version:foo%0Abar@unspecified",
        "indeterminate:no-version:foo%250Abar@unspecified",
    ]
    assert len(rungs) == 2


def test_colon_in_component_name_sanitizes_in_the_id(component_factory):
    """The id grammar is colon-delimited: a raw-malformed name embedding a
    colon must not smuggle extra delimiters into the id."""
    inventory = make_inventory(
        component_factory(
            name="odd:name",
            version=None,
            pypi_identity=None,
            indeterminate_reason=WithholdReason.NO_VERSION,
        )
    )
    findings, _ = DefaultPolicy().evaluate(inventory, [EMPTY_RESULT])
    assert findings[0].id == "indeterminate:no-version:odd%3Aname@unspecified"
    assert findings[0].subject == "odd:name"


def test_empty_growable_reason_token_degrades_never_crashes(component_factory):
    """An empty growable-enum token from a future producer must degrade to
    a grammar-valid id ('unspecified'), never crash Finding construction
    (the frozen Component deliberately does not coerce growable enums)."""
    inventory = make_inventory(
        component_factory(
            name="oddball",
            version=None,
            pypi_identity=None,
            indeterminate_reason="",  # constructible: growable, uncoerced
        )
    )
    findings, rungs = DefaultPolicy().evaluate(inventory, [EMPTY_RESULT])
    assert findings[0].id == "indeterminate:unspecified:oddball@unspecified"
    assert len(rungs) == 1
    assert rungs[0][0] is Status.INDETERMINATE


# --- hygiene axis is independent of the withhold reason ------------------------


def test_withheld_and_uncovered_component_surfaces_both_axes(
    component_factory,
):
    """The RAW_MALFORMED production path: indeterminate_reason set AND
    hygiene_covered=False. The withhold reason describes only the
    vulnerability axis — the hygiene axis must NOT go silent about its own
    deficiency."""
    inventory = make_inventory(
        component_factory(
            name="junk",
            version=None,
            pypi_identity=None,
            hygiene_covered=False,
            indeterminate_reason=WithholdReason.NO_VERSION,
        )
    )
    findings, rungs = DefaultPolicy().evaluate(inventory, [EMPTY_RESULT])
    by_id = {f.id: f for f in findings}
    assert sorted(by_id) == [
        "indeterminate:no-version:junk@unspecified",
        "indeterminate:uncovered:junk@unspecified",
    ]
    assert by_id["indeterminate:no-version:junk@unspecified"].axis == AXIS_VULNERABILITY
    assert by_id["indeterminate:uncovered:junk@unspecified"].axis == AXIS_HYGIENE
    assert len(rungs) == 2
    assert all(status is Status.INDETERMINATE for status, _ in rungs)
    assert all(driver is not None for _, driver in rungs)


# --- engine-error driver ids are sanitized --------------------------------------


def test_engine_error_owner_segment_is_sanitized():
    """A future engine owner embedding a newline/colon must not produce a
    multi-line or extra-delimited driver id — same sanitization as every
    component-derived segment."""
    record = ErrorRecord(
        kind=ErrorKind.ENGINE_EXECUTION_FAILED,
        owner="dep\ntry:x",
        message="boom",
    )
    result = EngineResult(
        findings=(), errors=(record,), coverage=(), axis=AXIS_HYGIENE
    )
    _, rungs = DefaultPolicy().evaluate(make_inventory(), [result])
    ((_, driver),) = rungs
    assert driver is not None
    assert driver.axis == AXIS_HYGIENE
    assert driver.finding_id == (
        "error:engine-execution-failed:dep%0Atry%3Ax"
    )
    assert "\n" not in driver.finding_id
