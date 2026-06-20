---
doc_type: spec
part_id: cf-atlas
display_name: cf_atlas Kedro Migration Spec
project_type_id: data
date: 2026-06-20
---

# Spec: cf_atlas Kedro Migration

## 1. Operational Philosophy & Platform Ecosystem

Before detailing the architectural migration of `cf_atlas`, all implementations must strictly adhere to our universal operational guidelines:

### 1.1 Build for Autonomous AI Agents
Every system, interface, and dataset we produce must be inherently legible to, and controllable by, machine intelligence.
*   **Web Agents**: Any visualization or dashboard (e.g., Vizro-AI) must use pristine semantic HTML, clear ARIA attributes, and deterministic layouts to ensure scraper and browser agents can navigate without hallucinating.
*   **Agent Workflows**: APIs must be self-documenting (OpenAPI/Swagger) and **idempotent first** so agents can safely retry network requests. Error messages must be hyper-clear to allow LLMs to auto-diagnose.
*   **The Agent Harness**: We implement strict schema validation guardrails to catch erratic agent behavior and maintain exhaustive run-trace histories for absolute context state management.

### 1.2 Spec-Driven Development & Agent Workforce (The 5 Personas)
We do not build or analyze on a whim. This migration is executed under the **BMAD Universal Workflow (v6.8.0 Framework)**. Work is systematically processed through an explicit agent team ecosystem consisting of five distinct personas:
1.  **Ingester (Analyst)**: Reads the incoming raw Parquet data or payloads.
2.  **Compiler (Architect)**: Transforms raw data into structured concepts via BSL.
3.  **Linker (Developer)**: Connects nodes (packages, CVEs, feedstocks) within the graph.
4.  **Linter (QA/Reviewer)**: Validates constraints and handles scheduled weekly reviews.
5.  **Oracle (Product Owner)**: Acts as the primary interface for external queries and strategic tools.

### 1.3 Pixi-First Platform Tooling
To support this operational model, our entire platform ecosystem is defined in `pixi.toml` and managed by `nebi`. We strictly leverage:
*   `bmad-method` (>=6.8.0) for the agent-driven framework.
*   `gh` for automated delivery review and PR creation.
*   `nebi` for ecosystem orchestration and environment scaffolding.

---

## 2. Deep Analysis: Current cf_atlas Pipeline

The `cf_atlas` data pipeline currently operates as a bespoke, hand-rolled orchestrator (`conda_forge_atlas.py` + `bootstrap_data.py`) spanning ~4,300 lines of code.

### 1.1 Current Architecture & Constraints
*   **Orchestration**: 22 hardcoded phases (B through N, plus O-S PyPI intelligence) executing in procedural order.
*   **State Management**: Custom checkpointing via a `phase_state` SQLite table (tracking cursors and completion).
*   **Incremental Processing**: Hand-rolled TTL gating using `*_fetched_at` timestamps on the primary `packages` table.
*   **Data Lineage**: Implicit. Dependencies between phases (e.g., Phase J requiring D and E) exist purely in the developer's head and the procedural calling order.
*   **Read Surface**: 16 bespoke CLIs (e.g., `staleness-report`, `behind-upstream`) that output text/JSON and require manual maintenance.
*   **Visualization**: None. The system relies entirely on terminal stdout/stderr for observability.

### 1.2 Identified Gaps
*   **Maintainability bottleneck**: Adding a new phase requires manually wiring it into the `PHASES` registry, ensuring the SQL schema is migrated, and updating the orchestrator loop.
*   **Opaque Execution**: When `--fresh` takes 3-4 hours, operators have no visual way to monitor the DAG, identify bottlenecks, or view intermediate dataset schemas.
*   **Rigid Read Surface**: The 16 CLIs answer 16 specific questions. Ad-hoc questions require dropping into `sqlite3 cf_atlas.db` and writing manual JOINs.

---

## 3. Review & Optimization Strategy

To resolve these bottlenecks, we propose migrating the custom orchestrator to **Kedro**, an open-source framework for building reproducible, maintainable, and modular data science code.

