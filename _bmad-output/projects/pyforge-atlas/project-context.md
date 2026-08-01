---
project_name: 'pyforge-atlas'
project_phase: 'shipped'
user_name: 'rxm7706'
date: '2026-08-04'
sections_completed: ['technology_stack', 'critical_implementation_rules', 'testing_patterns', 'execution_model', 'code_grounded_patterns']
---

# Project Context for AI Agents — pyforge-atlas

_Critical rules and patterns that AI agents must follow when implementing code in this project. This is the Kedro/Dagster/DuckDB migration of cf_atlas, currently shipped (31/31 stories complete as of 2026-07-25)._

---

## Technology Stack & Versions

**Core Orchestration:**
- Kedro 0.19.x+ (pixi-managed, Python 3.14 floor)
- Kedro-Dagster bridge (kedro-dagster for `KedroProjectTranslator`)
- Dagster (unspecified latest via pixi; schedules + retries + per-node timeouts)
- DuckDB (replaces SQLite; single compute + analytics engine)

**Data & Schema:**
- Parquet (primary store; TTL gating via `IncrementalParquetDataset` with per-dataset TTLs, never global)
- Ibis (semantic layer translation to DuckDB, read-only)
- Pandera (v1.18.2 **hard-capped**, no 1.19+ features; data-quality contracts before bad data lands)
- Great Expectations (≤1.18.2, behind validator-agnostic hook; never load-bearing)

**Observability & Compliance:**
- OpenLineage (per-node, end-to-end lineage)
- OpenTelemetry (traces resolve to named API calls)
- CycloneDX (universal SBOM ingest; `cfe:*` namespace + `?channel=conda-forge` qualifier preserved always)

**Frontend & Agents:**
- Vizro / Vizro-AI (read surface, replaces 28 CLIs; three CLI-first exceptions for latest-report artifacts)
- MCP tools (`kedro-mcp` authored over session/catalog APIs, never load-bearing; `query_vizro_ai` read interface)
- Pixi 0.26+ (environment isolation; loop worktrees lean, re-buildable)

**Development & Testing:**
- pytest (all verify gates use pytest; fixture-based, offline, `--frozen` mode)
- deptry (dependency-hygiene scan node; source-less inputs report `not-applicable`, never fail)

---

## Critical Implementation Rules

### 1. Testing Contract — Fixture-Based, Non-Credentialed, Frozen

**Rule (NFR-1, NFR-2, NFR-5):**
- ✅ All verify gates **must** be fixture-based, non-credentialed, run `--frozen`, and live in the tracked test tree.
- ✅ Never place test data in `.claude/data/` or any gitignored location.
- ✅ Credentials scope per destination host; a non-JFrog host **never** receives `X-JFrog-Art-Api`.
- ✅ Credentialed runs are attended-only (human present at execution).
- ✅ `llms-full-check` **must** pass after any dependency change (validate via `pixi run -e local-recipes llms-full-check`).

**What this means for agents:**
- Write tests using pytest fixtures that load test data from the tracked tree (`tests/fixtures/`, etc.).
- Never hardcode credentials; use environment variables or credential scope rules.
- If a test needs network access, provide a fixture that substitutes offline data.
- Offline/air-gapped degradation is skip-and-mark-stale, never fail (NFR-3).

**Files:**
- `src/shared/packages/pyforge-atlas/tests/` — all test files live here, tracked.
- Verify gates: `kedro-test` (import smoke + scaffold layout), `kedro-catalog-check` (AD-1 meta-tests), `parity-diff` (Wave B fixture parity), `bsl-metric-check` (Wave D metric parity), `dagster-dryrun` (Wave C Definitions load-only).

### 2. Architectural Boundaries — Import-Direction Meta-Tests (AD-1)

**Rule (NFR-5, Spine § Consistency Conventions):**
- ✅ No Dagster, `kedro-mcp`, or agent imports in `pipelines/`, `datasets/`, `hooks/`, `mcp/`.
- ✅ Core domain logic is **always** in `pipelines/` and `datasets/`; orchestration/MCP concerns are layered above.
- ✅ The `AD-1 import-direction meta-test` is **binding** — it ships with `kedro-catalog-check` and must pass in CI.

**What this means for agents:**
- When writing a new node or dataset, keep orchestration imports out of the core definition.
- Place Dagster op wrappers or MCP tool definitions in a separate layer that *imports* from pipelines, not vice versa.
- If you're adding a node to a pipeline, ask: "Does this import Dagster directly?" If yes, refactor the core logic into a pure function first.

**Files:**
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/` — domain pipelines, zero orchestration imports.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/` — Kedro datasets, zero orchestration imports.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/hooks.py` — Kedro hooks, no Dagster.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/` — MCP tool layer, orchestration-aware.

