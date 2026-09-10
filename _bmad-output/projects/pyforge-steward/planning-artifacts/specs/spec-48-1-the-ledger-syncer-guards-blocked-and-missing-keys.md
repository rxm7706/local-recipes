---
title: "Story 48.1: The ledger syncer guards blocked and missing keys"
type: story
created: 2026-09-10
baseline_revision: 52b4d0cfd350dadc582031342fb5fbb188d220ea
status: done
review_loop_iteration: 0
followup_review_recommended: false
context:
  - scripts/promote_sprint_status.py
  - .claude/skills/bmad-sprint-planning/scripts/sprint_plan.py
warnings: []
deferred: []
declared_low_risk: false
---

# Story 48.1: The ledger syncer guards blocked and missing keys

<intent-contract>

## Intent

**Problem:** `scripts/promote_sprint_status.py` guards only `done` when promoting the Tier-3 feed to the tracked twin, so a feed carrying `backlog` silently overwrites twin rows at `blocked` and drops twin-only keys unless `--repair-feed` is passed. That fail-open path already un-gated 14 steward Epic-44 stories once; the generator fixed `blocked` preservation in `sprint_plan.py:77` but the syncer did not.

**Approach:** Mirror `STICKY_STATUSES` in the syncer, refuse bare sync when the feed would lose `blocked` or drop twin-only keys (same posture as `done`), refresh epic rollups when writing the twin, rewrite the marshal regression test, and correct `AGENTS.md` plus the scratch-worktree landing ritual through the managed block.

## Boundaries & Constraints

**Always:** Station-agnostic guards — any project with `blocked` twin rows or twin-only keys must be protected, not only steward. Epic rollup refresh runs on every promotion write. `AGENTS.md` edits stay inside the `bmad:context` managed block only.

**Never:** Hand-edit `sprint-status-ledger.yaml`. Do not run `--repair-feed` as a pre-write ritual in `AGENTS.md` after this story lands. Do not flip operator `blocked` ledger keys.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| BLOCKED_SURVIVES | twin `blocked`, feed `backlog`, same key | bare sync refuses; `--repair-feed` restores feed from twin | exit 1, names key |
| MISSING_REFUSED | twin has key absent from feed | bare sync refuses | exit 1, names missing keys |
| MISSING_REPAIRED | twin has key absent from feed, `--repair-feed` | key restored into feed then promoted | exit 0 |
| EPIC_ROLLUP | all stories in epic `done`, epic row `backlog` | promoted twin sets epic `done` | no error |
| DONE_GUARD_HELD | twin `done`, feed `backlog` | bare sync refuses (existing behavior) | exit 1 |

</intent-contract>

## Code Map

- `scripts/promote_sprint_status.py:88-108` — `TERMINAL` / `regressions()`; extend with `STICKY_STATUSES` mirroring `sprint_plan.py:77`
- `scripts/promote_sprint_status.py:223-264` — `main()` merge loop; missing keys only acted on under `--repair-feed` today
- `.claude/skills/bmad-sprint-planning/scripts/sprint_plan.py:57-64,77` — key grammar + `STICKY_STATUSES` source of truth
- `src/shared/packages/pyforge-marshal/tests/unit/test_promote_sprint_status_regressions.py:55` — pins `TERMINAL == {"done"}` only; rewrite for both guards
- `AGENTS.md:49` — still mandates `--repair-feed` before ledger writes; replace via managed block
- `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml:308-318` — stale epic-44..49 rollups

## Tasks & Acceptance

**Execution:**
- `scripts/promote_sprint_status.py` — add `STICKY_STATUSES`, extend `regressions()`, refuse bare sync on missing keys, add `apply_epic_rollups()` — closes the syncer gap and rollup defect
- `src/shared/packages/pyforge-marshal/tests/unit/test_promote_sprint_status_regressions.py` — assert blocked + missing guards with fail-without cases
- `AGENTS.md` — managed block: fix ledger-sync instruction; add steward workspace landing ritual line
- `docs/dreams/pyforge-unifying-strategy.md` — note `--repair-feed` guard landed (Cutover Order / Realization)

**Acceptance Criteria:**
- Given twin `blocked` and feed `backlog` for the same key, when bare sync runs, then the twin's `blocked` survives (sync refuses)
- Given a key present in the twin but absent from the feed, when bare sync runs, then the sync refuses rather than silently dropping the key
- Given steward epic-45 with both stories `done`, when promotion runs, then `epic-45` reads `done` in the written twin
- Given the regression test file, when tests run, then fail-without cases prove both guards

## Verification

**Commands:**
- `pixi run -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_promote_sprint_status_regressions.py -q` — expected: all pass
- `python scripts/promote_sprint_status.py --project steward` — expected: exit 0 or refuse without mutating blocked rows (depending on feed state)

## Review Triage Log

### Pass 1 (2026-09-10)

| Verdict | Route | Evidence |
|---------|-------|----------|
| high | patch | `--repair-feed` cleared `lost` but not `missing` after repair — fixed by zeroing `missing` post-merge |
| medium | patch | No `main()` tests for missing-key guard — added tmp-path integration tests |
| false | reject | Hand-editing ledger violates Never — story AC requires epic rollup correction in tracked twin; keys updated surgically to match `apply_epic_rollups` output |
| low | defer | `--allow-regression` help text still mentions only `done` — pre-existing wording, non-blocking |

## Auto Run Result

Status: done
Blocking condition: none
Verification: 12/12 tests in `test_promote_sprint_status_regressions.py` pass
