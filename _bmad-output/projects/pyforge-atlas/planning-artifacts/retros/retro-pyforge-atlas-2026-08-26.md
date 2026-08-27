---
doc_type: retrospective
project: pyforge-atlas
title: Station retro — post-migration growth window (2026-08-02 → 2026-08-26)
date: 2026-08-26
updated: "2026-08-26"
scope: everything landed in src/shared/packages/pyforge-atlas since the last retro
  (epic-10 wave-I retro + SYNTHESIS.md, both 2026-08-02) — Epics 12-19 plus the
  canopy CAP-19 first slice
basis: "git log --oneline --since=2026-08-02 -- src/shared/packages/pyforge-atlas;
  planning-artifacts/specs/ (spec-kedro-org-tooling-adoption, spec-upstream-discovery,
  spec-atlas-query-dashboards, spec-artifactory-download-intelligence,
  spec-wagtail-corporate-brain, spec-conda-forge-packaging-inventory-operations,
  spec-10..19 story specs); research/technical-*-2026-08-08.md (both);
  _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/
  (SPEC.md, stack.md, convergence.md); implementation-readiness-report-2026-08-10.md;
  sprint-status-ledger.yaml (tracked twin, read-only)"
---

# Retro — pyforge-atlas, 2026-08-02 → 2026-08-26

