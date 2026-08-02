---
title: BMAD TEA + Playwright Testing Addendum (Reusable Pattern)
slug: tea-playwright-pattern
status: reference
created: 2026-08-02
audience: all-pyforge-projects
repeatable: true
---

# BMAD TEA + Playwright Testing Pattern (Fleet Standard)

This document defines a **reusable pattern** for applying BMAD TEA (Test Architecture Enterprise) + Playwright testing to any PyForge project. Use this to generate test architecture for pyforge-herald, pyforge-atlas, pyforge-warden, pyforge-marshal, etc.

---

## When to Apply This Pattern

✅ **Use this pattern for**:
- Any BMAD project with stories (output from `bmad-create-epics-and-stories`)
- Projects with CLI, web, API, or automation components
- Any project needing systematic test architecture before development

---

## How to Apply: 3-Step Process

### **Step 1: Dream → Spec**

Run `bmad-spec` to produce the spec (already done for Herald).

```bash
bmad-spec docs/dreams/pyforge-atlas-improvements.md --project pyforge-atlas
```

Output: `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-*.md`

### **Step 2: Spec → Stories**

Run `bmad-create-epics-and-stories` to produce epics + stories with BDD acceptance criteria.

```bash
bmad-create-epics-and-stories \
  --spec _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-*.md \
  --project pyforge-atlas
```

Output: `_bmad-output/projects/pyforge-atlas/planning-artifacts/epics-with-stories.md`

### **Step 3: Stories → Test Architecture**

