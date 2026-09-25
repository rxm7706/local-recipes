---
title: '21.1: `AGENTS.md` opens with what this repository is'
type: 'docs'
created: '2026-09-25'
status: 'ready'
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

**Problem:** `AGENTS.md` opens with the recipe factory and carries ~500 lines of notes, while the estate is two roots under a writer lock.

**Approach:** Through `bmad-project-context` for the managed block and by hand outside it: open with A's identity, the A/B roles, modes and writer lock; add the behavioural core; move each removed note to a named pointer target first.

## Boundaries & Constraints

**Always:**
- Use the worker's real status vocabulary (`draft → ready-for-dev → in-progress → in-review → done`).
- State that A is never archived (operator 2026-09-25).
- `CLAUDE.md` keeps the bare `@AGENTS.md` import.

**Never:**
- Do not merge PRs #1563 / #1564 / #1576; port their payload by hand where this story names it.
- Do not flip any Epic 44 `blocked` key or `pyforge.cutover_root`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.
- Do not edit `rxm7706/python-foundry`.
- Do not hand-edit the managed `bmad:context` block.
- Do not delete a pitfall without a pointer target that exists.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| removed incident note | pointer target | exists and is linked | fail loud |
| parity meta-test | scribe suite | green | fail loud |

</intent-contract>

## Binding

Parent Spec capability: `spec-python-foundry-cutover fnd:CAP-15`.
Dream: `docs/dreams/pyforge-unifying-strategy.md` § *Where next* → *Consolidation — 2026-09-25*.
Ledger key: `21-1-agents-md-opens-with-what-this-repository-is`.
Ledger status at mint: `backlog`.
Minted 2026-09-25 from `epics.md` so `marshal factory dispatch` can resolve `spec-21-1-agents-md-opens-with-what-this-repository-is.md`.

## Epic excerpt

**Type:** docs • **Effort:** M • **Deps:** — • **FR/AD:** fnd:CAP-15 • spec-pyforge-scribe CAP-27 • cross-station: steward index 67.7 flips `done` when this closes; reference payload PR #1563 (branch `docs/agents-pyforge-bmad`)
**Surface:** `AGENTS.md` (managed block through `bmad-project-context`; sections outside it by hand), `CLAUDE.md` (pointer + Claude-only notes), the pointer targets each removed note moves to (`.claude/memory/`, `docs/reference/`), `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py` only if a parity rule must follow a moved section.
**Given** `AGENTS.md` opens with the recipe factory and carries ~500 lines of accumulated notes, while the estate is two roots under a writer lock
**When** this story lands
**Then** the file opens with A's identity, the A/B roles, the modes (never `move`) and the writer lock, stating that A is never archived; the behavioural core adds heal-the-tissue, state over action, read-only harness ledgers and implement / review separation, using the worker's real status vocabulary (`draft → ready-for-dev → in-progress → in-review → done`); every incident note removed from the file has a named pointer target that exists
**And** `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` green; `governance-currency` (in `detectors-ci`) green; `CLAUDE.md` still imports `@AGENTS.md` bare

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0 (`governance-currency`).
