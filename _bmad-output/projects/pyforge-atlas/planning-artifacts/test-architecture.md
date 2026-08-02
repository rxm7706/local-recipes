---
title: "Test Architecture — pyforge-atlas"
type: test-architecture
date: 2026-08-02
version: 1.0.0
status: draft
scope: "All 38 stories (Wave 0, A–H, Epic 10 I0–I5), 78 pytest files, 930 collected tests"
target_coverage: "Retrospective — documents coverage that already shipped, not coverage to be built"
---

# Test Architecture — PyForge Atlas

## Executive Summary

This document was authored 2026-08-02, replacing a fabricated boilerplate placeholder
(81 lines: generic "Target Stories: TBD" on every row of a 3-row strategy table, no
real story references, an empty `tests/unit/`/`tests/integration/`/`tests/meta/`
layout that does not exist in the repo). That placeholder was discovered this session
inside a bulk commit that also contained a false migration note and other fabricated
content across multiple stations' planning artifacts — all found and remediated in
this session before this file was written.

Unlike a conventional test-architecture document, which is written *before*
implementation to plan coverage, **this document is retrospective**. Atlas is 100%
code-complete: all 38 stories across 11 waves (Wave 0; Waves A–H per the frozen spec
§ 9 structure; Epic 10's post-audit truth-up I0–I5) shipped via merged PRs (#69–#131 in
range; PR #131 itself was an abandoned audit branch, superseded by Epic 10's own
per-story PRs). `sprint-status-ledger.yaml` in this same directory records
`development_status: done` for every one of the 38 story keys plus all 11
epic/epic-retrospective keys. This document describes the test coverage that already
exists in `src/shared/packages/pyforge-atlas/tests/`, not coverage that remains to be
built.

**Grounding method.** Every one of the 78 test files under
`src/shared/packages/pyforge-atlas/tests/` carries an explicit `Story <ID>` (or, for
the six `catalog/` files, a `Gate check N (AC-x)` cross-reference to Story A2's
acceptance criteria) citation in its own module docstring, naming the story that
introduced it. Those citations — extracted directly from the files via
`grep`, not inferred from directory names or guessed from titles — are the primary
evidence for every row below. Three test files (`mcp/test_read_surface.py`,
`dashboard/test_dashboard_dryrun.py`, `orchestration/test_definitions_dryrun.py`)
carry citations to *more than one* story, because Epic 10 stories I4/G3/H4 extended
files that an earlier wave had already built; those are noted explicitly rather than
forced into a single row. A full suite collection
(`pixi run -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests
--collect-only -q`, run 2026-08-02 as part of writing this document) reports **930
tests collected, 0 errors**, confirming both that the files exist as claimed and that
the suite is currently green-collectible.

**What could not be confidently mapped to a test file, stated plainly:** three
stories genuinely have none, and are documented as such rather than assigned an
invented file — see § *Stories With No Dedicated Test File*. All three are explained
by their own subject matter (a pre-harness skill artifact, and two documentation
truth-up stories whose verify gates are non-pytest reference/frontmatter checks).

---

## Test Strategy by Wave

Atlas's test tree is organized by **domain** (`catalog/`, `pipelines/`, `mcp/`,
`semantic/`, …), not by **test level** (there is no `tests/unit/` vs
`tests/integration/` vs `tests/e2e/` split anywhere in the repo). Marshal's
UT/IT/E2E three-column checkmark grid assumes that split exists; forcing the same
grid onto Atlas's files would mean asserting per-row unit/integration/e2e checkmarks
the repository's own structure does not support, which is exactly the kind of
unverifiable claim this rewrite exists to remove. Instead, each row below states the
**Level** qualitatively from evidence actually present in the file (its own docstring,
its use of real vs. faked objects, whether it drives a browser) — and the two files
that are genuinely Playwright browser E2E, plus the one file that is genuinely a
cross-process integration test, are called out explicitly rather than left implicit.

### Wave 0 — Legacy Translation via Skill Forge (1 story)

| Story | Title | Test file(s) | Level | Note |
|---|---|---|---|---|
| **0.1** | Generate legacy contextual skill (cf-atlas-legacy@8.78.0) | *none* | — | Pre-harness execution scaffolding (a Skill Forge artifact, not product code). epics.md records this story's own verify gate as "none exists yet (pre-harness); acceptance is the queryable skill artifact itself." No pytest file was ever expected for this story, and none exists. |

### Wave A — `nebi` Scaffold & Catalog (3 stories)

**Scope**: the harness every later wave builds on — scaffold, catalog, incremental
dataset class — plus the first two named verify gates.