Run the **`bmad-tea-playwright` workflow** (custom workflow you'll create) to generate test architecture with Playwright specs:

```bash
bmad-tea-playwright \
  --epics _bmad-output/projects/pyforge-atlas/planning-artifacts/epics-with-stories.md \
  --architecture _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/*.md \
  --project pyforge-atlas \
  --output-file test-architecture-tea.md
```

Output: `_bmad-output/projects/pyforge-atlas/planning-artifacts/test-architecture-tea.md`

---

## Workflow: `bmad-tea-playwright`

**Input**: Epics + Stories document (from Step 2)  
**Output**: Complete test architecture with Playwright implementation  
**Runtime**: ~5-10 minutes

### Workflow Steps

1. **Risk Assessment** (MOMENT 2)
   - Parse all stories
   - Extract high-risk items (webhooks, auth, data integrity, automation)
   - Generate risk heat map

2. **Test Matrix Generation** (MOMENT 3)
   - Per story: unit tests, integration tests, e2e tests
   - Convert BDD acceptance criteria → test case names + assertions
   - Assign to Playwright patterns (CLI, web, integration, etc.)

3. **Playwright Framework Scaffold** (MOMENT 4)
   - Generate `playwright.config.ts` (project-specific config)
   - Generate `pytest.ini` (Python unit/integration config)
   - Generate fixture stubs (CLI runner, web pages, database, webhooks)
   - Generate test directory structure (`tests/unit/`, `tests/e2e/`, etc.)

4. **Integration Scenarios** (MOMENT 4)
   - Extract workflow patterns from stories
   - Generate 3 end-to-end scenarios covering all major paths
   - Define Playwright test cases for each scenario

5. **Quality Gates** (MOMENT 4)
   - Coverage targets (unit >80%, integration >70%, e2e happy-path + risks)
   - Per-epic merge criteria
   - System-level ship gate definition

---

## Output Structure (Template)

Every project using this pattern will have:

```
<project>/
├── tests/
│   ├── fixtures/
│   │   ├── cli_fixtures.ts          # (if project has CLI)
│   │   ├── web_fixtures.ts          # (if project has web)
│   │   ├── db_fixtures.py           # (if project has database)
│   │   └── conftest.py              # pytest config
│   │
│   ├── unit/
│   │   ├── test_*.py                # Per-story unit tests
│   │   └── conftest.py
│   │
│   ├── integration/
│   │   ├── test_*.py                # Cross-story integration tests
│   │   └── conftest.py
│   │
│   ├── e2e/
│   │   ├── cli/
│   │   │   └── test_*.ts            # CLI e2e tests (Playwright)
│   │   ├── web/
│   │   │   └── test_*.ts            # Web e2e tests (Playwright)
│   │   ├── pages/                   # Page objects
│   │   └── conftest.ts
│   │
│   ├── performance/
│   │   └── test_*.ts                # Latency, throughput benchmarks
│   │
│   └── visual/
│       └── test_*.ts                # Visual regression tests
│
├── playwright.config.ts             # Playwright config (generated, project-specific)
├── pytest.ini                       # Pytest config (generated)
└── test-architecture-tea.md         # This file (generated)
```

---

## Key Customization Points

Each project's test architecture is customized based on:

1. **Project components**: Does it have CLI? Web? API? Webhooks?
2. **Risk profile**: High-risk items get more test layers
3. **Automation patterns**: Webhook + cron, manual authoring, real-time, etc.
4. **Technology stack**: 
   - Python backend → pytest + Click CliRunner
   - React frontend → Playwright web tests
   - Async jobs → mock time + async fixtures
   - Database → SQLAlchemy + test DB factories

---

## Template: Playwright Fixtures (Shared)

All projects use the **same fixture patterns**. Create a shared package:

### `pyforge-testing-kit` (Shared Package)

```
pyforge-testing-kit/
├── playwright/
│   ├── cli_runner.ts       # CliRunner base class (spawn subprocess)
│   ├── page_fixtures.ts    # Shared page objects (Header, Sidebar, etc.)
│   ├── http_mocks.ts       # Shared HTTP mocking patterns
│   └── time_mocks.ts       # Time-based mocking (freezegun, playright.clock)
│
├── pytest/
│   ├── db_fixtures.py      # Database factory base classes
│   ├── auth_fixtures.py    # Auth context fixtures
│   ├── builders.py         # Test data builders (ProgressBuilder, etc.)
│   └── assertion_helpers.py  # Shared assertion helpers
│
└── templates/
    ├── playwright.config.ts.jinja    # Config template (customizable per project)
    ├── pytest.ini.jinja              # Pytest config template
    └── conftest.ts.jinja             # Playwright conftest template
```

**Usage in each project**:
```python
# tests/fixtures/conftest.py
from pyforge_testing_kit.pytest import db_fixtures, auth_fixtures

# Reuse shared fixtures
@pytest.fixture
def test_db():
    return db_fixtures.create_test_db()

@pytest.fixture
def mock_auth():
    return auth_fixtures.mock_operator_role()
```

---

## Fleet Integration: CLAUDE.md Update

Add to `CLAUDE.md` under "Behavioral Guidelines" → "Testing":

```markdown
## Testing as Engineering (BMAD TEA + Playwright)

Every PyForge project follows the **Dream-to-Code model with systematic testing**:

1. **Dream** → `bmad-spec` produces spec
2. **Spec** → `bmad-create-epics-and-stories` produces stories
3. **Stories** → `bmad-tea-playwright` produces test architecture
4. **Test Architecture** → Development teams execute tests as stories are built

**Default Test Framework**: Playwright (CLI, web, integration) + pytest (unit)
- Playwright handles: CLI subprocess testing, web UI, integration workflows, visual regression, performance
- pytest handles: Unit tests, database fixtures, state assertions
- Shared: `pyforge-testing-kit` package (reusable fixtures, page objects, builders)

**Test Architecture Output**:
- `test-architecture-tea.md` (risk assessment, test matrix, scenarios, quality gates)
- `tests/` directory (fixtures, unit, integration, e2e, performance)
- `playwright.config.ts` + `pytest.ini` (project-specific configs)

**Execution Flow**:
```
Dream → Spec → Stories → (parallel: dev + test architecture)
  ↓
bmad-tea-playwright generates test-architecture-tea.md
  ↓
Dev team implements stories + runs tests (pytest unit, Playwright e2e)
  ↓
Quality gates: unit >80%, integration >70%, e2e happy-path + 3 risks
  ↓
Merge to main (all gates PASS)
```

**Repeatability**:
- Apply pattern to any BMAD project: `bmad-tea-playwright --epics <file> --project <name>`
- All PyForge projects use same fixtures (inherited from `pyforge-testing-kit`)
- Test architecture scales to 10+ projects without duplication
```

---

## Orchestration: Workflow Script

Save this as `.claude/workflows/tea-playwright-fleet-apply.yaml` (or `.md` for the script):

```yaml
name: Apply TEA + Playwright to PyForge Project
description: Generate test architecture for any BMAD project

inputs:
  project_name: string  # e.g., "pyforge-atlas"
  epics_file: string    # Path to epics-with-stories.md
  architecture_file: string  # Path to ARCHITECTURE-SPINE.md

steps:
  - name: Validate inputs
    action: check_files_exist
    files: [epics_file, architecture_file]
  
  - name: Generate risk assessment
    action: bmad_tea_risk_analysis
    input: epics_file
    output: risk-heat-map.md
  
  - name: Generate test matrix
    action: bmad_tea_test_matrix
    input: epics_file
    output: test-matrix.md
  
  - name: Generate Playwright fixtures
    action: generate_playwright_fixtures
    project: project_name
    output: tests/fixtures/
  
  - name: Generate integration scenarios
    action: generate_integration_scenarios
    input: epics_file
    output: tests/e2e/
  
  - name: Generate quality gates
    action: generate_quality_gates
    input: architecture_file
    output: quality-gates.md
  
  - name: Assemble test-architecture-tea.md
    action: assemble_document
    inputs: [risk-heat-map, test-matrix, scenarios, quality-gates]
    output: test-architecture-tea.md
    location: _bmad-output/projects/{project_name}/planning-artifacts/
```

---

## Checklist: Using This Pattern

### Per Project

- [ ] Dream exists: `docs/dreams/<project>.md`
- [ ] Spec produced: `_bmad-output/projects/<project>/planning-artifacts/specs/spec-*.md`
- [ ] PRD produced: `_bmad-output/projects/<project>/planning-artifacts/prds/prd-*.md`
- [ ] Architecture produced: `_bmad-output/projects/<project>/planning-artifacts/architecture/*.md`
- [ ] Epics + Stories produced: `epics-with-stories.md`
- [ ] **Test architecture generated**: `test-architecture-tea.md` ← YOU ARE HERE
- [ ] `tests/` directory scaffolded with fixtures
- [ ] `playwright.config.ts` + `pytest.ini` created
- [ ] Development teams ready to execute stories with tests

---

## Metrics: Fleet View

Dashboard should track per project:

```
Project          | Dream | Spec | PRD | Arch | Epics | Stories | Test Arch | Dev Ready
-----------------|-------|------|-----|------|-------|---------|-----------|----------
pyforge-herald   |  ✅   |  ✅  |  ✅  |  ✅  |   ✅   |    ✅    |    ✅     |    🚀
pyforge-atlas    |  ✅   |  ✅  |  ✅  |  ✅  |   ✅   |    ✅    |    ⏳     |    ⏸️
pyforge-warden   |  ✅   |  ✅  |  ✅  |  ✅  |   ✅   |    ✅    |    ⏳     |    ⏸️
pyforge-marshal  |  ✅   |  ✅  |  ✅  |  ✅  |   ✅   |    ✅    |    📋    |    ⏸️
```

Each step in the chain is **automated or templated** (no manual re-work per project).

---

## Next: Automate This Workflow

1. **Create skill**: `bmad-tea-playwright` (or extend existing `bmad-create-epics-and-stories`)
2. **Create shared package**: `pyforge-testing-kit` (fixtures, page objects, builders)
3. **Update CLAUDE.md**: Add testing pattern as fleet standard
4. **Update dashboard**: Track test-architecture status per project
5. **Run on fleet**: Apply to pyforge-atlas, pyforge-warden, pyforge-marshal

---

## References

- **Herald implementation**: `_bmad-output/projects/pyforge-herald/planning-artifacts/test-architecture-tea.md`
- **Playwright docs**: https://playwright.dev/
- **BMAD TEA docs**: https://bmad-code-org.github.io/bmad-method-test-architecture-enterprise/llms-full.txt
- **Shared testing kit**: (to be created in `/src/shared/packages/pyforge-testing-kit/`)
