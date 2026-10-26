---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/addendum.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md
  - docs/specs/cfe-atlas-datapipeline-kedro-migration.md (v5.6 — §§ 2.5, 9, 10, 11, 14 binding)
project: pyforge-atlas
status: final
created: 2026-07-17
updated: "2026-10-25"   # RE-STAMPED 2026-10-25 (later; the 2026-10-25 atlas retro's candidate fixes): Story 33.2 added to done Epic 33 (a fix under CAP-9 and AD-3, no CAP, no flag: the spine counts twelve pipelines, the MCP face names its eight as MCP-triggerable) and Story 34.13 added to done Epic 34 (a fix under CAP-64, no CAP, no flag: atlas declares brotli, closes DW-atlas-34-5-1; operator ruling "brotli + brotli-python (Recommended)"); keys 33-2 and 34-13 added (backlog), epic-33 and epic-34 reopened by them (doctor Story 41.5); no other epic or story moved. Earlier 2026-10-25: RE-STAMPED 2026-10-25 (the PRD's FR arrows were counted, not traced): Epic 39 / Story 39.1 added (a chore under spec-one-chain-per-station CAP-5 and CAP-3, no CAP, no flag; operator rulings 2026-10-25 "Approve as proposed (Recommended)", "Drop the arrow (Recommended)", "Append a correction (Recommended)", and "CAP-4, CAP-5, CAP-15" for FR-6 after review): 23 atlas PRD FR arrows the 2026-09-17 fold had counted are re-mapped to the Spec capabilities that realize them, and FR-15, FR-61 and FR-63 wait on a source-capability decision (DW-atlas-39-1); keys 39-1 (backlog), epic-39 (backlog) and epic-39-retrospective (optional) added; arch->epics cascade for the spine's re-stamp of the same date; no other epic or story moved. Prior "2026-10-24"   # RE-STAMPED 2026-10-24 (latest): Story 37.12 added to done Epic 37 (a fix under CAP-63 / CAP-64, no CAP, no flag): the Pages Vizro job keeps the public stores' last-good copies between runs (actions/cache over data/raw, data/stores/* except the vdb store, and the vulnerability snapshot history the cve-watcher diffs); key 37-12 added (done; epic-37 back to done). Prior "2026-10-24"   # RE-STAMPED 2026-10-24 (later): Story 34.12 added to done Epic 34 (a fix under CAP-64, no CAP, no flag): a vulnerability feed that cannot be reached keeps its last good copy under the AD-13 marker; key 34-12 added (done; epic-34 back to done); closes DW-atlas-38-1-1. Prior "2026-10-24"   # RE-STAMPED 2026-10-24: Epic 38 / Story 38.1 minted (CAP-69; no CAP; the existing flag pyforge.atlas.board_projections for the version-downloads path): semantic_packages reads its upload times and archived flag, version-downloads its upload dates; keys epic-38 (backlog), epic-38-retrospective (optional) and 38-1 added; owns DW-atlas-37-6-2 and DW-atlas-37-7-2. Prior "2026-10-23"   # RE-STAMPED 2026-10-23 (later): Story 37.6 done (CAP-69; no CAP; the existing flag pyforge.atlas.board_projections): legacy release-cadence's counts from per-version upload times streamed out of every subdir's full repodata.json.zst (operator ruling 2026-10-23); closes DW-atlas-37-6-1, opens DW-atlas-37-6-2. Prior "2026-10-23"   # RE-STAMPED 2026-10-23 (later): Story 37.7 done (CAP-69; no CAP; the existing flag pyforge.atlas.board_projections): legacy find-alternative's top 10 candidates for every archived package on the channel, from the summary and keywords the cf-graph anchor rows now carry; closes DW-atlas-37-7-1, opens DW-atlas-37-7-2 and DW-atlas-37-7-3. Prior "2026-10-23"   # RE-STAMPED 2026-10-23 (later): Story 37.8 done (CAP-69; no CAP; the existing flag pyforge.atlas.board_projections): legacy export-purls' six artifacts and their manifest; closes DW-atlas-37-8-1. Prior "2026-10-23"   # RE-STAMPED 2026-10-23 (later): Story 37.10 done (CAP-69; no CAP; the existing flag pyforge.atlas.board_projections): a new catalog_index pipeline, run after each build, reports every catalog entry's last write, row count, tier and status; closes DW-atlas-37-10-1. Prior "2026-10-23"   # RE-STAMPED 2026-10-23: Story 37.9 done (CAP-69; no CAP; the existing flag pyforge.atlas.board_projections): the mapping-gap classifies the unmapped packages as legacy mapping_gap does, read-only; closes DW-atlas-37-9-1. Prior "2026-10-23"   # RE-STAMPED 2026-10-23: Story 37.5 done (CAP-69; no CAP; the existing flag pyforge.atlas.board_projections): the cve-watcher reads a diff of two vulnerability snapshots; closes DW-atlas-37-5-1. Prior "2026-10-22"   # RE-STAMPED 2026-10-22 (later): Story 37.11 added to Epic 37 (a fix under CAP-63 / CAP-69, no CAP, no flag): a board's note reads "Data gap" only where data is missing. Prior "2026-10-22"   # RE-STAMPED 2026-10-22: arch->epics cascade for FR-71 amended in place (CAP-63, operator ruling 2026-10-21: the identity boards show their public-derived rows on Pages); Story 37.2's Then and Surface lines amended in place; no story added, renumbered or removed, no ledger key moved. Prior: RE-STAMPED 2026-10-19: Epic 37 / Stories 37.1-37.10 minted (spec-pyforge-atlas CAP-63 amended, CAP-69; FR-71, FR-77); see § Currency reconciliation — 2026-10-19. Prior: RE-STAMPED 2026-10-18 (later): Epics 34-36 / Stories 34.1-34.9 (+34.10, minted with Story 34.2), 35.1-35.4, 36.1-36.3 minted (spec-pyforge-atlas CAP-64..CAP-68, FR-72..FR-76; atlas fills its own data, Dream entry 2026-10-18): 16 story keys (backlog), epic-34..36 (backlog) and their retrospective keys (optional) added; no other key moved. Earlier: RE-STAMPED 2026-10-18: Epic 33 / Story 33.1 minted (fix under spec-pyforge-atlas CAP-9, no CAP, no flag; the atlas CLI reaches the verbs its contracts name, from any directory; Dream entry 2026-10-18): keys epic-33, epic-33-retrospective and 33-1 added; no other key moved. Prior: RE-STAMPED 2026-10-15: Story 30.2's text amended in place to CAP-63 as amended 2026-10-15 (the task under [feature.pyforge-atlas.tasks], run in -e pyforge-atlas; the exact-file VENDORED_ROOTS entry for the vendored plotly.min.js); no story added, renumbered or removed, no ledger key moved. Prior: RE-STAMPED 2026-10-14: Epic 31 / Story 31.1 minted (fix under spec-pyforge-atlas CAP-20, no CAP, no flag; closes DW-atlas-steward-100-7-1: atlas passes mypy in pyforge-foundry-full, and the existing mypy task runs there in the lint-types CI job and in pr-preflight; Dream entry 2026-10-14; renumbered from 30.1 after the Pages chain took Epic 30). Prior: RE-STAMPED 2026-10-14: Epic 30 / Stories 30.1-30.2 minted (features under spec-pyforge-atlas CAP-62 and CAP-63, FR-70 and FR-71, AD-21 amended; flags pyforge.atlas.viz_export_artifact and pyforge.atlas.vizro_static_boards) from the operator ruling of 2026-10-13 (the DAG export reaches Pages as an artifact; Dream entry of that date): keys 30-1 and 30-2 (backlog), epic-30 (backlog) and epic-30-retrospective (optional) added; no other key moved. See § Currency reconciliation — 2026-10-14. Prior: RE-STAMPED 2026-10-13: Epic 29 / Story 29.1 minted (fix under spec-pyforge-atlas CAP-16, no CAP, no flag; the range-test recorder race, Dream entry 2026-10-13). Prior: RE-STAMPED 2026-10-11: Epic 28 / Story 28.1 minted (fix under spec-pyforge-atlas CAP-6, no CAP, no flag; the live-attach fixture socket path, Dream entry 2026-10-11). Prior: RE-STAMPED 2026-10-10: arch->epics cascade after the spine's 2026-10-10 re-stamp (Story 25.1's gate cleared, its key flipped blocked -> backlog by operator ruling); no epic or story added or changed; § Currency reconciliation — 2026-10-10 appended. Prior: RE-STAMPED 2026-10-04: Story 27.5 added to done Epic 27 (fix, no CAP, no flag; DW-atlas-27-3-1); epic-27 reopens to in-progress (operator ruling 2026-10-04; doctor Story 41.5). Prior 2026-10-03   # RE-STAMPED 2026-10-03 (Phase 4+5): Epic 27 / Stories 27.1-27.4 minted from the operator's Phase 4+5 ruling (fix, no CAP, no flag; 96 open medium and low deferrals). Prior: RE-STAMPED 2026-10-03: arch->epics cascade for marshal Story 66.2's deferred-work backfill; no epic or story minted. Prior 2026-09-29   # RE-STAMPED 2026-09-29: Epic 26 / Story 26.1 minted (spec-one-chain-per-station CAP-11 relay; no atlas CAP or FR). Prior 2026-09-28   # RE-STAMPED 2026-09-28: Epic 25 / Stories 25.1-25.2 minted (spec-pyforge-atlas CAP-61, FR-69); Story 24.4's stale pre-rekey "Story 25.2" citations corrected to 24.2; § Currency reconciliation — 2026-09-28 appended. Prior 2026-09-20 (fleet consistency pass).
currency_review: "Reviewed 2026-09-06 (Epic 24 added: spec-bmad-suite-lifecycle atlas relay — mcp-builder for the MCP face, Story 24.1). Reviewed 2026-08-10 (Phase 2 audit) — false Status lines corrected to done, rollup keys fixed via Tier-3+sync; see planning-artifacts/implementation-readiness-report-2026-08-10.md. Prior review 2026-08-02. Validated 2026-08-26 against the re-cut architecture spine — no heading or status changed; see the dated validation note at end of file. 2026-08-27: Epic 20 appended (spec-atlas-query-dashboards CAP-5..7 reconcile against the 2026-08-26 query-plane rulings); no existing heading or status changed."
generatedBy: bmad-create-epics-and-stories (unattended Tier-2 stage 3)
# The single canonical story source for this station: every `### Story` heading
# here maps 1:1 to a sprint-status-ledger.yaml story key. Exactly one per station (marshal:AD-72).
epics_role: canonical
---

## Fold provenance (2026-09-17)

Station Spec spec-pyforge-atlas reminted absorbed capabilities as CAP-1..CAP-60. This heading is the INV-A citation window for the folded set: spec-pyforge-atlas CAP-1 CAP-2 CAP-3 CAP-4 CAP-5 CAP-6 CAP-7 CAP-8 CAP-9 CAP-10 CAP-11 CAP-12 CAP-13 CAP-14 CAP-15 CAP-16 CAP-17 CAP-18 CAP-19 CAP-20 CAP-21 CAP-22 CAP-23 CAP-24 CAP-25 CAP-26 CAP-27 CAP-28 CAP-29 CAP-30 CAP-31 CAP-32 CAP-33 CAP-34 CAP-35 CAP-36 CAP-37 CAP-38 CAP-39 CAP-40 CAP-41 CAP-42 CAP-43 CAP-44 CAP-45 CAP-46 CAP-47 CAP-48 CAP-49 CAP-50 CAP-51 CAP-52 CAP-53 CAP-54 CAP-55 CAP-56 CAP-57 CAP-58 CAP-59 CAP-60.



# cf_atlas Kedro/Dagster/DuckDB Migration - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for the cf_atlas
Kedro/Dagster/DuckDB migration, decomposing the PRD (FR-1..FR-22) and the
Architecture Spine (AD-1..AD-23) into implementable stories.

**Frozen contract:** the story IDs and wave structure of spec § 9
(`docs/specs/cfe-atlas-datapipeline-kedro-migration.md` v5.6) are preserved
verbatim — 32 stories, Waves 0 + A–H, IDs `0.1`, `A1–A3`, `B1–B10`, `C1–C2`,
`D1–D3`, `E1–E2`, `F1–F4`, `G1–G3`, `H1–H4`. **The spec ID is each story's
primary key**; the `Epic.Story` number shown in parentheses is an epic-local
alias only. No story was renumbered, split, merged, added, or dropped. Where
this document compresses an acceptance criterion, the spec § 9 wording remains
the binding authority.

Each story carries: its spec § 9 ACs (restated as Given/When/Then), the FRs it
implements, the architecture invariants (AD-x) that bind it, its § 2.5
execution mode, its gating open question (with the § 11 default), its verify
gate, and its dependency edges (§ 14 ordering).

**Execution-mode legend** (spec § 2.5):
- **ATTENDED** — scheduled wave-boundary event with human present.
- **DEV-AUTO** — `bmad-dev-auto` (the retired 6.x name of `bmad-build-auto`) inline single-story implementation.
- **LOOP-S** — bmad-loop, per-story-spec-approval gate.
- **LOOP-E** — bmad-loop, per-epic approval gate.

## Requirements Inventory

### Functional Requirements

FR numbering is the spec's, preserved exactly (PRD § 4 carries the full contract text).

FR-1: Declarative data access via the Kedro Data Catalog; per-host credential scoping; all 20 `resolve_*_urls` override points survive.
FR-2: The 23 cataloged phases refactored into modular, DAG-resolved pipelines (seven § 5.2 domain pipelines); Phase I becomes an explicit node; § 3.3 per-phase engineering contracts bind the ports.
FR-3: `IncrementalParquetDataset` preserves TTL gating with per-dataset TTLs (never a global constant).
FR-4: `phase_state` removed; resumability via Kedro runner + persisted Parquet.
FR-5: DuckDB replaces SQLite and all fragmented compute proposals (compute + graph CTEs + `vss` vector, one engine).
FR-6: Dagster orchestrates schedules + retries via `kedro-dagster`; per-node timeouts; three bootstrap profiles as job configs; sensors (Wave G).
FR-7: MCP surface preserved, authored over Kedro session/catalog APIs; `kedro-mcp` never load-bearing.
FR-8: Boring Semantic Layer over the catalog (Ibis → DuckDB) — the single translation interface.
FR-9: Read surface migrates from 28 CLIs to Vizro / Vizro-AI pages + `query_vizro_ai` MCP tool; three named CLI-first exceptions surface latest-report artifacts.
FR-10: Data-quality contracts halt bad data (pandera-first; GX version-capped 1.18.2 behind a validator-agnostic hook).
FR-11: A2A interface for inter-agent collaboration (cf_atlas analytical agent ↔ conda-forge-expert authoring agent).
FR-12: Lineage + observability via OpenLineage + OpenTelemetry, down to named API calls.
FR-13: Universal SBOM ingestion normalized to CycloneDX; `cfe:*` namespace + `?channel=conda-forge` qualifier never stripped.
FR-14: WASM portability — Vizro-AI + BSL in-browser via duckdb-wasm/Pyodide over statically-hosted Parquet (HTTP Range, zero backend).
FR-15: Pixi-first, nebi-scaffolded, conda-forge-only toolchain; Python 3.14 floor; lean env for loop worktrees.
FR-16: Dependency-hygiene scan node (deptry); source-less inputs report `not-applicable`, never failure.
FR-17: Transitive resolution + the ~856k-component universe BOM extend the SBOM intake; 14-day freshness contract; six-bucket matching semantics preserved.
FR-18: Unified CI policy gate — four-axis `ComplianceReport`, frozen exit-code convention (0/1/2, full enum {0,1,2,130}); `inventory-match` enum flip with one-release `INVENTORY_MATCH_LEGACY_EXIT=1` window.
FR-19: Conda-native vulnerability source Basilisk (querybatch + bounded detail fetch); name-based matching; tri-state `fix_available`; offline-skip hedge.
FR-20: Release-to-availability velocity signal (`release_lag_hours` + `release_lag_qualifies`); 90-day recency gate; first-availability computation.
FR-21: Migration-readiness source — conda-forge-bot-data status datasets, per-migration partitioning (zero code change for new migrations); four-way readiness split; `not-in-tracker` labeled inferred.
FR-22: AI Software Factory layer — (a) Karpathy wiki scaffold + 5 personas, (b) agno crews, (c) La Suite/Wagtail REST sync, (d) Dagster-triggered crews.

### NonFunctional Requirements

Extracted from PRD §§ 4–7/11 and the Architecture Spine (the PRD has no
freestanding NFR section; these are the binding cross-cutting qualities).

NFR-1: All verify gates are fixture-based, non-credentialed, run `--frozen`, and live in the tracked test tree — never `.claude/data/` (AD-11).
NFR-2: Credentials scope per destination host; a non-JFrog host never receives `X-JFrog-Art-Api`; credentialed runs are attended-only (AD-2, AD-11).
NFR-3: Offline/air-gapped degradation is skip-and-mark-stale, never fail; last-good dataset kept intact; consumer profile fully offline (AD-13).
NFR-4: Performance honesty — incremental re-materialization is the headline claim; cold-start is benchmarked, never promised (AC-7, SM-3, SM-C1).
NFR-5: Conda-forge-only, pixi-managed, Python 3.14 floor; no JVM/standalone binaries; GX capped at 1.18.2 (no ≥1.19 features); `llms-full-check` green after any dependency change (AD-16, AD-9).
NFR-6: One frozen exit-code convention everywhere a CLI/gate exits: 0 pass / 1 policy-fail / 2 error, full enum {0, 1, 2, 130}; `indeterminate` → 1 (AD-12).
NFR-7: Every node emits OpenLineage events and participates in end-to-end OTel traces resolving to named API calls (AD-20).
NFR-8: Dashboard pages meet the spec § 2.1 agent-legibility bar — semantic HTML, ARIA attributes, deterministic layouts (FR-9).
NFR-9: Timeouts and retry budgets are per-node; the 1800 s coarse-cap silent-phase-drop class is structurally impossible (AD-6).
NFR-10: Pipeline snapshots are advisory, never authoritative for the authoring loop; payloads feeding authoring decisions carry their build timestamp (AD-17).
NFR-11: Operator-workstation envelope — ~3 GB storage budget (vdb 2.5 GB dominant); the runtime Parquet store is fully rebuildable (Spine deployment envelope).
NFR-12: Loop execution is sequential (`max_parallel = 1`); gates are never weakened, removed, or demoted from attended to unattended to raise the autonomy share (SM-C2, AD-11).

### Additional Requirements

From the Architecture Spine (binding on story implementation):

- **Starter template:** the project is scaffolded by `nebi` (Kedro project + own lean pixi env) — Story A1 is the scaffold story; physical naming resolved 2026-07-17 (sprint-change-proposal, warden alignment): workspace member `src/shared/packages/pyforge-atlas/`, namespace package `pyforge.atlas`; Parquet-store detail stays A1-owned.
- AD-1 import-direction meta-test (no Dagster/`kedro-mcp` imports in `pipelines/`, `datasets/`, `hooks/`, `mcp/`) ships with `kedro-catalog-check` (A2).
- The Consistency Conventions table binds all stories: seven snake_case pipeline packages; `# legacy: Phase <ID>` provenance comments; `<domain>_<entity>` dataset names with layer tags; canonical join keys (`conda_name` / `pypi_name` / `(conda_name, advisory_id)`; purls never internal join keys); timestamps normalized to epoch seconds at ingest; additive-first schema evolution; degradation vocabulary `stale` / `unresolved` / `not-applicable` never interchanged; `conf/base` tracked vs `conf/local` gitignored; explicit env/run-config beats profile defaults.
- Execution seam (AD-18): loop stories run in worktrees only after the symlink bootstrap; all BMAD writes resolve through the `_bmad-output` symlinks; switching only via `scripts/bmad-switch pyforge-atlas`; keystone stories B1/B2/F1 get pre-flight budget raises; REVIEW sessions constrained to correctness-affecting findings; PR-per-wave wraps local squash-merge; the effort closes with the CFE Rule-2 retro.
- Wave-0 preconditions: one-time hooks approval; live `bmad-groundtruth` re-check (intake was git-surface-only); worktree symlink bootstrap (validated by A3); heaviest-story budget review.
- Wave-B verify assets are TEA `atdd`-generated red-phase fixtures (§ 14 per-wave operating loop).
- Deferred decisions with owners (Spine § Deferred) resolve inside the named story specs: A1 physical naming, E1 A2A transport, F3 embedding model + offline `vss` provisioning, F1 benchmark threshold, H1 MinIO server provisioning, D2 CIS two-spine design specs.
- Conditional surface: if trendshift Track A ships Phase T before Wave B completes, Phase T joins the migration surface — re-check with live groundtruth at execution start (PRD § 6.1).
- Per CLAUDE.md Rule 1, any story touching recipe code or atlas tooling invokes `conda-forge-expert`; Rule 2 retro at effort closeout.

### UX Design Requirements

No bmad-ux design contract exists for this project (verified:
`{planning_artifacts}/ux-designs/` absent). The spec supplies its own
frontend precondition, carried as a story-level requirement rather than
UX-DRs: **frontend work in Waves D/G (D2, D3, G1) is preceded by the CIS
two-spine specs (`DESIGN.md` + `EXPERIENCE.md`, spec § 2.4)**, and all pages
meet the § 2.1 agent-legibility bar (NFR-8). D2 page inventory/design detail
is deferred to those specs (Spine Deferred).

### FR Coverage Map

| FR | Epic (Wave) | Stories |
|---|---|---|
| FR-1 | Epic 2 (A) | A2 |
| FR-2 | Epic 3 (B) | B1, B2, B5, B6 |
| FR-3 | Epic 2 (A) | A3 |
| FR-4 | Epic 2 (A) + Epic 3 (B) | A3, B4 |
| FR-5 | Epic 7 (F) | F1, F3 |
| FR-6 | Epic 3 (B) + Epic 4 (C) + Epic 8 (G) + Epic 9 (H) | B5, C1, C2, G3, H4 |
| FR-7 | Epic 3 (B) | B3 |
| FR-8 | Epic 5 (D) | D1 |
| FR-9 | Epic 5 (D) | D2, D3 |
| FR-10 | Epic 7 (F) | F2, F4 |
| FR-11 | Epic 6 (E) | E1 |
| FR-12 | Epic 6 (E) | E2 |
| FR-13 | Epic 3 (B) | B7 |
| FR-14 | Epic 8 (G) | G1, G2 |
| FR-15 | Epic 2 (A) | A1 |
| FR-16 | Epic 7 (F) | F4 |
| FR-17 | Epic 3 (B) | B7 |
| FR-18 | Epic 7 (F) | F4 |
| FR-19 | Epic 3 (B) | B8 |
| FR-20 | Epic 3 (B) | B9 |
| FR-21 | Epic 3 (B) | B10 |
| FR-22 | Epic 9 (H) | H1 (a), H2 (b), H3 (c), H4 (d) |

Story 0.1 is a Wave-0 enabler (no FR — execution scaffolding per spec § 2.4).
All 22 FRs are covered; no FR is uncovered; no story is unmapped.

## Epic List

Epics map 1:1 to the spec § 9 waves (frozen structure — the wave is the
delivery boundary, each wave ends standalone-valuable with its own gate and
PR; consolidation or re-slicing was deliberately not applied).

### Epic 1: Wave 0 — Legacy Translation via Skill Forge (1 story: 0.1)
Developer agents get a hallucination-free, queryable model of the legacy orchestrator before any port begins.
**FRs covered:** none (execution enabler).

### Epic 2: Wave A — `nebi` Scaffold & Catalog (3 stories: A1, A2, A3)
The operator and loop agents get a scaffolded, pixi-provisioned Kedro project with a declared Data Catalog and TTL-preserving incremental dataset class — the harness every later wave builds on.
**FRs covered:** FR-1, FR-3, FR-4 (partial — primitive), FR-15.

### Epic 3: Wave B — Pipeline Node Porting & MCP Integration (10 stories: B1–B10)
All 23 legacy phases run as DAG-resolved Kedro nodes with proven output parity; agents trigger pipelines and read datasets via MCP; three new signal sources land as additive riders.
**FRs covered:** FR-2, FR-4 (retirement), FR-6 (partial — refresh assets), FR-7, FR-13, FR-17, FR-19, FR-20, FR-21.

### Epic 4: Wave C — Orchestration & Visualization (2 stories: C1, C2)
The operator watches scheduled, retried, per-node-timed runs in the Dagster UI and inspects lineage via `pixi run viz` instead of tailing stdout.
**FRs covered:** FR-6 (core).

### Epic 5: Wave D — Semantic Layer & Dashboards (3 stories: D1, D2, D3)
The live-confirmed consumer CLIs are answerable from BSL-driven Vizro pages (8 dashboard pages + factory-status ship in v1; full 28-CLI inventory deferred, `DW-D2-1`) plus a natural-language field callable from Claude Code.
**FRs covered:** FR-8, FR-9.

### Epic 6: Wave E — A2A Integration, Lineage & Observability (2 stories: E1, E2)
Agents exchange structured payloads over a single A2A channel; every node, run, and query is lineage-tracked and traceable end-to-end.
**FRs covered:** FR-11, FR-12.

### Epic 7: Wave F — The DuckDB Singularity (4 stories: F1, F2, F3, F4)
DuckDB is the only engine (compute/graph/vector); contracts halt bad data; the four-axis policy gate holds the frozen exit-code contract for CI.
**FRs covered:** FR-5, FR-10, FR-16, FR-18.

### Epic 8: Wave G — WebAssembly Portability & Event-Driven Sensors (3 stories: G1, G2, G3)
The intelligence surface runs in-browser with zero backend against statically-hosted Parquet; sensors enable near-real-time ingestion.
**FRs covered:** FR-14, FR-6 (sensors).

### Epic 9: Wave H — The AI Software Factory & Karpathy Wiki (4 stories: H1, H2, H3, H4)
The knowledge-base factory layer compiles, lints, and publishes the wiki autonomously, triggered by Dagster, consuming (never writing) atlas data.
**FRs covered:** FR-22, FR-6 (crew triggers).

### Epic 10: Post-Audit Remediation — Round-3 Findings (6 stories: I0–I5)
The independent Round-3 spec-to-code audit's verified atlas findings are closed at
their source, so the shipped claims and the code agree. Added post-ship (2026-07-27)
by `sprint-change-proposal-2026-07-27.md`; unlike Epics 1–9 it maps to no spec § 9
wave, because it exists to repair what those waves left divergent.
**FRs covered:** none new — the epic re-establishes FR-4, FR-13 and FR-21 claims that
drifted from their implementations.

