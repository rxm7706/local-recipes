---
title: 'Idle backoff'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: true
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** Story 4.1's `watch.watch` polls every watched deck at one fixed, clamped `interval`
forever, even a deck that has been silent for hours or days. That burns API calls and rate-limit
budget for no operator-visible benefit -- a long-idle deck deserves a lazier poll cadence than an
actively-edited one.

**Approach:** Extend `watch.py`'s per-deck state with an idle-poll counter. Every truly-idle poll (the
steady-state branch of Story 4.1's debounce -- no candidate etag pending, and the poll came back
unchanged) increments it; once it reaches `IDLE_BACKOFF_THRESHOLD` (10), the deck's own poll interval
doubles (capped at `IDLE_BACKOFF_CAP`, 10 minutes) and the counter resets to keep accumulating toward
the next doubling. Any detected change -- a new candidate etag seen, or a pull actually firing --
resets the interval straight back to `DEFAULT_POLL_INTERVAL` (60s) and the idle counter to 0, so an
active deck never stays throttled once it starts moving again.

## Boundaries & Constraints

**Always:**
- The idle counter (`_DeckWatch.idle_streak`) increments ONLY on the truly-idle branch of
  `_poll_deck` -- no pending candidate, poll unchanged. A poll that is *settling* a real edit (a
  pending candidate, poll unchanged, which triggers a pull) is activity, not idleness, and must never
  increment this counter.
- At `idle_streak >= IDLE_BACKOFF_THRESHOLD`: `deck.interval = min(deck.interval * 2,
  IDLE_BACKOFF_CAP)`, then `idle_streak` resets to 0 (not left at the threshold) so backoff can
  continue compounding on the next 10 idle polls, not fire every single poll thereafter.
- Every branch that represents "a change happened" (a fresh candidate etag recorded, OR a pull
  firing) resets `deck.interval` to `DEFAULT_POLL_INTERVAL` and `deck.idle_streak` to 0 -- literally,
  per the AC's own wording ("resets to the 60s default"), not to whatever custom `interval` the
  caller originally requested.
- `WatchEvent` gains a `"backoff"` kind, reported when a doubling happens, alongside the existing
  `"idle"`/`"settling"`/`"pulled"` kinds from Story 4.1.
- Backoff is strictly per-deck: `watch()`'s existing due-time scheduling (Story 4.1) already treats
  each deck's `interval` independently, so a backed-off deck simply becomes less frequently due while
  every other watched deck's own schedule is unaffected.

**Block If:** N/A -- no spike, no live gate.

**Never:**
- No change to the debounce state machine itself (Story 4.1's `pending_etag`/`confirmed_etag` logic
  is untouched) -- this story only adds a counter and an interval mutation alongside it.
- No live MCP call anywhere in this package's own test suite -- same fake-transport/fake-pull
  convention as Story 4.1.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 10th consecutive idle poll | `idle_streak` reaches `IDLE_BACKOFF_THRESHOLD` | `interval` doubles (60 -> 120); `on_event` reports `"backoff"`; counter resets to 0 | No error |
