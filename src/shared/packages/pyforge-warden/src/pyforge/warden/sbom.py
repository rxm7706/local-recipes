"""CycloneDX 1.6 SBOM projection (Story 4.1).

Ownership decisions recorded:

* ``render_cyclonedx`` is a PURE, READ-ONLY projection over an
  already-resolved ``ResolvedInventory``/``ComplianceReport`` -- it never
  mutates either argument, never calls ``merge_components``, and derives no
  new coverage/identity data of its own (``report.py``/``inventory.py`` own
  those computations). The scanned root is ``metadata.component``
  (``ComponentType.APPLICATION``), never a ``components[]`` entry --
  ``inventory.py``'s own ``ResolvedInventory`` docstring states the root
  project never enters the inventory.
* ``SBOM_SCHEMA_VERSION`` lives HERE, decoupled from
  ``report.REPORT_SCHEMA_VERSION`` (NFR-I2) -- the two artifacts version
  independently; mirrors ``report.py::REPORT_SCHEMA_VERSION``'s own
  ownership precedent (``models.py`` stays frozen, no new constant there).
* Purls are built ONLY via ``packageurl.PackageURL`` -- never
  ``inventory.py::derive_purl()``/``Component.purl`` (PEP 503 collapses
  dots, the wrong rule for purls -- G98 requires lowercase + ``_``->``-``
  with dots preserved; verified live against the installed
  ``packageurl-python`` 0.17.6: ``PackageURL(type="pypi",
  name="Django_Foo.Bar", version="1.0")`` -> ``pkg:pypi/django-foo.bar@1.0``,
  and it percent-encodes control/reserved characters rather than ever
  smuggling raw bytes into purl syntax).
* ``cfe:*`` conda-identity properties are scoped to CONDA components only
  (a PyPI component's own ``pypi_identity`` mirrors its own identity --
  ``extract/_identity.py``'s ``_pypi_component``/``pep508_pypi_component``
  -- so a cross-reference property there would just restate the
  component's own purl) and gated on ``identity_source``: ``cfe:pypi_purl``
  whenever ``pypi_identity`` resolved (any source); ``cfe:match_confidence``/
  ``cfe:match_source`` ONLY when ``identity_source == IdentitySource.MAP``
  specifically -- a lock/native-resolved identity was never
  probabilistically matched (``Component.mapping_confidence``'s own
  docstring scopes it to "the map's per-pair tier"), so attaching a map
  confidence tier to it would misrepresent how it was actually resolved.
* Determinism (``bom.serial_number``/``metadata.timestamp``) is explicitly
  OUT of scope this story -- no ``determinism.py`` exists for either
  artifact yet; both fields stay volatile in v1 (mirrors ``cli.py``'s own
  ``--deterministic`` no-op precedent, and the epic's own Technical
  Decisions: "shared with the report renderer, not owned solely here").
* No component ``licenses[]``/supplier/author/manufacturer data is ever
  emitted -- the resolved inventory carries none of it; fabricating any of
  it would misrepresent data this tool never collected (NFR-S7).
* The rendered document self-validates against the CycloneDX 1.6 schema
  before being returned (mirrors ``report.py::render_json``'s
  validate-before-emit discipline). ``JsonStrictValidator.validate_str``
  does not raise on failure -- it RETURNS a
  ``cyclonedx.validation.ValidationError`` (not an ``Exception`` subclass)
  or ``None`` -- so a failure is re-raised here as a distinctly-typed
  ``SbomValidationError``, letting a caller/test tell a rendering defect
  apart from any other exception. ``cli.py`` catches it broadly (review
  finding, 2026-07-18): the SBOM is emitted AFTER the report is already
  fully assembled, so an internal defect here must degrade to a loud
  stderr diagnostic in ``cli.py``, never suppress the already-valid
  report or alter ``report.exit_code`` -- unlike ``render_json``, whose
  own failure genuinely means there is no valid report to emit.
* ``cfe:match_confidence``/``cfe:match_source`` are each independently
  omitted (never emitted as a valueless property) when their value is
  ``None`` -- ``identity_source == MAP`` does not itself guarantee a
  non-``None`` ``mapping_confidence`` (a merge across disagreeing
  carriers can legitimately null it, ``inventory.py::
  _merge_group_pypi_identity``) or a bundled-map hit for
  ``match_source``; a present-but-empty property key would misrepresent
  "nothing to honestly say" as data (review finding, 2026-07-18).
"""

from __future__ import annotations

