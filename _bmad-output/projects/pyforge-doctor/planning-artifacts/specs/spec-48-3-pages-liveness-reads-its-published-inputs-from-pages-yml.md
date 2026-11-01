---
title: "48.3: pages-liveness reads its published inputs from pages.yml"
type: 'fix'
created: '2026-11-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-48-2-a-pages-deploy-more-than-a-day-behind-its-inputs-is-named-in-fleet-picture.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-doctor.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/pages_liveness.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_sources_pages_liveness.py
  - src/shared/packages/pyforge-doctor/tests/fixtures/pages_liveness/
  - .github/workflows/pages.yml
  - docs/governance/ci-surfaces.yaml
---

<intent-contract>

## Intent

**Problem:** CAP-91's `pages-liveness` source names a Pages deploy more than a day behind its inputs. At
`03a7aff5d9` three things the source and its capability say are no longer true, and one rule misses the stall it is
for:

- **The inputs are a hand copy.** `PUBLISHED_INPUTS`
  (`src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/pages_liveness.py:48-59`) lists ten pathspecs copied
  from the herald Dream's M1 list. `.github/workflows/pages.yml` now carries the deploy's own `paths:` filter
  (`on.pull_request.paths`, the `&pages_paths` anchor, aliased by `on.push.paths`), sixteen entries, and nothing
  compares the two. The filter lists `docs/foundry/marketplace/**` (steward Story 109.3), which the source lacks, so a
  stuck marketplace-only deploy goes unseen. The test at
  `src/shared/packages/pyforge-doctor/tests/unit/test_sources_pages_liveness.py:496-509` pins the literal tuple, so it
  agrees with the copy and not with the workflow. Spec open question 2 asked for exactly this pin once `pages.yml`
  carried the filter.
- **The comments name what does not exist.** The comment above `PUBLISHED_INPUTS` cites the herald Dream's list; the
  comment above `STALE_AFTER` (`:61-63`) cites a registry row `dashboard.deploy` that does not exist. The 24 h figure
  is the `pages` row's `stuck_rules.deploy_waiting_hours` in `docs/governance/ci-surfaces.yaml`. CAP-91 still says
  subject herald (the code registers steward, `sources/__init__.py:396-406`), eleven pathspecs with `docsite` (herald
  Story 43.7 removed it, `fa6e11d4e4`), and a `git log` without `--first-parent`.
- **The rule never reads the clock** (`DW-doctor-48-2-1`, `deferred-work-ledger.md:3029`). The rule
  (`pages_liveness.py:94-112`) is stale when the latest input commit is more than 24 hours newer than `last-modified`.
  A deploy that stalls within a day of the last good one reads clean until a later input commit lands more than a day
  after that deploy, which in a quiet week is never; and when the last deploy is more than a day old, every new input
  landing reads stale through its normal build-and-deploy window.

These are the EGM audit's accepted findings DOC-M-Z4, DOC-M-D2, DOC-M-C5 and DOC-D-C2 (cluster DOC-CL-6), recorded in
`_bmad-output/projects/pyforge-doctor/planning-artifacts/research/egm-audit-2026-11-01.md`. The operator ruled on
2026-11-01 (memlog line 875): pin `PUBLISHED_INPUTS` to `pages.yml` with named exclusions; keep `STALE_AFTER` a
constant with its names corrected; fold `DW-doctor-48-2-1`'s clock-aware rule into this story.

**Approach:**
1. **Pin the inputs to the workflow.** A test reads `.github/workflows/pages.yml` as data (`yaml.safe_load`; PyYAML
   reads the bare `on:` key as the boolean `True`, so the test reads `data.get("on", data.get(True))`), takes
   `on.push.paths`, drops each entry's trailing `/**`, removes five named exclusions, and asserts the result equals
   `PUBLISHED_INPUTS` as a set with no duplicates, naming each path missing on either side. The exclusions, from
   Story 48.2's change log, build or deploy the site and publish nothing: `.github/workflows/pages.yml`,
   `scripts/pages_*.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/pages.py`,
   `src/shared/packages/pyforge-steward/src/pyforge/steward/marketplace_pages.py` and
   `src/shared/packages/pyforge-herald/src/pyforge/herald/pages_env.py`. `PUBLISHED_INPUTS` gains
   `docs/foundry/marketplace`. The test replaces the literal-tuple test at `:496-509` and keeps its URL and
   `STALE_AFTER` assertions.
