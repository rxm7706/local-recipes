"""Report assembly + deterministic JSON rendering (Story 1.2).

Ownership decisions recorded:

* ``REPORT_SCHEMA_VERSION`` lives HERE — assembly stamps the contract
  version; ``models.py`` is frozen and must not grow constants.
* Coverage honesty under the null engine: one ``AxisCoverage`` per axis
  (hygiene + vulnerability); ``manifests_found``/``manifests_parsed`` come
  from discovery, ``deps_total`` is the post-merge inventory count,
  ``deps_assessed`` is 0 (nothing was assessed by an engine — the truthful
  claim until 1.3/1.5), and ``resolution_depth`` claims ``direct-only`` only
  when a manifest actually parsed (the empty-dir case makes no claim).
* ``render_json`` self-validates every document against the packaged
  ``data/report-schema.json`` BEFORE emit and dumps with every argument
  fixed (``sort_keys=True, ensure_ascii=True, indent=2,
  separators=(",", ": ")``) — byte-identical output is a construction
  property, not a mode. Story 1.8 owns renderers proper; this is 1.2
  plumbing.
* No clock, no volatile fields: ``vuln_data`` is all-``None`` (no vuln data
  was consulted under the null engine).

Status/exit projection is delegated wholesale to ``verdict.py`` (the sole
owner); this module feeds it the collected rungs and stores the result.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from functools import lru_cache
from importlib import resources

import jsonschema

from . import __version__
from .interfaces import EngineResult
from .inventory import ResolvedInventory
from .models import (
    AXIS_HYGIENE,
    AXIS_VULNERABILITY,
    AxisCoverage,
    ComplianceReport,
    ErrorRecord,
    Finding,
    ResolutionDepth,
    Status,
    StatusDriver,
    VulnData,
)
from .verdict import compose, exit_code_for

REPORT_SCHEMA_VERSION = "1.0.0"
TOOL_NAME = "python-deptry-osv-scanner"

# The two v1 axes every 1.2 report covers (an OPEN string mechanism — a
# license/SAST axis lands additively later).
_REPORT_AXES = (AXIS_HYGIENE, AXIS_VULNERABILITY)


@lru_cache(maxsize=1)
def _packaged_schema() -> dict[str, object]:
    schema_file = (
        resources.files("python_deptry_osv_scanner") / "data" / "report-schema.json"
    )
    return json.loads(schema_file.read_text(encoding="utf-8"))


def assemble_report(
    *,
    inventory: ResolvedInventory,
    findings: Sequence[Finding],
    rungs: Iterable[tuple[Status | str, StatusDriver | None]],
    errors: Sequence[ErrorRecord],
    manifests_found: int,
    manifests_parsed: int,
    engine_results: Sequence[EngineResult] = (),
) -> ComplianceReport:
    """Assemble the ``ComplianceReport`` from the pipeline's outputs.

    ``verdict.compose`` picks the winning rung; ``verdict.exit_code_for``
    projects it. ``ComplianceReport.__post_init__`` then enforces the
    status/exit/driver coherence invariants at construction.

    Coverage ownership (recorded): manifest counts and ``deps_total`` are
    ORCHESTRATOR-derived here. ``deps_assessed`` is per-axis: Story 1.3
    consumes an engine's ``EngineResult.coverage`` when it reports one for
    that axis (deptry raises the hygiene axis to ``deps_assessed ==
    inventory.count`` on a successful run), clamped to ``deps_total``; an
    axis with no engine coverage claim (the vulnerability axis until Story
    1.5) stays ``deps_assessed=0`` — the truthful "nothing assessed"."""
    status, driver = compose(rungs)
    resolution_depth = (
        ResolutionDepth.DIRECT_ONLY.value if manifests_parsed > 0 else None
    )
    # Highest per-axis deps_assessed any engine claims (honest max coverage).
    assessed_by_axis: dict[str, int] = {}
    for result in engine_results:
        for engine_coverage in result.coverage:
            assessed_by_axis[engine_coverage.axis] = max(
                assessed_by_axis.get(engine_coverage.axis, 0),
                engine_coverage.deps_assessed,
            )
    coverage = tuple(
        AxisCoverage(
            axis=axis,
            manifests_found=manifests_found,
            manifests_parsed=manifests_parsed,
            deps_total=inventory.count,
            deps_assessed=min(assessed_by_axis.get(axis, 0), inventory.count),
            resolution_depth=resolution_depth,
        )
        for axis in _REPORT_AXES
    )
    return ComplianceReport(
        schema_version=REPORT_SCHEMA_VERSION,
        tool_name=TOOL_NAME,
        tool_version=__version__,
        status=status,
        status_driver=driver,
        exit_code=exit_code_for(status),
        findings=tuple(findings),
        coverage=coverage,
        vuln_data=VulnData(source=None, snapshot_at=None, max_age_ok=None),
        inventory_count=inventory.count,
        resolved_scan_set=inventory.resolved_scan_set,
        errors=tuple(errors),
    )


def render_json(report: ComplianceReport) -> str:
    """Render the report as ONE deterministic, schema-valid JSON document.

    Self-validates against the packaged schema before emit — an invalid
    document raises here (fail-loud) instead of contaminating stdout."""
    document = report.to_json_dict()
    jsonschema.Draft202012Validator(_packaged_schema()).validate(document)
    return json.dumps(
        document,
        sort_keys=True,
        ensure_ascii=True,
        indent=2,
        separators=(",", ": "),
    )
