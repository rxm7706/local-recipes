---
source_pin: 'BMAD 6.11.0 / conda-forge-expert v8.84.0'
project_name: 'pyforge-scribe'
project_phase: 'shipped'
user_name: 'rxm7706'
date: '2026-08-24'
sections_completed: ['overview', 'status']
---

# Project Context for AI Agents — Scribe

_Critical rules and patterns for Event Attribution & Ledger. Ledger: all stories done — design-complete (re-ground 2026-08-24)._

**Status:** sprint-status-ledger — **28** done · **0** backlog · **6** optional (incl. epics); design-complete / all stories done.

**Living docs:** re-ground of `architecture-bmad-infra.md` + the 8 station `project-context.md` rulebooks is a **marshal** SYNC-RUNBOOK duty (CAP-7 decision 2026-08-24) — not a per-station relay. Pins use `source_pin: BMAD 6.11.0 / conda-forge-expert v8.84.0`.

---

## Overview

This is the Event Attribution & Ledger station within the PyForge Guild. 

**Critical Rules:**
- Follow the project's spec and architecture documents as the binding contract.
- Use the station's existing project-context from pyforge-scribe.md as the reference.
- All implementation must pass the station's readiness gates before merging.
- Coordinate with other stations via the deferred-work ledger.

**Key Reference Files:**
- Spec: `docs/specs/` or `_bmad-output/projects/pyforge-scribe/planning-artifacts/SPEC.md`
- Architecture: `_bmad-output/projects/pyforge-scribe/planning-artifacts/architecture.md` (if exists)
- Epics: `_bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md`
- Readiness: `_bmad-output/projects/pyforge-scribe/planning-artifacts/implementation-readiness-report*.md`
- Deferred Work: `_bmad-output/projects/pyforge-scribe/planning-artifacts/deferred-work-ledger.md`

---

## Testing & Gates

All stories in this project must pass:
1. **Local verification:** Run the station's test suite (if exists).
2. **Readiness gate:** `bmad-sprint-planning` readiness gate (6.11; former check-implementation-readiness absorbed) at epic completion.
3. **Integration gate:** All dependent stories must complete before downstream gates.

---

## Execution Model

- Stories are tracked in the sprint-status ledger under this station.
- Deferred work is recorded in the ledger with owner and target completion date.
- Each story spec carries its own acceptance criteria and dependencies.
- BMAD loop orchestration drives unattended story execution when gates are met.

---

## References

- **Station directory:** `_bmad-output/projects/pyforge-scribe/`
- **Planning artifacts:** `_bmad-output/projects/pyforge-scribe/planning-artifacts/`
- **Implementation artifacts:** `_bmad-output/projects/pyforge-scribe/implementation-artifacts/` (gitignored)
