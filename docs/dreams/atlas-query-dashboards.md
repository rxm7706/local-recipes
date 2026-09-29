---
title: A query against the atlas DB becomes an interactive dashboard, no SPA framework
type: dream
owner: atlas
status: archived
archived-reason: retired
---

> **Consolidated into** [`docs/dreams/pyforge-atlas.md`](pyforge-atlas.md) on 2026-09-17 (one-chain-per-station CAP-3). This file is the record; new work appends to the station Dream.

# A query against the atlas DB becomes an interactive dashboard, no SPA framework

## The Dream

`cf_atlas.db` (DuckDB) already holds 16 schema versions' worth of real analytical data —
staleness, feedstock health, PyPI intelligence, universe SBOM inventory — queryable today only
through CLI tools (`staleness-report`, `feedstock-health`, `whodepends`, etc.) or hand-written SQL
against the database file directly. This Dream is the gap between "I can query it" and "I can
hand someone an interactive, filterable, drillable view of the answer" — a Panel/Bokeh widget
embedded in a lightweight server, server-rendered and WebSocket-driven, never a React/Vue SPA —
matching this repo's own established no-SPA convention (Steward's dashboard app is server-rendered
Django; Herald's Guildhall board is vanilla JS).

## What it looks like when real

- A DuckDB query against `cf_atlas.db` renders as a Tabulator grid, a chart, or a pivot table —
  static queries as HTML fragments needing no WebSocket; genuinely interactive ones (filter,
  drill, re-sort live) running Bokeh's WebSocket protocol through whatever ASGI host is already in
  play, the same server-driven shape [[data-visualization-dashboards]]'s WF source describes for
  Django Channels, adapted to this repo's own hosting choices rather than assuming Django
  specifically.
- Widget TYPES are pluggable, not hard-coded to the source dream's own SQL-Explorer-specific set —
  this repo has no SQL Explorer dependency to abstract away in the first place, since the query
  surface here is atlas's own DuckDB file, not a third-party query tool's saved-query registry.
- No new client-side JavaScript framework — Bokeh/Panel's own server-side rendering is the whole
  point of the "Django, no React" shape both this Dream and its WF source were reaching for.

## What is real

