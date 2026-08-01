---
project_name: 'pyforge-herald'
project_phase: 'in-progress'
user_name: 'rxm7706'
date: '2026-08-01'
sections_completed: ['overview', 'status']
---

# Project Context for AI Agents — Herald

_Critical rules and patterns for Presentation Deck & Infographic Layer. This project is currently 17/17 stories (infrastructure only)._

**Status:** 17/17 stories (infrastructure only)

---

## Overview

This is the Presentation Deck & Infographic Layer station within the PyForge Guild. 

**Critical Rules:**
- Follow the project's spec and architecture documents as the binding contract.
- Use the station's existing project-context from pyforge-herald.md as the reference.
- All implementation must pass the station's readiness gates before merging.
- Coordinate with other stations via the deferred-work ledger.

**Key Reference Files:**
- Spec: `docs/specs/` or `_bmad-output/projects/pyforge-herald/planning-artifacts/SPEC.md`
- Architecture: `_bmad-output/projects/pyforge-herald/planning-artifacts/architecture.md` (if exists)
- Epics: `_bmad-output/projects/pyforge-herald/planning-artifacts/epics.md`
- Readiness: `_bmad-output/projects/pyforge-herald/planning-artifacts/implementation-readiness-report*.md`
- Deferred Work: `_bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md`

---

## Testing & Gates

All stories in this project must pass:
1. **Local verification:** Run the station's test suite (if exists).
2. **Readiness gate:** `bmad-check-implementation-readiness` at epic completion.
3. **Integration gate:** All dependent stories must complete before downstream gates.

---

## Execution Model

- Stories are tracked in the sprint-status ledger under this station.
- Deferred work is recorded in the ledger with owner and target completion date.
- Each story spec carries its own acceptance criteria and dependencies.
- BMAD loop orchestration drives unattended story execution when gates are met.

---

## References

- **Station directory:** `_bmad-output/projects/pyforge-herald/`
- **Planning artifacts:** `_bmad-output/projects/pyforge-herald/planning-artifacts/`
- **Implementation artifacts:** `_bmad-output/projects/pyforge-herald/implementation-artifacts/` (gitignored)
