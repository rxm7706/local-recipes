---
runScope: 'system-level'
runKey: 'system'
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-09-07'
---

# TEA Test Design — Progress Checkpoint (pyforge-atlas, system-level)

## Step 1: Detect Mode & Prerequisites

**Mode:** System-Level. Both PRD (`prds/prd-pyforge-atlas-2026-07-17/prd.md`) and ADR/architecture
(`architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md`) exist for pyforge-atlas,
and `epics.md` also exists. Per step-01's rule A ("Both PRD/ADR + Epic/Stories → Prefer System-Level
Mode first"), System-Level is selected. No `{implementation_artifacts}/sprint-status.yaml` check was
needed since rule A already resolved the mode.

**Prerequisites confirmed:** PRD has FRs (FR-1..22) + a Risks & Mitigations section (§11); ADR has
AD-1..23 (invariants), a Stack table, and a Deferred list. Requirements are testable — nearly every
FR states an explicit "Consequence:" clause.

**Run identity:** `run_scope = system-level`, `run_key = system`.

**Checkpoint check:** No prior checkpoint existed at this path — fresh run.

## Step 2: Load Context & Knowledge Base

**Config:** `tea_use_playwright_utils=true`, `tea_use_pactjs_utils=true`, `tea_pact_mcp=mcp`,
`tea_browser_automation=auto`, `test_stack_type=auto`.

**Stack detection:** `src/shared/packages/pyforge-atlas/pyproject.toml` present; no `playwright.config.*`
or JS frontend framework in the atlas package; two Python-Playwright (`playwright.sync_api`) driven
pytest files exist (`tests/dashboard/test_dashboard_e2e.py`, `tests/wasm/test_wasm_smoke.py`).
`{detected_stack} = backend` (Python/Kedro/Dagster/DuckDB pipeline + a Vizro dashboard tested via
pytest, not a JS/TS frontend). The playwright-utils mandate's package
(`@seontechnologies/playwright-utils`) is a JS/TS library and does not apply verbatim to this Python
codebase — noted as a gap rather than forced; QA doc Appendix A substitutes a Python/pytest +
`playwright.sync_api` example instead.

**Pact.js / Pact MCP:** No `pact/`, `tests/contract/`, `.pacttest.ts`, or `@pact-foundation/pact`
found; no consumer/provider contract-testing surface exists for this station (its "contracts" are
Kedro node I/O and pandera schemas, not HTTP consumer/provider pacts). Contract testing and Pact
loading are marked not relevant for this run.

**Documents loaded:** `prd.md`, `ARCHITECTURE-SPINE.md`, `epics.md` (headers/scope only — story-level
detail intentionally not re-derived; the epic list and FR/AD material carry the testable surface),
`test-architecture.md` (baseline, for context only, not duplicated), `pixi.toml` (verify-gate task
descriptions: `kedro-test`, `kedro-catalog-check`, `parity-diff`, `dagster-dryrun`, `bsl-metric-check`,
`duckdb-singularity`, `wasm-smoke`, `query-plane-parity`).

**Knowledge fragments loaded:** `adr-quality-readiness-checklist.md`, `nfr-criteria.md`,
`test-levels-framework.md`, `risk-governance.md`, `test-quality.md`, `probability-impact.md`,
`test-priorities-matrix.md`.

## Step 3: Testability & Risk Assessment

Testability review and a 9-item risk register (R-001..R-010, no R-004) were produced — see
`test-design-architecture.md` for the full matrices. Summary: 3 high-priority risks (score ≥6), all
concentrated in the not-yet-executed legacy-retirement path (B4 parity, MCP re-backing ownership,
AD-23 admission-lock release asymmetry); 4 medium; 2 low.

## Step 4: Coverage Plan & Execution Strategy

Coverage scenarios organized P0-P3 by capability/architecture-invariant (FR-/AD-ID), not by story ID
— see `test-design-qa.md` § Test Coverage Plan. Execution strategy: PR-time offline `--frozen` pytest
gates vs. human-scheduled attended wave-boundary events (this system has no nightly/weekly k6 or
chaos tier — noted as a deviation from the template's default assumption).

## Step 5: Generate Outputs & Validate

Both documents written and cross-checked for consistent risk IDs, priority levels, and dates.
Handoff document written to `test-design/pyforge-atlas-handoff.md`. Checklist in `checklist.md`
applied; System-Level Mode two-document validation section followed.
