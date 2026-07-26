---
title: cf_atlas Kedro/Dagster/DuckDB Migration
status: final
created: 2026-07-17
updated: 2026-07-17
project: pyforge-atlas
intent_source: docs/specs/cfe-atlas-datapipeline-kedro-migration.md (v5.6, ANALYSIS COMPLETE)
---

# PRD: cf_atlas Kedro/Dagster/DuckDB Migration

## 0. Document Purpose

This PRD is the Tier-2 planning artifact for migrating the `cf_atlas` conda-forge
intelligence pipeline from a hand-rolled ~10,000-LOC orchestrator to a
Kedro + Dagster + DuckDB stack with a Boring Semantic Layer (BSL), a
Vizro/Vizro-AI read surface, and MCP/A2A agent interfaces. Its readers are the
downstream BMAD workflows (`bmad-architecture`, `bmad-create-epics-and-stories`)
and the execution loop (`bmad-loop` / `bmad-dev-auto`) that will implement it.

The intake spec — `docs/specs/cfe-atlas-datapipeline-kedro-migration.md` v5.6 —
is the authoritative contract. This PRD preserves its FR numbering (FR-1..FR-22),
its wave/story structure (Waves 0 + A–H, 32 stories), its § 2.5 graduated-autonomy
execution model, and its § 12 out-of-scope boundary **verbatim in intent**; it adds
product framing (vision, users, metrics, risks) and records every decision made
during this unattended intake (§ 9). Where this PRD compresses, the spec section
cited in parentheses carries the binding detail. Live-surface counts (phases,
CLIs, MCP tools, schema version) are the spec § 3.3 snapshot, re-verified at
intake HEAD `4cf1b74` on 2026-07-17 (`intake-groundtruth-2026-07-17.md`).

This PRD was produced headless; no human elicitation occurred. All open
questions were resolved to the spec's § 11 recommended defaults (§ 8, § 9).

## 1. Vision

`cf_atlas` is the intelligence layer of an AI-assisted conda-forge packaging
factory: 23 cataloged pipeline phases build a database over the channel's
feedstock population (19,726 at the spec's 2026-07-16 full-population run) —
versions, downloads, maintainers, vulnerabilities, and readiness signals — read
today through 28 bespoke CLIs and 23 atlas-relevant MCP tools. The legacy
orchestrator demonstrably ships — but every new phase re-implements
checkpointing, TTL gating, and backoff by hand; lineage lives in the
developer's head; execution is observable only via stdout; and ad-hoc questions
require hand-written SQL. That cost is **chronic and compounding, not acute**
(spec § 3.2, PRFAQ-reframed), and it lands hardest on the factory's actual
workforce: autonomous agents cannot safely extend a 10,000-line procedural
monolith.

The migration's load-bearing justification is **agent-maintainability** (PRFAQ
kill-test, CONDITIONAL PASS, 2026-07-16): small, pure, contract-guarded Kedro
nodes with declared inputs/outputs and machine-checkable data contracts are
what the repo's graduated-autonomy loop execution can safely maintain and
extend — "the price of never hand-wiring story 33." The performance story is
told honestly: the 3–4 h cold rebuild is network-bound, so the win is
**incremental re-materialization** (only affected nodes re-run), query-time
analytics, and Phase-F parquet reads — never an engine-swap cold-start miracle
(AC-7 scoping).

On top of the migrated DAG, the read surface inverts: instead of 28 fixed
questions, a BSL semantic graph (Ibis → DuckDB) powers Vizro dashboards, a
Vizro-AI natural-language query path, and MCP/A2A surfaces through which BMAD
agents trigger pipelines, read datasets, and hand structured insights to the
recipe-authoring agent. The 2026-07-16 market research confirms the demand
shape: **feeds > pages** (scenario ranking B > C > A) — the productizable
value is machine-consumable data, which is exactly what this migration's
identity layer and new signal sources (FR-19/20/21) produce; no new
requirements follow from it, and the internal-customers-first premise stands.

## 2. Target User

### 2.1 Jobs To Be Done

- **Operator (rxm7706)** — maintain ~769-feedstock coverage without babysitting
  a monolith: see the DAG, spot bottlenecks, re-run only what's stale, trust
  that bad data halts instead of persisting.
- **CFE authoring agents** (`conda-forge-expert` skill sessions) — query
  package/vulnerability/readiness intelligence through MCP with consistent
  semantics; receive structured signals (CVE found → fix authored) via A2A.
- **BMAD execution agents** (bmad-loop / dev-auto sessions) — extend the
  pipeline safely: add a node, declare its datasets, inherit
  checkpoint/TTL/backoff/contract machinery for free, verified by
  deterministic fixture gates.
- **CI** — consume one schema-validated `ComplianceReport` and one frozen
  exit-code gate instead of scraping CLI text.

This is an internal, non-commercial product: "adoption" means operator + agent
usage; sustainability is governed by the spec § 13 integration-surface matrix
reviews.

### 2.2 Non-Users (v1)

- External/public dashboard consumers (market scenario A — weakest demand;
  the D2 "factory status" Vizro page is the right-sized showcase).
- The conda-forge Security SIG and downstream scanners (Trivy/Syft/OSV): the
  OSV-format feed they need is a recorded § 12.1 candidate gated on SIG
  constitution — an operator engagement, not migration scope.
- Enterprise Python Manifest consumers (§ 4.11 target state the graph
  *enables*; not built here).

### 2.3 Key User Journeys

*Lighter form (internal tooling, solo operator + agent workforce).*

- **UJ-1. The operator watches a rebuild instead of tailing stdout.** rxm7706
  kicks off the maintainer-profile job; Dagster shows per-node state, retries,
  and timings; `pixi run viz` renders lineage; a cold-run Phase R overrun no
  longer silently kills Phases F/K/N. (FR-2, FR-6.)
- **UJ-2. A BMAD agent triggers and reads a pipeline via MCP.** An agent calls
  `run_vulnerability_pipeline`, waits on completion, reads the
  `basilisk_vulns` dataset natively, and passes a structured advisory payload
  ("Basilisk advisory on libtiff; KEV status via the `cisa_kev` overlay") to
  the recipe-authoring agent over A2A. (FR-7, FR-11, FR-19.)
- **UJ-3. An ad-hoc question needs no SQL.** The operator (or Claude Code via
  `query_vizro_ai`) asks "top 10 most-downloaded packages with critical CVEs
  and stale maintainership"; Vizro-AI compiles it against the BSL graph and
  returns a chart grounded in declared metrics. (FR-8, FR-9.)
