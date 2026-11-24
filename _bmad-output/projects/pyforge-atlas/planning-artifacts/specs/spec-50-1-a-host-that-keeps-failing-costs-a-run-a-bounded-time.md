---
title: '50.1: A host that keeps failing costs a run a bounded time'
type: 'fix'
created: '2026-11-22'
status: 'done'
story: 50-1-a-host-that-keeps-failing-costs-a-run-a-bounded-time
spec: spec-pyforge-atlas
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/rate_limit.py'
  - 'src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/vcs_sources.py'
  - 'src/shared/packages/pyforge-atlas/tests/unit/datasets/test_failure_budget.py'
  - 'src/shared/packages/pyforge-atlas/conf/base/catalog.yml'
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - docs/dreams/pyforge-atlas.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The `vizro` job of `kedro-viz-publish.yml` was cancelled at its 240-minute limit on five runs in a row (2026-11-02 twice, 2026-11-09, 2026-11-13, 2026-11-16; e.g. run 43809671038), each time silent after `Saving data to vcs_gitlab_api_raw (VcsHostSeedDataset)`. The same refresh took 3 min 14 s on 2026-10-26 (run 40274605430). So the live site still serves the 2026-10-26 Vizro export. With `pyforge.atlas.live_vcs_universe` on, `VcsHostSeedDataset.load_many` asks two URLs a project, each retried three times, each attempt waiting its 20 s timeout or a `Retry-After` of up to 60 s: a host that fails every request for a transient cause costs up to eight minutes a project, with no limit and no line logged. The registries' loop has the same shape.

**Approach:** A `FailureBudget` (`rate_limit.py`), fresh per `load_many`, with three limits, each of which stops the run for that host (`HostUnavailable`): the seconds spent on requests that failed for a transient cause even after their retries (their attempts and the waits between them; 300 s), the count of such requests in a row (five), and the run's wall clock, checked between identifiers, for a host that answers slowly and fails nothing (1800 s). A request that answers in the end costs nothing, and a refusal resets the count. One loop (`_BudgetedRefresh._run`) serves `VcsHostSeedDataset` and `RegistryUpstreamDataset`: it logs how many it asks, a progress line a minute, and the stop with its reason; on a stop it persists what it got, leaves every row it did not reach or that failed for the stopping cause at its last-good value, and marks the store stale. `save` treats a stale store as due, so the next run asks again whatever the store's age. The eight registry entries take legacy Phase L's 20 s request timeout (the default is 900 s). Both datasets take the limits and a clock as constructor arguments; the defaults apply with no other catalog edit.

Ledger key: `50-1-a-host-that-keeps-failing-costs-a-run-a-bounded-time`.

### Living CAP citations

- spec-pyforge-atlas CAP-64, CAP-65 (realized, no text change); FR-72 ← CAP-64; FR-73 ← CAP-65; AD-13.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep every request, credential rule and endpoint of Stories 35.4 and 35.5 as it is.

**Never:**
- Never count a refusal (a 404, a refused redirect) against the budget.
- Never overwrite a row the run did not reach, and never clear a staleness marker on a stopped run.
- Never use the network in a test: an injected fetcher, sleep and clock.

## Acceptance Criteria

**Given** the public data build ran into its 240-minute limit on five runs, silent inside `vcs_gitlab_api_raw`'s refresh, because a host that fails every request for a transient cause costs two URLs times four attempts times up to 60 s a project with no limit and no line logged
**When** a host or registry refresh spends 300 s on failed requests, or five requests in a row fail after their retries
**Then** the host is not asked again in that run; what the run got is persisted, the rows it never reached keep their last-good values, the store is marked stale with the reason, and the log names the host, how many were asked and why it stopped; a refusal uses none of the budget, a host that recovers is asked to the end, and each run starts with a fresh budget
**And** atlas's package half passes, with a test that replays the stall (every request a 429 with `Retry-After: 60`, 300 projects) and fails when the run is not stopped inside the budget

- **AC1 — The budget's tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/unit/datasets/test_failure_budget.py -q
  ```

- **AC2 — Atlas's package half passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-atlas pyforge-atlas-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-atlas CAP-64, CAP-65 (realized, no text change); FR-72 ← CAP-64; FR-73 ← CAP-65; AD-13.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the second 2026-11-22 entry; operator, 2026-11-22: "Do this task here: Fix the stalled Vizro dashboard export job".
- Epic: Epic 50, minted with this story.
- Ledger key: `50-1-a-host-that-keeps-failing-costs-a-run-a-bounded-time` (`done`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."50"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

**Not verified here:** what the runner's requests to GitLab meet (five cancelled runs log nothing inside the refresh; from a laptop the same code answers in under half a second a project), and that the `vizro` job then finishes inside its limit. Both can only be read from the first run of `kedro-viz-publish.yml` with this change: its log will carry `gitlab: asking for N project(s)` and either the summary line or `gitlab unavailable this run: <reason>`.

## Review record (2026-11-22)

Independent review of the staged diff against this spec: pass with fixes, all applied. A host that answers slowly
(failing nothing) and a read that hangs were not bounded: the run now has a wall-clock deadline, and a progress line a
minute. A registry could cost an hour before the budget was consulted: the eight registry entries take a 20 s request
timeout. A stopped run that got some rows made the store look fresh, and the next run cleared its marker unasked:
`save` treats a stale store as due. A row that failed for the stopping cause was written over its last-good value: a
stopped run now persists only rows with a version or a refusal. A host that waits out a 429 now and then was stopped:
a request that answers in the end costs nothing. The budget is passed as an argument, never kept on the dataset.

**Limits that stand:** the wall-clock deadline is checked between identifiers, so one request that never returns at
all (no read for longer than its timeout is still bounded by the timeout; a DNS lookup is not) can outlast it; the
time the rate limiter waits is charged on the release-then-tag path only.
