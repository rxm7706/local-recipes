---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
inputDocuments:
  - docs/specs/kedro-cf-atlas-migration.md
  - _bmad-output/projects/local-recipes/project-context.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture-cf-atlas.md
workflowType: 'prd'
project_name: 'cfe-atlas-data'
project_slug: 'cfe-atlas-data'
status: 'draft'
phase_gate: 'awaiting-review (PRD → architecture)'
date: '2026-06-20'
---

# Product Requirements Document — cfe-atlas-data

**Author:** rxm7706
**Date:** 2026-06-20
**Project slug:** `cfe-atlas-data`
**Intake spec:** `docs/specs/kedro-cf-atlas-migration.md` (elevated from Quick Flow → full BMAD method)
**Repository model:** monorepo — all code lives in-tree under `local-recipes`; this slug namespaces BMAD artifacts only.

> **Phase-gate note.** This PRD is the first artifact of a full-BMAD planning chain.
> It is written for review *before* architecture. Downstream artifacts
> (`architecture-cf-atlas-kedro.md`, `ux-design.md`, `epics.md`, the two validation
> gate reports) are produced only after this PRD is accepted.

---

## 1. Executive Summary

`cf_atlas` is the offline intelligence layer of the `conda-forge-expert` skill: a
SQLite database populated by a hand-rolled, ~4,300-LOC orchestrator
(`conda_forge_atlas.py` + `bootstrap_data.py`) that runs 22 procedural phases
(B → N, plus the O–S PyPI-intelligence phases) and is read through 16 bespoke CLIs
(`staleness-report`, `behind-upstream`, `feedstock-health`, …) plus a FastMCP tool
surface.

The orchestrator works, but it has three structural problems: (1) **maintainability**
— adding a phase means hand-wiring the `PHASES` registry, the SQL schema migration,
and the orchestrator loop; (2) **opacity** — a `--fresh` run takes 3–4 hours with no
way to watch the DAG, find bottlenecks, or inspect intermediate schemas; (3) **a rigid
read surface** — 16 CLIs answer 16 fixed questions, and anything else means hand-writing
`sqlite3` JOINs.

This project migrates that orchestrator to a **declarative, observable, modular data
platform**: **Kedro** (catalog + DAG-resolved pipelines), **Dagster** (scheduling,
retries, sensors), **DuckDB** (single compute/graph/vector engine over partitioned
Parquet), a **Boring Semantic Layer** (Ibis → DuckDB) feeding a **Vizro / Vizro-AI**
read surface, and **MCP + A2A** agent interfaces — with optional **WASM** portability.
The legacy orchestrator runs in parallel until **proven dataset parity** retires it.

On top of that data platform, this PRD **also delivers the AI Software Factory layer**
(intake spec §7 + §4.12): a **Wagtail CMS / django-lasuite** knowledge-base presentation
tier (the "Corporate Brain"), a **Karpathy Wiki** memory architecture
(`wiki/raw` → `wiki/compiled` → `wiki/outputs`) backed by Minio (S3) + PostgreSQL with
DuckDB/Ibis as the semantic query engine, and an **agentic maintenance loop** where the
5-persona workforce reads Parquet, builds relationships, indexes documents, and writes
Markdown pages / Marp decks / charts back into the CMS.

Every component is conda-forge-sourced and pixi-managed, scaffolded by `nebi`. No
standalone binaries, no JVM. The migration preserves the existing GitHub/PyPI/Anaconda
source set and the existing air-gapped/enterprise routing contract.

---

## 2. Problem Statement & Product Vision

### 2.1 Problem

| # | Problem | Evidence (from intake spec §3) |
|---|---|---|
| P1 | Adding/altering a phase is high-friction and error-prone. | Manual `PHASES` registry + schema migration + loop edits. |
| P2 | Execution is opaque; no DAG, lineage, or progress visibility. | 3–4 h `--fresh` with terminal-only stdout/stderr. |
| P3 | Data lineage exists only in the developer's head. | Phase dependencies (J needs D+E) are implicit in call order. |
| P4 | Read surface is rigid (16 fixed CLIs). | Ad-hoc questions require manual `sqlite3` JOINs. |
| P5 | No data-quality guardrails; malformed upstream data can poison the DB. | No contract enforcement mid-pipeline. |
| P6 | Cold-start latency (3–4 h) bottlenecks iteration. | SQLite + single-threaded procedural compute. |

