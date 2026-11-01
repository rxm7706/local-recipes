---
title: "48.3: pages-liveness reads its published inputs from pages.yml"
type: 'fix'
created: '2026-11-01'
status: 'done'
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

Status: done (independent review passed 2026-11-01; see Review Triage Log)

**What changed**

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/pages_liveness.py` — `PUBLISHED_INPUTS` gains
  `docs/foundry/marketplace` (eleven pathspecs, in `pages.yml`'s order). The comment above it names
  `.github/workflows/pages.yml`'s `on.push.paths`, the five exclusions and herald Story 43.7's `docsite` drop; the
  comment above `STALE_AFTER` (still `timedelta(hours=24)`) names the `pages` row's
  `stuck_rules.deploy_waiting_hours` in `docs/governance/ci-surfaces.yaml`, which no Doctor code reads. A module
  clock `now` (default `_utc_now`, aware UTC) is replaced by tests as `urlopen` is. The rule: stale only when
  `last-modified` is before the input commit's date (`pending`) and `now - commit_date > STALE_AFTER`; the stale
  WARN reads `Pages input waited <N|more than N> hours: last-modified …, inputs … (published-input commit <sha> on
  origin/main, undeployed at <now>), <url>` (the 2026-10-06 replay's evidence ends at character 107); the OK row
  ends `deployed after it (clock <now>)` or `not yet deployed, waiting within 24 hours (clock <now>)`. Evidence
  keeps `lag_hours` (commit against header) and gains `now` and `waited_hours` (whole hours; 0 when deployed after
  the commit). The git argv, the HTTP path and every unavailable case are unchanged.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_pages_liveness.py` — the literal-tuple test is
  replaced by `test_the_published_inputs_are_pages_yml_s_filter_less_the_named_exclusions` (reads `pages.yml` with
  `yaml.safe_load`, `data.get("on", data.get(True))`, drops `/**`, removes the five exclusions, refuses duplicates,
  names each path missing on either side, and fails when a named exclusion leaves the filter); URL and
  `STALE_AFTER` assertions kept in `test_the_url_and_the_threshold_are_constants`. New: AC4's five cases, a
  deployed-after-it row at four clocks, a commit at the deploy's own second, the clock-injection mutation test, the
  marketplace and no-excluded-path mutation tests, the comment test (AC3) and `test_every_fixture_that_reaches_the_rule_names_its_clock`
  (AC5). The every-fixture test asserts one clock read when a fixture names `now` and none otherwise.
- `src/shared/packages/pyforge-doctor/tests/fixtures/pages_liveness/` — `commit_{23,25,exactly_24}_hours_newer.json`
  replaced by `input_waited_23_hours.json`, `input_waited_exactly_24_hours.json`,
  `input_waited_24_hours_and_one_second.json`, `input_waited_25_hours.json` (deploy T, commit T+2 h, `now` measured
  from the commit) and `fresh_input_on_a_two_day_old_deploy.json`; `site_newer_than_commit.json`,
  `head_405_get_200.json` and `replay_2026_10_06.json` name their `now` (the replay's is six days after the deploy:
  waited 78 h, lag still 65 h). The eight unavailable fixtures are unchanged and name no `now`.
