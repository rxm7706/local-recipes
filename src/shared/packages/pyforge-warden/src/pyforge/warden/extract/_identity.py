"""Shared identity-resolution + component-construction helpers for the E1
extractors (Story 2.2) -- the foundation ``extract/lockfiles.py`` (Story
2.6), ``extract/recipe_v1.py``/``meta_v0.py``/``environment_yml.py``/
``pixi.py`` (Story 2.2) all build on, so trust-sensitive conda<->pypi
mapping logic and honest version-exactness classification exist in exactly
ONE place across all 6 extractors.

Two families of helpers live here:

* **Factored verbatim out of ``extract/lockfiles.py``** (behavior-identical
  -- 2.6's tests stay green): ``TRUSTED_MATCH_CONFIDENCE``,
  ``_resolve_conda_pypi_identity``, ``_unmapped_conda_component``,
  ``_conda_component``, ``_pypi_component``, ``_raw_malformed``.
  ``_conda_component``/``_unmapped_conda_component`` gained one new
  keyword-only parameter, ``extraction_mode`` (default
  ``ExtractionMode.PARSED``, lockfiles.py's own -- and every pre-2.2 --
  behavior, unchanged): the four new Story 2.2 format extractors need to
  build an honestly-degraded ``NAME_ONLY`` conda component (a best-effort
  name recovered from an unresolved template construct) through the SAME
  conda->pypi identity path, not a parallel one.
* **New in Story 2.2** (not factored from anywhere -- shared because 4 of
  the 6 extractors need the SAME conda-matchspec-string / PEP-508-string
  parsing discipline): ``split_conda_dep_string``/
  ``classify_conda_specifier`` (conda matchspec syntax --
  ``recipe_v1.py``/``meta_v0.py``/``environment_yml.py``/``pixi.py``'s
  conda-ecosystem rows) and ``pep508_pypi_component`` (PEP 508 syntax --
  ``environment_yml.py``'s ``- pip:`` list and ``pixi.py``'s
  ``[pypi-dependencies]`` tables), plus ``read_bounded_text`` (the NFR-S5
  two-cap read, mirroring ``lockfiles.py::_read_bounded`` exactly so the 4
  new extractors don't each duplicate it -- ``lockfiles.py`` keeps its own
  pre-2.2 copy untouched, for the same byte-for-byte-test-stability reason
  its identity builders were factored out rather than edited in place).

Ownership decisions recorded (new-in-2.2 pieces only; the factored pieces'
decisions are unchanged, see their own docstrings):

* ``classify_conda_specifier`` mirrors ``pyproject.py::_exact_pin``'s
  discipline, translated to conda matchspec syntax: only a BARE
  (no-operator) version token or an explicit ``==`` pin is concrete.
  Conda's own legacy fuzzy-prefix ``=`` (single equals -- empirically
  ``numpy=1.11`` matches ``1.11``, ``1.11.1``, ``1.11.2``, ... per conda's
  own docs, exactly like a ``.*`` wildcard) is conservatively withheld as
  ``range-only``, never treated as exact -- so is any other comparison
  operator, and a ``.*``-suffixed version regardless of operator (mirrors
  pyproject's ``==1.2.*``-is-a-range precedent). An entirely absent/``*``
  specifier is ``no-version`` (a genuinely bare dependency, never a
  guessed exactness). ``===`` (3+ leading equals, PEP 440's "arbitrary
  equality" -- not standard conda matchspec syntax) is likewise
  conservatively withheld as ``range-only`` rather than treated as a
  slightly-malformed ``==``: naively stripping exactly 2 leading ``=``
  characters would otherwise bake a stray leading ``=`` into the
  "version" (``===1.2.3`` -> ``=1.2.3``), a corrupted value that must
  never be reported as a confident exact match (fixed 2026-07-16 —
  live-verified: ``classify_conda_specifier('===1.2.3')`` used to return
  ``('=1.2.3', None)``).
* ``split_conda_dep_string`` handles BOTH whitespace-separated
  (``numpy >=1.20``, common in recipe.yaml/meta.yaml/environment.yml) and
  contiguous (``python=3.11``, common in environment.yml) matchspec
  strings via one regex -- real conda tooling accepts both forms
  interchangeably.
* ``pep508_pypi_component`` mirrors
  ``pyproject.py::PyprojectExtractor._component``'s shape exactly
  (``identity_source=NATIVE`` -- a PyPI-native declaration IS its own
  identity) but is NOT imported from ``pyproject.py``: duplicating the
  ~15-line exactness check here keeps this module's dependency graph
  one-directional (a lower-level shared foundation every extractor can
  depend on, never the reverse) rather than coupling it to one specific
  higher-level extractor's internals.
* ``read_bounded_text`` NFR-S5-bounds total size AND per-line length
  BEFORE any parser (YAML or TOML) sees the bytes -- a hostile manifest
  can never hang or OOM the parser. No compiled pattern here carries a
  nested unbounded quantifier.

This module parses/classifies DATA only: no ``jinja2`` import, no
execution primitive, no network module (NFR-S1/S2 -- the ``extract/``
AST-denylist meta-test covers this file automatically).
"""

