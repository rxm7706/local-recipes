---
title: First portal slice — list loop homes
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-26'
baseline_revision: c3f75232a15bb3c28730c546e8f955cda59054df
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/change-history/sprint-change-proposal-2026-08-25-station-skill-portal.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-1-skf-domain-skills-from-station-packages.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-2-personas-act-only-through-grammar-and-mcp.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** Empty /stations/marshal/ does not list loop homes.

**Approach:** List provisioned loop homes via PortalClient only. Do not implement bmad-loop ingest.

## Acceptance Criteria

- Given an authenticated marshal-role session, when the operator opens /stations/marshal/, then homes list via PortalClient only.
- Given this PR, when reviewed, then bmad-loop → supervisor ingest is not implemented.
- Given src/platform/, when scanned, then no raw HTTP, no pyforge.* import, no chrome copy.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger key `27-2-first-portal-slice-loop-homes`.

**Block If:** A change would replace `conda-forge-expert`, add `pyforge.*` under `src/platform/`, or start the paired Wave story this spec does not own.

**Never:** bmad-loop ingest. Epic 22 dispatch. Raw HTTP. Chrome copy.

</intent-contract>

## Code Map

- django-marshal
- PortalClient

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated. Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 27.2 and the 2026-08-25 station-skill-portal SCP. Follow steward 29.1/29.2 for SKF+persona shape. Wave A stories must not edit `CLAUDE.md` / `AGENTS.md` except steward 33.1 via `skf-export-skill` after rebase if required.

## Spec Change Log

- 2026-08-25: drafted from epics.md for fleet drain preflight
- 2026-08-26: /stations/marshal/ lists provisioned homes via PortalClient.list_loop_homes

## Review Triage Log

Self-review (build-auto reviewers not spawned — parent Wave B agent): ACs hold — PortalClient-only list, no ingest, no pyforge under src/platform, chrome still extended.

## Auto Run Result

Status: done
Reconciled 2026-09-20: the `in-review` verdict below is the session's own record at halt time; the story was landed afterwards and the ledger row promoted to `done` by `1e845b55fc 2026-09-16 land marshal fold (CAP-8 pilot): one chain — 32 Dreams, 55 Specs, rekey 2026-09-16` — that promotion is the ruling this record now reflects.
baseline_revision: c3f75232a15bb3c28730c546e8f955cda59054df
Verification: marshal meta 7 passed; platform portal tests 7 passed (plus empty-homes case added)

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Status reconcile 2026-09-20

- frontmatter `status` `shipped` → `done` (ledger row `27-2-first-portal-slice-list-loop-homes: done`).
- Auto Run Result `Status: in-review` → `done` (see the reconcile line under it).
