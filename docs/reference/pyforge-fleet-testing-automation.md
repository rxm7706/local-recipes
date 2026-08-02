# PyForge Fleet: Automated BMAD TEA + Playwright Testing (Repeatable Pattern)

**Goal**: One-command test architecture generation for any PyForge project.

---

## What You Have Now

### 1. **Canonical Reference** (Herald)
✅ `_bmad-output/projects/pyforge-herald/planning-artifacts/test-architecture-tea.md` (1,895 lines)
- Serves as the **reference implementation** for all projects
- Includes Playwright patterns for CLI, web, integration, automation, visual, performance testing
- All other projects inherit from this structure

### 2. **Reusable Pattern Document**
✅ `_bmad-output/projects/pyforge-herald/planning-artifacts/tea-playwright-addendum.md`
- Describes **how to apply the pattern** to any project
- Lists customization points (CLI? Web? Webhooks?)
- Shows shared fixture strategy

### 3. **Automation Script**
✅ `_bmad/scripts/bmad_tea_playwright.py`
- **One command** generates test architecture for any project
- Parses epics → generates risk assessment → test matrix → Playwright config → fixtures
- Produces: `test-architecture-tea.md` + `playwright.config.ts` + `pytest.ini` + test directory scaffold

### 4. **Fleet Pattern Memory**
✅ Auto-memory entry documenting the pattern (reusable across sessions)

---

## How to Use: One Command Per Project

### **For pyforge-atlas:**

```bash
python _bmad/scripts/bmad_tea_playwright.py \
  --project pyforge-atlas \
  --epics _bmad-output/projects/pyforge-atlas/planning-artifacts/epics-with-stories.md \
  --architecture _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/ARCHITECTURE-SPINE.md \
  --output-dir _bmad-output/projects/pyforge-atlas/planning-artifacts/
```

**Output:**
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/test-architecture-tea.md` ✅
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/playwright.config.ts` ✅
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/pytest.ini` ✅
- `_bmad-output/projects/pyforge-atlas/tests/` (directory scaffold) ✅

### **For pyforge-warden:**

```bash
python _bmad/scripts/bmad_tea_playwright.py \
  --project pyforge-warden \
  --epics _bmad-output/projects/pyforge-warden/planning-artifacts/epics-with-stories.md \
  --architecture _bmad-output/projects/pyforge-warden/planning-artifacts/architecture/ARCHITECTURE-SPINE.md \
  --output-dir _bmad-output/projects/pyforge-warden/planning-artifacts/
```

### **For pyforge-marshal, pyforge-doctor, etc.:**

Same pattern — just change `--project` and `--epics`/`--architecture` paths.

---

## Fleet Orchestration (Automated across all projects)

Create a **batch script** to run on all projects:

```bash
#!/bin/bash
# apply_tea_playwright_fleet.sh

PROJECTS=(
  "pyforge-herald"
  "pyforge-atlas"
  "pyforge-warden"
  "pyforge-marshal"
  "pyforge-doctor"
  "pyforge-genesis"
  "pyforge-manticore"
  "pyforge-mason"
)

for project in "${PROJECTS[@]}"; do
  echo "🔄 Generating test architecture for $project..."
  
  EPICS="_bmad-output/projects/$project/planning-artifacts/epics-with-stories.md"
  ARCH="_bmad-output/projects/$project/planning-artifacts/architecture/ARCHITECTURE-SPINE.md"
  OUTPUT="_bmad-output/projects/$project/planning-artifacts/"
  
  if [[ -f "$EPICS" ]]; then
    python _bmad/scripts/bmad_tea_playwright.py \
      --project "$project" \
      --epics "$EPICS" \
      --architecture "$ARCH" \
      --output-dir "$OUTPUT"
    echo "✅ $project complete"
  else
    echo "⏳ $project: no epics-with-stories.md yet"
  fi
done

