---
title: Doctor — one bedside manner for the whole fleet
type: dream
owner: doctor
status: specified
---

# Doctor — check the vitals, keep the ecosystem alive

## The Dream

The Physician's dream: **a factory is only as autonomous as its health checks.**
Before any run, verify the machinery is sound — a missing engine or broken
config fails fast, never mid-build. After anything ships, keep a finger on the
fleet's pulse: staleness, new advisories, upstream abandonment — surfaced as
signals, not surprises. And never stop at a finding: every diagnosis names its
root cause and ships an **ordered prescription** — what to patch, upgrade, or
retire, in what order. Over time, the fleet's overall condition should be
readable at a glance, not reconstructed by hand from five CLIs.

## What it looks like when real, today (v1)

- `doctor check --env --engines` — pre-flight before Marshal spins the factory.
- `doctor monitor --fleet --watch staleness,cve` — the continuous pulse (default
  two highest-signal axes; more addable per invocation).
- `doctor diagnose --target … --prescribe` — partitioned, ranked findings with a
  named root cause for each.
- `--json` on every verb, one schema-versioned `DoctorReport` envelope.

## Why this is a consolidation, not an invention

The instruments already beat inside the factory — Doctor is one bedside manner
over all of them, not a new detection engine:

- **warden · self-check**: the engine-availability doctor check, wrapped as a
  library import (never a subprocess reimplementation).
- **atlas · health & watch**: `feedstock-health`, `staleness-report`,
  `behind-upstream`, `cve-watcher`, `release-cadence` — MCP-first with CLI
  fallback.
- **The one genuinely new instrument**: a credential/environment-hygiene check
  (the `JFROG_API_KEY` unconditional-injection pattern is exactly a Doctor
  finding) — deliberately the *only* new detection capability v1 adds, not a
  precedent for adding others without a matching decision.

## The frontier — named, not yet built

Four capabilities sit outside v1's boundary on purpose — the PRD's own
non-goals name them as "a possible v1.x addition, not a v1 commitment" rather
than rejecting them outright. Real, wanted, deliberately sequenced after the
walking skeleton proves itself:

1. **Health scoring** — a composite grade (A–F) synthesizing Doctor's own
   already-gathered findings across axes (age, staleness, CVE exposure,
   abandonment signal). Not a new scanning engine — a new aggregation layer
   over data Doctor already collects, so it doesn't reopen the "no new
   instruments" boundary v1 draws.
2. **A persistent fleet-health surface** — today's `monitor --fleet` is a
   point-in-time CLI/JSON snapshot; a tracked, at-a-glance view of the whole
   fleet's condition is the natural next step once the snapshot format has
   proven itself in practice.
3. **An adoption-tracking axis** — cf_atlas's `adoption-stage` and
   `version-downloads` signals are named as candidate sources in this Dream's
   own original draft but never made it into `monitor --fleet`'s wired axis
   set. Real, cited, unbuilt.
4. **Safe upgrade-path recommendation** — `--prescribe` ranks and names a root
   cause today, but stops short of naming a target version. A narrow,
   single-hop "here is the next safe version" suggestion (not a full
   transitive dependency-graph resolver — that stays explicitly out of scope)
   is the natural extension once ranking is trusted.

## Why this is different from a fabricated dream

An earlier, separate dream (`pyforge-doctor-dependency-health.md`, created
2026-08-02) proposed most of this same frontier, but inside a bulk commit
later found to contain fabricated content elsewhere (a false migration note,
boilerplate test-architecture docs invented for six stations). Its four
genuinely new items — health scoring, the persistent dashboard, adoption
tracking, and upgrade-path recommendation — survived verification against
Doctor's real, already-authored PRD and are captured above, in Doctor's own
voice and grounded in Doctor's own existing constraints (never a new scanning
engine, never a real graph resolver). The other two-thirds of that dream —
"multi-axis A–F scoring... validated against 1000+ real packages," "95%+
obsolescence catch rate," "80%+ operator acceptance" — were invented precision
with no grounding anywhere in this project's real work, and do not carry
forward. That dream is archived; this one is the real record.

## Realization log