2. **Correct the comments.** The comment above `PUBLISHED_INPUTS` says the inputs are `pages.yml`'s filter less the
   named exclusions (`docsite` dropped by herald Story 43.7), pinned by the test; the comment above `STALE_AFTER` says
   the 24 h is the `pages` row's `stuck_rules.deploy_waiting_hours` in `docs/governance/ci-surfaces.yaml`, which no
   Doctor code reads. No runtime or test read of the registry is added (operator question 3: the "no second reader of
   steward's registry" non-goal stands).
3. **Read the clock.** The site is stale when `last-modified` is before the committer date of the latest
   first-parent input commit on `refs/remotes/origin/main` (its landing on `main`) and the clock, an injectable `now`
   (a module-level clock the tests replace, as they replace `urlopen`), is more than `STALE_AFTER` past that date.
   The `pages-liveness-stale` WARN leads with how long the input has waited and both dates, so `fleet-picture`'s
   110-character cut keeps them, then the commit and the URL; the evidence gains `now` and the wait in whole hours.
   A commit dated before `last-modified` is the OK row whatever the clock. Every unreadable case stays one
   `pages-liveness-unavailable` WARN.
4. **Close the deferral and record the chain.** `DW-doctor-48-2-1` closes citing this story. One decision on the
   station Spec's memlog restates CAP-91 for the DOC-CL-1 re-derive; then the surface reconcile and scoped stamps.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-91** (a stalled Pages deploy is named within a day): the inputs, the 24 h figure's
  source and the rule realize its title; a fix, no new CAP.
- **No flag.** `type: fix` (`spec-feature-flag-governance` Q1).
- **Origin.** `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-01 (the EGM fleet audit) entry; the
  operator ruling of 2026-11-01 (memlog line 875).

## Acceptance Criteria

- **AC1 — Pinned to the workflow.** A test in
  `src/shared/packages/pyforge-doctor/tests/unit/test_sources_pages_liveness.py` reads `.github/workflows/pages.yml`
  as data and asserts `set(PUBLISHED_INPUTS)` equals `on.push.paths` with each trailing `/**` dropped, less the five
  named exclusions, and that `PUBLISHED_INPUTS` has no duplicate; its failure names each path missing on either side.
  The literal-tuple test at `:496-509` is replaced; the URL and `STALE_AFTER` assertions stay.
- **AC2 — Marketplace is an input.** `PUBLISHED_INPUTS` holds `docs/foundry/marketplace`; the existing argv test
  still shows the `git log` pathspecs equal `PUBLISHED_INPUTS`, after `--first-parent` and the full refname.
- **AC3 — True comments, one constant.** The comments above `PUBLISHED_INPUTS` and `STALE_AFTER` name `pages.yml`, the
  exclusions and the `pages` row of `docs/governance/ci-surfaces.yaml`; no comment names `dashboard.deploy` or the
  herald Dream's M1 list as the source; `STALE_AFTER` stays `timedelta(hours=24)`; no code or test reads
  `ci-surfaces.yaml`.
- **AC4 — The clock decides.** With `now` injected:
  - a deploy at T, an input commit landing at T+2 h, `now` T+2 h+25 h → one `pages-liveness-stale` WARN (the stall
    within a day of the last good deploy, which the old rule missed);
  - the same with `now` T+2 h+23 h → the OK row;
  - a two-day-old deploy and an input commit that landed fifteen minutes before `now` → the OK row (the old rule read
    it stale);
  - an input commit dated before `last-modified` → the OK row whatever `now` is;
  - a wait of exactly 24 hours → the OK row; a wait of 24 hours and one second → stale.
- **AC5 — Every fixture carries its clock.** Each fixture under
  `src/shared/packages/pyforge-doctor/tests/fixtures/pages_liveness/` that reaches the rule names its `now`; the
  23/24/25-hour boundary fixtures measure the wait from the input commit's date to `now`; the unavailable fixtures
  (HEAD 404 then GET 404, HEAD 503 then GET 503, a `URLError`, a timeout, a 200 without the header, an unparseable
  header, a `CliBridgeError`, an empty `git log`) keep their one `pages-liveness-unavailable` WARN and no OK.
- **AC6 — Mutation.** Each change below fails a named test; restore each:
  - the rule reverted to commit-against-header (`commit_date - last_modified > STALE_AFTER`);
  - a wait of exactly 24 hours reported stale;
  - `docs/foundry/marketplace` dropped from `PUBLISHED_INPUTS`;
  - an excluded path (`scripts/pages_*.py`) added to `PUBLISHED_INPUTS`;
  - the rule reading the real clock instead of the injected one.
- **AC7 — The deferral closes.** `DW-doctor-48-2-1` in
  `_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md` reads `status: closed` with a
  `closed:` line citing this story and its merge; `deferred-work-check` stays green.
- **AC8 — Unchanged.** Every finding is a WARN or the one OK row (AD-2); the dispatcher exits 0 on every fixture; the
  source makes one HTTP request (HEAD, then GET when HEAD is not 2xx) and one `git log` through `cli_bridge.run_git`,
  no fetch; the sole-subprocess meta-test still names `cli_bridge` alone; `fleet-picture`'s probe and
  `tests/scripts/test_fleet_picture_pages_liveness.py` pass unchanged; `.github/workflows/pages.yml` is not edited;
  steward's `src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py` passes
  (`.github/workflows` is already a `doctor_paths` root, so the pin test fires on a filter change).
- **AC9 — The chain.** One `(decision)` line on
  `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md`, appended with
  `_bmad/scripts/memlog.py`, restates CAP-91 for the DOC-CL-1 re-derive: (a) subject steward
  (`sources/__init__.py:396-406`); (b) the inputs are `pages.yml`'s filter less the named exclusions, `docsite`
  dropped by herald Story 43.7; (c) the 24 h figure is the registry's `pages` row; (d) `git log --first-parent`;
  (e) open question 2 is answered; (f) the clock-aware rule. Memlog line 788 already records the subject move and the
  `docsite` drop as events; the per-finding events are at lines 879 (DOC-M-Z4), 883 (DOC-M-D2), 892 (DOC-M-C5) and
  896 (DOC-D-C2). `SPEC.md` is not hand-edited.
- **AC10 — Surface reconciled.** Each governed path this story changes is named in a reconcile event on every Spec
  `spec-surface-check` names for it (`spec-pyforge-doctor`; `spec-pyforge-core`, which co-governs station `src/`),
  then stamped scoped, one `--spec` each, from a clean tree after `git add`.

## Boundaries & Constraints

**Always:**
- Keep Story 48.2's HARD boundaries: one public URL and the local git log; no `gh`, no GitHub API, no token, no fetch,
  no write (NFR-1); `cli_bridge.run_git` is the one subprocess (AD-5); not in `detectors-ci`, `doctor check`'s default
  set or `monitor`'s axes.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Never read `docs/governance/ci-surfaces.yaml` at runtime or in a test: Doctor is not a second reader of steward's
  registry (operator ruling 2026-11-01).
- Never edit `.github/workflows/pages.yml` to make the pin pass; a filter change is steward's, and the pin follows it.
- Never hand-edit `SPEC.md`; never stamp a Spec this story's diff does not touch.

## I/O & Edge-Case Matrix

| `last-modified` | Latest input commit (first-parent) | `now` | Verdict |
|---|---|---|---|
| after the commit | any | any | OK |
| T | T+2 h | T+2 h+23 h | OK |
| T | T+2 h | T+2 h+24 h | OK (exactly the threshold) |
| T | T+2 h | T+2 h+25 h | `pages-liveness-stale`, waited 25 hours |
| T−48 h | `now`−15 min | — | OK |
| unreadable | any | any | `pages-liveness-unavailable` |
| any | git read fails | any | `pages-liveness-unavailable` |

## Named, not fixed here

- **The second host.** Spec open question 1 stands; the URL stays a constant.
- **A schedule.** `fleet-picture`'s cadence is the operator's (Spec non-goal).
- **The identical-build case.** A commit whose build is byte-identical to the live tree is not redeployed; herald's
  build stamp makes every commit's tree differ, and the daily refresh redeploys a day-old live build, as Story 48.2's
  spec records.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-doctor` CAP-91 (Story 48.2, the pages-liveness source and its `fleet-picture`
  probe). No CAP is minted, and `SPEC.md` changes only through the DOC-CL-1 re-derive.

Parent: spec-pyforge-doctor CAP-91

- Audit findings carried: DOC-M-Z4, DOC-M-D2, DOC-M-C5, DOC-D-C2 (cluster DOC-CL-6); residue file
  `_bmad-output/projects/pyforge-doctor/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Closes: `DW-doctor-48-2-1` (folded by the operator's ruling of 2026-11-01).
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-01 (the EGM fleet audit) entry.
- Epic: Epic 48 (`done`; this story reopens it through the roll-up, Story 41.5). The audit's cluster drafted it as
  Story 56.2 under a new Epic 56; it is keyed into its done epic instead (operator rule 2026-10-04: a fix story goes
  into its done epic).
- Ledger key: `48-3-pages-liveness-reads-its-published-inputs-from-pages-yml`.
- Deps: none.
- Surface: `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/pages_liveness.py`,
  `src/shared/packages/pyforge-doctor/tests/unit/test_sources_pages_liveness.py`,
  `src/shared/packages/pyforge-doctor/tests/fixtures/pages_liveness/`,
  `_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md`; `.github/workflows/pages.yml` is
  read, never edited. `marshal-policy.toml` `[epic_surfaces]."48"` does not list the deferred-work ledger: a
  dispatched build adds it first (MRS-GATE-007); the in-PR hand build needs no change.
- Build mode: in-PR (built in the EGM audit landing PR, branch `egm-audit-2026-11`).
- Minted 2026-11-01 by marshal Story 113.7's landing.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_pages_liveness.py -q` — expected: pass (AC1–AC6).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-live-test` — expected: pass (the test file is `live_tree`-marked, so this half runs it).
- `pixi run --frozen -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/meta/test_cli_bridge_sole_subprocess.py -q` — expected: pass (AC8).
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_fleet_picture_pages_liveness.py -q` — expected: pass (AC8).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q` — expected: pass (AC8).
- The five mutations of AC6 — expected: each fails its named test. Restore each.
- `pixi run --frozen -e pyforge-guild deferred-work-check` — expected: exit 0 (AC7).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog events and the scoped stamps (AC10).
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0.
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.

**Operator, after landing (a live, unauthenticated read):**
- `pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources pages-liveness` — expected: exit 0 and the OK
  row naming the live `last-modified`, the latest published-input commit and the clock.

## Auto Run Result

Status: backlog

## Spec Change Log

- 2026-11-01: minted `backlog` (in-PR) from the EGM audit's cluster DOC-CL-6 (findings DOC-M-Z4, DOC-M-D2, DOC-M-C5,
  DOC-D-C2) at the operator's ruling of 2026-11-01 (pin to `pages.yml` with named exclusions; `STALE_AFTER` a
  constant; fold `DW-doctor-48-2-1`); marshal Story 113.7's landing.

## Review Triage Log

- (none yet)
