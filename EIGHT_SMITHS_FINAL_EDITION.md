# The Eight Smiths — Final Edition (2026-08-02)

## The Guild — Eight Stations, One Owner of Execution

**Doctrine**: Every station renders its own verdict. The hand that builds is never the gate that judges. Marshal alone owns execution, sequencing on verdicts it never authors.

---

## The Eight Smiths: Refined Mottos

### 🎺 **Herald** — The Proclaimer
**Motto**: "Capture the dream. Illustrate the telemetry. Proclaim the release."

- **Station**: pyforge-herald
- **Role**: Visual Media Engine & System Messenger
- **Responsibilities**: 
  - First to touch the Dream (Design-Code-Bridge, Deckcraft)
  - Continuous visibility (telemetry infographics, weekly updates)
  - Last to ship it (omnichannel broadcasts, video scripts)
- **Core Promise**: Invisible engineering is failed engineering
- **Carries Forward**: Load-bearing — aligns perfectly with deck positioning

---

### ⚔️ **Marshal** — The Commander
**Motto**: "Enforce the spec. Guard the boundaries. Run the line."

- **Station**: pyforge-marshal
- **Role**: Build Factory Supervisor & BMAD Orchestrator
- **Responsibilities**:
  - Turns Spec into validated code (gated story loops)
  - Mobilizes sub-agents, contains context
  - Owns monorepo operation + PR lifecycle
- **Core Promise**: No vibe coding. Autonomy a human can trust.
- **Carries Forward**: Load-bearing — perfect alignment with deck

---

### 🗺️ **Atlas** — The Navigator
**Motto**: "Map the ecosystem. Know the risks. Set the foundation."

- **Station**: pyforge-atlas
- **Role**: Dependency Mapper & Data Pipeline Architect
- **Responsibilities**:
  - Maps PyPI + Conda together (bridging naming, versions, registries)
  - Provides intelligence for downstream decisions (Doctor, Warden)
  - Defines supply-chain baseline + risk surface
- **Core Promise**: Know what you depend on. Know what risks you carry.
- **Refinement Reason**: "Know the risks" adds strategic value that deck emphasizes but motto didn't explicitly state

---

### 🛡️ **Warden** — The Guardian
**Motto**: "Halt the threat. Clear the axes. Protect the perimeter."

- **Station**: pyforge-warden
- **Role**: 6-Axis Security & Hygiene Auditor
- **Responsibilities**:
  - Audits six axes (hygiene, security, license, currency, provenance, maintenance)
  - Hard-blocks CI when thresholds break
  - Never false-green: unevaluable is failure
- **Core Promise**: One CLI, zero trust. The gate that never lies.
- **Carries Forward**: Load-bearing — "Clear the axes" is domain-specific brilliance (the six audit axes)

---

### 🧱 **Mason** — The Artisan
**Motto**: "Orchestrate the build. Bridge two worlds. Ship deterministically."

- **Station**: pyforge-mason
- **Role**: Package & Release Craftsman
- **Responsibilities**:
  - Authors v1 recipe.yaml (via CFE delegation)
  - Resolves unified lockfiles
  - Publishes to PyPI wheels + conda-forge in one deterministic pass
  - Tends 769 feedstocks via conda-forge-expert craft
- **Core Promise**: Dual-ecosystem mastery without duplication.
- **Refinement Reason**: "Orchestrate" emphasizes unique value (wrapping CFE, not forging); "Bridge two worlds" captures dual-ship strategy; "Ship deterministically" echoes deck's emphasis on reproducibility

---

### 🏥 **Doctor** — The Physician
**Motto**: "Check the vitals. Diagnose the fault. Rank what matters."

- **Station**: pyforge-doctor
- **Role**: Ecosystem Health & Diagnostics Officer
- **Responsibilities**:
  - Pre-flight self-check before factory spins (health metrics)
  - Continuous pulse (freshness, drift, CVEs, abandonment)
  - Ranks findings into remediation worklists
  - Holds verdict on Marshal's own conformance
- **Core Promise**: Know the health. Diagnose the problem. Decide what's urgent.
- **Refinement Reason**: "Rank what matters" emphasizes Doctor's unique value — prioritization layer (Warden finds threats, Doctor ranks them by impact)

---

### 📖 **Scribe** — The Chronicler
**Motto**: "Capture the decision. Keep the graph. Answer from memory."

- **Station**: pyforge-scribe
- **Role**: Knowledge Curator & Team Memory Keeper
- **Responsibilities**:
  - Captures every load-bearing decision (decision capture layer)
  - Curates into team-owned knowledge graph
  - Answers for humans and agents (recall interface)
  - Cure for tribal memory
- **Core Promise**: Where Herald tells the world, Scribe tells the team.
- **Carries Forward**: Load-bearing — perfect alignment with deck positioning

---

### 👑 **Steward** — The Provisioner
**Motto**: "Supply the estate. Guard the credentials. Ensure reliability."

- **Station**: pyforge-steward
- **Role**: Platform, Deployment & Operations Officer
- **Responsibilities**:
  - Provisions runners and environments (platform supply)
  - Deploys services (Pages, infrastructure)
  - Holds and rotates credentials (secure access governance)
  - Enforces budgets (resource oversight)
  - Answers the pager (operational continuity)