from __future__ import annotations

import re
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement

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

# --- factored verbatim out of extract/lockfiles.py (Story 2.6) --------------

# The one confidence tier trusted enough to set pypi_identity (Story 2.1
# AC3). Exported (not module-private) so interfaces.py's dep001_trusted
# gate reuses this exact value instead of a disconnected copy.
TRUSTED_MATCH_CONFIDENCE = "verified"


def _resolve_conda_pypi_identity(
    name: str,
) -> tuple[PypiIdentity, str | None] | None:
    """Consult the conda->pypi map (Story 2.1) for ``name`` -- ``None`` on a
    miss. This defensively reads the two columns epics.md's own AC text
    names (``pypi_name`` and ``match_confidence``) and falls back to a miss
    on anything else -- never guessed, never crashes."""
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


def _unmapped_conda_component(
    name: str,
    version: str | None,
    provenance: tuple[Provenance, ...],
    mapping_confidence: str | None,
    *,
    extraction_mode: ExtractionMode = ExtractionMode.PARSED,
) -> Component:
    """The shared withhold shape for both a map miss and an
    untrusted-confidence hit (see ``_conda_component``) -- only
    ``mapping_confidence`` differs between the two callers, so both share
    one ``Component`` construction rather than drifting independently."""
    return Component(
        name=name,
        version=version,
        ecosystem=Ecosystem.CONDA,
        pypi_identity=None,
        identity_source=IdentitySource.NONE,
        mapping_confidence=mapping_confidence,
        cve_match_level=CveMatchLevel.NONE,
        extraction_mode=extraction_mode,
        purl=derive_purl(Ecosystem.CONDA, name, version),
        provenance=provenance,
        hygiene_covered=True,
        vuln_matchable=False,
        indeterminate_reason=WithholdReason.UNMAPPED_ECOSYSTEM,
    )


