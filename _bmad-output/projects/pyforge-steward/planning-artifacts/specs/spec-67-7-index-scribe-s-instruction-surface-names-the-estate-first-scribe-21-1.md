---
title: '67.7: Index — scribe''s instruction surface names the estate first (scribe 21.1)'
type: 'docs'
created: '2026-09-25'
status: 'blocked'
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

**Problem:** CAP-15's surface is scribe's instruction surface; steward needs one row showing it.

**Approach:** This row flips `done` when scribe Story 21.1 closes.

## Boundaries & Constraints

**Always:**
- Scribe's artifacts are named, never edited, by steward.

**Never:**
- Do not merge PRs #1563 / #1564 / #1576; port their payload by hand where this story names it.
- Do not flip any Epic 44 `blocked` key or `pyforge.cutover_root`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.
- Do not edit `rxm7706/python-foundry`.
- Do not flip this key off `blocked` before scribe 21.1 is `done` (operator confirmation required).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| scribe 21.1 done | scribe ledger | row flips `done` | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-python-foundry-cutover fnd:CAP-15`.
Dream: `docs/dreams/pyforge-unifying-strategy.md` § *Where next* → *Consolidation — 2026-09-25*.
Ledger key: `67-7-index-scribe-s-instruction-surface-names-the-estate-first-scribe-21-1`.
Ledger status at mint: `blocked` — operator confirmation required to flip.
Minted 2026-09-25 from `epics.md` so `marshal factory dispatch` can resolve `spec-67-7-index-scribe-s-instruction-surface-names-the-estate-first-scribe-21-1.md`.

## Epic excerpt

**Type:** index • **Effort:** S • **Deps:** cross-station: scribe Story 21.1 (ledger `blocked` until it closes) • **FR/AD:** fnd:CAP-15
**Surface:** this file only (the index row). Scribe's artifacts are **named, never edited** by steward.
**Given** scribe owns the instruction surface (`spec-pyforge-scribe:CAP-27`) and CAP-15's surface is `AGENTS.md` / `CLAUDE.md`
**When** scribe lands Story 21.1
**Then** this row flips `done`

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- scribe ledger shows `21-1-agents-md-opens-with-what-this-repository-is: done`.
