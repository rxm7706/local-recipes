---
title: cf_atlas Kedro/Dagster/DuckDB Migration
status: final
created: 2026-07-17
updated: 2026-08-01
project: pyforge-atlas
intent_source: docs/specs/cfe-atlas-datapipeline-kedro-migration.md (v5.6, ANALYSIS COMPLETE)
currency_review: Reviewed 2026-08-01 — spec corrections applied to PRD. CAP-8 "28-CLI inventory is answerable" false claim corrected to "8 pages + factory-status; full 28-CLI deferred (DW-D2-1)". FR-4 run-admission retirement (silent-drop cap) already correctly stated (line 248-249). AD-23 lock-store placement details remain architectural (not PRD-level).
---

# PRD: cf_atlas Kedro/Dagster/DuckDB Migration

> **Consolidated 2026-08-02** — see
> `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-unity-data-stack-2026-07-25/prd.md`
> and
> `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-wasm-analytics-stack-2026-07-25/prd.md`
> for the original standalone documents (moved there intact, not deleted).
> This PRD now also carries the Unity Data Stack and
> Wasm Analytics Stack PRDs verbatim as `## Satellite:` sections at the end
> of this file (per explicit user override of the dream-level-only
> consolidation convention — see `docs/dreams/pyforge-atlas.md` § *The
> estate Atlas hosts*). This document's frontmatter `status:` continues to
> describe this primary Atlas PRD only; each satellite section states its
> own status inline. FR/SM/OQ numbering below (FR-1..FR-22, etc.) is
> **local to this primary PRD** — the satellite sections carry their own,
> independently-numbered FR/SM/OQ series; do not conflate the two.

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
- Consequence: the live-confirmed consumer CLIs (`behind-upstream`,
  `query-atlas`, `whodepends`, `feedstock-health`, `my-feedstocks`,
  `detail-cf-atlas`, `staleness-report`) are answerable from pages, where for
  three exceptions "answerable" means the latest-report artifact is surfaced
  read-only. The full 28-CLI inventory port is deferred (`DW-D2-1`); the D2
  gate covers 8 dashboard pages + factory-status. *(Corrected 2026-07-27,
  AUD-ATLAS-041: this clause previously claimed all 28 were answerable.)*
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

**Why DC-2…DC-6 are listed at all — and a correction.** The first reading of this
was that the five bring-ups appeared in no ledger. **That was wrong**, and it was
an artifact of reading a truncated file. They *were* properly deferred at build
time — `DW-C1-1` and `DW-G3` (live daemon), `DW-H1` (MinIO/PostgreSQL),
`DW-H2` (agno LLM synthesis + the F3 `vss` retriever), `DW-H3` (live Wagtail),
`DW-H4` (live crew daemon) — as recorded in the effort run log's index of **54**
deferrals.

The real finding is narrower than first stated: **`implementation-artifacts/deferred-work.md`
is truncated to 9 of those 54 entries**, stopping after `DW-B2-5` — collateral of
the 2026-07-19 copy failure — and it is **gitignored**. It was briefly believed
the other 45 were lost. **They were not**: 52 of 54 survive with full bodies in
the tracked `spec-archive/ATLAS-BMAD-SPECS-CONSOLIDATED.md`, and are now
consolidated into `planning-artifacts/deferred-work-ledger.md` (tracked). Only
**`DW-A2-P4` and `DW-D2`** are genuinely unrecovered.

So DC-2…DC-6 are not "untracked work now tracked" — they are the **durable
re-statement, in Tier 2, of deferrals whose Tier-3 ledger did not survive**. That
is precisely why they belong here and not there.

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

---

## Satellite: Unity Data Stack

> **Folded in verbatim 2026-08-02** from
> `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-unity-data-stack-2026-07-25/prd.md`
> (status at fold-in: `draft`; frontmatter also carried its own
> `currency_review` note dated 2026-08-04). Content below is unmodified from
> the standalone document (its own `addendum.md` companion is not duplicated
> here — see that same archived folder). Its FR-1..FR-60 / SM-1..SM-9 /
> OQ-1..OQ-23 numbering is local to this satellite section and is
> independent of the primary PRD's FR-1..FR-22 above.

### PRD: Unity Data Stack

#### 0. Document Purpose

This PRD is for the architecture stage that follows it, for the platform team who will build
Unity, and for the enterprise stakeholders who must decide whether to adopt it. It is
**capability-oriented**: it states what the platform must do and how that will be verified.
Mechanism — which tool, which flag, which file layout — belongs in `addendum.md` and in the
architecture document, except where a specific technology is itself a **requirement inherited
from the Constitution**, in which case the provenance is cited (see § 14).

Structure: a Glossary anchors vocabulary (§ 3); features group globally-numbered Functional
Requirements (§ 5); cross-cutting quality lives in its own section (§ 6); enterprise and
regulated-domain concerns get dedicated sections (§ 7–9, § 13); and two sections exist that a
generic PRD would not have — **§ 14 Constitution Provenance Map** (every mandate traced to the
requirement that carries it) and **§ 15 Research Deltas** (every intake claim that research
falsified, with the correction).

**This PRD builds on prior artifacts and does not duplicate them.** The product brief
(`briefs/brief-unity-data-stack-2026-07-25/brief.md`) carries positioning and the problem
narrative; its `addendum.md` carries the full intake inventory — the Constitution's 14-article
map, the ~200-task taxonomy, the platform-conditional dependency knowledge, and the
rejected/superseded ledger. The two research reports carry the evidence base and every citation.

`[ASSUMPTION]` This PRD was produced headless with no user present. Every inferred value is
tagged inline and indexed in § 17. **Nothing tagged `[ASSUMPTION]` should be treated as
confirmed scope.**

---

#### 1. Vision

Unity Data Stack is the **conda-native, air-gap-first, spec-governed monorepo platform for
enterprise Python data engineering** — one shared repository where teams across an organization
co-contribute reusable templates, plugins, libraries, components, services, dashboards, reports,
and applications on a single opinionated toolchain.

The value is not the monorepo. It is that **six problems get solved once instead of once per
team**: resolving native dependencies, reproducing an environment offline, satisfying
supply-chain compliance, deploying to OpenShift, testing across platforms, and letting another
team contribute without breaking anything. Each team currently solves these slightly
differently, and the organization pays for the difference forever — in onboarding time, in
duplicated internal libraries, in audits measured in weeks, and in the quiet conclusion that
sharing code across teams is more trouble than it is worth.

Unity's distinguishing property is that its reproducibility guarantee covers the **whole** stack.
Wheel-native monorepo platforms resolve Python packages; a data platform is also made of DuckDB,
Arrow's ABI, PostgreSQL client libraries, nginx, and Node. Unity resolves both halves together,
offline, on every supported platform — and emits the compliance evidence to prove what it
resolved.

**Unity assembles more than it invents.** Realized capability in the host repository —
`pyforge-warden` (multi-axis compliance gating), `conda-forge-expert` and 769 maintained
feedstocks (conda-native supply), the `enterprise-airgap` routing doctrine, `pyforge-atlas`
(dependency intelligence) — covers a large fraction of the intake ambition. Unity is principally
an **integration and governance** effort, plus genuinely new work on the lock architecture, the
governance split, and the contribution model.

---

#### 2. Why Now

Timing is load-bearing, for two independent reasons.

**The regulatory clock.** The EU Cyber Resilience Act entered into force 2024-12-10.
**Vulnerability-reporting obligations begin 2026-09-11** — approximately seven weeks after this
document's date — requiring manufacturers to report actively exploited vulnerabilities. Main
obligations, covering the full product lifecycle, apply **2027-12-11**. Obligations propagate
through the value chain, so an internal platform feeding products placed on the EU market
inherits the evidentiary burden. "Know what you ship, continuously" moves from good practice to
dated legal duty inside this PRD's planning horizon.

`[ASSUMPTION]` CRA is treated as a **design forcing-function and a capability Unity must be able
to discharge** — not as an assertion that every Unity deployment is regulated. Applicability
depends on whether the adopting enterprise places products with digital elements on the EU
market. See OQ-3 and OQ-16.

**The artifact decay clock.** Three substantial intake artifacts exist — a 37 KB Constitution,
a 1,726-line working pixi root, a 12 KB toolchain spec — authored 2026-01 → 2026-05 and never
landed in a repository. Research has now verified that they have measurably drifted (§ 15):
pixi has moved 14 minor versions past a hard exact pin that blocks installation outright; a
flagship command depends on a flag that does not exist; Python 3.12 has gone security-only and
3.15 first-releases 2026-10-01. **The work either lands soon or the intake set needs
re-verification from scratch.**

---

#### 3. Target User

##### 3.1 Jobs To Be Done

- **Ship a data product** without becoming a toolchain administrator first.
- **Install a colleague's internal library** and have it work on the first attempt.
- **Reproduce an environment** offline, on a different OS, months later, byte-for-byte.
- **Contribute a fix** to shared code owned by another team, and have it land in days.
- **Answer "what is in our estate, and is any of it being exploited right now?"** continuously,
  with evidence, without a person walking N repositories.
- **Set a standard once** and have it hold, without policing it by hand.
- **Deploy behind a firewall** as the ordinary path, not as a project.
- **Onboard a new engineer** without transferring tribal knowledge.

##### 3.2 Non-Users (v1)

`[ASSUMPTION]` These audience boundaries were inferred from the Dream and the intake artifacts,
not confirmed with a stakeholder.

- **Teams outside Python/data.** Unity is Python-first by mandate; a front-end-only or JVM team
  is not a v1 audience (Node tooling exists only in service of Python-backed applications).
- **Organizations wanting a hosted SaaS platform.** Unity is a platform an enterprise runs.
- **Teams needing a service catalog/portal.** That is Backstage's job; see § 10.
- **Single-team projects.** Unity's cost is justified by cross-team sharing. One team with one
  service should not adopt it.

##### 3.3 Key User Journeys

Unity is developer infrastructure, so journeys are scoped to the moments where the platform's
value or failure is actually felt. Four carry the product.

- **UJ-1. Dana joins the `cdo` team and is productive before lunch.**
  Dana is a data engineer, first day, laptop freshly imaged, no prior context on this
  organization's toolchain. Entry state: repository access, nothing installed but git.
  Path: she clones, runs the documented bootstrap command, and pixi materializes the
  `local-dev` environment; she runs the task that starts the local stack; she opens the Dagster
  UI and sees assets running against a local DuckDB. Climax: she edits an asset, runs the
  package's test task, and it passes — without having asked anyone a question. Resolution: she
  has a working environment identical to CI's and knows the four commands that matter.
  **Edge case:** her machine is behind the corporate proxy with no public internet — she sources
  the air-gap configuration and the same commands work against the internal mirror.

- **UJ-2. Marcus installs a library another domain published, and it just works.**
  Marcus works in `customer`; the `cdo` team published a shared analytics library that depends on
  DuckDB, PyArrow, and a PostgreSQL client. Entry state: an existing working environment.
  Path: he adds the dependency, the Workspace re-solves, and the native components resolve
  alongside the Python ones. Climax: `import` works first try; no ABI error, no manual system
  package, no day lost. Resolution: he uses the shared Package instead of writing a second one.
  **Edge case:** the solve genuinely conflicts — the platform reports which package and which
  constraint, and the compatibility-detection Environment (§ 5.1, FR-7) has usually caught it
  before he did.

- **UJ-3. Priya fixes a bug in code her team does not own.**
  Priya finds a defect in a shared Package owned by another Domain. Entry state: she has the fix
  in her head and no commit rights on that Package. Path: she reads the Package's declared
  ownership, opens a branch following the documented contribution path, writes the regression
  test the standard requires, and opens a PR; the automated gates run; the **Trusted Committer**
  for that Package is auto-requested as reviewer. Climax: the Trusted Committer reviews and
  merges — days, not quarters. Resolution: the fix is in the shared Package; there is no fork.
  **Edge case:** the Trusted Committer disagrees with the approach — the disagreement is resolved
  in the PR against the Constitution's stated Mandates rather than by seniority.

- **UJ-4. Sam answers the auditor before the meeting ends.**
  Sam owns compliance. Entry state: an auditor asks what open-source components are in the
  production estate, under what licences, and whether anything is being actively exploited.
  Path: Sam retrieves the Compliance Report and SBOM produced by the most recent build of each
  deployed artifact. Climax: the answer is a generated artifact carrying Provenance, not a
  three-week reconciliation exercise. Resolution: Sam files it. **Edge case:** a component *is*
  affected by an actively-exploited vulnerability — the platform already flagged it and the
  remediation PR is open.

---

#### 4. Glossary

Downstream artifacts must use these terms exactly.

- **Workspace** — the single Unity repository root; the unit that defines shared configuration,
  the supported-platform matrix, and the set of Packages.
- **Package** — one independently-manifested unit inside the Workspace (a shared library, an
  infrastructure service, or a domain service). Has an owner, a manifest, and tests.
- **Feature** — a named, reusable block of dependency and configuration declarations.
  Features compose into Environments. (Pixi terminology, adopted deliberately.)
- **Environment** — a named, solvable composition of Features that a developer or CI job
  activates. One Environment is active at a time.
- **Stage** — one of the twelve points in the delivery lifecycle (`public`, `local`, `agents`,
  `vendor`, `dev`, `ci`, `integration`, `testing`, `uat`, `production`, `dr`, `oss`). A Stage
  carries a branch policy, a Data Classification, a network posture, and a datastore.
  **A Stage is not an Environment** — see FR-9.
- **Data Classification** — one of `Public`, `Deidentified`, `Proprietary`, `Restricted`,
  attached to a Stage and governing what data may be present.
- **Domain** — a business-owned area (e.g. `customer`, `cdo`) that owns Data Products and the
  Packages that produce them.
