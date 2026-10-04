---
title: "83.21: Landing finalize writes the epic roll-ups the sync writes"
type: 'fix'
created: '2026-10-04'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py
  - scripts/promote_sprint_status.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the landing finalize writes the tracked ledger's `epic-N` rows from the Tier-3 feed verbatim, so a stale feed epic row overwrites the correct roll-up.

- **Where it happens:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py`, in the sprint-ledger promotion (around :1500), sets `working = promote_mod.render(project_key, src_rel, incoming)` from the parsed feed. It never calls `promote_mod.apply_epic_rollups`, which `sprint-ledger-sync` applies to every write (`scripts/promote_sprint_status.py`, since Story 28.24). After that, `render_ledger_advancements` promotes story rows to `done` without recomputing their epics.
- **Why the feed's epic rows are stale:** the sync writes roll-ups into the twin only, never into the feed. So the feed's epic rows lag behind the twin.
- **Seen on 2026-10-04:** doctor 41.5's landing (`b9869e5c6d`, after #1826) moved `epic-41` from `in-progress` to `backlog`, while 41.1 and 41.5 are `done`.
- **Seen on 2026-10-03:** three landing promotions (`1be676d263`, `fd328844d6`, `cc137c9faa`) dropped done `epic-66`, `epic-35` and `epic-17` to `backlog`. `ledger-regression` turned main's Detectors red on each push.
- **Still exposed:** on 2026-10-04 two more feeds held stale epic rows that the next landing would have copied, marshal `epic-85` and mason `epic-27`. Both were aligned by hand.

**Approach:** the finalize promotion writes the statuses it publishes through `apply_epic_rollups`, after the feed sync and after the story advancements, so that its twin matches what `sprint-ledger-sync` would write for the same statuses. Keep one roll-up, the sync's. If the module cannot be loaded, finalize must not write epic rows it could not compute: it leaves the twin's own epic rows as they are and journals a WARN.

Ledger key: `83-21-landing-finalize-writes-the-epic-roll-ups-the-sync-writes`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- Story 79.1 (a landing promotes the story's feed row, tracked spec and ledger twin) and Story 28.24 (the sync's roll-up). This is a defect of shipped behaviour, so it mints no new CAP. Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.

## Acceptance Criteria

- Given a feed whose `epic-9` row reads `backlog` while its stories read `done` and `in-progress` When the landing finalize promotes the ledger Then the twin's `epic-9` reads `in-progress`, the value `sprint-ledger-sync` writes; a real-git fixture test pins it, and removing the roll-up fails the test (mutation)
- Given the last open story of `epic-9` promoted to `done` by the finalize When the twin is written Then `epic-9` reads `done`
- Given a done epic with all stories done and a stale feed row `epic-9: backlog` When the finalize runs Then the twin keeps `epic-9: done`, and `ledger-regression` over the promotion commit reports `ok`
- Given the promotion module cannot be loaded When the finalize runs Then it writes no epic row it did not compute, and journals a WARN
- Given the replayed inputs of `b9869e5c6d` (doctor 41.5) When the fixed finalize runs Then `epic-41` reads `in-progress`

## Boundaries & Constraints

**Always:**
- Use the sync's own `apply_epic_rollups`, never a second roll-up rule.
- Run the roll-up on the final statuses, after the story advancements.

**Never:**
- Never change the sync's roll-up.
- Never relax `ledger-regression` to hide a bad roll-up.
- Never write the feed's epic rows from the twin here. The feed stays the intent record (Story 79.1).

</intent-contract>

## Binding

- Parent: Story 79.1 and the 2026-10-04 doctor 41.5 landing.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (finalize roll-up) entry.
- Epic: Epic 83.
- Ledger key: `83-21-landing-finalize-writes-the-epic-roll-ups-the-sync-writes`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Minted 2026-10-04 on the operator's standing direction to keep moving: found by this session while landing doctor 41.5.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- 2026-10-04: build complete (hand-built on `land/pyforge-marshal-83-21`), ready for an independent review. No review has run yet.
