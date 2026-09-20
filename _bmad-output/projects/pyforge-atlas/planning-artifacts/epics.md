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
updated: "2026-09-20"
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

- **Delivered 2026-07-17 — PR #69.** Full record: `specs/spec-0-1-generate-legacy-contextual-skill.md`.

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

- **Delivered 2026-07-17 — PR #70.** Full record: `specs/spec-a1-scaffold-the-kedro-pixi-project-via-nebi.md`.

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

- **Delivered 2026-07-17 — PR #71.** Full record: `specs/spec-a2-define-the-data-catalog-for-all-sources-outputs.md`.

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

- **Delivered 2026-07-17 — PR #72.** Full record: `specs/spec-a3-implement-incrementalparquetdataset-for-ttl-gating.md`.

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

- **Delivered 2026-07-17 — PR #73.** Full record: `specs/spec-b1-port-the-conda-side-backbone-phases-into-kedro-nodes.md`.

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

- **Delivered 2026-07-17 — PR #75.** Full record: `specs/spec-b2-port-the-pypi-vulnerability-pipelines.md`.

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

- **Delivered 2026-07-17 — PR #76.** Full record: `specs/spec-b3-re-expose-the-data-surface-as-kedro-api-native-mcp-tools.md`.

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

- **Delivered 2026-07-18 — PR #77.** Full record: `specs/spec-b4-verify-dataset-parity-against-the-legacy-orchestrator.md`.

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

- **Delivered 2026-07-18 — PR #78.** Full record: `specs/spec-b5-port-the-external-refresh-assets-3-4.md`.

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

- **Delivered 2026-07-18 — PR #79.** Full record: `specs/spec-b6-port-the-seed-gaps-pipeline.md`.

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

- **Delivered 2026-07-18 — PR #80.** Full record: `specs/spec-b7-extend-the-universal-sbom-intake-resolver-formats-universe-bom-buckets.md`.

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

- **Delivered 2026-07-18 — PR #81.** Full record: `specs/spec-b8-basilisk-conda-native-vulnerability-ingestion.md`.

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

- **Delivered 2026-07-18 — PR #82.** Full record: `specs/spec-b9-release-to-availability-velocity-columns.md`.

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

- **Delivered 2026-07-18 — PR #83.** Full record: `specs/spec-b10-migration-readiness-datasets-classification-node.md`.

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

- **Delivered 2026-07-18 — PR #84.** Full record: `specs/spec-c1-integrate-kedro-dagster-for-scheduling-execution.md`.

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

- **Delivered 2026-07-18 — PR #85.** Full record: `specs/spec-c2-integrate-kedro-viz-expose-a-pixi-task.md`.

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

- **Delivered 2026-07-18 — PR #86.** Full record: `specs/spec-d1-define-the-boring-semantic-layer-bsl-models.md`.

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

- **Delivered 2026-07-18 — PR #87.** Full record: `specs/spec-d2-build-the-vizro-dashboard-port-the-28-clis-to-pages.md`.

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

- **Delivered 2026-07-18 — PR #88.** Full record: `specs/spec-d3-integrate-vizro-ai-expose-the-nl-interface-as-an-mcp-tool.md`.

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

- **Delivered 2026-07-18 — PR #90.** Full record: `specs/spec-e1-implement-the-a2a-communication-interfaces.md`.

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

- **Delivered 2026-07-18 — PR #91.** Full record: `specs/spec-e2-integrate-openlineage-opentelemetry.md`.

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

- **Delivered 2026-07-18 — PR #92.** Full record: `specs/spec-f1-complete-the-duckdb-consolidation-prove-the-cold-start-claim.md`.

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

- **Delivered 2026-07-18 — PR #93.** Full record: `specs/spec-f2-implement-the-data-validation-hook-and-inline-pandera-contracts.md`.

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

- **Delivered 2026-07-18 — PR #94.** Full record: `specs/spec-f3-implement-vector-similarity-search-rag-via-duckdb-vss.md`.

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

- **Delivered 2026-07-18 — PR #95.** Full record: `specs/spec-f4-dependency-hygiene-node-unified-ci-policy-gate.md`.

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