- **Data Product** — a Domain's published analytical output, versioned and contract-bearing.
- **Layer** — one of `Raw`, `Curated`, `Consumption`; the stage of refinement of a Data Product.
- **Asset** — an orchestrated unit of computation producing part of a Data Product.
- **Lockfile** — a resolved, hash-bearing record sufficient to reproduce an Environment without
  re-resolution.
- **Workspace Lock** — the authoritative Lockfile covering both native and Python packages.
- **Exported Lock** — a derived, standards-format Lockfile (PEP 751 `pylock.toml`) generated
  from the Workspace Lock for consumers that cannot read the Workspace Lock.
- **Compliance Report** — the schema-validated machine-readable output of the compliance gate,
  covering hygiene, security, licence, and currency findings.
- **SBOM** — a Software Bill of Materials describing the components of a built artifact.
- **Provenance** — a signed or unsigned attestation describing how an artifact was built.
- **Constitution** — the governing standards document; the source of Unity's mandates.
- **Mandate** — a Constitution rule. Either a **Platform Invariant** (binding everywhere, not
  overridable) or a **Domain Default** (overridable by a Domain with recorded justification).
- **Trusted Committer** — the named role, per Package, accountable for reviewing and accepting
  contributions from outside the owning team.
- **Quality Gate** — the single command that runs every automated check, byte-identical to what
  CI runs.
- **Air-Gap Mode** — operation with no public network egress, all dependencies served from
  internal mirrors.
- **Offline Bundle** — a self-contained, transportable artifact sufficient to materialize an
  Environment with no network access at all.

---

#### 5. Features

Nine features, FR-1 through FR-60.

##### 5.1 Workspace Substrate

**Description.** The Workspace is the foundation: one root that declares the supported platform
matrix, the shared channels and mirrors, the Features, the Environments, and the set of
Packages. Every other feature stands on it. Realizes UJ-1, UJ-2.

The intake working root proves the shape works and simultaneously demonstrates three defects the
substrate must not reproduce: an exact toolchain pin that blocks installation, a fat base
dependency block inherited by environments declared minimal, and ~35 lines of commented-out
duplicate declarations standing in for a feature the toolchain now provides natively (see
brief addendum § C.4).

**Functional Requirements**

###### FR-1: Single Workspace root

A platform engineer can declare, in one Workspace root, the supported platform matrix, the
package channels, the minimum system requirements, and the set of Packages.

**Consequences (testable):**
- The root declares a platform matrix; every declared platform resolves.
- The root declares minimum OS/kernel floors, and a machine below the floor fails with a
  diagnostic naming the unmet requirement rather than an opaque solver error.
- Adding a Package requires editing exactly one place in the root.

###### FR-2: Toolchain version pinned as a range, never an exact equality

The Workspace declares its required workspace-manager version as a floor with a tested ceiling.

**Consequences (testable):**
- A developer on any toolchain version within the declared range can open the Workspace.
- A developer below the floor gets a diagnostic naming the required minimum.
- **Provenance/delta:** supersedes the intake root's `requires-pixi = "==0.59.0"`, which blocks
  every current install (research D4). See § 15.

###### FR-3: Environments compose from Features with no inherited bloat

Environments are composed from named Features, and an Environment declared minimal contains only
what it declares.

**Consequences (testable):**
- Every Environment declares which Features it composes and why it exists.
- Environments declared minimal-footprint (`production`, `dr`, `oss`) do **not** contain build
  tooling, package-authoring tooling, or developer utilities.
- The installed size of a minimal Environment is measured and asserted against a documented
  ceiling; regressions fail the Quality Gate.
- **Provenance/delta:** supersedes the intake root's fat base dependency block, inherited by
  every Environment including those declared minimal (brief addendum § C.4.2).

###### FR-4: No duplicated dependency declarations

A dependency version is declared once in the Workspace and referenced elsewhere.

**Consequences (testable):**
- No dependency version string appears twice across the root's Features and targets.
- A lint check fails the Quality Gate on duplication.

###### FR-5: Per-Package manifests with declared ownership

Each Package carries its own manifest declaring its dependencies, its tests, its owning Domain
or team, and its Trusted Committer.

**Consequences (testable):**
- Every Package resolves an owner and a Trusted Committer; a Package with neither fails the gate.
- Package-scoped tasks (test, lint) exist for every Package and are discoverable uniformly.

###### FR-6: Platform-conditional dependency handling

The Workspace expresses dependencies that are unavailable on a subset of platforms, with the
reason recorded, and still resolves on every declared platform.

**Consequences (testable):**
- Each platform-conditional declaration carries a machine-readable reason code and a
  human-readable note (e.g. "conda-forge lacks `python-quickjs` on osx-arm64").
- Every declared platform resolves; a platform that cannot resolve is either removed from the
  matrix or has its blocker recorded.
- **Provenance:** preserves the hard-won portability knowledge in the intake root
  (brief addendum § C.5) rather than rediscovering it.

###### FR-7: Cross-stack compatibility detection

The Workspace provides an Environment that composes the full mandated library set for the
purpose of detecting cross-library conflicts before they reach a Domain.

**Consequences (testable):**
- The compatibility Environment solves, or fails with a named conflicting pair.
- It runs on a schedule and on dependency-changing PRs.
- It is explicitly not a deployable Environment.
- **Provenance:** the intake root's `monorepo-full-stack` environment, kept — an unusually good
  idea, and an honest acknowledgement of the mandated stack's compatibility surface.

###### FR-8: Excluded Packages carry their exclusion reason

A Package excluded from the default composition records why, and the exclusion is discoverable.

**Consequences (testable):**
- Each exclusion states the blocking conflict and the condition under which it would be revisited.
- **Provenance:** `airflow-server` (SQLAlchemy <2.0 conflict with the orchestrator) and
  `sharepoint-mcp-server` (pyjwt conflict) are carried forward as documented exclusions.

###### FR-9: Stages are modelled separately from Environments

The twelve Stages are represented as a first-class concept distinct from Environments, carrying
branch policy, Data Classification, network posture, and datastore.

**Consequences (testable):**
- A Stage resolves to exactly one Environment; multiple Stages may share one Environment.
- Changing a Stage's Data Classification does not require re-solving an Environment.
- The number of distinct solved Environments is bounded by genuine dependency-set variation, not
  by the Stage count.
- **Provenance/delta:** the intake root declares ~20 Environments in which five are byte-identical
  (`vendor`/`dev`/`integration`/`testing`/`uat`) and three more are identical (`production`/`dr`/
  `oss`) — twelve Stages collapsing to roughly four dependency sets (brief addendum § B.1).
  See OQ-9.

**Notes.** `[NOTE FOR PM]` FR-9 is the one requirement in this feature that changes the intake
design rather than correcting it. It is stated as a requirement because the conflation has a
measurable cost (eight redundant solves), but the counter-argument — that semantic Environment
names are a valuable operator contract — is real. Architecture must decide (OQ-9).

---

##### 5.2 Dependency Resolution and Lock Architecture

**Description.** The reproducibility guarantee. Unity resolves native and Python packages
together and produces a Workspace Lock that reproduces an Environment on every supported
platform, offline. Consumers that cannot read the Workspace Lock get an Exported Lock in the
PEP 751 standard format, derived from it. Realizes UJ-1, UJ-2.

This is the feature the intake set got most wrong, and the correction is load-bearing: PEP 751
does **not** guarantee multi-platform coverage (it uses environment markers), and the intake
toolchain spec's flagship generation command uses a flag that does not exist. The
"Cryptographic Predictability" outcome it promised currently has no verified mechanism (§ 15,
D1 + D3).

**Functional Requirements**

###### FR-10: One authoritative Workspace Lock covering both native and Python packages

The Workspace produces a single Lockfile that records resolved native (conda) and Python (PyPI)
packages together, with hashes.

**Consequences (testable):**
- The lock reproduces an identical Environment on a clean machine with no resolution step.
- Native components (database engines, columnar libraries, web servers, language runtimes) are
  covered by the same guarantee as Python packages.
- The lock is committed to version control.

###### FR-11: Multi-platform coverage is verified, not assumed

For every declared platform, the Workspace proves the lock is sufficient to materialize the
Environment on that platform.

**Consequences (testable):**
- A gate materializes each Environment on each declared platform (natively or via emulation) and
  fails if any platform is uncovered.
- Coverage is reported per platform, not as a single boolean.
- **Provenance/delta:** the intake toolchain spec asserted the lockfile format guarantees
  multi-platform targets; PEP 751 explicitly does not (§ 15, D1).

###### FR-12: Exported Lock in PEP 751 format, derived from the Workspace Lock

The Workspace generates a PEP 751 `pylock.toml` from the Workspace Lock for standards-consuming
tools.

**Consequences (testable):**
- The Exported Lock validates against PEP 751 `lock-version` 1.0.
- Regenerating it from an unchanged Workspace Lock is byte-stable.
- A drift check fails the Quality Gate when the Exported Lock does not match the Workspace Lock.
- `[ASSUMPTION]` The Workspace Lock is authoritative and the Exported Lock is derived
  (pixi-primary). The reverse direction and a split-by-tier variant are live alternatives —
  **this is the single decision everything downstream depends on** (OQ-1).

###### FR-13: Offline Bundle for air-gapped materialization

The Workspace produces a transportable Offline Bundle that materializes a named Environment with
no network access.

**Consequences (testable):**
- A machine with no network egress materializes the Environment from the bundle alone.
- The bundle records which Environment and which lock it was built from.
- Bundle production is a documented, repeatable task.

###### FR-14: Mirror routing by environment variable only

All package sources are redirectable to internal mirrors through environment variables, with no
edit to any committed manifest.

**Consequences (testable):**
- The same committed manifest resolves against public sources and against internal mirrors,
  selected only by environment.
- No mirror hostname is required in any committed file for Air-Gap Mode to work.
- **Provenance:** Constitution Art. II § 2.2 (air-gap capability); the intake root's
  `CONDA_CHANNEL_ALIAS` / `PIP_INDEX_URL` / `UV_INDEX_URL` / `GHE_HOST` design, kept.

###### FR-15: Credentials never appear in URLs or command lines

Registry credentials are supplied through a credential store or masked runner inputs, never
interpolated into index URLs, manifests, lockfiles, or command arguments.

**Consequences (testable):**
- No committed file contains a credential-bearing URL, including variable-interpolated forms.
- No CI step passes a credential as a command-line argument.
- A scan for credential-bearing URL patterns fails the Quality Gate.
- **Provenance/delta:** the intake toolchain spec declares a Token Isolation Rule and then
  violates its spirit with `https://${USER}:${TOKEN}@…` in `extra-index-urls` and a
  `--index-url` interpolation in CI (brief addendum § D.1, research § 4.3).

###### FR-16: Credentials are attached per host

Outbound requests receive credentials only for the host those credentials belong to.

**Consequences (testable):**
- A request to a host other than the configured registry carries no registry credential.
- A test asserts non-attachment for a non-matching host.
- **Provenance:** closes the known `JFROG_API_KEY` unconditional-injection defect recorded in
  the `enterprise-airgap` Dream, at the platform level.

###### FR-17: Dependency update policy is explicit and recorded

Packages held back from automatic updating are listed with a reason and a revisit condition.

**Consequences (testable):**
- Every held-back package has a recorded reason (LTS pin, transitive constraint, known breakage).
- A held-back package with no reason fails the gate.
- **Provenance/delta:** the intake root holds ten packages back in an inline command comment with
  no recorded rationale (brief addendum § C.6).

---

##### 5.3 Quality Gate

**Description.** One command runs every automated check, and it is byte-identical to what CI
runs. This is what makes "it passed locally" a guarantee instead of a hope, and it is the
mechanism by which the Constitution stops being a wiki page. Realizes UJ-1, UJ-3.

**Functional Requirements**

###### FR-18: Single Quality Gate command with CI parity

A developer runs one command that executes every check CI executes.

**Consequences (testable):**
- The set of checks run locally equals the set run in CI; a parity test asserts this and fails
  when they diverge.
- Local pass predicts CI pass; the green-local/red-CI rate is measured (SM-3).
- **Provenance:** Constitution Art. IV § 4.6 — "This matches exactly what CI runs."

###### FR-19: Lint, format, and type checking

The Quality Gate enforces linting, formatting, and static type checking across Python, and
configuration formats (TOML, YAML, SQL).

**Consequences (testable):**
- A style or type violation fails the gate with a file and line reference.
- Formatting is auto-correctable by a documented command.
- **Provenance:** Constitution Art. IV § 4.1–4.3.

###### FR-20: Test coverage thresholds enforced

The Quality Gate enforces the Constitution's coverage requirements and fails on regression.

**Consequences (testable):**
- Asset-producing code meets the mandated 100% coverage threshold; other Python modules meet the
  mandated 80% minimum.
- Coverage that decreases relative to the base branch fails the gate.
- **Provenance:** Constitution Art. III § 3.1, § 3.5.

###### FR-21: Tests precede implementation for new code, and regressions precede fixes

New capability lands with its tests; a bug fix lands with a test that fails without the fix.

**Consequences (testable):**
- The contribution standard states the requirement and review verifies it.
- `[ASSUMPTION]` Enforcement is by review rather than by automation — automated
  test-before-implementation detection is unreliable. See OQ-13.
- **Provenance:** Constitution Art. III § 3.1.

###### FR-22: Security scanning in the Quality Gate

Static code security analysis and dependency vulnerability scanning run in the gate.

**Consequences (testable):**
- A finding above the configured severity threshold fails the gate.
- Findings carry a stable identifier so they can be baselined and tracked.
- **Provenance:** Constitution Art. IV § 4.4, Art. XII § 12.5. Implementation via the
  Compliance Report (§ 5.6) rather than a separate mechanism.

###### FR-23: Pre-commit hooks mirror a subset of the gate

Fast checks run at commit time; the full gate runs on demand and in CI.