### 2.2 Vision

A `cf_atlas` where **phases are declarative nodes** whose DAG is resolved automatically,
**execution is observable** end-to-end (Kedro-Viz structure + Dagster runtime +
OpenLineage/OpenTelemetry traces), **the read surface is a semantic layer** any
operator or agent can query in natural language, and **one engine (DuckDB)** handles
analytics, graph traversal, and vector search over partitioned Parquet — fast enough
to make a full refresh a routine operation rather than an overnight job.

### 2.3 Guiding constraints (non-negotiable, inherited from `project-context.md`)

- **Offline-first / air-gap-tolerant.** Every workflow must function given internal
  proxies/mirrors; the `<HOST>_BASE_URL` redirect contract is preserved.
- **conda-forge-only toolchain, pixi-managed.** No standalone binaries / JVM.
- **Monorepo.** All code in-tree; no new repository.
- **Parity-gated retirement.** The legacy orchestrator is not deleted until Story B4
  proves dataset parity.
- **CFE skill is authoritative.** Per CLAUDE.md Rule 1, all atlas-tooling work routes
  through `conda-forge-expert`; per Rule 2, the effort closes with a CFE retro.

---

## 3. Goals & Success Criteria

### 3.1 Product goals

| G | Goal |
|---|---|
| G1 | Replace the procedural orchestrator with a declarative Kedro pipeline whose DAG is auto-resolved. |
| G2 | Make execution observable (structure, runtime state, lineage, traces). |
| G3 | Replace SQLite + fragmented compute proposals with a single DuckDB engine. |
| G4 | Replace the 16 fixed CLIs with a semantic layer + NL/dashboard + MCP read surface. |
| G5 | Preserve the MCP agent surface and add an A2A inter-agent channel. |
| G6 | Add data-quality contracts that halt bad data before persistence. |
| G7 | Materially reduce cold-start time below the 3–4 h baseline. |
| G8 | Preserve offline/air-gap operation and the conda-forge-only constraint. |
| G9 | Stand up the AI Software Factory: a Wagtail/django-lasuite knowledge base, the Karpathy Wiki memory tier, and an agentic maintenance loop that compiles atlas intelligence into a living, queryable corporate brain. |

### 3.2 Measurable success criteria

| SC | Criterion | Target / measure |
|---|---|---|
| SC1 | Dataset parity vs. legacy. | Exact row-count + value parity on the actionable views (Q1 default); timestamp/ordering-only diffs documented as benign. |
| SC2 | Cold-start refresh time. | Materially below 3–4 h; **target ≤ 1 h** on the reference host (validated in Story F1). |
| SC3 | New-phase friction. | Adding a phase = adding a node + catalog entry; **no orchestrator-loop or registry edit** required. |
| SC4 | Read-surface coverage. | All 16 legacy CLI questions answerable from a Vizro page or the BSL/Vizro-AI NL field. |
| SC5 | Agent surface preserved. | Every ported MCP tool callable from Claude Code; ≥1 pipeline triggerable + ≥1 dataset readable via `kedro-mcp`. |
| SC6 | Data-quality enforcement. | A seeded malformed record (e.g. PyPI JSON missing a version) halts the node and raises an A2A alert before persistence. |
| SC7 | Observability. | Per-node lineage + metrics via OpenLineage; end-to-end OTel traces resolve to specific API calls. |
| SC8 | Air-gap preserved. | Full pipeline runs against `<HOST>_BASE_URL`-redirected mirrors with no public-host dependency. |
| SC9 | Toolchain purity. | `pixi.lock` resolves entirely from conda-forge; no standalone binary / JVM dependency. |
| SC10 | AI Software Factory operational. | The Wagtail KB renders ≥1 agent-generated intelligence report; the Karpathy Wiki `raw→compiled→outputs` flow round-trips end-to-end; an agent writes a Markdown page + a Marp deck + a chart into the CMS via the output channels. |

