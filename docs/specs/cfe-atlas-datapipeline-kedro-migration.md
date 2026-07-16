---
doc_type: spec
part_id: cf-atlas-datapipeline
display_name: cfe-atlas-datapipeline Kedro Migration Spec
project_type_id: data
date: 2026-06-20
status: ready
spec_updated: 2026-07-16
---

# Spec: cfe-atlas-datapipeline Kedro Migration

> **BMAD intake document.** Written for full BMAD execution (Full Flow
> track — data-platform migration effort). 9 implementation waves
> (0 + A–H) decomposed into the User Stories in § 9. Run BMAD with this
> file as the intent document:
>
> ```
> run bmad — implement the intent in docs/specs/cfe-atlas-datapipeline-kedro-migration.md
> ```
>
> This is the **v5 reset** of the spec — a clean re-authoring (2026-07-16)
> that states every standing decision once, in place. The v1–v4.1 layered
> evolution lives in this file's git history; § 15 carries the compact
> decision log and evidence pointers.

---

## 1. Status

| Field | Value |
|---|---|
| Status | **v5 (reset) — clean re-authoring 2026-07-16, grounded on live surface main `58a6dcc` / skill v8.78.0; ready for full BMAD execution intake.** 6 open questions (§ 11: Q1–Q4, Q6, Q7), none v1-blocking. |
| Owner | rxm7706 |
| Track | BMAD Full Flow (includes separate PRD/architecture phases) |
| Scope | Migrate the hand-rolled `cf_atlas` orchestrator (`conda_forge_atlas.py` + `bootstrap_data.py`, ~10,000 LOC, 23 cataloged phases) to a Kedro pipeline + Dagster orchestration + DuckDB compute, with a Vizro/Vizro-AI read surface and a Boring-Semantic-Layer + MCP/A2A agent interface. Includes three committed new-signal sources (FR-19 Basilisk vulnerabilities, FR-20 release velocity, FR-21 migration readiness). |
| Target | The `cf_atlas` intelligence layer under `.claude/skills/conda-forge-expert/` (data pipeline + read CLIs + MCP tools). |
| Tooling | Pixi-first; every component sourced from conda-forge and scaffolded via `nebi`. |
| Lifetime | Forward-looking migration. Legacy orchestrator runs in parallel until dataset parity is proven (Story B4), then is retired. |
| Predecessor | The existing 23-cataloged-phase `cf_atlas` pipeline (22 registered + Phase I; exact registry in § 3.3) and its 28 read CLIs. |

**Groundtruth rule**: the counts and literals in this spec are a snapshot of
§ 3.3's grounding commit. At BMAD intake, **re-enumerate the migration
surface from live groundtruth** (`pixi run -e local-recipes bmad-groundtruth`,
SKILL.md § Atlas Intelligence Layer) rather than trusting any inline literal —
per the standing rule that `docs/specs/` stays mutually in sync.

---

## 2. Operational Philosophy & Platform Ecosystem

Before detailing the architectural migration of `cf_atlas`, all implementations must strictly adhere to our universal operational guidelines.

### 2.1 Build for Autonomous AI Agents

Every system, interface, and dataset we produce must be inherently legible to, and controllable by, machine intelligence.

*   **Web Agents**: Any visualization or dashboard (e.g., Vizro-AI) must use pristine semantic HTML, clear ARIA attributes, and deterministic layouts to ensure scraper and browser agents can navigate without hallucinating.
*   **Agent Workflows**: APIs must be self-documenting (OpenAPI/Swagger) and **idempotent first** so agents can safely retry network requests. Error messages must be hyper-clear to allow LLMs to auto-diagnose.
*   **The Agent Harness**: We implement strict schema validation guardrails to catch erratic agent behavior and maintain exhaustive run-trace histories for absolute context state management. We integrate the **n8n-BMAD** framework for orchestrating automated QA Linter workflows and structural checks.

### 2.2 Spec-Driven Development & Agent Workforce (The 5 Personas)

We do not build or analyze on a whim. This migration is executed under the **BMAD Universal Workflow (v6.8.0 Framework)**, leveraging the **BMAD Architecture Suite Expansion Pack** during Tier-2 planning. Work is systematically processed through an explicit agent team ecosystem consisting of five distinct personas:

1.  **Ingester (Analyst)**: Reads the incoming raw Parquet data or payloads.
2.  **Compiler (Architect)**: Transforms raw data into structured concepts via BSL.
3.  **Linker (Developer)**: Connects nodes (packages, CVEs, feedstocks) within the graph.
4.  **Linter (QA/Reviewer)**: Validates constraints and handles scheduled weekly reviews. We explicitly augment this persona with the **Test Architect (TEA)** module (`npx bmad-method install --modules bmm,tea`) to design the Dagster validation contracts and parity tests.
5.  **Oracle (Product Owner)**: Acts as the primary interface for external queries and strategic tools.

### 2.3 Pixi-First Platform Tooling

To support this operational model, our entire platform ecosystem is defined in `pixi.toml` and managed by `nebi`. We strictly leverage:

*   `bmad-method` (>=6.8.0) for the agent-driven framework.
*   `gh` for automated delivery review and PR creation.
*   `nebi` for ecosystem orchestration and environment scaffolding.

### 2.4 Planning & Translation Tools

To execute this migration effectively, we utilize two crucial ecosystem extensions:
*   **Skill Forge (SKF)**: For translating the ~10,000 lines of legacy code into an ingestible agent context skill (Wave 0) with provable provenance.
*   **Creative Intelligence Suite (CIS)**: Utilizing the CIS planning agents (e.g., Carson the Brainstorming Coach and Maya the Design Thinking Coach) to explicitly define the downstream read surface (Vizro/Vizro-AI) and output the two-spine technical specs (`DESIGN.md` + `EXPERIENCE.md`) before writing frontend code.

### 2.5 BAD (BMAD Autonomous Development) Orchestration

To achieve true parallel execution across our 9 implementation waves, we execute this spec using the **BAD** module. BAD orchestrates multiple isolated git worktrees simultaneously, enforcing the following toolchain and skill pipeline:

*   **Prerequisite Modules**: Installed via `npx bmad-method install --modules bmm,tea,cis`.
*   **Tier-2 Planning Skills**: `@bmad-create-prd`, `@bmad-create-architecture`, and `@bmad-create-epics-and-stories`.
*   **Tier-3 Execution Skills**: BAD loops through the 7-step pipeline per story using:
    1. `@bmad-create-story`
    2. `@bmad-testarch-atdd` (TEA)
    3. `@bmad-dev-story` (Linker)
    4. `@bmad-testarch-test-review` (TEA)
    5. `@bmad-code-review` (Linter)

---

## 3. Current State: the cf_atlas Pipeline

The `cf_atlas` data pipeline currently operates as a bespoke, hand-rolled orchestrator (`conda_forge_atlas.py` + `bootstrap_data.py`) spanning ~10,000 lines of code (8,902 + 1,094 at skill v8.78.0).

### 3.1 Current Architecture & Constraints

*   **Orchestration**: 23 cataloged phases (22 registered + the Phase I side-effect; conda-side B → N incl. sub-phases, plus O–S PyPI intelligence; exact registry in § 3.3) executing in procedural order.
*   **State Management**: Custom checkpointing via a `phase_state` SQLite table (tracking cursors and completion).
*   **Incremental Processing**: Hand-rolled TTL gating using `*_fetched_at` timestamps on the primary `packages` table.
*   **Data Lineage**: Implicit. Dependencies between phases (e.g., Phase J requiring D and E) exist purely in the developer's head and the procedural calling order. The extreme case is Phase I (per-version download history): it exists only as a side-effect of Phase F's anaconda-api path — never registered in `PHASES`, invisible to `--skip`/`--only` — yet `version-downloads` and `release-cadence` depend on it. The migration makes it an explicit node with declared outputs.
*   **Read Surface**: 28 bespoke CLIs — 17 atlas read CLIs (e.g., `staleness-report`, `behind-upstream`), the 4 seed-gap suggesters, plus the 7-CLI cyclonedx suite (§ 3.3) — that output text/JSON and require manual maintenance.
*   **Visualization**: None. The system relies entirely on terminal stdout/stderr for observability.

### 3.2 Identified Gaps

*   **Maintainability bottleneck**: Adding a new phase requires manually wiring it into the `PHASES` registry, ensuring the SQL schema is migrated, and updating the orchestrator loop.
*   **Opaque Execution**: When `--fresh` takes 3-4 hours, operators have no visual way to monitor the DAG, identify bottlenecks, or view intermediate dataset schemas.
*   **Rigid Read Surface**: The 28 CLIs answer 28 specific questions. Ad-hoc questions require dropping into `sqlite3 cf_atlas.db` and writing manual JOINs.

### 3.3 Live-Surface Snapshot (main `58a6dcc`, skill v8.78.0, 2026-07-16)

The authoritative enumeration of the migration surface. Stories and FRs reference
this section instead of inline literals; re-verify with
`pixi run -e local-recipes bmad-groundtruth` at BMAD intake before planning.

*   **Schema**: `SCHEMA_VERSION = 29`; 22 tables; 5 views —
    `v_actionable_packages`, `v_pypi_candidates`, `v_pypi_intelligence_valid`
    (its consumers must read the view, never the raw table),
    `v_packages_enriched`, and `v_current_version_vulns` (the ONLY
    query-time-correct vuln source; the `packages.vuln_*` rollup is
    report-only). `trendshift-conda-forge.md` Phase T claims v29→v30.
*   **Phases**: 23 cataloged — 22 registered in the `PHASES` list
    (`conda_forge_atlas.py`, the single source of truth): B, B.5, B.6, C,
    C.5 (deferred), D, O, P, Q, R, S, E, E.5, F, G, G', H, J, K, L, M, N —
    plus **Phase I** (per-version download history), a side-effect of Phase
    F's anaconda-api path, cataloged in `atlas-phases-overview.md` but never
    registered (no independent scheduling; it ships with F and feeds
    `version-downloads` / `release-cadence` / G'). The migration promotes it
    to an explicit node. All of them write to `cf_atlas.db`. Credentialed: P
    (ClickHouse `default` / BigQuery ADC), E.5 / K / N (GitHub token),
    G / G' (vuln-db environment). TTL-gated set (hand-maintained
    `atlas_phase._TTL_GATED` map): F, G, G', H, K, L. Phase B.5 resolves the
    **dedicated feedstock** for split-out outputs via `_pick_feedstock`
    (umbrella vs dedicated — e.g. `dbt-bigquery` → the `dbt-bigquery`
    feedstock, not `dbt`) — attribution semantics every maintainer-scoped
    CLI depends on; the node port must preserve them (Story B1). Phase B.6
    yanked detection is deliberately **lite** (presence-in-current-repodata
    → `latest_status`); its full per-version variant is a recorded future
    hook, not current behavior (see the Story B1 note and § 12).
*   **Script surface**: 61 canonical scripts + 5 `_`-prefixed helpers under
    `.claude/skills/conda-forge-expert/scripts/`; 57 thin wrappers under
    `.claude/scripts/conda-forge-expert/`; 93 local-recipes + 7 vuln-db pixi
    tasks. The three-place rule (canonical script + wrapper + pixi task +
    SCRIPTS meta entry) is meta-test-enforced.