### 3. Naming & Schema Consistency (Spine § Consistency Conventions)

**Rule (Binding on all stories):**
- ✅ Pipeline packages: **snake_case** (e.g., `ingest_conda_forge`, `analyze_sbom`).
- ✅ Dataset names: `<domain>_<entity>` with layer tags (e.g., `conda_feedstock` vs `feedstock_enriched`; layer tag suffix).
- ✅ Canonical join keys: `conda_name` / `pypi_name` / `(conda_name, advisory_id)` — **never** use purls as internal join keys.
- ✅ Timestamps: normalized to **epoch seconds** at ingest (never milliseconds or ISO strings in the columnar store).
- ✅ Schema evolution: **additive-first** — new columns are added, never dropped; renamed columns require a deprecation period.
- ✅ Degradation vocabulary: `stale` / `unresolved` / `not-applicable` — **never interchange** these terms.
- ✅ All legacy provenance: `# legacy: Phase <ID>` comments in code showing which phase a refactored node came from.

**What this means for agents:**
- Before creating a dataset, check the existing catalog for naming patterns; follow them exactly.
- If merging two tables, use the canonical join key — don't invent a new one.
- When timestamps arrive as ISO strings, convert to epoch seconds at the ingest node.
- If you need to remove a column, mark it deprecated first in a release, then drop it in the next.

**Files:**
- `src/shared/packages/pyforge-atlas/conf/base/catalog.yml` — the Kedro catalog (source of truth for dataset definitions).
- `src/shared/packages/pyforge-atlas/conf/base/parameters.yml` — pipeline parameters (environment/run config).

### 4. Exit-Code Convention — Frozen, Universal (NFR-6)

**Rule (Binding on all CLI and gate exits):**
- ✅ Exit code **0** = pass
- ✅ Exit code **1** = policy fail (data quality, compliance gate failed, etc.)
- ✅ Exit code **2** = error (exception, crash)
- ✅ Exit code **130** = interrupted (e.g., SIGINT)
- ✅ Indeterminate state always maps to **1** (policy fail).
- ✅ Never use other exit codes; `indeterminate` → 1 is binding.

**What this means for agents:**
- When adding a gate or CLI command, use these exit codes exclusively.
- In error handling, distinguish between "data rejected" (1) and "code crashed" (2).
- Never use exit code 42 or other ad-hoc values.

**Files:**
- Any new CLI under `src/shared/packages/pyforge-atlas/__main__.py` or sub-CLIs.

### 5. Compliance Report Structure (NFR-6, FR-18)

**Rule:**
- ✅ Four-axis `ComplianceReport` with **frozen exit-code convention** (0/1/2, full enum {0, 1, 2, 130}).
- ✅ `inventory-match` enum has a one-release `INVENTORY_MATCH_LEGACY_EXIT=1` window (for backward compatibility, deprecated).
- ✅ All gates produce a `ComplianceReport` or compatible JSON structure for integration with the CI exit-code gate.

**What this means for agents:**
- If adding a new compliance check, structure it as a `ComplianceReport` with the four-axis fields.
- Use the frozen exit codes; don't create per-report codes.

### 6. Offline & Air-Gap Degradation (NFR-3)

**Rule:**
- ✅ Offline/air-gapped degradation is **skip-and-mark-stale**, never fail.
- ✅ Last-good dataset is kept intact and reused.
- ✅ Consumer profile fully offline (can materialize, query, export without network).
- ✅ If a credential scope rule blocks a request, mark the data as stale; don't error.

**What this means for agents:**
- When writing a data-fetch node, wrap it in a try-except that marks the dataset stale on network failure.
- Keep the last successful Parquet file; query it if a refresh fails.
- Use the `not-applicable` degradation token for nodes that don't apply in offline mode.

---

## Testing Patterns

### Verify Gate Structure

Each wave has a dedicated `pytest` gate:

| Wave | Gate | Command | Purpose |
|---|---|---|---|
| 0 | N/A | N/A | Execution scaffolding |
| A | `kedro-test` | `pytest src/.../tests -q` | Import smoke + scaffold layout |
| A | `kedro-catalog-check` | `pytest src/.../tests/catalog -q` | AD-1 meta-tests + 20 override points |
| B | `parity-diff` | `pytest src/.../tests/parity -q` | Fixture-mode parity diff vs legacy snapshots |
| C | `dagster-dryrun` | `pytest src/.../tests/orchestration -q` | Definitions load-only (no daemon) |
| D | `bsl-metric-check` | `pytest src/.../tests/semantic -q` | Metric-parity re-implementation check |

### Fixture Patterns

- **Captured legacy snapshots:** `tests/fixtures/parity/` contains DataFrames captured from the legacy orchestrator; Wave B parity gate compares migrated nodes' output to these fixtures.
- **Stub credentials:** `tests/fixtures/credentials/` contains safe, non-secret credential placeholders for testing (e.g., `MOCK_JFROG_TOKEN`).
- **Offline data:** `tests/fixtures/data/` contains static Parquet files for offline gate runs.

