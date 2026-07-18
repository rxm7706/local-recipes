"""``universal_sbom`` TERMINAL stage (Story F4, FR-16 / FR-18 / FR-10).

Two nodes that converge the shipped CLI-scraping exit surface into ONE
schema-validated ``ComplianceReport`` and ONE frozen exit code:

- :func:`run_dependency_hygiene` — the deptry dependency-hygiene node (FR-16).
  Runs deptry over an accompanying project source tree and emits schema-shaped
  hygiene findings. A **source-less** intake (a bare manifest / lockfile / SBOM
  passthrough — the common consumer profile) reports **``not-applicable``,
  never a failure** (FR-16 frozen source-less semantics) and needs no ``[gate]``
  extra at all. deptry execution is delegated to ``pyforge.warden``'s
  ``DeptryEngine`` (the package's sole subprocess site) — this module never
  shells out itself (the AC-2 no-inline-IO ban forbids ``subprocess`` in the
  atlas surface; the subprocess lives in the warden package).

- :func:`assemble_and_gate` — the F4 TERMINAL gate node and, per **AD-12**, the
  **SINGLE producer** of the four-axis ``ComplianceReport``. It assembles the
  hygiene axis (from the deptry node), the security axis (from the atlas-native
  ``inventory-match`` / ``cve`` inputs — the atlas never re-invokes
  ``osv-scanner``; standalone ``pyforge.warden`` does), and the license /
  currency axes (from atlas-native data — the SBOM match report's behind-upstream
  buckets — or ``not-applicable``), validates the assembled report against
  ``pyforge.warden``'s schema, computes the frozen exit code via
  ``verdict.exit_code_for``, and on a policy breach HALTS Dagster (reusing F2's
  ``DataContractViolation`` — **AD-9**, identical failure semantics to an FR-10
  contract violation) after raising an A2A alert on E1's channel (**AD-20**).

Schema BY IMPORT, never vendored (AD-12, the load-bearing correct-course
decision 2026-07-17)
--------------------------------------------------------------------------
The gate validates against ``pyforge.warden.models.ComplianceReport`` /
``pyforge.warden.verdict`` — imported **LAZILY**, inside the node bodies, via
the declared ``pyforge-atlas[gate]`` extra (``[project.optional-dependencies]
gate = ["pyforge-warden"]``) — NEVER a vendored copy. So the atlas package
imports fine WITHOUT warden and every OTHER pipeline runs unaffected; absent the
extra, only the gate node (and the source-bearing hygiene path) fails, with an
EXPLICIT install hint (:data:`INSTALL_HINT`). The planned promotion of the gate
into an MCP tool + pixi CLI is then a wiring change, not a schema change.

Exit codes are SOLE-OWNED by ``pyforge.warden.verdict`` (the frozen CI contract:
0 clean / 1 policy-fail / 2 error / 130 SIGINT). This module NEVER hand-rolls an
``int`` / ``sys.exit(<literal>)`` — every exit code is produced by
``verdict.exit_code_for`` (and the legacy ``inventory-match`` window in
:func:`inventory_match_exit_code` REMAPS warden's frozen output, never a
status→literal table).

No inline IO (AC-2): stdlib + the atlas-internal ``a2a`` / ``validation`` seams
only; ``pyforge.warden`` is imported lazily inside the nodes. ``dagster`` /
``kedro_mcp`` are never imported (AD-1).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from pyforge.atlas.a2a import AtlasAlert, Severity, build_alert_payload
from pyforge.atlas.validation import ContractViolation, DataContractViolation

# The catalog name of the terminal artifact — the dataset the gate is the single
# producer of, and the dataset the halt (DataContractViolation) is attributed to.
REPORT_DATASET = "sbom_compliance_report_entry"

# The env flag that RESTORES the legacy inverted inventory-match exit enum for one
# release (FR-18 deprecation window) — see :func:`inventory_match_exit_code`.
INVENTORY_MATCH_LEGACY_EXIT_ENV = "INVENTORY_MATCH_LEGACY_EXIT"

# The explicit install hint surfaced when the ``[gate]`` extra (pyforge-warden) is
# absent — every OTHER pipeline still runs; only the gate node fails, right here.
INSTALL_HINT = (
    "the F4 policy gate requires pyforge-warden (the ComplianceReport schema is "
    "imported, never vendored — AD-12). Install the extra: "
    "`pip install pyforge-atlas[gate]` (or add pyforge-warden to the environment). "
    "Every other pipeline runs without it."
)

# The default four-axis policy. ``max_critical=0`` is the spec's strict default
# (a run with zero critical vulns still passes it); license/currency gates are
# flag-activated and OFF in v1 (they populate the report, they do not block).
_DEFAULT_POLICY: dict[str, Any] = {
    "max_critical": 0,
    "max_high": None,
    "kev_gate": True,
}


def _as_dict(value: Any) -> dict:
    """A config sub-section coerced to a dict — a key set to ``null`` (or a scalar/list) in
    parameters.yml yields ``None``/non-dict, on which ``.get()`` would raise; degrade to ``{}``
    so a malformed params file can't crash the gate with an AttributeError (Gemini #95)."""
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    """A config list coerced to a list — a key set to ``null`` yields ``None``, over which
    iteration would raise; degrade to ``[]`` (Gemini #95)."""
    return value if isinstance(value, list) else []