*   **Read CLIs (28)**: 17 atlas read CLIs (`detail-cf-atlas`,
    `staleness-report`, `feedstock-health`, `whodepends`, `behind-upstream`,
    `cve-watcher`, …) + the 4 seed-gap suggesters (`lts-registry-gap`,
    `cwe-seed-gap`, `spdx-schema-gap`, `license-map-gap` — read-only;
    § 3.4) + the 7-CLI cyclonedx suite (`export-purls`, `mapping-gap`,
    `universe-sbom`, `inventory-match`, `add-handoff`, `library-futures`,
    `recommend-2027`).
*   **MCP**: 46 `@mcp.tool()` functions in `.claude/tools/conda_forge_server.py`
    (23 atlas-relevant). `library-futures`, `add-handoff`, and the 4 seed-gap
    suggesters are deliberately CLI/pixi-only — do not add MCP tools for them
    during the port.
*   **External endpoints**: 19 `resolve_*_urls` helpers in `_http.py`, each
    overridable via `<HOST>_BASE_URL` for enterprise/JFrog mirror routing,
    plus `S3_PARQUET_BASE_URL` (Phase F parquet backend) and
    `ENDOFLIFE_BASE_URL` (EOL/LTS cache). These become external/API dataset
    nodes in the Kedro catalog (FR-1). FR-19 adds a 20th helper
    (`resolve_basilisk_urls` + `BASILISK_BASE_URL`); FR-21 rides the
    existing `resolve_github_raw_urls` — no new helper. `repo.prefix.dev`
    is already the first public mirror in the repodata fallback chain
    (JFrog → prefix.dev → conda.anaconda.org).
*   **Data files** — runtime (gitignored, `.claude/data/conda-forge-expert/`):
    `cf_atlas.db`, `purl-export/`, `universe-sbom/`, `eol_cache.json`
    (TTL 7 d, offline-stale-OK), `pypi_conda_map.json`, `vdb/`, `cve/`.
    Git-tracked seeds: `cwe_categories_seed.json`, `lts-registry.yaml`,
    `spdx.schema.json`.
*   **Write paths** — exactly 6 writers to `cf_atlas.db`:
    `conda_forge_atlas.py` (including the shared `phase_r_upsert_one` /
    `apply_readiness_scores` helpers that `add-handoff` reuses — the
    single-write-path property to preserve), `atlas_phase.py` TTL reset,
    the `mapping_gap.py` `g10_spelling` no-clobber writeback (see the
    mapping contract below), and the three standalone vulnerability-scoring
    fetchers — `cisa_kev_fetcher.py` (`cisa_kev`), `epss_fetcher.py`
    (`epss_scores`), and `cwe_catalog_fetcher.py` (`cwe_categories`) —
    whose tables Phase G / G' overlay at build time.
*   **Mapping / purl contracts**: `packages.pypi_name` rows written by
    `mapping-gap` carry `match_source='g10_spelling'` with
    `match_confidence` `verified`/`likely`, and the no-clobber UPDATE never
    touches `parselmouth`/`recipe_source_url` provenance — any
    re-implementation of the mapping layer must keep `g10_spelling` as a
    valid provenance tier and preserve the no-clobber rule. Exported purls
    use the `cfe:*` property namespace and the `?channel=conda-forge`
    qualifier on conda purls (G98) — FR-13's normalizer preserves both.