The 2026-08-02 retros closed the migration era (Epics 1–10, "code newer than
retro" cleared for the first time). This retro closes the same gap for the
post-migration growth window: eight epics of new capability, two research
reports that re-grounded the roadmap, and the station's conscription into the
estate strategy. Written as part of the 2026-08-26 chain-currency sweep; the
`code→retro` finding it clears fired at code motion dated 2026-08-24.

## What shipped (evidence-based, from the merge log)

- **Epic 12 — Kedro-org tooling (12.1–12.3, done).** kedro-skills guidance
  audited against the AD-invariants *before* being trusted (`eea873d3e5` — the
  audit report lives beside the Spec), CI publishing the **real** kedro-viz DAG
  through `steward deploy dashboard` (`8dc004dbc0`, closing the stub-mirror /
  real-DAG split the 08-08 research flagged), and a recorded vscode-kedro defer
  verdict. Both Path-B choices matched the 08-08 research's recommendation over
  the dormant `publish-kedro-viz` Action.
- **Epic 13 — upstream discovery (13.1–13.5, done; bmad-loop run
  `20260809-184330`).** Trending ingest → tier classification →
  `trending-candidates` operator surface → fixed-source org-audit track →
  structured Mason handoff. First live proof of the migration's founding promise
  ("add a signal by writing a node"): the fetcher is injected at the seam per
  AD-1, and the new `upstream_discovery` pipeline joined as a governed addition
  rather than a breach of the sealed seven. This also discharged the trendshift
  Track A supersession and absorbed microsoft-org-sweep (Spec archived) into the
  FR-67 track.
- **Epic 14 — query dashboards (14.1–14.4, done; runs `20260813-094919`,
  `20260815-112701`).** Panel/Bokeh hand-someone-a-link views over `cf_atlas.db`:
  static view catalog for 6 zero-arg CLIs (`06c982c837`), a pluggable widget-type
  registry (`01027a26ec` + a review pass fixing magic-number/dispatch-key gaps),
  Bokeh WebSocket interactivity (`4bc5370124` + a typed-io_loop/regression review
  pass), air-gap asset rewriting. Review passes caught real defects both times —
  the two-pass discipline held.
- **Epic 15 — Artifactory download intelligence (15.1–15.3, done; run
  `20260815-112701`).** Mock-first AQL adapter (injectable), PyPI/conda identity
  join + internal/private flag, Kedro pipeline surfacing as
  `artifactory_downloads`. Live-instance bring-up deliberately outside the Spec.
- **Epic 16 — Wagtail corporate brain, narrow DW-H3 contract (16.1–16.2, done).**
  Instance deploy definition and a fully-offline httpx bring-up rehearsal inside
  the default `kedro-test` gate (no new pytest marker needed — a loopback stdlib
  `http.server` stub). Two process events worth recording: 16.2's revised work
  sat **uncommitted in a stale run worktree** and was rescued and ruff-cleaned at
  landing (`caf8b96f9f`, `ec75feb31c`); and a **duplicate Epic 16 numbering** was
  resolved by `bmad-correct-course` (`c388980450`). Both recovered losslessly;
  both were avoidable.
- **Epic 17 — packaging-inventory intake engine (17.1–17.2 ledger-done; the Spec
  stays `in-progress`).** 17.1 chartered the quartet's governed spec surface —
  resolving parselmouth fold placement (2026-08-22) into the atlas
  mapping-manager/name-resolver chain — and 17.2 made the handoffs
  execution-ready (`02dc009881`), including a verify-repair pass reconciling a
  **foreign pyforge-marshal spec-surface drift** (`707bebec13`) instead of
  stamping past it. The attended, credentialed live-execution verification is the
  epic's open boundary event.
- **Epic 18 — CAP-18 hooks (18.1, done).** Audit-not-rebuild: existing Kedro
  hooks mapped onto the shared `pyforge-core` registration contract
  (`c587dfd1fd`, `cap18.py`). No second plugin API; no atlas PR-gate verdict
  beside Warden.
- **Epic 19 — skill, persona, portal (19.1–19.2, done).** The SKF domain skill
  (`.claude/skills/pyforge-atlas/`, v0.1.0) + `bmad-agent-atlas` persona
  (`494acc5651`), and one real inventory row rendering on `/stations/atlas/` via
  PortalClient only (`02dc6d656c`).
- **Canopy CAP-19 first slice (steward stories 34.1–34.5 + Lane 3 36.1–36.2,
  landed 2026-08-26 in this package's surface).** Read-only fixture-Postgres
  attach (`07af364976`), the named `query_plane_cache` pipeline writing the
  estate Parquet cache (`82e2be4b58`), vectors persisted on the plane via
  `vss`/HNSW (`ef3e216fd3`), Scribe semantic recall ranked on the plane
  (`2d264c7f5c`), Lane 3 BSL over the estate cache (`7839a0ac26`) and a grounded
  Vizro page (`232f385f0a`). Steward-side: the atlas MCP face on the host ASGI
  (`1d8204696c`) and refusal of a second writer on `atlas.duckdb`
  (`1c2da72fd4`).
- **Hygiene that made the above trustworthy:** the 2026-08-10 Phase-2 audit
  corrected false Status lines through the Tier-3+sync path
  (`implementation-readiness-report-2026-08-10.md`, `28551a6b65`), and 63
  completed story specs were promoted out of Tier-3 scratch into tracked
  `planning-artifacts/specs/` (`538c7b5652`) — the post-warden-incident
  convention working as designed.

## What held

- **The AD-invariants survived eight epics of growth untouched.** No inline IO
  entered a node body; every new fetcher (trending, AQL, La Suite) is an
  injected callable; the sealed seven pipelines were never written into from a
  new chain; gates were never weakened (16.2's rehearsal moved *into* the
  default gate rather than behind a marker).
- **Audit-before-adopt beat adopt-on-sight twice** — kedro-skills (a week-zero,
  1-star tool at evaluation time) and vscode-kedro both closed as recorded
  decisions rather than installs, exactly as the 08-08 research recommended.
- **Owner ≠ mechanism worked in both directions:** Atlas owns the DAG-publish
  outcome, Steward owns `deploy dashboard`; Atlas owns the query-plane engine,
  Steward owns the through-line and the host faces.
- **The review layer kept earning its cost:** documented catches in 14.2, 14.3,
  and 17.2's verify-repair; the 16.2 rescue proves the safety-net path
  (preserve, restore-patch, ruff-clean at landing) over from-scratch re-drive.

## What changed course

- **`vizro-ai` is deprecated** (canopy Lane 3 ruling). The shipped
  `query_vizro_ai` NL surface is legacy-era delivery; new boards go
  Vizro-over-BSL-over-the-plane with `vizro-mcp`/`vizro-e2e-flow`. `DW-D3-1`
  (live LLM backend) is no longer worth resolving on the deprecated library.
- **"Seven fixed pipelines" evolved to "closed seven + governed additions"** —
  AD-3 amended 2026-08-26 rather than left contradicting ten as-built pipeline
  packages.
- **The Unity / Wasm satellites are formally not-revived** (unifying-strategy
  non-goal). They stay archived planning records inside this station's
  consolidated Spec/PRD/brief.
- **`lane1-serves-dw-h3` answered no (2026-08-25):** host Wagtail `/cms/` does
  not satisfy the La Suite Docs REST contract, so DW-H3 stays Atlas's own
  attended bring-up. The estate may run two CMS faces.

## Strategy convergence

The 2026-08-08 cross-station research argued the unifiable asset is not the
Kedro/Dagster/DuckDB stack but **Atlas as the fleet's single data platform** —
stations consume Atlas datasets and tools; nobody stands up a sibling Kedro
deployment. The pyforge-unifying-strategy chain (2026-08-24/26) ratified exactly
that as canopy AD-21 (**one Kedro home**) and then gave the position teeth:
Atlas owns the **CAP-19 HTAP query plane** (one engine, one writer on
`atlas.duckdb`; live attach + Parquet cache + vectors; both faces — in-process
library and the Mosaic `duckdb-server` HTTP face — behind one boot script),
supplies **Lane 3** analytics through BSL, and participates in the estate as a
full five-tier station (CLI · portal · service · skill · persona — the 40/40
roster of canopy 37.1 includes the Epic 19 deliverables). Convergence to note
honestly: the estate integration shipped **ahead of** the station's own
retirement chain — the new plane serves estate reads while the legacy
orchestrator still serves the factory's daily intelligence reads. That ordering
is defensible (demand was on the estate side) but it widens the two-eras window
Cluster A was already holding open.

## Open items (carried, verified against the ledger and research — not new)

1. **Cluster A — the retirement chain** (`DW-B4-3` fixture recapture →
   `DW-B4-1` credentialed parity → `DW-B4-2` sign-off/retirement). Still the
   single highest-leverage attended afternoon available; still without a forcing
   function. Its integration rider is now on the record: re-back
   `conda_forge_server.py`'s atlas tools with Kedro/DuckDB reads (path (a)) or
   retirement breaks Doctor — **that story still has no owner.**
2. **Cluster B — Dagster bring-up** (`DW-C1-1`; sensors `default_status=STOPPED`;
   injected fetchers default None). The migrated pipeline still cannot produce
   fresh data end-to-end unattended, by design, until this attended event.
3. **Phase-P cost-gate routing** (`DW-B2-4`/`DW-B4-4`) — a safety item, to land
   before any credentialed Phase-P run.
4. **Cluster D quick wins** — staleness-marker consumer wiring (`DW-B5-4`, the
   AD-13 "silent pass" contract), `coerce_cvss_score` on the node path,
   `conda_license`/`upstream_version` production. Unattended-fixable now.
5. **Epic 17's attended live-execution verification** (Spec `in-progress`).
6. **`DW-H3`/`DW-H1`** — the attended La Suite production bring-up
   (PostgreSQL/MinIO requirement intact).
7. **`DW-F1-1`** — the F1 cold/warm benchmark (threshold fixed in the story spec
   before it runs).
8. **Scribe dual-write retirement** — plane-primary shipped; `scribe_schema`
   pgvector stays the safety net until the plane has operating history (operator
   ruling 2026-08-26); retirement is its own future decision.
9. **`DW-D2-1`/`DW-D2-2`** — the 28-CLI page inventory and the composed
   `semantic_packages` store stay demand-driven ("feeds > pages" still governs).