| Repeated backoff | idle polls continue accumulating past 10, 20, 30, 40, 50 | 60 -> 120 -> 240 -> 480 -> 600 (capped) -> 600 | No error |
| A change interrupts a backed-off deck | a candidate etag is seen, or a pull fires, after `interval` had grown | `interval` resets to `DEFAULT_POLL_INTERVAL` (60.0); `idle_streak` resets to 0 | No error |
| Fewer than 10 idle polls | 1-9 consecutive idle polls | `interval` unchanged; every event is `"idle"` | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/watch.py` -- edit -- `IDLE_BACKOFF_THRESHOLD`,
  `IDLE_BACKOFF_CAP` module constants; `_DeckWatch.idle_streak` field; `_poll_deck`'s idle/settling/
  pulled branches all gain the counter increment/reset + interval reset/doubling logic; `WatchEvent`'s
  `kind` docstring comment gains `"backoff"`.
- `src/shared/packages/pyforge-herald/tests/test_watch.py` -- edit -- three new tests:
  `test_ten_consecutive_unchanged_polls_double_the_interval`,
  `test_idle_backoff_never_exceeds_the_ten_minute_cap`,
  `test_a_detected_change_resets_the_interval_to_the_default`.

## Design Notes

**Judgment call: reset always lands on `DEFAULT_POLL_INTERVAL`, never the caller's own requested
`interval`.** The AC's literal text is "resets to the 60s default on the next cycle," not "resets to
its own baseline." A caller who requested `--interval 90` and later backs off to 180 would, on this
story's reading, reset to 60 (not 90) once activity resumes -- a narrower, more conservative interval
than the caller's own choice, which is the safer direction to err in (more responsive after an edit,
never less). Recorded explicitly because the alternative reading (reset to the caller's own clamped
starting interval) is equally defensible and was rejected only because the AC's wording is unambiguous
about the literal value.

**Judgment call: the counter resets to 0, not `IDLE_BACKOFF_THRESHOLD - 1`, after a doubling.**
Resetting fully means the NEXT doubling also needs 10 full idle polls, giving a clean geometric
progression (10, 20, 30, ... polls to reach each successive doubling) rather than a doubling every
single poll once the threshold is first crossed. This matches the AC's "~10 consecutive... polls" for
every subsequent doubling too, not just the first.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- full suite green. Baseline before this
  story: 490 passed, 2 skipped (Story 4.1). After this story: 493 passed, 2 skipped (+3).

**Deferred live-MCP proof:** none beyond Story 4.1's own deferred proof -- this story adds no new
transport call, only local interval bookkeeping around the same `read_file` poll.

## Spec Change Log

## Review Triage Log

### 2026-08-07 — Self-review pass (single agent, no independent second reviewer)

Adversarial re-read after the suite was green, looking specifically for: the idle counter
incrementing on a settling (non-idle) poll, the doubling formula overshooting the cap, and the
reset-on-change branch missing one of its two trigger points (candidate-seen vs. pull-fired).

- `[none]` No defects found. Verified directly:
  - `_poll_deck`'s "settling" branch (a fresh candidate etag) and its "pulled" branch (the candidate
    held and a pull fired) both reset `idle_streak` to 0 and `interval` to `DEFAULT_POLL_INTERVAL` --
    neither ever increments the idle counter, since the increment line lives only inside the
    no-pending-candidate/unchanged branch.
  - `test_idle_backoff_never_exceeds_the_ten_minute_cap` runs 50 idle polls and asserts the exact
    backoff sequence `[120.0, 240.0, 480.0, 600.0, 600.0]` -- `min(deck.interval * 2,
    IDLE_BACKOFF_CAP)` is exercised past the cap twice (4th and 5th doublings), not just once.
  - `test_a_detected_change_resets_the_interval_to_the_default` runs a deck through one full backoff
    (10 idle polls -> 120s) then a settle-then-pull sequence, asserting the FINAL event's interval is
    back to 60.0 -- covers the reset happening on the "pulled" branch specifically, the harder of the
    two reset triggers to get right (it is nested inside the pending-candidate/unchanged path, not the
    simpler top-level "changed" branch).
- `addressed_findings`: 0. `followup_review_recommended: true` retained per this repo's own practice
  for a story mutating shared per-deck scheduling state with no independent second reviewer yet.

**Verification:** `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 493 passed, 2 skipped.

### 2026-08-08 -- Adversarial review pass (Blind Hunter + Edge Case Hunter, no shared context)

- `[medium]` `[patch]` **`_clamp_interval` only enforced the 30s floor, not the 600s
  `IDLE_BACKOFF_CAP` ceiling.** `herald deck watch --interval 100000` was honored literally for the
  first ~9 idle polls (recorded sleep sequence `[100000.0]*9 + [600.0]` in the reviewer's probe) --
  the reactive backoff logic only caught up once `idle_streak` crossed `IDLE_BACKOFF_THRESHOLD`. A
  real edit landing during that window went undetected for `interval * IDLE_BACKOFF_THRESHOLD`
  seconds (~11.5 days at that interval) before self-correcting to the cap -- a silent footgun for a
  typo'd `--interval` value, not a crash. Fixed: `_clamp_interval` now clamps to
  `[MIN_POLL_INTERVAL, IDLE_BACKOFF_CAP]`, applied once at loop entry (same call site as the
  existing floor clamp). New regression test:
  `test_interval_above_the_idle_backoff_cap_is_clamped_to_600s`.
- `addressed_findings`: 1 (medium). No `intent_gap`, no `bad_spec`, no `defer`, no `reject`.

**Re-verification (2026-08-08, after this patch):** `pixi run --frozen -e pyforge-herald
pyforge-herald-test` -- 496 passed, 2 skipped.

**Follow-up review recommendation:** none outstanding for this story.