- **UJ-4. CI blocks a policy breach.** A repo pipeline run assembles the
  four-axis `ComplianceReport`; a KEV-affecting-current hit exits 1 under the
  frozen convention, halts Dagster, and raises an A2A alert. (FR-16, FR-18,
  FR-10.)
- **UJ-5. An agent adds phase 24 without hand-wiring.** A loop-driven story
  adds a new signal as a Kedro node + catalog entries + pandera contract;
  TTL/resume/observability are inherited; the wave's verify gate proves it.
  (FR-1, FR-2, FR-3, FR-10 — the agent-maintainability journey the whole
  migration exists for.)

## 3. Glossary

- **cf_atlas** — the conda-forge intelligence data layer under
  `.claude/skills/conda-forge-expert/`; today `cf_atlas.db` (SQLite, schema
  v29) built by 23 cataloged phases.
- **Phase** — a legacy pipeline stage (B → N conda-side incl. sub-phases,
  O–S PyPI intelligence, plus unregistered Phase I). Migrates to one or more
  **nodes**.
- **Node** — a pure Kedro function with declared input/output **datasets**;
  the migration's unit of logic.
- **Dataset** — a declaratively cataloged data artifact (`conf/base/catalog.yml`):
  API source, Parquet partition, DuckDB table, or external seed.
- **Domain pipeline** — one of the seven modular Kedro pipelines of spec § 5.2
  (Core; PyPI Intelligence; Vulnerability; VCS & Health; Universal SBOM;
  Seed-Gaps; Read-Surface/Derived-Artifacts).
- **Wave** — an implementation batch (0, A–H); each wave's first deliverable is
  its own deterministic **verify gate**.
- **Graduated autonomy** — the § 2.5 execution model: Waves 0+A attended/
  dev-auto (they build the harness), Wave B loop-driven under
  per-story-spec-approval, C–E relaxing to per-epic, F–H mixed; loop execution
  is sequential (`max_parallel = 1`); attended events (B4 parity, C1 bring-up,
  D3 backend, F1 benchmark, G2 publish) are scheduled wave-boundary events.
- **Parity** — Story B4's proof that Kedro outputs match legacy `cf_atlas.db`
  (Q1 tolerance); gates legacy retirement.
- **External-refresh asset** — a separately-built local store (AppThreat vdb,
  offline OSV store, `pypi_conda_map.json`) orchestrated as a scheduled asset
  (§ 3.4, Story B5).
- **Bootstrap profile** — one of `maintainer` / `admin` / `consumer` job
  configurations over the same DAG; explicit env/run-config beats profile
  defaults; Phase P is admin-opt-in only.
- **BSL** — Boring Semantic Layer: declared dimensions/measures over the
  catalog (Ibis → DuckDB), the single translation interface for Vizro-AI,
  MCP, and agents.
- **Derived layer** — post-rebuild regenerated artifacts (`export-purls`,
  `universe-sbom`, seed-gap reports, `ComplianceReport`) under the 14-day
  freshness contract.
- **ComplianceReport** — pyforge-warden's four-axis (hygiene, security,
  license, currency) schema-validated artifact; assembled at the FR-18
  terminal gate under the frozen exit-code convention (0 pass / 1 policy-fail
  / 2 error; full enum {0, 1, 2, 130}).
- **New-signal sources** — the three committed additions: Basilisk conda-native
  vulnerabilities (FR-19), release-to-availability velocity (FR-20),
  migration readiness (FR-21). Additive, not parity-gated.
- **Verify gate** — a fixture-based, `--frozen`, non-credentialed pixi task the
  loop runs deterministically (`kedro-test`, `kedro-catalog-check`,
  `parity-diff`, `dagster-dryrun`, `bsl-metric-check`, `wasm-smoke`).

## 4. Features

*FR numbering is the spec's, preserved exactly. Each FR states the capability
contract and at least one testable consequence; the cited spec sections and
story ACs (§ 9–10 of the spec) remain the binding, fuller test surface.
FR locations: § 4.1 FR-1..4 · § 4.2 FR-5 · § 4.3 FR-6 · § 4.4 FR-7, FR-11 ·
§ 4.5 FR-8, FR-9 · § 4.6 FR-10, FR-12 · § 4.7 FR-13, FR-16, FR-17, FR-18 ·
§ 4.8 FR-14 · § 4.9 FR-15 · § 4.10 FR-19..21 · § 4.11 FR-22.*

### 4.1 Declarative Pipeline Core (Waves A–B)

**Description:** Replace the procedural orchestrator with a declared DAG:
every source and output cataloged, every phase a node, incremental state a
reusable dataset class, resumability native. Realizes UJ-5.

#### FR-1: Declarative data access via the Kedro Data Catalog
All API sources and Parquet outputs are datasets in `conf/base/catalog.yml`;
no data-access logic in node functions. Credentials are scoped **per
destination host** — a fix, not a port: legacy `_http.py` injects the JFrog
credential on every outbound request. (Spec § 5.1; Story A2.)
- Consequence: `kedro-catalog-check` passes (catalog resolves; no inline IO).
- Consequence: a non-JFrog host never receives `X-JFrog-Art-Api`.
- Consequence: all 20 `resolve_*_urls` override points (incl. new
  `BASILISK_BASE_URL`) survive for enterprise/air-gapped routing.

#### FR-2: Phases refactored into modular, DAG-resolved pipelines
The 23 cataloged phases become nodes in the seven domain pipelines; execution
order resolves from the DAG. Phase I becomes an explicit node. The § 3.3
per-phase engineering contracts bind the ports (Phase P two-layer cost gate,
Phase K 3-RPS token bucket, Phase F provenance discipline, Phase H serial
gate, B.5 `_pick_feedstock` attribution, EPSS 0–100 normalization). (Stories
B1, B2, B5, B6.)
- Consequence: no procedural call order anywhere; nodes unit-test on
  DataFrame IO.
- Consequence: contract fixtures (cost-gate, token-bucket, provenance,
  no-clobber) carry over green.
- Consequence: the maintainer-universe delta vs cf-graph (~44 feedstocks) is
  reconciled or documented (B1/B4).

#### FR-3: `IncrementalParquetDataset` preserves TTL gating
The `*_fetched_at` TTL semantics live in one reusable dataset class with
**per-dataset** TTLs (Phase D 7 d, Phase P 30 d, EPSS 1 d, CWE 90 d, …) —
never a global constant. (Story A3, the designated first loop story/worktree
smoke.)
- Consequence: unit test proves stale rows re-fetch, fresh rows skip.

