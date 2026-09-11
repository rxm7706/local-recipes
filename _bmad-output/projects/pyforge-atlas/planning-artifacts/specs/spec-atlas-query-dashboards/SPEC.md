---
spec: atlas-query-dashboards
status: shipped   # Story 25.1 (2026-09-10): CAP-1..CAP-4 superseded by the live Vizro/BSL board;
                  # CAP-5..CAP-7 are the live contract. The second Lane-3 runtime is retired.
updated: "2026-09-09"
owner-dream: docs/dreams/atlas-query-dashboards.md
surface:
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/  # Epic 14 landed the Panel/Bokeh views module here; Epic 20 (CAP-5..7) extends the same package surface
  - scripts/dashboard_serve.py  # Story 20.5's DW-D2-3 local-serve entrypoint (CAP-7)
sources:
  - ../../../../../../docs/dreams/atlas-query-dashboards.md
  - ../../../../pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md  # § Open Questions — the three 2026-08-26 operator query-plane rulings that bind CAP-5..CAP-7
open_questions: []   # ANSWERED 2026-09-09. Session bridging (batch § 2.1 row atlas-B2) dies with
                     # the C1 retirement — no route survives to mount behind an authenticated host,
                     # and `src/platform/tests/test_host_board_row_isolation.py:26` already forbids
                     # the shape. The CIS two-spine question was STALE (readiness finding D-3):
                     # planning-artifacts/DESIGN.md and EXPERIENCE.md both exist, Stories 20.4 and
                     # 20.5 read `done`, DW-D2-1 reads `status: closed`.
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

- **CAP-1** — **SUPERSEDED 2026-09-09** (batch C1; see § *Retirement of the second Lane-3 runtime*)
  - **intent:** The lowest-risk rendering mode ships first: a curated catalog of views mirroring
    the existing CLIs (`staleness-report`, `feedstock-health`, `whodepends`, …), each a static
    query against `cf_atlas.db` rendered as an HTML fragment — no WebSocket, no server session.
    The query surface is `cf_atlas.db` directly; there is no second data layer.
  - **success:** Each catalog view emits a self-contained HTML fragment from the live
    `cf_atlas.db` whose rows agree with its CLI counterpart's output on the same database
    snapshot; rendering a static view opens zero WebSocket connections.
  - **verified:** retirement confirmed, not the original capability — `views/` (both
    `src/.../pyforge/atlas/views/` and `tests/unit/views/`) is fully deleted (commit
    `caeae255d05`), zero remaining importers of `pyforge.atlas.views` repo-wide
    (`git grep`), and `bokeh`/`panel` no longer appear in `pyforge-atlas`'s
    `pyproject.toml`. Superseded by the live Vizro/BSL board (`dashboard/app.py`).
- **CAP-2** — **SUPERSEDED 2026-09-09** (batch C1; see § *Retirement of the second Lane-3 runtime*)
  - **intent:** Genuinely interactive views (filter, drill, re-sort live) layer on Bokeh's
    WebSocket protocol through whatever ASGI host is chosen at decomposition time — host-agnostic
    by design ("a Panel/Bokeh dashboard needs an ASGI host, not specifically a CMS"); no
    dependency on DW-H3/Wagtail being stood up.
  - **success:** At least one catalog view runs filter/drill/re-sort against `cf_atlas.db` over a
    live Bokeh WebSocket session on the chosen host; swapping the host touches mounting code
    only, never a view definition.
  - **verified:** retirement confirmed (same evidence as CAP-1) — `views/` deleted in
    `caeae255d05`, zero remaining importers, `bokeh`/`panel` dropped from
    `pyproject.toml`. Superseded by the live Vizro/BSL board.
