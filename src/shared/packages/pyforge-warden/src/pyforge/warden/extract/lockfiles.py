"""Lockfile extraction — the locked-closure vuln hero path (Story 2.6).

Parses ``pixi.lock`` / ``conda-lock.yml`` into the existing ``Component``/
``ResolvedInventory`` model via ``yaml.safe_load`` ONLY (NFR-S1/S2 — the
AST-denylist meta-test covers this file automatically). No new merge logic
is needed: ``inventory.merge_components``'s existing Gap-B fold already
lets a lockfile's exact version subsume a looser ``pyproject.toml`` entry
of the same identity.

Ownership decisions recorded:

* pixi.lock ``conda:`` rows carry no ``name:``/``version:`` fields — the
  URL/path value's BASENAME is extracted FIRST
  (``value.rsplit("/", 1)[-1]``), THEN the name-version-build regex is
  applied to the BASENAME ONLY: running the pattern against the
  un-stripped value lets a subdir path segment (e.g. ``linux-64/``) bleed
  into the captured name (the URL-basename pitfall — regression-tested
  against ``_openmp_mutex``). A basename that doesn't match is kept as
  ``RAW_MALFORMED``/``NO_VERSION`` — never dropped.
* pixi.lock ``pypi:`` rows use their own ``name:``/``version:`` fields
  directly (``identity_source=LOCK``) — no second basename-guessing
  heuristic when both are absent (kept ``RAW_MALFORMED``/``NO_VERSION``
  instead; out of this story's scope).
* conda-lock.yml rows always carry explicit ``name:``/``version:``/
  ``manager:`` fields (``conda``|``pip``) — no basename parsing for this
  format at all. ``manager: pip`` → ``Ecosystem.PYPI``,
  ``identity_source=LOCK``; ``manager: conda`` → ``Ecosystem.CONDA``.
* Routing goes through the ``Router`` seam (FR2): the 4 module-level
  section-token constants below are the synthetic ``(kind, section)``
  pairs ``DefaultRouter.route()`` matches — a lockfile's rows are
  ecosystem-mixed per file (unlike ``pyproject.toml``'s one-shot section),
  so the extractor never assigns ``Ecosystem`` directly (every existing
  extractor calls the router; this stays precedent-consistent).
* A conda-ecosystem row with no PyPI identity calls
  ``mapping.load_conda_pypi_map()`` (today an empty ``{}`` stub pending
  Story 2.1) and, finding nothing, withholds as ``UNMAPPED_ECOSYSTEM`` —
  never guessed, never dropped. Once 2.1 populates the map, a hit resolves
  richer (``IdentitySource.MAP`` + the map's own confidence tier) with no
  change to this module's call site.
* Scope: the flat top-level ``packages:``/``package:`` list only (every
  package the file ever resolved, across all environments/platforms) — no
  per-environment/per-platform selection. Mirrors this repo's own sibling
  parser (``.claude/skills/conda-forge-expert/scripts/scan_project.py::
  parse_pixi_lock``); avoids host-platform-dependent behavior and errs
  toward more coverage, not less.
* NFR-S5: the whole file is size-capped and line-length-capped BEFORE
  ``yaml.safe_load`` (either cap exceeded raises ``UnparsableManifestError``
  rather than risk a hang/OOM on hostile input); the basename regex has no
  nested unbounded quantifiers.
* Error taxonomy (mirrors ``extract/pyproject.py``): a structurally corrupt
  document (not a mapping, a list field of the wrong type, a package entry
  of the wrong shape) raises ``UnparsableManifestError`` for the WHOLE
  manifest; a well-typed but content-degenerate ROW (an unparseable conda
  basename, a pypi row missing both identity fields) degrades to one
  ``RAW_MALFORMED`` component instead — never dropped, never crashes.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from ..interfaces import Router
from ..inventory import (
    Component,
    Provenance,
    PypiIdentity,
    canonical_name,
    derive_purl,
)
from ..mapping import load_conda_pypi_map
from ..models import (
    CveMatchLevel,
    Ecosystem,
    ExtractionMode,
    IdentitySource,
    ScannedManifest,
    WithholdReason,
)
from . import UnparsableManifestError

# The 4 synthetic (kind, section) routing tokens (imported into routing.py
# exactly as PROJECT_DEPENDENCIES_SECTION already is).
PIXI_LOCK_CONDA_SECTION = "packages[kind=conda]"
PIXI_LOCK_PYPI_SECTION = "packages[kind=pypi]"
CONDA_LOCK_CONDA_SECTION = "package[manager=conda]"
CONDA_LOCK_PYPI_SECTION = "package[manager=pip]"

# NFR-S5: a lockfile exceeding either cap raises UnparsableManifestError
# rather than risk a hang/OOM on hostile input. Both are well above any
# legitimate lockfile (this repo's own multi-platform, multi-environment
# pixi.lock is ~1.7MB with a longest line under 200 bytes).
_MAX_LOCKFILE_BYTES = 20_000_000
_MAX_LINE_BYTES = 8_192

# Basename-first (see module docstring): applied to
# ``value.rsplit("/", 1)[-1]`` ONLY, never the raw URL/path. No nested
# unbounded quantifiers (NFR-S5).
_CONDA_BASENAME_RE = re.compile(r"^(.+)-([^-]+)-[^-]+\.(?:conda|tar\.bz2)$")


def _read_bounded(manifest_path: Path, manifest: ScannedManifest) -> str:
    """Read + NFR-S5-bound the raw bytes, THEN decode — a size/line check
    ahead of ``yaml.safe_load`` so a hostile lockfile can never hang or OOM
    the parser."""
    raw = manifest_path.read_bytes()
    if len(raw) > _MAX_LOCKFILE_BYTES:
        raise UnparsableManifestError(
            f"unparsable manifest {manifest.path}: exceeds the "
            f"{_MAX_LOCKFILE_BYTES}-byte size cap (NFR-S5)"
        )
    for line in raw.split(b"\n"):
        if len(line) > _MAX_LINE_BYTES:
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: a line exceeds the "
                f"{_MAX_LINE_BYTES}-byte length cap (NFR-S5)"
            )
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UnparsableManifestError(
            f"unparsable manifest {manifest.path}: {exc}"
        ) from exc


def _load_yaml(manifest_path: Path, manifest: ScannedManifest) -> object:
    text = _read_bounded(manifest_path, manifest)
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise UnparsableManifestError(
            f"unparsable manifest {manifest.path}: {exc}"
        ) from exc


def _optional_str_field(
    entry: dict[str, object], key: str, manifest: ScannedManifest
) -> str | None:
    """``entry[key]`` as a string, ``None`` when the key is absent/``null``,
    or a raised ``UnparsableManifestError`` when present with the WRONG
    type (a structural schema violation, not a content-level degeneracy)."""
    value = entry.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise UnparsableManifestError(
            f"unparsable manifest {manifest.path}: {key!r} must be a "
            f"string, got {type(value).__name__}"
        )
    return value


def _resolve_conda_pypi_identity(
    name: str,
) -> tuple[PypiIdentity, str | None] | None:
    """Consult the (today-stub) conda→pypi map for ``name`` — ``None`` on a
    miss (today ALWAYS, since the bundled asset is ``{}`` pending Story
    2.1). The value shape a populated map entry carries is Story 2.1's to
    finalize; this defensively reads the two columns epics.md's own AC text
    names (``pypi_name`` and ``match_confidence``) and falls back to a miss
    on anything else — never guessed, never crashes."""
    entry = load_conda_pypi_map().get(name)
    if not isinstance(entry, dict):
        return None
    pypi_name = entry.get("pypi_name")
    if not isinstance(pypi_name, str) or not pypi_name:
        return None
    confidence = entry.get("match_confidence")
    return (
        PypiIdentity(name=canonical_name(Ecosystem.PYPI, pypi_name), version=None),
        confidence if isinstance(confidence, str) else None,
    )


def _conda_component(
    name: str, version: str | None, provenance: tuple[Provenance, ...]
) -> Component:
    """Build a conda-ecosystem ``Component``, consulting the conda→pypi map
    (see ``_resolve_conda_pypi_identity``); a miss withholds as
    ``UNMAPPED_ECOSYSTEM`` (never guessed)."""
    mapped = _resolve_conda_pypi_identity(name)
    if mapped is None:
        return Component(
            name=name,
            version=version,
            ecosystem=Ecosystem.CONDA,
            pypi_identity=None,
            identity_source=IdentitySource.NONE,
            mapping_confidence=None,
            cve_match_level=CveMatchLevel.NONE,
            extraction_mode=ExtractionMode.PARSED,
            purl=derive_purl(Ecosystem.CONDA, name, version),
            provenance=provenance,
            hygiene_covered=True,
            vuln_matchable=False,
            indeterminate_reason=WithholdReason.UNMAPPED_ECOSYSTEM,
        )
    identity, confidence = mapped
    identity = PypiIdentity(name=identity.name, version=version)
    return Component(
        name=name,
        version=version,
        ecosystem=Ecosystem.CONDA,
        pypi_identity=identity,
        identity_source=IdentitySource.MAP,
        mapping_confidence=confidence,
        cve_match_level=CveMatchLevel.EXACT if version else CveMatchLevel.NAME_ONLY,
        extraction_mode=ExtractionMode.PARSED,
        purl=derive_purl(Ecosystem.CONDA, name, version),
        provenance=provenance,
        hygiene_covered=True,
        vuln_matchable=bool(version),
        indeterminate_reason=None if version else WithholdReason.NO_VERSION,
    )


def _pypi_component(
    name: str, version: str | None, provenance: tuple[Provenance, ...]
) -> Component:
    """Build a PyPI-ecosystem ``Component`` from a lockfile's own
    ``name``/``version`` (``identity_source=LOCK`` — already
    PEP-503-canonical in practice)."""
    identity_name = canonical_name(Ecosystem.PYPI, name)
    if version:
        return Component(
            name=name,
            version=version,
            ecosystem=Ecosystem.PYPI,
            pypi_identity=PypiIdentity(name=identity_name, version=version),
            identity_source=IdentitySource.LOCK,
            mapping_confidence=None,
            cve_match_level=CveMatchLevel.EXACT,
            extraction_mode=ExtractionMode.PARSED,
            purl=derive_purl(Ecosystem.PYPI, name, version),
            provenance=provenance,
            hygiene_covered=True,
            vuln_matchable=True,
            indeterminate_reason=None,
        )
    return Component(
        name=name,
        version=None,
        ecosystem=Ecosystem.PYPI,
        pypi_identity=PypiIdentity(name=identity_name, version=None),
        identity_source=IdentitySource.LOCK,
        mapping_confidence=None,
        cve_match_level=CveMatchLevel.NAME_ONLY,
        extraction_mode=ExtractionMode.PARSED,
        purl=derive_purl(Ecosystem.PYPI, name, None),
        provenance=provenance,
        hygiene_covered=True,
        vuln_matchable=False,
        indeterminate_reason=WithholdReason.NO_VERSION,
    )


def _raw_malformed(
    ecosystem: Ecosystem, raw_name: str, provenance: tuple[Provenance, ...]
) -> Component:
    """A row that could not be identified at all — kept, marked, withheld;
    never dropped silently (mirrors ``extract/pyproject.py``'s invalid-
    requirement handling)."""
    name = raw_name or "<unidentifiable-lockfile-entry>"
    return Component(
        name=name,
        version=None,
        ecosystem=ecosystem,
        pypi_identity=None,
        identity_source=IdentitySource.NONE,
        mapping_confidence=None,
        cve_match_level=CveMatchLevel.NONE,
        extraction_mode=ExtractionMode.RAW_MALFORMED,
        purl=derive_purl(ecosystem, name, None),
        provenance=provenance,
        hygiene_covered=False,
        vuln_matchable=False,
        indeterminate_reason=WithholdReason.NO_VERSION,
    )


class PixiLockExtractor:
    """Extract the locked closure from a pixi.lock's flat top-level
    ``packages:`` list (every environment/platform the file ever resolved —
    no per-environment/per-platform selection, see module docstring)."""

    def __init__(self, router: Router) -> None:
        self._router = router

    def extract(
        self, manifest_path: Path, manifest: ScannedManifest
    ) -> tuple[Component, ...]:
        document = _load_yaml(manifest_path, manifest)
        if document is None:
            return ()
        if not isinstance(document, dict):
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: top-level document "
                "is not a mapping"
            )
        packages = document.get("packages")
        if packages is None:
            packages = []
        if not isinstance(packages, list):
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: 'packages' must be "
                "a list"
            )
        return tuple(self._component(entry, manifest) for entry in packages)

    def _component(
        self, entry: object, manifest: ScannedManifest
    ) -> Component:
        if not isinstance(entry, dict):
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: a 'packages' entry "
                "is not a mapping"
            )
        if "conda" in entry:
            return self._conda_row(entry, manifest)
        if "pypi" in entry:
            return self._pypi_row(entry, manifest)
        raise UnparsableManifestError(
            f"unparsable manifest {manifest.path}: a 'packages' entry has "
            "neither a 'conda' nor a 'pypi' key"
        )

    def _conda_row(
        self, entry: dict[str, object], manifest: ScannedManifest
    ) -> Component:
        ecosystem = self._router.route(manifest.kind, PIXI_LOCK_CONDA_SECTION)
        provenance = (
            Provenance(manifest=manifest.path, section=PIXI_LOCK_CONDA_SECTION),
        )
        value = _optional_str_field(entry, "conda", manifest) or ""
        basename = value.rsplit("/", 1)[-1]  # basename-FIRST (see docstring)
        match = _CONDA_BASENAME_RE.match(basename) if basename else None
        if match is None:
            return _raw_malformed(ecosystem, value, provenance)
        return _conda_component(match.group(1), match.group(2), provenance)

    def _pypi_row(
        self, entry: dict[str, object], manifest: ScannedManifest
    ) -> Component:
        ecosystem = self._router.route(manifest.kind, PIXI_LOCK_PYPI_SECTION)
        provenance = (
            Provenance(manifest=manifest.path, section=PIXI_LOCK_PYPI_SECTION),
        )
        name = _optional_str_field(entry, "name", manifest)
        version = _optional_str_field(entry, "version", manifest)
        if not name:
            # Both identity fields absent (or name blank): no second
            # basename-guessing heuristic — kept RAW_MALFORMED instead.
            url = _optional_str_field(entry, "pypi", manifest) or ""
            return _raw_malformed(ecosystem, url, provenance)
        return _pypi_component(name, version, provenance)


class CondaLockExtractor:
    """Extract the locked closure from conda-lock.yml's flat ``package:``
    list — rows always carry explicit ``name``/``version``/``manager``
    fields (no basename parsing needed for this format)."""

    def __init__(self, router: Router) -> None:
        self._router = router

    def extract(
        self, manifest_path: Path, manifest: ScannedManifest
    ) -> tuple[Component, ...]:
        document = _load_yaml(manifest_path, manifest)
        if document is None:
            return ()
        if not isinstance(document, dict):
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: top-level document "
                "is not a mapping"
            )
        entries = document.get("package")
        if entries is None:
            entries = []
        if not isinstance(entries, list):
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: 'package' must be "
                "a list"
            )
        return tuple(self._component(entry, manifest) for entry in entries)

    def _component(
        self, entry: object, manifest: ScannedManifest
    ) -> Component:
        if not isinstance(entry, dict):
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: a 'package' entry "
                "is not a mapping"
            )
        name = _optional_str_field(entry, "name", manifest)
        if not name:
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: a 'package' entry "
                "has no name"
            )
        manager = entry.get("manager")
        if manager == "conda":
            section = CONDA_LOCK_CONDA_SECTION
        elif manager == "pip":
            section = CONDA_LOCK_PYPI_SECTION
        else:
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: package {name!r} "
                f"has an unrecognized manager {manager!r} (expected "
                "'conda' or 'pip')"
            )
        ecosystem = self._router.route(manifest.kind, section)
        provenance = (Provenance(manifest=manifest.path, section=section),)
        version = _optional_str_field(entry, "version", manifest)
        if ecosystem is Ecosystem.PYPI:
            return _pypi_component(name, version, provenance)
        return _conda_component(name, version, provenance)
