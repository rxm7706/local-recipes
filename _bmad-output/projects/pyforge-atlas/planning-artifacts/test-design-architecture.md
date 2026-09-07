---
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-09-07'
workflowType: 'testarch-test-design'
inputDocuments:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/test-architecture.md
  - pixi.toml (pyforge-atlas verify-gate task descriptions)
---

# Test Design for Architecture: pyforge-atlas (Kedro/Dagster/DuckDB Migration)

**Purpose:** Architectural concerns, testability gaps, and NFR requirements for review by the
Atlas/platform team. Serves as a contract on what must be addressed before the legacy orchestrator
is retired and before further automated coverage is committed to the Dagster daemon path.

**Date:** 2026-09-07
**Author:** Rxm7706 (TEA — Master Test Architect)
**Status:** Architecture Review Pending
**Project:** pyforge-atlas
**PRD Reference:** `planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md`
**ADR Reference:** `planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md`

> **Retrofit note:** this is a *system-level* test design produced after most of the system already
> shipped (24 epics / 91 stories in `epics.md`, per the mechanically-generated baseline
> `test-architecture.md`). TEA was not present at intake. Accordingly, "blockers" below are reframed
> from "pre-implementation" to "pre-legacy-retirement" — the one gate this system has not yet passed.

---

## Executive Summary

**Scope:** The Kedro/Dagster/DuckDB migration of the legacy `cf_atlas` orchestrator: 10 as-built
pipeline packages (the sealed seven — core, pypi_intelligence, vulnerability, vcs_health,
universal_sbom, seed_gaps, derived_artifacts — plus `upstream_discovery`, `artifactory_downloads`,
`query_plane_cache`), a BSL/Ibis semantic layer, a Vizro dashboard + WASM read surface, MCP/A2A agent
interfaces, and a Wave-H AI-factory layer.

**Business Context** (from PRD):

- **Problem:** the legacy procedural orchestrator's `phase_state` checkpointing, global TTL constant,
  and 1800s coarse timeout silently dropped phases; agents could not safely trigger or introspect it.
- **Revenue/Impact:** internal factory-productivity tool, not customer-revenue-facing; success is
  measured by parity + agent-maintainability (SM-1, SM-2), not by an external SLA.
- **GA Launch:** the migration itself shipped 2026-07-18; the system is now in a post-ship
  reconciliation phase (Epics 10, 12–24 landed since).