#### FR-4: `phase_state` removed; resumability via runner + persisted Parquet
Checkpointing is Kedro-native; the bespoke `phase_state` table is deleted with
the legacy orchestrator at B4 parity. (Stories A3, B4.)
- Consequence: an interrupted run resumes from persisted intermediates
  without a custom checkpoint table.

### 4.2 Compute Engine (Wave F)

#### FR-5: DuckDB replaces SQLite and all fragmented compute proposals
One engine for analytical compute, graph traversal (recursive CTEs), and
vector search (`vss`), reading partitioned Parquet natively. Sequencing: the
Kedro path writes partitioned Parquet from Wave A (spec § 5.1) and B4 retires
the legacy SQLite write path — Parquet/DuckDB is canonical throughout; F1 is
residue cleanup (migrate/delete any surface still reading legacy
`cf_atlas.db`) plus the benchmark. (Stories F1, F3.)
- Consequence: no `sqlite3` import outside the retired legacy tree
  (grep-gated).
- Consequence: the attended F1 benchmark records warm-incremental (headline)
  AND cold-full wall-clock vs the 3–4 h network-bound baseline — evidence,
  not promises (AC-7).
- Consequence: a `vss` similarity query returns ranked results (F3).

### 4.3 Orchestration & Operations (Wave C)

#### FR-6: Dagster orchestrates schedules + retries via `kedro-dagster`
The Kedro DAG compiles to a Dagster repository; schedules encode the
`guides/atlas-operations.md` cadence table; the three bootstrap profiles
become named job configurations (profile defaults lose to explicit config);
timeouts are **per-node** — the legacy 1800 s `cf_atlas_core` cap that
silently dropped Phases F/K/N is structurally impossible. `kedro-viz` gives
the structural view (`pixi run viz`). `kedro-dagster` is **replaceable glue**
(bus factor ≈ 1; Dagster under Prefect acquisition watch — Q2 re-verify at
Wave C start; exit ramps: Dagster Components / Prefect deployer). Realizes
UJ-1. (Stories C1, C2, B5, G3, H4.)
- Consequence: `dagster-dryrun` passes (definitions load, schedules
  enumerate) without live execution.
- Consequence: Phase P stays opt-in (`PHASE_P_ENABLED=1`), admin-profile
  only, never a default schedule.
- Consequence: external-refresh assets run scheduled with retries; consumer
  profile still works air-gapped.

### 4.4 Agent Interfaces (Waves B, E)

#### FR-7: MCP surface preserved (Kedro-API-native; kedro-mcp never load-bearing)
The atlas-relevant MCP tools (23 of 46 in `conda_forge_server.py`) are audited
and re-authored over Kedro session/catalog APIs; agents trigger named
pipelines and read datasets via MCP. `library-futures` / `add-handoff` / the
seed-gap suggesters stay CLI-only. Realizes UJ-2. (Story B3.)
- Consequence: the trigger/read surface works with `kedro-mcp` absent.

#### FR-11: A2A interface for inter-agent collaboration
The cf_atlas analytical agent exchanges structured payloads with the
`conda-forge-expert` authoring agent (publish/subscribe or direct message);
contract violations and policy breaches raise A2A alerts. Realizes UJ-2, UJ-4.
(Story E1.)
- Consequence: a structured payload round-trips between the two agents.

### 4.5 Semantic Layer & Read Surface (Wave D)

#### FR-8: Boring Semantic Layer over the catalog (Ibis → DuckDB)
The metrics/business logic of the 28 read CLIs become declared BSL dimensions
and measures — the single translation interface. Maintainer-role facts are
first-class dimensions. Realizes UJ-3. (Story D1.)
- Consequence: `bsl-metric-check` proves BSL answers match legacy CLI outputs
  on core metrics (staleness, adoption stage, feedstock health).

#### FR-9: Read surface migrates from 28 CLIs to Vizro / Vizro-AI
Read-only CLIs become Vizro pages plus a Vizro-AI NL field, exposed as web
dashboard and as the `query_vizro_ai` MCP tool. Three exceptions stay
CLI-first with latest-report artifacts surfaced read-only: `add-handoff`
(write path), `inventory-match` (per-invocation inputs), `library-futures`
(in-memory by design). A "factory status" page reads BMAD artifact state.
The live-confirmed consumer CLIs — those observed in use today by the
feedstock-refresh / failure-remediation workflows: `behind-upstream`,
`query-atlas`, `whodepends`, `feedstock-health`, `my-feedstocks`,
`detail-cf-atlas`, `staleness-report` — port first. Frontend work in Waves
D/G is preceded by the CIS two-spine specs (`DESIGN.md` + `EXPERIENCE.md`,
spec § 2.4). Realizes UJ-3. (Stories D2, D3; Q3 gates the D3 LLM backend.)
- Consequence: every read-only legacy CLI question is answerable from a page,
  where for the three named exceptions "answerable" means the latest-report
  artifact is surfaced read-only — the D2 acceptance bar covers all 28.
- Consequence: pages meet the spec § 2.1 agent-legibility bar — semantic
  HTML, ARIA attributes, deterministic layouts (the factory-status page is
  explicitly tagged agent-readable in spec § 13.2).
- Consequence: `query_vizro_ai` is callable from Claude Code.

### 4.6 Data Quality, Lineage & Observability (Waves E–F)

#### FR-10: Data-quality contracts halt bad data (pandera-first)
Inline pandera contracts in nodes; Great Expectations as boundary layer behind
the same validator-agnostic `AfterNodeRunHook` — GX **version-capped at
conda-forge 1.18.2** (upstream declares `<3.14` at 1.19.0; no GX ≥1.19
features). Dagster halts on violation and raises an A2A alert. Realizes UJ-4.
(Story F2.)
- Consequence: a malformed-payload fixture halts the pipeline before persist.
- Consequence: swapping/stubbing the second validator requires no node
  changes.

#### FR-12: Lineage + observability via OpenLineage + OpenTelemetry
Nodes, runs, and DuckDB queries are instrumented: lineage + per-node metrics
(rows, latency, cache hits) via OpenLineage; end-to-end traces via OTel down
to specific API calls. (Story E2.)
- Consequence: a pipeline run emits OpenLineage events for every node, and
  one end-to-end OTel trace resolves down to a named API call.

### 4.7 Universal SBOM & Policy Gate (Waves B, F)

