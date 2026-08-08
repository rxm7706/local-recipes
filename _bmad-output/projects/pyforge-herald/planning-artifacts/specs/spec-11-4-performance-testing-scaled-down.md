---
title: 'Performance Testing, Scaled Down to the CLI-Testable Claims'
type: 'feature'
created: '2026-08-08'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** Epic 11's original Story 11.4 (`epics-with-stories.md` lines 969-975) specs
four ACs: "CLI commands <1s (95th percentile)," "web tabs <2s load (95th percentile),"
"archive search responsive," "no memory leaks during long sessions." Two of these
(CLI-command latency, archive search) have a real, honest scaled-down test in this
architecture. Two do not: there is no browser or server in this test suite to measure a
"web tab load" against (the dashboard is a static Vite bundle reading a pre-generated JSON
snapshot -- there is no live page to load in any test here), and `herald` is a one-shot CLI
process with no long-running session to leak memory across.

**Approach:** Test the two real bullets, honestly, at the boundary this architecture
actually has: seed 100 synthetic records per Moment directly via each module's own storage
functions (`progress.upsert`, `claims.create`+`claims.publish`, `notices.author_notice`) --
not through 100 CLI subprocess calls, which would measure process-spawn overhead instead of
the command itself -- then time `herald progress`/`herald success list`/`herald notice list`
(plus a filtered `success list --status published` variant, standing in for "archive search
responsive," since there is no separate archive-search surface beyond each Moment's own
listing filter) end to end via in-process `cli.main`, asserting each stays comfortably under
a 1-second budget. The other two bullets are left explicitly, honestly untested in this
story's docstring rather than invented against a fake proxy.

## Boundaries & Constraints

**Always:**
- 100 records per Moment (`RECORD_COUNT = 100`), matching the task's own "a moderately-sized
  local dataset (e.g. 100 synthetic records)" framing.
- Seeding calls each module's real public write path (`progress.upsert`,
  `claims.create`+`claims.publish`, `notices.author_notice`) directly, in-process -- not
  `cli.main` in a loop and not a subprocess per record. The *timed* portion of each test is
  only the single listing command under measurement, via `time.perf_counter()` around one
  `cli.main([...])` call.
- `TIME_BUDGET_SECONDS = 1.0` -- the AC's own number, applied as a hard ceiling (not a
  95th-percentile statistical claim, which would need many timed runs and a real
  distribution to be meaningful; a single generous-budget assertion is the honest scaled-down
  form of "fast enough that an operator never notices," the AC's actual intent).
- Every claim seeded for the Success timing tests is published (`claims.publish`, with
  `evidence.validate_for_publish` stubbed so seeding 100 of them never reaches
  `deny_network`) -- exercising the same code path (`claims.to_dict`'s per-entry
  `is_stale` computation) a real `--json` listing runs in production, not a shortcut that
  skips it.
- The docstring at the top of the test module states explicitly, for a future reader, which
  two of the original AC's four bullets are and are not covered here, and why -- so "not
  tested" reads as a documented decision, not an oversight.

**Block If:** N/A -- purely local, in-process; no network, no subprocess.

**Never:**
- No web-tab load-time test -- no browser/headless-page-load tooling is introduced into this
  package's test suite to fake one; see Design Notes.
- No memory-leak/long-session test -- `herald` has no long-running session anywhere in this
  architecture; a test asserting "no leak" would either be vacuously true (nothing to leak
  across, since the process exits after one command) or would have to synthesize a fictional
  "session" no real code path represents.
- No change to any storage module's public API to make seeding faster -- 100 sequential
  calls to each module's existing `create`/`upsert`/`author_notice` (each of which reads +
  rewrites its whole file, an already-documented O(n) cost per call in each module's own
  docstring) is fast enough at n=100 that optimizing the seed path would be solving a
  problem this story never actually hit.

## I/O & Edge-Case Matrix

| Scenario | Input | Expected | Notes |
|---|---|---|---|
| `herald progress --json` | 100 seeded records | 100 NDJSON lines, elapsed < 1.0s | |
| `herald success --json list` | 100 seeded, all published | 100 NDJSON lines, elapsed < 1.0s | |
| `herald notice --json list` | 100 seeded, all published | 100-entry JSON array, elapsed < 1.0s | |
| `herald success --json list --status published` | same 100 | 100 NDJSON lines, elapsed < 1.0s | stands in for "archive search responsive" |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/tests/test_performance_epic11.py` -- create -- the
  module docstring documenting all four original AC bullets' scaled-down disposition; seed
  helpers (`_seed_progress`, `_seed_claims`, `_seed_notices`); the four timed tests.

## Design Notes

**Judgment call: a hard 1.0s ceiling, not a 95th-percentile measurement.** The original AC's
"95th percentile" framing presumes a production traffic distribution this test suite has no
way to synthesize honestly -- a single local process, run once per test, has no percentile
to compute. A hard ceiling against a realistic (100-record) dataset is the scaled-down form
that still proves the actual property an operator cares about ("this command doesn't hang"),
without dressing up one sample as a statistical claim it isn't.

**Judgment call: "archive search responsive" reuses `success list --status`, not a new
search feature.** Neither `claims.py`, `progress.py`, nor `notices.py` has a concept of
"archive search" distinct from their existing `list_*` functions' own filter parameters
(`status`/`date_range`/`category`/`station`) -- there is no separate search index or
full-text query anywhere in this package. Timing a filtered listing call *is* timing the
only search-shaped surface that exists; inventing a new search feature to have something
more literally named "search" to time would be scope creep no other Story in Epic 11 (or
Epics 8-10) asked for.

**Judgment call: no headless-browser dependency added for the web-tab-load bullet.**
Considered and rejected: adding Playwright/Selenium (or similar) to this package's pixi
environment purely to fake a "page load" against a static Vite bundle with no server would
be exactly the kind of speculative infrastructure weight `evidence.py`'s own docstring
already argues against for a comparable case (adding a scheduler dependency for one weekly
check) -- and even if added, the "load time" it would measure (a bundler dev server's
cold-start, or a `file://` fetch) would not represent the AC's actual concern (a deployed
static site's real load time), so the investment would not even answer the question.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 740 passed, 2 skipped
  (whole-package total, immediately after this story landed).
- `ruff format --check` / `ruff check` -- clean.

**Manual checks:**
- `pytest tests/test_performance_epic11.py -q` in isolation -- 4 passed in well under a
  second combined (observed: 0.78s total for all four tests, including seeding).

## Spec Change Log

## Review Triage Log