---

## 4. Personas & Stakeholders

The intake spec (§2.2, §7.3) defines a 5-persona agent workforce; this PRD treats
them as the consumer roles the platform must serve, plus the human operator.

| Persona | Role | Primary need |
|---|---|---|
| **Operator (human, rxm7706)** | Runs refreshes, inspects health, ships recipes. | Fast, observable refreshes; ad-hoc queryability; air-gap operation. |
| **Ingester (Analyst agent)** | Reads raw Parquet/payloads. | Declarative catalog access; clean dataset contracts. |
| **Compiler (Architect agent)** | Transforms raw data → structured concepts via BSL. | A trustworthy semantic layer (consistent metrics/dimensions). |
| **Linker (Developer agent)** | Connects packages/CVEs/feedstocks in the graph. | Native graph traversal (DuckDB recursive CTEs). |
| **Linter (QA agent)** | Validates constraints; weekly scheduled reviews. | Great-Expectations contracts; Dagster schedules. |
| **Oracle (Product-Owner agent)** | External query interface + strategic tools. | MCP/A2A surface; NL query; report generation. |

---

## 5. User Journeys

**J1 — Operator refreshes the atlas (offline).**
Operator runs the refresh → Dagster schedules/triggers the Kedro DAG → nodes read
through `<HOST>_BASE_URL`-redirected mirrors → Great-Expectations contracts gate each
ingest → partitioned Parquet is written → operator watches structure in Kedro-Viz and
runtime/retries in the Dagster UI → OpenLineage/OTel capture lineage + traces. *(FR-2,
FR-6, FR-10, FR-12; SC2, SC6, SC7, SC8.)*

**J2 — Operator asks an ad-hoc question.**
Operator opens the Vizro dashboard (or asks Vizro-AI in natural language, or calls the
`query_vizro_ai` MCP tool) → BSL translates to a consistent DuckDB query → a chart/insight
returns without hand-written SQL. *(FR-8, FR-9; SC4.)*

**J3 — Agent-driven remediation (MCP + A2A).**
The `cf_atlas` analytical agent finds a CVE/staleness signal via BSL → hands a structured
payload over A2A to the `conda-forge-expert` recipe-authoring agent → which authors the
fix. MCP lets agents trigger named pipelines and read datasets natively. *(FR-7, FR-11;
SC5.)*

**J4 — Maintainer adds a new phase.**
Maintainer writes a pure-function node + a `catalog.yml` entry → Kedro resolves it into
the DAG automatically; no registry/loop edit. *(FR-2; SC3.)*

**J5 — Legacy retirement (parity gate).**
Kedro and legacy run in parallel → parity check compares Parquet outputs to `cf_atlas.db`
tables → on zero material drift, the legacy orchestrator is marked for retirement. *(FR-4;
SC1; AC-1.)*

---

## 6. Scope

### 6.1 In scope — phased delivery (Waves A–G)

Delivery follows the intake spec's waves A–G, plus **Wave H (AI Software Factory)**
folded in per your Q5 decision; each wave depends on the prior wave's deliverables.
Epics/stories are derived in the downstream `epics.md`.

| Wave | Theme | Headline deliverables |
|---|---|---|
| **A** | Scaffold & Catalog | `nebi`-scaffolded Kedro+pixi project; `catalog.yml` for all sources/outputs; `IncrementalParquetDataset` (TTL gating). |
| **B** | Node porting & MCP | Core pipeline (B–M) + PyPI/Vulnerability pipelines as nodes; `kedro-mcp` re-exposure; **parity check (B4 — gates legacy retirement)**. |
| **C** | Orchestration & Viz | `kedro-dagster` schedules/retries; `kedro-viz` via a pixi task. |
| **D** | Semantic layer & dashboards | BSL models; Vizro dashboard (16 CLIs → pages); Vizro-AI NL field + `query_vizro_ai` MCP tool. |
| **E** | A2A & observability | A2A interface; OpenLineage + OpenTelemetry. |
| **F** | DuckDB singularity | All datasets on DuckDB/partitioned Parquet; Great-Expectations validation nodes; `vss` vector search. |
| **G** | WASM & sensors | Pyodide/DuckDB-WASM intelligence surface; static-host Parquet emission; Dagster Sensors (near-real-time). |
| **H** | **AI Software Factory** (intake §7 + §4.12) | Wagtail CMS / django-lasuite presentation tier; Karpathy Wiki memory architecture (`raw`/`compiled`/`outputs`) on Minio (S3) + PostgreSQL; agentic maintenance loop (read Parquet → relate → index → synthesize); output channels (Markdown / Marp / matplotlib → CMS). |

