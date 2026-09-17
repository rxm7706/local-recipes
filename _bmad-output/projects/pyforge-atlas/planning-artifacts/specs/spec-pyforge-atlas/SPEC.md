---
id: SPEC-pyforge-atlas
spec: pyforge-atlas
status: ready
updated: "2026-09-17"
owner-dream: docs/dreams/pyforge-atlas.md
covers-dreams:
  - docs/dreams/pyforge-atlas.md
  - docs/dreams/artifactory-download-intelligence.md
  - docs/dreams/atlas-kedro-catalog-expansion.md
  - docs/dreams/atlas-query-dashboards.md
  - docs/dreams/conda-forge-packaging-inventory-operations.md
  - docs/dreams/enterprise-data-models-and-apis.md
  - docs/dreams/kedro-org-tooling-adoption.md
  - docs/dreams/microsoft-org-sweep.md
  - docs/dreams/pyforge-atlas-intelligence-platform.md
  - docs/dreams/unity-data-stack.md
  - docs/dreams/upstream-discovery.md
  - docs/dreams/wagtail-corporate-brain.md
  - docs/dreams/wasm-analytics-stack.md
surface:
  - src/shared/packages/pyforge-atlas/**
  - src/prototype/packages/pyforge-atlas-kedro-viz/**
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/
  - src/shared/packages/pyforge-atlas/conf/base/catalog.yml
  - src/shared/packages/pyforge-atlas/conf/base/globals.yml
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/**
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/upstream_discovery/**
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/pypi_intelligence/**
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/core/**
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/**
  - .github/workflows/kedro-viz-publish.yml
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/
  - scripts/dashboard_serve.py
  - scripts/conda-forge-packaging-inventory-operations_metrics.py
  - scripts/tests/test_conda_forge_packaging_inventory_operations_metrics.py
  - scripts/tests/fixtures/inventory_universe/generate_fixtures.py
  - scripts/tests/fixtures/inventory_universe/mini-workbook.xlsx
  - scripts/tests/fixtures/inventory_universe/catalog/derived/inventory_universe/inventory_universe.parquet
  - scripts/tests/fixtures/inventory_universe/catalog/intermediate/core_packages_enumerated/core_packages_enumerated.parquet
  - scripts/tests/fixtures/inventory_universe/catalog/intermediate/pypi_universe/pypi_universe.parquet
  - scripts/tests/fixtures/inventory_universe/catalog/primary/pypi_conda_mapping/pypi_conda_mapping.parquet
  - scripts/tests/fixtures/inventory_universe/catalog/raw/openteams_project_1_board_raw/openteams_project_1_board.parquet
  - scripts/tests/test_quartet_no_xlsx_surface.py
  - scripts/conda-forge-packaging-inventory-operations_openteams_identity.py
  - scripts/conda-forge-packaging-inventory-operations_priority.py
  - scripts/openteams_identity_dashboards.py
  - conf/conda-forge-packaging-inventory-operations.local.env.example
  - conf/conda-forge-packaging-inventory-operations_curated_groups.json
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/factory/lasuite.py
  - src/shared/packages/pyforge-atlas/tests/factory/test_lasuite.py
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-atlas/tools/lasuite_bringup.py
  - src/shared/packages/pyforge-atlas/tests/factory/test_lasuite_live_rehearsal.py
surface-drift-exclude:
  # 2026-09-12: also governed by the spec(s) named below, which already
  # reconciles each of these files cleanly -- this kernel spec's own
  # memlog does not move for routine story work anymore, so double-
  # claiming them only produced permanent drift-presumed noise here.
  # Coverage is unchanged (still listed under `surface:` above); only
  # this spec's own drift tracking for these specific files is off.
  - src/shared/packages/pyforge-atlas/pixi.toml   # also governed by pyforge-steward/spec-pyforge-unifying-strategy
  - src/shared/packages/pyforge-atlas/pyproject.toml   # also governed by pyforge-steward/spec-pyforge-unifying-strategy
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/__init__.py   # also governed by pyforge-steward/spec-pyforge-unifying-strategy
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/parity.py   # also governed by pyforge-steward/spec-pyforge-unifying-strategy
  - src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_dashboard_dryrun.py   # also governed by pyforge-steward/spec-pyforge-unifying-strategy
  - src/shared/packages/pyforge-atlas/tests/meta/test_cli_tool_parity.py   # also governed by pyforge-steward/spec-pyforge-unifying-strategy
  - src/shared/packages/pyforge-atlas/tests/tools/test_live_artifactory_transport.py   # also governed by pyforge-steward/spec-pyforge-unifying-strategy
  - src/shared/packages/pyforge-atlas/tests/unit/catalog/test_no_inline_io.py   # also governed by pyforge-steward/spec-pyforge-unifying-strategy
  - src/shared/packages/pyforge-atlas/tests/unit/singularity/test_duckdb_sole_engine.py   # also governed by pyforge-steward/spec-pyforge-unifying-strategy
  - src/shared/packages/pyforge-atlas/tests/unit/test_dashboard_app.py   # also governed by pyforge-steward/spec-pyforge-unifying-strategy
  - src/shared/packages/pyforge-atlas/tests/unit/test_dashboard_data.py   # also governed by pyforge-steward/spec-pyforge-unifying-strategy
  - src/shared/packages/pyforge-atlas/tests/unit/test_dashboard_factory_status.py   # also governed by pyforge-steward/spec-pyforge-unifying-strategy
  - src/shared/packages/pyforge-atlas/tests/unit/test_dashboard_identity_gist.py   # also governed by pyforge-steward/spec-pyforge-unifying-strategy
  - src/shared/packages/pyforge-atlas/tools/live_artifactory_transport.py   # also governed by pyforge-steward/spec-pyforge-unifying-strategy
companions:
  - signals.md               # the 23 ported phases -> nodes, the 3 additive riders, the Warden boundary on signals
  - catalog-contract.md      # 7 pipelines x 86 datasets, every declared TTL, the two freshness clocks, identity + join keys
  - degradation-contract.md  # the 3 markers, the fixed policy mapping, the frozen exit projection
  - gate-contract.md         # the 7 gates, what each proves and what they refuse to do
  - constitution-provenance.md  # [Unity satellite, folded in 2026-08-02] the 14-Article Constitution map + the 8 required amendments
sources:
  - ../../../../../../docs/dreams/pyforge-atlas.md
open_questions: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

> **Consolidated 2026-08-02** — see
> `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-unity-data-stack/SPEC.md` and
> `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wasm-analytics-stack/SPEC.md`
> for the original standalone documents (moved there intact, not deleted).
> This Spec now also carries the Unity Data Stack and Wasm
> Analytics Stack Spec contracts, folded in as `Satellite:` subsections
> under each of the five fields below, with `CAP-n` renumbered to continue
> this Spec's sequence (`CAP-18`..`CAP-26` Unity, `CAP-27`..`CAP-31` Wasm)
> and cross-referenced `AD-n` renumbered to match the merged
> `ARCHITECTURE-SPINE.md` (`AD-24`..`AD-46` Unity, `AD-47`..`AD-56` Wasm).
> Each satellite's own `FR-n`/`SM-n` numbering (local to its own PRD) is
> **not** renumbered and stays independent of the primary Spec's `FR-1`..`FR-22`.

# Atlas — the intelligence layer an agent workforce can extend

## Why

The Navigator's mandate is *chart the dependencies, map the world, define the floor* — and
the map has to stay drawn by agents, not heroes. The legacy `cf_atlas` orchestrator did ship
real signal for years: 23 cataloged phases building a database over the conda-forge feedstock
population (19,726 at the 2026-07-16 full-population run) — versions, downloads, maintainers,
vulnerabilities, readiness — read through 28 bespoke CLIs and 23 atlas-relevant MCP tools.
Its cost was never acute; it was **chronic and compounding**. Every new phase hand-rolled its
own checkpointing, TTL gating, and backoff. Data lineage lived in one developer's head.
Execution was observable only through stdout. Ad-hoc questions required hand-written SQL
against a single SQLite file. A 1800-second coarse timeout could silently drop a phase and
score the run green.

The load-bearing justification was never performance — it is **agent-maintainability**.
As the factory's workforce shifted from one developer occasionally touching this code to
loop-driven agents adding phase 24 unattended, a ~10,000-line procedural monolith became the
single largest risk to the whole packaging factory's autonomy story. The answer is a
declarative DAG small enough, pure enough, and contract-guarded enough that an agent can add
a signal by writing a node and declaring its datasets, inheriting checkpointing, TTL, backoff,
validation, lineage, and scheduling for free — verified by deterministic fixture gates rather
than tribal knowledge.

The performance story is told honestly and deliberately under-claimed: the cold rebuild is
network-bound, so the win is **incremental re-materialization**, query-time analytics, and
Parquet reads — never an engine-swap cold-start miracle. Atlas is conda-forge-only by name,
serving one operator and one agent workforce; that narrowness is the design, not a gap to
close later.

**2026-08-02 consolidation.** Atlas's project tree also plans two adjacent,
substantial platform initiatives — Unity Data Stack (an enterprise
innersource Python monorepo platform) and Wasm Analytics Stack (a
WASI-sandboxed analytical pipeline for hardened OpenShift) — neither a
capability of the `cf_atlas` pipeline described above, each its own
initiative with its own Why, Capabilities, Constraints, Non-goals, Success
signal, and Assumptions. Both were seeded 2026-07-23 and planned to
PRD + Architecture depth by 2026-07-25; neither has epics/stories or code
yet. Per an explicit user decision on 2026-08-02 (overriding this repo's
default dream-level-only consolidation convention), their full Spec/PRD/
Architecture chains were folded into this station's single Spec/PRD/
Architecture rather than kept as separate chains under the same project
tree. Their content appears below as `Satellite:` subsections under each of
this document's five fields.

## Capabilities
One-chain rebase 2026-09-17. Each reminted CAP keeps provenance `← spec-<old> CAP-m (shipped <date>)`.
- **CAP-1 — the DAG is the orchestrator** ← spec-pyforge-atlas CAP-1 (shipped 2026-09-09)
  - **intent:** Every unit of ingestion or compute is a pure function with declared inputs and
  - **success:** The 23 legacy phases run as DAG-resolved nodes across exactly seven typed
- **CAP-2 — all IO is catalog-declared, all credentials are host-scoped** ← spec-pyforge-atlas CAP-2 (shipped 2026-09-09)
  - **intent:** No node function contains data-access logic, and a credential reaches only the
  - **success:** Every source and output is an entry in `conf/base/catalog.yml`; a static gate
- **CAP-3 — incremental state is a dataset concern, not a node concern** ← spec-pyforge-atlas CAP-3 (shipped 2026-09-09)
  - **intent:** Freshness, resumption, and re-fetch decisions belong to one reusable dataset
  - **success:** `IncrementalParquetDataset` round-trips `*_fetched_at` TTL state; stale rows
- **CAP-4 — one execution plane, orchestrated and budgeted** ← spec-pyforge-atlas CAP-4 (shipped 2026-09-09)
  - **intent:** The operator watches scheduled, retried, per-node-budgeted runs instead of
  - **success:** The DAG compiles to a single Dagster repository; schedules encode the
- **CAP-5 — event-driven ingestion on the same plane** ← spec-pyforge-atlas CAP-5 (shipped 2026-09-09)
  - **intent:** Upstream release activity can pull the pipeline forward incrementally instead
  - **success:** Sensors watch upstream release feeds and turn a detected event into exactly
- **CAP-6 — one engine for compute, graph, and vector** ← spec-pyforge-atlas CAP-6 (shipped 2026-09-09)
  - **intent:** Analytical compute, graph traversal, and semantic retrieval all run in the same
  - **success:** Partitioned Parquet is the canonical persistence format and DuckDB the only
- **CAP-7 — retirement earned by recorded parity, not asserted** ← spec-pyforge-atlas CAP-7 (shipped 2026-09-09)
  - **intent:** The legacy orchestrator is retired only against evidence a human signed.
  - **success:** A fixture-based, loop-callable parity harness compares migrated Parquet
- **CAP-8 — the read surface is declared once and consumed everywhere** ← spec-pyforge-atlas CAP-8 (shipped 2026-09-09)
  - **intent:** Metric logic lives in exactly one place, and every read surface — page,
  - **success:** Staleness, adoption stage, feedstock health, and maintainer-role facts are
- **CAP-9 — agents trigger and read the pipeline natively** ← spec-pyforge-atlas CAP-9 (shipped 2026-09-09)
  - **intent:** An authoring or execution agent can run a named pipeline and read the resulting
  - **success:** The atlas-relevant MCP tools are authored directly over session and catalog
- **CAP-10 — one structured channel between agents** ← spec-pyforge-atlas CAP-10 (shipped 2026-09-09)
  - **intent:** Insights, contract violations, and policy breaches move between the analytical
  - **success:** The analytical agent hands a typed payload to the authoring agent over a
- **CAP-11 — bad data halts before it persists** ← spec-pyforge-atlas CAP-11 (shipped 2026-09-09)
  - **intent:** A malformed upstream payload stops the run rather than quietly landing in the
  - **success:** Inline dataframe contracts run behind one validator-agnostic after-node hook;
- **CAP-12 — every run is traceable to the API call** ← spec-pyforge-atlas CAP-12 (shipped 2026-09-09)
  - **intent:** A failure or a slow run is diagnosable from recorded lineage and traces rather
  - **success:** Every node emits lineage events carrying rows, latency, and cache hits, and
- **CAP-13 — any manifest becomes one comparable inventory, behind one exit code** ← spec-pyforge-atlas CAP-13 (shipped 2026-09-09)
  - **intent:** CI consumes one schema-validated artifact and one exit code instead of scraping
  - **success:** Every supported manifest format normalizes to CycloneDX preserving the
- **CAP-14 — new signals ride in additively, with their failure modes fixture-pinned** ← spec-pyforge-atlas CAP-14 (shipped 2026-09-09)
  - **intent:** A newly ingested signal reaches the read surface without renegotiating the
  - **success:** Conda-native advisories are ingested by batched query with a bounded detail
- **CAP-15 — the derived layer regenerates and refuses to go stale** ← spec-pyforge-atlas CAP-15 (shipped 2026-09-09)
  - **intent:** Reports and exports are downstream nodes of the rebuild, and a consumer can
  - **success:** Derived datasets (purl exports, universe BOM, freshness reports) re-run after
- **CAP-16 — the read surface runs with no backend at all** ← spec-pyforge-atlas CAP-16 (shipped 2026-09-09)
  - **intent:** The intelligence surface is portable to a browser against a static host.
  - **success:** The dashboard and semantic layer load and query client-side over Parquet
- **CAP-17 — the knowledge factory maintains itself and never writes back** ← spec-pyforge-atlas CAP-17 (shipped 2026-09-09)
  - **intent:** Agent crews compile, lint, publish, and answer over a wiki built from pipeline
  - **success:** The three-stage `raw/ → compiled/ → outputs/` tree exists with a layout
- **CAP-18 — A platform engineer declares one Workspace root —** ← spec-pyforge-atlas CAP-18 (shipped 2026-09-09)
  - **intent:** A platform engineer declares one Workspace root — platform matrix, channels, system-requirement floors, and the set of Packages — from which Environments compose from named Features with no inherited bloat, and every Package carries a declared owner.
  - **success:** FR-1–9 hold: adding a Package requires editing exactly one place; no dependency version string is duplicated; a minimal Environment's installed size is measured against a documented ceiling and a regression fails the gate; Stages are modelled separately from Environments so the number of distinct solves is bounded by genuine dependency variation, not Stage naming (AD-27).
- **CAP-19 — The Workspace produces one authoritative Workspace Lock covering** ← spec-pyforge-atlas CAP-19 (shipped 2026-09-09)
  - **intent:** The Workspace produces one authoritative Workspace Lock covering native and Python packages together, reproducing an Environment offline on every declared platform, with a derived standards-format export and an air-gapped Offline Bundle, and credentials that are host-scoped and never appear in a URL or argument.
  - **success:** FR-10–17 hold: multi-platform coverage is proven by materialization, never assumed (FR-11); the Exported Lock is generated from, and drift-checked against, one pinned Workspace Lock commit SHA, failing the gate on mismatch (FR-12, resolves PRD OQ-1 via AD-25).
- **CAP-20 — A developer runs one command that executes every** ← spec-pyforge-atlas CAP-20 (shipped 2026-09-09)
  - **intent:** A developer runs one command that executes every check CI executes — lint, format, type checking, coverage thresholds, security scanning, and a tagged behavioural-test tier — with pre-commit mirroring a fast subset.
  - **success:** FR-18–25 hold: a parity check asserts the local and CI check-sets are identical and fails on divergence (AD-32); coverage that decreases relative to the base branch fails the gate.
- **CAP-21 — Every Constitution Mandate is classified, machine-readably, as a** ← spec-pyforge-atlas CAP-21 (shipped 2026-09-09)
  - **intent:** Every Constitution Mandate is classified, machine-readably, as a Platform Invariant (no override) or a Domain Default (Domain-overridable with a recorded decision); violations name the clause they violate; amendment is a governed, versioned process.
  - **success:** FR-26–32 hold: an unclassified Mandate, or an override with no linked decision record, fails the Quality Gate (AD-31); the Constitution carries semver, ratified/amended/next-review dates; a coverage report distinguishes automatically-enforced Mandates from human-review-only ones.
- **CAP-22 — Every Package names a Trusted Committer accountable for** ← spec-pyforge-atlas CAP-22 (shipped 2026-09-09)
  - **intent:** Every Package names a Trusted Committer accountable for reviewing outside contributions, an outside contributor finds a documented path to contribute to code they don't own, and branch/commit/merge conventions are enforced automatically.
  - **success:** FR-33–38 hold: a Package with no Trusted Committer fails the gate; a scaffolded Package or Data Product passes the Quality Gate immediately with no manual fixes (FR-37); cross-team contribution rate and an internal-fork counter-signal are both measured (FR-38).
- **CAP-23 — Every built artifact carries a versioned SBOM with** ← spec-pyforge-atlas CAP-23 (shipped 2026-09-09)
  - **intent:** Every built artifact carries a versioned SBOM with a populated dependency graph (runtime-scoped and full variants) and a build-provenance attestation, continuously gated against exploitation-aware vulnerability data through one schema-validated Compliance Report, with baselining/grandfathering and opt-in remediation proposals.
  - **success:** FR-39–47 hold, delivered by **integrating** `pyforge-warden` (already a strict superset of the intake approach) rather than reimplementing it; SBOM generation runs against the built artifact and a test asserts a populated transitive dependency edge (AD-34); an artifact with no provenance attestation cannot be promoted to any Stage whose policy requires approval (AD-35).
- **CAP-24 — Each Domain owns Data Products layered Raw →** ← spec-pyforge-atlas CAP-24 (shipped 2026-09-09)
  - **intent:** Each Domain owns Data Products layered Raw → Curated → Consumption, with an enforced naming convention, a structured metadata contract, and versioned schema contracts; one reference Domain (`customer`) is implemented end to end as the pattern others follow.
  - **success:** FR-48–54 hold: a schema change that breaks a declared consumer is detected before merge, requiring a version increment and migration note (FR-52, AD-39); the reference Domain exercises all three Layers, publishes a contract, and passes every gate — its structure is exactly what the FR-37 scaffolding templates generate.
- **CAP-25 — Every capability available with public network access is** ← spec-pyforge-atlas CAP-25 (shipped 2026-09-09)
  - **intent:** Every capability available with public network access is available in Air-Gap Mode (or declares why not); deployment is declarative and environment-promoted under Stage policy; secrets are never committed and are validated present at service startup; a Stage's Data Classification bounds which datastores and network posture it may be configured against.
  - **success:** FR-55–58 hold: a parity test enumerates capabilities and asserts each works air-gapped, targeting 100% with declared exceptions (SM-6); a secret-shaped string committed to the repository fails an automated check (FR-57).
- **CAP-26 — A developer starts, stops, and inspects the full** ← spec-pyforge-atlas CAP-26 (shipped 2026-09-09)
  - **intent:** A developer starts, stops, and inspects the full local service stack — aggregate and per-service — with single commands, and the Workspace names a small, stable public task API.
  - **success:** FR-59–60 hold: status reports actual service health, not process existence; removing or renaming a public task is a breaking change requiring a decision record.
- **CAP-27 — A business user uploads an `.xlsx` file via** ← spec-pyforge-atlas CAP-27 (shipped 2026-09-09)
  - **intent:** A business user uploads an `.xlsx` file via an OIDC-authenticated FastAPI endpoint, and its structure and data quality are checked inside a genuine WASI Preview 2 sandbox before any row reaches ingestion, with row-level failures reported precisely and valid rows queued independently of rejected ones.
  - **success:** FR-1–4 hold: an unauthenticated request receives HTTP 401 before the upload body is read; a structurally-invalid file is rejected in full (zero rows reach Bronze); each rejected row's error names the specific column/rule that failed without blocking rows that passed; no row reaches DuckDB Bronze via `dlt` without having passed validation.
- **CAP-28 — `dbt-duckdb` transforms Bronze into schema-declared Silver and Gold** ← spec-pyforge-atlas CAP-28 (shipped 2026-09-09)
  - **intent:** `dbt-duckdb` transforms Bronze into schema-declared Silver and Gold models, emits column-level lineage for every model, and a failing `dbt test` blocks promotion of that model's output to the next layer.
  - **success:** FR-5–7 hold: every `dbt run` is traceable to the Bronze table state it consumed; a lineage query for any Gold column returns its full upstream column chain back to Bronze; a `dbt run` with a failing test does not update the corresponding table and the prior good state remains queryable.
- **CAP-29 — One W3C trace ID, minted once at the** ← spec-pyforge-atlas CAP-29 (shipped 2026-09-09)
  - **intent:** One W3C trace ID, minted once at the browser/API boundary, correlates OTel spans and OpenLineage facets across every pipeline stage to Marquez via a per-pod Vector sidecar, so a single trace-ID lookup reconstructs the full upload-to-Gold journey with no gaps.
  - **success:** FR-8–11 hold: the trace ID returned to the client at upload time is the same one attached to that upload's eventual Gold-table lineage record; a trace query for any upload returns spans for every stage it passed through with no gap; Marquez returns the full Bronze→Silver→Gold lineage graph; no pipeline container other than the Vector sidecar holds an external telemetry egress path.
- **CAP-30 — An automated, non-hollow gate mechanically proves the WASI** ← spec-pyforge-atlas CAP-30 (shipped 2026-09-09)
  - **intent:** An automated, non-hollow gate mechanically proves the WASI validation component cannot reach any capability beyond its WIT-declared surface, and a build-time check blocks denylisted imports from ever entering the component's dependency closure.
  - **success:** FR-12–13 hold: the gate fails on any host interaction beyond the component's declared WIT imports; deliberately widening the component's declared capabilities without a corresponding WIT change makes the gate fail, proving it checks something rather than always passing; adding a denylisted import (`numpy`, `pandas`, `pyarrow`, `pydantic`, or any other C-extension-backed or `componentize-py`-unproven package) fails `pixi run build`, not a later runtime error.
- **CAP-31 — One Pixi toolchain builds every artifact the pipeline** ← spec-pyforge-atlas CAP-31 (shipped 2026-09-09)
  - **intent:** One Pixi toolchain builds every artifact the pipeline needs, including the compiled WASI component, and the same security context runs identically under a Podman digital twin and OpenShift Restricted SCC, with DuckDB state persisted via a `ReadWriteOnce` PVC at a consistent mount path.
  - **success:** FR-14–17 hold: a clean checkout plus `pixi install && pixi run build` produces a runnable digital twin with no manual steps outside Pixi; every container starts as non-root UID 1001 with a read-only root filesystem in both the digital twin and OCP; the Helm chart's security context matches Restricted SCC exactly with no `anyuid` or other elevated binding requested; pipeline restarts do not lose previously-ingested Bronze/Silver/Gold data.
- **CAP-32 — An AQL adapter queries an Artifactory instance's own** ← spec-artifactory-download-intelligence CAP-1 (shipped 2026-09-17)
  - **intent:** An AQL adapter queries an Artifactory instance's own telemetry: it resolves
  - **success:** Against a mock AQL transport serving canned topology + download responses, the
- **CAP-33 — Adapter results join into the SAME identity space** ← spec-artifactory-download-intelligence CAP-2 (shipped 2026-09-17)
  - **intent:** Adapter results join into the SAME identity space Phase C/C.5 already maintain —
  - **success:** A mock-served package that exists publicly joins to the same identity row Phase
- **CAP-34 — A package pulled from Artifactory with no public** ← spec-artifactory-download-intelligence CAP-3 (shipped 2026-09-17)
  - **intent:** A package pulled from Artifactory with no public PyPI counterpart — absent from
  - **success:** In a mock run containing both a public package and a mock-only package, exactly
- **CAP-35 — The work ships as a new atlas Kedro** ← spec-artifactory-download-intelligence CAP-4 (shipped 2026-09-17)
  - **intent:** The work ships as a new atlas Kedro pipeline following the established phase
  - **success:** The pipeline registers alongside the existing atlas pipelines and its output is
- **CAP-36 — Kedro self-containment (Phases A–B)** ← spec-atlas-kedro-catalog-expansion CAP-1 (shipped 2026-09-09)
  - **intent:** A fresh clone runs the documented Kedro bootstrap on
  - **success:** `pixi run pyforge-atlas-bootstrap` completes green; production
- **CAP-37 — Public index catalog completeness (Phase C, Tier 0–2)** ← spec-atlas-kedro-catalog-expansion CAP-2 (shipped 2026-09-09)
  - **intent:** Every live source the inventory verification matrix needs is
  - **success:** `conda-forge-packaging-inventory-operations_metrics.py
- **CAP-38 — Identity join in `upstream_discovery` (Phase D)** ← spec-atlas-kedro-catalog-expansion CAP-3 (shipped 2026-09-09)
  - **intent:** PURL Associator ingest, OpenTeams project 1 board ingest,
  - **success:** Export rows match today's `GIST_SCHEMA` identity columns and
- **CAP-39 — Quartet consumes Atlas exports (thin orchestration)** ← spec-atlas-kedro-catalog-expansion CAP-4 (shipped 2026-09-09)
  - **intent:** Inventory scripts stop owning public-index fetch and identity
  - **success:** Metrics and identity scripts have no direct fetch to public
- **CAP-40 — Bootstrap operator Vizro pages (optional follow-on, Story 21.9)** ← spec-atlas-kedro-catalog-expansion CAP-5 (shipped 2026-09-09)
  - **intent:** After bootstrap, operators inspect index health, identity
  - **success:** Three new pages (`bootstrap-index-health`,
- **CAP-41 — Kedro-Viz publish stays in sync (optional follow-on, Story 21.10)** ← spec-atlas-kedro-catalog-expansion CAP-6 (shipped 2026-09-09)
  - **intent:** Static Kedro-Viz export republishes when catalog or dataset
  - **success:** `kedro-viz-publish.yml` triggers on `catalog.yml`, `globals.yml`,
- **CAP-42 — Vizro parity with identity canvases (Epic 22 follow-on)** ← spec-atlas-kedro-catalog-expansion CAP-7 (shipped 2026-09-09)
  - **intent:** Vizro becomes a **parallel replacement** for the three Cursor
  - **success:** Three Vizro pages (`identity-catalog`, `identity-ops`,
- **CAP-43 — Complete inventory export, zero deferred (Epic 23 closure)** ← spec-atlas-kedro-catalog-expansion CAP-8 (shipped 2026-09-09)
  - **intent:** Close the dream with **no data slices left in `scripts/`** —
  - **success:** Enterprise builds `enterprise_jfrog_consumption.parquet` per
- **CAP-44 — The lowest-risk rendering mode ships first: a curated** ← spec-atlas-query-dashboards CAP-1 (shipped 2026-09-09)
  - **intent:** The lowest-risk rendering mode ships first: a curated catalog of views mirroring
  - **success:** Each catalog view emits a self-contained HTML fragment from the live
- **CAP-45 — Genuinely interactive views (filter, drill, re-sort live) layer** ← spec-atlas-query-dashboards CAP-2 (shipped 2026-09-09)
  - **intent:** Genuinely interactive views (filter, drill, re-sort live) layer on Bokeh's
  - **success:** At least one catalog view runs filter/drill/re-sort against `cf_atlas.db` over a
- **CAP-46 — Widget TYPES are pluggable behind a small registry** ← spec-atlas-query-dashboards CAP-3 (shipped 2026-09-09)
  - **intent:** Widget TYPES are pluggable behind a small registry, not hard-coded to a
  - **success:** Adding a new widget type is one registry entry plus one renderer, with zero
- **CAP-47 — The CDN-URL-rewriting concern for air-gapped deployment is carried** ← spec-atlas-query-dashboards CAP-4 (shipped 2026-09-09)
  - **intent:** The CDN-URL-rewriting concern for air-gapped deployment is carried from day one,
  - **success:** A page rendered under the air-gapped profile contains zero references to
- **CAP-48 — The query plane the views read serves BOTH** ← spec-atlas-query-dashboards CAP-5 (shipped 2026-09-09)
  - **intent:** The query plane the views read serves BOTH faces behind ONE boot script: the
  - **success:** One boot script raises both faces; with the platform stack down it degrades
- **CAP-49 — The composed semantic stores the grounded dashboard pages** ← spec-atlas-query-dashboards CAP-6 (shipped 2026-09-09)
  - **intent:** The composed semantic stores the grounded dashboard pages bind to (DW-D2-2's
  - **success:** A single `kedro run --pipeline <named>` materializes the composed stores from
- **CAP-50 — The deferred Vizro page inventory completes: the CIS** ← spec-atlas-query-dashboards CAP-7 (shipped 2026-09-09)
  - **intent:** The deferred Vizro page inventory completes: the CIS two-spine specs
  - **success:** Both spine files exist under `planning-artifacts/` covering every unshipped
- **CAP-51 — the governed from-scratch run** ← spec-conda-forge-packaging-inventory-operations CAP-1 (shipped 2026-09-17)
  - **intent:** Recorded capability from the absorbed Spec.
  - **success:** The absorbed Spec's success clause is the record.
- **CAP-52 — execution-ready handoffs** ← spec-conda-forge-packaging-inventory-operations CAP-2 (shipped 2026-09-17)
  - **intent:** Recorded capability from the absorbed Spec.
  - **success:** The absorbed Spec's success clause is the record.
- **CAP-53 — trending ingest** ← spec-upstream-discovery CAP-1 (shipped 2026-09-17)
  - **intent:** The dataflow ingests GitHub-trending Python repos
  - **success:** A run produces a fresh trending snapshot dataset; a
- **CAP-54 — tier classification** ← spec-upstream-discovery CAP-2 (shipped 2026-09-17)
  - **intent:** A classifier node joins each ingested repo against existing
  - **success:** Every ingested row in a batch carries a tier or an
- **CAP-55 — operator surface** ← spec-upstream-discovery CAP-3 (shipped 2026-09-17)
  - **intent:** An operator or agent can query the tiered candidate list
  - **success:** The CLI and MCP tool return matching output for the same
- **CAP-56 — fixed-source audit track** ← spec-upstream-discovery CAP-4 (shipped 2026-09-17)
  - **intent:** The same discover→triage→tier→wave-package shape
  - **success:** A fixed-source batch produces the same tiered/reasoned
- **CAP-57 — downstream handoff** ← spec-upstream-discovery CAP-5 (shipped 2026-09-17)
  - **intent:** Every surviving candidate (tier 1 or 2) passes a
  - **success:** A candidate reaching packaging carries a recorded
- **CAP-58 — a minimal live Wagtail/La Suite instance satisfies `LaSuiteClient`'s** ← spec-wagtail-corporate-brain CAP-1 (shipped 2026-09-17)
  - **intent:** a minimal live Wagtail/La Suite instance satisfies `LaSuiteClient`'s
  - **success:** with `LASUITE_BASE_URL` + `LASUITE_API_TOKEN` exported, `resolve_lasuite_config()`
- **CAP-59 — a real httpx-backed `Opener` replaces the mock at** ← spec-wagtail-corporate-brain CAP-2 (shipped 2026-09-17)
  - **intent:** a real httpx-backed `Opener` replaces the mock at the module's sole network seam —
  - **success:** `WikiSyncer.sync_all()` runs live through that opener with ZERO edits to
- **CAP-60 — the round-trip + idempotency semantics `test_lasuite.py` already proves** ← spec-wagtail-corporate-brain CAP-3 (shipped 2026-09-17)
  - **intent:** the round-trip + idempotency semantics `test_lasuite.py` already proves against
  - **success:** the attended session runs that four-step sequence against the real CMS and each

## Constraints

- **Atlas measures; Warden judges.** An upstream-maintenance signal
  (OpenSSF-Scorecard class) is a **Warden axis**, never an Atlas gate — Atlas may
  join and expose it as a feed, but the verdict is not Atlas's to render.
  `pyforge-warden` already names six axes (hygiene · security · license ·
  currency · provenance · **maintenance**), gating the first four in v1. This is
  the Charter's *the hand that builds is never the gate that judges* applied to
  signals: it rules out scoring or thresholding any maintenance metric here.
  *(Resolved 2026-07-25 from the Warden contract; no operator decision required.)*

- **The DAG is the single source of truth; every orchestration and surface plugin is
  replaceable glue.** Pipeline structure, node logic, and dataset declarations live only in the
  Kedro project. The Dagster binding, the MCP plugin, and the semantic-layer binding are thin
  adapters a single story could swap without touching nodes or catalog — the named exit ramps
  are recorded. No node, dataset, hook, or MCP module may import the orchestrator's or the
  plugin's APIs, enforced by an import-direction meta-test shipped with the catalog gate. This
  is why a single-maintainer plugin is an acceptable dependency and not an existential one.
- **One execution plane.** Budgets (per-node timeout and retry), validation hooks, lineage and
  trace instrumentation, and profile definitions are declared in run configuration, so every
  entry point — scheduled job, sensor, MCP trigger, CLI — executes the identical named pipeline
  with identical machinery; an MCP trigger names a profile explicitly or inherits `maintainer`.
  **Run admission IS implemented** *(shipped 2026-07-29, Story 10.6, closing `DW-AD23-1` /
  `AUD-ATLAS-046`; it was correctly recorded as unimplemented between 2026-07-27 and then)*. A
  dataset has one writing run at a time: `pyforge.atlas.admission.RunAdmissionHooks`, registered
  in `settings.HOOKS`, takes one OS file lock per output dataset in `before_pipeline_run` and
  releases in both `after_pipeline_run` and `on_pipeline_error`. Two concurrent triggers of the
  same dataset set — an MCP trigger racing a CLI run, or two MCP triggers — are rejected fast
  with a typed error naming the holder, or retried to a finite deadline if the run explicitly asked for a bounded wait (a poll on the lock — no queue, no ordering or fairness guarantee)
  (`--params admission_wait_seconds=<n>`); they are never interleaved. Granularity is the
  pipeline's declared output set — concretely `pipeline.all_outputs()`, a deliberate superset that
  includes in-run intermediates because over-locking fails safe — so genuinely disjoint pipelines
  still run concurrently. The
  `in_process` executor in `conf/base/dagster.yml` remains what serializes ops *within* a single
  run — a different property, and on the Dagster plane a load-bearing one (`DW-AD23-2`). Four
  boundaries stand: file locks are single-machine (NFS `flock` is unreliable); release on the
  Dagster plane is process-local, and a *failed* Dagster run releases nothing in-process at all
  (its `on_pipeline_error` fires in the daemon, not the run worker); because kedro calls
  `before_pipeline_run` outside its `try` with admission dispatched first, a later before-hook
  that raises leaves the locks held until the process exits — as does a non-`Exception` exit
  from the runner, which kedro's `except Exception` does not catch and which therefore reaches
  neither `on_pipeline_error` nor `after_pipeline_run` — an availability wedge for the
  long-lived MCP server, not a correctness hole; and unlinking a lock file out from under its
  holder does not free that holder's flock, so the next acquirer takes a fresh inode at the
  same path — two writers, silently. That last one is a property of `flock`, not a
  configuration choice, and `DW-AD23-3` removed the routine way to trigger it: the store is
  the data tree's SIBLING (`<data_root>.locks`), not its child, so `rm -rf data/` cannot reach
  it, and a `PYFORGE_ATLAS_LOCK_ROOT` that would put it back inside is refused.
  Admission's first-dispatch position is enforced
  by `@hook_impl(tryfirst=True)`, not by its place in the `settings.HOOKS` tuple, which
  entry-point plugins would otherwise outrank.
- **No data-access logic in a node body, ever.** Sources, outputs, credentials, endpoints, and
  physical layout are catalog concerns; nodes are pure functions taking and returning
  dataframes. Credentials attach to a dataset's destination host only. Nodes carry no retries,
  no backoff, and no checkpointing — those are dataset and orchestrator concerns.
- **Offline degradation is skip-and-mark-stale, never raise.** When its endpoint is
  unreachable, an external-source node skips gracefully, **keeps the last-good dataset intact**
  (it never writes an empty dataset over it), and stamps a machine-readable staleness marker in
  dataset metadata. Consumers surface the marker and apply the freshness contract: data stale
  beyond its bound degrades the affected read or policy axis to `indeterminate`, never a silent
  pass. The consumer profile is fully offline by design. New external sources bind the standard
  rate-limit discipline: concurrency cap, `Retry-After` plus jittered backoff, remaining quota
  surfaced to the schedule.
- **New-signal datasets are additive riders and are excluded from the parity gate.** Parity
  compares legacy-surface outputs only; the conda-native vulnerability, velocity, and
  migration-readiness datasets are never parity-gated, and a parity delay does not block them.
  Their correctness is held instead by fixture-enforced binding guards — one per measured
  failure mode. The three riders and their pinned failure modes: `signals.md`.
- **Velocity qualifies on a 90-day window and computes against first availability.** A
  version-unchanged package whose upstream release is older than 90 days is excluded
  (`release_lag_qualifies = false`) — the guard against the false "half the channel is behind"
  reading. Lag is computed against the **minimum per-build repodata timestamp** for the matched
  version, never the latest upload, so a rebuild of the same version inside the window cannot
  shift the measurement. Both failure modes are fixture-pinned.
- **`version_status.v2.json` is deliberately excluded** from the migration-readiness ingest.
  Readiness is driven by the upstream `status/` category lists plus per-migration detail, so a
  new upstream migration requires zero code change; the aggregate file is not a source, and
  `not-in-tracker` membership is always labeled **inferred**, never reported as confirmed
  tracker status.
- **Seven closed domain pipelines; the producer owns the dataset.** The pipeline set is fixed.
  Each dataset has exactly one producing pipeline; a new signal joins its assigned pipeline,
  never a new ad-hoc one. Two pipelines writing one dataset is the failure this rules out.
  Allocation, every declared TTL, and the two freshness clocks: `catalog-contract.md`.
- **One store, one engine.** Partitioned Parquet is canonical and DuckDB is the only compute,
  graph, and vector engine — no separate graph, vector, or dataframe engine is reintroduced,
  and no dual store survives. Performance claims stay honestly scoped: incremental
  re-materialization is the headline; cold-start is benchmarked, never promised.
- **The legacy behavioral contracts bind the ports.** The shipped, fixture-guarded behaviors
  port intact with their fixtures green — the two-layer query-cost gate, the single-worker
  token bucket, provenance discipline on download sources, the serial gate, dedicated-feedstock
  attribution, no-clobber writeback, the KEV overlay and score-type unwrap, the `cfe:*`
  namespace and channel qualifier (never stripped), percentile normalization, view-validity
  discipline, and the single-write-path property. A story instruction never overrides these.
  The per-phase port map and the four contracts most often misread: `signals.md`.
- **The semantic layer is the single translation interface.** Metrics and dimensions are
  declared once; read surfaces consume them and never write raw SQL against the store. Catalog
  dataset passthrough for agent reads is not a metric surface and computes nothing. MCP tool
  bodies carry no metric or business logic — metric semantics live in exactly one place per era,
  with the parity gate anchoring the handover.
- **Validation is validator-agnostic and version-capped by policy.** Inline dataframe contracts
  are the primary layer; the boundary validator participates only behind the same hook and only
  at its pinned version — the cap is a policy statement, not merely a pin, and no story may
  depend on features above it. The validator-integration plugins are banned. A contract
  violation raises a native exception; the policy gate fails with identical semantics.
- **One frozen exit-code convention, one report producer.** Exit 0 pass / 1 policy-fail / 2
  error over the closed enum `{0, 1, 2, 130}`, with `indeterminate` projecting to 1, everywhere
  a CLI or gate exits. The compliance report is Warden's four-axis schema **unmodified and
  consumed by import** through an optional extra — never a vendored copy, so drift is impossible
  by construction. Exactly one terminal node assembles every report; upstream pipelines produce
  inputs and never assemble. Absent the extra, the gate node fails with an explicit install
  hint while every other pipeline runs.
- **Exactly one cross-package code edge, and it points one way.** This project may depend on
  `pyforge-warden` only through the optional gate extra; `pyforge-warden` never imports this
  package. Warden's consumption of atlas *data* is data-level and optional-if-present. Both
  tools install and run independently.
- **Gates are fixtures, never credentials — and are never weakened.** Every wave's first
  deliverable is its own deterministic gate; all gates are fixture-based, non-credentialed, run
  frozen, and live in the tracked test tree, never in the gitignored runtime data directory.
  The verify set grows and never shrinks. Gates are never weakened, removed, or demoted from
  attended to unattended to raise the autonomy share — attended boundary events are features,
  not friction. Credentialed runs are attended-only. The enumerated set — what each gate proves
  and what each refuses to do: `gate-contract.md`.
- **Pipeline snapshots are advisory, never authoritative for authoring.** Before acting, the
  recipe-authoring loop re-verifies live; no surface may position its datasets as a substitute
  for that check, and payloads feeding authoring decisions carry their build timestamp.
- **The factory layer consumes; it never writes atlas data.** Wiki and CMS components read
  pipeline outputs through the catalog and semantic layer and write only the wiki tree and the
  CMS; wiki outputs carry their source datasets' staleness markers forward, so republication
  never launders freshness.
- **Scope is closed at the committed source set.** New external data sources beyond the
  committed set are out of the migration's universe; candidate feeds are recorded, never
  committed, and promotion requires measured evidence becoming a requirement and a story.
  Static seeds, template trees, live authoring-time fetches, and user-supplied inputs are
  declared **inputs**, never pipeline products.
- **Identity and format conventions are fixed and non-negotiable.** Conda purls carry the
  channel qualifier; the `cfe:*` property namespace is preserved; versions compare by PEP 440;
  percentiles are stored on one scale; all timestamps normalize to epoch seconds **at the
  dataset boundary** (millisecond repodata values convert once). Canonical join keys are
  `conda_name` (plus feedstock attribution where it applies), `pypi_name`, and
  `(conda_name, advisory_id)`; the name-mapping dataset is the only bridge; **purls are
  interchange identity and never internal join keys**. Full identity table: `catalog-contract.md`.
- **Dataset schema evolution is additive-first.** New columns are nullable; a breaking change
  to a persisted dataset requires, in the same story, a catalog version note plus a migration
  node or re-materialization plus updated contracts and fixtures. No global schema-version
  constant returns.
- **Three degradation markers, never interchanged:** `stale` (dataset freshness) · `unresolved`
  (a resolver could not run) · `not-applicable` (nothing existed to assess). The policy mapping
  is fixed: `not-applicable` reports not-applicable; `unresolved` or stale-beyond-contract
  routes to `indeterminate`. Full projection and the Warden boundary: `degradation-contract.md`.
- **Conda-forge-only, pixi-managed, py3.14-floored provisioning.** Every component is
  conda-forge-sourced, pixi-managed, and scaffolded by the project generator; no standalone
  binaries and no JVM. Two PyPI-sourced components are **recorded exceptions** with packaging
  them as a candidate task — no further PyPI additions without the same recorded treatment. The
  package ships its own lean environment so loop worktrees never materialize the repo's fat
  environment, and any dependency change updates the library catalog in the same change.
- **Tracked config versus local config is a hard boundary.** Base configuration is tracked;
  local configuration holds credentials and is gitignored. Explicit environment or run-config
  always beats a profile default.
- **This Spec governs its code surface.** A change under the declared surface that does not
  move this Spec's memlog is a checker finding — the migration's code cannot drift out from
  under its contract. Behavioral change flows through this project's BMAD chain (stories,
  correct-course), and the chain companions above carry the per-requirement detail this
  contract compresses.
- **Conda-forge work inside this surface is skill-governed.** Any story touching recipe code or
  the packaging skill invokes the `conda-forge-expert` skill, and an effort closes with its
  retrospective — the repo's standing Rules 1 and 2, which this contract does not override.

### Satellite: Unity Data Stack constraints

> Folded in verbatim 2026-08-02 from `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-unity-data-stack/SPEC.md`,
> with `AD-n` renumbered to match the merged `ARCHITECTURE-SPINE.md`.

- **One authoritative lock (AD-25):** exactly one Workspace Lock (conda+PyPI together) is authoritative and committed; every other lock artifact (Exported Lock, Offline Bundle) is generated from it and drift-checked against one pinned commit SHA per release — never hand-edited, never a second resolution input.
- **Materialized coverage, never inferred (AD-26):** for every declared platform × every deployable Environment, a gate materializes the Environment from the lock and fails if it cannot; coverage is reported per platform, never as a single boolean.
- **One-way dependency direction (AD-30):** dependencies flow shared → platform-infrastructure → domain, never upward or sideways between Domains; a Domain consumes another Domain's *published* Data Product/API only, never its Package or datastore directly; a cycle detector runs in the Quality Gate.
- **Every Mandate machine-classified (AD-31):** each Constitution Mandate carries a stable identifier and a classification of exactly `platform-invariant` or `domain-default`; an unclassified Mandate, or a check with no declared Mandate, fails the Quality Gate.
- **Tasks, not inline commands (AD-32):** every gate check is a named task with a globally unique name; CI invokes task names only — no inline tool invocation, no inline installation, no environment mutation; a parity check and a name-uniqueness check both run in the gate.
- **Host-scoped credentials (AD-33):** credentials live only in the credential store or masked runner inputs; no committed file contains a credential-bearing URL in any form; no process receives a credential as a command-line argument; a request attaches a credential only when its host matches.
- **Lean-by-declaration Environments (AD-36):** every deployable Environment inherits no default dependency set and composes only what it names; installed size is measured against a recorded ceiling and a regression fails the gate (exempt: the FR-7 compatibility-detection Environment, explicitly non-deployable).
- **One accountable station per plane (AD-40):** each plane and cross-cutting concern resolves to exactly one pyforge-crew station (Marshal / Atlas / Warden / Mason / Steward / Doctor / Scribe / Herald); an unowned capability, or one claimed by two stations, is a defect — full map in the architecture-spine companion.
- **The Constitution's 14 Articles are the requirement spine.** Every FR traces to an Article or to its explicit disposition; 8 amendments are required before re-ratification. Full Article map and the 8 amendments are in `constitution-provenance.md` — not restated here.
- **The intake toolchain spec's flagship lock command does not exist:** `pdm export --format pylock --override-platform=...` has no such flag on `pdm export` (verified 2026-07-25); that exact mechanism cannot be reused as written, and PEP 751 itself does not guarantee multi-platform coverage — this is the empirical grounding for AD-25/AD-26 replacing an unverified format guarantee with gate-verified materialization. Detail in `constitution-provenance.md`.
- **Compliance by integration, not reimplementation (AD-29):** the compliance capability is `pyforge-warden`, consumed as a CLI in its own lean, isolated Environment — never imported as a library, never invoked only in CI; the gate's exit code derives from its Compliance Report file.
- **Python targets revised (Constitution Art. XIV amendment):** primary targets are 3.13 and 3.14; 3.12 is legacy-consumer-only (security-phase upstream); 3.15 first-releases 2026-10-01 and must be planned for inside this horizon.

### Satellite: Wasm Analytics Stack constraints

> Folded in verbatim 2026-08-02 from `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wasm-analytics-stack/SPEC.md`,
> with `AD-n` renumbered to match the merged `ARCHITECTURE-SPINE.md`.

- **Maturity verdict (the project's central scoping fact):** DuckDB's native engine has no WASI build and no WASI roadmap upstream, so `dlt`, `dbt-duckdb`, and DuckDB itself cannot run inside a genuine WASI component today. The WASI sandbox is therefore scoped narrowly to the pure-Python upload-validation step only; a future `wasm32-wasi` build target for ingestion or transform requires an ADR amendment citing new upstream evidence, not an incremental extension of this project.
- **AD-47, trust-boundary data shape:** the validation component's WIT interface accepts and returns only primitive/record types (strings, numbers, booleans, lists, records) — never a host-shared-memory or buffer type. No Arrow buffers, no raw Excel bytes cross the WIT boundary; Excel bytes are parsed into rows entirely outside the sandbox, before the WIT call.
- **AD-48, denylist is a build gate:** `pixi run build` runs a static-import-scan against the validation component's source and its resolved dependency closure, failing the build — not merely a policy or PR-review expectation — on any denylisted import, direct or transitive.
- **AD-50, the isolation gate must be non-hollow:** it ships with a meta-test from its first version — deliberately widening the component's declared WIT capabilities without a matching interface change must make the gate fail — and it runs on every build.
- **AD-51, one trace-ID field:** `upload_trace_id` is always the bare 32-hex-character W3C trace-id (never the full `traceparent` string, never a UUID, never dashed), minted once at FastAPI ingress, and is never conflated with OpenLineage's own separately-minted `runId`.
- **AD-52, one securityContext, two consumers:** a single canonical security-context definition is authored once under `deploy/`; the Helm chart and the Podman compose file both consume it via a generation step, neither hand-authors its own copy.
- **AD-53, DuckDB single-writer:** each validated upload triggers exactly one `dlt` load followed by exactly one `dbt run` scoped to that load — 1:1, never batched — both invoked sequentially by the same owning process; a move to concurrent or batched transforms is a scope change requiring an ADR amendment.
- **AD-54, air-gap-routable dependency fetch:** every build-time fetch (Pixi packages, DuckDB extensions, the `componentize-py`/Wasmtime toolchain) routes through the configured channel/mirror; no build script hardcodes a public URL.
- **AD-55, synchronous upload:** `POST /upload/excel` blocks through parsing, WASI validation, and returns the full per-row result in one HTTP response; the returned trace ID is a correlation handle for observability/lineage lookups, not a polling handle — there is no V1 polling endpoint.
- **AD-56, authentication at the ingress boundary:** OIDC token validation happens at a sidecar/gateway boundary in front of `apps/api/`, never embedded per-request inside the application code itself.

### Reconciliation notes (2026-08-02 consolidation)

No contradiction was found between the primary Atlas contract and either
satellite's non-goals/constraints — the three bodies of work govern
disjoint code surfaces (Atlas: `src/shared/packages/pyforge-atlas/**`;
Unity: `constitution.md`/`config/**`/`templates/**` at an as-yet-unbuilt
repository root; Wasm: `apps/**`/`deploy/**` at an as-yet-unbuilt repository
root), so no rule in one binds code the other two own. One difference is
worth naming explicitly rather than leaving implicit: **the three bodies of
work commit to three different Python floors** — Atlas is conda-forge-only,
pixi-managed, and **py3.14-floored** (exact-minor pinned, shipped); Unity's
Constitution Art. XIV amendment targets **primary 3.13/3.14, 3.12
legacy-consumer-only**; Wasm's host/pipeline processes pin **3.12** as a
deliberately conservative, explicitly revisitable stability floor (nothing
in its pinned dependency set forces it). This is not a conflict to resolve
— each project owns its own environment and dependency closure — but a
reader of this merged Spec should not assume one floor applies across all
three.

## Non-goals

- **A public, versioned API tier** — access is agent-mediated (MCP + `a2a`) and
  no HTTP surface exists. **Deferred, not refused**: it is committed as a real
  future capability, tracked as **DC-1** in the PRD § 6.4. Non-goal *for this
  scope*, not forever.
- **Live production bring-ups** — Dagster daemon, PostgreSQL servers and an
  RWX-capable storage class, live Wagtail, agno LLM synthesis, and the production
  `vss` retriever each ship a seam and run against local/embedded defaults.
  *(Storage kind re-pointed 2026-09-09, batch § 2.3 C16 / row atlas-B6: this line
  read "MinIO/PostgreSQL servers", a phrase inherited from atlas's own DW-H1 ledger
  heading rather than chosen here. `docs/dreams/pyforge-unifying-strategy.md:406-408`
  — "No MinIO as a fourth core kind", re-affirmed 2026-09-05. The Non-goal itself is
  unchanged: this Spec provisions no servers.)* Tracked as **DC-2…DC-6** in the
  PRD § 6.4. *(Each was properly deferred at build time — `DW-C1-1`/`DW-G3`,
  `DW-H1`…`DW-H4`. The live Tier-3 ledger is truncated to 9 and gitignored, but the
  complete set of **52** is consolidated and tracked at
  `planning-artifacts/deferred-work-ledger.md`; DC-2…DC-6 are the contract-level
  re-statement of the six that outlived the migration.)*

- **A separate graph, vector, or dataframe engine** — one engine, by decision, not by omission.
- **Continued SQLite and hand-rolled checkpoint-table orchestration.**
- **Standalone binaries or JVM dependencies**, and any non-conda-forge provisioning path
  outside the two recorded exceptions.
- **An alternative agent framework** — the BMAD method governs execution.
- **New external data sources beyond the committed set**, and any candidate-feed promotion
  without measured evidence. Do not ship "more sources" to look busier.
- **A metadata backend swap to the upstream GraphQL API** (a recorded hook only, for the
  deferred full yanked-status detection).
- **A public OSV-format export feed and public dashboard productization** — demand is feeds over
  pages; the single factory-status page is the intentionally narrow public surface and does not
  grow.
- **Enterprise manifest generation as a deliverable** — the graph enables it; this does not
  build it.
- **Spreadsheet tabs and project boards as SBOM-intake formats.**
- **Building the compliance-report schema** — it is Warden's contract, consumed by import.
- **Rewriting the recipe-authoring skill itself.**
- **Chasing cold-start wall-clock**, raising the autonomy share by weakening gates, growing the
  signal count for its own sake, or growing dashboard breadth — the four standing anti-metrics.
- **Live authoring-time fetches as pipeline data** — transactional by nature, and pipeline
  snapshots never substitute for the authoring loop's live re-verification.
- **The upstream-discovery surface** — trending and org-audit ingestion is a separate Spec in
  this project (`spec-upstream-discovery`) and was never absorbed into this migration's stories.
- **A unified observation view** across the loop TUI, the BMAD artifact dashboards, and the
  pipeline UIs — three deliberately unjoined planes.

### Satellite: Unity Data Stack non-goals

> Folded in verbatim 2026-08-02 from `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-unity-data-stack/SPEC.md`.

- Unity is not an Internal Developer Portal — no catalog UI, no service-discovery portal; it emits catalog-consumable facts, an adopter running Backstage integrates rather than migrates.
- Unity is not a build-graph engine — no attempt to out-cache Pants, Bazel, or Nx on fine-grained caching or remote execution; orthogonal and unwinnable.
- Unity does not maintain a second registry of truth — manifests are the source; catalogs, ownership maps, and portal feeds are all derived.
- Unity is not a product to be sold — it is a platform an enterprise runs.
- Unity does not replace a Domain's judgement about its own data models — global interoperability concerns are Platform Invariants, local modelling is a Domain Default.
- Unity does not target SLSA Build L3 in v1 — L1 mandatory, L2 goal; L3 needs hardened builders, deferred.
- Unity does not perform data-content inspection in v1 — Data Classification is enforced at the configuration boundary only (which datastore, which network), not content-level PII detection/masking/deletion.
- Unity is not a general-purpose polyglot monorepo — Python-first by mandate.
- Bootstrapping new Unity instances — depends on `pyforge-genesis`, unbuilt; a v2 dependency.
- Local Kubernetes development — the required cluster tool isn't available through the mandated channel on every platform; the intake root's documented stub stands.

### Satellite: Wasm Analytics Stack non-goals

> Folded in verbatim 2026-08-02 from `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wasm-analytics-stack/SPEC.md`.

- A general-purpose Wasm-sandboxing framework for arbitrary third-party logic — the WASI boundary in v1 is scoped exclusively to the Excel-upload validation step.
- Running `dlt`, `dbt`, or DuckDB itself inside a WASI Preview 2 sandbox — blocked at the DuckDB-dependency level per the technical research, not a scoping choice to revisit without new upstream evidence.
- Apache Arrow buffers as the host↔WASI-component interchange format — deferred pending a confirmed `pyarrow`-in-WASI path or an Arrow-maintained WASM/WASI interchange primitive.
- A browser-side query/dashboard surface onto Gold tables — v2, would reuse the `pyforge-atlas` G1 DuckDB-WASM/Pyodide pattern directly rather than reinvent it.
- A general ingestion platform for arbitrary source types — Excel upload is the only ingestion path in v1.
- Multi-tenant Unity Data Stack platform integration — a kinship, not a v1 commitment.
- Migration to `dbt Fusion` (the Rust engine) — blocked until it gains a DuckDB adapter; a watch item, not scheduled.

## Success signal

An agent adds a new signal by writing a node, declaring its datasets, and attaching a
contract — and inherits checkpointing, TTL, backoff, scheduling, validation, lineage, and
tracing without writing one line of any of them. That is the whole bet, and it is proven
mechanically rather than asserted.

Six deterministic, non-credentialed, fixture-based gates hold the contract, each shipped as its
wave's first deliverable and never weakened afterward: `kedro-test` (unit and contract
fixtures, including the namespace-package import smoke), `kedro-catalog-check` (the catalog
resolves; **no inline IO** survives in node bodies; the import-direction ban holds; the 20
override points and per-host credential scoping are asserted), `parity-diff` (fixture mode
in-loop, credentialed full run at the attended boundary), `dagster-dryrun` (definitions load;
jobs, schedules, and sensors enumerate without live execution), `bsl-metric-check` (declared
metrics answer as the legacy CLIs did), and `wasm-smoke` (a headless browser loads the built
artifact, asserts zero non-loopback requests, and fails on an in-page error). Beside them: a
grep gate proving no SQLite path survives the migrated surface, exit-code and schema fixtures on
the policy gate, a byte-identical-seed test on the read-only suggesters, and one fixture per
named measurement failure mode on the new signals.

The shipped evidence: **32 of 32 stories across Waves 0 and A–H, merged through PRs #69–#102,
2026-07-17/18** (#74 and #89 in that range belong to other efforts; #103 is the CFE Rule-2 retro
closeout and #105 a follow-up review sweep) — the parity **harness** delivered and
fixture-green, three new
signals landed through declared machinery with zero hand-written checkpoint code, and every
loop-driven story executed without a gate being removed to get there.

**What `shipped` does and does not mean** *(added 2026-07-27, `AUD-ATLAS-047` / `AUD-ATLAS-049`)*.
`status: shipped` means **the 32 stories merged** — not that every attended boundary event has
been discharged. Three remain outstanding as of 2026-07-27:

- **The credentialed parity run, operator sign-off, and legacy retirement have not occurred.**
  `conda_forge_atlas.py` remains live at ~402 KB; the retirement gate refuses fixture mode by
  design (`DW-B4-2`). This section previously read "parity recorded and signed before the legacy
  orchestrator retired" — that was an overclaim.
- **The F1 cold/warm benchmark was never run** (`DW-F1-1`). The DuckDB-singularity half of F1
  shipped; the performance half did not. Per SM-3 the pass threshold must be fixed in the story
  spec *before* the benchmark runs.
- **The live Dagster daemon has never ticked** a schedule or sensor (`DW-C1-1`, `DW-G3`,
  `DW-H4`); definitions build and validate offline only.

### Satellite: Unity Data Stack success signal

> Folded in verbatim 2026-08-02 from `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-unity-data-stack/SPEC.md`
> (status: planning-complete, unscheduled — no epics/stories/code yet; SM-n
> below is local to `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-unity-data-stack-2026-07-25/prd.md`).

Onboarding: a new engineer reaches a running local stack with a passing package test using only written documentation, in under an hour, single-digit commands (SM-1). Cross-team reuse — the innersource proof — trends up (contributions merged into Packages the contributor doesn't own) while the internal-fork counter-metric does not rise in step (SM-2 vs. SM-C1); if it stays near zero, the platform has failed at its premise regardless of technical quality. Reproducibility is verified, not assumed: 100% of declared platforms materialize every Environment from the lock, online and offline (SM-4). Compliance latency — time from vulnerability publication to a determination of estate impact — is measured in minutes, ahead of the EU CRA's 2026-09-11 reporting-obligation deadline (SM-5). Air-gap parity reaches 100% of enumerated capabilities, with any exception explicitly declared, never silently degraded (SM-6).

### Satellite: Wasm Analytics Stack success signal

> Folded in verbatim 2026-08-02 from `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wasm-analytics-stack/SPEC.md`
> (status: planning-complete, unscheduled — no epics/stories/code yet; SM-n
> below is local to `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-wasm-analytics-stack-2026-07-25/prd.md`; `CAP-27`
> below was `CAP-1` in the standalone document).

The seed use case — Excel upload → WASI-validated → DuckDB Bronze → Silver/Gold via `dbt`, traced end-to-end — runs correctly and identically under `podman --read-only --user 1001` locally and under real OpenShift Restricted SCC, with the WASI validation component's sandboxing mechanically verified, not just asserted (SM-1). The Isolation-Verification Gate passes on every build and demonstrably fails when the component's declared capability surface is deliberately widened without a corresponding WIT change — the non-hollow-gate proof (SM-2). The project ships zero claims beyond what the technical research verified as buildable today. Two counter-metrics guard against gaming the primary signals: growing workaround complexity in the denylist (SM-C1) is a signal to reconsider the WASI-sandboxing bet, not a target to minimize by weakening the boundary; and upload-validation latency must never be optimized by moving checks out of the sandbox back into the trusted process (SM-C2), which would defeat CAP-27's entire purpose.

## Assumptions

- The story set is **complete** (32/32, 2026-07-18), so this contract is written in the present
  tense as a standing description of what Atlas is, not a plan for building it.
- The stack bets remain current: a 2026-07-25 currency review found every component actively
  maintained with no deprecations. The orchestration binding's single-maintainer bus factor is a
  confirmed **watch item**, not an active problem — the recorded exit ramps are the standing
  mitigation, and the replaceable-glue constraint is what makes them cheap.
- Scope discipline — conda-forge-only, one operator plus an agent workforce — is a deliberate
  design choice validated against the general-purpose cross-ecosystem comparables, not a gap.
  Those platforms are architectural reference points only; Atlas is internal and non-commercial.
- Several capabilities ship their **decision logic and seams** with live bring-up deliberately
  deferred and recorded: the persistent orchestration daemon, the object-store and database
  servers behind the factory layer, the live CMS transport, agent-LLM synthesis in the crews,
  and the production embedding retriever. Each is injectable, offline by default, and gated by
  fixtures — the contract is that the seam exists and defaults safe, not that the service is
  running.
- The prototype DAG mirror inside the surface is **generated, not hand-maintained**; it moves
  only when the real pipeline structure moves, which is exactly when this contract should move
  too.

### Satellite: Unity Data Stack assumptions

> Folded in verbatim 2026-08-02 from `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-unity-data-stack/SPEC.md`.
> `AD-25` below (was `AD-2`) is renumbered to match the merged
> `ARCHITECTURE-SPINE.md`; unresolved items are carried to
> § Open Questions (satellites) below.

- **Pixi-primary lock architecture:** the Workspace Lock (`pixi.lock`) is authoritative; `pylock.toml` is a derived PEP 751 export; offline deployment uses `pixi-pack`/`pixi-unpack`. Conda-native resolution is the differentiator and the alternative (PDM/PEP-751-primary) would discard it. This is the architecture's resolution (AD-25) but see § Open Questions (satellites) — it still needs explicit human ratification.
- V1 targets SLSA Build L1 mandatory, L2 (signed provenance from a hosted build platform) as the goal; L3 is out of scope.
- V1 delivers the Domain pattern plus one worked reference Domain (`customer`); the remaining ten Domains are adoption work, not build work — see § Open Questions (satellites), this changes MVP effort by an order of magnitude if wrong.
- Data Classification is enforced at the configuration boundary; content-level inspection is deferred to v2.
- Primary Python targets are 3.13 and 3.14; 3.12 is legacy-only; 3.15 (2026-10-01) must be planned for inside this horizon.

### Satellite: Wasm Analytics Stack assumptions

> Folded in verbatim 2026-08-02 from `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wasm-analytics-stack/SPEC.md`.

- Python 3.12 is chosen as a conservative stability floor for host/pipeline processes, even though nothing in the pinned dependency set (`dlt`/`dbt-core`/`dbt-duckdb`/`duckdb` all support through 3.14) forces it — revisitable.
- Marquez's actual deployed image/version needs re-verification at implementation time; its last GitHub release tag (0.50.0, 2024-10-24) is stale relative to active repo development, and Marquez ships primarily via Docker/Maven rather than GitHub release tags.
- No cost ceiling, no air-gap-routing detail beyond the general `enterprise-airgap` posture, and no SLA/RTO/RPO commitment is stated in the founding Dream or brief; none should be assumed by downstream work until resolved.

## Resolved questions

All four closed **2026-07-25**; `open_questions[]` is empty. Recorded here rather
than deleted, so the disposition is auditable. (This section covers the
**primary** Atlas Spec only — the two satellites carry their own,
still-open questions; see § Open Questions (satellites) at the end of this
document.)

- **Does Atlas expose a public, versioned API tier?** → **Yes, eventually.**
  Deferred as a real capability, *not* closed as a non-goal. Tracked **DC-1**
  (PRD § 6.4). Today: MCP (11 tools) + `a2a`, both agent-mediated; no HTTP
  surface exists. Landed in § Non-goals as a scope-bounded non-goal.
- **Where does an upstream-maintenance signal live?** → **A Warden axis**, not an
  Atlas feed. Resolved from the Warden contract itself; no operator decision was
  needed. Landed in § Constraints.
- **What closes the deferred live bring-ups?** → **Tracked deferral.** The five
  become **DC-2…DC-6** (PRD § 6.4) — owned and visible, not scheduled. Landed in
  § Non-goals. *Correction on the record:* the first pass claimed they appeared in
  no ledger. They did — `DW-C1-1`/`DW-G3`/`DW-H1`…`DW-H4`. The Tier-3 ledger is
  **truncated to 9** and gitignored, so the deferrals were honest and their *live*
  record was lost — but the full set was recovered into Tier-2. *Second correction
  (2026-07-27):* the run log's index of "54" double-counted two aliases
  (`DW-A2-P4` → `DW-B5-3`, `DW-D2` → `DW-D2-2`). The true count is **52**, all
  present in `planning-artifacts/deferred-work-ledger.md`. Nothing was lost.
- **Do the 8 optional per-epic retrospectives run?** → **They run.** Not waived.
  Sprint-status carries 9 retro entries — 8 `optional`, 1 `done` (epic-9). The
  CFE Rule-2 retro landed separately as v8.79.0; these 8 are additive. Process
  disposition only — bends no design decision, so it lands in no kernel field.

## Open Questions (satellites)

Unlike the primary Atlas Spec's `open_questions[]` (empty — all resolved,
see § Resolved questions above), both satellites carry genuinely open
questions, honestly preserved rather than silently resolved by this
2026-08-02 consolidation. Neither is invented away here.

### Satellite: Unity Data Stack open questions

> Folded in verbatim 2026-08-02 from `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-unity-data-stack/SPEC.md`.
> `AD-25`/`AD-31` below (was `AD-2`/`AD-8`) are renumbered to match the
> merged `ARCHITECTURE-SPINE.md`.

- **Lock authority (blocks everything):** is the Workspace Lock authoritative with the PEP 751 export derived, or the reverse, or split by tier? The architecture (AD-25) already resolves this as workspace-lock-primary and this Spec carries it as an assumption, but it still requires explicit **human confirmation** before any build work begins — it has not yet been independently ratified.
- **V1 Domain count (order-of-magnitude sizing):** does v1 ship the pattern plus one worked Domain, or all eleven? Carried as an assumption above but not confirmed at sign-off.
- **Platform Invariant vs. Domain Default classification:** AD-31 supplies the classification *mechanism*, but which specific Mandates get which classification is an unresolved sign-off decision — it directly determines whether Unity is genuinely federated/innersource (Data Mesh principle 4) or centrally imposed in practice.
- **Governance boundary:** where does the Constitution's spec-kit governance end and this repo's BMAD planning chain begin? Both are live simultaneously; unresolved, and the two risk drifting independently without an explicit decision.

### Satellite: Wasm Analytics Stack open questions

> Folded in verbatim 2026-08-02 from `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wasm-analytics-stack/SPEC.md`.
> `AD-55` below (was `AD-9`) is renumbered to match the merged
> `ARCHITECTURE-SPINE.md`.

- **Upload size / latency budget:** exact maximum upload file size and the expected weekly row-count/latency budget for the "within seconds" claim — needed before Architecture can size the validation component's performance envelope; a large-enough file may force revisiting the synchronous-upload design (AD-55) via ADR amendment.
- **Named regulatory framework:** which specific framework(s), if any, this deployment must satisfy beyond Restricted SCC + OIDC (HIPAA, PCI-DSS, SOX, none) — a named framework would likely add audit-log retention and encryption-at-rest requirements not yet captured.
- **`componentize-py` rule-configuration redesign:** does the build-time-only import restriction force a redesign of the validation component's rule-configuration mechanism, if rules were meant to be dynamically loaded per file-type?
- **Operational ownership:** who is on-call for this pipeline in production, and what SLA (if any) applies to validation/ingestion latency — needed before Architecture commits to a specific deployment topology.
- **Data classification and retention:** no scheme (PII, confidential) is defined for Bronze/Silver/Gold or Marquez's lineage history; if the seed use case's actual data (headcount/cost) carries PII, this adds retention/access-control requirements not currently specified.

## Currency pass — 2026-09-09

**Status holds.** `status: shipped` and the owner Dream's `realized` both survive the exercised
realization gate: the pipelines, the MCP face, the BSL models and the Vizro board all run. Two
body claims were behind the station and are re-grounded above — the story count (see
`shipped_scope_note`) and the deferred 28-CLI page inventory (CAP-8; DW-D2-1 is closed).

**CLI⇄tool parity gate → Story 25.3.** An incoming cross-station claim (decision batch § 2.3 C10,
marshal-A finding E6 → mason/atlas): atlas's MCP tools — like the 46 conda-forge-expert tools —
have **no CLI⇄tool parity gate**. The governed front door is the HTTP station face
(`mcp_http.py:137`, `POST /stations/atlas/mcp`) with stdio servers as local adapters, but nothing
asserts that every `pyforge atlas …` verb has a tool and vice versa. It lands as **Epic 25 Story
25.3**, "Atlas's MCP tools pass the CLI⇄tool parity gate" (ledger `backlog`), not as an Epic 24
rider.

Grounding found while minting it, worth keeping: atlas is the ONE station the unified front door
cannot AST-introspect — `pyforge.core.dispatch.PREPARATORY_UNINTROSPECTABLE['atlas']`
(`core/dispatch.py:29`) points at steward's `spec-22-prep-atlas-kedro-cli-introspection`
(`status: ready`, never minted as a ledger key), whose own Approach says "a later story must
generate the CAP-5 parity matrix for atlas verbs from Kedro's own command surface, still without
reimplementing pipelines in core". **Story 25.3 IS that story.** The one-line `pyforge-core` edit
it implies is steward's surface — split it, or land a steward memlog line first, or
`spec-surface-check` reds at merge. C10's other half, the 46 CFE tools, stays mason's.