`cf_atlas.db` (DuckDB `>=1.5.5`, per `pyforge-atlas`'s own `pixi.toml`) is real, live, and already
the target of the 11 CLI query tools listed in this repo's own skill reference
(`detail-cf-atlas`, `staleness-report`, `feedstock-health`, `whodepends`, `behind-upstream`,
`cve-watcher`, `version-downloads`, `release-cadence`, `find-alternative`, `adoption-stage`,
`scan-project`) — every one of them is, structurally, "a DuckDB query rendered as text"; this
Dream is the same queries rendered as an interactive widget instead. ~~Nothing
Panel/Bokeh/Channels-shaped exists in this repo yet — this is a genuinely new presentation layer,
not a port of anything already built.~~ *(Written 2026-08-14; **superseded 2026-09-09**, fleet
readiness pass. Bokeh-shaped code DID come to exist: Epic 14 built `pyforge/atlas/views/`, a
complete static-fragment + Bokeh-WebSocket runtime over six of these CLIs, and all four of its
stories read `done`. **Nothing ever called it** — no CLI verb, no pixi task, no ASGI mount, no
importer outside its own unit tests — and it reached `cf_atlas.db` through a bridge whose own
docstring records that its dynamic-import shape keeps the DuckDB-singularity gate green while the
loaded script imports `sqlite3` (`views/cli_bridge.py:11-17`). The operator retired it on
2026-09-09 (decision batch § 2.3 C1; atlas Story 25.1 deletes the package). The struck sentence is
kept as the record of where this Dream started — see § Realization log.)*

A related, larger finding surfaced while investigating this Dream: atlas already has a REAL,
tested (against an in-memory mock, network-injectable) client for an EXTERNAL Wagtail/Django CMS
— `factory/lasuite.py`'s `LaSuiteClient`/`WikiSyncer`, built for Story H3, pushing the
Karpathy-wiki's report pages to a "Corporate Brain" CMS. Standing up the live server side is
`DW-H3` (atlas's own deferred-work ledger) — explicitly deferred as an ATTENDED bring-up (an
operator decision, not a code gap), not speculative. If that server is ever stood up, THIS
Dream's Panel/Bokeh widgets are exactly the kind of thing the source `data-visualization-dashboards`
dream describes embedding inside a Wagtail `BokehPanelPage` — a real Kinship, but this Dream does
not depend on DW-H3 being resolved; a Panel/Bokeh dashboard needs an ASGI host, not specifically a
CMS.

## Constraints

- **Query `cf_atlas.db` directly — no second data layer.** This Dream visualizes what atlas
  already computes; it does not compute anything new or maintain a parallel query surface.
- **No SPA framework.** Server-rendered/WebSocket-driven only, matching this repo's established
  convention across every existing dashboard surface.

## Non-goals

- **Not a notebook-style coding environment** — read-only visualization of existing queries, per
  the source dream's own v1 scope, carried over unchanged.
- **Not real-time streaming** — queries run on demand.
- **Not a drag-and-drop dashboard builder** — a curated set of views, not a general BI tool.
- **Not deciding whether the Wagtail CMS (DW-H3) gets built** — that is atlas's own already-deferred,
  attended decision; this Dream neither depends on nor blocks it.

## Full feature audit against `data-visualization-dashboards`

Every capability the source dream names, and this Dream's disposition on each:

| Source feature | Disposition | Why |
|---|---|---|
| SQL Explorer query → Panel/Bokeh widget | **Reframed** | No SQL Explorer dependency exists here to abstract; the equivalent query surface is `cf_atlas.db` directly, already queried by 11 existing CLI tools. |
| Static query → HTML fragment (no WebSocket) | **Included** | Directly transferable — the simplest, lowest-risk rendering mode. |
| Interactive Panel app → Bokeh WebSocket via Channels, same OIDC session | **Included, host-agnostic** | The WebSocket-driven interactivity is kept; "via Django Channels specifically" is loosened to "via whatever ASGI host is in play," since this repo has no existing Django+Channels deployment this Dream should presuppose (unlike the WF source, which already has one). |
| JWT-based WebSocket session auth bridged to Django cookies | **Omitted, no target session system** | This repo has no existing web-session auth system a dashboard would bridge into yet — Steward's own dashboard (Story 9.1+) has its own, narrower identity-at-the-boundary model; if this Dream is ever realized against that surface, session bridging is a Spec-time decision, not assumed here. |
| Custom staticfiles finder for Bokeh/Panel extension assets | **Included, deferred detail** | Real implementation detail, not a scoping decision — carried forward as a "when built" concern, not resolved here. |
| CDN-URL rewriting for airgapped environments | **Included, high relevance** | This repo already has real air-gap/enterprise-routing concerns (`[[enterprise-airgap]]`, `_http.py`'s truststore chain) — this is one of the more DIRECTLY applicable pieces of the source dream, not a WF-specific artifact. |
| Pluggable widget types | **Included, reframed** | Kept as a design principle, but not scoped to the source's specific widget catalog (Tabulator/Perspective/PGWalker) — which widgets matter here is a Spec-time question against atlas's own query shapes. |

## Kinships

[[pyforge-atlas]] (the estate; `cf_atlas.db` is the data source) · [[enterprise-airgap]] (the
CDN-rewriting concern is directly relevant to this repo's own already-real air-gap posture) ·
[[artifactory-download-intelligence]] (a sibling atlas Dream captured in the same investigation;
its output could plausibly become one of this Dream's dashboards, not a dependency) ·
[[wagtail-corporate-brain]] (the dream this one's investigation surfaced — a real, evidence-backed
CMS destination this Dream's widgets could embed inside if that Dream's own narrow scope is ever
realized, not a dependency)

## Realization log

- **2026-08-14** — Dream captured while porting a sibling org's dream catalog for PyForge fit.
  Reframed from "Django+Channels+SQL-Explorer" (the source's own stack) to "no SPA, host-agnostic"
  since this repo has neither Django+Channels nor SQL Explorer deployed anywhere yet — the actual
  transferable idea is "server-rendered interactive widgets over an existing query surface," and
  `cf_atlas.db` is that surface. Investigation surfaced a larger, unrelated finding along the way:
  atlas already has a tested client (`factory/lasuite.py`) for an external Wagtail CMS, with the
  server-side bring-up explicitly deferred as `DW-H3` — real, not speculative, and directly
  relevant to re-scoping [[wagtail-corporate-brain]] far more favorably than this batch's
  first-pass tiering had it.
- **2026-08-14** — Spec authored (spec-atlas-query-dashboards, pyforge-atlas) by the 2026-08-14 dream-backlog audit: curated CLI-mirroring view catalog, static-fragment mode first, Bokeh-WebSocket interactivity behind a pluggable widget registry, ASGI-host-agnostic, air-gap CDN rewriting from day one.

- **2026-09-09** — **Fleet readiness pass, then RETIRED (operator batch § 2.3 C1).** Verified
  against live code at `fe4025ea90`. Epic 14 (CAP-1..4) and Epic 20 (CAP-5..7) all read `done`;
  `DESIGN.md`/`EXPERIENCE.md` exist; DW-D2-1 and DW-D2-2 are closed. But CAP-1..4's own runtime,
  `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/`, has **no importer outside its own
  unit tests** — no CLI verb, no pixi task, no ASGI mount, even though `views/__init__.py:10-13`
  describes `asgi.py::app` as a mount target. It also reads the legacy SQLite `cf_atlas.db`
  through `views/cli_bridge.py`, whose docstring (`:11-17`) records that its dynamic-import shape
  keeps the F1 DuckDB-singularity gate green while the loaded script imports `sqlite3` — a
  private, non-BSL read against the Unifying ruling "no private DuckDB … BSL is the
  dashboard/agent SQL contract" (`pyforge-unifying-strategy.md:400`), and against
  `spec-pyforge-atlas`'s own Non-goal "Continued SQLite". Built, merged, off — the
  marshal-token-economy shape. **Operator decision 2026-09-09: RETIRE.** The estate's real Lane-3
  surface is the Vizro board over the D1 BSL seam (`dashboard/app.py`, gated by
  `dashboard-dryrun`, served by `pixi run -e local-recipes dashboard-serve`). Atlas Story 25.1
  deletes the package and its tests; the widget-registry idea survives only if a Vizro page asks
  for it. The declared open question about session bridging dies with the module (the estate
  already forbids mounting an analytics runtime on the identity-bearing host —
  `src/platform/tests/test_host_board_row_isolation.py:26`). The Spec stays `in-progress` until
  25.1 lands and then reads `shipped` on the strength of CAP-5..CAP-7, which are real, live and
  exercised. Status here moves `specified` → `archived` (`archived-reason: retired`).