**Consequences (testable):**
- Commit-time checks complete within a documented time budget (NFR-4).
- Every commit-time check is also in the full gate.
- **Provenance:** Constitution Art. IV § 4.5.

###### FR-24: Local CI execution

A developer can execute the CI workflows locally before pushing.

**Consequences (testable):**
- A documented command runs the CI workflow set locally.
- **Provenance:** Constitution Art. X § 10.3; the intake root's `act-ci-*` tasks.

###### FR-25: Behavioural test tier with selectable slices

The Workspace supports behaviour-level tests alongside unit tests, selectable by tag.

**Consequences (testable):**
- A smoke slice runs in under the documented budget and is usable as a fast pre-merge signal.
- Slices are selectable by tag (smoke, integration, per-Domain).
- **Provenance/delta:** present in the intake root (behave, with `@smoke`/`@integration` tags) and
  **absent from the Constitution's Art. III**, which describes only unit/integration/asset tiers.
  Article III should be amended (§ 14.3).

---

##### 5.4 Constitution and Governance

**Description.** Unity's standards are machine-enforced, and the Constitution is the source. The
central new work is the **global-versus-local split**: which Mandates are Platform Invariants
binding everywhere, and which are Domain Defaults a Domain may override with recorded
justification. Without that split Unity is centrally imposed rather than innersource, and it
violates the federated half of federated computational governance. Realizes UJ-3.

**Functional Requirements**

###### FR-26: Every Mandate is classified as Platform Invariant or Domain Default

The Constitution classifies each Mandate, and the classification is machine-readable.

**Consequences (testable):**
- Every Mandate resolves to exactly one classification; an unclassified Mandate fails the gate.
- Platform Invariants cannot be overridden by any Package or Domain.
- **Provenance/delta:** the Constitution currently declares itself uniformly "immutable" and
  "non-negotiable", which conflicts with Data Mesh principle 4 (research § 3.1). See OQ-5.

###### FR-27: Domain Default overrides require a recorded decision

A Domain overriding a Domain Default records the decision, its rationale, its alternatives, and
its consequences.

**Consequences (testable):**
- An override without a linked decision record fails the gate.
- Overrides are enumerable — a reader can list every active override and its reason.
- **Provenance:** Constitution Art. V § 5.4 (ADRs), Art. II § 2.5, Art. XIII § 13.3, generalized
  from pixi-scoped exceptions to all Domain Defaults.

###### FR-28: Violations report the clause they violate

An automated check that fails a Mandate names the Constitution section and clause.

**Consequences (testable):**
- Every Mandate-enforcing check carries the identifier of the clause it enforces.
- A failure message includes that identifier.
- **Provenance:** Constitution Governance § Agent Mandate — "Agents MUST report audit failures by
  referencing the specific section and clause."

###### FR-29: Mandates without an enforcing check are visible

The platform reports which Mandates are automatically enforced and which rely on human review.

**Consequences (testable):**
- A coverage report lists every Mandate and its enforcement status.
- A Mandate claimed as enforced with no corresponding check fails the report.

###### FR-30: Constitution amendment is a governed, versioned process

Amendments follow a defined process and the document carries a version and ratification date.

**Consequences (testable):**
- The Constitution carries semantic version, ratified date, amended date, and next-review date.
- An amendment produces a log entry describing what changed and why.
- A review date in the past raises a warning.
- **Provenance/delta:** Constitution Governance § Amendment Process. The intake Constitution is
  v1.2.0 with `Next Review: 2026-02-20` — **already five months overdue** (brief addendum § A.2.5).

###### FR-31: Architecture decisions are recorded

Significant technical decisions are captured as decision records with context, alternatives,
decision, and consequences.

**Consequences (testable):**
- The decision record set is discoverable and indexed.
- A change matching the Constitution's complexity-gate criteria without a decision record fails
  review.
- **Provenance:** Constitution Art. V § 5.4, Art. XIII § 13.3.

###### FR-32: Documentation exists where the Constitution requires it

Every major directory carries documentation covering purpose, setup, usage, dependencies, and
ownership.

**Consequences (testable):**
- A check fails when a Package or major directory lacks the required documentation.
- Documentation links resolve (link check in the gate).
- **Provenance:** Constitution Art. V § 5.3, Art. X § 10.1.

---

##### 5.5 Innersource Contribution Model

**Description.** The largest gap in the intake set, found independently from two research angles.
The Constitution requires "at least one human approval" and never says whose; the toolchain
spec's role matrix omits every feedback-loop role. For a platform whose entire premise is
cross-team co-contribution, **the social layer is essentially unspecified**. This feature
supplies it. Realizes UJ-3, UJ-1.

**Functional Requirements**

###### FR-33: Every Package has a named Trusted Committer

Each Package declares one or more Trusted Committers accountable for reviewing and accepting
outside contributions.

**Consequences (testable):**
- Every Package resolves at least one Trusted Committer; a Package without one fails the gate.
- The Trusted Committer is auto-requested as reviewer on a PR touching that Package.
- The role's responsibilities and expected response window are documented.
- **Provenance/delta:** supplies what Constitution Art. VIII § 8.3 leaves undefined
  (research OQ-M5).

###### FR-34: A documented contribution path for outside contributors

A contributor from outside the owning team can find, in one place, how to contribute to a
Package they do not own.

**Consequences (testable):**
- The path covers: finding the owner, branch convention, required tests, review expectation, and
  escalation when the Trusted Committer does not respond.
- A new contributor completes a first contribution using only written documentation.
- **Provenance:** InnerSource Commons practice (Trusted Committer, host team, contributor);
  absent from the intake set.

###### FR-35: Branch and commit conventions are enforced

The Workspace enforces its branching model and commit message convention automatically.

**Consequences (testable):**
- A non-conforming PR title or commit fails an automated check.
- The default integration branch is explicit and documented.
- **Provenance:** Constitution Art. VIII § 8.1–8.2. `[NOTE FOR PM]` The Constitution mandates
  Gitflow with `develop` as default — **this conflicts with the host repository's trunk-based
  `main` convention**. Unity is a separate repository so there is no direct collision, but the
  choice should be re-confirmed rather than inherited (OQ-11).

###### FR-36: Merge gates are explicit and automated

The conditions for merge are enumerated and machine-checked where possible.

**Consequences (testable):**
- All seven Constitution PR gates are represented; each is marked automated or human.
- A PR cannot merge with any automated gate failing.
- **Provenance:** Constitution Art. VIII § 8.3.

###### FR-37: Scaffolding templates for new Packages and Data Products

A contributor generates a conforming new Package or Data Product from a template.

**Consequences (testable):**
- A generated Package passes the Quality Gate immediately, with no manual fixes.
- Templates cover at minimum: shared library, service, and Data Product.
- Starting from a template is the documented default path.
- **Provenance:** Constitution § 1.3 (`templates/` for agentic code generation).

###### FR-38: Contribution and reuse are measured

The platform reports cross-team contribution and shared-library reuse over time.

**Consequences (testable):**
- Reports distinguish contributions to owned versus non-owned Packages.
- Reports surface internal forks/duplicates as a counter-signal.
- Validates SM-2 and SM-C1.

---

##### 5.6 Supply-Chain Compliance and Evidence

**Description.** Compliance is a build artifact, not an activity. Every built artifact carries an
SBOM and Provenance; the estate is continuously gated against actively-exploited vulnerability
data. This is the feature the regulatory clock (§ 2) makes urgent — and it is largely
**integration** work: `pyforge-warden` already implements a strict superset of the intake spec's
approach. Realizes UJ-4.

**Functional Requirements**

###### FR-39: Versioned SBOM for every built artifact

Every artifact produced for deployment carries an SBOM in a declared, version-pinned standard
format.

**Consequences (testable):**
- The SBOM validates against the declared specification version.
- The specification version is pinned and recorded, not implicit.
- The SBOM is attached to or discoverable from the artifact.
- **Provenance/delta:** the intake spec emits unversioned CycloneDX; CycloneDX 1.7 is now
  **ECMA-424**, so "CycloneDX" alone no longer identifies a single contract (research § 2.1).

###### FR-40: Runtime-scoped and full SBOM variants

The platform produces both a runtime-scoped SBOM (deployed components only) and a full SBOM
(including development and test components).

**Consequences (testable):**
- The runtime SBOM contains no development-only or test-only component.
- Both are produced from the same resolved source and are mutually consistent.
- **Provenance:** the intake spec's `sbom-prod` / `sbom-full` split, kept.

###### FR-41: SBOM carries a dependency graph, not a flat component list

The SBOM records dependency relationships between components, not merely their presence.

**Consequences (testable):**
- The SBOM's dependency relationships are populated and non-trivial.
- A test asserts that a known transitive relationship appears as an edge.
- **Provenance/delta:** the intake spec's generator, in the mode the spec uses, carries a
  documented "no transitive components will be identified" caveat. A flat inventory answers
  "do I ship X?" but not "what reaches X?" — which is what exploitability analysis requires
  (research § 2.2). **Verify empirically and early** (OQ-6).

###### FR-42: Build Provenance attestation

Every built artifact carries an attestation describing how it was built.

**Consequences (testable):**
- The attestation records the building entity, the build process, and the top-level inputs
  (SLSA Build L1 minimum).
- `[ASSUMPTION]` v1 targets **L1 mandatory, L2 (signed provenance from a hosted build platform)
  as the goal**; L3 is out of scope. See OQ-7.
- **Provenance/delta:** provenance is **entirely absent** from the intake set. SBOM says what is
  *in* an artifact; nothing said how it came to be (research § 2.3).

###### FR-43: Continuous vulnerability gating with exploitation status

The platform continuously evaluates the estate against vulnerability data enriched with
exploitation status, and gates on configurable thresholds.

**Consequences (testable):**
- Findings distinguish known-exploited vulnerabilities from merely-published ones.
- Thresholds are configurable per Stage; a `production`-bound artifact with an exploited-vulnerability
  finding fails its gate.
- Time from vulnerability publication to a determination of affectedness is measured (SM-5).
- **Provenance/delta:** supersedes the intake spec's `pip-audit`-based scan — which covers neither
  pixi manifests nor exploitation status — with the existing Compliance Report capability
  (research § 5.1.3). See OQ-4 for the integration boundary.

###### FR-44: Schema-validated Compliance Report

The compliance gate emits one machine-readable report covering hygiene, security, licence, and
currency findings.

**Consequences (testable):**
- The report validates against a published schema.
- The gate's exit code reflects the report's verdict.
- The report is retained as evidence with a timestamp and the inputs it evaluated.

###### FR-45: Baselining and grandfathering

Existing findings can be baselined so that a gate can be adopted without a flag day, while new
findings still fail.

**Consequences (testable):**
- A baselined finding does not fail the gate; a new finding does.
- Baseline entries carry an owner and a revisit condition.
- The baseline shrinks over time and its size is reported.

###### FR-46: Licence policy enforcement

Component licences are evaluated against a declared policy.

**Consequences (testable):**
- A component under a disallowed licence fails the gate, naming the component and licence.
- The policy is declared in one place and is auditable.
- **Provenance:** Constitution Art. XII § 12.4 ("Review dependency licenses").

###### FR-47: Remediation proposals are automated and opt-in

The platform can propose dependency remediations as reviewable change proposals.

**Consequences (testable):**
- A remediation proposal is a reviewable PR, never an automatic merge.
- The proposal states which finding it addresses.
- Actuation is opt-in per Package.
- **Provenance/delta:** the intake spec's daily auto-patch workflow, retained in spirit and
  superseded in mechanism — it had no severity gate, no exploitation awareness, and no evidence
  trail.

---

##### 5.7 Data Product Platform

**Description.** Domains own Data Products, layered Raw → Curated → Consumption, orchestrated as
Assets with declared contracts. This is the part of the intake Constitution that is most complete
and most faithful to its source architecture — Article VII implements Data Mesh principles 1 and
2 well (research § 3). The requirements here mostly ratify it. Realizes UJ-2.

**Functional Requirements**

###### FR-48: Domain-owned Data Products with enforced boundaries

Each Data Product belongs to exactly one Domain; cross-Domain consumption happens through
published interfaces, not direct datastore access.

**Consequences (testable):**
- Every Data Product resolves an owning Domain.
- A cross-Domain direct datastore access is detectable and fails review.
- **Provenance:** Constitution Art. VII § 7.1, § 7.4.

###### FR-49: Three-Layer refinement model

Every Data Product declares its Layer as `Raw`, `Curated`, or `Consumption`.

**Consequences (testable):**
- An Asset with no Layer, or an invalid Layer, fails the gate.
- **Provenance:** Constitution Art. VII § 7.2. Recorded as a deliberate Unity convention — the
  Data Mesh source text is silent on internal layer naming (research § 3.2).

###### FR-50: Enforced Asset naming convention

Asset names follow `<domain>_<layer>_<entity>_<verb>`.

**Consequences (testable):**
- A non-conforming name fails an automated check.
- The `<domain>` segment must match a declared Domain and `<layer>` a declared Layer.
- **Provenance:** Constitution Art. VII § 7.3.

###### FR-51: Asset metadata contract

Every Asset declares owner, domain, layer, and update frequency as structured metadata.

**Consequences (testable):**
- An Asset missing any required metadata field fails the gate.
- Metadata is queryable across the Workspace — the answer to "what does this Domain publish?"
  is generated, not maintained.
- **Provenance:** Constitution Art. V § 5.2, Art. IX § 9.1.

###### FR-52: Data Product contracts with compatibility policy

Each Data Product publishes a schema contract; breaking changes are versioned.

**Consequences (testable):**
- A schema change that breaks a declared consumer is detected before merge.
- Breaking changes require a version increment and a migration note.
- **Provenance:** Constitution Art. VII § 7.5.

###### FR-53: Asset test requirements

Every Asset has tests covering input validation, transformation logic, output schema, edge cases,
and upstream integration.

