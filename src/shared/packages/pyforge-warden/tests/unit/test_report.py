"""Unit tests — ``report.assemble_report``'s ``hygiene_applicable`` coverage
override (Story 2.4, AC3) and ``report.render_text`` in isolation (Story 1.8).

Constructs a minimal ``ResolvedInventory`` directly (no CLI, no engines) and
calls ``assemble_report`` in isolation: the ``hygiene_applicable=False``
coverage-shape override, and a regression pin that the default
(``hygiene_applicable=True``, or omitted entirely) reproduces the pre-2.4
coverage shape byte-for-byte.

The ``render_text`` tests below construct a ``ComplianceReport`` directly
(no CLI, no engines — mirrors ``tests/unit/test_models.py``'s
``_sample_report`` pattern) so ordering/driver/error behavior is pinned at
the renderer level, independent of any real scan pipeline.
"""

from __future__ import annotations

from pyforge.warden.interfaces import EngineResult
from pyforge.warden.inventory import ResolvedInventory
from pyforge.warden.models import (
    AXIS_HYGIENE,
    AXIS_INGESTION,
    AXIS_VULNERABILITY,
    AxisCoverage,
    ComplianceReport,
    ErrorKind,
    ErrorRecord,
    Finding,
    Severity,
    SeverityTier,
    Status,
    StatusDriver,
    VulnData,
)
from pyforge.warden.report import assemble_report, render_text

_NO_VULN_DATA = VulnData(source=None, snapshot_at=None, max_age_ok=None)


def _inventory(component_factory, *, count: int = 2) -> ResolvedInventory:
    components = tuple(
        component_factory(name=f"pkg{i}", version="1.0.0") for i in range(count)
    )
    return ResolvedInventory(components=components, resolved_scan_set=())


def _assemble(inventory, **overrides):
    kwargs = dict(
        inventory=inventory,
        findings=(),
        rungs=(),
        errors=(),
        manifests_found=1,
        manifests_parsed=1,
        vuln_data=_NO_VULN_DATA,
    )
    kwargs.update(overrides)
    return assemble_report(**kwargs)


def test_default_omitted_preserves_the_pre_2_4_coverage_shape(component_factory):
    inventory = _inventory(component_factory)
    report = _assemble(inventory)
    by_axis = {c.axis: c for c in report.coverage}
    assert by_axis["hygiene"].deps_total == 2
    assert by_axis["hygiene"].deps_assessed == 0
    assert by_axis["hygiene"].resolution_depth == "direct-only"
    assert by_axis["vulnerability"].deps_total == 2
    assert by_axis["vulnerability"].deps_assessed == 0
    assert by_axis["vulnerability"].resolution_depth == "direct-only"


def test_explicit_true_matches_the_default_byte_for_byte(component_factory):
    inventory = _inventory(component_factory)
    default_report = _assemble(inventory)
    explicit_report = _assemble(inventory, hygiene_applicable=True)
    assert explicit_report.coverage == default_report.coverage


def test_hygiene_not_applicable_zeroes_deps_total_and_assessed(component_factory):
    inventory = _inventory(component_factory)
    report = _assemble(inventory, hygiene_applicable=False)
    by_axis = {c.axis: c for c in report.coverage}
    assert by_axis["hygiene"].deps_total == 0
    assert by_axis["hygiene"].deps_assessed == 0
    assert by_axis["hygiene"].resolution_depth is None


def test_hygiene_not_applicable_keeps_manifest_counts_real(component_factory):
    inventory = _inventory(component_factory)
    report = _assemble(
        inventory, hygiene_applicable=False, manifests_found=3, manifests_parsed=2
    )
    by_axis = {c.axis: c for c in report.coverage}
    assert by_axis["hygiene"].manifests_found == 3
    assert by_axis["hygiene"].manifests_parsed == 2


def test_hygiene_not_applicable_leaves_the_vulnerability_axis_untouched(
    component_factory,
):
    inventory = _inventory(component_factory)
    report = _assemble(inventory, hygiene_applicable=False)
    by_axis = {c.axis: c for c in report.coverage}
    assert by_axis["vulnerability"].deps_total == 2
    assert by_axis["vulnerability"].resolution_depth == "direct-only"


def test_hygiene_not_applicable_overrides_an_engines_own_coverage_claim(
    component_factory,
):
    """The override wins regardless of what an engine's own EngineResult
    claims for the hygiene axis (the module docstring's explicit bar)."""
    inventory = _inventory(component_factory)
    engine_result = EngineResult(
        findings=(),
        errors=(),
        coverage=(
            AxisCoverage(
                axis=AXIS_HYGIENE,
                manifests_found=1,
                manifests_parsed=1,
                deps_total=2,
                deps_assessed=2,
                resolution_depth=None,
            ),
        ),
        axis=AXIS_HYGIENE,
    )
    report = _assemble(
        inventory, hygiene_applicable=False, engine_results=(engine_result,)
    )
    by_axis = {c.axis: c for c in report.coverage}
    assert by_axis["hygiene"].deps_total == 0
    assert by_axis["hygiene"].deps_assessed == 0


