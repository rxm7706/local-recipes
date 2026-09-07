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
  - src/shared/packages/pyforge-atlas/tests/dashboard/test_dashboard_e2e.py
  - src/shared/packages/pyforge-atlas/tests/wasm/test_wasm_smoke.py
---

# Test Design for QA: pyforge-atlas (Kedro/Dagster/DuckDB Migration)

**Purpose:** Test execution recipe for the QA/platform team. Defines what to test, how to test it, and
what QA needs from other teams — prioritized by risk, not by re-listing every existing story.

**Date:** 2026-09-07
**Author:** Rxm7706 (TEA — Master Test Architect)
**Status:** Draft
**Project:** pyforge-atlas

**Related:** See `test-design-architecture.md` for testability concerns and architectural blockers.
**Also related:** `test-architecture.md` (mechanically-generated, story-by-story test-file inventory;
this document deliberately does not duplicate that matrix — see § Not in Scope).

---

## Executive Summary

**Scope:** risk-tiered test coverage for the already-largely-shipped pyforge-atlas migration (10
pipeline packages, BSL/Ibis semantic layer, Vizro dashboard + WASM read surface, MCP/A2A interfaces,
Wave-H AI factory). This document names the *gaps* in an existing, substantial test suite rather than
proposing a from-scratch plan.

**Risk Summary:**

- Total Risks: 9 (3 high-priority score ≥6, 4 medium, 2 low)
- Critical categories: OPS and TECH (legacy-retirement readiness, AD-23 concurrency)

**Coverage Summary:**

- P0 tests: 4 (critical paths — admission locking, parity, policy gate, engine singularity)
- P1 tests: 5 (orchestration dryrun, BSL parity, offline degradation, WASM smoke, query-plane parity)
- P2 tests: 3 (new-signal binding guards, dependency-drift gate, Wave-H fixture suite)
- P3 tests: 2 (GX-ceiling static guard, exploratory DAG-view cross-check)
- **Total**: ~14 named scenarios, of which **~11 already exist** as pixi verify-gate tasks or
  fixture suites; **~3 are net-new gap-closing work** (~25–55 hours, well under 2 weeks for 1
  engineer)

---

## Not in Scope

**Components or systems explicitly excluded from this test plan:**

| Item                                                                    | Reasoning                                                                                     | Mitigation                                                                 |
| ------------------------------------------------------------------------| ------------------------------------------------------------------------------------------------| -----------------------------------------------------------------------------|
| **Unity Data Stack satellite** (AD-24..46 in the same architecture file) | Draft-status PRD/architecture folded in verbatim 2026-08-02; no atlas epic implements it        | Re-run system-level TEA when/if it graduates from draft to active scope    |
| **Wasm Analytics Stack satellite** (AD-47..56)                          | Same — a separate draft satellite initiative, not an atlas deliverable                          | Same                                                                       |
| **Credentialed/live-network attended events** (B4 parity comparator, F1 benchmark, C1 Dagster bring-up, G2 static-host publish, D3 LLM backend wiring) | AD-11 deliberately keeps these attended, human-signed-off, wave-boundary events outside the automated gate set | Covered by the recorded-evidence mitigation in the architecture doc, not by automated coverage here |
| **Wave-H external services** (PostgreSQL, MinIO *server*)              | MinIO exists only as a Python SDK in-env; server provisioning is an open Deferred item (R-009)  | Fixture-mode crew tests already cover the code paths against a mock/fixture wiki |
| **The legacy `conda_forge_server.py` MCP surface itself**              | Owned by the `conda-forge-expert` skill, not the atlas station; atlas only audits which of its tools are atlas-relevant | Covered by CFE's own test suite                                           |
| **Full 28-CLI dashboard inventory**                                    | Deferred by the PRD itself (`DW-D2-1`); only the 8 dashboard pages + factory-status page shipped in v1 | Re-scope when `DW-D2-1` is picked up                                       |