from cyclonedx.model import Property
from cyclonedx.model.bom import Bom, BomMetaData
from cyclonedx.model.component import Component as CdxComponent
from cyclonedx.model.component import ComponentType
from cyclonedx.model.tool import Tool
from cyclonedx.output.json import JsonV1Dot6
from cyclonedx.schema import SchemaVersion
from cyclonedx.validation.json import JsonStrictValidator
from packageurl import PackageURL

from .inventory import Component, ResolvedInventory
from .mapping import load_conda_pypi_map
from .models import Ecosystem, IdentitySource
from .report import ComplianceReport

SBOM_SCHEMA_VERSION = "0.1.0"

# This repo's sole conda channel (``Component`` carries no channel field of
# its own -- see the story spec's Boundaries & Constraints).
_CONDA_CHANNEL = "conda-forge"

_VALIDATOR = JsonStrictValidator(SchemaVersion.V1_6)


class SbomValidationError(Exception):
    """The rendered document failed its own CycloneDX 1.6 schema validation
    -- an internal rendering defect. Deliberately NOT a ``ValueError``/
    ``OSError`` -- see the module docstring for why."""


def render_cyclonedx(inventory: ResolvedInventory, report: ComplianceReport) -> str:
    """Render ``inventory`` as a schema-valid CycloneDX 1.6 BOM JSON document.

    One ``Component`` per already-merged inventory component (``len(bom.
    components) == inventory.count``), the scanned root as
    ``metadata.component``/``metadata.tools`` (from ``report.tool_name``/
    ``report.tool_version``), and a single flat root -> every-component
    ``dependencies[]`` edge -- the one NTIA dependency relationship this
    flat inventory can honestly support; no transitive graph data exists,
    so no other edge is fabricated. Self-validated before returning; see
    the module docstring for the ``SbomValidationError`` fail-loud
    discipline."""
    components = [_build_component(component) for component in inventory.components]
    root = CdxComponent(
        name=report.tool_name,
        version=report.tool_version,
        type=ComponentType.APPLICATION,
    )
    partial_inventory = any(
        coverage.manifests_parsed < coverage.manifests_found
        for coverage in report.coverage
    )
    bom = Bom(
        components=components,
        metadata=BomMetaData(
            component=root,
            tools=[Tool(name=report.tool_name, version=report.tool_version)],
            properties=[
                Property(
                    name="cfe:partial_inventory",
                    value="true" if partial_inventory else "false",
                ),
                Property(name="cfe:schema_version", value=SBOM_SCHEMA_VERSION),
                Property(name="cfe:schema_status", value="experimental"),
            ],
        ),
    )
    bom.register_dependency(root, components)
    rendered = JsonV1Dot6(bom).output_as_string(indent=2)
    error = _VALIDATOR.validate_str(rendered)
    if error is not None:
        raise SbomValidationError(
            f"rendered CycloneDX SBOM failed 1.6 schema validation: {error}"
        )
    return rendered


def _build_component(component: Component) -> CdxComponent:
    return CdxComponent(
        name=component.name,
        version=component.version,
        purl=_component_purl(component),
        properties=_cfe_properties(component),
    )


def _component_purl(component: Component) -> PackageURL:
    """The G98-normalized purl -- built fresh via ``PackageURL``, never
    ``Component.purl``/``derive_purl()`` (see the module docstring)."""
    if component.ecosystem is Ecosystem.CONDA:
        return PackageURL(
            type="conda",
            name=component.name,
            version=component.version,
            qualifiers={"channel": _CONDA_CHANNEL},
        )
    return PackageURL(type="pypi", name=component.name, version=component.version)


def _cfe_properties(component: Component) -> list[Property]:
    """The ``cfe:*`` conda-identity properties (see the module docstring
    for the ecosystem/``identity_source`` gating rules)."""
    if component.ecosystem is not Ecosystem.CONDA or component.pypi_identity is None:
        return []
    pypi_purl = PackageURL(
        type="pypi",
        name=component.pypi_identity.name,
        version=component.pypi_identity.version,
    )
    properties = [Property(name="cfe:pypi_purl", value=str(pypi_purl))]
    if component.identity_source is IdentitySource.MAP:
        if component.mapping_confidence is not None:
            properties.append(
                Property(
                    name="cfe:match_confidence", value=component.mapping_confidence
                )
            )
        match_source = _match_source(component.name)
        if match_source is not None:
            properties.append(Property(name="cfe:match_source", value=match_source))
    return properties


def _match_source(conda_name: str) -> str | None:
    """A fresh lookup (never carried on ``Component`` itself -- confirmed
    absent from ``inventory.py``/``extract/_identity.py``)."""
    entry = load_conda_pypi_map().get(conda_name)
    if not isinstance(entry, dict):
        return None
    match_source = entry.get("match_source")
    return match_source if isinstance(match_source, str) else None
