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
* ``applied_waivers`` (Story 3.2, additive/defaulted) -- ``render_text``
  appends one line per ``waiver.WaiverNotice`` (id, reason, authorized_by,
  expires_at) after the finding/error lines. This module has no
  waiver-matching vocabulary of its own (that's ``waiver.py``'s domain), so
  the caller (``cli.py``) states which waivers actually suppressed a
  finding this run. Every notice's ``reason`` passes through
  ``_single_line`` first, same as every finding/error ``message``. The
  default ``()`` preserves every pre-3.2 caller/test byte-for-byte.
* ``expired_waivers``/``warn_only``/``warn_only_downgraded`` (Story 3.3,
  additive/defaulted) -- ``expired_waivers`` gets its own ``[waiver-
  expired]`` line per notice (an exact id match whose ``expires_at`` had
  already passed; ``apply_waivers`` left that rung's own re-block
  untouched -- this line only makes the fall-through visible for review).
  Its wording deliberately never asserts the finding is unconditionally
  still re-blocked: a coincident ``--warn-only`` can downgrade that same
  rung to ``warn``, so the status=/exit_code= summary line (already
  correct) is what states the actual current outcome. Both the
  pre-existing ``[waiver]`` loop and the new ``[waiver-expired]`` loop pass
  ``authorized_by``/``expires_at`` through ``_single_line`` too (Story 3.3
  review finding: previously only ``reason`` was sanitized in either loop
  -- an embedded newline in ``authorized_by`` forged an extra report
  line). ``warn_only``/``warn_only_downgraded`` gate a single
  graduate-to-enforcing nudge line, added ONLY when ALL THREE of
  ``warn_only``, ``status["value"] == "warn"``, and
  ``warn_only_downgraded > 0`` hold -- ``status == "warn"`` ALONE is not
  sufficient, since a report can compose ``warn`` for a reason
  ``--warn-only`` had nothing to do with (a native hygiene ``warn``-tier
  finding, or a finding a committed waiver already suppressed to some
  other rung). The nudge names the exact, correctly-pluralized downgraded-
  finding count (never ``len(report.findings)``, which would also count
  findings ``--warn-only`` never touched) and states that DROPPING
  ``--warn-only`` re-enables enforcement -- never implying ``--fail-on``
  alone suffices, since ``warn_blocking`` downgrades unconditionally
  regardless of the configured severity floor (only the COUNT of findings
  it downgrades can vary with ``--fail-on``, not the final status/exit
  code). The defaults (``()``/``False``/``0``) preserve every pre-3.3
  caller/test byte-for-byte.
* ``applied_baseline``/``expired_baseline`` (Story 6.8, additive/defaulted
  ``()`` -- mirrors ``applied_waivers``/``expired_waivers`` exactly, one
  feed over): ``render_text`` appends one ``[baseline]`` line per applied
  ``waiver.BaselineNotice`` (id, reason, expires_at -- no
  ``authorized_by``, since a baseline notice carries none) and one
  ``[baseline-expired]`` line per expired one, both AFTER the existing
  waiver loops. Every notice's ``reason``/``expires_at`` passes through
  ``_single_line`` first, same as the waiver loops. This module has no
  baseline-matching vocabulary of its own (that's ``waiver.py``'s
  domain), so the caller (``cli.py``) states which baseline entries
  actually suppressed a finding this run. The defaults preserve every
  pre-6.8 caller/test byte-for-byte.
