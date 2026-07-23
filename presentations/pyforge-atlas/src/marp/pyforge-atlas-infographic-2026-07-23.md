---
marp: true
paginate: true
size: 16:9
title: Atlas — infographic
style: |
  section { background:#f3f2f2; color:#201e1d; font-family:'Archivo',Arial,Helvetica,sans-serif; font-size:25px; }
  h1 { letter-spacing:-0.03em; color:#201e1d; }
  h2,h3 { letter-spacing:-0.02em; color:#201e1d; }
  strong { color:#c22a10; }
  a { color:#c22a10; }
  code { background:#eae9e9; color:#c22a10; padding:0 .3em; }
  section.lead { background:#ec3013; color:#f3f2f2; }
  section.lead h1, section.lead h2, section.lead h3, section.lead strong, section.lead code { color:#f3f2f2; }
  section.lead code { background:rgba(255,255,255,.15); }
  section.dark { background:#201e1d; color:#f3f2f2; }
  section.dark h1, section.dark h2, section.dark h3, section.dark strong { color:#f3f2f2; }
  hr { border:none; border-top:3px solid #201e1d; margin:.35em 0; }
  table { font-size:.7em; border-collapse:collapse; }
  th { background:#201e1d; color:#f3f2f2; text-align:left; }
  th,td { border:1px solid #d3d0cf; padding:5px 9px; }
---

<!-- _class: lead -->

ATLAS · `pyforge-atlas` · cfe-atlas-datapipeline-kedro-migration v5.6

# from monolith to dataflow — the field guide

The intelligence layer of an AI-assisted conda-forge packaging factory. Six-pillar stack: **Kedro** (nodes + catalog) · **Dagster** (orchestration) · **DuckDB** (compute + vss) · **BSL** (semantics) · **Vizro / AI** (read surface) · **MCP / A2A** (agents).

Owner RXM · Python 3.14 · 9 epics · 32 stories · Waves 0 + A–H · 19,726 feedstocks

<!-- Companion infographic: the full migration at a glance, four parts. -->

---

<!-- _class: dark -->

## PART I · From monolith to DAG

# One DAG. Seven pipelines. Maintainable by agents.

A 10k-LOC procedural monolith becomes declarative dataflow — the load-bearing justification is agent-maintainability.

---

## The problem

The orchestrator ships — but every new phase re-implements **checkpointing, TTL gating and backoff by hand**; lineage is implicit; execution is observable only via stdout. **Agents cannot safely extend a 10,000-line monolith.**

- **23** cataloged phases hand-wiring their own resume & rate-limit machinery
- **28** bespoke read CLIs answering fixed questions — no ad-hoc query path

---

## Declarative dataflow — before & after

| | Legacy · monolith | Migrated · declared DAG |
| --- | --- | --- |
| Logic | procedural call order | pure nodes (DataFrame in → out) |
| IO / creds | JFrog cred on every request | catalog-owned, scoped per host |
| Timeouts | one 1800 s cap dropped F/K/N | per-node budgets |
| State | `phase_state` table, SQLite | `IncrementalParquetDataset`, DuckDB/Parquet |

Six layers, one place each: compute · IO & state · orchestrate · semantics · surfaces · factory. **The Kedro DAG is the single source of truth; all glue is replaceable.**

---

## Seven domain pipelines

| Pipeline | Owns |
| --- | --- |
| `core` | population, versions, repodata, attribution |
| `pypi_intelligence` | PyPI join, mapping, behind-upstream |
| `vulnerability` | OSV · KEV · EPSS · CWE · Basilisk |
| `vcs_health` | maintainers, health, velocity, readiness |
| `universal_sbom` | intake, resolver, matcher, hygiene, gate |
| `seed_gaps` | four read-only suggesters |
| `derived_artifacts` | export-purls, universe-sbom, ComplianceReport |

**Producer owns the dataset** — consumers reference by catalog name; join keys fixed across pipelines; purls are export identity, never internal keys.

---

## Add phase 24 without hand-wiring

**Declare** a dataset → **write** a pure node → **contract** it with `pandera`.

**Inherited, zero code:** TTL gating · resume/checkpoint · backoff · lineage + OTel · profiles · DAG order.

The new signals (B8–B10) land through exactly this machinery — no hand-written checkpoint code. *The price of never hand-wiring story 33.*

---

## The verify-first gate

**Frozen exit codes:** `error` → 2 · `policy-violation` → 1 · `indeterminate` → 1 — *pass line* — `pass` / `not-applicable` → 0. Enum `{0,1,2,130}`.

Four-axis **ComplianceReport**, schema-by-import from `pyforge.warden` via `pyforge-atlas[gate]`.

**Six gates**, each a wave's first deliverable: `kedro-test` · `kedro-catalog-check` · `parity-diff` · `dagster-dryrun` · `bsl-metric-check` · `wasm-smoke`. Fixture-based, non-credentialed, `--frozen`.

---

<!-- _class: dark -->

## PART II · An agent workforce builds it

# Graduated autonomy, verify-first

6 attended · 4 dev-auto · 11 loop-S (per-story-spec) · 11 loop-E (per-epic). ~21 of 32 loop-drivable — gates never weakened to raise the share.

---

## Who runs it & the eight waves

**Consumers:** Operator (watches the DAG) · CFE authoring agents (MCP + A2A) · BMAD execution agents (add nodes under gates) · CI (one report, one exit code).

| Wave | Content | Gate |
| --- | --- | --- |
| 0 · A | SKF skill; scaffold, catalog, IncrementalParquetDataset | `kedro-test` |
| B | node ports · MCP · parity · SBOM · new signals | `parity-diff` · B4 |
| C · D | Dagster compile + schedules; BSL, Vizro, Vizro-AI | `dagster-dryrun` · `bsl-metric-check` |
| E · F | A2A + lineage; DuckDB consolidation, vss, policy gate | F1 attended |
| G · H | WASM + sensors; wiki + agno crews + Wagtail | `wasm-smoke` · fixtures |

Legacy retires only after **B4 parity** (the abort ramp).

---

## Which surface, when

The **BSL is the single semantic interface** — every read surface consumes it, never raw SQL.

| What you need | Reach for |
| --- | --- |
| Standing metric on a dashboard page | Vizro page (via BSL) |
| Ad-hoc natural-language question | `query_vizro_ai` |
| Programmatic read / pipeline trigger | MCP tool |
| Inter-agent signal or alert | A2A channel |
| Write path / per-invocation / in-memory | CLI-first (3 exceptions) |

Public page breadth stays at the D2 factory-status page — **feeds > pages**.

---

<!-- _class: dark -->

## PART III · New signals & open questions

# Additive riders · gated re-checks

Three new signals promoted by measured evidence; six open questions resolved to defaults and re-checked at the gate.

---

## Three new signal sources

- **FR-19 · Basilisk** — conda-native vulns (prefix.dev). Match by **package name, never the OSV ecosystem tag**; `fix_available` tri-state; offline-skip hedge.
- **FR-20 · Velocity** — release-to-availability lag; releases **≤ 90 days**, against **first availability**, never `latest_conda_upload`. Median ≈ 8.9 h.
- **FR-21 · Readiness** — four-way migration split; partitioned by upstream category lists (**new migration = zero code change**); `not-in-tracker` labeled inferred.

**Why now:** EU CRA Art. 14 clock starts `2026-09-11` — KEV / EPSS / Basilisk are time-relevant.

---

## Open questions — resolved to defaults, re-checked at the gate

| Q | Gate | Adopted default |
| --- | --- | --- |
| Q1 | B4 | exact parity on the actionable views |
| Q2 | C | on-demand Dagster; re-verify under Prefect acquisition |
| Q3 | D3 | repo model-backend config; no litellm |
| Q4 | G2 | GitHub Pages; host-agnostic emitter |
| Q6 | B5 | consolidate mapping on migrated Phase C |
| Q7 | B8 | build Basilisk once as Kedro nodes |

Q5 resolved → **FR-22 · Wave H**. Conditional Phase T (trendshift) joins only if it ships before Wave B completes.

---

<!-- _class: dark -->

## PART IV · The read surface inverts

# Five surfaces on top of the DAG

Instead of 28 fixed questions, a semantic graph powers dashboards, natural language, agents, a browser build, and a knowledge factory.

---

## Five surfaces

- **Semantic read** — BSL dimensions & measures · Vizro dashboards · Vizro-AI NL · factory-status page.
- **Agent plane** — MCP triggers + reads · A2A insights & alerts · one execution plane.
- **Portability** — duckdb-wasm / Pyodide · static Parquet + HTTP Range · zero backend.
- **AI factory · H** — Karpathy wiki · agno crews · Wagtail CMS sync · Dagster-triggered.
- **Quality & lineage** — pandera-first · GX behind one hook · OpenLineage · OTel traces.

---

## The pyforge family — atlas provides, warden uses

Two workspace members, one `pyforge` namespace; one optional code edge, zero cycles, both independently installable.

- **`pyforge-atlas` provides the data** — KEV/EPSS, Basilisk, velocity, mapping. `pyforge.atlas`; never imports warden.
- **`pyforge-warden` uses the data** — owns the four-axis ComplianceReport schema; consumed by atlas only at the F4 gate via `pyforge-atlas[gate]`.

---

<!-- _class: lead -->

Built to be maintained by agents

# A DAG an agent can extend without hand-wiring a checkpoint.

The real deliverable isn't speed — the cold rebuild is network-bound. It's the node shape that lets an autonomous workforce add phase 24 safely.

Atlas · module `pyforge.atlas` · dist `pyforge-atlas` · docs/specs/cfe-atlas-datapipeline-kedro-migration.md · v5.6
