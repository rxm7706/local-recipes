"""The canonical, digest-pinned context bundle (Story 46.2, spec-pyforge-
marshal CAP-192).

Story 28.8 gave the ``derived-context`` layer its DECLARATION half: which
planning sources feed which derived artifact. This module extends that
declaration surface -- the epic's declared ``DerivedArtifactDeclaration``s
plus the resolved ``derived-context``/``planning-graph`` layer config --
into one canonical, JSON-safe bundle, sha256-hashed over its sorted-key
serialization (``marshal context bundle --epic N [--expect-digest SHA]``).

Assembling the bundle needs no scribe subprocess: it hashes only
already-declared, already-resolved data, so two harnesses on the same
commit produce byte-identical bundles deterministically -- the one thing
genuinely provable byte-identical across Claude, Cursor, Copilot, Gemini
and Devin, unlike the LLM-authored ``epic-<N>-context.md`` prose itself
(Design Notes: never included in the hashed bundle).

Pure -- no filesystem, no ``os``, no ``time``, no subprocess (AD-4).
``cli/context.py`` owns the boundary I/O (listing the planning directories,
resolving the composed policy); this module only shapes and hashes data it
is handed.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence

from .derived_context import DerivedArtifactDeclaration
from .model import Finding, Severity

__all__ = (
    "BUNDLE_SCHEMA",
    "BUNDLE_SCHEMA_VERSION",
    "assemble_bundle",
    "bundle_digest",
    "digest_mismatch_finding",
)

#: Identifies the bundle shape -- distinct from the derived-context
#: manifest's own schema, which this module never writes.
BUNDLE_SCHEMA = "marshal-context-bundle"
BUNDLE_SCHEMA_VERSION = 1


def assemble_bundle(
    *,
    epic: str,
    derived_context_layer: Mapping[str, object] | None,
    planning_graph_layer: Mapping[str, object] | None,
    declarations: Sequence[DerivedArtifactDeclaration],
) -> dict[str, object]:
    """The canonical, JSON-safe context bundle for ``epic``.

    ``derived_context_layer``/``planning_graph_layer`` are the already-
    resolved ``{"enabled": bool, "aggressiveness": str}`` dicts
    ``policy.resolve_context_layers`` (via ``cli/seed.py``'s wrapper)
    produces for each of ``derived_context.DERIVED_CONTEXT_LAYER`` and
    ``planning_graph.PLANNING_GRAPH_LAYER`` -- ``None`` reads the same as an
    absent/off layer, the same rule every other consumer of that
    composition applies.

    ``declarations`` is sorted by name in the output -- the same stability
    ``derived_context.manifest_payload`` gives its own manifest, and for
    the same reason: an unstable ordering would churn the digest for no
    reason.

    Deliberately hashes only the DECLARATION half (source lists + resolved
    layer config), never the LLM-authored ``epic-<N>-context.md`` prose
    itself: two independent harness sessions never produce byte-identical
    prose, but they DO see the same on-disk planning files and the same
    composed policy on the same commit -- so hashing exactly this data is
    the one thing genuinely provable byte-identical across harnesses.
    """
    derived_layer = derived_context_layer or {}
    planning_layer = planning_graph_layer or {}
    return {
        "schema": BUNDLE_SCHEMA,
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "epic": epic,
        "derived_context": {
            "enabled": bool(derived_layer.get("enabled", False)),
            "aggressiveness": derived_layer.get("aggressiveness"),
            "declarations": [
                {
                    "name": declaration.name,
                    "sources": list(declaration.sources),
                    "output": declaration.output,
                }
                for declaration in sorted(declarations, key=lambda item: item.name)
            ],
        },
        "planning_graph": {
            "enabled": bool(planning_layer.get("enabled", False)),
            "aggressiveness": planning_layer.get("aggressiveness"),
        },
    }


def bundle_digest(bundle: Mapping[str, object]) -> str:
    """sha256 hex digest over a canonical sorted-key JSON serialization of
    ``bundle`` -- mirrors ``core/policy.py::EffectivePolicy.content_hash``
    and ``core/substrate.py``'s manifest digest primitive verbatim
    (``hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8"))
    .hexdigest()``), so the same commit and the same composed policy
    produce the same digest regardless of which harness assembled it."""
    canonical = json.dumps(bundle, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def digest_mismatch_finding(*, epic: str, expected: str, computed: str) -> Finding:
    """MRS-CTX-008 (WARN): a second harness's ``--expect-digest`` does not
    match the freshly assembled bundle's digest. Names both digests --
    never silent -- and never blocks: a mismatch means the two harnesses
    disagree on what to open with, not that either one failed to run."""
    return Finding(
        code="MRS-CTX-008",
        severity=Severity.WARN,
        message=(
            f"context bundle digest mismatch for epic {epic!r}: expected "
            f"{expected!r}, computed {computed!r}"
        ),
        path=None,
    )