- **Core Promise**: No privilege outlives its deployment. Reliable ops, every time.
- **Refinement Reason**: "Supply the estate" more authoritative than "provision the line" (ops-jargon); "Guard the credentials" more specific than "hold the keys"; "Ensure reliability" replaces vague "keep the lights on"

---

## Motto Alignment with Deck

| Smith | Kept? | Why |
|-------|-------|-----|
| Herald | ✅ Yes | "Capture the dream" aligns with deck's "First to touch the Dream" — load-bearing opening narrative |
| Marshal | ✅ Yes | Perfect alignment with deck's BMAD orchestrator positioning |
| Atlas | 🔄 Refined | Added "Know the risks" to emphasize strategic intelligence value; "Set the foundation" more concrete than "define the floor" |
| Warden | ✅ Yes | "Clear the axes" is domain-specific brilliance (the six audit axes) — keep exactly as-is |
| Mason | 🔄 Refined | "Orchestrate" emphasizes unique orchestration role (not just forging); "Bridge two worlds" captures dual-ship strategy; "Deterministically" echoes reproducibility emphasis |
| Doctor | 🔄 Refined | "Rank what matters" highlights Doctor's unique prioritization role (warden finds, doctor ranks) |
| Scribe | ✅ Yes | Perfect alignment with deck copy ("Where Herald tells the world, Scribe tells the team") |
| Steward | 🔄 Refined | More authoritative/formal language for executive deck; removes vague metaphors; "Guard the credentials" specific + concrete |

---

## Guild-Wide Testing Charter

Each Smith owns their testing responsibility:

| Smith | Testing Responsibility | Quality Gate |
|-------|------------------------|--------------|
| **Atlas** | Intelligence testing (discovery, risk assessment) | False positives <5%, Map completeness >99% |
| **Doctor** | Quality diagnostics + prioritization | Diagnosis accuracy >95%, Ranking correctness 100% |
| **Herald** | Visibility + proclamation testing | CLI <1s, Web <2s, Evidence links 0% broken |
| **Marshal** | Governance + orchestration testing | Policy validation >85%, Autonomy level enforcement 100% |
| **Mason** | Dual-ecosystem build testing | Build reproducibility 100%, Ship success >99.5% |
| **Scribe** | Memory + decision capture testing | Capture 100% of decisions, Recall accuracy >99% |
| **Steward** | Infrastructure + access governance testing | Provisioning success >99.9%, Key rotation verified |
| **Warden** | Compliance + risk-clearing testing | False-green rate 0%, Coverage 100% of dependencies |

---

## Execution Flow (Dream → Code)

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
Development
  → Herald captures the work (visibility)
  → Marshal enforces policies + runs loops
  → Atlas feeds intelligence (risks, dependencies)
  → Doctor checks pre-flight health + ranks issues
  → Mason orchestrates dual-ship
  → Scribe captures decisions
  → Steward provisions infrastructure
  → Warden gates before ship
  ↓
Shipped Feature
```

---

## The Doctrine in Action

**"The hand that builds is never the gate that judges"**:
- **Builder**: Mason (orchestrates build)
- **Gater**: Warden (halts threats, clears risks)
- **Coordinator**: Marshal (sequences on Warden's verdict, never overrides)

**"Every station renders its own verdict"**:
- Atlas: "Here are the risks in the dependency graph"
- Doctor: "Here are the health issues, ranked by priority"
- Warden: "Here is what failed audit, with specific causes"
- Marshal: "Based on all verdicts, here's the execution plan"

**"Marshal alone owns execution"**:
- Sequences on verdicts from 7 other stations
- Never authors those verdicts
- Owns PR lifecycle, gates, story loops, autonomy levels
- Accountable for "run the line" — factory throughput

---

## Summary: The Guild at a Glance

| # | Smith | Motto | Carries | Status |
|---|-------|-------|---------|--------|
| 1 | 🎺 Herald | Capture. Illustrate. Proclaim. | ✅ Load-bearing | Ready |
| 2 | ⚔️ Marshal | Enforce. Guard. Run the line. | ✅ Load-bearing | Shipping |
| 3 | 🗺️ Atlas | Map. Know risks. Set foundation. | 🔄 Refined | Shipped |
| 4 | 🛡️ Warden | Halt. Clear axes. Protect perimeter. | ✅ Load-bearing | Shipped |
| 5 | 🧱 Mason | Orchestrate. Bridge worlds. Ship deterministically. | 🔄 Refined | Ready |
| 6 | 🏥 Doctor | Check vitals. Diagnose. Rank what matters. | 🔄 Refined | Ready |
| 7 | 📖 Scribe | Capture. Keep graph. Answer memory. | ✅ Load-bearing | Ready |
| 8 | 👑 Steward | Supply estate. Guard credentials. Ensure reliability. | 🔄 Refined | Ready |

**Ready to ship**: 8 smiths, 8 stations, 1 factory, infinite ambition.

---

## References

- **EIGHT_SMITHS_TESTING_CHARTER.md** — Testing responsibility matrix + quality gates
- **GUILD_TEST_ARCHITECTURE_VISION.md** — TEA + Playwright framework
- **PYFORGE_FLEET_TESTING_ROADMAP.md** — Phase 1-4 implementation roadmap
- **test-architecture-tea.md** (Herald canonical) — Complete reference implementation

---

**The Guild — Eight Stations, One Owner of Execution. 2026-08-02.**