**Consequences (testable):**
- An Asset without tests for each required dimension fails the gate.
- **Provenance:** Constitution Art. III § 3.3.

###### FR-54: Reference Domain implementation

The Workspace ships one Domain implemented end to end as the pattern others follow.

**Consequences (testable):**
- The reference Domain exercises all three Layers, publishes a contract, and passes every gate.
- Its structure is what the scaffolding templates (FR-37) generate.
- `[ASSUMPTION]` v1 delivers **the pattern plus one worked Domain** (`customer`); the remaining
  ten are adoption work. This changes effort by an order of magnitude — see OQ-2.

---

##### 5.8 Deployment, Environments, and Air-Gap

**Description.** Getting the platform to where it runs — including where the internet does not
reach. Realizes UJ-1 (edge case), UJ-4.

**Functional Requirements**

###### FR-55: Air-Gap Mode parity

Every capability available with public network access is available in Air-Gap Mode.

**Consequences (testable):**
- A parity test enumerates capabilities and asserts each works air-gapped.
- A capability that cannot work air-gapped is declared as such with its reason, not silently
  degraded.
- Validates SM-6.
- **Provenance:** Constitution Art. II § 2.2; the `enterprise-airgap` Dream's stated posture.

###### FR-56: Declarative, environment-promoted deployment

Deployment state is declared in version control and reconciled to the runtime, with promotion
between Stages governed by that Stage's policy.

**Consequences (testable):**
- Deploying is a change to declared state, not an imperative action.
- Stages with a manual-approval policy cannot auto-promote.
- Configuration differences between Stages are expressed as overlays over a shared base.
- **Provenance:** Constitution Art. X § 10.4–10.5.

###### FR-57: Secrets are never committed and are validated at startup

Secrets are supplied at runtime, absent from version control, and their presence is checked at
process start.

**Consequences (testable):**
- A secret-shaped string committed to the repository fails an automated check.
- A service missing a required secret fails fast with a diagnostic naming it, rather than at
  first use.
- **Provenance:** Constitution Art. VI § 6.5, Art. XII § 12.1.

###### FR-58: Data Classification is enforced, not merely documented

A Stage's Data Classification constrains what data may be present and what controls apply.

**Consequences (testable):**
- A Stage classified below `Restricted` cannot be configured against a datastore holding
  restricted data.
- Stages carrying restricted data have access logging enabled.
- `[ASSUMPTION]` v1 enforces classification at the **configuration boundary** (which datastore, which
  network) rather than performing data-content inspection. Content-level PII detection and masking
  is a candidate for v2 — see OQ-8.
- **Provenance:** Constitution Art. VI § 6.2, Art. XII § 12.6. `[NOTE FOR PM]` The Constitution
  asserts PII masking, retention, right-to-deletion and audit logging with **no mechanism
  specified anywhere**. This is the largest unbacked assertion in the intake set.

---

##### 5.9 Developer Experience Surface

**Description.** The commands and services a developer touches daily. The intake root proves the
shape at scale — roughly 200 tasks covering the full local lifecycle — and simultaneously shows
its risk: a surface that large is unlearnable without a stable public subset. Realizes UJ-1.

**Feature-specific NFRs**
- The task surface must be discoverable: every task carries a description, and tasks are grouped.
- The **public** task subset (the commands a developer is expected to know) is explicitly named
  and kept small; everything else is an implementation detail reachable but not advertised.

**Functional Requirements**

*This feature's requirements are satisfied by FR-18 (Quality Gate), FR-24 (local CI), FR-37
(scaffolding), and the local-lifecycle capability below.*

###### FR-59: One-command local stack lifecycle

A developer starts, stops, and inspects the full local service stack with single commands, and
each service individually.

**Consequences (testable):**
- Start, stop, status, and restart exist at both aggregate and per-service granularity.
- Status reports actual health, not merely process existence.
- The aggregate start brings up services in dependency order.
- **Provenance:** the intake root's local-dev lifecycle task family (brief addendum § C.2).

###### FR-60: Stable public task API

The Workspace names a small set of tasks as its public developer API and keeps it stable.

**Consequences (testable):**
- The public set is documented and enumerable.
- Removing or renaming a public task is a breaking change requiring a decision record.
- **Provenance/delta:** the intake root marks four tasks as the "Agent & Developer Public API"
  (`start`, `stop`, `status`, `verify`) out of ~200 — an excellent instinct, made a requirement.

---

#### 6. Cross-Cutting NFRs

- **NFR-1 — Reproducibility.** An Environment materialized from the Workspace Lock is identical
  across machines, platforms, and time, given the same lock. Verified by FR-11.
- **NFR-2 — Offline-first.** No capability may assume public network egress. Air-Gap Mode is the
  design default, not a mode. Verified by FR-55.
- **NFR-3 — Local/CI fidelity.** The Quality Gate is byte-identical locally and in CI. Verified
  by FR-18.
- **NFR-4 — Feedback latency.** Commit-time checks complete within a budget low enough that they
  are not routinely bypassed; the full gate completes within a budget low enough to run before
  every push. Verified by FR-23 and counter-measured by SM-C3. `[ASSUMPTION]` Both budgets must be
  set against a measured baseline rather than invented — see OQ-12. **Until OQ-12 resolves, this
  NFR has no numeric bound and cannot be tested.**
- **NFR-5 — Onboarding cost.** A new engineer reaches a working local stack using only written
  documentation, with no tribal knowledge. Verified by FR-13, FR-37, FR-59; measured by SM-1.
- **NFR-6 — Auditability.** Every gate decision, override, and exception is recorded with who,
  when, and why, and is enumerable after the fact. Verified by FR-8, FR-17, FR-27, FR-44, FR-45.
- **NFR-7 — Diagnosability.** Failures name the cause: the unmet requirement, the conflicting
  constraint, the violated clause. An opaque solver error is a defect. Verified by FR-1, FR-2,
  FR-19, FR-28, FR-46, FR-57.
- **NFR-8 — Platform coverage.** Every capability works on every declared platform, or declares
  its exception with a reason. Verified by FR-6, FR-11.
- **NFR-9 — Extensibility without forking.** A Domain adds Packages, Environments, and Data
  Products without modifying platform-owned files. Verified by FR-5, FR-27, FR-37; measured by
  SM-8.
- **NFR-10 — Supply-chain integrity.** Every dependency is hash-verified; every artifact carries
  SBOM and Provenance. Verified by FR-10, FR-39, FR-41, FR-42.

---

#### 7. Compliance and Regulatory

- **CR-1 — EU Cyber Resilience Act.** Unity must be *able* to discharge CRA obligations for
  adopters within scope: continuous awareness of actively-exploited vulnerabilities in the estate
  (FR-43), retained evidence (FR-44), component inventory (FR-39–FR-41), and lifecycle
  vulnerability handling (FR-47). Dates: in force 2024-12-10; **reporting obligations
  2026-09-11**; main obligations 2027-12-11.
  `[NOTE FOR PM]` The fetched Commission page does **not** explicitly state an SBOM requirement.
  The inference that CRA Annex I's component-documentation duty is satisfied by SBOM is
  **widely held but unverified here** — confirm the Annex I wording before citing CRA as the
  authority for FR-39 (OQ-3).
- **CR-2 — GDPR and data privacy.** The Constitution asserts GDPR compliance, retention policy,
  PII masking outside production, access audit logging, and right-to-deletion. FR-57 and FR-58
  address the configuration boundary; **content-level obligations have no specified mechanism**
  in the intake set and are scoped out of v1 (OQ-8).
- **CR-3 — Licence compliance.** FR-46.
- **CR-4 — Supply-chain provenance.** FR-42, targeting SLSA Build L1 mandatory / L2 goal (OQ-7).
- **CR-5 — Standards conformance.** SBOM output conforms to a pinned specification version
  (FR-39); the Exported Lock conforms to PEP 751 `lock-version` 1.0 (FR-12).

---

#### 8. Constraints and Guardrails

**Safety.** Automated remediation never merges without human review (FR-47). Automated
enforcement fails closed: an unevaluable gate is a failing gate, never a passing one.

**Privacy.** Restricted data never leaves a Stage classified for it (FR-58). Secrets never enter
version control, lockfiles, logs, or command lines (FR-15, FR-57).

**Cost.** Environment count is bounded by genuine dependency variation, not by Stage naming
(FR-9) — every distinct Environment is a solve, an install, and a cache entry, paid on every
machine and every CI run. Minimal Environments must be genuinely minimal (FR-3).

**Dependency policy.** All package installation goes through the workspace manager; direct
installer invocation is prohibited (Constitution Art. II § 2.1, § 2.3). Exceptions require a
recorded decision (FR-27).

**Language and runtime targets.** `[ASSUMPTION]` Primary Python targets are **3.13 and 3.14**;
3.12 is supported for legacy consumers only and is **security-phase** upstream (no further
binary releases); **3.15 first-releases 2026-10-01** and must be planned for inside this horizon.
This revises the Constitution's stated preference — see § 15 D7 and OQ-10.

**Platform matrix.** `[ASSUMPTION]` The matrix is at minimum `linux-64`, `osx-arm64`, `win-64`.
Whether `linux-aarch64` is in v1 is unresolved (OQ-14) — the two intake gists disagree with each
other, and the mandated deployment target is Kubernetes, where ARM nodes are mainstream.

---

#### 9. Integration and Dependencies

| Dependency | Nature | Risk |
|---|---|---|
| **Compliance gate capability** (`pyforge-warden`) | Consumed, not rebuilt. Supplies FR-43–FR-47 | Integration boundary undecided (OQ-4) |
| **Conda-native package supply** (`conda-forge-expert`, 769 feedstocks) | The channel Unity resolves against; the escalation path when a component is missing | Coverage of the full mandated stack is spot-checked only (OQ-15) |
| **Dependency intelligence** (`pyforge-atlas`) | Feeds currency, staleness, and alternative-suggestion signals | Optional for v1 |
| **Air-gap routing doctrine** (`enterprise-airgap`) | The mirror/credential model behind FR-14–FR-16 | Carries a known credential-injection defect that FR-16 must close |
| **Bootstrapper** (`pyforge-genesis`) | Would instantiate Unity instances | Unbuilt — a v2 dependency, not v1 |
| **Workspace manager** (pixi) | The substrate itself | Multi-package workspace support is **preview** (OQ-9b); version moves fast |
| **Standards-format export** (PEP 751) | FR-12 | Consumer-side reader support is **experimental** (§ 15 D2) |
| **Orchestrator** (Dagster) | The Asset execution engine | Constitution mandates it as sole platform |
| **Container platform** (OpenShift/Kubernetes + GitOps) | Deployment target | Current version/lifecycle unverified (OQ-17) |
| **Governance toolkit** (spec-kit) | The Constitution's format | Boundary with BMAD planning undecided (OQ-18) |

---

#### 10. Non-Goals (Explicit)

- **Unity is not an Internal Developer Portal.** No service catalog UI, no discovery portal.
  Unity emits catalog-consumable facts derived from its manifests; an adopter running Backstage
  integrates rather than migrates.
- **Unity is not a build-graph engine.** No attempt to compete with Pants, Bazel, or Nx on
  fine-grained caching, affected-target computation, or remote execution. Orthogonal, and
  unwinnable.
- **Unity does not maintain a second registry of truth.** The manifests are the source; anything
  else is derived.
- **Unity is not a product to be sold.** It is a platform an enterprise runs.
- **Unity does not replace the Domains' judgement about their own data models.** Global
  interoperability concerns are Platform Invariants; local modelling is a Domain Default (FR-26).
- **Unity does not target SLSA Build L3 in v1.**
- **Unity does not perform data-content inspection in v1** (classification is enforced at the
  configuration boundary — FR-58).
- **Unity is not a general-purpose polyglot monorepo.** Python-first by mandate.

---

#### 11. MVP Scope

##### 11.1 In Scope

- Workspace substrate with corrected pinning, Environment composition, and Package manifests
  (FR-1–FR-9).
- Resolved lock architecture with verified multi-platform coverage, standards export, offline
  bundle, and safe credential handling (FR-10–FR-17).
- Quality Gate with CI parity (FR-18–FR-25).
- Constitution classified into Platform Invariants and Domain Defaults, machine-checkable, with
  a governed amendment process (FR-26–FR-32).
- Innersource contribution model: Trusted Committer role, contribution path, scaffolding,
  measurement (FR-33–FR-38).
- Compliance chain: versioned SBOM with dependency graph, provenance, continuous
  exploitation-aware gating, schema-validated report, baselining, licence policy, opt-in
  remediation (FR-39–FR-47) — **by integration**.
- Data Product platform requirements plus **one** reference Domain end to end (FR-48–FR-54).
- Air-gap parity, declarative deployment, secret handling, configuration-boundary classification
  enforcement (FR-55–FR-58).
- Developer surface: local stack lifecycle and a stable public task API (FR-59–FR-60).

##### 11.2 Out of Scope for MVP

- **The remaining ten Domains.** `[ASSUMPTION]` v1 ships the pattern plus one worked Domain; the
  intake root marks all eleven as "scaffolding only" with one reference implementation
  (OQ-2). `[NOTE FOR PM]` This is the largest single sizing lever in the document.
- **Content-level PII detection, masking, and right-to-deletion** — asserted by the Constitution
  with no mechanism; deferred to v2 (OQ-8).
- **SLSA Build L3** — requires hardened builders.
- **Local Kubernetes development** — the required cluster tool is not available through the
  mandated channel, and the deployment target is not available on all platforms. Keep the intake
  root's documented stub and its reasoning.
- **Excluded services** (`airflow-server`, `sharepoint-mcp-server`) — carried as documented
  exclusions with reasons (FR-8).
- **Bootstrapping new Unity instances** — depends on `pyforge-genesis`, unbuilt.
- **A catalog/portal UI** — see § 10.
- **Remote build caching / distributed execution** — see § 10.