- **Delivered 2026-07-18 — PR #96.** Full record: `specs/spec-g1-compile-the-intelligence-layer-to-pyodide-duckdb-wasm.md`.

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

- **Delivered 2026-07-18 — PR #97.** Full record: `specs/spec-g2-emit-parquet-artifacts-to-a-static-web-host.md`.

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
  corrected 73 → 86 in spec-a2/spec-b6.

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

4. **BS-5 DuckDB — cooperate, do not duplicate Story 25.2.** Single-writer discipline and
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
**Effort:** M • **Deps:** — • **Status:** backlog
**Given** the shipped CAP-19 engine (steward 34.1–34.5) **When** the single pixi-sourced boot
script runs **Then** the in-process library face is available by default (AD-16 local-first;
DuckDB stays a query face, never a fourth backing store) **And** the Mosaic `duckdb-server`
HTTP/Arrow face is raised by the SAME script only when the platform stack is up — with the
stack down it degrades to library-face-only with a structured notice, never a crash **And**
no second boot path exists (grep-verifiable: exactly one `duckdb-server` launch site)
(`query-plane-face` ruling, 2026-08-26).

### Story 19.2: Face parity is part of done (CAP-5)
**Effort:** S • **Deps:** S-20.1 • **Status:** backlog
**Given** both faces up on fixture data **When** the parity gate runs an identical query set
against the library face and the HTTP/Arrow face **Then** results agree row-for-row **And** a
seeded divergence fails the gate (proven in-test) **And** filesystem-less consumers bind to
the HTTP face per CAP-19's success wording ("the plane DSN or HTTP face") — parity is part of
the face's definition of done per the `query-plane-face` ruling (2026-08-26); the gate is
offline-safe.

### Story 19.3: Named-pipeline derivation of the dashboard stores (CAP-6)
**Effort:** M • **Deps:** — • **Status:** backlog
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
**Effort:** M • **Deps:** — • **Status:** backlog
**Given** DW-D2-1 — checked 2026-08-27: the CIS DESIGN/EXPERIENCE gap STILL BLOCKS (the
`DESIGN.md` + `EXPERIENCE.md` spine specs were never produced; no evidence-update since the
2026-07-30 verification) **When** the CIS Carson/Maya planning pass runs **Then** both spine
files land under `planning-artifacts/` covering every one of the 19 unshipped pages **And**
DW-D2-1's close cites them **And** until this story lands, S-20.5 must not expand the page
set past the live-confirmed core.

### Story 19.5: Port the remaining nineteen Vizro pages (CAP-7)
**Effort:** L • **Deps:** S-20.3, S-20.4 • **Status:** backlog
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
**Type:** feature • **Effort:** L • **Deps:** S-21.3 • **Status:** backlog
**Given** bootstrap **When** Tier 1 datasets fetch **Then** all Tier 1 entries in
`catalog-sources.md` are live in `catalog.yml` with smoke floors.

### Story 20.5: Tier 2 sources (about, curated orgs, Artifactory names)
**Type:** feature • **Effort:** M • **Deps:** S-21.4 • **Status:** backlog
**Given** attended creds when live fetch enabled **When** Tier 2 runs **Then** CDO universe
names come from catalog Parquet (telemetry deferred to Epic 23).

### Story 20.6: upstream_discovery identity join and export Parquet
**Type:** feature • **Effort:** L • **Deps:** S-21.5 • **Status:** backlog
**Given** associator + board fixtures **When** Phase D runs **Then** `identity_export_parquet`
matches today's join parity.

### Story 20.7: Quartet thin-out and gist wrapper
**Type:** feature • **Effort:** M • **Deps:** S-21.6 • **Status:** backlog
**Given** identity export Parquet **When** `--gist-only` runs **Then** inventory scripts delegate
join to Atlas; Epic 17 purl-associator constraint superseded with memlog.

### Story 20.8: End-to-end verification gate
**Type:** feature • **Effort:** M • **Deps:** S-21.7 • **Status:** backlog
**Given** no legacy DB on Kedro path **When** full bootstrap + `--live-catalog` **Then**
`parity-diff` and `bsl-metric-check` pass — Epic 21 success signal.

