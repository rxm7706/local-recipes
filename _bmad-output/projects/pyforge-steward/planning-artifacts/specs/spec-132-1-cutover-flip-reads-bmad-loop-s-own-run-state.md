---
title: '132.1: cutover flip reads bmad-loop''s own run state'
type: 'fix'
created: '2026-11-24'
status: 'done'
story: 132-1-cutover-flip-reads-bmad-loop-s-own-run-state
spec: spec-python-foundry-cutover
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # the loop guard is the flip's own gate; a gated gate is a silent green (roster list)
surface:
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/cutover.py'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_cutover.py'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `steward cutover flip` is refused while a Marshal loop runs, but `loops_running` reads a `status` or `state` word from each `state.json` under the loop home, and bmad-loop's `RunState.to_dict()` carries `finished`, `stopped` and `crashed` and no such word. A live run reads as not running, so the writer lock can move under it.

**Approach:** Read a state file under `<loop home>/.bmad-loop/runs/<run id>/` by bmad-loop's three keys: running until one of them is true. Count a run state that is unreadable, not an object, or carries neither the keys nor a status as running. Keep the status-word reading for any other `state.json`, and read past one that is not an object. Read the loop home from `BMAD_LOOP_HOME_ROOT` when it is set, and read the checkout's own `.bmad-loop/runs/` as well.

Ledger key: `132-1-cutover-flip-reads-bmad-loop-s-own-run-state`.

### Living CAP citations

- spec-python-foundry-cutover fnd:CAP-8 (realized, no text change); no AD moves; no FR.

## Boundaries & Constraints

**Always:**
- Read the file bmad-loop writes; a run state that cannot be shown over refuses the flip.
- Keep the refusal's opening words; name the state file and `bmad-loop stop` after them.

**Never:**
- Never import marshal or bmad-loop from steward's source, and never shell to a loop CLI.
- Never gate the guard behind a flag.

## Acceptance Criteria

**Given** `loops_running` reads a `status` or `state` word from each `state.json` under the loop home, and bmad-loop's run state carries `finished`, `stopped` and `crashed` and no such word
**When** a run's state file is read by those three keys, and a run state that cannot be shown over counts as running
**Then** an unfinished or paused run refuses the flip with "flip refused: a Marshal loop is running" and the state file's path, and a finished, stopped or crashed run does not
**And** the loop home follows `BMAD_LOOP_HOME_ROOT` when it is set, a `state.json` outside a run directory is read by its status word as before, and one that is a list is read past instead of raising

- **AC1 — The cutover tests pass.** Expected: exit 0.

  ```bash
  pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_cutover.py -q
  ```

- **AC2 — A state from the installed bmad-loop reads running.** Expected: exit 0 with no skip (the Guild environment carries bmad-loop; steward's own does not, and skips that one test).

  ```bash
  pixi run -e pyforge-guild pytest src/shared/packages/pyforge-steward/tests/unit/test_cutover.py -q
  ```

</intent-contract>

## Binding

- Capabilities: spec-python-foundry-cutover fnd:CAP-8 (realized, no text change); no AD moves; no FR.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-24 entry (the flip's loop guard reads the state bmad-loop writes); operator rulings of 2026-11-24.
- Epic: Epic 132, minted with this story.
- Ledger key: `132-1-cutover-flip-reads-bmad-loop-s-own-run-state`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."132"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-24: minted from the station Dream's 2026-11-24 entry and the operator's rulings of the same date; implemented the same day and left `in-review`: implementation and review do not share a session.
- 2026-11-24: closed. PR #2383 merged as b5019058e3 (`Merge pyforge-doctor/61-1 into main`) after its 43 CI checks passed and the full local `pr-preflight` exited 0; independent reviewers read the diff against this spec before the merge and their findings were applied.
