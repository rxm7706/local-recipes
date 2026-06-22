---
doc_type: spec
part_id: cf-atlas-datapipeline
display_name: cfe-atlas-datapipeline Kedro Migration Spec
project_type_id: data
date: 2026-06-20
status: ready
spec_updated: 2026-06-20
---

# Spec: cfe-atlas-datapipeline Kedro Migration

> **BMAD intake document.** Written for full BMAD execution (Full Flow
> track — data-platform migration effort). 7 implementation waves
> (A–G) decomposed into the User Stories in § 9. Run BMAD with this
> file as the intent document:
>
> ```
> run bmad — implement the intent in docs/specs/cfe-atlas-datapipeline-kedro-migration.md
> ```

---

## 1. Status

| Field | Value |
|---|---|
| Status | **Draft v1 — ready for full BMAD execution intake.** 5 open questions (§ 11), none v1-blocking. |
| Owner | rxm7706 |
| Track | BMAD Full Flow (includes separate PRD/architecture phases) |
| Scope | Migrate the hand-rolled `cf_atlas` orchestrator (`conda_forge_atlas.py` + `bootstrap_data.py`, ~4,300 LOC, 22 phases) to a Kedro pipeline + Dagster orchestration + DuckDB compute, with a Vizro/Vizro-AI read surface and a Boring-Semantic-Layer + MCP/A2A agent interface. |
| Target | The `cf_atlas` intelligence layer under `.claude/skills/conda-forge-expert/` (data pipeline + read CLIs + MCP tools). |
| Tooling | Pixi-first; every component sourced from conda-forge and scaffolded via `nebi`. |
| Lifetime | Forward-looking migration. Legacy orchestrator runs in parallel until dataset parity is proven (Wave B), then is retired. |
| Predecessor | The existing 15-phase `cf_atlas` pipeline (B → N + O–S) and its 16 read CLIs (`staleness-report`, `behind-upstream`, …). |

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
*   **Skill Forge (SKF)**: For translating the ~4,300 lines of legacy code into an ingestible agent context skill (Wave 0) with provable provenance.
*   **Creative Intelligence Suite (CIS)**: Utilizing the CIS planning agents (e.g., Carson the Brainstorming Coach and Maya the Design Thinking Coach) to explicitly define the downstream read surface (Vizro/Vizro-AI) and output the two-spine technical specs (`DESIGN.md` + `EXPERIENCE.md`) before writing frontend code.

### 2.5 BAD (BMAD Autonomous Development) Orchestration

To achieve true parallel execution across our 7 implementation waves, we execute this spec using the **BAD** module. BAD orchestrates multiple isolated git worktrees simultaneously, enforcing the following toolchain and skill pipeline:

*   **Prerequisite Modules**: Installed via `npx bmad-method install --modules bmm,tea,cis`.
*   **Tier-2 Planning Skills**: `@bmad-create-prd`, `@bmad-create-architecture`, and `@bmad-create-epics-and-stories`.
*   **Tier-3 Execution Skills**: BAD loops through the 7-step pipeline per story using:
    1. `@bmad-create-story`
    2. `@bmad-testarch-atdd` (TEA)
    3. `@bmad-dev-story` (Linker)
    4. `@bmad-testarch-test-review` (TEA)
    5. `@bmad-code-review` (Linter)

---

## 3. Deep Analysis: Current cf_atlas Pipeline

The `cf_atlas` data pipeline currently operates as a bespoke, hand-rolled orchestrator (`conda_forge_atlas.py` + `bootstrap_data.py`) spanning ~4,300 lines of code.

### 3.1 Current Architecture & Constraints