### Story 20.9: Vizro bootstrap health pages (optional, CAP-5)
**Type:** feature • **Effort:** M • **Deps:** S-21.8 • **Status:** backlog • **Optional:** yes
**Given** post-bootstrap Parquet **When** `dashboard-serve` **Then** three BSL health pages
render non-empty tables.

### Story 20.10: Kedro-Viz CI path sync (optional, CAP-6)
**Type:** chore • **Effort:** S • **Deps:** S-21.8 • **Status:** backlog • **Optional:** yes
**Given** a catalog-only PR **When** merged to main **Then** `kedro-viz-publish.yml` republishes
the static DAG export.

---

## Epic 21: Vizro parity with identity canvases

**Spec binding.** `spec-atlas-kedro-catalog-expansion` CAP-7 — parallel browser replacement for
the three Cursor Canvas identity views; deferred from Epic 21 for scope, not capability.
**Renumbered 2026-08-29** from draft Epic 19.

### Story 21.1: Ranked export bridge (quartet → Vizro feed)
**Type:** feature • **Effort:** S • **Deps:** S-21.8 • **Status:** backlog
**Given** `priority.py` on identity export **When** bridge runs **Then**
`identity_ranked_export.parquet` feeds Vizro until Epic 23.5 supersedes.

### Story 21.2: Vizro `identity-catalog` page
**Type:** feature • **Effort:** M • **Deps:** S-22.1 • **Status:** backlog • **Optional:** yes
**Given** ranked export **When** page loads **Then** row counts match catalog canvas fixture.

### Story 21.3: Vizro `identity-ops` page
**Type:** feature • **Effort:** M • **Deps:** S-22.1 • **Status:** backlog • **Optional:** yes
**Given** ranked export **When** four panes render **Then** pane totals match ops canvas fixture.

### Story 21.4: Vizro `identity-workbook` page
**Type:** feature • **Effort:** M • **Deps:** S-22.1 • **Status:** backlog • **Optional:** yes
**Given** enterprise Parquet absent or present **When** page loads **Then** honest shell or full
workbook parity respectively.

### Story 21.5: Canvas vs Vizro parity gate
**Type:** feature • **Effort:** M • **Deps:** S-22.2, S-22.3 • **Status:** backlog • **Optional:** yes
**Given** shared fixture **When** `dashboard-dryrun` parity test runs **Then** Vizro matches
canvas DATA aggregates.

### Story 21.6: Canvas deprecation switch
**Type:** chore • **Effort:** S • **Deps:** S-22.5 • **Status:** backlog • **Optional:** yes
**Given** parity gate green **When** `INVENTORY_IDENTITY_UI=vizro|canvas|both` **Then** default
`both` until operator opts into vizro-only.

---

## Epic 22: Complete inventory export — zero deferred

**Spec binding.** `spec-atlas-kedro-catalog-expansion` CAP-8 — closes
`docs/dreams/atlas-kedro-catalog-expansion.md` with `identity_complete_export.parquet` and
`enterprise_jfrog_consumption.parquet` per `complete-export-contract.md`.
**Renumbered 2026-08-29** from draft Epic 20.

### Story 22.1: Tier 3 bulk OS indexes
**Type:** feature • **Effort:** M • **Deps:** S-21.4 • **Status:** backlog
**Given** bootstrap **When** Tier 3 fetches run **Then** homebrew/nixpkgs/spack/debian/fedora
BOOLs land on verification export.

### Story 22.2: Enterprise JFROG consumption Parquet
**Type:** feature • **Effort:** L • **Deps:** S-21.5, Epic 15 • **Status:** backlog
**Given** mock or attended Artifactory transport **When** rollup runs **Then**
`enterprise_jfrog_consumption.parquet` matches §1 column contract on fixture.

### Story 22.3: Priority rules in Kedro (`inventory_priority_assignments`)
**Type:** feature • **Effort:** L • **Deps:** S-21.6, S-23.2 • **Status:** backlog
**Given** frozen priority fixture **When** Kedro node runs **Then** P/Score/Work parity vs
`priority.py`.

### Story 22.4: Deliverable A + `Packaging_Candidate_Status`
**Type:** feature • **Effort:** M • **Deps:** S-21.3, S-23.3, S-23.8 • **Status:** backlog
**Given** verification + priority Parquet **And** `inventory_universe` (S-23.8) as the row
grain **When** derived export writes **Then** `inventory_verified_packages.parquet` has exact
14-column order at the full-inventory grain (~38k rows), not the OpenTeams-universe grain.

