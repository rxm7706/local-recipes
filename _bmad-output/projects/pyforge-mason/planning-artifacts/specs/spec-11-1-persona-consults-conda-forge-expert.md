---
title: BMAD persona consults conda-forge-expert
type: feature
created: '2026-08-25'
status: ready
updated: '2026-08-25'
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/change-history/sprint-change-proposal-2026-08-25-station-skill-portal.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-1-skf-domain-skills-from-station-packages.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-2-personas-act-only-through-grammar-and-mcp.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** Mason needs a Path B persona without a second recipe skill.

**Approach:** Author bmad-agent-mason that consults conda-forge-expert (hand-authored). Emit only pyforge mason … and POST /stations/mason/mcp. NEVER run skf-create-skill against CFE. 01 recipe experiments still do not mint a portal/MCP/persona.

## Acceptance Criteria

- Given CFE is the operating skill, when this story completes, then .claude/skills/bmad-agent-mason/ exists as a BMAD launcher (SKILL.md + customize.toml), not SKF-compiled.
- Given a mason persona transcript, when checked, then it uses only pyforge mason … and POST /stations/mason/mcp plus consult of conda-forge-expert.
- Given .claude/skills/conda-forge-expert/, when this PR lands, then it is not version-nested SKF and has no generated_by: create-skill metadata added.
- Given CLAUDE.md/AGENTS.md, when this PR lands, then they are unchanged.
- Given src/platform/, when scanned, then no new pyforge.* import.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-mason/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-mason` only — never `scripts/bmad-switch`. Ledger key `11-1-persona-consults-conda-forge-expert`.

**Block If:** A change would replace `conda-forge-expert`, add `pyforge.*` under `src/platform/`, or start the paired Wave story this spec does not own.

**Never:** SKF skill that replaces CFE. Wave B diagnose portal. MinIO. 01 portal/MCP/persona. CLAUDE/AGENTS export.

</intent-contract>

## Code Map

- `.claude/skills/bmad-agent-mason/`
- `.claude/skills/conda-forge-expert/` — consult only, read-only
- `src/shared/packages/pyforge-mason/`

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated. Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 11.1 and the 2026-08-25 station-skill-portal SCP. Follow steward 29.1/29.2 for SKF+persona shape. Wave A stories must not edit `CLAUDE.md` / `AGENTS.md` except steward 33.1 via `skf-export-skill` after rebase if required.

## Spec Change Log

- 2026-08-25: drafted from epics.md for fleet drain preflight

## Review Triage Log

## Verification

**Commands:**
- station test suite for `pyforge-mason` — expected: new tests pass
- `git diff origin/main -- src/platform` — expected: no `import pyforge` / `from pyforge`
