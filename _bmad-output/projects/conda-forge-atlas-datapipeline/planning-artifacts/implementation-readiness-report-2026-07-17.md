---
stepsCompleted: [1, 2, 3, 4]
documentsIncluded:
  prd: prds/prd-conda-forge-atlas-datapipeline-2026-07-17/prd.md
  prdAddendum: prds/prd-conda-forge-atlas-datapipeline-2026-07-17/addendum.md
  architecture: architecture/architecture-conda-forge-atlas-datapipeline-2026-07-17/ARCHITECTURE-SPINE.md
  epics: epics.md
  ux: none (N/A per epics.md D-11 — data-pipeline effort, zero UX-DRs is correct)
  intakeSpec: docs/specs/cfe-atlas-datapipeline-kedro-migration.md (v5.6, ground truth)
  context:
    - agents-and-skills.md
    - intake-groundtruth-2026-07-17.md
mode: unattended (PM John + Architect Winston joint gate; iterate-to-pass)
---

# Implementation Readiness Assessment Report

**Date:** 2026-07-17
**Project:** conda-forge-atlas-datapipeline

## Document Inventory

| Type | File | Status |
|---|---|---|
| PRD | `prds/prd-conda-forge-atlas-datapipeline-2026-07-17/prd.md` (45,925 B, 2026-07-17) | Found (whole) |
| PRD addendum | `prds/prd-conda-forge-atlas-datapipeline-2026-07-17/addendum.md` (5,742 B) | Found |
| Architecture | `architecture/architecture-conda-forge-atlas-datapipeline-2026-07-17/ARCHITECTURE-SPINE.md` (39,554 B) | Found (whole) |
| Epics & Stories | `epics.md` (32 frozen-ID stories, 9 epics) | Found (whole) |
| UX | — | N/A by design (epics.md D-11: data-pipeline effort, zero UX-DRs) |
| Intake spec (ground truth) | `docs/specs/cfe-atlas-datapipeline-kedro-migration.md` v5.6 | Found (repo Tier 1) |
| Context | `agents-and-skills.md`, `intake-groundtruth-2026-07-17.md` | Found |

**Duplicates:** none (single whole version of each document type).
**Missing:** UX — recorded N/A (not a finding; D-11 rationale accepted).
**Environment constraints:** pixi unavailable in this session — any pixi-based checks are environment-deferred.

## PRD Analysis

### Functional Requirements

Spec-preserved numbering FR-1..FR-22 (22 FRs, no gaps; FR locations PRD § 4.1–4.11):