---

#### 12. Success Metrics

**Primary**

- **SM-1 — Time to productive.** Elapsed time from clone to a running local stack with a passing
  package test, by a new engineer using only written documentation. `[ASSUMPTION]` Target: under
  one hour, single-digit commands. Validates FR-1, FR-13, FR-59, NFR-5. Measured by timed
  onboarding of each new joiner.
- **SM-2 — Cross-team contribution rate.** Count of merged PRs authored by someone outside the
  owning team, per Package, per quarter — **trending up**. Validates FR-33–FR-38. *This is the
  innersource proof; if it stays near zero the platform has failed at its premise regardless of
  technical quality.*
- **SM-3 — Local/CI fidelity.** Rate of green-locally / red-in-CI outcomes — **trending to zero**.
  Validates FR-18, NFR-3.
- **SM-4 — Reproducibility coverage.** Percentage of declared platforms for which every
  Environment is verified materializable from the lock, online and offline. Target: 100%.
  Validates FR-11, FR-13, FR-55.
- **SM-5 — Compliance latency.** Elapsed time from vulnerability publication to a determination
  of whether the estate is affected. `[ASSUMPTION]` Target: minutes, automated. Validates FR-43,
  FR-44. *Directly serves the CRA reporting obligation.*

**Secondary**

- **SM-6 — Air-gap parity.** Percentage of enumerated capabilities verified working in Air-Gap
  Mode. Target: 100%, with any exception declared. Validates FR-55, NFR-2.
- **SM-7 — Mandate enforcement coverage.** Percentage of Mandates with an automated enforcing
  check. Validates FR-29. *Trending up; not expected to reach 100% — some Mandates are
  irreducibly human.*
- **SM-8 — Reuse depth.** Count of distinct Domains consuming each shared Package. Validates the
  premise that sharing is worth its cost.
- **SM-9 — Compliance baseline burn-down.** Size of the grandfathered finding baseline over time
  — **trending down**. Validates FR-45.

**Counter-metrics (do not optimize)**

- **SM-C1 — Internal fork/duplicate count.** Number of near-duplicate internal libraries.
  Counterbalances SM-2: contribution rate can be gamed by trivial PRs while people still fork
  rather than contribute. **If SM-2 rises and SM-C1 does not fall, SM-2 is not measuring what it
  claims to.**
- **SM-C2 — Environment count and aggregate installed size.** Counterbalances FR-9 and FR-3:
  the platform can always be made more capable by adding Environments and dependencies, and each
  is paid on every machine and every CI run.
- **SM-C3 — Quality Gate wall-clock time.** Counterbalances SM-3 and SM-7: fidelity and coverage
  both improve by adding checks, and a gate slow enough to be bypassed enforces nothing.
- **SM-C4 — Override count.** Counterbalances FR-26/FR-27: a governance split that produces
  hundreds of Domain Default overrides has classified the wrong things as defaults — but zero
  overrides means the split is theatre and Unity is centrally imposed after all. **Neither
  extreme is healthy.**

---

#### 13. Risk and Mitigations

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R-1 | **The lock mechanism is unproven.** The intake set's multi-platform guarantee rests on a non-existent flag and a misread of the format's scope | **High** | Resolve OQ-1 and OQ-16 before any other architecture work; FR-11 makes coverage a verified gate rather than an assumption |
| R-2 | **Two lockfiles, two solvers can silently disagree** — the seam where "reproducible" stops being true | **High** | FR-12's drift check; a single authoritative lock with the other derived |
| R-3 | **Mandated stack breadth.** Orchestrator + data-science toolbox + dbt + two web frameworks + CMS + ten infra services is a very large compatibility surface | **High** | FR-7's compatibility-detection Environment; FR-8's documented exclusions; scope discipline in § 11.2 |
| R-4 | **Experimental and preview dependencies in the critical path** — standards-format reader support is experimental; multi-package workspace support is preview | Medium | Pin versions; document a fallback for each; avoid preview features on the critical path where an alternative exists (OQ-9b) |
| R-5 | **Governance double-stack.** Two governance systems (spec-kit constitution, BMAD planning chain) are both live | Medium | Resolve OQ-18 explicitly rather than letting both drift |
| R-6 | **The social layer does not materialize.** Trusted Committers named but unresponsive; contribution path documented but unused | **High** | SM-2 with SM-C1 as counter-metric; FR-33's documented response-window expectation; escalation path in FR-34 |
| R-7 | **Constitution ossifies.** Already five months past its own review date | Medium | FR-30's overdue-review warning; FR-29's enforcement-coverage report as a forcing function |
| R-8 | **Stack currency drift resumes** — the intake set decayed in roughly six months | Medium | FR-17's recorded update policy; FR-7 running on schedule; treat currency as a gate axis |
| R-9 | **The platform is adopted technically and rejected socially** — teams use it because they must and route around it where they can | **High** | SM-2, SM-8, SM-C4; FR-26's Domain Defaults exist precisely so autonomy is real rather than rhetorical |
| R-10 | **Credential leakage.** A known unconditional-injection defect exists in inherited routing code | Medium | FR-15, FR-16, with tests asserting non-attachment |

---

#### 14. Constitution Provenance Map

Every Constitution mandate traced to the requirement that carries it, or to its disposition.
Source: `docs/intake/gists/spec-kit/constitution.md` v1.2.0 (ratified 2025-11-20).

##### 14.1 The Article II mandate table (rows sourced from several Articles)

| Mandate | Priority (as stated) | Carried by | Disposition |
|---|---|---|---|
| Local First — per-package environments, testing, docs | CRITICAL | FR-3, FR-5, FR-18, FR-59 | Adopted |
| Package Management — pixi, conda-forge, air-gap | CRITICAL | FR-1, FR-10, FR-14, § 8 | Adopted |
| Production — OpenShift + GitOps | CRITICAL | FR-56 | Adopted; version unverified (OQ-17) |
| MCP — agent message transport | CRITICAL | § 9 | Adopted. **Terminology corrected**: the Constitution expands MCP as "Multi-Agent Communication Protocol"; the correct expansion is **Model Context Protocol** |
| A2A — agent collaboration semantics | CRITICAL | § 9 | Adopted as an integration dependency; no v1 FR |
| REST — API architecture | CRITICAL | — | `[ASSUMPTION]` Applies to Packages Unity hosts, not to Unity's own surface. Not an FR |
| Environments — 12-stage SDLC | CRITICAL | FR-9, FR-58 | Adopted **as Stages**, modelled separately from Environments |
| Orchestration — Dagster ≥1.12.0, sole platform | HIGH | § 9, FR-48–FR-53 | Adopted; floor to be re-set (1.13.x current) |
| Data Mesh — DDD, three layers | HIGH | FR-48–FR-52 | Adopted |
| Data Science — Kedro, sole toolbox | HIGH | § 9 | Adopted as dependency; no v1 FR |
| Web Application — Django + React, preferred | HIGH | § 9 | Adopted as dependency; "preferred" ⇒ **Domain Default**, not Platform Invariant |
| RESTful API — FastAPI, preferred | MEDIUM | § 9 | Same |

##### 14.2 Articles I–XIV

| Article | Subject | Carried by |
|---|---|---|
| I | Identity, stack, repository structure | § 1, § 9, FR-1, FR-5 |
| II | Pixi-first package management | FR-1, FR-10, FR-14, FR-27, § 8 |
| III | Spec validation (tests) | FR-20, FR-21, FR-53; **amend** for FR-25 |
| IV | Agentic quality enforcement | FR-18, FR-19, FR-22, FR-23 |
| V | Specification standards | FR-31, FR-32, FR-51 |
| VI | 12-stage SDLC | FR-9, FR-57, FR-58 |
| VII | Data mesh | FR-48–FR-52 |
| VIII | Spec-driven collaboration | FR-33–FR-36 |
| IX | Dagster best practices | FR-50, FR-51, FR-53 |
| X | Continuous spec enforcement | FR-18, FR-24, FR-32, FR-56 |
| XI | Performance and scalability | **Not carried in v1** — no FR. `[NOTE FOR PM]` Article XI is entirely good-practice guidance with no platform mechanism. Candidate for demotion to a guide rather than a Mandate |
| XII | Security and compliance | FR-15, FR-16, FR-22, FR-39–FR-47, FR-57, FR-58 |
| XIII | Simplicity gate | FR-27, FR-31; § 8 |
| XIV | Python version support | § 8, § 15 D7 — **revised** |
| Governance | Authority, amendment, enforcement | FR-26, FR-28, FR-29, FR-30 |

##### 14.3 Amendments this PRD requires to the Constitution

1. **Art. II mandate table** — classify every row as Platform Invariant or Domain Default
   (FR-26). "Preferred" rows are Domain Defaults by their own wording; "sole" rows are Invariants.
2. **Art. III** — add the behavioural test tier that the working root already implements (FR-25).
3. **Art. XIV** — revise the support policy: 3.12 is security-phase upstream; 3.15 arrives
   2026-10-01; the stated 2-year rule, applied literally, already expires the declared baseline
   (§ 15 D7).
4. **Art. XI** — demote to guidance, or supply mechanisms and requirements.
5. **Art. XII § 12.6** — either supply mechanisms for PII masking / retention / right-to-deletion
   or scope them explicitly (OQ-8).
6. **Art. II MCP row** — correct the protocol expansion.
7. **Art. VIII § 8.3** — name whose approval (FR-33).
8. **Governance § Next Review** — overdue since 2026-02-20; re-ratify with this PRD's amendments.

---

#### 15. Research Deltas

Verified corrections to the intake artifacts. Full evidence and citations in the research
reports; graded **CONFIRMED** / **STALE** / **WRONG** / **NEW**.

