---
runScope: 'system-level'
runKey: 'system'
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-09-07'
workflowType: 'testarch-test-design'
inputDocuments:
  - '_bmad-output/projects/pyforge-herald/planning-artifacts/prds/prd-pyforge-herald-2026-08-01/prd.md'
  - '_bmad-output/projects/pyforge-herald/planning-artifacts/architecture/architecture-pyforge-herald-2026-08-01/ARCHITECTURE-SPINE.md'
  - '_bmad-output/projects/pyforge-herald/planning-artifacts/epics.md'
  - '_bmad-output/projects/pyforge-herald/planning-artifacts/sprint-status-ledger.yaml'
  - '_bmad-output/projects/pyforge-herald/planning-artifacts/test-architecture.md'
  - 'src/shared/packages/pyforge-herald/src/pyforge/herald/*.py'
  - 'src/shared/packages/pyforge-herald/tests/*.py'
  - 'src/shared/packages/pyforge-herald/web/package.json'
  - 'src/shared/packages/pyforge-herald/pyproject.toml'
  - '.claude/skills/bmad-testarch-test-design/resources/knowledge/{adr-quality-readiness-checklist,nfr-criteria,test-levels-framework,risk-governance,test-quality}.md'
---

# Test Design Progress — pyforge-herald (system-level)

## Step 1: Detect Mode & Prerequisites

**Mode decision:** System-Level.

- Config resolution: TEA's own `{project-root}/_bmad/tea/config.yaml` does not exist in this
  repo (a disclosed, known gap — steward 46.3 provisioned the skill repo-wide without a
  materialized runtime config). Substituted the unresolved values from
  `_bmad/custom/config.toml`'s `[modules.tea]` table, with `test_artifacts` resolved as
  `_bmad-output/projects/pyforge-herald/planning-artifacts` for this run (per the
  `{output_folder}/planning-artifacts` template, `output_folder` taken from
  `_bmad-output/projects/pyforge-herald/.bmad-config.toml`). `communication_language`
  resolved to `English` (`_bmad/custom/config.toml [core]`, matching
  `_bmad/config.toml [core].document_output_language`). No `user_name` key resolves anywhere
  in `_bmad/config*.toml` / `_bmad/custom/config*.toml` for this repo (only BMAD persona
  names — Mary, John, Sally, Winston, Amelia — appear under `[agents.*]`); the git/author
  identity `rxm7706` was used for the document `Author` field instead.