- FR-1: Declarative data access via the Kedro Data Catalog — all API sources and Parquet outputs cataloged in `conf/base/catalog.yml`; no data-access logic in nodes; credentials scoped per destination host (fix over legacy `_http.py`); all 20 `resolve_*_urls` override points (incl. `BASILISK_BASE_URL`) survive. (Story A2.)
- FR-2: The 23 cataloged phases refactored into 7 modular DAG-resolved domain pipelines; Phase I becomes explicit; § 3.3 per-phase engineering contracts bind the ports (Phase P cost gate, Phase K 3-RPS token bucket, Phase F provenance, Phase H serial gate, B.5 attribution, EPSS normalization). (Stories B1, B2, B5, B6.)
- FR-3: `IncrementalParquetDataset` preserves per-dataset TTL gating (7 d / 30 d / 1 d / 90 d…), never a global constant. (Story A3.)
- FR-4: `phase_state` removed; resumability Kedro-native via runner + persisted Parquet. (Stories A3, B4.)
- FR-5: DuckDB replaces SQLite and all fragmented compute proposals (compute + recursive CTEs + `vss`); Parquet canonical from Wave A; F1 = residue cleanup + attended benchmark (warm-incremental headline AND cold-full honesty). (Stories F1, F3.)
- FR-6: Dagster orchestrates schedules + retries via `kedro-dagster`; cadence-table schedules; 3 bootstrap profiles as job configs; per-node timeouts (retires the 1800 s `cf_atlas_core` defect); kedro-viz; glue replaceable (Q2 watch). (Stories C1, C2, B5, G3, H4.)
- FR-7: MCP surface preserved — 23 atlas-relevant tools re-authored over Kedro session/catalog APIs; `kedro-mcp` never load-bearing. (Story B3.)
- FR-8: Boring Semantic Layer over the catalog (Ibis → DuckDB); 28 read CLIs' metrics as declared dimensions/measures; `bsl-metric-check`. (Story D1.)
- FR-9: Read surface migrates from 28 CLIs to Vizro / Vizro-AI (+ `query_vizro_ai` MCP tool); 3 named CLI-first exceptions surfaced via latest-report artifacts; live-confirmed consumer CLIs port first; CIS two-spine specs precede frontend work; agent-legibility bar. (Stories D2, D3; Q3.)
- FR-10: Data-quality contracts halt bad data — pandera-first inline, GX (capped 1.18.2) as boundary layer behind validator-agnostic `AfterNodeRunHook`; Dagster halts + A2A alert. (Story F2.)
- FR-11: A2A interface for inter-agent collaboration; structured payload round-trip; alerts on contract/policy violations. (Story E1.)
- FR-12: Lineage + observability via OpenLineage + OpenTelemetry down to named API calls. (Story E2.)
- FR-13: Universal SBOM ingestion normalized to CycloneDX; core-tier manifests; `cfe:*` namespace + `?channel=conda-forge` qualifier preserved. (Story B7.)
- FR-14: WASM portability — duckdb-wasm/Pyodide in-browser; static Parquet host (GH Pages default, host-agnostic emitter); HTTP Range; zero backend. (Stories G1, G2; Q4.)
- FR-15: Pixi-first, nebi-scaffolded, conda-forge-only; py3.14 floor; lean dedicated env + `kedro-test`; air-gapped provisioning covers `_http.py` AND `.pixi/config.toml [pypi-config]`; `llms-full-check` green. (Story A1.)
- FR-16: Dependency-hygiene scan node (deptry); source-less → `not-applicable`; fills `hygiene` axis of `ComplianceReport`; security axis from `inventory-match`/`cve`. (Story F4.)
- FR-17: Transitive resolution (pip `--dry-run --report` / py-rattler) + ~856k-component universe BOM as `derived` dataset under 14-day freshness; six-bucket + three-way semantics preserved; NBSP paste fixture. (Story B7.)
- FR-18: Unified CI policy gate — terminal node assembles `ComplianceReport`, frozen exit-code convention (0/1/2, enum {0,1,2,130}); flips shipped inverted `inventory-match --policy` enum with one-release `INVENTORY_MATCH_LEGACY_EXIT=1` window; Dagster halt + A2A alert. (Story F4.)
- FR-19: Basilisk conda-native vulnerability source — querybatch (≤1,000) + bounded detail fetch; name-not-ecosystem-tag matching; tri-state `fix_available`; offline-skip + `BASILISK_BASE_URL` hedges. (Story B8; Q7.)
- FR-20: Release-to-availability velocity — `release_lag_hours`/`release_lag_qualifies` on Phase H join; ≤90-day window; first-availability (min per-build repodata timestamp) never `latest_conda_upload`; both 83.7% coincidence measurements re-verified at B9. (Story B9.)
- FR-21: Migration-readiness — conda-forge-bot-data status datasets partitioned by active migration (zero code change for new migrations); four-way readiness split; `not-in-tracker` labeled inference. (Story B10.)
- FR-22: AI Software Factory layer — wiki scaffold + 5 personas (H1), agno crews (H2), La Suite/Wagtail REST sync (H3), Dagster-triggered crews (H4); storage services conda-forge-provisioned. (Stories H1–H4.)

Total FRs: 22.

### Non-Functional Requirements

The PRD carries no separately-numbered NFR list; NFR content is embedded in FR consequences, § 7 Success Metrics, and § 11 Risks. Extracted for traceability:

