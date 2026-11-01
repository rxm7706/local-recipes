"""Where each dependency is declared -- the ``manifest_locations`` map (Story 16.6).

One builder for the ``canonical subject -> ("<manifest> [<section>]", ...)`` map
that ``render_text``'s remediation lines and the fix-PR actuator's manifest edit
both read. ``warden scan`` builds it from the post-merge inventory it already
holds (``manifest_locations_from_inventory``); the fleet's approve task builds
it on a fresh clone (``manifest_locations_for_target``), so the approved fix is
edited where the clone declares the package, never where an older scan saw it.
"""

from __future__ import annotations

from pathlib import Path

from .discovery import discover
from .extract import extractor_for
from .inventory import Component, ResolvedInventory, merge_components
from .report import _canonical_subject_key
from .routing import DefaultRouter


def manifest_locations_from_inventory(inventory: ResolvedInventory) -> dict[str, tuple[str, ...]]:
    """The ``manifest_locations`` map for a post-merge inventory.

    A finding's ``subject`` is the raw component name, so the map is keyed the
    same way, canonicalized with ``report._canonical_subject_key`` so a
    manifest's non-normalized spelling (``Foo_Bar``) still matches
    osv-scanner's normalized echo. Two components can share one name at
    different versions post-merge, so every same-named component's provenance
    is unioned (sorted, deduplicated) rather than the last one winning. A
    component with a ``pypi_identity`` is keyed by that name too: a vuln
    finding's subject mirrors the synthesized PyPI identity, which can differ
    from a conda component's own name. A subject with no entry simply gets no
    manifest clause and no manifest edit."""
    manifest_locations: dict[str, tuple[str, ...]] = {}
    for component in inventory.components:
        locations = tuple(f"{p.manifest} [{p.section}]" for p in component.provenance)
        keys = [_canonical_subject_key(component.name)]
        if component.pypi_identity is not None:
            keys.append(_canonical_subject_key(component.pypi_identity.name))
        for key in keys:
            manifest_locations[key] = tuple(sorted(set(manifest_locations.get(key, ())) | set(locations)))
    return manifest_locations


def manifest_locations_for_target(target: Path) -> dict[str, tuple[str, ...]]:
    """Discover and extract the Python manifests under ``target``, then build the map.

    Best effort, for a fix rather than a verdict: a manifest that fails to
    extract contributes no location (a package it alone declares then gets no
    manifest edit, which the actuator records as a failed outcome). Native
    non-Python lockfiles are not discovered -- the manifest edit never touches
    them. A discovery ``OSError`` propagates to the caller."""
    router = DefaultRouter()
    components: list[Component] = []
    manifests = discover(target)
    for manifest in manifests:
        try:
            extractor = extractor_for(manifest.kind, router)
            components.extend(extractor.extract(target / manifest.path, manifest))
        except Exception:  # noqa: BLE001 -- one bad manifest never loses the others
            continue
    inventory = ResolvedInventory(components=merge_components(components), resolved_scan_set=manifests)
    return manifest_locations_from_inventory(inventory)
