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
* ``vuln_data`` is a REQUIRED caller-supplied parameter (Story 1.5) — this
  module has no clock and derives no vuln provenance itself; ``cli.py``
  derives it from ``engine_results`` (an all-``None`` ``VulnData`` when no
  engine populated one, e.g. under the null engine or a hygiene-only run).
* ``has_locked_closure`` (Story 2.6, additive/defaulted) — this module has
  no lockfile-kind vocabulary (that's ``discovery.py``'s domain), so the
  caller (``cli.py``) states whether any parsed manifest was a lockfile.
  ``True`` claims ``resolution_depth=ResolutionDepth.LOCKED_CLOSURE`` for
  BOTH axes instead of the direct-only-if-parsed default; ``False`` (the
  default) preserves every pre-2.6 caller/test byte-for-byte.
* ``hygiene_applicable`` (Story 2.4, AC3, additive/defaulted) — mirrors
  ``has_locked_closure``'s precedent exactly: this module has no
  filesystem-walk vocabulary (that's ``hygiene.has_adjacent_python_source``,
  consulted by ``cli.py`` before ``DeptryEngine`` even runs), so the caller
  states the claim. ``False`` overrides the hygiene axis's ``deps_total``/
  ``deps_assessed``/``resolution_depth`` to the not-applicable shape
  (``0``/``0``/``None``) regardless of what any engine's own coverage
  claims — this module already ignores each engine's own ``deps_total``/
  ``resolution_depth`` (see below) and recomputes them itself, so merely
  having ``DeptryEngine`` not run only zeroes ``deps_assessed``, which
  still reads as "0 of N assessed" (a coverage FAILURE) rather than "0
  total, not applicable" (an honest scope exclusion) without this override.
  ``manifests_found``/``manifests_parsed`` and the vulnerability axis are
  untouched; the default ``True`` preserves every pre-2.4 caller/test
  byte-for-byte.

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
TOOL_NAME = "warden"

# The two v1 axes every 1.2 report covers (an OPEN string mechanism — a
# license/SAST axis lands additively later).
_REPORT_AXES = (AXIS_HYGIENE, AXIS_VULNERABILITY)


@lru_cache(maxsize=1)
def _packaged_schema() -> dict[str, object]:
    schema_file = (
        resources.files("pyforge.warden") / "data" / "report-schema.json"
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
    vuln_data: VulnData,
    engine_results: Sequence[EngineResult] = (),
    has_locked_closure: bool = False,
    hygiene_applicable: bool = True,
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
    axis with no engine coverage claim stays ``deps_assessed=0`` — the
    truthful "nothing assessed" (Story 1.5 gives ``OsvEngine`` the same
    claim on the vulnerability axis).

    ``vuln_data`` is caller-derived (Story 1.5: ``cli.py`` picks the first
    non-``None`` ``EngineResult.vuln_data`` across ``engine_results``, else
    an all-``None`` ``VulnData``) — this function stores it verbatim, never
    hardcoding it.

    ``hygiene_applicable=False`` (Story 2.4, AC3) overrides the hygiene
    axis's ``deps_total``/``deps_assessed``/``resolution_depth`` to the
    not-applicable shape (``0``/``0``/``None``) regardless of what any
    engine's own coverage claims; ``manifests_found``/``manifests_parsed``
    and the vulnerability axis are untouched."""
    status, driver = compose(rungs)
    resolution_depth = (
        ResolutionDepth.LOCKED_CLOSURE.value
        if has_locked_closure
        else (
            ResolutionDepth.DIRECT_ONLY.value if manifests_parsed > 0 else None
        )
    )
    # Highest per-axis deps_assessed any engine claims (honest max coverage).
    assessed_by_axis: dict[str, int] = {}
    for result in engine_results:
        for engine_coverage in result.coverage:
            assessed_by_axis[engine_coverage.axis] = max(
                assessed_by_axis.get(engine_coverage.axis, 0),
                engine_coverage.deps_assessed,
            )
    coverage = []
    for axis in _REPORT_AXES:
        # AC3: an inapplicable hygiene axis overrides deps_total/deps_assessed/
        # resolution_depth to the not-applicable shape regardless of what any
        # engine's own coverage claims (deps_assessed alone would still read
        # as "0 of N assessed" -- a coverage FAILURE -- rather than "0 total,
        # not applicable" -- an honest scope exclusion).
        not_applicable = axis == AXIS_HYGIENE and not hygiene_applicable
        coverage.append(
            AxisCoverage(
                axis=axis,
                manifests_found=manifests_found,
                manifests_parsed=manifests_parsed,
                deps_total=0 if not_applicable else inventory.count,
                deps_assessed=(
                    0
                    if not_applicable
                    else min(assessed_by_axis.get(axis, 0), inventory.count)
                ),
                resolution_depth=None if not_applicable else resolution_depth,
            )
        )
    coverage = tuple(coverage)
    return ComplianceReport(
        schema_version=REPORT_SCHEMA_VERSION,
        tool_name=TOOL_NAME,
        tool_version=__version__,
        status=status,
        status_driver=driver,
        exit_code=exit_code_for(status),
        findings=tuple(findings),
        coverage=coverage,
        vuln_data=vuln_data,
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
