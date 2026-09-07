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
workflowType: 'testarch-test-design'
inputDocuments:
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/prds/prd-pyforge-mason-2026-07-25/prd.md"
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md"
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/epics.md"
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/sprint-status-ledger.yaml"
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md"
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/test-architecture.md"
  - "src/shared/packages/pyforge-mason/pyproject.toml"
  - "src/shared/packages/pyforge-mason/tests/**"
  - "pixi.toml (pyforge-mason-test / pyforge-mason-test-slow tasks)"
  - ".claude/skills/bmad-testarch-test-design/resources/knowledge/risk-governance.md"
  - ".claude/skills/bmad-testarch-test-design/resources/knowledge/probability-impact.md"
  - ".claude/skills/bmad-testarch-test-design/resources/knowledge/nfr-criteria.md"
  - ".claude/skills/bmad-testarch-test-design/resources/knowledge/test-levels-framework.md"
  - ".claude/skills/bmad-testarch-test-design/resources/knowledge/test-priorities-matrix.md"
  - ".claude/skills/bmad-testarch-test-design/resources/knowledge/adr-quality-readiness-checklist.md"
---

# Step 1: Detect Mode & Prerequisites

**Mode:** System-Level. pyforge-mason has BOTH a PRD (`prd.md`, 50 FRs / 16 NFRs / 13 D-records) and
an architecture/ADR document (`ARCHITECTURE-SPINE.md`, 18 ADs) **and** a fully decomposed
epic/story set (`epics.md`, 14 epics / 61 stories). Step-01's mode-detection rule A explicitly
resolves this combination ("Both PRD/ADR + Epic/Stories → Prefer System-Level Mode first").
Rule B (file-based fallback) independently agrees: no `sprint-status.yaml` exists under
`implementation-artifacts/` for this station (that directory does not exist in this worktree at
all — pyforge-mason's tracked twin lives at `planning-artifacts/sprint-status-ledger.yaml`, a
different filename), so the epic-level trigger condition is not met either.

**Prerequisite check:** both System-Level requirements are present and read (PRD +
ARCHITECTURE-SPINE.md). Proceeding.

**Run identity:** `run_scope = system-level`, `run_key = system`.

**Existing checkpoint check:** no `test-design-progress-system.md` existed before this run. Fresh run.

# Step 2: Load Context & Knowledge Base

**Config:** `test_stack_type` resolved via scan, not left at literal `"auto"` — pyforge-mason is a
pure Python CLI (argparse, `pyproject.toml`, no `playwright.config.*`, no `package.json`, no
mobile indicators). `detected_stack = backend`. No `page.goto`/`page.locator` anywhere in its test
tree → API-only / no-browser profile.

**Playwright Utils (`tea_use_playwright_utils=true`):** relevance gate not met — pyforge-mason
ships no HTTP service and no browser-driven surface of its own; the one HTMX portal endpoint
(`/stations/mason/`, Story 11.2) is a `django-mason` app concern with its own test surface, out of
scope here (see Not in Scope). Playwright Utils fragments were not loaded.

**Pact.js Utils / Pact MCP (`tea_use_pactjs_utils=true`, `tea_pact_mcp="mcp"`):** relevance gate
not met — Mason's one integration boundary (`cfe.py`) is a subprocess/argv contract governed by
AD-4/AD-16's fixture-CFE-root discipline, not a broker-tracked HTTP/gRPC consumer contract. No
Pact artifacts, no `pact/` directory, no `PACT_BROKER_*` env vars exist. Per `pact-mcp.md`'s own
guidance this is reported once and the run continues without invoking the MCP tool or blocking.

**Knowledge fragments loaded (System-Level required set):** `adr-quality-readiness-checklist.md`,
`nfr-criteria.md`, `test-levels-framework.md`, `risk-governance.md`, `test-quality.md`,
`probability-impact.md`, `test-priorities-matrix.md`.

**Project artifacts loaded:** PRD §§4, 8–14 (Features, NFRs, Constraints, Decision Record, Risks,
Open Questions, Assumptions); ARCHITECTURE-SPINE.md Invariants & Rules (AD-1 through AD-16,
AD-25, AD-26); `epics.md` (Overview, Requirements Inventory, FR Coverage Map, Epic List, full
Epic 6/12/13/14 bodies, Canopy/Operating-model obligations, Validation/Reconciliation notes);
`sprint-status-ledger.yaml` (61 stories, all `done` except `14-1` = `backlog`);
`deferred-work-ledger.md` (60+ open findings scanned for risk-relevant, currently-true gaps);
the machine-generated `test-architecture.md` baseline (39 test files, story-coverage matrix) for
cross-reference only, not reproduced here; `pyforge-mason/tests/` tree (50 test files across
`unit/`, `integration/`, `meta/`, plus `fixtures/fake_cfe_root/`); `pyproject.toml`'s `slow`
marker convention; `pixi.toml`'s `pyforge-mason-test` / `pyforge-mason-test-slow` task definitions.

**Confirmed loaded; nothing missing for a System-Level run.**

# Step 3 & 4: Risk/Testability Assessment and Coverage Plan

Executed against the loaded artifacts; full output is the two generated documents themselves
(risk register, ASRs, testability concerns, NFR planning, coverage matrix, execution strategy,
resource estimates, quality gates all live there rather than being duplicated in this checkpoint).

# Step 5: Generate Outputs & Validate

**Execution mode:** resolved to **sequential**, not `agent-team`/`subagent`, despite
`tea_execution_mode="auto"`. Rationale: this run has no independent runtime capability probe for
launching cooperating peer workers that share the same grounding context gathered in Steps 2–4;
generating the two documents as two separate agents risked losing that shared grounding (a known
failure mode: a forked/subagent worker can drift from or fabricate content the parent already
verified). Both documents were authored directly, from the same evidence base, in one pass, then
cross-checked for consistency (shared risk IDs, shared NFR table, shared story counts).

**Outputs written:**
- `test-design-architecture.md` (system-level, Architecture/Dev audience)
- `test-design-qa.md` (system-level, QA audience)
- `test-design/pyforge-mason-handoff.md` (BMAD handoff — epic/story decomposition already exists
  for this station, so this handoff is a retrospective cross-check of that decomposition against
  the new risk register rather than a forward brief for a not-yet-decomposed effort)

**Validation:** checked against `checklist.md` in this workflow folder (see below); no CLI/browser
sessions were opened (no browser automation used, per Step 2); no temp artifacts were created
outside `{test_artifacts}`.