> **Wave H detail.** H decomposes into: **H1** Wagtail/django-lasuite KB scaffold
> (conda-forge-sourced, air-gap-deployable, REST-writable by agents); **H2** Karpathy Wiki
> memory tier (Minio + PostgreSQL; DuckDB/Ibis as semantic query engine over
> `wiki/raw`→`wiki/compiled`→`wiki/outputs`); **H3** agentic maintenance loop (the
> 5-persona workforce compiles/links/indexes atlas Parquet into the KB; relationship
> build + document indexing); **H4** output channels (BSL/agent results emitted as Wagtail
> Markdown pages, Marp decks, matplotlib charts). H depends on Waves D (BSL), E (A2A), and
> F (DuckDB) being complete.

### 6.2 Out of scope (with reason)

| Item | Reason |
|---|---|
| §4.11 **Enterprise Python Manifest (5k)** generation | Downstream target state the graph *enables*; a distinct deliverable, not part of the factory build-out. **Flag:** if you want this folded in too, say so — it's adjacent to Wave H but currently held out. |
| Neo4j / Kùzu / LanceDB / Polars as separate engines | Superseded by the DuckDB singularity (§4.8). |
| Continued SQLite + `phase_state` orchestration | Replaced by Kedro + Dagster + DuckDB. |
| `spec-kit` as agent framework | Explicitly rejected; `bmad-method` governs. |
| Standalone binaries / JVM | Pixi-first, conda-forge-only constraint. |
| New external data sources beyond GitHub/PyPI/Anaconda | Migration preserves the existing source set. |
| Rewriting the conda-forge recipe-authoring skill itself | This touches the `cf_atlas` intelligence layer, not the authoring loop. |

---

## 7. Functional Requirements

Formalized from intake-spec FR-1…FR-15 (1:1 mapping preserved for traceability).

- **FR-1 — Declarative data access.** All API sources (GitHub, PyPI, Anaconda) and all
  Parquet outputs are declared as Kedro datasets in `conf/base/catalog.yml`; no
  data-access logic embedded in node functions.
- **FR-2 — Phases as DAG-resolved nodes.** The 22 procedural phases become Kedro nodes
  with declared inputs/outputs, grouped into five domain pipelines (Core; PyPI
  Intelligence; Vulnerability; VCS & Health; Universal SBOM). Execution order is
  resolved from the DAG, not call order.
- **FR-3 — `IncrementalParquetDataset` TTL gating.** The `*_fetched_at` TTL semantics
  are encapsulated in a reusable dataset class with a unit test proving stale rows
  re-fetch and fresh rows skip.
- **FR-4 — Checkpointing without `phase_state`.** Resumability via Kedro runner +
  persisted intermediate Parquet; the `phase_state` SQLite table is removed.
- **FR-5 — DuckDB single engine.** DuckDB is the sole engine for analytical compute,
  graph traversal (recursive CTEs), and vector search (`vss`), reading partitioned
  Parquet natively.
- **FR-6 — Dagster orchestration.** The Kedro DAG compiles to a Dagster repository;
  daily/weekly schedules + retries move off cron+bash; state is observable in the
  Dagster UI.
- **FR-7 — MCP surface preserved.** The existing MCP tools in
  `.claude/tools/conda_forge_server.py` are audited and re-exposed via `kedro-mcp`
  (pipeline triggers + dataset reads) so BMAD agents retain access.