- `.github/workflows/pyforge-station-tests.yml` (outside the Surface; allowlisted, not Spec-governed) —
  `doctor_live_paths` gains `.github/workflows/pages.yml` and `docs/foundry/marketplace`. AC8's premise that
  `.github/workflows` is a `doctor_paths` root no longer holds since steward Story 117.4 split the live-tree half,
  and steward's trigger-map meta-test reds both new reads of the pin test until the live half fires on them; with
  the two rows the pin test runs on any `pages.yml` filter change. `.github/workflows/pages.yml` is not edited.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md` — one surface
  reconcile event (every path above as a full literal path) and the AC9 `(decision)` restating CAP-91 (a)–(f).

**Not done here (session owner):** AC7 — `DW-doctor-48-2-1` is closed by the session owner at promotion (this
build does not edit `deferred-work-ledger.md`); AC10 — the `spec-pyforge-core` co-governor reconcile for
`pages_liveness.py` and both scoped stamps (`spec-pyforge-doctor`, `spec-pyforge-core`) after `git add`.

**Commands (exit codes)**

- `pixi run --frozen -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_pages_liveness.py -q` — 0 (98 passed).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — 0 (1213 passed).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-live-test` — 0 (2719 + 4 passed).
- `pixi run --frozen -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/meta/test_cli_bridge_sole_subprocess.py -q` — 0 (11 passed).
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_fleet_picture_pages_liveness.py -q` — 0 (6 passed, file unchanged).
- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q` — 1 before the workflow rows (doctor_live: `.github/workflows/pages.yml`, `docs/foundry/marketplace`); after them 1 still, but only on concurrent mason (`test_mason_skills.py`) and scribe (`test_guild_env_membership.py`, `test_instruction_surface_parity.py`) reads from other stations' in-flight stories in this worktree — no doctor row.
- `ruff check` / `ruff format --check` (pyforge-guild's ruff, the doctor package's `[tool.ruff]`) on both Python files — 0 / 0.
- `mypy --cache-dir .mypy_cache/pyforge-guild -p pyforge.doctor` from the package root (lint-types' doctor slice) — 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — 0.
- AC6 mutations, each on a scratch copy of the package (never the shared tree), each failing its named test and restored (restored copy: 98 passed):
  1. rule reverted to `lag > STALE_AFTER` — fails `test_an_input_waiting_25_hours_is_one_stale_warn_naming_both_dates_the_sha_and_the_wait`, `test_mutation_a_fresh_input_on_a_two_day_old_deploy_is_the_ok_row` (11 failed);
  2. `>=` for `>` — fails `test_mutation_a_wait_of_exactly_24_hours_is_the_ok_row_not_stale` (3 failed);
  3. `docs/foundry/marketplace` dropped — fails `test_mutation_the_marketplace_tree_is_a_published_input` and the pin (2 failed);
  4. `scripts/pages_*.py` added — fails `test_mutation_no_excluded_path_is_a_published_input` and the pin (2 failed);
  5. `datetime.now(UTC)` for `now()` — fails `test_mutation_the_rule_reads_the_injected_clock_never_the_real_one` (25 failed).

**Review follow-up 2026-11-01** (both reviews' advisory): `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py`'s
`PAGES_LIVENESS` comment now states the clock-aware rule (an input that landed after the deploy and has waited more
than 24 hours is one WARN, an input the site was deployed after is the OK row, an unreadable side is one WARN) in
place of the retired "a deploy more than 24 hours behind its inputs"; `tests/scripts/test_fleet_picture_pages_liveness.py`'s
`_STALE` comment calls its message the retired 48.2 shape, kept as a fixture because fleet-picture only cuts a message
at 110 characters (comment only; the fixture and the six tests are unchanged). Surface reconcile on the
`spec-pyforge-doctor` memlog; `spec-pyforge-core`'s for `models.py` is the session owner's. `pyforge-doctor-test` 0
(1213 passed); `pytest tests/scripts/test_fleet_picture_pages_liveness.py` (pyforge-guild) 0 (6 passed); ruff check
and format on `models.py` (doctor `[tool.ruff]`) 0 / 0.

## Spec Change Log

- 2026-11-01: minted `backlog` (in-PR) from the EGM audit's cluster DOC-CL-6 (findings DOC-M-Z4, DOC-M-D2, DOC-M-C5,
  DOC-D-C2) at the operator's ruling of 2026-11-01 (pin to `pages.yml` with named exclusions; `STALE_AFTER` a
  constant; fold `DW-doctor-48-2-1`); marshal Story 113.7's landing.
- 2026-11-01: built in-PR, `in-review`. Deviation: AC8's trigger-map clause needed two `doctor_live_paths` rows in
  `.github/workflows/pyforge-station-tests.yml` (`.github/workflows/pages.yml`, `docs/foundry/marketplace`), outside
  the Surface; the premise that `.github/workflows` is a `doctor_paths` root predates steward Story 117.4's live-tree
  split. AC7 and AC10's stamps are left to the session owner.