- NFR-A (Performance, honest scoping): win = incremental re-materialization, never cold-start miracle; F1 benchmark records warm AND cold wall-clock; threshold fixed in F1 story spec pre-benchmark (SM-3, SM-C1, AC-7).
- NFR-B (Security/credentials): per-destination-host credential scoping (FR-1); non-JFrog hosts never receive `X-JFrog-Art-Api`; loop gates non-credentialed; Phase P admin-opt-in `PHASE_P_ENABLED=1`, never loop-reachable; credentialed runs are attended.
- NFR-C (Enterprise/air-gapped portability): 20 `resolve_*_urls` override points survive; consumer profile works air-gapped; offline degrade paths (`unresolved` marker, Basilisk offline-skip → stale-not-fail).
- NFR-D (Reliability/resumability): interrupted runs resume from persisted intermediates; per-node timeouts; scheduled retries; contracts halt bad data pre-persist.
- NFR-E (Observability): per-node OpenLineage events; end-to-end OTel traces to named API calls; Dagster per-node state/retries/timings.
- NFR-F (Provisioning/toolchain): conda-forge-only, pixi-first, py3.14 floor, no JVM/standalone binaries; `llms-full-check` drift gate; GX ≤1.18.2 ceiling.
- NFR-G (Determinism of verification): all loop gates fixture-based, non-credentialed, `--frozen`, tracked test tree (never `.claude/data/`).
- NFR-H (Rate/cost discipline): Phase K 3-RPS token bucket, Phase P two-layer cost gate, Basilisk ≤1,000/request + standard rate-limit discipline.
- NFR-I (Agent-legibility/accessibility): Vizro pages use semantic HTML, ARIA, deterministic layouts (spec § 2.1 bar).
- NFR-J (Data freshness): derived layer under the 14-day freshness contract; per-dataset TTLs.

### Additional Requirements & Constraints