**Architecture** (from the spine's AD-1..23):

- **Key decision 1 (AD-1/AD-4):** the Kedro DAG is the sole source of truth; DuckDB+Parquet is the
  only compute/graph/vector engine (no SQLite, no Neo4j/Kùzu/LanceDB/Polars).
- **Key decision 2 (AD-11):** verify-first — every wave's first deliverable is its own deterministic,
  offline, `--frozen` fixture gate; credentialed events stay attended and human-signed-off.
- **Key decision 3 (AD-23):** one execution plane — Dagster, MCP triggers, and CLI all ride the same
  Kedro job with a single OS-file-lock admission mechanism per output dataset.

**Expected Scale** (from ADR): ~3 GB local storage budget (vdb store dominant at 2.5 GB); operator
workstation + a sequential, worktree-isolated bmad-loop execution plane; no persistent daemon unless
Wave-G sensors force it (Q2, deferred).

**Risk Summary:**

- **Total risks:** 9 (3 high-priority ≥6, 4 medium, 2 low)
- **Test effort (gap-closing only — see companion QA doc's Effort Estimate table):** 2 net-new items, ~12–25 hours

---

## Quick Guide

### 🚨 BLOCKERS — Team Must Decide (Blocks Legacy Retirement)

1. **R-002: B4 credentialed parity sign-off is still pending** — the production data path remains
   the legacy orchestrator (`AD-19`'s "after B4 retires the legacy write path" clause is still
   pre-B4). No further legacy-retirement work should be scheduled until this attended event runs and
   its evidence is recorded (recommended owner: Atlas station lead).
2. **R-005: legacy-consumption cutover has no owner** — production consumers of
   `conda_forge_server.py` (Doctor's four-axis reads foremost) are not yet re-backed onto
   Kedro/DuckDB reads; the architecture's own 2026-08-26 currency reconciliation flags this story as
   "still unowned" (recommended owner: TBD — needs assignment before B4 sign-off is scheduled).
3. **R-003: AD-23 lock-release asymmetry is untested on the failure path** — acquisition is identical
   across the CLi/MCP/Dagster planes, but release is not: a Dagster multiprocess-executor subprocess
   exit, or a run failing before `on_pipeline_error` fires, can leave the per-dataset lock held with
   no automated regression covering that path (recommended owner: Atlas/platform, before the Wave-C
   daemon (DW-C1-1) goes live).

**What we need from team:** a decision/owner on these 3 items before scheduling further
legacy-retirement or Dagster-daemon work.

---

### ⚠️ HIGH PRIORITY — Team Should Validate

1. **R-001: Dagster-under-Prefect exit-ramp tripwire** — the two-condition trigger (a Kedro/Dagster
   minor breaks `kedro-test`'s import smoke **and** no upstream fix within 60 days) is recommended as
   already-operational; approve or tighten it at the Wave-C (Q2) checkpoint.
2. **R-006: two conda-forge-only exceptions** — `boring-semantic-layer` and `kedro-mcp` are
   PyPI-sourced (recorded AD-16 exception); recommend prioritizing the "package to conda-forge"
   candidate CFE task if either sees a security advisory before that lands.
3. **R-007: F1 benchmark pass threshold is still unset** — SM-3's incremental-vs-full-rebuild claim
   has no fixed numeric bound yet; recommend fixing it in the F1 story spec before the attended
   benchmark runs, per the architecture's own Deferred-list instruction.

**What we need from team:** review recommendations and approve (or adjust the thresholds/tripwires).

---

### 📋 INFO ONLY — Solutions Provided

1. **Test strategy:** pytest across 23 test directories (unit, integration, and fixture-based
   contract tests) plus two Python-`playwright.sync_api` browser gates (`test_dashboard_e2e.py`,
   `test_wasm_smoke.py`) — no JS/TS Playwright stack is in play here.
2. **Tooling:** 8 named pixi verify-gate tasks (`kedro-test`, `kedro-catalog-check`, `parity-diff`,
   `dagster-dryrun`, `bsl-metric-check`, `duckdb-singularity`, `wasm-smoke`, `query-plane-parity`),
   each the first deliverable of its wave per AD-11, all offline and `--frozen`.
3. **Tiered CI/CD:** PR-time = all 8 gates (offline, fixture-only); attended wave-boundary events
   (B4, F1, C1 Dagster bring-up, G2 publish, D3 LLM backend) are human-scheduled, not cron-scheduled —
   this system has no nightly/weekly k6 or chaos tier.
4. **Coverage:** the mechanically-generated baseline (`test-architecture.md`) already inventories 129
   test files against 91 stories; this document reprioritizes that surface by risk tier rather than
   re-deriving a story-by-story matrix.
5. **Quality gates:** see companion QA doc's Quality Gate criteria.

**What we need from team:** review and acknowledge.

---

## For Architects and Devs — Open Topics 👷

### Risk Assessment

**Total risks identified:** 9 (3 high-priority score ≥6, 4 medium, 2 low)

#### High-Priority Risks (Score ≥6) — IMMEDIATE ATTENTION

| Risk ID   | Category | Description                                                                                                             | Probability | Impact | Score  | Mitigation                                                                                     | Owner            | Timeline               |
| --------- | -------- | ------------------------------------------------------------------------------------------------------------------------| ------------ | ------ | ------ | ------------------------------------------------------------------------------------------------| ---------------- | ----------------------- |
| **R-001** | TECH     | Dagster acquired by Prefect (2026-07-13); `kedro-dagster` bus factor ≈ 1, carries `dagster <2.0` pin (AD-1/AD-6)         | 2            | 3      | **6**  | Exit ramps (Dagster Components / Kedro's Prefect deployer); Q2 re-verify at Wave C; two-condition tripwire | Atlas station    | Wave C start            |
| **R-002** | OPS      | B4 credentialed parity gate not yet run; legacy orchestrator remains the production data path (AD-19, DW-B4-1/DW-B4-2) | 2            | 3      | **6**  | Attended parity gate + recorded evidence before any retirement work proceeds                   | Atlas station lead | Before legacy retirement |
| **R-003** | TECH     | AD-23 lock-release asymmetry: Dagster multiprocess drop + failed-run non-release + lock-store-inside-data-tree hazard (DW-AD23-2) | 2 | 3 | **6** | Add a multiprocess-drop regression test or a lock-staleness reaper before the Wave-C daemon goes live | Atlas/platform   | Before DW-C1-1 daemon    |

#### Medium-Priority Risks (Score 3-5)

| Risk ID | Category | Description                                                                                                       | Probability | Impact | Score | Mitigation                                                                          | Owner         |
| ------- | -------- | ------------------------------------------------------------------------------------------------------------------| ------------ | ------ | ----- | -------------------------------------------------------------------------------------| ------------- |
| R-005   | OPS      | Production MCP consumers (Doctor's 4-axis reads) still ride legacy `conda_forge_server.py`; re-backing unowned (currency reconciliation 2026-08-26) | 2 | 2 | 4 | Charter an owning story before scheduling B4 sign-off                              | TBD           |
| R-006   | TECH     | Two PyPI-sourced deps (`boring-semantic-layer`, `kedro-mcp`) outside conda-forge-only doctrine (AD-16 recorded exception) | 2 | 2 | 4 | Track as a candidate CFE packaging task; both pinned and recorded, not silent      | Atlas/CFE     |
| R-007   | PERF     | F1 cold-start/warm-incremental benchmark not yet run; SM-3's pass threshold unset (DW-F1-1)                       | 2            | 2      | 4     | Fix the numeric threshold in the F1 story spec before the attended benchmark runs   | Atlas station |
| R-008   | SEC      | Credential leakage under loop bypass-permissions if FR-1 per-host scoping regresses (PRD §11)                     | 1            | 3      | 3     | Phase P stays admin-opt-in + non-credentialed; loop paths never touch live creds    | Atlas station |

#### Low-Priority Risks (Score 1-2)

| Risk ID | Category | Description                                                                                          | Probability | Impact | Score | Action  |
| ------- | -------- | -------------------------------------------------------------------------------------------------------| ------------ | ------ | ----- | ------- |
| R-009   | OPS      | MinIO exists only as a Python SDK in-env; server provisioning is an open Wave-H precondition (AD-22) | 2            | 1      | 2     | Monitor |
| R-010   | DATA     | GX version-ceiling drift: no story may depend on GX ≥1.19 features (AD-9); currently a policy, not a code gate | 1 | 2 | 2 | Monitor |

#### Risk Category Legend

- **TECH**: Technical/Architecture (flaws, integration, scalability)
- **SEC**: Security (access controls, auth, data exposure)
- **PERF**: Performance (SLA violations, degradation, resource limits)
- **DATA**: Data Integrity (loss, corruption, inconsistency)
- **BUS**: Business Impact (UX harm, logic errors, revenue)
- **OPS**: Operations (deployment, config, monitoring)

---

### NFR Testability Requirements

**Purpose:** Capture what architecture must provide so NFR validation can be automated later. This is
planning guidance, not final evidence assessment.

| NFR Category    | Threshold / Requirement                                                             | Current Design Support | Gap / Decision Needed                                              | Planned Evidence                                    |
| ---------------- | ------------------------------------------------------------------------------------| ----------------------- | ---------------------------------------------------------------------| ----------------------------------------------------|
| Security         | Per-destination-host credential scoping; no host outside its own credential (FR-1)  | Supported               | R-008: regression if FR-1 discipline slips under loop bypass-permissions | `kedro-catalog-check` per-host stub-credential test |
| Performance      | Incremental re-materialization beats legacy full-rebuild wall-clock (SM-3)          | Partial                 | **UNKNOWN** — pass threshold not yet fixed (R-007)                  | F1 attended benchmark record (cold + warm wall-clock) |
| Reliability      | Offline sources skip-and-mark-stale, never hard-fail (AD-13); admission serializes writers (AD-23) | Supported / Partial | R-003: Dagster-multiprocess lock-release path has no regression test | `tests/test_admission.py` (existing) + proposed multiprocess-drop test |
| Maintainability  | Every dependency change updates `docs/library-llms-full.md` in the same PR (AD-16)  | Supported               | None identified                                                     | `llms-full-check` CI task                           |

**Unknown thresholds:** the F1 performance pass threshold (SM-3) is the one explicitly unset NFR
value in this system — it is not guessed here; it is carried as risk R-007 and as an open item in the
architecture's own Deferred list ("F1 benchmark pass threshold → fixed in the F1 story spec before the
benchmark runs").

**Assessment boundary:** final PASS/CONCERNS/FAIL status belongs in `nfr-assess` after implementation
evidence exists.

---

### Testability Concerns and Architectural Gaps

**🚨 ACTIONABLE CONCERNS — Architecture Team Must Address**

#### 1. Blockers to Fast Feedback (WHAT WE NEED FROM ARCHITECTURE)

| Concern                                      | Impact                                                                 | What Architecture Must Provide                                                             | Owner            | Timeline                 |
| --------------------------------------------- | ------------------------------------------------------------------------| ----------------------------------------------------------------------------------------------| ---------------- | ------------------------- |
| **Attended-gate evidence isn't machine-checkable** | B4/F1/C1/G2/D3 are human-signed-off events with no fixture proving they ran; a regression in the live comparison itself could pass unnoticed between events | A recorded-evidence artifact (timestamp + operator + result), referenced (not gated) by CI  | Atlas station    | Before next B4/F1 re-run  |
| **AD-23 lock-release asymmetry untested**    | A wedged lock silently blocks every subsequent run on that dataset until process exit; only the two-process contention path is fixture-covered | Either a lock-staleness reaper or an explicit test exercising the multiprocess-drop scenario | Atlas/platform   | Before DW-C1-1 daemon     |
| **MCP-consumption cutover has no owner**     | Legacy retirement cannot proceed safely while Doctor's four-axis reads (and any other consumer) still depend on `conda_forge_server.py` | A chartered story to re-back those reads onto Kedro/DuckDB, or an explicit decision to keep both surfaces indefinitely | TBD (unowned)    | Before B4 sign-off scheduled |

#### 2. Architectural Improvements Needed (WHAT SHOULD BE CHANGED)

1. **Lock-staleness detection (AD-23)**
   - **Current problem:** release semantics differ by execution plane (CLI/MCP release cleanly;
     Dagster's multiprocess executor and a failed run before `on_pipeline_error` do not).
   - **Required change:** a TTL-based staleness check or reaper on `<data_root>/.locks`, or an
     explicit test proving the multiprocess-drop path is safe as-is.
   - **Impact if not fixed:** two writers can proceed against the same dataset (documented as an
     availability boundary today, not yet a correctness one — but untested).
   - **Owner:** Atlas/platform. **Timeline:** before the Wave-C daemon goes live.

---

### Testability Assessment Summary

**📊 CURRENT STATE — FYI**

#### What Works Well

- Every wave's first deliverable is its own deterministic, offline, `--frozen` fixture gate (AD-11) —
  no credentialed/live-network flakiness in the automated gate suite itself.
- Legacy contract fixtures (Phase P cost gate, Phase K token bucket, provenance discipline, no-clobber
  writeback, `test_no_thirty_gb_lie`) carried over verbatim (AD-10), giving regression continuity
  across the rewrite rather than a fresh, unproven test suite.
- A fixed, three-way degradation vocabulary (`stale` / `unresolved` / `not-applicable`, AD-13) makes
  offline and air-gapped paths predictable rather than opaque failures.
- One frozen exit-code convention (AD-12: 0/1/2/130) makes CI policy assertions uniform across all 10
  pipeline packages.

#### Accepted Trade-offs (No Action Required)

For this migration, the following trade-offs are acceptable:

- **Attended, credentialed events stay outside the automated gate set** (AD-11) — acceptable because
  they need live infrastructure or human judgment the loop must never touch unsupervised; revisit only
  if a safe read-only simulation becomes possible.
- **Two PyPI-sourced dependencies bypass conda-forge-only** (AD-16 recorded exception) — acceptable
  short-term since both are pinned and tracked as a candidate CFE packaging task (R-006).

This is technical debt (R-006) or an explicit design boundary (attended events) that should be
revisited opportunistically, not treated as a defect.

---

### Risk Mitigation Plans (High-Priority Risks ≥6)

**Purpose**: detailed mitigation strategies for the 3 high-priority risks (score ≥6). These MUST be
addressed before legacy-orchestrator retirement.

#### R-001: Dagster-under-Prefect deterioration (Score: 6) - HIGH

**Mitigation Strategy:**

1. Confirm the two-condition tripwire is monitored: a Kedro/Dagster minor breaking `kedro-test`'s
   import smoke, AND no upstream fix/acknowledged issue within 60 days.
2. If triggered, invoke the AD-1 exit ramp (Dagster Components or Kedro's Prefect deployer) — the
   Kedro DAG stays source of truth either way.
3. Re-verify at the Wave-C (Q2) checkpoint regardless of trigger state.

**Owner:** Atlas station. **Timeline:** Wave C start (ongoing watch). **Status:** Planned.
**Verification:** `kedro-test`'s import smoke stays green; no manual intervention needed unless the
tripwire fires.

#### R-002: B4 parity sign-off pending (Score: 6) - HIGH

**Mitigation Strategy:**

1. Schedule the attended B4 credentialed parity comparison (exact row-count + value parity on the
   `v_actionable_packages`-family views, per Q1's adopted default).
2. Record the evidence (timestamp, operator, diff result) alongside the existing `parity-diff`
   fixture-gate output.
3. Only after recorded sign-off, proceed with `phase_state`/`bootstrap-data` retirement.

**Owner:** Atlas station lead. **Timeline:** before any further legacy-retirement work. **Status:**
Planned. **Verification:** a dated evidence record exists and is referenced from the deferred-work
ledger.

#### R-003: AD-23 lock-release asymmetry (Score: 6) - HIGH

**Mitigation Strategy:**

1. Add a regression test exercising the Dagster multiprocess-executor lock-drop path (currently only
   the two-process CLI/MCP contention path is covered by `tests/test_admission.py`).
2. Evaluate a lock-staleness reaper (TTL-based) as an alternative or complement to a code-level fix.
3. Document the decision either way before the Wave-C daemon (DW-C1-1) goes live.

**Owner:** Atlas/platform. **Timeline:** before DW-C1-1. **Status:** Planned. **Verification:** a new
or extended `tests/test_admission.py` case covers the multiprocess-drop scenario, or a documented
decision to accept the risk is recorded.

---

### Assumptions and Dependencies

#### Assumptions

1. The 3 pipeline packages added after the original spine (`upstream_discovery`,
   `artifactory_downloads`, `query_plane_cache`) share AD-11's gate discipline, even though this pass
   did not independently re-verify each one's fixture coverage.
2. `kedro-dagster` ≥0.7.0 and its `dagster <2.0` pin remain solvable on Python 3.14 for the life of
   this test design; `kedro-test`'s import smoke is the only standing proof today.
3. The baseline (`test-architecture.md`, fingerprint `214630df01054361`, 91 stories / 129 test files)
   is current as of this run; anything added after that fingerprint is not reflected here.

#### Dependencies

1. B4 credentialed parity sign-off — required before any "legacy retired" coverage claim can be
   tested.
2. MinIO server provisioning decision — required before Wave-H factory-layer tests can exercise real
   object storage rather than the SDK alone.
3. Q2 Wave-C Dagster-acquisition re-verify — required before committing further automated coverage to
   the Dagster daemon path.

#### Risks to Plan

- **Risk**: this test design was produced retroactively over an already-largely-shipped system (24
  epics / 91 stories already exist) rather than pre-implementation.
  - **Impact**: some "pre-implementation blockers" a green-field TEA run would name don't apply here;
    they are reframed above as pre-legacy-retirement blockers instead.
  - **Contingency**: treat this document as a risk-tiered testability audit of the shipped system, not
    a green-field test plan; run epic-level TEA on any *new* epic before it ships, rather than folding
    it retroactively into this system-level document.

---

**End of Architecture Document**

**Next Steps for Architecture Team:**

1. Review Quick Guide (🚨/⚠️/📋) and assign owners for the 3 blockers.
2. Approve or adjust the R-001/R-006/R-007 recommendations.
3. Validate assumptions and dependencies above.
4. Feed back to QA on the companion doc's coverage plan.

**Next Steps for QA Team:**

1. Wait for the R-002/R-005/R-003 blockers to be resolved before claiming legacy-retirement coverage.
2. Refer to the companion QA doc (`test-design-qa.md`) for the coverage plan and code patterns.
3. Prioritize the 3 net-new gap-closing items (multiprocess-drop test, evidence-recording artifact,
   MCP-cutover story) over re-testing what already exists.