- **FR-8 — Boring Semantic Layer.** The metrics/business logic in the 16 read CLIs are
  declared as BSL dimensions/measures (Ibis → DuckDB) as the single translation layer.
- **FR-9 — Vizro / Vizro-AI read surface.** The 16 CLIs become Vizro pages plus a
  Vizro-AI NL query field, exposed as a web dashboard and a `query_vizro_ai` MCP tool.
- **FR-10 — Data-quality contracts.** Great-Expectations contracts wired into Kedro
  nodes; Dagster halts on violation and raises an A2A alert before bad data persists.
- **FR-11 — A2A interface.** A dedicated agent-to-agent surface lets the `cf_atlas`
  analytical agent hand structured payloads to the `conda-forge-expert` agent
  (publish/subscribe or direct message).
- **FR-12 — Lineage + observability.** Kedro nodes, Dagster runs, and DuckDB queries are
  instrumented with OpenLineage (lineage/metrics) and OpenTelemetry (tracing/logging).
- **FR-13 — Universal SBOM → CycloneDX.** A dedicated SBOM pipeline parses `pixi.toml`,
  `pixi.lock`, `pyproject.toml`, `recipe.yaml`, `meta.yaml`, normalizing to CycloneDX
  before writing to DuckDB.
- **FR-14 — WASM portability.** The Vizro-AI dashboard + BSL layer compile to
  `duckdb-wasm`/Pyodide; Parquet artifacts are served from a static host and pulled via
  HTTP Range requests with zero backend.
- **FR-15 — Pixi-first, nebi-scaffolded, conda-forge-only.** Every component is sourced
  from conda-forge and managed in a single `pixi.toml`, scaffolded by `nebi`; no
  standalone binaries / JVM.

### AI Software Factory (Wave H — intake §7 + §4.12)

- **FR-16 — Wagtail CMS knowledge base.** A Wagtail CMS / django-lasuite presentation
  tier is the human "Corporate Brain" (wiki article area, search, collaboration),
  populated dynamically by the agent workforce via REST (read/write). conda-forge-sourced
  and air-gap-deployable.
- **FR-17 — Karpathy Wiki memory architecture.** A three-zone memory store —
  `wiki/raw/` (Parquet landing), `wiki/compiled/` (knowledge graphs, BSL-mapped concepts,
  linked dependencies), `wiki/outputs/` (final reports/decks/visualizations) — backed by
  Minio (S3) + PostgreSQL, with DuckDB/Ibis as the semantic query engine.
- **FR-18 — Agentic maintenance loop.** The 5-persona workforce incrementally compiles,
  links, and maintains the KB: read Parquet outputs, build relationships, index documents,
  synthesize vulnerability/intelligence reports — driven through the MCP + A2A surfaces of
  FR-7/FR-11.
- **FR-19 — Output channels.** BSL/agent query results are emitted as Wagtail Markdown
  pages, Marp slide decks, and matplotlib charts written back into the CMS, creating a
  compounding centralized knowledge base.

---

## 8. Non-Functional Requirements

- **NFR-1 — Offline / air-gap.** Every phase runs against `<HOST>_BASE_URL`-redirected
  mirrors; preserves Phase F (`PHASE_F_SOURCE`) and Phase H (`PHASE_H_SOURCE`) offline
  backends. (project-context § Air-Gapped/Enterprise.)
- **NFR-2 — Performance.** Cold-start refresh **target ≤ 1 h** (SC2); incremental
  refreshes dominated by changed partitions, not full re-scan.
- **NFR-3 — Security / credential hygiene.** Preserve the documented `JFROG_API_KEY`
  cross-host-leak mitigation (scope to subshell; never inject on non-JFrog hosts). No
  secrets in committed config; auth via env vars only.
- **NFR-4 — Determinism / reproducibility.** Environment resolved via `pixi.lock`;
  pipeline runs reproducible given fixed inputs; Parquet writes atomic (per atlas
  engineering rule book).
