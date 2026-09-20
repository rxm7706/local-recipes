---
title: '20.1: The parity meta-test reds a TODO inside the managed block'
type: 'feature'
created: '2026-09-20'
status: 'done'
baseline_revision: '5e70a51cc1'
final_revision: 'pending — the merge commit of PR #1553'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md
  - src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** As the maintainer of the instruction surface, I want `test_instruction_surface_parity.py` to fail on a `TODO:` / `FIXME:` / "not yet landed" line between the `bmad:context` markers, So that a decision without a Story cannot sit in the block as a line every session pays for (found 2026-09-20: two such lines since 2026-09-04).

**Approach:** one meta-test over the text between `<!-- bmad:context -->` and `<!-- /bmad:context -->` plus a planted-fixture self-test; nothing outside the markers is in scope; lands after (or with) steward Story 66.2, which retires the two lines it would red today.

Ledger key: `20-1-the-parity-meta-test-reds-a-todo-inside-the-managed-block`.
Ledger status (do not edit the ledger): `done`.

### Living CAP citations

- `spec-pyforge-scribe` CAP-30; cross-project: `spec-pyforge-steward` spec-pyforge-steward:CAP-154 (Story 66.2) retires the two standing lines.

## Acceptance Criteria

- Given a planted `TODO:` line between the markers, When the meta-test runs, Then it fails naming the line.
- The live block passes once steward 66.2 has landed; TODO text outside the markers never fails it.

## Boundaries & Constraints

- `src/platform`'s `platform-ci` lane and `platform-ci-local` stay untouched; this story is about the ten `pyforge-*` packages and the repo's hooks.
- The CI lane and the `pr-preflight` leg call the SAME pixi tasks — never a second invocation that can drift.
- Only `pyforge-guild` exists at runtime (spec-pyforge-steward:CAP-152): every new task lives in `guild-tasks` and runs from `-e pyforge-guild`.
- `pixi.toml` is shared surface: regenerate `environment.yaml`, run `pyforge-station-tests` before pushing.

## Surface

- `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary checkout's copy of this file).

**Manual checks:**
- Plant `TODO: x` inside the block in a tmp copy → red, line named; the same text below the closing marker → green.

</intent-contract>

## Review Triage Log

### 2026-09-20 — hand-driven pass (operator: "we implement and do this now")
  - `[medium]` `[patch]` `test_managed_block_carries_no_todo_or_not_yet_landed_line` + `test_aspiration_guard_reads_only_between_the_markers` appended to `test_instruction_surface_parity.py`; scope is the text between the markers only. Red before steward 66.2's splice (it named exactly the two 2026-09-04 lines), green after.

## Auto Run Result

**Status:** done
**Summary:** a `TODO:` / `FIXME:` / "not yet landed" line inside `AGENTS.md`'s managed block fails the parity meta-test naming the line; outside the markers it is ignored.
**Verification:** `test_instruction_surface_parity.py` 25 passed (the guard red on the live block before 66.2's retirement, green after; planted-fixture self-test).
**Files changed:** `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py`.
**Residual risks:** none.
**Follow-up review recommendation:** false