# --- empty_extraction (Story 1.9, D2(c)) -----------------------------------


def test_empty_extraction_forces_resolution_depth_none_on_both_axes(
    component_factory,
):
    inventory = _inventory(component_factory)
    report = _assemble(inventory, empty_extraction=True)
    by_axis = {c.axis: c for c in report.coverage}
    assert by_axis["hygiene"].resolution_depth is None
    assert by_axis["vulnerability"].resolution_depth is None


def test_empty_extraction_default_false_is_byte_identical_to_pre_amendment(
    component_factory,
):
    inventory = _inventory(component_factory)
    default_report = _assemble(inventory)
    explicit_report = _assemble(inventory, empty_extraction=False)
    assert explicit_report.coverage == default_report.coverage


def test_empty_extraction_overrides_locked_closure_too(component_factory):
    """A pathological case (an empty pixi.lock that still parses): a
    positive has_locked_closure claim must not survive empty_extraction —
    'nothing was actually resolved' outranks 'this manifest kind proves the
    transitive closure when something IS resolved'."""
    inventory = _inventory(component_factory)
    report = _assemble(
        inventory, empty_extraction=True, has_locked_closure=True
    )
    by_axis = {c.axis: c for c in report.coverage}
    assert by_axis["hygiene"].resolution_depth is None
    assert by_axis["vulnerability"].resolution_depth is None


def test_empty_extraction_does_not_touch_deps_total_or_assessed(
    component_factory,
):
    """Unlike hygiene_applicable, empty_extraction does not need to zero
    deps_total/deps_assessed itself — the D2(c) condition already implies
    inventory.count == 0, so those fields are already honest."""
    inventory = ResolvedInventory(components=(), resolved_scan_set=())
    report = _assemble(inventory, empty_extraction=True)
    by_axis = {c.axis: c for c in report.coverage}
    assert by_axis["hygiene"].deps_total == 0
    assert by_axis["vulnerability"].deps_total == 0


# --- fail_under_coverage (Story 3.1, FR19's coverage-floor role) ----------


def test_fail_under_coverage_flags_a_below_floor_axis(component_factory):
    inventory = _inventory(component_factory)
    report = _assemble(inventory, fail_under_coverage=50.0)
    finding_ids = {f.id for f in report.findings}
    assert "indeterminate:coverage-floor:hygiene" in finding_ids
    assert "indeterminate:coverage-floor:vulnerability" in finding_ids
    assert report.status is Status.INDETERMINATE
    assert report.exit_code == 1


def test_fail_under_coverage_at_or_above_floor_is_unaffected(component_factory):
    inventory = _inventory(component_factory)
    engine_result = EngineResult(
        findings=(),
        errors=(),
        coverage=(
            AxisCoverage(
                axis=AXIS_HYGIENE,
                manifests_found=1,
                manifests_parsed=1,
                deps_total=2,
                deps_assessed=2,
                resolution_depth=None,
            ),
            AxisCoverage(
                axis=AXIS_VULNERABILITY,
                manifests_found=1,
                manifests_parsed=1,
                deps_total=2,
                deps_assessed=2,
                resolution_depth=None,
            ),
        ),
        axis=AXIS_HYGIENE,
    )
    unfloored = _assemble(inventory, engine_results=(engine_result,))
    at_floor = _assemble(
        inventory, fail_under_coverage=50.0, engine_results=(engine_result,)
    )
    # 100% assessed for both axes is at-or-above a 50% floor -- byte-for-
    # byte unaffected, same report a caller who never set the floor gets.
    assert at_floor == unfloored


def test_fail_under_coverage_never_flags_a_deps_total_zero_axis(component_factory):
    """A deps_total == 0 axis (here: hygiene, via hygiene_applicable=False)
    is vacuous -- never flagged regardless of the floor, even a floor of
    100. The vulnerability axis (deps_total=2, deps_assessed=0) still gets
    flagged, proving the exclusion is deps_total==0-specific, not a blanket
    'hygiene axis is exempt' special case."""
    inventory = _inventory(component_factory)
    report = _assemble(inventory, fail_under_coverage=100.0, hygiene_applicable=False)
    finding_ids = {f.id for f in report.findings}
    assert "indeterminate:coverage-floor:hygiene" not in finding_ids
    assert "indeterminate:coverage-floor:vulnerability" in finding_ids


def test_fail_under_coverage_default_is_byte_identical_to_omitting_the_param(
    component_factory,
):
    inventory = _inventory(component_factory)
    default_report = _assemble(inventory)
    explicit_report = _assemble(inventory, fail_under_coverage=0.0)
    assert explicit_report == default_report


# --- render_text (Story 1.8) ---------------------------------------------


def _report(**overrides) -> ComplianceReport:
    kwargs = dict(
        schema_version="1.0.0",
        tool_name="warden",
        tool_version="0.1.0",
        status=Status.CLEAN,
        status_driver=None,
        exit_code=0,
        findings=(),
        coverage=(),
        vuln_data=_NO_VULN_DATA,
        inventory_count=0,
        resolved_scan_set=(),
        errors=(),
    )
    kwargs.update(overrides)
    return ComplianceReport(**kwargs)


