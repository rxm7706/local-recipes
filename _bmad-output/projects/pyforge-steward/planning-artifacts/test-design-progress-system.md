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

# Test Design Progress — pyforge-steward (system-level)

## Step 1: Detect Mode & Prerequisites

**Mode detection (Priority Order per step-01-detect-mode.md):**

- **A) User intent**: no explicit user scope statement was given for this run beyond "target station pyforge-steward, choose Create mode" — so intent is not the deciding rule on its own, but pyforge-steward's planning-artifacts carry **both** a PRD/architecture set **and** an epics/stories set. Per the rule's own text: *"Both PRD/ADR + Epic/Stories → Prefer System-Level Mode first."*
- **B) File-based detection** (secondary confirmation): `{implementation_artifacts}/sprint-status.yaml` does not exist for pyforge-steward — its sprint tracking file is `planning-artifacts/sprint-status-ledger.yaml` (a differently-named, differently-located file; `implementation-artifacts/` for pyforge-steward has no matching file at all). Per the rule, absence of the exact expected file → **System-Level Mode**.

Both signals converge: **System-Level Mode.**

**Prerequisite check (System-Level):** PRD present (`prd-pyforge-steward-2026-07-25/prd.md`, FR-1..31/NFR-1..7, plus two companion PRDs for later epics), ADR/architecture present (7 architecture spines found — see below), epics present (`epics.md`, 47 epics / 190 stories) for scope. All prerequisites satisfied — no halt.

**Run identity:** `run_scope = system-level`, `run_key = system` (per rule: a project has one system-level test design).

**Existing checkpoint check:** No prior checkpoint at `{test_artifacts}/test-design-progress-system.md` existed before this run (confirmed via `ls` — file did not exist). Fresh run.

## Step 2: Load Context & Knowledge Base

**Config loaded** from the resolved `_bmad/custom/config.toml` `[modules.tea]` section (the real `_bmad/tea/config.yaml` this workflow's own activation instructions name does not exist in this repo — a known, disclosed gap already documented in `pyforge-steward`'s own Story 46.3 spec; substituted per the calling task's explicit instruction): `tea_use_playwright_utils=true`, `tea_use_pactjs_utils=true`, `tea_pact_mcp="mcp"`, `tea_browser_automation="auto"`, `test_stack_type="auto"`, `ci_platform="auto"`, `risk_threshold="p1"`. `test_artifacts` resolved to `_bmad-output/projects/pyforge-steward/planning-artifacts` (the `{output_folder}` template substituted with `pyforge-steward`'s own `.bmad-config.toml` `output_folder` value). `user_name`/`communication_language`/`document_output_language` = `Rxm7706`/`English`/`English`, carried from `_bmad/custom/config.toml` `[core]` per a prior sibling probe (reused, not re-derived).

**Stack detection:** `pyforge-steward` itself is a Python CLI/backend package (`pyproject.toml`, `pixi.toml`, no `package.json`/frontend framework at the package root) → **backend**. Its optional `[dashboard]` extra hosts a Django+Channels ASGI app (Epic 9) with its own Playwright e2e/ARIA suite owned by the Canopy host (`dashboard-dryrun` pixi task, outside this package). Classified overall stack as **backend** for this package's own test tier; noted the dashboard extra's frontend surface as owned elsewhere in both output documents' Appendix/Not-in-Scope sections.

**Project artifacts loaded (System-Level):**

