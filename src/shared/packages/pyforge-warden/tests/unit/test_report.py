"""Unit tests — ``report.assemble_report``'s ``hygiene_applicable`` coverage
override (Story 2.4, AC3).

Constructs a minimal ``ResolvedInventory`` directly (no CLI, no engines) and
calls ``assemble_report`` in isolation: the ``hygiene_applicable=False``
coverage-shape override, and a regression pin that the default
(``hygiene_applicable=True``, or omitted entirely) reproduces the pre-2.4
coverage shape byte-for-byte.
"""

from __future__ import annotations

from pyforge.warden.interfaces import EngineResult
from pyforge.warden.inventory import ResolvedInventory
from pyforge.warden.models import AXIS_HYGIENE, AxisCoverage, VulnData
from pyforge.warden.report import assemble_report

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
    )
    report = _assemble(
        inventory, hygiene_applicable=False, engine_results=(engine_result,)
    )
    by_axis = {c.axis: c for c in report.coverage}
    assert by_axis["hygiene"].deps_total == 0
    assert by_axis["hygiene"].deps_assessed == 0
