# The Eight Smiths & Their Testing Charter
## PyForge Dream to Code Factory — BMAD TEA + Playwright

---

## The Eight Smiths: Personas & Mottos

| Persona | Station | Motto | Testing Responsibility |
|---------|---------|-------|------------------------|
| **Herald** · Proclaimer | herald | "Capture the dream. Illustrate the telemetry. Proclaim the release." | Visibility testing (CLI, web UI, proclamation surfaces) |
| **Marshal** · Commander | marshal | "Enforce the spec. Guard the boundaries. Run the line." | Governance testing (policies, composition, configuration) |
| **Atlas** · Navigator | atlas | "Map the ecosystem. Know the risks. Set the foundation." | Intelligence testing (discovery, mapping, risk assessment) |
| **Warden** · Guardian | warden | "Halt the threat. Clear the axes. Protect the perimeter." | Security testing (gates, compliance, dependency validation) |
| **Mason** · Artisan | mason | "Orchestrate the build. Bridge two worlds. Ship deterministically." | Build testing (dual-ecosystem orchestration, assembly, shipping) |
| **Doctor** · Physician | doctor | "Check the vitals. Diagnose the fault. Rank what matters." | Quality testing (gates, diagnostics, prioritization) |
| **Scribe** · Chronicler | scribe | "Capture the decision. Keep the graph. Answer from memory." | Memory testing (documentation, decision capture, recall) |
| **Steward** · Provisioner | steward | "Supply the estate. Guard the credentials. Ensure reliability." | Operations testing (infrastructure, access governance, reliability) |

---

## Testing Charter: Each Smith's Role

### 🎺 **Herald** — Proclaimer
**Motto**: "Capture the dream. Illustrate the telemetry. Proclaim the release."

**Testing Focus**:
- CLI visibility (progress, success, notice commands)
- Web UI (4-tab navigation, responsive design, interactive elements)
- Proclamation accuracy (claims backed by evidence, notices permanent)
- E2E: Dream → Proclamation workflow

**Quality Gates**:
- CLI <1s (95th %)
- Web <2s (95th %)
- Evidence links validated (0% broken links)
- Visibility coverage >90%

---

### ⚔️ **Marshal** — Commander
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

### 🗺️ **Atlas** — Navigator
**Motto**: "Map the ecosystem. Know the risks. Set the foundation."

**Testing Focus**:
- Dependency discovery (accuracy, freshness)
- Mapping intelligence (correctness, completeness)
- Floor definition (schema, indexing, performance)
- Intelligence pipeline accuracy

**Quality Gates**:
- Discovery accuracy >95%
- Map completeness >99%
- Query performance <500ms
- Pipeline throughput benchmarks pass

---

### 🛡️ **Warden** — Guardian
**Motto**: "Halt the threat. Clear the axes. Protect the perimeter."

**Testing Focus**:
- Security gates (vulnerability detection, compliance)
- Threat halting (false positives/negatives balance)
- Dependency validation (supply chain integrity)
- Perimeter protection (all axes covered)

**Quality Gates**:
- Gate coverage 100% of dependencies
- False positive rate <5%
- Security scan performance <5min
- No unprotected vectors

---

### 🧱 **Mason** — Artisan
**Motto**: "Orchestrate the build. Bridge two worlds. Ship deterministically."

**Testing Focus**:
- Build orchestration (dual-ecosystem coordination)
- Environment binding (consistency, isolation)
- Dual-ship verification (PyPI + conda-forge correctness)
- Deterministic reproducibility

**Quality Gates**:
- Build reproducibility 100%
- Environment binding consistency >99%
- Ship success rate >99.5%
- Artifact integrity verified

---

### 🏥 **Doctor** — Physician
**Motto**: "Check the vitals. Diagnose the fault. Rank what matters."

**Testing Focus**:
- Vitals checking (health metrics, status checks)
- Fault diagnosis (error detection, root cause)
- Prioritization (ranking remediation by impact)
- Gate enforcement (quality, compliance)

**Quality Gates**:
- Health check coverage 100%
- Diagnosis accuracy >95%
- Gate pass rates tracked
- Ecosystem uptime >99.9%

---

### 📖 **Scribe** — Chronicler
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

### 👑 **Steward** — Provisioner
**Motto**: "Supply the estate. Guard the credentials. Ensure reliability."

**Testing Focus**:
- Infrastructure provisioning (platform availability, resource allocation)
- Credential management (secure access, rotation, audit)
- Operational reliability (no unexpected downtime)
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
5. **Mason** forges blocks and ships structure
6. **Doctor** checks vitals and keeps systems alive
7. **Scribe** captures decisions and answers from memory
8. **Steward** provisions and keeps lights on

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

## References

- **BMAD TEA + Playwright Framework**: `GUILD_TEST_ARCHITECTURE_VISION.md`
- **Deployment Roadmap**: `PYFORGE_FLEET_TESTING_ROADMAP.md`
- **Automation Script**: `_bmad/scripts/bmad_tea_playwright.py`
- **Herald (Canonical)**: `_bmad-output/projects/pyforge-herald/planning-artifacts/test-architecture-tea.md`

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
