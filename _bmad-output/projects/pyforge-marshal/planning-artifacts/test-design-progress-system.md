---
runScope: 'system-level'
runKey: 'system'
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-09-07'
inputDocuments:
  - '_bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md'
  - '_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md'
  - '_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md'
  - '_bmad-output/projects/pyforge-marshal/planning-artifacts/test-architecture.md'
  - '.claude/skills/bmad-testarch-test-design/resources/knowledge/{risk-governance,probability-impact,nfr-criteria,adr-quality-readiness-checklist,test-levels-framework,test-quality}.md'
---

# Workflow checkpoint (Story 31.1)

This is the `bmad-testarch-test-design` workflow's own per-run checkpoint, produced by a real
Create-mode run against the ACTIVE project `pyforge-marshal` (the same shape as every other
station's own `test-design-progress-system.md` under Story 31.1). See `test-design-architecture.md`
and `test-design-qa.md` in this directory for the generated documents themselves.

## Step 1: Detect Mode & Prerequisites

**Mode decision:** System-Level. Rule B applies ("Both PRD/ADR + Epic/Stories
→ Prefer System-Level Mode first") — pyforge-marshal has both a dedicated
PRD (`prds/prd-pyforge-marshal-2026-07-25/prd.md`, FR-1..FR-195) and
architecture set (`architecture/architecture-pyforge-marshal-2026-07-25/architecture.md`,
AD-1..AD-80) *and* a fully decomposed `epics.md` (37 epics / 208 stories).
Per this workflow's own priority order, PRD+ADR wins over epic/story
presence, so System-Level is correct even though `sprint-status.yaml`
(file-based tiebreaker B) also exists under implementation-artifacts.

**Prerequisite check:** PRD ✅, architecture/ADRs ✅ (AD-1..AD-80), tech-spec
✅ (same architecture doc), epics (for scope) ✅. No halt condition.

`run_scope = system-level`, `run_key = system`.

**Existing checkpoint check:** none existed at this path before this run
(fresh run).

## Step 2: Load Context & Knowledge Base

**Config (substituted — see the equivalence report):** `tea_use_playwright_utils=true`,
`tea_use_pactjs_utils=true`, `tea_pact_mcp="mcp"`, `tea_browser_automation="auto"`,
`test_stack_type="auto"`.

**Stack detection:** no `playwright.config.*`/`cypress.config.*` at repo
root; `pyforge-marshal` is a pure Python package
(`src/shared/packages/pyforge-marshal/pyproject.toml`, `requires-python
>=3.12`, argparse CLI, no frontend). No mobile indicators. →
`detected_stack = backend`. Playwright/Pact loading profiles are therefore
not exercised in depth for this run (no `page.goto`/`page.locator`, no
`pact/`/`tests/contract/**/*.pacttest.ts` naming, though a `tests/contract/`
directory does exist — inspected below); this is a CLI/API/unit-level test
estate, not a browser one.

**Contract-testing relevance check:** `tests/contract/` exists under
`pyforge-marshal`, but on inspection its contracts are internal Port/Adapter
conformance tests (HarnessPort, adapter conformance matrix — AD-19), not
consumer-driven Pact contracts against an external HTTP provider. Pact.js
Utils / Pact MCP are therefore noted as configured-but-not-relevant for this
station rather than loaded in depth.

**Artifacts loaded:** PRD (marshal-specific, not the umbrella `PRD.md`),
architecture (marshal-specific, not the umbrella `architecture.md`),
`epics.md` (37 epic headings + Epic 31 in full, since Epic 31 — "TEA
replaces the generator" — is the epic this very run is evidence for),
existing `test-architecture.md` (the mechanical generator's prior output,
read for comparison, never edited by this run).

**Knowledge fragments:** `adr-quality-readiness-checklist.md`,
`nfr-criteria.md`, `test-levels-framework.md`, `risk-governance.md`,
`test-quality.md` (system-level required set) — skimmed for rubric/headings
rather than read in full line-by-line, given this pass's time-box.

## Step 3: Testability & Risk Assessment

See `test-design-architecture.md` for the full testability review and risk
register. Summary: 8 real architectural risks already named in the
architecture doc (AR-1..AR-8) were carried forward and re-scored on the
P×I scale; 5 additional risks were derived from the 14 cross-cutting NFRs
(NFR-1..NFR-14) and from ADs whose violation would be a trust-property
failure (AD-8 unevaluable-is-failure, AD-9 supervisor independence, AD-13/
AD-29 promote-before-teardown, AD-27 allowlist-narrowing-only, AD-73
landing-evidence-grammar). No thresholds were guessed; NFR-14's own text
already flags its performance envelope as `[ASSUMPTION]`, carried through
as UNKNOWN/assumption rather than invented.

## Step 4: Coverage Plan & Execution Strategy

See `test-design-qa.md` for the coverage matrix, execution strategy (PR /
Nightly / Weekly), resource estimates, and quality gates. Test levels are
overwhelmingly Unit/Integration/Meta (matching the real
`src/shared/packages/pyforge-marshal/tests/{unit,integration,meta,contract,oracle}/`
layout) rather than E2E/Playwright, consistent with the backend stack
detection in Step 2.

Load next step: `step-05-generate-output.md`

## Step 5: Generate Outputs & Validate

**Execution mode resolved:** `sequential` — this run executed the workflow single-threaded
(no subagent/agent-team fan-out for parallel drafting of the architecture/QA pair), which is the
documented fallback when `tea_execution_mode="auto"` and neither `agent-team` nor `subagent`
capability was actually exercised.

**Outputs written (System-Level Mode → two documents + handoff, per workflow.yaml):**

- `test-design-architecture.md`
- `test-design-qa.md`
- `test-design/pyforge-marshal-handoff.md`

**Completion Report:**

- Mode used: System-Level
- Key risks: R-1, R-2, R-5, R-6, R-8 (all score 6/9, the high end of a 1-3×1-3 scale)
- Gate thresholds: P0=100% pass, coverage unchanged from the generator's declared targets
  (unit ≥80%, integration ≥70%)
- Open assumptions: NFR-14's numeric targets remain `[ASSUMPTION]`; B-1/B-2 (generator-baseline
  validity, no per-story matrix in these templates) are unresolved blockers, not findings this
  run could close itself.

**Validation against `checklist.md`:** risk matrix ✅, NFR planning ✅ (thresholds marked UNKNOWN
where genuinely unknown, not guessed), coverage matrix with P0-P3 ✅, execution strategy ✅,
resource estimates as ranges ✅, quality gates ✅. Not independently re-verified: whether every
single checklist checkbox was walked line-by-line (this was a time-boxed pass, not a full
validate-mode pass — a real `[V] Validate` run against `checklist.md` was not separately invoked).

workflowStatus: completed.