### Story 22.5: `identity_complete_export.parquet` (canonical)
**Type:** feature • **Effort:** L • **Deps:** S-23.3, S-23.4 • **Status:** backlog
**Given** identity + priority + enterprise joins **When** export materializes **Then** full
GIST_SCHEMA + handoff columns; supersedes Story 22.1 bridge.

### Story 22.6: BSL gist aggregates (CAP-8d)
**Type:** feature • **Effort:** M • **Deps:** S-23.5 • **Status:** backlog
**Given** complete export **When** BSL renders gist markdown **Then** parity vs today's gist
files on fixture; `gh gist edit` is thin actuator only.

### Story 22.7: Zero-deferred E2E gate
**Type:** feature • **Effort:** M • **Deps:** S-23.5, S-23.6, S-23.8, S-23.9 • **Status:** backlog
**Given** no workbook ingest — by the bootstrap **and** by the quartet (`openpyxl` absent
from `scripts/`) **When** bootstrap + Vizro + gist **Then** quartet data logic retired; dream
fully closed.

### Story 22.8: Workbook-free metrics universe (Kedro `inventory_universe` + `--analysis-xlsx` optional)
**Type:** feature • **Effort:** L • **Deps:** S-21.4, S-21.5 • **Status:** backlog
**Given** Tier 0–2 Parquet + the OpenTeams board dataset **When** `derived_artifacts` runs
**Then** `inventory_universe.parquet` holds one row per PEP-503 name with the workbook's
provenance labels, `role`, and `openteams_universe_member` **And** `metrics.py --live-catalog`
without `--analysis-xlsx` produces CSV/MD identical to the workbook run on a fixture (the
`10kClosed`-only rows are the one reported delta). *(Minted 2026-08-30 course correction.)*

### Story 22.9: Quartet workbook retirement (thin actuators, no `openpyxl` in `scripts/`)
**Type:** feature • **Effort:** L • **Deps:** S-23.4, S-23.5, S-23.6, S-23.8, S-22.1 • **Status:** backlog
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
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** unblocks Story 25.2's credentialed path • operator request 2026-09-10
**Surface:** `src/shared/packages/pyforge-atlas/tools/live_artifactory_transport.py` (new — NOT inside `src/pyforge/atlas/`, which `tests/unit/catalog/test_no_inline_io.py`'s `IO_DENYLIST` bans `requests`/`urllib3`/`httpx` from anywhere in; `tools/` mirrors the existing `tools/bootstrap.py` sibling-location precedent for attended-operator scripts), `src/shared/packages/pyforge-atlas/tests/tools/test_live_artifactory_transport.py`
**Given** `AqlTransport` (the sole HTTP seam `ArtifactoryAqlAdapter` takes) has only `_unconfigured_transport` wired anywhere in the package — Story 25.2 needs "an attended operator runs the pipelines end to end against live sources with the Artifactory credentials configured," but no live transport implementation exists for that operator to construct, only the injectable seam itself
**When** a new `live_transport(base_url, *, api_key=None, username=None, password=None)` factory is added, resolving auth the SAME way `.claude/skills/conda-forge-expert/scripts/_http.py` already does for JFrog elsewhere in this repo — `JFROG_API_KEY` → `X-JFrog-Art-Api` header, else `JFROG_USERNAME`/`JFROG_PASSWORD` → HTTP Basic — and performing exactly one HTTP round-trip per `AqlRequest`, matching the seam's own documented contract
**Then** the concrete HTTP client stays constructed OUTSIDE package import time (no top-level `requests`/`urllib` call, no credential read at import) — the factory is called explicitly by the attended operator's own run, at run time only
**And** a test suite exercises the factory with a mocked HTTP layer (no real network, no real credentials) covering: API-key auth header, username/password Basic auth, neither-configured raises a clear typed error naming which env var is missing, and one successful request/response round-trip shape
**And** this story does NOT itself run Story 25.2's live pipeline or touch any credential value — it only makes the missing transport exist for that attended, credentialed run to use

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