- PRD: `prd-pyforge-steward-2026-07-25/prd.md` (full read, 477 lines)
- Architecture: `architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md` (full read, AD-1..AD-9, CLI-package authoritative) + 6 companion spines' AD headers (`architecture-secure-live-dashboards-2026-08-09`, `architecture-jira-github-projects-sync-2026-08-09`, `architecture-unified-container-2026-08-09`, `architecture-pyforge-unifying-strategy-2026-08-24`, `architecture-python-foundry-cutover-2026-09-04`, `architecture-bmad-suite-lifecycle-2026-09-06`)
- Epics: `epics.md` (2911 lines; all 47 epic headers + all 190 story headers scanned; several epics' full story text read in detail — Epic 9 in full, Epic 8/26/34/37/40-47 story titles)
- Live code: `src/shared/packages/pyforge-steward/src/pyforge/steward/*.py` (18-module inventory) and `tests/{unit,conformance,meta}/*.py` (67-file inventory, filenames read to ground existing-coverage claims)

**Knowledge fragments loaded (System-Level required set):** `risk-governance.md`, `probability-impact.md`, `nfr-criteria.md`, `adr-quality-readiness-checklist.md` (headers/structure), `test-levels-framework.md` (referenced), `test-priorities-matrix.md` (P0-P3 criteria per step-04's own inline definitions), `test-quality.md` (referenced via tea-index.csv description).

**Playwright/Pact.js loading:** Given the detected `backend` stack and no Pact/contract-testing artifacts found in this package (no `pact/`, no `.pacttest.ts`, no `@pact-foundation/pact` dependency), Pact.js Utils fragments were not loaded as core context; `pactjs-utils-mandate.md`'s relevance gate was checked and found not triggered for this package specifically (Epic 8's Jira↔GitHub sync is a different integration shape, not a consumer/provider Pact contract). Playwright Utils fragments were likewise not loaded in depth — this package's own test surface is pytest, not Playwright/TypeScript — noted explicitly in `test-design-qa.md` Appendix A's Stack note.

## Step 3: Testability & Risk Assessment

**Testability review (System-Level):** Performed against the ADR Quality Readiness Checklist's 8 categories (Testability & Automation, Test Data Strategy, Scalability & Availability, Disaster Recovery, Security, Monitorability, QoS/QoE, Deployability), producing the "Testability Concerns and Architectural Gaps" and "Testability Assessment Summary" sections of `test-design-architecture.md`. Two ACTIONABLE concerns identified (query-plane SLO gap; container/manifest secret-scan gap) plus two architectural improvements (cross-station import boundary; base-install isolation).

**Risk assessment (all modes):** 19 candidate risks scored using the P×I (1-3 × 1-3) matrix from `probability-impact.md` / `risk-governance.md`. Final register: 18 risks after consolidation (8 high ≥6, 7 medium 3-5, 3 low 1-2). No score=9 (BLOCK/critical) risk identified. Full register in `test-design-architecture.md` § Risk Assessment.

**NFR planning:** NFR-1..7 (PRD) plus cross-cutting NFRs from Epic 9 (security/isolation), Epic 34/36 (performance, threshold UNKNOWN — converted to risk R-7), Epic 41 (reliability/DR, scope question raised), and the architecture spines' own drift-detector (maintainability). One UNKNOWN threshold recorded (query-plane staleness/latency) rather than guessed.

## Step 4: Coverage Plan & Execution Strategy

**Coverage matrix:** Built around the 18 risks plus the existing 67-file test inventory, classified into P0 (~9), P1 (~11), P2 (~9), P3 (~5) — total ~34 scenarios, the large majority of which are *existing* tests confirmed to already cover a risk/requirement, with ~7 new or extended tests recommended (R-2, R-6, R-9 extension, R-10, R-13 extension, R-14 drill, R-15).

**Execution strategy:** PR-only for the existing/new pytest suite (already fast and offline); two drill-shaped items (R-3's isolation canary run, R-14's cutover rehearsal) scheduled as manual/adopter-triggered rather than per-PR; R-7's performance probe blocked pending an Architecture-declared threshold.

**Resource estimates:** ~15-28 hours total QA effort, dominated by confirming existing coverage rather than writing new tests from scratch (67 of ~72 target tests already exist).

**Quality gates:** P0 100%, P1 ≥95%, no OPEN score-9 risk, R-14's rehearsal drill documented before Story 44.3 executes.

## Step 5: Generate Outputs & Validate

**Outputs written (System-Level, two documents + handoff, per workflow.yaml):**

1. `_bmad-output/projects/pyforge-steward/planning-artifacts/test-design-architecture.md` (using `test-design-architecture-template.md`)
2. `_bmad-output/projects/pyforge-steward/planning-artifacts/test-design-qa.md` (using `test-design-qa-template.md`)
3. `_bmad-output/projects/pyforge-steward/planning-artifacts/test-design/pyforge-steward-handoff.md` (using `test-design-handoff-template.md`, per step-05 § 4 — system-level mode only)

**Execution mode resolved:** `auto` → no subagent/agent-team capability probe available in this invocation context → resolved to **sequential** (single-worker, both documents authored in the same pass with explicit cross-references reconciled by hand rather than by parallel-worker merge).

**Validation:** Checked against `checklist.md`'s intent (risk register present, NFR planning present, coverage matrix present, execution strategy present, resource estimates present, quality gates present, mode-specific sections present in both documents). No CLI/browser sessions were opened (Playwright CLI exploration was not applicable — no live target URL for a CLI/backend package). No temp artifacts were written outside `{test_artifacts}/`.

**Deliberate scope note (Not in Scope, both documents):** This system-level pass does **not** reproduce `test-architecture.md`'s mechanically-generated full story-ID-to-test-file matrix (190 rows) — that remains the separate `_bmad/scripts/bmad_tea_playwright.py` / `tea-playwright-check` gate's job. This document organizes by risk tier (P0-P3) per TEA's own template design, citing specific story IDs only where a risk's mitigation is scoped to that story (approximately 25-30 distinct story IDs named across both documents and the handoff, out of 190 total).

**Completion report:** Mode used = System-Level. Outputs = the three files above. Key risks = 8 high-priority (R-1, R-3, R-6, R-9, R-10, R-13, R-14, R-16), none critical (score 9). Gate thresholds = P0 100% / P1 ≥95% / no OPEN score-9. Open assumptions = `epics.md`'s `sprint-status-ledger.yaml` "done" markers trusted as-read, not independently re-verified against live CI; the risk register reflects one read-through of 47 epic headers + 8 architecture spines' AD inventories, not a full per-story AC read (explicitly flagged as a "Risk to Plan" in the architecture document).