def _conda_component(
    name: str,
    version: str | None,
    provenance: tuple[Provenance, ...],
    *,
    extraction_mode: ExtractionMode = ExtractionMode.PARSED,
) -> Component:
    """Build a conda-ecosystem ``Component``, consulting the conda->pypi map
    (see ``_resolve_conda_pypi_identity``). Only a ``verified``-confidence
    hit is trusted enough to set ``pypi_identity`` (Story 2.1 AC3) -- a
    ``likely``/untrusted hit or an outright miss both withhold as
    ``UNMAPPED_ECOSYSTEM`` (never guessed), though a low-confidence hit's
    raw tier is still recorded on ``mapping_confidence`` for observability.

    ``extraction_mode`` (Story 2.2, default ``PARSED`` -- every pre-2.2
    caller's unchanged behavior): the 4 new format extractors pass
    ``NAME_ONLY`` here for a best-effort name recovered from an unresolved
    template construct, so it flows through the SAME identity-resolution
    path as a literal dependency rather than a parallel one."""
    mapped = _resolve_conda_pypi_identity(name)
    if mapped is None:
        return _unmapped_conda_component(
            name, version, provenance, None, extraction_mode=extraction_mode
        )
    identity, confidence = mapped
    if confidence != TRUSTED_MATCH_CONFIDENCE:
        return _unmapped_conda_component(
            name, version, provenance, confidence, extraction_mode=extraction_mode
        )
    identity = PypiIdentity(name=identity.name, version=version)
    return Component(
        name=name,
        version=version,
        ecosystem=Ecosystem.CONDA,
        pypi_identity=identity,
        identity_source=IdentitySource.MAP,
        mapping_confidence=confidence,
        cve_match_level=CveMatchLevel.EXACT if version else CveMatchLevel.NAME_ONLY,
        extraction_mode=extraction_mode,
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
    ``name``/``version`` (``identity_source=LOCK`` -- already
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
    """A row that could not be identified at all -- kept, marked, withheld;
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


# --- new in Story 2.2: conda matchspec syntax --------------------------------

# `name` stops at the first whitespace or operator character; `op` is one of
# the 7 conda/PEP-440-ish comparison tokens (2-char forms tried first so
# ">=" never partially matches as ">"); `version` is everything after,
# trimmed. No nested unbounded quantifiers (NFR-S5).
_CONDA_SPEC_RE = re.compile(
    r"^(?P<name>[^\s=<>!]+)\s*(?P<op>>=|<=|!=|==|=|>|<)?\s*(?P<version>.*)$"
)


def split_conda_dep_string(text: str) -> tuple[str, str | None] | None:
    """Split a conda matchspec-syntax dependency STRING (``name op version``,
    whitespace-separated OR contiguous, e.g. ``numpy >=1.20``,
    ``python=3.11``, bare ``python``) into ``(name, raw-specifier|None)``.
    ``None`` when ``text`` is empty/whitespace-only (a structurally empty
    entry -- the caller degrades it, never crashes)."""
    stripped = text.strip()
    if not stripped:
        return None
    match = _CONDA_SPEC_RE.match(stripped)
    if match is None:  # pragma: no cover -- the pattern is total over any
        return (stripped, None)  # non-empty string; defensive fallback only.
    name = match.group("name")
    op = match.group("op") or ""
    version = match.group("version").strip()
    if not version:
        return (name, None)  # a truly bare dependency: no specifier at all
    return (name, f"{op}{version}")


def classify_conda_specifier(
    specifier: str | None,
) -> tuple[str | None, WithholdReason | None]:
    """Classify a conda-syntax specifier (as returned by
    ``split_conda_dep_string``, or a pixi.toml TOML-table value verbatim)
    into ``(exact-version|None, non-exact-reason|None)`` -- see the module
    docstring for the exactness discipline."""
    if specifier is None or specifier.strip() in ("", "*"):
        return (None, WithholdReason.NO_VERSION)
    text = specifier.strip()
    for op in ("==", ">=", "<=", "!=", ">", "<", "="):
        if text.startswith(op):
            version = text[len(op) :].strip()
            # `===` (3+ leading equals) is NOT standard conda matchspec
            # syntax (conda uses bare/`=`/`==`, not PEP 440's `===`
            # "arbitrary equality") -- stripping exactly 2 leading `=`
            # chars here would otherwise leave a stray leading `=` baked
            # into `version` (`===1.2.3` -> `=1.2.3`), a corrupted value
            # silently treated as a confident exact match. Never guess:
            # an unrecognized 3+-equals shape falls through to the SAME
            # conservative RANGE_ONLY withhold as every other non-exact
            # operator below.
            if op == "==" and version and not version.startswith("="):
                if not version.endswith(".*"):
                    return (version, None)
            return (None, WithholdReason.RANGE_ONLY)
    # No operator prefix at all: a bare version token -- exact unless it is
    # itself a wildcard (mirrors pyproject's `==1.2.*`-is-a-range precedent).
    if text.endswith(".*"):
        return (None, WithholdReason.RANGE_ONLY)
    return (text, None)


# --- new in Story 2.2: PEP 508 syntax (pixi.toml [pypi-dependencies], -------
# environment.yml's nested `- pip:` list) ------------------------------------


def _exact_pep508_pin(requirement: Requirement) -> str | None:
    """Mirrors ``pyproject.py::_exact_pin``'s discipline (duplicated, not
    imported -- see the module docstring): only a single plain ``==`` or
    PEP 440 arbitrary-equality ``===`` specifier (non-wildcard) counts as a
    concrete version."""
    specifiers = list(requirement.specifier)
    if len(specifiers) != 1:
        return None
    specifier = specifiers[0]
    if specifier.version.endswith(".*"):
        return None
    if specifier.operator in ("==", "==="):
        return specifier.version
    return None


def pep508_pypi_component(
    raw: str, provenance: tuple[Provenance, ...]
) -> Component:
    """Build a PyPI-ecosystem ``Component`` from a PEP 508 requirement
    STRING -- ``identity_source=NATIVE``, mirroring
    ``pyproject.py::PyprojectExtractor._component``'s shape exactly (a
    PyPI-native declaration IS its own identity). Environment markers are
    ignored (union semantics, ``extraction_mode=union-marked``), same as
    ``pyproject.py``. An invalid PEP 508 string is kept ``raw-malformed``
    (never dropped)."""
    try:
        requirement = Requirement(raw)
    except InvalidRequirement:
        return _raw_malformed(Ecosystem.PYPI, raw, provenance)
    identity_name = canonical_name(Ecosystem.PYPI, requirement.name)
    extraction_mode = (
        ExtractionMode.UNION_MARKED
        if requirement.marker is not None
        else ExtractionMode.PARSED
    )
    version = _exact_pep508_pin(requirement)
    if version is not None:
        return Component(
            name=requirement.name,
            version=version,
            ecosystem=Ecosystem.PYPI,
            pypi_identity=PypiIdentity(name=identity_name, version=version),
            identity_source=IdentitySource.NATIVE,
            mapping_confidence=None,
            cve_match_level=CveMatchLevel.EXACT,
            extraction_mode=extraction_mode,
            purl=derive_purl(Ecosystem.PYPI, requirement.name, version),
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
        ecosystem=Ecosystem.PYPI,
        pypi_identity=PypiIdentity(name=identity_name, version=None),
        identity_source=IdentitySource.NATIVE,
        mapping_confidence=None,
        cve_match_level=CveMatchLevel.NAME_ONLY,
        extraction_mode=extraction_mode,
        purl=derive_purl(Ecosystem.PYPI, requirement.name, None),
        provenance=provenance,
        hygiene_covered=True,
        vuln_matchable=False,
        indeterminate_reason=reason,
    )


# --- new in Story 2.2: the shared NFR-S5 bounded read ------------------------


def read_bounded_text(
    manifest_path: Path,
    manifest: ScannedManifest,
    *,
    max_bytes: int,
    max_line_bytes: int,
) -> str:
    """Read + NFR-S5-bound the raw bytes (total size, THEN per-line length),
    THEN decode -- mirrors ``lockfiles.py::_read_bounded``'s two-cap pattern
    exactly, shared here so the 4 new Story 2.2 format extractors don't
    each duplicate it (``lockfiles.py`` keeps its own pre-2.2 copy
    untouched -- see the module docstring)."""
    raw = manifest_path.read_bytes()
    if len(raw) > max_bytes:
        raise UnparsableManifestError(
            f"unparsable manifest {manifest.path}: exceeds the "
            f"{max_bytes}-byte size cap (NFR-S5)"
        )
    for line in raw.split(b"\n"):
        if len(line) > max_line_bytes:
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: a line exceeds the "
                f"{max_line_bytes}-byte length cap (NFR-S5)"
            )
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UnparsableManifestError(
            f"unparsable manifest {manifest.path}: {exc}"
        ) from exc