| ID | Intake claim | Grade | Verified reality | Carried by |
|---|---|---|---|---|
| **D1** | "Universal Cryptographic Lockfile … tracks multi-platform targets" as a format guarantee | **WRONG (scope)** | PEP 751 is **Final** (2025-03-31) but explicitly does **not** provide universal multi-platform lockfiles automatically — it uses environment markers | FR-11 |
| **D2** | "pip v26.1+ (Deploy Engine)" reads `pylock.toml` | **STALE→NEW** | Correct — pip 25.1 added experimental `pip lock`; **26.1 added experimental `-r pylock.toml`**; latest 26.1.2 (2026-05-31). **Both experimental** | R-4; § 9 |
| **D3** | `pdm export --format pylock --override-platform=linux --override-platform=macos --override-platform=windows` | **WRONG** | **No `--override-platform` flag on `pdm export`**; platform targeting is on `pdm lock --platform`; format token is `pylock.toml`. Alternative: `uv export --format pylock.toml` | FR-12, OQ-16 |
| **D4** | `requires-pixi = "==0.59.0"` | **STALE** | Current is **0.73.0** (2026-07-15), 7 conda-forge subdirs. 0.73.0 adds `workspace = true` (removes the duplication smell), TOML 1.1, rich platforms (glibc/CUDA) | FR-2, FR-4 |
| **D5** | Workspace members as editable path installs | **NEW alternative** | Native multi-package workspaces now exist (`{ path = … }` + `{ workspace = true }`), **preview status** | OQ-9b, R-4 |
| **D6** | "dagster … doesn't support 3.14 yet" ⇒ `python <3.14` ceiling | **STALE** | dagster **1.13.15** declares `requires_python = "<3.15,>=3.10"` — 3.14 is supported. Ceiling's stated cause has expired | § 8, OQ-19 |
| **D7** | Python 3.14 preferred / 3.12 "legacy baseline" / 3.13 supported | **STALE** | **3.12 is security-phase** (no further binaries); 3.13 and 3.14 bugfix; **3.15 first-releases 2026-10-01**. The Constitution's own 2-year rule already expires 3.12 | § 8, § 14.3 |
| **D8** | Platform matrix (the two gists **disagree**: 4 platforms vs 3) | **STALE** | conda-forge ships the workspace manager for 7 subdirs incl. `linux-aarch64` and `win-arm64`; the mandated deployment target is Kubernetes, where ARM is mainstream | OQ-14 |
| **D9** | `pip-audit` + daily auto-patch as the security/compliance mechanism | **SUPERSEDED** | An existing capability is a strict superset: pixi-manifest coverage, **CISA-KEV** exploited-vulnerability gating, EPSS, licence and currency axes, schema-validated report, CI exit-code gate, opt-in fix-PR actuator | FR-43–FR-47, OQ-4 |
| **D10** | Unversioned CycloneDX output | **STALE** | CycloneDX **1.7** (2025-10-21) is **ECMA-424** (2025-12-10); adds formulation, declarations (compliance-as-code), citations; VEX/VDR and ML-BOM available | FR-39 |
| **D11** | SBOM from the lockfile is sufficient evidence | **GAP** | The generator's requirements mode carries a documented "no transitive components will be identified" caveat — risk is a **flat component list with no dependency graph** | FR-41, OQ-6 |
| **D12** | *(no provenance claim made)* | **GAP** | Provenance is entirely absent. SLSA **v1.2** current (v1.1 retired); L1 = provenance exists, L2 = signed provenance from a hosted build platform — **L2 is cheap on the CI already in use** | FR-42, OQ-7 |
| **D13** | Token Isolation Rule | **SELF-VIOLATED** | The spec's own manifest puts credentials in `extra-index-urls`; its CI interpolates them into `--index-url` on a command line | FR-15, FR-16 |
| **D14** | Constitution Art. VII implements Data Mesh | **CONFIRMED (2 of 4)** | Principles 1 (domain ownership) and 2 (data as a product) are faithfully implemented. Principle 3 (self-serve platform) is implicit — it is what Unity *is*. **Principle 4 (federated computational governance) is in tension**: the computational half is done well, the federated half is absent | FR-26, FR-27, OQ-5 |
| **D15** | Constitution is spec-kit format | **CONFIRMED + drift** | Format validated by adoption (**123.7k stars**, ~3.6× Backstage's 33.9k). But commands are now namespaced (`/speckit.constitution`), and upstream now ships **bundles** (role-based setups) that may subsume the toolchain spec's role matrix | OQ-18, OQ-20 |
| **D16** | Toolchain spec's 5-role agent matrix | **CONFIRMED + incomplete** | All five roles map onto the independently-evolved 8-station crew; two map excellently. The three unmapped stations are all **feedback-loop** roles (communication, diagnostics, memory) — the same under-specification of the human layer as the missing Trusted Committer | FR-33, § 9 |
| **D17** | Production container on `python:3.11-slim` | **CONTRADICTION** | The Constitution mandates Python 3.12–3.14; the spec's Dockerfile hardcodes 3.11 and `--python-version 311`, and switches away from conda for the production stage | § 8, OQ-1 |

**Confirmed and kept unchanged:** PEP 751 is Final; the feature/environment composition model;
the environment-variable mirror-override design; conda-native resolution as the differentiator;
the runtime/full SBOM split; the compatibility-detection environment; the documented
platform-conditional dependency knowledge; the `act`-based local CI mechanism; the four-task
public API instinct.

---

#### 16. Open Questions

Ordered by decision urgency. IDs are PRD-local; the research-report IDs they consolidate are
noted for traceability.

| # | Question | Blocks | Owner |
|---|---|---|---|
| **OQ-1** | **Is the Workspace Lock authoritative with the standards format derived, or the reverse, or split by tier?** The two intake gists answer differently and neither notices the conflict *(OQ-D8)* | **Everything.** Resolve first | Architecture |
| **OQ-2** | How many Domains are in v1 — the pattern plus one, or all eleven? *(OQ-D10)* | MVP sizing; **order-of-magnitude** | PRD sign-off |
| **OQ-3** | Exact CRA Annex I component-documentation wording — is SBOM required or inferred? *(OQ-D3)* | Whether CR-1 may cite CRA as FR-39's authority | Legal/compliance |
| **OQ-4** | Compliance-gate integration boundary — library, CLI, CI action, or tool-server? *(OQ-D4)* | FR-43–FR-47 | Architecture |
| **OQ-5** | Which Mandates are Platform Invariants and which are Domain Defaults? *(OQ-D7)* | FR-26, FR-27; the innersource-vs-imposed question | PRD sign-off |
| **OQ-6** | Does SBOM generation from the lock emit a dependency **graph** or a flat list? *(OQ-D5)* | FR-41. **Cheap empirical test — do early** | Architecture |
| **OQ-7** | Target SLSA level for v1? Recommendation: L1 mandatory, L2 goal *(OQ-D6)* | FR-42 | PRD sign-off |
| **OQ-8** | Does Data Classification require content-level enforcement (PII detection, masking, deletion), or is configuration-boundary enforcement sufficient for v1? *(OQ-D9)* | FR-58; CR-2; Constitution Art. XII § 12.6 | PRD sign-off |
| **OQ-9** | Should Stages be modelled as separate Environments at all, given five are byte-identical and three more are identical? *(OQ-M11)* | FR-9 | Architecture |
| **OQ-9b** | Adopt preview multi-package workspace support, or stay on editable path installs? *(OQ-M8)* | FR-5; R-4 | Architecture |
| **OQ-10** | Confirm the Python support policy revision (primary 3.13/3.14; 3.12 legacy-only; plan for 3.15) | § 8; Constitution Art. XIV amendment | PRD sign-off |
| **OQ-11** | Confirm the branching model — the Constitution mandates Gitflow with `develop` default | FR-35 | PRD sign-off |
| **OQ-12** | What are the actual latency budgets for commit-time checks and the full gate? | NFR-4; SM-C3 | Measure, then set |
| **OQ-13** | Is tests-before-implementation enforceable automatically, or review-only? | FR-21 | Architecture |
| **OQ-14** | Is `linux-aarch64` in v1's platform matrix? The gists disagree *(OQ-M10)* | § 8; FR-11 | PRD sign-off |
| **OQ-15** | Does **every** mandated component exist on the mandated channel, on every target platform? *(OQ-M2)* | R-3; FR-6 | Verify — bulk query |
| **OQ-16** | Which mechanism produces the verified multi-platform Exported Lock? *(OQ-M7)* | FR-11, FR-12 | Architecture |
| **OQ-17** | Current OpenShift version, Kubernetes baseline, EUS lifecycle? *(OQ-D1 — source returned 403)* | FR-56 | Verify before pinning |
| **OQ-18** | Where is the boundary between spec-kit governance and BMAD planning? Both are live *(OQ-M4)* | § 14; R-5 | PRD sign-off |
| **OQ-19** | Is the mandated orchestrator built for Python 3.14 on the mandated channel? *(OQ-M9)* | § 8's ceiling | Verify before pinning |
| **OQ-20** | Express the agent role matrix as an upstream governance-toolkit bundle? *(OQ-M3)* | § 9 | Architecture |
| **OQ-21** | Does the vulnerability scanner cover the Workspace Lock and the Exported Lock formats? *(OQ-D2)* | FR-43 | Verify at integration |
| **OQ-22** | Is the comparable set complete? Discovery search was unavailable during research *(OQ-M1)* | § 10's non-goals — every "Unity is not X" statement assumes X is correctly identified | Re-run when budget allows |
| **OQ-23** | Is there independent innersource adoption data to ground SM-2's target? *(OQ-M6)* | SM-2 | Research follow-up |

---

#### 17. Assumptions Index

Every `[ASSUMPTION]` in **this document**. **None is confirmed scope.**

`addendum.md` carries its own `[ASSUMPTION]` tags (in § A.3, § B.2, § C, § E, § F, § G) covering
mechanism preferences rather than scope. They are deliberately not indexed here — this index is
the complete list of *scope* assumptions; the addendum's are *implementation-option leanings* that
the architecture stage resolves.

| # | Section | Assumption | Resolve via |
|---|---|---|---|
| A-1 | § 0 | Produced headless with no user present; all inferences tagged | User review |
| A-2 | § 2 | CRA is a forcing-function and a capability to be able to discharge — not a claim that every deployment is regulated | OQ-3, OQ-16 |
| A-3 | § 5.2 / FR-12 | The Workspace Lock is authoritative; the standards-format lock is derived (pixi-primary) | **OQ-1** |
| A-4 | § 5.6 / FR-42 | SLSA L1 mandatory, L2 goal, L3 out of scope for v1 | OQ-7 |
| A-5 | § 5.7 / FR-54, § 11.2 | v1 delivers the Domain pattern plus one worked Domain, not all eleven | **OQ-2** |
| A-6 | § 5.8 / FR-58 | Data Classification is enforced at the configuration boundary; content inspection is v2 | OQ-8 |
| A-7 | § 5.3 / FR-21 | Tests-before-implementation is review-enforced, not automated | OQ-13 |
| A-8 | § 6 / NFR-4 | Latency budgets exist but specific numbers must be set against a measured baseline | OQ-12 |
| A-9 | § 8 | Primary Python targets are 3.13 and 3.14; 3.12 legacy-only; plan for 3.15 | OQ-10 |
| A-10 | § 8 | Platform matrix is at minimum linux-64, osx-arm64, win-64; ARM64 Linux unresolved | OQ-14 |
| A-11 | § 12 / SM-1 | Target: under one hour, single-digit commands | User review |
| A-12 | § 12 / SM-5 | Target: minutes, automated | User review |
| A-13 | § 14.1 | The REST mandate applies to Packages Unity hosts, not to Unity's own surface | User review |
| A-14 | § 3.2 | The listed non-user groups are correct audience boundaries | User review |

---

**Companion artifacts (satellite):** `addendum.md` (mechanism, options-considered, deferred
depth) and the standalone `brief.md`/`addendum.md` now live at
`archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-unity-data-stack-2026-07-25/addendum.md`
and
`archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/briefs/brief-unity-data-stack-2026-07-25/{brief.md,addendum.md}`
respectively (moved there intact 2026-08-02, not deleted) ·
`research/{market,domain}-…-2026-07-25.md` (still at its original, unmoved path)

## Satellite: Wasm Analytics Stack

> **Folded in verbatim 2026-08-02** from
> `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-wasm-analytics-stack-2026-07-25/prd.md`
> (status at fold-in: `final`; frontmatter also carried its own
> `currency_review` note dated 2026-08-04). Content below is unmodified from
> the standalone document. Its FR-1..FR-17 / SM-1..SM-4 numbering is local
> to this satellite section and is independent of the primary PRD's
> FR-1..FR-22 above.

### PRD: Wasm Analytics Stack
*Working title — confirm.*

#### 0. Document Purpose

This PRD is written for the Architecture stage that follows it directly (this
chain runs PRD → Architecture only; no epics/stories decomposition yet — this is
a far-horizon project whose stories will be decomposed fresh when scheduled), and
for any human reviewer deciding whether to schedule the build. It is structured
around a single, concrete seed use case (defined in `## 2 Target User` and
realized end-to-end in `## 4 Features`), not a general-purpose platform vision —
the brief this PRD builds on (`../../briefs/brief-wasm-analytics-stack-2026-07-25/brief.md`)
already made that scoping call explicit, and this PRD does not re-litigate it.
This PRD also builds directly on two research reports produced alongside the
brief — `../../research/technical-python-in-wasm-analytics-research-2026-07-25.md`
(the Python-in-WASM maturity verdict) and
`../../research/domain-sandboxed-analytics-deployments-research-2026-07-25.md`
(comparable production Wasm-sandboxing deployments) — both of which this PRD
treats as load-bearing, not background reading: several FRs below are scoped the
way they are *because* the research shows the alternative is not currently
buildable.

#### 1. Vision

Wasm Analytics Stack lets a regulated or hardened enterprise accept
user-uploaded data into an analytical pipeline without widening the trust
boundary of the pipeline's own code. A user uploads an Excel file; before that
file's contents touch anything else, a purpose-built validation step — compiled
to a genuine WASI Preview 2 component and run under Wasmtime, not just another
function in the same trusted process — checks it. Only validated rows ever reach
`dlt` ingestion, DuckDB Bronze, and the `dbt-duckdb` Silver/Gold transforms. Every
stage of that journey, from the browser to the Gold table, carries a live OTel
trace and an OpenLineage provenance record, natively, not bolted on after the
fact. And the whole thing — API, WASI component, ingestion, transformation — runs
through exactly one toolchain (Pixi) and is provably identical whether it's
running on a laptop, inside a `podman --read-only --user 1001` digital twin, or
inside a real OpenShift cluster under Restricted SCC.

What makes this worth building now, rather than as a plain OCP-hardened pipeline
with no Wasm layer at all: the sandboxing claim is mechanically verifiable, not
aspirational. The project's own research (§ Risk and Mitigations) is explicit that
most of the WASI-component ecosystem is not yet ready for C-extension-heavy data
libraries — so this PRD does not claim a fully Wasm-sandboxed DuckDB pipeline.
It claims a narrower, provably-true thing: the one place untrusted input first
touches the system is sandboxed at the code level, verified by an automated gate,
and everything downstream of that point runs on an already-hardened, already
well-understood OCP process boundary. That is a smaller claim than the April 2026
architecture gist this project descends from made — and, per the research, the
larger claim is not buildable with today's ecosystem.

#### 2. Target User

##### 2.1 Jobs To Be Done

- **As a platform/data engineer at a regulated enterprise**, I need to let
  business users upload data into an analytical pipeline without giving
  uploaded-file-derived logic the same trust level as the pipeline's own code.
- **As the same engineer**, I need one command sequence that behaves identically
  whether I run it on my laptop, in a Podman digital twin, or in the real OCP
  cluster — so "works in dev" and "works in prod" are the same claim, verified
  the same way.
- **As a security/compliance reviewer**, I need the pipeline's sandboxing claim
  to be something I can point an automated gate at, not something I have to take
  on the architecture document's word.
- **As a data consumer** (an analyst querying Gold tables, out of this PRD's V1
  scope but a stated future user), I need to trust that what reached Gold passed
  through a validated, traceable, lineage-recorded path.

##### 2.2 Non-Users (v1)

- End users who need a query/dashboard interface onto Gold tables — V1 ships no
  read surface at all (see § 6.2 Out of Scope); this is an ingestion+transform
  pipeline, not yet an analytics product a business user opens directly.
- Teams whose source data is not file-upload-shaped (streaming sources, API
  pulls, database CDC) — V1's WASI validation boundary is scoped to the
  file-upload trust-boundary problem specifically.
- Teams on Kubernetes distributions other than OpenShift, or without a
  Restricted-SCC-equivalent hardening requirement — the value proposition is
  specific to that posture; a generic K8s deployment would carry the WASI
  sandboxing cost without the OCP-hardening context that motivates it.

##### 2.3 Key User Journeys

- **UJ-1. Marcus uploads a weekly Excel report and finds out, in seconds, that
  three rows are malformed — before anything downstream ever sees them.**
  - **Persona + context:** Marcus, a business analyst at a regulated
    financial-services company, produces a weekly headcount-and-cost Excel
    report by hand and needs it in the shared analytical warehouse without
    filing a ticket with the platform team.
  - **Entry state:** authenticated via the enterprise OIDC provider (OpenShift
    identity), browser session, no prior interaction with this pipeline today.
  - **Path:** Marcus opens the upload page, selects `headcount-2026-w30.xlsx`,
    and submits. The FastAPI endpoint accepts the file and hands it to the
    WASI-sandboxed validation component. The component checks structure
    (expected columns present, types coherent) and data quality (no
    negative headcounts, no duplicate department keys) — entirely inside its
    own sandboxed boundary, with no filesystem or network access beyond what
    its WIT interface explicitly grants.
  - **Climax:** three rows fail validation (a department key typo, a negative
    cost value). Marcus sees a precise, row-level error message within seconds —
    the file was never partially ingested, and the 47 valid rows are queued
    separately from the 3 rejected ones pending his fix.
  - **Resolution:** Marcus corrects the three rows in Excel and re-uploads; this
    time all 50 rows pass, and `dlt` ingests them into DuckDB Bronze. Marcus
    never sees or cares that any of this happened inside a Wasm sandbox — from
    his side it's just "the upload told me exactly what was wrong."
  - **Edge case:** if the uploaded file isn't valid `.xlsx` at all (corrupted,
    wrong format), the WASI component rejects it before `dlt` or DuckDB are ever
    invoked — the failure is contained at the validation boundary, not
    discovered three stages downstream.

