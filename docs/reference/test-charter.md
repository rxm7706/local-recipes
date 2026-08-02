# The Eight Smiths Testing Charter

## The Guild — Eight Stations, One Owner of Execution

**Doctrine**: Every station renders its own verdict. The hand that builds is never the gate that judges. Marshal alone owns execution, sequencing on verdicts it never authors.

---

## The Eight Smiths: Refined Mottos

| # | Smith | Motto | Station | Role |
|---|-------|-------|---------|------|
| 1 | 🎺 Herald | Capture the dream. Illustrate the telemetry. Proclaim the release. | herald | Visual Media Engine & System Messenger |
| 2 | ⚔️ Marshal | Enforce the spec. Guard the boundaries. Run the line. | marshal | Build Factory Supervisor & BMAD Orchestrator |
| 3 | 🗺️ Atlas | Map the ecosystem. Know the risks. Set the foundation. | atlas | Dependency Mapper & Data Pipeline Architect |
| 4 | 🛡️ Warden | Halt the threat. Clear the axes. Protect the perimeter. | warden | 6-Axis Security & Hygiene Auditor |
| 5 | 🧱 Mason | Orchestrate the build. Bridge two worlds. Ship deterministically. | mason | Package & Release Craftsman |
| 6 | 🏥 Doctor | Check the vitals. Diagnose the fault. Rank what matters. | doctor | Ecosystem Health & Diagnostics Officer |
| 7 | 📖 Scribe | Capture the decision. Keep the graph. Answer from memory. | scribe | Knowledge Curator & Team Memory Keeper |
| 8 | 👑 Steward | Supply the estate. Guard the credentials. Ensure reliability. | steward | Platform, Deployment & Operations Officer |

---

## Testing Charter: Each Smith's Responsibility

### 🎺 Herald — Proclaimer
**Motto**: "Capture the dream. Illustrate the telemetry. Proclaim the release."

**Testing Focus**:
- CLI visibility (progress, success, notice commands)
- Web UI (4-tab navigation, responsive design, interactive elements)
- Proclamation accuracy (claims backed by evidence, notices permanent)
- E2E: Dream → Proclamation workflow

**Quality Gates**:
- CLI <1s (95th percentile)
- Web <2s (95th percentile)
- Evidence links validated (0% broken links)
- Visibility coverage >90%

---

### ⚔️ Marshal — Commander
**Motto**: "Enforce the spec. Guard the boundaries. Run the line."

**Testing Focus**:
- Policy composition (multi-layer config, inheritance)
- Boundary enforcement (rules, gates, constraints)
- Line execution (orchestration, coordination)
- Cross-station integration

**Quality Gates**:
- Policy validation unit tests >85%
- Boundary enforcement integration tests >75%
- No policy bypass scenarios
- Orchestration reliability >99%

---

### 🗺️ Atlas — Navigator
**Motto**: "Map the ecosystem. Know the risks. Set the foundation."

**Testing Focus**:
- Dependency discovery (accuracy, freshness)
- Risk assessment (correctness, completeness)
- Intelligence pipeline accuracy
- Ecosystem mapping (supply chain intelligence)

**Quality Gates**:
- Discovery accuracy >95%
- Map completeness >99%
- Query performance <500ms
- Pipeline throughput benchmarks pass

---

### 🛡️ Warden — Guardian
**Motto**: "Halt the threat. Clear the axes. Protect the perimeter."

**Testing Focus**:
- Security gates (vulnerability detection, compliance)
- Threat halting (false positives/negatives balance)
- Dependency validation (supply chain integrity)
- All six audit axes covered (hygiene, security, license, currency, provenance, maintenance)

**Quality Gates**:
- Gate coverage 100% of dependencies
- False positive rate <5%
- Security scan performance <5min
- No unprotected vectors

---

### 🧱 Mason — Artisan
**Motto**: "Orchestrate the build. Bridge two worlds. Ship deterministically."

