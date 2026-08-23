---
title: The gated upstream filing
type: chore
created: '2026-08-23'
status: ready
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 96c0678145
---

<intent-contract>

## Intent

**Problem:** CAP-3 (`spec-bmad-loop-baseline-drift`) requires the drafted upstream issue in `docs/dreams/bmad-loop-baseline-drift.md` to be filed against `bmad-code-org/bmad-loop` only after two gates — or a duplicate linked instead. Until gates clear, the draft stays unfiled by design. Story 10.1 intent-gap evidence shares this report path.

**Approach:** Record both gates as checked: (1) repo access / org relationship → issue vs PR vs discussion; (2) duplicate search first. Then either file the coordinated issue (append URL to both Dreams' Realization logs; register in `upstream-register.json`) or link a found duplicate. Never edit the installed `bmad_loop` package. Never implement 20.4–20.10.

## Acceptance Criteria

- Gate (1) and gate (2) recorded as checked in Dream Realization log(s) and/or story evidence.
- Outcome is either a filed upstream URL **or** a linked duplicate URL — never a silent skip without gate records.
- Both Dreams' Realization logs updated (`bmad-loop-baseline-drift` + `bmad-loop-intent-gap-work-preservation` as applicable).
- `upstream-register.json` (Story 6.8 register) gains/updates the entry.
- No edits to `bmad_loop` package source; no auto-land of deferred work.

## Boundaries & Constraints

**Never:** Patch `bmad_loop`. Never implement 20.4–20.10. Never `scripts/bmad-switch`. Finalize marshal ledger only. Do not touch steward 16-2.

</intent-contract>

## Code Map

- `docs/dreams/bmad-loop-baseline-drift.md` — drafted issue + Realization log + backlog gates
- `docs/dreams/bmad-loop-intent-gap-work-preservation.md` — shared report Realization log
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/upstream-register.json`
- Evidence from Story 10.1 / PRs #482–#484 as needed for the filing body

## Verification

- Gates documented; URL present (filed or duplicate)
- Register + Realization logs updated
- No `bmad_loop` package mutations in the PR