class GateDependencyMissing(RuntimeError):
    """Raised (with :data:`INSTALL_HINT`) when the ``pyforge-atlas[gate]`` extra
    is absent — the schema-by-import contract's explicit, actionable failure."""


def _load_warden() -> tuple[Any, Any, Any, str]:
    """Lazily import the warden schema/verdict/report modules (AD-12 schema BY
    import). Absent the ``[gate]`` extra this raises :class:`GateDependencyMissing`
    with an explicit install hint — the atlas package and every other pipeline are
    unaffected because this import happens INSIDE the node body, never at module
    import time."""
    try:
        from pyforge.warden import __version__ as version
        from pyforge.warden import models, report, verdict
    except ImportError as exc:  # pragma: no cover - exercised via the import-block test
        raise GateDependencyMissing(INSTALL_HINT) from exc
    return models, verdict, report, version


# ── node 1: deptry dependency-hygiene (FR-16) ─────────────────────────────────


def _not_applicable_hygiene(reason: str) -> dict[str, Any]:
    """The FR-16 source-less shape: ``not-applicable``, NEVER a failure."""
    return {
        "axis": "hygiene",
        "applicable": False,
        "reason": reason,
        "findings": [],
        "errors": [],
        "deps_total": 0,
        "deps_assessed": 0,
    }