*   **Orchestration**: 22 hardcoded phases (B through N, plus O-S PyPI intelligence) executing in procedural order.
*   **State Management**: Custom checkpointing via a `phase_state` SQLite table (tracking cursors and completion).
*   **Incremental Processing**: Hand-rolled TTL gating using `*_fetched_at` timestamps on the primary `packages` table.
*   **Data Lineage**: Implicit. Dependencies between phases (e.g., Phase J requiring D and E) exist purely in the developer's head and the procedural calling order.
*   **Read Surface**: 16 bespoke CLIs (e.g., `staleness-report`, `behind-upstream`) that output text/JSON and require manual maintenance.
*   **Visualization**: None. The system relies entirely on terminal stdout/stderr for observability.

### 3.2 Identified Gaps

*   **Maintainability bottleneck**: Adding a new phase requires manually wiring it into the `PHASES` registry, ensuring the SQL schema is migrated, and updating the orchestrator loop.
*   **Opaque Execution**: When `--fresh` takes 3-4 hours, operators have no visual way to monitor the DAG, identify bottlenecks, or view intermediate dataset schemas.
*   **Rigid Read Surface**: The 16 CLIs answer 16 specific questions. Ad-hoc questions require dropping into `sqlite3 cf_atlas.db` and writing manual JOINs.

---

## 4. Review & Optimization Strategy

To resolve these bottlenecks, we propose migrating the custom orchestrator to **Kedro**, an open-source framework for building reproducible, maintainable, and modular data science code.

### 4.1 Why Kedro?

*   **Data Catalog (`catalog.yml`)**: Decouples data access from logic. S3 parquet files, APIs, and SQLite tables become declaratively configured datasets.
*   **Modular Pipelines**: Transforms the 22 monolithic functions into explicit Nodes with declared inputs and outputs, automatically resolving the execution DAG.
*   **Testability**: Nodes become pure Python functions testing `pandas.DataFrame` inputs/outputs, making unit testing trivial compared to mocking SQLite connections.

### 4.2 Why Kedro-Viz?

