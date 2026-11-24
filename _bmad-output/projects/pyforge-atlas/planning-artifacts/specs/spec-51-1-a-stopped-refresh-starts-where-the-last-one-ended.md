---
title: '51.1: A stopped refresh starts where the last one ended'
type: 'fix'
created: '2026-11-22'
status: 'done'
story: 51-1-a-stopped-refresh-starts-where-the-last-one-ended
spec: spec-pyforge-atlas
difficulty: 'low'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/rate_limit.py'
  - 'src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/vcs_sources.py'
  - 'src/shared/packages/pyforge-atlas/tests/unit/datasets/test_stalest_first.py'
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - docs/dreams/pyforge-atlas.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The first public data build with Story 50.1 (run 45019765201) stopped GitLab's refresh as designed: `gitlab unavailable this run: HTTP 429; 361 s spent on failed requests (budget 300 s); finished 105 of 406`. Two things are left. `_BudgetedRefresh._run` asks the list in the order it is given, every run, so a run stopped at 105 refreshes the same 105 next time and the other 301 keep their old rows for as long as the host throttles. And the log names the 429 without what the host said about its limit, so the likely cause (the hosted runner's address, shared with other tenants: atlas sends at most 180 requests a minute against GitLab.com's 500 a minute for an address without a credential) cannot be read from a run.

**Approach:** The store file gains an `asked_at` column (epoch seconds): when the row was last asked for, whether or not the host answered. Before asking, `_run` orders the identifiers by it: those never asked first, then longest since asked first; asked in the same second, a row that holds a version goes before one that holds none, and the rest keep the order given. `load` still returns the three columns of `_VERSION_COLUMNS`. Every row a run writes carries the time. A row a stopped run asked and does not write (it failed for the stopping cause, or it is the one the stop interrupted) is marked too, by a row that writes over no value: a name the store holds keeps its version and error with the new time, a name it does not hold gets a row with no version and its error. A row the run did not reach keeps its old time. For the cause: a 429's rate-limit headers are read from the failed response as a fixed set of names (`RateLimit-Name`, `-Limit`, `-Observed`, `-Remaining`, `-Reset`, `Retry-After`) with values cut to plain characters, kept on the run's `FailureBudget`, logged once a run, and added to the reason of a stop a 429 caused, which the staleness marker records.

Ledger key: `51-1-a-stopped-refresh-starts-where-the-last-one-ended`.

### Living CAP citations

- spec-pyforge-atlas CAP-64, CAP-65 (realized, no text change); FR-72 ← CAP-64; FR-73 ← CAP-65; AD-13.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep every request, pace, budget, credential rule and endpoint of Stories 35.4, 35.5 and 50.1 as it is.

**Never:**
- Never add a column to what `load` returns.
- Never write a mark that a row was asked over a last-good value.
- Never write a host's header into the log or the marker as sent: a fixed set of names, values cut to plain characters and a fixed length.
- Never use the network in a test: an injected fetcher, sleep and clock.

## Acceptance Criteria

**Given** run 45019765201 stopped GitLab's refresh at 105 of 406 on HTTP 429, every run asks the same list in the same order, and the log does not carry what the host said about its limit
**When** a host or registry refresh runs
**Then** it asks the identifiers never asked first, then the rest longest since asked first (asked in the same second: a row with a version before one without, then the order given); every identifier it asks is marked with the time, in a column `load` never returns, and a mark writes over no last-good value; a row it did not reach keeps its old time; and a 429's rate-limit headers are logged once a run and added to the reason of a stop that a 429 caused, which the staleness marker records
**And** atlas's package half passes, with a test that stops a run part way twice and fails unless the second run asks the unreached identifiers before any the first run asked, and a test where three identifiers fail every time and the healthy ones are still reached

- **AC1 — The story's tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/unit/datasets/test_stalest_first.py src/shared/packages/pyforge-atlas/tests/unit/datasets/test_failure_budget.py -q
  ```

- **AC2 — Atlas's package half passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-atlas pyforge-atlas-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-atlas CAP-64, CAP-65 (realized, no text change); FR-72 ← CAP-64; FR-73 ← CAP-65; AD-13.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the third 2026-11-22 entry; operator, 2026-11-22: "Yes, start it".
- Epic: Epic 51, minted with this story.
- Ledger key: `51-1-a-stopped-refresh-starts-where-the-last-one-ended` (`done`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."51"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

**Not verified here:** that the hosted runner's shared address is the cause of the 429, and how many runs full coverage takes. Both can only be read from runs of `kedro-viz-publish.yml` with this change: a throttled run's log will carry `gitlab: the host limits requests: <headers>`.

## Review record (2026-11-22)

Independent review of the staged diff against this spec: pass with fixes, all applied but the two named below. The
first build marked only the rows it wrote, as `fetched_at`: an identifier that fails every time then had no time, was
first in every run, and three of them stopped each run before a healthy project was reached (confirmed by the
reviewer's script). The column is now `asked_at`, every identifier a run asks is marked, and a mark writes over no
value. A stop that a 503 caused quoted an earlier 429's headers: the headers join the reason of a 429 stop only. A
name that is not a string never matched its stored time: the order compares names as strings. Tests added for a
refusal's mark, a last-good value kept under a new mark, a stopped run with nothing to keep, and the identifiers that
fail every time.

**Limits that stand:** a run in which no identifier returns a version and none fails for a transient cause (every
answer a refusal) marks nothing, as before the story (AD-13: a batch with no version is not written), so its order
repeats. A `Retry-After` given as a date is logged with its spaces removed. The once-a-run line carries the first
thing the host said and the stop's reason the last. mypy does not run in atlas's environment: `lint-types` is its
check.
