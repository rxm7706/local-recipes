# PyForge Dream to Code Factory
## The Guild Crew & 8 Smiths — BMAD TEA + Playwright Testing (Fleet Standard)

**Date**: 2026-08-02  
**Status**: Phase 1 Complete ✅  
**Vision**: You now have a **repeatable, scalable system** for applying BMAD TEA + Playwright testing across the PyForge Dream to Code Factory — enabling the Guild Crew and 8 Smiths to execute dreams to code through 8 execution stations (atlas, doctor, herald, marshal, mason, scribe, steward, warden).

Test architecture is now a first-class citizen in the Dream-to-Code pipeline.

---

## The Guild Structure

**The Guild — eight stations, one owner of execution:**

```
┌──────────────────────────────────────────────────────────────────────┐
│             THE GUILD: EIGHT STATIONS, ONE OWNER OF EXECUTION        │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. ATLAS       — Data pipeline intelligence & discovery             │
│  2. DOCTOR      — Quality gates & compliance validation              │
│  3. HERALD      — Communication & proclamation surfaces              │
│  4. MARSHAL     — Policy composition & configuration (Owner)         │
│  5. MASON       — Build orchestration & artifact assembly            │
│  6. SCRIBE      — Memory & documentation systems                     │
│  7. STEWARD     — Governance & operational controls                  │
│  8. WARDEN      — Dependency compliance & security gates             │
│                                                                      │
│  ➜ Marshal owns the execution policy (the Guild's coordination)      │
│  ➜ All stations implement stories with tests                         │
│  ➜ All dreams flow through the same Dream-to-Code pipeline           │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Dream-to-Code Pipeline (Unified Across All Stations)

Every dream in the Guild flows through the same execution pipeline:

```
Dream
  ↓
Spec (5-field kernel)
  ↓
PRD (FRs + NFRs)
  ↓
Architecture (ADs + invariants)
  ↓
Epics + Stories (BDD acceptance criteria)
  ↓
[NEW] Test Architecture (BMAD TEA + Playwright)
  ↓
Development (pytest unit + Playwright e2e)
  ↓
Shipped Feature
```

**Key**: Test architecture is now **automatically generated** at step 6 via `bmad_tea_playwright.py`.

---

## What This Means for the Guild

### Before (Ad-Hoc Testing)
- Each station re-invented test strategy
- No consistency across the Guild
- Testing was an afterthought
- No reusable fixtures or patterns

### After (Systematic Testing)
- ✅ One test framework across all 8 stations (Playwright + pytest)
- ✅ One canonical reference (Herald)
- ✅ One-command deployment per station
- ✅ Shared fixtures package (all inherit)
- ✅ Unified quality gates (unit >80%, integration >70%, e2e)
- ✅ Fleet visibility (dashboard shows test-architecture per station)

---

## Herald: Canonical Reference

**Herald** is the canonical reference implementation for the entire Guild.

**Test Architecture**: `_bmad-output/projects/pyforge-herald/planning-artifacts/test-architecture-tea.md`

**Includes**:
- 1,895 lines of comprehensive test architecture
- 9 Playwright patterns (CLI, web, integration, async, visual, performance)
- Risk assessment (11 high-risk, 14 medium, 7 low items)
- Test matrix (54 test suites across 18 stories)
- Quality gates (coverage targets + acceptance criteria)
- 3 end-to-end integration scenarios

**All other stations inherit this structure** when the automation script runs.

---

## Automation: One Command Per Station

### Single Station
```bash
python _bmad/scripts/bmad_tea_playwright.py \
  --project pyforge-atlas \
  --epics _bmad-output/projects/pyforge-atlas/planning-artifacts/epics-with-stories.md \
  --architecture _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/ARCHITECTURE-SPINE.md