**Note:** items listed here have not been separately re-reviewed by QA/Dev/PM in this pass; they are
carried forward from the PRD's/architecture's own scope boundaries.

---

## Dependencies & Test Blockers

**CRITICAL:** QA cannot claim "legacy-retirement-ready" coverage without these items from other teams.

### Backend/Architecture Dependencies (Pre-Retirement)

**Source:** see architecture doc's "Quick Guide" for detailed mitigation plans.

1. **B4 credentialed parity evidence** — Atlas station — before the B4 attended event
   - What QA needs: the recorded parity-diff evidence artifact (Q1 default: exact row-count + value
     parity on the `v_actionable_packages`-family views).
   - Why it blocks: no fixture substitutes for the live comparison; QA's `parity-diff` pytest suite
     (`tests/parity`) already covers the fixture half only.

2. **F1 benchmark pass threshold** — Atlas station — before the F1 attended event
   - What QA needs: the fixed numeric threshold from the F1 story spec (currently unset, R-007).
   - Why it blocks: without a threshold, `duckdb-singularity`'s benchmark half (DW-F1-1) has no
     pass/fail criterion to automate.

### QA Infrastructure Setup (Already in Place)

1. **Test Data Factories** — fixture Parquet/CSV samples already exist per pipeline under
   `tests/fixtures/`, `tests/parity/`, `tests/semantic/`; contract fixtures (cost-gate, token-bucket,
   provenance, no-clobber) are carried over verbatim from the legacy system (AD-10) — no new factory
   pattern is needed.
2. **Test Environments**
   - Local: the `pyforge-atlas` pixi feature/environment; gates run via `pixi run -e pyforge-atlas
     <task>` (e.g. `kedro-test`, `kedro-catalog-check`).
   - CI/CD: the same pixi tasks, run `--frozen` and offline — no separate staging environment is
     declared (the architecture's "Deployment & environments" section lists only the operator
     workstation and the loop execution plane).

**Adapted example** (this station is Python/pytest, not TypeScript/Playwright — the template's
default `@seontechnologies/playwright-utils` example does not apply to a Python codebase; see
Appendix A for the real, in-repo pattern this station uses):

```python
# tests/dashboard/test_dashboard_e2e.py (real pattern already in this repo)
from playwright.sync_api import sync_playwright, expect
from pyforge.atlas.dashboard.app import build_dashboard

def test_dashboard_smoke(dashboard_server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(dashboard_server.url)
        expect(page.get_by_role("heading")).to_be_visible()
        browser.close()
```

---

## Risk Assessment

**Note:** full risk details in the Architecture doc. This section summarizes risks relevant to QA
test planning.

### High-Priority Risks (Score ≥6)

| Risk ID   | Category | Description                                             | Score | QA Test Coverage                                                                 |
| --------- | -------- | ----------------------------------------------------------| ----- | ------------------------------------------------------------------------------------|
| **R-001** | TECH     | Dagster-under-Prefect deterioration (`kedro-dagster` bus factor ≈ 1) | **6** | `dagster-dryrun`'s import-smoke half already gates this; no additional QA action beyond monitoring the tripwire |
| **R-002** | OPS      | B4 parity sign-off pending; legacy is still the production path | **6** | `parity-diff` fixture gate covers the code half; the credentialed half is architecture-owned (not QA-automatable) |
| **R-003** | TECH     | AD-23 lock-release asymmetry on the Dagster-multiprocess path | **6** | P0-001 below (net-new) |

### Medium/Low-Priority Risks

