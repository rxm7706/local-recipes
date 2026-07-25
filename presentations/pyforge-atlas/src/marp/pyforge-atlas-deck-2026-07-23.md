---
marp: true
paginate: true
size: 16:9
title: Atlas — from monolith to dataflow
style: |
  section { background:#f3f2f2; color:#201e1d; font-family:'Archivo',Arial,Helvetica,sans-serif; font-size:26px; }
  h1 { letter-spacing:-0.03em; color:#201e1d; }
  h2,h3 { letter-spacing:-0.02em; color:#201e1d; }
  strong { color:#c22a10; }
  a { color:#c22a10; }
  code { background:#eae9e9; color:#c22a10; padding:0 .3em; }
  section.lead { background:#ec3013; color:#f3f2f2; }
  section.lead h1, section.lead h2, section.lead h3, section.lead strong, section.lead code { color:#f3f2f2; }
  section.lead code { background:rgba(255,255,255,.15); }
  hr { border:none; border-top:3px solid #201e1d; margin:.35em 0; }
  table { font-size:.72em; border-collapse:collapse; }
  th { background:#201e1d; color:#f3f2f2; text-align:left; }
  th,td { border:1px solid #d3d0cf; padding:6px 10px; }
  pre { background:#1a1918; color:#e8e6e4; font-size:.62em; }
---

<!-- _class: lead -->

ATLAS · conda-forge intelligence layer · BMAD Tier-2 plan `pyforge-atlas`

# from monolith to dataflow

Migrating a hand-rolled **~10,000-LOC** conda-forge orchestrator to **Kedro + Dagster + DuckDB** — a DAG an **agent workforce** can maintain.

Module `pyforge.atlas` · engine Kedro · Dagster · DuckDB · 19,726 feedstocks · 9 epics · 32 stories

<!-- The thesis: cf_atlas is the intelligence layer of an AI-assisted conda-forge packaging factory. The migration turns a procedural monolith into declarative dataflow so agents can safely extend it. -->

---

<!-- _class: lead -->

## ACT I

# From monolith to DAG

Every phase hand-wires its own checkpointing, TTL and backoff; lineage lives in the developer's head. Declarative dataflow ends that.

<!-- Act I frames the problem and the paradigm shift. -->

---

## 01 · The problem

The orchestrator demonstrably ships — but the cost is **chronic, not acute**. Every new phase re-implements **checkpointing, TTL gating and backoff by hand**, lineage is implicit, and execution is observable only via stdout.

It lands hardest on the factory's real workforce: **agents cannot safely extend a 10,000-line procedural monolith.**

- **23** cataloged phases, each hand-wiring its own resume & rate-limit machinery
- **28** bespoke read CLIs answering fixed questions — no ad-hoc query path

<!-- The load-bearing justification for the whole migration is agent-maintainability. -->

---

## 02 · Declarative dataflow — before & after

**Legacy · procedural monolith**
~10k LOC; per-phase `phase_state` table · one 1800 s cap silently dropped Phases F/K/N · JFrog credential injected on every request · SQLite; order & lineage implicit.

**Migrated · declared DAG**
Pure nodes (DataFrame in → out) · catalog-owned IO, credentials scoped **per host** · per-node timeouts (the silent-drop class is gone) · `IncrementalParquetDataset` TTL; DuckDB / Parquet.

Six layers, one place each: **compute** (pure nodes) · **IO & state** (catalog) · **orchestrate** (Dagster) · **semantics** (BSL) · **surfaces** (Vizro · MCP) · **factory** (wiki + crews). The Kedro DAG is the single source of truth; all glue is replaceable.

<!-- Same factory, re-shaped: pipes-and-filters over a declared Data Catalog. -->

---

## 03 · Seven domain pipelines

The 23 phases become nodes in exactly seven fixed pipelines. **Producer owns the dataset** — no two pipelines write one artifact.

| Pipeline | Owns | Legacy phases |
| --- | --- | --- |
| `core` | population, versions, repodata, attribution | B · B.5 · B.6 · F · I · J · M |
| `pypi_intelligence` | PyPI join, mapping, behind-upstream | C · C.5 · D · H · O–S |
| `vulnerability` | OSV · KEV · EPSS · CWE · Basilisk | G · G′ + FR-19 |
| `vcs_health` | maintainers, health, velocity, readiness | E · E.5 · K · L · N + FR-20/21 |
| `universal_sbom` | intake, resolver, matcher, hygiene, gate | FR-13/16/17/18 |
| `seed_gaps` | four read-only suggesters | byte-identical-seed |
| `derived_artifacts` | export-purls, universe-sbom, ComplianceReport | 14-day freshness |

<!-- Consumers reference by catalog name; join keys are fixed across pipelines. -->

---

<!-- _class: lead -->

## ACT II

# Node-shaped, agent-maintainable

Declare a dataset, write a pure node, add a contract — and inherit TTL, resume, backoff, lineage and profiles for free.

<!-- Act II: why the node shape is the whole point. -->

---

## 04 · Add phase 24 without hand-wiring

1. **Declare** — add source & output as datasets in `catalog.yml`; no IO in the node.
2. **Write the node** — a pure function, DataFrame in → out; unit-tests on IO, no retries inside.
3. **Contract it** — an inline `pandera` schema; bad data halts → A2A alert.

**Inherited, zero code:** TTL gating · resume/checkpoint · backoff · lineage + OTel · profiles · DAG order.

The new signals — Basilisk, velocity, readiness (B8–B10) — land through exactly this machinery. **The price of never hand-wiring story 33.**

<!-- This is journey UJ-5, the load-bearing agent-maintainability story. -->

---

## 05 · What the migration buys

- **Incremental re-materialization** — only affected nodes re-run. The honest headline; the cold rebuild is network-bound and no engine-swap miracle is claimed.
- **DuckDB query surface** — analytical compute, recursive-CTE graph traversal and `vss` vector search over Parquet.
- **Universe SBOM** — a ~856k-component CycloneDX BOM as a derived dataset; `cfe:*` and the conda-forge purl qualifier preserved.
- **Agent-legible feeds** — MCP dataset reads + A2A payloads. The productizable value is machine-consumable data — **feeds > pages**.

<!-- Honest performance framing per AC-7: incremental re-materialization, not cold-start speed. -->

---

## 06 · The verify-first gate

**Frozen exit-code convention:** `error` → exit 2 · `policy-violation` → exit 1 · `indeterminate` → exit 1 — *pass line* — `pass` / `not-applicable` → exit 0. Enum `{0, 1, 2, 130}`.

The four-axis **ComplianceReport** is schema-by-import from `pyforge.warden` via `pyforge-atlas[gate]` — never a vendored copy.

**Six deterministic gates**, each a wave's first deliverable: `kedro-test` (A1) · `kedro-catalog-check` (A2) · `parity-diff` (B4, attended) · `dagster-dryrun` (C1) · `bsl-metric-check` (D1) · `wasm-smoke` (G1). Fixture-based, non-credentialed, `--frozen`. The loop never enters a wave whose gate doesn't exist.

<!-- Verify-first sequencing keeps the autonomous loop honest. -->

---

<!-- _class: lead -->

## ACT III

# An agent workforce builds it

Graduated autonomy, verify-first: the harness is built attended, then the loop drives the ports under gates it can't remove.

<!-- Act III: the execution model. -->

---

## 07 · Who runs it

- **Operator (rxm7706)** — watches the DAG; re-runs only what's stale.
- **CFE authoring agents** — query intelligence via MCP; receive A2A signals.
- **BMAD execution agents** — add nodes safely under verify gates.
- **CI** — one ComplianceReport, one exit code.

Internal and non-commercial across a **19,726-feedstock** population. Five journeys: *watch a rebuild · trigger via MCP · ask without SQL · CI blocks a breach · add phase 24.*

<!-- Adoption means operator + agent usage, not external dashboard consumers. -->

---

## 08 · Graduated autonomy

| Mode | Count | Stories |
| --- | --- | --- |
| Attended | **6** | 0.1 · B4 · C1 · D3 · F1 · G2 (wave-boundary events) |
| Dev-auto | **4** | A1 · A2 · D2 · H2 |
| Loop-S (per-story-spec) | **11** | node ports approved before each run |
| Loop-E (per-epic) | **11** | the relaxed tier once the harness holds |

~21 of 32 stories are loop-drivable — but **gates are never weakened, removed, or demoted** to raise that share. Attended events are features, not friction. Loop runs are sequential (`max_parallel = 1`).

<!-- Verify-first sequencing: Waves 0+A build the harness, B loop-driven at spec-approval, C-E per-epic, F-H mixed. -->

---

## 09 · Eight waves, thirty-two stories

| Wave | Stories | Content | Gate |
| --- | --- | --- | --- |
| 0 | 0.1 | SKF legacy-translation skill | attended · done |
| A | A1–A3 | scaffold · catalog · IncrementalParquetDataset | `kedro-test` |
| B | B1–B10 | node ports · MCP · parity · SBOM · new signals | `parity-diff` · B4 |
| C | C1–C2 | kedro-dagster compile · schedules · viz | `dagster-dryrun` |
| D | D1–D3 | BSL · Vizro 28-CLI port · Vizro-AI | `bsl-metric-check` |
| E | E1–E2 | A2A surface · OpenLineage + OTel | existing gates |
| F | F1–F4 | DuckDB consolidation + benchmark · vss · policy gate | F1 · attended |
| G | G1–G3 | WASM / Pyodide · static host · sensors | `wasm-smoke` |
| H | H1–H4 | Karpathy wiki · agno crews · Wagtail · triggers | fixture tests |

B8–B10 are additive, **not parity-gated**. The legacy orchestrator retires only after **B4 parity** (the abort ramp).

<!-- Wave order and gates preserved from the spec. -->

---

## 10 · Which surface, when

The **BSL is the single semantic interface** — every read surface consumes it, never raw SQL.

| What you need | Reach for |
| --- | --- |
| A standing metric on a dashboard page | Vizro page (via BSL) |
| An ad-hoc natural-language question | `query_vizro_ai` |
| Programmatic dataset read / pipeline trigger | MCP tool |
| An inter-agent structured signal or alert | A2A channel |
| A write path / per-invocation / in-memory | CLI-first (3 exceptions) |

Metric logic lives once. Public page breadth stays at the D2 factory-status page — **feeds > pages**.

<!-- The read surface inverts from 28 fixed CLIs to a semantic graph. -->

---

<!-- _class: lead -->

## ACT IV

# New signals, additive riders

Promoted by measured evidence → FR + story. Riders on the migration, never its justification — and never parity-gated.

<!-- Act IV: the three committed new signal sources. -->

---

## 11 · Three new signal sources

- **FR-19 · Basilisk** — conda-native vulnerabilities (prefix.dev), keyed by conda PURL. Match by **package name, never the OSV ecosystem tag**; `fix_available` is tri-state. Pre-announcement — offline-skip is the hedge.
- **FR-20 · Velocity** — release-to-availability lag; no new source. Restricted to releases **≤ 90 days old**, computed against **first availability**, never `latest_conda_upload`. Baseline: median ≈ 8.9 h.
- **FR-21 · Readiness** — a four-way migration split (noarch / rebuild-done / confirmed-pending / not-in-tracker). Partitioned by upstream category lists — **a new migration needs zero code change**; `not-in-tracker` is labeled inferred.

**Why now:** the EU CRA Art. 14 reporting clock starts `2026-09-11` — KEV / EPSS / Basilisk are time-relevant, and the bmad-loop machinery just landed.

<!-- Additive, fixture-guarded, not parity-gated. -->

---

## 12 · Open questions — resolved to defaults, re-checked at the gate

| Q | Gate | Adopted default |
| --- | --- | --- |
| Q1 | B4 | exact row-count + value parity on the actionable views |
| Q2 | Wave C | on-demand Dagster; re-verify under Prefect acquisition |
| Q3 | D3 | route Vizro-AI through repo model-backend config; no litellm |
| Q4 | G2 | GitHub Pages default; host-agnostic emitter |
| Q6 | B5 | consolidate mapping on migrated Phase C (DuckDB) |
| Q7 | B8 | build Basilisk once as Kedro nodes in Wave B |

None block earlier work. Q5 (AI-factory scope) was resolved → **FR-22 · Wave H**.

<!-- Each open question adopted at its spec default now, re-checked at its gating wave. -->

---

<!-- _class: lead -->

## ACT V

# The read surface inverts

Instead of 28 fixed questions, a semantic graph powers dashboards, natural language, agents, a zero-backend browser build, and a knowledge factory.

<!-- Act V: on top of the DAG, five surfaces and the PyForge family. -->

---

## 13 · On top of the DAG — five surfaces

- **Semantic read** — BSL dimensions & measures · Vizro dashboards · Vizro-AI NL · factory-status page.
- **Agent plane** — MCP triggers + reads · A2A insights & alerts · structured payloads · one execution plane.
- **Portability** — duckdb-wasm / Pyodide in-browser · static Parquet + HTTP Range · zero backend · host-agnostic emitter.
- **AI factory · Wave H** — Karpathy wiki · agno crews · Wagtail CMS sync · Dagster-triggered.
- **Quality & lineage** — pandera-first · GX behind one hook · OpenLineage events · OTel traces.

Every surface consumes the BSL.

<!-- The read surface inverts from fixed CLIs to a queryable semantic graph. -->

---

## 14 · The PyForge family — atlas provides, warden uses

Two workspace members in one `pyforge` namespace; exactly one optional code edge, zero cycles, both independently installable.

- **`pyforge-atlas` — provides the data:** the intelligence layer — KEV/EPSS, Basilisk, velocity, mapping datasets. `pyforge.atlas`, Python 3.14; never imports warden.
- **`pyforge-warden` — uses the data:** the multi-axis compliance gate; owns the four-axis ComplianceReport schema, consumed by atlas only at the F4 gate via `pyforge-atlas[gate]`.

<!-- atlas provides the data, warden uses it — data-level, optional-if-present. -->

---

<!-- _class: lead -->

Built to be maintained by agents

# The real deliverable isn't speed.

It's a DAG small enough, pure enough and contract-guarded enough that an agent can add phase 24 **without hand-wiring a single checkpoint.**

Atlas · module `pyforge.atlas` · dist `pyforge-atlas` · docs/specs/cfe-atlas-datapipeline-kedro-migration.md · v5.6

<!-- The close: the migration exists so an agent workforce can maintain and extend the pipeline. -->