- **CAP-3** — **SUPERSEDED 2026-09-09** (batch C1; see § *Retirement of the second Lane-3 runtime*)
  - **intent:** Widget TYPES are pluggable behind a small registry, not hard-coded to a
    Tabulator/chart/pivot set — a view declares its query plus a widget-type name; the registry
    maps name → renderer for both the static-fragment and WebSocket modes.
  - **success:** Adding a new widget type is one registry entry plus one renderer, with zero
    edits to existing view definitions; the seed set is derived from atlas's own query shapes
    (open question 1), not inherited from the source dream's catalog.
  - **verified:** retirement confirmed (same evidence as CAP-1) — `views/` deleted in
    `caeae255d05`, zero remaining importers, `bokeh`/`panel` dropped from
    `pyproject.toml`; the "kept only if a Vizro page actually asks for it" condition
    above was not met (no Vizro page adopts a pluggable widget-type registry — confirmed
    no registry module exists under `dashboard/`).
- **CAP-4** — **SUPERSEDED 2026-09-09** (batch C1; see § *Retirement of the second Lane-3 runtime*)
  - **intent:** The CDN-URL-rewriting concern for air-gapped deployment is carried from day one,
    for static fragments and WebSocket apps alike: Bokeh/Panel asset URLs resolve to
    locally-served or mirrored assets, composing with `_http.py`'s runtime-driven enterprise
    posture (truststore + JFrog/GitHub/.netrc chain, env vars only, never committed config) —
    the dream flags this as the most directly applicable piece of its source.
  - **success:** A page rendered under the air-gapped profile contains zero references to
    external CDN hosts (verifiable by grepping the emitted HTML); the default profile's output
    is unchanged.
  - **verified:** retirement confirmed (same evidence as CAP-1) — `views/` deleted in
    `caeae255d05`, zero remaining importers, `bokeh`/`panel` dropped from
    `pyproject.toml`. Superseded by the live Vizro/BSL board.
**CAP-1..CAP-4 amendment, 2026-09-09** (operator, fleet-readiness decision batch § 2.3 C1 / row
atlas-B1). The intent of all four is superseded by the live Vizro/BSL board (`dashboard/app.py`'s
`PAGE_INVENTORY`, reached through the D1 BSL seam, gated by `dashboard-dryrun`, served by
`pixi run -e local-recipes dashboard-serve`). The module they shipped into —
`src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/` — has no importer outside its own
unit tests: no CLI verb, no pixi task, no ASGI mount. It is deleted together with
`tests/unit/views/` and the `cli_bridge` dynamic-import evasion of the F1 DuckDB-singularity gate
(`views/cli_bridge.py:11-17`). The four texts stay on the record above as what was built and stood
down; the widget-registry idea (CAP-3) is kept only if a Vizro page actually asks for it.
Retirement is atlas **Story 25.1**.

- **CAP-5** *(added 2026-08-27 — bound by the `query-plane-face` operator ruling, 2026-08-26)*
  - **intent:** The query plane the views read serves BOTH faces behind ONE boot script: the
    in-process library face stays the default for every consumer that can reach the file
    (AD-16 local-first; DuckDB stays a query face, never a fourth backing store), and the
    Mosaic `duckdb-server` HTTP/Arrow face is raised by the SAME single, pixi-sourced boot
    script — only when the platform stack is up. Filesystem-less consumers bind to the HTTP
    face per CAP-19's success wording ("the plane DSN or HTTP face").
  - **success:** One boot script raises both faces; with the platform stack down it degrades
    to library-face-only with a structured notice, never a crash; no second boot path exists
    (grep-verifiable single `duckdb-server` launch site); a parity gate runs an identical
    query set against both faces and fails on any divergence — parity is part of the face's
    definition of done.
  - **verified:** the single boot script (`query_plane_boot.py`), stack-down degrade,
    second-boot refusal, and the singularity gate live in
    `tests/unit/test_query_plane_boot.py` (`test_stack_down_raises_library_face_only`,
    `test_second_boot_invocation_is_refused`, `test_real_duckdb_server_launches_from_the_one_site`)
    + `tests/unit/singularity/test_one_duckdb_server_launch_site.py`; the parity gate,
    including a seeded-divergence-fails case, live in
    `tests/unit/query_plane/test_face_parity.py::test_happy_path_rows_agree_row_for_row_including_empty_result`
    + `test_seeded_divergence_fails_and_names_the_divergent_query`
    + `test_face_down_reports_not_applicable_never_a_silent_pass`; 25 tests green (2026-09-11).