### 3.1 Why Kedro?
*   **Data Catalog (`catalog.yml`)**: Decouples data access from logic. S3 parquet files, APIs, and SQLite tables become declaratively configured datasets.
*   **Modular Pipelines**: Transforms the 22 monolithic functions into explicit Nodes with declared inputs and outputs, automatically resolving the execution DAG.
*   **Testability**: Nodes become pure Python functions testing `pandas.DataFrame` inputs/outputs, making unit testing trivial compared to mocking SQLite connections.

### 3.2 Why Kedro-Viz?
*   Provides an interactive, auto-generated visual representation of the `cf_atlas` DAG.
*   Allows operators to monitor real-time execution state, inspect dataset schemas (e.g., what exactly does Phase G' look like?), and track data lineage across the pipeline.

### 3.3 Why Vizro & Vizro-AI?
*   Replaces the 16 bespoke terminal CLIs with a high-quality, web-based dashboard application built explicitly for AI web agents (semantic DOM).
*   **Vizro-AI** introduces a natural language intelligence surface. Operators and BMAD agents can pass natural language queries (e.g., *"Plot the top 10 most downloaded packages that have critical CVEs and are unmaintained"*) which Vizro-AI compiles into pandas operations against the Kedro catalog and visualizes dynamically.

### 3.4 Why Dagster (`kedro-dagster`)?
*   Replaces the legacy cron + bash script orchestration of `bootstrap-data`.
*   Provides a production-grade orchestration engine to handle retry logic, resource constraints, and complex pipeline schedules.
*   The `kedro-dagster` plugin allows seamless compilation of the Kedro DAG into a Dagster graph, giving the best of both worlds (Kedro for authoring, Dagster for running).

### 3.5 Why MCP Integration (`kedro-mcp`)?
*   Maintains the critical requirement that BMAD agents can interrogate and interact with the pipeline via the Model Context Protocol.
*   By leveraging `kedro-mcp`, we can expose Kedro pipelines and catalog reads directly as MCP tools, replacing the need for bespoke subprocess wrappers in `FastMCP`.

### 3.6 Why Boring Semantic Layer (BSL)?
*   Provides a lightweight, developer-native semantic layer built on top of Ibis to bridge the gap between `cf_atlas.db` and AI agents.
*   Allows us to formally define business metrics (e.g., "staleness", "adoption stage") and dimensions as first-class nodes in a semantic graph, ensuring that LLMs (via Vizro-AI or MCP) generate accurate, consistent queries.
*   Preserves the structural knowledge of `cf_atlas.db` as a reusable semantic knowledge graph rather than relying on raw SQL prompts.

### 3.7 Why A2A (Agent-to-Agent) Integration?
*   While MCP allows human-to-agent or direct agent-to-tool integration, A2A allows specialized autonomous agents to collaborate.
*   Enables complex, multi-agent workflows where a data-analyst agent (querying BSL) can securely and seamlessly pass structured insights or sub-tasks directly to a recipe-authoring agent.

### 3.8 The DuckDB Singularity (Compute, Graph & Vector)
*   **Unified Engine**: The legacy SQLite database and fragmented compute proposals (Polars, Neo4j, Kùzu, LanceDB) will be completely replaced by **DuckDB**.
*   **Parquet Native**: DuckDB natively reads S3 Parquet and executes multi-core analytical queries, drastically reducing the 3-4 hour cold start time.
*   **All-in-One**: DuckDB handles graph traversals natively via recursive CTEs and handles RAG embeddings via the Vector Similarity Search (`vss`) extension.
*   **Data Quality Guardrails**: Integrating **Great Expectations** ensures we catch malformed API data (e.g., PyPI JSON missing version fields) mid-pipeline, preventing poisoned data from entering the database.

### 3.9 WebAssembly (WASM), Pixi-Native Portability & `nebi` Scaffolding
*   **Strict Pixi Tooling**: Every component of the pipeline (Kedro, Dagster, DuckDB, Ibis) will be sourced exclusively from `conda-forge` and managed via a single `pixi.toml`. No standalone binaries or JVM requirements.
*   **Ecosystem Management (`nebi`)**: The entire project structure, environment configuration, and Pixi toolchain will be scaffolded and managed using **`nebi`** (from `nebari-dev`). If custom scaffolding logic is required for Kedro-Dagster-WASM deployments, new features will be contributed back to `nebi-client`.
*   **Serverless Portability**: By compiling to `duckdb-wasm`, the entire intelligence surface (Vizro-AI dashboard and BSL layer) can run locally in the browser via Pyodide. The Kedro pipeline emits pure Parquet chunks to a static store (e.g., GitHub Pages), and the WASM runtime pulls them via HTTP Range requests with zero backend infrastructure.

### 3.10 Universal SBOM Integration (CycloneDX)
*   The legacy pipeline strictly tracks `meta.yaml` dependencies. The modernized pipeline will treat dependency extraction as a universal Software Bill of Materials (SBOM) ingestion problem.
*   It will natively parse `pixi.toml`, `pixi.lock`, `pyproject.toml`, `recipe.yaml`, and `meta.yaml` files and normalize them strictly into the **CycloneDX** standard format.
*   This creates a unified, ecosystem-agnostic semantic graph in DuckDB, allowing operators to cross-reference PyPI constraints (`pyproject.toml`) against conda constraints (`recipe.yaml`) using a globally recognized specification.

### 3.11 Target State: Enterprise Python Manifest Generation
*   **The 5k Manifest**: The intelligence graph built by `cf_atlas` will directly drive the programmatic generation of the **Enterprise Python Manifest**, capping the environment at 5,000 curated packages.
*   **SLSA Prioritization**: The pipeline will merge Google Assured OSS and Anaconda Defaults as an immutable base, then use the PyPI/Vulnerability intelligence scores to safely fill the remaining quota from `conda-forge`.
*   **Determinism & Mirroring**: The output will be resolved via `prefix.dev`, mirrored via JFrog Artifactory, and actuated strictly by `pixi.lock` for local environments (devcontainers) and Docker CI/CD deployments.

### 3.12 Target State: LLM-Powered Knowledge Base (Wagtail CMS)
*   **Markdown Compilation**: Beyond the Vizro dashboard, `cf_atlas` will output its intelligence artifacts as a compiled, living knowledge base powered by **Wagtail CMS** (leveraging `wagtail-markdown` and `django-lasuite`).
*   **Agentic Maintenance**: Using the "Karpathy Architecture", LLMs will incrementally compile, link, and maintain this knowledge base. They will read Parquet outputs, build relationships via `graphify`, index documents via `cocoindex`, and synthesize vulnerability reports.
*   **Extensible Outputs**: BMAD agents querying the BSL layer will output reports directly into the Wagtail CMS as Markdown pages, Marp slide decks, or matplotlib charts, creating a compounding, centralized organizational brain.

---

## 4. End-to-End Kedro Architecture

### 3.1 Data Catalog Design (`conf/base/catalog.yml`)
The bespoke `_http.py` and SQLite `init_schema()` logic will be mapped to Kedro Datasets:
*   **DuckDB Datasets**: `pandas.ParquetDataset` and native DuckDB integration will manage reads/writes. The pipeline writes partitioned Parquet files instead of updating a monolithic SQLite DB.
*   **API Datasets**: Custom API datasets or `pandas.JSONDataset` for GitHub, PyPI, and Anaconda API interactions.
*   **TTL / Incremental State**: We will implement a custom `IncrementalParquetDataset` that encapsulates the `*_fetched_at` TTL logic.

### 3.2 Modular Pipelines
The legacy phases will be refactored into domain-specific pipelines:
1.  **Core Pipeline**: Foundational conda-forge enumeration and graph building.
2.  **PyPI Intelligence Pipeline**: PyPI mapping, skew detection, and scoring.
3.  **Vulnerability Pipeline**: AppThreat VDB and CISA KEV ingestion and overlay.
4.  **VCS & Health Pipeline**: GitHub/GitLab live queries and upstream version tracking.
5.  **Universal SBOM Pipeline**: A dedicated pipeline utilizing native parsers and tools (e.g., `cdxgen`) to extract dependencies from `pixi.toml`, `pixi.lock`, `pyproject.toml`, `recipe.yaml`, and `meta.yaml`. These manifests will be strictly normalized into the **CycloneDX** specification before being written to DuckDB Parquet datasets.

### 3.3 Checkpointing & Idempotency
*   Remove the `phase_state` table.
*   Utilize Kedro's native `runner` capabilities and persistent intermediate Parquet datasets to achieve resumability.

### 3.4 Dagster Orchestration (`kedro-dagster`)
*   The entire Kedro pipeline will be converted into a Dagster repository using the `kedro-dagster` plugin.
*   Schedules (Daily for Phase N, Weekly for Phase F/G, etc.) will be defined as Dagster Schedules.
*   Phase states and retries will be monitored via the Dagit/Dagster UI, complementing the structural view provided by `kedro-viz`.

### 3.5 MCP Exfiltration (`kedro-mcp`)
*   The existing 19 MCP tools hosted in `.claude/tools/conda_forge_server.py` will be audited and ported.
*   `kedro-mcp` will expose datasets and pipeline triggers to Claude Code.
*   BMAD Agents will trigger specific pipelines (e.g., `run_vulnerability_pipeline`) and read the resulting datasets natively via MCP.

### 3.6 Semantic Knowledge Graph (Boring Semantic Layer)
*   We will implement the **Boring Semantic Layer (BSL)** on top of the Kedro Parquet datasets using Ibis (which natively compiles to DuckDB SQL).
*   The schema and business logic currently trapped inside the 16 query CLIs will be extracted and declared as BSL dimensions and measures.
*   This semantic knowledge graph will serve as the trusted translation interface for Vizro-AI and BMAD agents.

### 3.7 A2A (Agent-to-Agent) Integration
*   Alongside MCP, we will build a dedicated Agent-to-Agent communication surface.
*   This will allow the `cf_atlas` analytical agent (which uses BSL to formulate insights) to exchange structured payloads directly with the `conda-forge-expert` recipe-authoring agent.
*   The A2A interface will support publish/subscribe or direct-messaging protocols, providing an architectural foundation for autonomous, multi-agent remediation pipelines (e.g., Agent A finds a CVE via BSL, Agent B authors the fix).

### 3.8 Data Quality Guardrails (`kedro-great-expectations`)
*   We will define strict data contracts using Great Expectations integrated directly into Kedro nodes.
*   Dagster will halt nodes upon data contract violations, triggering A2A alerts for agentic investigation before bad data is ingested.

### 3.9 Event-Driven Sensors, Lineage & Observability
*   Instead of strictly batch-based polling, we will utilize **Dagster Sensors** tied to PyPI/GitHub webhooks or RSS feeds. This enables the pipeline to react incrementally in near-real-time to upstream ecosystem changes.
*   **OpenLineage** will track execution metadata (e.g., rows processed, latency, cache hits), exposing this telemetry to optimization agents for automated pipeline tuning.
*   **OpenTelemetry (OTel)** will provide end-to-end observability. By instrumenting the Kedro nodes, Dagster runs, and DuckDB queries with OTel, we ensure comprehensive distributed tracing, metrics, and structured logging, allowing operators and A2A agents to pinpoint exact bottlenecks or failures down to the specific API call.

---

## 5. Vizro-AI Intelligence Surface

The read-surface migration will decouple the data layer from the intelligence layer:
1.  **Dashboard scaffolding**: A Vizro app deployed locally (or via WASM) serving the core KPIs currently locked in CLIs (staleness, adoption stage, feedstock health).
2.  **Vizro-AI Integration**: Expose an input field (and an MCP tool for Claude Code) that accepts user prompts.
3.  **Agentic Interrogation**: The BMAD agent can use the MCP `query_vizro_ai` tool to ask open-ended questions about the semantic knowledge graph and receive back generated charts and insights.

---

## 6. The AI Software Factory Architecture

To seamlessly merge our `cf_atlas` data layer with the enterprise's overarching autonomous goals, the system maps perfectly onto the **4-Layer AI Software Factory Blueprint**:

### Layer 1: LA SUITE DOCS (Presentation - The Human UI)
The human interface relies on **django-lasuite** and the **Wagtail CMS**. This acts as the visual "Corporate Brain", exposing the main Wiki article area, real-time collaboration avatars, and a unified search bar. The CMS is populated dynamically by the backend agents via REST API (Read/Write).

### Layer 2: DAGSTER (Orchestration - The Trigger Engine)
`kedro-dagster` serves as the trigger engine. It manages the execution DAG via two primary activation pathways:
*   **Sensors**: Event-driven triggers (e.g., "New File Detected" when PyPI webhooks arrive or Parquet files are dumped).
*   **Schedules**: Cron-based triggers (e.g., "Weekly Schedule" to fire the Linter/QA agents for feedstock health checks).

### Layer 3: THE AGENT WORKFORCE (Governance)
The autonomous workflow is governed by the 5 specific personas (Ingester, Compiler, Linker, Linter, Oracle) powered entirely by `bmad-method` (we explicitly reject `spec-kit`). These agents execute the physical tools (`lasuite_client.py` for API push, `markdown_generator.py` for Wiki writing, `search_ops.py` for retrieval, and `pdf_parser.py` for deep research).

### Memory: THE KARPATHY WIKI (The Brain's Storage)
The LLM-Powered Knowledge base enforces a strict, incremental storage architecture backed by Minio (S3) and PostgreSQL (using DuckDB/Ibis as the semantic query engine):
*   `wiki/raw/`: The raw Parquet ingestion landing zone.
*   `wiki/compiled/`: The knowledge graphs, BSL mapped concepts, and linked dependency files.
*   `wiki/outputs/`: The final markdown reports, slide decks, and generated visualizations output by the Oracle agent.

---

## 7. Implementation Waves

*   **Wave A: `nebi` Scaffold & Catalog**
    *   Initialize the core project structure and `pixi` ecosystem using `nebi`.
    *   Define `catalog.yml` for all API sources and Parquet outputs.
    *   Implement the custom `IncrementalParquetDataset` for TTL gating.
*   **Wave B: Pipeline Node Porting & MCP Integration**
    *   Port Core Pipeline (B-M) into Kedro nodes.
    *   Port PyPI & Vulnerability pipelines.
    *   Integrate `kedro-mcp` to re-expose the data surface to Claude Code/BMAD agents.
    *   *Verification*: Run the Kedro pipeline in parallel with the legacy `bootstrap-data` to ensure dataset parity.
*   **Wave C: Orchestration & Visualization**
    *   Integrate `kedro-dagster` to handle scheduling and execution.
    *   Integrate `kedro-viz` for topological rendering.
    *   Expose the visualization server via a dedicated pixi task (`pixi run viz`).
*   **Wave D: Semantic Layer & Dashboards**
    *   Define the Boring Semantic Layer (BSL) models, dimensions, and measures on top of the Kedro catalog.
    *   Build the Vizro dashboard application driven by the BSL models.
    *   Port the 16 CLIs into Vizro pages.
    *   Integrate Vizro-AI and expose the natural language interface via a new MCP tool, powered by the BSL knowledge graph.
*   **Wave E: A2A Integration, Lineage & Observability**
    *   Implement the Agent-to-Agent communication interfaces.
    *   Define structured protocols for data passing between the BSL intelligence agents and the conda-forge execution agents.
    *   Integrate OpenLineage tracking.
    *   Instrument the pipeline with OpenTelemetry for end-to-end distributed tracing, metrics, and logging.
*   **Wave F: The DuckDB Singularity**
    *   Migrate all Datasets to use DuckDB backed by partitioned Parquet files.
    *   Inject `kedro-great-expectations` validation nodes for upstream API ingestions.
    *   Implement Vector Similarity Search (RAG) using DuckDB's `vss` extension.
*   **Wave G: WebAssembly Portability & Event-Driven Sensors**
    *   Compile the Vizro-AI and BSL intelligence layers to run in Pyodide/DuckDB-WASM locally in the browser.
    *   Configure the Kedro pipeline to output Parquet artifacts to a static web host (GitHub Pages).
    *   Implement Dagster Sensors to transition the pipeline into a near-real-time, event-driven state triggered by PyPI/GitHub webhooks.