- **Rule A (User Intent / artifact-based inference)** — pyforge-herald has **both** a
  finalized PRD (`prds/prd-pyforge-herald-2026-08-01/prd.md`, status `final`, two PRD bodies:
  Moment 1 Pitch + the Moments 2–4 satellite) **and** a finalized Architecture
  (`architecture-pyforge-herald-2026-08-01/ARCHITECTURE-SPINE.md`, AD-1..AD-20 plus the
  2026-08-26 Canopy/as-built reconciliation) **and** a complete epic/story breakdown
  (`epics.md`, 18 epics / 50 stories per its own frontmatter, all `done` in
  `sprint-status-ledger.yaml` except Epic 18's 3 stories, which are cross-station `blocked`).
  Per step-01's rule A: "Both PRD/ADR + Epic/Stories → Prefer System-Level Mode first."
- **Rule B (file-based fallback)** — confirms the same answer independently:
  `{implementation_artifacts}/sprint-status.yaml` does not exist for this station in this
  worktree (`_bmad-output/projects/pyforge-herald/implementation-artifacts/` doesn't exist at
  all; the tracked ledger lives at `planning-artifacts/sprint-status-ledger.yaml`, a
  differently-named file per this repo's own generated-ledger convention) → **System-Level**.
- No ambiguity to resolve interactively; `execution_hints.autonomous: true` — proceeded
  without asking.

**Run identity:** `run_scope = system-level`, `run_key = system`.

**Prerequisite check:** PRD (FR + NFR) present; ADRs present (AD-1..AD-20 + Canopy
reconciliation addenda); architecture/tech-spec present (same document, "System Boundaries &
Data Flow" + "Invariants by Slice"); epics present for scope context. All satisfied — no halt.

**Checkpoint:** no prior checkpoint existed at this path; fresh run.

## Step 2: Load Context & Knowledge Base

**Config flags read:** `tea_use_playwright_utils=true`, `tea_use_pactjs_utils=true`,
`tea_pact_mcp="mcp"`, `tea_browser_automation="auto"`, `test_stack_type="auto"`,
`ci_platform="auto"`, `risk_threshold="p1"`.

**Stack detection:** `pyproject.toml` present (`src/shared/packages/pyforge-herald/`, Python
backend) **and** `package.json` present with `react`/`react-dom`
(`src/shared/packages/pyforge-herald/web/`, frontend) → **`fullstack`** per the detection
rule ("both frontend and backend present → fullstack").

**Deviation recorded (reasonable, disclosed):** `tea_use_playwright_utils`/`tea_use_pactjs_utils`
default to the `@seontechnologies/playwright-utils` / Pact.js **TypeScript** npm packages —
neither exists in this Python-first station (`web/package.json` uses Vitest, not
Playwright/Cypress, for its own component tests; there is no `pact/`, `.pacttest.ts`, or
`@pact-foundation/pact` anywhere in the tree). Herald *does* use `playwright-python` for a
real, already-pinned headless-Chromium deck-QA render gate (`deck_qa.py`, Story 14.2) — so
Playwright itself is relevant, just not the JS-fixture flavor the config defaults assume.
Per this workflow's own mandate framing ("every code example is a pattern a developer will
copy"), copy-pasting TypeScript `apiRequest`/Pact fixtures into a pytest-only codebase would
be actively misleading. QA-doc code examples instead follow the project's own real,
already-established pytest idioms (`monkeypatch`-based stubs, `tmp_path`-isolated
`.herald/` fixtures, the `live`/`live_webhook` opt-in marker pair in
`pyproject.toml [tool.pytest.ini_options]`), and the contract-testing gap this station
actually has (webhook payload-shape drift against the real GitHub Actions producer, no Pact
broker or schema-drift CI check) is captured as risk R-004 rather than solved by installing
new JS tooling into a Python package.

**Knowledge fragments loaded (System-Level required set):** `adr-quality-readiness-checklist.md`,
`nfr-criteria.md`, `test-levels-framework.md`, `risk-governance.md`, `test-quality.md`,
`probability-impact.md`, `test-priorities-matrix.md`, `contract-testing.md` (pactjs-utils
disabled-in-practice per the deviation above; the conceptual fragment applies instead of the
JS-specific ones), `playwright-cli.md` (browser-automation `auto`).

**Artifacts loaded:** PRD (both bodies + 2026-08-26 reconciliation), Architecture spine
(AD-1..AD-20 + satellite + reconciliation), `epics.md` (epic list + all `### Story` headings),
`sprint-status-ledger.yaml` (50-story done/blocked status), the existing generated
`test-architecture.md` baseline (context only, not authoritative for this workflow's shape),
the full `src/pyforge/herald/*.py` module list (21 modules) and `tests/*.py` inventory (45
files, cross-checked docstrings for `test_performance_epic11.py`,
`test_reliability_epic11.py`, `test_integration_epic11.py`, `test_webhook_live_smoke.py`,
`webhook.py`'s `_problem_unknown_fields`, `scheduler.py`'s `run_evidence_revalidation`),
`web/package.json` and `web/src/**/*.test.jsx` (Vitest component tests), `pyproject.toml`
`[tool.pytest.ini_options]` markers.

## Step 3 & Step 4

See the generated documents (`test-design-architecture.md` §§ Risk Assessment, NFR
Testability Requirements, Testability Concerns; `test-design-qa.md` §§ Risk Assessment, NFR
Test Coverage Plan, Test Coverage Plan P0–P3, Execution Strategy, QA Effort Estimate) for the
full step-3/step-4 output — inlined there rather than duplicated here per the anti-bloat
checklist rule.

## Step 5: Generate Outputs & Validate

**Execution mode:** no explicit user override in this run; `tea_execution_mode` config value
not set in `[modules.tea]` (defaults to `auto`); no subagent/agent-team launch capability
probed in this context → resolved to **sequential**. Both system-level documents authored
sequentially, then reconciled for cross-document consistency (shared risk IDs, shared
priority scale, matching dates/author).

**Outputs written:**

- `test-design-architecture.md`
- `test-design-qa.md`
- `test-design/pyforge-herald-handoff.md`

Validated against `checklist.md` (system-level two-document + handoff sections). No CLI
browser sessions were opened (browser exploration step is for live web-app crawling; a
completed, already-tested station's test design was produced from code + docs, not live
URL exploration).