#### FR-13: Universal SBOM ingestion normalized to CycloneDX
The SBOM pipeline parses the tiered intake (core: `pixi.toml`, `pixi.lock`,
`pyproject.toml`, `recipe.yaml`, `meta.yaml`; extended tier per spec § 4.10),
normalizing to CycloneDX. The normalizer preserves the `cfe:*` property
namespace (incl. the `recommend-2027` six-property set) and the
`?channel=conda-forge` purl qualifier. (Story B7.)
- Consequence: each core-tier manifest fixture normalizes to CycloneDX with
  `cfe:*` properties and the `?channel=conda-forge` qualifier intact — never
  stripped during normalization.

#### FR-16: Dependency-hygiene scan node (deptry)
A hygiene node runs deptry when project source accompanies the manifest;
source-less inputs report `not-applicable` (frozen semantics shared with
pyforge-warden). Findings fill the `hygiene` axis of the four-axis
`ComplianceReport`; `security` comes from `inventory-match`/`cve` (the atlas
does not re-invoke osv-scanner); `license`/`currency` fill from atlas-native
data or `not-applicable`. (Story F4.)
- Consequence: an injected unused-dependency fixture yields a schema-valid
  `hygiene` finding; a source-less input reports `not-applicable`, never a
  failure.

#### FR-17: Transitive resolution + the universe BOM extend the intake
A transitive-resolver node (pip `--dry-run --report` / py-rattler solve)
upgrades bare manifests to full dependency sets (depth + fan-out recorded),
honoring mirror routing and degrading gracefully offline (`unresolved`
marker). The ~856k-component universe BOM is a first-class `derived` catalog
dataset under the 14-day freshness contract. The matching node preserves
`inventory-match`'s six-bucket semantics and three-way version comparison.
(Story B7.)
- Consequence: NBSP-padded pasted `conda list`/`pip list` text parses
  identically to ASCII-space form (fixture).

#### FR-18: Unified CI policy gate
One terminal node assembles the `ComplianceReport`, converges pyforge-warden's
strict exit-code gate with `inventory-match --policy` thresholds, emits the
schema-validated artifact, and halts Dagster on failure (A2A alert; CI
consumes the exit code). **Reconciliation obligation**: the shipped
`inventory-match --policy` enum is inverted; FR-18 flips it to the frozen
convention with a one-release deprecation window
(`INVENTORY_MATCH_LEGACY_EXIT=1`). A BOD-26-04-style risk-tiered threshold
mode is recorded as future option, not committed. Realizes UJ-4. (Story F4.)
- Consequence: a policy breach (e.g. `max_critical=0` violated or a
  KEV-affecting-current hit) exits 1, error paths exit 2, Dagster halts, and
  an A2A alert fires — identical failure semantics to an FR-10 violation.
- Consequence: `INVENTORY_MATCH_LEGACY_EXIT=1` restores the legacy codes for
  exactly one release; CI consumers otherwise see the frozen convention.

### 4.8 Portability (Wave G)

#### FR-14: WASM portability for the intelligence surface
The Vizro-AI dashboard + BSL layer run in-browser via duckdb-wasm/Pyodide;
Parquet artifacts publish to a static host (GitHub Pages per Q4 default;
emitter host-agnostic) and are pulled via HTTP Range with zero backend.
(Stories G1, G2; Q4.)
- Consequence: `wasm-smoke` (Playwright headless load-and-query) passes
  against the built artifact.

### 4.9 Toolchain & Provisioning (Wave A)

#### FR-15: Pixi-first, nebi-scaffolded, conda-forge-only
Every component sourced from conda-forge, managed in `pixi.toml`, scaffolded
by `nebi`; no standalone binaries or JVM. The stack is **already resolved
in-env** — adoption is wiring, not dependency addition; governing gates are
the Python 3.14 floor, the known pins, and the `llms-full-check` drift gate.
Air-gapped provisioning covers both routing layers (`_http.py` AND
`.pixi/config.toml [pypi-config]`). The scaffolded project ships its own lean
pixi env (worktree economics) and the `kedro-test` verify task. (Story A1.)
- Consequence: the FR-15 stack resolves at its pins on Python 3.14;
  `llms-full-check` passes after any dependency change (catalog updated in
  the same PR).
- Consequence: the lean env + `kedro-test` gate run in a worktree without
  materializing the fat `local-recipes` env.

### 4.10 New Signal Sources (Wave B — additive, not parity-gated)

**Description:** Three committed sources promoted by the spec's
evidence-gating pattern (measured evidence → FR + story). They are **riders**
on the migration, never its justification (PRFAQ).

#### FR-19: Conda-native vulnerability source — Basilisk (prefix.dev)
Two nodes: `POST /v1/querybatch` (≤1,000 queries/request) writes
`basilisk_vulns` keyed by conda PURL (CEP-63 draft form); a bounded
`GET /v1/vulns/{id}` detail fetch under standard rate-limit discipline.
Binding constraints: match by package name never the OSV ecosystem tag;
version currency ≠ security currency; `fix_available` is tri-state (`unknown`
never collapses to `false`; ~85.3% of matches resolve as upgrade-resolvable
via the `behind_upstream` join). Basilisk is pre-announcement: offline-skip +
`BASILISK_BASE_URL` are the hedges. (Story B8; Q7.)
- Consequence: fixtures prove the three binding constraints — a PyPI-tagged
  `affected[]` entry still matches its conda package; an enumerated-versions-
  only advisory yields `fix_available=unknown`; a `behind-upstream`-`current`
  package can still carry an advisory.
- Consequence: offline (consumer profile), the nodes skip gracefully and mark
  the dataset stale rather than failing.