- 2026-11-01: `in-review` -> `in-progress` — independent review failed (Review Triage Log): `lint-types` ruff I001 in
  `test_sources_pages_liveness.py`, and AC7's `DW-doctor-48-2-1` still open.
- 2026-11-01: `in-progress` -> `done` — second independent review passed (Review Triage Log): the I001 blank line is
  back and `DW-doctor-48-2-1` reads `status: closed` with a `closed:` line citing this story.

## Review Triage Log

- 2026-11-01 — reviewer: independent session (did not write this code; judged the diff against this spec, not the
  Auto Run Result). **Verdict: fail — back to `in-progress`.**
  - **Failure 1 — `lint-types` is red on this story's test file.** `pixi run --frozen -e pyforge-guild python
    scripts/lint_types.py ruff` (the task `lint-types.yml` and `pr-preflight` call verbatim; it runs `ruff check`
    from the package dir) exits 1 for pyforge-doctor with `I001 Import block is un-sorted or un-formatted` at
    `src/shared/packages/pyforge-doctor/tests/unit/test_sources_pages_liveness.py:9`: the diff dropped the blank
    line between the third-party block (`import pytest`, the new `import yaml`) and the first-party
    `from pyforge.doctor …` imports. It is the only ruff finding in pyforge-doctor. The Auto Run Result's
    "`ruff check` … 0" does not reproduce. Fix: put the blank line back after `import yaml`.
  - **Failure 2 — AC7 is not met.** `DW-doctor-48-2-1`
    (`_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md:3029`) still reads
    `status: open` with no `closed:` line. The ledger is in this story's Surface, and a closure citing the story
    in-PR has precedent on the same ledger (the `closed:` line at `:3117`, doctor Story 49.1). Close it citing this
    story; `deferred-work-check` is green today (exit 0) and must stay so.
  - Held, with evidence: AC1 (the pin reads `pages.yml` with `yaml.safe_load`, `data.get("on", data.get(True))`,
    drops `/**`, removes the five exclusions, refuses duplicates, names each side); AC2 (`docs/foundry/marketplace`
    in `PUBLISHED_INPUTS`; the argv test passes); AC3 (comments name `pages.yml`, the exclusions and the `pages` row;
    no `dashboard.deploy` / M1; `STALE_AFTER` 24 h; no read of `ci-surfaces.yaml`); AC4 and AC5 (fixtures checked by
    hand: T 12:00, input T+2 h, clocks at +23 h / +24 h / +24 h 1 s / +25 h; a 47 h 45 min lag at 15 min wait;
    the eight unavailable fixtures name no `now` and read no clock); AC8 (`pages.yml` unedited;
    `tests/scripts/test_fleet_picture_pages_liveness.py` unchanged and passing; the steward trigger-map meta-test
    exits 1 only on mason and scribe rows from other stations' in-flight stories, no doctor row); AC9 (the memlog
    decision covers (a)–(f)). The out-of-Surface `pyforge-station-tests.yml` rows are a recorded deviation and
    allowlisted (`.github/**`).
  - Commands (exit codes read from `$?`): `pytest …/test_sources_pages_liveness.py` 0 (98 passed);
    `pyforge-doctor-test` 0 (1213); `pyforge-doctor-live-test` 0 (2728 + 4); `pytest …/test_cli_bridge_sole_subprocess.py`
    0 (11); `pytest tests/scripts/test_fleet_picture_pages_liveness.py` (pyforge-guild) 0 (6); trigger-map meta-test
    1 (foreign rows only); `deferred-work-check` 0; `lint_types.py ruff` 1 (Failure 1); `ruff-format` 0; `mypy` 0;
    `spec-surface-check` 0.
  - AC6 mutations, each on a scratch mirror (`PYTHONPATH` to the mirror's `src`, `pages.yml` copied), restored each
    time: rule reverted to `lag > STALE_AFTER` → 11 failed (incl.
    `test_an_input_waiting_25_hours_is_one_stale_warn_…`, `test_mutation_a_fresh_input_on_a_two_day_old_deploy_…`);
    `>=` for `>` → 3 failed (incl. `test_mutation_a_wait_of_exactly_24_hours_is_the_ok_row_not_stale`);
    `docs/foundry/marketplace` dropped → the marketplace test and the pin; `scripts/pages_*.py` added → the
    no-excluded-path test and the pin; `datetime.now(UTC)` for `now()` → 25 failed (incl.
    `test_mutation_the_rule_reads_the_injected_clock_never_the_real_one`).
  - Advisory (no AC; fix while here, healed tissue): `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py:222-225`
    still says "a deploy more than 24 hours behind its inputs is one WARN", the retired rule; and
    `tests/scripts/test_fleet_picture_pages_liveness.py:24-29` labels the retired "Pages deploy more than 65 hours
    behind" message "The source's own shape" (AC8 keeps that file unchanged, so only its comment is in question).
  - Left to the session owner (reserved by this workflow, not judged): AC10's `spec-pyforge-core` co-governor
    reconcile and the scoped stamps; `detectors-ci` and the full `pr-preflight`.
- 2026-11-01 — reviewer: independent session, second review (did not write this code; judged the working-tree diff
  of `pages_liveness.py`, its unit test, its fixtures and `deferred-work-ledger.md` against this spec, not the Auto
  Run Result). **Verdict: pass — `done`.**
  - **First-review Failure 1 (ruff I001) — fixed.** The blank line after `import yaml` is back
    (`test_sources_pages_liveness.py:25-27`). `.pixi/envs/pyforge-guild/bin/ruff check .` and `ruff format --check`
    from inside `src/shared/packages/pyforge-doctor` exit 0 / 0; `pixi run --frozen -e pyforge-guild python
    scripts/lint_types.py ruff` exits 0 (all 19 packages ok), `… ruff-format` 0, `… mypy` 0.
  - **First-review Failure 2 (AC7) — fixed.** `DW-doctor-48-2-1` (`deferred-work-ledger.md:3029-3039`) reads
    `status: closed` and carries a `closed: 2026-11-01 — doctor Story 48.3 (spec …)` line naming the story, its spec,
    Epic 48, the rule and its fixtures, and "CAP-91 re-derives in the same PR". No merge SHA can exist before the
    landing, and the in-PR closure precedent on the same ledger (`:3118`, doctor Story 49.1) cites none either;
    held. `pixi run --frozen -e pyforge-guild deferred-work-check` exits 0.
  - Held, re-checked: AC1 (`test_the_published_inputs_are_pages_yml_s_filter_less_the_named_exclusions` reads
    `pages.yml` with `yaml.safe_load` and `data.get("on", data.get(True))`, takes `on.push.paths` (the `*pages_paths`
    alias, 16 entries), drops `/**`, removes the five exclusions, refuses duplicates, names each side; the old
    literal-tuple test is gone; URL and `STALE_AFTER` asserted in `test_the_url_and_the_threshold_are_constants`);
    AC2 (`docs/foundry/marketplace` in `PUBLISHED_INPUTS`; the argv test still equals the pathspecs after
    `--first-parent` and the full refname); AC3 (comments name `.github/workflows/pages.yml`, the five exclusions and
    the `pages` row's `stuck_rules.deploy_waiting_hours` — that row is `docs/governance/ci-surfaces.yaml:53-63`, value
    24; no `dashboard.deploy` or M1 in the doctor source tree; `STALE_AFTER` is `timedelta(hours=24)`; the only
    `ci-surfaces.yaml` hits are the comment and a string assertion on the source text, no read of the file); AC4
    (fixtures checked by hand: deploy 2026-10-13T12:00Z, input T+2 h, clock +23 h → OK, +24 h → OK, +24 h 1 s →
    stale, +25 h → stale "waited 25 hours"; a 2026-10-12 deploy with an input 15 min before the clock → OK with
    `lag_hours` 47; an input before or at `last-modified` → OK at four clocks up to a year out); AC5 (every fixture
    with a verdict names `now`, the eight unavailable fixtures name none, and the every-fixture test asserts one
    clock read or none); AC8 (`pages.yml` unedited; the rule adds no request and no subprocess; the
    sole-subprocess meta-test passes; `tests/scripts/test_fleet_picture_pages_liveness.py` and `fleet_picture.py`'s
    pages probe unchanged and passing; the steward trigger-map meta-test exits 1 on eight foreign rows only —
    marshal `test_factory_challenge.py`, mason `test_mason_skills.py` / `test_persona_consults_cfe.py`, scribe
    `test_instruction_surface_parity.py` / `test_guild_env_membership.py` — and no doctor row); AC9 (the memlog
    `(decision)` covers (a)–(f), beside the surface-reconcile event).
  - AC6, re-run by this reviewer on a scratch mirror of the package (`PYTHONPATH` to the mirror's `src`, confirmed by
    `pages_liveness.__file__`; `pages.yml` copied to the mirror root), each restored and the restored copy 98 passed:
    rule reverted to `lag > STALE_AFTER` → 11 failed (incl.
    `test_an_input_waiting_25_hours_is_one_stale_warn_naming_both_dates_the_sha_and_the_wait`,
    `test_mutation_a_fresh_input_on_a_two_day_old_deploy_is_the_ok_row`); `>=` for `>` → 3 failed (incl.
    `test_mutation_a_wait_of_exactly_24_hours_is_the_ok_row_not_stale`); `docs/foundry/marketplace` dropped → 2
    failed (`test_mutation_the_marketplace_tree_is_a_published_input` and the pin); `"scripts/pages_*.py"` added → 2
    failed (`test_mutation_no_excluded_path_is_a_published_input` and the pin); `clock = datetime.now(UTC)` for
    `now()` → 25 failed (incl. `test_mutation_the_rule_reads_the_injected_clock_never_the_real_one`).
  - Commands (exit codes read from `$?`, output to files): `pytest …/test_sources_pages_liveness.py` (pyforge-doctor)
    0 (98 passed); `pyforge-doctor-test` 0 (1213 passed); `pytest …/test_cli_bridge_sole_subprocess.py` 0 (11);
    `pytest tests/scripts/test_fleet_picture_pages_liveness.py` (pyforge-guild) 0 (6); `deferred-work-check` 0;
    `lint_types.py ruff` 0, `ruff-format` 0, `mypy` 0; `spec-surface-check` 0; trigger-map meta-test 1 (foreign rows
    only, above); `pyforge-doctor-live-test` 1 (2729 passed, 1 failed), the one failure foreign:
    `tests/meta/test_portal_fleet_pulse.py::test_story_does_not_add_pyforge_under_src_platform` reds on
    `src/platform/tests/test_warden_fleet_proposals.py: import urllib.request`, another station's in-flight edit in
    this worktree, none of this story's files. The session owner should clear it before the push: it is a doctor
    meta-test and will red doctor's live lane on this PR.
  - Advisory, unchanged since the first review (no AC; outside this story's file list):
    `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py:222-225` still describes the retired rule ("a
    deploy more than 24 hours behind its inputs is one WARN"), and `tests/scripts/test_fleet_picture_pages_liveness.py:24`
    still calls the retired "Pages deploy more than 65 hours behind" message "The source's own shape".
  - Left to the session owner (reserved, not judged): AC10. `scripts/.spec-surface-baseline.json` lists
    `pages_liveness.py` under both `pyforge-doctor/spec-pyforge-doctor` and `pyforge-marshal/spec-pyforge-core`; the
    doctor memlog carries the 48.3 reconcile event, the `spec-pyforge-core` memlog
    (`_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md`) carries none yet,
    and neither Spec is stamped. Also reserved: `detectors-ci` and the full `pr-preflight`.
