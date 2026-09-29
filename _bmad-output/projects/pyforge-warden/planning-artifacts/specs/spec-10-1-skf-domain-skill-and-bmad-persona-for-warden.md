---
title: SKF domain skill and BMAD persona for warden
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-26'
baseline_revision: 865b95dc951c8a6de87d05bb10c8395a75da8008
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/change-history/sprint-change-proposal-2026-08-25-station-skill-portal.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-1-skf-domain-skills-from-station-packages.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-2-personas-act-only-through-grammar-and-mcp.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** Warden has no station-owned SKF skill or bmad-agent-warden.

**Approach:** SKF from src/shared/packages/pyforge-warden/ if missing. Persona uses only pyforge warden … and POST /stations/warden/mcp. Does not publish a second PR-gate verdict. No CFE replace. No CLAUDE/AGENTS export.

## Acceptance Criteria

- Given steward 29 proved the shape, when this story completes, then .claude/skills/pyforge-warden/ exists with provenance.
- Given bmad-agent-warden, when it acts, then it does not publish a second PR-gate verdict.
- Given CFE and CLAUDE.md/AGENTS.md, when this PR lands, then they are unchanged.
- Given src/platform/, when scanned, then no new pyforge.* import.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-warden/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-warden` only — never `scripts/bmad-switch`. Ledger key `10-1-skf-domain-skill-and-bmad-persona-for-warden`.

**Block If:** A change would replace `conda-forge-expert`, add `pyforge.*` under `src/platform/`, or start the paired Wave story this spec does not own.

**Never:** Wave B audit start/get. Second PR gate. CFE replace. CLAUDE/AGENTS export.

</intent-contract>

## Code Map

- `.claude/skills/pyforge-warden/`
- `.claude/skills/bmad-agent-warden/`
- `src/shared/packages/pyforge-warden/`

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated. Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 10.1 and the 2026-08-25 station-skill-portal SCP. Follow steward 29.1/29.2 for SKF+persona shape. Wave A stories must not edit `CLAUDE.md` / `AGENTS.md` except steward 33.1 via `skf-export-skill` after rebase if required.

## Spec Change Log

- 2026-08-25: drafted from epics.md for fleet drain preflight

## Review Triage Log

## Auto Run Result

Status: done

Summary: SKF `pyforge-warden` compiled from `src/shared/packages/pyforge-warden/` with provenance. `bmad-agent-warden` consults CAP-15 and may only emit `pyforge warden …` and `POST /stations/warden/mcp`. Persona does not publish a second PR-gate verdict. CFE and CLAUDE.md/AGENTS.md unchanged. No `pyforge.*` under `src/platform/`. Story 10.2 not started.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