#### FR-20: Release-to-availability velocity signal (rebuild-cadence-guarded)
`release_lag_hours` + `release_lag_qualifies` on the Phase H join — no new
external source. Hard constraints: restrict to upstream releases ≤90 days old,
and compute against **first availability of the matched version** (minimum
per-build repodata timestamp), never `latest_conda_upload` (the false "47%
behind" failure is fixture-blocked). Live calibration baseline: median
≈ 8.9 h, ~72.4% within 24 h. Two distinct measurements coincide at 83.7% —
the share of lag-qualifying builds within 72 h, and the share of the naive
">10 days behind" bucket whose upstream release was over a year old —
re-verify both against the spec § 15 evidence gists at B9. (Story B9.)
- Consequence: fixtures block both failure modes — a >90-day-old upstream
  release is excluded (`release_lag_qualifies = false`), and a same-version
  rebuild inside the window does not shift `release_lag_hours`.

#### FR-21: Migration-readiness source — conda-forge-bot-data status datasets
Category-list + per-migration detail datasets (partitioned by active
migration — new migrations need no code change) plus a readiness-classification
node producing the four-way split (noarch / rebuild-done / confirmed-pending /
not-in-tracker) with blocker labels and a top-unmigrated-by-volume ranking.
`not-in-tracker` is labeled as inference, never confirmed status. Fetches ride
the existing `resolve_github_raw_urls`; `version_status.v2.json` is excluded.
(Story B10.)
- Consequence: a new migration appearing upstream requires zero code change
  (category lists drive the partitioning); the classification output labels
  `not-in-tracker` as inferred, fixture-proven.

### 4.11 The AI Software Factory Layer (Wave H)

#### FR-22: Karpathy wiki + agent crews + CMS sync + Dagster triggers
Committed scope (Q5 resolution): (a) the `wiki/raw/ → compiled/ → outputs/`
scaffold with the 5 personas (H1); (b) `agno` compile/lint/Q&A crews on that
scaffold (H2); (c) La Suite/Wagtail REST sync to the Layer-1 CMS (H3);
(d) Dagster assets + sensors + schedules triggering the crews autonomously
(H4). Storage services (PostgreSQL, MinIO) conda-forge-provisioned per FR-15.
- Consequence: the four deliverables pass their fixture tests —
  scaffold-layout test + persona resolution (H1); crews end-to-end on a
  fixture wiki (H2); mock-Wagtail round-trip incl. idempotent re-push (H3);
  asset dry-run + simulated new-raw-file sensor trigger (H4). See SM-10.

## 5. Non-Goals (Explicit)

Verbatim boundary from spec § 12 — anything not in spec § 3.3/§ 3.4 or this
list's committed set is outside the migration's universe:

- Neo4j / Kùzu / LanceDB / Polars as separate engines (DuckDB singularity).
- Continued SQLite + `phase_state` orchestration.
- `spec-kit` as agent framework (rejected; `bmad-method` governs).
- Standalone binaries / JVM dependencies.
- Enterprise Python Manifest (5k) generation as a deliverable (enabled, not built).
- **New external data sources beyond the committed set** (legacy
  GitHub/PyPI/Anaconda set + Basilisk + conda-forge-bot-data `status/`).
  § 12.1 candidate signals and § 13.1 Candidate feeds are recorded, NOT
  committed — promotion requires measured evidence → FR + story.
- prefix.dev GraphQL API as a metadata backend (recorded hook:
  `variants.yankedReason` for Phase B.6's deferred full yanked detection).
- Ecosystem-composition-by-language report (deferred; measured facts preserved
  in the spec row).
- Spreadsheet tabs / GitHub Projects boards as SBOM-intake formats.
- `pyforge.warden` v1 standalone build (own spec; this migration models only
  the promoted atlas surface — schema-compatible by design).
- Rewriting the recipe-authoring skill itself.
- Static seeds + template trees as pipeline products (curated inputs only).
- Live authoring-time fetches (recipe-generator pulls, `gh`/Azure DevOps,
  live repodata) — transactional, not pipeline data; pipeline snapshots stay
  **advisory** and never substitute the authoring loop's live re-verification.
- OSV-format export feed + public dashboard productization (market scenarios
  B/A): recorded § 12.1 candidate (SIG-gated) and deferred respectively —
  no new FRs from the market research.

## 6. Scope & Execution Model

### 6.1 In Scope: Waves 0 + A–H (32 stories)

Wave order and story list preserved from spec § 9; each story's binding ACs
live there. Execution modes per § 2.5 (attended / dev-auto / LOOP-S
per-story-spec-approval / LOOP-E per-epic).

| Wave | Stories | Content | Gate (first deliverable) |
|---|---|---|---|
| 0 | 0.1 | SKF legacy-translation skill (execution scaffolding, no FR) | — (attended) |
| A | A1–A3 | nebi scaffold, data catalog, `IncrementalParquetDataset` | `kedro-test` (A1), `kedro-catalog-check` (A2); A3 = first loop story + worktree smoke |
| B | B1–B10 | Node ports (B1 conda-side, B2 PyPI+vuln), MCP (B3), parity (B4), external-refresh assets (B5), seed-gaps (B6), SBOM intake (B7), Basilisk (B8), velocity (B9), migration-readiness (B10) | `parity-diff` built incrementally through B1–B3, consumed + attended sign-off at B4 (spec § 2.5 says "B1–B4", B4's AC says "B1–B3" — read as build B1–B3, consume B4); B4 = attended parity event; Q6 before B5, Q7 before B8 |
| C | C1–C2 | kedro-dagster compilation + schedules; kedro-viz | `dagster-dryrun`; C1 bring-up attended; Q2 at wave start |
| D | D1–D3 | BSL models, Vizro dashboard + 28-CLI port, Vizro-AI + MCP tool | `bsl-metric-check`; D3 backend attended; Q3 at D3 |
| E | E1–E2 | A2A surface; OpenLineage + OTel | no new gate (§ 2.5 assigns Wave E none; its stories verify against the existing gates) |
| F | F1–F4 | DuckDB consolidation + benchmark, validation hooks, `vss` RAG, hygiene + policy gate | F1 = attended benchmark |
| G | G1–G3 | WASM/Pyodide, static Parquet host, Dagster sensors | `wasm-smoke`; G2 publish attended; Q4 at G2 |
| H | H1–H4 | Karpathy wiki scaffold + personas, agno crews, Wagtail sync, Dagster-triggered crews | (modes per story: H1/H3/H4 LOOP-E, H2 dev-auto) |

B8/B9/B10 are additive new-signal stories, **not parity-gated** — B4 compares
legacy-surface outputs only. Legacy orchestrator retires only after B4 proves
parity per Q1.

Conditional surface: if `trendshift-conda-forge.md` Track A ships before
Wave B completes, Phase T (tables, view, CLI/MCP tool, schema v30) joins the
migration surface with its invariants — re-check its status alongside the
live groundtruth at execution start (spec § 3.3).

### 6.2 Execution model (binding, from spec § 2.5)

Graduated autonomy with verify-first sequencing: ~21 of 32 stories are
loop-drivable (11 at spec-approval, ~10 relaxable to per-epic); the loop never
enters a wave whose gate doesn't exist; all gates are fixture-based (tracked
test tree, never `.claude/data/`), non-credentialed, run `--frozen`. Loop runs
are sequential. Wave B runs with TEA `atdd`-generated red-phase fixtures as
the verify assets, per the spec § 14 per-wave operating loop (Q-drain → TEA
test-design/atdd → loop → sweep → boundary event → PR per wave).
Preconditions: hooks approval; **`scripts/bmad-switch
pyforge-atlas`** — this supersedes spec § 2.5/§ 14's
pre-intake `bmad-switch local-recipes` literal, since this effort's artifacts
now live under the new project slug (deviation recorded, § 9.11); worktree
symlink bootstrap (validated by A3); heaviest-story budget review (B1/B2/F1).
Per CLAUDE.md Rule 1, any story touching recipe code or atlas tooling invokes
`conda-forge-expert`; per Rule 2, the effort closes with a CFE-skill retro.

### 6.3 Out of Scope for MVP

§ 5 Non-Goals plus: the kedro-viz prototype refresh
(`prototypes/cf-atlas-kedro-viz` predates the seven-pipeline decomposition —
follow-up, not this effort), and the three upstream bmad-loop feature requests
(resume-on-timeout, retry-from-attempt, PR-lifecycle hook — upstream's
timeline).

### 6.4 Deferred capabilities (tracked, contract-level)

> **Added 2026-07-25** when the four remaining `SPEC.md` `open_questions[]` were
> resolved. These are **committed-but-unscheduled capabilities**, not defects and
> not MVP scope. They live here — Tier-2 `planning-artifacts/`, git-tracked —
> rather than in `implementation-artifacts/deferred-work.md`, which is
> **gitignored** and would not survive a clone. Implementation-level gaps
> (the nine `DW-*` rows) stay there; contract-level deferrals belong here.

| ID | Deferred capability | Origin | Status |
|---|---|---|---|
| **DC-1** | **Public, versioned API tier** beyond agent-mediated access. Today: MCP (11 tools) + the `a2a` module, both agent-mediated; no HTTP surface exists (no FastAPI/APIRouter anywhere in the package). Operator decision 2026-07-25: this *is* intended eventually — deferred as a real capability, not closed as a non-goal. | `SPEC.md` OQ-1 | deferred, unscheduled |
| **DC-2** | **Dagster daemon** — scheduled/sensor-driven runs against a live daemon rather than in-process execution. | `SPEC.md` OQ-3 | deferred, unscheduled |
| **DC-3** | **MinIO / PostgreSQL servers** — object-store + relational substrates in place of the local/embedded defaults. | `SPEC.md` OQ-3 | deferred, unscheduled |
| **DC-4** | **Live Wagtail** — the publish surface running against a real instance. | `SPEC.md` OQ-3 | deferred, unscheduled |
| **DC-5** | **agno LLM synthesis** — live synthesis in the NL/RAG path. | `SPEC.md` OQ-3 | deferred, unscheduled |
| **DC-6** | **Production `vss` retriever** — the DuckDB VSS vector retriever at production settings. | `SPEC.md` OQ-3 | deferred, unscheduled |

**Why DC-2…DC-6 are listed at all:** the Spec named these five live bring-ups as
an open question, and **none of them appeared in any ledger** — the nine tracked
`DW-*` rows are all B-wave implementation gaps. So the contract named work that
nothing tracked, and the honest answer to *"what closes them?"* was *"nothing."*
Listing them makes them owned and visible; it does not schedule them.

**Not deferred — resolved to an owner:** an OpenSSF-Scorecard-class maintenance
signal (`SPEC.md` OQ-2) is a **Warden axis**, not an Atlas feed. `pyforge-warden`
already names six axes (hygiene · security · license · currency · provenance ·
**maintenance**), gating on the first four in v1. Atlas *measures*; Warden
*judges* — the same separation the Charter states as *the hand that builds is
never the gate that judges*.

## 7. Success Metrics

Derived from the spec's whole-migration acceptance criteria (AC-1..AC-11) and
tempered by the PRFAQ kill-test. Two metrics (SM-11, SM-12) deliberately
extend the spec's AC list where it has coverage gaps: the AC set carries no
direct criterion for the SBOM intake family (FR-13/16/17 short of the FR-18
gate) and AC-3's orchestration substance otherwise maps to no SM.

**Primary**

- **SM-1 (Parity before retirement):** B4 parity check reports zero material
  drift per Q1's tolerance (= exact row-count + value parity on the
  `v_actionable_packages`-family views; timestamp/ordering-only diffs
  documented as benign); legacy orchestrator retired only after recorded
  evidence. Validates FR-2, FR-4 (AC-1, AC-2).
- **SM-2 (Agent-maintainability):** a new signal lands as node + catalog +
  contract with zero hand-written checkpoint/TTL/backoff code — demonstrated
  in-effort by B8/B9/B10 landing through declared machinery, and by all 11
  committed LOOP-S stories executing loop-driven without gate removal (the
  ~21/32 total loop-driven share is a recorded target, not a gate). Validates
  FR-1, FR-2, FR-3, FR-10 (the load-bearing justification).
- **SM-3 (Incremental re-materialization):** warm incremental refresh
  re-runs only affected nodes (affected-node re-run counts recorded) and
  beats the legacy full-rebuild pattern on wall-clock; the pass threshold is
  fixed in the F1 story spec before the benchmark runs, and pass is
  adjudicated at the attended F1 boundary event against the recorded
  evidence — operator sign-off is the acceptance. Validates FR-5 (AC-7).
- **SM-4 (Read-surface completeness):** every read-only legacy CLI question
  answerable from a Vizro page — the three FR-9 exceptions counting via their
  surfaced latest-report artifacts, so the bar covers all 28;
  `bsl-metric-check` parity on core metrics; `query_vizro_ai` callable via
  MCP. Validates FR-8, FR-9 (AC-4).
- **SM-5 (Agent surfaces live):** MCP pipeline-trigger + dataset-read and the
  A2A payload hand-off work end-to-end from a BMAD agent session. Validates
  FR-7, FR-11 (AC-5).

**Secondary**

- **SM-6:** contracts halt bad data with A2A alert; lineage + traces
  observable end-to-end; policy gate holds the frozen exit-code contract.
  Validates FR-10, FR-12, FR-18 (AC-6).
- **SM-7:** three new signals live per their fixture-enforced guards
  (ecosystem-tag match, tri-state `fix_available`, 90-day gate,
  first-availability lag, inferred `not-in-tracker` labeling); the v2
  ecosystem-health analysis Sections 2–6 reproducible from the pipeline.
  Validates FR-19, FR-20, FR-21 (AC-10).
- **SM-8:** in-browser surface loads and queries statically-hosted Parquet
  with zero backend (`wasm-smoke`); sensors trigger incremental ingestion.
  Validates FR-14, FR-6 (AC-8).
- **SM-9:** conda-forge-only provisioning holds (`llms-full-check` green;
  py3.14 floor; no JVM/standalone binaries). Validates FR-15 (AC-9).
- **SM-10:** Wave-H factory deliverables pass their fixture tests (scaffold
  layout, crews on fixture wiki, Wagtail round-trip, sensor-triggered crew).
  Validates FR-22 (AC-11).
- **SM-11 (SBOM intake — extends the AC list):** each core-tier fixture
  manifest round-trips to a schema-valid CycloneDX BOM preserving `cfe:*` and
  `?channel=conda-forge`; the NBSP paste fixture passes; a deptry finding
  populates the `hygiene` axis; a bare manifest resolves transitively with
  depth + fan-out recorded. Validates FR-13, FR-16, FR-17.
- **SM-12 (Orchestration operations — covers AC-3):** Dagster Schedules
  encode the cadence table; the three profiles exist as job configurations
  with the override precedence; per-node timeouts demonstrably retire the
  1800 s `cf_atlas_core` defect (C1 AC); `pixi run viz` renders the DAG.
  Validates FR-6 (AC-3).

**Counter-metrics (do not optimize)**

- **SM-C1: Cold-start wall-clock.** The cold rebuild is network-bound; do not
  chase or promise engine-swap cold-start speedups — F1 benchmarks it
  honestly, nothing more. Counterbalances SM-3 (PRFAQ overclaim guard).
- **SM-C2: Autonomy share.** Do not raise the loop-driven story count by
  weakening gates; "fullest use" ≠ gate removal. Attended boundary events are
  features, not friction. Counterbalances SM-2.
- **SM-C3: Signal count.** Do not promote § 12.1/§ 13.1 candidates to ship
  "more sources"; promotion requires the evidence-gating pattern.
  Counterbalances SM-7.
- **SM-C4: Dashboard breadth.** Demand is feeds > pages; do not grow the
  public-facing page surface beyond D2's factory-status page. Counterbalances
  SM-4 (market-research verdict).

## 8. Open Questions

The spec's § 11 set, numbering stable; none v1-blocking. Q5 (AI Software
Factory scope) was resolved during spec evolution and retired — its outcome
is committed as FR-22/Wave H and it is deliberately absent here. "Gates"
means the named wave/story may not start until the question's re-check is
recorded; nothing blocks PRD approval or earlier waves. **Unattended
resolution: each open question is adopted at its § 11 recommended default
now, and remains a scheduled re-check at its gating wave** — the wave gate
drains the question before dependent stories run.

