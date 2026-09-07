---
runScope: 'system-level'
runKey: 'system'
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted:
  - 'step-01-detect-mode'
  - 'step-02-load-context'
  - 'step-03-risk-and-testability'
  - 'step-04-coverage-plan'
  - 'step-05-generate-output'
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-09-07'
---

# Test Design Progress — pyforge-warden (system-level)

## Step 1: Detect Mode & Prerequisites

**Mode detected:** System-Level (Priority-A file-based rule: both a PRD + architecture document AND epics/stories exist for pyforge-warden — `planning-artifacts/prds/prd-pyforge-warden-2026-07-14/prd.md`, `planning-artifacts/architecture/architecture-pyforge-warden-2026-07-14/architecture.md`, and `planning-artifacts/epics.md` all present — step-01's rule "Both PRD/ADR + Epic/Stories → Prefer System-Level Mode first" applies). No autonomous run has an interactive user to ask, so this priority-order rule resolved the mode deterministically. Rule B (file-based fallback: `sprint-status.yaml` presence → epic-level) was not needed since Rule A already resolved unambiguously, and in any case no `implementation-artifacts/sprint-status.yaml` exists for this project in this worktree.

**Prerequisites confirmed:** PRD (FR1-FR40 + NFRs), architecture.md (complete, `status: complete`), epics.md (11 epics / 43 stories).

**Run identity:** `run_scope = system-level`, `run_key = system`.

**Existing checkpoint check:** none existed at this path prior to this run — fresh run.

## Step 2: Load Context & Knowledge Base

**Stack detection:** `backend` (Python stdlib CLI; `pyproject.toml`/`pixi.toml` present at `src/shared/packages/pyforge-warden/`; no `playwright.config.*`/`cypress.config.*`/browser package.json signals in the package under test). No mobile indicators. Judgment call: this repo overall carries Playwright infra for other purposes, but pyforge-warden itself is a non-interactive CLI with no browser/API-over-HTTP surface in its core gate path — the QA document adapts the Playwright-utils-mandated examples to pytest (this project's actual test framework, confirmed in `architecture.md` § Starter Template Evaluation: "Test: pytest").

**Artifacts loaded:** PRD (full), architecture.md (full), epics.md (headers + story list, 43 stories / 11 epics), deferred-work-ledger.md (DW-5-2-5, DW-5-2-6, DW-5-2-7 entries), sprint-status-ledger.yaml (story/epic status), existing `test-architecture.md` baseline (for cross-reference only, not duplicated), and a listing of the real test suite (64 files under `tests/{unit,conformance,meta}/`) and `src/pyforge/warden/` module tree.

**Config flags read:** `tea_use_playwright_utils=true`, `tea_use_pactjs_utils=true`, `tea_pact_mcp=mcp`, `tea_browser_automation=auto`, `test_stack_type=auto` (resolved to `backend`), `risk_threshold=p1`. Pact/contract-testing knowledge was evaluated for relevance (per step-02 §3) and judged **not relevant** — pyforge-warden has no consumer/provider HTTP contract surface in its CLI core; not loaded.

**Knowledge fragments loaded (System-Level required set):** `adr-quality-readiness-checklist.md`, `nfr-criteria.md`, `test-levels-framework.md`, `risk-governance.md`, `test-quality.md`.

## Step 3: Testability & Risk Assessment

Full testability review and 14-item risk register (5 high / 5 medium / 4 low) recorded in `test-design-architecture.md` §§ Risk Assessment, Testability Concerns, NFR Testability Requirements. Summary: the C0 never-false-green invariant is well-architected (the false-green triad + adversarial fixture corpus) but has one live gap — the corpus-oracle and differential-oracle suites that would *detect* an extractor regression are not wired into any CI workflow or scheduler (DW-5-2-5), and a calendar-scheduled baseline-expiry event (DW-5-2-7) risks being mistaken for a regression by an unattended process.

## Step 4: Coverage Plan & Execution Strategy

24-scenario P0-P3 coverage plan recorded in `test-design-qa.md` § Test Coverage Plan, cross-referencing the 64 real test files already in the repository rather than proposing net-new tests where coverage already exists. Execution strategy adapted to this project's real tooling (pytest + `-m slow` marker), not the template's default Playwright/k6 tiers. Resource estimates reframed as gap-closure effort (~30-70 hours) since this is a retrospective design over an already-shipped system, not a pre-implementation estimate.

## Step 5: Generate Outputs & Validate

**Execution mode:** resolved to **sequential** — no subagent/agent-team runtime was available to probe in this execution context, so per the resolution rule (`auto` → fall back to `sequential` when neither capability is available) both documents were authored directly, then reconciled for cross-document consistency (shared risk IDs, shared priority levels, matching dates/authors).

**Outputs written:**
- `test-design-architecture.md` (system-level, architecture audience)
- `test-design-qa.md` (system-level, QA audience)
- `test-design/pyforge-warden-handoff.md` (BMAD handoff, system-level mode only)

Validated against `checklist.md`'s System-Level Mode: Two-Document Validation and BMAD Handoff Validation sections. No CLI/browser sessions were opened (backend stack, no browser exploration applicable) so there is nothing to clean up.
