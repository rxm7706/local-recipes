"""Story F4 gate (FR-16 / FR-18 / FR-10, AD-9/AD-12/AD-20) — the deptry hygiene
node + the converged four-axis policy gate (the ``universal_sbom`` TERMINAL stage).

Wave F's verify gate is ``kedro-test`` (this package is collected there). These tests
assert the load-bearing F4 behaviours:

- (a) an injected unused-dependency fixture yields a schema-valid HYGIENE finding in the
  ``ComplianceReport`` artifact (deptry runs the hygiene axis);
- (b) a source-less input reports ``not-applicable``, NEVER a failure (FR-16);
- (c) a policy breach exits with warden's frozen code (1 = policy-fail), HALTS via a native
  raise (F2's ``DataContractViolation`` — AD-9, identical to an FR-10 violation), and raises
  an A2A alert on E1's real channel (AD-20);
- (d) an operational error → warden's frozen exit 2 (never a false pass);
- (e) the assembled report validates against ``pyforge.warden``'s four-axis schema;
- (f) the F4 gate node is the SINGLE producer of the ``ComplianceReport`` (AD-12);
- (g) absent the ``[gate]`` extra the gate node fails with an EXPLICIT install hint while
  every OTHER pipeline still resolves/runs (schema BY import, never vendored — AD-12);
- (h) the ``inventory-match`` exit-code flip lands with its one-release deprecation window
  (``INVENTORY_MATCH_LEGACY_EXIT=1``), routed through warden's frozen ``exit_code_for``.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest
from kedro.io import DataCatalog, MemoryDataset
from kedro.pipeline import Pipeline, node
from kedro.runner import SequentialRunner

from pyforge.atlas.a2a import AtlasAlert, AuthoringInbox, Severity, hand_off
from pyforge.atlas.pipelines.universal_sbom import gate as gate_mod
from pyforge.atlas.pipelines.universal_sbom.gate import (
    GateDependencyMissing,
    assemble_and_gate,
    inventory_match_exit_code,
    run_dependency_hygiene,
)
from pyforge.atlas.pipelines.universal_sbom.pipeline import create_pipeline
from pyforge.atlas.validation import DataContractViolation

STAMP = "2026-07-18T00:00:00Z"
FIXTURE = Path(__file__).parent / "fixtures" / "unused_dep_project"

# A match report shaped like B7's match node output (the atlas-native currency signal).
_MATCH_REPORT = {
    "kind": "sbom-match-report",
    "atlas_built_at": 1,
    "stale": False,
    "components": [{"name": "numpy", "bucket": "CURRENT"}],
    "buckets": {"CURRENT": 1},
}


def _critical_security(kev: bool = False) -> dict:
    return {
        "gate": {
            "security": {
                "source": "atlas-cve",
                "snapshot_at": "2026-07-18",
                "findings": [
                    {
                        "id": "vuln:CVE-2026-0001:numpy@1.0",
                        "severity": "critical",
                        "subject": "numpy",
                        "kev": kev,
                        "affecting_current": kev,
                        "message": "critical vuln",
                    }
                ],
            }
        }
    }


# --------------------------------------------------------------------------- #
# (a) unused-dependency fixture -> a schema-valid hygiene finding in the report
# --------------------------------------------------------------------------- #
def test_unused_dep_fixture_yields_hygiene_finding_in_report():
    params = {"gate": {"hygiene_source_dir": str(FIXTURE)}}
    hygiene = run_dependency_hygiene({}, params)
    assert hygiene["applicable"] is True
    assert any(f["id"] == "hygiene:DEP002:requests" for f in hygiene["findings"])

    document = assemble_and_gate(hygiene, _MATCH_REPORT, params)
    # DEP002 is a warn (exit 0) — the report is returned (persists), carrying the finding.
    assert document["exit_code"] == 0
    ids = {f["id"] for f in document["findings"]}
    assert "hygiene:DEP002:requests" in ids
    hygiene_finding = next(f for f in document["findings"] if f["id"] == "hygiene:DEP002:requests")
    assert hygiene_finding["axis"] == "hygiene"


# --------------------------------------------------------------------------- #
# (b) source-less input -> not-applicable, NEVER a failure (FR-16)
# --------------------------------------------------------------------------- #
def test_source_less_input_is_not_applicable_never_failure():
    hygiene = run_dependency_hygiene({}, {})  # no source dir configured
    assert hygiene["applicable"] is False
    assert hygiene["findings"] == []
    assert hygiene["errors"] == []

    document = assemble_and_gate(hygiene, _MATCH_REPORT, {})
    assert document["exit_code"] == 0  # not a failure
    assert document["status"]["value"] in {"clean", "not-applicable", "warn"}
    hygiene_cov = next(c for c in document["coverage"] if c["axis"] == "hygiene")
    assert hygiene_cov["deps_total"] == 0 and hygiene_cov["deps_assessed"] == 0


def test_source_dir_without_python_is_not_applicable(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")
    hygiene = run_dependency_hygiene({}, {"gate": {"hygiene_source_dir": str(tmp_path)}})
    assert hygiene["applicable"] is False  # no adjacent *.py -> deptry N/A, not a failure


# --------------------------------------------------------------------------- #
# (c) policy breach -> frozen exit 1 + halt + A2A alert (identical to FR-10)
# --------------------------------------------------------------------------- #
def test_policy_breach_halts_with_frozen_exit_1_and_alerts():
    inbox = AuthoringInbox()
    hygiene = run_dependency_hygiene({}, {})  # source-less -> hygiene not-applicable
    params = _critical_security()  # one critical vuln, default max_critical=0

    with pytest.raises(DataContractViolation) as excinfo:
        assemble_and_gate(
            hygiene, _MATCH_REPORT, params,
            alert_sink=lambda a: hand_off(a, inbox), build_stamp=STAMP,
        )

    raised = excinfo.value
    assert isinstance(raised, Exception)  # native — Dagster/kedro treat it as a run failure
    assert raised.alert.evidence["exit_code"] == 1  # warden's frozen policy-fail code
    assert raised.alert.evidence["status"] == "policy-violation"
    assert raised.alert.rule == "policy-gate:policy-violation"
    # the alert rode E1's real channel and round-tripped to the exact AtlasAlert.
    assert len(inbox.payloads) == 1
    received = inbox.payloads[0]
    assert isinstance(received, AtlasAlert)
    assert received == raised.alert
    assert received.build_stamp == STAMP


def test_kev_affecting_current_is_a_breach():
    # max_high unbounded + max_critical raised, but the KEV gate still trips on a
    # KEV-affecting-current hit (independent policy boundary).
    params = _critical_security(kev=True)
    params["gate"]["policy"] = {"max_critical": 5, "max_high": None, "kev_gate": True}
    with pytest.raises(DataContractViolation) as excinfo:
        assemble_and_gate({"applicable": False, "findings": [], "errors": []}, _MATCH_REPORT, params, build_stamp=STAMP)
    assert excinfo.value.alert.evidence["exit_code"] == 1


def test_security_within_policy_is_warn_not_breach():
    params = _critical_security()
    params["gate"]["policy"] = {"max_critical": 5, "max_high": None, "kev_gate": False}
    document = assemble_and_gate({"applicable": False, "findings": [], "errors": []}, _MATCH_REPORT, params)
    assert document["exit_code"] == 0  # within policy -> warn, exit 0
    assert document["status"]["value"] == "warn"


# --------------------------------------------------------------------------- #
# (d) an operational error -> warden's frozen exit 2 (never a false pass)
# --------------------------------------------------------------------------- #
def test_deptry_engine_error_yields_frozen_exit_2():
    hygiene = {
        "axis": "hygiene",
        "applicable": True,
        "findings": [],
        "errors": [{"kind": "engine-unavailable", "owner": "deptry", "message": "deptry not on PATH"}],
        "deps_total": 0,
        "deps_assessed": 0,
    }
    with pytest.raises(DataContractViolation) as excinfo:
        assemble_and_gate(hygiene, _MATCH_REPORT, {}, build_stamp=STAMP)
    assert excinfo.value.alert.evidence["exit_code"] == 2  # error dominates -> frozen error code
    assert excinfo.value.alert.evidence["status"] == "error"
    assert excinfo.value.alert.severity is Severity.critical


# --------------------------------------------------------------------------- #
# (e) the assembled report validates against warden's four-axis schema
# --------------------------------------------------------------------------- #
def test_report_is_four_axis_and_schema_valid():
    # assemble_and_gate calls report.render_json internally (schema self-validation);
    # a returned document therefore validated. Assert the four axes are present.
    document = assemble_and_gate({"applicable": False, "findings": [], "errors": []}, _MATCH_REPORT, {})
    axes = {c["axis"] for c in document["coverage"]}
    assert axes == {"hygiene", "vulnerability", "license", "currency"}
    assert document["schema_version"].startswith("1.")


def test_license_and_currency_degrade_to_atlas_native_or_not_applicable():
    # currency populated from the atlas-native match report; license -> not-applicable.
    document = assemble_and_gate({"applicable": False, "findings": [], "errors": []}, _MATCH_REPORT, {})
    currency = next(c for c in document["coverage"] if c["axis"] == "currency")
    license_cov = next(c for c in document["coverage"] if c["axis"] == "license")
    assert currency["deps_total"] == 1  # from the match report's 1 component (atlas-native)
    assert license_cov["deps_total"] == 0 and license_cov["deps_assessed"] == 0  # not-applicable


# --------------------------------------------------------------------------- #
# (f) the F4 gate node is the SINGLE producer of the ComplianceReport (AD-12)
# --------------------------------------------------------------------------- #
def test_single_producer_of_compliance_report():
    pkg_dir = Path(gate_mod.__file__).parent
    # Only gate.py may construct a warden ComplianceReport in the universal_sbom package.
    producers = []
    for py in sorted(pkg_dir.glob("*.py")):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            if isinstance(n, ast.Attribute) and n.attr == "ComplianceReport":
                producers.append(py.name)
    assert set(producers) <= {"gate.py"}, f"a non-gate module constructs ComplianceReport: {producers}"

    # Exactly one pipeline node produces the terminal report dataset.
    pipe = create_pipeline()
    emitters = [nd.name for nd in pipe.nodes if "sbom_compliance_report_entry" in nd.outputs]
    assert emitters == ["assemble_and_gate"]


# --------------------------------------------------------------------------- #
# (g) absent the [gate] extra: explicit install hint, other pipelines unaffected
# --------------------------------------------------------------------------- #
def test_gate_absent_extra_fails_with_install_hint_others_run(monkeypatch):
    # Simulate the [gate] extra being absent: block the warden import.
    monkeypatch.setitem(sys.modules, "pyforge.warden", None)

    # (1) the gate node fails with an EXPLICIT install hint.
    with pytest.raises(GateDependencyMissing) as excinfo:
        assemble_and_gate({"applicable": False, "findings": [], "errors": []}, _MATCH_REPORT, {})
    assert "pyforge-atlas[gate]" in str(excinfo.value)

    # (2) independence preserved: a source-less hygiene call needs NO warden.
    assert run_dependency_hygiene({}, {})["applicable"] is False

    # (3) every OTHER pipeline still resolves (the atlas package imports fine w/o warden).
    from pyforge.atlas.pipelines.seed_gaps.pipeline import create_pipeline as seed_pipeline

    assert len(seed_pipeline().nodes) >= 1
    assert len(create_pipeline().nodes) == 4  # the universal_sbom pipeline itself still builds


# --------------------------------------------------------------------------- #
# (h) inventory-match exit-code flip + one-release deprecation window (FR-18)
# --------------------------------------------------------------------------- #
def test_inventory_match_exit_flip_and_deprecation_window():
    from pyforge.warden.models import Status

    frozen_env: dict[str, str] = {}
    legacy_env = {gate_mod.INVENTORY_MATCH_LEGACY_EXIT_ENV: "1"}

    # Frozen convention (default): 0 clean / 1 policy-fail / 2 error — warden-owned.
    assert inventory_match_exit_code(Status.CLEAN, env=frozen_env) == 0
    assert inventory_match_exit_code(Status.POLICY_VIOLATION, env=frozen_env) == 1
    assert inventory_match_exit_code(Status.ERROR, env=frozen_env) == 2

    # Legacy window restores the INVERTED enum (0 pass / 2 policy-violation / 1 error).
    assert inventory_match_exit_code(Status.CLEAN, env=legacy_env) == 0
    assert inventory_match_exit_code(Status.POLICY_VIOLATION, env=legacy_env) == 2
    assert inventory_match_exit_code(Status.ERROR, env=legacy_env) == 1


# --------------------------------------------------------------------------- #
# real one-pipeline run: the breach HALTS before the report persists (Dagster/kedro)
# --------------------------------------------------------------------------- #
class _TrackingDataset(MemoryDataset):
    def __init__(self, saves: list[str], name: str) -> None:
        super().__init__()
        self._saves = saves
        self._name = name

    def save(self, data) -> None:  # type: ignore[override]
        self._saves.append(self._name)
        super().save(data)


def test_real_pipeline_breach_halts_before_report_persists():
    inbox = AuthoringInbox()
    saves: list[str] = []
    params = _critical_security()

    def _gate_node(hyg, match, parameters):
        return assemble_and_gate(
            hyg, match, parameters, alert_sink=lambda a: hand_off(a, inbox), build_stamp=STAMP
        )

    pipe = Pipeline(
        [
            node(run_dependency_hygiene, ["sbom_intake_entry", "parameters"], "sbom_hygiene_entry", name="hyg"),
            node(_gate_node, ["sbom_hygiene_entry", "sbom_match_report_entry", "parameters"], "sbom_compliance_report_entry", name="gate"),
        ]
    )
    catalog = DataCatalog(
        {
            "sbom_intake_entry": MemoryDataset({}),
            "sbom_match_report_entry": MemoryDataset(_MATCH_REPORT),
            "parameters": MemoryDataset(params),
            "sbom_hygiene_entry": MemoryDataset(),
            "sbom_compliance_report_entry": _TrackingDataset(saves, "report"),
        }
    )
    with pytest.raises(DataContractViolation):
        SequentialRunner().run(pipe, catalog)
    # the failing report never persisted (halt is pre-persist) and the alert rode the channel.
    assert saves == []
    assert len(inbox.payloads) == 1
    assert inbox.payloads[0].evidence["exit_code"] == 1


# --------------------------------------------------------------------------- #
# Reviewer fixes — the terminal gate must DEGRADE on hostile inputs, never crash
# --------------------------------------------------------------------------- #
def test_all_indeterminate_security_axis_is_indeterminate_not_a_min_crash():
    """MUST-FIX (both reviewers): a security axis carrying ONLY indeterminate:* ids (warden's
    OsvEngine routinely emits these) has no vuln: id — the old min(... vuln:) was an empty
    sequence → ValueError crashing the terminal gate. It must degrade to INDETERMINATE."""
    params = {
        "gate": {
            "security": {
                "source": "atlas-cve",
                "snapshot_at": "2026-07-18",
                "findings": [
                    {"id": "indeterminate:offline-db-unavailable:numpy@1.0", "severity": "unknown",
                     "subject": "numpy", "message": "db offline"},
                ],
            }
        }
    }
    document = assemble_and_gate({"applicable": False, "findings": [], "errors": []}, _MATCH_REPORT, params)
    # no breach → WARN/exit 0, driven off the (indeterminate) finding id — NOT a min()-over-empty crash.
    assert document["status"]["value"] == "warn"
    assert document["exit_code"] == 0


def test_out_of_vocab_severity_tier_degrades_to_unknown_not_a_crash():
    """SHOULD (Reviewer-B): an upstream feed's non-vocab tier ('important'/'moderate'/typo) must
    degrade to the 'unknown' tier, not crash SeverityTier() construction in the terminal gate."""
    params = {
        "gate": {
            "security": {
                "source": "atlas-cve", "snapshot_at": "2026-07-18",
                "findings": [
                    {"id": "vuln:RHSA-2026-1:openssl@3.0", "severity": "important",  # RedHat tier
                     "subject": "openssl", "message": "rh vuln"},
                ],
            }
        }
    }
    # 'important' is not critical/high, so no breach → warn/exit 0; the point is it does not crash.
    document = assemble_and_gate({"applicable": False, "findings": [], "errors": []}, _MATCH_REPORT, params)
    assert document["exit_code"] == 0


def test_whitespace_only_build_stamp_falls_back_not_a_masking_error():
    """SHOULD (Reviewer-B): a whitespace-only build_stamp is truthy, so a bare `or` chain passed
    it through and AtlasAlert then rejected it — a confusing ValueError masking the real breach.
    .strip() emptiness test → the 'unknown-build' fallback, and the BREACH alert still fires."""
    params = _critical_security()  # one critical → breach → exit 1 + alert
    with pytest.raises(DataContractViolation) as excinfo:
        assemble_and_gate({"applicable": False, "findings": [], "errors": []}, _MATCH_REPORT, params, build_stamp="   ")
    assert excinfo.value.alert.evidence["exit_code"] == 1        # the real breach, not a stamp error
    assert excinfo.value.alert.build_stamp == "unknown-build"     # whitespace → safe fallback
