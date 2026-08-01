---
project_name: 'pyforge-warden'
project_phase: 'shipped'
user_name: 'rxm7706'
date: '2026-08-01'
sections_completed: ['overview', 'status']
---

# Project Context for AI Agents — Warden

_Critical rules and patterns for Compliance Gate & Project Orchestration. This project is currently 31/31 stories, 2026-07-24 retro._

**Status:** 31/31 stories, 2026-07-24 retro

---

## Overview

This is the Compliance Gate & Project Orchestration station within the PyForge Guild. 

**Critical Rules:**
- Follow the project's spec and architecture documents as the binding contract.
- Use the station's existing project-context from pyforge-warden.md as the reference.
- All implementation must pass the station's readiness gates before merging.
- Coordinate with other stations via the deferred-work ledger.

**Key Reference Files:**
- Spec: `docs/specs/` or `_bmad-output/projects/pyforge-warden/planning-artifacts/SPEC.md`
- Architecture: `_bmad-output/projects/pyforge-warden/planning-artifacts/architecture.md` (if exists)
- Epics: `_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md`
- Readiness: `_bmad-output/projects/pyforge-warden/planning-artifacts/implementation-readiness-report*.md`
- Deferred Work: `_bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md`

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

- **Station directory:** `_bmad-output/projects/pyforge-warden/`
- **Planning artifacts:** `_bmad-output/projects/pyforge-warden/planning-artifacts/`
- **Implementation artifacts:** `_bmad-output/projects/pyforge-warden/implementation-artifacts/` (gitignored)