| Story | Title | Test file(s) | Level | Note |
|---|---|---|---|---|
| **A1** | Scaffold the Kedro + pixi project via `nebi` | `test_scaffold_layout.py`, `test_import_smoke.py` | Unit/fixture (offline, non-credentialed — NFR-1) | Builds the `kedro-test` gate itself (`pytest tests -q`, the umbrella gate for the whole suite). `test_scaffold_layout.py` proves the warden-mirrored workspace-member layout (hatchling build-backend, dual conda+wheel artifacts, PEP 420 `pyforge.atlas` namespace package with no stray `pyforge/__init__.py`, the `[gate]` optional-dependency extra pinned to exactly `["pyforge-warden"]`). `test_import_smoke.py` proves `import pyforge.atlas`, `import pyforge.warden` side-by-side, and the `kedro_dagster` AD-16 py3.14-unclassified glue import. |
| **A2** | Define the Data Catalog for all sources + outputs | `catalog/test_catalog_resolution.py`, `catalog/test_conventions.py`, `catalog/test_credential_scoping.py`, `catalog/test_no_inline_io.py`, `catalog/test_override_points.py`, `catalog/test_yaml_hygiene.py` | Unit + structural meta-test (offline, stub credentials, network hard-blocked — NFR-1) | Builds the `kedro-catalog-check` gate (`pytest tests/catalog -q`). Six files, each an explicit "Gate check N" against A2's AC-1..AC-4: full catalog resolution via `DataCatalog.from_config` with zero network (check 1); the no-inline-IO import ban plus the AD-1 import-direction meta-test (checks 2–3, "polices every later wave's node code" per its own docstring); naming/layer/TTL/path conventions from the spine's Consistency table (check 4); the pinned 20-override-point accounting — 19-live + 1-reserved, never a bare 20 (check 5); per-host credential scoping that inverts the legacy `_http.py` defect where `X-JFrog-Art-Api` attached to every outbound request regardless of destination host (check 6); a duplicate-YAML-key guard added after a real incident (`BIGQUERY_BASE_URL` doubled in `globals.yml` by a racing edit). |
| **A3** | Implement `IncrementalParquetDataset` for TTL gating | `datasets/test_incremental_parquet.py`, `test_hooks.py` | Unit/fixture (offline, non-credentialed — NFR-1) | Also the spec-designated first loop-driven story and worktree-execution smoke (LOOP-S). `datasets/test_incremental_parquet.py` round-trips the per-row `fetched_at`/TTL state. `test_hooks.py` drives `ProjectHooks.after_catalog_created` — described in its own docstring as "the ENTIRE production TTL-wiring path" — against a real `kedro.io.DataCatalog` (not a mock), asserting the per-dataset TTL injection, loud-fail on a missing TTL, and per-dataset materialization isolation. |

### Wave B — Pipeline Node Porting & MCP Integration (10 stories)

**Scope**: every legacy phase ported as a DAG-resolved Kedro node with proven output
parity; three new signal sources (Basilisk, release velocity, migration readiness)
land as additive riders not gated on parity.

