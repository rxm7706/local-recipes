"""Static-host Parquet artifact emitter — Story G2 (FR-14, AD-2, AD-21).

The **single owner** of the published-artifact LAYOUT (Spine convention): the chunking
scheme + the ``manifest.json`` contract are defined exactly ONCE, here. The ``publish`` Range
gate READS this layout (via :func:`load_manifest`) and never re-defines it.

**NOT YET a manifest consumer: the G1 ``wasm/`` runtime.** G1 shipped before this emitter and
its ``index.html`` fetches a flat ``./core_feedstock_health.parquet`` (its own ``build.py``
produces that flat file) — it does NOT read ``manifest.json``/:func:`chunk_url` today. So the
single-owner invariant holds for the emitter + the gate, but G1 is a SECOND, independent layout
until it is migrated to consume this manifest — that migration is DEFERRED (DW-G2-2). Do not
read this module's "single owner" as "every consumer already reads the manifest"; it means the
PUBLISHED-site layout has one authoritative definition here.

Host-agnostic (AD-2, Q4): :func:`emit_static_site` writes the artifact layout to a target
*directory* — "the static host filesystem". WHICH host serves that directory (GitHub Pages
for the public path, an enterprise/JFrog mirror for air-gapped consumers) is a deploy/config
choice, NOT baked into the emit logic. No host URL, no ``github.io``, appears anywhere in
this module. A consumer composes chunk URLs from a runtime base via :func:`chunk_url`.
"""

from __future__ import annotations

from .emitter import (
    LAYOUT_VERSION,
    MANIFEST_NAME,
    ManifestChecksumError,
    chunk_url,
    emit_static_site,
    load_manifest,
    verify_manifest,
)

__all__ = [
    "LAYOUT_VERSION",
    "MANIFEST_NAME",
    "ManifestChecksumError",
    "chunk_url",
    "emit_static_site",
    "load_manifest",
    "verify_manifest",
]