- **2026-10-24 (the warn backlog behind three preflight lines)** — **Found: a full-scope `pr-preflight` prints one
  line per detector, and three of those lines stood for 146 standing warnings.** `dreams-hygiene` printed one
  `dream-readme-missing` line; run alone it reports 121 warnings (64 `dream-readme-missing`, 23
  `dream-status-trailing-comment`, 32 `kinship-wikilink-dead`, 2 `realization-log-missing`). `docs-currency` holds
  one `docs-currency-generated-stale` finding (`docs/reference/bmad-estate-llms-full.md` is `kind: generated` with no
  `generator:` in `docs/map.yaml`, because its generator is scribe's CLI and the check runs only `scripts/docs_*.py`)
  and 19 `docs-currency-authored-stale` pages (sources moved past `verified:`, five dead references).
  `bmad-output-hygiene` printed one `orphan-file` line and holds five (herald 1, marshal 2, steward 2). Every one is
  `warn` and none gates, so they ride every run unread; atlas Story 27.6's session listed the three summary lines as a
  follow-up, and the operator chose, in session, to clear all 146 in one change ("All 146"). **What it looks like when
  fixed:** the three detectors report `ok` on the branch: the generated page names a `scripts/docs_*.py` door that
  hands both modes to scribe's CLI; each
  authored page is re-read against the sources that moved, corrected where they changed it, and re-stamped
  `verified:`; every dead reference resolves; every Dream file has a `docs/dreams/README.md` row, a status line with no
  trailing comment, Kinship links that resolve (retargeted to the Dream a folded one now lives in, or plain text
  where none does) and, when archived, a Realization log; each orphan planning file is cited from the record it belongs to.
  **Constraints:** a `fix` under CAP-84 (documentation currency) and CAP-42 (the fleet hygiene sweep), with no CAP and
  no flag; no detector, threshold or severity changes (the door is the one new script); the README's sentence that rows are never added by hand to
  close the backlog is replaced in the same change, since the operator ruled to close it (a governance edit, recorded
  on the README's governing Spec); a stale page is re-verified against its sources, never re-stamped unread. Owner
  `spec-pyforge-doctor`. → Epic 30 / Story 30.4, specced 2026-10-24.
- **2026-10-22 (the fleet-picture probe guard)** — **Found: twice a new `fleet-picture` ATTENTION probe reached `main`
  without a stub in the CFE meta-test, and each time the test failed without naming the probe.**
  `.claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_main_attention.py` runs `fleet_picture.main()` with
  every probe in its `_PROBES` tuple stubbed. A probe `main()` calls that is not listed reads the faked
  `subprocess.run`, degrades to its own "could not check" line, and turns the file's three tests red. Story 45.1's
  `ci_pause_drift_findings` did that (fixed by mason Story 31.1, CFE v8.100.4), and so did Story 48.2's
  `pages_liveness_findings` (fixed by herald Story 45.1, CFE v8.101.1). The guard that would have named both was
  written on the 2026-10-14 branch `doctor-45-2-fleet-picture-probe-list`, which never landed; its stub fix landed
  separately, so only the guard remained (team memory, 2026-10-18 addendum). **What it looks like when fixed:** a test
  in the same file reads `scripts/fleet_picture.py` with `ast` and requires `_PROBES` to equal the module-level
  `*_findings` / `*_staleness` functions `main()` calls, naming each missing or extra probe, so the next probe fails by
  name in the CFE lane. Epic 45's policy surface declares the meta-test and the CFE version carriers. **Constraints:**
  a test-only fix under CAP-89 (Story 45.1, the probe this file first missed), no CAP and no flag;
  `scripts/fleet_picture.py` does not change; the conda-forge-expert retro (Rule 2) lands with it. Owner
  `spec-pyforge-doctor`. → Epic 45 / Story 45.3, specced 2026-10-22 (45.2 was the unlanded branch's number).
- **2026-10-17 (the detector registry finds a detector's task by its path)** — **Found: `scripts/detectors.py` gives a
  detector the first pixi task whose `cmd` contains the detector's file name, so a task that names the detector's test
  file takes the detector.** `discover()` tests `path.name in c` (`scripts/detectors.py:166`-`:167` at `ab38be642f`),
  and `test_flag_gate_check.py` contains `flag_gate_check.py`. Steward Story 103.3's review saw six detectors go to
  `scripts-lib-test` while that task listed its test files in `cmd`. Story 103.3 moved the list into an argument file
  and pinned only its own library tasks; the matcher stayed (`DW-doctor-103-3-1`). Measured at `ab38be642f`, with the 36
  files of `tests/scripts/scripts-lib-test.txt` inline in a task ahead of the others, nine of the 28 detectors map to
  it. The registry never runs a task (`run_one` runs the script), but the task is what `--list`, `--json` and the
  generated `docs/reference/detectors.md` name, and its absence is the registry's own gap finding ("declares scope but
  has no pixi task"). A wrong match hides that gap: a detector whose own task is gone still reads as tasked while any
  task names its test. Today all 28 map to their own tasks, so the defect is latent. **What it looks like when fixed:**
  a detector's task is the first task, in `pixi.toml` order and skipping a `--json` task as today, whose `cmd` holds the
  detector's repo-relative path as one shell word: `scripts/flag_gate_check.py`, or `./scripts/flag_gate_check.py`.
  `tests/scripts/test_flag_gate_check.py`, or a same-named file in another directory, is a different path and never
  matches. A test reproduces the capture and fails on the old matcher, a detector left with only a test listing reads
  as a registry gap, and all 28 live detectors keep the task they map to today, each task's `cmd` running that
  detector's path. **Constraints:** a fix under FR-15 (the registry Doctor owns; Stories 6.2 and 6.9), no CAP, no flag.
  No live mapping changes, and no detector is added or dropped. `run_one` and the Doctor-source half
  (`_DOCTOR_SOURCE_TASKS`, which `DW-FU-6-9-3` pinned in Story 41.2) do not change. `scripts/detectors.py` and the new
  test stay stdlib-only, so the test runs in `pyforge-ci`. `pixi.toml` is not edited. Owner `spec-pyforge-doctor`.
  → Epic 49 / Story 49.1, specced 2026-10-17.
- **2026-10-14 (the Detectors scripts lane outgrew its timeout)** — **Found: the `scripts-suite` job ran past its
  15-minute limit, and GitHub cancelled it.** It happened on `main` at `8d04520770` and on PR #2204. The job has two
  test steps: `tests/scripts` in `pyforge-ci` (5m22s to 9m10s across six runs on 2026-10-14), then
  `pyforge-doctor-aggregate-scripts-test` in `pyforge-doctor` (4m56s to 6m30s when it finished). A local `--durations` run of the second step took 691.89 s, and 684.59 s of it
  was one test, `test_run_doctor_sources_filters_by_scope_like_a_scanned_detector`. It calls the real
  `_run_doctor_sources` twice, for `repo` and for `all`, and each call gathers every Doctor source over the live tree.
  The test then checks only row counts and that `dashboard-drift` is present. Every other test in the two files takes
  under 0.4 s. The same test ran its real gathers in the first step too, because `pyforge-ci` resolves Doctor's
  run-deps through `spec-kit`. **What it looks like when fixed:** the test swaps Doctor's dispatch table for stubs, so it checks scope
  filtering and row building without gathering, and it shows that a `repo` call skips a source whose scope is
  `runtime`. The two files finish in under a minute locally. The `detectors` job still runs every real gather through
  `detectors-ci`. The job's `timeout-minutes` rises to 25, so the first step's growth does not cancel the lane again.
  **Constraints:** a fix under CAP-42 and CAP-43 (Epic 39's `pyforge-doctor-aggregate-scripts-test`), no CAP, no flag.
  No assertion loses its intent, and `scripts/detectors.py` does not change. Operator ask 2026-10-14: "raise
  timeout-minutes for that job (to about 25) and make those two test files faster". Owner `spec-pyforge-doctor`.
  → Epic 47 / Story 47.1, specced 2026-10-14.
- **2026-10-14 (ci pause drift, specced)** — **Found: the report Doctor was waiting for now exists, and it already
  does the looking.** Steward Story 99.3 landed one command that lists every CI surface with a verdict, read from the
  registry and from GitHub, and that refuses rather than guesses when GitHub cannot be read
  (`spec-pyforge-steward:CAP-166`). So Doctor needs no second pair of eyes on GitHub. It needs to read that one report
  and say aloud the parts that need the operator. Three things do: a surface whose live state differs from what the
  registry declares (this also covers a workflow switched off by hand with no row); a surface that is stuck (a deploy
  waiting more than a day, five or more cancelled runs in a row, or a paused expensive build whose weekly canary has
  not passed lately); and a pause whose review date has passed, even when one of the other two already applies.
  **What it looks like when fixed:** the operator runs `fleet-picture` and its ATTENTION block names each such
  surface on its own line, with the row's owner and the reason. When Doctor cannot read the report (GitHub not
  signed in, steward's own switch off, steward not installed), it says so in one line instead of reporting a clean
  fleet. Nothing it reports changes an exit code. The 2026-10-06 waiting deploy, replayed from a recorded report, is
  named stuck. **Changed since the 2026-10-12 entry:** Doctor reads steward's report, not the registry and GitHub
  itself, so there is one reader of GitHub and one set of verdicts. The `monitor --fleet` `ci` axis is not carried:
  that verb's axes are conda-forge feedstock signals. The check runs on demand and in `fleet-picture`, never in
  `detectors-ci`, because it needs a live, signed-in read. **Constraints:** advisory, never a second PR gate; reads
  steward only through its command line. `bmad-spec` ruled it `flag-exempt: detector-or-gate`: it is a check that
  judges, and switching it off would bring back the silent-off surface it exists to name, so
  `pyforge.doctor.ci_pause_drift` is not minted. Kinships: `spec-pyforge-steward:CAP-166` (Stories 99.3 and 99.6
  produce the verdicts it reads), `docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md` (§ 4.4, § 5, § 6), and the
  herald tile and marshal landing line, which read the same report on their own chains. Owner `spec-pyforge-doctor`.
  → CAP-89 / FR-22, specced 2026-10-14; Epic 45 / Story 45.1.
- **2026-10-13 (one registry orders the whole site, and a stale site tells on itself) — Wanted: `docs/map.yaml` orders
  every section of the Pages site, and an advisory source notices a Pages deploy that stopped.** From the herald
  Dream's same-day entry *the Pages deployment, redesigned* (operator rulings 2026-10-13). Today `docs/map.yaml`
  orders the four quadrants, and herald's `docsite/content/site.yml` feeds the Herald rows into doctor's
  `sidebar_from_map.py` (Story 40.1): two registries, one generator. Measured the same day: the Pages deploy sat in
  `waiting` from 2026-10-06 to 2026-10-12 and no detector saw it; `docs/MAP.md` § *Publish roots* still says the
  dossier publishes at the root, which Story 27.2 moved under `/herald/` on 2026-10-08. **What it looks like when
  real:** `map.yaml` gains additive sections for the non-docs prefixes (`herald`, `status`, `pipelines`, `dashboards`,
  `changes`) so one file orders the sidebar, the top menu and the home tiles, and herald's `site.yml` nav list retires
  into it; an advisory `fleet-picture` source compares the live Pages root's `last-modified` with the latest commit on
  `main` that touched a published input and warns past 24 hours (the 2026-10-06 class, beside Story 43.1's
  `waiting_deployment_over_24h`); `docs/MAP.md`'s *Publish roots* row is corrected and its *outside this map* table
  names `docsite/` and `docs-site/` side by side until M3 dissolves `docsite/`; `docs-map-hygiene` warns on a
  top-level directory the table does not name. **Constraints:** findings stay advisory and never change an exit code;
  the `map.yaml` schema change is additive and `docs-map-hygiene` keeps every current check; the probe reads one
  public URL and the local git log, never the GitHub API. **Kinships:** [[pyforge-herald]] (the site and the lead
  entry), [[pyforge-steward]] (`ci_pause_drift`, the registry row). Owner `spec-pyforge-doctor`; → `bmad-spec` after
  herald's, one story in M2 (registry) and one in M1 (the MAP rows). → CAP-90 / CAP-91, FR-23 / FR-24, AD-14, Epic 48 /
  Stories 48.1–48.2, specced 2026-10-14 (the registry and the MAP rows are one story, 48.1; the probe is 48.2).
- **2026-10-12 (the env-hygiene scan stops growing with the test suite)** — **Found: Story 44.1 made the five-second
  budget judge CPU, and `DW-doctor-44-1` showed the margin is thin and shrinking.** One `doctor check` on the repo root
  spends 2.75 s of CPU at `c447946b3f`. Under load that is about 1.25x headroom, and the scan grew 19% in eight days.
  Measured at `09fd904b02` with each phase of the real `_scan_file` timed, one scan of 2721 files costs:
  - 0.67 s parsing the 178 files that pass both prefilters;
  - 0.69 s in the visitor;
  - 0.34 s in `_resolve_os_aliases`, a second full `ast.walk` of every parsed tree;
  - 0.29 s reading and prefiltering.

  Of the 178 parsed files, 72 are test code. They cost 0.71 s and yield two of today's four findings: a steward test
  fixture that is ungated on purpose, and a Django `tests.py`. The other two findings are real code, in two
  conda-forge-expert scripts. **What it looks like when fixed:** the scan resolves `os` aliases inside the visitor's
  one walk, and it does not scan test code (`test_*.py`, `*_test.py`, `conftest.py`, `tests.py`, and anything under a
  `tests/` or `test/` directory, judged relative to the scan target). That is about 1.0 s, 36% less CPU. The two real
  findings stay. **Constraints:** a fix restoring NFR-4's margin under CAP-1, no CAP, no flag. The five-second budget
  and Story 44.1's CPU measure stay. The detector's verdicts on non-test code do not change. A scan pointed directly at
  a fixtures directory still scans it, because the rule is relative to the target. Operator ruling 2026-10-12:
  "Single pass + skip tests (Recommended)". Owner `spec-pyforge-doctor`. → Epic 46 / Story 46.1, specced 2026-10-12.
- **2026-10-12 (the speed budget under preflight load)** — **Found: `doctor check`'s five-second budget test fails
  only when other lanes share the machine.** `tests/unit/test_check_speed_budget.py` runs `doctor check` on the live
  repo root: one warm-up, then five timed runs judged by their median wall time. In local `pr-preflight` on 2026-10-12
  it read 7.26 s, 5.19 s and 5.76 s on three branches. Alone it passes. **Measured at `c447946b3f`:**
  - `doctor check` spends 2.75 s of CPU against 2.73 s of wall time on an idle machine. It is single-threaded and
    CPU-bound, and only 0.4 s of that is child processes (`deptry --version`, `git ls-files`, `osv-scanner
    --version`).
  - About 95% is doctor's own `env_hygiene` scan: discovery 0.33 s over 2720 `.py` files, then 2.24 s to read them,
    parse the 178 that mention `environ` or `getenv`, and walk their ASTs. The cost is spread across many files; the
    largest single file is 0.15 s.
  - So the budget does measure doctor's own work. What fails is the clock: about twenty preflight lanes on sixteen
    cores stretch a CPU-bound run's wall time 2-2.7x.
  - Separately, the work is growing. The same code costs 2.31 s of CPU on the 2026-10-04 tree and 2.75 s on today's,
    with tracked `.py` files up from 2562 to 2801.
  **What it looks like when fixed:** the test judges the five-second budget on the CPU the run spends (self plus
  reaped children). That equals idle wall time for this run and does not stretch with other lanes' load. The
  warm-up, the median of five, the non-vacuous findings guard and the 5.0 s number all stay. The scan's growth with
  the repo is a deferral row carrying the measurement, so the margin is watched, not assumed. **Constraints:** a
  fix under CAP-1 (the fast pre-flight) and NFR-4 (the speed budget), no CAP, no flag, test-only. The budget is not
  raised, and the test is not skipped, marked `slow` or moved out of its lane. Operator ask, 2026-10-12: "yes, chain
  the doctor budget test fix too". Owner `spec-pyforge-doctor`. → Epic 44 / Story 44.1, specced 2026-10-12.
- **2026-10-12 (ci pause drift)** — **Found: a surface can be off for days with no switch flipped, and no Doctor
  source notices.** `dashboard.yml` run 37447093993 (2026-10-06 10:02) parked its `deploy` job in `waiting` on the
  `github-pages` environment (zero reviewers, wait timer 0, `current_user_can_approve=false`); `concurrency: { group:
  pages, cancel-in-progress: false }` then cancelled every later run — 199 of the last 200 — and Pages served a
  six-day-old build until the operator cancelled the run on 2026-10-12 (run 38244315305 then deployed green). The same
  blindness covers the switches that exist: two `PAUSE_*` repository variables set 2026-10-04 and 2026-10-09 with no
  review date, six workflows `disabled_manually` since 2026-08-24 with no recorded reason, and
  `ACTIONS_ENABLED=false`, dead since it was set, cited as evidence in three planning docs until deleted 2026-10-12.
  `fleet-picture` and `doctor monitor --fleet` have no CI axis. Steward's same-day append mints the registry
  (`docs/governance/ci-surfaces.yaml`), the switch convention and `pyforge steward ci status --json`; the plan is
  `docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md`. **What it looks like when fixed:** a new Doctor source,
  `ci_pause_drift`, advisory, reads the registry and the same live surfaces `steward ci status` reads (`gh variable
  list`, the Actions API's workflow state and recent runs, pending deployments) and raises one finding per rule:
  declared state ≠ live value; `review_by` elapsed; a deployment `waiting` longer than 24 h; five or more consecutive
  `cancelled` runs on one workflow; a `disabled_manually` workflow without a `paused-manually` or `retired` row; a
  paused `cost: high` row whose canary has no green run in 14 days. It appears in `fleet-picture` as its own section
  and in `monitor --fleet` as a `ci` axis; a `warn` never changes the exit code, and an unauthenticated probe is
  refused, not read as green. The 2026-10-06 incident, replayed from a recorded `gh` fixture, yields `stuck` within
  one run. **Constraints:** a feature under CAP-54 (a new Doctor source, not an extension), beside CAP-2 and CAP-6
  (the fleet view); advisory, never a second PR gate; behind a flag (`pyforge.doctor.ci_pause_drift` proposed) unless
  `bmad-spec` rules it `detector-or-gate`; depends on steward's registry and `steward ci status --json` landing first;
  reads `pyforge.steward` through the CLI's JSON, never by import. Operator ruling 2026-10-12: the plan's recommended
  answers Q1–Q8 stand; Epic 43 went to Story 43.1 the same day, so this is a new epic. Owner `spec-pyforge-doctor`.
  → specced 2026-10-14 as CAP-89 / FR-22 (see the 2026-10-14 entry for what changed); Epic 45 / Story 45.1.
- **2026-10-12 (bmad-drift knows dispatch run artifacts)** — **Found: bmad-drift fails the files marshal dispatch
  writes into its own Tier-3 store.** Marshal Story 47.1 (with 47.2 and 93.1) writes a recall-feedback pair into the
  dispatch worktree's gitignored `implementation-artifacts/`: `recall-feedback__<story>__<run>.md` and a sibling
  `….md.query-ran` (`core/recall_feedback.py`, `adapters/harness_bmadloop.py`). `classify()` has no rule for either,
  so `check_coverage` fails both as `uncovered` (HARD), and `detectors-ci` exits 1 in that worktree while CI's fresh
  clone, which has no Tier-3 files, stays green. Found on 2026-10-12 on marshal Story 97.2, whose dispatch worktree
  holds exactly those two files. Reproduced at `70975ae790` with the factory tests' own clean fixture: one OK row, then
  one `uncovered` FAIL per planted file. Marshal writes more Tier-3 shapes that no rule covers:
  `epic-<N>-continuity.md`, `session-advisories/<run>/` (`marshal context advisory`, the session-close ritual),
  `dispatch-runs-quarantine/` (where marshal's stale-run remedy tells the operator to move a run; 145 files on the
  primary checkout fail today), the `token-economy-benchmark-*.json` defaults, and the session's
  `bmad-build-auto-result-<slug>.md`. A blocked session's `*attempted-change*.patch` is the one copy of the attempt, yet
  bmad-drift calls it a `stray-file` "already in git history", and `scripts/bmad_drift_check.py --fix` deletes it.
  Every earlier new shape went the same way (`classify()`'s dated comments list them): red after it landed, then one
  more rule. **What it looks like when fixed:** one declared list in `sources/factory.py` names every Tier-3 shape
  marshal, or the session it dispatches, writes, with the writer it came from. `classify()` reads it, and a test that
  reads marshal's source without importing it fails when marshal starts writing a shape the list lacks. A file no rule names still fails as `uncovered`. **Constraints:** a
  fix, no new CAP, no flag. It works under CAP-12 (one classification rule set, fail-closed for anything else), with
  CAP-11, and keeps the classifier's independence: it never imports `pyforge.marshal`. Operator ask, 2026-10-12: "Do
  this task here: Teach bmad-drift about dispatch recall-feedback files". Owner `spec-pyforge-doctor`. → Epic 43 /
  Story 43.1, specced 2026-10-12.
- **2026-10-11 (duplicate frontmatter keys in story specs)** — **Found: 37 tracked story specs repeat a frontmatter
  key, and no detector says so.** Measured on `main` at `a21524e9d6` with a duplicate-key-detecting YAML loader: 37 of
  the 1,407 tracked story specs with frontmatter carry 40 repeated keys, `followup_review_recommended` 29 times and
  `review_loop_iteration` 11 times, across marshal, steward, herald, doctor, mason and warden. The other 900 tracked
  frontmatter files under `_bmad-output/` and `docs/` repeat nothing. The writer is the `bmad-build-auto` session under
  marshal dispatch, which adds a line where it was told to set one (marshal's Dream, same date). Readers disagree on
  such a block: PyYAML, and so Doctor's own `_frontmatter_parse_text` (CAP-81), keeps the last value, while marshal's
  scalar reader keeps the first. Four specs hold two different values. Herald 29.2 reads `followup_review_recommended:
  true`, then `false`, so Doctor's `deferred-work` (CAP-86) reads the flag as `false` and marshal reads it as `true`;
  `git blame` shows the `true` is the review pass's write and the `false` the stale line it meant to replace.
  Steward 91.1's dispatch branch repeats `review_loop_iteration` again today, and herald 37.1 was cleaned by hand on
  2026-10-11. **What it looks like when fixed:** a Doctor source reads every tracked story spec's frontmatter with a
  loader that records a repeated key at any depth, and fails each one by file, key, both lines and both values; it runs
  in `detectors-ci`, so a PR that adds a repeat goes red. A block that does not parse is reported, never passed.
  **Constraints:** `type: feature`, `flag-exempt: detector-or-gate`, under CAP-81 (a frontmatter block is read one way)
  with CAP-86 (the follow-up flag it reads); no new CAP. `_frontmatter_parse_text` and every existing source's verdict
  do not change. It lands after marshal Story 96.1 cleans the 37 specs and stops the writer, or it reds `main`; that is
  a cross-station gate, so its ledger key is minted `blocked` (operator ask 2026-10-11: "Do this task here: Stop story
  specs gaining duplicate frontmatter keys"). Owner `spec-pyforge-doctor`. → Epic 42 / Story 42.1, specced 2026-10-11.
- **2026-10-07 (detector gaps)** — **Found: two detectors red a landing when no requirement and no flag changed.**
  (1) `chain-currency` dates a station Spec by its `SPEC.md` and its `.memlog.md` (`scripts/fleet_scan.py`
  `_stage_globs`), and the `spec → prd` feeds edge fires once that date is more than 2 days past the PRD's
  (`_FEEDS_GRACE_DAYS`). Every landing appends a surface-reconcile entry to its station's Spec memlog (AGENTS.md
  pre-PR item 5), and marshal's `dispatch land` appends a `Story N.M landed` entry; each append moves the memlog's
  `updated:` to the landing date. So any landing on a station whose PRD is three or more days old reds
  `chain_currency_sweep_check` in `pr-preflight` and `detectors-ci`, though no requirement moved. On 2026-10-07 it held
  herald 28.1 (the herald Spec, and the doctor Spec through a co-governor reconcile), steward 74.2 and warden 14.2
  until each got a hand PRD, spine and epics cascade; mason hit it on 2026-10-05 (the runbook's last Worked Example:
  "a landing that only appends to the memlog moves it"). Measured on `966b166f76`: one `(event) Surface reconcile`
  append to atlas's memlog (PRD 2026-10-03) turns `chain_currency_sweep_check.py --project pyforge-atlas` from exit 0
  to exit 1. (2) The flag gate's per-environment check (`scripts/flag_gate_check.py` `judge_spec_env_defaults`,
  Story 34.3) judges every `done` flagged story spec against the tree. Story specs are permanent records and one flag
  serves one CAP, so stories share keys: steward 74.1 and 74.2 both declare `pyforge.steward.object_store_consumer`;
  74.1 shipped it off everywhere, 74.2 turns it on in dev and staging. With 74.2's overlay values in the tree the gate
  reports two `flag-default-env-mismatch` FAILs on 74.1's `done` spec (reproduced on `966b166f76`), and the 74.2 branch
  cleared them only by rewriting 74.1's historical `flag.default` (`37800e84e5`). Herald's `deck_publish` and
  `deck_viewer` and marshal's `verify_fix_loop` and `preserve_refs` (seven 87.x specs) are shared the same way.
  **What it looks like when fixed:** the `spec → prd` edge reads the Spec's contract date, `SPEC.md` and the memlog's
  newest contract entry, so a surface reconcile or a landing record does not move it while a CAP mint, a decision or a
  re-derived `SPEC.md` still does; and for a key that several `done` specs of one station declare, the gate judges the
  tree against the highest-numbered one, the earlier declarations being history. **Constraints:** fix stories, no new
  CAP, no flag; the 2-day grace, the rule-date baseline and every other rule stay. Owners `spec-pyforge-doctor`
  (CAP-20, CAP-21) and `spec-feature-flag-governance` (CAP-2). They go into Epics 6 and 34 and reopen them. → Stories
  6.13 and 34.6, specced 2026-10-07.
- **2026-10-06 (rekey dating)** — **Found: `ledger-direction` reads a new story through an old fold's rekey map.**
  `gather_direction` passes every merge-derived story id through every rekey map the station tracks (Story 27.2),
  whenever the merge happened. Atlas's 2026-09-17 fold shifted Epics 12..25 to 11..24, so `rekey-2026-09-17.md` maps
  the OLD `25-2` to `24-2`. When atlas's NEW Story 25.2 landed (`3f2744da9e Merge pyforge-atlas/25-2 into main`,
  2026-10-05), the detector read it as 24.2, which is `blocked`, and failed `landed-but-unpromoted` on `main`; every
  local `pr-preflight` then stopped at `detectors-ci`. The same reader also walks each entry to a fixed point across
  the union of maps, so a shift map holding both `13-1 -> 12-1` and `12-1 -> 11-1` would carry a pre-fold `13-1` to
  `11-1`. **What it looks like when fixed:** a map applies only to merges committed before it reached the base ref's
  first-parent line, one hop per map, maps in the order they arrived; a map whose arrival cannot be read keeps today's
  translation. Story 27.2's live atlas rows (13-5, 14-4, 15-3) stay clean. **Constraints:** a fix story, no new CAP,
  no flag. It goes into Epic 27 and reopens it. Owner `spec-pyforge-doctor`. → Story 27.6, specced 2026-10-06.
- **2026-10-05 (generator trust)** — **Ruling: Doctor runs no generator from the judged tree.** Story 40.1's review found
  a third site where a judged tree runs code at Doctor's privileges: `docs_currency` runs the generator script the
  tree's own `docs/map.yaml` names (`DW-doctor-40-1-2`, high, unverified pending a ruling on the trust model). The
  operator ruled it a defect. **What it looks like when fixed:** the generated-page check runs Doctor's own copy of
  each declared `scripts/docs_*.py` generator with `--root <target>`, so the tree supplies only data; a declared path
  outside that set runs nothing. **Constraints:** a fix story, no new CAP, no flag. It goes into Epic 40 and reopens
  it. Owner `spec-pyforge-doctor`. → Story 40.2, specced 2026-10-05.
- **2026-10-04 (env count)** — **Found: bmad-drift counts 35 pixi environments; `pixi.toml` has 36.** Doctor's
  `_env_count` and the script it came from both scan lines inside the `[environments]` block and stop at the next
  header, so an environment declared as its own `[environments.<name>]` table (`python-agent-platform`) is never
  counted. The count feeds the ground truth, `count-stale`, `surface-changed` and the sync baseline; PR #1862's
  re-ground banners had to explain the gap. **What it looks like when fixed:** both counters read the manifest with
  `tomllib` and agree with it; a manifest that does not parse reads as unknown, never an uncaught error.
  **Constraints:** a fix story, no new CAP, no flag. It goes into Epic 6 and reopens it. Owner `spec-pyforge-doctor`.
  → Story 6.12, specced 2026-10-04.
- **2026-10-04 (later)** — **Found: Story 41.3 made chain-completeness blind to the one-chain fold's citation
  window.** Since `bc562fc6b8` (41.3, from `26a298ed12`), INV-A reads only the `## Epic N`, `## Capabilities` and
  `### Story N` sections of a station's PRD and epics (`_DECOMP_SECTION_OPEN_RE`, `sources/board.py`). Each station's
  `## Fold provenance (2026-09-17)` section, written as "the INV-A citation window" for the reminted CAPs on the
  one-chain pilot's ruling (`spec-one-chain-per-station` memlog, 2026-09-16 lesson 11), no longer counts. Six station
  Specs now read `spec-not-decomposed` FAIL on `main`: atlas, doctor, marshal, scribe, steward and warden. The
  Detectors summary row named only warden's, because it shows the last line. Measured: with that one heading added
  back, the live tree reports none; whether a CAP shipped plays no part. **What it looks like when fixed:** a fold
  provenance section counts as decomposition again, so the six FAILs clear; a `## Changelog` section still credits
  nothing, and an open CAP that no epic, story or fold window cites still fails. **Constraints:** a fix story, no new
  CAP, no flag. Owner `spec-pyforge-doctor`. Found by the Epic 41 retrospective (`retro-pyforge-doctor-2026-10-04.md`).
  → Story 41.6, specced 2026-10-04.
- **2026-10-04** — **Found: a fix story cannot join its own done epic.** The operator expects a done epic to reopen when a
  story is added to it, and the sync's roll-up does that. But `ledger-regression`, blocking in CI, reads `epic-N` keys
  as stories, so the reopen turns Detectors red (marshal 85.4 under Epic 85: `epic-85` `done -> in-progress`, exit 2).
  The only way round it was a new epic for every fix, which clutters the specs, sprints and ledger. The guard still
  matters for epics: on 2026-10-03 three promotions dropped done epics to `backlog` while all their stories stayed
  done, and Detectors caught each one. **What it looks like when fixed:** an epic leaves `done` without a finding when
  a new non-done story joins it. Every other move of a done key is still a regression. **Constraints:** a fix story,
  no new CAP, no flag. Owner `spec-pyforge-doctor`. → Story 41.5, specced 2026-10-04.
- **2026-10-03 (Phase 4+5)** — **Phases 4 and 5 of the deferral burn-down: doctor's medium and low deferrals.**
  Measured on `main` with a parser over `deferred-work-ledger.md`: 39 open medium and 84 open low rows. The
  operator ruled both phases run now, on the idle station lanes: every medium row is fixed, each fix also closes
  the low rows in the modules it touches, and no row closes without a landed fix, a `resolution:` and a cited
  `verified:` line; then, overriding the module-cluster sizing, fewer and larger stories split by package area,
  at most about 30 rows each. **What it looks like when fixed:** the chain sources (spec-surface, dream-chain,
  the deferred-work checks, the verification sweep), the ledger, story-status and capability-effect sources,
  the board, factory, hygiene and status-body readers, and the check CLI, score and bmad-method source each
  report what they measured and say when they could not; the 14 recommended follow-up reviews run; doctor's
  own epics Status lines, Spec annotations and docs pages read true. **Constraints:** fix stories, no new CAP,
  no flag (`spec-feature-flag-governance` Q1). DW-FU-7-1-7 is marshal's code and goes to marshal's chain; the one
  high (unverified) row, DW-doctor-40-1-2, waits for its ruling. Owner `spec-pyforge-doctor`. → Epic 41 /
  Stories 41.1-41.4, specced 2026-10-03.

- **2026-10-02** — **Phase 2 of the deferral burn-down: doctor's high deferrals.** Re-verified at HEAD, three
  detector-correctness deferrals stand: the chain-layers audit `exec`s `scripts/fleet_scan.py` from the tree it judges
  (`sources/factory.py` does the same with `scripts/pixi_env_matrix.py`), `ledger-regression` never verifies `head` and
  reads an unresolvable one as every ledger deleted, and `score` grades a wholesale gather failure as a WARN axis, not
  `incomplete`. **Constraints:** operator ruling 2026-10-02: start Phase 2 after the inflow wave. A fix story, no new
  CAP, no flag; it closes its DW rows on landing. Owner `spec-pyforge-doctor`. → Epic 40 / Story 40.1, specced 2026-10-02.

- **2026-10-01 (evening)** — **Found: the step Story 38.5 added to CI has no `pr-preflight` leg.** 38.5 moved the
  three aggregate tests of `tests/scripts/test_detectors_doctor_sources.py` onto a second Detectors `scripts-suite` step
  under `-e pyforge-doctor`, because they skip in `pyforge-ci`. `pr-preflight` runs the first step
  (`pyforge-doctor-scripts-test`, in `pyforge-ci`) but not the second, so locally those tests only ever skip.
  Correction to the 38.5 entry below: `pr-preflight` does run the scripts lane; what it lacked was this step. 38.3 got
  past CI because `dispatch/*` branches skip `pr-preflight` and the landing did not wait for checks, which marshal 80.1
  (`spec-pyforge-marshal:CAP-284`) has since closed.
  **What it looks like when fixed:** the second step is a named task that the `scripts-suite` job and `pr-preflight`
  both call, and a meta-test reds any `scripts-suite` step that `pr-preflight` does not run.
  **Constraints:** `pyforge-ci` stays stdlib-only; the CI step keeps running the same tests. Operator ruling 2026-10-01:
  fix it now. Owner `spec-pyforge-doctor`. → Epic 39 / Story 39.1, specced 2026-10-01.

- **2026-10-01 (later)** — **Found: Story 38.3's aggregate tests need Doctor's run-deps, and the scripts lane has
  none.** 38.3 added three tests to `tests/scripts/test_detectors_doctor_sources.py` that import Doctor's dispatch table
  (`pyforge.doctor.sources.__main__`), which imports `docs_currency` (`jsonschema`, `yaml`). The Detectors workflow's
  `scripts-suite` job runs `tests/scripts` in the stdlib-only `pyforge-ci` env, so all three fail there
  (`ModuleNotFoundError: jsonschema`), and `main` went red on that lane at `d6b0a85992`. The dispatch landed regardless:
  `scripts-suite` is not a required check, and `pr-preflight` has no twin for it.
  **What it looks like when fixed:** the three tests skip where the dispatch table cannot import, as the file's existing
  unimportable-Doctor test already allows, and run for real in a second `scripts-suite` step under `pyforge-doctor`, so the
  name-to-dispatch check 38.3 added keeps CI coverage.
  **Constraints:** `pyforge-ci` stays stdlib-only (its purpose); no test is weakened or deleted. Owner
  `spec-pyforge-doctor`. → Epic 38 / Story 38.5, specced 2026-10-01.

- **2026-10-01** — **Found: four places Doctor lets deferrals and dead checks pile up.** The 2026-09-30 deferral
  burn-down (937 open entries re-read against `main`) found Doctor's own checks letting the ledgers drift:
  - **A `verified:` line can assert a verdict with no evidence.** CAP-29 says every line cites a `file:line` or a measured
    fact, but nothing checks it: two lines said "still open" after the fix had landed (DW-FU-42-3-9, DW-FU-46-1-6) and one
    checked the wrong file (DW-10-3-1) (DW-OPS-2026-10-01-4).
  - **A Spec `surface:` glob that matches nothing is invisible.** `spec-surface` reports a stale allowlist entry but not a
    stale surface glob, the asymmetry `spec-regenerable-factory`'s memlog recorded and Story 6.9 noted; 25 globs across
    7 Specs match no tracked file while the check reports ok (DW-OPS-2026-10-01-2).
  - **`sources/hygiene.py` never runs.** Story 9.2 built the fleet hygiene sweep (CAP-42) as a registered source, but
    nothing dispatches it, so its four deferrals describe code nothing runs (DW-OPS-2026-10-01-1). Operator ruling
    2026-10-01: wire it in, warn-only (CAP-43: reported, never auto-applied); it reports 5 orphan-file warnings today.
  - **`doctor check .` never finishes on the primary checkout.** The env-hygiene walk hits its 50,000-entry cap (57,142)
    on untracked local directories (`.cursor/cdao-p15-noarch-build`, `var/scribe-pg`, `var/platform-local`) and
    reports incomplete (DW-OPS-2026-10-01-3).
  **What it looks like when fixed:** a new `verified:` line with no citation reds the deferred-work check; a dead surface
  glob is a named warning; the hygiene sweep runs with the other detectors, warn-only; `doctor check .` completes on the
  primary checkout.
  **Constraints:** lines already written are grandfathered by date, never rewritten; the dead-glob finding warns, so the
  25 known globs do not red the merge gate; hygiene stays advisory; the walk prunes only what git does not track.
  Owner `spec-pyforge-doctor`. → CAP-88 (the dead-glob finding) / Epic 38 / Stories 38.1–38.4, specced 2026-10-01.

- **2026-09-28 (night)** — **Proposed: capability-ledger's post-PIN check reads only live Specs.** Found by the
  session coordinator and verified the same night on `main` (`0c8c07e6fc`). `capability-ledger-check` (Story 55.2,
  `fcl:CAP-2`, `sources/capability_ledger.py`) prints eight WARNs of the form `post-PIN Spec without a ledger row
  --append`, and all eight are noise. The ledger inventories only `ready` and `in-progress` Specs (`_LIVE_STATUSES`,
  the extract contract in steward's `spec-foundry-capability-ledger/extract.md`). The post-PIN loop, though, warns for
  every `SPEC.md` added after the ledger's `source_sha` without reading its status. Seven of the eight are
  `status: absorbed` folds (`spec-docs-shelf-alignment`, `spec-design-sync-loop`, `spec-marshal-run-watch`,
  `spec-token-economy-claude-session-path`, `spec-self-hosted-bmad-marketplace`, `spec-vocabulary-one-name-one-job`,
  `spec-work-passports-dated-extracts`), and one is a `draft` (`spec-marshal-recall-in-the-loop`). None of them can
  ever gain a row, because their CAPs are never extracted, so there is nothing to classify. A warning nobody can clear
  teaches readers to skip the source, and it buries the one warning that matters: a live Spec added after the PIN with
  no row. **What it looks like when real:** the post-PIN check warns only for a Spec whose frontmatter `status` is live
  (the same `_LIVE_STATUSES` the extract reads) and that has no row. An absorbed or draft Spec added after the PIN
  stays silent until it goes live, and then warns until it is classified. On `main` the source reports OK.
  **Constraints:** the HARD checks do not change (an unclassified live CAP, `A-only` without an expiry, a
  `verified-in-foundry` claim without a case id); the `--append` WARN keeps its message and its `kind: append`; the
  source writes no ledger row. Kinships: `fcl:CAP-2` (the `--append` clause this narrows to the extract's own scope),
  CAP-36 (the detector sees what it claims to check). Owner: `spec-pyforge-doctor`. → CAP-87 / Epic 35 / Story 35.1
  (FR-20), specced 2026-09-28.
- **2026-09-28** — **Proposed: a recommended follow-up review is carried, and Doctor checks it on every
  PR.** Operator ruling 2026-09-28. `spec-pyforge-marshal:CAP-275` makes a landing carry it: `dispatch_land_finalize`
  files a `DW-FRR-<story>` row (`origin: dispatch-followup-review`) for a story whose tracked spec reads
  `status: done` with `followup_review_recommended: true` (Story 66.1), and a one-time backfill carries
  every spec that already reads so, held by a marshal meta test (Story 66.2). That meta test runs only in
  marshal's own suite, which fires on a marshal diff. A doctor or herald PR that lands a flagged spec,
  or edits a ledger and drops its carrying row, is never checked. Measured 2026-09-28: 210 tracked
  specs read `done` with the flag true; by a scratch count only 18 have a carrying row under 66.2's
  predicate today, so the check has to wait for the backfill. **What it looks like when real:**
  Doctor's `deferred-work` source (`deferred-work-check`, in `detectors-ci`) reports every tracked
  story spec that reads `done` with an explicit truthy flag and has no row in its own project's tracked
  `deferred-work-ledger.md` naming it in `source_spec:` under `origin: dispatch-followup-review` or
  `review-budget-followup`, the same predicate as marshal's meta test, as a FAIL, on every PR. A
  follow-up that already ran is seen through the tracked spec: `bmad-build-auto` writes the flag
  `false` before its one follow-up pass and forces it `false` at that pass's halt, so an explicit
  `false` is out of scope. **Constraints:** Doctor reads tracked files only; a Tier-3 dispatch journal
  is gitignored and absent on a runner. Doctor imports no station's internals, so the predicate is
  Doctor's own and matches marshal's by fixtures. The check lands only after marshal Story 66.2 has
  backfilled `main`, or it reds `main`: marshal's `Deps:` parser is station-local, so the story is a
  ledger gate the operator flips. Kinships: `spec-pyforge-marshal:CAP-275` (Stories 66.1 and 66.2),
  CAP-36 (the detector sees what it claims to check), CAP-35..44 (`deferred-work-visibility`, folded).
  Owner: `spec-pyforge-doctor`. → CAP-86 / Story 33.1 (FR-19), specced 2026-09-28.
- **2026-09-27 (late)** — **Proposed: Doctor names the refs it judges by their full refname.**
  Marshal Stories 60.1 and 61.1 found that git resolves a short name through `refs/<n>`,
  `refs/tags/<n>`, `refs/heads/<n>`, then `refs/remotes/<n>`: a local branch or tag named
  `origin/main` stands in for the remote, and a tag named `main` for the local branch. Their third
  review left one reader outside marshal's package (`DW-marshal-doctor-route3-short-main-2026-09-27`),
  and a sweep of Doctor found five: the story-status source's route 3 (`log main`), the
  `ledger-direction` source (`log`, `show` and `ls-tree` of `main`), the `ledger-regression` source
  (its `origin/main` base, rev-parsed, merge-based, listed and shown), and the `frozen-path-changed`
  and `live-proof-surface` sources' diff base (`origin/main`). All five run in `detectors-ci`, and
  `ledger-regression` blocks a merge: with a stray ref they judge the wrong history — a regression missed, a landing
  unseen, a story read as landed that never was. **What it looks like when real:** every git read
  Doctor makes of a branch names `refs/heads/<branch>` or `refs/remotes/<remote>/<branch>`, from one
  Doctor-local helper (Doctor never imports a station's internals); a stray ref named like a branch
  changes no verdict; findings people read still say `main` / `origin/main`. **Constraints:** no
  verdict changes when no stray ref exists; the sources keep their signatures. Kinships: marshal:CAP-270
  (60.1), marshal:CAP-271 (61.1); owner `spec-pyforge-doctor`.
- **2026-09-19 (night)** — **Proposed: the documentation is right, and refreshing it is repeatable
  — by the change that invalidated it, not by a campaign.** Seeded at the review of PR #1529 (a
  parallel session's "persona-based documentation" PR: 14 authored pages, 130 identical
  `README.md` stubs inside skill directories, a `docs-map-hygiene` source that reds on 44 files
  because it scans everything `docs/MAP.md` itself excludes, ten Spec baselines re-stamped on
  content-free memlog lines, a 32-line hand-written Spec filed as a story spec whose CAP-82 /
  Epic 29 collided with the ones minted an hour earlier). The research that fixed the shape:
  `planning-artifacts/research/documentation-currency-and-repeatable-refresh-2026-09-19.md`.
  What the estate already owns: the Diátaxis map with a scope contract (CAP-63/64, `docs/MAP.md`
  § *Outside this map*), `general-docs-consistency` (warn-only, fail-open — CAP-62's posture for
  docs detectors), and two generator + stamp + detector exemplars (`library-llms-full.md` +
  `llms-full-check`; herald's `facts.yaml` + `deck-facts`). What it lacks: any enforcement of the
  map, any notion of which pages are *generated* from a source of truth versus *authored*, and any
  currency signal for authored prose — which is why the PR's own pages shipped with dead paths, a
  non-existent CLI grammar and "fleet-picture reads the Tier-3 ledgers". Operator rulings the same
  night: remove the 130 READMEs (the installer regenerates and retires those dirs — 71 deletions in
  the 6.10→6.11 upgrade alone; no harness reads a README there); the registry is a `docs/map.yaml`
  machine twin of `MAP.md`; doctor owns the chain end-to-end (it owns CAP-48..65 already); keep the
  14 pages, corrected and registered with `sources:`. Decomposed the same night as **CAP-83** (the
  map is enforced within its own scope — missing link = fail, unmapped quadrant page = warn, the
  four quadrants only, index pages exempt; Story 30.1, landed with the PR) and **CAP-84** (documentation
  currency: `docs/map.yaml` registry with `kind: generated | authored | pointer`, `owner`, `sources`,
  stamps; generators for the pixi-task reference, the station CLI cheat sheet, the detector table
  and the skills catalog; a `docs-currency` source that reds a stale generated page, a stale
  authored page — a named source moved past `verified:` or a path/command in it no longer resolves —
  and a stray file in a managed skill dir; warn first, ratcheted to fail per check; the
  `bmad-os-docs-audit → bmad-os-diataxis` pass as the authored-page refresh, triggered by the
  finding; Stories 30.2–30.3, `backlog`).
- **2026-09-19 (evening)** — **Proposed: the sibling drift check records a per-Dream human
  acknowledgement, and knows where the sibling went.** The moment a `GH_TOKEN` reached the
  sibling (the operator's `.bashrc` now exports one from `gh auth token`), CAP-71 reported six
  Dreams diverging on status / content_hash / title: `django-accelerator-framework`,
  `enterprise-data-models-and-apis`, `miniforge-installer`, `package-inventory-eligibility`,
  `pixi-container-image`, `reusable-cicd-workflows`. All six are `archived` here — folded into
  their station Dreams on 2026-09-17 — while the sibling still holds the pre-fold copies
  (`status: dreamt`, untouched since 2026-08-13; the whole sibling repo has not been pushed to
  since 2026-08-24). The Spec's own constraints settle the direction — read-only, never a sync
  engine, their prose unlicensed, reconciliation human and per-Dream — so the answer is an
  acknowledgement, not a push. Two gaps: (1) there is no way to *record* that acknowledgement, so
  the six re-fire on every run and will drown a genuine later change; a `sibling-acknowledged:
  <sibling content_hash>` line on the local Dream should silence exactly that hash and re-fire on
  any other, and a locally `archived` Dream without one should say so in the finding. (2) The
  sibling moved: `OpenTeams-WFT-CDO/mgmt-wf-python-modernization` now 301-redirects to
  `openteams-ai/mgmt-wf-python-modernization`; `sibling_dreams.py` hard-codes the old owner and
  works only while GitHub keeps redirecting. Decomposed the same day as **CAP-82 / Epic 29 /
  Story 29.1** (doctor `DW-OPS-2026-09-19-6` carries the six as the acceptance fixture).
  **Shipped 2026-09-20:** Story 29.1 landed — `sibling_dreams.py` honours `sibling-acknowledged:
  <hash>` (whole-Dream suppression on hash match, re-fires naming both hashes otherwise, `archived`
  named in the no-acknowledgement case) and `_SIBLING_OWNER` now points at `openteams-ai`. All six
  Dreams carry their landing-day acknowledgement; live re-verification: zero `sibling-dreams-drift`
  findings, exit 0. `DW-OPS-2026-09-19-6` closed.
- **2026-09-18 (night)** — **Proposed: a frontmatter reader that stops at the
  first `---` it sees.** `sources/chain.py::_frontmatter_parse` splits a spec on
  the first `---` *anywhere in the file*, not on a line-anchored fence. Marshal
  Story 50.5's tracked spec quotes a `"---"` fence inside its first deferral's
  `evidence:`, so the YAML was cut mid-scalar, `yaml.safe_load` still returned a
  mapping, and the detector saw one deferral where two exist: the first lost its
  `location:` (and so its fingerprint, `fdd6bce25c09` for `3bc3d91bdf95`), the
  second — severity *high* — was invisible to `deferred-work` and to
  `deferred_work_intake.py`, which reported "all 118 already in tracked ledger."
  Every doctor source that reads frontmatter through this helper (spec status,
  deferrals, surface, ownership) inherits the same silent truncation, and a
  quoted fence is ordinary in any spec about frontmatter. Reconciled by hand
  tonight (DW-FU-50-5 rewritten in full-parse form, DW-FU-50-6 added). The
  fix is a line-anchored fence split (marshal's `promotion.py`/`spec_surface.py`
  already parse this way after 50.5); it is `spec-pyforge-doctor` surface, so it
  waits for its CAP and Story rather than a night-time patch. Same family as
  CAP-80's lesson: a reader that degrades silently is worse than one that
  refuses. **Decomposed 2026-09-19** as CAP-81 / **Epic 28**, Story 28.1 (27.4
  stays a reserved hole); the same helper's second defect — `if "---" in text:
  return {}, True` marks any prose file with a horizontal rule as unparseable
  frontmatter — is in the CAP's success.
- **2026-09-19 (afternoon)** — **Proposed: a hollow landing is invisible to every Doctor
  instrument.** Marshal Story 51.3 landed as PR #1501 with a branch diff of one file, +2/−1
  (its own tracked spec's status flip), and finalize promoted `51-3 → done`; `story-status`
  reported ok (the merge subject `Merge pyforge-marshal/51-3 into main` exists),
  `status-body-consistency` never compares a tracked spec's frontmatter `status:` to its
  ledger row, and `sources/ledger.py` attributes by subject alone. Two readers are missing:
  a landing-evidence route that checks the merge's first-parent diff touched the story's
  declared Surface (or any path outside `specs/spec-<key>*.md`), and a tracked-spec-status
  vs ledger-row cross-check. Both are `spec-pyforge-doctor` surface — the next `bmad-spec`
  pass. Same day, from 28.1's own review: `status_body_consistency._parse_frontmatter` is a
  verbatim pre-CAP-81 copy (DW-FU-28-1), `factory.py`'s pin-scope extractor splits the same
  way (DW-FU-28-1-2), and a docs-only PR that flips a live-repo test never fires the station
  lane (found on #1493/#1494).
- **2026-09-18 (later still)** — **Corrected: the atlas rows were a rekey, not a
  sibling.** Story 27.1 landed (PR #1471) with both halves of CAP-78 real —
  `ledger-regression` judges a PR at its merge-base, and the merge-history
  sources read each station's own `merge_subject_template` — but its dispatched
  session refused, correctly, to claim the second symptom: atlas's 13-5 / 14-4 /
  15-3 `landed-but-unpromoted` rows come from atlas's *own* bmad-loop merges
  read with pre-rekey keys (`rekey-2026-09-17.md`: 13-5→12-5, 14-4→13-4,
  15-3→14-3), which `gather_direction` cannot map because only `gather()` was
  made rekey-aware (Story 25.3). The entry below overstated the cause; CAP-78's
  success is corrected and the real fix is CAP-79 / Story 27.2. And one thing
  27.1 broke by doing exactly what CAP-78 said: reading only a station's
  *current* template orphans the merges it landed under the old one — marshal
  `34-3` (`Merge 34-3 into main`, 2026-09-12) read as `done` with no merge
  anywhere the moment marshal's policy moved to `Merge pyforge-marshal/{key}
  into main`. CAP-80 / Story 27.3: the legacy form counts for a station for the
  keys its own ledger knows, and for nothing else.
- **2026-09-18 (later)** — **Proposed: a PR is judged at its merge-base, and a
  merge subject is attributed to the station it names.** Twice today Doctor's
  merge-history sources reported a regression that was not one. (1) `ledger-
  regression` ran on herald PR #1465's `detectors` lane at 18:17Z — two minutes
  *after* `marshal factory dispatch` had merged the PR unattended and promoted
  `23-6 → done` on `main` — and compared `origin/main..HEAD`: the PR head still
  said `backlog`, main now said `done`, so the blocking step reported
  `done-key-regressed: pyforge-herald: 1 story key(s) moved out of done` and
  redded the lane on a PR whose branch never touched that row. The question a
  PR check must answer is "what does this branch change?", which is the ledger
  at `merge-base(origin/main, HEAD)` vs `HEAD` — the tip of `main` is the wrong
  base whenever main moves first, and under unattended landing it always moves
  first. (2) `ledger-direction` has reported `pyforge-atlas/13-5`, `14-4` and
  `15-3` as *landed-but-unpromoted* all day: `sources/marshal.py:87` hardcodes
  `_MERGE_SUBJECT_TEMPLATE = "Merge {key} into main"`, so another station's
  `Merge 13-5 into main` reads as atlas's 13.5 landed — the same un-scoped
  templated shape marshal's own supervisor tripped on this morning (herald
  23.x via atlas's `Merge 23-N into main`; marshal is closing its side as
  `spec-pyforge-marshal:CAP-247` and station policies now render
  `Merge <slug>/{key} into main`). Doctor's sources must read each station's
  own `merge_subject_template` from its `marshal-policy.toml` — a TOML read,
  never a marshal import — and accept only a subject whose slug is that
  station's. Seeded as CAP-78, decomposed the same day as Epic 27 / Story 27.1;
  advisory posture unchanged, and `ledger-regression` stays the one blocking
  Doctor step in CI (ruling 2026-09-14) — this makes its verdict true, not softer.
- **2026-09-18** — **Proposed: the map of what no agent can verify without a
  live proof.** Bugs cluster where agents cannot see them — not because the
  code is hard, but because verifying it correct needs a real round-trip
  against something outside the repo (a third-party API, a live browser, a
  service with its own auth and its own drift), and a dev pass's own
  self-report is never evidence of that, only a live proof is. This fleet
  already has several such surfaces, each documented only in its own
  station's prose, nowhere aggregated: herald's Claude Design MCP bridge (a
  push isn't proven until read back through the live serve URL, harness
  stripped, byte-compared), herald's live webhook host (opt-in only,
  `HERALD_LIVE_WEBHOOK=1`, never in the default gate), scribe's
  Postgres+pgvector cluster (`scribe-pg-up` first), atlas's
  Chromium/DuckDB/WASM pipeline, warden's live OSV-scanner/CISA-KEV/EPSS
  feeds. Every one already has a real, working live-proof mechanism; what's
  missing is one place that says *these exist, here's how to actually prove
  them, and a dev pass's own confidence is not enough evidence on its own.*
  Motivating incident, same session: herald's mcp SDK transport broke across
  two separate 2.x changes (`streamablehttp_client` renamed with a different
  call signature; `CallToolResult.isError` renamed to `.is_error`), caught
  by neither review nor the test suite nor a dev pass's self-report — only a
  real live push-then-read-back against Claude Design surfaced it. Shape:
  one doctor-owned, fleet-wide inventory of these surfaces (station, surface,
  what a static pass cannot see, how to prove it live, roughly how
  expensive); a story/PR touching one gets an advisory finding naming it,
  never gating, matching Doctor's own posture. Not yet a CAP or an Epic —
  recorded here as the seed; decomposition follows if greenlit.

- **2026-08-08** — **Doctor took the verdict on the Marshal's own row.** Charter §6
  has said since 2026-07-28 that the Doctor holds it, *"the one station that would
  otherwise grade itself"* — but nothing implemented it. A single `sprint-ledger-sync`
  run then destroyed 96 `done` markers across four stations and printed success, and
  all three guards written in response lived in Marshal's own surface. Doctor gained a
  ninth Source (`marshal-durability`), CAP-9, FR-14, AD-11/AD-12 and Epic 5. The
  design point worth remembering: unlike the warden source, this one **imports no
  station package** — a durability verdict assembled from the judged station's own
  code would fail exactly when that station's machinery is what broke.

- **2026-07-23** — persona defined in [[pyforge-charter]]; chapter deck seeded
  (`presentations/pyforge-doctor/`).
- **2026-07-25** — full planning chain landed: Spec (CAP-1..CAP-4), PRD
  (FR-1..FR-9), Architecture (AD-1..AD-7), Epics (3 epics, 12 stories).
- **2026-08-02** — Epic 1 shipped (5/5 stories: package scaffold, warden
  engine-check wrap, tri-state checks, credential/env-hygiene check, CLI
  wiring). Epics 2 (Fleet Pulse) and 3 (Diagnose & Prescribe) remain pending,
  7 stories. Dream consolidated same day: the fabricated `dependency-health`
  dream retired, its real remainder (four frontier items above) captured here
  and decomposed into a genuine Epic 4 (CAP-5..CAP-8, FR-10..FR-13) rather
  than left as an unlinked aspiration.

## Fold — one chain (2026-09-17)

Doctor rebases to one Dream, one Spec, one PRD, one spine, one epic chain. Folded topic Dreams are archived in place with `Consolidated into [[pyforge-doctor]]` banners. Absorbed Spec folders keep pointer + memlog + companions.

Folded Dreams: [[bmad-drift-new-artifact-shape]], [[bmad-method-version-drift]], [[capability-effect-check]], [[chain-currency-sweep]], [[deferred-work-audit-completeness]], [[deferred-work-resolution-sweep]], [[deferred-work-visibility]], [[docs-shelf-alignment]], [[fleet-hygiene-verification-exemplar-program]], [[general-docs-consistency]], [[pixi-candidate-currency]], [[pyforge-doctor-dependency-health]], [[sibling-dreams-drift]], [[status-body-consistency]].