- **NFR-5 — Toolchain purity.** conda-forge-only; pixi-managed; `nebi`-scaffolded; no
  JVM / standalone binaries (FR-15 as an NFR gate on every dependency).
- **NFR-6 — Rate-limit safety.** Honor existing per-host/per-registry concurrency caps
  (`PHASE_*_CONCURRENCY`) and Retry-After/jitter patterns from the atlas engineering
  rule book during node ports.
- **NFR-7 — Backward-compatible consumer surface.** Read-side outputs consumed today
  (e.g. `pypi_intelligence` columns, actionable views) keep stable semantics so existing
  skill consumers don't break during parallel-run.
- **NFR-8 — Observability overhead bounded.** OTel/OpenLineage instrumentation must not
  materially regress NFR-2.
- **NFR-9 — Testability.** Each node is a pure function unit-testable on
  `pandas.DataFrame`/Parquet IO without mocking SQLite connections.
- **NFR-10 — Factory air-gap deployability.** The Wave-H stack (Wagtail, django-lasuite,
  Minio, PostgreSQL) must be conda-forge-sourced and deployable in an air-gapped /
  enterprise environment (Minio as the S3 backend keeps the memory tier off public AWS;
  no external SaaS dependency for the CMS or memory store).

---

## 9. Acceptance Criteria (whole migration)

Carried 1:1 from intake-spec §10 (the definition of done for the migration):

- **AC-1.** Kedro reproduces legacy `cf_atlas` outputs with proven parity (Story B4)
  before legacy retirement.
- **AC-2.** `phase_state` table and hand-rolled `*_fetched_at` checks are gone;
  resumability via Kedro runner + persisted Parquet + `IncrementalParquetDataset`.
- **AC-3.** Dagster owns scheduling + retries; phase state observable in the Dagster UI;
  `pixi run viz` renders the DAG.
- **AC-4.** The 16 read CLIs are answerable from Vizro pages + a Vizro-AI NL field +
  `query_vizro_ai` MCP tool, all driven by BSL.
- **AC-5.** MCP + A2A let agents trigger pipelines, read datasets, and hand structured
  payloads to the `conda-forge-expert` agent.
- **AC-6.** Great-Expectations contracts halt bad data; OpenLineage + OTel provide
  lineage + end-to-end tracing.
- **AC-7.** DuckDB is the single compute/graph/vector engine; cold-start materially
  faster than the 3–4 h baseline.
- **AC-8.** The intelligence surface runs in-browser via DuckDB-WASM against
  statically-hosted Parquet; Dagster Sensors enable near-real-time ingestion.
- **AC-9.** Every component is conda-forge-sourced + pixi-managed (`nebi`-scaffolded);
  no standalone binaries / JVM.
- **AC-10.** The AI Software Factory is operational: the Wagtail/django-lasuite KB is
  agent-writable via REST; the Karpathy Wiki `raw→compiled→outputs` flow round-trips on
  Minio + PostgreSQL; and the agentic maintenance loop emits ≥1 Markdown page, Marp deck,
  and chart into the CMS from atlas intelligence.

---

## 10. Open Questions & Resolutions

| Q | Question | Resolution for this PRD |
|---|---|---|
| Q1 | Dataset-parity tolerance for legacy retirement. | **Resolved (default):** exact row-count + value parity on actionable views; timestamp/ordering-only diffs documented as benign. Gates B4. |
| Q2 | Dagster deployment footprint (daemon vs on-demand). | **Default:** on-demand/scheduled local invocation; revisit a persistent daemon only if Wave-G Sensors require it. Confirm at Wave C. |
| Q3 | Vizro-AI LLM backend + enterprise routing. | **Default:** route through the repo's existing model-backend config + `_http.py` enterprise routing; no hardcoded public endpoint. Confirm at Wave D. |
| Q4 | WASM artifact-store hosting. | **Default:** GitHub Pages for the public path; keep the emitter host-agnostic for an enterprise/JFrog-mirrored static store. Confirm at Wave G. |
| Q5 | Scope of the §7 AI Software Factory layer. | **Resolved (you decided 2026-06-20):** **in scope** — folded in as Wave H (FR-16…FR-19, AC-10, SC10). |