- **CAP-6** *(added 2026-08-27 — bound by the `query-plane-catalog` operator ruling, 2026-08-26)*
  - **intent:** The composed semantic stores the grounded dashboard pages bind to (DW-D2-2's
    `semantic_packages` family, plus the `core_feedstock_health` Parquet the 2026-08-26 first
    visual pass found absent in a fresh checkout) are derived by the NAMED downstream plane
    pipeline — the opt-in optimization layer: the closed seven pipelines stay sealed and keep
    producing the canonical datasets untouched; consumers choose per call (canonical datasets
    direct, or the plane as the fast path); no silent `01_raw` tree.
  - **success:** A single `kedro run --pipeline <named>` materializes the composed stores from
    the sealed seven's outputs with zero diff inside the seven; `dashboard/data.py`'s
    "BSL-wired SHELL pages" banner retires; the grounded pages render rows (not
    honestly-empty shells) in a fresh checkout after that one pipeline run; DW-D2-2 closes
    citing this capability's story.
  - **verified:** the named `semantic_packages` pipeline (`pipelines/semantic_packages/nodes.py`,
    docstring cites "Story 20.3, CAP-6" directly) reads only the sealed seven's own catalog
    dataset names — never a raw source — live in
    `tests/unit/test_semantic_packages_pipeline.py::test_pipeline_reads_only_sealed_seven_output_names_never_a_raw_source`;
    honest-NULL degrade for not-yet-migrated metrics (never a crash) live in
    `test_composed_store_lets_the_deferred_bsl_metrics_degrade_honestly_not_crash`;
    12 tests green across the pipeline + node suites (2026-09-11). A fresh-checkout
    end-to-end `kedro run` producing real (non-empty) rows was not independently
    re-executed in this pass — verified at the node/pipeline-contract level only.
- **CAP-7** *(added 2026-08-27 — adopts the DW-D2-1/DW-D2-3 residue into this spec's chain)*
  - **intent:** The deferred Vizro page inventory completes: the CIS two-spine specs
    (`DESIGN.md` + `EXPERIENCE.md`, the DW-D2-1 precondition — still not produced as of
    2026-08-27) are produced first, then the remaining 19 of 28 CLI pages port against them,
    BSL-routed, reading canonical datasets or the plane per CAP-6's per-call choice. The
    DW-D2-3 residual rides along: the §2.1 semantic-HTML/ARIA browser-agent navigation check
    and a data-present visual pass through the now-existing serve entrypoint
    (`scripts/dashboard_serve.py`, evidence-update 2026-08-26).
  - **success:** Both spine files exist under `planning-artifacts/` covering every unshipped
    page; all 28 pages render with stable ids/titles; the ARIA navigation check and a
    data-present visual pass via `pixi run -e local-recipes dashboard-serve` are recorded;
    Vizro stays outside the Canopy host and Django imports no Vizro; the page set is NOT
    expanded past the live-confirmed core before the spine specs land.
  - **verified:** both spine files exist
    (`planning-artifacts/{DESIGN.md,EXPERIENCE.md}`); `pixi run -e local-recipes dashboard-dryrun`
    green (72 tests, 2026-09-11) — builds the full page inventory with stable ids/titles AND
    runs the real-server Playwright e2e + §2.1 semantic-HTML/ARIA navigation check
    (`tests/integration/dashboard/test_dashboard_e2e.py`). Page count has grown past this
    CAP's original 28 to **34** (Story 21.9 CAP-5 added pages after this Spec's success
    criterion was written — pixi task description confirms "Full 34-page inventory shipped");
    the intent (spine-gated, all-pages-render, ARIA-checked) holds, the literal "28" is stale
    and superseded upward, not a shortfall.