**Testing Focus**:
- Build orchestration (dual-ecosystem coordination)
- Environment binding (consistency, isolation)
- Dual-ship verification (PyPI + conda-forge)
- Deterministic reproducibility

**Quality Gates**:
- Build reproducibility 100%
- Environment binding consistency >99%
- Ship success rate >99.5%
- Artifact integrity verified

---

### 🏥 Doctor — Physician
**Motto**: "Check the vitals. Diagnose the fault. Rank what matters."

**Testing Focus**:
- Health metrics (status checks, diagnostics)
- Fault diagnosis (error detection, root cause)
- Prioritization (ranking by impact, urgency)
- Gate enforcement (quality, compliance)

**Quality Gates**:
- Health check coverage 100%
- Diagnosis accuracy >95%
- Gate pass rates tracked
- Ecosystem uptime >99.9%

---

### 📖 Scribe — Chronicler
**Motto**: "Capture the decision. Keep the graph. Answer from memory."

**Testing Focus**:
- Decision capture accuracy (no loss of context)
- Graph integrity (relationships preserved)
- Memory recall (fast, accurate answers)
- Documentation completeness

**Quality Gates**:
- Decision capture 100% of changes
- Graph query performance <100ms
- Recall accuracy >99%
- Documentation coverage >95%

---

### 👑 Steward — Provisioner
**Motto**: "Supply the estate. Guard the credentials. Ensure reliability."

**Testing Focus**:
- Infrastructure provisioning (resource availability)
- Credential management (secure, auditable)
- Operational continuity (no unexpected downtime)
- Access governance (privilege enforcement)

**Quality Gates**:
- Provisioning success >99.9%
- Key rotation verified
- Uptime SLA met (≥99%)
- Alert/escalation coverage 100%

---

## The Guild Crew: One Owner of Execution

**Marshal** owns the execution policy — the coordination layer that ties all 8 Smiths together.

**The Chain of Command**:
```
GUILD CREW
    ↓
[Marshal — Execution Owner]
    ↓
┌─────────────────────────────────────────┐
│  Herald  ·  Atlas   ·  Warden          │
│  Mason   ·  Doctor  ·  Scribe  ·  Steward
│         [8 Smiths]                     │
└─────────────────────────────────────────┘
    ↓
Dream → Code Pipeline (All 8 stations)
    ↓
[Test Architecture — BMAD TEA + Playwright]
    ↓
Development (Each Smith implements with tests)
    ↓
Shipped Features
```

---

## Testing as a Smith's Craft

Each Smith's craft includes:

1. **Unit Tests** (>80% coverage)
   - Smith tests their component's logic
   - Dependencies mocked
   - Edge cases covered

2. **Integration Tests** (>70% coverage)
   - Smith integrates with adjacent stations
   - Cross-Smith workflows tested
   - End-to-end scenarios verified

3. **E2E Tests** (Happy path + 3 risks)
   - Smith tests their Motto comes true
   - Full Dream-to-Code workflow
   - Visual + performance verified

4. **Performance Tests** (<1s CLI, <2s web)
   - Smith's craft meets speed requirements
   - No regressions in throughput
   - Benchmarks tracked

---

## The Testing Hierarchy (Guild-Wide)

```
ALL 8 SMITHS
    ↓
Quality Gates (Unit >80%, Integration >70%, E2E pass)
    ↓
Each Smith's Craft Tests (per motto)
    ↓
Integration Layer Tests (Smith-to-Smith)
    ↓
End-to-End Scenarios (Dream-to-Code)
    ↓
Shipped with Confidence
```

---

## Deployment: Eight Smiths, One Release

When a dream flows through the Dream-to-Code Factory:

1. **Herald** captures and illustrates it
2. **Marshal** enforces the spec and runs the line
3. **Atlas** charts dependencies and maps the world
4. **Warden** halts threats and protects the perimeter
5. **Mason** orchestrates builds and ships structure
6. **Doctor** checks vitals and keeps systems alive
7. **Scribe** captures decisions and answers from memory
8. **Steward** supplies platform and ensures reliability

**All with systematic tests** — each Smith's craft is verified before handoff.

---

## The Charter Principle

> "The Guild Crew and Eight Smiths execute dreams to code through test-driven excellence."

Each Smith:
- ✅ Tests their own craft (unit + integration)
- ✅ Integrates with adjacent Smiths (cross-station)
- ✅ Delivers their Motto (quality verified)
- ✅ Passes the gates (quality gates enforced)
- ✅ Ships with confidence (full test coverage)

---

---

## Implementation Roadmap (Phase 1-4)

### Phase 1: Foundation ✅ COMPLETE

**Deliverables**:
- [x] Herald test architecture (1,895 lines with Playwright patterns)
- [x] Pattern documented (reusable across projects)
- [x] Automation script created (one command per project)

**Files**: `_bmad-output/projects/pyforge-herald/planning-artifacts/test-architecture-tea.md`

### Phase 2: Automation Setup ⏳ NEXT SPRINT (6-8 hours)

**Deliverables**:
- [ ] Create `pyforge-testing-kit` shared package (npm + PyPI)
- [ ] Add pixi task: `pixi run tea-playwright-all`
- [ ] Test full cycle on pyforge-atlas

### Phase 3: Fleet Deployment 📋 2-3 WEEKS (30 min execution)

**Deliverables** (All 8 Smiths):
- [ ] Run script on atlas, doctor, herald, marshal, mason, scribe, steward, warden
- [ ] Verify consistency across all 8 stations
- [ ] Update dashboard with test-architecture column

**Batch Command**:
```bash
bash apply_tea_playwright_fleet.sh
```

### Phase 4: Development Integration 🚀 ONGOING

**Deliverables**:
- [ ] Each station implements stories with tests (pytest unit + Playwright e2e)
- [ ] CI gates enforce coverage (unit >80%, integration >70%, e2e)
- [ ] Dashboard tracks test status per station

---

## How to Apply to Any Project

**Pre-Requisite**: Project must have `epics-with-stories.md`

**Command**:
```bash
python _bmad/scripts/bmad_tea_playwright.py \
  --project <project-name> \
  --epics _bmad-output/projects/<project-name>/planning-artifacts/epics-with-stories.md \
  --architecture _bmad-output/projects/<project-name>/planning-artifacts/architecture/ARCHITECTURE-SPINE.md
```

**Output**:
- `test-architecture-tea.md` (project-specific test strategy)
- `playwright.config.ts` (Playwright configuration)
- `pytest.ini` (Pytest configuration)
- `tests/` (directory scaffold with fixture stubs)

---

## References

- **Canonical Reference**: `_bmad-output/projects/pyforge-herald/planning-artifacts/test-architecture-tea.md` (Herald test architecture, 1,895 lines)
- **Automation Script**: `_bmad/scripts/bmad_tea_playwright.py` (one command per project)
- **Pattern Documentation**: `_bmad-output/projects/pyforge-herald/planning-artifacts/tea-playwright-addendum.md` (reusable pattern guide)

---

## Summary

**The Eight Smiths execute their craft through the PyForge Dream to Code Factory.**

Each Smith has their motto, their station, and their testing responsibility. All are unified by:
- One Dream-to-Code pipeline
- One test framework (BMAD TEA + Playwright)
- One quality standard (unit >80%, integration >70%, e2e pass)
- One owner of execution (Marshal)

**Together, they turn dreams into shipped features with confidence.**

🎺 Herald · ⚔️ Marshal · 🗺️ Atlas · 🛡️ Warden · 🧱 Mason · 🏥 Doctor · 📖 Scribe · 👑 Steward

**The Guild — Eight Stations, One Owner of Execution.**