---

## Execution Model

### Worktree & BMAD Integration

**Rule (Spine § Execution Seam, AD-18):**
- ✅ Loop stories run in worktrees only after the symlink bootstrap (Story A3).
- ✅ All BMAD writes resolve through the `_bmad-output` symlinks.
- ✅ Switching active project: `scripts/bmad-switch pyforge-atlas` (never hand-edit symlinks).
- ✅ Keystone stories (B1, B2, F1) get pre-flight budget raises (longer time-box).

### Pixi Environment

**Rule (FR-15, NFR-5):**
- ✅ Pixi-first, nebi-scaffolded, conda-forge-only toolchain.
- ✅ Python 3.14 floor (no 3.13 or earlier).
- ✅ Lean env for loop worktrees (re-buildable, ~3 GB storage budget including vdb).
- ✅ All dependencies tracked in `pixi.toml`; no pip-installed packages outside of pixi.

### conda-forge-expert Rule (CLAUDE.md Rule 1)

**Rule:**
- ✅ Any story touching recipe code or atlas tooling invokes `conda-forge-expert` skill first.
- ✅ The skill's 9-step loop and Operating Principles are authoritative.
- ✅ After effort closes, Rule-2 retro improves the skill based on findings.

---

## Performance & Honesty (NFR-4)

**Rule:**
- ✅ Incremental re-materialization is the headline claim and must be benchmarked.
- ✅ Cold-start is benchmarked, never promised.
- ✅ Per-node timeouts are explicit; the 1800 s coarse-cap silent-phase-drop is **structurally impossible** (NFR-9).

---

## Deferred Decisions

Resolved inside named story specs:
- **A1:** Physical naming / namespace package location (resolved 2026-07-17 as `src/shared/packages/pyforge-atlas/` + `pyforge.atlas`).
- **E1:** A2A transport mechanism.
- **F3:** Embedding model + offline `vss` provisioning.
- **F1:** Benchmark threshold for incremental speed gains.
- **H1:** MinIO server provisioning.
- **D2:** CIS two-spine design specs (`DESIGN.md` + `EXPERIENCE.md`).
- **Conditional surface:** If trendshift Track A ships Phase T before Wave B completes, Phase T joins the migration surface — re-check with live groundtruth at execution start.

---

## Code-Grounded Implementation Patterns (Session 2026-08-04 Enrichment)

### Complete Module Directory Structure

The actual `src/pyforge/atlas/` tree contains more top-level modules than the initial doc listed. **Full directory:**

Core orchestration & data:
- `pipelines/` — domain pipelines (ingest_conda_forge, analyze_sbom, etc.)
- `datasets/` — Kedro dataset classes
- `hooks.py` — Kedro hooks (lifecycle registration)
- `pipeline_registry.py` — dynamic pipeline discovery (the **critical** file for node wiring)

Data operations:
- `semantic/` — Ibis metric expressions + boring-semantic-layer bindings (FR-8)
- `a2a/` — A2A (agent-to-agent) interface for inter-agent collaboration
- `parity/` — Wave B parity verification fixtures + tooling

Support modules:
- `observability.py` — **SOLE** module allowed to import openlineage/opentelemetry
- `provenance.py` — legacy provenance tracking + CFA commit pins
- `admission.py` / `validation.py` — data-quality check enforcement
- `settings.py` — configuration + credentials scoping rules
- `__main__.py` — CLI entry point

Analytics/publishing:
- `dashboard/` — Vizro pages (replaces 28 legacy CLIs)
- `publish/` — export/artifact delivery
- `nl/` / `factory/` / `orchestration/` / `rag/` — specialized sub-modules

### Semantic Layer Pattern (FR-8: Ibis→DuckDB)

The boring-semantic-layer (BSL) pattern enforces single translation surface. Real code:

```python
# semantic/metrics.py — pure Ibis, no DuckDB/pandas
def adoption_stage(conda_name: ibis.Expr, ...) -> ibis.Expr:
    """Adoption stage ranking. Legacy: adoption_stage() CFA:3847."""
    # Age formula preserves legacy quirk: age_days or 99999
    age = ibis.ifelse(...).else_(99999)
    ...
```

```python
# semantic/models.py — BSL binds expressions to datasets
from boring_semantic_layer import SemanticModel, Dimension, Measure
model = SemanticModel(..., measures=[
    Measure("adoption_stage", adoption_stage, ...),
])
```

```python
# Reading: never pandas, never raw SQL
def duckdb_table_from_parquet(path: str, *, connection=None):
    con = connection if connection is not None else ibis.duckdb.connect()
    return con.read_parquet(path)  # Ibis table, not DataFrame
```

