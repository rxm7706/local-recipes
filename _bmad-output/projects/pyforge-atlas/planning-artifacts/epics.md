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
generatedBy: bmad-create-epics-and-stories (unattended Tier-2 stage 3)
---

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
- **DEV-AUTO** — `bmad-dev-auto` inline single-story implementation.
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
Every read-only question the 28 CLIs answered is answerable from BSL-driven Vizro pages plus a natural-language field callable from Claude Code.
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

**Epic dependency chain:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 (each wave
depends on the prior wave's deliverables — spec § 9 preamble). Within-epic
ordering is § 14's: B1/B2 → B3 → B4 → B5 → B6 → B7 → B8 → B9 → B10; B8/B9/B10
are additive, not parity-gated; legacy retirement only after B4 proves parity
per Q1.

---

## Epic 1: Wave 0 — Legacy Translation via Skill Forge (SKF)

Convert the legacy orchestrator into queryable, provenance-grade context so
Wave-B ports are grounded in fact, not model memory.

### Story 0.1 (1.1): Generate legacy contextual skill

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

### Story A1 (2.1): Scaffold the Kedro + pixi project via `nebi`

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

### Story A2 (2.2): Define the Data Catalog for all sources + outputs

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

### Story A3 (2.3): Implement `IncrementalParquetDataset` for TTL gating

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

### Story B1 (3.1): Port the conda-side backbone phases into Kedro nodes

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

### Story B2 (3.2): Port the PyPI & Vulnerability pipelines

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

### Story B3 (3.3): Re-expose the data surface as Kedro-API-native MCP tools

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

### Story B4 (3.4): Verify dataset parity against the legacy orchestrator

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

### Story B5 (3.5): Port the external-refresh assets (§ 3.4)

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

### Story B6 (3.6): Port the Seed-Gaps pipeline

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

### Story B7 (3.7): Extend the Universal SBOM intake (resolver, formats, universe BOM, buckets)

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

### Story B8 (3.8): Basilisk conda-native vulnerability ingestion

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

### Story B9 (3.9): Release-to-availability velocity columns

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

### Story B10 (3.10): Migration-readiness datasets + classification node

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

### Story C1 (4.1): Integrate `kedro-dagster` for scheduling + execution

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
- **Invariants:** AD-6, AD-1 (`kedro-dagster` is replaceable glue; no upward imports), AD-23 (one execution plane; run admission serializes per dataset set).
- **Mode:** ATTENDED (bring-up boundary event — one of the five § 2.5 attended events; the `dagster-dryrun` gate it builds is loop-consumable thereafter).
- **Gating question:** **Q2** — default adopted (above); re-verify the Dagster bet at wave start (release cadence under Prefect, `kedro-dagster` compatibility, Components/Prefect-deployer ramps).
- **Verify gate:** **builds `dagster-dryrun`**.
- **Depends on:** Epic 3 complete (nodes + refresh assets to schedule).

### Story C2 (4.2): Integrate `kedro-viz` + expose a pixi task

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

### Story D1 (5.1): Define the Boring Semantic Layer (BSL) models

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

### Story D2 (5.2): Build the Vizro dashboard + port the 28 CLIs to pages

As the operator,
I want a BSL-driven Vizro app reproducing the 28 read CLIs as pages, including a factory-status page,
So that every read-only question is answerable from a page meeting the agent-legibility bar.

**Acceptance Criteria:** (spec § 9 Story D2, binding)

**Given** the D1 BSL models and the CIS two-spine design specs
**When** the Vizro app is built
**Then** a Vizro dashboard serves the core KPIs currently locked in CLIs
**And** a "factory status" page reads the BMAD artifact state (sprint-status.yaml, epics frontmatter, `bmad-drift-check --specs` JSON) — agent-readable per § 13.2
**And** each read-only legacy CLI question is answerable from a Vizro page, where for the three FR-9 exceptions (`add-handoff`, `inventory-match`, `library-futures`) "answerable" means the latest-report artifact is surfaced read-only — the bar covers all 28
**And** the live-confirmed consumer set ports first: `behind-upstream`, `query-atlas`, `whodepends`, `feedstock-health`, `my-feedstocks`, `detail-cf-atlas`, `staleness-report`
**And** pages meet the § 2.1 agent-legibility bar (semantic HTML, ARIA, deterministic layouts; NFR-8) and public-facing breadth stays at the factory-status page (SM-C4).

- **FRs:** FR-9.
- **Invariants:** AD-8, AD-17 (authoring-feeding pages carry build timestamps).
- **Mode:** DEV-AUTO (visual judgment, § 9 preamble).
- **Gating question:** none.
- **Verify gate:** `bsl-metric-check` (+ `kedro-test`); D2 page inventory detail resolves in the CIS specs (Spine Deferred).
- **Depends on:** D1.

### Story D3 (5.3): Integrate Vizro-AI + expose the NL interface as an MCP tool

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

### Story E1 (6.1): Implement the A2A communication interfaces

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

### Story E2 (6.2): Integrate OpenLineage + OpenTelemetry

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

### Story F1 (7.1): Complete the DuckDB consolidation + prove the cold-start claim

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

### Story F2 (7.2): Implement the data-validation hook and inline Pandera contracts

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

### Story F3 (7.3): Implement Vector Similarity Search (RAG) via DuckDB `vss`

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

### Story F4 (7.4): Dependency-hygiene node + unified CI policy gate

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

### Story G1 (8.1): Compile the intelligence layer to Pyodide / DuckDB-WASM

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

### Story G2 (8.2): Emit Parquet artifacts to a static web host

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

### Story G3 (8.3): Implement Dagster Sensors for near-real-time ingestion

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

---

## Epic 9: Wave H — The AI Software Factory & Karpathy Wiki

The factory layer consumes pipeline outputs and writes only wiki/CMS (AD-22).
MinIO server provisioning is an H1 precondition (Spine Deferred).

### Story H1 (9.1): Scaffold the Karpathy Wiki folder structure and Agent Personas

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

### Story H2 (9.2): Implement Agno Compilation, Linting, and Q&A Crews

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

### Story H3 (9.3): Integrate La Suite Docs REST API Sync

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

### Story H4 (9.4): Orchestrate Crews via Dagster

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