*   Provides an interactive, auto-generated visual representation of the `cf_atlas` DAG.
*   Allows operators to monitor real-time execution state, inspect dataset schemas (e.g., what exactly does Phase G' look like?), and track data lineage across the pipeline.

### 4.3 Why Vizro & Vizro-AI?

*   Replaces the 16 bespoke terminal CLIs with a high-quality, web-based dashboard application built explicitly for AI web agents (semantic DOM).
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
*   It will natively parse `pixi.toml`, `pixi.lock`, `pyproject.toml`, `recipe.yaml`, and `meta.yaml` files and normalize them strictly into the **CycloneDX** standard format.
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

The legacy phases will be refactored into domain-specific pipelines:

1.  **Core Pipeline**: Foundational conda-forge enumeration and graph building.
2.  **PyPI Intelligence Pipeline**: PyPI mapping, skew detection, and scoring.
3.  **Vulnerability Pipeline**: AppThreat VDB and CISA KEV ingestion and overlay.
4.  **VCS & Health Pipeline**: GitHub/GitLab live queries and upstream version tracking.
5.  **Universal SBOM Pipeline**: A dedicated pipeline utilizing native parsers and tools (e.g., `cdxgen`) to extract dependencies from `pixi.toml`, `pixi.lock`, `pyproject.toml`, `recipe.yaml`, and `meta.yaml`. These manifests will be strictly normalized into the **CycloneDX** specification before being written to DuckDB Parquet datasets.

### 5.3 Checkpointing & Idempotency

*   Remove the `phase_state` table.
*   Utilize Kedro's native `runner` capabilities and persistent intermediate Parquet datasets to achieve resumability.

### 5.4 Dagster Orchestration (`kedro-dagster`)

*   The entire Kedro pipeline will be converted into a Dagster repository using the `kedro-dagster` plugin.
*   Schedules (Daily for Phase N, Weekly for Phase F/G, etc.) will be defined as Dagster Schedules.
*   Phase states and retries will be monitored via the Dagit/Dagster UI, complementing the structural view provided by `kedro-viz`.

### 5.5 MCP Exfiltration (`kedro-mcp`)

*   The existing 19 MCP tools hosted in `.claude/tools/conda_forge_server.py` will be audited and ported.
*   `kedro-mcp` will expose datasets and pipeline triggers to Claude Code.
*   BMAD Agents will trigger specific pipelines (e.g., `run_vulnerability_pipeline`) and read the resulting datasets natively via MCP.

### 5.6 Semantic Knowledge Graph (Boring Semantic Layer)

*   We will implement the **Boring Semantic Layer (BSL)** on top of the Kedro Parquet datasets using Ibis (which natively compiles to DuckDB SQL).
*   The schema and business logic currently trapped inside the 16 query CLIs will be extracted and declared as BSL dimensions and measures.
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

To seamlessly merge our `cf_atlas` data layer with the enterprise's overarching autonomous goals, the system maps perfectly onto the **4-Layer AI Software Factory Blueprint**.

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

The 22 legacy procedural phases become Kedro Nodes with declared inputs/outputs grouped into the five domain pipelines of § 5.2. Execution order is resolved by Kedro from the DAG, not by procedural call order. (§ 4.1, § 5.2.)

### FR-3. Custom `IncrementalParquetDataset` preserves TTL gating

The `*_fetched_at` TTL incremental-processing semantics are encapsulated in a reusable dataset class, replacing the hand-rolled timestamp checks. (§ 5.1.)

### FR-4. `phase_state` table removed; resumability via Kedro runner + persisted Parquet

Checkpointing is achieved through Kedro's native runner and persistent intermediate Parquet datasets. The bespoke `phase_state` SQLite table is deleted. (§ 5.3.)

### FR-5. DuckDB replaces SQLite + all fragmented compute proposals

DuckDB is the single engine for analytical compute, graph traversal (recursive CTEs), and vector search (`vss` extension), reading partitioned Parquet natively. (§ 4.8, Wave F.)

### FR-6. Dagster orchestrates schedules + retries via `kedro-dagster`

The Kedro DAG compiles to a Dagster repository. Daily/weekly schedules and retry logic move from cron+bash to Dagster Schedules; state is observable in the Dagster UI. (§ 4.4, § 5.4.)

### FR-7. MCP surface preserved via `kedro-mcp`

The existing MCP tools in `.claude/tools/conda_forge_server.py` are audited and ported so BMAD agents retain pipeline-trigger + dataset-read access via MCP. (§ 4.5, § 5.5.)

### FR-8. Boring Semantic Layer over the Kedro catalog (Ibis → DuckDB)

The metrics and business logic currently embedded in the 16 read CLIs are declared as BSL dimensions and measures, serving as the trusted translation layer for Vizro-AI and agents. (§ 4.6, § 5.6.)

### FR-9. Read surface migrates from 16 CLIs to a Vizro / Vizro-AI dashboard

The 16 bespoke CLIs become Vizro pages + a Vizro-AI natural-language query field, exposed both as a web dashboard and as an MCP tool. (§ 4.3, § 6.)

### FR-10. Data-quality contracts via Great Expectations halt bad data

Great Expectations contracts are wired into Kedro nodes; Dagster halts on contract violation and raises an A2A alert before bad data is persisted. (§ 4.8, § 5.8.)

### FR-11. A2A interface for inter-agent collaboration

A dedicated Agent-to-Agent surface lets the `cf_atlas` analytical agent exchange structured payloads with the `conda-forge-expert` recipe-authoring agent. (§ 4.7, § 5.7.)

### FR-12. Lineage + observability via OpenLineage + OpenTelemetry

Kedro nodes, Dagster runs, and DuckDB queries are instrumented with OpenLineage (lineage/metrics) and OpenTelemetry (distributed tracing/logging). (§ 5.9.)

### FR-13. Universal SBOM ingestion normalized to CycloneDX

A dedicated SBOM pipeline parses `pixi.toml`, `pixi.lock`, `pyproject.toml`, `recipe.yaml`, and `meta.yaml`, normalizing to CycloneDX before writing to DuckDB. (§ 4.10, § 5.2.)

### FR-14. WASM portability for the intelligence surface

The Vizro-AI dashboard and BSL layer compile to `duckdb-wasm`/Pyodide; Parquet artifacts are served from a static host (GitHub Pages) and pulled via HTTP Range requests with zero backend. (§ 4.9, Wave G.)

### FR-15. Pixi-first, nebi-scaffolded toolchain (conda-forge only)

Every component (Kedro, Dagster, DuckDB, Ibis, …) is sourced from conda-forge and managed in a single `pixi.toml`, scaffolded by `nebi`. No standalone binaries or JVM. (§ 2.3, § 4.9.)

---

## 9. User Stories

The implementation waves (0 + A–G) decompose into the stories below. Each wave depends on the prior wave's deliverables. Stories within a wave may proceed in parallel where noted.

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

#### Story B1 — Port the Core Pipeline (phases B–M) into Kedro nodes

**Goal**: Refactor the foundational conda-forge enumeration + graph-building phases into Kedro Nodes with declared inputs/outputs.

**Acceptance criteria**:
- Each phase B–M is a pure-function node with explicit inputs/outputs.
- The DAG resolves automatically (no procedural call order).
- Maps to FR-2.

#### Story B2 — Port the PyPI & Vulnerability pipelines

**Goal**: Refactor the PyPI intelligence (O–S) and vulnerability (AppThreat VDB / CISA KEV) phases into their domain pipelines.

**Acceptance criteria**:
- PyPI Intelligence and Vulnerability pipelines exist per § 5.2.
- Each node is independently unit-testable on `pandas.DataFrame` IO.
- Maps to FR-2.

#### Story B3 — Integrate `kedro-mcp` to re-expose the data surface

**Goal**: Audit the 19 existing MCP tools and re-expose datasets + pipeline triggers to Claude Code / BMAD agents via `kedro-mcp`.

**Acceptance criteria**:
- BMAD agents can trigger a named pipeline (e.g., `run_vulnerability_pipeline`) via MCP.
- BMAD agents can read a resulting dataset natively via MCP.
- Maps to FR-7.

#### Story B4 — Verify dataset parity against the legacy orchestrator

**Goal**: Run the Kedro pipeline in parallel with legacy `bootstrap-data` and prove output parity before retiring the legacy path.

**Acceptance criteria**:
- A parity check compares Kedro Parquet outputs against legacy `cf_atlas.db` tables and reports zero material drift.
- Parity evidence is recorded; only then is the legacy orchestrator marked for retirement.

### Wave C — Orchestration & Visualization

#### Story C1 — Integrate `kedro-dagster` for scheduling + execution

**Goal**: Compile the Kedro DAG into a Dagster repository; move daily/weekly schedules and retry logic off cron+bash.

**Acceptance criteria**:
- Schedules (daily Phase N, weekly Phase F/G, …) exist as Dagster Schedules.
- Retries + phase state are observable in the Dagster UI.
- Maps to FR-6.

#### Story C2 — Integrate `kedro-viz` + expose a pixi task

**Goal**: Render the topological DAG via `kedro-viz` and serve it through a dedicated pixi task.

**Acceptance criteria**:
- `pixi run viz` launches the Kedro-Viz server.
- Operators can inspect dataset schemas + data lineage in the browser.

### Wave D — Semantic Layer & Dashboards

#### Story D1 — Define the Boring Semantic Layer (BSL) models

**Goal**: Extract the metrics/business logic from the 16 CLIs into BSL dimensions + measures on top of the Kedro catalog (Ibis → DuckDB).

**Acceptance criteria**:
- BSL declares the core metrics (staleness, adoption stage, feedstock health, …).
- The BSL layer is the single translation interface for downstream consumers.
- Maps to FR-8.

#### Story D2 — Build the Vizro dashboard + port the 16 CLIs to pages

**Goal**: Build a Vizro app driven by the BSL models; reproduce the 16 CLIs as Vizro pages.

**Acceptance criteria**:
- A Vizro dashboard serves the core KPIs currently locked in CLIs.
- Each of the 16 legacy CLI questions is answerable from a Vizro page.
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
- **AC-4.** The 16 read CLIs are answerable from Vizro pages, plus a Vizro-AI NL field and `query_vizro_ai` MCP tool, all driven by the BSL.
- **AC-5.** MCP + A2A surfaces let BMAD agents trigger pipelines, read datasets, and hand structured payloads to the `conda-forge-expert` agent.
- **AC-6.** Great Expectations contracts halt bad data; OpenLineage + OpenTelemetry provide lineage + end-to-end tracing.
- **AC-7.** DuckDB is the single compute/graph/vector engine; cold-start is materially faster than the 3–4 h legacy baseline.
- **AC-8.** The intelligence surface runs in-browser via DuckDB-WASM against statically-hosted Parquet; Dagster Sensors enable near-real-time ingestion.
- **AC-9.** Every component is conda-forge-sourced and pixi-managed (`nebi`-scaffolded); no standalone binaries / JVM.

---

## 11. Open Questions

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

### Q5 — Scope of the AI Software Factory layer (§ 7) in this migration

§ 7 (LA SUITE DOCS / Wagtail CMS / Karpathy Wiki) describes a broader factory blueprint. Is the Wagtail/CMS knowledge-base layer in scope for *this* migration, or a follow-on effort once the Kedro+Dagster+DuckDB core lands?

**Resolution**: The Unity Knowledge Stack / AI Software Factory architecture (Wagtail CMS, Agno, Dagster, Karpathy Wiki) is explicitly **IN SCOPE** and must be delivered as Wave H.

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
| New external data sources beyond the current GitHub/PyPI/Anaconda set | Migration preserves the existing source set; new sources are out of scope. |
| Rewriting the conda-forge recipe-authoring skill itself | This migration touches the `cf_atlas` intelligence layer, not the recipe-authoring loop. |

---

## 13. References

### Internal

- `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py` + `bootstrap_data.py` — the legacy orchestrator being migrated.
- `.claude/tools/conda_forge_server.py` — the FastMCP server whose tools are ported via `kedro-mcp` (FR-7).
- `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md` — phase-indexed map of the current pipeline (source for § 5.2 pipeline decomposition).
- `.claude/skills/conda-forge-expert/reference/atlas-phase-engineering.md` — engineering patterns (rate limits, atomic writes, enterprise routing) that constrain the node ports.
- `docs/specs/atlas-phase-f-s3-backend.md` — the S3/parquet backend whose datasets become Kedro catalog entries (§ 5.1).
- `CLAUDE.md` § "BMAD ↔ conda-forge-expert integration" — Rule 1 + Rule 2 governing this BMAD effort.

### External / ecosystem

- Kedro + `kedro-viz` + `kedro-dagster` + `kedro-mcp` plugins (all managed via Pixi/conda-forge per FR-15).
- Great Expectations + Pandera (for native data quality validation).
- DuckDB (+ `vss` extension), Ibis, Boring Semantic Layer.
- Vizro + Vizro-AI.
- Dagster (+ Sensors), OpenLineage, OpenTelemetry.
- `nebi` (nebari-dev) for project scaffolding.
- CycloneDX SBOM specification; `cdxgen`.

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
Then Wave B (B1/B2 node ports → B3 kedro-mcp → B4 parity check — do NOT retire
the legacy orchestrator until B4 proves parity per Q1's default).

Proceed wave by wave using the BAD execution engine (C orchestration+viz, D semantic layer+dashboards,
E A2A+observability, F DuckDB singularity, G WASM+sensors, H AI Software Factory). Resolve Q2/Q3/Q4
at the start of their gating wave; default to the recommendations in § 11.

Per CLAUDE.md Rule 1, the BAD Linker subagents must invoke the conda-forge-expert skill for any work that touches recipe code or atlas tooling. Per Rule 2, close with a CFE-skill retro + CHANGELOG entry.
```
