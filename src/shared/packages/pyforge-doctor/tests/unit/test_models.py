"""Unit tests for ``pyforge.doctor.models`` (Story 1.1) — covers every row of
the spec's I/O & Edge-Case Matrix for the Finding/DoctorReport contract,
plus schema validation of the packaged ``data/report-schema.json`` against
the two minimal fixtures and against ``DoctorReport.to_json_dict()`` output.
"""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

import jsonschema
import pytest
from pyforge.core.report import BASE_ENVELOPE_SCHEMA, compose

from pyforge.doctor.models import (
    DoctorReport,
    DoctorStatus,
    Finding,
    Partition,
    Prescription,
    Source,
)

_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _schema() -> dict:
    schema_text = resources.files("pyforge.doctor").joinpath("data", "report-schema.json").read_text(encoding="utf-8")
    return json.loads(schema_text)


def _fixture(name: str) -> dict:
    return json.loads((_FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _finding(status: DoctorStatus = DoctorStatus.OK) -> Finding:
    return Finding(
        source=Source.ENV_HYGIENE,
        check="x",
        status=status,
        message="m",
        evidence={},
    )


# --- Finding: valid / unknown status / unknown source ---------------------


def test_valid_finding_constructs():
    finding = Finding(
        source=Source.ENV_HYGIENE,
        check="x",
        status=DoctorStatus.WARN,
        message="m",
        evidence={},
    )
    assert finding.source is Source.ENV_HYGIENE
    assert finding.status is DoctorStatus.WARN


def test_finding_accepts_raw_string_source_and_status():
    finding = Finding(source="warden-doctor", check="x", status="ok", message="m", evidence={})
    assert finding.source is Source.WARDEN_DOCTOR
    assert finding.status is DoctorStatus.OK


def test_finding_unknown_status_rejected():
    with pytest.raises(ValueError):
        Finding(
            source=Source.ENV_HYGIENE,
            check="x",
            status="critical",
            message="m",
            evidence={},
        )


def test_finding_unknown_source_rejected():
    with pytest.raises(ValueError):
        Finding(
            source="not-a-source",
            check="x",
            status=DoctorStatus.OK,
            message="m",
            evidence={},
        )


def test_finding_non_dict_evidence_rejected():
    with pytest.raises(ValueError):
        Finding(
            source=Source.ENV_HYGIENE,
            check="x",
            status=DoctorStatus.OK,
            message="m",
            evidence=["not", "a", "dict"],
        )


def test_finding_evidence_is_defensively_copied():
    """frozen=True only blocks attribute reassignment -- mutating the
    original dict after construction must not leak into the Finding."""
    evidence = {"k": "v"}
    finding = Finding(
        source=Source.ENV_HYGIENE,
        check="x",
        status=DoctorStatus.OK,
        message="m",
        evidence=evidence,
    )
    evidence["k"] = "mutated"
    assert finding.evidence == {"k": "v"}


def test_source_taxonomy_is_exactly_this_closed_set():
    # The taxonomy is CLOSED but extensible by review, never an open/stringly-typed
    # escape hatch -- it stays a fixed, enumerable set and this test is the gate.
    # The member COUNT is deliberately not in the test's name: the set-equality
    # assertion below is the contract, and a number in the name only goes stale
    # the next time a story appends a member (as "nine" then "eleven" both did).
    # Story 4.3 (FR-12, AD-9) added ADOPTION; 2026-08-08 added MARSHAL_DURABILITY,
    # Doctor's verdict on the Marshal's own row (Charter §6 -- "the one station that
    # would otherwise grade itself"), after a sync destroyed 96 `done` markers across
    # four stations and every guard written in response lived in Marshal's own surface.
    # Story 6.4 (FR-15) added LEDGER_REGRESSION and STORY_STATUS, porting
    # scripts/ledger_regression_check.py and scripts/story_status_check.py's own
    # judgements into Doctor's package. Story 6.5 (FR-15) added
    # CHAIN_COMPLETENESS, DASHBOARD_DRIFT and CHECK_LAYOUT, porting
    # scripts/chain_completeness_check.py, scripts/dashboard_drift_check.py and
    # docs/dashboard/check_layout.py's own judgements on the fleet-status board.
    # Story 6.6 (FR-15) added DREAM_CHAIN, SPEC_SURFACE and DEFERRED_WORK, porting
    # scripts/dream_chain_check.py, scripts/spec_surface_check.py and
    # scripts/deferred_work_check.py's own judgements on the Dream-to-Code chain.
    # Story 6.7 (FR-15) added FORWARD_DEPENDENCY, porting
    # scripts/forward_dependency_check.py's judgement on the one defect the
    # harness's own picker is blind to. Unlike its siblings that port was not a
    # pure relocation: the script imported bmad_loop.sprintstatus, which
    # sources/deps.py restates instead (AD-13), so the verdict no longer
    # requires the machinery it judges.
    # Story 6.8 (FR-15) added BMAD_DRIFT, porting scripts/bmad_drift_check.py's
    # judgement on the pyforge-marshal project docs' own currency -- the tenth
    # and last of Epic 6's Charter §6 sweep.
    # Story 9.2 (CAP-8) added BMAD_OUTPUT_HYGIENE, giving Story 9.1's five
    # pure hygiene predicates their first production caller (sources/hygiene.py),
    # walking every station's own planning artifacts at once.
    # Story 11.1 (Epic 11/CAP-1) added DUE_FOR_VERIFICATION, the first
    # genuinely NEW (non-ported) member: a per-project batch of tracked
    # deferred-work-ledger entries due for re-verification.
    # Story 10.1 (Epic 10/CAP-1) added BMAD_METHOD_VERSION_DRIFT: whether the
    # installed BMAD-METHOD framework version meets pixi.toml's own declared
    # floor -- distinct from the existing BMAD_DRIFT (a different artifact:
    # the installed framework tool, not pyforge-marshal's project-doc
    # currency).
    # Story 13.1 (Epic 13/CAP-1) added BACKLOG_INTAKE: which tracked
    # deferred-work-ledger entries, fleet wide, precisely name a caller-
    # supplied epic/story -- wired as its own `doctor backlog-intake`
    # verb, not a sweep dispatched by name.
    # Story 17.2 (Epic 17 / FR-147) added DREAMS_HYGIENE: Dream-tier
    # hygiene mode on the dream-chain surface (`dream-chain --dreams`).
    # Story 17.3 (Epic 17 / FR-150 residual + FR-152) added
    # CHAIN_LAYERS_AUDIT: per-project layer presence
    # (`chain-completeness --layers --project <slug>`).
    # Retro action item 3 (retro-pyforge-steward-2026-09-04.md, 2026-09-05)
    # added PLATFORM_POLICY_SUITE: src/platform's manifest-only tests/policy
    # subset, so a pixi.toml regression is caught even when Platform CI is
    # disabled.
    # Story 20.2 (Epic 20) added BMAD_RENDER_CONFIG_AMBIGUITY: whether
    # render_skill.py's own central-config merge holds a bare key ambiguous
    # across two dotted paths -- the class that HALTs every rendering skill.
    # Story 20.3 (Epic 20) added FROZEN_PATH_CHANGED: whether a capability
    # currently rebuilding/moving in the tracked capability ledger had one
    # of its own frozen source paths touched by origin/main..HEAD (AD-22).
    assert {member.value for member in Source} == {
        "warden-doctor",
        "staleness-report",
        "cve-watcher",
        "behind-upstream",
        "feedstock-health",
        "release-cadence",
        "env-hygiene",
        "adoption",
        "marshal-durability",
        "ledger-regression",
        "ledger-direction",
        "story-status",
        "chain-completeness",
        "dashboard-drift",
        "check-layout",
        "dream-chain",
        "spec-surface",
        "deferred-work",
        "forward-dependency",
        "bmad-drift",
        "bmad-output-hygiene",
        "due-for-verification",
        "bmad-method-version-drift",
        "backlog-intake",
        "sibling-dreams-drift",
        "dreams-hygiene",
        "chain-layers-audit",
        "platform-policy-suite",
        "bmad-render-config-ambiguity",
        "frozen-path-changed",
        "capability-effect",
        "status-body-consistency",
        "pixi-currency-ledger",
        "general-docs-consistency",
        "capability-ledger",
        # Doctor Epic 25 (spec-one-chain-per-station, guild outcome / doctor
        # mechanism): 25.1 sprawl gate, 25.2 FR<-CAP check.
        "chain-sprawl",
        "fr-without-cap",
        # Story 30.1 (spec-pyforge-doctor CAP-83): docs/MAP.md vs the four
        # Diátaxis quadrants -- missing link FAIL, unmapped page FAIL
        # (promoted from WARN by Story 30.2).
        "docs-map-hygiene",
        # Story 23.7 (Epic 23 / spec-pyforge-doctor CAP-54): leftover-
        # shelf path occupancy vs the docs/MAP.md allow-list.
        "docs-shelf-occupancy",
        # Story 26.1 (spec-pyforge-doctor CAP-77): a touched surface
        # catalogued in live-proof-surfaces.md gets an advisory finding
        # naming it, matched via the catalog's own Surface globs column.
        "live-proof-surface",
        # Story 30.2 (spec-pyforge-doctor CAP-84): docs/map.yaml vs its
        # render (docs/MAP.md), authored-page staleness, skill-dir hygiene.
        "docs-currency",
    }


def test_finding_to_json_dict_shape():
    assert _finding().to_json_dict() == {
        "source": "env-hygiene",
        "check": "x",
        "status": "ok",
        "message": "m",
        "evidence": {},
    }


# --- Prescription -----------------------------------------------------


def test_prescription_unknown_partition_rejected():
    with pytest.raises(ValueError):
        Prescription(
            finding_ref="x",
            partition="not-a-partition",
            rank=None,
            rank_factors=None,
            action="do it",
            root_cause="because",
        )


def test_prescription_rank_and_rank_factors_stay_none_able():
    prescription = Prescription(
        finding_ref="x",
        partition=Partition.BLOCKED,
        rank=None,
        rank_factors=None,
        action="do it",
        root_cause="because",
    )
    assert prescription.rank is None
    assert prescription.rank_factors is None


def test_prescription_rank_factors_is_defensively_copied():
    rank_factors = {"k": "v"}
    prescription = Prescription(
        finding_ref="x",
        partition=Partition.ACTIONABLE,
        rank=1,
        rank_factors=rank_factors,
        action="do it",
        root_cause="because",
    )
    rank_factors["k"] = "mutated"
    assert prescription.rank_factors == {"k": "v"}


def test_prescription_to_json_dict_shape():
    prescription = Prescription(
        finding_ref="hygiene:DEP001:foo",
        partition=Partition.ACTIONABLE,
        rank=1,
        rank_factors={"severity": "high"},
        action="upgrade foo",
        root_cause="foo is unmaintained",
    )
    assert prescription.to_json_dict() == {
        "finding_ref": "hygiene:DEP001:foo",
        "partition": "actionable",
        "rank": 1,
        "rank_factors": {"severity": "high"},
        "action": "upgrade foo",
        "root_cause": "foo is unmaintained",
        "safe_upgrade_target": None,
        "safe_upgrade_reason": None,
    }


def test_prescription_safe_upgrade_fields_default_to_none():
    # Story 4.4: existing (pre-Epic-4) construction sites never pass these
    # kwargs -- they must default to None, not raise a TypeError.
    prescription = Prescription(
        finding_ref="x",
        partition=Partition.ACTIONABLE,
        rank=1,
        rank_factors={},
        action="do it",
        root_cause="because",
    )
    assert prescription.safe_upgrade_target is None
    assert prescription.safe_upgrade_reason is None


def test_prescription_safe_upgrade_fields_round_trip():
    prescription = Prescription(
        finding_ref="x",
        partition=Partition.ACTIONABLE,
        rank=1,
        rank_factors={},
        action="do it",
        root_cause="because",
        safe_upgrade_target="2.1.0",
        safe_upgrade_reason="patch version bump, no known breaking-change signal",
    )
    document = prescription.to_json_dict()
    assert document["safe_upgrade_target"] == "2.1.0"
    assert document["safe_upgrade_reason"] == ("patch version bump, no known breaking-change signal")


# --- DoctorReport: verb/prescriptions coherence ----------------------------


def test_check_report_serializes_with_no_prescriptions_key():
    report = DoctorReport(
        schema_version=1,
        verb="check",
        generated_at="2026-07-25T00:00:00Z",
        findings=(_finding(),),
        prescriptions=None,
    )
    assert "prescriptions" not in report.to_json_dict()


def test_monitor_report_serializes_with_no_prescriptions_key():
    report = DoctorReport(
        schema_version=1,
        verb="monitor",
        generated_at="2026-07-25T00:00:00Z",
        findings=(),
        prescriptions=None,
    )
    assert "prescriptions" not in report.to_json_dict()


def test_diagnose_report_empty_prescriptions_serializes_as_empty_list():
    report = DoctorReport(
        schema_version=1,
        verb="diagnose",
        generated_at="2026-07-25T00:00:00Z",
        findings=(),
        prescriptions=[],
    )
    assert report.to_json_dict()["prescriptions"] == []


def test_diagnose_report_missing_prescriptions_rejected():
    with pytest.raises(ValueError):
        DoctorReport(
            schema_version=1,
            verb="diagnose",
            generated_at="2026-07-25T00:00:00Z",
            findings=(),
            prescriptions=None,
        )


def test_check_report_with_prescriptions_set_rejected():
    prescription = Prescription(
        finding_ref="x",
        partition=Partition.ACTIONABLE,
        rank=None,
        rank_factors=None,
        action="do it",
        root_cause="because",
    )
    with pytest.raises(ValueError):
        DoctorReport(
            schema_version=1,
            verb="check",
            generated_at="2026-07-25T00:00:00Z",
            findings=(),
            prescriptions=[prescription],
        )


def test_unknown_verb_rejected():
    with pytest.raises(ValueError):
        DoctorReport(
            schema_version=1,
            verb="bogus",
            generated_at="2026-07-25T00:00:00Z",
            findings=(),
        )


def test_schema_version_zero_rejected():
    with pytest.raises(ValueError):
        DoctorReport(
            schema_version=0,
            verb="check",
            generated_at="2026-07-25T00:00:00Z",
            findings=(),
        )


def test_schema_version_negative_rejected():
    with pytest.raises(ValueError):
        DoctorReport(
            schema_version=-1,
            verb="check",
            generated_at="2026-07-25T00:00:00Z",
            findings=(),
        )


def test_diagnose_report_with_a_real_prescription_round_trips_through_schema():
    """Exercises Prescription.to_json_dict() via a real DoctorReport (not
    just an empty prescriptions list), validated against the packaged
    schema's #/$defs/prescription."""
    prescription = Prescription(
        finding_ref="hygiene:DEP001:foo",
        partition=Partition.ACTIONABLE,
        rank=1,
        rank_factors={"severity": "high"},
        action="upgrade foo",
        root_cause="foo is unmaintained",
    )
    report = DoctorReport(
        schema_version=1,
        verb="diagnose",
        generated_at="2026-07-25T00:00:00Z",
        findings=(_finding(),),
        prescriptions=[prescription],
    )
    document = report.to_json_dict()
    assert document["prescriptions"] == [prescription.to_json_dict()]
    jsonschema.validate(document, _schema())


# --- Schema validation: fixtures + live-constructed reports ----------------


def test_minimal_check_report_fixture_validates_against_schema():
    jsonschema.validate(_fixture("minimal_check_report.json"), _schema())


def test_minimal_diagnose_report_fixture_validates_against_schema():
    jsonschema.validate(_fixture("minimal_diagnose_report.json"), _schema())


def test_sample_report_with_finding_fixture_validates_against_composed_schema():
    """Story 14.3, SPEC-pyforge-core CAP-4: a real captured report (with a
    real finding, not the empty-findings minimal fixtures above) validates
    against the packaged schema COMPOSED with the shared base envelope
    schema -- proving the composed schema still admits every payload that
    validated against the station schema alone."""
    jsonschema.validate(_fixture("sample_report_with_finding.json"), compose(BASE_ENVELOPE_SCHEMA, _schema()))


def test_check_report_json_dict_validates_against_schema():
    report = DoctorReport(
        schema_version=1,
        verb="check",
        generated_at="2026-07-25T00:00:00Z",
        findings=(),
        prescriptions=None,
    )
    jsonschema.validate(report.to_json_dict(), _schema())


def test_diagnose_report_json_dict_validates_against_schema():
    report = DoctorReport(
        schema_version=1,
        verb="diagnose",
        generated_at="2026-07-25T00:00:00Z",
        findings=(),
        prescriptions=[],
    )
    jsonschema.validate(report.to_json_dict(), _schema())


def test_diagnose_report_missing_prescriptions_key_fails_schema():
    """The raw (un-validated-by-the-model) document shape a schema consumer
    might still receive from elsewhere — the schema itself must independently
    reject a diagnose document lacking prescriptions."""
    document = {
        "schema_version": 1,
        "verb": "diagnose",
        "generated_at": "2026-07-25T00:00:00Z",
        "findings": [],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(document, _schema())


def test_check_report_with_prescriptions_key_fails_schema():
    document = {
        "schema_version": 1,
        "verb": "check",
        "generated_at": "2026-07-25T00:00:00Z",
        "findings": [],
        "prescriptions": [],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(document, _schema())


def test_schema_source_enum_matches_the_source_taxonomy_exactly():
    """The schema's `source` enum and `models.Source` must not drift apart.

    Story 5.1 added ``Source.MARSHAL_DURABILITY`` to the Python enum but not to
    the schema, and nothing caught it: 5.1 shipped the source with **no caller**,
    so its findings were never rendered and never validated. The gap surfaced only
    when Story 5.2 wired the gather into ``doctor check`` -- ``--json`` raised
    ``jsonschema.ValidationError`` and the CLI exited 2, on a source that had been
    "done" for a day.

    Asserted as SET EQUALITY in both directions on purpose. A one-way check
    (schema ⊆ enum) would still have passed while marshal-durability was missing,
    which is exactly the direction that broke.
    """
    schema_sources = set(_schema()["$defs"]["finding"]["properties"]["source"]["enum"])
    taxonomy = {member.value for member in Source}
    assert schema_sources == taxonomy, (
        "schema `source` enum and models.Source disagree — "
        f"only in schema: {sorted(schema_sources - taxonomy)}; "
        f"only in taxonomy: {sorted(taxonomy - schema_sources)}"
    )