## Constraints

- **Always:** query `cf_atlas.db` directly — no second data layer, no parallel query surface, no
  new metric computation. This visualizes what atlas already computes.
- **Always:** no SPA framework (React/Vue or kin) — server-rendered / WebSocket-driven only,
  matching every existing dashboard surface in this repo.
- **Always:** mode ordering is risk ordering — the static-fragment mode (CAP-1) is the base
  layer; WebSocket interactivity (CAP-2) layers on top of it and never replaces it.
- **Always:** host-agnostic — nothing in the view catalog, registry, or renderers binds to a
  specific ASGI host, and nothing presupposes DW-H3/Wagtail existing.
- **Always** *(2026-08-27, per the `query-plane-catalog` ruling 2026-08-26)*: the query plane
  is an OPT-IN optimization layer, never a second source of truth — the first constraint
  above ("query `cf_atlas.db` directly — no second data layer") is amended exactly this far:
  a view may take the plane as the fast path, chosen per call, while the sealed seven keep
  producing the canonical datasets untouched. No silent `01_raw`; reopening the seven stays
  declined.
- **Always** *(2026-08-27, per the `query-plane-face` ruling 2026-08-26)*: both plane faces
  behind ONE pixi-sourced boot script — in-process library by default (AD-16 local-first),
  Mosaic `duckdb-server` HTTP/Arrow raised only when the platform stack is up; parity between
  the faces is part of done. DuckDB stays a query face, never a fourth backing store.

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
  *(Amended 2026-08-27, operator reconcile:* the module fence stands — no rework of the
  shipped Vizro architecture — but COMPLETING D2's deferred inventory is now tracked on this
  spec's chain as CAP-7 / Stories 20.4–20.5, because the DW-D2-1/2/3 residue had ledger
  entries and no story home for dispatch. Vizro stays Lane 3 / outside the Canopy host, per
  the epics file's Canopy obligation 3.)*

## Success signal

Today, handing someone the answer to "which feedstocks are stale?" means running
`staleness-report` and pasting text. After this ships: every view in the curated catalog renders
from the live `cf_atlas.db` as a linkable static HTML fragment (CAP-1); at least one view is
live-interactive over Bokeh's WebSocket protocol on the chosen ASGI host (CAP-2); a new widget
type lands as a registry entry without touching view definitions (CAP-3); and the air-gapped
render profile emits pages with zero external CDN URLs (CAP-4).

**Extended 2026-08-27 (CAP-5..CAP-7):** one boot script raises both plane faces with a green
parity gate between them (CAP-5); one named-pipeline run materializes the composed dashboard
stores in a fresh checkout with zero diff inside the sealed seven (CAP-6); and the CIS
two-spine specs exist, all 28 Vizro pages render against them, and the §2.1 ARIA + data-present
visual passes are recorded (CAP-7) — closing DW-D2-1, DW-D2-2, and DW-D2-3 with citations.

## Open Questions

- ~~"Which widget types actually matter for atlas's query shapes (grid vs chart vs pivot, per
  view) — the registry's seed set is a decomposition-time survey of the 11 mirrored CLIs, not
  the source dream's Tabulator/Perspective/PGWalker catalog."~~ — **answered at decomposition,
  Story 14.2 (done):** the seed set was derived from the survey of the 11 mirrored CLIs' query
  shapes, per its AC; not the source dream's catalog.
- ~~"Session bridging if these views are ever hosted against Steward's dashboard surface —
  Steward has its own, narrower identity-at-the-boundary model; bridging is a decision made then,
  never assumed here."~~ — **CLOSED 2026-09-09** (batch § 2.1 row atlas-B2): it dies with the
  module. C1 retires `views/`, so no route exists to mount behind an authenticated host, and the
  estate already forbids the shape —
  `src/platform/tests/test_host_board_row_isolation.py:26`
  (`_SECOND_STACK_TOP = frozenset({'vizro','dash'})`, AST-asserted across all nine host/portal
  roots).