* ``manifest_locations``/``fixed_versions`` (Story 5.1, AC1, additive/
  defaulted ``{}`` -- the render_text-only remediation-content side channel,
  mirroring ``applied_waivers``/``applied_baseline``'s established caller-
  supplied-param precedent exactly): ``render_text`` appends one remediation
  line (``      -> fix: ...``) right after each rendered finding line,
  templated per id-family/axis by the new private ``_remediation_line`` --
  never for ``errors[]`` (AC1's "not a re-wrap of 1.7's typed errors" scopes
  this to finding diagnostics only). This module has no manifest-provenance
  or fixed-version vocabulary of its own (``inventory.Component.provenance``
  and ``vuln.OsvParse.fixed_versions`` are -- respectively -- ``inventory.py``'s
  and ``vuln.py``'s domains), so the caller (``cli.py``) states both: a
  ``name -> tuple("<manifest> [<section>]", ...)`` lookup built once from the
  post-merge inventory (keys canonicalized via ``_canonical_subject_key``;
  the lookup canonicalizes the subject the same way), and a ``finding.id ->
  fixed version string`` mapping merged across every engine result. A finding whose ``subject`` has no
  entry in ``manifest_locations`` (e.g. this module's own synthetic
  ``indeterminate:coverage-floor:<axis>`` finding, whose ``subject`` is an
  axis name, not a package) simply omits the manifest clause -- never
  crashes, never fabricates a location. The composed remediation string
  passes through ``_single_line`` too, same as every other free-text field.
  The defaults keep every pre-5.1 call site signature-compatible, but they
  do NOT reproduce pre-5.1 output (unlike the parameters above): AC1 makes
  the remediation line unconditional per finding, so a defaulted call still
  renders it — the defaults only omit the manifest-clause/fixed-version
  enrichment (this story updated four pre-existing byte-exact tests for
  exactly that reason).

Status/exit projection is delegated wholesale to ``verdict.py`` (the sole
owner); this module feeds it the collected rungs and stores the result.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from functools import lru_cache
from importlib import resources
from types import MappingProxyType
from typing import Any, cast

import jsonschema

from . import __version__
from .interfaces import EngineResult
from .inventory import ResolvedInventory
from .models import (
    AXIS_CURRENCY,
    AXIS_HYGIENE,
    AXIS_LICENSE,
    AXIS_VULNERABILITY,
    AxisCoverage,
    ComplianceReport,
    ErrorRecord,
    FeedProvenance,
    Finding,
    ResolutionDepth,
    SeverityTier,
    Status,
    StatusDriver,
    SuppressedFinding,
    VulnData,
)
from .verdict import compose, exit_code_for
from .waiver import BaselineNotice, WaiverNotice

# Story 6.1: the one sanctioned additive schema bump (1.0.0 -> 1.1.0, staying
# inside _SCHEMA_VERSION_RE) admitting Epic 6's slots; behavior-neutral for
# shipped scans (only schema_version + the two new coverage rows change).
REPORT_SCHEMA_VERSION = "1.1.0"
TOOL_NAME = "warden"

# The v1 axes every report covers (an OPEN string mechanism). Story 6.1 widens
# this to four — license/currency register here so their coverage rows are
# emitted (deps_assessed=0 until the 6.2/6.3 producers run); an assessed axis
# NOT in this tuple is a hard error (F6), never silently dropped.
_REPORT_AXES = (AXIS_HYGIENE, AXIS_VULNERABILITY, AXIS_LICENSE, AXIS_CURRENCY)


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
    suppressions: Sequence[SuppressedFinding] = (),
    kev_data: FeedProvenance | None = None,
    epss_data: FeedProvenance | None = None,
    license_gating: bool = False,
    currency_data: FeedProvenance | None = None,
    currency_gating: bool = False,
    warn_as_error: bool = False,
    actuation: object | None = None,
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

    ``kev_data`` (Story 6.4, additive/defaulted ``None`` — mirrors
    ``vuln_data``'s own threading exactly): caller-derived too (``cli.py``
    picks the first non-``None`` ``EngineResult.kev_data`` across
    ``engine_results``) and stored verbatim into ``ComplianceReport.
    kev_data``; this module never computes KEV provenance itself.

    ``epss_data`` (Story 6.7, additive/defaulted ``None`` — mirrors
    ``kev_data``'s own threading exactly, one feed over): caller-derived too
    (``cli.py`` picks the first non-``None`` ``EngineResult.epss_data``
    across ``engine_results``) and stored verbatim into ``ComplianceReport.
    epss_data``; this module never computes EPSS provenance itself.

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
    comparison structurally never fires (a no-op).

    ``license_gating`` (Story 6.2, default ``False`` — every pre-6.2 caller's
    behavior, unchanged): ``cli.py`` passes ``config.license_gating``
    (``True`` iff ``--allow-licenses``/``--deny-licenses`` is set) into the
    license axis's OWN ``AxisCoverage.gating`` — every other axis's row
    keeps the field's own default (``False``). Transparency of
    configuration state (FR37's "gating: false is honesty, not
    invisibility"); the actual license-axis rung escalation this gate drives
    is threaded separately through ``DefaultPolicy.evaluate`` ->
    ``license_rung(policy=config.license_policy)`` (Story 6.5), not here —
    this row only reports whether the gate is configured.

    Fix 8 (review finding, 2026-07-18): ``gating`` is additionally gated on
    the axis actually being applicable/assessed (``AXIS_LICENSE in
    assessed_by_axis`` — the SAME condition ``not_applicable`` already
    computes for ``deps_total``/``deps_assessed``/``resolution_depth`` in
    the coverage-row loop below), so ``config.license_gating`` alone can
    never claim ``gating: true`` for a scan where the license engine never
    ran (e.g. ``manifests_parsed == 0``) — that combination was
    self-contradictory (an active gate over zero assessed dependencies).

    ``currency_data``/``currency_gating`` (Story 6.3, additive/defaulted —
    mirror ``kev_data``/``license_gating`` exactly): ``cli.py`` picks the
    first non-``None`` ``EngineResult.currency_data`` across
    ``engine_results`` (the bundled LTS registry's own ``FeedProvenance``,
    see ``currency.py``'s module docstring) and passes ``config.
    currency_gating`` (``True`` iff ``--max-lag``/``--require-lts``/
    ``--fail-on-eol`` is set) into the currency axis's own ``AxisCoverage.
    gating``, gated on axis applicability the SAME way ``license_gating`` is
    (Fix 8's pattern, applied identically here).

    ``warn_as_error`` (Story 6.5, additive/defaulted ``False`` — the
    strict-shop exit knob): threaded straight through into ``verdict.
    exit_code_for(status, …, warn_is_error=warn_as_error)``, exactly like
    ``allow_empty`` — this module owns no exit-projection logic of its own
    (``verdict.py`` is the sole owner), so its only role here is plumbing
    ``cli.py``'s ``--warn-as-error`` flag alongside the composed driver. It
    never changes the composed status or any rung; it only makes a ``warn``
    STATUS project to a non-zero exit (orthogonal to ``--warn-only``, which
    downgrades blocking rungs pre-compose).

    ``actuation`` (Story 6.9, additive/defaulted ``None`` -- the frozen 6.1
    ``ComplianceReport.actuation`` slot, populated not edited): ``cli.py``
    passes the fix-PR actuator's ``Actuation.to_json_dict()`` payload (a
    JSON-serializable dict) verbatim, or ``None`` when neither
    ``--open-fix-prs``/``--fix-prs-dry-run`` is set. Stored pass-through into
    ``ComplianceReport.actuation`` (models.py already serializes it verbatim);
    it never touches any rung, the composed status, or the exit code."""
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
    # F6 (Story 6.1): a coverage claim for an axis NOT registered in
    # _REPORT_AXES is a hard error — the pre-6.1 loop below silently dropped
    # it (it only emits rows for registered axes), which would let a producer
    # bug pass unnoticed.
    unregistered = sorted(set(assessed_by_axis) - set(_REPORT_AXES))
    if unregistered:
        raise ValueError(
            f"coverage claim for unregistered axis/axes {unregistered!r} — "
            f"every assessed axis must be registered in _REPORT_AXES "
            f"{list(_REPORT_AXES)!r} (F6: never silently dropped)"
        )
    coverage = []
    for axis in _REPORT_AXES:
        # AC3: an inapplicable hygiene axis overrides deps_total/deps_assessed/
        # resolution_depth to the not-applicable shape regardless of what any
        # engine's own coverage claims (deps_assessed alone would still read
        # as "0 of N assessed" -- a coverage FAILURE -- rather than "0 total,
        # not applicable" -- an honest scope exclusion).
        #
        # Story 6.1: license/currency register here so their rows are emitted,
        # but they have no producer yet -- an axis with NO engine coverage
        # claim is honestly not-applicable (deps_total=0), NOT "0 of N
        # assessed" (which --fail-under-coverage would flag, an unsanctioned
        # verdict change). Behavior-neutral, and forward-compatible: a 6.2/6.3
        # producer registering an EngineResult coverage claim flips the axis
        # applicable automatically (it enters assessed_by_axis).
        not_applicable = (axis == AXIS_HYGIENE and not hygiene_applicable) or (
            axis in (AXIS_LICENSE, AXIS_CURRENCY) and axis not in assessed_by_axis
        )
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
                # Fix 8 (review finding, 2026-07-18): gate `gating` the SAME
                # way `not_applicable` already gates deps_total/deps_assessed/
                # resolution_depth above -- config.license_gating threaded in
                # alone let a manifests_parsed==0 scan (the license engine
                # never runs; AXIS_LICENSE never enters assessed_by_axis)
                # report gating=true alongside deps_total=0/deps_assessed=0,
                # self-contradictory ("the gate is active" + "nothing was
                # assessed"). `not not_applicable` for AXIS_LICENSE is exactly
                # "AXIS_LICENSE in assessed_by_axis" per the not_applicable
                # expression above. Story 6.3: the currency axis mirrors this
                # identically via currency_gating.
                gating=(
                    (license_gating and not not_applicable)
                    if axis == AXIS_LICENSE
                    else (currency_gating and not not_applicable)
                    if axis == AXIS_CURRENCY
                    else False
                ),
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
        exit_code=exit_code_for(
            status,
            driver=driver,
            allow_empty=allow_empty,
            warn_is_error=warn_as_error,
        ),
        findings=tuple(findings),
        coverage=coverage,
        vuln_data=vuln_data,
        inventory_count=inventory.count,
        resolved_scan_set=inventory.resolved_scan_set,
        errors=tuple(errors),
        suppressions=tuple(suppressions),
        kev_data=kev_data,
        epss_data=epss_data,
        currency_data=currency_data,
        actuation=actuation,
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


_CANONICAL_KEY_RUNS = re.compile(r"[-_.]+")


def _canonical_subject_key(name: str) -> str:
    """PEP-503-canonicalize a ``manifest_locations`` key / lookup subject
    (``Foo_Bar``/``foo.bar``/``foo-bar`` collapse to ``foo-bar`` — the same
    normalization ``inventory``'s identity merge already applies). Review
    finding (2026-07-24): a manifest may declare a non-normalized spelling
    while osv-scanner echoes the normalized one — without collapsing both
    sides, the clause silently misses though the location data is present.
    Two spellings that collapse together ARE the same PyPI package, so the
    resulting union is correct, never a cross-attribution."""
    return _CANONICAL_KEY_RUNS.sub("-", name).lower()


def _manifest_clause(
    subject: str | None, manifest_locations: Mapping[str, tuple[str, ...]]
) -> str:
    """The ``" (declared in <manifest> [<section>]; ...)"`` clause a
    remediation line appends when ``subject`` has a known declaration site
    — empty string (never fabricated) when ``subject`` is ``None`` or has
    no entry in ``manifest_locations`` (Story 5.1's own synthetic
    ``indeterminate:coverage-floor:<axis>`` finding, whose ``subject`` is an
    axis name, hits this path every time). Keys are matched via
    ``_canonical_subject_key`` — ``cli.py``'s build site canonicalizes the
    keys with the same helper."""
    if subject is None:
        return ""
    locations = manifest_locations.get(_canonical_subject_key(subject))
    if not locations:
        return ""
    return f" (declared in {'; '.join(locations)})"


# Concrete next-action text per hygiene DEP-code (deptry's own semantics,
# verified against the installed deptry 0.25.1 violation classes — mirrors
# hygiene.py's own DEP005 docstring precedent of reading deptry's real
# behavior rather than guessing): DEP001 = imported but not declared ->
# declare it; DEP002 = declared but unused -> remove it; DEP003 = imported
# but only a transitive dependency -> declare it directly; DEP004 = imported
# in non-dev code but declared as a dev dependency -> move dependency
# groups; DEP005 = declared but part of the standard library -> remove it,
# redundant. Review finding (2026-07-24): deptry's ``module`` field — the
# finding ``subject`` — is an IMPORT name for the imported-side codes
# (DEP001/DEP003/DEP004: ``cv2``/``yaml``/``PIL``, not the distribution
# ``opencv-python``/``pyyaml``/``pillow``), so those templates say "the
# distribution that provides {subject}" rather than presenting the import
# name itself as manifest-declarable; the declared-side codes
# (DEP002/DEP005) already carry the declared name and stay direct.
_DEP_CODE_ACTIONS: Mapping[str, str] = MappingProxyType(
    {
        "DEP001": (
            "declare the distribution that provides {subject} in the "
            "manifest -- {subject} is imported but not currently declared"
        ),
        "DEP002": (
            "remove {subject} from the manifest -- it is declared but not "
            "used in the codebase"
        ),
        "DEP003": (
            "add the distribution that provides {subject} as a direct "
            "dependency in the manifest -- it is currently only available "
            "transitively"
        ),
        "DEP004": (
            "move the distribution that provides {subject} out of the "
            "dev-dependency group in the manifest -- it is imported in "
            "non-dev code"
        ),
        "DEP005": (
            "remove {subject} from the manifest -- it is part of the "
            "Python standard library"
        ),
    }
)


def _dep_code_action(code: str, subject: str) -> str:
    """The concrete next action for one hygiene DEP-code — an unrecognized
    future code (never one of the five ``_DEP_CODE_ACTIONS`` keys) degrades
    to a generic review action, never a crash."""
    template = _DEP_CODE_ACTIONS.get(code)
    if template is None:
        return f"review the {code} finding for {subject} and update the manifest accordingly"
    return template.format(subject=subject)


def _remediation_line(
    finding: dict[str, Any],
    *,
    manifest_locations: Mapping[str, tuple[str, ...]],
    fixed_versions: Mapping[str, str],
) -> str | None:
    """One concrete remediation action per finding (AC1), templated per
    id-family/axis — appended by ``render_text`` right after the finding's
    own line. Never merely re-states ``finding['message']``: each family
    names its own specific identity (advisory id + severity + fixed-version
    for vuln, the DEP-code for hygiene, the SPDX expression for license, the
    eol_date/lag for currency, the reason token for indeterminate:), the
    declaring manifest(s)+section(s) when known (``_manifest_clause``), and
    a concrete next action. Returns ``None`` only for a finding id matching
    none of the five frozen id families (unreachable given ``Finding.
    __post_init__``'s own grammar guard, but defensive per this module's
    never-crash ethos — never a fabricated location, never a raise)."""
    finding_id: str = finding["id"]
    raw_subject = finding["subject"]
    subject = raw_subject if raw_subject is not None else "the dependency"
    manifest_clause = _manifest_clause(raw_subject, manifest_locations)

    if finding_id.startswith("vuln:"):
        _, advisory_id, _ = finding_id.split(":", 2)
        fixed = fixed_versions.get(finding_id)
        if fixed is not None:
            action = f"upgrade {subject} to >= {fixed} to resolve {advisory_id}"
        else:
            # Review finding (2026-07-24): a missing fixed_versions entry
            # means no fixed version was RECORDED in the advisory data we
            # read (e.g. a versions:-only or GIT-ranges-only record) -- it
            # does NOT prove no fix exists upstream. The line must not
            # assert worldwide absence and steer a user toward a waiver
            # when an upgrade may exist.
            action = (
                f"no fixed version is recorded in the advisory data for "
                f"{advisory_id} affecting {subject} -- check the advisory "
                "upstream, or consider a waiver or removing the dependency"
            )
        return f"{action}{manifest_clause}"

    if finding_id.startswith("hygiene:"):
        _, code, _ = finding_id.split(":", 2)
        return f"{_dep_code_action(code, subject)}{manifest_clause}"

    if finding_id.startswith("license:"):
        license_info = finding.get("license") or {}
        if license_info.get("verdict") == "denied":
            expression = license_info.get("expression") or "unknown"
            action = (
                f"{subject}: license {expression} is denied by policy -- "
                "replace the dependency or add a waiver"
            )
        else:
            action = (
                f"{subject}: license could not be resolved -- verify "
                "manually or add a waiver"
            )
        return f"{action}{manifest_clause}"

    if finding_id.startswith("currency:"):
        reason = finding_id.split(":", 2)[1]  # eol | over-lag | unknown
        currency_info = finding.get("currency") or {}
        if reason == "eol":
            eol_date = currency_info.get("eol_date") or "unknown"
            action = (
                f"{subject}: reached end-of-life ({eol_date}) -- upgrade to "
                "a supported release"
            )
        elif reason == "over-lag":
            lag = currency_info.get("lag")
            latest = currency_info.get("latest") or "the latest release"
            action = (
                f"{subject}: {lag} release(s) behind {latest} -- upgrade "
                "to close the gap"
            )
        else:
            action = (
                f"{subject}: currency could not be resolved -- verify "
                "manually or add a waiver"
            )
        return f"{action}{manifest_clause}"

    if finding_id.startswith("indeterminate:"):
        reason = finding_id.split(":", 2)[1]
        action = (
            f"{subject}: investigate the {reason!r} condition and resolve "
            "it, or add a waiver"
        )
        return f"{action}{manifest_clause}"

    return None


def render_text(
    report: ComplianceReport,
    *,
    applied_waivers: Sequence[WaiverNotice] = (),
    expired_waivers: Sequence[WaiverNotice] = (),
    applied_baseline: Sequence[BaselineNotice] = (),
    expired_baseline: Sequence[BaselineNotice] = (),
    warn_only: bool = False,
    warn_only_downgraded: int = 0,
    actuation: object | None = None,
    manifest_locations: Mapping[str, tuple[str, ...]] = MappingProxyType({}),
    fixed_versions: Mapping[str, str] = MappingProxyType({}),
) -> str:
    """Render the report as a human-readable, explicitly NON-CONTRACT summary.

    Built from ``report.to_json_dict()`` — the same deterministically-sorted
    shape ``render_json`` emits (see the module docstring) — never a second,
    independently-maintained sort. One verdict line (tool, status, exit
    code, finding count), a driver line when the status carries one, then
    one line per finding (axis, severity tier, id, message) — immediately
    followed by one remediation line (Story 5.1, AC1; ``      -> fix:
    ...``, via the new private ``_remediation_line``, templated per
    id-family/axis from ``manifest_locations``/``fixed_versions`` — see the
    module docstring; ``None`` omits the line, never fabricates one) — and
    one line per error (kind, owner, message; errors[] get NO remediation
    line), both in ``to_json_dict()``'s sorted order, then one line per
    ``applied_waivers`` notice (Story 3.2; id, reason, authorized_by,
    expires_at) and one line per ``expired_waivers`` notice (Story 3.3;
    same four fields, ``[waiver-expired]`` marker, non-"re-blocked" wording
    — see the module docstring), then one line per ``applied_baseline``
    notice (Story 6.8; id, reason, expires_at — no ``authorized_by``) and
    one line per ``expired_baseline`` notice (same three fields,
    ``[baseline-expired]`` marker, same non-"re-blocked" wording), all four
    in caller-supplied order, then (Story 3.3) at most one graduate-to-
    enforcing nudge line when ``warn_only`` is set, the composed status is
    ``warn``, and ``warn_only_downgraded > 0`` (see the module docstring
    for why all three are required), then (Story 6.9) one ``[actuation]``
    line per fix-PR outcome (``<status> <action> <finding_id>[ ->
    <pr_url>]``) when ``actuation`` is a non-``None`` payload dict.
    Free-format lines: unlike ``render_json``'s document, this output is
    never schema-validated. Every ``message``/``reason``/``authorized_by``/
    ``expires_at``/remediation string is passed through ``_single_line``
    first — see its docstring."""
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
        remediation = _remediation_line(
            finding,
            manifest_locations=manifest_locations,
            fixed_versions=fixed_versions,
        )
        if remediation is not None:
            lines.append(f"      -> fix: {_single_line(remediation)}")
    for error in document["errors"]:
        message = _single_line(error["message"])
        lines.append(f"  [error:{error['kind']}] {error['owner']} -- {message}")
    for notice in applied_waivers:
        reason = _single_line(notice.reason)
        authorized_by = _single_line(notice.authorized_by)
        expires_at = _single_line(notice.expires_at)
        lines.append(
            f"  [waiver] {notice.id} -- reason={reason} "
            f"authorized_by={authorized_by} expires_at={expires_at}"
        )
    for notice in expired_waivers:
        reason = _single_line(notice.reason)
        authorized_by = _single_line(notice.authorized_by)
        expires_at = _single_line(notice.expires_at)
        lines.append(
            f"  [waiver-expired] {notice.id} -- reason={reason} "
            f"authorized_by={authorized_by} expires_at={expires_at} -- "
            "expired, needs review/renewal"
        )
    for baseline_notice in applied_baseline:
        reason = _single_line(baseline_notice.reason)
        expires_at = _single_line(baseline_notice.expires_at)
        lines.append(
            f"  [baseline] {baseline_notice.id} -- reason={reason} "
            f"expires_at={expires_at}"
        )
    for baseline_notice in expired_baseline:
        reason = _single_line(baseline_notice.reason)
        expires_at = _single_line(baseline_notice.expires_at)
        lines.append(
            f"  [baseline-expired] {baseline_notice.id} -- reason={reason} "
            f"expires_at={expires_at} -- expired, needs review/renewal"
        )
    # Story 6.9: the fix-PR actuator's outcomes, one terse line each, present
    # only when --open-fix-prs/--fix-prs-dry-run ran (actuation is not None).
    # Built from the same JSON-serializable payload the report already carries
    # (already sorted by finding id); pr_url is appended only when present.
    if isinstance(actuation, dict):
        outcomes = actuation.get("outcomes")
        if isinstance(outcomes, list):
            for outcome in outcomes:
                if not isinstance(outcome, dict):
                    continue
                line = (
                    f"  [actuation] {outcome.get('status')} "
                    f"{outcome.get('action')} "
                    f"{_single_line(str(outcome.get('finding_id')))}"
                )
                pr_url = outcome.get("pr_url")
                if pr_url:
                    line += f" -> {_single_line(str(pr_url))}"
                lines.append(line)
    if warn_only and status["value"] == "warn" and warn_only_downgraded > 0:
        finding_word = "finding" if warn_only_downgraded == 1 else "findings"
        lines.append(
            f"  [warn-only] {warn_only_downgraded} {finding_word} not "
            "enforced while --warn-only is set -- drop --warn-only to "
            "re-enable enforcement"
        )
    return "\n".join(lines)
