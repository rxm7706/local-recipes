"""BSL-driven Vizro read surface (Story D2, FR-9, AD-8/AD-17/NFR-8).

The D2 dashboard layer ports the read-only atlas CLIs to Vizro pages. Every page
gets its data by QUERYING the D1 Boring-Semantic-Layer models
(``pyforge.atlas.semantic``) — the single metric-translation interface (AD-8) — never
by re-writing SQL or re-implementing a metric in this layer.

Scope (honest core): this wave ships the Vizro app framework, the live-confirmed-first
consumer pages the D2 AC names, and the fully-specified factory-status page. The FULL
28-page inventory + per-page visual design is CIS-two-spine-deferred (DESIGN.md +
EXPERIENCE.md, not yet produced) — see ``implementation-artifacts/deferred-work.md``
(DW-D2). Pages whose migrated data is not yet in the store are BSL-wired SHELLS that
render empty (never fabricated) and carry a documented data-gap note.

``vizro`` is REPLACEABLE visualization glue (AD-1/AD-6 spirit): only this subpackage may
import it (enforced by ``tests/catalog/test_no_inline_io.py``), mirroring the C1
dagster-glue and D1 BSL-in-``semantic/`` scoping.
"""

from __future__ import annotations

from .app import build_dashboard

__all__ = ["build_dashboard"]
