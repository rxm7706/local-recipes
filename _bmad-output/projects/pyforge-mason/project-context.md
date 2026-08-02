---
project_name: 'pyforge-mason'
project_phase: 'in-progress'
user_name: 'rxm7706'
date: '2026-08-02'
sections_completed: ['overview', 'status']
---

# Project Context for AI Agents — Mason

_Critical rules and patterns for Mason, the packaging station. This project
is currently 4/48 stories done (per `sprint-status-ledger.yaml`, the tracked
completion source of record)._

**Status:** 4/48 stories done (39 backlog, 5 optional)

---

## Overview

Mason is the **packaging** station in the PyForge Guild — the CLI
productizing the `conda-forge-expert` capability (`mason recipe/package/environment`).
`mason recipe` wraps the CFE skill + MCP surface by subprocess; `package` and
`environment` are built natively. Never forks the craft.

**Critical Rules:**
- Follow the project's PRD and architecture documents as the binding contract.
- All implementation must pass the station's readiness gates before merging.
- Coordinate with other stations via the deferred-work ledger.

**Key Reference Files:**
- Brief: `_bmad-output/projects/pyforge-mason/planning-artifacts/briefs/brief-pyforge-mason-2026-07-25/brief.md`
- PRD: `_bmad-output/projects/pyforge-mason/planning-artifacts/prds/prd-pyforge-mason-2026-07-25/prd.md`
- Architecture: `_bmad-output/projects/pyforge-mason/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md`
- Epics: `_bmad-output/projects/pyforge-mason/planning-artifacts/epics.md`
- Readiness: `_bmad-output/projects/pyforge-mason/planning-artifacts/implementation-readiness-report-20260801.md`
- Deferred Work: `_bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md`

---

## Testing & Gates

All stories in this project must pass:
1. **Local verification:** `pixi run -e local-recipes pytest src/shared/packages/pyforge-mason/tests/`
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

- **Station directory:** `_bmad-output/projects/pyforge-mason/`
- **Planning artifacts:** `_bmad-output/projects/pyforge-mason/planning-artifacts/`
- **Implementation artifacts:** `_bmad-output/projects/pyforge-mason/implementation-artifacts/` (gitignored)
