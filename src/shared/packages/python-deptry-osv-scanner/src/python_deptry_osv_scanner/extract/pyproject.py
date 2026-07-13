"""Minimal pyproject extractor (Story 1.2) — E1's first no-execution-zone
module.

NFR-S1: this package parses via ``tomllib`` + ``packaging.requirements``
ONLY — no ``eval``/``exec``/``subprocess``/``os.system``/``jinja2``, no YAML.
The AST-denylist meta-test polices it.

Ownership decisions recorded:

* Only ``[project].dependencies`` is read (optional-dependencies, dep-groups
  and the other manifest formats arrive with later E1 stories).
* The concrete-version forms are a single plain ``==X.Y.Z`` specifier
  without a ``.*`` suffix AND PEP 440 arbitrary equality ``===X`` (which
  pins exactly one version by definition); multi-specifier sets and the
  ``==1.2.*`` prefix match are conservatively withheld as ``range-only``
  (never guess a version — Gap-C).
* A bare name (no specifier, or a URL requirement) withholds as
  ``no-version``.
* An invalid PEP 508 entry is KEPT as ``extraction_mode=raw-malformed``
  (name = the raw string, ``identity_source=none``, ``pypi_identity=None``,
  withheld) — never dropped silently. Its withhold reason is ``no-version``
  (no version could be parsed; the closest honest token in the frozen enum).
* Environment markers are ignored: the dep is extracted regardless (union
  semantics — the honest superset).
* ``tomllib.TOMLDecodeError`` (and structurally-corrupt ``[project]``
  tables) raise ``UnparsableManifestError`` — the CLI catches EXACTLY that
  class into ``ErrorRecord(kind=unparsable-manifest)`` (fail-loud, report
  still emitted); any other ``ValueError`` out of this module is diagnosed
  as an internal error, never as a manifest problem.
* A PyPI-native declaration IS its own identity: ``identity_source=native``,
  ``pypi_identity`` carries the PEP-503-CANONICAL name
  (``inventory.canonical_name``) so the single-record path matches the
  merge path's canonical spelling; ``Component.name`` keeps the raw
  declared spelling (Gap-C trustworthy provenance).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement

from ..interfaces import Router
from ..inventory import (
    Component,
    Provenance,
    PypiIdentity,
    canonical_name,
    derive_purl,
)
from . import UnparsableManifestError
from ..models import (
    CveMatchLevel,
    Ecosystem,
    ExtractionMode,
    IdentitySource,
    ScannedManifest,
    WithholdReason,
)

# The 1.2 section token for [project].dependencies (routing keys on it).
PROJECT_DEPENDENCIES_SECTION = "project.dependencies"


class PyprojectExtractor:
    """Extract honest (Gap-C) components from ``[project].dependencies``."""

    def __init__(self, router: Router) -> None:
        self._router = router

    def extract(
        self, manifest_path: Path, manifest: ScannedManifest
    ) -> tuple[Component, ...]:
        try:
            with manifest_path.open("rb") as handle:
                data = tomllib.load(handle)
        except tomllib.TOMLDecodeError as exc:
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: {exc}"
            ) from exc
        project = data.get("project", {})
        if not isinstance(project, dict):
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: [project] is not a table"
            )
        raw_dependencies = project.get("dependencies", [])
        if not isinstance(raw_dependencies, list) or not all(
            isinstance(entry, str) for entry in raw_dependencies
        ):
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: [project].dependencies "
                "must be an array of strings"
            )
        ecosystem = self._router.route(manifest.kind, PROJECT_DEPENDENCIES_SECTION)
        provenance = (
            Provenance(manifest=manifest.path, section=PROJECT_DEPENDENCIES_SECTION),
        )
        components: list[Component] = []
        for entry in raw_dependencies:
            if not entry.strip():
                raise UnparsableManifestError(
                    f"unparsable manifest {manifest.path}: empty dependency entry"
                )
            components.append(self._component(entry, ecosystem, provenance))
        return tuple(components)

    def _component(
        self,
        raw: str,
        ecosystem: Ecosystem,
        provenance: tuple[Provenance, ...],
    ) -> Component:
        try:
            requirement = Requirement(raw)
        except InvalidRequirement:
            # Kept, marked, withheld — never dropped silently.
            return Component(
                name=raw,
                version=None,
                ecosystem=ecosystem,
                pypi_identity=None,
                identity_source=IdentitySource.NONE,
                mapping_confidence=None,
                cve_match_level=CveMatchLevel.NONE,
                extraction_mode=ExtractionMode.RAW_MALFORMED,
                purl=derive_purl(ecosystem, raw, None),
                provenance=provenance,
                hygiene_covered=False,
                vuln_matchable=False,
                indeterminate_reason=WithholdReason.NO_VERSION,
            )
        # The identity name is PEP-503-canonical (matches what the 1.1 merge
        # path would canonicalize to); Component.name keeps the raw spelling.
        identity_name = canonical_name(Ecosystem.PYPI, requirement.name)
        version = _exact_pin(requirement)
        if version is not None:
            return Component(
                name=requirement.name,
                version=version,
                ecosystem=ecosystem,
                pypi_identity=PypiIdentity(name=identity_name, version=version),
                identity_source=IdentitySource.NATIVE,
                mapping_confidence=None,
                cve_match_level=CveMatchLevel.EXACT,
                extraction_mode=ExtractionMode.PARSED,
                purl=derive_purl(ecosystem, requirement.name, version),
                provenance=provenance,
                hygiene_covered=True,
                vuln_matchable=True,
                indeterminate_reason=None,
            )
        reason = (
            WithholdReason.RANGE_ONLY
            if len(requirement.specifier) > 0
            else WithholdReason.NO_VERSION
        )
        return Component(
            name=requirement.name,
            version=None,
            ecosystem=ecosystem,
            pypi_identity=PypiIdentity(name=identity_name, version=None),
            identity_source=IdentitySource.NATIVE,
            mapping_confidence=None,
            cve_match_level=CveMatchLevel.NAME_ONLY,
            extraction_mode=ExtractionMode.PARSED,
            purl=derive_purl(ecosystem, requirement.name, None),
            provenance=provenance,
            hygiene_covered=True,
            vuln_matchable=False,
            indeterminate_reason=reason,
        )


def _exact_pin(requirement: Requirement) -> str | None:
    """The concrete version iff the requirement pins exactly one version:
    a single plain ``==`` pin, or PEP 440 arbitrary equality ``===`` (which
    matches exactly one literal version string by definition).

    ``==1.2.*`` is a PREFIX match (a range), not an exact pin — withheld."""
    specifiers = list(requirement.specifier)
    if len(specifiers) != 1:
        return None
    specifier = specifiers[0]
    if specifier.operator == "===":
        return specifier.version
    if specifier.operator != "==" or specifier.version.endswith(".*"):
        return None
    return specifier.version
