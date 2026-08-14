---
spec: atlas-query-dashboards
status: ready
owner-dream: docs/dreams/atlas-query-dashboards.md
surface:
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/  # new presentation module — nothing Panel/Bokeh-shaped exists in the repo yet
sources:
  - ../../../../../../docs/dreams/atlas-query-dashboards.md
open_questions:
  - "Which widget types actually matter for atlas's query shapes (grid vs chart vs pivot, per view) — the registry's seed set is a decomposition-time survey of the 11 mirrored CLIs, not the source dream's Tabulator/Perspective/PGWalker catalog."
  - "Session bridging if these views are ever hosted against Steward's dashboard surface — Steward has its own, narrower identity-at-the-boundary model; bridging is a decision made then, never assumed here."
  - "ASGI host choice — the contract is 'any ASGI host'; which one actually mounts the Bokeh WebSocket protocol is picked at decomposition time (explicitly NOT contingent on DW-H3/Wagtail)."
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what
> to build, test, and validate. `docs/dreams/atlas-query-dashboards.md` is listed in
> `sources:` for narrative rationale this contract intentionally omits.

# A `cf_atlas.db` query renders as a hand-someone-a-link dashboard — Panel/Bokeh, no SPA

## Why

A gap to close, not a bug. `cf_atlas.db` (DuckDB, 16 schema versions of real analytical data —
staleness, feedstock health, PyPI intelligence, universe-SBOM inventory) is queryable today only
through CLI tools or hand-written SQL against the database file. The 11 atlas query CLIs named in
the skill reference (`detail-cf-atlas`, `staleness-report`, `feedstock-health`, `whodepends`,
`behind-upstream`, `cve-watcher`, `version-downloads`, `release-cadence`, `find-alternative`,
`adoption-stage`, `scan-project`) are each, structurally, "a DuckDB query rendered as text";
nothing renders the same queries as an interactive, filterable, drillable view you can hand
someone a link to. The remedy is Panel/Bokeh widgets — server-rendered / WebSocket-driven,
explicitly NO SPA framework, per this repo's established convention for tooling surfaces
(Steward's dashboard app is server-rendered Django; Herald's Guildhall board is vanilla JS).

Station state: pyforge-atlas is complete (68/70; only optional per-epic retros open), so capacity
exists — this Spec opens a NEW epic at decomposition time; it resumes nothing prior.

## Capabilities

- **CAP-1**
  - **intent:** The lowest-risk rendering mode ships first: a curated catalog of views mirroring
    the existing CLIs (`staleness-report`, `feedstock-health`, `whodepends`, …), each a static
    query against `cf_atlas.db` rendered as an HTML fragment — no WebSocket, no server session.
    The query surface is `cf_atlas.db` directly; there is no second data layer.
  - **success:** Each catalog view emits a self-contained HTML fragment from the live
    `cf_atlas.db` whose rows agree with its CLI counterpart's output on the same database
    snapshot; rendering a static view opens zero WebSocket connections.
- **CAP-2**
  - **intent:** Genuinely interactive views (filter, drill, re-sort live) layer on Bokeh's
    WebSocket protocol through whatever ASGI host is chosen at decomposition time — host-agnostic
    by design ("a Panel/Bokeh dashboard needs an ASGI host, not specifically a CMS"); no
    dependency on DW-H3/Wagtail being stood up.
  - **success:** At least one catalog view runs filter/drill/re-sort against `cf_atlas.db` over a
    live Bokeh WebSocket session on the chosen host; swapping the host touches mounting code
    only, never a view definition.
- **CAP-3**
  - **intent:** Widget TYPES are pluggable behind a small registry, not hard-coded to a
    Tabulator/chart/pivot set — a view declares its query plus a widget-type name; the registry
    maps name → renderer for both the static-fragment and WebSocket modes.
  - **success:** Adding a new widget type is one registry entry plus one renderer, with zero
    edits to existing view definitions; the seed set is derived from atlas's own query shapes
    (open question 1), not inherited from the source dream's catalog.
- **CAP-4**
  - **intent:** The CDN-URL-rewriting concern for air-gapped deployment is carried from day one,
    for static fragments and WebSocket apps alike: Bokeh/Panel asset URLs resolve to
    locally-served or mirrored assets, composing with `_http.py`'s runtime-driven enterprise
    posture (truststore + JFrog/GitHub/.netrc chain, env vars only, never committed config) —
    the dream flags this as the most directly applicable piece of its source.
  - **success:** A page rendered under the air-gapped profile contains zero references to
    external CDN hosts (verifiable by grepping the emitted HTML); the default profile's output
    is unchanged.

## Constraints

- **Always:** query `cf_atlas.db` directly — no second data layer, no parallel query surface, no
  new metric computation. This visualizes what atlas already computes.
- **Always:** no SPA framework (React/Vue or kin) — server-rendered / WebSocket-driven only,
  matching every existing dashboard surface in this repo.
- **Always:** mode ordering is risk ordering — the static-fragment mode (CAP-1) is the base
  layer; WebSocket interactivity (CAP-2) layers on top of it and never replaces it.
- **Always:** host-agnostic — nothing in the view catalog, registry, or renderers binds to a
  specific ASGI host, and nothing presupposes DW-H3/Wagtail existing.

## Non-goals

- **Not** a notebook-style coding environment — read-only visualization of existing queries,
  per the source dream's v1 scope, carried over unchanged.
- **Not** real-time streaming — queries run on demand.
- **Not** a drag-and-drop dashboard builder or general BI tool — a curated set of views.
- **Not** deciding whether the Wagtail CMS (atlas ledger `DW-H3`) gets built — this Spec neither
  depends on nor blocks that already-deferred, attended decision.
- **Not** a rework of atlas's existing Vizro dashboard module
  (`src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/`, Story D2) — that surface
  reads the migrated Parquet catalog through the D1 BSL seam; this one queries `cf_atlas.db`
  directly and lands as a separate module under a non-colliding name.

## Success signal

Today, handing someone the answer to "which feedstocks are stale?" means running
`staleness-report` and pasting text. After this ships: every view in the curated catalog renders
from the live `cf_atlas.db` as a linkable static HTML fragment (CAP-1); at least one view is
live-interactive over Bokeh's WebSocket protocol on the chosen ASGI host (CAP-2); a new widget
type lands as a registry entry without touching view definitions (CAP-3); and the air-gapped
render profile emits pages with zero external CDN URLs (CAP-4).

## Open Questions

- "Which widget types actually matter for atlas's query shapes (grid vs chart vs pivot, per
  view) — the registry's seed set is a decomposition-time survey of the 11 mirrored CLIs, not
  the source dream's Tabulator/Perspective/PGWalker catalog."
- "Session bridging if these views are ever hosted against Steward's dashboard surface — Steward
  has its own, narrower identity-at-the-boundary model; bridging is a decision made then, never
  assumed here."
- "ASGI host choice — the contract is 'any ASGI host'; which one actually mounts the Bokeh
  WebSocket protocol is picked at decomposition time (explicitly NOT contingent on
  DW-H3/Wagtail)."