- **Q1 — Parity tolerance (gates B4 → retirement).** Adopted default: exact
  row-count + value parity on the actionable views (the
  `v_actionable_packages`-family views); timestamp/ordering-only diffs
  documented as benign.
- **Q2 — Dagster footprint + acquisition watch (gates Wave C).** Adopted
  default: on-demand/scheduled invocation locally; persistent daemon only if
  Wave-G sensors require it. Re-verify the Dagster bet at Wave C start
  (release cadence under Prefect, kedro-dagster compatibility, Components/
  Prefect-deployer ramps); switch on concrete deterioration, not headlines.
- **Q3 — Vizro-AI LLM backend (gates D3).** Adopted default: route through
  repo model-backend configuration; never hardcode a public endpoint.
  Defining the `_http.py`-analog LLM routing chain is the real work; known
  bounds: no litellm (py3.14 floor), copilot-api bridge ineligible,
  llama.cpp/ollama/mlx-lm in-env.
- **Q4 — WASM artifact host (gates G2).** Adopted default: GitHub Pages
  public path; emitter host-agnostic for enterprise mirrors.
- **Q6 — Mapping-source consolidation (gates B5's mapping asset).** Adopted
  default: consolidate on migrated Phase C (DuckDB) and re-point
  `name_resolver.py`/`recipe-generator.py`; keep the flat-cache refresh only
  if authoring-time reads prove to need a standalone file. `g10_spelling`
  provenance + no-clobber survive regardless.
- **Q7 — Basilisk landing point (gates B8).** Adopted default: build once as
  Kedro nodes in Wave B; pull a legacy Phase U forward only if trendshift's
  timeline leaves a pre-migration window where interim coverage matters.

## 9. Decisions & Assumptions (unattended intake)

Recorded per the headless protocol; full audit trail in `.memlog.md`.

1. **No human elicitation occurred.** Every choice below is either the spec's
   stated decision or the § 11 recommended default; nothing was invented.
2. **Spec-as-contract:** FR-1..FR-22 numbering, the 0+A–H / 32-story
   structure, § 2.5 graduated autonomy, and the § 12 boundary are preserved
   verbatim in intent. No new scope; § 12.1 candidates stay candidates.
3. **Open questions Q1–Q4, Q6, Q7** adopted at spec defaults (§ 8 above),
   each re-checked at its gating wave.
4. **PRFAQ verdict reflected in framing, not requirements:** CONDITIONAL PASS;
   vision leads with agent-maintainability; AC-7/SM-3 scoped to incremental
   re-materialization; § 3.2 framed chronic-not-acute; severability ramp and
   kill scenarios recorded as risks (§ 11), fallback-not-plan.
5. **Market-research verdict reflected in context only:** feeds > pages,
   B > C > A, no new FRs; scenario deltas remain § 12.1 candidates
   (OSV-export SIG-gated); SM-C4 guards against dashboard-breadth drift.
6. **Config resolution without pixi:** run folder named with the project slug
   `pyforge-atlas` (from the project
   `.bmad-config.toml`) rather than global `project_name: local-recipes`;
   customization resolved via `uv run resolve_customization.py`; live
   `bmad-groundtruth`/`bmad-drift-check` could not run in this container —
   the git-surface groundtruth note (2026-07-17) stands in, and the live CLI
   re-check remains a Wave-0 precondition.
7. **Stakes calibration (assumed):** internal, chain-top (feeds architecture +
   epics + loop execution); solo operator + agent workforce; launch-grade
   rigor on contracts, internal-tool scale on personas/journeys (lighter UJ
   form). `[ASSUMPTION]`
8. **Entry point (assumed):** Vision + Features (capability-first data
   platform); journeys captured in light form rather than elicited.
   `[ASSUMPTION]`
9. **Volatile-count discipline:** live-surface counts cite the spec § 3.3
   snapshot + intake groundtruth rather than free-standing literals, per the
   project-context drift rule.
10. **Addendum:** rejected alternatives, the null-alternative record, tool-bet
    exit ramps, verify-task inventory, and research-artifact pointers live in
    `addendum.md` (downstream architecture input), not the PRD body.
11. **Loop switch target superseded:** spec § 2.5/§ 14 predate this intake and
    say `bmad-switch local-recipes`; this effort's Tier-2/Tier-3 artifacts
    live under the project slug `pyforge-atlas`, so the loop
    precondition is `scripts/bmad-switch pyforge-atlas`
    (§ 6.2). Recorded as a deviation from the spec's literal text — the
    CLAUDE.md marker/symlink desync hazard is exactly what this guards.
12. **Derived hardening (not spec-literal):** "Phase P never loop-reachable"
    (§ 11 risk table) is derived from two spec rules — `PHASE_P_ENABLED=1`
    admin-opt-in and non-credentialed loop gates — not stated verbatim in the
    spec.
13. **Warden-alignment correct-course (2026-07-17, owner-approved):** the
    product packages as `pyforge-atlas` in the shared `pyforge` namespace
    beside `pyforge-warden` (workspace member, warden build pattern), with
    exactly one optional code dependency (`pyforge-atlas[gate]` → warden's
    ComplianceReport schema, F4 only) and pyforge-warden recorded as a
    first-class *data* consumer of the atlas datasets (KEV/EPSS, Basilisk,
    velocity, mapping) — relationship: atlas provides the data, warden uses
    the data; both tools remain independently installable/runnable. Details:
    epics D-16, spine Packaging & namespace row,
    `sprint-change-proposal-2026-07-17.md`. No FR changes — FR-15/FR-18
    already accommodate.

## 10. Why Now

- **The execution machinery just landed:** bmad-method 6.10 + bmad-loop v0.8.1
  are adopted (bmad-loop-adoption W1–W3 done) — the agent workforce that
  justifies node-shaped architecture exists now.
- **Standards matured:** CycloneDX 1.7 = ECMA-424, purl = ECMA-427 (Dec 2025);
  CEP-63 conda-purl in flight; duckdb-wasm at parity.
- **Regulatory clock:** EU CRA Art. 14 reporting starts 2026-09-11, making
  exploited-vuln signal classes (KEV/EPSS/Basilisk) time-relevant.
- **Unfavorable but unwaitable:** orchestrator-market churn (Prefect acquired
  Dagster Labs 2026-07-13). Waiting defers value without reducing
  uncertainty; the exit ramps (§ 11) are the mitigation, and Q2's Wave-C
  re-verify is the checkpoint.
- **Opportunity cost, named once:** ~32 stories displace feedstock-refresh
  throughput; acceptable because § 2.5 unattended execution carries most
  stories, waves are severable with value at each boundary, and B4 is an
  abort ramp bounding sunk cost at Waves 0–B.

## 11. Risks & Mitigations

| Risk | Tripwire | Mitigation / ramp |
|---|---|---|
| Dagster-under-Prefect deterioration breaks `kedro-dagster` (`<2.0` pin, bus factor ≈ 1) | Q2 re-verify at Wave C start | Glue kept thin; exit ramps: Dagster Components or Kedro's Prefect deployer; Kedro DAG stays source of truth |
| B4 parity economically unreachable | Attended parity gate (wave-boundary event) | Abort ramp: keep legacy, salvage the D/G read-surface value via the § 4.6 severability ramp (Ibis-over-SQLite fallback — fallback, not plan) |
| Verify gates never built (verify-first slips) | Wave-A exit criteria: gates are named story deliverables | Loop never enters a wave whose gate doesn't exist |
| Basilisk disappears/changes (pre-announcement API) | Offline-skip marks dataset stale, never fails | `BASILISK_BASE_URL` override; Security-SIG community mapping is the watch-item successor |
| Anaconda CDN/API ToS shift (biggest structural dependency) | § 13 matrix review | S3-parquet consumer path + mirror chain already specced |
| GX ceiling (upstream `<3.14` at 1.19.0) | No story may depend on GX ≥1.19 | pandera-first; validator-agnostic hook lets GX drop out entirely |
| Worktree × multi-project-symlink seam; worktree env-materialization cost | A3 designated first loop story + smoke | Wave-0 bootstrap; lean dedicated env from A1; keystone budget pre-raises (B1/B2/F1) |
| Credential leakage under loop bypass-permissions | FR-1 per-host scoping (a fix, not a port) | Phase P is `PHASE_P_ENABLED=1` admin-opt-in and loop gates are non-credentialed (§ 2.5) — hence never loop-reachable (derived hardening, § 9.12); credentialed runs are attended events |

## 12. Assumptions Index

Inline `[ASSUMPTION]` tags (elicitation gaps):

- § 9.7 — stakes calibration (internal chain-top, solo operator) assumed, not
  elicited.
- § 9.8 — Vision + Features entry point assumed; UJs captured in light form.

Recorded facts with residual verification debt (not elicitation gaps, so not
tagged inline):

- § 0/§ 9.6 — groundtruth verified via git-surface diff only (pixi
  unavailable); live `bmad-groundtruth` remains a Wave-0 precondition.
- § 6.1 — trendshift Phase T remains conditional surface; re-check its status
  alongside groundtruth at execution start (spec § 3.3).
- § 6.2/§ 9.11 — the loop's `bmad-switch` target is
  `pyforge-atlas`, superseding the spec's pre-intake
  `local-recipes` literal.

## 13. References

- Contract: `docs/specs/cfe-atlas-datapipeline-kedro-migration.md` (v5.6).
- Groundtruth: `_bmad-output/projects/pyforge-atlas/planning-artifacts/intake-groundtruth-2026-07-17.md`.
- PRFAQ (kill-test) + distillate:
  `_bmad-output/projects/local-recipes/planning-artifacts/prfaq-cfe-atlas-kedro-migration.md` / `-distillate.md`.
- Research (2026-07-16, all under
  `_bmad-output/projects/local-recipes/planning-artifacts/research/`):
  corpus-gap-analysis, domain-cf-atlas-domain-triad,
  market-cf-atlas-intelligence-surface,
  technical-agentic-sdlc-kedro-migration-execution.
- Companion: `addendum.md` (this workspace) — rejected alternatives,
  null-alternative record, exit-ramp detail, verify-task inventory.
