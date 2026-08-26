---
title: First portal slice — one inventory/run row
type: feature
created: '2026-08-25'
status: ready
updated: '2026-08-25'
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/change-history/sprint-change-proposal-2026-08-25-station-skill-portal.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-1-skf-domain-skills-from-station-packages.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-2-personas-act-only-through-grammar-and-mcp.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** Empty /stations/atlas/ shell does no real job.

**Approach:** HTMX on /stations/atlas/ shows one factory inventory or run-state row via django-pyforge PortalClient only. Not DW-H3. Not Vizro.

## Acceptance Criteria

- Given an authenticated atlas-role session, when the operator opens /stations/atlas/, then one row renders via PortalClient only.
- Given src/platform/ and django-atlas, when reviewed, then no raw HTTP, no pyforge.* under src/platform/, no chrome copy.
- Given DW-H3 / La Suite REST, when this story lands, then it is not implemented here.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-atlas/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-atlas` only — never `scripts/bmad-switch`. Ledger key `19-2-first-portal-slice-inventory-row`.

**Block If:** A change would replace `conda-forge-expert`, add `pyforge.*` under `src/platform/`, or start the paired Wave story this spec does not own.

**Never:** DW-H3 REST. Vizro on the host. Raw HTTP. pyforge.* under src/platform/. Chrome copy.

</intent-contract>

## Code Map

- django-atlas portal templates/views
- django-pyforge PortalClient (read-only pattern from other stations)

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated. Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 19.2 and the 2026-08-25 station-skill-portal SCP. Follow steward 29.1/29.2 for SKF+persona shape. Wave A stories must not edit `CLAUDE.md` / `AGENTS.md` except steward 33.1 via `skf-export-skill` after rebase if required.

## Spec Change Log

- 2026-08-25: drafted from epics.md for fleet drain preflight

## Review Triage Log

## Verification

**Commands:**
- station test suite for `pyforge-atlas` — expected: new tests pass
- `git diff origin/main -- src/platform` — expected: no `import pyforge` / `from pyforge`
