---
title: First portal slice — deck status for one slug
type: feature
created: '2026-08-25'
status: ready
updated: '2026-08-25'
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/change-history/sprint-change-proposal-2026-08-25-station-skill-portal.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-1-skf-domain-skills-from-station-packages.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-2-personas-act-only-through-grammar-and-mcp.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** Empty /stations/herald/ does not show deck status.

**Approach:** Show herald deck status for one slug via PortalClient only.

## Acceptance Criteria

- Given an authenticated herald-role session, when the operator opens /stations/herald/, then one slug's status renders via PortalClient only.
- Given src/platform/, when scanned, then no raw HTTP, no pyforge.* import, no chrome copy.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-herald/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-herald` only — never `scripts/bmad-switch`. Ledger key `17-2-first-portal-slice-deck-status`.

**Block If:** A change would replace `conda-forge-expert`, add `pyforge.*` under `src/platform/`, or start the paired Wave story this spec does not own.

**Never:** Lane 1 CMS takeover. Raw HTTP. Chrome copy.

</intent-contract>

## Code Map

- django-herald
- PortalClient

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated. Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 17.2 and the 2026-08-25 station-skill-portal SCP. Follow steward 29.1/29.2 for SKF+persona shape. Wave A stories must not edit `CLAUDE.md` / `AGENTS.md` except steward 33.1 via `skf-export-skill` after rebase if required.

## Spec Change Log

- 2026-08-25: drafted from epics.md for fleet drain preflight

## Review Triage Log

## Verification

**Commands:**
- station test suite for `pyforge-herald` — expected: new tests pass
- `git diff origin/main -- src/platform` — expected: no `import pyforge` / `from pyforge`
