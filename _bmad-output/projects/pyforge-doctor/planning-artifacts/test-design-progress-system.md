---
runScope: 'system-level'
runKey: 'system'
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted:
  - step-01-detect-mode
  - step-02-load-context
  - step-03-risk-and-testability
  - step-04-coverage-plan
  - step-05-generate-output
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-09-07'
workflowType: 'testarch-test-design'
inputDocuments:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/prds/prd-pyforge-doctor-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml
  - src/shared/packages/pyforge-doctor/pyproject.toml
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ (directory listing)
  - src/shared/packages/pyforge-doctor/tests/{unit,meta}/ (directory listing, 61 files)
  - .claude/skills/bmad-testarch-test-design/resources/knowledge/{risk-governance,probability-impact,nfr-criteria,test-levels-framework,adr-quality-readiness-checklist,test-priorities-matrix,test-quality}.md
---

# Test Design Progress — pyforge-doctor (system-level)

## Step 1: Detect Mode & Prerequisites

**Mode:** System-Level (Phase 3). Decision rule applied — workflow.yaml step-01,
§1 Mode Detection, priority (A) User Intent: "Both PRD/ADR + Epic/Stories → Prefer
System-Level Mode first." pyforge-doctor has all three: a completed PRD
(`prds/prd-pyforge-doctor-2026-07-25/prd.md`, FR-1..16, status `final`), a
completed architecture spine (`architecture/architecture-pyforge-doctor-2026-07-25/
ARCHITECTURE-SPINE.md`, AD-1..AD-13, status `final`), and `epics.md` (20 epics, 113
stories). File-based detection (priority B) was not reached — priority A resolved
first. Confirmed: `{implementation_artifacts}/sprint-status.yaml` does not exist for
this project either way (only the tracked `planning-artifacts/sprint-status-ledger.yaml`
twin exists), which would itself have pointed at Epic-Level had priority A been
ambiguous — it was not.

**Prerequisite check (System-Level):** PRD ✓, architecture/ADR ✓, tech-spec ✓ (the
spine doubles as both). All present — no HALT.

**Run identity:** `run_scope=system-level`, `run_key=system`.

**Existing checkpoint:** none found at this path before this run — fresh run.

## Step 2: Load Context & Knowledge Base

**Config (workaround, per task instructions — `_bmad/tea/config.yaml` does not exist
in this repo; resolved from `_bmad/custom/config.toml` `[modules.tea]` with
`{output_folder}` substituted as `_bmad-output/projects/pyforge-doctor` for this
run, and `[core]`):** `test_artifacts=_bmad-output/projects/pyforge-doctor/planning-artifacts`,
`tea_use_playwright_utils=true`, `tea_use_pactjs_utils=true`, `tea_pact_mcp=mcp`,
`tea_browser_automation=auto`, `test_stack_type=auto`, `ci_platform=auto`,
`risk_threshold=p1`, `user_name=rxm7706` (git `user.name`; no `_bmad/config.user.toml`
exists in this worktree — the installer-generated user layer is gitignored and absent
— so this is the closest available honest resolution, mirroring how the repo's other
BMAD skills fall back), `communication_language=English`, `document_output_language=English`.

**Stack detection:** `test_stack_type=auto` → scanned `pyforge-doctor`'s own package.
No `playwright.config.*`/`cypress.config.*`/frontend framework, no mobile indicators.
Backend indicators present (`pyproject.toml`, Python, `requires-python=">=3.14"`).
**Detected stack: `backend`** — a non-interactive CLI (console script `doctor`),
confirmed by the PRD's own §UX Design Requirements ("N/A — non-interactive CLI").
This overrides the templates' web/Playwright-flavored examples throughout both
outputs below with pytest/AST-meta-test equivalents, matching what the package
actually ships (61 files under `tests/{unit,meta}/`, zero `tests/e2e`).

**Playwright Utils / Pact.js / Pact MCP:** flags are on repo-wide, but none apply —
Doctor has no browser surface (API-only profile's own gate — no `page.goto`/
`page.locator` exist anywhere in this package) and no consumer/provider contract
surface (no `pact/`, no `@pact-foundation/pact`, no `PACT_BROKER_*`). Noted and
skipped per each fragment's own relevance gate, not silently ignored.

**Knowledge fragments loaded (System-Level, core tier):**
`adr-quality-readiness-checklist.md`, `nfr-criteria.md`, `test-levels-framework.md`,
`risk-governance.md`, `test-quality.md`, `probability-impact.md`,
`test-priorities-matrix.md`.

**Project artifacts loaded:** PRD (§4 Features/FRs, §5 Non-Goals, §6 MVP Scope, §8
Open Questions, both Currency reconciliations), Architecture Spine (Design Paradigm,
AD-1..AD-13, Consistency Conventions, Structural Seed, Capability→Architecture Map,
Deferred, both Currency reconciliations — including the "Carried debts" list), and
`epics.md` (Requirements Inventory, FR Coverage Map, Epic 1 detail, Epics 7–20
headers/story Given-When-Then, Canopy + Operating-model obligations, Currency
validation notes). Cross-checked against the as-built package:
`src/shared/packages/pyforge-doctor/` (pyproject.toml, `sources/` module listing —
15 modules incl. `bmad_method.py`; 61 test files across `tests/unit/` and
`tests/meta/`) and `sprint-status-ledger.yaml` (113 stories; Epics 1–19 done,
**Epic 20 — Stories 20.1–20.3/20.5 `backlog`, 20.4 `blocked`** — the one
undelivered surface).

## Step 3 & 4: see generated outputs

Risk assessment, testability review, NFR planning, and coverage/execution plan are
recorded directly in `test-design-architecture.md` and `test-design-qa.md` (this
workflow's step files direct their content into the final templates rather than a
separate progress narrative once System-Level mode's two-document split is active).

## Step 5: Generate Outputs & Validate

**Execution mode:** `tea_execution_mode` not set in the merged config → `auto`.
Capability probe (`tea_capability_probe=true`) found no subagent/agent-team launch
capability available inside this run's execution context → resolved to
**`sequential`**. Both documents were authored sequentially, then cross-checked for
consistency (same risk IDs, same story citations) — the parallel-worker path this
step file offers for `agent-team`/`subagent` mode was not applicable.

**Outputs written:**
- `test-design-architecture.md` — Architecture/Dev audience.
- `test-design-qa.md` — QA audience.
- `test-design/pyforge-doctor-handoff.md` — BMAD handoff (`{project_name}` resolved
  to the station slug `pyforge-doctor`, not the repo-wide `local-recipes`, since this
  run is scoped to one station's planning tree, not the whole multi-project repo).

**Validation:** checked against `checklist.md` (this workflow's own checklist) —
see the Validation Notes captured in `test-design-qa.md`'s closing appendix. No CLI
browser sessions were opened (backend stack; N/A). No temp artifacts were written
outside `{test_artifacts}/`.

**Completion report:** System-Level mode. 9 risks identified (1 HIGH score-6, 6
MEDIUM score-4, 2 LOW score-2 — none at CRITICAL/score-9). Coverage plan scoped to
Epic 20 (the fleet's only backlog surface, 5 stories) plus 3 named carried-debt
regression items — not a re-litigation of Epics 1–19's 108 already-shipped,
already-tested stories. Key open assumption carried forward: the DoctorReport
`schema_version` bump policy (PRD §8 Q4) stays unresolved and is now load-bearing
for Epic 20 (R-9).
