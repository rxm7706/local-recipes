"""BSL-driven Vizro read surface (Story D2, FR-9, AD-8/AD-17/NFR-8).

The D2 dashboard layer ports the read-only atlas CLIs to Vizro pages. Every page
gets its data by QUERYING the D1 Boring-Semantic-Layer models
(``pyforge.atlas.semantic``) — the single metric-translation interface (AD-8) — never
by re-writing SQL or re-implementing a metric in this layer.

Scope: the full 34-page inventory ships (Story 20.5, CAP-7 — closes DW-D2-1), ported
against the CIS two-spine design (``planning-artifacts/{DESIGN,EXPERIENCE}.md``, Story
20.4). Pages whose migrated data is not yet in the store are BSL-wired SHELLS that
render empty (never fabricated) and carry a documented data-gap note; 4 pages are
FR-9 report-artifact viewers (latest cached run only) and 2 are per-invocation
live-scan-artifact pages.

Story 27.3 closed the gap between what DESIGN.md specifies and what rendered: each
page's ``PageDef`` now DECLARES the filter columns and the chart DESIGN.md gives it
(``app._declared_filters`` / ``app._declared_chart`` build them,
``tests/integration/dashboard/test_dashboard_controls.py`` reds on drift either way),
the two live-scan pages really submit their scan (:mod:`.scan_submit`, through the
sanctioned ``pyforge.core.process`` seam — this package starts a process nowhere
else), and the page chrome carries ``navigation``/``main`` landmarks that Vizro
0.1.60 does not ship (``app.LandmarkDashboard``).

``vizro`` is REPLACEABLE visualization glue (AD-1/AD-6 spirit): only this subpackage may
import it (enforced by ``tests/catalog/test_no_inline_io.py``), mirroring the C1
dagster-glue and D1 BSL-in-``semantic/`` scoping.
"""

from __future__ import annotations

from .app import build_dashboard

__all__ = ["build_dashboard"]