- Execution-model constraints (binding, § 6.2): graduated autonomy; sequential loop (`max_parallel=1`); verify-first (loop never enters a wave whose gate doesn't exist); attended boundary events (B4, C1, D3, F1, G2); preconditions (hooks approval, `scripts/bmad-switch conda-forge-atlas-datapipeline`, worktree symlink bootstrap, keystone budget review B1/B2/F1).
- CLAUDE.md Rule 1/2 integration: recipe/atlas-touching stories invoke `conda-forge-expert`; closeout CFE retro mandatory.
- Frozen contracts: FR numbering, story IDs, § 12 out-of-scope boundary, exit-code enum {0,1,2,130}.
- Open questions Q1–Q4, Q6, Q7 adopted at § 11 defaults, re-checked at gating waves; Q5 retired into FR-22.
- Conditional surface: trendshift Phase T joins if Track A ships before Wave B completes.

### PRD Completeness Assessment

Strong: complete FR set with testable consequences per FR; explicit non-goals (verbatim § 12 boundary); success metrics mapped FR↔SM↔AC including deliberate extensions (SM-11, SM-12) covering AC-gap areas; counter-metrics; decision audit trail (§ 9, 12 numbered decisions incl. 2 tagged assumptions); risks with tripwires and ramps; addendum separates architecture-input depth. No unresolved placeholders. Weaknesses: none blocking at PRD level; NFRs are embedded rather than enumerated (acceptable — extracted above; the binding test surface is the spec's story ACs).

## Epic Coverage Validation

### Coverage Matrix

Cross-checked two ways: the epics.md FR Coverage Map table, and the per-story `**FRs:**` tags (both directions).

| FR | PRD Requirement (short) | Epic Coverage | Status |
|---|---|---|---|
| FR-1 | Declarative Data Catalog + per-host credentials | Epic 2: A2 | Covered |
| FR-2 | 23 phases → 7 DAG pipelines w/ engineering contracts | Epic 3: B1, B2, B5, B6 | Covered |
| FR-3 | `IncrementalParquetDataset` per-dataset TTLs | Epic 2: A3 | Covered |
| FR-4 | `phase_state` removed; Kedro-native resumability | Epic 2: A3 (primitive) + Epic 3: B4 (retirement) | Covered |
| FR-5 | DuckDB singularity (compute/graph/`vss`) | Epic 7: F1, F3 | Covered |
| FR-6 | Dagster schedules/retries/profiles/per-node timeouts/sensors | Epics 3/4/8/9: B5, C1, C2, G3, H4 | Covered |
| FR-7 | MCP surface over Kedro APIs | Epic 3: B3 | Covered |
| FR-8 | BSL over the catalog | Epic 5: D1 | Covered |
| FR-9 | 28 CLIs → Vizro/Vizro-AI + `query_vizro_ai` | Epic 5: D2, D3 | Covered |
| FR-10 | Contracts halt bad data (pandera-first, GX-capped) | Epic 7: F2, F4 | Covered |
| FR-11 | A2A inter-agent interface | Epic 6: E1 | Covered |
| FR-12 | OpenLineage + OTel | Epic 6: E2 | Covered |
| FR-13 | SBOM → CycloneDX, `cfe:*` + qualifier preserved | Epic 3: B7 | Covered |
| FR-14 | WASM portability + static Parquet host | Epic 8: G1, G2 | Covered |
| FR-15 | Pixi-first, nebi, conda-forge-only, py3.14 | Epic 2: A1 | Covered |
| FR-16 | deptry hygiene node | Epic 7: F4 | Covered |
| FR-17 | Transitive resolution + universe BOM | Epic 3: B7 | Covered |
| FR-18 | Unified CI policy gate + enum flip | Epic 7: F4 | Covered |
| FR-19 | Basilisk ingestion | Epic 3: B8 | Covered |
| FR-20 | Release-to-availability velocity | Epic 3: B9 | Covered |
| FR-21 | Migration-readiness datasets | Epic 3: B10 | Covered |
| FR-22 | Factory layer (a–d) | Epic 9: H1(a), H2(b), H3(c), H4(d) | Covered |

Reverse direction: no story claims an FR absent from the PRD. Story 0.1 carries no FR by design (spec-explicit enabler, D-13). The epics FR Coverage Map table and the per-story FR tags agree exactly (B5 tags FR-2 + FR-6, matching both map rows).

### Missing Requirements

None. Zero FRs uncovered.

### NFR coverage note (beyond the step's FR mandate)

epics.md enumerates NFR-1..NFR-12 (extracted from PRD/Spine) and binds them via story invariants (AD-x tags); every PRD-embedded NFR extracted in this report's PRD Analysis (NFR-A..J) maps into epics NFR-1..12 plus the Consistency Conventions block. No orphan NFR.

### Coverage Statistics

- Total PRD FRs: 22
- FRs covered in epics: 22
- Coverage: 100%

## UX Alignment Assessment

### UX Document Status

Not found — and **N/A by design**, not a gap. Verified: no `*ux*` artifact under planning-artifacts. epics.md D-11 records the rationale: no bmad-ux spine pair exists for this data-pipeline effort; zero UX-DRs is correct.

### UI-implied analysis

UI surfaces DO exist in scope (Vizro dashboard D2, Vizro-AI field D3, WASM in-browser surface G1). The planning set handles this without a separate UX artifact via a spec-native substitute chain, verified aligned across all three documents:

- PRD § 4.5 (FR-9): frontend work in Waves D/G preceded by the CIS two-spine specs (`DESIGN.md` + `EXPERIENCE.md`, spec § 2.4); § 2.1 agent-legibility bar (semantic HTML, ARIA, deterministic layouts).
- Architecture: AD-8 (all read surfaces translate through BSL), Spine Deferred item "D2 CIS two-spine design specs" with a named owner story.
- Epics: NFR-8 carries the agent-legibility bar; D2/D3/G1 ACs restate the CIS precondition; D2 is DEV-AUTO (visual judgment) rather than loop-driven; SM-C4 bounds public page breadth.

### Alignment Issues

None. The three documents state the same substitute contract with no contradiction.

### Warnings

- (Non-blocking observation) The CIS two-spine specs do not exist yet — deliberately deferred to the D2 story spec (Spine Deferred, owner assigned). Not a readiness blocker: they are a Wave-D story-entry precondition, waves A–C are unaffected, and the deferral has a recorded owner + resolution point. Flagged so sprint planning schedules the CIS spec work before D2 opens.
