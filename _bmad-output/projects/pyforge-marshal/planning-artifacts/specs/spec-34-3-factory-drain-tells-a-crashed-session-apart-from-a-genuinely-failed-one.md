---
title: '`factory drain` tells a crashed session apart from a genuinely failed one'
type: 'feature'
created: '2026-09-10'
status: 'done'
baseline_revision: '64ea7659d022c4d2c97938c6ac39e936d65c27c4'
review_loop_iteration: 1
followup_review_recommended: false
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** When a dispatch session dies (crash, kill, or a real failure), the run is recorded
with a terminal verdict (`failed`, `stopped_externally`) that `factory drain` treats as
permanently blocked — "never auto-retried, never forced past" by design, correct when the story
genuinely failed. But an environment crash is not a story failure, and drain has no way to tell
the two apart. Every crash this session required the operator to notice the block, bypass it with
a manual single-story `factory dispatch` (which does retry cleanly), and know that trick exists.
There is no sanctioned "this was infrastructure, not the story — retry" path through `factory
drain` itself.

**Approach:** When `factory drain` encounters a blocked story, classify the block using the
already-computed facts `dispatch-resume`'s own "no live dispatch to recover" check surfaces (git
progress, review/verify-cycle evidence). A block with ZERO git progress and ZERO
review/verify-cycle evidence is classified **environment**; anything else stays **story**. Sanction
a retry path for environment-classified blocks only, leaving the existing manual-override
behavior for genuine story failures completely unchanged.

## Boundaries & Constraints

**Always:**
- A blocked story whose last recorded verdict shows zero git progress AND zero
  review/verify-cycle evidence is classified `environment`.
- Environment-classified blocks get a sanctioned retry path (`--mode skip_on_blocked`'s existing
  escape hatch, or a new explicit `--retry-environment-blocks` flag).

**Never:**
- Never weakens `factory drain`'s existing "never-auto-retried, never-forced-past" guarantee for
  a story block that DOES show real git progress, a failed verify run, or an escalation — those
  stay `story`-classified and still require the existing manual override, unchanged.
- Never auto-retries an environment-classified block silently — the retry path is still an
  explicit, named action the operator or a chained campaign opts into.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Live reproduction (the motivating case) | A dispatch session crashes before doing anything (`completion_verdict: stopped_externally`, zero git progress) | Classified `environment`; eligible for the new retry path | n/a |
| Genuine failure | A dispatch session runs, makes real git progress, and fails verify | Classified `story`; existing manual-override-only behavior, unchanged | n/a |
| Escalation | A dispatch session pauses on an unresolved escalation | Classified `story`; existing behavior, unchanged | n/a |
| Retry path used | Operator/campaign retries an environment-classified block | Story becomes eligible for a fresh dispatch, same as today's manual bypass | n/a |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py` — blocked-story classification logic.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` — `dispatch-resume`'s own `stopped_externally`/`completion_verdict` facts, already computed, now also feeding this classification.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_fleet*.py` — new fixtures.

## Tasks & Acceptance

**Execution:**
- `feature` — classify a blocked story as `environment` when its last recorded verdict shows zero git progress and zero review/verify-cycle evidence, `story` otherwise.
- `feature` — sanction a retry path for `environment`-classified blocks only (extend `--mode skip_on_blocked` or add `--retry-environment-blocks`).
- `feature` — leave `story`-classified blocks' existing manual-override-only behavior completely unchanged.
- `feature` — add a fixture reproducing a crashed-before-any-progress run and a fixture reproducing a real verify failure, asserting only the crashed one is eligible for the new retry path.

**Acceptance Criteria:**
- Given every terminal crash this session left the story permanently blocked in `factory drain`'s eyes with the only recovery path being an operator manually bypassing the block via single-story `factory dispatch`, when `factory drain` encounters a blocked story whose last recorded verdict shows zero git progress and zero review/verify-cycle evidence, then it classifies the block as `environment` rather than `story`, and a sanctioned retry path clears only `environment`-classified blocks.
- A genuine story failure (real git progress, a failed verify run, an escalation) still requires the existing manual override, unchanged.
- A fixture reproduces one of each and asserts only the crashed one is eligible for the new retry path.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: full suite green, including the new crashed-vs-failed classification tests

## Spec Change Log

- 2026-09-10: added the missing `## Verification` -> `**Commands:**` section before dispatch, to avoid the `core.gate.check_spec_binding` (Story 2.7, MRS-GATE-010) refusal `spec-34-2`'s own dispatch run hit for the identical omission.

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 14 findings — high 0, medium 2, low 5, false 3, maybe-false 4
- findings:
  - `[medium]` `[patch]` Git gather errors defaulted to environment classification — fixed: unknown git progress forces STORY in `station_story_block_facts`
  - `[medium]` `[patch]` Escalation pause I/O matrix row untested — added `test_escalation_pause_is_story_block_and_not_skipped_under_skip_on_blocked`
  - `[low]` `[patch]` CLI `--retry-environment-blocks` wiring untested — added `test_retry_environment_blocks_cli_wiring_moves_past_crash`
  - `[low]` `[reject]` `leave_one` + flag untested — defer; same code path as drain_to_zero in `plan_station_queue`
  - `[low]` `[reject]` fleet-drain-playbook.md stale — documentation follow-up, not story scope
  - `[low]` `[reject]` Structured block class not in cycle JSON payloads — enhancement, not AC
  - `[low]` `[reject]` Misleading CLI help "also honored under skip_on_blocked" — acceptable; flag is additive for drain modes
  - `[false]` `[reject]` stopped_externally + zero progress scenario — CAP-2 yields FAILED for zero progress; covered by crash fixture
  - `[false]` `[reject]` No shared helper with dispatch-resume — spec intent satisfied via same journal/git facts, not shared function requirement
  - `[false]` `[reject]` skip_on_blocked narrowing breaks R4 reading — R3 matches spec Never clause; intentional behavior change
  - `[maybe-false]` `[defer]` Substring escalation heuristic too narrow — `"escalation"` in stop_reason matches live marshal markers; escalation fixture added
  - `[maybe-false]` `[defer]` Transient failures classified environment — pre-existing TRANSIENT short-circuit returns None before classification
  - `[maybe-false]` `[defer]` Harness-done follow replan with environment block — edge case; follow path passes retry flag
  - `[maybe-false]` `[defer]` Git-progress-only story block without verify journal — covered indirectly via progressed FakeVcs + terminal gate

## Auto Run Result

Status: done

**Summary:** `factory drain` now classifies derived blocks as `environment` (zero git progress, zero review/verify evidence) or `story` (everything else). Environment blocks skip only under explicit `--mode skip_on_blocked` or `--retry-environment-blocks`; story failures still halt the station.

**Files changed:**
- `dispatch_fleet.py` — `FleetBlockClass`, classification helpers, narrowed skip logic in `plan_station_queue`
- `cli/dispatch.py` — `station_story_block_facts`, `--retry-environment-blocks` flag, block-class plumbing through fleet cycle
- `test_dispatch_fleet.py` — unit + integration fixtures for crash vs verify-failure vs escalation

**Review:** 2 medium patches applied (git-error conservative STORY, escalation + CLI tests); 5 low rejected; 3 false; 4 deferred unverified.

**Verification:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 7764 passed, 12 deselected.

**Residual risks:** Operators who relied on `skip_on_blocked` skipping genuine story failures must use manual single-story dispatch instead (spec-intended). Playbook docs not updated in this story.