- ~~"ASGI host choice — the contract is 'any ASGI host'; which one actually mounts the Bokeh
  WebSocket protocol is picked at decomposition time (explicitly NOT contingent on
  DW-H3/Wagtail)."~~ — **answered at decomposition, Story 14.3 (done):** the host was chosen in
  that story's spec; swapping it touches mounting code only, per its AC.
- ~~*(added 2026-08-27)* "The CIS two-spine specs (`DESIGN.md` + `EXPERIENCE.md`, DW-D2-1) —
  checked 2026-08-27: still not produced …"~~ — **STALE; CLOSED 2026-09-09** (readiness finding
  D-3): the two spine specs DO exist (`planning-artifacts/DESIGN.md`,
  `planning-artifacts/EXPERIENCE.md`), Stories 20.4 and 20.5 both read `done`, and DW-D2-1 reads
  `status: closed`. The "still not produced" text was never reconciled after delivery.

**No open questions remain on this Spec.**

## Decomposition & coverage record — 2026-08-27

**Coverage map (why status moved `ready` → `in-progress`, not `shipped`).** The original
contract (CAP-1..CAP-4) is fully decomposed AND shipped as **Epic 14** on this station's own
chain — the `ready` status was stale:

| Capability | Story (epics.md) | Tracked-ledger key | Status |
|---|---|---|---|
| CAP-1 static view catalog | Story 14.1 | `14-1-static-view-catalog` | done |
| CAP-2 Bokeh WebSocket interactivity | Story 14.3 | `14-3-bokeh-websocket-interactivity` | done |
| CAP-3 pluggable widget registry | Story 14.2 | `14-2-pluggable-widget-registry` | done |
| CAP-4 air-gap asset rewriting | Story 14.4 | `14-4-air-gap-asset-rewriting` | done |

The spec is not `shipped` because the three operator rulings dated **2026-08-26** (steward
`spec-pyforge-unifying-strategy/SPEC.md` § Open Questions) extended this spec's design space,
decomposed here as CAP-5..CAP-7 → **Epic 20** (Stories 20.1–20.5) — *reconciled 2026-09-09: all
five now read `done`; the "all `backlog`" text was the same missed post-delivery reconcile as the
DW-D2-1 open question below.*

**How the three rulings bind:**

1. **`query-plane-face` — "both, one boot script."** Binds CAP-5. The in-process library face
   is default (AD-16 local-first); the Mosaic `duckdb-server` HTTP/Arrow face is committed now
   behind the SAME single pixi-sourced boot script, raised only when the platform stack is up;
   parity between the faces is part of the face's definition of done; filesystem-less
   consumers bind to the HTTP face per CAP-19's success wording. → Stories 20.1 (boot script)
   and 20.2 (parity gate). Not covered by the shipped steward slice: 34.1–34.5 built attach /
   cache pipeline / vectors / DSN gate / scribe driver — none of them the boot script or the
   parity gate.
2. **`query-plane-catalog` — "named new pipeline, opt-in optimization layer."** Binds CAP-6
   and amends this spec's "no second data layer" constraint exactly that far: the sealed
   seven stay sealed and canonical; the named downstream pipeline derives the plane's Parquet
   cache; consumers choose per call; no silent `01_raw`. → Story 20.3 derives the composed
   DASHBOARD stores (DW-D2-2 + the fresh-checkout `core_feedstock_health` gap) through that
   pattern. Steward 34.2 shipped the named pipeline for the estate OLTP cache; the
   atlas-canonical composed stores the grounded pages need remain unmaterialized — that
   residue is what 20.3 owns.
