"""CycloneDX projection of estate-wide eligibility results (Story 7.3 / CAP-3).

Renders ``compute_eligibility_union`` output through the same CycloneDX 1.6
+ ``packageurl.PackageURL`` discipline as ``sbom.py`` — never PEP-503
dot-collapsing. Does not mutate eligibility inputs; no I/O.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from cyclonedx.model import Property
from cyclonedx.model.bom import Bom, BomMetaData
from cyclonedx.model.component import Component as CdxComponent
from cyclonedx.model.component import ComponentType
from cyclonedx.model.tool import Tool
from cyclonedx.output.json import JsonV1Dot6
from cyclonedx.schema import SchemaVersion
from cyclonedx.validation.json import JsonStrictValidator
from packageurl import PackageURL

from .eligibility import EligibilityResult
from .models import Ecosystem
from .sbom import SbomValidationError

__all__ = ("render_eligibility_cyclonedx", "SbomValidationError")

_VALIDATOR = JsonStrictValidator(SchemaVersion.V1_6)
_CONDA_CHANNEL = "conda-forge"


def _as_serial_uuid(serial_number: str | UUID) -> UUID:
    if isinstance(serial_number, UUID):
        return serial_number
    text = serial_number.strip()
    if text.startswith("urn:uuid:"):
        text = text[len("urn:uuid:") :]
    return UUID(text)


def render_eligibility_cyclonedx(
    results: tuple[EligibilityResult, ...],
    *,
    tool_name: str = "pyforge-warden",
    tool_version: str = "0.1.0",
    serial_number: str | UUID | None = None,
    timestamp: datetime | None = None,
) -> str:
    """Deterministic CycloneDX 1.6 JSON for an eligibility-union result set.

    When ``serial_number`` and ``timestamp`` are supplied, two calls with the
    same inputs produce byte-identical documents. When omitted, CycloneDX
    library defaults apply (volatile) — callers who need determinism pass
    both explicitly (tests do).
    """
    components = [_build_component(result) for result in results]
    root = CdxComponent(
        name=tool_name,
        version=tool_version,
        type=ComponentType.APPLICATION,
        # Stable bom-ref so two renders with fixed serial/timestamp match.
        bom_ref=f"application:{tool_name}@{tool_version}",
    )
    meta_kwargs: dict = {
        "component": root,
        "tools": [Tool(name=tool_name, version=tool_version)],
        "properties": [
            Property(name="cfe:eligibility_schema", value="0.1.0"),
            Property(name="cfe:schema_status", value="experimental"),
        ],
    }
    if timestamp is not None:
        meta_kwargs["timestamp"] = timestamp.astimezone(UTC)
    bom = Bom(components=components, metadata=BomMetaData(**meta_kwargs))
    if serial_number is not None:
        bom.serial_number = _as_serial_uuid(serial_number)
    bom.register_dependency(root, components)
    rendered = JsonV1Dot6(bom).output_as_string(indent=2)
    # Normalize JSON key order for determinism across library versions.
    rendered = json.dumps(json.loads(rendered), indent=2, sort_keys=True) + "\n"
    error = _VALIDATOR.validate_str(rendered)
    if error is not None:
        raise SbomValidationError(f"eligibility CycloneDX failed 1.6 schema validation: {error}")
    return rendered


def _build_component(result: EligibilityResult) -> CdxComponent:
    identity = result.identity
    purl = _identity_purl(identity.ecosystem, identity.canonical_name, identity.version)
    props = [
        Property(name="cfe:eligibility_status", value=result.status.value),
    ]
    for entry in result.provenance:
        props.append(
            Property(
                name="cfe:provenance",
                value=f"{entry.source}|{entry.locator}|{entry.timestamp}",
            )
        )
    return CdxComponent(
        name=identity.canonical_name,
        version=identity.version,
        purl=purl,
        properties=props,
        bom_ref=str(purl),
    )


def _identity_purl(ecosystem: Ecosystem, name: str, version: str | None) -> PackageURL:
    if ecosystem is Ecosystem.CONDA:
        return PackageURL(
            type="conda",
            name=name,
            version=version,
            qualifiers={"channel": _CONDA_CHANNEL},
        )
    return PackageURL(type="pypi", name=name, version=version)