- **UJ-2. Elena verifies a new build behaves identically in her laptop's digital
  twin and in the OCP cluster, then traces one Bronze row all the way to Gold.**
  - **Persona + context:** Elena, a platform engineer, is validating a pipeline
    change before it ships to the regulated-enterprise OCP cluster she's
    responsible for.
  - **Entry state:** local checkout, Pixi installed, no cluster access needed
    for the first half of this journey.
  - **Path:** Elena runs `pixi run build` (compiles the WASI validation
    component alongside the rest of the stack), then `podman-compose up` to
    bring up the digital twin under `--read-only --user 1001` — the same
    security context Restricted SCC enforces in OCP. She re-runs UJ-1's upload
    scenario against the digital twin and confirms identical behavior. Satisfied,
    she deploys the same artifact to the OCP cluster via the GitOps pipeline.
  - **Climax:** in the OCP cluster, she pulls up Marquez and searches for
    Marcus's `headcount-2026-w30.xlsx` upload by trace ID (captured from the
    original OTel span at the FastAPI boundary). She sees the full lineage:
    upload → validation (pass) → Bronze row → Silver transform → Gold table,
    each hop timestamped and column-level-attributed.
  - **Resolution:** Elena has verified, without guessing, that dev/twin/prod
    parity holds and that the lineage claim is real, not documented-but-untested.
  - **Edge case:** if the digital twin and the OCP cluster ever disagree (e.g. a
    dependency resolves differently), that disagreement is itself the signal
    the one-toolchain claim exists to prevent — Elena's workflow should make
    such drift visible immediately, not silently.

#### 3. Glossary

- **WASI Preview 2 component** — a WebAssembly module compiled against the WASI
  0.2/0.3 component-model spec, with an explicit WIT-defined interface
  (capabilities) rather than ambient system access. This project's validation
  logic is one.
- **Wasmtime** — the Bytecode Alliance's WASI-component host runtime; hosts the
  validation component both in the digital twin and in OCP.
- **componentize-py** — the Bytecode Alliance tool that compiles a Python
  application into a WASI Preview 2 component. Per the technical research, its
  Python surface is restricted: no dynamic runtime imports, and C-extension
  support is real but shallow (works for SQLite3, `.abi3.so`-recognized native
  extensions in some cases; does not work for numpy/pandas/pyarrow without an
  unmaintained community wheel-build project this PRD does not depend on).
- **Isolation-Verification Gate** — this project's mechanical proof (an
  automated Wasmtime-host smoke test) that the validation component's sandbox
  boundary holds — the pattern is adapted from `pyforge-atlas` story G1's
  `wasm-smoke` gate, which proved a browser-hosted Wasm artifact made zero
  non-loopback network requests.
- **Digital twin** — the local/CI verification environment: the same container
  images and security context (`podman --read-only --user 1001`) as the OCP
  deployment, run outside a real cluster.
- **Restricted SCC** — OpenShift's Restricted Security Context Constraint:
  non-root UID 1001, read-only root filesystem, no privilege escalation. The
  hard deployment constraint for every container in this project, WASI-sandboxed
  or not.
- **Bronze / Silver / Gold** — the medallion data-layering convention: Bronze is
  raw-but-validated ingested data (DuckDB table, written by `dlt`), Silver is
  cleaned/conformed, Gold is business-ready/aggregated (both written by
  `dbt-duckdb`).
- **`dlt` (data load tool)** — the Python ingestion library moving validated rows
  from the FastAPI upload path into DuckDB Bronze. Runs as a conventional,
  Restricted-SCC-hardened process — not a WASI component (§ Risk and
  Mitigations explains why).
- **`dbt-duckdb`** — the `dbt` adapter targeting DuckDB, running the
  Bronze→Silver→Gold SQL transformations. Also a conventional process, not a
  WASI component, for the same DuckDB-dependency reason as `dlt`.
- **OTel span** — a single traced operation (an OpenTelemetry unit of work),
  emitted at each pipeline stage and correlated by a shared trace ID originating
  at the browser (W3C Trace Context).
- **OpenLineage facet** — a structured provenance record (who/what/when
  transformed which columns) emitted by `dlt` and `dbt` to Marquez.
- **Marquez** — the OpenLineage-compatible metadata/lineage service this project
  emits facets to and queries lineage from (UJ-2).
- **Vector sidecar** — the per-pod telemetry-forwarding sidecar aggregating OTel
  spans before they leave the pod.
- **WIT interface** — the WebAssembly Interface Type definition declaring
  exactly what a WASI component may import/export; the validation component's
  entire capability surface is enumerated here, nothing implicit.

#### 4. Features

##### 4.1 Authenticated Upload & WASI-Sandboxed Validation

**Description:** The system's entire trust-boundary-crossing surface for V1.
A business user (Marcus, UJ-1) authenticates via the enterprise OIDC provider,
uploads an Excel file to a FastAPI endpoint, and the file's bytes are handed to
a `componentize-py`-compiled WASI Preview 2 component running under Wasmtime —
not to any code sharing a trust boundary with the rest of the pipeline. The
component's WIT interface grants it exactly the capability to receive bytes and
return a structured validation result; nothing else. `[ASSUMPTION]` The
component receives a pre-parsed, plain-Python-object representation of the
spreadsheet (rows as dicts/lists of scalars) rather than raw Excel bytes or an
Arrow buffer — per the technical research, there is no confirmed
`pyarrow`-in-WASI path and no Arrow-maintained WASM/WASI interchange primitive,
so the parsing step (turning `.xlsx` bytes into rows) happens in conventional,
non-sandboxed code immediately before the WASI boundary, and only the
structural/data-quality *checks themselves* run inside the sandbox.

**Functional Requirements:**

###### FR-1: Authenticated Excel Upload

A business user can upload an `.xlsx` file via `POST /upload/excel` after
authenticating through the enterprise OIDC/OAuth2 provider. Realizes UJ-1.

**Consequences (testable):**
- Unauthenticated requests receive HTTP 401 before the upload body is read.
- A successfully authenticated upload returns a tracking/trace ID the client can
  use to poll validation status.
- The endpoint enforces a maximum file size (`[ASSUMPTION]` exact limit is an
  open question — see § 8).

###### FR-2: WASI-Sandboxed Structural & Data-Quality Validation

The system validates every uploaded file's structure (expected columns present,
types coherent) and data quality (domain-specific rules, e.g. no negative
values in numeric fields expected to be non-negative) inside a WASI Preview 2
component, before any row reaches `dlt` or DuckDB. Realizes UJ-1.

**Consequences (testable):**
- The validation component's WIT interface declares no filesystem or network
  import beyond what's explicitly required for the check itself (ideally none).
- A file that fails structural validation (wrong columns, unreadable as tabular
  data) is rejected in full — zero rows reach Bronze.