**Epic dependency chain:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 (each wave
depends on the prior wave's deliverables — spec § 9 preamble). Within-epic
ordering is § 14's: B1/B2 → B3 → B4 → B5 → B6 → B7 → B8 → B9 → B10; B8/B9/B10
are additive, not parity-gated; legacy retirement only after B4 proves parity
per Q1. **Epic 10 sits outside that chain** — it depends on the whole migration
having shipped, and its stories are ordered by the verify gate rather than by
wave (I3 first: `kedro-test` is red on main until it lands, so every later story
would inherit a failing gate).

---

## Epic 1: Wave 0 — Legacy Translation via Skill Forge (SKF)

Convert the legacy orchestrator into queryable, provenance-grade context so
Wave-B ports are grounded in fact, not model memory.

### Story 1.1: Generate legacy contextual skill

- **Delivered 2026-07-17 — PR #69.** Full record: `specs/spec-1-1-generate-legacy-contextual-skill.md`.

As a Wave-B developer agent,
I want the legacy `conda_forge_atlas.py` orchestrator converted into an `agentskills.io`-compliant skill via Skill Forge,
So that I can query hallucination-free legacy provenance while porting phases.

**Acceptance Criteria:** (spec § 9 Story 0.1, binding)

**Given** the legacy orchestrator source at intake HEAD
**When** the SKF module runs
**Then** it outputs a structured skill repository modeling the legacy logic
**And** developer agents can query this skill for hallucination-free provenance during Wave B
**And** this is a Wave-0 enabler: no FR — the skill artifact is execution scaffolding per spec § 2.4, not product surface.

- **FRs:** none (enabler).
- **Invariants:** AD-10 (the legacy behavioral contracts this skill must model faithfully), AD-18 (Wave-0 preconditions execute alongside: hooks approval, live `bmad-groundtruth` re-check, symlink bootstrap, budget review).
- **Mode:** ATTENDED (Wave 0 is attended per § 2.5 / PRD § 6.1).
- **Gating question:** none.
- **Verify gate:** none exists yet (pre-harness); acceptance is the queryable skill artifact itself.
- **Depends on:** nothing (first story of the effort).

---

## Epic 2: Wave A — `nebi` Scaffold & Catalog

Build the harness: scaffold, catalog, incremental dataset class — and the
first two verify gates the loop needs before it may run anything.

### Story 2.1: Scaffold the Kedro + pixi project via `nebi`

- **Delivered 2026-07-17 — PR #70.** Full record: `specs/spec-2-1-scaffold-the-kedro-pixi-project-via-nebi.md`.

As the operator,
I want the Kedro project structure and pixi wiring initialized by `nebi` with its own lean env and `kedro-test` gate,
So that every later story lands in a provisioned, verifiable, worktree-affordable project.

**Acceptance Criteria:** (spec § 9 Story A1, binding)

**Given** the FR-15 stack already resolved in the `local-recipes` env
**When** `nebi` scaffolds the project
**Then** a Kedro project skeleton exists, scaffolded by `nebi`
**And** the FR-15 stack resolves at its pins on Python 3.14 (all conda-forge, no standalone binaries / JVM) and `pixi run` activates cleanly
**And** `pixi run -e local-recipes llms-full-check` passes after any dependency change (library catalog updated in the same PR)
**And** air-gapped provisioning is documented for both routing layers (`.pixi/config.toml [pypi-config]` and the `_http.py` overrides)
**And** the scaffolded project ships its own lean pixi env (loop worktrees never materialize the fat `local-recipes` env) and the `kedro-test` verify task — Wave A's deterministic gate — including the import smoke for py3.14-unclassified glue (e.g. `kedro_dagster`, AD-16)
**And** *(correct-course 2026-07-17)* the scaffold root is `src/shared/packages/pyforge-atlas/` — a pixi build workspace member mirroring `pyforge-warden` (hatchling; dual conda + wheel/sdist artifacts; dedicated `[feature.pyforge-atlas]` env + `pyforge-atlas-build-conda`/`-build-dist` tasks)
**And** *(correct-course 2026-07-17)* the Python package is the `pyforge.atlas` namespace package (`src/pyforge/atlas/`, imports `pyforge.atlas.*` beside `pyforge.warden.*`); `kedro-test`'s import smoke covers the Kedro-project-in-namespace-package seam, with flat `pyforge_atlas` as the recorded fallback if nebi/Kedro tooling rejects the dotted form
**And** *(correct-course 2026-07-17)* `pyforge-warden` is wired as the optional extra `pyforge-atlas[gate]` — the only cross-package code dependency (ComplianceReport schema/validators, consumed at F4); installed in the atlas env by default; no reverse warden→atlas import exists (both tools stay independently installable).

- **FRs:** FR-15.
- **Invariants:** AD-16, AD-11 (gate is a named story deliverable), AD-18, Packaging & namespace convention (warden-aligned — Spine Deferred slot RESOLVED 2026-07-17).
- **Mode:** DEV-AUTO (harness-building, § 2.5).
- **Gating question:** none.
- **Verify gate:** **builds `kedro-test`**.
- **Depends on:** 0.1.

### Story 2.2: Define the Data Catalog for all sources + outputs

- **Delivered 2026-07-17 — PR #71.** Full record: `specs/spec-2-2-define-the-data-catalog-for-all-sources-outputs.md`.

As a pipeline node author,
I want every API source and Parquet output declared as a Kedro dataset in `conf/base/catalog.yml`,
So that no data-access logic ever lives in node functions and credentials scope per host.

**Acceptance Criteria:** (spec § 9 Story A2, binding)

**Given** the legacy `_http.py` / `init_schema()` data-access surface
**When** the catalog is authored
**Then** all current data access is represented declaratively in `catalog.yml`
**And** no data-access logic remains inline in (future) node functions
**And** a `kedro-catalog-check` verify task exists (catalog resolves, no inline IO) — a § 2.5 loop gate — shipping the AD-1 import-direction meta-test
**And** credentials attach per destination host only (a non-JFrog host never receives `X-JFrog-Art-Api`) and all 20 `resolve_*_urls` override points survive as dataset-level endpoint config (FR-1 consequences).

- **FRs:** FR-1.
- **Invariants:** AD-2, AD-1 (meta-test), AD-13 (endpoint override convention).
- **Mode:** DEV-AUTO (harness-building, § 2.5).
- **Gating question:** none.
- **Verify gate:** **builds `kedro-catalog-check`**.
- **Depends on:** A1.

### Story 2.3: Implement `IncrementalParquetDataset` for TTL gating

- **Delivered 2026-07-17 — PR #72.** Full record: `specs/spec-2-3-implement-incrementalparquetdataset-for-ttl-gating.md`.

As a pipeline node author,
I want the `*_fetched_at` TTL incremental logic encapsulated in one reusable dataset class with per-dataset TTLs,
So that no node ever re-implements checkpoint/TTL/backoff and resumability is Kedro-native.

**Acceptance Criteria:** (spec § 9 Story A3, binding)

**Given** the catalog from A2
**When** `IncrementalParquetDataset` is implemented
**Then** it exists and round-trips TTL state
**And** a unit test proves stale rows are re-fetched and fresh rows are skipped
**And** TTLs are declared per dataset in the catalog (Phase D 7 d, Phase P 30 d, EPSS 1 d, CWE 90 d, …) — never a global constant (FR-3).

- **FRs:** FR-3, FR-4 (the dataset class is the resumability primitive).
- **Invariants:** AD-5, AD-18 (this story validates the worktree symlink bootstrap and measures worktree env-materialization cost), AD-11.
- **Mode:** LOOP-S — **the designated first loop-driven story and worktree smoke** (§ 2.5 preconditions).
- **Gating question:** none.
- **Verify gate:** `kedro-test` (unit suite; also proves the loop-in-worktree seam before Wave B commits to loop execution).
- **Depends on:** A1, A2.

---

## Epic 3: Wave B — Pipeline Node Porting & MCP Integration

Port every phase, prove parity, expose the MCP surface, land the three new
signals. Wave-B verify assets are TEA `atdd` red-phase fixtures; the
`parity-diff` harness is built incrementally through B1–B3 and consumed at the
attended B4 event. B8/B9/B10 are additive, never parity-gated.

### Story 3.1: Port the conda-side backbone phases into Kedro nodes

- **Delivered 2026-07-17 — PR #73.** Full record: `specs/spec-3-1-port-the-conda-side-backbone-phases-into-kedro-nodes.md`.

As a BMAD execution agent,
I want the conda-forge enumeration + graph-building + VCS/health phases (B, B.5, B.6, E, E.5, F, J, K, L, M, N) as pure Kedro nodes in the Core and VCS & Health pipelines,
So that the conda-side backbone resolves from the DAG with its legacy behavioral contracts intact.

**Acceptance Criteria:** (spec § 9 Story B1, binding)

**Given** the § 3.3 phase registry and the Wave-A catalog
**When** the conda-side phases are ported
**Then** each phase is a pure-function node with explicit inputs/outputs and the DAG resolves automatically (no procedural call order)
**And** Phase B.5's `_pick_feedstock` dedicated-feedstock attribution survives the port with its unit tests carried over as node tests
**And** Phase I (per-version download history) becomes an explicit node with declared outputs — no longer an unregistered side-effect of Phase F
**And** the § 3.3 engineering contracts are fixture-tested in the node suite: Phase K's single-worker 3 RPS token bucket (`PHASE_K_AGGRESSIVE` opt-out) and Phase F's provenance discipline (`downloads_source` semantics, s3-only breakdown tables, DELETE-by-scope-key writes, calendar-month `downloads_30d`)
**And** the Phase E port reconciles — or explicitly documents — the maintainer-universe delta (~44 feedstocks) vs cf-graph discovery
**And** Phase B.6 ports with its lite semantics (presence-in-repodata → `latest_status`); full yanked detection stays an optional follow-on, not this story.

- **FRs:** FR-2.
- **Invariants:** AD-3, AD-10, AD-4 (Parquet canonical from Wave A), AD-5 (no node-local checkpointing), AD-13.
- **Mode:** LOOP-S. **Keystone story — pre-flight budget raise (AD-18).**
- **Gating question:** none.
- **Verify gate:** `kedro-test` + begins building **`parity-diff`** (B1–B3 build, B4 consumes).
- **Depends on:** A1–A3 (catalog + dataset class + gates).

### Story 3.2: Port the PyPI & Vulnerability pipelines

- **Delivered 2026-07-17 — PR #75.** Full record: `specs/spec-3-2-port-the-pypi-vulnerability-pipelines.md`.

As a BMAD execution agent,
I want the PyPI intelligence phases (C, C.5, D, H, O–S incl. the shared single-write-path helpers) and vulnerability phases (G / G') ported into their domain pipelines,
So that PyPI and vulnerability intelligence run as unit-testable DAG nodes with all shipped guards intact.

**Acceptance Criteria:** (spec § 9 Story B2, binding)

**Given** the § 5.2 pipeline decomposition
**When** the PyPI + vulnerability phases are ported
**Then** the PyPI Intelligence and Vulnerability pipelines exist per § 5.2 and each node unit-tests on `pandas.DataFrame` IO
**And** the `add-handoff` single-write-path property and the `v_pypi_intelligence_valid` / `v_current_version_vulns` view contracts are preserved
**And** the vulnerability read-path contract is preserved: the atlas `cisa_kev` KEV overlay and the `_coerce_cvss_score` ScoreType unwrap survive in the migrated read surface
**And** Phase P ports with its two-layer cost gate intact (dry-run preflight + `maximum_bytes_billed` + job timeout, `_PARTITIONDATE` literal bounds), stays opt-in/admin-only, and `test_no_thirty_gb_lie.py` carries over
**And** Phase H's serial gate ports without re-including the pypi-only denominator; EPSS percentiles stay normalized 0–100; `pypi_intelligence.notes` operator overrides survive Phase S re-runs.

- **FRs:** FR-2.
- **Invariants:** AD-3, AD-10, AD-6 (Phase P admin-opt-in, never a default schedule), AD-5, AD-13.
- **Mode:** LOOP-S. **Keystone story — pre-flight budget raise (AD-18).**
- **Gating question:** none.
- **Verify gate:** `kedro-test` + `parity-diff` (building).
- **Depends on:** B1 (Core pipeline datasets).

### Story 3.3: Re-expose the data surface as Kedro-API-native MCP tools

- **Delivered 2026-07-17 — PR #76.** Full record: `specs/spec-3-3-re-expose-the-data-surface-as-kedro-api-native-mcp-tools.md`.

As a CFE authoring agent,
I want the 23 atlas-relevant MCP tools re-authored over Kedro session/catalog APIs with pipeline triggers and dataset reads,
So that I can trigger named pipelines and read datasets via MCP with no load-bearing plugin dependency.

**Acceptance Criteria:** (spec § 9 Story B3, binding)

**Given** the 46 existing MCP tools (23 atlas-relevant) in `conda_forge_server.py`
**When** the audit + re-authoring completes
**Then** BMAD agents can trigger a named pipeline (e.g. `run_vulnerability_pipeline`) via MCP
**And** BMAD agents can read a resulting dataset natively via MCP
**And** `kedro-mcp` is not a load-bearing dependency of the trigger/read surface — the surface works with it absent
**And** non-atlas recipe-authoring tools stay on the legacy FastMCP server; `library-futures` / `add-handoff` stay CLI-only
**And** MCP tool bodies carry no metric/business logic (dataset passthrough + triggers only, AD-7); triggered runs ride the same Kedro job machinery (AD-23).

- **FRs:** FR-7.
- **Invariants:** AD-7, AD-23, AD-17 (payloads advisory + timestamped), AD-1.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` + `parity-diff` (build completes at B3).
- **Depends on:** B1, B2 (datasets to expose).

### Story 3.4: Verify dataset parity against the legacy orchestrator

- **Delivered 2026-07-18 — PR #77.** Full record: `specs/spec-3-4-verify-dataset-parity-against-the-legacy-orchestrator.md`.

As the operator,
I want the Kedro pipeline run in parallel with legacy `bootstrap-data` and proven output-equivalent,
So that the legacy orchestrator (and `phase_state`) can be retired on recorded evidence, not hope.

**Acceptance Criteria:** (spec § 9 Story B4, binding)

**Given** the `parity-diff` harness built through B1–B3
**When** the full credentialed parity run executes as an attended wave-boundary event
**Then** the parity check compares Kedro Parquet outputs against legacy `cf_atlas.db` tables and reports zero material drift per Q1's default (exact row-count + value parity on the `v_actionable_packages`-family views; timestamp/ordering-only diffs documented benign)
**And** the harness itself is a fixture-based, loop-callable `parity-diff` pixi task
**And** parity evidence is recorded with human sign-off; only then is the legacy orchestrator marked for retirement
**And** B4 compares legacy-surface outputs only — B8/B9/B10 signals are out of parity scope (AD-14).

- **FRs:** FR-4 (the `phase_state` table retires with the legacy orchestrator), whole-migration AC-1.
- **Invariants:** AD-19 (retirement gate + abort ramp bounding sunk cost at Waves 0–B), AD-11 (attended event, credentialed run attended-only), AD-4.
- **Mode:** ATTENDED (parity boundary event — one of the five § 2.5 attended events).
- **Gating question:** **Q1** (parity tolerance) — § 11 default adopted: exact row-count + value parity on actionable views, benign-diff documentation. Comparison granularity beyond the Q1 views resolves in the B4 evidence record (Spine Deferred).
- **Verify gate:** **consumes `parity-diff`** (fixture mode in-loop; credentialed full run at the event).
- **Depends on:** B1, B2, B3.

### Story 3.5: Port the external-refresh assets (§ 3.4)

- **Delivered 2026-07-18 — PR #78.** Full record: `specs/spec-3-5-port-the-external-refresh-assets-3-4.md`.

As the operator,
I want `vdb-refresh`, `update-cve-db`, and `update-mapping-cache` wrapped as scheduled external-refresh assets in their domain pipelines,
So that the three separately-built stores refresh with retries and observability across all three bootstrap profiles.

**Acceptance Criteria:** (spec § 9 Story B5, binding)

**Given** the three § 3.4 separately-built local stores and the legacy tasks' TTLs
**When** the refresh assets are ported
**Then** each refresh runs as a Dagster-scheduled asset with retries + observability, cadence matching the legacy TTLs
**And** Phases G / G' and `scan-project` offline mode consume the refreshed stores exactly as before — the pipeline never writes them outside the refresh assets
**And** the vuln-db environment dependency is a declared resource requirement, not an implicit shell-out
**And** Q6's decision is recorded **before** porting `update-mapping-cache` (consolidation may retire it instead); `g10_spelling` provenance + no-clobber survive regardless
**And** the consumer profile keeps working air-gapped.

- **FRs:** FR-2, FR-6.
- **Invariants:** AD-6, AD-13, AD-10 (mapping contract), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** **Q6** (mapping-source consolidation) — § 11 default adopted: consolidate on migrated Phase C (DuckDB), re-point `name_resolver.py`/`recipe-generator.py`; keep the flat-cache refresh only if authoring-time reads prove to need a standalone file. Must be recorded before this story's mapping asset work.
- **Verify gate:** `kedro-test` (+ `dagster-dryrun` once C1 exists; schedule assertions land as fixtures here).
- **Depends on:** B4 sequence position per § 14 (runs after parity; needs B1/B2 pipelines; Q6 drained first).

### Story 3.6: Port the Seed-Gaps pipeline

- **Delivered 2026-07-18 — PR #79.** Full record: `specs/spec-3-6-port-the-seed-gaps-pipeline.md`.

As the operator,
I want the four report-only gap suggesters as terminal report nodes of the Seed-Gaps pipeline,
So that seed-freshness reports regenerate after every rebuild without ever mutating the curated seeds.

**Acceptance Criteria:** (spec § 9 Story B6, binding)

**Given** the external seed datasets and the § 3.4 Seed-freshness report nodes table
**When** `lts-registry-gap`, `cwe-seed-gap`, `spdx-schema-gap`, `license-map-gap` are ported
**Then** each suggester is a report node reading exactly the inputs in that table, emitting a `derived`-layer freshness report
**And** the nodes are strictly read-only — the byte-identical-seed guarantee survives as a pipeline test
**And** the pipeline re-runs after every rebuild, alongside the § 5.2 item 7 derived artifacts
**And** `mapping-gap` stays in the PyPI Intelligence pipeline with its `g10_spelling` no-clobber writeback — it is not a Seed-Gaps node.

- **FRs:** FR-2.
- **Invariants:** AD-15, AD-3, AD-10.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (byte-identical-seed fixture + report-node fixtures).
- **Depends on:** B1, B2 (upstream datasets); § 14 position after B5.

### Story 3.7: Extend the Universal SBOM intake (resolver, formats, universe BOM, buckets)

- **Delivered 2026-07-18 — PR #80.** Full record: `specs/spec-3-7-extend-the-universal-sbom-intake-resolver-formats-universe-bom-buckets.md`.

As a CI consumer,
I want the transitive-resolver node, the widened tiered manifest intake, the universe-BOM catalog dataset, and the matching node with shipped bucket semantics,
So that any manifest normalizes to CycloneDX and matches against the full conda-forge universe.

**Acceptance Criteria:** (spec § 9 Story B7, binding)

**Given** the § 4.10 tiered intake formats
**When** the SBOM pipeline is extended
**Then** a bare `requirements.txt` resolves to a full transitive dependency set with resolution depth + fan-out recorded (offline: `unresolved` marker, AD-13)
**And** every § 4.10 format normalizes to CycloneDX preserving the `cfe:*` property namespace and the `?channel=conda-forge` qualifier
**And** the full-universe CycloneDX BOM is a catalog dataset under the 14-day freshness contract; consumers refuse a stale atlas exactly as the legacy gate does
**And** a matching run reproduces the legacy six-bucket classification (ADD / ADD-NONPYPI / UPDATE-FEEDSTOCK / UPDATE-PIN / CURRENT / UNKNOWN) on a fixture inventory
**And** NBSP-padded pasted `conda list` / `pip list` text parses identically to its ASCII-space form (fixture).

- **FRs:** FR-13, FR-17.
- **Invariants:** AD-10 (`cfe:*` + qualifier never stripped), AD-12 (B7 produces security inputs, never assembles reports), AD-15, AD-13, AD-3.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (format fixtures, six-bucket fixture, NBSP fixture).
- **Depends on:** B1, B2; § 14 position after B6.

### Story 3.8: Basilisk conda-native vulnerability ingestion

- **Delivered 2026-07-18 — PR #81.** Full record: `specs/spec-3-8-basilisk-conda-native-vulnerability-ingestion.md`.

As a CFE authoring agent,
I want the two Basilisk ingestion nodes in the Vulnerability pipeline with the tri-state `fix_available` join,
So that conda-native advisories reach the read surface without conflating version currency with security currency.

**Acceptance Criteria:** (spec § 9 Story B8, binding)

**Given** Q7's landing decision recorded before implementation
**When** the ingestion nodes land
**Then** a batch run over the full Python population writes `basilisk_vulns` (`conda_name`, `advisory_id`, `modified`) via `POST /v1/querybatch` at ≤1,000 queries per request (plus the bounded `GET /v1/vulns/{id}` detail fetch under standard rate-limit discipline)
**And** matching is by package name: a fixture proves an advisory whose `affected[]` ecosystem tag reads `PyPI` still matches its conda package
**And** `fix_available` is tri-state: a fixture advisory carrying only an enumerated `versions` list yields `unknown`, never `false`
**And** no read surface conflates version currency with security currency — a package can be `current` per `behind-upstream` AND carry a Basilisk advisory (fixture-proven)
**And** `BASILISK_BASE_URL` routes the endpoint per the mirror-routing convention; offline (consumer profile) the nodes skip gracefully and mark the dataset stale rather than failing.

- **FRs:** FR-19.
- **Invariants:** AD-13 (offline-skip + last-good + staleness marker), AD-14 (additive rider, fixture-enforced guards, not parity-gated), AD-2 (one new override point: `resolve_basilisk_urls`), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** **Q7** (Basilisk landing point) — § 11 default adopted: build once as Kedro nodes in Wave B; a legacy Phase U pulls forward only if trendshift's timeline leaves a pre-migration window that matters. Recorded before implementation.
- **Verify gate:** `kedro-test` (the three binding-constraint fixtures + offline-skip fixture).
- **Depends on:** B2 (Vulnerability pipeline exists); NOT gated on B4 parity.

### Story 3.9: Release-to-availability velocity columns

- **Delivered 2026-07-18 — PR #82.** Full record: `specs/spec-3-9-release-to-availability-velocity-columns.md`.

As the operator,
I want `release_lag_hours` + `release_lag_qualifies` derived on the Phase H join with the 90-day recency gate,
So that packaging velocity is measurable without the false "47% behind" failure mode.

**Acceptance Criteria:** (spec § 9 Story B9, binding)

**Given** Phase H's retained per-release `upload_time_iso_8601`
**When** the column pair is derived
**Then** it exists on the Phase H join dataset with no new external fetch introduced
**And** the rebuild-cadence guard is fixture-enforced: a version-unchanged package whose upstream release is >90 days old is excluded (`release_lag_qualifies = false`)
**And** lag is computed against first availability of the matched version (minimum per-build repodata `timestamp`), fixture-enforced: a second build of the same version inside the window does not shift `release_lag_hours`
**And** a population run reproduces the live baseline shape (median ≈ 9 h, ~72% within 24 h) within reasonable drift, recorded as a calibration reference (not a hard gate); the two coincident 83.7% measurements re-verify against the § 15 evidence gists.

- **FRs:** FR-20.
- **Invariants:** AD-14 (never `latest_conda_upload`; not parity-gated), AD-3 (lives in `vcs_health`), timestamp convention (epoch seconds at ingest — repodata ms converted at the dataset boundary).
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (both failure-mode fixtures).
- **Depends on:** B2 (Phase H dataset); NOT gated on B4 parity.

### Story 3.10: Migration-readiness datasets + classification node

- **Delivered 2026-07-18 — PR #83.** Full record: `specs/spec-3-10-migration-readiness-datasets-classification-node.md`.

As the operator,
I want conda-forge-bot-data `status/` category lists and per-migration detail ingested with a readiness-classification node,
So that migration readiness (e.g. python314) is a queryable four-way split with blocker labels and volume ranking.

**Acceptance Criteria:** (spec § 9 Story B10, binding)

**Given** the `status/` category lists and `migration_json/<name>.json` detail
**When** the datasets + classification node land
**Then** the category-list datasets enumerate active migrations and drive per-migration partitioning — a new migration upstream requires zero code change
**And** for a live migration the classification node produces the four-way readiness split (noarch / rebuild-done / confirmed-pending / not-in-tracker) with the per-feedstock blocker buckets (`in-pr`, `awaiting-pr`, `awaiting-parents`, `not-solvable`, `bot-error`)
**And** the `not-in-tracker` bucket is labeled as inferred, never confirmed tracker status (fixture-proven in the report output)
**And** the downloads join yields a top-unmigrated-by-volume ranking
**And** all fetches route through the existing `resolve_github_raw_urls` (no new override helper); offline the nodes skip gracefully and mark the datasets stale (`version_status.v2.json` excluded).

- **FRs:** FR-21.
- **Invariants:** AD-13, AD-14 (not parity-gated), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (zero-code-change partitioning fixture + inferred-label fixture).
- **Depends on:** B1 (feedstock set + `conda_noarch`), B2 (downloads join); NOT gated on B4 parity.

---

## Epic 4: Wave C — Orchestration & Visualization

Move scheduling and retries off cron+bash; make execution observable.
**Wave gate:** Q2 (Dagster footprint + acquisition health) re-verified at wave
start — § 11 default adopted: on-demand/scheduled local invocation, no
persistent daemon unless Wave-G sensors force it; switch to an exit ramp only
on concrete deterioration.

### Story 4.1: Integrate `kedro-dagster` for scheduling + execution

- **Delivered 2026-07-18 — PR #84.** Full record: `specs/spec-4-1-integrate-kedro-dagster-for-scheduling-execution.md`.

As the operator,
I want the Kedro DAG compiled into a Dagster repository with schedules, retries, profiles, and per-node timeouts,
So that I watch runs in the Dagster UI and the 1800 s silent-phase-drop defect is structurally retired.

**Acceptance Criteria:** (spec § 9 Story C1, binding)

**Given** the migrated Kedro DAG
**When** `kedro-dagster` compiles it
**Then** schedules exist as Dagster Schedules encoding the `guides/atlas-operations.md` cadence table (bootstrap weekly; F/H/K/L/E.5 + G-after-vdb daily; E/J/M every 6 h; N hourly per maintainer; refresh assets weekly)
**And** the three bootstrap profiles (maintainer / admin / consumer) exist as named Dagster job configurations with the guide's override precedence (explicit run-config/env beats profile defaults)
**And** retries + phase state are observable in the Dagster UI
**And** timeouts are per-node: a cold-run Phase R overrun can no longer abort Phase F/K/N — the legacy 1800 s `cf_atlas_core` defect is demonstrably retired
**And** a `dagster-dryrun` verify task exists (definitions load, schedules enumerate — no live execution); the schedule bring-up itself is an attended event (Q2)
**And** Phase P stays `PHASE_P_ENABLED=1`, admin-config-only, never a default schedule.

- **FRs:** FR-6.
- **Invariants:** AD-6, AD-1 (`kedro-dagster` is replaceable glue; no upward imports), AD-23 (one execution plane; run admission serializes per dataset set — **admission clause RESTORED 2026-07-29: retracted 2026-07-27 as unimplemented (`AUD-ATLAS-046`), built and gated by Story 10.6 (`admission.py` + `settings.HOOKS`), which closes `DW-AD23-1`. C1's `in_process` executor still only serializes ops within a run — and on the Dagster plane it is load-bearing for admission's release path, `DW-AD23-2`**).
- **Mode:** ATTENDED (bring-up boundary event — one of the five § 2.5 attended events; the `dagster-dryrun` gate it builds is loop-consumable thereafter).
- **Gating question:** **Q2** — default adopted (above); re-verify the Dagster bet at wave start (release cadence under Prefect, `kedro-dagster` compatibility, Components/Prefect-deployer ramps).
- **Verify gate:** **builds `dagster-dryrun`**.
- **Depends on:** Epic 3 complete (nodes + refresh assets to schedule).

### Story 4.2: Integrate `kedro-viz` + expose a pixi task

- **Delivered 2026-07-18 — PR #85.** Full record: `specs/spec-4-2-integrate-kedro-viz-expose-a-pixi-task.md`.

As the operator,
I want the topological DAG rendered by `kedro-viz` behind a dedicated pixi task,
So that I inspect dataset schemas and lineage in the browser instead of reading orchestrator source.

**Acceptance Criteria:** (spec § 9 Story C2, binding)

**Given** the compiled DAG
**When** `pixi run viz` executes
**Then** it launches the Kedro-Viz server
**And** operators can inspect dataset schemas + data lineage in the browser.

- **FRs:** FR-6 (structural observability), whole-migration AC-3.
- **Invariants:** AD-1, AD-6.
- **Mode:** LOOP-E.
- **Gating question:** none (Q2 drained at C1).
- **Verify gate:** `dagster-dryrun` + `kedro-test` (existing gates; viz task smoke lands in the pixi task inventory).
- **Depends on:** C1.

---

## Epic 5: Wave D — Semantic Layer & Dashboards

Invert the read surface: 28 fixed questions become declared metrics + pages +
one NL field. Frontend precondition: the CIS two-spine specs (`DESIGN.md` +
`EXPERIENCE.md`) precede D2/D3 frontend work (spec § 2.4).

### Story 5.1: Define the Boring Semantic Layer (BSL) models

- **Delivered 2026-07-18 — PR #86.** Full record: `specs/spec-5-1-define-the-boring-semantic-layer-bsl-models.md`.

As a downstream consumer (page, MCP read, agent),
I want the 28 read CLIs' metric logic declared once as BSL dimensions + measures over the catalog (Ibis → DuckDB),
So that every read surface translates through one semantic interface with proven metric parity.

**Acceptance Criteria:** (spec § 9 Story D1, binding)

**Given** the metric/business logic embedded in the 28 read CLIs
**When** the BSL models are declared
**Then** BSL declares the core metrics (staleness, adoption stage, feedstock health, …)
**And** maintainer-role facts (`package_maintainers ⋈ maintainers`) are first-class BSL dimensions — the raw-SQL JOINs live consumers write today become declared queries
**And** the BSL layer is the single translation interface for downstream consumers
**And** a `bsl-metric-check` verify task exists: metric-parity fixtures proving BSL answers match the legacy CLI outputs for the core metrics (the AD-7 metric-semantics handover anchor).

- **FRs:** FR-8.
- **Invariants:** AD-8, AD-4 (Ibis → DuckDB only).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** **builds `bsl-metric-check`**.
- **Depends on:** Epic 4 (stable orchestrated datasets); B4 (canonical Parquet store).

### Story 5.2: Build the Vizro dashboard + port the 28 CLIs to pages

- **Delivered 2026-07-18 — PR #87.** Full record: `specs/spec-5-2-build-the-vizro-dashboard-port-the-28-clis-to-pages.md`.

As the operator,
I want a BSL-driven Vizro app reproducing the 28 read CLIs as pages, including a factory-status page,
So that every read-only question is answerable from a page meeting the agent-legibility bar.

**Acceptance Criteria:** (spec § 9 Story D2, binding)

**Given** the D1 BSL models and the CIS two-spine design specs
**When** the Vizro app is built
**Then** a Vizro dashboard serves the core KPIs currently locked in CLIs
**And** a "factory status" page reads the BMAD artifact state (sprint-status.yaml, epics frontmatter, `bmad-drift-check --specs` JSON) — agent-readable per § 13.2
**And** the live-confirmed consumer CLIs are answerable from a Vizro page, where for the three FR-9 exceptions (`add-handoff`, `inventory-match`, `library-futures`) "answerable" means the latest-report artifact is surfaced read-only — 8 dashboard pages + factory-status ship in v1; the full 28-CLI inventory port is deferred (`DW-D2-1`) *(corrected 2026-08-02, matching the PRD's 2026-08-01 CAP-8 correction, AUD-ATLAS-041 — this line previously claimed the bar covered all 28)*
**And** the live-confirmed consumer set ports first: `behind-upstream`, `query-atlas`, `whodepends`, `feedstock-health`, `my-feedstocks`, `detail-cf-atlas`, `staleness-report`
**And** pages meet the § 2.1 agent-legibility bar (semantic HTML, ARIA, deterministic layouts; NFR-8) and public-facing breadth stays at the factory-status page (SM-C4).

- **FRs:** FR-9.
- **Invariants:** AD-8, AD-17 (authoring-feeding pages carry build timestamps).
- **Mode:** DEV-AUTO (visual judgment, § 9 preamble).
- **Gating question:** none.
- **Verify gate:** `bsl-metric-check` (+ `kedro-test`); D2 page inventory detail resolves in the CIS specs (Spine Deferred).
- **Depends on:** D1.

### Story 5.3: Integrate Vizro-AI + expose the NL interface as an MCP tool

- **Delivered 2026-07-18 — PR #88.** Full record: `specs/spec-5-3-integrate-vizro-ai-expose-the-nl-interface-as-an-mcp-tool.md`.

As a CFE authoring agent (and the operator),
I want a Vizro-AI natural-language query field and a `query_vizro_ai` MCP tool over the BSL knowledge graph,
So that ad-hoc questions need no SQL and are callable from Claude Code.

**Acceptance Criteria:** (spec § 9 Story D3, binding)

**Given** the D1 BSL graph and the D2 dashboard
**When** Vizro-AI is integrated
**Then** a natural-language query (e.g. the § 4.3 example) returns a generated chart/insight
**And** the `query_vizro_ai` MCP tool is callable from Claude Code
**And** the LLM backend routes through repo model-backend configuration — never a hardcoded public endpoint (Q3 default).

- **FRs:** FR-9.
- **Invariants:** AD-8, AD-7 (MCP body carries no metric logic).
- **Mode:** ATTENDED (backend boundary event — one of the five § 2.5 attended events).
- **Gating question:** **Q3** (Vizro-AI LLM backend) — § 11 default adopted: route through repo model-backend configuration; defining the `_http.py`-analog LLM routing chain is the real work; bounds: no litellm (py3.14 floor), copilot-api bridge ineligible, llama.cpp/ollama/mlx-lm in-env.
- **Verify gate:** `bsl-metric-check` (existing; NL path verified at the attended event).
- **Depends on:** D1, D2.

---

## Epic 6: Wave E — A2A Integration, Lineage & Observability

Wave E adds no new verify gate (§ 2.5 assigns it none); its stories verify
against the existing gates plus their own fixture assets.

### Story 6.1: Implement the A2A communication interfaces

- **Delivered 2026-07-18 — PR #90.** Full record: `specs/spec-6-1-implement-the-a2a-communication-interfaces.md`.

As a CFE authoring agent,
I want a structured A2A surface between the cf_atlas analytical agent and the conda-forge execution agents,
So that insights, contract violations, and policy breaches arrive as structured payloads, not prose.

**Acceptance Criteria:** (spec § 9 Story E1, binding)

**Given** the two agents (cf_atlas analytical, `conda-forge-expert` authoring)
**When** the A2A surface is built
**Then** the `cf_atlas` analytical agent can hand a structured payload to the `conda-forge-expert` agent (publish/subscribe or direct-message — transport resolves in this story's spec, Spine Deferred)
**And** payload schemas live in the `a2a/` module — the single schema source for alerts and insights (AD-20)
**And** payloads feeding authoring decisions carry their build timestamp (AD-17).

- **FRs:** FR-11.
- **Invariants:** AD-20 (sole structured inter-agent channel), AD-17.
- **Mode:** LOOP-E.
- **Gating question:** none (A2A transport is a story-spec decision, not a Q-gate).
- **Verify gate:** existing gates + payload round-trip fixture in `kedro-test`.
- **Depends on:** B3 (MCP surface), Epic 5 (BSL insights to carry).

### Story 6.2: Integrate OpenLineage + OpenTelemetry

- **Delivered 2026-07-18 — PR #91.** Full record: `specs/spec-6-2-integrate-openlineage-opentelemetry.md`.

As the operator,
I want Kedro nodes, Dagster runs, and DuckDB queries instrumented with OpenLineage and OTel,
So that lineage, per-node metrics, and end-to-end traces are observable down to specific API calls.

**Acceptance Criteria:** (spec § 9 Story E2, binding)

**Given** the compiled DAG and hooks layer
**When** instrumentation lands
**Then** lineage + per-node metrics (rows, latency, cache hits) are captured via OpenLineage
**And** end-to-end distributed traces are visible via OTel down to specific API calls
**And** emitted-event/span fixtures are this story's gate assets (AD-20 — fixture-verified, since Wave E has no new named gate).

- **FRs:** FR-12.
- **Invariants:** AD-20, AD-6 (hooks declared in run config — every entry point inherits them, AD-23).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** existing gates + emitted-event/span fixtures in `kedro-test`.
- **Depends on:** C1 (Dagster runs to instrument).

---

## Epic 7: Wave F — The DuckDB Singularity

One engine, contracts that halt, the policy gate CI consumes.

### Story 7.1: Complete the DuckDB consolidation + prove the cold-start claim

- **Delivered 2026-07-18 — PR #92.** Full record: `specs/spec-7-1-complete-the-duckdb-consolidation-prove-the-cold-start-claim.md`.

As the operator,
I want all legacy-`cf_atlas.db` residue migrated or deleted and the performance claims honestly benchmarked,
So that DuckDB/Parquet is the sole store and AC-7's claims are evidence, not promises.

**Acceptance Criteria:** (spec § 9 Story F1, binding)

**Given** B4's legacy retirement and the Wave-A-onward Parquet path
**When** the residue cleanup + benchmark run
**Then** no SQLite read or write path remains anywhere in the migrated surface (grep-gated: no `sqlite3` import outside the retired legacy tree)
**And** the attended benchmark records both a warm incremental refresh (the headline — only affected nodes re-run) and the cold full-build wall-clock vs the legacy 3–4 h network-bound baseline, with evidence recorded per AC-7's honest scoping
**And** the pass threshold was fixed in this story's spec **before** the benchmark ran (SM-3); pass is adjudicated at the attended event by operator sign-off.

- **FRs:** FR-5.
- **Invariants:** AD-4 (grep gate), AD-19, SM-C1 (do not chase cold-start).
- **Mode:** ATTENDED (benchmark boundary event — one of the five § 2.5 attended events). **Keystone story — pre-flight budget raise + `dev_stall_grace_s` raise (AD-18/Spine).**
- **Gating question:** none (threshold is a story-spec decision, Spine Deferred).
- **Verify gate:** grep gate + `kedro-test`; benchmark evidence at the attended event; wave-boundary `test-all`.
- **Depends on:** B4 (retirement decided), Epics 4–6 (surfaces that might still read legacy).

### Story 7.2: Implement the data-validation hook and inline Pandera contracts

- **Delivered 2026-07-18 — PR #93.** Full record: `specs/spec-7-2-implement-the-data-validation-hook-and-inline-pandera-contracts.md`.

As the operator,
I want inline pandera contracts behind a validator-agnostic `AfterNodeRunHook` with version-capped GX as boundary layer,
So that bad data halts the pipeline before persisting, with an A2A alert.

**Acceptance Criteria:** (spec § 9 Story F2, binding)

**Given** a malformed-payload fixture (e.g. PyPI JSON missing a version field)
**When** the node runs under the validation hook
**Then** the validation failure halts execution by raising a native Python exception
**And** the failure propagates to Dagster, halting the pipeline and raising an A2A alert
**And** the hook interface is validator-agnostic: swapping/adding the GX backend requires no node changes (fixture-proven with a stub second validator)
**And** GX participates only at conda-forge 1.18.2 (no ≥1.19 features); the `kedro-great-expectations`/`kedro-pandera` plugins are banned (AD-9).

- **FRs:** FR-10.
- **Invariants:** AD-9, AD-20 (alert channel), AD-23 (hook rides every entry point).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (halt fixture + stub-validator fixture).
- **Depends on:** E1 (A2A alert channel), C1 (Dagster halt propagation).

### Story 7.3: Implement Vector Similarity Search (RAG) via DuckDB `vss`

- **Delivered 2026-07-18 — PR #94.** Full record: `specs/spec-7-3-implement-vector-similarity-search-rag-via-duckdb-vss.md`.

As a CFE authoring agent,
I want RAG embeddings + similarity search via DuckDB's `vss` extension,
So that semantic retrieval over embedded artifacts runs in the same single engine.

**Acceptance Criteria:** (spec § 9 Story F3, binding)

**Given** embedded artifacts in the DuckDB store
**When** a similarity query runs
**Then** it returns ranked results from DuckDB via `vss`
**And** the embedding model/strategy and offline `vss` extension provisioning (default network `INSTALL` collides with AD-13 for the consumer profile) are resolved in this story's spec (Spine Deferred).

- **FRs:** FR-5.
- **Invariants:** AD-4, AD-13 (offline provisioning tension — must resolve, not ignore).
- **Mode:** LOOP-E.
- **Gating question:** none (embedding strategy is a story-spec decision).
- **Verify gate:** `kedro-test` (ranked-results fixture).
- **Depends on:** F1 (consolidated store).

### Story 7.4: Dependency-hygiene node + unified CI policy gate

- **Delivered 2026-07-18 — PR #95.** Full record: `specs/spec-7-4-dependency-hygiene-node-unified-ci-policy-gate.md`.

As CI,
I want the deptry hygiene node and the converged four-axis policy gate as the Universal SBOM pipeline's terminal stage,
So that one schema-validated `ComplianceReport` and one frozen exit code replace CLI scraping.

**Acceptance Criteria:** (spec § 9 Story F4, binding)

**Given** the B7 SBOM pipeline and the F2 validation machinery
**When** the hygiene node + policy gate land
**Then** an injected unused-dependency fixture yields a schema-valid hygiene finding in the `ComplianceReport` artifact (source-less inputs report `not-applicable`, never failure — FR-16)
**And** a policy breach (e.g. `max_critical=0` violated, or a KEV-affecting-current hit) exits with the frozen contract codes (1 policy-fail / 2 error), halts Dagster, and raises an A2A alert — identical failure semantics to an FR-10 violation
**And** the assembled report validates against the four-axis `ComplianceReport` schema (hygiene + security populated; license/currency from atlas-native data or `not-applicable`), with the F4 terminal node as the single producer (AD-12)
**And** the `inventory-match` exit-code flip lands with its one-release deprecation window (`INVENTORY_MATCH_LEGACY_EXIT=1`); CI consumers see the frozen convention
**And** the report schema matches `pyforge-warden.md`'s `ComplianceReport` **by import** *(correct-course 2026-07-17)* — the gate node validates against `pyforge.warden`'s schema module via the `pyforge-atlas[gate]` extra, never a vendored copy (AD-12 schema-by-import); absent the extra, the gate node fails with an explicit install hint while all other pipelines run (independence preserved) — so the planned promotion (MCP tool + pixi CLI) requires no schema change.

- **FRs:** FR-16, FR-18, FR-10.
- **Invariants:** AD-12 (single producer; scope split; degradation-vocabulary mapping), AD-9, AD-20, AD-15.
- **Mode:** LOOP-S (unattended assumption — see Decisions § D-6: the exit-code flip + frozen convention warrant per-story spec approval).
- **Gating question:** none.
- **Verify gate:** `kedro-test` (schema fixtures + exit-code fixtures + `not-applicable` fixture).
- **Depends on:** B7 (intake + matcher), F2 (validation machinery).

---

## Epic 8: Wave G — WebAssembly Portability & Event-Driven Sensors

Zero-backend read surface + event-driven ingestion. Sensor event sources and
the daemon revisit (Q2 tension) resolve at G3.

### Story 8.1: Compile the intelligence layer to Pyodide / DuckDB-WASM

- **Delivered 2026-07-18 — PR #96.** Full record: `specs/spec-8-1-compile-the-intelligence-layer-to-pyodide-duckdb-wasm.md`.

As a dashboard consumer,
I want the Vizro-AI dashboard + BSL layer running in-browser via Pyodide / DuckDB-WASM,
So that the intelligence surface needs no backend at all.

**Acceptance Criteria:** (spec § 9 Story G1, binding)

**Given** the D-wave dashboard + BSL layer
**When** the WASM build runs
**Then** the dashboard loads and queries run client-side in the browser with no backend
**And** a `wasm-smoke` verify task exists (Playwright headless load-and-query against the built artifact — Chromium pre-provisioned).

- **FRs:** FR-14.
- **Invariants:** AD-21, AD-11 (gate is the wave's first deliverable).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** **builds `wasm-smoke`**.
- **Depends on:** Epic 5 (dashboard + BSL), F1 (canonical store).

### Story 8.2: Emit Parquet artifacts to a static web host

- **Delivered 2026-07-18 — PR #97.** Full record: `specs/spec-8-2-emit-parquet-artifacts-to-a-static-web-host.md`.

As a dashboard consumer,
I want Parquet artifacts published to a static host and pulled via HTTP Range,
So that the WASM runtime reads live data with zero backend.

**Acceptance Criteria:** (spec § 9 Story G2, binding)

**Given** the G1 WASM runtime
**When** the emitter publishes
**Then** Parquet artifacts are published to the static host (Q4 default: GitHub Pages) and consumed by the WASM runtime via HTTP Range
**And** the emitter is host-agnostic so an enterprise mirror can substitute (Q4)
**And** the published artifact layout (chunking, manifest) has a single owner: this emitter (Spine convention).

- **FRs:** FR-14.
- **Invariants:** AD-21, AD-2 (mirror substitution).
- **Mode:** ATTENDED (publish boundary event — one of the five § 2.5 attended events).
- **Gating question:** **Q4** (WASM artifact host) — § 11 default adopted: GitHub Pages public path; emitter host-agnostic.
- **Verify gate:** **consumes `wasm-smoke`** (against the published artifact at the attended event; fixture-hosted in-loop).
- **Depends on:** G1.

### Story 8.3: Implement Dagster Sensors for near-real-time ingestion

As the operator,
I want the pipeline event-driven via Dagster Sensors on upstream events (PyPI/GitHub webhooks or RSS),
So that ingestion is near-real-time and incremental instead of purely scheduled.

**Acceptance Criteria:** (spec § 9 Story G3, binding)

**Given** the C1 Dagster repository
**When** a simulated upstream event fires
**Then** it triggers the relevant pipeline incrementally via a Dagster Sensor
**And** the event-source choice (webhooks vs RSS) and the persistent-daemon question it drags in (Q2 revisit condition) are resolved and recorded in this story's spec (Spine Deferred).

- **FRs:** FR-6, spec § 5.9.
- **Invariants:** AD-6, AD-23 (sensor-triggered runs ride the same job machinery), AD-5 (incremental via the dataset class).
- **Mode:** LOOP-E.
- **Gating question:** Q2 revisit condition only (daemon footprint — resolves here if sensors require it; not a blocking Q-gate).
- **Verify gate:** `dagster-dryrun` (sensors enumerate) + simulated-event fixture in `kedro-test`.
- **Depends on:** C1, G2 (per § 14 wave order).
- **DELIVERED (2026-07-18 — closes Wave G):** two sensors (`pypi_release_sensor` → Phase H, `vcs_release_sensor` → Phase K) added to C1's `defs` via `orchestration/event_source.py` (dagster-free logic) + `build_upstream_sensor` in `orchestration/definitions.py`; a simulated event → one `RunRequest` for the existing incremental job (AD-23/AD-5), no-event → `SkipReason`. Event source = RSS/poll cursor (not webhooks); live daemon deferred (DW-G3). Gate `test_definitions_dryrun.py` +12; AD-1 import-ban + `dagster definitions validate` green. See spec § 5.9 / Q2.

---

## Epic 9: Wave H — The AI Software Factory & Karpathy Wiki

The factory layer consumes pipeline outputs and writes only wiki/CMS (AD-22).
MinIO server provisioning is an H1 precondition (Spine Deferred).

### Story 9.1: Scaffold the Karpathy Wiki folder structure and Agent Personas

As the operator,
I want the `wiki/raw/ → compiled/ → outputs/` tree and the 5 BMAD personas (Ingester, Compiler, Linker, Linter, Oracle) defined,
So that the knowledge-base factory has its storage shape and workforce.

**Acceptance Criteria:** (spec § 9 Story H1, binding)

**Given** the scaffolded project
**When** the wiki scaffold lands
**Then** the three-stage wiki tree exists with a scaffold-layout test
**And** the 5 persona definitions resolve through the § 2 customization layers
**And** PostgreSQL/MinIO storage services are conda-forge-provisioned per AD-16 (MinIO server provisioning resolved as this story's precondition).

- **FRs:** FR-22(a).
- **Invariants:** AD-22, AD-16.
- **Mode:** LOOP-E (spec § 9 explicit).
- **Gating question:** none.
- **Verify gate:** scaffold-layout test + persona-resolution test in `kedro-test`.
- **Depends on:** Epic 8 complete (wave order); pipeline outputs to consume exist from Epic 3+.
- **DELIVERED (2026-07-18 — opens Wave H):** new `pyforge.atlas.factory` package. `factory/wiki.py` = the single-owner `raw/→compiled/→outputs/` layout contract (`WIKI_STAGES`/`WikiLayout`/`scaffold_wiki`) with a per-segment `stage_path` traversal guard enforcing the AD-22 write-boundary; `factory/personas.py` = the 5 § 2.2 personas + `resolve_personas(*overlays)` (BMAD customization layers, highest-priority-last; overlay may only refine — unknown name / rename rejected; workforce frozen at five); `factory/storage.py` = env-driven resolver defaulting to the OFFLINE filesystem backend (MinIO selected only when `ATLAS_WIKI_S3_ENDPOINT` set; host-agnostic AD-2). MinIO/PostgreSQL SERVER bring-up DEFERRED (DW-H1). Gate `tests/factory/` (26). AD-1 import-ban green. PR #99.

### Story 9.2: Implement Agno Compilation, Linting, and Q&A Crews

As the operator,
I want `agno` crews that compile raw docs, lint the wiki, and answer questions,
So that the wiki maintains itself with agent labor.

**Acceptance Criteria:** (spec § 9 Story H2, binding)

**Given** the H1 scaffold and a fixture wiki
**When** each crew runs end-to-end
**Then** compile transforms raw → compiled, lint reports violations, and Q&A answers grounded in compiled content
**And** wiki outputs carry their source datasets' staleness markers forward (AD-13/AD-22 — republication never launders freshness).

- **FRs:** FR-22(b).
- **Invariants:** AD-22, AD-13.
- **Mode:** DEV-AUTO (spec § 9 explicit: crew design needs judgment).
- **Gating question:** none (crew design detail is a story-spec decision, Spine Deferred).
- **Verify gate:** crews-on-fixture-wiki tests in `kedro-test`.
- **Depends on:** H1.
- **DELIVERED (2026-07-18):** `factory/crews.py` — `CompileCrew` (raw→compiled, per-doc-resilient, forwards source staleness from BOTH the inline `stale:` frontmatter AND the `.staleness.json` sidecar into compiled frontmatter + a visible body banner — AD-13/AD-22, republication never launders freshness), `LintCrew` (reports `missing-frontmatter`/`missing-title`/`empty-body`/`broken-link` [path-resolved, recursive]/`laundered-staleness`/`malformed-frontmatter`; never raises), `QACrew` (grounded answers over compiled content; deterministic keyword retriever + extractive synthesizer defaults). agno-Agent/LLM synthesis + F3-vss production retriever are injectable seams, offline by default — live bring-up DEFERRED (DW-H2). Gate `tests/factory/test_crews.py` (26). AD-1 import-ban green (yaml+stdlib only). An independent adversarial review found 2 MUST-FIX (inline-staleness laundering; lint/QA crash-on-malformed) + 1 SHOULD-FIX (leaf-only broken-link) — all fixed + regression-tested before merge.

### Story 9.3: Integrate La Suite Docs REST API Sync

As the operator,
I want `LaSuiteClient` + `WikiSyncer` pushing compiled wiki files to the Layer-1 CMS via the Wagtail/Django REST API,
So that humans read the factory's knowledge in the presentation layer.

**Acceptance Criteria:** (spec § 9 Story H3, binding)

**Given** the H2 compiled wiki output and a mock Wagtail API
**When** the sync runs
**Then** a round-trip fixture test passes against the mock (push, update, idempotent re-push).

- **FRs:** FR-22(c).
- **Invariants:** AD-22 (writes only wiki/CMS; idempotent re-push).
- **Mode:** LOOP-E (spec § 9 explicit).
- **Gating question:** none.
- **Verify gate:** mock-Wagtail round-trip fixture in `kedro-test`.
- **Depends on:** H1, H2.
- **DELIVERED (2026-07-18):** `factory/lasuite.py` — `LaSuiteClient` (create/update/get/list over the Wagtail/Django REST shape; clear `LaSuiteError` on non-2xx AND on a 2xx-without-id, per § 2.1) + `WikiSyncer` (idempotent **outputs/**→CMS push keyed by content sha: new→create, changed→update, unchanged→SKIP with NO remote call). CMS source is `outputs/` (the Oracle's final reports, per the H1 layout contract + § 7.4), not internal `compiled/` (`source_stage` override available). Transport is the injected `opener` seam — package code holds no HTTP client (AC-2, no-inline-IO gate green); the default opener refuses clearly. Mapping sidecar lives at the wiki ROOT (AD-22), written ATOMICALLY (tmp+os.replace) and corruption-loud on load. Verified against an in-memory mock Wagtail (push/update/idempotent-re-push/mapping-resume). Live Wagtail server + httpx opener bring-up DEFERRED (DW-H3). Independent review found 3 SHOULD-FIX (malformed-2xx KeyError; non-atomic sidecar write; compiled-vs-outputs contract contradiction) + NITs — all fixed + regression-tested. Gate `tests/factory/test_lasuite.py`.

### Story 9.4: Orchestrate Crews via Dagster

As the operator,
I want Dagster assets, sensors (new raw files), and schedules (weekly linting) triggering the Agno crews autonomously,
So that the factory layer runs itself.

**Acceptance Criteria:** (spec § 9 Story H4, binding)

**Given** the H2 crews and the C1 Dagster repository
**When** the assets/sensors/schedules land
**Then** an asset dry-run enumerates the crew assets
**And** a simulated new-raw-file event triggers the compile crew via a Sensor.

- **FRs:** FR-22(d), FR-6.
- **Invariants:** AD-22, AD-6, AD-23.
- **Mode:** LOOP-E (spec § 9 explicit).
- **Gating question:** none.
- **Verify gate:** `dagster-dryrun` (crew assets enumerate) + simulated-trigger fixture.
- **Depends on:** H1, H2, H3; C1.
- **DELIVERED (2026-07-18 — closes Wave H + the migration):** the Wave-H crews run on C1's single Dagster plane (AD-6/AD-23). `orchestration/definitions.py` gains crew ASSETS (`compiled_wiki` → CompileCrew, `wiki_lint_report` → LintCrew, `deps=[compiled_wiki]`), their asset-jobs (`wiki_compile_job`/`wiki_lint_job`), a weekly LINT schedule (`wiki_lint_schedule`, `0 6 * * 1`, § 7.2), and the new-raw-file compile SENSOR (`wiki_raw_file_sensor` → `wiki_compile_job`, ships STOPPED). The raw-scan + cursor-dedupe DECISION logic lives in `orchestration/wiki_events.py` (dagster-free — AD-1 holds; only definitions.py imports dagster). `dagster definitions validate` green; a simulated new-raw-file event (injected lister + `build_sensor_context`) → one `RunRequest` for the compile job. Live daemon + wiki-store bring-up DEFERRED (DW-H4). Gate `test_definitions_dryrun.py` H4 section (+12; C1/G3 invariants scoped to kedro op-jobs via `_kedro_jobs`). Independent review found 1 SHOULD-FIX (`_decode_cursor` crashed on a valid-JSON-but-nested cursor, breaking its "never a crash" contract) — fixed (filter to str inside the guard) + regression-tested; the `_kedro_jobs` scoping was verified NOT to weaken any C1/G3 guard.

---

## Epic 10: Post-Audit Remediation — Round-3 Findings

Added 2026-07-27 by `sprint-change-proposal-2026-07-27.md`, after the migration
shipped. An independent spec-to-code audit (a different model, run against main)
raised 49 findings; the atlas-owned subset was re-verified claim by claim, and the
survivors are closed here. The audit branch (PR #131) is abandoned and will never
merge — `planning-artifacts/specs/spec-code-audit-remediation-2026-07-26.md` is the
only record of what was incorporated, and its Incorporation record carries the
disposition of all 49.

Two conventions govern this epic:

- **Verify-gate order, not wave order.** I3 runs first because `kedro-test` is red
  on main until it lands (6 failures). Any other story would inherit a failing gate
  and could not prove its own change.
- **Findings are closed at their source.** A claim that drifted from its code is
  fixed in whichever is wrong — the audit's value was in the disagreement, not in
  assuming the code was right.

### Story 10.1: Restore atlas dependency-completeness so the suite can collect

As the operator,
I want the pyforge-atlas package to declare every module it imports,
So that the test suite collects at all.

**Acceptance Criteria:**

**Given** a resolved `pyforge-atlas` environment
**When** `kedro-test` runs
**Then** collection completes with zero import errors.

- **Findings:** AUD-ATLAS-010, AUD-ATLAS-013.
- **Mode:** DEV (direct).
- **Verify gate:** `kedro-test` collects.
- **Depends on:** none (BLOCKER — everything else in the epic waits on it).
- **DELIVERED (2026-07-27):** 15 runtime dependencies declared from an AST-derived
  import inventory in `pixi.toml` + `pyproject.toml`. `boring_semantic_layer` was
  deliberately EXCLUDED as PyPI-only (no conda-forge feedstock) and is carried as a
  known gap rather than silently vendored. 17 collection errors → 781 passed.

### Story 10.2: Truth-up the Spec kernel and its companions

As a reader of the Spec,
I want its Constraints and Success signal to state what actually shipped,
So that the contract is not overclaiming.

**Acceptance Criteria:**

**Given** the shipped code
**When** the kernel's claims are checked one by one
**Then** each is true, retracted, or scoped with a stated exception.

- **Findings:** AUD-ATLAS-041, 046, 047, 049.
- **Mode:** DEV (direct).
- **Verify gate:** reference-integrity check; no broken links.
- **Depends on:** I0.
- **DELIVERED (2026-07-27):** the "One execution plane" run-admission claim RETRACTED
  from Constraints (it asserted a cross-run safety property that `in_process` does not
  provide — the real work is I5); CAP-8 corrected to the 8 shipped PageDefs; the
  Success signal gained a scope note; `shipped_scope_note` added to frontmatter
  recording that top-level `status: shipped` covers waves 0–H, not the F1 benchmark.

### Story 10.3: Uniform story-spec frontmatter, without laundering provenance

As a maintainer,
I want the story specs to carry consistent frontmatter,
So that they are machine-readable — without rewriting recovered originals.

**Acceptance Criteria:**

**Given** 32 story specs, 12 of them verbatim recovered originals
**When** frontmatter is applied
**Then** the 20 authored specs are uniform
**And** the 12 recovered originals keep their original form, with the exception documented.

- **Findings:** AUD-ATLAS-045 (decision), AUD-ATLAS-048.
- **Mode:** DEV (direct).
- **Verify gate:** spec-surface check.
- **Depends on:** I0.
- **DELIVERED (2026-07-27):** the audit's blanket `status: shipped` stamp was REVERSED
  for the 12 recovered originals — provenance over uniformity, per
  `planning-artifacts/README.md`. Rewriting a verbatim recovered artifact to satisfy a
  linter destroys the only evidence of what was actually written. Catalog-entry counts
  corrected 73 → 86 in spec-2-2/spec-3-6.

### Story 10.4: Preserve NULL identity under pandas 3.0

As a consumer of the semantic layer,
I want a NULL group key to come back as `None`, not `NaN`,
So that null groups remain identifiable and no value is mis-attributed.

pandas 3.0 coerces `None` → `NaN` in `str`-dtype columns. Because `NaN != NaN`, a
NaN group key cannot be looked up, compared, or used as a dict key — so a "null
maintainer" group becomes unreachable rather than merely unnamed. Six tests
reproduce this on main and are the ready-made regression set:

```
tests/pipelines/core/test_nodes.py::test_attribute_feedstocks_handles_nan_feedstocks_cell
tests/pipelines/core/test_nodes.py::test_attribute_feedstocks_node
tests/pipelines/seed_gaps/test_nodes.py::test_licmap_likely_and_report_tiers
tests/semantic/test_bsl_metric_parity.py::test_is_actionable_matches_legacy_view
tests/semantic/test_bsl_metric_parity.py::test_feedstock_health_filters_match_legacy
tests/semantic/test_maintainer_dimension.py::test_maintainer_with_no_packages_and_package_with_no_maintainer
```

Observed: `assert None in {'alice': Decimal('100'), 'zzz': nan, nan: None}` — the
null-maintainer group is present but keyed `nan`, so the assertion that it exists
cannot pass.

**Acceptance Criteria:**

**Given** a frame with a genuine NULL in a grouping column
**When** it flows through the affected nodes and the semantic layer
**Then** the null group is keyed `None`, not `NaN`
**And** no real row's measure is attributed to the null group
**And** a NULL measure stays NULL rather than becoming a fabricated `0`
**And** all six tests above pass with no assertion weakened to accommodate `NaN`.

- **Findings:** AUD-ATLAS-011.
- **Invariants:** the existing null-identity contracts in the listed tests are
  BINDING — the fix goes in the production path, never in the assertions.
- **Mode:** LOOP (bmad-loop).
- **Verify gate:** `kedro-test` GREEN (781 → 787 passing), `kedro-catalog-check`.
- **Depends on:** I0. **Blocks I4 and I5** — the gate is red until this lands.

### Story 10.5: Stamp advisory data with its build provenance (AD-17)

As an agent reading atlas data,
I want every advisory response to carry the build stamp of the data behind it,
So that I can tell fresh data from stale.

**AMENDED 2026-07-28 after a CRITICAL escalation — the first draft's approach was
wrong, and the loop was right to refuse it.** The dev session implemented the
original ACs faithfully (all 6 tasks, 790/790 green), then its review pass found the
defect was in *this contract*, reverted rather than ship it, and escalated. The
original AC said the envelope carries a `build_stamp` computed as wall-clock-**now**
at call time. That can never distinguish fresh data from stale — every read of a
month-old dataset reports "now" — which contradicts AD-13 ("republication never
launders freshness"), SPEC.md's own AD-17 definition (a payload carries **the
pipeline's build timestamp**, not a read receipt), and the Wave-H `CompileCrew`
precedent, which forwards *source* staleness into republished output rather than
fabricating a fresh timestamp.

**The escalation offered two ways out and BOTH ARE REJECTED.** (a) "invent or build a
new per-dataset freshness signal" — unnecessary, see C1. (b) "rename the field away
from AD-17 framing to an honest response-generation receipt" — that keeps the useless
value and deletes the requirement instead of meeting it. **C1–C6 below are binding.**

**The escalation's blocking premise was FALSE, and this is why (b) is rejected.** It
concluded "no per-dataset materialization timestamp exists anywhere in the catalog
today." `IncrementalParquetDataset` already *"stamps + round-trips a per-row
`fetched_at` epoch timestamp and owns the TTL freshness verdict"* — **15 catalog
entries** carry it. The signal exists, is already persisted, and needs no inventing.

**C1 — Stamp from the DATA's own provenance, never from the clock.** *Given* a dataset
read, *when* the envelope is built, *then* its freshness fields derive from that
dataset's own recorded provenance. Per kind, exhaustively (75 catalog entries today):

| Dataset kind | Count | Provenance the stamp MUST use |
|---|---|---|
| `IncrementalParquetDataset` | 15 | its own `fetched_at` column (epoch seconds) |
| `pandas.ParquetDataset` | 22 | the materialized file's mtime |
| `api.APIDataset` | 24 | **`now` IS correct here** — the read genuinely is the fetch |
| everything else | rest | `null` + an explicit `reason`, never a fabricated value |

**C2 — The envelope is self-describing about WHICH of those it got.** *Given* any
envelope, *when* a consumer inspects it, *then* a `provenance_kind` field names the
source of the timestamp (e.g. `row-fetched-at` · `file-mtime` · `live-fetch` ·
`unavailable`). An agent must never have to guess whether a timestamp means "the data
is from then" or "we called the API just now" — those are opposite meanings and the
whole finding (AUD-ATLAS-043) is that conflating them is what made the field useless.

**C3 — For row-level provenance, carry the RANGE and judge on the OLDEST.** *Given* an
incremental dataset whose rows were fetched at different times, *when* the envelope is
built, *then* it carries both the oldest and newest `fetched_at`, and any staleness
verdict uses the **oldest** (worst case). A single summary timestamp on a partially
refreshed dataset is itself a small laundering of freshness.

**C4 — `null` is a valid, REQUIRED answer.** *Given* a dataset with no recoverable
provenance, *when* the envelope is built, *then* the timestamp is `null` with a stated
`reason` and the call still succeeds. Fabricating a plausible value is the defect this
story exists to remove; failing the read would be worse than a truthful "unknown".

**C5 — Version the envelope (folds in the escalation's `bad_spec` finding).** *Given*
this is a breaking change to the response shape, *when* the envelope ships, *then* it
carries a `schema_version`. The escalation raised this and it stands regardless of the
approach chosen.

**C6 — Close the AUD-ATLAS-044 half too.** *Given* the Vizro dashboard, *when* any page
renders, *then* it carries its data's stamp — not only `factory-status`, which is the
sole page carrying one today (`dashboard/app.py`). Same rule as C1: the page shows the
provenance of the data it displays, not the time it was rendered.

- **Findings:** AUD-ATLAS-043, AUD-ATLAS-044 (+ the escalation's `schema_version`
  `bad_spec` finding, folded into C5).
- **Invariants:** AD-17, AD-13 (republication never launders freshness) — the invariant
  the original AC would have violated.
- **Mode:** LOOP (bmad-loop). Re-driven from this corrected contract; the reverted
  patch is NOT restored, because it faithfully implemented the wrong approach.
- **Verify gate:** `kedro-test` + `kedro-catalog-check`, plus per-kind envelope tests
  proving a **persisted** dataset reports its own recorded time and **not** the read
  time — a test that only asserts "a stamp is present" does not discharge C1, since
  the rejected implementation passed exactly that test.
- **Depends on:** I3 (gate).

### Story 10.6: Make run admission real, or stop claiming it

As the operator,
I want concurrent triggers on one dataset set to be genuinely serialized,
So that two runs cannot write the same dataset at once.

The Spec asserted this as a safety property and `definitions.py:26` documented it,
but `dagster.yml` declares only the `in_process` executor — which serializes ops
WITHIN a run and provides no cross-run or cross-process admission at all. I1 retracted
the claim; this story decides whether to build the property or record its absence as
a contract-level non-goal.

**The mechanism question is CLOSED — operator decision, 2026-07-28.** The story's
former `q_gate` ("file lock vs DB lock vs Dagster run-queue — decide in the story
spec") was resolved by the operator before this story was drafted. D1–D6 below are
**binding ACs, not suggestions**; the dev session implements them rather than
re-deciding. Rationale is recorded so a future reader can re-open it on evidence,
not on taste.

**Grounding (verified in the code, 2026-07-28):** writes land as **Parquet** under
`data/` (env-overridable `PYFORGE_ATLAS_DATA_ROOT`). Every DuckDB connection in the
package is argless — `duckdb.connect()` / `ibis.duckdb.connect()` — i.e. **in-memory**;
DuckDB is the query engine over Parquet, **not** a persistent store. Concurrent
writers are therefore *multiple processes on one machine sharing a POSIX filesystem*:
the 7 MCP `run_*` tools (each calling `KedroSession.run`), the CLI, and — once
DW-C1-1 lands — Dagster.

**Acceptance Criteria (D1–D6, all binding):**

**D1 — Mechanism: an OS file lock.** *Given* the write store is Parquet on a local
filesystem, *when* admission is enforced, *then* it uses `filelock` (**already present
in the `pyforge-atlas` env** — no new dependency).
*Rejected — DB lock:* there is no database to lock. DuckDB here is in-memory, so this
would mean **creating** a persistent store purely for coordination — a new failure
domain — and DuckDB permits one writer process anyway, i.e. its file lock with extra
steps.
*Rejected — Dagster run-queue (`QueuedRunCoordinator` + `tag_concurrency_limits`):*
it governs only runs that pass through the Dagster daemon. **The MCP tools never touch
Dagster** — they call `KedroSession.run` directly. It would guard the one entry point
that is not the problem, leave the agent-facing path unguarded, and cannot even be
demonstrated today (the daemon is deferred, DW-C1-1). Shipping it would satisfy this
story's letter while leaving AD-23's actual property false — the precise defect class
AUD-ATLAS-046 raised.

**D2 — Placement: a Kedro hook registered in `settings.HOOKS`.** *Given* AD-23's rule
is "every entry point rides the same machinery", *when* the lock is acquired, *then* it
happens in `before_pipeline_run` and is released in **both** `after_pipeline_run` **and**
`on_pipeline_error`. This is the load-bearing half of the story: `HOOKS = (ProjectHooks(),
AtlasObservabilityHooks(), DataValidationHooks())` is *already* the seam validation and
lineage use for exactly this reason — a `kedro run`, an MCP trigger and a Dagster run all
pass through `KedroSession.run`. Admission is the same kind of cross-cutting guarantee and
belongs in the same place. Admission logic MUST NOT live in `mcp/`, in `orchestration/
definitions.py`, or in any node body.

**D3 — Reject, do not queue** (with an opt-in bounded wait). *Given* a dataset set whose
lock is held, *when* a second run requests admission, *then* it fails fast with a typed
error naming **which** dataset(s) are locked, the holding run id, and the hold start time.
A blocking wait is available only via explicit opt-in with a finite timeout. Rationale: the
caller is usually an agent over MCP, where a silent block is indistinguishable from a hang
and may hit the MCP timeout anyway; queueing is the right default for a daemon, not for a
synchronous tool call.

**D4 — Granularity: the pipeline's declared OUTPUT dataset set**, one lock per dataset,
**acquired in sorted name order**. *Given* two pipelines with disjoint outputs, *when* both
run, *then* both proceed concurrently. *Given* two pipelines sharing one output dataset,
*when* both run, *then* exactly one is admitted. Sorted acquisition order is the deadlock
avoidance and costs nothing. A single global lock is NOT acceptable: it would serialize
genuinely unrelated pipelines (`seed_gaps` vs `vulnerability`) and would overclaim, since
AD-23 says *per target dataset set*, not "one run at a time".

**D5 — Stale locks are reclaimable.** *Given* a lock whose holding PID is no longer alive,
*when* a new run requests admission, *then* it reclaims the lock and proceeds, recording
that it did so. The lock file records holder PID + start time. A SIGKILL'd run must never
wedge the factory permanently — that converts a safety feature into an outage.

**D6 — Build it; the non-goal escape hatch is CLOSED.** The AC formerly permitted
"record the absence as a contract-level non-goal". That option is withdrawn: AD-23 is
currently DEMOTED in the spine because the claim outran the code, and documenting the
absence would leave a spine invariant permanently half-stated. On green, **re-promote
AD-23 to its full form** in `ARCHITECTURE-SPINE.md` and correct the retracted docstring in
`orchestration/definitions.py`.

**Stated boundary (write it down, don't discover it later):** file locks do not hold
across machines — NFS `flock` is unreliable. Atlas is single-machine today, so this is in
scope as written; a multi-machine atlas re-opens D1. Dagster's run-queue is **not** wasted:
once the daemon lands it is a complementary nicety for Dagster-originated runs, while this
hook-level lock remains the actual safety property because it is the only one covering MCP
and CLI.

- **Findings:** AUD-ATLAS-046, DW-AD23-1.
- **Invariants:** AD-23 (re-promoted by this story, per D6).
- **Mode:** LOOP (bmad-loop) — per the policy's HARD-STORY procedure, flip
  `[adapter.dev] model` to `opus` before running this one.
- **Verify gate:** `kedro-test` + `kedro-catalog-check`, plus a NEW **two-process**
  concurrency test: a real second OS process (not a thread, not a mock) attempting the
  same dataset set is rejected, and one with a disjoint set is admitted. A single-process
  test does not discharge this AC — the defect being fixed is cross-process.
- **Depends on:** I3 (gate); informed by I1's retraction.

---

## Execution-Mode Summary (per § 2.5)

| Mode | Count | Stories |
|---|---|---|
| ATTENDED | 6 | 0.1, B4 (parity), C1 (bring-up), D3 (backend), F1 (benchmark), G2 (publish) |
| DEV-AUTO | 4 | A1, A2, D2, H2 |
| LOOP-S (per-story-spec-approval) | 11 | A3, B1, B2, B3, B5, B6, B7, B8, B9, B10, F4 |
| LOOP-E (per-epic) | 11 | C2, D1, E1, E2, F2, F3, G1, G3, H1, H3, H4 |

22 loop-drivable stories (11 + 11) against § 2.5's "~21 of 32 (11 at
spec-approval, ~10 relaxable to per-epic)" — within the spec's "~" tolerance;
see Decisions D-6/D-7. Attended boundary events are exactly the five § 2.5
events plus attended Wave 0. Loop execution is sequential; keystones B1/B2/F1
carry pre-flight budget raises.

## Q-Gate Summary (§ 11, unattended defaults adopted)

| Q | Gates | Default adopted | Drained at |
|---|---|---|---|
| Q1 | B4 → legacy retirement | Exact row-count + value parity on actionable views; benign diffs documented | B4 event |
| Q2 | Wave C (+ G3 revisit) | On-demand/scheduled local; daemon only if sensors require; switch ramps only on concrete deterioration | C1 wave start |
| Q3 | D3 | Repo model-backend routing; no hardcoded endpoint | D3 event |
| Q4 | G2 | GitHub Pages; host-agnostic emitter | G2 event |
| Q6 | B5 mapping asset | Consolidate on migrated Phase C; `g10_spelling` + no-clobber survive | Before B5 |
| Q7 | B8 | Build once as Kedro nodes in Wave B | Before B8 |

## Decisions & Assumptions (unattended intake)

Recorded per the headless protocol; no human elicitation occurred. Every
resolution below is the spec's stated decision, the § 11 recommended default,
or a minimal structural inference flagged as such.

1. **D-1 — Epics = waves, verbatim.** The step-2 guidance to organize epics by
   user value was satisfied by adopting the spec § 9 wave structure unchanged:
   waves ARE the value/risk boundaries (each ends with its own gate, boundary
   event, and PR — § 14), and the task contract freezes them. No
   consolidation, splitting, or renumbering was applied; the file-churn check
   (step 4) is satisfied because waves already partition by component
   (scaffold / pipelines / dagster / bsl+vizro / a2a+hooks / duckdb+gate /
   wasm / wiki).
2. **D-2 — Story IDs.** Spec § 9 IDs are the primary keys; the template's
   `N.M` numbering appears only as a parenthesized epic-local alias. Sprint
   planning and story files must key on the spec IDs.
3. **D-3 — B4 parity-harness wording conflict** (spec § 2.5 "parity-diff
   through B1–B4" vs B4's AC "built incrementally through B1–B3"): resolved
   as build B1–B3, consume + attended sign-off at B4 — the PRD § 6.1 /
   addendum § 3 resolution, carried forward here.
4. **D-4 — `bmad-switch` target.** Spec § 2.5/§ 14's pre-intake
   `bmad-switch local-recipes` literal is superseded by
   `scripts/bmad-switch pyforge-atlas` (PRD § 9.11, AD-18).
5. **D-5 — Open questions** Q1–Q4, Q6, Q7 adopted at § 11 defaults (table
   above), each remaining a scheduled re-check drained at its gating
   wave/story before dependent work runs. Q5 retired (outcome = Wave H).
6. **D-6 — F4 at LOOP-S `[ASSUMPTION]`.** § 2.5 fixes 11 spec-approval
   stories but names only A3 + Wave B's nine loop stories explicitly (10).
   F4 is assigned the 11th spec-approval slot because it lands the frozen
   exit-code flip + `ComplianceReport` single-producer semantics (AD-12) —
   the highest-blast-radius unattended story outside Wave B. The
   technical-research drivability map (spec § 13.4 artifact) is the
   reconciliation authority at sprint planning; if it names a different
   11th story, follow it and re-note here.
7. **D-7 — Mode totals.** The resulting 11 LOOP-S + 11 LOOP-E = 22
   loop-drivable vs § 2.5's "~21 (11 + ~10)": read as within the spec's
   explicit "~" tolerance. Attended = the five named boundary events + Wave-0
   0.1; DEV-AUTO = A1/A2 (harness, § 2.5), D2 (visual judgment, § 9
   preamble), H2 (spec-explicit).
8. **D-8 — Wave E gate.** § 2.5 assigns Wave E no new named gate; E1/E2
   verify against existing gates plus their own fixture assets (AD-20 names
   emitted-event/span fixtures as E2's gate assets). This is spec-conformant,
   not a gap.
9. **D-9 — C1 mode.** C1 is both a gate-builder (`dagster-dryrun`) and an
   attended bring-up event. Modeled as ATTENDED (the § 2.5 boundary-event
   list governs); the dryrun gate it ships is loop-consumable by later
   stories. Same pattern for G2 (attended publish consuming `wasm-smoke`).
10. **D-10 — Step-2 "no forward dependencies" vs B5–B7 sequencing.** § 14
    orders B5→B6→B7 after B4, but their substance depends only on B1/B2
    (+ Q6 for B5) — each is implementable from previous stories only; the
    § 14 order is preserved as the execution sequence. B8/B9/B10 depend on
    B1/B2 datasets and are explicitly not parity-gated (AD-14), so a B4
    parity delay does not block them (spec § 9 preamble).
11. **D-11 — No UX contract.** No bmad-ux spine pair exists; the CIS
    two-spine precondition for D2/D3/G1 frontend work is carried as a
    story-level requirement instead of UX-DRs (spec § 2.4). Zero UX-DRs is
    therefore correct, not missing coverage.
12. **D-12 — Starter-template rule.** Step-4 expects "Epic 1 Story 1" to be
    the scaffold story; here the scaffold is A1 (Epic 2 Story 1) because
    frozen Wave 0 (SKF legacy translation) precedes it as execution
    scaffolding. Recorded as a deliberate deviation mandated by the frozen
    wave structure.
13. **D-13 — Story 0.1 has no FR** (spec-explicit enabler); FR coverage is
    complete over FR-1..FR-22 without it.
14. **D-14 — Whole-migration ACs (spec § 10)** map onto epics via the PRD
    success metrics (SM-1..SM-12) and are not duplicated per story; each
    story's binding ACs remain spec § 9's text, restated here in
    Given/When/Then without semantic alteration.
15. **D-15 — Conditional Phase T** (trendshift Track A): not modeled as a
    story; if it ships before Wave B completes it joins the migration surface
    per PRD § 6.1 — re-check at execution start alongside the live
    groundtruth (a Wave-0 precondition).
16. **D-16 — Warden-alignment correct-course (2026-07-17, owner-approved,
    attended)**: A1 gains the warden-pattern packaging ACs (workspace member
    `src/shared/packages/pyforge-atlas/`, `pyforge.atlas` namespace package,
    hatchling + dual artifacts, dedicated pixi feature/env); F4's
    ComplianceReport conformance becomes schema-by-import via the optional
    `pyforge-atlas[gate]` extra. Dependency inventory (per the owner's
    independence requirement): atlas→warden = the one optional `[gate]`
    code edge; warden→atlas = zero code edges (warden consumes atlas *data*
    — KEV/EPSS/velocity/mapping datasets — optional-if-present, a future
    warden-side story); shared third-party deps co-resolve at workspace
    level. Both tools install and run independently. Proposal:
    `sprint-change-proposal-2026-07-17.md`; spine Decisions § 10.

---

## Epic 11: Kedro-org tooling — audit, publish, decide

**Value delivered.** Atlas's own Kedro deployment stops being an unusually
invariant-heavy island: the org's tooling is evaluated against it on the record, and the
pipeline DAG is published continuously rather than screenshotted.

### Story 11.1: kedro-skills audit-then-adopt (FR-61)
**Effort:** S • **Status:** done
**Given** `kedro-skills` pinned at the evaluated version **When** it runs against the real
`pyforge-atlas` project **Then** every piece of generated guidance is audited against the
AD-invariants; passing content lands in `.claude/skills/` reproducibly; contradicting
content is excluded **with the contradiction recorded**; **And** "not yet" is a valid
final verdict that closes the story.

### Story 11.2: Publish the real DAG continuously (FR-62)
**Effort:** S • **Deps:** Steward S-2.1 (`deploy dashboard`) • **Status:** done
**Given** a push touching the pipelines tree **Then** CI builds Kedro-Viz from the **real**
package, never the stub-mirror, and publishes **through `steward deploy dashboard`** —
Atlas owns the outcome, Steward owns the mechanism.

### Story 11.3: Record the `vscode-kedro` verdict (FR-63)
**Effort:** XS • **Status:** done
**Given** the evaluation **Then** a dated adopt/defer decision exists; if deferred, an
optional `.vscode/extensions.json` recommendation is the whole deliverable. The
**decision** closes this, not an installation.

---

## Epic 12: Upstream discovery — what to package next

**Value delivered.** The factory stops picking packaging targets by hand. Atlas proposes;
Mason packages.

### Story 12.1: Trending ingest (FR-64)
**Effort:** M • **Status:** done
**Given** a schedule **Then** GitHub-trending candidates land in a named dataset under the
`<domain>_<entity>` convention, via an **injected** fetcher (AD-1), never inline IO.

### Story 12.2: Tier classification (FR-65)
**Effort:** M • **Deps:** S-13.1 • **Status:** done
**Given** ingested candidates **Then** each is tiered by declared rules, and an
unclassifiable candidate is **reported**, never silently tiered.

### Story 12.3: `trending-candidates` operator surface (FR-66)
**Effort:** S • **Deps:** S-13.2 • **Status:** done
**Given** a classified set **Then** a CLI/MCP tool answers "what is worth packaging next?"
with `--json`, read-only and offline-safe like every other atlas read surface.

### Story 12.4: Fixed-source audit track (FR-67)
**Effort:** S • **Deps:** S-13.2 • **Status:** done
**Given** the declared org-audit list **Then** each candidate's CURRENT state is
re-verified before proposal — one that shipped independently since the list was written is
dropped, not re-proposed.

### Story 12.5: Downstream handoff to Mason (FR-68)
**Effort:** XS • **Deps:** S-13.3 • **Status:** done
**Given** a selected candidate **Then** it hands off as structured data, not prose; Atlas
proposes and never authors a recipe.

---

## Epic 13: Atlas query dashboards — hand-someone-a-link views

Decomposes **`spec-atlas-query-dashboards`**
(`planning-artifacts/specs/spec-atlas-query-dashboards/SPEC.md`, CAP-1..CAP-4).

**Value delivered.** A `cf_atlas.db` query stops being CLI-text-only: the 11 atlas query
CLIs gain linkable Panel/Bokeh views — static HTML fragments first, live filter/drill
layered on top — no SPA framework, no second data layer, and an air-gap-clean render
profile. Fenced off: the existing Vizro `dashboard/` module (Story 5.2's surface, reading
the Parquet catalog through the D1 BSL seam) is untouched — this lands as a separate
module under a non-colliding name, querying `cf_atlas.db` directly.

### Story 13.1: Static view catalog (CAP-1)
**Effort:** M • **Deps:** — • **Status:** done
**Given** the live `cf_atlas.db` **When** a curated catalog view mirroring one of the 11
query CLIs (`staleness-report`, `feedstock-health`, `whodepends`, …) renders **Then** it
emits a self-contained HTML fragment whose rows agree with its CLI counterpart's output on
the same database snapshot **And** rendering a static view opens zero WebSocket
connections — the lowest-risk mode ships first and stays the base layer.

### Story 13.2: Pluggable widget registry (CAP-3)
**Effort:** S • **Deps:** S-14.1 • **Status:** done
**Given** the view catalog **When** a view declares its query plus a widget-type NAME
**Then** a small registry maps name → renderer for both the static-fragment and WebSocket
modes **And** adding a new widget type is one registry entry plus one renderer with zero
edits to existing view definitions; the seed set derives from a survey of the 11 mirrored
CLIs' query shapes (spec open question 1), not the source dream's
Tabulator/Perspective/PGWalker catalog.

### Story 13.3: Bokeh WebSocket interactivity (CAP-2)
**Effort:** M • **Deps:** S-14.2 • **Status:** done
**Given** the ASGI host chosen in this story's spec (the contract is "any ASGI host" —
explicitly NOT contingent on DW-H3/Wagtail) **When** at least one catalog view runs live
**Then** filter/drill/re-sort execute against `cf_atlas.db` over a Bokeh WebSocket
session **And** swapping the host touches mounting code only, never a view definition —
the static mode (S-14.1) survives unchanged underneath.

### Story 13.4: Air-gap asset rewriting (CAP-4)
**Effort:** S • **Deps:** S-14.3 • **Status:** done
**Given** the air-gapped render profile **When** any page — static fragment or WebSocket
app — renders **Then** Bokeh/Panel asset URLs resolve to locally-served or mirrored
assets and the emitted HTML contains zero references to external CDN hosts
(grep-verifiable) **And** the default profile's output is unchanged, composing with
`_http.py`'s runtime-driven enterprise posture (env vars only, never committed config).

---

## Epic 14: Artifactory download intelligence — mock-first AQL

Decomposes **`spec-artifactory-download-intelligence`**
(`planning-artifacts/specs/spec-artifactory-download-intelligence/SPEC.md`, CAP-1..CAP-4).

**Value delivered.** Atlas answers the org-specific question public crawls structurally
cannot: what THIS organization pulls from ITS OWN Artifactory, and which pulls have no
public counterpart at all — built mock-first against an injectable transport (the proven
`LaSuiteClient` shape), with NO live instance named or contacted anywhere in scope, code,
config, or tests; live bring-up is a separate, later, attended step outside this epic.

### Story 14.1: Injectable AQL adapter (CAP-1)
**Effort:** M • **Deps:** — • **Status:** done
**Given** a mock AQL transport serving canned topology + download responses **When** the
adapter runs **Then** it resolves virtual-repo topology to the backing repositories and
returns name+version-aggregated download rows **And** constructing it without a transport
fails loudly (no network default), no test path opens a live connection, and credentials
route only through `_http.py`'s existing truststore + JFrog chain — never a second
bespoke credential path.

### Story 14.2: Identity join and internal flag (CAP-2, CAP-3)
**Effort:** M • **Deps:** S-15.1 • **Status:** done
**Given** adapter rows for a public package and a mock-only package **When** they join
into the SAME identity space Phase C/C.5 maintain (parselmouth's
`compressed_mapping.json` + atlas's source-URL extension) **Then** the public package
resolves to the identical identity row Phase C/C.5 would produce — no new PyPI-metadata
or conda-forge-crossref fetch path in the diff **And** exactly the mock-only package
carries the queryable internal/private flag; identity is enriched, never forked.

### Story 14.3: Kedro pipeline surfacing (CAP-4)
**Effort:** S • **Deps:** S-15.2 • **Status:** done
**Given** the adapter + join **When** the work registers as a new atlas Kedro pipeline
following the established phase conventions (per-phase caching, env-var concurrency
knobs, structured logging — `atlas-phase-engineering.md`) **Then** its rows land in the
atlas DB and export in `export-purls`-shaped form consumable by the existing export
surface without a bespoke reader **And** no parallel report format is introduced.

---

## Epic 15: Wagtail corporate brain — the narrow DW-H3 contract

Decomposes **`spec-wagtail-corporate-brain`**
(`planning-artifacts/specs/spec-wagtail-corporate-brain/SPEC.md`, CAP-1..CAP-3).

**Value delivered.** The shipped `LaSuiteClient`/`WikiSyncer` (Story 9.3) stops waiting
on an improvised server: the minimal live Wagtail/La Suite instance is DEFINED against
the client's frozen contract and rehearsed locally, so the separately-scheduled ATTENDED
bring-up (deferred-work ledger DW-H3) runs against a contract instead of improvising one.
The attended event itself is explicitly OUT of the loop's scope — these stories build
everything up to it; DW-H3 flips to closed only when that session later runs and passes,
citing the spec. `factory/lasuite.py` stays a read-only contract surface throughout
(AC-2: no HTTP client enters package code).

### Story 15.1: Instance deploy definition (CAP-1)
**Effort:** M • **Deps:** none (consumes Steward's deploy/credential verbs as the mechanism — Charter §5; atlas grows no deploy code) • **Status:** done
**Given** `LaSuiteClient`'s frozen REST contract **When** the minimal-instance deploy
definition lands (the substrate and DW-H1/SQLite open questions resolved in this story's
spec) **Then** it specifies Bearer-token auth plus the four routes the client calls —
`POST /api/v1/documents/` (2xx body MUST carry `id`), `PATCH /api/v1/documents/{id}/`,
`GET /api/v1/documents/{id}/`, `GET /api/v1/documents/all/` — per the shapes
`MockWagtail` encodes, with `resolve_lasuite_config()` returning a config once
`LASUITE_BASE_URL` + `LASUITE_API_TOKEN` are exported **And** the definition is
air-gap-deployable: mirrored indexes only, admin/site static assets served locally with
zero CDN references, endpoint + token via env/secret-mount — never a committed
credential.

### Story 15.2: Httpx opener and rehearsal (CAP-2, CAP-3)
**Effort:** M • **Deps:** S-16.1 • **Status:** done
**Given** a locally-stood-up instance per the S-16.1 definition **When** a real
httpx-backed `Opener` — constructed OUTSIDE package code (a bring-up script / the C1
Dagster resource) — replaces `_unconfigured_opener` at the module's sole network seam
**Then** `WikiSyncer.sync_all()` rehearses the mock-proven four-step sequence (first push
CREATEs every `outputs/` page; unchanged re-push makes NO remote call; a changed page
yields exactly ONE update; a fresh syncer resumes from `.lasuite_sync.json`) with ZERO
edits to `factory/lasuite.py` and the no-inline-IO gate green **And** that same sequence
is recorded as the attended session's acceptance checklist (per the spec's verification-
home open question) — executing the ATTENDED live bring-up stays out of scope.


## Epic 16: The packaging-inventory intake engine, governed

**Spec binding.** Decomposes `spec-conda-forge-packaging-inventory-operations` CAP-1..2 —
chartering the quartet (runner/prompt/config/replay) that already runs allowlisted in
scripts/+conf/; the allowlist's own delete-when-specced rule executes at 17.1.

### Story 16.1: The from-scratch run is a chartered capability
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-conda-forge-packaging-inventory-operations CAP-1 • **Status:** done
**Given** a clean workspace **Then** the quartet regenerates the full inventory from the
workbook + live indexes + curated feeds (Master Prompt v3.0 bound): PEP-503 identity +
provenance + timestamped verify per package, inspectable P1–P10/Score ranking, dated
append-only identity tabs, gist id via env — and the spec's `surface:` claims the quartet
with the allowlist lines DELETED. The parselmouth fold-placement question resolves here
with a dated entry.

### Story 16.2: Handoffs are execution-ready
**Type:** feature • **Effort:** M • **Deps:** S-17.1 • **FR/AD:** spec-conda-forge-packaging-inventory-operations CAP-2 • **Status:** done
**Given** a completed run **Then** the OpenTeams universe emits one `[Conda-Forge
Packaging] {name}` issue per library + the dated Mason handoff tab (four dispositions),
the AOSS-Free extra queue never expands the universe, and the three dashboard views render
from the live identity tab — Mason consumes a tab without questions.

---

## Canopy obligations (2026-08-24)

Recorded by `sprint-change-proposal-2026-08-24-canopy.md` (Phase 5,
`docs/dreams/pyforge-unifying-strategy.md`). Atlas Epics 1–17 are **complete**; steward
Epics 18–30 own Canopy implementation on `src/platform/`. **No Epic 18 here** — atlas must
not copy steward stories.

1. **`lane1-serves-dw-h3` — answered 2026-08-25: no.** Epic 16
   (`spec-wagtail-corporate-brain`) and the frozen `LaSuiteClient` REST contract
   (`POST /api/v1/documents/`, `PATCH /api/v1/documents/{id}/`, `GET /api/v1/documents/{id}/`,
   `GET /api/v1/documents/all/`) define atlas's narrow DW-H3 bring-up contract. They are **not**
   Wagtail's own admin/API surface (`/cms/` on the host). Canopy Lane 1 does **not** absorb or
   re-mint `spec-wagtail-corporate-brain` and does **not** satisfy DW-H3. DW-H3 remains open
   until the attended bring-up of a server that speaks that REST contract runs.

2. **MCP — mount, do not duplicate.** Atlas already ships `build_server()` (Story 3.3). Steward
   Story **21.2** (*Atlas MCP on the host, dual-era*) brings that face onto the host ASGI at
   `POST /stations/atlas/mcp` using the official `mcp` SDK and dual-era revisions
   `2025-03-26`–`2026-07-28`. Atlas does **not** build a second MCP server or a parallel public
   port.

3. **CAP-7 boards — steward dashboard only on the host.** Analytical boards mounted behind the
   Canopy host consume **`pyforge.steward.dashboard`** (filter-then-search, steward Epic 23).
   Atlas adopting that pattern for its own **Vizro CLI** boards (`dashboard/` module, Story 5.2)
   is a **non-goal**. Vizro stays **outside** the host; Epic 14 query views follow their own
   ASGI contract and are not re-scoped here.

4. **BS-5 DuckDB — cooperate, do not duplicate steward Story 25.2.** Single-writer discipline and
   `read_only=True` on atlas read paths are **atlas-local** (DuckDB consolidation, Epic 7).
   Steward Story **25.2** (*One DuckDB writer*) implements the **absence-test** gate on the estate.
   Atlas records cooperation with that gate; it does **not** add a duplicate steward story.

5. **Five-tier symmetry.** Atlas already satisfies **Tier 1 (CLI)**. Steward Epics **19**
   (empty portal shell) and **21** (hosted MCP face) stay steward. **Skill, persona, and the
   first real portal job are atlas Epic 19** (2026-08-25) — not steward 29 and not a copy of
   Canopy 18–30. Atlas must **not** grow a second chrome layer, duplicate `django-pyforge`
   registration, or expose an extra public port. DW-H3 / La Suite REST is **not** this epic.

## Operating-model obligations (2026-08-24)

Estate-wide bind from Unifying Strategy Grounding (hooks/plugins principle + Q1–Q8)
and steward `sprint-change-proposal-2026-08-24-operating-model.md` (**§6 revisited**).
**Hooks and plugins (canopy:AD-21):** as far as possible every layer is replaceable —
the process owns hook specifications; a plugin implements or replaces a layer without
a fork. Kedro
[architecture overview](https://docs.kedro.org/en/stable/getting-started/architecture_overview/)
*names* the split; it does not require this station to be a Kedro project. Warden owns
PR-gate hook specs (Q8). This station owns its process hooks.

**Always / Never (every station):**
- Five-tier completeness is the **03** shape. 01/02 stay spec+script or spec+skill.
- Guildhall / switcher must not tile `work_class` 01 or 02 as a station.
- Golden Path: humans, CI, and agents invoke the same Pixi task names.
- CloudEvents: `spec_id` + git sha + SBOM purl; Jira optional; never fail for a missing key.
- Path B = Agent Canopy + this station's persona. Tachyon = production LLM provider adapter.
- Lane 2 = HTMX; station compute = FastAPI. No station-local DRF JSON:API on the portal.
- Design station processes as hook specs + plugins (AD-21). Do not fork a process to swap a vendor.
- **Never** a competing PR quality-gate verdict. Quality scanners register as **Warden plugins**.
- Scorecard measures are unpublished (human + agent + team; draft later). Do not optimize to invented metrics.

**Atlas-local:** Atlas already *is* a Kedro project. Pipeline/project hooks are the **reference** for the spec-vs-plugin split. Story **18.1** audits them against steward S-32.1. They are not Warden's PR-gate hook book and must not publish a competing PR pass/fail. DRF JSON:API stays on the enterprise-data-models kinship only. Vizro stays Lane 3 / outside host as already bound.

**Pointers:** `change-history/sprint-change-proposal-2026-08-24-operating-model.md`;
`change-history/sprint-change-proposal-2026-08-24-hook-specs.md`;
steward `sprint-change-proposal-2026-08-24-hook-specs.md`; `DW-OM-2026-08-24`;
`change-history/sprint-change-proposal-2026-08-25-station-skill-portal.md`.

## Epic 17: Kedro hooks on the shared contract

Audit, do not rebuild. Atlas is already Kedro. **FR-45.** Deps: steward S-32.1.

### Story 17.1: Map existing Kedro hooks to CAP-18

As an atlas maintainer,
I want existing pipeline/project hooks to implement the shared registration shape,
So that atlas does not grow a second plugin API or a pipeline PR-gate.

**Type:** chore • **Effort:** M • **Deps:** steward S-32.1 • **FR/AD:** FR-45 • canopy:AD-21
**Given** the live Kedro hook surfaces **When** the audit completes **Then** each named point is mapped to the FR-43 contract (or an explicit N/A with reason)
**And** today's backends remain the default plugins
**And** no atlas job publishes a PR pass/fail beside Warden

## Epic 18: Atlas owns its skill, persona, and one portal job

Steward 19/21 shipped the empty `/stations/atlas/` shell and host MCP. Steward 29 proved SKF+persona *shape*. This epic does **not** copy Canopy 18–30. Not DW-H3. Not Vizro on the host.

### Story 18.1: SKF domain skill and BMAD persona for atlas

As an autonomous agent,
I want an atlas SKF skill from `pyforge-atlas/` and a `bmad-agent-atlas` persona,
So that Path B uses CAP-5 grammar and CAP-4 MCP only.

**Type:** feature • **Effort:** L • **Deps:** S-18.1 • **FR/AD:** canopy FR-37, FR-38 • canopy:AD-17
**Given** steward 29.1 compiled the shape on another station **When** this story completes **Then** SKF compiles from `src/shared/packages/pyforge-atlas/` if missing
**And** the persona uses only `pyforge atlas …` and `POST /stations/atlas/mcp`
**And** `conda-forge-expert` is not replaced

### Story 18.2: First portal slice — one inventory/run row

As an atlas operator,
I want HTMX on `/stations/atlas/` to show one factory inventory or run-state row,
So that Lane 2 does a real job without Vizro or La Suite.

**Type:** feature • **Effort:** M • **Deps:** S-19.1 • **FR/AD:** canopy FR-10 • canopy:AD-7
**Given** an authenticated atlas-role session **When** the operator opens `/stations/atlas/` **Then** one row renders via PortalClient only
**And** no raw HTTP, no `pyforge.*` under `src/platform/`, no chrome copy, no DW-H3 REST

---

## Epic 19: The query plane meets the query surfaces

Decomposes **`spec-atlas-query-dashboards`**
(`planning-artifacts/specs/spec-atlas-query-dashboards/SPEC.md`) **CAP-5..CAP-7** — the
2026-08-27 extension minted from the three operator rulings dated 2026-08-26 in the steward
strategy SPEC § Open Questions (`query-plane-face`: both faces, one boot script, parity part
of done; `query-plane-catalog`: named new pipeline as the opt-in optimization layer, closed
seven sealed; `query-plane-scribe-cutover`: dual-write — covered by steward 34.5, no atlas
story owed). CAP-1..CAP-4 shipped as Epic 14 and are untouched here.

**Fenced off (no double-mint).** The CAP-19 engine's first slice — steward 34.1–34.5 plus
Lane 3 36.1–36.2 — shipped 2026-08-26 on the STEWARD chain (see this file's 2026-08-26
validation note); this epic owns only the atlas-side query-surface residue: the boot script,
the face-parity gate, the composed-dashboard-store derivation, the CIS two-spine specs, and
the remaining 19 Vizro pages (adopting the DW-D2-1/2/3 residue, which had ledger entries but
no story home for dispatch).

### Story 19.1: One boot script raises both plane faces (CAP-5)
**Effort:** M • **Deps:** — • **Status:** done
**Given** the shipped CAP-19 engine (steward 34.1–34.5) **When** the single pixi-sourced boot
script runs **Then** the in-process library face is available by default (AD-16 local-first;
DuckDB stays a query face, never a fourth backing store) **And** the Mosaic `duckdb-server`
HTTP/Arrow face is raised by the SAME script only when the platform stack is up — with the
stack down it degrades to library-face-only with a structured notice, never a crash **And**
no second boot path exists (grep-verifiable: exactly one `duckdb-server` launch site)
(`query-plane-face` ruling, 2026-08-26).

### Story 19.2: Face parity is part of done (CAP-5)
**Effort:** S • **Deps:** S-20.1 • **Status:** done
**Given** both faces up on fixture data **When** the parity gate runs an identical query set
against the library face and the HTTP/Arrow face **Then** results agree row-for-row **And** a
seeded divergence fails the gate (proven in-test) **And** filesystem-less consumers bind to
the HTTP face per CAP-19's success wording ("the plane DSN or HTTP face") — parity is part of
the face's definition of done per the `query-plane-face` ruling (2026-08-26); the gate is
offline-safe.

### Story 19.3: Named-pipeline derivation of the dashboard stores (CAP-6)
**Effort:** M • **Deps:** — • **Status:** done
**Given** the sealed seven pipelines' canonical outputs **When** the NAMED downstream plane
pipeline runs (one `kedro run --pipeline <named>`) **Then** the composed semantic stores the
grounded dashboard pages bind to (DW-D2-2's `semantic_packages` family plus the
`core_feedstock_health` Parquet the 2026-08-26 first visual pass found absent in a fresh
checkout) are materialized **And** zero diff lands inside the sealed seven and no silent
`01_raw` tree appears (`query-plane-catalog` ruling, 2026-08-26) **And** consumers keep the
per-call choice — canonical datasets direct, or the plane as the fast path **And**
`dashboard/data.py`'s "BSL-wired SHELL pages" banner retires, with DW-D2-2 closed citing this
story.

### Story 19.4: The CIS two-spine specs exist (CAP-7)
**Effort:** M • **Deps:** — • **Status:** done
**Given** DW-D2-1 — checked 2026-08-27: the CIS DESIGN/EXPERIENCE gap STILL BLOCKS (the
`DESIGN.md` + `EXPERIENCE.md` spine specs were never produced; no evidence-update since the
2026-07-30 verification) **When** the CIS Carson/Maya planning pass runs **Then** both spine
files land under `planning-artifacts/` covering every one of the 19 unshipped pages **And**
DW-D2-1's close cites them **And** until this story lands, S-20.5 must not expand the page
set past the live-confirmed core.

### Story 19.5: Port the remaining nineteen Vizro pages (CAP-7)
**Effort:** L • **Deps:** S-20.3, S-20.4 • **Status:** done
**Given** the two-spine specs (S-20.4 — this story is GATED: the DW-D2-1 CIS gap still blocks
as of 2026-08-27) and the materialized stores (S-20.3) **When** the remaining 19 of 28 CLI
pages port against the spines — BSL-routed, reading canonical datasets or the plane per the
`query-plane-catalog` ruling's per-call choice **Then** all 28 pages render with stable
ids/titles **And** the DW-D2-3 residual executes: the §2.1 semantic-HTML/ARIA browser-agent
navigation check plus a data-present visual pass through
`pixi run -e local-recipes dashboard-serve` (`scripts/dashboard_serve.py`, the DW-D2-3
serve entrypoint, evidence-update 2026-08-26) **And** Vizro stays outside the Canopy host
(this file's Canopy obligation 3) and Django imports no Vizro.

---

## Epic 20: Kedro catalog expansion — self-contained inventory data plane

**Spec binding.** Decomposes `spec-atlas-kedro-catalog-expansion` CAP-1..4 (+ optional CAP-5..6) —
`docs/dreams/atlas-kedro-catalog-expansion.md`. Makes pyforge-atlas bootstrap and materialize
the public index + identity export Parquet the inventory quartet consumes via `--live-catalog`,
without `cf_atlas.db` on the Kedro path. **Renumbered 2026-08-29** from draft Epic 18 to avoid
collision with Epic 18 (Kedro hooks) in this file.

### Story 20.1: Relocate atlas data defaults and add pyforge-atlas-bootstrap
**Type:** feature • **Effort:** M • **Deps:** — • **Status:** done
**Given** an empty `PYFORGE_ATLAS_DATA_ROOT` **When** `pixi run pyforge-atlas-bootstrap` runs
**Then** `globals.yml` store paths resolve under `${paths.data_root}/stores/` (not
`.claude/data/conda-forge-expert/`) **And** the documented operator env block ships with the
pixi task **And** bootstrap smoke passes on an empty data root (Phase A only — SQLite seeds
unchanged).

### Story 20.2: Remove cf_atlas.db seeds from production datasets
**Type:** feature • **Effort:** L • **Deps:** S-21.1 • **Status:** done
**Given** no `CF_ATLAS_DB` on the Kedro path **When** production datasets load **Then** no
dataset defaults to `cf_atlas.db`; `parity-diff` passes.

### Story 20.3: Tier 0 harden and `--live-catalog` contract
**Type:** feature • **Effort:** M • **Deps:** S-21.2 • **Status:** done
**Given** Tier 0 Parquet materialized **When** `metrics.py --live-catalog` runs **Then**
verification BOOLs read Parquet only; scale gates pass. *(Landed PR #941, 2026-08-30. Scope
is exactly the three Tier 0 verification sets; the package universe still comes from
`--analysis-xlsx` until Story 23.8 — see the 2026-08-30 course-correction note below.)*

### Story 20.4: Tier 1 catalog sources (SelfExplainML, Anaconda, Basilisk, AOSS)
**Type:** feature • **Effort:** L • **Deps:** S-21.3 • **Status:** done
**Given** bootstrap **When** Tier 1 datasets fetch **Then** all Tier 1 entries in
`catalog-sources.md` are live in `catalog.yml` with smoke floors.

### Story 20.5: Tier 2 sources (about, curated orgs, Artifactory names)
**Type:** feature • **Effort:** M • **Deps:** S-21.4 • **Status:** done
**Given** attended creds when live fetch enabled **When** Tier 2 runs **Then** CDO universe
names come from catalog Parquet (telemetry deferred to Epic 23).

### Story 20.6: upstream_discovery identity join and export Parquet
**Type:** feature • **Effort:** L • **Deps:** S-21.5 • **Status:** done
**Given** associator + board fixtures **When** Phase D runs **Then** `identity_export_parquet`
matches today's join parity.

### Story 20.7: Quartet thin-out and gist wrapper
**Type:** feature • **Effort:** M • **Deps:** S-21.6 • **Status:** done
**Given** identity export Parquet **When** `--gist-only` runs **Then** inventory scripts delegate
join to Atlas; Epic 17 purl-associator constraint superseded with memlog.

### Story 20.8: End-to-end verification gate
**Type:** feature • **Effort:** M • **Deps:** S-21.7 • **Status:** done
**Given** no legacy DB on Kedro path **When** full bootstrap + `--live-catalog` **Then**
`parity-diff` and `bsl-metric-check` pass — Epic 21 success signal.

### Story 20.9: Vizro bootstrap health pages (optional, CAP-5)
**Type:** feature • **Effort:** M • **Deps:** S-21.8 • **Status:** done • **Optional:** yes
**Given** post-bootstrap Parquet **When** `dashboard-serve` **Then** three BSL health pages
render non-empty tables.

### Story 20.10: Kedro-Viz CI path sync (optional, CAP-6)
**Type:** chore • **Effort:** S • **Deps:** S-21.8 • **Status:** done • **Optional:** yes
**Given** a catalog-only PR **When** merged to main **Then** `kedro-viz-publish.yml` republishes
the static DAG export.

---

## Epic 21: Vizro parity with identity canvases

**Spec binding.** `spec-atlas-kedro-catalog-expansion` CAP-7 — parallel browser replacement for
the three Cursor Canvas identity views; deferred from Epic 21 for scope, not capability.
**Renumbered 2026-08-29** from draft Epic 19.

### Story 21.1: Ranked export bridge (quartet → Vizro feed)
**Type:** feature • **Effort:** S • **Deps:** S-21.8 • **Status:** done
**Given** `priority.py` on identity export **When** bridge runs **Then**
`identity_ranked_export.parquet` feeds Vizro until Epic 23.5 supersedes.

### Story 21.2: Vizro `identity-catalog` page
**Type:** feature • **Effort:** M • **Deps:** S-22.1 • **Status:** done • **Optional:** yes
**Given** ranked export **When** page loads **Then** row counts match catalog canvas fixture.

### Story 21.3: Vizro `identity-ops` page
**Type:** feature • **Effort:** M • **Deps:** S-22.1 • **Status:** done • **Optional:** yes
**Given** ranked export **When** four panes render **Then** pane totals match ops canvas fixture.

### Story 21.4: Vizro `identity-workbook` page
**Type:** feature • **Effort:** M • **Deps:** S-22.1 • **Status:** done • **Optional:** yes
**Given** enterprise Parquet absent or present **When** page loads **Then** honest shell or full
workbook parity respectively.

### Story 21.5: Canvas vs Vizro parity gate
**Type:** feature • **Effort:** M • **Deps:** S-22.2, S-22.3 • **Status:** done • **Optional:** yes
**Given** shared fixture **When** `dashboard-dryrun` parity test runs **Then** Vizro matches
canvas DATA aggregates.

### Story 21.6: Canvas deprecation switch
**Type:** chore • **Effort:** S • **Deps:** S-22.5 • **Status:** done • **Optional:** yes
**Given** parity gate green **When** `INVENTORY_IDENTITY_UI=vizro|canvas|both` **Then** default
`both` until operator opts into vizro-only.

---

## Epic 22: Complete inventory export — zero deferred

**Spec binding.** `spec-atlas-kedro-catalog-expansion` CAP-8 — closes
`docs/dreams/atlas-kedro-catalog-expansion.md` with `identity_complete_export.parquet` and
`enterprise_jfrog_consumption.parquet` per `complete-export-contract.md`.
**Renumbered 2026-08-29** from draft Epic 20.

### Story 22.1: Tier 3 bulk OS indexes
**Type:** feature • **Effort:** M • **Deps:** S-21.4 • **Status:** done
**Given** bootstrap **When** Tier 3 fetches run **Then** homebrew/nixpkgs/spack/debian/fedora
BOOLs land on verification export.

### Story 22.2: Enterprise JFROG consumption Parquet
**Type:** feature • **Effort:** L • **Deps:** S-21.5, Epic 15 • **Status:** done
**Given** mock or attended Artifactory transport **When** rollup runs **Then**
`enterprise_jfrog_consumption.parquet` matches §1 column contract on fixture.

### Story 22.3: Priority rules in Kedro (`inventory_priority_assignments`)
**Type:** feature • **Effort:** L • **Deps:** S-21.6, S-23.2 • **Status:** done
**Given** frozen priority fixture **When** Kedro node runs **Then** P/Score/Work parity vs
`priority.py`.

### Story 22.4: Deliverable A + `Packaging_Candidate_Status`
**Type:** feature • **Effort:** M • **Deps:** S-21.3, S-23.3, S-23.8 • **Status:** done
**Given** verification + priority Parquet **And** `inventory_universe` (S-23.8) as the row
grain **When** derived export writes **Then** `inventory_verified_packages.parquet` has exact
14-column order at the full-inventory grain (~38k rows), not the OpenTeams-universe grain.

### Story 22.5: `identity_complete_export.parquet` (canonical)
**Type:** feature • **Effort:** L • **Deps:** S-23.3, S-23.4 • **Status:** done
**Given** identity + priority + enterprise joins **When** export materializes **Then** full
GIST_SCHEMA + handoff columns; supersedes Story 22.1 bridge.

### Story 22.6: BSL gist aggregates (CAP-8d)
**Type:** feature • **Effort:** M • **Deps:** S-23.5 • **Status:** done
**Given** complete export **When** BSL renders gist markdown **Then** parity vs today's gist
files on fixture; `gh gist edit` is thin actuator only.

### Story 22.7: Zero-deferred E2E gate
**Type:** feature • **Effort:** M • **Deps:** S-23.5, S-23.6, S-23.8, S-23.9 • **Status:** done
**Given** no workbook ingest — by the bootstrap **and** by the quartet (`openpyxl` absent
from `scripts/`) **When** bootstrap + Vizro + gist **Then** quartet data logic retired; dream
fully closed.

### Story 22.8: Workbook-free metrics universe (Kedro `inventory_universe` + `--analysis-xlsx` optional)
**Type:** feature • **Effort:** L • **Deps:** S-21.4, S-21.5 • **Status:** done
**Given** Tier 0–2 Parquet + the OpenTeams board dataset **When** `derived_artifacts` runs
**Then** `inventory_universe.parquet` holds one row per PEP-503 name with the workbook's
provenance labels, `role`, and `openteams_universe_member` **And** `metrics.py --live-catalog`
without `--analysis-xlsx` produces CSV/MD identical to the workbook run on a fixture (the
`10kClosed`-only rows are the one reported delta). *(Minted 2026-08-30 course correction.)*

### Story 22.9: Quartet workbook retirement (thin actuators, no `openpyxl` in `scripts/`)
**Type:** feature • **Effort:** L • **Deps:** S-23.4, S-23.5, S-23.6, S-23.8, S-22.1 • **Status:** done
**Given** the Atlas exports **When** the four quartet scripts run **Then** identity/priority/
dashboards/metrics read only Parquet (`identity_complete_export`, `inventory_priority_assignments`,
`enterprise_jfrog_consumption`, `inventory_verified_packages`), every workbook flag refuses with
a pointer, and `grep openpyxl|load_workbook|XlsxReader scripts/` is empty. *(Minted 2026-08-30
course correction.)*

---

## Epic 23: Atlas builds its MCP face with `mcp-builder`

**Spec binding.** The atlas-side relay of `spec-bmad-suite-lifecycle` (Dream
`docs/dreams/bmad-suite-lifecycle.md`, 2026-09-06): labs' `mcp-builder` (CAP-6) for the atlas MCP
face (`POST /stations/atlas/mcp`, spec-21-4). **HARD boundaries:** installed by name under consent
(steward 46.5), never the marketplace; the face's contract stays `pyforge atlas …` grammar
(lifecycle spine AD-1, AD-2).

### Story 23.1: `mcp-builder` is atlas-wielded for the MCP face
**Type:** docs • **Effort:** XS • **Deps:** — (after steward 46.5 — cross-station: ledger `blocked`, AD-10) • **FR/AD:** spec-bmad-suite-lifecycle CAP-6 • AD-2 • spec-21-4 (MCP faces)
**Surface:** `.claude/skills/bmad-agent-atlas/SKILL.md` (routing line), the register § 2 row (one AGENTS.md pointer line only, AD-2/AD-11), `adoption-register.md` § 2 row
**Given** the labs skill installed by name **When** the atlas persona routes new MCP tool scaffolding to `mcp-builder` with the constraint that generated tools call `pyforge atlas …` verbs only **Then** the register names atlas as sole wielder, the routing line states the grammar constraint, and CLAUDE.md is untouched

---

## Epic 24: Turn on what is built — atlas's realization-gate effect stories

**Spec binding.** Atlas's satellite of the fleet realization gate — operator decision batch
`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`
§ 2.3 **C6**: "effect stories on the **owning station's** epics … atlas, herald, mason, scribe each
a small epic", with steward Epic 49 carrying only an index row per station. Each story here closes
the gap between "the epic reads `done`" and "the named success criterion is exercised in the
running estate" — the marshal-token-economy shape. Epics 14 and 23 are both closed, so these land
in a new epic rather than reopening a completed one (Epic 11 never existed, by design; 25 is the
next free number). **Effect test, per steward Story 49.2:** *does it have a caller outside its own
test file?*

### Story 24.1: Retire the second Lane-3 runtime
**Type:** code • **Effort:** S • **Deps:** — • **FR/AD:** `spec-atlas-query-dashboards` CAP-1..CAP-4 (superseded) • decision batch § 2.3 C1 / row atlas-B1
**Surface:** `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/` (delete), `src/shared/packages/pyforge-atlas/tests/unit/views/` (delete), `src/shared/packages/pyforge-atlas/tests/unit/catalog/test_no_inline_io.py` (the Story 14.3 ASGI-containment test and its positive control both name `views/asgi.py`), `src/shared/packages/pyforge-atlas/pyproject.toml` (`bokeh`/`tornado`/`starlette` run-deps, declared for `views/` only), `src/shared/packages/pyforge-atlas/pixi.toml` (the mirrored AUD-ATLAS-010 run-dependency lines)
**Given** the `views/` package has **no importer anywhere outside `tests/unit/views/`** — no CLI verb, no pixi task, no ASGI mount, even though `views/__init__.py:10-13` describes `asgi.py::app` as a mount target — and it reaches the legacy SQLite `cf_atlas.db` through `views/cli_bridge.py`, whose own docstring (`:11-17`) records that its dynamic-import shape keeps the F1 DuckDB-singularity gate green *while the loaded script imports `sqlite3`* — a private, non-BSL read against the CAP-19 ruling "no private DuckDB … BSL is the dashboard/agent SQL contract" and against `spec-pyforge-atlas`'s own Non-goal "Continued SQLite"
**When** the package and its unit-test directory are deleted, the `test_no_inline_io.py` assertions that exist only to fence `views/asgi.py` go with them, and the run-dependencies declared solely for this module (`bokeh`, `tornado`, `starlette` — verified to have zero other importer in `src/`, `tests/` or `tools/`) are dropped from **both** `pyproject.toml` and the member `pixi.toml`, kept byte-for-byte in step per AUD-ATLAS-010
**Then** `grep -rn "atlas\.views"` across the repo returns nothing, `pixi run -e local-recipes dashboard-dryrun` stays green, `pixi run -e pyforge-atlas pyforge-atlas-test` stays green, and the F1 singularity gate is green **with no dynamic-import evasion left in the tree to keep it that way**
**And** the supersession is recorded, not merely performed: `spec-atlas-query-dashboards` notes CAP-1..CAP-4 superseded by the live Vizro/BSL board and moves `in-progress` → `shipped` on the strength of CAP-5..CAP-7; atlas ledger entries `DW-14-2-1` and `DW-14-3-2` close citing this story; the Dream (`docs/dreams/atlas-query-dashboards.md`, already `archived` / `archived-reason: retired`) keeps the narrative record
**And** nothing is resurrected on the way out: the pluggable-widget-registry idea is re-introduced only if a Vizro page actually asks for it, and `httpx` stays declared in the root `pixi.toml` — it is named there as *also* required by Story 16.2's `tools/lasuite_bringup.py`, so pruning the starlette test must not take it.
**And** the page-count literals the same surfaces carry are made current on the way through: `PAGE_INVENTORY` in `dashboard/app.py` holds **34** `PageDef` entries (Epic 22's three identity pages), while `app.py:13`'s docstring says 28 and the root `pixi.toml:1065` / `:1070` task descriptions say 31 — the literals are replaced by the measured count (or by wording that does not quote a number), closing the page-count open question `spec-pyforge-atlas` raised on 2026-09-09 (fleet readiness re-derive; chain-currency runbook § overtaken)

### Story 24.2: Materialize CAP-8's canonical Parquets — one recorded run
**Type:** ops • **Effort:** M • **Deps:** — (ATTENDED; ledger status `blocked` on the credentialed path) • **FR/AD:** `spec-atlas-kedro-catalog-expansion` CAP-8 • decision batch § 2.2 row atlas-B5 + § 2.3 C6
**Surface:** the `derived_artifacts` / `artifactory_downloads` pipelines and `conf/base/catalog.yml` (`identity_complete_export` `:987-989`, `enterprise_jfrog_consumption` `:1301-1303` — read, not edited), a tracked run record under `planning-artifacts/`, `docs/dreams/atlas-kedro-catalog-expansion.md` (status), atlas `deferred-work-ledger.md` (`DW-FU-23-5`, `DW-D2-3`)
**Given** Epics 21, 22 and 23 are 100% `done` and the catalog **declares** both canonical exports — and a declared Kedro dataset is a contract, not data
**When** an attended operator runs the pipelines end to end against live sources with the Artifactory credentials configured, and records the run as a tracked artifact (command line, dataset paths, row counts, date)
**Then** `identity_complete_export.parquet` and `enterprise_jfrog_consumption.parquet` both exist with non-zero rows, the run record is cited from the Dream's Realization log, and `docs/dreams/atlas-kedro-catalog-expansion.md` moves `specified` → `realized` **in the same commit that records the run**
**And** `DW-FU-23-5` closes citing this story, and `DW-D2-3`'s open residual — the data-present visual pass — is taken in the same attended session, because this run is precisely its missing precondition
**And** no gate is weakened and no row is fabricated to reach a green: honest-empty stays honest, and if the credentialed path is unavailable the story stays `blocked` rather than declaring success
**Cross-station note** *(prose, deliberately NOT a cross-project `Deps:` token)*: the attended, credentialed Artifactory path this story needs is the **same event** `spec-conda-forge-packaging-inventory-operations` holds itself `in-progress` for ("CAP-2 (17.2) code landed, live-execution verification deferred (attended, credentialed run pending)"). One precondition, two Specs — they must not disagree about whether it has been met.

### Story 24.3: Atlas's MCP tools pass the CLI⇄tool parity gate
**Type:** code • **Effort:** M • **Deps:** — • **FR/AD:** marshal Story 18.2 / FR-155 (the primitive) • decision batch § 2.3 C10 / marshal-A finding E6
**Surface:** `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/tools.py`, a new `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/parity.py`, `src/shared/packages/pyforge-atlas/tests/meta/test_cli_tool_parity.py`, `src/shared/packages/pyforge-atlas/src/pyforge/atlas/__main__.py` (verb *enumeration* only — Kedro's routing is not reimplemented)
**Given** CLI⇄tool parity is enforced today for **marshal alone** — `pyforge/marshal/mcp/parity.py` and its gated meta-test `tests/meta/test_cli_tool_parity.py` (Story 18.2, FR-155: "drift fails the gated meta-test; review is not the gate") — while atlas's six tools (`run_pipeline`, `read_dataset`, `query_vizro_ai`, `query_trending_candidates`, `list_pipelines`, `list_datasets`) are asserted against nothing
**And given** atlas is the one station the unified front door cannot AST-introspect — `pyforge.core.dispatch.PREPARATORY_UNINTROSPECTABLE["atlas"]` points at `spec-22-prep-atlas-kedro-cli-introspection`, whose own Approach reads "a later story must generate the CAP-5 parity matrix for atlas verbs from Kedro's own command surface, still without reimplementing pipelines in core" — **this is that story**, and that preparatory spec (steward tree, `status: ready`) has never been minted as a ledger key
**When** the marshal primitive's *shape* is extended over atlas — an atlas-side `parity.py` declaring the same four contracts (every tool claiming a verb maps to a real verb; every verb declared on-surface has at least one tool; `cli: None` tools are declared tool-only helpers; the CLI-only allowlist may not go stale) — with atlas's verb inventory derived from **Kedro's own command surface at runtime**, never from a copied Click group and never from a hand-typed list
**Then** `pixi run -e pyforge-atlas pyforge-atlas-test` runs a gated `tests/meta/test_cli_tool_parity.py` that fails on injected drift in **both** directions, the live inventory passes clean, and every allowlisted CLI-only verb carries the sentence saying why — an allowlist is a declaration with a reason, never a way to reach green
**And** the `PREPARATORY_UNINTROSPECTABLE["atlas"]` entry is re-pointed at this story or removed; a silent skip stays forbidden. That one line lives in `pyforge-core` (`core/dispatch.py:29`), which is **steward's** surface — so it is either split into a steward story or recorded in steward's memlog **before** the edit lands, otherwise `spec-surface-check` reds at merge (the doctor-B8 foreign-surface hazard)
**Cross-station note** *(prose, deliberately NOT a cross-project `Deps:` token)*: C10's other half — the **46 conda-forge-expert MCP tools** — is **mason's**, not atlas's. This story does not widen to it, and nothing here changes the ruling that the HTTP station face (`POST /stations/atlas/mcp`) is the governed front door with stdio servers as local adapters.

### Story 24.4: A live Artifactory transport exists for the attended operator to plug in
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** unblocks Story 24.2's credentialed path • operator request 2026-09-10
**Surface:** `src/shared/packages/pyforge-atlas/tools/live_artifactory_transport.py` (new — NOT inside `src/pyforge/atlas/`, which `tests/unit/catalog/test_no_inline_io.py`'s `IO_DENYLIST` bans `requests`/`urllib3`/`httpx` from anywhere in; `tools/` mirrors the existing `tools/bootstrap.py` sibling-location precedent for attended-operator scripts), `src/shared/packages/pyforge-atlas/tests/tools/test_live_artifactory_transport.py`
**Given** `AqlTransport` (the sole HTTP seam `ArtifactoryAqlAdapter` takes) has only `_unconfigured_transport` wired anywhere in the package — Story 24.2 needs "an attended operator runs the pipelines end to end against live sources with the Artifactory credentials configured," but no live transport implementation exists for that operator to construct, only the injectable seam itself
**When** a new `live_transport(base_url, *, api_key=None, username=None, password=None)` factory is added, resolving auth the SAME way `.claude/skills/conda-forge-expert/scripts/_http.py` already does for JFrog elsewhere in this repo — `JFROG_API_KEY` → `X-JFrog-Art-Api` header, else `JFROG_USERNAME`/`JFROG_PASSWORD` → HTTP Basic — and performing exactly one HTTP round-trip per `AqlRequest`, matching the seam's own documented contract
**Then** the concrete HTTP client stays constructed OUTSIDE package import time (no top-level `requests`/`urllib` call, no credential read at import) — the factory is called explicitly by the attended operator's own run, at run time only
**And** a test suite exercises the factory with a mocked HTTP layer (no real network, no real credentials) covering: API-key auth header, username/password Basic auth, neither-configured raises a clear typed error naming which env var is missing, and one successful request/response round-trip shape
**And** this story does NOT itself run Story 24.2's live pipeline or touch any credential value — it only makes the missing transport exist for that attended, credentialed run to use

---

## Epic 25: Atlas keeps each scanned repo's dependency history (spec-pyforge-atlas CAP-61)

**Spec binding.** Minted 2026-09-28 from the station Dream's entry *Atlas keeps each scanned repo's dependency history,
so a fix knows when a dependency arrived and which other repos carry it* — carried from the Warden Dream's entry of the
same day (the security-scanning intake, whose Phase 2 persisted a `dependency_graphs` table per repo and commit).
Warden's actuator and fleet scan (`spec-pyforge-warden:CAP-24`, `spec-pyforge-warden:CAP-26`) read the history. **HARD boundaries:** Atlas
measures, Warden judges — the dataset carries no verdict, score or threshold; no hook or file is ever written into a
scanned repo; no `sqlite3` import and no `subprocess` import under `src/pyforge/atlas` (AD-4's F1 gate, the no-inline-IO
gate — `git` and `git pkgs` run through `pyforge.core.process`); no webhook; no import of `pyforge.warden` or
`django_warden_fabric`; every story ships behind its flag (`spec-feature-flag-governance:CAP-1`).

### Story 25.1: A per-repo dependency-history dataset from git-pkgs and an estate pixi parser
**Type:** feature • **Effort:** L • **Deps:** — (cross-station: mason Story 21.1 ships the git-pkgs conda package; ledger `blocked` until the operator flips it) • **FR/AD:** spec-pyforge-atlas CAP-61 (FR-69) • AD-2, AD-3, AD-4, AD-5, AD-13
**Flag:** `pyforge.atlas.dependency_history` (OFF: the dataset is not built and the pipeline node skips as `not-applicable`)
**Surface:** `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/` (a new `dependency_history.py` custom dataset: a clone in Atlas's cache, `git pkgs init --no-hooks` with `GIT_PKGS_DB` at a throwaway path, the DuckDB read, the estate pixi parser), `pipelines/vcs_health/` (the node that lands `repo_dependency_history`), `conf/base/catalog.yml`, `conf/base/parameters.yml` (TTL), `tests/unit/datasets/`, `tests/unit/catalog/test_credential_scoping.py` (the GHE host entry), the member `pixi.toml` / `pyproject.toml` and the root `pixi.toml` / `pixi.lock` / `environment.yaml` (the git-pkgs run-dependency range), `src/platform/config/flags.json`
**Given** a fixture git repo whose commits add, bump and remove a dependency in `pyproject.toml` and add one in `pixi.toml`
**When** the `vcs_health` pipeline builds `repo_dependency_history` for it
**Then** there is one row per change — repo, commit SHA, epoch-second commit time, manifest path, ecosystem, name, requirement before and after, and a `source` of `git-pkgs` or `estate-pixi-parser` — in a Parquet partition for that repo
**And** the fixture repo's file listing and `.git/hooks` are unchanged afterwards and no `pkgs.sqlite3` remains anywhere; `test_duckdb_sole_engine.py` and `test_no_inline_io.py` stay green
**And** a repo whose head has not moved is not re-walked (AD-5), and an unreachable repo keeps its last-good partition marked `stale` (AD-13)

### Story 25.2: A poll-cursor sensor refreshes the history over Warden's fleet inventory
**Type:** feature • **Effort:** M • **Deps:** S-25.1 • **FR/AD:** spec-pyforge-atlas CAP-61 (FR-69) • AD-1, AD-6
**Flag:** `pyforge.atlas.dependency_history_sensor` (OFF: the sensor skips every tick with a `flag off` reason)
**Surface:** `src/shared/packages/pyforge-atlas/src/pyforge/atlas/orchestration/` (a dagster-free decision module in `event_source.py`'s shape, wired only in `definitions.py`), `conf/base/catalog.yml` (`warden_fleet_inventory`, a raw JSON dataset over Warden's export path), `tests/unit/orchestration/` (`test_definitions_dryrun.py` and a new decision test), `src/platform/config/flags.json`
**Given** Warden's fleet inventory export as a raw catalog dataset and the per-repo cursor (each repo's default-branch head SHA)
**When** the sensor ticks
**Then** unchanged heads skip with a reason, and moved heads coalesce into one run request for the Story 25.1 job and advance the cursor; the default production source is offline (`[]`) like `offline_event_source`, and no webhook exists
**And** the decision half imports no Dagster (AD-1) and nothing from `pyforge.warden` or `django_warden_fabric`; only `orchestration/definitions.py` wraps it
**Cross-station note** *(prose, deliberately NOT a `Deps:` token)*: the live inventory is Warden's Story 16.1 export (`spec-pyforge-warden:CAP-26`). This story is built and gated on a fixture export, so it does not wait for it; the attended live wiring follows 16.1.

## Epic 26: The factory-status page stops reading the retired intake-spec tier (spec-one-chain-per-station CAP-11)

**Spec binding.** Minted 2026-09-29 from `docs/governance/spec-one-chain-per-station/SPEC.md` CAP-11 (owner Dream
`docs/dreams/one-chain-per-station.md`, `owner: guild`). `docs/specs/` retires, and CHAIN-STANDARD §11 requires its readers
to follow before the PR that empties it (doctor Story 37.1). Atlas's factory-status page is one such reader. Atlas mints no
CAP and registers no FR for this story: the CAP is the Guild Spec's, enumerated here and in that Spec's `.memlog.md`, as
doctor's relay epics do. **HARD boundaries:**
- No file moves in this story.
- The page's other sources (the build stamp, `sprint-status.yaml`, `epics.md`) are unchanged.
- No dataset is added to the catalog.

Steward Epic 77, herald Epic 34 and marshal Epic 76 carry the other readers. The story is a `chore`.

### Story 26.1: The factory-status frame drops its docs/specs rows
**Type:** chore • **Effort:** S • **Deps:** — • **FR/AD:** `spec-one-chain-per-station:CAP-11` (CHAIN-STANDARD §11: readers follow the move)
**Surface:**
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/factory_status.py`: `read_spec_statuses`, the
  `specs_dir` default and parameter, and the `docs/specs` rows.
- `dashboard/app.py`: the page text naming `docs/specs/*.md`.
- The tests that build or inject a `docs/specs` directory: `tests/unit/test_dashboard_factory_status.py`,
  `tests/integration/dashboard/conftest.py` and `tests/integration/dashboard/test_dashboard_dryrun.py`.

**Given** the factory-status frame emits one `source="docs/specs"` row per legacy intake spec, and
`test_dashboard_dryrun.py` asserts at least one such row
**When** the `docs/specs` source is removed
**Then** the frame carries the build-stamp, `sprint-status.yaml` and `epics.md` rows only, and the page text no longer names
`docs/specs/`
**And** the dry-run test asserts no `docs/specs` row where it asserted at least one, so it passes before and after
`docs/specs/` empties; `pixi run -e pyforge-atlas kedro-test` and `pixi run -e pyforge-atlas kedro-catalog-check` green

## Epic 27: Phase 4+5 of the deferral burn-down — atlas's open medium and low deferrals, fixed

Minted 2026-10-03 from the operator's Phase 4+5 ruling: every open medium and low row in atlas's tracked deferred-work ledger is fixed where it lives, and closed only by a landed fix with a `resolution:` and a cited `verified:` line. A parser over `deferred-work-ledger.md` counts 36 open medium and 60 open low rows (114 unrated open rows are outside the ruling). All 96 are placed in four stories split by package area, per the operator's same-day sizing ruling: fewer, larger stories, at most about 30 rows each. These are `fix` stories: no CAP, no FR, no flag (`spec-feature-flag-governance` Q1). 18 rows repeat another row (later intakes re-ingested the same text) and close with it. Story 23.9 thinned the inventory quartet into actuators over Atlas's Kedro exports after many of these rows were raised, so each story re-locates a row before fixing it. Operator ruling 2026-10-03, after the mint: the nine rows in Story 27.4 that only an independent follow-up review of an already-landed story can close (DW-FU-13-3, DW-13-3-7, DW-10-5-9, DW-10-6-4, DW-FRR-16-1, DW-FRR-19-1, DW-FRR-20-2, DW-FRR-20-3, DW-FRR-20-4) leave that story and stay open for a separate per-station review batch, so the four stories now place 87 rows (36 medium, 51 low).

### Story 27.1: The inventory exports refuse a hollow verification set, and the quartet scripts fail loud
**Type:** fix • **Effort:** L • **Deps:** — • **FR/AD:** — (a `fix`, so no new CAP and no FR; `spec-feature-flag-governance` Q1: a `fix` needs no flag) • AD-3, AD-11, AD-13
**Surface:** `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/derived_artifacts/` (the inventory and identity-export nodes), `scripts/conda-forge-packaging-inventory-operations_{metrics,openteams_identity,priority}.py`, `scripts/openteams_identity_dashboards.py`, `scripts/tests/` (their tests and fixtures), `tests/packaging/test_openteams_handoffs.py`, `src/shared/packages/pyforge-atlas/tests/pipelines/derived_artifacts/`, `docs/reference/conda-forge-packaging-inventory-operations_*.md` (the replay and prompt docs, in step with the scripts), the atlas deferred-work ledger
**Spec:** `planning-artifacts/specs/spec-27-1-inventory-exports-refuse-hollow-sets-and-the-quartet-fails-loud.md`
**Given** the 25 open rows against the inventory quartet and the Kedro `derived_artifacts` exports it now formats
**When** each row is re-located against the current tree and fixed where its behaviour lives
**Then** an empty or sub-floor verification set is refused by name, `create_missing_issues` backs off, the export reader fails named on bad input, the gist and export columns share one schema, and a from-scratch fixture run reproduces the committed inventory
**And** 25 rows (9 medium, 16 low) are each closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed: DW-FU-17-1, DW-FU-17-2, DW-FU-21-3-2, DW-FU-21-3-7, DW-FU-21-3-12, DW-FU-21-7, DW-FU-21-7-2, DW-FU-21-7-3, DW-FU-21-7-4, DW-FU-17-2-2, DW-FU-17-2-3, DW-FU-17-2-7, DW-FU-21-3-3, DW-FU-21-3-4, DW-FU-21-3-5, DW-FU-21-3-6, DW-FU-21-3-8, DW-FU-21-3-9, DW-FU-21-3-10, DW-FU-21-3-11, DW-FU-21-7-5, DW-FU-21-7-6, DW-FU-21-7-7, DW-FU-21-7-8, DW-FU-23-5; `pixi run -e pyforge-atlas kedro-test` and `pixi run -e pyforge-atlas kedro-catalog-check` green

### Story 27.2: The data plane honours its data root, degrades offline and fetches what it claims
**Type:** fix • **Effort:** L • **Deps:** — • **FR/AD:** — (a `fix`, so no new CAP and no FR; `spec-feature-flag-governance` Q1: a `fix` needs no flag) • AD-2, AD-3, AD-5, AD-6, AD-13
**Surface:** `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/` (`vcs_sources.py`, `request_datasets.py`, `refresh.py`, `core_sources.py`, `identity_sources.py`, `basilisk.py`, `upstream_discovery.py`), `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/` (`vcs_health/`, `upstream_discovery/`, `pypi_intelligence/`), `src/shared/packages/pyforge-atlas/src/pyforge/atlas/orchestration/definitions.py`, `src/shared/packages/pyforge-atlas/conf/base/` (`catalog.yml`, `globals.yml`, `parameters.yml`), `src/shared/packages/pyforge-atlas/tests/` (`pipelines/`, `parity/`, `catalog/`), `src/shared/packages/pyforge-atlas/README.md`, the `pyforge-atlas-bootstrap` task description (member or root `pixi.toml`, with `environment.yaml` regenerated if the root changes), `.github/workflows/pyforge-station-tests.yml` (the atlas job), `planning-artifacts/specs/spec-20-6-upstream_discovery-identity-join-and-export-parquet.md` (a Spec Change Log line only), the atlas deferred-work ledger
**Spec:** `planning-artifacts/specs/spec-27-2-the-data-plane-honours-its-data-root-and-fetches-what-it-claims.md`
**Given** the 26 open rows against Atlas's datasets, catalog, pipelines, orchestration and CI lane
**When** the story lands
**Then** every output lands under `PYFORGE_ATLAS_DATA_ROOT`, a partial refresh batch keeps the rows outside it, the vcs triggers fetch real identifiers, offline and fresh-root runs exit 0 with stale markers, and CI runs both atlas gates
**And** 26 rows (12 medium, 14 low) are each closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed: DW-FU-21-2-2, DW-FU-21-2-4, DW-FU-21-4, DW-FU-21-5, DW-FU-21-5-3, DW-FU-21-6, DW-FU-21-8-2, DW-FU-21-8-9, DW-FU-21-8-3, DW-FU-21-8-5, DW-FU-21-8-10, DW-FU-21-8-8, DW-FU-21-2-3, DW-FU-21-2-5, DW-FU-21-2-6, DW-FU-21-2-7, DW-FU-21-2-8, DW-FU-21-3, DW-FU-21-4-2, DW-FU-21-4-3, DW-FU-21-4-4, DW-FU-21-6-2, DW-FU-21-6-3, DW-FU-21-6-4, DW-FU-21-8, DW-FU-21-8-4; `pixi run -e pyforge-atlas kedro-test` and `pixi run -e pyforge-atlas kedro-catalog-check` green

### Story 27.3: The read surfaces render what DESIGN.md specifies, and prove it on fixture data
**Type:** fix • **Effort:** L • **Deps:** S-26.1 • **FR/AD:** — (a `fix`, so no new CAP and no FR; `spec-feature-flag-governance` Q1: a `fix` needs no flag) • AD-1, AD-4, AD-7, AD-8, AD-17
**Surface:** `src/shared/packages/pyforge-atlas/src/pyforge/atlas/query_plane_boot.py`, `src/shared/packages/pyforge-atlas/tests/query_plane/`, `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/` (`app.py`, `data.py`, `factory_status.py`, `__init__.py`), `src/shared/packages/pyforge-atlas/src/pyforge/atlas/semantic/`, `src/shared/packages/pyforge-atlas/tests/dashboard/`, `src/shared/packages/pyforge-atlas/tests/integration/dashboard/`, `src/shared/packages/pyforge-atlas/tests/pipelines/semantic_packages/`, `src/shared/packages/pyforge-atlas/README.md`, `src/shared/packages/django-pyforge/` (`base.html` and a vendored htmx static file), the atlas deferred-work ledger
**Spec:** `planning-artifacts/specs/spec-27-3-the-read-surfaces-render-what-design-specifies-on-real-data.md`
**Given** the 21 open rows against the query plane, the dashboard, the semantic layer and the portal chrome
**When** the story lands
**Then** the yielded plane raises a typed error, the parity gate covers NULL, date, timestamp, decimal and blob values, every page renders its declared DESIGN.md controls, the scan pages run a scan through `pyforge.core.process`, and the e2e suite passes against fixture data with navigation and main landmarks
**And** 21 rows (8 medium, 13 low) are each closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed: DW-FU-20-1, DW-FU-20-2-2, DW-FU-20-5, DW-FU-20-5-8, DW-FU-20-5-2, DW-FU-20-5-9, DW-FU-20-5-4, DW-FU-20-5-11, DW-FU-20-2-3, DW-FU-20-3, DW-FU-20-3-2, DW-FU-20-3-3, DW-FU-20-5-3, DW-FU-20-5-10, DW-FU-20-5-5, DW-FU-20-5-12, DW-FU-20-5-6, DW-FU-20-5-13, DW-FU-20-5-7, DW-FU-20-5-14, DW-FU-19-2; `pixi run -e pyforge-atlas kedro-test` and `pixi run -e pyforge-atlas kedro-catalog-check` green

### Story 27.4: The planning record matches the tree and the cross-station seams hold
**Type:** fix • **Effort:** L • **Deps:** S-27.1, S-27.2, S-27.3 • **FR/AD:** — (a `fix`, so no new CAP and no FR; `spec-feature-flag-governance` Q1: a `fix` needs no flag) • — (planning record and cross-station test seams)
**Surface:** `planning-artifacts/DESIGN.md`, `planning-artifacts/epics.md` (per-story `Status:` lines only), `planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/catalog-sources.md`, the atlas deferred-work ledger, `src/shared/packages/pyforge-atlas/tests/meta/` (the planning and citation tests), `src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py`, `.claude/skills/bmad-agent-atlas/SKILL.md` and `_bmad/custom/bmad-cis-design-thinking.toml`
**Spec:** `planning-artifacts/specs/spec-27-4-the-planning-record-matches-the-tree-and-owed-reviews-run.md`
**Given** the 15 open rows in Atlas's planning record and at its seams with doctor and steward
**When** Stories 27.1-27.3 have landed and this story runs
**Then** DESIGN.md, epics.md, catalog-sources.md and the ledger match the tree under tests that fail on drift, every closed row's citation resolves, steward's register test checks the routing constraint, and the template placeholder resolves through `_bmad/custom/`
**And** 15 rows (7 medium, 8 low) are each closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed: DW-FU-20-4-2, DW-FU-20-4-5, DW-FU-20-4-4, DW-FU-20-4-7, DW-FU-21-8-6, DW-FU-21-8-11, DW-FU-24-1, DW-FU-20-2, DW-FU-20-4, DW-FU-21-5-2, DW-FU-21-5-4, DW-FU-21-8-7, DW-FU-20-4-3, DW-FU-20-4-6, DW-FU-24-1-2; `pixi run -e pyforge-atlas kedro-test` and `pixi run -e pyforge-atlas kedro-catalog-check` green

### Story 27.5: The distribution-breakdown facet filter builds its control
**Type:** fix • **Effort:** S • **Deps:** S-27.3 • **FR/AD:** — (a `fix`, so no new CAP and no FR; `spec-feature-flag-governance` Q1: a `fix` needs no flag) • AD-8, AD-11 (the FR-9 Vizro read surface; gates are fixtures) • Story 27.3 (`DW-FU-20-5`)
**Surface:** `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/` (`app.py`), `src/shared/packages/pyforge-atlas/tests/integration/dashboard/` (`test_dashboard_e2e.py`, `test_dashboard_controls.py`), the atlas deferred-work ledger
**Spec:** `planning-artifacts/specs/spec-27-5-the-distribution-breakdown-facet-filter-builds-its-control.md`
**Given** the fixture data tree and the `distribution-breakdown` page, which declares a `facet` filter and a chart (DESIGN.md § 3.8)
**When** the dashboard is built and the page is served
**Then** `#distribution-breakdown--filter-facet` holds its selector on every build and page load, never an empty 0×0 container, and a test that needs no browser pins the root cause
**And** the non-strict `xfail` that #1842 put on `test_declared_controls_render_against_real_rows` is removed and the test passes ten runs in a row; `DW-atlas-27-3-1` (medium) is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed; `pixi run -e pyforge-atlas kedro-test` and `pixi run -e pyforge-atlas kedro-catalog-check` green

### Story 27.6: The distribution-breakdown e2e test waits for its grid to mount
**Type:** fix • **Effort:** S • **Deps:** S-27.5 • **FR/AD:** — (a `fix`, so no new CAP and no FR; `spec-feature-flag-governance` Q1: a `fix` needs no flag) • spec-pyforge-atlas CAP-8 (the read surface) • AD-11 (gates are never weakened)
**Flag:** none (`spec-feature-flag-governance` Q1, a fix)
**Surface:** `src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_dashboard_e2e.py` (the grid checks of its three grid tests, through one `expect_grid_mounted` helper, and a doubled docstring line), the atlas deferred-work ledger, the `spec-pyforge-atlas` memlog and its co-governor's (the surface reconcile), `scripts/.spec-surface-baseline.json` (the scoped stamps)
**Spec:** `planning-artifacts/specs/spec-27-6-the-distribution-breakdown-e2e-test-waits-for-its-grid-to-mount.md`
**Given** `9ab7ef1cf1`, where `test_declared_controls_render_against_real_rows` waits for `networkidle`, then 15 s each for the facet filter, its dropdown and the chart's container, all rendered from the page layout, then asserts `#distribution-breakdown--grid` contains `linux-64` with Playwright's 5 s default, though Vizro fills that grid only from the page's `on_page_load` callback and the browser then loads dash-ag-grid's lazy grid chunk (`async-community.js`); 32 copies of the test on 16 xdist workers beside 48 busy loops fail 4 of 24 with `Locator expected to contain text 'linux-64'`, as the 2026-10-24 full-scope `pr-preflight` did; and the file's navigation and grounded-pages tests check grids filled the same way under the same default
**When** the tests run under that load
**Then** right after `goto` the test waits up to 60 s for the AG Grid to mount inside `#distribution-breakdown--grid` (`.ag-root-wrapper` attached), the element the page draws last, then checks the filter, its dropdown, the chart and the `linux-64` row as before; every other grid check in the file first waits for its grid's mount the same way; and no copy fails its assertions (setup errors, the fixture's server not binding within 60 s at that load, are counted and reported apart)
**And** against a fixture root without the `linux-64` row the test still fails on the row assertion with the grid's actual text; the diff adds no skip, `xfail`, retry or rerun and keeps every assertion; only the test file changes under `src/`; `DW-atlas-retro-2026-10-15-1` (medium) is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed; `pixi run -e pyforge-atlas pyforge-atlas-test`, `kedro-test` and `kedro-catalog-check` green
**Status:** done

## Epic 28: The live-attach fixture Postgres starts under any basetemp (fix under spec-pyforge-atlas CAP-6)

Minted 2026-10-11 from the station Dream's entry of that date (live-attach fixture socket path) and the operator's ask
in session, "Do this task here: Fix atlas live-attach test socket path overflow". `fixture_postgres` in
`tests/unit/test_read_only_live_attach.py` starts a throwaway PostgreSQL with its Unix socket under `tmp_path`. Under
pr-preflight's per-lane `--basetemp` that socket path passes the 107-byte AF_UNIX limit, the server exits, and the two
fixture-backed tests error at setup: warden 16.1's fix pass red the `pyforge-atlas-test` lane on it on 2026-10-11. The
test reaches Postgres only over TCP, so the fixture needs no socket. A defect against `spec-pyforge-atlas` CAP-6 (the
read-only ATTACH joins the one DuckDB plane, AD-4), so no CAP is minted; a new epic because no atlas epic owns the test
(steward Story 34.1 shipped it under `spec-pyforge-unifying-strategy` CAP-19, and atlas mints none of that CAP's
stories). **HARD boundaries:** test-only, in `fixture_postgres`; `live_attach.py`, `duckdb_writer.py`, the two tests'
bodies and their assertions do not change; no skip, `xfail` or rerun is added (AD-11: gates are never weakened).

### Story 28.1: The live-attach fixture Postgres starts under any basetemp
**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** — (a `fix`, so no new CAP and no FR; `spec-feature-flag-governance` Q1: a `fix` needs no flag) • spec-pyforge-atlas CAP-6 • `spec-pyforge-unifying-strategy` CAP-19 (canopy:FR-46; steward Story 34.1 shipped the test) • AD-4, AD-11
**Flag:** none (`spec-feature-flag-governance` Q1, a fix)
**Surface:** `src/shared/packages/pyforge-atlas/tests/unit/test_read_only_live_attach.py` (`fixture_postgres`, :88-:209, only), the `spec-pyforge-atlas` and `spec-pyforge-unifying-strategy` memlogs (the surface reconcile), `scripts/.spec-surface-baseline.json` (the two scoped stamps)
**Spec:** `planning-artifacts/specs/spec-28-1-the-live-attach-fixture-postgres-starts-under-any-basetemp.md`
**Given** `2b5e0d649b`, where `fixture_postgres` starts PostgreSQL with `-k '<tmp_path>/pgsock'`, and a pytest basetemp longer than 107 bytes: warden 16.1's pr-preflight run red the `pyforge-atlas-test` lane on it ("5 passed, 2 errors" when reproduced with a 214-byte basetemp; the server log reads `Unix-domain socket path ".../pgsock/.s.PGSQL.<port>" is too long (maximum 107 bytes)`)
**When** the fixture starts its server
**Then** it opens no Unix socket (`-c unix_socket_directories=''` in place of `-k`, with no socket directory under `tmp_path`), and `test_federated_read_across_two_schemas` and `test_write_through_attach_is_refused` pass, not skip, under that basetemp when PostgreSQL binaries are present
**And** with no PostgreSQL binaries both tests still skip with the fixture's existing reason; the diff adds no skip or `xfail`; only the test file changes; restoring `-k '<tmp_path>/pgsock'` reds both tests under the long basetemp (mutation); `pixi run -e pyforge-atlas kedro-test` and `pixi run -e pyforge-atlas kedro-catalog-check` green
**Status:** done

## Epic 29: The range test server records each response before the client can read it (fix under spec-pyforge-atlas CAP-16)

Minted 2026-10-13 from the station Dream's entry of that date (range-test recorder race) and the operator's ask in
session, "Do this task here: Fix flaky atlas range-read test under xdist". `_RangeServer` in
`tests/integration/publish/test_emit_range.py` appends each response to its request log only after writing the body,
so a client can finish its query, and the test can assert, before the server thread records anything:
`test_count_star_reads_footer_only_over_range` (one Range request) failed that way in a pre-push `pr-preflight` lane on
2026-10-13 with `assert (200 not in [] and 206 in [])`. A defect against `spec-pyforge-atlas` CAP-16 (the read surface
runs with no backend at all; Story 8.2 shipped the Range proof), so no CAP is minted; a new epic because Epic 8 is
done. **HARD boundaries:** test-only, in `_RangeServer`'s handler and one new regression test; `pyforge.atlas.publish`
and every existing assertion stay unchanged; no skip, `xfail`, retry or sleep is added to an existing test (AD-11:
gates are never weakened); the new test's delay seam defaults to 0 for every other test.

### Story 29.1: The range test server records each response before the client can read it
**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** — (a `fix`, so no new CAP and no FR; `spec-feature-flag-governance` Q1: a `fix` needs no flag) • spec-pyforge-atlas CAP-16 (Story 8.2 shipped the Range proof) • AD-2, AD-11
**Flag:** none (`spec-feature-flag-governance` Q1, a fix)
**Surface:** `src/shared/packages/pyforge-atlas/tests/integration/publish/test_emit_range.py` (`_RangeServer`'s handler and one new test, only), the `spec-pyforge-atlas` memlog (the surface reconcile), `scripts/.spec-surface-baseline.json` (the scoped stamp)
**Spec:** `planning-artifacts/specs/spec-29-1-the-range-test-server-records-each-response-before-the-client-can-read-it.md`
**Given** `0d5702f516`, where the handler appends to `codes`, `ranges`, `range_spans` and `bytes_served` after `self.wfile.write(data)`, and a handler delayed 0.5 s after each body write: the log reads `[]` right after a `count(*)` query and `[206]` a second later
**When** a client reads from `_RangeServer`
**Then** every branch (206, 200, 416) records the response before writing any of it, so the log is complete when the client can read the response; a new regression test delays each body write and asserts the request is in the log as soon as the query returns
**And** every existing test and assertion in the file is unchanged and green; the diff adds no skip, `xfail`, retry or sleep to an existing test; only the test file changes; moving the appends back after the write reds the new test (mutation); `pixi run -e pyforge-atlas pyforge-atlas-test` green
**Status:** done

## Epic 30: The DAG export and the Vizro boards reach Pages as workflow artifacts (spec-pyforge-atlas CAP-62, CAP-63)

Minted 2026-10-14 from the station Dream's entry of 2026-10-13 (the DAG export reaches Pages as an artifact) — the
operator ruling carried from the herald Dream's same-day entry *the Pages deployment, redesigned* — via `bmad-spec`
(CAP-62 amending CAP-41, CAP-63; FR-70, FR-71; AD-21 amended). Measured 2026-10-13: `docs/dashboard/kedro-viz/`
(11 MB, 215 tracked files) was last written 2026-08-15; `kedro-viz-publish.yml` has been `disabled_manually` since
2026-08-24 with no recorded reason; 23 first-parent merges since then touched the paths it watches, so the published
graph lags its DAG by two months; its builds took 92 to 137 s. Steward Epic 99 is done, so every job gets a `PAUSE_*`
switch and a registry row by the Story 99.2 convention. **HARD boundaries:**
- No server and no live data on Pages (the placement rule on the herald Dream); the live Vizro server and the console
  stay Lane 1 `/console/`.
- Nothing atlas runs commits to `main`, calls `deploy-pages`, or edits `pages.yml` / `dashboard.yml` (steward's and
  herald's); the artifact is the only handoff, and `/dashboard/kedro-viz/` keeps its URL.
- Zero third-party origins in anything handed to the Pages build (herald AD-21): plotly.js is vendored once, never
  `'cdn'`.
- `conf/local/credentials.yml` stays stubbed in the producer as today; AD-1 import boundaries hold (`pipelines/`,
  `datasets/`, `hooks.py` untouched; the exporter lives under `dashboard/` and `tools/`).
- The registry `docs/governance/ci-surfaces.yaml`, its schema and the `steward ci` duty are steward's: atlas names the
  switch and the row; the `paused-manually → live` move is the operator's gate, never a blocked row.
- A board with a declared access column is never exported statically (`sld:AD-10`): refuse, never warn.

### Story 30.1: The DAG export reaches Pages as a workflow artifact

As a reader of `/dashboard/kedro-viz/` who wants the pipeline graph to be the one on `main`,
I want atlas's producer workflow to build the Kedro-Viz export on every DAG change and hand it to the Pages build as a
workflow artifact that carries its commit and date,
So that the published graph stops lagging its DAG by months and no bot commit carries 11 MB of export bytes onto `main`.

**Type:** feature • **Effort:** M • **Deps:** — (cross-station, prose, never a blocked row: steward Story 102.2, the renamed `pages.yml`, exists to consume it; steward Story 102.4 is the consumer step) • **FR/AD:** spec-pyforge-atlas CAP-62 (FR-70), amending CAP-41 • AD-21 (amended 2026-10-14), AD-17, AD-1, AD-11; reads `pyforge-steward:CAP-166` • Dream 2026-10-13 (the DAG export reaches Pages as an artifact) • operator ruling 2026-10-13
**Flag:** `pyforge.atlas.viz_export_artifact` (new; minted by this story; tree default off, dev on through the overlay. OFF: `viz-publish-stage` stages as today, writes no manifest, and the upload step is skipped)
**Surface:** `.github/workflows/kedro-viz-publish.yml` (the upload step, the CI-pause fragment, `permissions`, the retired commit steps), `src/shared/packages/pyforge-atlas/tools/normalize_viz_build.py` or a sibling `tools/viz_manifest.py` (the manifest), `pixi.toml` (`viz-publish-stage`), `docs/dashboard/kedro-viz/**` (leaves git), `.gitignore` (the staging path), `docs/dashboard/README.md`, a flag reader under `src/shared/packages/pyforge-atlas/src/pyforge/atlas/`, tests under `src/shared/packages/pyforge-atlas/tests/` (the workflow shape, the manifest, the flag in both states), `src/platform/config/flags.json`, `src/platform/config/flag-overlays.json`, `docs/governance/flag-inventory/pyforge-atlas.md`, `docs/governance/ci-surfaces.yaml` (the row's `switch`; steward's co-governed edit)
**Spec:** `planning-artifacts/specs/spec-30-1-the-dag-export-reaches-pages-as-a-workflow-artifact.md`
**Given** `kedro-viz-publish.yml` as it stands (path filter, stub credentials, `viz-publish-stage`, then `steward deploy dashboard` committing `docs/dashboard/kedro-viz/` with `contents: write`), disabled by hand since 2026-08-24, and a committed export last written 2026-08-15
**When** the story's tree is built with the flag on
**Then** `git ls-files docs/dashboard/kedro-viz` lists nothing and the path is gitignored; `viz-publish-stage` leaves `manifest.json` beside `index.html` with `export_commit` (40-hex, equal to `git rev-parse HEAD`), `export_date` (ISO 8601 UTC) and `kedro_viz_version` (equal to `deploy-viz-metadata`'s `version`); the workflow has one `actions/upload-artifact` step (`name: kedro-viz-export`, `retention-days: 90`, the staged path), no `steward deploy dashboard`, `git checkout -B main` or `git config user.name` step, `permissions.contents: read`, the path filter, `workflow_dispatch` and the stub-credentials step unchanged, and its job `if:` carries `PAUSE_KEDRO_VIZ_PUBLISH`
**And** the registry row `kedro-viz-publish` names `switch: PAUSE_KEDRO_VIZ_PUBLISH` (its `paused-manually → live` move is the operator's, through steward's `ci` duty, after the workflow is re-enabled on GitHub); `docs/dashboard/README.md` names the artifact and no longer names `steward deploy dashboard`; with the flag off no manifest is written and the staged tree is byte-identical to today's; `kedro-test` and `kedro-catalog-check` green; the flag test runs the key in both states with `pyforge.testing_kit.flags.flag_states`
**Status:** done

### Story 30.2: Vizro boards publish as static exports under /dashboard/vizro/

As a reader of the Pages site who wants the atlas boards without a server,
I want each board of the BSL-driven Vizro dashboard exported offline as a static page, with its data's build stamp,
and handed to the Pages build as a workflow artifact that loads nothing from a third-party origin,
So that the dashboards sit beside the pipeline graph under `/dashboard/`, air-gap-clean, while the live Vizro server
stays on Lane 1.

**Type:** feature • **Effort:** L • **Deps:** S-30.1 (cross-station, prose, never a blocked row: herald Story 43.3 (CAP-61, M3) `publicDir` mounts; steward 102.4's consumer step, generalized to this artifact) • **FR/AD:** spec-pyforge-atlas CAP-63 (FR-71), extending CAP-8, CAP-40, CAP-42, CAP-50 and CAP-62 • AD-21 (amended 2026-10-14), AD-17, AD-8, AD-1; `sld:AD-10` (steward spine) • Dream 2026-10-13 • operator ruling 2026-10-13
**Flag:** `pyforge.atlas.vizro_static_boards` (new; minted by this story; tree default off, dev on through the overlay. OFF: the task refuses with the flag-off message and writes nothing)
**Surface:** `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/static_export.py` (new: the exporter over `build_dashboard`, the vendored plotly copy, the manifest, the access-column refusal), `pixi.toml` (`vizro-static-export` under `[feature.pyforge-atlas.tasks]`; amended 2026-10-15, was `[feature.local-recipes.tasks]`), `.github/workflows/kedro-viz-publish.yml` (a second job — or its own workflow with its own registry row, the operator's call), `.gitignore` (`docs/dashboard/vizro/`), `docs/dashboard/README.md`, tests under `src/shared/packages/pyforge-atlas/tests/integration/dashboard/` and `tests/unit/` (the export on the fixture data root, the vendored script, the refusal, the manifest, the workflow shape, the flag in both states), `src/platform/config/flags.json`, `src/platform/config/flag-overlays.json`, `docs/governance/flag-inventory/pyforge-atlas.md`
**Spec:** `planning-artifacts/specs/spec-30-2-vizro-boards-publish-as-static-exports-under-dashboard-vizro.md`
**Given** the 34-page BSL-driven `Dashboard` object `dashboard-dryrun` builds offline in `-e local-recipes`, each page carrying its own AD-17 stamp, and the archived intake workaround whose `include_plotlyjs='cdn'` herald AD-21 forbids
**When** `pixi run -e pyforge-atlas vizro-static-export` runs with the flag on against the fixture data root *(amended 2026-10-15, orchestrator ruling; operator may override)*
**Then** it exits 0 and writes `docs/dashboard/vizro/index.html`, one `<page-id>/index.html` per exported page, exactly one `assets/plotly.min.js` (plotly's own `package_data` copy), and `manifest.json` with `exported_at`, `export_commit` and one `boards[]` entry per page (`id`, `title`, `path`, `data_build_timestamp`); `grep -rl cdn.plot.ly docs/dashboard/vizro` prints nothing and every `<script src=` resolves to the vendored file; the Run controls of `scan-project` and `env-inspect` are absent and those pages say they show the latest cached result
**And** a fixture board with a declared access column makes the task exit 1 naming the board and write nothing (`sld:AD-10`); with the flag off it refuses and writes nothing; with the export under `docs/dashboard/vizro/`, `pixi run -e site pages-check` exits 0 with no cross-origin finding under `dashboard/vizro/`, the one `VENDORED_ROOTS` entry under the mount being the exact file `dashboard/vizro/assets/plotly.min.js` (herald:AD-21 rule 5; amended 2026-10-15, was "`VENDORED_ROOTS` unchanged"); the producer job uploads `docs/dashboard/vizro/` as `vizro-static-export` (`retention-days: 90`) and has no commit or push step; `dashboard-dryrun`, `kedro-test` and `kedro-catalog-check` green; the flag test runs the key in both states with `flag_states`
**Status:** done

## Epic 31: Atlas passes mypy in `pyforge-foundry-full`, and a lane keeps it so (fix under spec-pyforge-atlas CAP-20)

Minted 2026-10-14 from the station Dream's entry of that date (foundry-full mypy), from `DW-atlas-steward-100-7-1`,
and from the operator's approval, "chain the three DWs". `sbom-laptop-gate` runs `lint-types` inside
`pyforge-foundry-full`, where Atlas's real runtime libraries are installed, and mypy finds 72 errors in 8 Atlas files
there (measured at `846d8383f5`). `pyforge-guild`, where the CI `lint-types` lane and `pr-preflight` run mypy, lacks
those libraries and reads them as `Any`, so CI stays green, and no workflow runs mypy in `pyforge-foundry-full`. A
defect against `spec-pyforge-atlas` CAP-20 (one command runs every check CI runs, type checking included; AD-32: local
and CI never drift apart), so no CAP is minted. The lane itself is `spec-pyforge-steward:CAP-153`'s and its list
`spec-pyforge-steward:CAP-159`'s; both are cited, not changed. A new epic, because no open atlas epic owns the type
gate. **HARD boundaries:**
- Typed call sites first. One per-module, per-code override (`call-arg` on `pyforge.atlas.dashboard.app`, Vizro's
  `Annotated` defaults) and nothing broader. Never `ignore_errors`, an inline `# type: ignore` or a `cast`.
- The lane is the existing `mypy` task run in `pyforge-foundry-full`: one more step in the existing `lint-types` CI job
  and one more `pr-preflight` lane. No new script, environment, dependency or plugin.
- No test is weakened (AD-11). The four OpenLineage assertions move to the key the spec defines; touched modules meet
  the 80% unit floor without a lowered floor or a skipped test.

### Story 31.1: Atlas passes mypy in `pyforge-foundry-full`, and a lane keeps it so

As the operator whose laptop gate has been red on `main` while every CI lane stayed green,
I want Atlas to type-check against its real libraries, and that check to run in CI and before every push,
So that a type error only real library types reveal reds the PR that adds it, not the laptop weeks later.

**Type:** fix • **Effort:** M • **Deps:** — • **FR/AD:** — (a `fix`, so no new CAP and no FR; `spec-feature-flag-governance` Q1: a `fix` needs no flag) • spec-pyforge-atlas CAP-20 • `spec-pyforge-steward:CAP-153`, `spec-pyforge-steward:CAP-159`, `fnd:CAP-13` (cited) • AD-11, AD-32 • closes `DW-atlas-steward-100-7-1` • Dream 2026-10-14 (foundry-full mypy) • operator approval 2026-10-14 "chain the three DWs"
**Flag:** none (`spec-feature-flag-governance` Q1, a fix)
**Surface:** seven atlas modules: `dashboard/app.py`, `views/widgets.py`, `datasets/upstream_discovery.py`, `orchestration/definitions.py`, `mcp/session.py`, `observability.py` and `rag/store.py` (`query_plane_vectors.py` unchanged). Also `src/shared/packages/pyforge-atlas/pyproject.toml` (one override), `tests/unit/observability/test_observability_fixtures.py` (four assertions), two new vss-free unit test modules (`rag/store.py`, `mcp/session.py`) and a new `tests/meta/test_foundry_full_mypy_lane.py`. Outside atlas: `.github/workflows/lint-types.yml` (one step) and `pixi.toml` (`pr-preflight-lanes`), with `docs/how-to/pixi-tasks.md` and `environment.yaml` regenerated if they move. Plus each governor's memlog (see the story spec), `scripts/.spec-surface-baseline.json` and the atlas `deferred-work-ledger.md` (closing the DW)
**Spec:** `planning-artifacts/specs/spec-31-1-atlas-passes-mypy-in-pyforge-foundry-full-and-a-lane-keeps-it-so.md`
**Given** `846d8383f5`, where `pixi run --frozen -e pyforge-foundry-full lint-types` exits 1 with `pyforge-atlas` at `Found 72 errors in 8 files`. By file: `dashboard/app.py` 59 (54 `call-arg` on Vizro models whose defaults sit inside `Annotated[..., Field(default=...)]`), `views/widgets.py` 4, two each in `upstream_discovery.py`, `definitions.py` and `query_plane_vectors.py`, and one each in `session.py`, `observability.py` and `rag/store.py`. `pyforge-guild` reports none, and no workflow runs mypy in `pyforge-foundry-full`
**When** `pixi run --frozen -e pyforge-foundry-full mypy` runs, on a branch, in CI or in `pr-preflight`
**Then** it exits 0. The 17 errors that are neither Vizro's `call-arg` nor the OpenLineage defect, and the one the Bokeh import fix exposes, are fixed by typed call sites, annotations or narrowing, with no `# type: ignore`, `cast` or `ignore_errors`. The only new override is `call-arg` on `pyforge.atlas.dashboard.app`, and with it removed only Vizro's "Missing named argument" errors return. `observability.py` emits `outputStatistics` under `outputFacets`, and the four assertions read it there. `pixi run --frozen -e pyforge-guild lint-types` still exits 0
**And** the `lint-types` CI job installs `pyforge-guild pyforge-foundry-full` and runs `pixi run --frozen -e pyforge-foundry-full mypy`. `pr-preflight-lanes` gains `{ task = "mypy", environment = "pyforge-foundry-full" }`, and an atlas meta test pins both. Reverting one typed fix reds the foundry-full leg while the guild leg stays green (mutation). `pyforge-atlas-coverage-gate`, `kedro-test`, `kedro-catalog-check`, `pyforge-atlas-test` and `pyforge-station-tests` exit 0. Every governing Spec is reconciled and stamped scoped, and the DW row closes citing the merge
**Status:** done

## Epic 32: The DAG export builds in CI, and a failed build fails its task (fix under spec-pyforge-atlas CAP-62)

Minted 2026-10-17 from the station Dream's entry of that date (kedro-viz-publish's stub credentials drifted). The
operator lifted every CI pause on 2026-10-16 (PR #2247), which re-enabled `kedro-viz-publish.yml`, and the dispatch
Story 30.1 names as the operator's step (run `39002722593`, `990d796c7f`) failed in its `publish` job with
`Unable to find credentials 'gitlab_token'`: the workflow's own stub carries two of the eight credential keys
`conf/base/catalog.yml` names, while `tools/bootstrap.py`'s stub, a second copy, carries all eight. kedro-viz 12.5.0
exits 0 when its build fails, so `viz-build` read green and the failure surfaced one step later as `build does not
exist`. Past the build, the job's flag step ran `print_viz_export_flag.py` in `-e pyforge-guild`, which cannot import
`pyforge.atlas` (found by the story's independent review; folded into 32.1 by orchestrator ruling, 2026-10-17). A
defect against `spec-pyforge-atlas` CAP-62 (the DAG export reaches Pages as a workflow artifact), so no CAP is minted;
a new epic because Epic 30, which shipped the producer, is done. **HARD boundaries:**
- One source for the stub: the workflow writes it through `tools/bootstrap.py`, never from a key list of its own, and
  the writer never overwrites a file that holds anything. No credential, token or secret enters the workflow (AD-11).
- The `vizro` job, the upload step, the artifact's name and retention, the flag gate (beyond its step's environment,
  `-e pyforge-guild` → `-e pyforge-atlas`), `on.push.paths` and the CI-pause `if:` fragments do not change;
  `ci_surface_gates.py --check` stays at exit 0.
- No test is weakened (AD-11). Story 30.1's byte pin on the old stub step hands over to a pin on its source; every other
  assertion in `test_viz_export_artifact.py` stays.

### Story 32.1: The DAG export builds in CI, and a failed build fails its task

As the operator who dispatched `kedro-viz-publish.yml` to hand Pages its first `kedro-viz-export`,
I want the workflow's stub credentials to come from the one list the catalog is checked against, and `viz-build` to
fail when `kedro viz build` does,
So that a new catalog credential reds a PR instead of the publish run, and a failed build stops at the step that failed.

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** — (a `fix`, so no new CAP and no FR; `spec-feature-flag-governance` Q1: a `fix` needs no flag) • spec-pyforge-atlas CAP-62 (FR-70) • AD-11, AD-21 • Dream 2026-10-17 (kedro-viz-publish's stub credentials drifted) • run `39002722593`
**Flag:** none (`spec-feature-flag-governance` Q1, a fix)
**Surface:** `.github/workflows/kedro-viz-publish.yml` (the `publish` job's stub step and its comment, and the flag step's environment, only), `src/shared/packages/pyforge-atlas/tools/bootstrap.py` (`CREDENTIAL_KEYS`, `--credentials-only`), a new `src/shared/packages/pyforge-atlas/tools/viz_build_check.py`, `pixi.toml` (`viz-build`'s `cmd` and description, `pyforge-atlas-bootstrap`'s description), a new `src/shared/packages/pyforge-atlas/tests/unit/test_viz_publish_build.py`, `src/shared/packages/pyforge-atlas/tests/unit/test_viz_export_artifact.py` (AC4's stub byte pin only), each governor's memlog, `scripts/.spec-surface-baseline.json`
**Spec:** `planning-artifacts/specs/spec-32-1-the-dag-export-builds-in-ci-and-a-failed-build-fails-its-task.md`
**Given** `17670a0580`, where the workflow's stub step writes `bigquery_adc` and `github_token` as auth pairs, `conf/base/catalog.yml` names eight credential keys, `tools/bootstrap.py`'s `_CREDENTIALS_STUB` names all eight as `{}`, and `viz-build` is `rm -rf build && kedro viz build`
**When** the workflow's `publish` job runs on a runner with no `conf/local/credentials.yml`, or `viz-build` runs where a catalog key is missing
**Then** the stub step runs `tools/bootstrap.py --credentials-only`, which writes every key in `CREDENTIAL_KEYS` as `{}` when the file is absent or empty and leaves a non-empty file untouched; no string in the workflow names a credential key or `credentials.yml`; the flag step and every other `pixi run … python …/pyforge-atlas/tools/*.py` step runs in `-e pyforge-atlas`, where the flag prints `enabled=true`; `viz-build` on a scratch copy built that way exits 0 and writes `build/index.html`, `build/api/main` and `build/api/deploy-viz-metadata`, and `viz-publish-stage` exits 0 and fills `docs/dashboard/kedro-viz/`; with a key missing, `viz-build` exits 1 naming the missing build files
**And** a test reads every `credentials:` key in every `conf/base/**/catalog*.y*ml` and fails when `CREDENTIAL_KEYS` lacks one (mutation: drop a key; a second catalog file) or the workflow carries a key list again, in any string (mutation); a test pins `viz-build`'s check against kedro-viz's deployer and fails when it is removed (mutation); a test fails when an atlas tool step names another env (mutation: `pyforge-guild` back); `pyforge-atlas-test`, `kedro-test`, `kedro-catalog-check`, `pyforge-atlas-coverage-gate`, `lint-types` and `ci_surface_gates.py --check` exit 0; every governing Spec is reconciled and stamped scoped
**Status:** done

## Epic 33: The atlas CLI reaches the verbs its contracts name, from any directory (fix under spec-pyforge-atlas CAP-9)

Minted 2026-10-18 from the station Dream's entry of that date (the atlas CLI has no verbs). The operator ran the skill's
quick-start command, `pyforge atlas run --pipeline core`, from the repo root on 2026-10-17; it exited 2 with `Got
unexpected extra argument (run)`. `pyforge.atlas.__main__.main` hands every argument to Kedro's `find_run_command`,
which returns the `run` command itself, so the binary reaches no verb at all, while the skill, the `bmad-agent-atlas`
persona, the FR-155 parity gate (`mcp/parity.py`, which reads `kedro.framework.cli.project.project_group`) and
`TOOL_SPECS` (`["run", "--pipeline", <name>]`) all name verbs. From the repo root a run also reads the repo root's own
`conf/`, not atlas's catalog, because Kedro's project discovery starts at the cwd. A defect against `spec-pyforge-atlas`
CAP-9 (agents trigger and read the pipeline natively), so no CAP is minted; a new epic because the epics that shipped
the CLI (2, Story A1; its `--version` intercept came from steward Story 7.1), the skill (18) and the gate (24) are done. **HARD boundaries:**
- The binary dispatches to Kedro's own `project_group`, the group the parity gate already reads; Kedro's routing is
  not reimplemented and no plugin or global command is added to the surface.
- The project root is the one the MCP face pins (`mcp/session.py` `PROJECT_ROOT`); `--version` stays the
  first-token-only intercept that loads no Kedro.
- No pipeline, dataset, catalog entry or MCP tool behaviour changes; `TOOL_SPECS` changes only its declared CLI argv
  (`--pipeline` to `--pipelines`, Kedro 1.6's non-deprecated flag).

### Story 33.1: The atlas CLI reaches the verbs its contracts name, from any directory

As an operator or agent following atlas's skill,
I want `pyforge atlas run --pipelines <name>` to run atlas's pipeline against atlas's own project from wherever I stand,
So that the documented grammar, the persona's RUN menu and the parity gate describe a CLI that exists.

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** — (a `fix`, so no new CAP and no FR; `spec-feature-flag-governance` Q1: a `fix` needs no flag) • spec-pyforge-atlas CAP-9 • canopy:FR-13 • AD-23 • Dream 2026-10-18 (the atlas CLI has no verbs)
**Flag:** none (`spec-feature-flag-governance` Q1, a fix)
**Surface:** `src/shared/packages/pyforge-atlas/src/pyforge/atlas/__main__.py`, `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/tools.py` (`TOOL_SPECS` `cli` argv only), `src/shared/packages/pyforge-atlas/tests/unit/test_main_version.py`, a new `src/shared/packages/pyforge-atlas/tests/unit/test_main_dispatch.py`, `src/shared/packages/pyforge-atlas/tests/meta/test_cli_tool_parity.py`, `src/shared/packages/pyforge-atlas/README.md`, the `kedro run --pipeline` text in `dashboard/app.py`, `dashboard/data.py`, `pipelines/semantic_packages/README.md` and `tests/unit/mcp/test_audit_mapping.py` (text only), `.claude/skills/pyforge-atlas/0.1.0/pyforge-atlas/SKILL.md` and `provenance-map.json`, `.claude/skills/bmad-agent-atlas/customize.toml`, atlas's `test-architecture.md` (regenerated), herald's `deferred-work-ledger.md` (one row for the decks), the station Dream, each governor's memlog, `scripts/.spec-surface-baseline.json`
**Spec:** `planning-artifacts/specs/spec-33-1-the-atlas-cli-reaches-the-verbs-its-contracts-name.md`
**Given** `13f2df3778`, where `main` returns `find_run_command("pyforge.atlas")(*args, **kwargs)`, `pyforge atlas run` exits 2 with `Got unexpected extra argument (run)`, and a run started from the repo root resolves its Kedro project to the repo root
**When** `pyforge atlas <verb> …` is invoked from the repo root, from the atlas member dir, or from any other directory
**Then** each verb in `kedro.framework.cli.project.project_group` (`ipython`, `package`, `run`) is reached through `main` with the atlas project's metadata as its `obj` and atlas's member dir as the cwd; `pyforge atlas run --pipelines seed_gaps` from the repo root runs atlas's own catalog and creates no new path at the repo root; a bare `pyforge atlas` prints the three verbs and starts no run; `pyforge atlas --version` still prints one line and loads no Kedro; `TOOL_SPECS` declares `["run", "--pipelines", <name>]`; the skill, the persona and the README name that grammar and point dataset listing at MCP `list_atlas_datasets`
**And** a test fails when any verb the parity gate counts is unreachable through `main` (mutation: `main` back on `find_run_command`), when `main` runs a verb outside the member dir (mutation: drop the cwd pin), and when a `run_*` tool declares the deprecated `--pipeline` (mutation); `pyforge-atlas-test`, `kedro-test`, `kedro-catalog-check`, `pyforge-atlas-coverage-gate` and `lint-types` exit 0; every governing Spec is reconciled and stamped scoped
**Status:** done

### Story 33.2: The spine counts twelve pipelines, and the MCP face names its eight as the MCP-triggerable ones

As an operator or agent reading AD-3 or calling `list_atlas_pipelines`,
I want the spine to name every registered pipeline and the MCP face to say its eight names are the MCP-triggerable set,
So that neither text claims a pipeline count the registry no longer has.

**Type:** fix • **Effort:** XS • **Deps:** — • **FR/AD:** — (a `fix`, so no new CAP and no FR; `spec-feature-flag-governance` Q1: a `fix` needs no flag) • spec-pyforge-atlas CAP-9 • AD-3 • Dream 2026-10-25 (twelve pipelines, eight triggers) • retro-pyforge-atlas-2026-10-25 Finding 7 (candidate fixes 4 and 5)
**Flag:** none (`spec-feature-flag-governance` Q1, a fix)
**Surface:** the spine's AD-3 amendment parenthetical (in place) and a `## Currency reconciliation` entry; `mcp/server.py` (`list_atlas_pipelines` docstring, the served tool description), `mcp/tools.py` (`TOOL_SPECS` `list_pipelines` description, the `PIPELINE_NAMES` comment, `list_pipelines` docstring), `tests/unit/mcp/test_audit_mapping.py` (module docstring), `.claude/skills/pyforge-atlas/` (the `list_pipelines` line)
**Spec:** `planning-artifacts/specs/spec-33-2-the-spine-counts-twelve-pipelines-and-the-mcp-face-names-its-eight.md`
**Given** `register_pipelines()` registers twelve pipelines (`catalog_index` outside `__default__`), while AD-3's amendment says its rule "holds across all ten" and the MCP texts call `PIPELINE_NAMES`' eight "the registered pipelines"
**When** the story lands
**Then** AD-3's amendment names the twelve and which run in `__default__`, and every MCP text names the eight as the MCP-triggerable pipelines, the other four CLI-only by design
**And** no pipeline, tool, trigger set or test assertion changes; `pixi run -e pyforge-atlas pyforge-atlas-test` green
**Status:** done

## Epic 34: A plain run fills every dataset a public source serves (spec-pyforge-atlas CAP-64, FR-72)

Minted 2026-10-18 from the station Dream's entry of that date (atlas fills its own data) and the operator's rulings
recorded on the Spec's memlog: public sources go live in-package by default; credentialed requests only under
`PYFORGE_ATLAS_CREDENTIALED=1`; BigQuery stays off. The unattended refresh of 2026-10-17 left 40 of the 57 Parquet
datasets on disk at 0 rows. Every source, its datasets, its legacy phase and its parity measure: the Spec companion
`live-sources.md`. **HARD boundaries:**
- The no-inline-IO denylist (`tests/unit/catalog/test_no_inline_io.py`) does not change: fetches compose
  `kedro_datasets.api.APIDataset` or run a subprocess through `pyforge.core.process`.
- An unreachable endpoint keeps last-good and marks stale (AD-13); no gate, test or CI job makes a network call
  (recorded responses and fixtures only, AD-11), and none sets `PYFORGE_ATLAS_CREDENTIALED`.
- A `fix` story restores a source that was meant to work and needs no flag; a `feature` story ships behind
  `pyforge.atlas.live_public_sources`, whose OFF state is today's behaviour (the store keeps last-good, offline).
- Each story records its parity measure against the legacy `cf_atlas.db` figure of the same day in its story spec.

### Story 34.1: endoflife.date and the SPDX list arrive as records the seed-gap reports read

As an operator running the seed-gap reports,
I want `pypi_endoflife_raw` and `seed_spdx_upstream_list_raw` to load parsed JSON,
So that `seed_gaps_spdx_report` and `seed_gaps_lts_registry_report` stop reading an empty input.

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-atlas CAP-64 (FR-72) • AD-2, AD-13
**Flag:** none (a fix)
**Surface:** `conf/base/catalog.yml` (the two entries), a JSON-returning API dataset under `src/pyforge/atlas/datasets/`, the seed-gap nodes' input handling only if the shape changes, their tests
**Given** both entries are bare `api.APIDataset`, whose `load()` returns a `requests.Response`, and `report_lts_registry_gap` / `_spdx_upstream_ids` need a list or dict
**When** the catalog loads either entry
**Then** it returns the decoded JSON (endoflife.date's product list; SPDX's `licenses` document), the SPDX report holds rows on a fixture and on a live run, and an unreachable host degrades per AD-13
**And** a test feeds a recorded response and fails when the dataset returns a `Response` again (mutation)
**Status:** done

### Story 34.2: The Phase C mapping fills from the conda-forge bot's name mapping

As the PyPI-intelligence pipeline,
I want `pypi_parselmouth_mapping_raw` to read the bot's published `mappings/pypi/name_mapping.yaml`,
So that `pypi_conda_mapping`, and every PyPI-keyed dataset after it, fills on a fresh data root.

**Type:** fix • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-atlas CAP-64 (FR-72) • AD-10 (single writer), AD-13
**Flag:** none (a fix)
**Surface:** `datasets/core_sources.py` (`ParselmouthMappingDataset`), `conf/base/catalog.yml`, `conf/base/globals.yml` if a new endpoint override is needed, the catalog override-point pins, tests
**Given** `pypi_parselmouth_mapping_raw` reads `${paths.pypi_conda_map}`, which only `export_pypi_conda_map` writes, from the mapping it should produce
**When** a run starts on a fresh data root
**Then** the raw source loads the bot's YAML over `APIDataset` (`raw.githubusercontent.com/conda-forge/conda-forge-bot-data/main/mappings/pypi/name_mapping.yaml`), `pypi_conda_mapping` holds rows within the story's tolerance of legacy Phase C (11,005 matched conda rows, 2026-10-18), the g10 spelling and no-clobber rules hold, and `export_pypi_conda_map` stays the flat file's one writer
**And** `pypi_current_versions`, `pypi_intelligence_enriched` and `vcs_release_velocity` hold rows on the same run
**Status:** done

### Story 34.3: Dependencies, feedstock health and maintainers read the bot's split graph repos

As the core and VCS-health pipelines,
I want `core_cf_graph_raw` to read `node_attrs`, `pr_info` and `version_pr_info` from the repos the conda-forge bot now publishes them in,
So that `core_dependencies`, `core_feedstock_health` and the maintainer tables fill again.

**Type:** fix • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-atlas CAP-64 (FR-72) • AD-2, AD-13
**Flag:** none (a fix)
**Surface:** `datasets/core_sources.py` (`CfGraphTarballDataset`, `parse_cf_graph_tarball`), `conf/base/catalog.yml`, `conf/base/globals.yml` (endpoint overrides), the catalog override-point pins, `pipelines/vcs_health/nodes.py` (`enrich_maintainers` input columns only), tests
**Given** `regro/cf-graph-countyfair` now serves `conda-forge/conda-forge-bot-data`, whose tarball has no `node_attrs/`, `pr_info/` or `version_pr_info/`; cf-scripts publishes them in `conda-forge-bot-data-node_attrs`, `-pr_info` and `-version_pr_info`, five directories deep (`get_sharded_path`)
**When** the dataset loads
**Then** it reads the three split tarballs, walks the sharded paths, emits a `maintainers` column, and `core_dependencies`, `core_feedstock_health`, `vcs_maintainers` and `vcs_package_maintainers` hold rows; the feedstock count is checked against the bot's `all_feedstocks.json` (legacy reads nothing since the split, so it is not the oracle here)
**And** each source URL is an override point (AD-2), and an unreachable repo keeps last-good under `stale`
**Status:** done

### Story 34.4: The download tables fill from Anaconda's monthly parquet

As the core pipeline,
I want `S3DownloadStatsDataset` to read Anaconda's public monthly download parquet,
So that `core_downloads`, its three breakdowns and `core_version_download_history` fill.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-atlas CAP-64 (FR-72) • AD-5 (incremental), AD-13
**Flag:** `pyforge.atlas.live_public_sources` (shared by Epic 34's feature stories; registered by the first to land)
**Surface:** `datasets/core_sources.py` (`S3DownloadStatsDataset`), `datasets/request_datasets.py` (`fetch_one`'s ignored request key), `conf/base/catalog.yml`, flag registration (four places, `docs/reference/story-spec-flag-block.md`), tests
**Given** `S3DownloadStatsDataset.load()` returns an empty frame and `AnacondaDownloadsDataset.fetch_one` ignores its request key without a fetcher
**When** the core pipeline runs with the flag on
**Then** the five download tables hold rows within the story's tolerance of legacy Phase F (31,041 packages, 2026-10-18), month files cache incrementally, and `fetch_one` requests the key it is given
**And** with the flag off the stores keep last-good, unchanged from today
**Status:** done

### Story 34.5: The five OS-distro indexes refresh themselves

As the cross-channel signal,
I want the Homebrew, Nixpkgs, Spack, Debian and Fedora stores to own a public refresher,
So that `pypi_tier3_channel_flags` fills.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-atlas CAP-64 (FR-72) • AD-6 (amended 2026-10-18), AD-13
**Flag:** `pyforge.atlas.live_public_sources`
**Surface:** `datasets/tier3_sources.py`, `conf/base/catalog.yml`, `tools/bootstrap.py`'s expected-stale list, tests
**Given** `_Tier3PackagesDatasetBase` is constructed with no `fetcher`, so each store marks "refresh due but no refresher wired"
**When** a run reaches the stores with the flag on
**Then** each store fetches its index over `APIDataset`, holds rows, and `pypi_tier3_channel_flags` holds rows
**And** the bootstrap no longer lists the five as expected stale
**Status:** done

### Story 34.6: The public discovery stores refresh themselves

As the upstream-discovery and identity pipelines,
I want GitHub trending, the about-maintainers list, the purl associator, the Anaconda distribution 2026.x list and the AOSS premium list to own public refreshers,
So that `trending_candidates_classified`, `enterprise_conda_maintainers` and the public half of identity fill.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-atlas CAP-64 (FR-72) • AD-6 (amended), AD-13
**Flag:** `pyforge.atlas.live_public_sources`
**Surface:** `datasets/upstream_discovery.py`, `datasets/identity_sources.py`, `conf/base/catalog.yml`, `tools/bootstrap.py`'s expected-stale list, tests
**Given** these stores are constructed with no `fetcher`
**When** a run reaches them with the flag on
**Then** each fetches over `APIDataset`, holds rows, and the three downstream datasets hold rows
**And** the GitHub trending page is read unauthenticated (no credential)
**Status:** done

### Story 34.7: The vulnerability stores refresh themselves

As the vulnerability pipeline,
I want the vdb and OSV stores to own their refreshers,
So that `vulnerability_package_rollup` and `vulnerability_package_version_vulns` fill.

**Type:** feature • **Effort:** M • **Deps:** 34.4 (per-version rows need downloads) • **FR/AD:** spec-pyforge-atlas CAP-64 (FR-72) • AD-6 (amended), AD-13
**Flag:** `pyforge.atlas.live_public_sources`
**Surface:** `datasets/refresh.py` (`VDBStoreDataset`, `OSVOfflineStoreDataset`), `datasets/vdb_extract.py` (the extractor, run in the vuln-db env), `datasets/public_sources.py` (`fetch_bytes`), `datasets/core_sources.py` (the about URLs, `package_recipe_fields`), `pipelines/vulnerability/` (the trigger's purls and versions, Phase G's dedupe), `orchestration/definitions.py` (the budget), tests
**Given** both stores are constructed with no `refresher`
**When** a run reaches them with the flag on
**Then** the vdb store builds through `pyforge.core.process` (the vuln-db env's `vdb-refresh`) and is normalized to the store format, the OSV store fetches the public bucket, and both rollups hold rows within the story's tolerance of legacy Phase G (33,841 scanned, 2026-10-18)
**And** a failed build keeps last-good under `stale`
**Status:** done

### Story 34.8: Migration status fills through a driver node

As the VCS-health pipeline,
I want a single-writer node to drive the migration category and detail datasets,
So that `vcs_migration_readiness` fills.

**Type:** feature • **Effort:** S • **Deps:** 34.4 • **FR/AD:** spec-pyforge-atlas CAP-64 (FR-72) • AD-10, AD-13
**Flag:** `pyforge.atlas.live_public_sources`
**Surface:** `datasets/migration_status.py`, `pipelines/vcs_health/` (a driver node), `conf/base/catalog.yml`, the pipeline-inventory and single-writer pins, tests
**Given** `MigrationCategoryDataset.refresh` and `MigrationDetailDataset.fetch_partitions` are never called and the five category entries are consumed by no node
**When** the pipeline runs with the flag on
**Then** a driver node reads the bot's `status/migration_json` publicly, one partition per migration, and `vcs_migration_readiness` holds rows
**Status:** done

### Story 34.9: Phase P fills from the public ClickHouse mirror

As the PyPI-intelligence pipeline,
I want `pypi_downloads_monthly` to read legacy's free ClickHouse source,
So that PyPI download counts fill without BigQuery.

**Type:** feature • **Effort:** S • **Deps:** 34.2 • **FR/AD:** spec-pyforge-atlas CAP-64 (FR-72) • AD-6 (Phase P), AD-13
**Flag:** `pyforge.atlas.live_public_sources`
**Surface:** a ClickHouse download dataset under `datasets/`, `conf/base/catalog.yml`, `pipelines/pypi_intelligence/` (source selection), tests
**Given** only `PyPIBigQueryDownloadsDataset` exists and the operator ruled BigQuery off
**When** the pipeline runs with the flag on
**Then** `pypi_downloads_monthly` holds rows from the ClickHouse mirror within the story's tolerance of legacy Phase P (1,000 rows, top by 90-day downloads, 2026-10-18), and no BigQuery call is made
**Status:** done

### Story 34.10: Phase H covers every mapped PyPI project, gated by its serial

As the PyPI-intelligence pipeline,
I want the PyPI-JSON fan-out to fetch every mapped project that was never fetched, whose PyPI serial moved, or whose copy is 30 days old,
So that `pypi_current_versions` and everything after it cover the mapped universe, as legacy Phase H does.

**Type:** feature • **Effort:** M • **Deps:** 34.2 • **FR/AD:** spec-pyforge-atlas CAP-64 (FR-72) • AD-5 (incremental), AD-13
**Flag:** `pyforge.atlas.live_public_sources`
**Surface:** `datasets/request_datasets.py` (`PyPIJsonFanOutDataset`), `pipelines/pypi_intelligence/` (the trigger's inputs: the serial snapshot), `conf/base/catalog.yml` if a parameter moves, flag registration if this story lands first, tests
**Given** `PYPI_JSON_FANOUT_LIMIT` caps the fan-out at 200 names per run with a rotating offset, so the ~11k mapped names take about 55 runs to cover once (Story 34.2, measured 2026-10-18), while legacy Phase H (`_phase_h_eligible_pypi_names`, CFA:4168) fetches every never-fetched, serial-moved or 30-day-old row of the actionable universe
**When** the pipeline runs with the flag on
**Then** the fan-out's batch is that eligible set (serials from `pypi_universe_serial_snapshots`, stored per row at fetch), rate-limited and uncapped by default (`PYPI_JSON_FANOUT_LIMIT` stays an explicit cap), a 429 or 503 is retried with `Retry-After` as legacy Phase H does (Story 34.2 counts every `DatasetError`, 429/503 and timeouts included, as a per-project miss), and `pypi_current_versions` holds rows within the story's tolerance of legacy Phase H's coverage measured the same day
**And** a warm run with no serial movement fetches only the 30-day re-checks; with the flag off the fan-out keeps today's bounded behaviour
**Status:** done

### Story 34.11: The Phase C mapping fills legacy's name-coincidence and recipe-source tiers

As the PyPI-intelligence pipeline,
I want the PyPI-to-conda mapping to fill the two tiers legacy fills after parselmouth,
So that Phase H, the vdb scan and everything keyed on a PyPI name cover legacy's universe, not half of it.

**Type:** fix • **Effort:** M • **Deps:** 34.2 (the parselmouth tier), 34.3 (node_attrs) • **FR/AD:** spec-pyforge-atlas CAP-64 (FR-72) • AD-3, AD-13
**Flag:** `pyforge.atlas.live_public_sources` (the node_attrs and simple-index fetches it reads; the mapping itself is pure)
**Surface:** `datasets/core_sources.py` (each output's recipe `source_url` in the cf-graph frame), `pipelines/pypi_intelligence/` (`map_pypi_conda` and its inputs), `orchestration/definitions.py` (its budget), tests
**Given** `map_pypi_conda` maps only the bot's parselmouth names (10,967 on 2026-10-18), while legacy's Phase H universe is 20,938 names, because legacy also maps a PyPI project whose lower-cased name is the conda name (Phase D, CFA:1837-1895) and every output attributed to a feedstock whose recipe downloads from PyPI (Phase C.5 in Phase E, CFA:2434-2446) (`DW-atlas-34-10-1`)
**When** the pipeline runs
**Then** `pypi_conda_mapping` carries `name_coincidence` and `recipe_source_url` rows, each only for a package the tier before left unmapped, and its PyPI names cover legacy Phase H's universe within the story's tolerance, measured the same day
**Status:** done

### Story 34.12: A vulnerability feed that cannot be reached keeps its last good copy

As the Pages data build,
I want the CISA KEV, FIRST EPSS and MITRE CWE feeds to keep their last good frame when a fetch fails,
So that one unreachable host no longer stops the whole run.

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-atlas CAP-64 (FR-72) • AD-2, AD-13, AD-17
**Flag:** none (a fix)
**Surface:** `datasets/vulnerability_feeds.py` (`CisaKevDataset`, `EpssFeedDataset`, `CweCatalogDataset`), `datasets/__init__.py`, `provenance.py`, `conf/base/catalog.yml` (the three entries), the Spec companion `live-sources.md`, tests
**Given** the three feeds load through `APIDataset` with no fallback, so a connection failure raises `DatasetError` out of the catalog: kedro-viz-publish's Vizro job failed on five merges to main on 2026-10-23 with `vulnerability_cwe_catalog_raw: Failed to connect to the remote server` (`DW-atlas-38-1-1`)
**When** a feed's fetch fails, returns an HTTP error, or returns a body that does not parse to rows
**Then** the dataset serves its last good frame from `raw/<entry>/last_good.parquet` (or, on a fresh root, the empty frame of the feed's columns) under the AD-13 `.staleness.json` marker, never raises, and the run goes on; the bootstrap-index-health board shows the entry `stale` (on a fresh root `missing`) with the marker's reason, and provenance reports the copy's age
**And** each request carries a timeout and no `~/.netrc` credential; unit tests with no network cover a connect failure, an HTTP error, a malformed body and a fresh root, and fail when the fallback is removed (mutation)
**Status:** done

### Story 34.13: Atlas declares the brotli its nixpkgs store decodes

As the operator installing pyforge-atlas outside the conda-forge env,
I want the package to declare the brotli module its nixpkgs Tier-3 store imports,
So that a pip install decodes `packages.json.br` instead of marking the store stale.

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-atlas CAP-64 (FR-72) • AUD-ATLAS-010 (an undeclared import is a runtime dependency) • Dream 2026-10-25 (the nixpkgs store decodes brotli by luck) • operator ruling 2026-10-25 • closes `DW-atlas-34-5-1`
**Flag:** none (a fix)
**Surface:** `src/shared/packages/pyforge-atlas/pyproject.toml` (`brotli>=1.2`), `src/shared/packages/pyforge-atlas/pixi.toml` (`brotli-python = ">=1.2"`), `pixi.lock` (the pyforge-atlas source entries' run-dependencies), `tests/packaging/test_dependency_completeness.py` (the PyPI-to-conda name map), `docs/reference/library-llms-full.md` (the catalog bullet)
**Spec:** `planning-artifacts/specs/spec-34-13-atlas-declares-the-brotli-its-nixpkgs-store-decodes.md`
**Given** `datasets/tier3_sources.py` imports `brotli` through a guarded `importlib.import_module`, and the env has it only through conda-forge `urllib3`'s `brotli-python` dependency
**When** the story lands
**Then** both manifests declare it at `>=1.2`, `pixi.lock` records that string for every pyforge-atlas source entry, and a fresh pixi installs the env `--locked`
**And** `pyforge-deps-test` passes with the name map, `llms-full-check` passes, and `pixi run -e pyforge-atlas pyforge-atlas-test` green
**Status:** done

## Epic 35: VCS and registry fetches cover the full universe, credentialed on opt-in (spec-pyforge-atlas CAP-65, FR-73)

Minted 2026-10-18 with Epic 34, from the same Dream entry and rulings ("Full universe (Recommended)"; the opt-in
`PYFORGE_ATLAS_CREDENTIALED=1`). Supersedes Story 27.2's identity-derived batches. **HARD boundaries:**
- A request that carries a credential runs only under the opt-in; a transport fixture proves it in each story.
- Credentials attach to their own host only (AD-2); no token appears in a log, a dataset or a staleness marker.
- Feature stories ship behind `pyforge.atlas.live_vcs_universe`, whose OFF state is today's identity-scoped behaviour.

### Story 35.1: One opt-in switch, and GitHub authenticates

As an operator running a credentialed refresh,
I want `PYFORGE_ATLAS_CREDENTIALED=1` to be the one switch every credentialed dataset reads, and GitHub requests to carry a bearer header,
So that credentialed fetches run when I ask and never otherwise.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-atlas CAP-65 (FR-73) • AD-2, AD-11
**Flag:** `pyforge.atlas.live_vcs_universe`
**Surface:** `settings.py` / `conf/base/globals.yml` (the switch, read through `env_or`), `datasets/vcs_sources.py`, `datasets/request_datasets.py` (an `AuthBase` built from `github_token`), the credential-scoping pins, flag registration, tests
**Given** the `github_token` dict cannot authenticate `kedro_datasets.api.APIDataset`, and no switch separates credentialed from public runs
**When** a credentialed dataset loads
**Then** without the switch it keeps last-good under `stale` and sends nothing; with it, GitHub requests carry `Authorization: Bearer` to the GitHub host only
**And** a transport fixture fails if any request carries a credential without the switch (mutation)
**Status:** done

### Story 35.2: The VCS batches come from the whole universe

As the VCS-health pipeline,
I want the GitHub, GitLab, Codeberg and registry batches built from the actionable conda-forge universe,
So that the fetches cover what legacy Phases K, L and N cover.

**Type:** feature • **Effort:** M • **Deps:** 34.3 (node_attrs), 34.7 (the about URLs on the frame), 35.1 (the flag) • **FR/AD:** spec-pyforge-atlas CAP-65 (FR-73)
**Flag:** `pyforge.atlas.live_vcs_universe`
**Surface:** `pipelines/vcs_health/vcs_refresh_identifiers.py`, `pipelines/vcs_health/nodes.py` and `pipeline.py` (the refresh trigger inputs), `datasets/refresh.py` (`RefreshRequest`), `datasets/request_datasets.py` and `datasets/vcs_sources.py` (the stores read the flag), tests
**Given** `batches_from_identity` builds every batch from `identity_packages_primary`, the OpenTeams subset
**When** the refresh triggers run with the flag on
**Then** the batches come from package enumeration joined with node_attrs' repo, dev and homepage URLs and registry names, upstream (K) separate from feedstock (E.5, N), and a population test proves identity no longer drives them
**Status:** done

### Story 35.3: Upstream versions and feedstock health come from GitHub

As the VCS-health pipeline,
I want the GitHub query to read releases and tags for upstream repos and health for feedstock repos, batched,
So that `vcs_upstream_versions`, `vcs_live_health` and `vcs_archived_feedstocks` fill.

**Type:** feature • **Effort:** L • **Deps:** 35.1, 35.2 • **FR/AD:** spec-pyforge-atlas CAP-65 (FR-73) • AD-13
**Flag:** `pyforge.atlas.live_vcs_universe`
**Surface:** `datasets/request_datasets.py` (`fetch_github`, the Phase K, N and E.5 queries, the store's `(kind, key)`), `pipelines/vcs_health/nodes.py` (the three consumers), `orchestration/definitions.py` (the budget), tests
**Given** `fetch_repo_health` asks only for archived status, stars, last push and open issues, so `upstream_version` is always NA
**When** a credentialed run reaches the GitHub stores
**Then** the three datasets hold rows within the story's tolerance of legacy K (23,896 fetched), N (28,682 feedstocks) and E.5 (864 archived), all measured 2026-10-18
**Status:** done

### Story 35.4: GitLab, Codeberg and the eight registries fill

As the VCS-health pipeline,
I want the GitLab, Codeberg and registry stores fetched live for the universe population,
So that `vcs_registry_versions` and the non-GitHub upstream versions fill.

**Type:** feature • **Effort:** M • **Deps:** 35.2 • **FR/AD:** spec-pyforge-atlas CAP-65 (FR-73) • AD-2, AD-13
**Flag:** `pyforge.atlas.live_vcs_universe`
**Surface:** `datasets/vcs_sources.py` (the hosts' release-then-tag path, the registries' version choices), `datasets/credentials.py` (`HeaderAuth`, `gitlab_auth`), `conf/base/catalog.yml` (crates and rubygems at one request a second), tests
**Given** the stores are live-capable but their batches were empty
**When** a run reaches them with the flag on
**Then** `vcs_registry_versions` holds rows within the story's tolerance of legacy L (375, 2026-10-18), and GitLab and Codeberg upstream versions within legacy K's GitLab (400) and Codeberg (26) counts; public registries send no credential
**Status:** done

## Epic 36: Basilisk, the OpenTeams identity sources and the estate source (spec-pyforge-atlas CAP-66..CAP-68, FR-74..FR-76)

Minted 2026-10-18 with Epics 34 and 35 (the operator's extras: "Basilisk vulns, OpenTeams identity sources,
Estate-source producer"). Two of its stories start from an open question on the Spec (`## Open Questions —
2026-10-18`), settled with the operator before the story's spec is written. **HARD boundaries:** as Epic 35's for
credentials; each feature story names its own flag.

### Story 36.1: The Basilisk population runs

As the vulnerability pipeline,
I want the public Basilisk package listing refreshed on every run, and driver nodes to query Basilisk for the conda PURL population and fetch details for matched advisories under the opt-in,
So that the listing fills unattended and the three Basilisk datasets fill once the operator supplies a token.

**Type:** feature • **Effort:** M • **Deps:** 35.1 (the opt-in switch) • **FR/AD:** spec-pyforge-atlas CAP-66 (FR-74, amended 2026-10-18 by operator ruling) • AD-2, AD-13, AD-14
**Flag:** `pyforge.atlas.basilisk_population` (the drivers); the listing's refresher reads `pyforge.atlas.live_public_sources`, as the other public discovery stores do
**Surface:** `datasets/basilisk.py` (the listing's refresher, the two drivers), `datasets/credentials.py` (`basilisk_auth`), `datasets/refresh.py` (`RefreshRequest`), `pipelines/vulnerability/` (the two trigger nodes), `orchestration/definitions.py` (their budgets), `tools/bootstrap.py`, flag registration, README, tests
**Given** `query_population` and `fetch_details` are never called, `load()` returns last-good even with a fetcher, the package listing has no refresher (`DW-atlas-34-6-2`), and the advisory endpoints answer 401 without a bearer token (probed 2026-10-18)
**When** the pipeline runs with the flag on
**Then** a plain run with network fills `discovery_basilisk_packages_raw`; against a recorded fixture the advisories, details and rollup fill; without `PYFORGE_ATLAS_CREDENTIALED=1` no request carries a credential and the three stores keep last-good under `stale`
**And** with the opt-in and a Basilisk token in `PYFORGE_ATLAS_BASILISK_TOKEN`, a live run's population equals `core_packages_enumerated`'s row count (operator-attended; no token exists today)
**Status:** done

### Story 36.2: The OpenTeams board and the staged-recipes PRs fill on opt-in

As the identity pipeline,
I want the OpenTeams project board and the staged-recipes PR list fetched with `github_token` under the opt-in,
So that `identity_packages_primary`, the identity exports and the inventory priorities fill.

**Type:** feature • **Effort:** M • **Deps:** 35.1, 34.6 • **FR/AD:** spec-pyforge-atlas CAP-67 (FR-75) • AD-2, AD-11
**Flag:** `pyforge.atlas.identity_live_sources`
**Surface:** `datasets/identity_sources.py` (`OpenTeamsBoardDataset`, `StagedRecipesPRDataset`: their credentialed refreshers), flag registration, tests
**Given** both datasets are constructed with no `fetcher`
**When** a credentialed run reaches them with the flag on
**Then** `identity_packages_primary` holds rows from each `identity_source`, and `identity_complete_export` and `inventory_priority_assignments` hold rows; without the opt-in no request carries a credential
**Status:** done

### Story 36.3: The query-plane estate source has a producer

As the query plane,
I want a named atlas node to write `query_plane_estate_source`,
So that `query_plane_cache` builds the estate cache from data.

**Type:** feature • **Effort:** M • **Deps:** — (BLOCKED, operator ruling 2026-10-18: deferred until a steward story exports the platform tables through `pyforge.core.station_port`; atlas never reads platform OLTP directly) • **FR/AD:** spec-pyforge-atlas CAP-68 (FR-76) • canopy FR-47 • AD-1
**Flag:** `pyforge.atlas.estate_source_producer`
**Surface:** decided with the steward export (a node under `pipelines/query_plane_cache/`, its catalog entry, tests); the export itself is a steward story
**Given** steward Story 34.2 declared `query_plane_estate_source` and nothing produces it
**When** `pyforge atlas run --pipelines query_plane_cache` runs on a fresh data root with the flag on
**Then** it exits 0, writes `query_plane_estate`, and the estate model answers its measures
**Status:** blocked

## Epic 37: The Vizro boards read what the pipelines write, on Pages too (spec-pyforge-atlas CAP-63 amended, CAP-69, FR-71, FR-77)

Minted 2026-10-19 from the Dream entry of that date and the operator's rulings ("Data-first + 10 rewires",
"Public-only Pages", "Weekly + on push"). With Epics 34-36 filling the stores, 31 of the 34 boards still rendered
honest-empty: the Pages job had no data, the dashboard read another data root than Kedro writes, and 20 of the 27
board paths were no catalog entry's `filepath`. **HARD boundaries:** the Pages job runs public sources only (no secret,
no `PYFORGE_ATLAS_CREDENTIALED`, BigQuery off; AD-11); a board's dimension names stay; the export never publishes a board
that declares an access column (`sld:AD-10`). Stories 37.5-37.10 are the boards no pipeline feeds, at backlog by ruling.

### Story 37.1: The dashboard reads the data root Kedro writes

As the operator,
I want the dashboard and its static export to read the data root Kedro writes,
So that a local `pyforge atlas run` shows on the boards.

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-atlas CAP-69 (FR-77) • AD-8, AD-17
**Surface:** `dashboard/data.py` (`default_data_root`), tests
**Given** `default_data_root()` walks up to `.git` and resolves `<repo>/data`, which holds only `raw/`, while Kedro writes `src/shared/packages/pyforge-atlas/data`
**When** `dashboard-dryrun` runs after a local `pyforge atlas run` with no `PYFORGE_ATLAS_DATA_ROOT`
**Then** each wired board reads that run's data, and `PYFORGE_ATLAS_DATA_ROOT` still wins when set
**Status:** done

### Story 37.2: The Pages Vizro export builds the public atlas data first

As a Pages reader,
I want the published boards built from a fresh public atlas run,
So that the boards on `/dashboard/vizro/` carry data rather than honest-empty notices.

**Type:** feature • **Effort:** M • **Deps:** 37.1 • **FR/AD:** spec-pyforge-atlas CAP-63 amended 2026-10-19 (FR-71) • AD-11, AD-21, sld:AD-10
**Flag:** `pyforge.atlas.vizro_static_boards` (Story 30.2's)
**Surface:** `.github/workflows/kedro-viz-publish.yml` (the `vizro` job: a weekly schedule, the data build, its timeout), `tools/vizro_static_export.py`, `dashboard/static_export.py` (the static row cap, DW-atlas-37-3-1), the CI surface registry if the schedule is declared there, tests
**Given** the `vizro` job exports on a runner with no atlas data
**When** it runs weekly, on push or by dispatch
**Then** it writes the credentials stub, runs `pyforge atlas run` over the public pipelines with no `PYFORGE_ATLAS_CREDENTIALED`, exports against that data root and uploads the artifact; credentialed and enterprise sources stay empty, and the identity boards show what public inputs give them (operator ruling 2026-10-21)
**Status:** done

### Story 37.3: The seed-gap, version-download and distribution boards read their datasets

As the operator,
I want the six boards whose content a pipeline already writes to read it,
So that they render rows instead of "backing file not found".

**Type:** fix • **Effort:** M • **Deps:** 37.1 • **FR/AD:** spec-pyforge-atlas CAP-69 (FR-77) • AD-8
**Surface:** `dashboard/data.py` (paths), `semantic/models.py` (expressions), `pipelines/derived_artifacts` (the distribution table's compose node), `conf/base/catalog.yml`, `definitions.py`, `dashboard/app.py` (the two boards' notes), `tests/fixtures/data` and `build_fixture_data.py`, tests
**Given** the four seed-gap boards read `primary/<x>_gap/` while `seed_gaps` writes `derived/seed_gaps_<x>_report/`, and version-downloads and distribution-breakdown read paths nothing writes
**When** a run has written `seed_gaps`' reports, `core_version_download_history` and the three `core_downloads_*_breakdown` tables
**Then** the six boards render those rows with their dimension names unchanged
**Status:** done

### Story 37.4: Behind-upstream, whodepends, live-catalog coverage and the universe SBOM boards fill

As the operator,
I want the two shell boards to get their models and the two coverage boards their projections,
So that four more boards render rows from a public run.

**Type:** feature • **Effort:** M • **Deps:** 37.1 • **FR/AD:** spec-pyforge-atlas CAP-69 (FR-77) • AD-8, AD-14
**Flag:** `pyforge.atlas.board_projections`
**Surface:** `semantic/models.py` (two models), `dashboard/data.py`, `dashboard/app.py`, `dashboard/static_export.py`, three projection nodes in `derived_artifacts` (behind-upstream, whose PEP 440 lag labels SQL cannot express; live-catalog coverage; the SBOM summary) with their catalog entries and node timeouts, the flag in `src/platform/config/`, tests
**Given** behind-upstream and whodepends have no model and live-catalog-coverage and universe-sbom read paths nothing writes
**When** a run has written `vcs_upstream_versions`, `core_dependencies`, the inventory flags and the universal SBOM
**Then** the four boards render rows; with the flag off they read as before
**Status:** done

### Story 37.5: The cve-watcher reads a vulnerability history

As the operator,
I want a node to append each run's vulnerability rollup as a dated snapshot and diff the two latest,
So that the cve-watcher board shows what changed since the last scan (legacy `vuln_history`, `cve_watcher.py`).

**Type:** feature • **Effort:** M • **Deps:** 37.1 • **FR/AD:** spec-pyforge-atlas CAP-69 (FR-77, the boards no pipeline feeds; operator ruling 2026-10-19: backlog) • AD-8, AD-14
**Surface:** a node and catalog entry under the pipeline that owns its inputs, `dashboard/data.py`, `semantic/models.py`, tests
**Given** no pipeline writes the board's dataset
**When** a run has written two runs' `vulnerability_package_rollup`
**Then** cve-watcher renders the packages whose counts moved, with `since_days` and the KEV flag
**Status:** done

### Story 37.6: The release-cadence reads per-version upload times

As the operator,
I want the per-version upload time legacy reads from `package_version_downloads.upload_unix`,
So that the release-cadence board counts releases in 30, 90 and 365 days.

**Type:** feature • **Effort:** M • **Deps:** 37.1 • **FR/AD:** spec-pyforge-atlas CAP-69 (FR-77, the boards no pipeline feeds; operator ruling 2026-10-19: backlog) • AD-8, AD-14
**Surface:** a node and catalog entry under the pipeline that owns its inputs, `dashboard/data.py`, `semantic/models.py`, tests
**Given** no pipeline writes the board's dataset
**When** a run has written a source of per-version upload times (the anaconda.org files API or the full repodata)
**Then** release-cadence renders `releases_30d`, `releases_90d` and `releases_365d` per package
**Status:** done

### Story 37.7: The find-alternative scores candidates for archived packages

As the operator,
I want a node that scores alternatives for each archived package as legacy `find_alternative.py` does per query,
So that the find-alternative board lists candidates without a live query.

**Type:** feature • **Effort:** M • **Deps:** 37.1 • **FR/AD:** spec-pyforge-atlas CAP-69 (FR-77, the boards no pipeline feeds; operator ruling 2026-10-19: backlog) • AD-8, AD-14
**Surface:** a node and catalog entry under the pipeline that owns its inputs, `dashboard/data.py`, `semantic/models.py`, tests
**Given** no pipeline writes the board's dataset
**When** a run has written `vcs_archived_feedstocks`, `semantic_packages` and the package summaries
**Then** find-alternative renders candidates with `similarity_score` and `adoption_stage`
**Status:** done

### Story 37.8: The export-purls lists the PURL artifacts

As the operator,
I want the six legacy `export_purls.py` artifacts and a manifest of them,
So that the export-purls board shows each artifact, when it was built and its rows.

**Type:** feature • **Effort:** M • **Deps:** 37.1 • **FR/AD:** spec-pyforge-atlas CAP-69 (FR-77, the boards no pipeline feeds; operator ruling 2026-10-19: backlog) • AD-8, AD-14
**Surface:** a node and catalog entry under the pipeline that owns its inputs, `dashboard/data.py`, `semantic/models.py`, tests
**Given** no pipeline writes the board's dataset
**When** a run has written `core_packages_enumerated`, `pypi_conda_mapping` and the vulnerability rollup
**Then** export-purls renders one row per artifact with `regenerated_at` and `row_count`
**Status:** done

### Story 37.9: The mapping-gap classifies the unmapped packages

As the operator,
I want legacy `mapping_gap.py`'s classification over `pypi_conda_mapping`,
So that the mapping-gap board says why a package has no PyPI name.

**Type:** feature • **Effort:** M • **Deps:** 37.1 • **FR/AD:** spec-pyforge-atlas CAP-69 (FR-77, the boards no pipeline feeds; operator ruling 2026-10-19: backlog) • AD-8, AD-14
**Surface:** a node and catalog entry under the pipeline that owns its inputs, `dashboard/data.py`, `semantic/models.py`, tests
**Given** no pipeline writes the board's dataset
**When** a run has written `pypi_conda_mapping`, `core_packages_enumerated` and the cf-graph source URLs
**Then** mapping-gap renders `classification`, `match_source` and `match_confidence` per package
**Status:** done

### Story 37.10: The bootstrap-index-health reports each catalog entry's freshness

As the operator,
I want a node that reads every catalog entry's last write and row count,
So that the bootstrap-index-health board shows which datasets are stale or empty.

**Type:** feature • **Effort:** M • **Deps:** 37.1 • **FR/AD:** spec-pyforge-atlas CAP-69 (FR-77, the boards no pipeline feeds; operator ruling 2026-10-19: backlog) • AD-8, AD-14
**Surface:** a node and catalog entry under the pipeline that owns its inputs, `dashboard/data.py`, `semantic/models.py`, tests
**Given** no pipeline writes the board's dataset
**When** a run has written the catalog and each dataset's staleness marker
**Then** bootstrap-index-health renders `catalog_entry`, `tier`, `regenerated_at` and `row_count`
**Status:** done

### Story 37.11: A board's note reads "Data gap" only where data is missing

As a reader of the Vizro boards, live or on Pages,
I want a board that shows data to describe it, not to call its own note a data gap,
So that "Data gap" means the board's data is missing.

**Type:** fix • **Effort:** XS • **Deps:** — • **FR/AD:** spec-pyforge-atlas CAP-63 and CAP-69 (FR-71, FR-77; no new CAP); AD-17 • **Flag:** none (`spec-feature-flag-governance` Q1)
**Surface:** `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/{app.py,static_export.py}`, `tests/unit/test_dashboard_app.py`, `tests/unit/test_dashboard_static_export.py`
**Spec:** `planning-artifacts/specs/spec-37-11-a-board-s-note-reads-data-gap-only-where-data-is-missing.md`
**Given** `dashboard/app.py` labels every `PageDef.note` "**Data gap:**", so a board with data (behind-upstream's 95 rows on Pages) reads as a gap
**When** a note on a page with a data function and an available dataset reads "**About this board:**", and "**Data gap:**" stays for a shell page, the identity workbook's `gap_message`, and a page whose AD-17 provenance is unavailable
**Then** every board's label matches its data: over Story 37.2's public-run data root, 15 boards read "About this board" (each with a stamped dataset) and 15 read "Data gap" (each with an unavailable stamp)
**And** the static export still drops a live-scan note under either label; no board's data or note text changes; the atlas unit and dashboard integration tests pass
**Status:** done

### Story 37.12: The Pages data build keeps its last good copies between runs

As a Pages reader,
I want the Pages data build to start from the previous run's last good copies,
So that a public source that cannot be reached on build day shows its previous data, marked stale, instead of an empty table.

**Type:** fix • **Effort:** S • **Deps:** 34.12 • **FR/AD:** spec-pyforge-atlas CAP-63 amended 2026-10-19 (FR-71) and CAP-64 (FR-72; no new CAP) • AD-11, AD-13, AD-17
**Flag:** none (a fix; the job's steps stay behind Story 30.2's `pyforge.atlas.vizro_static_boards`, as every step of the job is)
**Surface:** `.github/workflows/kedro-viz-publish.yml` (the `vizro` job: a cache restore before the build, a cache save after it), `tests/unit/test_vizro_static_boards.py`
**Spec:** `planning-artifacts/specs/spec-37-12-the-pages-data-build-keeps-its-last-good-copies-between-runs.md`
**Given** the `vizro` job builds on a fresh data root every run, so Story 34.12's last-good fallback has no copy there and an outage publishes the feed's table empty (the bootstrap-index-health board reads `missing`)
**When** the job runs after a run whose build succeeded
**Then** it restores that run's `data/raw`, `data/stores/*` and vulnerability snapshot history (never `data/stores/vdb`, no other output-layer file) from the repository's Actions cache before the build and saves its own after a build that succeeds, so an unreachable public source serves the previous copy under its AD-13 marker (`stale`, with the reason) and the cve-watcher has an earlier snapshot to diff; the copies reach the weekly run once the operator raises the cache limit (operator ruling 2026-10-24, `DW-atlas-37-12-1`)
**And** the job stays public-only (no secret, no token, no `PYFORGE_ATLAS_CREDENTIALED`; AD-11), a failed build still fails the job and saves nothing, and the workflow test pins the steps' order, paths, key and gate, and that every last-good store under the data root is cached
**Status:** done

### Story 37.13: The cve-watcher marks an earlier run's diff stale

As a Pages reader,
I want the cve-watcher to date its diff by its latest snapshot and say when that snapshot is not the last run's,
So that a run whose vulnerability database build failed never shows the previous run's diff as current.

**Type:** fix • **Effort:** S • **Deps:** 37.5, 37.12 • **FR/AD:** spec-pyforge-atlas CAP-69 (FR-77) and CAP-64 (FR-72; no new CAP) • AD-13, AD-17
**Flag:** `pyforge.atlas.board_projections` (Story 37.5's; the board change is on its on path only)
**Surface:** `datasets/snapshot_history.py` (the AD-13 marker), `provenance.py` (the snapshot store's stamp), `dashboard/app.py` (the cve-watcher's stamp and the stamp line's reason), `dashboard/data.py` (the store's path), tests
**Spec:** `planning-artifacts/specs/spec-37-13-the-cve-watcher-marks-an-earlier-run-s-diff-stale.md`
**Given** a Pages run whose vulnerability database build fails, so `vulnerability_package_rollup` is empty, the snapshot store is unchanged, and the diff equals the run before under the diff file's fresh mtime (DW-atlas-37-12-3)
**When** the cve-watcher board is built with `pyforge.atlas.board_projections` on
**Then** its AD-17 stamp is the older of its latest snapshot's time and the diff file's mtime, and the stamp line says `stale` with the reason while `SnapshotHistoryDataset` carries the AD-13 marker it writes on a save that appends no snapshot (removed by the next save that appends one); with no snapshot store the board reads as a data gap
**And** the diff, its columns, the catalog and the node count do not change; with the flag off the board is stamped as before; no other board's stamp changes
**Status:** done

## Epic 38: The semantic store has its upload times and archived flag (spec-pyforge-atlas CAP-69, FR-77)

Minted 2026-10-24 from the Dream entry of that date, closing DW-atlas-37-6-2 and DW-atlas-37-7-2. Story 37.6 streams
every conda-forge version's upload times out of the full repodata; `semantic_packages` still declares its upload
inputs NULL and reads the archived flag only from the GitHub query a public run leaves empty, so the adoption-stage,
staleness and find-alternative boards read "unknown" or fresh. **HARD boundaries:** no core output changes; the
boards' dimension names stay; the version-downloads path moves behind `pyforge.atlas.board_projections`.

### Story 38.1: The semantic store reads its upload times and archived flag

As the operator,
I want `semantic_packages` to carry each package's latest upload, its age, its 30-day releases and its version count,
and the archived flag the cf-graph holds, and version-downloads to show each version's upload date,
So that the adoption-stage, staleness, find-alternative and version-downloads boards read real lifecycle data.

**Type:** feature • **Effort:** M • **Deps:** 37.6 • **FR/AD:** spec-pyforge-atlas CAP-69 (FR-77) • pyforge-atlas:AD-8, AD-13, AD-14
**Flag:** `pyforge.atlas.board_projections` (the version-downloads path)
**Surface:** `datasets/repodata_uploads.py` (each version's newest build and its file time), `pipelines/derived_artifacts/{release_cadence,alternatives,lifecycle,pipeline}.py`, `pipelines/semantic_packages/{nodes,pipeline}.py`, `semantic/{metrics,models}.py`, `dashboard/{app,data}.py`, the catalog and node timeouts, the `pyforge-atlas-bootstrap` task in `pixi.toml` and the Pages job in `.github/workflows/kedro-viz-publish.yml` (one DAG with `semantic_packages`), docs, tests
**Spec:** `planning-artifacts/specs/spec-38-1-the-semantic-store-reads-its-upload-times-and-archived-flag.md`
**Given** `semantic_packages` declares its four upload inputs NULL and marks no feedstock archived on a public run, and version-downloads' `upload_date` is null
**When** a run has written `core_repodata_uploads_raw`, `core_packages_enumerated`, the cf-graph and the attribution
**Then** `semantic_packages` carries `latest_conda_upload`, `latest_upload_age_days`, `releases_30d` and `total_versions` as legacy derives them, and `feedstock_archived` from either source
**And** with the flag on, version-downloads reads each version's `upload_date`; the adoption-stage board classifies packages out of `unknown`
**Status:** done

## Epic 39: The atlas PRD's FR arrows name the capabilities the Spec carries

Minted 2026-10-25 from the station Dream's entry of the same date (the PRD's FR arrows were counted, not traced), at
the operator's rulings "Approve as proposed (Recommended)", "Drop the arrow (Recommended)" and "Append a correction
(Recommended)". The 2026-09-17 one-chain fold appended an `← CAP-n` arrow to every FR heading by counting, so
FR-1..FR-22 read CAP-1..CAP-22 and FR-61..FR-68 read CAP-1..CAP-8, and only four of those 30 name the capability that
realizes them. A chore under `spec-one-chain-per-station` CAP-5 and CAP-3: no CAP is minted and no flag is added. It
is a new epic because the concern is the PRD's traceability, not any capability epic.
**HARD boundaries:**
- Only the 23 approved arrows change, plus the two fold-written lines the rulings name; no FR title, body or number
  moves.
- FR-15, FR-61 and FR-63 keep their arrows until the operator decides their source capability.
- No `SPEC.md` change, no detector rule change, and no satellite FR is touched.

### Story 39.1: Every atlas PRD FR arrow names the Spec capability that realizes it

As the operator reading the atlas PRD to learn which capability a requirement serves,
I want every `FR-n ← CAP-m` arrow to name the capability the Spec actually carries,
So that a requirement traces to its contract instead of to a number the fold counted.

**Type:** chore • **Effort:** S • **Deps:** — • **FR/AD:** spec-one-chain-per-station CAP-5 (FRs derive from CAPs) and CAP-3 (the station fold procedure) • Dream 2026-10-25 (the PRD's FR arrows were counted, not traced) • operator rulings 2026-10-25
**Flag:** none (`spec-feature-flag-governance` Q1, a chore)
**Surface:** `planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md` (23 FR headings, the `### FR-61..FR-68 delivered` heading, the fold-provenance line and a currency-reconciliation section); the spine and epics `updated:` re-stamps; the deferred-work ledger row for FR-15, FR-61 and FR-63
**Spec:** `planning-artifacts/specs/spec-39-1-every-atlas-prd-fr-arrow-names-the-spec-capability-that-realizes-it.md`
**Given** `f8803da678`, where the fold commit `86d1cdf3ee` numbered FR-1..FR-22 and FR-61..FR-68's arrows by counting
**When** the story lands
**Then** each of the 23 headings carries the arrow in the spec-pyforge-atlas memlog's 2026-10-25 re-map table, every cited CAP exists, and FR-15, FR-61 and FR-63 are named as awaiting a source-capability decision
**And** doctor's `fr-without-cap` and the planning detectors stay green
**Status:** done

## Validation note — 2026-08-26 (chain-currency sweep)

Validated against the architecture spine as re-cut today (its `## Currency
reconciliation — 2026-08-26` + the AD-3 amendment). Findings, none requiring a
heading or status change:

- **Story-to-architecture fit holds.** Epics 12–19 all land inside the amended
  AD-3 shape: 13.x built `upstream_discovery` and 15.x `artifactory_downloads` as
  governed new pipelines; no story wrote into the sealed seven from outside them.
  Epic 18's audit-don't-rebuild outcome (`cap18.py` maps existing hooks; no second
  plugin API) matches AD-1; Epic 19's ACs (persona uses only `pyforge atlas …` +
  `POST /stations/atlas/mcp`; portal renders via PortalClient only) match the
  spine's two-MCP-faces note and the canopy contract.
- **Foreign AD/FR namespaces are cited correctly.** The `canopy:AD-21` / `canopy
  FR-37/38/10` references in Epics 18–19 belong to the unifying-strategy
  architecture, not this project's AD-1..AD-23/FR-1..FR-22 — disambiguated in the
  spine's reconciliation section; the epic text needs no edit.
- **CAP-19 stories (canopy 34.1–34.5, Lane 3 36.1–36.2) are deliberately NOT
  minted here** although their code lands in this station's surface — they are
  tracked on the steward chain (one story in flight per station; the strategy SPEC
  forbids re-dispatching 18–37). This file remains the canonical story source for
  atlas-keyed ledger stories only (marshal:AD-72 role unchanged).
- **Numbering is as intended:** Epic 11 does not exist (10 → 12 by design — Epic
  10 was the post-audit insertion, 12+ the post-migration chains), and the earlier
  duplicate-Epic-16 numbering was resolved by the 2026-08-22 correct-course
  (`c388980450`); one Epic 16 heading remains.
- **Statuses spot-checked against the tracked ledger** (12.1–13.5, 14.1–14.4,
  15.1–15.3, 16.1–16.2, 18.1, 19.1–19.2 done; 17.1–17.2 done with Epic 17's
  attended live-execution verification carried on the Spec, which reads
  `in-progress`): no rollup drift found in this pass. `epics→sprint` currency
  self-heals via the daily ledger stamp.

---

## Course-correction note — 2026-08-30 (workbook retirement)

Trigger: Story 21.3 (PR #941), the first story on any station to reach marshal's automated
`dispatch → verify → land` path, was held because `--live-catalog-only` read as "workbook-
free" while `records`/`tab_packages` still came from `docs/Analysis_Dataset-2026-08-12.xlsx`
(an untracked 11 MB local file). Findings and changes (`change-history/sprint-change-proposal-2026-08-30.md`):

- **21.3 landed at its contracted scope** (three Tier 0 verification sets — `stories.yaml`:
  "Thin metrics.py only"); the help text was accurate. Marked `done`.
- **Gap 1 — no story owned the metrics-side universe cutover.** Minted **23.8**
  (`inventory_universe` Kedro dataset + `--analysis-xlsx` optional; Deps S-21.4, S-21.5).
- **Gap 2 — 23.4's row grain.** Its spec names `identity_packages_primary` (~7.5k OpenTeams
  universe) but deliverable A is the ~38k full-inventory union; 23.4 now depends on 23.8.
- **Gap 3 — nothing removed the workbook code.** Minted **23.9** (identity/priority/
  dashboards/metrics thin-out, `openpyxl` gone from `scripts/`; Deps S-23.4, S-23.5, S-23.6,
  S-23.8, S-22.1). 23.7 now depends on 23.8 + 23.9 and gates the quartet as well as bootstrap.
- **Known residue, operator decision:** `10kClosed` (10,000 rows) has no catalog source; 23.8
  reports the delta instead of seeding it (SPEC Non-goal: no workbook mirror).
- **Drain order** (marshal `fleet-drain-queue.yaml`, xlsx-elimination critical path first, deps
  respected): 21.4 → 21.5 → 21.6 → **23.8** → 21.7 → 21.8 → 23.1 → 23.2 → 23.3 → 23.4 → 22.1 →
  23.5 → 23.6 → **23.9** → 22.2 → 22.3 → 22.4 → 22.5 → 23.7 → 22.6 → 21.9 → 21.10.
- Epic 21's `Deps:` chain is unchanged; stories 21.4–21.10 were never blocked by scope, only by
  21.3's hold.


## Test-tree convergence — reconciled 2026-09-07

`pyforge-atlas`'s tests moved to the fleet standard (`tests/unit/` + `tests/meta/`, with
`tests/fixtures/` never collected) under marshal Story 32.5,
`spec-fleet-consistency-standard` CAP-2. Fifteen loose root-level test files and **22 topic
directories** (catalog, pipelines, wasm, publish, dashboard, …) now live at
`tests/unit/<topic>/` with their structure intact.

The domain taxonomy is preserved deliberately: nesting by domain *under* a suite is
conformant, inventing a sibling of `unit/` for a domain is not. Atlas is the station where
that distinction matters most — its topic directories mirror the Kedro pipeline layout, not
a test-level split.

Consequence for this chain: the coverage gate's suite map now sees atlas's whole tree. It
previously resolved only `tests/meta/`, so the great majority of atlas's 129 test files were
measured by nothing. 1735 tests pass, 18 skipped, after the move.

Also: `pyforge-atlas-test` now exists as the canonical pixi task name (CLAUDE.md documents
`pyforge-<station>-test` as the fleet grammar, and atlas was the one station where that
command did not resolve); `kedro-test` is retained as a delegating alias.

## Currency reconciliation — 2026-09-20

*Chain-currency sweep: `spec-pyforge-atlas/.memlog.md` gained a 2026-09-20 event (the fleet
consistency pass reconciled 56 tracked story specs' frontmatter against the sprint ledger and
reconstructed missing Auto Run Results from git), which post-dated this artifact through the
`spec→prd→arch→epics` cascade. It is bookkeeping, not a capability: no requirement, decision or
story changes here. `updated:` bumped to record that the check ran.*

## Currency reconciliation — 2026-09-28

`arch→epics` edge after the spine's 2026-09-28 re-stamp (§ Currency reconciliation — 2026-09-28: FR-69 / CAP-61 lands on
AD-1, AD-2, AD-3, AD-4, AD-5, AD-6 and AD-13 as written; no AD added, amended or removed). Epic 25 (Stories 25.1–25.2)
decomposes CAP-61. **25.1** is minted `blocked` on mason Story 21.1 (the git-pkgs conda package): the Deps parser is
station-local, so the gate is prose on the `**Deps:**` line and the operator flips the row. Story 24.4's text named
"Story 25.2" three times for what the 2026-09-17 rekey made Story 24.2 (`rekey-2026-09-17.md`); those citations now read
24.2, and the BS-5 note's "do not duplicate Story 25.2" now names steward's Story 25.2, so neither can be taken for
the new atlas Story 25.2. Every Story heading still maps 1:1 to a `sprint-status-ledger.yaml`
key (`25-1`, `25-2` and `epic-25` added, `epic-25-retrospective` at `optional`, through the Tier-3 feed and
`sprint-ledger-sync`). `updated:` bumped.

## Currency reconciliation — 2026-10-03

`arch→epics` edge after the spine re-stamp of 2026-10-03 (marshal Story 66.2 (`pyforge-marshal:CAP-275`) backfilled a `DW-FRR-<story>` row into every station's tracked deferred-work ledger for each landed story spec that still recommends a follow-up review, atlas's included, and recorded the co-governor surface reconcile on `spec-pyforge-atlas`'s memlog on 2026-10-03). No epic or story is minted: the `DW-FRR` rows are
review work recorded in the deferred-work ledger, and any follow-up review they lead to is dispatched against its own
story's key. Every Story heading still maps 1:1 to a `sprint-status-ledger.yaml` key; no ledger key moved. `updated:`
bumped.

## Currency reconciliation — 2026-10-10

The `arch→epics` edge, after the spine's 2026-10-10 re-stamp.

Story 25.1's gate cleared: mason Story 21.1 is done on main (PR #1990), and the operator ruled "yes flip the six cleared stories and dispatch them". Its ledger key moves
`blocked → backlog`, and its story spec reads `ready-for-dev` with dated notes:
- the package does not yet resolve from any workspace channel;
- Story 25.2 already ships the placeholder node and catalog entry that 25.1 fills.

Story 25.1's block above is left as minted (it carries no Status line). Every Story heading still maps 1:1 to a
`sprint-status-ledger.yaml` key, and no key was added or removed. `updated:` bumped.

## Currency reconciliation — 2026-10-13 (range-test recorder race)

Epic 29 / Story 29.1 is new: a `fix` under `spec-pyforge-atlas` CAP-16, so no CAP, FR or AD moves and the PRD and the
spine are not re-stamped. The heading maps 1:1 to its `sprint-status-ledger.yaml` key (`29-1-…` and `epic-29` at
`backlog`, `epic-29-retrospective` at `optional`, through a worktree-local Tier-3 feed and `sprint-ledger-sync
--project atlas`); `marshal-policy.toml` `[epic_surfaces]."29"` lands with it. No existing key changed; no blocked key
flipped. `updated:` bumped.

## Currency reconciliation — 2026-10-14 (the DAG export reaches Pages as an artifact)

`arch→epics` edge after the spine's 2026-10-14 re-stamp (FR-70 / CAP-62, FR-71 / CAP-63; AD-21 amended, no AD added).
Epic 30 / Stories 30.1 and 30.2 decompose the two CAPs from the Dream's 2026-10-13 entry and the operator ruling it
carries. Both stories are `type: feature` behind a flag (`pyforge.atlas.viz_export_artifact`,
`pyforge.atlas.vizro_static_boards`) and are minted `backlog`; cross-station work (steward 102.2 / 102.4, herald CAP-61
M3) is prose on the `**Deps:**` lines and in the story specs, never a blocked row. The two new headings map 1:1 to
their `sprint-status-ledger.yaml` keys (`30-1-the-dag-export-reaches-pages-as-a-workflow-artifact`,
`30-2-vizro-boards-publish-as-static-exports-under-dashboard-vizro`, both `backlog`; `epic-30` `backlog`;
`epic-30-retrospective` `optional`), written through a worktree-local Tier-3 feed seeded from the tracked ledger and
`sprint-ledger-sync --project atlas`. Measured with `fleet_scan.parse_sprint_status` after the sync: 107 story keys
(104 done) and 30 epic keys, from 105 (104 done) and 29 before this mint. `marshal-policy.toml` `[epic_surfaces]."30"`
lands with it. No existing key changed; no blocked key flipped. `updated:` bumped.

## Currency reconciliation — 2026-10-19 (the Vizro boards read what the pipelines write)

`arch→epics` edge after the spine's 2026-10-19 re-stamp (FR-77 / CAP-69 registered, FR-71 / CAP-63 amended; no AD
added, removed or amended). Epic 37 decomposes them: Stories 37.1-37.4 now (operator ruling "Data-first + 10 rewires")
and Stories 37.5-37.10, the six boards no pipeline feeds, at `backlog` by the same ruling, each with a deferred-work
row. Every new heading maps 1:1 to a `sprint-status-ledger.yaml` key (`37-1-…` to `37-10-…` and `epic-37` at
`backlog`, `epic-37-retrospective` at `optional`), written through the Tier-3 feed and `sprint-ledger-sync --project
atlas`. `marshal-policy.toml` `[epic_surfaces]."37"` lands with it. No existing key changed; no blocked key flipped.
`updated:` bumped.
