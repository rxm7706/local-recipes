"""Shared test fixtures (Story 1.1).

``make_component`` is the single Component factory for the whole suite,
exposed via the ``component_factory`` fixture — test modules take the
fixture instead of importing across test files.
"""

from __future__ import annotations

from typing import Any

import pytest

from python_deptry_osv_scanner.inventory import (
    Component,
    Provenance,
    PypiIdentity,
    derive_purl,
)
from python_deptry_osv_scanner.models import (
    CveMatchLevel,
    Ecosystem,
    ExtractionMode,
    IdentitySource,
    WithholdReason,
)

_UNSET: Any = object()


def make_component(
    name: str = "requests",
    version: str | None = "2.31.0",
    ecosystem: Ecosystem = Ecosystem.PYPI,
    *,
    provenance: tuple[tuple[str, str], ...] = (("pyproject.toml", "dependencies"),),
    purl: str | None = None,
    cve_match_level: CveMatchLevel | None = None,
    indeterminate_reason: WithholdReason | None = None,
    pypi_identity: PypiIdentity | None = _UNSET,
    identity_source: IdentitySource = IdentitySource.NATIVE,
    mapping_confidence: str | None = None,
    extraction_mode: ExtractionMode = ExtractionMode.PARSED,
    hygiene_covered: bool = True,
    vuln_matchable: bool | None = None,
) -> Component:
    has_version = bool(version)  # "" is version-less, same as None
    if cve_match_level is None:
        cve_match_level = (
            CveMatchLevel.EXACT if has_version else CveMatchLevel.NAME_ONLY
        )
    if pypi_identity is _UNSET:
        pypi_identity = PypiIdentity(name=name, version=version)
    if vuln_matchable is None:
        # The Gap-C predicate (enforced by Component.__post_init__).
        vuln_matchable = (
            has_version and pypi_identity is not None and indeterminate_reason is None
        )
    return Component(
        name=name,
        version=version,
        ecosystem=ecosystem,
        pypi_identity=pypi_identity,
        identity_source=identity_source,
        mapping_confidence=mapping_confidence,
        cve_match_level=cve_match_level,
        extraction_mode=extraction_mode,
        purl=purl if purl is not None else derive_purl(ecosystem, name, version),
        provenance=tuple(Provenance(manifest=m, section=s) for m, s in provenance),
        hygiene_covered=hygiene_covered,
        vuln_matchable=vuln_matchable,
        indeterminate_reason=indeterminate_reason,
    )


@pytest.fixture
def component_factory():
    """The shared ``Component`` factory (a plain function; see
    ``make_component``)."""
    return make_component
