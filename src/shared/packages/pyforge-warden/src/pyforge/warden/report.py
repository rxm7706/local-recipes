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
* ``render_text`` (Story 1.8) builds its lines from ``to_json_dict()`` — the
  SAME deterministically-sorted shape ``render_json`` emits — instead of
  iterating ``report.findings``/``report.errors`` directly: a second,
  independently-maintained sort in this function would risk the two
  renderers silently disagreeing on order across a future field-growth
  event. Its output is explicitly NON-CONTRACT (free-format lines, never
  schema-validated) — only ``render_json``'s document is the contract.
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
* ``allow_empty`` (Story 1.9, additive/defaulted) — threaded straight
  through into ``verdict.exit_code_for(status, driver=driver,
  allow_empty=allow_empty)``; this module owns no exit-projection logic of
  its own (``verdict.py`` is the sole owner), so its only role here is
  plumbing the caller's flag alongside the composed driver.
* ``empty_extraction`` (Story 1.9, D2(c), additive/defaulted) — mirrors
  ``hygiene_applicable``'s override shape: this module has no rung-
  counting vocabulary of its own (that's ``cli.py``'s domain — the
  ``manifests_parsed > 0 and not rungs`` gate), so the caller states the
  claim. ``True`` forces BOTH axes' ``resolution_depth`` to ``None`` (the
  same "no claim" shape the not-applicable/empty-tree path already uses,
  taking priority even over ``has_locked_closure``) instead of the
  ``direct-only``/``locked-closure`` claim a positive ``manifests_parsed``/
  ``has_locked_closure`` would otherwise produce — a manifest that parsed
  but yielded nothing extractable has nothing honest to claim resolution
  depth over. ``deps_total``/``deps_assessed`` need no separate override:
  the D2(c) condition already implies ``inventory.count == 0``, so they
  are already the honest 0/0 without this flag's help. This is the
  mechanical realization of epics.md story 1.9's AC text "the exit
  downgrades to 0 with ``coverage: none`` recorded". The default ``False``
  preserves every pre-1.9 caller/test byte-for-byte.