3. **`query-plane-scribe-cutover` — "dual-write for now."** No atlas story owed: covered by
   steward Story 34.5 (`34-5-scribe-semantic-recall-uses-the-plane`, done) with `scribe_schema`
   pgvector staying the dual-written safety net. It binds this spec only as shared-plane
   context — the plane the views may read is also scribe's primary store; retirement of the
   pgvector write is a later, explicit decision on the steward chain.

**Steward-chain fence (no double-mint).** The CAP-19 engine's first slice — steward Stories
34.1–34.5 plus Lane 3 36.1–36.2 — shipped 2026-08-26 ON THE STEWARD CHAIN even though the code
lands on this station's surface; this station's epics file (validation note, 2026-08-26)
deliberately does not re-mint them, and the strategy SPEC forbids re-dispatching its epics.
Epic 20 owns only the atlas-side query-surface residue enumerated above.

**Deferred-work cross-references (atlas `deferred-work-ledger.md`):**

- **DW-D2-1** (CIS two-spine gating the full 28-page inventory) — **CLOSED** (*reconciled
  2026-09-09*): Story 20.4 produced `planning-artifacts/DESIGN.md` and
  `planning-artifacts/EXPERIENCE.md`, Story 20.5 landed against them, and the ledger entry reads
  `status: closed`. The "checked 2026-08-27: still blocking" text was stale.
- **DW-D2-2** (BSL-wired shell pages awaiting composed-store materialization) — Story 20.3
  materializes the stores through the named plane pipeline; the entry closes citing it.
- **DW-D2-3** (visual verification of the rendered UI) — its 2026-08-26 evidence-update
  removed both blockers (serve entrypoint `scripts/dashboard_serve.py` exists; first visual
  pass ran: `factory-status` fully live, root `feedstock-health` honestly-empty pending
  pipeline outputs). The residual (§2.1 semantic-HTML/ARIA check + a data-present visual
  pass) is folded into Story 20.5's ACs; the data-present precondition is Story 20.3.

## Retirement of the second Lane-3 runtime — 2026-09-09

**Decision (operator, `fleet-readiness-decision-batch-2026-09-09.md` § 2.3 C1 / row atlas-B1):
RETIRE.** `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/` and `tests/unit/views/`
are deleted. Epic 14 shipped CAP-1..CAP-4 as a second Lane-3 runtime that nothing reaches, and its
`cli_bridge` dynamic-import bridge reads the legacy SQLite store while its own docstring records
that the DuckDB-singularity gate "stays green even though the loaded script itself imports
`sqlite3`" — a declared evasion of CAP-19 and of `spec-pyforge-atlas`'s own Non-goal. The rejected
alternative was to mount it (`pyforge atlas views serve`) under a recorded exemption, which would
institutionalise a second engine against a Never.

- **Effect story:** atlas **Story 25.1**, "Retire the second Lane-3 runtime", under a NEW
  **Epic 25** (batch § 2.3 C6 — effect stories live on the owning station's epics). Epic 14 is
  closed 4/4 `done`, so a 14.5 would reopen a completed epic; Epic 25 is the first free number
  (Epic 11 never existed by design). Steward Epic 49 carries only the index row.
- **Owner Dream:** `docs/dreams/atlas-query-dashboards.md` moves `specified → archived` with
  `archived-reason: retired` — the README-sanctioned reason already used by
  `docs/dreams/artifact-console.md` for a runtime that was built and stood down.
- **Cross-station obligation (steward):** the matching `docs/dreams/README.md` row/status is owed,
  or `dreams-hygiene` emits `readme-table-drift` for this slug. The Unifying Dream's Kinships line
  (`:669`) asserting this as "a second, shipped Lane-3 runtime" is false under the realization gate
  and is replaced with the retirement.
- **What survives:** CAP-5 (one boot script, both plane faces), CAP-6 (the named composed-store
  pipeline) and CAP-7 (the 28-page Vizro inventory) are the live contract; this Spec stays
  `in-progress` until Story 25.1 lands.