def test_render_text_clean_report_is_a_single_header_line():
    """No driver, no findings, no errors: just the verdict line — no
    trailing driver/finding/error lines at all."""
    report = _report(status=Status.CLEAN, status_driver=None, exit_code=0)
    assert render_text(report) == "warden: status=clean exit_code=0 findings=0"


def test_render_text_findings_render_in_to_json_dict_sorted_order_with_driver():
    """Two findings inserted OUT of sorted order (zzz before aaa): the
    rendered lines must appear in ``to_json_dict()``'s sorted order (aaa
    before zzz), never insertion order — proving render_text reuses that
    sort rather than a second, independently-maintained one. Also exercises
    both severity-tier branches: an explicit tier ('high') and the 'none'
    fallback for a severity-less finding, and the driver-present line."""
    finding_zzz = Finding(
        id="hygiene:DEP002:zzz",
        axis=AXIS_HYGIENE,
        message="zzz unused",
        subject="zzz",
        severity=None,
    )
    finding_aaa = Finding(
        id="hygiene:DEP002:aaa",
        axis=AXIS_HYGIENE,
        message="aaa unused",
        subject="aaa",
        severity=Severity(tier=SeverityTier.HIGH, raw=None),
    )
    report = _report(
        status=Status.WARN,
        status_driver=StatusDriver(axis=AXIS_HYGIENE, finding_id="hygiene:DEP002:aaa"),
        exit_code=0,
        findings=(finding_zzz, finding_aaa),
        inventory_count=2,
    )
    assert render_text(report) == "\n".join(
        [
            "warden: status=warn exit_code=0 findings=2",
            "  driver: axis=hygiene id=hygiene:DEP002:aaa",
            "  [hygiene] high hygiene:DEP002:aaa -- aaa unused",
            "  [hygiene] none hygiene:DEP002:zzz -- zzz unused",
        ]
    )


def test_render_text_errors_render_in_to_json_dict_sorted_order_with_driver():
    """Two errors inserted OUT of sorted order (unparsable-manifest before
    internal-error): 'internal-error' < 'unparsable-manifest' lexically, so
    the rendered lines must flip to that sorted order."""
    unparsable = ErrorRecord(
        kind=ErrorKind.UNPARSABLE_MANIFEST,
        owner="extract",
        message="pyproject.toml: broken TOML",
    )
    internal = ErrorRecord(
        kind=ErrorKind.INTERNAL_ERROR,
        owner="discovery",
        message="discovery failed",
    )
    report = _report(
        status=Status.ERROR,
        status_driver=StatusDriver(
            axis=AXIS_INGESTION,
            finding_id="error:unparsable-manifest:pyproject.toml",
        ),
        exit_code=2,
        errors=(unparsable, internal),
    )
    assert render_text(report) == "\n".join(
        [
            "warden: status=error exit_code=2 findings=0",
            "  driver: axis=ingestion id=error:unparsable-manifest:pyproject.toml",
            "  [error:internal-error] discovery -- discovery failed",
            "  [error:unparsable-manifest] extract -- pyproject.toml: broken TOML",
        ]
    )


def test_render_text_neutralizes_embedded_newlines_in_finding_and_error_messages():
    """Review finding (2026-07-17): unlike ``Finding.id`` (regex-guarded
    against ``\\n`` at construction), ``message`` is engine/exception-derived
    free text with no such guarantee -- a message embedding
    ``"\\n  driver: axis=vulnerability id=vuln:FAKE-0001:evil@1.0"`` must
    render as ONE line with a literal ``\\n`` escape, never fabricate a
    second, indistinguishable-from-real line in this human-facing output."""
    hostile_finding = Finding(
        id="hygiene:DEP002:zzz",
        axis=AXIS_HYGIENE,
        message="zzz unused\n  driver: axis=vulnerability id=vuln:FAKE-0001:evil@1.0",
        subject="zzz",
        severity=None,
    )
    hostile_error = ErrorRecord(
        kind=ErrorKind.INTERNAL_ERROR,
        owner="discovery",
        message="discovery failed\r\nwith a fabricated second line",
    )
    report = _report(
        status=Status.ERROR,
        status_driver=StatusDriver(
            axis=AXIS_INGESTION, finding_id="error:internal-error:target"
        ),
        exit_code=2,
        findings=(hostile_finding,),
        errors=(hostile_error,),
    )
    rendered = render_text(report)
    lines = rendered.splitlines()
    # One line per finding + one per error: the embedded \n/\r\n never grew
    # the line count, and no fabricated "  driver: ..." line appears.
    assert len(lines) == 4
    assert lines[2] == (
        "  [hygiene] none hygiene:DEP002:zzz -- zzz unused\\n  driver: "
        "axis=vulnerability id=vuln:FAKE-0001:evil@1.0"
    )
    assert lines[3] == (
        "  [error:internal-error] discovery -- discovery failed\\nwith a "
        "fabricated second line"
    )
    assert sum(1 for line in lines if line.startswith("  driver: ")) == 1