### MCP Tool Registration — Two-Shape Rule + Lazy Import

`mcp/server.py` lazy-imports fastmcp **inside** `build_server()` — allows import without fastmcp/kedro_mcp present. `mcp/tools.py` enforces (via AST-scanned test) that every tool body is exactly ONE of two shapes:

1. `session.run(pipeline_name="...", ...)` — Kedro pipeline invocation
2. `_provenance.load_with_provenance(catalog, ...)` — provenance-wrapped read

**Non-allowed in `mcp/tools.py`:**
- Direct `ibis`, `pandas`, `duckdb` imports (the module is orchestration-only; data logic lives in `semantic/`/`datasets/`)
- Orchestration imports above `mcp/` layer

### Credential Scoping — Declarative in Catalog, Not Runtime Host-Detection

Contrary to what "JFrog/GitHub host-specific logic" might imply, credential scoping is **structural, not procedural**. Each catalog entry has (or lacks) a `credentials:` key:

```yaml
vcs_github_api_raw:
  type: pyforge.atlas.datasets.GitHubRequestDataset
  url: ${globals:endpoint_bases.GITHUB_API_BASE_URL}/graphql
  credentials: github_token  # <-- this is it
```

Enforcement is in `tests/catalog/test_credential_scoping.py`:
- Asserts the credentialed-entry set equals a fixed allowlist
- Guards against `jfrog.evil.example.com` substring tricks via suffix-match on actual hostnames (`_is_artifactory_host`, guards JFrog entries specifically)
- This fix addresses legacy bug: "JFrog branch evaluated first, host computed but never consulted, attached X-JFrog-Art-Api to every request"

### OpenLineage/OpenTelemetry — Single-Seam, No-Op by Default

`observability.py` is the **ONLY** module allowed to import `openlineage`/`opentelemetry` (AST-enforced). Both backends default to no-op:

```python
# No exporter attached by default
tracer_provider = TracerProvider()  # local, no-op dispatch
openlineage_client = None  # skip emission
```

Nodes stay pure `DataFrame→DataFrame` (zero instrumentation in node bodies). Hooks registered once in `settings.HOOKS` so both Kedro and Dagster runs inherit instrumentation atomically.

### IncrementalParquetDataset — TTL Gotchas

The sole reusable TTL primitive (replaces legacy `phase_state` table). Non-obvious patterns:

- **TTL staleness uses strict `<`** (not `>=`) to match legacy SQL exactly
- **`ttl_seconds` is injected post-construction** by `hooks.py` from `params:ttls.<name>` — never passed at catalog-resolution time (the A2 gate constructs entries with no TTL)
- **Outer Kedro `version:` is explicitly rejected** with `ValueError` — IO is delegated to composed inner `ParquetDataset`, and version tracking would break that delegation

### Legacy Provenance Convention — `# legacy: Phase <ID>`

Every ported node in `pipelines/core/nodes.py` etc. carries the convention:

```python
# legacy: Phase B (phase_b_conda_enumeration CFA:1408; view v_actionable_packages CFA:376)
def conda_enumerate(...):
    ...
```

Where `CFA` = `conda_forge_atlas.py @ b18cbb5` (the legacy monolith's commit pin). This convention is **real and consistent** — agents benefit from seeing the legacy origin and corresponding commit SHA.

### Pipeline & Node Registration — Dynamic Discovery + Empty-Scaffold Guard

`pipeline_registry.py` uses `find_pipelines(raise_errors=True)` and must guard the empty-scaffold case (a zero-node repo would build an empty Pipeline):

```python
pipelines = find_pipelines(raise_errors=True)
# Guard: sum() over an empty dict returns int 0, not a Pipeline
if not pipelines:
    pipelines["__default__"] = Pipeline([])
```

Individual pipelines (e.g., `pipelines/vulnerability/pipeline.py`) wire nodes via **`inputs=`/`outputs=` strings** (catalog names), not procedural references. Kedro resolves DAG execution order **automatically from declared edges** — never call nodes procedurally.

---

## References

- **Spec (binding contract):** `docs/specs/cfe-atlas-datapipeline-kedro-migration.md` (v5.6, § 2.5, 9, 10, 11, 14).
- **Epics (deliverable breakdown):** `_bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md`.
- **Retro (2026-07-25, 31/31 stories shipped):** `_bmad-output/projects/pyforge-atlas/planning-artifacts/retros/`.
- **Kedro docs:** https://docs.kedro.org/ (v0.19.x+ patterns).
- **Pandera v1.18.2:** https://pandera.readthedocs.io/ (hard cap; no ≥1.19 features).
- **CLAUDE.md § Recommendation on autonomy:** Describes autonomous menu-driven BMAD execution pattern (already applied).

