"""External evidence sources + the standalone identity API (Story 7.1).

Epic 7 (estate-wide eligibility) needs two things Warden's per-project scan
pipeline doesn't provide on its own: a way to ingest evidence about package
eligibility from OUTSIDE the scanned project (an existing SBOM, another
manifest tree) and a standalone way to compute a canonical package identity
without first constructing a full 15-field ``inventory.Component``. This
module supplies both:

* ``PackageIdentity``/``resolve_identity`` — the standalone identity API,
  built on ``inventory.canonical_name``/``inventory.derive_purl`` verbatim
  (never a second, divergent implementation) plus a small curated PyPI
  alias table for import-name-vs-distribution-name mismatches
  (``sklearn`` -> ``scikit-learn``).
* ``SourceContract`` — an ``@runtime_checkable`` Protocol
  (``name`` + ``fetch``/``parse``/``validate``/``ingest``), mirroring the
  ``Engine``/``Extractor``/``Router`` precedent in ``interfaces.py``.
  ``fetch``/``parse``/``validate``'s intermediate payload shapes are
  adapter-own (raw JSON text vs. a discovered manifest tuple, say) — only
  ``ingest``'s no-argument, ``tuple[SourceEvidence, ...]``-returning shape
  is shared across every adapter, so this Protocol types those three stages
  as plain ``object`` deliberately, not by omission.
* ``register_source``/``source_factories``/``registered_sources`` — a
  registration registry mirroring ``engines.py``'s
  ``register_engine``/``engine_factories``/``registered_engines`` exactly,
  including its same-factory-object idempotency guard.
* Two concrete adapters: ``CycloneDXSourceAdapter`` (reads an EXTERNAL
  CycloneDX JSON document — Story 7.3 owns CycloneDX *output*, this only
  *reads* one) and ``ManifestSourceAdapter`` (wraps the existing
  per-project scan pipeline — ``discovery.discover`` +
  ``extract.extractor_for`` + ``routing.DefaultRouter``, all reused
  unchanged — as one evidence source over a local target).

Design decision (recorded 2026-08-22, review loopback 1): the registry
mechanism above is built and fully tested WITHOUT self-registering either
shipped adapter at module import time. Neither adapter is zero-arg-
constructible (both require a ``Path`` at construction — an external
CycloneDX document path, or a local scan target) and this story names no
legitimate default ``Path`` for either (no bundled default document, no
default scan target). Inventing one purely to populate the registry at
import time would be exactly the speculative behavior "Simplicity First"
forbids, and would make a bare ``registered_sources()`` call either crash
on first use or return misleading placeholder instances. A later call site
that actually knows an adapter's construction path registers a concrete
zero-arg closure there instead, e.g.::

    register_source(lambda: CycloneDXSourceAdapter(doc_path))

No adapter in this module opens a network socket (NFR-S2 precedent): both
read only the local filesystem.

This module reads local files as DATA only: no subprocess, no network.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from packageurl import PackageURL

from . import discovery
from .extract import extractor_for
from .inventory import Component, canonical_name, derive_purl
from .models import Ecosystem, ScannedManifest
from .routing import DefaultRouter

# --- the identity API ------------------------------------------------------

# Small, curated, git-review-owned PyPI import-name -> distribution-name
# aliases (mirrors this codebase's existing hand-curated-table precedent:
# mapping.py's bundled conda<->pypi map, the LTS registry, the license map).
# Keys are already PEP-503-canonical (``resolve_identity`` applies this
# table AFTER normalizing) -- seeded with the one alias the epic AC names;
# extend by review, never by a general alias-mining engine.
_PYPI_ALIASES: dict[str, str] = {
    "sklearn": "scikit-learn",
}


@dataclass(frozen=True)
class PackageIdentity:
    """A resolved package identity from an evidence source.

    Deliberately standalone -- NOT ``inventory.Component``. ``Component``
    carries several additional fields (``mapping_confidence``,
    ``cve_match_level``, ``provenance``, ``hygiene_covered``, ...) that
    describe a per-project compliance SCAN, meaningless to an external
    evidence source that only knows "this package, this version, from this
    place." ``PackageIdentity`` is the smallest value object that lets
    ``inventory.canonical_name``/``derive_purl`` be reused without that
    unrelated baggage.
    """

    ecosystem: Ecosystem
    canonical_name: str
    version: str | None
    purl: str


def resolve_identity(ecosystem: Ecosystem, name: str, version: str | None = None) -> PackageIdentity:
    """Resolve ``(ecosystem, name, version)`` to a canonical ``PackageIdentity``.

    PEP-503-normalizes ``name`` via ``inventory.canonical_name`` (identical
    to ``inventory.Component``'s own identity rule), then applies
    ``_PYPI_ALIASES`` (pypi-only -- conda names are already channel-
    canonical, per ``canonical_name``'s own contract), then derives the
    purl via ``inventory.derive_purl`` from the alias-resolved canonical
    name. An empty-string ``version`` normalizes to ``None`` HERE, in
    exactly this one place -- ``PackageIdentity`` itself carries no
    ``__post_init__`` duplicating the check.
    """
    version = version if version else None
    resolved_name = canonical_name(ecosystem, name)
    if ecosystem is Ecosystem.PYPI:
        resolved_name = _PYPI_ALIASES.get(resolved_name, resolved_name)
    return PackageIdentity(
        ecosystem=ecosystem,
        canonical_name=resolved_name,
        version=version,
        purl=derive_purl(ecosystem, resolved_name, version),
    )


@dataclass(frozen=True)
class SourceEvidence:
    """One observation of a package's identity from a ``SourceContract``.

    ``source_name`` is the adapter's own ``name``; ``locator`` identifies
    WHERE within that source the observation came from (the CycloneDX
    document path, or the scanned target path); ``raw_name`` is the
    identity-bearing name exactly as the source declared it (before
    ``resolve_identity``'s canonicalization), kept alongside the resolved
    ``identity`` for provenance/debugging.
    """

    identity: PackageIdentity
    source_name: str
    locator: str
    raw_name: str


# --- the SourceContract Protocol + registry --------------------------------


@runtime_checkable
class SourceContract(Protocol):
    """An evidence source: ``fetch`` -> ``parse`` -> ``validate`` -> per-
    entry identity resolution, mirroring the ``Engine``/``Extractor``/
    ``Router`` precedent in ``interfaces.py``. ``ingest`` takes no
    arguments and internally sequences the three prior stages itself --
    callers only ever call ``ingest()``.

    ``fetch``/``parse``/``validate``'s payload shapes are adapter-own (see
    the module docstring), so they are typed here as plain ``object``
    deliberately -- only ``ingest``'s shape is shared across every adapter.
    """

    name: str

    def fetch(self) -> object: ...

    def parse(self, raw: object) -> object: ...

    def validate(self, parsed: object) -> object: ...

    def ingest(self) -> tuple[SourceEvidence, ...]: ...


_SOURCE_FACTORIES: list[Callable[[], SourceContract]] = []


def register_source(
    factory: Callable[[], SourceContract],
) -> Callable[[], SourceContract]:
    """Register a source factory (decorator-friendly: returns the factory).

    Mirrors ``engines.register_engine`` exactly, including its same-
    factory-object idempotency guard: re-registering the SAME factory
    object is a no-op. That guard only de-dupes a reused factory
    REFERENCE, never a freshly-constructed closure -- a caller who wants
    idempotent registration must hold onto and reuse ONE factory object; a
    fresh ``lambda: Adapter(path)`` built on each registration attempt is a
    DIFFERENT object every time (even closing over an identical argument)
    and registers again, since object identity, not argument equality, is
    what this guard checks.
    """
    if factory not in _SOURCE_FACTORIES:
        _SOURCE_FACTORIES.append(factory)
    return factory


def source_factories() -> tuple[Callable[[], SourceContract], ...]:
    """The registered factories, in deterministic (registration) order."""
    return tuple(_SOURCE_FACTORIES)


def registered_sources() -> tuple[SourceContract, ...]:
    """Fresh adapter instances, in deterministic (registration) order.

    Starts EMPTY and stays empty unless a caller registers a concrete
    factory -- see the module docstring's Design decision note."""
    return tuple(factory() for factory in _SOURCE_FACTORIES)


# --- CycloneDXSourceAdapter --------------------------------------------------

_CYCLONEDX_BOM_FORMAT = "CycloneDX"

# purl type token -> Ecosystem (derived from the enum, never hand-spelled
# twice -- both ecosystems' purl type strings equal their StrEnum value).
_ECOSYSTEM_BY_PURL_TYPE: dict[str, Ecosystem] = {ecosystem.value: ecosystem for ecosystem in Ecosystem}


class CycloneDXSourceAdapter:
    """Reads evidence from an EXTERNAL CycloneDX JSON document (read-only --
    Story 7.3 owns CycloneDX *output*; this is the mirror-image *read*
    path). Only the flat top-level ``components[]`` array is walked --
    nested/transitive ``components[].components[]`` entries and the
    document's own ``metadata.component`` are out of this story's scope
    (matches the spec's I/O matrix, which only describes a flat
    ``components[]``)."""

    name: str = "cyclonedx"

    def __init__(self, path: Path) -> None:
        self._path = path

    def fetch(self) -> str | None:
        """The document's raw text, or ``None`` on an untrustworthy read
        (missing file, unreadable, non-utf-8) -- mirrors
        ``feeds.load_kev_catalog``'s own tolerant fetch-stage convention."""
        try:
            return self._path.read_text(encoding="utf-8")
        except OSError, UnicodeDecodeError:
            return None

    def parse(self, raw: str | None) -> object | None:
        """A tolerant ``json.loads`` -- ``None`` on anything not valid JSON
        (mirrors ``feeds.load_kev_catalog``)."""
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except ValueError:
            # json.JSONDecodeError is itself a ValueError subclass.
            return None

    def validate(self, parsed: object | None) -> list[object] | None:
        """Checks ``bomFormat == "CycloneDX"`` and a list ``components``
        key; returns the component list, or ``None`` on anything else
        untrustworthy (not an object, wrong ``bomFormat``, non-list/absent
        ``components``)."""
        if not isinstance(parsed, dict):
            return None
        if parsed.get("bomFormat") != _CYCLONEDX_BOM_FORMAT:
            return None
        components = parsed.get("components")
        if not isinstance(components, list):
            return None
        return components

    def ingest(self) -> tuple[SourceEvidence, ...]:
        components = self.validate(self.parse(self.fetch()))
        if not components:
            return ()
        evidence: list[SourceEvidence] = []
        for entry in components:
            if not isinstance(entry, dict):
                continue
            purl_value = entry.get("purl")
            if not isinstance(purl_value, str) or not purl_value:
                # No purl, or a non-string value: never guessed (mirrors
                # feeds.py's tolerant-per-entry convention).
                continue
            try:
                purl = PackageURL.from_string(purl_value)
            except ValueError:
                # An unparseable purl string: skipped, not raised.
                continue
            ecosystem = _ECOSYSTEM_BY_PURL_TYPE.get(purl.type)
            if ecosystem is None:
                # An unrecognized purl type (e.g. npm): out of this story's
                # two-ecosystem scope, skipped.
                continue
            raw_name = entry.get("name")
            if not isinstance(raw_name, str) or not raw_name:
                # Falls back to the purl's own name -- always present on a
                # successfully-parsed purl.
                raw_name = purl.name
            evidence.append(
                SourceEvidence(
                    identity=resolve_identity(ecosystem, purl.name, purl.version),
                    source_name=self.name,
                    locator=str(self._path),
                    raw_name=raw_name,
                )
            )
        return tuple(evidence)


# --- ManifestSourceAdapter ---------------------------------------------------


class ManifestSourceAdapter:
    """Wraps the existing per-project scan pipeline (``discovery.discover``
    + ``extract.extractor_for`` + ``routing.DefaultRouter``, all reused
    UNCHANGED -- no new manifest-parsing logic) as one ``SourceContract``
    evidence source over a local target."""

    name: str = "manifest"

    def __init__(self, target: Path) -> None:
        self._target = target

    def fetch(self) -> tuple[ScannedManifest, ...]:
        """The resolved scan set -- degrades to an empty tuple on any
        ``OSError`` (``discovery.discover``'s own documented fail-closed
        contract: a missing/inaccessible/replaced target, a symlinked
        subdirectory, or an entry-cap overrun), mirroring
        ``CycloneDXSourceAdapter.fetch()``'s own OSError-tolerant guard --
        a bad scan target degrades to no evidence rather than crashing
        ``ingest()``."""
        try:
            return discovery.discover(self._target)
        except OSError:
            return ()

    def parse(self, manifests: tuple[ScannedManifest, ...]) -> tuple[Component, ...]:
        """Extracts every manifest via the real per-project pipeline,
        tolerating (skipping) any manifest whose extraction raises --
        mirrors ``cli.py``'s own broad ``except (SystemExit, Exception)``
        backstop at the identical extraction call site: one manifest's
        unexpected extractor bug (``UnparsableManifestError``, ``OSError``,
        or anything else) must never crash evidence collection for the
        rest of the target."""
        router = DefaultRouter()
        components: list[Component] = []
        for manifest in manifests:
            try:
                extractor = extractor_for(manifest.kind, router)
                extracted = extractor.extract(self._target / manifest.path, manifest)
                components.extend(extracted)
            except SystemExit, Exception:  # noqa: BLE001, S112 -- the
                # tolerant-per-manifest seam doctrine (cli.py's own
                # identical backstop at this call site): any exception here
                # is this one manifest's problem, never a reason to abort
                # the rest, and there is nothing else to do with it (no
                # ErrorRecord contract exists on SourceEvidence).
                # components.extend(extracted) is INSIDE this same try: a
                # malformed (non-iterable/None) return from a future/buggy
                # extractor must be tolerated exactly like a raised
                # exception, never crash evidence collection for the rest
                # of the target.
                continue
        return tuple(components)

    def validate(self, components: tuple[Component, ...]) -> tuple[Component, ...]:
        """A pass-through identity check -- always a valid, possibly-empty
        tuple (``parse`` already produced honest ``Component``s)."""
        return components

    def ingest(self) -> tuple[SourceEvidence, ...]:
        components = self.validate(self.parse(self.fetch()))
        return tuple(
            SourceEvidence(
                identity=resolve_identity(component.ecosystem, component.name, component.version),
                source_name=self.name,
                locator=str(self._target),
                raw_name=component.name,
            )
            for component in components
        )
