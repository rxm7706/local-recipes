---
sources:
  - _bmad/scripts/bmad_tea_playwright.py
  - scripts/tea_playwright_check.py
  - src/shared/packages/pyforge-testing-kit/README.md
verified: 2026-11-17
---

# The Eight Smiths Testing Charter

## The Guild — Eight Stations, One Owner of Execution

**Doctrine**: Every station renders its own verdict. The hand that builds is never the gate that judges. Marshal alone owns execution, sequencing on verdicts it never authors.

## The Eight Smiths: Refined Mottos

The mottos and roles are the Charter's (`docs/dreams/pyforge-charter.md`); where this table and the Charter disagree, the Charter wins.

| # | Smith | Motto | Station | Role |
|---|-------|-------|---------|------|
| 1 | 🎺 Herald | Capture the dream. Illustrate the telemetry. Proclaim the release. | herald | Visual Media Engine & System Messenger |
| 2 | ⚔️ Marshal | Enforce the spec. Guard the boundaries. Run the line. | marshal | Autonomous Build Factory Supervisor & Orchestrator |
| 3 | 🗺️ Atlas | Chart the dependencies. Map the world. Define the floor. | atlas | Dependency Mapper & Data Pipeline Architect |
| 4 | 🛡️ Warden | Halt the threat. Clear the axes. Protect the perimeter. | warden | Six-Axis Ecosystem Security & Hygiene Auditor |
| 5 | 🧱 Mason | We forge the blocks. We bind the environment. We ship the structure. | mason | Package & Release Craftsman |
| 6 | 🏥 Doctor | Check the vitals. Diagnose the fault. Keep the ecosystem alive. | doctor | Ecosystem Health & Diagnostics Officer |
| 7 | 📖 Scribe | Capture the decision. Keep the graph. Answer from memory. | scribe | Knowledge Curator & Team Memory Keeper |
| 8 | 👑 Steward | Provision the line. Hold the keys. Keep the lights on. | steward | Platform, Deployment & Operations Officer |

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

### 🗺️ Atlas — Navigator
**Motto**: "Chart the dependencies. Map the world. Define the floor."

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

### 🛡️ Warden — Guardian
**Motto**: "Halt the threat. Clear the axes. Protect the perimeter."

**Testing Focus**:
- Security gates (vulnerability detection, compliance)
- Threat halting (false positives/negatives balance)
- Dependency validation (supply chain integrity)
- All six audit axes covered (hygiene, security, license, currency, provenance, maintenance); the Charter records the first four as gating today and provenance and maintenance as Vision-tier, not built

**Quality Gates**:
- Gate coverage 100% of dependencies
- False positive rate <5%
- Security scan performance <5min
- No unprotected vectors

### 🧱 Mason — Artisan
**Motto**: "We forge the blocks. We bind the environment. We ship the structure."

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

### 🏥 Doctor — Physician
**Motto**: "Check the vitals. Diagnose the fault. Keep the ecosystem alive."

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

### 👑 Steward — Provisioner
**Motto**: "Provision the line. Hold the keys. Keep the lights on."

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

## The Charter Principle

> "The Guild Crew and Eight Smiths execute dreams to code through test-driven excellence."

Each Smith:
- ✅ Tests their own craft (unit + integration)
- ✅ Integrates with adjacent Smiths (cross-station)
- ✅ Delivers their Motto (quality verified)
- ✅ Passes the gates (quality gates enforced)
- ✅ Ships with confidence (full test coverage)

## Implementation Roadmap (Phase 1-4)

The roadmap below was written on 2026-08-02. Phases 1 to 3 have since landed in a different shape from the one first planned; each phase says what the tree holds on 2026-11-17.

### Phase 1: Foundation ✅ COMPLETE

**Deliverables**:
- [x] Herald test architecture
- [x] Pattern documented (reusable across projects)
- [x] Automation script created (one command per project)

**Files**: `_bmad-output/projects/pyforge-herald/planning-artifacts/test-architecture.md`, generated by `_bmad/scripts/bmad_tea_playwright.py`.

<!-- governance-currency:ignore-start (the pre-reconcile filename, cited as superseded) -->
The first hand-written version was `_bmad-output/projects/pyforge-herald/planning-artifacts/test-architecture-tea.md` (1,895 lines); the generated file replaced it.
<!-- governance-currency:ignore-end -->

### Phase 2: Automation Setup ✅ COMPLETE

**Deliverables**:
- [x] `pyforge-testing-kit` shared package: `src/shared/packages/pyforge-testing-kit/`, a Python package (no npm half was built)
- [x] Pixi task: `pixi run -e pyforge-guild tea-playwright-all`
- [x] Full cycle run on pyforge-atlas

### Phase 3: Fleet Deployment ✅ COMPLETE

**Deliverables** (All 8 Smiths):
- [x] Script run on atlas, doctor, herald, marshal, mason, scribe, steward, warden: each station has a `planning-artifacts/test-architecture.md`
- [x] Consistency across all 8 stations is held by a detector, `pixi run -e pyforge-guild tea-playwright-check`
- [ ] Update dashboard with test-architecture column

**Batch Command**:
```bash
pixi run -e pyforge-guild tea-playwright-all
```

### Phase 4: Development Integration 🚀 ONGOING

**Deliverables**:
- [ ] Each station implements stories with tests (pytest unit + Playwright e2e)
- [ ] CI gates enforce coverage (unit >80%, integration >70%, e2e); today `scripts/coverage_gates_ci.py` enforces per-station floors on touched modules, not these two figures
- [ ] Dashboard tracks test status per station

## How to Apply to Any Project

**Pre-Requisite**: the station has an `epics.md` under `_bmad-output/projects/pyforge-<station>/planning-artifacts/`. The script covers the eight stations only.

**Command**:
```bash
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-<station>
```

Add `--dry-run` to render and validate without writing, `--check` to compare the story ids in `epics.md` with the Story Coverage Matrix on disk, and `--scaffold` to create empty `unit/`, `integration/`, `e2e/` and `fixtures/` folders under the station package's `tests/`.

**Output**:
- `planning-artifacts/test-architecture.md` (the station's test strategy, regenerated from `epics.md` and the live test inventory; a `TBD` in the output fails the run)

## References

- **Canonical Reference**: `_bmad-output/projects/pyforge-herald/planning-artifacts/test-architecture.md` (Herald test architecture)
- **Automation Script**: `_bmad/scripts/bmad_tea_playwright.py` (one command per station, or `--all`)
- **Originating Dream**: `archive/docs/dreams/pyforge-testing-charter.md`

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