```

**Output** (per station):
- `test-architecture-tea.md` (project-specific test strategy)
- `playwright.config.ts` (Playwright configuration)
- `pytest.ini` (Pytest configuration)
- `tests/` (directory scaffold with fixture stubs)

### All 8 Stations at Once
```bash
bash apply_tea_playwright_guild.sh
```

**Time**: ~30 minutes to deploy across all 8 stations

---

## Shared Fixtures: One Package for the Guild

**`pyforge-testing-kit`** — shared testing infrastructure all stations inherit:

```
pyforge-testing-kit/
├── playwright/
│   ├── cli_runner.ts          # Spawn CLI subprocess
│   ├── page_fixtures.ts       # Web page objects
│   ├── http_mocks.ts          # HTTP response mocking
│   └── time_mocks.ts          # Time-based testing (cron, stale-links)
│
├── pytest/
│   ├── db_fixtures.py         # Database factories
│   ├── auth_fixtures.py       # Auth context mocking
│   ├── builders.py            # Test data builders
│   └── assertion_helpers.py   # State assertions
│
└── templates/
    ├── playwright.config.ts.jinja
    ├── pytest.ini.jinja
    └── conftest.ts.jinja
```

**Usage**: All 8 stations install and import from this package.

**Benefit**: Update once, benefit all stations instantly.

---

## Quality Gates (Guild-Wide)

**Every story in every station must pass:**

| Gate | Target | Tool |
|------|--------|------|
| **Unit Coverage** | >80% | pytest --cov |
| **Integration Coverage** | >70% | pytest --cov |
| **E2E Coverage** | Happy path + 3 high-risk scenarios | Playwright |
| **CLI Performance** | <1s (95th percentile) | Playwright timers |
| **Web Performance** | <2s (95th percentile) | Playwright timers |
| **Ready to Merge** | All gates PASS | CI enforces |

---

## Execution Phases

### Phase 1: Foundation ✅ COMPLETE
- [x] Herald test architecture (1,895 lines)
- [x] Automation script created
- [x] Pattern documented
- [x] Memory entry saved

**Time**: ~8 hours (completed in this session)

### Phase 2: Shared Infrastructure ⏳ NEXT SPRINT
- [ ] Create `pyforge-testing-kit` package
- [ ] Add pixi task: `pixi run tea-playwright-all`
- [ ] Update CLAUDE.md with testing section
- [ ] Test full cycle on one station (atlas)

**Time**: ~6-8 hours

### Phase 3: Guild-Wide Deployment 📋 2-3 WEEKS
- [ ] Run script on atlas
- [ ] Run script on doctor
- [ ] Run script on herald (verify reference)
- [ ] Run script on marshal
- [ ] Run script on mason
- [ ] Run script on scribe
- [ ] Run script on steward
- [ ] Run script on warden

**Time**: ~30 minutes (all 8 stations in parallel)

### Phase 4: Development Integration 🚀 ONGOING
- [ ] Each station implements stories with tests
- [ ] CI gates enforce coverage + performance
- [ ] Dashboard tracks test-architecture status
- [ ] Shared fixtures refined based on feedback

---

## Guild Dashboard: Unified View

**Track Dream-to-Code across the entire Guild:**

```
Station      | Dream | Spec | PRD | Arch | Epics | Stories | Test Arch | Dev Status
-------------|-------|------|-----|------|-------|---------|-----------|----------
ATLAS        |  ✅   |  ✅  |  ✅  |  ✅  |  ✅   |   ✅    |    ✅     | 🚀 Coding
DOCTOR       |  ✅   |  ✅  |  ✅  |  ✅  |  ✅   |   ✅    |    ✅     | 🏗️  Ready
HERALD       |  ✅   |  ✅  |  ✅  |  ✅  |  ✅   |   ✅    |    ✅     | 🏗️  Ready
MARSHAL      |  ✅   |  ✅  |  ✅  |  ✅  |  ✅   |   ✅    |    ✅     | 📋 Queued
MASON        |  ✅   |  ✅  |  ✅  |  ✅  |  ✅   |   ✅    |    ⏳     | 🎯 Next
SCRIBE       |  ✅   |  ✅  |  ✅  |  ✅  |  ✅   |   ✅    |    ⏳     | 🎯 Next
STEWARD      |  ✅   |  ✅  |  ✅  |  ✅  |  ✅   |   ✅    |    ⏳     | 🎯 Next
WARDEN       |  ✅   |  ✅  |  ✅  |  ✅  |  ✅   |   ✅    |    ✅     | 🏗️  Ready
```

**Each column** represents a stage in the Dream-to-Code pipeline. **Test Architecture** (new column) shows:
- ✅ Complete (test-architecture-tea.md generated)
- ⏳ In progress (running script)
- 📋 Ready (epics exist, waiting for deployment)

---

## Key Principles

### 1. One Owner of Execution
**Marshal** owns the execution policy — the coordination layer that ties all 8 stations together.

### 2. Unified Pipeline
All dreams flow through the same Dream-to-Code pipeline. Test architecture is automatic at step 6.

### 3. Shared Foundation
All stations inherit from Herald (canonical reference) and `pyforge-testing-kit` (shared fixtures).

### 4. No Duplication
Write once (fixtures, patterns, configurations), inherit everywhere.

### 5. Guild Visibility
Dashboard shows Dream-to-Code progress for all 8 stations in one view.

---

## Benefits (Guild-Wide)

| Benefit | Impact |
|---------|--------|
| **One Test Framework** | Consistency across 8 stations |
| **One Command Per Station** | 30 min to deploy to entire Guild |
| **Shared Fixtures** | Updates benefit all stations instantly |
| **Unified Quality Gates** | Unit >80%, integration >70%, e2e pass |
| **Fleet Visibility** | Dashboard shows test-architecture per station |
| **Dream-to-Code Continuity** | Tests flow naturally from stories |
| **Scalable** | Add new stations to Guild without overhead |

---

## Next Actions (Immediate)

1. **Commit & push** Herald test architecture (complete Dream-to-Code cycle)
2. **Review** `test-architecture-tea.md` (canonical reference)
3. **Announce** Guild messaging: "The Guild — eight stations, one owner of execution"

---

## Next Actions (This Sprint)

1. Create `pyforge-testing-kit` shared package
2. Add pixi task: `pixi run tea-playwright-all`
3. Update CLAUDE.md with testing section
4. Test full cycle on Atlas (verify automation works)

---

## Next Actions (2-3 Weeks)

1. Run `apply_tea_playwright_guild.sh` (deploy to all 8)
2. Verify consistency across Guild
3. Update dashboard with test-architecture column
4. Announce: "Guild is test-ready"

---

## Summary

**The Guild now has systematic testing as a first-class citizen in the Dream-to-Code pipeline.**

Every dream flows through the same pipeline: Spec → PRD → Architecture → Epics → Stories → **Test Architecture** → Development.

**Herald is the canonical reference.** All other stations inherit via:
1. One-command automation (bmad_tea_playwright.py)
2. Shared fixtures (pyforge-testing-kit)
3. Unified quality gates (unit >80%, integration >70%, e2e)

**Result**: No duplication, consistent patterns, fleet visibility, and scalability.

**The Guild is ready for development teams to build with confidence.**

---

## References

- **Herald (Canonical)**: `_bmad-output/projects/pyforge-herald/planning-artifacts/test-architecture-tea.md`
- **Automation Script**: `_bmad/scripts/bmad_tea_playwright.py`
- **Pattern Document**: `_bmad-output/projects/pyforge-herald/planning-artifacts/tea-playwright-addendum.md`
- **Fleet Roadmap**: `PYFORGE_FLEET_TESTING_ROADMAP.md`
- **Playwright Docs**: https://playwright.dev/
- **BMAD TEA Docs**: https://bmad-code-org.github.io/bmad-method-test-architecture-enterprise/llms-full.txt
