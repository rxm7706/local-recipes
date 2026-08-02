---
project_name: 'pyforge-herald'
project_phase: 'in-progress'
user_name: 'rxm7706'
date: '2026-08-02'
sections_completed: ['overview', 'status']
---

# Project Context for AI Agents — Herald

_Critical rules and patterns for Herald, the visual media & communications
station. This project is currently 4/27 stories done (per
`sprint-status-ledger.yaml`, the tracked completion source of record)._

**Status:** 4/27 stories done (18 backlog, 5 optional)

---

## Overview

Herald is the **visual media & communications** station in the PyForge
Guild — the `herald` CLI formalizing the realized Design↔Code bridge
(`seed`/`pull`, watch mode, stale-mirror detection), plus deck and
infographic production.

**Critical Rules:**
- Follow the project's PRD and architecture documents as the binding contract.
- All implementation must pass the station's readiness gates before merging.
- Coordinate with other stations via the deferred-work ledger.

**Key Reference Files:**
- Brief: `_bmad-output/projects/pyforge-herald/planning-artifacts/briefs/brief-herald-pitch-2026-08-01/brief.md`
- PRD: `_bmad-output/projects/pyforge-herald/planning-artifacts/prds/prd-pyforge-herald-2026-08-01/prd.md`
- Architecture: `_bmad-output/projects/pyforge-herald/planning-artifacts/architecture/architecture-herald-pitch-2026-08-01/ARCHITECTURE-SPINE.md`
- Epics: `_bmad-output/projects/pyforge-herald/planning-artifacts/epics.md`
- Readiness: `_bmad-output/projects/pyforge-herald/planning-artifacts/implementation-readiness-report-20260801.md`
- Deferred Work: `_bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md`

---

## Testing & Gates

All stories in this project must pass:
1. **Local verification:** `pixi run -e local-recipes pytest src/shared/packages/pyforge-herald/tests/`
2. **Readiness gate:** `bmad-check-implementation-readiness` at epic completion.
3. **Integration gate:** All dependent stories must complete before downstream gates.

---

## Execution Model

- Stories are tracked in `sprint-status-ledger.yaml` (the tracked twin of the
  gitignored Tier-3 feed — dashboards and CI read the ledger, not the feed).
- Deferred work is recorded in the ledger with owner and target completion date.
- Each story spec carries its own acceptance criteria and dependencies.
- BMAD loop orchestration drives unattended story execution when gates are met.

---

## References

- **Station directory:** `_bmad-output/projects/pyforge-herald/`
- **Planning artifacts:** `_bmad-output/projects/pyforge-herald/planning-artifacts/`
- **Implementation artifacts:** `_bmad-output/projects/pyforge-herald/implementation-artifacts/` (gitignored)