def run_dependency_hygiene(
    sbom_intake_entry: dict[str, Any],
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run deptry over an accompanying project source tree → hygiene findings.

    The source directory is read from ``params:gate.hygiene_source_dir`` (or the
    legacy ``params:hygiene.source_dir``). When NONE is configured — a bare
    manifest / lockfile / SBOM passthrough — the hygiene axis is ``not-applicable``
    (FR-16, never a failure) and warden is never imported (the source-less
    consumer profile needs no ``[gate]`` extra). When a source dir IS present,
    deptry runs via ``pyforge.warden``'s ``DeptryEngine`` (the sole subprocess
    site; imported lazily via the ``[gate]`` extra). An AST-source-less directory
    likewise reports ``not-applicable`` (deptry's import analysis does not apply).

    Emits a plain, JSON-native dict (never a ``ComplianceReport`` — AD-12: only
    the terminal gate node produces that)."""
    params = parameters or {}
    source_dir = _as_dict(params.get("gate")).get("hygiene_source_dir") or _as_dict(
        params.get("hygiene")
    ).get("source_dir")
    if not source_dir:
        return _not_applicable_hygiene(
            "no project source accompanies the intake (bare manifest / lockfile / "
            "SBOM passthrough) — deptry's import analysis is not applicable (FR-16)"
        )

    _load_warden()  # fail EARLY with the install hint if the [gate] extra is absent
    from pyforge.warden.engines import DeptryEngine
    from pyforge.warden.hygiene import has_adjacent_python_source
    from pyforge.warden.inventory import ResolvedInventory

    target = Path(source_dir)
    if not target.is_dir() or not has_adjacent_python_source(target):
        return _not_applicable_hygiene(
            f"no adjacent Python source under {source_dir!r} — deptry's AST/import "
            "analysis is not applicable (FR-16)"
        )

    # deptry reads the project's own pyproject.toml natively (FR9). An empty
    # inventory front-door is a documented no-op for a pyproject-native scan; a
    # richer intake-derived front-door is future work (DW-F4-1).
    result = DeptryEngine().run(target, ResolvedInventory(components=(), resolved_scan_set=()))
    findings = [
        {"id": f.id, "message": f.message, "subject": f.subject} for f in result.findings
    ]
    errors = [
        {"kind": e.kind.value, "owner": e.owner, "message": e.message}
        for e in result.errors
    ]
    raw_assessed = max((c.deps_assessed for c in result.coverage), default=0)
    raw_total = max((c.deps_total for c in result.coverage), default=0)
    n = len(findings)
    return {
        "axis": "hygiene",
        "applicable": True,
        "findings": findings,
        "errors": errors,
        "deps_total": max(raw_total, n),
        "deps_assessed": max(raw_assessed, n),
    }


# ── node 2: the F4 TERMINAL four-axis policy gate (single producer, AD-12) ─────


def _first_id_of_tier(security_findings: list[dict[str, Any]], tier: str) -> str | None:
    for sd in security_findings:
        if sd.get("severity") == tier:
            return sd["id"]
    return None


def assemble_and_gate(
    sbom_hygiene_entry: dict[str, Any],
    sbom_match_report_entry: dict[str, Any],
    parameters: dict[str, Any] | None = None,
    *,
    alert_sink: Callable[[AtlasAlert], None] | None = None,
    build_stamp: str | None = None,
) -> dict[str, Any]:
    """Assemble + validate the four-axis ``ComplianceReport`` (AD-12 SINGLE
    producer), then gate on the frozen exit code.

    Axes: **hygiene** (from the deptry node) and **security** (atlas-native
    ``inventory-match``/``cve`` findings, policy-evaluated) are populated;
    **license** / **currency** come from atlas-native data (the SBOM match
    report's behind-upstream signal) or ``not-applicable`` (FR-16 degradation
    vocabulary — never a failure). The report is validated against
    ``pyforge.warden``'s packaged schema (``report.render_json``), the exit code
    is projected by ``verdict.exit_code_for`` (SOLE owner — never a literal).

    On a clean/warn verdict (exit 0) the assembled report dict is returned (it
    persists to the ``derived`` layer). On a policy breach (exit 1) or an
    operational error (exit 2) the gate emits an A2A alert on E1's channel (AD-20)
    and raises F2's ``DataContractViolation`` (AD-9 — identical halt semantics to
    an FR-10 contract violation), which propagates to Dagster and halts the run
    before the failing report persists. The frozen exit code always rides IN the
    report artifact (and the raised alert's evidence) for CI to consume.

    ``alert_sink`` / ``build_stamp`` are injected (AD-17): the default sink is a
    no-op (offline), the F4 gate test injects a ``hand_off`` → ``AuthoringInbox``
    sink to prove the alert rides the real A2A channel."""
    params = parameters or {}
    gate_params = _as_dict(params.get("gate"))
    # Schema BY IMPORT (AD-12) — lazy; the install hint fires here if [gate] absent.
    models, verdict, report, version = _load_warden()

    findings: list[Any] = []
    coverage: list[Any] = []
    errors: list[Any] = []
    rungs: list[tuple[Any, Any]] = []

    # --- hygiene axis (deptry node) ---
    hyg = _as_dict(sbom_hygiene_entry)
    if hyg.get("applicable"):
        from pyforge.warden.hygiene import hygiene_rung

        for fd in _as_list(hyg.get("findings")):
            finding = models.Finding(
                id=fd["id"],
                axis=models.AXIS_HYGIENE,
                message=fd["message"],
                subject=fd.get("subject"),
                severity=None,
            )
            findings.append(finding)
            rungs.append(hygiene_rung(finding))
        hyg_errors = _as_list(hyg.get("errors"))
        for ed in hyg_errors:
            errors.append(
                models.ErrorRecord(
                    kind=models.ErrorKind(ed["kind"]), owner=ed["owner"], message=ed["message"]
                )
            )
        if hyg_errors:
            first = hyg_errors[0]
            rungs.append(
                (
                    models.Status.ERROR,
                    models.StatusDriver(
                        models.AXIS_INGESTION, f"error:{first['kind']}:{first['owner']}"
                    ),
                )
            )
        n_hyg = len(_as_list(hyg.get("findings")))
        coverage.append(
            models.AxisCoverage(
                models.AXIS_HYGIENE,
                1,
                1,
                max(int(hyg.get("deps_total", 0)), n_hyg),
                max(int(hyg.get("deps_assessed", 0)), n_hyg),
                None,
            )
        )
    else:
        # FR-16: source-less → not-applicable (never a failure).
        rungs.append((models.Status.NOT_APPLICABLE, None))
        coverage.append(models.AxisCoverage(models.AXIS_HYGIENE, 0, 0, 0, 0, None))

    # --- security axis (atlas-native inventory-match/cve; policy-evaluated) ---
    security = _as_dict(gate_params.get("security"))
    security_findings = _as_list(security.get("findings"))
    policy = {**_DEFAULT_POLICY, **_as_dict(gate_params.get("policy"))}
    if security_findings:
        n_crit = n_high = 0
        kev_hit_id: str | None = None
        _valid_tiers = {t.value for t in models.SeverityTier}
        for sd in security_findings:
            raw_tier = sd.get("severity", "unknown")
            # An out-of-vocab tier from an upstream feed (a RedHat "important"/"moderate", a
            # typo) must DEGRADE to "unknown", not crash the terminal gate at SeverityTier()
            # construction (Reviewer-B). The raw string is preserved in Severity.raw below.
            tier = raw_tier if raw_tier in _valid_tiers else "unknown"
            finding = models.Finding(
                id=sd["id"],
                axis=models.AXIS_VULNERABILITY,
                message=sd.get("message", "vulnerability"),
                subject=sd.get("subject"),
                severity=models.Severity(models.SeverityTier(tier), sd.get("raw", raw_tier)),
                kev=sd.get("kev"),
                epss=sd.get("epss"),
            )
            findings.append(finding)
            if tier == "critical":
                n_crit += 1
            elif tier == "high":
                n_high += 1
            if sd.get("kev") and sd.get("affecting_current") and kev_hit_id is None:
                kev_hit_id = finding.id
        breach_id: str | None = None
        if policy.get("max_critical") is not None and n_crit > policy["max_critical"]:
            breach_id = _first_id_of_tier(security_findings, "critical")
        elif policy.get("max_high") is not None and n_high > policy["max_high"]:
            breach_id = _first_id_of_tier(security_findings, "high")
        elif policy.get("kev_gate") and kev_hit_id is not None:
            breach_id = kev_hit_id
        if breach_id is not None:
            rungs.append(
                (models.Status.POLICY_VIOLATION, models.StatusDriver(models.AXIS_VULNERABILITY, breach_id))
            )
        else:
            # No breach → WARN (exit 0, no false halt). warden's engines routinely emit ONLY
            # indeterminate:* ids (offline db, name-level CVE, stale data), so an all-indeterminate
            # axis has NO vuln: id — the old min(... vuln:) was an empty sequence → ValueError
            # crashing the terminal gate (MUST-FIX, both reviewers). Drive the WARN off the
            # smallest real finding id (prefer a vuln: id when present), never a min() over empty.
            # Restrict to the VULNERABILITY axis: ``findings`` also holds hygiene ids, and
            # "hygiene:" < "indeterminate:" lexicographically, so a min() over ALL findings could
            # pick a hygiene id as this axis's driver (Gemini #95). The vuln axis is non-empty
            # here (this branch runs because security_findings is applicable).
            vuln_axis_ids = sorted(f.id for f in findings if f.axis == models.AXIS_VULNERABILITY)
            vuln_ids = [i for i in vuln_axis_ids if i.startswith("vuln:")]
            driver_id = vuln_ids[0] if vuln_ids else vuln_axis_ids[0]
            rungs.append((models.Status.WARN, models.StatusDriver(models.AXIS_VULNERABILITY, driver_id)))
        coverage.append(
            models.AxisCoverage(
                models.AXIS_VULNERABILITY, 1, 1, len(security_findings), len(security_findings), None
            )
        )
        vuln_data = models.VulnData(
            source=security.get("source", "atlas-cve"),
            snapshot_at=security.get("snapshot_at", "unknown"),
            max_age_ok=security.get("max_age_ok", True),
        )
    else:
        rungs.append((models.Status.NOT_APPLICABLE, None))
        coverage.append(models.AxisCoverage(models.AXIS_VULNERABILITY, 0, 0, 0, 0, None))
        vuln_data = models.VulnData(None, None, None)

    # --- currency axis (atlas-native, from the SBOM behind-upstream match report) ---
    match = sbom_match_report_entry or {}
    match_components = match.get("components")
    if match_components is not None:
        coverage.append(
            models.AxisCoverage("currency", 1, 1, len(match_components), len(match_components), None)
        )
        # Currency is a flag-activated gate (OFF in v1): populated, informational,
        # never blocking — it contributes a clean rung, never a finding.
        rungs.append((models.Status.CLEAN, None))
    else:
        coverage.append(models.AxisCoverage("currency", 0, 0, 0, 0, None))
        rungs.append((models.Status.NOT_APPLICABLE, None))

    # --- license axis (atlas-native SPDX or not-applicable) ---
    license_findings = _as_list(_as_dict(gate_params.get("license")).get("findings"))
    if license_findings:
        for ld in license_findings:
            finding = models.Finding(
                id=ld["id"],  # indeterminate:<reason>:<pkg> family (open-axis finding)
                axis="license",
                message=ld.get("message", "license"),
                subject=ld.get("subject"),
                severity=None,
            )
            findings.append(finding)
            rungs.append((models.Status.WARN, models.StatusDriver("license", finding.id)))
        coverage.append(
            models.AxisCoverage("license", 1, 1, len(license_findings), len(license_findings), None)
        )
    else:
        coverage.append(models.AxisCoverage("license", 0, 0, 0, 0, None))
        rungs.append((models.Status.NOT_APPLICABLE, None))

    # --- compose → project (SOLE-owned by warden) → assemble → validate ---
    status, driver = verdict.compose(rungs)
    exit_code = verdict.exit_code_for(status, driver=driver)
    inventory_count = len(match_components) if match_components is not None else len(findings)
    compliance = models.ComplianceReport(
        schema_version=report.REPORT_SCHEMA_VERSION,
        tool_name="pyforge-atlas-gate",
        tool_version=version,
        status=status,
        status_driver=driver,
        exit_code=exit_code,
        findings=tuple(findings),
        coverage=tuple(coverage),
        vuln_data=vuln_data,
        inventory_count=inventory_count,
        resolved_scan_set=(),
        errors=tuple(errors),
    )
    report.render_json(compliance)  # validates against warden's packaged four-axis schema
    document = compliance.to_json_dict()

    if exit_code == 0:
        return document  # clean/warn → the report persists to the derived layer

    # Breach (exit 1) or operational error (exit 2): halt with F2's semantics + alert.
    # A whitespace-only stamp ("   ") is truthy, so a bare `or` chain would pass it through and
    # then AtlasAlert's _stamp_present validator would reject it — a confusing ValueError on the
    # BREACH path, masking the real breach (Reviewer-B). Test emptiness with .strip().
    # str()-coerce each candidate: a build_stamp parsed from unquoted YAML can be an int or a
    # date object, and calling .strip() on it directly would raise AttributeError (Gemini #95).
    stamp = (
        str(build_stamp or "").strip()
        or str(gate_params.get("build_stamp") or "").strip()
        or str(params.get("build_stamp") or "").strip()
        or "unknown-build"
    )
    sbom_cfg = params.get("sbom")
    sbom_cfg = sbom_cfg if isinstance(sbom_cfg, dict) else {}
    subject = gate_params.get("subject") or sbom_cfg.get("project_name") or "user-inventory"
    alert_severity = Severity.critical if status is models.Status.ERROR else Severity.high
    evidence = {
        "exit_code": exit_code,
        "status": status.value,
        "driver": driver.finding_id if driver is not None else None,
    }
    alert = build_alert_payload(
        subject=subject,
        severity=alert_severity,
        rule=f"policy-gate:{status.value}",
        build_stamp=stamp,
        evidence=evidence,
    )
    sink = alert_sink if alert_sink is not None else (lambda _alert: None)
    sink(alert)
    violation = ContractViolation(
        dataset=REPORT_DATASET,
        validator="pyforge-atlas-policy-gate",
        rule=f"policy-gate:{status.value}",
        evidence=evidence,
    )
    raise DataContractViolation(REPORT_DATASET, [violation], alert)


# ── inventory-match exit-code flip + one-release deprecation window (FR-18) ────


def inventory_match_exit_code(status: Any, *, env: dict[str, str] | None = None) -> int:
    """Project a verdict status to ``inventory-match``'s exit code under the FROZEN
    convention (0 clean / 1 policy-fail / 2 error) — SOLE-owned by
    ``verdict.exit_code_for``.

    The shipped legacy ``inventory-match --policy`` enum is INVERTED (0 pass /
    2 policy-violation / 1 error). FR-18 flips it to the frozen convention; setting
    ``INVENTORY_MATCH_LEGACY_EXIT=1`` RESTORES the legacy codes for ONE release so CI
    consumers migrate deliberately. The legacy value is derived by REMAPPING warden's
    frozen output (swap 1↔2), never a hand-rolled status→literal table — the frozen
    contract stays sole-owned by warden."""
    models, verdict, report, _version = _load_warden()
    frozen = verdict.exit_code_for(status)  # 0/1/2/130 — the frozen CI contract
    resolved_env = os.environ if env is None else env
    if resolved_env.get(INVENTORY_MATCH_LEGACY_EXIT_ENV) == "1":
        legacy_remap = {0: 0, 1: 2, 2: 1, verdict.EXIT_SIGINT: verdict.EXIT_SIGINT}
        return legacy_remap[frozen]
    return frozen