Status/exit projection is delegated wholesale to ``verdict.py`` (the sole
owner); this module feeds it the collected rungs and stores the result.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from functools import lru_cache
from importlib import resources
from typing import Any, cast

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
    SeverityTier,
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
    allow_empty: bool = False,
    empty_extraction: bool = False,
    fail_under_coverage: float = 0.0,
) -> ComplianceReport:
    """Assemble the ``ComplianceReport`` from the pipeline's outputs.

    ``verdict.compose`` picks the winning rung; ``verdict.exit_code_for``
    projects it (now given ``driver``/``allow_empty`` too — Story 1.9's one
    sanctioned flag-driven exit exception). ``ComplianceReport.__post_init__``
    then enforces the status/exit/driver coherence invariants at
    construction.

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
    and the vulnerability axis are untouched.

    ``empty_extraction=True`` (Story 1.9, D2(c)) forces BOTH axes'
    ``resolution_depth`` to ``None`` — see the module docstring.

    ``fail_under_coverage`` (Story 3.1, default ``0.0``/off — FR19's
    coverage-floor role): once per-axis coverage below is computed, an axis
    with ``deps_total > 0`` whose ``deps_assessed/deps_total*100`` falls
    below the floor composes one ``indeterminate:coverage-floor:<axis>``
    rung with a paired ``Finding`` — closing deferred-work.md's remaining
    zero-real-analysis gap (a project an engine can't resolve for reasons
    internal to itself emits no findings, so the pre-3.1 report read fully-
    covered/clean for that reason) whenever a caller actually configures a
    floor. A ``deps_total == 0`` axis (not-applicable, or a genuinely empty
    scan) is never flagged — a percentage has nothing to be computed over.
    At the default (``0``), a percentage is never negative, so the
    comparison structurally never fires (a no-op)."""
    findings = list(findings)
    rungs = list(rungs)
    resolution_depth = (
        None
        if empty_extraction
        else (
            ResolutionDepth.LOCKED_CLOSURE.value
            if has_locked_closure
            else (
                ResolutionDepth.DIRECT_ONLY.value if manifests_parsed > 0 else None
            )
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

    # Story 3.1 (FR19's coverage-floor role, opt-in): an axis whose assessed
    # fraction falls below fail_under_coverage composes one
    # indeterminate:coverage-floor:<axis> rung + paired Finding -- a real
    # gate, never a silent pass on zero real analysis (deferred-work.md).
    # deps_total == 0 (not-applicable, or a genuinely empty scan) is vacuous
    # -- nothing to assess, never flagged.
    for axis_coverage in coverage:
        if axis_coverage.deps_total == 0:
            continue
        pct = axis_coverage.deps_assessed / axis_coverage.deps_total * 100
        if pct < fail_under_coverage:
            finding_id = f"indeterminate:coverage-floor:{axis_coverage.axis}"
            findings.append(
                Finding(
                    id=finding_id,
                    axis=axis_coverage.axis,
                    message=(
                        f"{axis_coverage.axis}: only {pct:.1f}% of "
                        f"{axis_coverage.deps_total} dependencies assessed "
                        f"({axis_coverage.deps_assessed} assessed) -- below "
                        f"the configured {fail_under_coverage:.1f}% "
                        "coverage floor"
                    ),
                    subject=axis_coverage.axis,
                    severity=None,
                )
            )
            rungs.append(
                (
                    Status.INDETERMINATE,
                    StatusDriver(axis=axis_coverage.axis, finding_id=finding_id),
                )
            )

    status, driver = compose(rungs)
    return ComplianceReport(
        schema_version=REPORT_SCHEMA_VERSION,
        tool_name=TOOL_NAME,
        tool_version=__version__,
        status=status,
        status_driver=driver,
        exit_code=exit_code_for(status, driver=driver, allow_empty=allow_empty),
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


def _single_line(text: str) -> str:
    """Neutralize embedded line breaks so one finding/error's ``message``
    can never fabricate extra ``render_text`` lines (Story 1.8 review
    finding, 2026-07-17). Unlike ``Finding.id`` (regex-guarded against
    ``\\n`` at construction), ``message`` is engine/exception-derived free
    text — e.g. deptry's own JSON message field, or a raw ``str(exc)`` at a
    ``cli.py`` error seam — with no such guarantee. A message containing
    ``\\n  driver: axis=...`` would otherwise render as a second,
    indistinguishable-from-real line in this explicitly human-facing,
    non-schema-validated output."""
    return text.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")


def render_text(report: ComplianceReport) -> str:
    """Render the report as a human-readable, explicitly NON-CONTRACT summary.

    Built from ``report.to_json_dict()`` — the same deterministically-sorted
    shape ``render_json`` emits (see the module docstring) — never a second,
    independently-maintained sort. One verdict line (tool, status, exit
    code, finding count), a driver line when the status carries one, then
    one line per finding (axis, severity tier, id, message) and one line
    per error (kind, owner, message), both in ``to_json_dict()``'s sorted
    order. Free-format lines: unlike ``render_json``'s document, this
    output is never schema-validated. Every ``message`` is passed through
    ``_single_line`` first — see its docstring."""
    # to_json_dict()'s declared return type is dict[str, object] (every
    # nested value equally untyped) -- it is JSON-primitive data, not a
    # typed structure, so the cast is the honest boundary rather than
    # threading `object` narrowing through every access below.
    document = cast(dict[str, Any], report.to_json_dict())
    status = document["status"]
    lines = [
        f"{TOOL_NAME}: status={status['value']} "
        f"exit_code={document['exit_code']} findings={len(document['findings'])}"
    ]
    driver = status["driver"]
    if driver is not None:
        lines.append(f"  driver: axis={driver['axis']} id={driver['finding_id']}")
    for finding in document["findings"]:
        severity = finding["severity"]
        tier = severity["tier"] if severity is not None else SeverityTier.NONE.value
        message = _single_line(finding["message"])
        lines.append(f"  [{finding['axis']}] {tier} {finding['id']} -- {message}")
    for error in document["errors"]:
        message = _single_line(error["message"])
        lines.append(f"  [error:{error['kind']}] {error['owner']} -- {message}")
    return "\n".join(lines)