> Q1 and Q5 are resolved and binding. Q2/Q3/Q4 carry defaults and are confirmed at the
> start of their gating wave (full-BMAD per-wave gate).
>
> **New question opened by folding in Wave H — Q6 (gates Wave H):** are Wagtail,
> django-lasuite, `wagtail-markdown`, and Minio **available on conda-forge** at usable
> versions? PostgreSQL and Minio are present; Wagtail/django-lasuite presence must be
> verified in architecture, and any gap becomes a prerequisite recipe-authoring task
> routed through `conda-forge-expert` (CLAUDE.md Rule 1). This materially enlarges the
> effort and is the top Wave-H feasibility risk (R7).

---

## 11. Dependencies, Constraints & Risks

### 11.1 External dependencies (all conda-forge-sourced — NFR-5)
Kedro + `kedro-viz` + `kedro-dagster` + `kedro-mcp` + `kedro-great-expectations`;
DuckDB (+ `vss`); Ibis; Boring Semantic Layer; Vizro + Vizro-AI; Dagster (+ Sensors);
OpenLineage; OpenTelemetry; `nebi`; CycloneDX / `cdxgen`.

> **Availability risk (R1).** Several of these (e.g. `kedro-mcp`, `kedro-dagster`,
> Boring Semantic Layer, Vizro-AI, `nebi`) must be **verified present on conda-forge** at
> the required versions during architecture; any gap becomes a prerequisite
> recipe-authoring task routed through `conda-forge-expert` (CLAUDE.md Rule 1). This is
> the single largest feasibility risk and is the first architecture-phase investigation.

### 11.2 Internal dependencies
`.claude/skills/conda-forge-expert/scripts/{conda_forge_atlas,bootstrap_data}.py`
(migration source); `.claude/tools/conda_forge_server.py` (MCP ports);
`reference/atlas-phases-overview.md` + `atlas-phase-engineering.md` (node-port
constraints); `docs/specs/atlas-phase-f-s3-backend.md` (S3/Parquet datasets → catalog).

### 11.3 Risks

| R | Risk | Mitigation |
|---|---|---|
| R1 | Required plugins not on conda-forge. | Verify in architecture; author missing recipes via CFE skill before depending on them. |
| R2 | Parity drift hard to reach exactly. | Q1 tolerance + Story B4 evidence file; parallel-run until clean. |
| R3 | Vizro-AI backend conflicts with air-gap. | Q3 default routes through `_http.py`; no public endpoint. |
| R4 | Observability regresses performance (NFR-2 vs NFR-8). | Bound instrumentation; measure cold-start with/without. |
| R5 | Wave H materially enlarges effort / timeline. | Sequenced last (depends on D+E+F); can be gated/deferred independently without blocking Waves A–G value. |
| R6 | Credential cross-host leak during node ports. | NFR-3; preserve documented `JFROG_API_KEY` mitigation. |
| R7 | Wagtail / django-lasuite / Minio not on conda-forge at usable versions (Q6). | Verify in architecture; author missing recipes via CFE skill before Wave H depends on them; this is the top Wave-H feasibility risk. |

---

## 12. References

**Internal:** `docs/specs/kedro-cf-atlas-migration.md` (intake);
`_bmad-output/projects/local-recipes/planning-artifacts/architecture-cf-atlas.md`
(current-state "before"); `_bmad-output/projects/local-recipes/project-context.md`
(rulebook); `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md`,
`atlas-phase-engineering.md`; `CLAUDE.md` § "BMAD ↔ conda-forge-expert integration".

**Process:** Full BMAD method. Next artifacts (post-gate): `architecture-cf-atlas-kedro.md`
→ `ux-design.md` (Vizro dashboard) → `epics.md` → `validation-report-PRD.md`
(`bmad-validate-prd`) → `implementation-readiness-report.md`
(`bmad-check-implementation-readiness`). Closeout: `bmad-retrospective` + mandatory
`conda-forge-expert` CFE retro + CHANGELOG (CLAUDE.md Rule 2).
