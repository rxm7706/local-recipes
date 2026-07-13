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

from python_deptry_osv_scanner import engines as engines_module
from python_deptry_osv_scanner.engines import (
    NullEngine,
    register_engine,
    registered_engines,
)
from python_deptry_osv_scanner.interfaces import (
    DefaultPolicy,
    Engine,
    EngineResult,
    Extractor,
    Policy,
    Router,
    VulnStrategy,
)
from python_deptry_osv_scanner.inventory import ResolvedInventory, merge_components
from python_deptry_osv_scanner.models import (
    AXIS_HYGIENE,
    AXIS_VULNERABILITY,
    CveMatchLevel,
    Ecosystem,
    ErrorKind,
    ErrorRecord,
    Finding,
    ScannedManifest,
    Status,
    StatusDriver,
    WithholdReason,
)

MANIFEST = ScannedManifest(path="pyproject.toml", kind="pyproject.toml")
EMPTY_RESULT = EngineResult(findings=(), errors=(), coverage=())


def make_inventory(*components) -> ResolvedInventory:
    return ResolvedInventory(
        components=merge_components(components),
        resolved_scan_set=(MANIFEST,),
    )


# --- registry + null engine --------------------------------------------------


def test_registry_has_exactly_the_null_engine():
    engines = registered_engines()
    assert len(engines) == 1
    assert isinstance(engines[0], NullEngine)
    assert engines[0].name == "null"


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
    assert names == ["null", "dummy"]


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
    assert finding.id == "indeterminate:no-version:leftpad"
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
    assert findings[0].id == "indeterminate:range-only:requests"


def test_engine_findings_pass_through(component_factory):
    engine_finding = Finding(
        id="hygiene:DEP002:leftpad",
        axis=AXIS_HYGIENE,
        message="unused dependency",
        subject="leftpad",
        severity=None,
    )
    result = EngineResult(findings=(engine_finding,), errors=(), coverage=())
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    findings, _ = DefaultPolicy().evaluate(inventory, [result])
    assert engine_finding in findings


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
    assert findings[0].id == "indeterminate:name-only:weak"
    ((status, driver),) = rungs
    assert status is Status.INDETERMINATE
    assert driver is not None
    assert driver.finding_id == "indeterminate:name-only:weak"


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
        id="indeterminate:no-version:leftpad",
        axis=AXIS_VULNERABILITY,
        message="engine-side withhold record",
        subject="leftpad",
        severity=None,
    )
    result = EngineResult(findings=(engine_finding,), errors=(), coverage=())
    inventory = make_inventory(
        component_factory(
            name="leftpad",
            version=None,
            indeterminate_reason=WithholdReason.NO_VERSION,
        )
    )
    findings, rungs = DefaultPolicy().evaluate(inventory, [result])
    assert [f.id for f in findings] == ["indeterminate:no-version:leftpad"]
    assert findings[0].message == "engine-side withhold record"
    assert rungs[0][1].finding_id == engine_finding.id


def test_empty_inventory_feeds_nothing():
    findings, rungs = DefaultPolicy().evaluate(make_inventory(), [EMPTY_RESULT])
    assert findings == ()
    assert rungs == ()


# --- engine errors feed the verdict (P1) --------------------------------------


def test_engine_error_records_feed_error_rungs():
    """An engine ErrorRecord must reach the verdict: one (error, driver)
    rung per record, driver id in the error:<kind>:<owner> grammar."""
    record = ErrorRecord(
        kind=ErrorKind.ENGINE_EXECUTION_FAILED, owner="deptry", message="boom"
    )
    result = EngineResult(findings=(), errors=(record,), coverage=())
    findings, rungs = DefaultPolicy().evaluate(make_inventory(), [result])
    assert findings == ()
    ((status, driver),) = rungs
    assert status is Status.ERROR
    assert driver == StatusDriver(
        axis=AXIS_VULNERABILITY,
        finding_id="error:engine-execution-failed:deptry",
    )


