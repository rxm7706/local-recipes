---
title: SKF domain skill and BMAD persona for marshal
type: feature
created: '2026-08-25'
status: in-review
updated: '2026-08-25'
baseline_revision: 865b95dc951c8a6de87d05bb10c8395a75da8008
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/change-history/sprint-change-proposal-2026-08-25-station-skill-portal.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-1-skf-domain-skills-from-station-packages.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-2-personas-act-only-through-grammar-and-mcp.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** Marshal has no station-owned SKF skill or bmad-agent-marshal.

**Approach:** SKF from src/shared/packages/pyforge-marshal/ if missing. Persona uses only pyforge marshal … and POST /stations/marshal/mcp. Do not implement bmad-loop → supervisor ingest. No CFE replace. No CLAUDE/AGENTS export.

## Acceptance Criteria

- Given steward 29 proved the shape, when this story completes, then .claude/skills/pyforge-marshal/ exists with provenance.
- Given bmad-agent-marshal, when it completes a station task, then only grammar + MCP appear.
- Given this PR, when reviewed, then no bmad-loop ingest wire is added.
- Given CFE and CLAUDE.md/AGENTS.md, when this PR lands, then they are unchanged.
- Given src/platform/, when scanned, then no new pyforge.* import.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger key `27-1-skf-skill-and-persona-for-marshal`.

**Block If:** A change would replace `conda-forge-expert`, add `pyforge.*` under `src/platform/`, or start the paired Wave story this spec does not own.

**Never:** Wave B loop-home list. Supervisor ingest. Epic 22 factory dispatch. CFE replace. CLAUDE/AGENTS export.

</intent-contract>

## Code Map

- `.claude/skills/pyforge-marshal/`
- `.claude/skills/bmad-agent-marshal/`
- `src/shared/packages/pyforge-marshal/`

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated. Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 27.1 and the 2026-08-25 station-skill-portal SCP. Follow steward 29.1/29.2 for SKF+persona shape. Wave A stories must not edit `CLAUDE.md` / `AGENTS.md` except steward 33.1 via `skf-export-skill` after rebase if required.

## Spec Change Log

- 2026-08-25: drafted from epics.md for fleet drain preflight

## Review Triage Log

## Verification

**Commands:**
- station test suite for `pyforge-marshal` — expected: new tests pass
- `git diff origin/main -- src/platform` — expected: no `import pyforge` / `from pyforge`