- A file that passes structural validation but fails row-level data-quality
  checks reports failures per-row, without blocking the rows that did pass
  (partial acceptance, per UJ-1's resolution beat).
- The validation component's Python dependency surface contains no
  `numpy`/`pandas`/`pyarrow`/`pydantic` import — enforced at build time (FR-13).

**Out of Scope:**
- Semantic/business-rule validation beyond structural + declared data-quality
  rules (e.g. cross-referencing an uploaded headcount against an external HR
  system) — V1's validation is self-contained to the file's own contents.

###### FR-3: Validation Failure Handling & Surfacing

A user whose upload contains invalid rows receives a precise, row-level error
report and can resubmit corrected data without re-uploading valid rows twice.
Realizes UJ-1.

**Consequences (testable):**
- Each rejected row's error message names the specific column/rule that failed.
- Valid rows from a partially-failing upload are queued for ingestion (FR-4)
  independently of the rejected rows' resolution.

###### FR-4: Validated-Row Ingestion to DuckDB Bronze

Rows that pass validation are ingested into a DuckDB Bronze table via `dlt`,
running as a conventional Restricted-SCC-hardened process (not a WASI
component — see § Risk and Mitigations for why). Realizes UJ-1.

**Consequences (testable):**
- No row reaches Bronze without having passed FR-2's validation.
- `dlt`'s schema inference records the Bronze table schema derived from the
  validated rows, available for the transformation stage (FR-5).

**Feature-specific NFRs:**
- Validation latency: the WASI component's check must complete within a bound
  tight enough that UJ-1's "within seconds" claim holds for a
  realistically-sized weekly report (`[ASSUMPTION]` exact row-count/latency
  target is an open question — see § 8).

##### 4.2 Bronze → Silver → Gold Transformation

**Description:** Once validated data lands in Bronze, `dbt-duckdb` transforms it
through Silver (cleaned/conformed) to Gold (business-ready), with every
transformation's column-level lineage captured, not just the transformation's
success/failure. This feature is entirely conventional-process-hosted (not
Wasm-sandboxed) per the technical research's finding that DuckDB has no WASI
build.

**Functional Requirements:**

###### FR-5: `dbt-duckdb` Transformation Pipeline

The system runs a `dbt-duckdb` project transforming Bronze tables into Silver
and Gold layers on a defined schedule/trigger. Realizes UJ-2.

**Consequences (testable):**
- Every `dbt run` invocation is traceable to the Bronze table state (and,
  transitively, the upload event) it consumed.
- Silver/Gold table schemas are declared in the `dbt` project, not inferred
  ad hoc.

###### FR-6: Column-Level Lineage Emission

Every `dbt` model emits column-level lineage (which Silver/Gold columns derive
from which Bronze columns, through which transformation) as an OpenLineage
facet. Realizes UJ-2.

**Consequences (testable):**
- A lineage query for any Gold column returns its full upstream column chain
  back to the originating Bronze column.

###### FR-7: `dbt test` Quality Gate

Every transformation run is gated by `dbt test` — schema and data-quality tests
declared per model — and a failing test blocks promotion of that model's output
to the next layer.

**Consequences (testable):**
- A `dbt run` with a failing test does not update the corresponding Silver/Gold
  table; the prior good state remains queryable.

##### 4.3 End-to-End Observability & Provenance

**Description:** OTel tracing and OpenLineage provenance are native to every
stage, correlated by one trace ID originating at the browser, so a single
lookup (UJ-2) reconstructs the full journey of any row from upload to Gold.

**Functional Requirements:**

###### FR-8: W3C Trace Context Propagation

A W3C Trace Context originating in the browser upload request is propagated
through the FastAPI endpoint, the WASI validation component invocation, `dlt`
ingestion, and every `dbt` model run touching that data. Realizes UJ-2.

**Consequences (testable):**
- The trace ID returned to the client at upload time (FR-1) is the same trace
  ID attached to that upload's eventual Gold-table lineage record.

###### FR-9: OTel Span Emission at Every Stage

Each pipeline stage (API request, validation, ingestion, each `dbt` model run)
emits its own OTel span, tagged with the shared trace ID, to a per-pod Vector
sidecar.

**Consequences (testable):**
- A trace query for any upload's trace ID returns spans for every stage the
  upload passed through, with no gap in the chain.

###### FR-10: OpenLineage Facet Emission to Marquez

`dlt` and `dbt` emit OpenLineage facets (dataset-level and column-level) to
Marquez on every run. Realizes UJ-2.

**Consequences (testable):**
- Marquez's UI/API returns the full Bronze→Silver→Gold lineage graph for any
  ingested dataset.

###### FR-11: Vector Sidecar Telemetry Aggregation

A Vector sidecar aggregates OTel spans within each pod before forwarding
externally, so no pipeline component needs its own direct external telemetry
egress.

**Consequences (testable):**
- No pipeline container process other than the Vector sidecar holds an
  external network egress path for telemetry.

##### 4.4 Mechanically-Verified WASI Sandbox Isolation

**Description:** The project's core differentiating claim — that the validation
component is genuinely sandboxed — is proven by an automated gate, not asserted
by a design document. This directly answers the domain research's finding that
comparable production Wasm-sandboxing deployments treat this as a first-class
concern, and mirrors the `pyforge-atlas` G1 precedent of a mechanical,
gate-enforced isolation proof.

**Functional Requirements:**

###### FR-12: Isolation-Verification Gate

An automated gate runs the compiled validation component under a Wasmtime host
configured with only the WIT-declared capabilities and asserts no capability
beyond that declared set is reachable (e.g. no filesystem write, no network
egress, if none are declared). Realizes UJ-2 (the compliance-reviewer JTBD in
§ 2.1).

**Consequences (testable):**
- The gate fails if the component attempts any host interaction beyond its
  declared WIT imports.
- The gate is non-hollow: deliberately widening the component's declared
  capabilities without a corresponding WIT change causes the gate to fail (the
  gate must prove it's checking something, not always passing).

###### FR-13: WASI Component Dependency Audit

A build-time check enforces that the validation component's Python source
imports nothing from a denylist (`numpy`, `pandas`, `pyarrow`, `pydantic`, any
other C-extension-backed or `componentize-py`-unproven package), failing the
build if violated.

**Consequences (testable):**
- Adding a denylisted import to the validation component's source fails
  `pixi run build`, not just a later runtime error.

##### 4.5 One Toolchain: Local Dev, Digital Twin, Production OCP

**Description:** Pixi orchestrates every build/verify/deploy step; the same
commands run identically on a laptop, in the Podman digital twin, and (via
GitOps) in the OpenShift cluster — the parity UJ-2 exercises directly.

**Functional Requirements:**

###### FR-14: Pixi-Orchestrated Build

`pixi install` and `pixi run build` produce every artifact the pipeline needs,
including the compiled WASI validation component, from a single toolchain
definition. Realizes UJ-2.

**Consequences (testable):**
- A clean checkout, `pixi install && pixi run build`, produces a runnable
  digital twin with no manual steps outside Pixi.

###### FR-15: Podman Digital-Twin Parity

`podman-compose up` brings up the full pipeline locally under
`--read-only --user 1001` — the same security context OCP Restricted SCC
enforces — so a failure under Restricted SCC is caught before deployment, not
after. Realizes UJ-2.

**Consequences (testable):**
- Every container in the digital twin starts successfully as non-root UID 1001
  with a read-only root filesystem; any component that requires writable
  storage does so only via an explicitly mounted volume, never the rootfs.

###### FR-16: OpenShift Restricted SCC Compliant Deployment

The production deployment (via GitOps/Helm) runs under OpenShift's Restricted
SCC with no exceptions requested.

**Consequences (testable):**
- The Helm chart's pod security context matches Restricted SCC's requirements
  exactly (non-root UID 1001, `readOnlyRootFilesystem: true`, no privilege
  escalation) — no `anyuid` or other elevated SCC binding required.

###### FR-17: Persistent Storage via ReadWriteOnce PVC

DuckDB's on-disk state (Bronze/Silver/Gold) is backed by a `ReadWriteOnce` PVC
mounted at a defined path, consistent between the digital twin and OCP.

**Consequences (testable):**
- Pipeline restarts do not lose previously-ingested Bronze/Silver/Gold data;
  state survives pod recreation as long as the PVC persists.

#### 5. Non-Goals (Explicit)

- This project does not build a general-purpose Wasm-sandboxing framework for
  arbitrary third-party logic — the WASI component boundary in V1 is scoped
  exclusively to the Excel-upload validation step.
- This project does not attempt to run `dlt`, `dbt`, or DuckDB itself inside a
  WASI Preview 2 sandbox — the technical research found this blocked at the
  DuckDB-dependency level, not a scoping choice to revisit without new upstream
  evidence.
- This project does not ship a browser-side query/dashboard surface in V1 (that
  would reuse the `pyforge-atlas` G1 DuckDB-WASM/Pyodide pattern directly rather
  than reinvent it, per the brief's Vision section, but is explicitly out of
  this PRD).
- This project does not become a general ingestion platform supporting arbitrary
  source types in V1 — Excel upload is the only ingestion path.

#### 6. MVP Scope

##### 6.1 In Scope

- FastAPI upload endpoint with OIDC authentication (FR-1).
- `componentize-py`-compiled WASI Preview 2 validation component with a
  mechanically-verified isolation gate (FR-2, FR-3, FR-12, FR-13).
- `dlt` ingestion to DuckDB Bronze (FR-4).
- `dbt-duckdb` Bronze→Silver→Gold with column-level lineage and `dbt test`
  gating (FR-5, FR-6, FR-7).
- End-to-end OTel tracing + OpenLineage provenance to Marquez via a Vector
  sidecar (FR-8 through FR-11).
- One Pixi toolchain spanning local dev, Podman digital twin, and OCP
  deployment, with Restricted SCC compliance in both the digital twin and
  production (FR-14 through FR-17).

##### 6.2 Out of Scope for MVP

- Any WASI-sandboxed execution of `dlt`, `dbt`, or DuckDB — deferred
  indefinitely pending upstream WASI support for DuckDB's native engine (not a
  near-term v2 item; see § Risk and Mitigations).
- Apache Arrow buffers as the host↔WASI-component interchange format —
  deferred pending a confirmed `pyarrow`-in-WASI path or an Arrow-maintained
  WASM/WASI interchange primitive.
- A browser-side dashboard/read surface onto Gold tables — v2, would follow the
  `pyforge-atlas` G1 DuckDB-WASM/Pyodide pattern. `[NOTE FOR PM]` this is the
  most natural v2 candidate and should be revisited once V1's ingestion path is
  stable, since G1 already de-risked most of the technical approach.
- Multi-source ingestion beyond Excel (streaming, API pull, CDC) — v2+.
- Multi-tenant Unity Data Stack platform integration — v2+, tracked as a
  kinship, not a commitment.
- Migration to `dbt Fusion` (the Rust engine) — blocked until it gains a DuckDB
  adapter; tracked as a watch item, not scheduled.

#### 7. Success Metrics

**Primary**
- **SM-1**: The seed use case (Excel upload → WASI-validated → DuckDB Bronze →
  Silver/Gold via `dbt`) completes successfully, with identical behavior, in
  all three environments (laptop, Podman digital twin, OCP cluster). Validates
  FR-1 through FR-17.
- **SM-2**: The Isolation-Verification Gate (FR-12) passes on every build and
  demonstrably fails when the validation component's declared capability
  surface is deliberately widened without a corresponding WIT change (the
  non-hollow-gate test). Validates FR-12, FR-13.

**Secondary**
- **SM-3**: 100% of pipeline stages (API, validation, ingestion, each `dbt`
  model run) emit a correlated OTel span and, where applicable, an OpenLineage
  facet — verified by a single trace-ID lookup returning the full chain with no
  gaps. Validates FR-8 through FR-11.
- **SM-4**: Zero Restricted SCC exceptions requested in the production Helm
  deployment. Validates FR-16.

**Counter-metrics (do not optimize)**
- **SM-C1**: Validation-component build complexity (lines of workaround code
  needed to satisfy `componentize-py`'s import/dependency constraints) should
  not be optimized away by simply widening the denylist (FR-13) to let more
  through — a growing denylist-workaround footprint is a signal to reconsider
  the WASI-sandboxing bet (§ Kill Criteria in the brief), not a target to
  minimize by weakening the boundary. Counterbalances SM-1/SM-2.
- **SM-C2**: Upload-validation latency should not be optimized by moving checks
  out of the WASI sandbox back into the trusted process — that would satisfy a
  speed metric while quietly defeating FR-2's entire purpose. Counterbalances
  SM-1.

#### 8. Open Questions

1. Exact maximum upload file size and expected weekly row-count/latency budget
   for FR-1/FR-2's "within seconds" claim (UJ-1) — needed before Architecture can
   size the validation component's performance budget.
2. Which specific regulatory framework(s), if any, this deployment must satisfy
   beyond "Restricted SCC + OIDC" (HIPAA, PCI-DSS, SOX, none) — the Dream and
   gist name the posture generically ("regulated enterprise") without a named
   framework; § Compliance and Regulatory below is written generically pending
   this answer.
3. Whether `componentize-py`'s runtime-import restriction (all imports must
   resolve at build time — technical research § 2) forces any redesign of the
   validation component's rule-configuration mechanism (e.g. if validation
   rules were meant to be dynamically loaded per file-type, that pattern may
   not work as-is).
4. Operational ownership: who is on-call for this pipeline in production, and
   what SLA (if any) applies to validation/ingestion latency — not addressed in
   the Dream or brief; needed before Architecture commits to a specific
   deployment topology (§ Operational Requirements is intentionally thin
   pending this).
5. Whether the WASI Isolation-Verification Gate (FR-12) needs to run on every
   CI build or only on validation-component-touching changes — an
   Architecture/CI-design question, not a product one, but affects the build
   pipeline's shape.

#### 9. Assumptions Index

- § 4.1 — the validation component receives pre-parsed plain-Python data
  (rows as dicts/scalars), not raw Excel bytes or an Arrow buffer, because no
  confirmed `pyarrow`-in-WASI or Arrow-WASM-interchange path exists.
- § 4.1 FR-1 — exact max upload file size is unset pending § 8 Q1.
- § 4.1 FR-2 (feature-specific NFR) — exact validation-latency target is unset
  pending § 8 Q1.

---

##### Cross-Cutting NFRs

- **Security.** Every container non-root UID 1001, read-only rootfs (Restricted
  SCC, FR-16). The WASI validation component's capability surface is
  WIT-declared and mechanically checked (FR-12) — no ambient filesystem/network
  access. OIDC authentication gates the only external-input entry point
  (FR-1). No pipeline component other than the Vector sidecar holds external
  telemetry egress (FR-11).
- **Portability / Air-gap compatibility.** `[ASSUMPTION]` Per this repo's
  established `enterprise-airgap` posture (kinship named in the Dream), the
  stack's dependencies (Pixi packages, the DuckDB Parquet-extension-style
  vendoring pattern `pyforge-atlas` G1 already established) should be
  air-gap-routable through an internal mirror/Artifactory, not hardcoded to
  reach the public internet at build or run time. Architecture should treat
  this as a hard constraint on dependency-fetch design, not an afterthought.
- **Reliability.** Digital-twin/production parity (FR-15) exists specifically
  so that a Restricted-SCC-incompatible change is caught locally, not in
  production.
- **Observability.** 100% span/facet coverage is itself an NFR restated as
  SM-3 — not aspirational, gate-checked.

##### Constraints and Guardrails

- **Safety (sandbox boundary).** The WASI component's WIT interface is the
  single source of truth for what the validation logic can touch — any
  capability not explicitly declared there must not be reachable, enforced by
  FR-12's gate.
- **Dependency guardrail.** FR-13's denylist (no `numpy`/`pandas`/`pyarrow`/
  `pydantic` inside the WASI component) is a hard guardrail, not a style
  preference — per the technical research, violating it means shipping a
  component that either fails to build under `componentize-py` or depends on
  the unmaintained `dicej/wasi-wheels` project this PRD explicitly does not
  rely on.
- **Cost.** `[ASSUMPTION]` No cost ceiling was stated in the Dream or brief;
  Fermyon Spin's cited production case (batch order processing, 60% compute
  cost reduction — domain research § 1) is weak positive evidence Wasm
  sandboxing is not inherently a cost tax, but no cost budget is set here.

##### Risk and Mitigations

*(carried forward from the brief's Known Risks section, restated against this
PRD's FRs)*

| Risk | Mitigation | Related FRs |
|---|---|---|
| The WASI-component ecosystem is ahead of typical Python production usage — this project pushes the frontier, per the domain research (only 1 of 3 comparable deployments offers Python as first-class). | Keep the WASI component's Python surface deliberately narrow (validation logic only, denylist-enforced). | FR-2, FR-13 |
| `componentize-py`'s own limitations are real: no dynamic runtime imports, `pydantic` support still open/unresolved upstream. | Audit the validation component's dependency surface at Architecture time, not discovered at build time; no `pydantic` inside the sandbox. | FR-13, § 8 Q3 |
| Component Model 1.0 itself is not yet finalized (WASI 0.3 shipped June 2026; 1.0 still roadmap). | Pin Wasmtime and `componentize-py` versions deliberately; treat a future spec-breaking change as a budgeted risk. | FR-14 |
| `wasi-threads` was removed from Wasmtime (47.0.0, 2026-07-20) — no mature multi-threaded execution model inside a WASI component today. | Design the validation component single-threaded, async-if-needed via WASI 0.3 primitives. | FR-2 |
| The April 2026 source gist's "Arrow buffers across the Wasm boundary" claim has no supporting implementation found anywhere. | This PRD does not repeat that claim — FR-2 is scoped to plain-Python-object validation. | FR-2 |

##### Integration and Dependencies

- **Enterprise OIDC/identity provider** — FR-1's authentication path; specific
  provider (Keycloak, Red Hat SSO, other) not yet named — Architecture
  decision.
- **Marquez** — the OpenLineage-compatible lineage service FR-10 emits to; this
  PRD assumes it is deployed alongside the pipeline, not a pre-existing
  enterprise service — Architecture should confirm.
- **Vector** — the telemetry sidecar (FR-11); assumed deployed per-pod.
- **`pyforge-atlas` (kinship, not a dependency)** — this PRD's Isolation-
  Verification Gate (FR-12) and future v2 dashboard both directly reuse
  patterns G1 already shipped; no code dependency in V1, but architecture
  should consult G1's implementation, not re-derive its gate design from
  scratch.
- **Unity Data Stack (kinship, future)** — the innersource platform this
  project could eventually run on top of; no integration in V1.

##### Data Governance

- **Layering as classification boundary.** Bronze holds validated-but-raw data;
  Silver/Gold hold conformed/business-ready data. `[ASSUMPTION]` No explicit
  data-classification (PII, confidential, etc.) scheme is defined in the Dream
  or brief — Architecture should treat this as an open question if the seed
  use case's actual data (headcount/cost, per UJ-1) turns out to carry PII,
  which would add retention/access-control requirements not currently
  specified.
- **Lineage retention.** OpenLineage facets accumulate in Marquez
  indefinitely by default; a retention policy is not specified — open question
  for Architecture/Ops.
- **Storage retention.** Bronze/Silver/Gold data persists on the PVC (FR-17)
  until explicitly purged; no retention/deletion policy specified in this PRD.

##### Compliance and Regulatory

`[ASSUMPTION]` No specific named regulatory framework (HIPAA, PCI-DSS, SOX,
GDPR) is stated in the Dream, gist, or brief — the posture is described
generically as "regulated enterprise" / "hardened enterprise." This PRD treats
Restricted SCC compliance (FR-16) and OIDC-gated access (FR-1) as the concrete,
verifiable compliance baseline, and defers naming a specific framework to
§ 8 Q2. If a specific framework is named later, it will likely add requirements
(audit-log retention, specific encryption-at-rest guarantees) not yet captured
here.

##### Operational Requirements

`[ASSUMPTION]` Not addressed in the Dream or brief and left intentionally thin
pending § 8 Q4 (operational ownership/SLA). No SLA, RTO/RPO, or support-tier
commitment is made in this PRD. Architecture should not assume a specific
uptime target without this being resolved first.