| Risk ID | Category | Description                                                        | Score | QA Test Coverage                                                    |
| ------- | -------- | ---------------------------------------------------------------------| ----- | ------------------------------------------------------------------------|
| R-005   | OPS      | Doctor's 4-axis reads still ride legacy `conda_forge_server.py`     | 4     | Not QA-automatable — an ownership/charter gap, not a test gap        |
| R-006   | TECH     | Two PyPI-sourced deps outside conda-forge-only doctrine              | 4     | P2-002 (`llms-full-check`, existing)                                  |
| R-007   | PERF     | F1 benchmark threshold unset                                         | 4     | Blocked on architecture team fixing the threshold (see Dependencies) |
| R-008   | SEC      | Credential-scoping regression under loop bypass-permissions          | 3     | Covered by `kedro-catalog-check`'s existing per-host stub-credential test |
| R-009   | OPS      | MinIO server not provisioned                                         | 2     | P2-003 (fixture-mode Wave-H suite, existing)                          |
| R-010   | DATA     | GX version-ceiling drift (no story may use GX ≥1.19 features)        | 2     | P3-001 (static/code-review guard — no automated gate exists today)   |

---

## NFR Test Coverage Plan

**Purpose:** map NFR requirements to planned validation work. This defines what evidence QA should
create or collect; it does not assign final PASS/CONCERNS/FAIL status.

| NFR Category    | Requirement / Threshold                                                   | Planned Validation                                        | Tool / Level                | Evidence Artifact                              | Priority |
| ---------------- | ----------------------------------------------------------------------------| --------------------------------------------------------------| -------------------------------| ---------------------------------------------------| -------- |
| Security         | Per-destination-host credential scoping (FR-1)                            | Stub-credential integration test: a non-JFrog host never receives `X-JFrog-Art-Api` | Integration (pytest)         | `kedro-catalog-check` output (existing)          | P1       |
| Performance      | Incremental re-materialization beats legacy full-rebuild wall-clock (SM-3) | Attended cold + warm wall-clock benchmark against the fixed threshold | Manual/attended (F1 story)   | F1 benchmark record (pending threshold, R-007)   | P1       |
| Reliability      | Admission serializes writers per dataset; offline sources degrade, never fail (AD-13/AD-23) | Two-process contention test (existing) + proposed multiprocess-drop regression | Integration (pytest)         | `tests/test_admission.py` (existing + proposed)  | P0       |
| Maintainability  | Every dependency change updates `docs/library-llms-full.md` in the same PR (AD-16) | CI drift check on every PR touching `pixi.toml`             | Static/CI                    | `llms-full-check` task output                    | P2       |

**Missing thresholds or evidence sources:** the F1 performance threshold (R-007) needs architecture
sign-off before it can be automated; see Dependencies & Test Blockers above.

---

## Entry Criteria

**QA testing cannot begin (on the 3 net-new items) until ALL of the following are met:**