echo "✅ Fleet test architecture generation complete!"
```

**Run once to generate for all projects:**
```bash
bash apply_tea_playwright_fleet.sh
```

---

## Shared Fixtures Package (Next Layer)

Create **`src/shared/packages/pyforge-testing-kit/`** — all projects inherit from it:

```
pyforge-testing-kit/
├── src/
│   ├── playwright/
│   │   ├── cli_runner.ts          # Base CliRunner class
│   │   ├── page_fixtures.ts       # Shared page objects (Header, Tabs, etc.)
│   │   ├── http_mocks.ts          # Shared HTTP mocking patterns
│   │   ├── time_mocks.ts          # Time-based mocking (freezegun, clock)
│   │   └── index.ts               # Exports
│   │
│   ├── pytest/
│   │   ├── db_fixtures.py         # Base database fixtures
│   │   ├── auth_fixtures.py       # Shared auth context fixtures
│   │   ├── builders.py            # Test data builders
│   │   ├── assertion_helpers.py   # Shared assertions
│   │   └── __init__.py
│   │
│   └── templates/
│       ├── playwright.config.ts.jinja
│       ├── pytest.ini.jinja
│       └── conftest.ts.jinja
│
├── package.json                   # npm package
├── pyproject.toml                 # Python package
└── README.md
```

**Usage in each project:**

```typescript
// tests/e2e/cli/test-example.ts
import { CliRunner } from 'pyforge-testing-kit/playwright';
import { test, expect } from '@playwright/test';

const cli = new CliRunner(process.env.PYTHON_PATH || 'python');

test('example CLI test', async () => {
  const result = await cli.run(['progress', 'warden']);
  expect(result.exitCode).toBe(0);
});
```

```python
# tests/unit/test_example.py
from pyforge_testing_kit.pytest import db_fixtures

def test_database_transaction(test_db):
    """Inherited from pyforge-testing-kit."""
    record = test_db.create_progress(station='warden')
    assert record.station == 'warden'
```

---

## Dashboard Integration (Track Across Fleet)

Add to dashboard (`docs/dashboard/data.js`):

```javascript
const TEST_ARCHITECTURE_STATUS = {
  'pyforge-herald': {
    status: 'complete',
    file: '_bmad-output/projects/pyforge-herald/planning-artifacts/test-architecture-tea.md',
    coverage: { unit: '>80%', integration: '>70%', e2e: 'happy_path + risks' },
  },
  'pyforge-atlas': {
    status: 'generated',  // Just ran bmad_tea_playwright.py
    file: '_bmad-output/projects/pyforge-atlas/planning-artifacts/test-architecture-tea.md',
    coverage: { unit: '>80%', integration: '>70%', e2e: 'happy_path + risks' },
  },
  'pyforge-warden': {
    status: 'pending',  // Waiting for epics-with-stories.md
  },
  // ... etc for all 8 projects
};
```

**Dashboard view:**

```
Project              | Dream | Spec | PRD | Arch | Epics | Test Arch | Dev Status
--------------------|-------|------|-----|------|-------|-----------|----------
pyforge-herald       |  ✅   |  ✅  |  ✅  |  ✅  |  ✅   |    ✅     | 🚀 Coding
pyforge-atlas        |  ✅   |  ✅  |  ✅  |  ✅  |  ✅   |    ✅     | 🏗️ Ready
pyforge-warden       |  ✅   |  ✅  |  ✅  |  ✅  |  ✅   |    ✅     | 🏗️ Ready
pyforge-marshal      |  ✅   |  ✅  |  ✅  |  ✅  |  ✅   |    ✅     | 📋 Queued
pyforge-doctor       |  ✅   |  ✅  |  ✅  |  ✅  |  ✅   |    ⏳     | 🎯 In queue
pyforge-genesis      |  ✅   |  ✅  |  ✅  |  ✅  |  ✅   |    ⏳     | 🎯 In queue
```

---

## Integration with CLAUDE.md

Add to `.CLAUDE.md` under "Behavioral Guidelines" → "Testing":

```markdown
## Testing as Engineering: BMAD TEA + Playwright (Fleet Standard)

Every PyForge project follows **Dream-to-Code** with systematic testing:

**Execution Chain**:
```
Dream → Spec → Stories → (parallel: dev + tests)
  ↓
bmad-create-epics-and-stories produces: epics-with-stories.md
  ↓
bmad_tea_playwright.py generates: test-architecture-tea.md
  ↓
Dev teams implement stories + run tests (pytest unit, Playwright e2e)
  ↓
All tests pass: unit >80%, integration >70%, e2e happy-path + risks
  ↓
Merge to main
```

**Repeatability**: Apply `bmad_tea_playwright.py` to any project with stories (one command):