def test_engine_error_rungs_ride_alongside_component_rungs(component_factory):
    record = ErrorRecord(
        kind=ErrorKind.ENGINE_TIMEOUT, owner="osv", message="timed out"
    )
    result = EngineResult(findings=(), errors=(record,), coverage=())
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    _, rungs = DefaultPolicy().evaluate(inventory, [result])
    assert (Status.CLEAN, None) in rungs
    assert any(status is Status.ERROR for status, _ in rungs)


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
        EngineResult(findings=(first,), errors=(), coverage=()),
        EngineResult(findings=(second,), errors=(), coverage=()),
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
    assert [f.id for f in findings] == ["indeterminate:unmatchable:oddball"]
    assert findings[0].axis == AXIS_VULNERABILITY
    ((status, driver),) = rungs
    assert status is Status.INDETERMINATE
    assert driver == StatusDriver(
        axis=AXIS_VULNERABILITY, finding_id="indeterminate:unmatchable:oddball"
    )


def test_uncovered_component_without_reason_never_feeds_clean(
    component_factory,
):
    inventory = make_inventory(
        component_factory(name="oddball", version="1.0.0", hygiene_covered=False)
    )
    findings, rungs = DefaultPolicy().evaluate(inventory, [EMPTY_RESULT])
    assert [f.id for f in findings] == ["indeterminate:uncovered:oddball"]
    assert findings[0].axis == AXIS_HYGIENE
    ((status, driver),) = rungs
    assert status is Status.INDETERMINATE
    assert driver == StatusDriver(
        axis=AXIS_HYGIENE, finding_id="indeterminate:uncovered:oddball"
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
        "indeterminate:uncovered:oddball",
        "indeterminate:unmatchable:oddball",
    ]
    assert len(rungs) == 2
    assert all(status is Status.INDETERMINATE for status, _ in rungs)
    assert all(driver is not None for _, driver in rungs)


# --- driver axis mirrors the referenced finding (P10) --------------------------


def test_reused_engine_finding_id_keeps_that_findings_axis(component_factory):
    """When the derived id already exists among engine findings, the rung
    driver's axis is THAT finding's axis — never hardcoded vulnerability."""
    engine_finding = Finding(
        id="indeterminate:no-version:leftpad",
        axis=AXIS_HYGIENE,  # the indeterminate: id family is axis-free
        message="engine-side withhold record",
        subject="leftpad",
        severity=None,
    )
    result = EngineResult(findings=(engine_finding,), errors=(), coverage=())
    inventory = make_inventory(
        component_factory(
            name="leftpad",
            version=None,
            indeterminate_reason=WithholdReason.NO_VERSION,
        )
    )
    _, rungs = DefaultPolicy().evaluate(inventory, [result])
    ((_, driver),) = rungs
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
    assert findings[0].id == "indeterminate:no-version:foo%0Abar"
    assert findings[0].subject == "foo\nbar"
    assert rungs[0][1].finding_id == "indeterminate:no-version:foo%0Abar"


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
    assert findings[0].id == "indeterminate:no-version:bad%0D%0Aname"
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
        "indeterminate:no-version:foo%0Abar",
        "indeterminate:no-version:foo%250Abar",
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
    assert findings[0].id == "indeterminate:no-version:odd%3Aname"
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
    assert findings[0].id == "indeterminate:unspecified:oddball"
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
        "indeterminate:no-version:junk",
        "indeterminate:uncovered:junk",
    ]
    assert by_id["indeterminate:no-version:junk"].axis == AXIS_VULNERABILITY
    assert by_id["indeterminate:uncovered:junk"].axis == AXIS_HYGIENE
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
    result = EngineResult(findings=(), errors=(record,), coverage=())
    _, rungs = DefaultPolicy().evaluate(make_inventory(), [result])
    ((_, driver),) = rungs
    assert driver is not None
    assert driver.finding_id == (
        "error:engine-execution-failed:dep%0Atry%3Ax"
    )
    assert "\n" not in driver.finding_id