- [ ] R-002/R-005/R-003 blockers acknowledged by the Atlas station lead (owners assigned)
- [ ] F1 benchmark pass threshold fixed in the F1 story spec (unblocks R-007's evidence collection)
- [ ] `pyforge-atlas` pixi environment installable and `kedro-test` green on the target branch
- [ ] Access to `tests/test_admission.py`'s existing two-process contention fixture as a starting
      point for the proposed multiprocess-drop extension

## Exit Criteria

**This gap-closing pass is complete when ALL of the following are met:**

- [ ] All P0 tests passing (existing + the one net-new admission-lock regression test)
- [ ] All P1 tests passing or explicitly triaged
- [ ] No open high-priority (score ≥6) risk lacks either a passing test or a recorded
      architecture-owned mitigation plan
- [ ] Coverage sufficiency agreed by Atlas station lead
- [ ] R-007's threshold question is either resolved or explicitly still pending with the F1 story
      spec referenced as the tracking artifact

---

## Test Coverage Plan

**IMPORTANT:** P0/P1/P2/P3 = **priority and risk level**, NOT execution timing. See "Execution
Strategy" for when tests run. Scenarios are organized by capability/architecture-invariant (FR-/AD-ID),
not by story ID — the companion mechanically-generated `test-architecture.md` already carries the
story-by-story file inventory; duplicating it here would add noise, not signal.

### P0 (Critical)

**Criteria:** Blocks core functionality + High risk (≥6) + No workaround

| Test ID    | Requirement                                                                                          | Test Level        | Risk Link   | Notes                                                             |
| ---------- | --------------------------------------------------------------------------------------------------------| -------------------- | ----------- | ----------------------------------------------------------------- |
| **P0-001** | AD-23: a Dagster multiprocess-executor subprocess exit (or a run failing before `on_pipeline_error`) must not leave the per-dataset lock wedged for later CLI/MCP triggers | Integration (pytest) | R-003       | **Net-new** — extends `tests/test_admission.py`                  |
| **P0-002** | B4 parity: migrated node output vs. legacy snapshot matches exactly (row-count + value) on `v_actionable_packages`-family views | Integration (fixture) | R-002       | Existing — `parity-diff`; credentialed half is architecture-owned |
| **P0-003** | FR-18 policy gate: a policy breach exits 1, an error path exits 2, Dagster halts, and an A2A alert fires (identical to an FR-10 violation) | Integration (pytest) | (FR-18/AD-12) | Existing — `universal_sbom` terminal-node tests                  |
| **P0-004** | AD-4 engine singularity: no `sqlite3` import exists outside the retired legacy tree                 | Static/grep-gated    | (AD-4)      | Existing — `duckdb-singularity`                                  |

**Total P0:** 4 (1 net-new)

---

### P1 (High)

**Criteria:** Important features + Medium/high risk + Common workflows

| Test ID    | Requirement                                                                                     | Test Level               | Risk Link   | Notes                              |
| ---------- | -----------------------------------------------------------------------------------------------------| --------------------------- | ----------- | ------------------------------------ |
| **P1-001** | `dagster-dryrun`: schedules enumerate, each op carries its own timeout, Phase P stays admin-only | Integration (pytest)       | R-001       | Existing — `dagster-dryrun`         |
| **P1-002** | BSL metric parity: staleness/adoption/feedstock-health/downloads/actionable + maintainer join match legacy CLI formula | Integration (pytest) | (AD-8)      | Existing — `bsl-metric-check`       |
| **P1-003** | Offline degradation: an unreachable external source skips gracefully, keeps last-good data, stamps a staleness marker, never hard-fails | Unit/Integration | (AD-13/R-008 boundary) | Existing — per-pipeline fixtures |
| **P1-004** | WASM smoke: browser-side query against the published Parquet artifact succeeds with zero non-loopback requests | E2E (Python `playwright.sync_api`) | (AD-21) | Existing — `wasm-smoke`             |
| **P1-005** | Query-plane parity: library face vs. HTTP/Arrow face return row-identical results; a seeded-divergence negative test proves the gate isn't vacuous | Integration (pytest) | (CAP-19)    | Existing — `query-plane-parity`     |

**Total P1:** 5 (all existing)

---

### P2 (Medium)

**Criteria:** Secondary features + Low/medium risk + Regression prevention

| Test ID    | Requirement                                                                                                     | Test Level      | Risk Link | Notes                                     |
| ---------- | ---------------------------------------------------------------------------------------------------------------| ------------------ | --------- | -------------------------------------------|
| **P2-001** | New-signal binding guards: Basilisk matches by package name not OSV tag; `fix_available` stays tri-state; velocity excludes releases >90 days old and never uses `latest_conda_upload` | Unit (fixture) | (AD-14)   | Existing — per-story fixture suites (B8/B9/B10) |
| **P2-002** | conda-forge-only doctrine: `llms-full-check` passes after any `pixi.toml` dependency change                     | Static/CI        | R-006     | Existing — `llms-full-check`              |
| **P2-003** | Wave-H fixture suite: scaffold layout + persona resolution, crews-on-fixture-wiki, mock-Wagtail idempotent round-trip, sensor-triggered crew dry-run | Integration (pytest) | R-009 | Existing — FR-22 fixture suite            |

**Total P2:** 3 (all existing)

---

### P3 (Low)

**Criteria:** Nice-to-have + Exploratory + Documentation validation

| Test ID    | Requirement                                                                                | Test Level         | Notes                                                        |
| ---------- | -----------------------------------------------------------------------------------------------| ---------------------| ---------------------------------------------------------------|
| **P3-001** | GX-ceiling guard: no test suite currently asserts the absence of GX ≥1.19-only features (R-010) | Static/code-review  | **Gap, not automated today** — recommend a lint rule or CI grep, not urgent |
| **P3-002** | Exploratory: `pixi run viz`'s rendered DAG matches the Structural Seed's pipeline-dependency diagram | Manual/exploratory | No automation planned — periodic manual spot-check            |

**Total P3:** 2 (0 automated; both exploratory/manual by design)

---

## Execution Strategy

**Philosophy:** this system has no k6/chaos/nightly tier today — every automated gate is an offline,
`--frozen` pytest run; the only "long-running" work is the human-scheduled attended events, which are
not CI-cron-scheduled at all.

### Every PR: pytest verify gates

**All 8 named gates** (any priority level):

- `kedro-test`, `kedro-catalog-check`, `parity-diff`, `dagster-dryrun`, `bsl-metric-check`,
  `duckdb-singularity`, `wasm-smoke`, `query-plane-parity` — plus the proposed P0-001 extension.
- All offline, `--frozen`, non-credentialed (AD-11).
- Actual current runtime was not measured in this pass; assumed compatible with a PR-time budget
  given every gate scopes to fixtures rather than live data.

**Why run in PRs:** fast feedback, no expensive infrastructure — the architecture deliberately keeps
every automated gate this cheap.

### Nightly/Weekly: none scheduled

This system has no k6, chaos, or long-running automated suite. The only expensive/slow work is the
attended wave-boundary events below, which run on a human schedule, not a cron schedule.

**Manual/attended events** (excluded from automation by design, per AD-11):

- B4 credentialed parity comparison
- F1 cold-start/warm-incremental benchmark
- C1 Dagster daemon bring-up
- G2 static-host publish
- D3 Vizro-AI LLM backend wiring

---

## QA Effort Estimate

**Gap-closing effort only** (excludes the ~11 scenarios that already exist as pixi tasks/fixture
suites):

| Priority  | Count (net-new) | Effort Range   | Notes                                                        |
| --------- | ---------------- | -------------- | --------------------------------------------------------------|
| P0        | 1                | ~10–20 hours   | Multiprocess-drop lock regression test (P0-001)              |
| P1        | 0                | —              | All 5 P1 scenarios already exist                              |
| P2        | 0                | —              | All 3 P2 scenarios already exist                              |
| P3        | 1                | ~2–5 hours     | GX-ceiling lint/CI guard (P3-001); P3-002 stays manual        |
| **Total** | **2**            | **~12–25 hours** | Well under 1 week for 1 engineer, once R-002/R-005/R-007 architecture decisions land |

**Assumptions:**

- Excludes the architecture-owned items (recorded-evidence artifact, F1 threshold-fixing, MCP-cutover
  story ownership) — those are Atlas-station decisions, not QA test-development effort.
- Assumes the existing `tests/test_admission.py` fixture harness is reusable for the P0-001 extension.

**Dependencies from other teams:** see "Dependencies & Test Blockers" above.

---

## Implementation Planning Handoff

| Work Item                                                    | Owner            | Target Milestone            | Dependencies/Notes                             |
| ---------------------------------------------------------------| ------------------| ------------------------------| ---------------------------------------------------|
| Multiprocess-drop lock regression test (P0-001)               | Atlas/platform    | Before DW-C1-1 daemon        | Extends `tests/test_admission.py`                |
| Recorded-evidence artifact for B4/F1 attended events           | Atlas station     | Before next B4/F1 re-run     | Referenced (not gated) by CI                      |
| MCP-consumption cutover story (Doctor's 4-axis reads)          | TBD (unowned)     | Before B4 sign-off scheduled | Currently flagged unowned in the architecture doc |
| GX-ceiling lint/CI guard (P3-001)                              | Atlas/platform    | Opportunistic                | Low priority, not urgent                          |

---

## Interworking & Regression

**Services and components impacted by this system:**

| Service/Component | Impact                                                                      | Regression Scope                                                         | Validation Steps                                             |
| -------------------| -------------------------------------------------------------------------------| -----------------------------------------------------------------------------| -----------------------------------------------------------------|
| **pyforge-warden** | Consumes the F4 terminal gate's `ComplianceReport` schema via the `pyforge-atlas[gate]` extra | Warden's own schema-validation tests must pass against any F4 schema change | Run `pyforge-warden-test` after any `universal_sbom` gate change |
| **pyforge-doctor** | Reads legacy `conda_forge_server.py` for its four-axis compliance reads (R-005) | No atlas change should silently break Doctor's legacy read path until the cutover story lands | Manual smoke of Doctor's factory-sources gather after any MCP-surface change |
| **pyforge-steward** | Serves the atlas MCP face (`POST /stations/atlas/mcp`) and the query-plane HTTP/Arrow face | `query-plane-parity` already gates row-identical behavior between the two faces | Re-run `query-plane-parity` after any query-plane change        |
| **conda-forge-expert** | Receives A2A alerts on contract violations (FR-10) and policy breaches (FR-18) | A2A payload schema changes must stay backward-compatible for the CFE-side consumer | Contract-fixture round-trip in `tests/a2a_surface/`              |

**Regression test strategy:**

- Run the affected downstream station's own test suite (`pyforge-<station>-test`) whenever a shared
  contract (ComplianceReport schema, A2A payload schema, query-plane face) changes.
- No shared staging environment exists; cross-team coordination is via the tracked contract fixtures
  themselves, not a live integration environment.

---

## Appendix A: Code Examples & Tagging

**This station is Python/pytest, not TypeScript/Playwright.** The workflow's default
`@seontechnologies/playwright-utils` example does not apply to a Python codebase; the pattern below
reflects what this repo actually uses (`playwright.sync_api`, driven from pytest fixtures).

```python
# Dagster multiprocess-lock scenario -- plain pytest, no browser surface
# (see the WASM smoke example above for this repo's Playwright pattern instead).
import pytest

@pytest.mark.p0
def test_admission_lock_survives_multiprocess_drop(kedro_session, tmp_data_root):
    """P0-001 (net-new): a Dagster multiprocess-executor subprocess exit must not
    leave the per-dataset lock wedged for a later CLI/MCP trigger."""
    # Arrange: acquire the admission lock as the Dagster multiprocess plane would,
    # then simulate the subprocess exiting without releasing it.
    ...
    # Act: a second, independent trigger attempts to acquire the same lock.
    ...
    # Assert: the second trigger either serializes cleanly (bounded wait + retry)
    # or is rejected — never silently interleaved with the first.
    assert True  # replace with the real admission-lock assertion
```

**Run specific priority tiers:**

```bash
# Run only P0 tests
pixi run -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests -q -m p0

# Run the full gate suite (mirrors CI)
pixi run -e pyforge-atlas kedro-test
pixi run -e pyforge-atlas kedro-catalog-check
pixi run -e pyforge-atlas parity-diff
pixi run -e pyforge-atlas dagster-dryrun
pixi run -e pyforge-atlas bsl-metric-check
pixi run -e pyforge-atlas duckdb-singularity
pixi run -e local-recipes wasm-smoke
pixi run -e pyforge-atlas query-plane-parity
```

---

## Appendix B: Knowledge Base References

- **Risk Governance**: `risk-governance.md` - Risk scoring methodology
- **Test Priorities Matrix**: `test-priorities-matrix.md` - P0-P3 criteria
- **Test Levels Framework**: `test-levels-framework.md` - E2E vs API vs Unit selection
- **Test Quality**: `test-quality.md` - Definition of Done

---

**Generated by:** BMad TEA Agent
**Workflow:** `bmad-testarch-test-design`
**Version:** 5.0 (Step-File Architecture)
