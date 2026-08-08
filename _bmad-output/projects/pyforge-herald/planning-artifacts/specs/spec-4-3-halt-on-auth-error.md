---
title: 'Halt on auth error'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** Stories 4.1-4.2 built the poll/debounce/backoff loop. Neither story added or needed an
explicit halt-on-auth-error mechanism -- `watch.py` never wraps a poll or a pull in `try`/`except`, so
an `AuthError` (a `TransportError` subclass Story 1.2 already defined, raised by `McpTransport` on a
rejected or expired credential) already propagates straight out of `watch()` un-retried, and
`cli.dispatch` (AD-6's sole `HeraldError` catch point, unchanged since Epic 1) already reports it
structurally on stderr with the mapped non-zero exit code. Nothing was broken; nothing needed fixing.
What was missing was proof: no test in this package exercised an `AuthError` arising specifically
*during a watch loop with multiple decks*, and no test confirmed the CLI's own reporting path for it.

**Approach:** Add the explicit tests this story's ACs ask for -- both at `watch.py`'s own level (an
`AuthError` on one watched deck's poll halts every deck, with no retry of the failed poll) and at the
CLI level (`herald deck watch` surfaces it with `dispatch`'s usual one-line stderr message and exit
code 4). No production code changes: this is the "verify existing guidance held" shape this repo's own
retro convention already anticipates for a story whose behavior was already correct by construction.

## Boundaries & Constraints

**Always:**
- A `watch.py`-level test seeds two decks, makes the SECOND deck's poll raise `AuthError`, and asserts
  (a) `pytest.raises(AuthError)` around the `watch()` call, (b) the failing deck's `read_file` was
  called exactly once (no retry), and (c) the injected `pull` spy was never called (the halt happens
  before any pull could fire, since both decks are freshly idle).
- A `cli.py`-level test monkeypatches `watch_module.watch` to raise `AuthError`, asserts `cli.main`
  returns exit code 4 (`errors.exit_code_for`'s existing `TransportError` mapping -- no new entry
  needed, since `AuthError` is already one of its subclasses), asserts the fake `watch` was called
  exactly once (`dispatch` never retries the whole operation), and asserts the stderr line names both
  `AuthError` and the `/design-login` remediation text `AuthError`'s own message always carries
  (`errors.py`'s existing docstring guarantee, Story 1.2).
- No new exception type: `errors.py` already had `AuthError` (Story 1.2) with the correct
  `TransportError` ancestry and `exit_code_for` mapping (Story 1.4) -- verified, not re-implemented.

**Block If:** N/A -- no spike, no live gate.

**Never:**
- No `try`/`except AuthError` (or any `HeraldError`) added anywhere in `watch.py` -- adding one would
  be a regression against AD-6 (one catch point, `cli.dispatch`) and against this exact AC ("the loop
  does not attempt a retry of the failed poll before halting" -- a catch-and-retry, even a single
  retry, would violate this).
- No live MCP call anywhere in this package's own test suite -- same fake-transport convention as
  Stories 4.1-4.2.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Second watched deck's poll raises `AuthError` | two seeded decks, `fail_after=1` on the transport | `watch()` raises `AuthError`; the failing deck's `read_file` called exactly once; `pull` never called | `AuthError` (a `TransportError`/`HeraldError`) |
| CLI: `watch_module.watch` raises `AuthError` | `herald deck watch <slug>` | one stderr line naming `AuthError` + `/design-login`; exit code 4 | per `errors.exit_code_for` |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/tests/test_watch.py` -- edit -- one new test,
  `test_auth_error_halts_every_watched_deck_with_no_retry`.
- `src/shared/packages/pyforge-herald/tests/test_cli_watch.py` -- edit -- one new test,
  `test_deck_watch_auth_error_halts_and_reports_structurally_with_nonzero_exit`.
- No production code touched: `watch.py` (Stories 4.1-4.2) and `errors.py`/`cli.py` (Epic 1) already
  had every piece this story needed.

## Design Notes

**Why this story has no production diff.** The four collaborating pieces already existed before this
story started: (1) `errors.AuthError` (Story 1.2) is a `TransportError` subclass carrying the
`/design-login` remediation in its own message. (2) `errors.exit_code_for` (Story 1.4) already maps
every `TransportError` (including `AuthError`, via `isinstance`) to exit code 4. (3) `cli.dispatch`
(Story 1.4, unchanged since) is the sole `HeraldError` catch point and already renders exactly one
structured stderr line per AD-6, with no retry logic anywhere in it. (4) `watch.py` (Stories 4.1-4.2)
never introduced a `try`/`except` around a poll or a pull -- by omission, not by a deliberate "catch
and re-raise" pattern, any exception (including `AuthError`) was already guaranteed to propagate
unmodified and un-retried the moment `watch.py` first existed. This story's only job was proving that
chain holds together for the specific "auth error mid-multi-deck-loop" scenario the ACs describe, and
recording it as an explicit regression-tested guarantee rather than an implicit, untested one.

**Judgment call: the watch-level test uses `fail_after=1` on the SECOND deck, not the first.** This
proves the halt is not simply "the loop never got past deck one" (which a bug could satisfy trivially)
-- deck "alpha" is genuinely polled successfully once, and only deck "beta"'s poll fails, which is a
stronger proof that the halt is a real propagation through the loop's scheduling, not an artifact of
which deck happens to run first.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- full suite green. Baseline before this
  story: 493 passed, 2 skipped (Story 4.2). After this story: 495 passed, 2 skipped (+2). Matches the
  original combined Epic 4 total exactly, confirming no test was lost across the three-story split.

**Deferred live-MCP proof:** none beyond Stories 4.1-4.2's own deferred proof. A genuine live auth
failure (an expired `/design-login` credential against the real endpoint) is impractical to provoke
deliberately and is already covered at the unit level by `test_mcp_transport.py`'s existing
`AuthError`-raising tests from Epic 1 (unchanged, out of this story's scope).

## Spec Change Log

## Review Triage Log

### 2026-08-07 — Self-review pass (single agent, no independent second reviewer)

Adversarial re-read looking specifically for: a hidden retry (e.g. a bare `except Exception: continue`
anywhere in the polling loop that would swallow the `AuthError` instead of propagating it), and the
CLI-level test asserting the fake `watch` was called exactly once (proving `dispatch` itself never
retries).

- `[none]` No defects found. `grep -n "except" src/shared/packages/pyforge-herald/src/pyforge/herald/watch.py`
  returns no matches at all -- the loop's `while True:` body has no exception handling whatsoever, so
  every exception any poll or pull call raises propagates immediately and unmodified. `calls == [1]`
  in the CLI test directly proves `dispatch` did not re-invoke the fake `watch`.
- `addressed_findings`: 0. `followup_review_recommended: false` -- unlike Stories 4.1/4.2, this story
  adds no production code and no new state-mutation surface; the two new tests are narrow, and the
  guarantee they assert was already structurally forced by the absence of any `except` clause, not by
  new logic that could regress independently.

**Verification:** `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 495 passed, 2 skipped.

## Epic 4 close-out note

This completes Epic 4 ("Stay in sync automatically") -- `herald deck watch` now polls, debounces,
backs off when idle, and halts cleanly on an auth error, wired through `cli.py`'s existing
`dispatch`/`bridge.run` composition exactly like every other deck subcommand. Per this repo's own
`CLAUDE.md` (BMAD <-> conda-forge-expert integration, Rule 2), a retro is owed only for BMAD efforts
that did conda-forge (`recipes/`, `conda-forge-expert` skill) work -- this epic touched neither, so
that retro does not apply here. The three per-story specs in this directory (4.1, 4.2, 4.3) are this
epic's durable record; no consolidated epic-level spec is authored separately (per this repo's "one
canonical planning artifact" convention -- the per-story specs already are that record).
