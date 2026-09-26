---
title: '67.6: Index — herald''s dossier states the cutover''s control plane (herald 26.1)'
type: 'docs'
created: '2026-09-25'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** CAP-14's surface is herald's `docsite/**` (`spec-pyforge-herald`, which absorbed `spec-pyforge-pages` 2026-09-17); steward needs one row showing it.

**Approach:** This row flips `done` when herald Story 26.1 closes.

## Boundaries & Constraints

**Always:**
- Herald's artifacts are named, never edited, by steward.

**Never:**
- Do not merge PRs #1563 / #1564 / #1576; port their payload by hand where this story names it.
- Do not flip any Epic 44 `blocked` key or `pyforge.cutover_root`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.
- Do not edit `rxm7706/python-foundry`.
- Do not flip this key off `blocked` before herald 26.1 is `done` (operator confirmation required).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| herald 26.1 done | herald ledger | row flips `done` | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-python-foundry-cutover fnd:CAP-14`.
Dream: `docs/dreams/pyforge-unifying-strategy.md` § *Where next* → *Consolidation — 2026-09-25*.
Ledger key: `67-6-index-herald-s-dossier-states-the-cutover-s-control-plane-herald-26-1`.
Ledger status at mint: `blocked` — operator confirmation required to flip.
Minted 2026-09-25 from `epics.md` so `marshal factory dispatch` can resolve `spec-67-6-index-herald-s-dossier-states-the-cutover-s-control-plane-herald-26-1.md`.

## Epic excerpt

**Type:** index • **Effort:** S • **Deps:** cross-station: herald Story 26.1 (ledger `blocked` until it closes) • **FR/AD:** fnd:CAP-14
**Surface:** this file only (the index row). Herald's artifacts are **named, never edited** by steward.
**Given** herald owns `docsite/**` (`spec-pyforge-herald`'s surface; it absorbed `spec-pyforge-pages` on 2026-09-17) and CAP-14's surface is the dossier
**When** herald lands Story 26.1
**Then** this row flips `done`

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- herald ledger shows `26-1-the-dossier-reads-the-a-b-cutover-as-control-plane-fact: done`.

## Outcome

Flipped `done` 2026-09-26, on operator confirmation. AGENTS.md requires that confirmation before a `blocked` key moves.
- Herald Story 26.1 landed through PR #1619, merge `df7a651aa9` ("Merge pyforge-herald/26-1 into main").
  - `git merge-base --is-ancestor` confirms its commits are on `main`.
  - Herald's tracked ledger on `main` reads `26-1-the-dossier-reads-the-a-b-cutover-as-control-plane-fact: done` and `epic-26: done`.
- Steward changed only its own index row: this spec, the Story 67.6 status line in `epics.md`, and the ledger row through `sprint-ledger-sync`. No herald artifact was edited.
- `pixi run --frozen -e pyforge-steward pyforge-steward-test`: 1695 passed, 2 skipped.