```bash
python _bmad/scripts/bmad_tea_playwright.py \
  --project <name> \
  --epics _bmad-output/projects/<name>/planning-artifacts/epics-with-stories.md \
  --architecture _bmad-output/projects/<name>/planning-artifacts/architecture/ARCHITECTURE-SPINE.md
```

**Shared Infrastructure**: All projects inherit from `pyforge-testing-kit`:
- Fixtures: CLI runner, page objects, database factories, auth contexts
- Patterns: Playwright config, pytest config, test structure
- Frameworks: Playwright (CLI/web/integration) + pytest (unit)

**Fleet Tracking**: Dashboard shows test-architecture status per project (generated, complete, in-progress, pending).
```

---

## Checklist: Making It a Fleet Standard

### Phase 1: Foundation (Herald) ✅
- [x] Herald test architecture complete (canonical reference)
- [x] Playwright patterns documented (CLI, web, integration, etc.)
- [x] Automation script created (`bmad_tea_playwright.py`)
- [x] Pattern document written (`tea-playwright-addendum.md`)

### Phase 2: Automation (This Sprint) 
- [ ] Create `pyforge-testing-kit` shared package (npm + PyPI)
- [ ] Add script to pixi.toml: `pixi run tea-playwright-all` (runs on all projects)
- [ ] Update CLAUDE.md with testing pattern
- [ ] Update dashboard to track test-architecture status
- [ ] Test on pyforge-atlas (full cycle: Dream → Spec → Stories → Test Arch)

### Phase 3: Fleet Deployment (Next Sprint)
- [ ] Run `bmad_tea_playwright.py` on pyforge-atlas
- [ ] Run `bmad_tea_playwright.py` on pyforge-warden
- [ ] Run `bmad_tea_playwright.py` on pyforge-marshal
- [ ] Run `bmad_tea_playwright.py` on pyforge-doctor, pyforge-genesis, etc.
- [ ] Verify all test architectures are consistent (same patterns, structure)
- [ ] Update dashboard: all 8+ projects show test-architecture status

### Phase 4: Development Integration (Ongoing)
- [ ] Dev teams implement Herald stories + run tests (Playwright E2E, pytest unit)
- [ ] CI gates on test pass rates (unit >80%, integration >70%, e2e scenarios)
- [ ] Monitor test execution across fleet (dashboard shows per-project test status)

---

## Key Benefits

✅ **One Command Per Project**: No manual re-work  
✅ **Consistent Structure**: All projects follow same test patterns  
✅ **Scalable**: Add 10+ projects without overhead  
✅ **Shared Fixtures**: `pyforge-testing-kit` eliminates duplication  
✅ **Fleet Visibility**: Dashboard tracks status across all projects  
✅ **Dream-to-Code Continuity**: Tests flow naturally from stories  

---

## Next Actions

1. **Create `pyforge-testing-kit` package** (shared fixtures)
   - Tasks: CLI runner, page objects, builders, templates
   - Time: 2-3 hours
   - Blocks: None (Herald can start with inline fixtures, migrate later)

2. **Run script on pyforge-atlas** (test the automation)
   - Command: `python _bmad/scripts/bmad_tea_playwright.py --project pyforge-atlas ...`
   - Verify: test-architecture-tea.md generated, matches Herald structure
   - Time: 15 minutes
   - Blocks: None (atlas epics already exist)

3. **Update CLAUDE.md + dashboard** (document the pattern)
   - Add testing section to CLAUDE.md
   - Add test-architecture-tea column to fleet dashboard
   - Time: 30 minutes
   - Blocks: None

4. **Deploy to entire fleet** (run on all 8 projects)
   - Script: `bash apply_tea_playwright_fleet.sh` (batch runner)
   - Verify: All 8 projects have test-architecture-tea.md
   - Time: 30 minutes
   - Blocks: All projects must have epics-with-stories.md

---

## References

- **Herald (Canonical)**: `_bmad-output/projects/pyforge-herald/planning-artifacts/test-architecture-tea.md`
- **Pattern Doc**: `_bmad-output/projects/pyforge-herald/planning-artifacts/tea-playwright-addendum.md`
- **Automation Script**: `_bmad/scripts/bmad_tea_playwright.py`
- **Playwright Docs**: https://playwright.dev/
- **BMAD TEA Docs**: https://bmad-code-org.github.io/bmad-method-test-architecture-enterprise/llms-full.txt