| Story | Title | Test file(s) | Level | Note |
|---|---|---|---|---|
| **B1** | Port the conda-side backbone phases into Kedro nodes | `pipelines/core/test_nodes.py`, `pipelines/vcs_health/test_nodes.py`, `pipelines/vcs_health/test_rate_limit_contract.py`, `datasets/test_rate_limit.py`, `datasets/test_request_datasets.py`, `pipelines/test_dag_resolves.py`, `parity/test_parity_core.py`, `parity/test_parity_vcs_health.py`, `parity/harness.py` | Unit/fixture; begins the `parity-diff` harness (Integration) | Ports Phases B, B.5, B.6, E, E.5, F, J, K, L, M, N into the Core + VCS & Health pipelines. `parity/harness.py`'s own docstring: "The Wave-B `parity-diff` gate BEGINS here" (Task 5/AC-7) — B1 seeds the Core + VCS fixtures. Phase K's single-worker 3 RPS token bucket lives in `test_rate_limit_contract.py`/`test_rate_limit.py`; Phase B.5's `_pick_feedstock` dedicated-feedstock attribution and Phase I's promotion to an explicit node are in `test_nodes.py`. |
| **B2** | Port the PyPI & vulnerability pipelines | `pipelines/pypi_intelligence/test_nodes.py`, `pipelines/pypi_intelligence/test_review_hardening.py`, `pipelines/pypi_intelligence/test_serial_gate.py`, `pipelines/vulnerability/test_contracts.py`, `pipelines/vulnerability/test_nodes.py`, `datasets/test_bigquery_cost_gate.py`, `datasets/test_no_thirty_gb_lie.py`, `datasets/test_pypi_json_request_dataset.py`, `datasets/test_vdb_boundary.py`, `parity/test_parity_pypi_intelligence.py`, `parity/test_parity_vulnerability.py` | Unit/fixture; extends `parity-diff` | Ports Phases C, C.5, D, H, O–S (PyPI Intelligence) and G/G' (Vulnerability). Phase P's two-layer cost gate (dry-run preflight + `maximum_bytes_billed` + job timeout) is proven in `test_bigquery_cost_gate.py`; `test_no_thirty_gb_lie.py` carries the specific named regression from the legacy phase forward. |
| **B3** | Re-expose the data surface as Kedro-API-native MCP tools | `mcp/test_trigger_surface.py`, `mcp/test_audit_mapping.py`, `mcp/test_kedro_mcp_absent.py`, `mcp/test_no_business_logic_in_tool_bodies.py`, `parity/test_parity_complete.py` | Unit + structural (AST scan) + real import-absence integration | `parity/test_parity_complete.py` completes the `parity-diff` harness build (B1 began it, B2 extended it, B3 completes it, B4 consumes it) by pinning that the node registry is a superset of the pipeline nodes. `mcp/test_kedro_mcp_absent.py` sets `sys.modules["kedro_mcp"] = None` and freshly imports + exercises both the trigger and read surfaces — proving FR-7's "never load-bearing" claim by demonstration, not assertion. `mcp/test_no_business_logic_in_tool_bodies.py` is an AST scan over `mcp/tools.py` for AD-7 (no metric/business logic in tool bodies). |
| **B4** | Verify dataset parity against the legacy orchestrator | `parity/test_capture_tooling.py`, `parity/test_evidence_and_retirement_gate.py`, `parity/test_frame_diff_bites.py`, `parity/test_legacy_surface_scope.py`, `parity/test_parity_runner_fixture_mode.py`, `parity/parity_runner.py`, `parity/capture_fixtures.py` | Integration (fixture-mode, loop-collectible); the credentialed full run is an ATTENDED wave-boundary event, not a pytest-collected path | `parity/parity_runner.py`'s docstring: "The credentialed-parity-run comparator (Story B4, AC-1/AC-2)" — it compares Kedro Parquet outputs against the legacy `cf_atlas.db` tables and emits a `ParityEvidenceRecord` per view; that comparator runs live only at the attended sign-off event. The five `test_*.py` files here are the loop-collectible, offline, fixture-mode proof that the harness itself is correct (capture tooling, evidence-record shape, frame-diff granularity, legacy-surface scope, fixture-mode operation of the runner). |
| **B5** | Port the external-refresh assets (§ 3.4) | `datasets/test_refresh_assets.py`, `pipelines/pypi_intelligence/test_mapping_export.py`, `pipelines/test_refresh_schedule_fixtures.py`, `pipelines/test_refresh_single_writer.py` | Unit/fixture | Three separately-built local stores (`vdb-refresh`, `update-cve-db`, `update-mapping-cache`) as scheduled Dagster assets. `test_refresh_single_writer.py`'s own docstring names this "Story B5 — AC-2": it proves the `add-handoff` single-write-path invariant applied to the external stores — each of the three stores is produced by exactly one node (its own refresh asset) and consumed read-only everywhere else (Phases G/G' and `scan-project` offline mode never write them). |
| **B6** | Port the Seed-Gaps pipeline | `pipelines/seed_gaps/test_byte_identical_seed.py`, `pipelines/seed_gaps/test_nodes.py`, `pipelines/seed_gaps/test_pipeline_shape.py` | Unit/fixture | The four report-only gap suggesters (`lts-registry-gap`, `cwe-seed-gap`, `spdx-schema-gap`, `license-map-gap`) as terminal Seed-Gaps report nodes. `test_byte_identical_seed.py` is the pipeline-level proof the nodes never mutate the curated seeds. (`test_nodes.py` in this directory also carries one of Epic 10's Story I3 pandas-3.0 regression tests — see that row.) |
| **B7** | Extend the Universal SBOM intake (resolver, formats, buckets) | `datasets/test_sbom_intake.py`, `pipelines/derived_artifacts/test_universe_sbom.py`, `pipelines/universal_sbom/test_freshness.py`, `pipelines/universal_sbom/test_match.py`, `pipelines/universal_sbom/test_normalize.py` | Unit/fixture | Transitive resolver, widened tiered-manifest intake, the full-universe CycloneDX BOM under a 14-day freshness contract, and the legacy six-bucket classification (ADD / ADD-NONPYPI / UPDATE-FEEDSTOCK / UPDATE-PIN / CURRENT / UNKNOWN). `test_normalize.py` covers the NBSP-padded pasted-`conda list`/`pip list` fixture parsing identically to its ASCII-space form. |
| **B8** | Basilisk conda-native vulnerability ingestion | `datasets/test_basilisk.py`, `pipelines/vulnerability/test_basilisk_nodes.py` | Unit/fixture, including an explicit offline-skip fixture | The two Basilisk ingestion nodes (`POST /v1/querybatch` batch + bounded per-advisory detail fetch) with the tri-state `fix_available` join; a fixture proves an advisory with only an enumerated `versions` list yields `unknown`, never `false`. |
| **B9** | Release-to-availability velocity columns | `pipelines/vcs_health/test_release_velocity.py` | Unit/fixture | `release_lag_hours` + `release_lag_qualifies` derived on the Phase H join; the 90-day rebuild-cadence guard and the first-availability (minimum per-build repodata `timestamp`) fixtures are both named failure-mode tests in this one file. |
| **B10** | Migration-readiness datasets + classification node | `datasets/test_migration_status.py`, `pipelines/vcs_health/test_migration_readiness.py` | Unit/fixture | conda-forge-bot-data `status/` category lists driving zero-code-change per-migration partitioning; the four-way readiness split (noarch / rebuild-done / confirmed-pending / not-in-tracker) with the `not-in-tracker`-is-inferred-never-confirmed label fixture. |

### Wave C — Orchestration & Visualization (2 stories)

| Story | Title | Test file(s) | Level | Note |
|---|---|---|---|---|
| **C1** | Integrate `kedro-dagster` for scheduling + execution | `orchestration/test_definitions_dryrun.py` (Story C1 section — file lines ~1–265) | Integration (dry-run: Dagster `Definitions` load only, no live execution — DW-C1 defers the live daemon) | Builds the `dagster-dryrun` gate (`pytest tests/orchestration -q`). Proves schedules enumerate, jobs resolve, each op carries its own timeout (retiring the legacy 1800 s coarse-cap silent-phase-drop defect), and the three bootstrap-profile job configs exist. **The same file's later sections belong to Wave-G Story G3 and Wave-H Story H4** — see those rows; it is one shared gate file with three story-scoped sections, not three separate files. |
| **C2** | Integrate `kedro-viz` + expose a pixi task | `orchestration/test_viz_loadable.py` | Unit/fixture (DAG-loadability smoke) | The `viz` pixi task itself (`kedro viz run --no-browser`, run from the atlas project root) is a manual operator command, not a CI-collected pytest path; `test_viz_loadable.py` is the loop-collectible proof that the compiled DAG loads for `kedro-viz` at all. |

### Wave D — Semantic Layer & Dashboards (3 stories)

| Story | Title | Test file(s) | Level | Note |
|---|---|---|---|---|
| **D1** | Define the Boring Semantic Layer (BSL) models | `semantic/test_bsl_metric_parity.py`, `semantic/test_maintainer_dimension.py`, `semantic/test_metric_provenance.py` | Unit/fixture, metric-parity (offline, `--frozen`) | Builds the `bsl-metric-check` gate (`pytest tests/semantic -q`). Core metrics (staleness, adoption stage, feedstock health, …) each declared once as Ibis→DuckDB and matched against an *independently re-implemented* legacy-CLI formula (the DW-B1-1 honesty requirement — a metric-parity test that reused the same code on both sides would prove nothing). The maintainer-role join (`package_maintainers ⋈ maintainers`) is a first-class BSL dimension in `test_maintainer_dimension.py`. (Both `test_bsl_metric_parity.py` and `test_maintainer_dimension.py` also each carry one of Epic 10's Story I3 pandas-3.0 regression tests — see that row.) |
| **D2** | Build the Vizro dashboard + port the 28 CLIs to pages | `dashboard/test_dashboard_dryrun.py`, `dashboard/test_dashboard_e2e.py` | `dashboard_dryrun.py`: dry-run (builds the Vizro app object, never serves it). `dashboard_e2e.py`: real Playwright browser-level E2E. | `dashboard_e2e.py`'s own docstring: "Playwright-based browser-level E2E tests for the Vizro dashboard (FR-9)" — one of only two genuinely browser-driven Playwright files in the whole suite (the other is Wave G's `wasm_smoke.py`). **`dashboard_dryrun.py`'s file also carries an Epic 10 Story I4 section** (line 312+, an AD-17 per-page provenance-stamp test) — see that row. |
| **D3** | Integrate Vizro-AI + expose the NL interface as an MCP tool | `nl/test_query_vizro_ai_dryrun.py` | Dry-run (LLM backend not exercised live in-loop) | The `query_vizro_ai` MCP tool surface. Q3's LLM-backend routing decision (repo model-backend configuration, never a hardcoded public endpoint) is resolved at D3's attended boundary event, not proven by this file alone. |

### Wave E — A2A Integration, Lineage & Observability (2 stories)

Spec § 2.5 assigns Wave E no new named gate; both stories verify against the existing
gates plus their own fixture files.

| Story | Title | Test file(s) | Level | Note |
|---|---|---|---|---|
| **E1** | Implement the A2A communication interfaces | `a2a_surface/test_a2a_payloads.py` | Unit/fixture (payload schema round-trip) | Structured A2A payload schemas living in the `a2a/` module — the single schema source for inter-agent alerts and insights (AD-20). |
| **E2** | Integrate OpenLineage + OpenTelemetry | `observability/test_observability_fixtures.py` | Unit/fixture (emitted-event/span fixtures) | Lineage + per-node metrics via OpenLineage, distributed traces via OTel down to named API calls — this file's fixture assets are, per the epic, "this story's gate assets" since no new named gate exists for Wave E. |

### Wave F — The DuckDB Singularity (4 stories)

| Story | Title | Test file(s) | Level | Note |
|---|---|---|---|---|
| **F1** | Complete the DuckDB consolidation + prove the cold-start claim | `singularity/test_duckdb_sole_engine.py` | Structural grep-gate (no `sqlite3` read/write path in the migrated surface) + fixture; the benchmark itself is NOT a pytest assertion | Builds the `duckdb-singularity` gate (`pytest tests/singularity -q`). The pixi task's own description: "the one legacy-SQLite reader (the B4 credentialed parity comparator) is pinned to `tests/`, never `src/`. The cold-start/warm-incremental benchmark is the ATTENDED half (DW-F1-1)" — i.e. CI enforces the grep gate; the AC-7 performance claim is adjudicated by operator sign-off at the attended benchmark event, not by a collected test. |
| **F2** | Implement the data-validation hook and inline Pandera contracts | `validation/test_validation_hook.py` | Unit/fixture (halt-on-malformed-payload + stub-validator-swap fixtures) | The validator-agnostic `AfterNodeRunHook`; a fixture proves swapping/adding the GX backend requires no node changes. This file also carries an inline comment referencing the AUD-ATLAS-011 pin (Epic 10 Story I3) on an incidental empty-frame dtype interaction it had to accommodate — noted here for completeness, not claimed as I3's primary coverage. |
| **F3** | Implement Vector Similarity Search (RAG) via DuckDB `vss` | `rag/test_vss_similarity_search.py` | Unit/fixture (ranked-results fixture) | RAG embeddings + similarity search via DuckDB's `vss` extension. |
| **F4** | Dependency-hygiene node + unified CI policy gate | `policy_gate/test_policy_gate.py` | Unit/fixture (schema fixtures + frozen exit-code fixtures + `not-applicable` fixture) | The deptry hygiene node and the four-axis `ComplianceReport` policy gate; validates against `pyforge.warden`'s schema **by import** via the `pyforge-atlas[gate]` extra (AD-12), never a vendored copy — absent the extra, this gate node fails with an explicit install hint while every other pipeline keeps running. |

### Wave G — WebAssembly Portability & Event-Driven Sensors (3 stories)

| Story | Title | Test file(s) | Level | Note |
|---|---|---|---|---|
| **G1** | Compile the intelligence layer to Pyodide / DuckDB-WASM | `wasm/test_wasm_smoke.py` | Real Playwright headless-Chromium E2E | Builds the `wasm-smoke` gate. The pixi task's own description: "a Playwright HEADLESS Chromium load-and-query against the built wasm artifact... serves `wasm/build/` over a loopback static host, drives the pre-provisioned Chromium, BLOCKS + asserts zero non-loopback requests (offline / no-CDN proof), waits for the in-browser DuckDB-WASM query to reach ready." Requires the separate `wasm-build` task first (npm-installs `@duckdb/duckdb-wasm` + esbuild, vendors the parquet extension locally so the runtime never hits `extensions.duckdb.org`). Full Vizro-in-Pyodide render is deferred (DW-G1) — this gate proves the DuckDB-WASM query path, not the whole dashboard. |
| **G2** | Emit Parquet artifacts to a static web host | `publish/test_emit_range.py` | Unit/fixture (host-agnostic emitter, HTTP-Range consumption) | Consumes `wasm-smoke` against the published artifact at the attended G2 publish event (Q4: GitHub Pages default); fixture-hosted in-loop. |
| **G3** | Implement Dagster Sensors for near-real-time ingestion | `orchestration/test_definitions_dryrun.py` (Story G3 section — file lines ~266–572) | Integration (dry-run: sensors enumerate; DW-G3 defers the live daemon) + a real simulated-event fixture | Two sensors — `pypi_release_sensor` → Phase H, `vcs_release_sensor` → Phase K — added via `orchestration/event_source.py` (kept Dagster-free, AD-1) and `build_upstream_sensor`. A simulated event drives exactly one `RunRequest` for the existing incremental job; a no-event tick yields `SkipReason`. Event source is RSS/poll-cursor, not webhooks (a documented deviation recorded at delivery). |

### Wave H — The AI Software Factory & Karpathy Wiki (4 stories)

The factory layer consumes pipeline outputs and writes only wiki/CMS (AD-22).

| Story | Title | Test file(s) | Level | Note |
|---|---|---|---|---|
| **H1** | Scaffold the Karpathy Wiki structure + 5 factory personas | `factory/test_wiki_scaffold.py`, `factory/test_personas.py` | Unit/fixture (scaffold-layout + persona-resolution) | The three-stage `raw/ → compiled/ → outputs/` tree with a per-segment `stage_path` traversal guard enforcing the AD-22 write-boundary; the 5 personas (Ingester, Compiler, Linker, Linter, Oracle) via `resolve_personas(*overlays)` over the BMAD customization layers — an overlay may only refine, never rename or add to the frozen five-person workforce. |
| **H2** | Agno compilation, linting & Q&A crews | `factory/test_crews.py` | Unit/fixture (crews driven against a fixture wiki, end-to-end within the fixture) | `CompileCrew` (raw→compiled, forwards source staleness from both inline frontmatter and a `.staleness.json` sidecar — republication never launders freshness, AD-13/AD-22), `LintCrew` (six violation classes, never raises), `QACrew` (grounded answers over compiled content, deterministic keyword retriever by default). agno-Agent/LLM synthesis is an injectable, offline-by-default seam (live bring-up deferred, DW-H2). |
| **H3** | Integrate La Suite / Wagtail Docs REST API sync | `factory/test_lasuite.py` | Integration (in-memory mock Wagtail server — push / update / idempotent-re-push / mapping-resume round-trip) | `LaSuiteClient` + `WikiSyncer`; CMS source is `outputs/` (not internal `compiled/`), sha-keyed idempotent sync (new→create, changed→update, unchanged→SKIP with no remote call); the mapping sidecar is written atomically (tmp+`os.replace`). Live Wagtail server + httpx transport bring-up deferred (DW-H3). |
| **H4** | Orchestrate crews via Dagster | `orchestration/test_definitions_dryrun.py` (Story H4 section — file lines ~573+) | Integration (dry-run: asset dry-run enumerates crew assets) + a real simulated-trigger fixture | Crew assets (`compiled_wiki` → CompileCrew, `wiki_lint_report` → LintCrew), a weekly lint schedule (`wiki_lint_schedule`, `0 6 * * 1`), and a new-raw-file compile sensor (`wiki_raw_file_sensor`, ships STOPPED). Raw-scan + cursor-dedupe logic lives in `orchestration/wiki_events.py`, kept Dagster-free (AD-1 holds — only `definitions.py` imports dagster). Live daemon + wiki-store bring-up deferred (DW-H4). |

### Epic 10 — Post-Audit Remediation: Round-3 Findings (6 stories, I0–I5)

Added 2026-07-27 after the migration shipped, closing the atlas-owned subset of an
independent spec-to-code audit's 49 findings. Two conventions from epics.md govern
this epic and are worth restating here because they explain the test evidence below:
findings are closed *at their source* (fixed in whichever of spec-vs-code was wrong,
not assumed to be the code), and the epic runs in **verify-gate order**, not wave
order — I3 first, because `kedro-test` was red on `main` (six failing tests) until it
landed.

| Story | Title | Test file(s) | Level | Note |
|---|---|---|---|---|
| **I0** | I0 — Atlas dependency completeness — unblock `kedro-test` (AUD-ATLAS-010/013) | *no dedicated file* — verified as a whole-suite collection property | n/a (suite-wide, not one file) | The AC is "collection completes with zero import errors," which is a property of the entire 78-file, 930-test tree collecting cleanly, not of any single test. epics.md's own delivered note: "17 collection errors → 781 passed." The one narrow regression test for this finding's *specific* defect (an undeclared transitive `filelock` dependency) happens to live inside Story I5's file: `test_admission.py::test_filelock_is_declared_in_both_manifests`, whose own docstring cites `AUD-ATLAS-010` directly — it is there because `filelock` is I5's own admission-lock dependency, not because I0 has a dedicated home in that file. |
| **I1** | I1 — Kernel + companion truth-up: retract the false run-admission claim (AUD-ATLAS-046/041/047/049) | *none* | doc-only | Verify gate is "reference-integrity check; no broken links" over the Spec kernel's prose — not a pytest path. Retracted the "one execution plane" run-admission safety claim from Constraints (the real fix is I5); corrected CAP-8 to the 8 shipped PageDefs; added a `shipped_scope_note`. |
| **I2** | I2 — Uniform story-spec frontmatter + README reversal (AUD-ATLAS-045/048) | *none* | doc-only | Verify gate is a "spec-surface check" over the 32 story specs' frontmatter — not a pytest path. Reversed the audit's blanket `status: shipped` stamp for the 12 recovered-original specs (provenance over uniformity — rewriting a verbatim recovered artifact to satisfy a linter destroys the only evidence of what was actually written). |
| **I3** | I3 — pandas 3.0 None-identity contracts — FIRST loop story, `kedro-test` is red until it lands (AUD-ATLAS-011) | `pipelines/core/test_nodes.py` (`test_attribute_feedstocks_handles_nan_feedstocks_cell`, `test_attribute_feedstocks_node`), `pipelines/seed_gaps/test_nodes.py` (`test_licmap_likely_and_report_tiers`), `semantic/test_bsl_metric_parity.py` (`test_is_actionable_matches_legacy_view`, `test_feedstock_health_filters_match_legacy`), `semantic/test_maintainer_dimension.py` (`test_maintainer_with_no_packages_and_package_with_no_maintainer`), `test_import_smoke.py` (`test_pandas_null_identity_pin_applied`) | Unit/fixture — six named pre-existing tests, all red on `main` before this story, all green after | pandas 3.0 coerces `None`→`NaN` in `str`-dtype columns; because `NaN != NaN`, a null group key becomes unreachable. The fix pins `future.infer_string` off in the production path (never weakens an assertion to accommodate `NaN`). `test_import_smoke.py`'s own docstring names this exactly: "(e) the AUD-ATLAS-011 pandas NULL-identity pin canary (story 10-4)." Gate went `kedro-test` GREEN, 781→787 passing. **Blocks I4 and I5** — the epic runs in gate order because of this dependency. |
| **I4** | I4 — AD-17 advisory timestamps: MCP `read_dataset` envelope + per-page build stamps (AUD-ATLAS-043/044) | `mcp/test_read_surface.py`, `dashboard/test_dashboard_dryrun.py` (I4 section, line 312+) | Unit/fixture (per-dataset-kind envelope tests) | `mcp/test_read_surface.py`'s own docstring: "returned since Story I4 inside an AD-17 build-provenance envelope." Per dataset kind: `IncrementalParquetDataset` (15 catalog entries) stamps from its own `fetched_at` column; `pandas.ParquetDataset` (22 entries) from the materialized file's mtime; `api.APIDataset` (24 entries) correctly uses `now` (the read genuinely is the fetch); everything else returns `null` + an explicit `reason`, never a fabricated value. A `provenance_kind` field self-describes which case applied. The C6 half of this story (closing AUD-ATLAS-044 — every dashboard page, not only `factory-status`, carries its data's stamp) is the section added to `dashboard/test_dashboard_dryrun.py` rather than a new file. This story was re-driven after a CRITICAL escalation rejected its first draft (a wall-clock-now `build_stamp`, which can never distinguish fresh from stale data) — the reverted patch is not restored anywhere in the tree. |
| **I5** | I5 — Run admission / single-writer — DW-AD23-1, re-promotes AD-23 (AUD-ATLAS-046 impl half) | `test_admission.py` | Integration — real cross-process (`subprocess.Popen`, no threads, no mocks) | `RunAdmissionHooks` registered in `settings.HOOKS`, acquiring in `before_pipeline_run` and releasing in both `after_pipeline_run` and `on_pipeline_error`; `filelock`-based (already in the env, no new dependency), per-dataset-set granularity acquired in sorted name order (deadlock avoidance), reject-fast by default with an explicit opt-in bounded wait, and stale-lock (dead-PID) reclaim so a `SIGKILL`'d run cannot wedge the factory permanently. This is the single strongest integration-level test in the suite: the gate spawns a real second OS process to prove cross-process contention rather than simulating it with a thread or a monkeypatched lock — the file's own docstring documents two prior review passes that caught exactly this shortcut (a CWD-relative lock root that never actually contended across processes, and a wait test that passed with the wait switched off). On green, AD-23 is re-promoted to full form in `ARCHITECTURE-SPINE.md`, closing the gap I1 had retracted. |

---

## Gate Inventory

Five stories build a *named*, pixi-task-backed verify gate; the rest verify against
whichever named gate already exists plus their own fixture files. This table is the
real `pixi.toml` task definitions (`[feature.pyforge-atlas.tasks.*]`), not a
reconstruction:

| Gate (pixi task) | Command | Built by | Files it collects |
|---|---|---|---|
| `kedro-test` | `pytest src/shared/packages/pyforge-atlas/tests -q` | A1 | all 78 files, 930 tests — the umbrella gate |
| `kedro-catalog-check` | `pytest .../tests/catalog -q` | A2 | 6 files |
| `parity-diff` | `pytest .../tests/parity -q` | B1 begins, B2 extends, B3 completes | 12 `test_*.py` files + 3 support modules (`harness.py`, `parity_runner.py`, `capture_fixtures.py`) |
| `bsl-metric-check` | `pytest .../tests/semantic -q` | D1 | 3 files |
| `dagster-dryrun` | `pytest .../tests/orchestration -q` | C1 (base section), extended by G3 and H4 | 2 files, 3 story-scoped sections |
| `duckdb-singularity` | `pytest .../tests/singularity -q` | F1 | 1 file (structural grep-gate) |
| `wasm-smoke` | Playwright headless Chromium against the built `wasm-build` artifact | G1 | 1 file |
| `viz` | `kedro viz run --no-browser` (manual/operator command, not CI-collected) | C2 | n/a — proven loadable by `test_viz_loadable.py` instead |

Waves E and F4 and every Epic-10 story other than I0/I1/I2/I3 verify against these
existing gates plus their own fixture files — per spec § 2.5, Wave E was deliberately
assigned no new named gate.

---

## Stories With No Dedicated Test File

Three of the 38 stories genuinely have no pytest coverage, and each is explained by
its own subject matter rather than being a coverage gap:

- **0.1** (Wave 0) predates the test harness entirely — it is a Skill Forge artifact
  (a queryable model of the legacy orchestrator), not product code, and its own
  acceptance criteria in epics.md state the verify gate is "none exists yet
  (pre-harness)."
- **I1** (Epic 10) is a documentation truth-up of the Spec kernel's own prose
  (retracting an overclaim, correcting a count). Its verify gate — "reference-integrity
  check; no broken links" — checks markdown cross-references, not code, and is not a
  pytest path.
- **I2** (Epic 10) is a documentation uniformity pass over 32 story-spec frontmatter
  blocks, explicitly *reversed* for the 12 recovered-original specs to preserve
  provenance over uniformity. Its verify gate — "spec-surface check" — is likewise not
  a pytest path.

No other story in the 38 lacks a test file; every remaining story maps to at least one
file whose own docstring names it.

---

## Test Coverage Summary

| Partition | Stories | Count |
|---|---|---|
| Dedicated pytest coverage (unit, fixture, integration, or E2E) | A1–A3, B1–B10, C1–C2, D1–D3, E1–E2, F1–F4, G1–G3, H1–H4, I3, I4, I5 | 35 / 38 |
| ...of which real Playwright browser E2E | D2 (`dashboard_e2e.py`), G1 (`wasm_smoke.py`) | 2 / 38 |
| ...of which real cross-process integration (spawned OS subprocess) | I5 (`test_admission.py`) | 1 / 38 |
| Verified by a non-pytest documentation/reference check (doc-only) | I1, I2 | 2 / 38 |
| No verify gate — pre-harness execution scaffolding | 0.1 | 1 / 38 |
| **Total** | | **38 / 38** |

**Suite totals** (measured, not estimated): 78 test files under
`src/shared/packages/pyforge-atlas/tests/`; 930 tests collected
(`pytest --collect-only -q`, 2026-08-02); 3 non-test support modules inside
`tests/parity/` (`harness.py`, `parity_runner.py`, `capture_fixtures.py`) that the
`parity-diff` gate's `test_*.py` files import rather than duplicate.

---

## Appendix: Full Test-File Inventory

Every row is a directly-measured `pytest --collect-only -q` count against
`src/shared/packages/pyforge-atlas/tests/` (2026-08-02), not an estimate. Where a file
serves more than one story (the three noted throughout this document), the split
is shown where it could be measured precisely by line-number bucketing against the
docstring's own section markers; `test_definitions_dryrun.py`'s split is approximate
because 6 of its 56 collected items are parametrized cases of fewer `def test_`
functions, so the three section counts (by top-level function) undercount its true
collected total — stated here rather than papered over.

| File | Tests collected | Story |
|---|---:|---|
| `a2a_surface/test_a2a_payloads.py` | 22 | E1 |
| `catalog/test_catalog_resolution.py` | 4 | A2 |
| `catalog/test_conventions.py` | 10 | A2 |
| `catalog/test_credential_scoping.py` | 7 | A2 |
| `catalog/test_no_inline_io.py` | 12 | A2 |
| `catalog/test_override_points.py` | 11 | A2 |
| `catalog/test_yaml_hygiene.py` | 3 | A2 |
| `dashboard/test_dashboard_dryrun.py` | 20 (18 D2 + 2 I4) | D2, I4 |
| `dashboard/test_dashboard_e2e.py` | 1 | D2 |
| `datasets/test_basilisk.py` | 23 | B8 |
| `datasets/test_bigquery_cost_gate.py` | 12 | B2 |
| `datasets/test_incremental_parquet.py` | 21 | A3 |
| `datasets/test_migration_status.py` | 25 | B10 |
| `datasets/test_no_thirty_gb_lie.py` | 3 | B2 |
| `datasets/test_pypi_json_request_dataset.py` | 8 | B2 |
| `datasets/test_rate_limit.py` | 9 | B1 |
| `datasets/test_refresh_assets.py` | 25 | B5 |
| `datasets/test_request_datasets.py` | 5 | B1 |
| `datasets/test_sbom_intake.py` | 19 | B7 |
| `datasets/test_vdb_boundary.py` | 7 | B2 |
| `factory/test_crews.py` | 24 | H2 |
| `factory/test_lasuite.py` | 13 | H3 |
| `factory/test_personas.py` | 15 | H1 |
| `factory/test_wiki_scaffold.py` | 11 | H1 |
| `mcp/test_audit_mapping.py` | 6 | B3 |
| `mcp/test_kedro_mcp_absent.py` | 3 | B3 |
| `mcp/test_no_business_logic_in_tool_bodies.py` | 3 | B3 |
| `mcp/test_read_surface.py` | 19 | I4 |
| `mcp/test_trigger_surface.py` | 3 | B3 |
| `nl/test_query_vizro_ai_dryrun.py` | 27 | D3 |
| `observability/test_observability_fixtures.py` | 18 | E2 |
| `orchestration/test_definitions_dryrun.py` | 56 (~19 C1 + ~17 G3 + ~14 H4 by top-level function; see note above) | C1, G3, H4 |
| `orchestration/test_viz_loadable.py` | 2 | C2 |
| `parity/test_capture_tooling.py` | 4 | B4 |
| `parity/test_evidence_and_retirement_gate.py` | 10 | B4 |
| `parity/test_frame_diff_bites.py` | 10 | B4 |
| `parity/test_legacy_surface_scope.py` | 6 | B4 |
| `parity/test_parity_complete.py` | 1 | B3 |
| `parity/test_parity_core.py` | 8 | B1 |
| `parity/test_parity_pypi_intelligence.py` | 11 | B2 |
| `parity/test_parity_runner_fixture_mode.py` | 7 | B4 |
| `parity/test_parity_vcs_health.py` | 6 | B1 |
| `parity/test_parity_vulnerability.py` | 7 | B2 |
| `pipelines/core/test_nodes.py` | 18 | B1 (+ 2 of I3's 6 regression tests) |
| `pipelines/derived_artifacts/test_universe_sbom.py` | 4 | B7 |
| `pipelines/pypi_intelligence/test_mapping_export.py` | 8 | B5 |
| `pipelines/pypi_intelligence/test_nodes.py` | 14 | B2 |
| `pipelines/pypi_intelligence/test_review_hardening.py` | 8 | B2 |
| `pipelines/pypi_intelligence/test_serial_gate.py` | 5 | B2 |
| `pipelines/seed_gaps/test_byte_identical_seed.py` | 2 | B6 |
| `pipelines/seed_gaps/test_nodes.py` | 13 | B6 (+ 1 of I3's 6 regression tests) |
| `pipelines/seed_gaps/test_pipeline_shape.py` | 5 | B6 |
| `pipelines/test_dag_resolves.py` | 17 | B1 |
| `pipelines/test_refresh_schedule_fixtures.py` | 5 | B5 |
| `pipelines/test_refresh_single_writer.py` | 3 | B5 |
| `pipelines/universal_sbom/test_freshness.py` | 5 | B7 |
| `pipelines/universal_sbom/test_match.py` | 9 | B7 |
| `pipelines/universal_sbom/test_normalize.py` | 6 | B7 |
| `pipelines/vcs_health/test_migration_readiness.py` | 16 | B10 |
| `pipelines/vcs_health/test_nodes.py` | 9 | B1 |
| `pipelines/vcs_health/test_rate_limit_contract.py` | 11 | B1 |
| `pipelines/vcs_health/test_release_velocity.py` | 17 | B9 |
| `pipelines/vulnerability/test_basilisk_nodes.py` | 14 | B8 |
| `pipelines/vulnerability/test_contracts.py` | 5 | B2 |
| `pipelines/vulnerability/test_nodes.py` | 7 | B2 |
| `policy_gate/test_policy_gate.py` | 16 | F4 |
| `publish/test_emit_range.py` | 12 | G2 |
| `rag/test_vss_similarity_search.py` | 20 | F3 |
| `semantic/test_bsl_metric_parity.py` | 7 | D1 (+ 2 of I3's 6 regression tests) |
| `semantic/test_maintainer_dimension.py` | 5 | D1 (+ 1 of I3's 6 regression tests) |
| `semantic/test_metric_provenance.py` | 4 | D1 |
| `singularity/test_duckdb_sole_engine.py` | 3 | F1 |
| `test_admission.py` | 107 | I5 (+ 1 narrow I0 regression test) |
| `test_hooks.py` | 8 | A3 |
| `test_import_smoke.py` | 6 | A1 (+ 1 of I3's 6 regression tests) |
| `test_scaffold_layout.py` | 3 | A1 |
| `validation/test_validation_hook.py` | 20 | F2 |
| `wasm/test_wasm_smoke.py` | 1 | G1 |

Column sums to 930, matching the collection total reported in the Executive Summary.

---

## Framework & Tooling

**Pytest**: the sole test runner across the whole suite (`pytest = ">=9.1.1"`,
declared as a `[feature.pyforge-atlas]` dependency specifically so `kedro-test` can
collect). No `pytest-cov`/`pytest-xdist`/`pytest-timeout` plugin pins are declared for
this package (unlike Marshal's test-architecture, which does declare them) — do not
carry those over by inference.

**Playwright**: used by exactly two files — `dashboard/test_dashboard_e2e.py`
(FR-9 Vizro dashboard) and `wasm/test_wasm_smoke.py` (the `wasm-smoke` gate) — both
against a headless, pre-provisioned Chromium. `pixi.toml`'s own comment on the
dependency: "G1 `wasm-smoke` + the D2 dashboard e2e test drive headless [Chromium]."

**DuckDB**: the sole compute/graph/vector engine (Story F1's consolidation); the
`duckdb-singularity` gate is a structural grep-gate (no `sqlite3` import path anywhere
in the migrated `src/` surface) rather than a functional test, because the property
being enforced is architectural, not behavioral.

**Kedro `DataCatalog`**: several files construct a *real* `kedro.io.DataCatalog`
rather than mocking it — `catalog/test_catalog_resolution.py` (full offline
resolution via `DataCatalog.from_config`), `test_hooks.py` (a real kedro 1.5.0
catalog), `mcp/test_read_surface.py` (a genuine `catalog.load` passthrough seeded with
a `MemoryDataset`) — a deliberate pattern favoring real objects over mocks wherever the
object itself is cheap and offline-safe.

**Environment**: `pixi run -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests -q`
is the real invocation (env name `pyforge-atlas`, a dedicated lean pixi feature/env
distinct from the fat `local-recipes` env, per Story A1's warden-mirrored packaging
decision — loop worktrees never materialize the fat env).

---

## Readiness Checklist

Because this document is retrospective, every item below is checked against what
already shipped, not against a plan:

- [x] All 38 stories defined in `epics.md`, each with its own FR/AD citations and a
      "Delivered — PR #NNN" line (0.1 through H4) or a Findings citation (I0–I5)
- [x] All 78 test files exist and are attributable to a specific story via their own
      module docstrings (verified by direct `grep`, not inferred)
- [x] Full-suite collection verified green: 930 tests, 0 collection errors
      (2026-08-02)
- [x] Every named verify gate (`kedro-test`, `kedro-catalog-check`, `parity-diff`,
      `bsl-metric-check`, `dagster-dryrun`, `duckdb-singularity`, `wasm-smoke`) traced
      to its real `pixi.toml` task definition and the story that built it
- [x] The 3 stories with no dedicated test file identified and explained individually
      (§ *Stories With No Dedicated Test File*), not glossed over
- [x] `sprint-status-ledger.yaml` cross-checked: all 38 story keys + 11 epic/retro keys
      read `development_status: done`
- [ ] Coverage-percentage or pass/fail metrics beyond "930 tests collect cleanly" were
      **not** independently re-measured for this document (no full `kedro-test` *run*
      — as opposed to *collection* — was executed while writing this file; a live run
      would additionally require the credentialed/attended-event pieces of B4, F1's
      benchmark, and G1/G2's built artifacts, which are out of scope for a planning
      artifact)

---

**Status**: DRAFT — retrospective description of shipped test coverage, not a plan for
future coverage. Superseded only if Atlas resumes active development (e.g. one of the
DW-* deferred items — DW-C1-1 live daemon, DW-G1 full Vizro-in-Pyodide render, DW-H2/H3/H4
live bring-up — is picked up as a new story), at which point this document should gain
new rows rather than be regenerated as boilerplate.

**Coverage measured**: 78 test files, 930 collected tests, 35/38 stories with
dedicated pytest coverage, 2/38 doc-only, 1/38 pre-harness.

**Last updated**: 2026-08-02