*   **Vulnerability read-path contract**: `detail-cf-atlas --vdb-all` overlays
    the atlas `cisa_kev` table onto vdb results via `_load_kev_cves` (vdb
    6.6.2's own KEV flags are always False — aqua ignores `kevc/`), reporting
    **KEV-affecting-current** to match Phase G's `vuln_kev_affecting_current`;
    CVSS base scores pass through `_coerce_cvss_score` (unwraps the pydantic
    `ScoreType` that vdb 6.6.2's partial `model_dump` leaves behind). Any
    migrated vuln read surface must keep both behaviors (Story B2).
*   **Scoring / report contracts**: `recommend-2027` stamps six `cfe:*` BOM
    properties (`futures_tier`, `futures_score`, `py314_readiness`,
    `lts_status`, `eol_date`, `atlas_built_at`) — the FR-13 normalizer
    preserves them like the rest of the `cfe:` namespace. Operator tier
    overrides travel via a `cfe:futures_tier=<tier>` marker in
    `pypi_intelligence.notes` plus a `--overrides` sidecar file — any
    migrated store must keep that notes-marker channel readable. The
    `library-futures` calibration gate is fixture-test-enforced (a weights
    change that reorders the pinned ranking fails CI) and must survive as a
    pipeline test. `library-futures` scoring is **in-memory /
    inventory-scoped by design** — there is no futures DB column; do not
    "migrate" a table for it.
*   **Freshness machinery**: `check_freshness` (`universe_sbom.py`,
    `STALE_AFTER_DAYS = 14`) consumed by 5 scripts; `*_fetched_at` columns +
    meta keys drive per-phase TTL gating; derived artifacts (`export-purls`,
    `universe-sbom`) regenerate after every atlas rebuild — model them as
    downstream nodes of the rebuild.
*   **Environments / tests**: 11 pixi environments (local-recipes / vuln-db /
    gcloud split, plus the standalone no-default-feature `pyforge-warden`
    and `bmad-ui` envs); test suite of 85 unit + 4 integration + 8 meta
    files. The meta tests pin the three-place rule and docs integrity — the
    migration keeps them green or explicitly retires them with the legacy
    path.
*   **Operational profiles** (`guides/atlas-operations.md` — the operational
    process the migration must reproduce): `bootstrap-data` ships three
    profiles — `--profile maintainer` (daily default; Phase E + N auto-scoped
    to `gh api user`), `--profile admin` (weekly channel-wide sweep), and
    `--profile consumer` (air-gapped: Phase F = s3-parquet, Phase H =
    cf-graph, no Phase N, no Phase D universe upsert) — with env-override
    precedence (`os.environ.setdefault`: explicit env/flags always win over
    profile defaults). The guide also fixes the per-source cron cadence
    table, the per-phase recovery playbook, and the ~3 GB storage budget
    (vdb dominates at 2.5 GB). Known legacy defect: the `cf_atlas_core`
    sub-step's HARD 1800 s wall-clock cap silently drops Phase F/K/N on cold
    admin runs (Phase R's first 5,000-candidate pull alone is ~15 min) — the
    concrete failure FR-6's per-node timeouts eliminate.
*   **Orchestration machinery this migration replaces**: `phase_state`
    checkpoint save/load, per-phase hardcoded `commit_every` values
    (200–5000), exponential/jittered backoff, the `atomic_writer` helper
    (`_http.py`), the linear `PHASES` driver with `--skip`/`--only`, the
    hand-maintained `_TTL_GATED` map, and the `bootstrap_data.py` sub-step
    driver with its single coarse `cf_atlas_core` timeout.

### 3.4 Out-of-pipeline data surfaces (the migration boundary)

Inventory of every data surface the `conda-forge-expert` skill uses that the
atlas pipeline does NOT build (verified against live code 2026-07-16). Three
enter this migration's scope as **external-refresh assets** (§ 5.2, Story B5);
the rest stay outside, each with the reason noted. This section fixes the
scope boundary — anything not listed in § 3.3 or here is out of the
migration's universe.

**In scope — separately-built local data stores (become orchestrated refresh
assets):**

| Store | Refreshed by | Upstream source | Consumers |
|---|---|---|---|
| AppThreat vdb (`vdb/` + `vdb-cache/`, ~2.5 GB) | `vdb-refresh` pixi task (**vuln-db env**, `appthreat-vulnerability-db`) | NVD / GHSA / OSV / npm / Snyk feeds | Phases G / G' (**read-only**), `detail-cf-atlas`, `inventory-channel`, `scan-project` |
| Offline OSV CVE store (`cve/`) | `update-cve-db` → `cve_manager.py` | osv.dev GCS bucket (`OSV_VULNS_BUCKET_URL`-overridable) | `vulnerability_scanner.py` offline mode |
| `pypi_conda_map.json` flat mapping cache | `update-mapping-cache` → `mapping_manager.py` | regro/cf-graph (parselmouth) + conda-forge-metadata API | `name_resolver.py`, `recipe-generator.py`, `mapping_gap.py` — **independent of Phase C** (see Q6) |

`bootstrap_data.py` already orchestrates the first two alongside the atlas
build; the migrated pipeline must not regress below that coverage.

**Out of scope (declared as inputs, never built by the pipeline):**

*   **Static git-tracked seeds** — `lts-registry.yaml`,
    `cwe_categories_seed.json`, `spdx.schema.json`, the legacy mapping seeds,
    `config/skill-config.yaml`. Curated inputs; the Kedro catalog declares
    them as versioned external datasets where the pipeline reads them.
*   **Recipe template trees** (`templates/`, 14 language families) — Phase S
    stores only the template *path string*; the files are read at
    recipe-generation time by the authoring loop.
*   **Live authoring-time fetches** — `recipe-generator.py` (PyPI metadata +
    sdist SHA256 at generation moment), `dependency-checker.py` (live channel
    repodata / Artifactory mirror), `pr_artifacts.py` (Azure DevOps API),
    `submit_pr.py` + feedstock maintenance (`gh` CLI), npm/GitHub version
    checkers. Transactional point-in-time operations of the recipe-authoring
    loop (§ 12), not pipeline data.
*   **User-supplied inputs** — the `recipes/` tree and the manifests / locks
    / SBOMs / containers passed to `scan-project` / `inventory-match`;
    per-invocation entry datasets (modeled as such in the catalog).
*   **The skill knowledge base** (SKILL.md, `reference/`, `guides/`) —
    documentation, not data.

**Seed-freshness report nodes (read-only fan-out from the curated inputs).**
The curated seeds above stay hand-owned (the pipeline reads, never writes
them), but each has a **read-only gap-suggester** that diffs the seed
against live ground truth and *proposes* additions for git review — the
maintenance loop that keeps a hand-curated input from silently drifting. The
migrated pipeline models the four suggesters below as terminal **report
nodes** fanned out from their external seed datasets — report-only, they never
mutate the atlas — **with the sole exception of `mapping-gap`, which writes
back** (the `g10_spelling` provenance UPDATE, § 3.3 mapping contract) and is
listed for completeness:

| Suggester | Curated input | Ground-truth it diffs against | Node reads | Node behavior |
|---|---|---|---|---|
| `lts-registry-gap` | `data/lts-registry.yaml` | endoflife.date `/api/all.json` | `v_actionable_packages` + the eol feed | Report-only (derived-layer) |
| `cwe-seed-gap` | `cwe_categories_seed.json` | the MITRE `cwe_categories` catalog | `cwe_categories` (rows bucketed `Other`) | Report-only (derived-layer) |
| `spdx-schema-gap` | `spdx.schema.json` (vendored enum) | the upstream SPDX license list | `v_actionable_packages.conda_license` | Report-only (derived-layer) |
| `license-map-gap` | in-code `_LICENSE_TO_SPDX` | the vendored SPDX enum | `v_pypi_intelligence_valid.license_raw` (NULL `license_spdx`) | Report-only (derived-layer) |
| `mapping-gap` | the PyPI↔conda mapping | `pypi_universe` + corroborators | `packages` | **Write-back** (`g10_spelling`) — not a report node |

**Except for `mapping-gap` (which writes back to the core atlas)**, these are
downstream of the atlas rebuild (they read its views), produce `derived`-layer
report artifacts only, and — like the `export-purls` / `universe-sbom`
regeneration cadence — re-run after every rebuild so the freshness reports
track the live universe. The four report-only suggesters are the dedicated
**Seed-Gaps Pipeline** (§ 5.2 item 6, ported by Story B6); the kedro-viz
prototype (`prototypes/cf-atlas-kedro-viz`) mirrors it as its `seed_gaps`
pipeline. `mapping-gap` stays in the mapping / Phase-C layer (its writeback
belongs with the mapping stage, not the report fan-out).

---

## 4. Target Architecture: Why These Choices

To resolve the § 3.2 bottlenecks, we migrate the custom orchestrator to **Kedro**, an open-source framework for building reproducible, maintainable, and modular data science code.

### 4.1 Why Kedro?

*   **Data Catalog (`catalog.yml`)**: Decouples data access from logic. S3 parquet files, APIs, and SQLite tables become declaratively configured datasets.
*   **Modular Pipelines**: Transforms the 23 cataloged phases (22 registered + Phase I) into explicit Nodes with declared inputs and outputs, automatically resolving the execution DAG.
*   **Testability**: Nodes become pure Python functions testing `pandas.DataFrame` inputs/outputs, making unit testing trivial compared to mocking SQLite connections.

### 4.2 Why Kedro-Viz?

*   Provides an interactive, auto-generated visual representation of the `cf_atlas` DAG.
*   Allows operators to monitor real-time execution state, inspect dataset schemas (e.g., what exactly does Phase G' look like?), and track data lineage across the pipeline.

### 4.3 Why Vizro & Vizro-AI?

*   Replaces the 28 bespoke terminal CLIs (§ 3.3) with a high-quality, web-based dashboard application built explicitly for AI web agents (semantic DOM).
*   **Vizro-AI** introduces a natural language intelligence surface. Operators and BMAD agents can pass natural language queries (e.g., *"Plot the top 10 most downloaded packages that have critical CVEs and are unmaintained"*) which Vizro-AI compiles into pandas operations against the Kedro catalog and visualizes dynamically.

### 4.4 Why Dagster (`kedro-dagster`)?

*   Replaces the legacy cron + bash script orchestration of `bootstrap-data`.
*   Provides a production-grade orchestration engine to handle retry logic, resource constraints, and complex pipeline schedules.
*   The `kedro-dagster` plugin allows seamless compilation of the Kedro DAG into a Dagster graph, giving the best of both worlds (Kedro for authoring, Dagster for running).

### 4.5 Why MCP Integration (`kedro-mcp`)?

*   Maintains the critical requirement that BMAD agents can interrogate and interact with the pipeline via the Model Context Protocol.
*   By leveraging `kedro-mcp`, we can expose Kedro pipelines and catalog reads directly as MCP tools, replacing the need for bespoke subprocess wrappers in `FastMCP`.

### 4.6 Why Boring Semantic Layer (BSL)?

*   Provides a lightweight, developer-native semantic layer built on top of Ibis to bridge the gap between `cf_atlas.db` and AI agents.
*   Allows us to formally define business metrics (e.g., "staleness", "adoption stage") and dimensions as first-class nodes in a semantic graph, ensuring that LLMs (via Vizro-AI or MCP) generate accurate, consistent queries.
*   Preserves the structural knowledge of `cf_atlas.db` as a reusable semantic knowledge graph rather than relying on raw SQL prompts.

### 4.7 Why A2A (Agent-to-Agent) Integration?

*   While MCP allows human-to-agent or direct agent-to-tool integration, A2A allows specialized autonomous agents to collaborate.
*   Enables complex, multi-agent workflows where a data-analyst agent (querying BSL) can securely and seamlessly pass structured insights or sub-tasks directly to a recipe-authoring agent.

### 4.8 The DuckDB Singularity (Compute, Graph & Vector)

*   **Unified Engine**: The legacy SQLite database and fragmented compute proposals (Polars, Neo4j, Kùzu, LanceDB) will be completely replaced by **DuckDB**.
*   **Parquet Native**: DuckDB natively reads S3 Parquet and executes multi-core analytical queries, drastically reducing the 3-4 hour cold start time.
*   **All-in-One**: DuckDB handles graph traversals natively via recursive CTEs and handles RAG embeddings via the Vector Similarity Search (`vss`) extension.
*   **Data Quality Guardrails**: Integrating **Great Expectations** ensures we catch malformed API data (e.g., PyPI JSON missing version fields) mid-pipeline, preventing poisoned data from entering the database.

### 4.9 WebAssembly (WASM), Pixi-Native Portability & `nebi` Scaffolding

*   **Strict Pixi Tooling**: Every component of the pipeline (Kedro, Dagster, DuckDB, Ibis) will be sourced exclusively from `conda-forge` and managed via a single `pixi.toml`. No standalone binaries or JVM requirements.
*   **Ecosystem Management (`nebi`)**: The entire project structure, environment configuration, and Pixi toolchain will be scaffolded and managed using **`nebi`** (from `nebari-dev`). If custom scaffolding logic is required for Kedro-Dagster-WASM deployments, new features will be contributed back to `nebi-client`.
*   **Serverless Portability**: By compiling to `duckdb-wasm`, the entire intelligence surface (Vizro-AI dashboard and BSL layer) can run locally in the browser via Pyodide. The Kedro pipeline emits pure Parquet chunks to a static store (e.g., GitHub Pages), and the WASM runtime pulls them via HTTP Range requests with zero backend infrastructure.

### 4.10 Universal SBOM Integration (CycloneDX)

*   The legacy pipeline strictly tracks `meta.yaml` dependencies. The modernized pipeline will treat dependency extraction as a universal Software Bill of Materials (SBOM) ingestion problem.
*   **Tiered intake** (FR-13 + FR-17). Policy-supported core tier: `pixi.toml`, `pixi.lock`, `pyproject.toml`, `recipe.yaml`, and `meta.yaml`. Extended tier (already handled by the shipped `scan-project` / `inventory-match` tooling — of which `requirements.txt` and `environment.yml` incl. nested `pip:` are also covered by `pyforge-warden.md`'s Manifest Resolution Engine): `requirements.txt`, `environment.yml` (including nested `pip:` blocks), `conda-lock.yml`, `pdm.lock`, live venv / conda environments, container images, `pip freeze` / `conda list` text, and SBOM-in passthrough (CycloneDX/SPDX). Everything normalizes strictly into the **CycloneDX** standard format.
*   This creates a unified, ecosystem-agnostic semantic graph in DuckDB, allowing operators to cross-reference PyPI constraints (`pyproject.toml`) against conda constraints (`recipe.yaml`) using a globally recognized specification.

### 4.11 Target State: Enterprise Python Manifest Generation

*   **The 5k Manifest**: The intelligence graph built by `cf_atlas` will directly drive the programmatic generation of the **Enterprise Python Manifest**, capping the environment at 5,000 curated packages.
*   **SLSA Prioritization**: The pipeline will merge Google Assured OSS and Anaconda Defaults as an immutable base, then use the PyPI/Vulnerability intelligence scores to safely fill the remaining quota from `conda-forge`.
*   **Determinism & Mirroring**: The output will be resolved via `prefix.dev`, mirrored via JFrog Artifactory, and actuated strictly by `pixi.lock` for local environments (devcontainers) and Docker CI/CD deployments.

### 4.12 Target State: LLM-Powered Knowledge Base (Wagtail CMS)

*   **Markdown Compilation**: Beyond the Vizro dashboard, `cf_atlas` will output its intelligence artifacts as a compiled, living knowledge base powered by **Wagtail CMS** (leveraging `wagtail-markdown` and `django-lasuite`).
*   **Agentic Maintenance**: Using the "Karpathy Architecture", LLMs will incrementally compile, link, and maintain this knowledge base. They will read Parquet outputs, build relationships via `graphify`, index documents via `cocoindex`, and synthesize vulnerability reports.
*   **Extensible Outputs**: BMAD agents querying the BSL layer will output reports directly into the Wagtail CMS as Markdown pages, Marp slide decks, or matplotlib charts, creating a compounding, centralized organizational brain.

---

## 5. End-to-End Kedro Architecture

### 5.1 Data Catalog Design (`conf/base/catalog.yml`)

The bespoke `_http.py` and SQLite `init_schema()` logic will be mapped to Kedro Datasets:

*   **DuckDB Datasets**: `pandas.ParquetDataset` and native DuckDB integration will manage reads/writes. The pipeline writes partitioned Parquet files instead of updating a monolithic SQLite DB.
*   **API Datasets**: Custom API datasets or `pandas.JSONDataset` for GitHub, PyPI, and Anaconda API interactions.
*   **TTL / Incremental State**: We will implement a custom `IncrementalParquetDataset` that encapsulates the `*_fetched_at` TTL logic.

### 5.2 Modular Pipelines

The legacy phases refactor into seven domain-specific pipelines:

1.  **Core Pipeline**: Foundational conda-forge enumeration and graph building.
2.  **PyPI Intelligence Pipeline**: PyPI mapping, skew detection, and scoring. Also hosts the `pypi_conda_map.json` refresh (`update-mapping-cache`) as an external-refresh asset — pending Q6's consolidation decision (§ 11; the asset itself is inventoried in § 3.4) — and the `mapping-gap` `g10_spelling` writeback (§ 3.3 mapping contract: the one gap tool that mutates the atlas belongs with the mapping stage).
3.  **Vulnerability Pipeline**: AppThreat VDB and CISA KEV ingestion and overlay; the external-refresh assets for the AppThreat vdb (`vdb-refresh`, vuln-db env) and the offline OSV store (`update-cve-db`) per § 3.4 — today orchestrated by `bootstrap_data.py`, tomorrow Dagster-scheduled (Story B5); and the **Basilisk ingestion node family** (FR-19, Story B8) — a batch-query node (`POST /v1/querybatch`, ≤1,000 queries/request) writing the `basilisk_vulns` dataset keyed by conda PURL (`pkg:conda/conda-forge/<name>@<version>`, CEP 63) plus a bounded detail-fetch node (`GET /v1/vulns/{id}`), a second, conda-native vulnerability identity axis complementary to the PyPI-keyed vdb. Read nodes honor the § 3.3 vulnerability read-path contract (atlas `cisa_kev` KEV overlay + CVSS ScoreType coercion).
4.  **VCS & Health Pipeline**: GitHub/GitLab live queries and upstream version tracking; the **release-to-availability velocity columns** (FR-20, Story B9) on the Phase H join — `release_lag_hours` + `release_lag_qualifies`, computed only where the upstream release is ≤90 days old (the rebuild-cadence-artifact guard); and the **migration-readiness nodes** (FR-21, Story B10) — external datasets over `conda-forge/conda-forge-bot-data` `status/` (category lists + per-migration `migration_json/<name>.json`, partitioned by active migration) plus a classification node joining them against the feedstock set and Phase B's `conda_noarch`.
5.  **Universal SBOM Pipeline**: A dedicated pipeline utilizing native parsers and tools (e.g., `cdxgen`) to extract dependencies from the tiered intake of § 4.10, strictly normalized into the **CycloneDX** specification before being written to DuckDB Parquet datasets. Four node families beyond parsing (FR-16/17/18): a **transitive-resolver node** (pip `--dry-run --report` for PyPI / py-rattler solve for conda; records depth + fan-out) that upgrades bare manifests to full dependency sets — resolution honors the `_http.py` mirror-routing contract (§ 3.3 external endpoints) and degrades gracefully when offline (consumer profile: resolve from a provided lockfile or cached index, else skip resolution and mark the BOM `unresolved` rather than fail); the **inventory-match matching node** preserving the shipped six-bucket semantics (ADD / ADD-NONPYPI / UPDATE-FEEDSTOCK / UPDATE-PIN / CURRENT / UNKNOWN, three-way version comparison, channeldata-live recovery); a forward-looking **dependency-hygiene scan node** (deptry — unused / missing / misplaced deps; FR-16, Story F4); and the **unified CI policy gate** (FR-18) as the pipeline's terminal quality node.
6.  **Seed-Gaps Pipeline**: The four report-only gap suggesters (`lts-registry-gap`, `cwe-seed-gap`, `spdx-schema-gap`, `license-map-gap` — § 3.4) as terminal report nodes fanned out from their external seed datasets, downstream of the atlas rebuild, producing `derived`-layer freshness reports only. Strictly read-only; `mapping-gap` is deliberately excluded (its writeback lives in pipeline 2). Ported by Story B6.
7.  **Read-Surface / Derived-Artifacts Pipeline**: The post-rebuild regeneration nodes — `export-purls` (six purl/mapping artifacts) and `universe-sbom` (the ~856k-component full-universe CycloneDX BOM, a first-class `derived`-layer catalog dataset) — bound to every rebuild per the § 3.3 freshness machinery; the 14-day `check_freshness` gate (`STALE_AFTER_DAYS = 14`) becomes the dataset-level freshness contract the four derived-artifact consumers (`universe-sbom`, `inventory-match`, `library-futures`, `recommend-2027`) enforce.

### 5.3 Checkpointing & Idempotency

*   Remove the `phase_state` table.
*   Utilize Kedro's native `runner` capabilities and persistent intermediate Parquet datasets to achieve resumability.

### 5.4 Dagster Orchestration (`kedro-dagster`)

*   The entire Kedro pipeline will be converted into a Dagster repository using the `kedro-dagster` plugin.
*   Schedules (Daily for Phase N, Weekly for Phase F/G, etc.) will be defined as Dagster Schedules. The per-source **cron cadence table in `guides/atlas-operations.md`** is the source of truth those Schedules encode (bootstrap weekly; F/H/K/L/E.5 + G-after-vdb daily; E/J/M every 6 h; N hourly per maintainer; vdb-refresh / update-cve-db / update-mapping-cache weekly). Phase N's hourly cadence is the guide's *measured* maintainer-scope cost (batched GraphQL, ~30 s for ~700 feedstocks) — the port inherits that rate-limit-aware batching, and the Dagster Schedule surfaces remaining-rate-limit as a resource so operators with larger portfolios can back the cadence off (4–6 h) instead of hitting the ceiling.
*   The three **bootstrap profiles** (`maintainer` / `admin` / `consumer` — § 3.3 operational profiles) become named Dagster **job configurations** over the same DAG (phase subset + per-phase source selection), preserving the guide's override precedence: profile values are defaults (`os.environ.setdefault` semantics today); explicit run-config / env always wins.
*   Phase states and retries will be monitored via the Dagit/Dagster UI, complementing the structural view provided by `kedro-viz`. The guide's per-phase **recovery playbook** (symptom → recovery) and TTL-reset recipes map to per-node retry policies and selective re-materialization; Phase N's checkpoint/resume becomes FR-4 resumability.
*   **Timeouts are per-node**, replacing `bootstrap_data.py`'s single coarse `cf_atlas_core` cap — the 1800 s hard timeout that silently drops Phase F/K/N on cold admin runs (§ 3.3 known issue) cannot recur when each node carries its own budget and failure isolation.
*   The ~3 GB storage budget (vdb 2.5 GB dominant) is declared as a resource constraint on the vulnerability pipeline's external-refresh assets.

### 5.5 MCP Exfiltration (`kedro-mcp`)

*   The existing 46 MCP tools hosted in `.claude/tools/conda_forge_server.py` (23 atlas-relevant, § 3.3) will be audited and ported; the non-atlas recipe-authoring tools stay on the FastMCP server.
*   `kedro-mcp` will expose datasets and pipeline triggers to Claude Code.
*   BMAD Agents will trigger specific pipelines (e.g., `run_vulnerability_pipeline`) and read the resulting datasets natively via MCP.

### 5.6 Semantic Knowledge Graph (Boring Semantic Layer)

*   We will implement the **Boring Semantic Layer (BSL)** on top of the Kedro Parquet datasets using Ibis (which natively compiles to DuckDB SQL).
*   The schema and business logic currently trapped inside the 28 query CLIs (§ 3.3) will be extracted and declared as BSL dimensions and measures.
*   This semantic knowledge graph will serve as the trusted translation interface for Vizro-AI and BMAD agents.

### 5.7 A2A (Agent-to-Agent) Integration

*   Alongside MCP, we will build a dedicated Agent-to-Agent communication surface.
*   This will allow the `cf_atlas` analytical agent (which uses BSL to formulate insights) to exchange structured payloads directly with the `conda-forge-expert` recipe-authoring agent.
*   The A2A interface will support publish/subscribe or direct-messaging protocols, providing an architectural foundation for autonomous, multi-agent remediation pipelines (e.g., Agent A finds a CVE via BSL, Agent B authors the fix).

### 5.8 Data Quality Guardrails (Great Expectations & Pandera)

*   We will define strict data contracts using Great Expectations and Pandera. The outdated `kedro-great-expectations` and `kedro-pandera` plugins are blocked/banned.
*   We will write custom Kedro `AfterNodeRunHook` classes to run Great Expectations validations, and use inline Pandera schema assertions inside nodes.
*   Dagster will halt nodes upon validation failures (which raise exceptions in Kedro), triggering A2A alerts for agentic investigation before bad data is persisted.

### 5.9 Event-Driven Sensors, Lineage & Observability

*   Instead of strictly batch-based polling, we will utilize **Dagster Sensors** tied to PyPI/GitHub webhooks or RSS feeds. This enables the pipeline to react incrementally in near-real-time to upstream ecosystem changes.
*   **OpenLineage** will track execution metadata (e.g., rows processed, latency, cache hits), exposing this telemetry to optimization agents for automated pipeline tuning.
*   **OpenTelemetry (OTel)** will provide end-to-end observability. By instrumenting the Kedro nodes, Dagster runs, and DuckDB queries with OTel, we ensure comprehensive distributed tracing, metrics, and structured logging, allowing operators and A2A agents to pinpoint exact bottlenecks or failures down to the specific API call.

---

## 6. Vizro-AI Intelligence Surface

The read-surface migration will decouple the data layer from the intelligence layer:

1.  **Dashboard scaffolding**: A Vizro app deployed locally (or via WASM) serving the core KPIs currently locked in CLIs (staleness, adoption stage, feedstock health).
2.  **Vizro-AI Integration**: Expose an input field (and an MCP tool for Claude Code) that accepts user prompts.
3.  **Agentic Interrogation**: The BMAD agent can use the MCP `query_vizro_ai` tool to ask open-ended questions about the semantic knowledge graph and receive back generated charts and insights.

---

## 7. The AI Software Factory Architecture

To seamlessly merge our `cf_atlas` data layer with the enterprise's overarching autonomous goals, the system maps onto the **4-Layer AI Software Factory Blueprint**. This layer is **in scope** and delivered as Wave H.

### 7.1 Layer 1 — LA SUITE DOCS (Presentation - The Human UI)

The human interface relies on **django-lasuite** and the **Wagtail CMS**. This acts as the visual "Corporate Brain", exposing the main Wiki article area, real-time collaboration avatars, and a unified search bar. The CMS is populated dynamically by the backend agents via REST API (Read/Write).

### 7.2 Layer 2 — DAGSTER (Orchestration - The Trigger Engine)

`kedro-dagster` serves as the trigger engine. It manages the execution DAG via two primary activation pathways:

*   **Sensors**: Event-driven triggers (e.g., "New File Detected" when PyPI webhooks arrive or Parquet files are dumped).
*   **Schedules**: Cron-based triggers (e.g., "Weekly Schedule" to fire the Linter/QA agents for feedstock health checks).

### 7.3 Layer 3 — THE AGENT WORKFORCE (Governance)

The autonomous workflow is governed by the 5 specific personas (Ingester, Compiler, Linker, Linter, Oracle) powered entirely by `bmad-method` (we explicitly reject `spec-kit`). These agents execute the physical tools (`lasuite_client.py` for API push, `markdown_generator.py` for Wiki writing, `search_ops.py` for retrieval, and `pdf_parser.py` for deep research).

### 7.4 Memory Layer — THE KARPATHY WIKI (The Brain's Storage)

The LLM-Powered Knowledge base enforces a strict, incremental storage architecture backed by Minio (S3) and PostgreSQL (using DuckDB/Ibis as the semantic query engine):

*   `wiki/raw/`: The raw Parquet ingestion landing zone.
*   `wiki/compiled/`: The knowledge graphs, BSL mapped concepts, and linked dependency files.
*   `wiki/outputs/`: The final markdown reports, slide decks, and generated visualizations output by the Oracle agent.

---

## 8. Functional Requirements

### FR-1. Declarative data access via Kedro Data Catalog

All API sources (GitHub, PyPI, Anaconda) and all Parquet outputs are declared as datasets in `conf/base/catalog.yml`. No data-access logic embedded in node functions. (§ 4.1, § 5.1.)

### FR-2. Phases refactored into modular, DAG-resolved pipelines

The 23 cataloged legacy phases (22 registered + Phase I) become Kedro Nodes with declared inputs/outputs grouped into the seven domain pipelines of § 5.2. Execution order is resolved by Kedro from the DAG, not by procedural call order. (§ 4.1, § 5.2.)

### FR-3. Custom `IncrementalParquetDataset` preserves TTL gating

The `*_fetched_at` TTL incremental-processing semantics are encapsulated in a reusable dataset class, replacing the hand-rolled timestamp checks. (§ 5.1.)

### FR-4. `phase_state` table removed; resumability via Kedro runner + persisted Parquet

Checkpointing is achieved through Kedro's native runner and persistent intermediate Parquet datasets. The bespoke `phase_state` SQLite table is deleted. (§ 5.3.)

### FR-5. DuckDB replaces SQLite + all fragmented compute proposals

DuckDB is the single engine for analytical compute, graph traversal (recursive CTEs), and vector search (`vss` extension), reading partitioned Parquet natively. (§ 4.8, Wave F.)

### FR-6. Dagster orchestrates schedules + retries via `kedro-dagster`

The Kedro DAG compiles to a Dagster repository. Daily/weekly schedules and retry logic move from cron+bash to Dagster Schedules (cadence per the `guides/atlas-operations.md` table, § 5.4); state is observable in the Dagster UI. The `bootstrap-data --fresh` entry point becomes the full-DAG Dagster job (the `__default__` Kedro pipeline); the three bootstrap profiles become named job configurations; the script itself is retired at B4 parity along with the legacy orchestrator. Motivating failure: the legacy `cf_atlas_core` sub-step's HARD 1800 s cap silently drops Phase F/K/N on cold admin runs (§ 3.3) — per-node Dagster timeouts/retries make that class of failure structurally impossible. (§ 4.4, § 5.4.)

### FR-7. MCP surface preserved via `kedro-mcp`

The existing MCP tools in `.claude/tools/conda_forge_server.py` are audited and ported so BMAD agents retain pipeline-trigger + dataset-read access via MCP. (§ 4.5, § 5.5.)

### FR-8. Boring Semantic Layer over the Kedro catalog (Ibis → DuckDB)

The metrics and business logic currently embedded in the 28 read CLIs (§ 3.3) are declared as BSL dimensions and measures, serving as the trusted translation layer for Vizro-AI and agents. (§ 4.6, § 5.6.)

### FR-9. Read surface migrates from 28 CLIs to a Vizro / Vizro-AI dashboard

The 28 bespoke CLIs (§ 3.3) become Vizro pages + a Vizro-AI natural-language query field, exposed both as a web dashboard and as an MCP tool. (§ 4.3, § 6.)

### FR-10. Data-quality contracts via Great Expectations halt bad data

Great Expectations contracts are wired into Kedro nodes; Dagster halts on contract violation and raises an A2A alert before bad data is persisted. (§ 4.8, § 5.8.)

### FR-11. A2A interface for inter-agent collaboration

A dedicated Agent-to-Agent surface lets the `cf_atlas` analytical agent exchange structured payloads with the `conda-forge-expert` recipe-authoring agent. (§ 4.7, § 5.7.)

### FR-12. Lineage + observability via OpenLineage + OpenTelemetry

Kedro nodes, Dagster runs, and DuckDB queries are instrumented with OpenLineage (lineage/metrics) and OpenTelemetry (distributed tracing/logging). (§ 5.9.)

### FR-13. Universal SBOM ingestion normalized to CycloneDX

A dedicated SBOM pipeline parses the tiered intake of § 4.10 (core tier: `pixi.toml`, `pixi.lock`, `pyproject.toml`, `recipe.yaml`, `meta.yaml`), normalizing to CycloneDX before writing to DuckDB. The normalizer preserves the `cfe:*` property namespace — including the `recommend-2027` property set (§ 3.3 scoring contracts) — and the `?channel=conda-forge` purl qualifier; it never strips either during normalization. FR-17 extends the intake and adds transitive resolution. (§ 4.10, § 5.2.)

### FR-14. WASM portability for the intelligence surface

The Vizro-AI dashboard and BSL layer compile to `duckdb-wasm`/Pyodide; Parquet artifacts are served from a static host (GitHub Pages) and pulled via HTTP Range requests with zero backend. (§ 4.9, Wave G.)

### FR-15. Pixi-first, nebi-scaffolded toolchain (conda-forge only)

Every component (Kedro, Dagster, DuckDB, Ibis, …) is sourced from conda-forge and managed in a single `pixi.toml`, scaffolded by `nebi`. No standalone binaries or JVM. (§ 2.3, § 4.9.)

### FR-16. Dependency-hygiene scan node (deptry) in the Universal SBOM pipeline

A hygiene node runs `deptry` over the § 4.10 tiered intake **when project source code accompanies the manifest** — deptry's analysis is AST/import-based, so for source-less inputs (bare manifests, lockfiles, SBOM passthrough) the node skips gracefully and the report records the reduced scope instead of failing. Findings (unused / missing / transitive-only / misplaced dependencies) populate the `hygiene` section of `pyforge-warden.md`'s `ComplianceReport` schema; the *complete* report — `hygiene` from this node plus a `security` section sourced from `inventory-match`/`cve` (the atlas does **not** re-invoke `osv-scanner`; standalone `pyforge.warden` v1 does) — is assembled and schema-validated at the FR-18 terminal gate (`derived` layer). Because the shared artifact is pyforge-warden's `ComplianceReport`, the planned promotion of `pyforge.warden` into the atlas surface (MCP tool + pixi CLI, consolidation with `scan-project`) is a wiring change, not a redesign. The toolchain is conda-native (`recipes/deptry`, `recipes/osv-scanner` mirror on main; `fawltydeps` / `pip-check-reqs` as candidate future engines). (§ 4.10, § 5.2 item 5, Story F4.)

### FR-17. Transitive resolution + the universe BOM extend the SBOM intake

(a) A transitive-resolver node (pip `--dry-run --report` for PyPI / py-rattler solve for conda; records resolution depth + fan-out) upgrades bare manifests to full dependency sets before CycloneDX normalization; it honors the `_http.py` mirror-routing overrides and degrades gracefully offline (lockfile/cached-index resolution, else an explicit `unresolved` marker) so the consumer profile keeps working air-gapped. (b) The intake accepts the full § 4.10 tiered format set. (c) The ~856k-component full-universe CycloneDX BOM is a first-class catalog dataset (`derived` layer, regenerated after every rebuild, guarded by the 14-day freshness contract — § 5.2 item 7). (d) The matching node preserves `inventory-match`'s six-bucket semantics, three-way version comparison, and channeldata-live recovery. Extends FR-13. (§ 5.2 items 5 + 7, Story B7.)

### FR-18. Unified CI policy gate

One terminal quality node assembles the full `ComplianceReport` — `hygiene` from the FR-16 node, `security` from `inventory-match`/`cve` — converging `pyforge-warden.md`'s strict exit-code gate with `inventory-match --policy` (exit 0 pass / 1 policy-fail / 2 error; `max_critical` / `max_high` / KEV thresholds), emits the schema-validated artifact into the `derived` layer, and halts Dagster on failure exactly like an FR-10 contract violation (raising the A2A alert). CI consumes the exit code. (§ 5.2 item 5 terminal node, § 5.8, Story F4.)

### FR-19. Conda-native vulnerability source: Basilisk (prefix.dev)

The Vulnerability Pipeline gains a second, conda-native identity axis: `api.basilisk.prefix.dev` — a live, no-auth, OSV-compatible REST API matched against the actual conda-forge PURL (`pkg:conda/conda-forge/<name>@<version>`, CEP 63 form) — complementary to the PyPI-keyed vdb of Phase G. It catches advisories on packages the PyPI-keyed pipeline structurally cannot see because they were never PyPI packages (live-validated over the full 21,163-package Python population: confirmed advisories on `libuuid` — 203M downloads, CVE-2026-3184 — `libtiff`, `libarchive`, `perl`, all non-Python C/system libraries riding as transitive Python-environment dependencies).

Ingestion is two nodes (§ 5.2 item 3): a **batch-query node** — `POST /v1/querybatch`, documented cap 1,000 queries/request (live run: 85 requests of 250 over the full population, zero errors) — writing the `basilisk_vulns` dataset in the lightweight batch shape (`conda_name`, `advisory_id`, `modified`); and a **bounded detail-fetch node** — `GET /v1/vulns/{id}` for full OSV detail (severity, `affected[].ranges[].events`) — a separate follow-up pass (live: all 765 unique advisory IDs in one pass, no further batching).

Constraints hardened by the live analysis, all binding on the implementation:

*   **Match by package name, never by the OSV ecosystem tag** — the raw `affected[]` entries retain their *original* source ecosystem (typically `PyPI`), never `conda-forge`; an ecosystem-field consumer silently finds nothing (hit and fixed during the live run).
*   **Version currency ≠ security currency** — 113 of the 348 confirmed-match packages are classified `current` by `behind-upstream`'s lag logic; no read surface may render a `current` verdict as "unaffected."
*   **`fix_available` is tri-state** (`true` / `false` / `unknown`) — ~48% of advisories carry no structured fix-version data (enumerated `versions` list only, a data-completeness gap in the upstream OSV records); `unknown` must never collapse to `false`. The derived signal is cheap and high-value: name-matched, `packaging.version`-compared cross-referencing of `affected[].ranges[].events[].fixed` against the current installed version live-resolved **85.3% of 5,101 (package, advisory) matches as upgrade-resolvable** — mostly a packaging-currency problem, not an open security-research one. Join at query time against `behind_upstream`'s upstream-version data (same join key Phase H already requires).

The endpoint gets a `resolve_basilisk_urls` helper + `BASILISK_BASE_URL` override per the § 3.3 mirror-routing convention (19 → 20 `resolve_*_urls`). Landing point (Kedro-only vs interim legacy Phase U) is Q7 (§ 11). (§ 5.2 item 3, Story B8.)

### FR-20. Release-to-availability velocity signal (with the rebuild-cadence guard)

The VCS & Health pipeline derives the previously-unmeasured rate metric "how long does conda-forge take to publish a matching build after upstream releases": a `release_lag_hours` + `release_lag_qualifies` column pair on the existing Phase H join. **No new external source** — Phase H's PyPI JSON fetch already carries `upload_time_iso_8601` per release and currently discards it after extracting `info.version`; the node simply retains it.

Hard constraint, validated the expensive way: a naive `latest_conda_upload − pypi_upload_time` delta is **not** a lag measurement — conda-forge periodically rebuilds long-stable, version-unchanged packages (migrations, ABI/compiler bumps, Python-matrix expansion), so `latest_conda_upload` reflects the *most recent rebuild*, not *first availability*. A naive full-population run produced a false "47% more than 10 days behind" headline; 83.7% of that bucket had a PyPI release itself over a year old. The computation MUST therefore restrict to packages whose upstream release is ≤90 days old (`release_lag_qualifies` — threshold cross-validated live at both a 5,000-package downloads-biased sample and the full 19,726-feedstock population, landing within 1 percentage point of each other). Live baseline the migrated signal should reproduce: **median 8.9 h, 72.4% within 24 h, 83.7% within 72 h**. (§ 5.2 item 4, Story B9.)

### FR-21. Migration-readiness source: conda-forge-bot-data status datasets

The VCS & Health pipeline ingests the data behind `conda-forge.org/status/#migrations` — the `conda-forge/conda-forge-bot-data` repo's `status/` tree:

*   **Category-list datasets** — `status/regular_status.json`, `longterm_status.json`, `closed_status.json`, `paused_status.json` (+ `total_status.json` as the summary) enumerate the active/closed/paused migrations; they drive the partitioning, so the surface generalizes beyond any single hardcoded migration (python314 today, python315 tomorrow — no code change).
*   **Per-migration detail datasets** — `status/migration_json/<name>.json`, partitioned by active migration, carrying the per-feedstock buckets the status page renders: `done`, `in-pr`, `awaiting-pr`, `awaiting-parents`, `not-solvable`, `bot-error`.
*   **A readiness-classification node** joins a migration's detail against the atlas feedstock set and Phase B's `conda_noarch` column, producing a four-way readiness split (noarch / rebuild-done / confirmed-pending / not-in-tracker) and blocker labels; the downloads join (Phase F) yields the top-unmigrated-by-volume ranking. **The `not-in-tracker` bucket is an inference, not tracker data** — feedstocks absent from the migration JSON are *assumed* unmigrated; the classification must label the bucket as such, never present it as confirmed status.

Everything is raw GitHub content fetched via the **existing** `resolve_github_raw_urls` helper — no new `resolve_*_urls` helper, and enterprise/JFrog mirror routing is inherited (§ 3.3 external endpoints). Deliberately excluded: `version_status.v2.json` (the bot's version-update queue) — the atlas measures version currency itself (Phases H/K, `behind-upstream`) and does not mirror the bot's view of the same signal. (§ 5.2 item 4, Story B10.)

---

## 9. User Stories

The implementation waves (0 + A–H) decompose into the stories below. Each wave depends on the prior wave's deliverables. Stories within a wave may proceed in parallel where noted. Within Wave B, stories **B8/B9/B10 are additive new-signal stories, not parity-gated** — Story B4's parity check compares legacy-surface outputs only.

### Wave 0 — Legacy Translation via Skill Forge (SKF)

#### Story 0.1 — Generate legacy contextual skill

**Goal**: Convert the legacy `conda_forge_atlas.py` orchestrator into an `agentskills.io` compliant skill using Skill Forge.

**Acceptance criteria**:
- The SKF module outputs a structured skill repository modeling the legacy logic.
- Developer agents can query this skill for hallucination-free provenance during Wave B.

### Wave A — `nebi` Scaffold & Catalog

#### Story A1 — Scaffold the Kedro + pixi project via `nebi`

**Goal**: Initialize the core project structure and `pixi` ecosystem using `nebi`, sourcing every component from conda-forge.

**Acceptance criteria**:
- A Kedro project skeleton exists, scaffolded by `nebi`.
- `pixi.toml` declares Kedro, Dagster, DuckDB, Ibis (all conda-forge), no standalone binaries / JVM.
- `pixi run` activates the environment cleanly.
- Maps to FR-15.

#### Story A2 — Define the Data Catalog for all sources + outputs

**Goal**: Declare every API source (GitHub, PyPI, Anaconda) and every Parquet output as a Kedro dataset in `conf/base/catalog.yml`.

**Acceptance criteria**:
- All current `_http.py` / `init_schema()` data access is represented declaratively in `catalog.yml`.
- No data-access logic remains inline in (future) node functions.
- Maps to FR-1.

#### Story A3 — Implement `IncrementalParquetDataset` for TTL gating

**Goal**: Encapsulate the `*_fetched_at` TTL incremental logic in a reusable custom dataset class.

**Acceptance criteria**:
- `IncrementalParquetDataset` exists and round-trips TTL state.
- A unit test proves stale rows are re-fetched and fresh rows are skipped.
- Maps to FR-3.

### Wave B — Pipeline Node Porting & MCP Integration

#### Story B1 — Port the conda-side backbone phases into Kedro nodes

**Goal**: Refactor the foundational conda-forge enumeration + graph-building + VCS/health phases (B, B.5, B.6, E, E.5, F, J, K, L, M, N per § 3.3) into Kedro Nodes with declared inputs/outputs, split across the Core and VCS & Health pipelines of § 5.2.

**Acceptance criteria**:
- Each conda-side phase is a pure-function node with explicit inputs/outputs.
- The DAG resolves automatically (no procedural call order).
- Phase B.5's `_pick_feedstock` dedicated-feedstock attribution (§ 3.3 — umbrella vs dedicated for split-out outputs, e.g. `dbt-bigquery`) survives the port; its unit tests carry over as node tests.
- Phase I (per-version download history) becomes an explicit node with declared outputs — no longer an unregistered side-effect of Phase F.
- Maps to FR-2.

Note: Phase B.6 ports with its **lite** semantics (presence-in-repodata → `latest_status`), which is all parity requires. Its deferred full per-version yanked detection has a recorded cheaper candidate path — prefix.dev GraphQL `variants.yankedReason` targeted queries instead of the ~1 GB repodata diff the legacy docstring priced (§ 12 evaluation row). Optional follow-on, not part of this story.

#### Story B2 — Port the PyPI & Vulnerability pipelines

**Goal**: Refactor the PyPI intelligence phases (C, C.5 mapping + D enumeration + H skew detection + O–S scoring per § 5.2, including the shared `phase_r_upsert_one` / `apply_readiness_scores` single-write-path helpers that `add-handoff` reuses) and the vulnerability phases (G / G' — AppThreat VDB / CISA KEV) into their domain pipelines.

**Acceptance criteria**:
- PyPI Intelligence and Vulnerability pipelines exist per § 5.2.
- Each node is independently unit-testable on `pandas.DataFrame` IO.
- The `add-handoff` single-write-path property (§ 3.3 write paths) and the `v_pypi_intelligence_valid` / `v_current_version_vulns` view contracts are preserved.
- The vulnerability read-path contract (§ 3.3) is preserved: the atlas `cisa_kev` KEV overlay (vdb's own KEV flags are unusable) and the `_coerce_cvss_score` ScoreType unwrap survive in the migrated read surface.
- Maps to FR-2.

#### Story B3 — Integrate `kedro-mcp` to re-expose the data surface

**Goal**: Audit the 46 existing MCP tools (23 atlas-relevant, § 3.3) and re-expose datasets + pipeline triggers to Claude Code / BMAD agents via `kedro-mcp`; non-atlas recipe-authoring tools stay on the FastMCP server. Keep `library-futures` / `add-handoff` CLI-only.

**Acceptance criteria**:
- BMAD agents can trigger a named pipeline (e.g., `run_vulnerability_pipeline`) via MCP.
- BMAD agents can read a resulting dataset natively via MCP.
- Maps to FR-7.

#### Story B4 — Verify dataset parity against the legacy orchestrator

**Goal**: Run the Kedro pipeline in parallel with legacy `bootstrap-data` and prove output parity before retiring the legacy path.

**Acceptance criteria**:
- A parity check compares Kedro Parquet outputs against legacy `cf_atlas.db` tables and reports zero material drift.
- Parity evidence is recorded; only then is the legacy orchestrator marked for retirement.

#### Story B5 — Port the external-refresh assets (§ 3.4)

**Goal**: Wrap the three separately-built data stores — `vdb-refresh` (AppThreat vdb, vuln-db env), `update-cve-db` (offline OSV store), and `update-mapping-cache` (`pypi_conda_map.json`) — as scheduled external-refresh assets in their § 5.2 domain pipelines, preserving today's `bootstrap_data.py` orchestration coverage across all three bootstrap profiles (§ 3.3 / `guides/atlas-operations.md` — the consumer profile must keep working air-gapped).

**Acceptance criteria**:
- Each refresh runs as a Dagster-scheduled asset with retries + observability; cadence matches the legacy tasks' TTLs.
- Phases G / G' and `scan-project` offline mode consume the refreshed stores exactly as before — the pipeline never writes them outside the refresh assets.
- The vuln-db environment dependency is a declared resource requirement, not an implicit shell-out.
- Q6's decision is recorded before porting `update-mapping-cache` (consolidation may retire it instead).
- Maps to FR-2, FR-6.

#### Story B6 — Port the Seed-Gaps pipeline

**Goal**: Port the four report-only gap suggesters (`lts-registry-gap`, `cwe-seed-gap`, `spdx-schema-gap`, `license-map-gap`) as the terminal report nodes of the Seed-Gaps Pipeline (§ 5.2 item 6), fanned out from their external seed datasets and downstream of the atlas rebuild.

**Acceptance criteria**:
- Each suggester is a report node reading exactly the inputs in the § 3.4 **Seed-freshness report nodes** table (not the separately-built local-stores table), emitting a `derived`-layer freshness report.
- The nodes are strictly read-only — the byte-identical-seed guarantee (fixture-enforced in the legacy test suite) survives as a pipeline test.
- The pipeline re-runs after every rebuild, alongside the § 5.2 item 7 derived artifacts.
- `mapping-gap` stays in the PyPI Intelligence pipeline with its `g10_spelling` no-clobber writeback (§ 3.3 mapping contract) — it is not a Seed-Gaps node.
- Maps to FR-2.

#### Story B7 — Extend the Universal SBOM intake (resolver, formats, universe BOM, buckets)

**Goal**: Implement the transitive-resolver node, the widened § 4.10 tiered manifest intake, the universe-BOM catalog dataset, and the inventory-match matching node with its shipped bucket semantics (§ 5.2 item 5 + item 7).

**Acceptance criteria**:
- A bare `requirements.txt` resolves to a full transitive dependency set with resolution depth + fan-out recorded.
- Every § 4.10 format normalizes to CycloneDX preserving the `cfe:*` property namespace and the `?channel=conda-forge` qualifier.
- The full-universe CycloneDX BOM is a catalog dataset under the 14-day freshness contract; consumers refuse a stale atlas exactly as the legacy gate does.
- A matching run reproduces the legacy six-bucket classification (ADD / ADD-NONPYPI / UPDATE-FEEDSTOCK / UPDATE-PIN / CURRENT / UNKNOWN) on a fixture inventory.
- Pasted `conda list` / `pip list` text padded with non-breaking spaces parses identically to its ASCII-space form (fixture case — the S5a parsers cover these formats but not this whitespace variant today; § 15 decision log).
- Maps to FR-13, FR-17.

#### Story B8 — Basilisk conda-native vulnerability ingestion

**Goal**: Implement the two Basilisk ingestion nodes (FR-19) in the Vulnerability Pipeline — `POST /v1/querybatch` → `basilisk_vulns` dataset, plus the bounded `GET /v1/vulns/{id}` detail fetch — with the derived tri-state `fix_available` column joined at query time against `behind_upstream`. Record Q7's landing decision (§ 11) before implementation.

**Acceptance criteria**:
- A batch run over the full Python population writes `basilisk_vulns` (`conda_name`, `advisory_id`, `modified`) via `POST /v1/querybatch` at ≤1,000 queries per request.
- Matching is by package name: a fixture proves an advisory whose `affected[]` ecosystem tag reads `PyPI` still matches its conda package (the ecosystem-tag gotcha, FR-19).
- `fix_available` is tri-state: a fixture advisory carrying only an enumerated `versions` list yields `unknown`, never `false`.
- No read surface conflates version currency with security currency — a package can be `current` per `behind-upstream` AND carry a Basilisk advisory (fixture-proven).
- `BASILISK_BASE_URL` routes the endpoint per the mirror-routing convention; offline (consumer profile) the nodes skip gracefully and mark the dataset stale rather than failing.
- Maps to FR-19.

#### Story B9 — Release-to-availability velocity columns

**Goal**: Retain Phase H's per-release `upload_time_iso_8601` and derive `release_lag_hours` + `release_lag_qualifies` (FR-20) on the Phase H join, with the 90-day recency gate.

**Acceptance criteria**:
- The column pair exists on the Phase H join dataset; no new external fetch is introduced.
- The rebuild-cadence guard is fixture-enforced: a version-unchanged package whose upstream release is >90 days old is excluded (`release_lag_qualifies = false`) — the false "47% behind" classification (FR-20) cannot recur.
- A population run reproduces the live baseline shape (median ≈ 9 h, ~72% within 24 h) within reasonable drift, recorded as a calibration reference (not a hard gate).
- Maps to FR-20.

#### Story B10 — Migration-readiness datasets + classification node

**Goal**: Ingest the `conda-forge-bot-data` `status/` category lists and per-migration `migration_json/<name>.json` detail as external datasets (FR-21), partitioned by active migration, and implement the readiness-classification node over the feedstock set + `conda_noarch`.

**Acceptance criteria**:
- The category-list datasets enumerate active migrations and drive the per-migration partitioning — adding a new migration upstream requires no code change.
- For a live migration (python314 at authoring time), the classification node produces the four-way readiness split (noarch / rebuild-done / confirmed-pending / not-in-tracker) and surfaces the per-feedstock blocker buckets (`in-pr`, `awaiting-pr`, `awaiting-parents`, `not-solvable`, `bot-error`).
- The `not-in-tracker` bucket is labeled as inferred, never as confirmed tracker status (fixture-proven in the report output).
- The downloads join yields a top-unmigrated-by-volume ranking.
- All fetches route through `resolve_github_raw_urls` (mirror routing inherited); offline (consumer profile) the nodes skip gracefully and mark the datasets stale rather than failing.
- Maps to FR-21.

### Wave C — Orchestration & Visualization

#### Story C1 — Integrate `kedro-dagster` for scheduling + execution

**Goal**: Compile the Kedro DAG into a Dagster repository; move daily/weekly schedules and retry logic off cron+bash.

**Acceptance criteria**:
- Schedules exist as Dagster Schedules and encode the `guides/atlas-operations.md` cadence table (bootstrap weekly; F/H/K/L/E.5 daily; E/J/M every 6 h; N hourly per maintainer; refresh assets weekly).
- The three bootstrap profiles (maintainer / admin / consumer) exist as named Dagster job configurations with the guide's override precedence (explicit run-config/env beats profile defaults).
- Retries + phase state are observable in the Dagster UI.
- Timeouts are per-node: a cold-run Phase R overrun can no longer abort Phase F/K/N (the legacy 1800 s `cf_atlas_core` defect, § 3.3/FR-6, is demonstrably retired).
- Maps to FR-6.

#### Story C2 — Integrate `kedro-viz` + expose a pixi task

**Goal**: Render the topological DAG via `kedro-viz` and serve it through a dedicated pixi task.

**Acceptance criteria**:
- `pixi run viz` launches the Kedro-Viz server.
- Operators can inspect dataset schemas + data lineage in the browser.

### Wave D — Semantic Layer & Dashboards

#### Story D1 — Define the Boring Semantic Layer (BSL) models

**Goal**: Extract the metrics/business logic from the 28 read CLIs (§ 3.3) into BSL dimensions + measures on top of the Kedro catalog (Ibis → DuckDB).

**Acceptance criteria**:
- BSL declares the core metrics (staleness, adoption stage, feedstock health, …).
- The BSL layer is the single translation interface for downstream consumers.
- Maps to FR-8.

#### Story D2 — Build the Vizro dashboard + port the 28 CLIs to pages

**Goal**: Build a Vizro app driven by the BSL models; reproduce the 28 read CLIs (§ 3.3) as Vizro pages.

**Acceptance criteria**:
- A Vizro dashboard serves the core KPIs currently locked in CLIs.
- Each of the 28 legacy CLI questions is answerable from a Vizro page.
- Maps to FR-9.

#### Story D3 — Integrate Vizro-AI + expose the NL interface as an MCP tool

**Goal**: Add the Vizro-AI natural-language query field and a `query_vizro_ai` MCP tool, both powered by the BSL knowledge graph.

**Acceptance criteria**:
- A natural-language query (e.g., the § 4.3 example) returns a generated chart/insight.
- The `query_vizro_ai` MCP tool is callable from Claude Code.
- Maps to FR-9.

### Wave E — A2A Integration, Lineage & Observability

#### Story E1 — Implement the A2A communication interfaces

**Goal**: Build the Agent-to-Agent surface with structured protocols for data passing between BSL intelligence agents and the conda-forge execution agents.

**Acceptance criteria**:
- The `cf_atlas` analytical agent can hand a structured payload to the `conda-forge-expert` agent (publish/subscribe or direct-message).
- Maps to FR-11.

#### Story E2 — Integrate OpenLineage + OpenTelemetry

**Goal**: Instrument Kedro nodes, Dagster runs, and DuckDB queries with OpenLineage (lineage/metrics) and OpenTelemetry (tracing/logging).

**Acceptance criteria**:
- Lineage + per-node metrics (rows, latency, cache hits) are captured via OpenLineage.
- End-to-end distributed traces are visible via OTel down to specific API calls.
- Maps to FR-12.

### Wave F — The DuckDB Singularity

#### Story F1 — Migrate all datasets to DuckDB-backed partitioned Parquet

**Goal**: Replace SQLite + fragmented compute proposals with DuckDB reading partitioned Parquet natively.

**Acceptance criteria**:
- SQLite is removed; all datasets read/write via DuckDB.
- Cold-start time is materially below the legacy 3–4 h baseline.
- Maps to FR-5.

#### Story F2 — Implement direct Data Validation Hook and inline Pandera checks

**Goal**: Wire Great Expectations validations into a custom Kedro `AfterNodeRunHook` and implement inline `pandera` assertions within nodes.

**Acceptance criteria**:
- A validation failure (e.g., PyPI JSON missing a version field or schema checks failing) halts execution by raising a native Python exception.
- The failure propagates to Dagster, halting the pipeline and raising an A2A alert.
- Maps to FR-10.

#### Story F3 — Implement Vector Similarity Search (RAG) via DuckDB `vss`

**Goal**: Implement RAG embeddings + similarity search using DuckDB's `vss` extension.

**Acceptance criteria**:
- A similarity query over embedded artifacts returns ranked results from DuckDB.
- Maps to FR-5.

#### Story F4 — Dependency-hygiene node + unified CI policy gate

**Goal**: Add the `deptry` hygiene scan node (FR-16) and the converged policy gate (FR-18) as the Universal SBOM pipeline's terminal quality stage, wired into the F2 validation machinery.

**Acceptance criteria**:
- An injected unused-dependency fixture yields a schema-valid hygiene finding in the `ComplianceReport` artifact.
- A policy breach (e.g. `max_critical=0` violated, or a KEV-affecting-current hit) exits with the contract codes (1 policy-fail / 2 error), halts Dagster, and raises an A2A alert — identical failure semantics to an FR-10 contract violation.
- The report schema matches `pyforge-warden.md`'s `ComplianceReport`, so the planned promotion (MCP tool + pixi CLI) requires no schema change.
- Maps to FR-16, FR-18, FR-10.

### Wave G — WebAssembly Portability & Event-Driven Sensors

#### Story G1 — Compile the intelligence layer to Pyodide / DuckDB-WASM

**Goal**: Run the Vizro-AI dashboard + BSL layer locally in the browser via Pyodide / DuckDB-WASM.

**Acceptance criteria**:
- The dashboard loads and queries run client-side in the browser with no backend.
- Maps to FR-14.

#### Story G2 — Emit Parquet artifacts to a static web host

**Goal**: Configure the Kedro pipeline to output Parquet artifacts to a static host (GitHub Pages), pulled via HTTP Range requests.

**Acceptance criteria**:
- Parquet artifacts are published to the static host and consumed by the WASM runtime via HTTP Range.
- Maps to FR-14.

#### Story G3 — Implement Dagster Sensors for near-real-time ingestion

**Goal**: Transition the pipeline to an event-driven state triggered by PyPI/GitHub webhooks (or RSS) via Dagster Sensors.

**Acceptance criteria**:
- A simulated upstream event triggers the relevant pipeline incrementally via a Dagster Sensor.
- Maps to FR-6, § 5.9.

### Wave H — The AI Software Factory & Karpathy Wiki

#### Story H1 — Scaffold the Karpathy Wiki folder structure and Agent Personas
**Goal**: Create the `wiki/raw/`, `wiki/compiled/`, and `wiki/outputs/` directory structure, and define the 5 BMAD personas (Ingester, Compiler, Linker, Linter, Oracle).

#### Story H2 — Implement Agno Compilation, Linting, and Q&A Crews
**Goal**: Write the `agno` Python implementations for the three workflows that compile the raw docs, lint the wiki, and provide Q&A.

#### Story H3 — Integrate La Suite Docs REST API Sync
**Goal**: Implement the `LaSuiteClient` and `WikiSyncer` to push the compiled wiki files from Layer 3 (Agent Workforce) to Layer 1 (Human UI) using the Wagtail/Django REST API.

#### Story H4 — Orchestrate Crews via Dagster
**Goal**: Write Dagster assets, sensors (for new raw files), and schedules (for weekly linting) to trigger the Agno execution workflows autonomously.

---

## 10. Acceptance Criteria (Whole Migration)

- **AC-1.** The Kedro pipeline reproduces the legacy `cf_atlas` outputs with proven dataset parity (Story B4) before the legacy orchestrator is retired.
- **AC-2.** The `phase_state` table and the hand-rolled `*_fetched_at` checks are gone; resumability is provided by Kedro runner + persisted Parquet + `IncrementalParquetDataset`.
- **AC-3.** Dagster owns scheduling + retries; phase state is observable in the Dagster UI; `pixi run viz` renders the DAG.
- **AC-4.** The 28 read CLIs (§ 3.3) are answerable from Vizro pages, plus a Vizro-AI NL field and `query_vizro_ai` MCP tool, all driven by the BSL.
- **AC-5.** MCP + A2A surfaces let BMAD agents trigger pipelines, read datasets, and hand structured payloads to the `conda-forge-expert` agent.
- **AC-6.** Great Expectations contracts halt bad data; OpenLineage + OpenTelemetry provide lineage + end-to-end tracing; the unified policy gate (FR-18) preserves the deptry / `inventory-match --policy` exit-code contract (0/1/2).
- **AC-7.** DuckDB is the single compute/graph/vector engine; cold-start is materially faster than the 3–4 h legacy baseline.
- **AC-8.** The intelligence surface runs in-browser via DuckDB-WASM against statically-hosted Parquet; Dagster Sensors enable near-real-time ingestion.
- **AC-9.** Every component is conda-forge-sourced and pixi-managed (`nebi`-scaffolded); no standalone binaries / JVM.
- **AC-10.** The three new-signal sources are live in the migrated surface: the `basilisk_vulns` dataset (conda-PURL identity axis, tri-state `fix_available`), the release-velocity column pair (90-day-gated), and the migration-readiness datasets + classification (per-migration partitioning, inferred `not-in-tracker` labeling), per FR-19 / FR-20 / FR-21 (Stories B8 / B9 / B10). Together they make the v2 ecosystem-health analysis (§ 15 evidence) reproducible from the pipeline for its Sections 2–6; Section 1's composition-by-language classifier stays deferred per § 12.

---

## 11. Open Questions

Numbering is stable across spec versions (other artifacts cross-reference it);
Q5 was resolved and retired — its outcome (the § 7 AI Software Factory layer
is in scope as Wave H) is stated in the body, not re-asked here.

### Q1 — Dataset-parity tolerance for legacy retirement (gates B4 → legacy retirement)

What counts as "zero material drift" when comparing Kedro Parquet outputs to legacy `cf_atlas.db`? Row-count exactness, or tolerance for ordering / floating-point / timestamp differences?

**Default**: exact row-count + value parity on the actionable views; document any timestamp/ordering-only diffs as benign.

### Q2 — Dagster deployment footprint (gates Wave C)

Does Dagster run as a long-lived local daemon, or only on-demand for scheduled runs? The legacy path was cron+bash. A persistent Dagster daemon adds an always-on process to the operator's machine.

**Default**: on-demand / scheduled invocation locally; revisit a persistent daemon only if Sensors (Wave G) require it.

### Q3 — Vizro-AI LLM backend (gates D3)

Which model backend powers Vizro-AI's NL→pandas compilation, and does it respect the repo's enterprise / air-gapped routing (JFrog, internal mirrors) per `_http.py`?

**Default**: route through the existing repo model-backend configuration; do not hardcode a public LLM endpoint.

### Q4 — WASM artifact-store hosting (gates G2)

Is GitHub Pages the committed static host for Parquet artifacts, or should this support an enterprise/JFrog-mirrored static store for air-gapped consumers?

**Default**: GitHub Pages for the public path; keep the artifact emitter host-agnostic so an enterprise mirror can be substituted.

### Q6 — Consolidate the dual PyPI↔conda mapping sources (gates Story B5's mapping asset)

The skill maintains two mapping surfaces: atlas Phase C (DB-resident parselmouth join, extended by C.5 and the `mapping-gap` g10_spelling writeback) and the flat `pypi_conda_map.json` cache (`update-mapping-cache`; read by `name_resolver.py` / `recipe-generator.py` at authoring time; sourced from regro/cf-graph + the conda-forge-metadata API — § 3.4). Should the migration port the flat cache as-is, or retire it by pointing the authoring-side consumers at the migrated Phase C dataset?

**Default**: consolidate — make the migrated Phase C mapping (DuckDB) the single source and re-point `name_resolver.py` / `recipe-generator.py` at it; keep the flat-cache refresh only if authoring-time reads prove to need a standalone file artifact (offline / no-DB contexts). Whatever the decision, the `g10_spelling` provenance tier and the no-clobber writeback rule (§ 3.3 mapping contract) must survive.

### Q7 — Basilisk landing point: Kedro-native only, or an interim legacy Phase U (gates Story B8)

FR-19 can land either exclusively as Kedro Vulnerability-Pipeline nodes (this migration, Story B8), or first as a legacy-orchestrator **Phase U** (the next letter after trendshift's Phase T, claiming the schema bump after its v30) if conda-native vulnerability coverage is wanted before Wave B completes.

**Default**: build once, as Kedro nodes in Wave B — avoid a double implementation. Pull a legacy Phase U forward only if the trendshift effort's timeline leaves a pre-migration window long enough for the interim coverage to matter; if that happens, the Phase U port then folds into Story B8 like every other § 3.3 phase.

---

## 12. Out of Scope

The following are deliberately excluded from this migration, with reason:

| Item | Reason |
|---|---|
| Neo4j / Kùzu / LanceDB / Polars as separate engines | Superseded by the DuckDB Singularity (§ 4.8); DuckDB handles compute + graph + vector in one engine. |
| Continued SQLite + `phase_state` orchestration | Replaced by Kedro + Dagster + DuckDB (FR-4, FR-5, FR-6). |
| `spec-kit` as the agent framework | Explicitly rejected (§ 7.3); `bmad-method` governs the agent workforce. |
| Standalone binaries / JVM dependencies | Pixi-first, conda-forge-only constraint (FR-15, § 4.9). |
| Enterprise Python Manifest (5k) generation as a deliverable | Downstream target state (§ 4.11) the graph *enables*; not built in this migration. |
| New external data sources beyond the committed set | The committed source set is: the legacy GitHub/PyPI/Anaconda set (already including endoflife.date, osv.dev, and the local deptry / osv-scanner toolchain — § 3.3 / § 3.4), plus `api.basilisk.prefix.dev` (FR-19) and the `conda-forge/conda-forge-bot-data` `status/` datasets (FR-21). Anything beyond that set is out of scope. |
| prefix.dev GraphQL API (`prefix.dev/api/graphql`) as an additional metadata backend | Evaluated 2026-07-16, not promoted: no vulnerability types (Basilisk REST is the FR-19 surface); package/variant metadata duplicates repodata, which the atlas already sources with `repo.prefix.dev` as its first public mirror; the per-package query model is unfit for bulk enumeration vs one repodata fetch. **Recorded future hook**: `variants.yankedReason` gives per-version yanked status + reason via targeted no-auth queries — the cheap candidate path for Phase B.6's deferred full yanked detection (legacy alternative: ~1 GB patched-vs-unpatched repodata diff). See the Story B1 note. |
| Ecosystem-composition-by-language report | A channel-health *report* concern, not migration surface (deferred from the 2026-07-16 live analysis; candidate for a future feedstock-health / Vizro page). Measured facts preserved for whoever builds it: the atlas's cross-ecosystem columns (`npm_name`, `cran_name`, `cpan_name`, `luarocks_name`, `maven_coord`) are almost entirely unpopulated at scale (136 of 11,602 non-Python packages matched `npm_name`; 0 for CRAN/CPAN) — an accurate composition report must key on conda-forge naming-convention prefixes instead (`r-*` alone is 11.6% of the entire channel, the real second-largest ecosystem). |
| Spreadsheet (`.ods`/`.xlsx`) tabs and GitHub Projects boards as SBOM-intake formats | Analysis-prep conveniences, not manifests; export to any § 4.10 supported format instead. |
| `pyforge.warden` v1 standalone build (`docs/specs/pyforge-warden.md`) | Built under its own spec as an internal-first library. This migration models only the *promoted* atlas surface (FR-16 / FR-18) — the hygiene node contract matches its `ComplianceReport` schema so consolidation with `scan-project` lands as wiring, not redesign. |
| Rewriting the conda-forge recipe-authoring skill itself | This migration touches the `cf_atlas` intelligence layer, not the recipe-authoring loop. |
| Static seeds + recipe template trees as pipeline *products* | Curated inputs (§ 3.4); the catalog declares them as versioned external datasets — the pipeline reads, never generates, them. |
| Live authoring-time fetches (recipe-generator PyPI/sha256 pulls, `gh`/Azure DevOps, live channel repodata) | Transactional point-in-time operations of the recipe-authoring loop (§ 3.4); not pipeline data and not schedulable. |

---

## 13. References

### Internal

- `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py` + `bootstrap_data.py` — the legacy orchestrator being migrated.
- `.claude/tools/conda_forge_server.py` — the FastMCP server whose tools are ported via `kedro-mcp` (FR-7).
- `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md` — phase-indexed map of the current pipeline (source for § 5.2 pipeline decomposition).
- `.claude/skills/conda-forge-expert/reference/atlas-phase-engineering.md` — engineering patterns (rate limits, atomic writes, enterprise routing) that constrain the node ports.
- `.claude/skills/conda-forge-expert/guides/atlas-operations.md` — the current operational process (bootstrap profiles, cron cadence table, recovery playbook, storage budget) that § 5.4 / FR-6 must reproduce.
- `docs/specs/cfe-shipped-releases.md` Part 8 — the S3/parquet backend (Phase F Waves 1–3) whose datasets become Kedro catalog entries (§ 5.1).
- `docs/specs/cyclonedx-universe-inventory.md` (shipped) — the 7-CLI suite, purl conventions, freshness gate, and bucket semantics FR-13/FR-17 preserve.
- `docs/specs/pyforge-warden.md` (in-progress) — the `pyforge.warden` v1 build whose `ComplianceReport` schema + exit-code gate FR-16/FR-18 anticipate.
- `CLAUDE.md` § "BMAD ↔ conda-forge-expert integration" — Rule 1 + Rule 2 governing this BMAD effort.

### External / ecosystem

- Kedro + `kedro-viz` + `kedro-dagster` + `kedro-mcp` plugins (all managed via Pixi/conda-forge per FR-15).
- Great Expectations + Pandera (for native data quality validation).
- DuckDB (+ `vss` extension), Ibis, Boring Semantic Layer.
- Vizro + Vizro-AI.
- Dagster (+ Sensors), OpenLineage, OpenTelemetry.
- `nebi` (nebari-dev) for project scaffolding.
- CycloneDX SBOM specification; `cdxgen`.
- `deptry` + `osv-scanner` (conda-native: `recipes/deptry`, the `recipes/osv-scanner` mirror; `fawltydeps` / `pip-check-reqs` as ecosystem context) — the FR-16/FR-18 hygiene + gate toolchain.
- `api.basilisk.prefix.dev` — the OSV-compatible, conda-native vulnerability API (FR-19); conda PURLs per CEP 63.
- `conda-forge/conda-forge-bot-data` `status/` tree — category lists (`regular_status.json` / `longterm_status.json` / `closed_status.json` / `paused_status.json` / `total_status.json`) + per-migration `migration_json/<name>.json`; the data behind `conda-forge.org/status/#migrations` (FR-21).
- prefix.dev GraphQL API (`prefix.dev/api/graphql` — public queries, no auth) — evaluated, not promoted (§ 12); recorded hook: `variants.yankedReason` for Phase B.6's deferred full yanked detection.

---

## 14. Suggested BMAD Invocation

**Phase 1: Tier-2 Planning**
```
@bmad-create-prd — use docs/specs/cfe-atlas-datapipeline-kedro-migration.md
@bmad-create-architecture
@bmad-create-epics-and-stories
```

**Phase 2: Execution via BAD**
```
npx bmad-method install --modules bmm,tea,cis

# Let BAD orchestrate the generated stories in parallel git worktrees:
bmad run bad-pipeline

Wave 0 first (0.1 SKF legacy translation).
Then Wave A (A1 nebi scaffold → A2 catalog → A3 IncrementalParquetDataset).
Then Wave B (B1/B2 node ports → B3 kedro-mcp → B4 parity check → B5
external-refresh assets (resolve Q6 first) → B6 seed-gaps pipeline →
B7 SBOM intake extensions → B8 Basilisk ingestion (resolve Q7 first) →
B9 release-velocity columns → B10 migration-readiness datasets —
B8/B9/B10 are additive new-signal stories, not parity-gated. Do NOT retire
the legacy orchestrator until B4 proves parity per Q1's default).

Proceed wave by wave using the BAD execution engine (C orchestration+viz,
D semantic layer+dashboards, E A2A+observability, F DuckDB singularity
incl. F4 hygiene+policy gate, G WASM+sensors, H AI Software Factory).
Resolve Q2/Q3/Q4 at the start of their gating wave; default to the
recommendations in § 11.

Note: the kedro-viz prototype (prototypes/cf-atlas-kedro-viz) predates the
seven-pipeline decomposition and the FR-16..FR-21 nodes — refresh it as a
follow-up, not as part of this spec's execution.

Per CLAUDE.md Rule 1, the BAD Linker subagents must invoke the conda-forge-expert skill for any work that touches recipe code or atlas tooling. Per Rule 2, close with a CFE-skill retro + CHANGELOG entry.
```

---

## 15. Provenance & Decision Log

This spec is a **v5 clean reset** (2026-07-16). The layered v1–v4.1 document —
with its per-refresh sync-chain annotations — lives in this file's git
history; everything binding from it is integrated into the body above. The
compact decision log:

| Date | Decision |
|---|---|
| 2026-06-20 | v1 authored (Kedro/Dagster/DuckDB migration, waves 0 + A–G; § 7 factory layer as open question). |
| 2026-07-02…-06 | cyclonedx-universe-inventory shipped; its surface (7-CLI suite, purl conventions, freshness gate, bucket semantics) folded in as preserved contracts; § 5.2 grew to seven pipelines; stories B6/B7/F4 + FR-16/17/18 added; Q5 resolved → the AI Software Factory is in scope as Wave H. |
| 2026-07-10 | v3 re-grounding (main `de5462d`, skill v8.76.0): Phase I cataloged; `atlas-operations.md` operational ground truth adopted into § 5.4/FR-6 (profiles, cadence table, the 1800 s `cf_atlas_core` defect as FR-6's motivating failure); seed-gap suggesters + pyforge-warden cross-intake. |
| 2026-07-16 | v4: live-analytics gating — **FR-19** (Basilisk) + **FR-20** (release velocity) promoted with Stories B8/B9 + Q7; ecosystem-composition report deferred (§ 12); manifest parsing found already covered (S5a) except the NBSP paste variant → Story B7 AC. Re-grounded on main `58a6dcc` / skill v8.78.0. |
| 2026-07-16 | v4.1: reproducibility audit of the v2 report → **FR-21** (conda-forge-bot-data migration-status datasets) + Story B10. |
| 2026-07-16 | prefix.dev GraphQL API evaluated, not promoted (§ 12 row; `yankedReason` hook noted on Story B1). |
| 2026-07-16 | **v5 reset**: this clean re-authoring. No scope change — FR/story/AC/Q numbering preserved. |

**Evidence** (live, multi-stage ecosystem analysis backing FR-19/FR-20/FR-21
and the § 12 deferrals; every number measured against the live atlas + live
external APIs):

- `gist.github.com/rxm7706/76eb84093c3408b26ed6156b037c6d80` (v1)
- `gist.github.com/rxm7706/73db2b7ab8935f95ea6e549ed994c778` (v2, adds Basilisk — the report whose Sections 2–6 AC-10 makes pipeline-reproducible)
