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

- **2026-10-24 (docs-currency's two detector gaps)** — **Found: `docs-currency` reports a generator that cannot run
  as a stale page, and flags true references as dead in two shapes.** Story 30.4's review recorded both
  (`DW-doctor-30-4-1`, `DW-doctor-30-4-2`). (1) `_check_generated_page` reads every non-zero exit of a generator's
  `--check` as "stale against its generator", so `scripts/docs_bmad_estate.py`'s exit 2 (could not run, where
  `pyforge.scribe` is not importable) reads as a hand edit. (2) The dead-reference scan strips a path's trailing `/`
  before `git check-ignore`, so a directory-only ignore rule such as `docs/dashboard/kedro-viz/` never matches an
  absent path; and a backticked `bmad-*` token resolves only as a skill, a script or an exact pixi task, so a
  detector named by its source (`bmad-output-hygiene`, task `bmad-output-hygiene-check`) reads as a dead skill.
  `scripts/governance_currency_check.py` mirrors both scan rules and has both gaps. Story 30.4 reworded three true
  references around them. **What it looks like when fixed:** a generator exit of 2 (or any exit but 0 and 1, or a
  crash that exits 1 with a traceback) is reported as could-not-run, never as stale; the ignore check also tries a
  path the page wrote with a trailing `/` in that slashed form; a `bmad-*` or
  `skf-*` token resolves when `<token>-check` is a pixi task; both detectors change together, and the kedro-viz and
  `bmad-output-hygiene` references read as they did (`.claude/worktrees/` is ignored only by a local
  `.git/info/exclude`, so a fresh clone rightly reads it as absent, and the page keeps its placeholder paths). **Constraints:** a fix under CAP-84, no CAP and no flag; no check name, severity or
  threshold changes; the two detectors keep their mirrored rules identical. Owner `spec-pyforge-doctor`. → Epic 30 /
  Story 30.5, specced 2026-10-24.
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
  `verified:`; every dead reference resolves or is marked historical; every Dream file has a `docs/dreams/README.md`
  row, a status line with no trailing comment, Kinship links that resolve (retargeted to the Dream a folded one now
  lives in, or plain text or a plain link where none does) and, when archived, a Realization log; each orphan planning file is cited from the record it belongs to.
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
- **2026-10-26 (every requirement derives from a capability) — Found:** the 2026-09-16/17 folds wrote every PRD's `FR-n ← CAP-m` arrows by counting, and `fr-without-cap` (Story 25.2) could not tell — it checked that a cited number existed somewhere in an open Spec, read `FR-1.1` as `FR-1`, could not see `FR33` or `NFR-C2`, and took a wrapped prose line that opens with an id as a definition; doctor's own FR-14 and FR-15 cited the Charter's §6 instead of a capability, FR-16 had no PRD heading, and the fold cut 88 of the Spec's intent and success bullets. **Ruled** (2026-10-26, operator, fleet-wide: "yes forbid it"): a requirement cites one or more defined capabilities and nothing else (`spec-one-chain-per-station` CAP-5 as amended; CHAIN-STANDARD § 12), enforced by Doctor. **For doctor:** CAP-92 — `fr-without-cap` reads every requirement definition, resolves each cite against a capability definition line in the named Spec, fails a non-CAP arrow, an unhyphenated or duplicate id and a counted run (four or more consecutive ids whose CAP number steps in lockstep while no title shares a word with its CAP), on new findings only against a baseline that only shrinks, with a title-overlap score advisory only; CAP-93 minted from FR-15 so it cites a capability; FR-14 ← CAP-9; FR-16's heading added; the cut bullets restored by script from `4d3ae19674^`. Epic 50 / Story 50.1 (`flag-exempt: detector-or-gate`), the anchor of the one-PR effort; both CAPs route `rebuild` (ruling (e)); the Epic 50 retrospective lands in the same PR.
- **2026-10-26 (the inventory and the gate measure the retrofit as ruled) — Found:** the flag inventory at `97c8211773` read 30 runtime rows where the checked-in reports read 49, because Doctor's join lets the last citing story win and steward Story 111.1 cites `CAP-1..CAP-168` with a planning Surface; it also admitted a blocked story's Surface, so an unbuilt capability read runtime; and the gate's `flag-pre-rule` warned on 840 specs, 826 of them done, where scope ruling 3 names the warned population as stories already in backlog. **Ruled** (2026-10-26, operator: the CAP-7 retrofit sheet approved as recommended — R4 an exempt `flag-infrastructure` retrofit story covers the flag platform's capability, R6 the warning covers live pre-rule specs only, R8 the join fix is in scope). **For doctor:** a citations join that keeps every citing story (the caller-reach join unchanged), the inventory joining landed stories only and keeping the best class, the warning narrowed to live specs, and the roster's `flag_retrofit_cover_exemptions` read as a capability's cover. Epic 51 / Story 51.1, a fix built in the one-PR retrofit effort; no doctor CAP minted.

## 2026-10-26 — A spike report is not a corrupt file, and the classifier can't yet tell the difference (folded from bmad-drift-new-artifact-shape)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 53.1). The body below is `docs/dreams/bmad-drift-new-artifact-shape.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/bmad-drift-new-artifact-shape.md`.*

## A spike report is not a corrupt file, and the classifier can't yet tell the difference

### The Dream

`pyforge.doctor.sources.factory` (Doctor's port of `scripts/bmad_drift_check.py`, Story
6.8/FR-15) is the single verdict on whether `pyforge-marshal`'s own tracked project docs are
in sync with the live factory. Its `check_coverage` walks the whole
`_bmad-output/projects/pyforge-marshal/` tree and HARD-fails any file `classify()` cannot
name a shape for — "not covered by drift-check — add a classification rule." That rule is
deliberately unforgiving: `classify()`'s own docstring calls an unclassified file "a hole,
not a pass," and the function's body is a long, dated sequence of hand-authored `re.fullmatch`
blocks, each one a git-reviewed response to a *previous* file shape landing as `uncovered` —
fourteen files on 2026-07-28 when the detector was retargeted onto the sharded station
layout, eleven more shapes on 2026-08-08. The mechanism works exactly as designed: a new
shape goes red, a human reviews it, a rule is added, the shape is now covered forever.

On 2026-08-11 (PR #427, Marshal Story 7.6) that mechanism fired a third time.
`_bmad-output/projects/pyforge-marshal/planning-artifacts/spike-0-copier-api-fit-report.md`
— a throwaway design-spike's PASS/FAIL verdict, written straight to the project's
`planning-artifacts/` root because the story's own epics.md `**Surface:**` line said so
("spike report in marshal planning-artifacts") — is a shape `classify()` has never seen:
not `spec-*` (the tracked-spec pattern), not under `specs/`, not one of the eleven prior
one-off carve-outs. It falls through every rule to `UNKNOWN` and trips a HARD `uncovered`
finding in `pixi run -e local-recipes detectors-ci`. The landing agent for that story
confirmed the fix belongs in Doctor's classifier, not in a marshal-package landing, and left
it as CI-red rather than patch code out of scope for that PR.

Running `check_coverage` directly against the live tree confirms the shape is real but
narrow: exactly one file trips it today. Nothing else under `pyforge-marshal`'s tree —
including the sibling spec file `implementation-artifacts/spec-7-6-spike-0-copier-api-fit.md`
that the same story also wrote, which matches the existing `tracked:spec` rule cleanly — is
affected. The naming choice "Spike-0" (epics.md, Story 7.6) leaves open that a Spike-1 could
follow a future Marshal story and repeat the identical shape.

### What it looks like when real

- `classify()` has a rule for the bare "spike report written to `planning-artifacts/` root"
  shape (however precisely scoped — literally `spike-*-report.md`, or a slightly wider
  pattern if the Spec's own research finds one — that is a decomposition-time decision, not
  settled here), so the 2026-08-11 file — and any future Spike-*N* report following the same
  convention — is covered rather than HARD-failing `detectors-ci`.
- The fix is exactly what the last two "shapes that landed as uncovered" incidents already
  were: one small, explicit, git-reviewed classification rule, added the same way, in the
  same function, with the same dated-comment convention the file already uses. Nothing about
  `check_coverage`'s fail-closed default changes — an honestly unrecognized file still HARD
  fails; this closes one specific, now-identified hole in what "recognized" already covers.
- `pixi run -e local-recipes detectors-ci` reports clean for `bmad-drift` again without
  anyone having silently widened the classifier's tolerance for genuinely unexpected files.

### Constraints

- This is a narrow gap-fill for one identified, confirmed shape — not a redesign of
  `check_coverage`'s HARD-by-default posture, and not a general "auto-accept new shapes"
  mechanism. The existing rule that an unrecognized file is a hole, not a pass, stays intact;
  only the recognized set grows.
- No implementation detail is prescribed here — not the exact regex, not whether the rule
  folds into the existing spike-adjacent carve-outs or stands alone, not whether it should
  also anticipate a `Spike-1` before one exists. That is for the Spec and its downstream story.
- This Dream does not extend to the classifier's independence rule (never importing
  `pyforge.marshal`, per the module's own docstring) or its per-check isolation model —
  both stay exactly as they are.

### Realization log

- **2026-08-11** — Captured after `pixi run -e local-recipes detectors-ci` reported one
  `bmad-drift` `uncovered` HARD finding for
  `_bmad-output/projects/pyforge-marshal/planning-artifacts/spike-0-copier-api-fit-report.md`,
  landed by PR #427 (Marshal Story 7.6, the Copier API-fit spike). Marshal's own landing
  agent confirmed the fix belongs in `pyforge.doctor.sources.factory::classify`, out of
  scope for a marshal-package PR, and left it red rather than patch it out of turn. Verified
  by running `check_coverage` directly against the live tree: exactly one file trips it;
  every other file the same story wrote (including its sibling
  `implementation-artifacts/spec-7-6-spike-0-copier-api-fit.md`) already matches an existing
  rule. Queued as a Dream rather than patched by hand, per the operator's standing decision
  (the same treatment as Story 5.8) to route this class of gap through the Dream/Spec/story
  chain instead of a same-session classifier edit — `factory.py`'s `classify()` was
  deliberately left untouched pending the Spec/story.
- **2026-08-14** — Realized — Story 6.11's implementation (commit `c9e59028ff`, stranded on its loop branch by a destructive rearm reset) landed via PR #491; the classifier recognizes the spike-report shape and the SPEC flipped to shipped in the same merge. Status flipped by the 2026-08-14 dream-backlog chain audit.

## 2026-10-26 — Doctor notices when BMAD-METHOD's own installed core falls behind upstream (folded from bmad-method-version-drift)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 53.1). The body below is `docs/dreams/bmad-method-version-drift.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/bmad-method-version-drift.md`.*

## Doctor notices when BMAD-METHOD's own installed core falls behind upstream

### The Dream

Doctor already reports staleness for everything else this fleet depends on — feedstocks
behind upstream, dependency floors behind CVE fixes, artifacts behind their own baseline.
It says nothing today about BMAD-METHOD itself: whether the fleet's declared dependency
floor and its actually-installed `_bmad/bmm/**`/`_bmad/core/**` content agree, or how far
behind the latest upstream release either one is. An operator finds out only by noticing —
the way this Dream's own sibling, [[bmad-method-core-upgrade]], got captured: because the
user happened to remember to check.

The Dream is a standing Finding, wired into Doctor's existing Source/Finding registry the
same way `behind-upstream` already reports stale feedstocks: `pixi.toml`'s declared
`bmad-method` floor, the actually-installed `_bmad/_config/manifest.yaml` version, and the
latest release upstream publishes, diffed and surfaced as one more row in `doctor report` /
the fleet-picture ATTENTION block — never requiring an operator to think to ask.

### What is real

Nothing. Confirmed 2026-08-15, and not hypothetical: `pixi.toml` already declares
`bmad-method = ">=6.11.0"`, but `_bmad/_config/manifest.yaml` — the actually-installed core
— still reports `version: 6.10.0`. The dependency floor was bumped without the installed
content ever being reconciled, and nothing in the fleet noticed or reported it. This Dream
exists to make that class of drift visible on its own, the next time it happens.

### What it looks like when real

- A new read-only Source (mirrors `adoption-stage`'s own wiring, per FR-12's precedent —
  same Finding shape, no new plumbing invented) reads `pixi.toml`'s declared `bmad-method`
  floor, `_bmad/_config/manifest.yaml`'s installed version, and the latest upstream release
  (however Doctor's existing upstream-version machinery already answers that question for
  other dependencies), and reports a Finding whenever any two of the three disagree.
- Surfaces through Doctor's existing report/verdict shape and `fleet-picture`'s ATTENTION
  block — a `warn`, never a `fail` (matches the PRD's own "an incomplete axis gathers as
  `incomplete`, never overstates confidence" discipline; a version-drift Finding is
  informational, not a build-breaking gate).
- Feeds [[bmad-method-core-upgrade]] as an input signal an operator can act on, but does not
  itself trigger anything — Doctor never mutates state (PRD Non-Goals: "No auto-remediation
  actuator in v1... Doctor never opens PRs, patches files, or mutates any state").

### Constraints

- **Read-only, always.** This Dream reports; it never runs `npx bmad-method install` or
  touches `_bmad/**` — that is [[bmad-method-core-upgrade]]'s (owner: steward) territory
  entirely. Mirrors the detect/fix split Epic 8 already established for doctor's own
  deferred-work backlog (`pyforge.doctor` stays read-only by construction; any actuator is a
  sibling script outside the package).
- **Do not duplicate [[bmad-method-core-upgrade]]'s own pre-flight diff.** That Dream may
  still perform its own dry-run diff immediately before an apply — this Dream's job is the
  AMBIENT, continuously-refreshed signal an operator sees without running anything, not the
  upgrade tool's own safety check.

### Non-goals

- Not applying, merging, or reconciling anything — see Constraints.
- Not deciding which currently-unexercised BMAD modules to keep or drop
  ([[one-front-door]]'s own open question).
- Not a general "any dependency is behind" detector — this Dream is specifically about
  BMAD-METHOD's own installed core, because it is a special case (an installed *governance*
  layer with local customizations to protect, not an ordinary pinned dependency) that the
  existing `behind-upstream`-style machinery does not obviously already cover end to end.

### Kinships

[[bmad-method-core-upgrade]] (owner: steward, split off the same day — the apply half of
what was originally one unowned Dream; this Dream is its detection half) ·
[[bmad-module-provisioning]] (realized; the Constraint whose amendment made the split
possible) · [[pyforge-doctor]] (the station; FR-12's `adoption-stage` wiring is this
Dream's direct precedent for "new read-only Source, same Finding shape").

### Realization log

- **2026-08-15** — Dream captured, split off [[bmad-method-core-upgrade]]. That Dream was
  originally one unowned capability spanning both "detect drift" and "apply an upgrade."
  Investigation into resolving its ownership (prompted by the dashboard's ACCOUNTABILITY
  gate refusing to publish over its `unassigned` owner) found the two halves belong to
  different stations by their own existing shape — Doctor already owns ambient, read-only
  staleness reporting elsewhere in the fleet, and its PRD Non-Goals explicitly keep it
  mutation-free, matching this half exactly; Steward owns the mutating apply half. No
  precedent exists for a Dream naming more than one owner (checked against all 100 Dreams at
  the time), so rather than co-own one Dream, it was split into two, kept in sync via
  Kinships. Concrete motivating proof, found during the same investigation: `pixi.toml`
  already requires `bmad-method >=6.11.0` while the installed `_bmad/_config/manifest.yaml`
  still reports `6.10.0` — live drift, right now, that nothing in the fleet currently
  reports.

## 2026-10-26 — A capability is not done until something exercises it (folded from capability-effect-check)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 53.1). The body below is `docs/dreams/capability-effect-check.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/capability-effect-check.md`.*

## A capability is not done until something exercises it

### The Dream

The fleet's ledgers say 737 of 775 stories are `done`, and the fleet is not switched on.
The 2026-09-09 readiness pass found **eighteen** capabilities of one identical shape: a
`done` epic, merged code, a green suite — and a named success criterion that has never
been exercised in the running estate. `risk-tiered-review-depth` is `shipped` with zero
callers outside `tests/unit/test_gate.py`. `marshal-token-economy` is 24/24 `done` with
every layer off. `marshal-parallel-dispatch-fanout` has `max_parallel = 1` everywhere and
has never run a wave. Three of those four were visible only by grepping for call sites;
no board, no detector and no ledger could tell.

The Dream is the cheap, ambient half of the realization gate: a doctor Source that, for
every capability the fleet declares, asks **"is anything reaching this?"** — and says so
in the same breath as `story-status-check` says whether the story landed. Two questions,
side by side, every time anyone runs `detectors`: *did it merge* and *is it in effect*.

It is deliberately not a judgement. It is the difference between "nobody noticed" and
"we chose not to" — the same distinction `chain-completeness`'s INV-A was built to make
one tier up, applied one tier down, to the capability rather than the Spec.

### The join key (named up front, on purpose)

The check joins on **`(spec-slug, CAP-N)`** — the pair `board.py`'s own
`_parse_declared_cap_ids` and `_cited_cap_ids_by_spec` already produce for INV-A. That
key reaches code through the citing story's `Surface:` line in the owning station's
`epics.md`, and reaches evidence through an optional `verified:` line on the CAP itself
in `SPEC.md`. Nothing new is parsed that the fleet does not already parse.

Naming the key in the Dream is not ceremony. This station shipped
[[sibling-dreams-drift]] against a join (`title:`) the estate does not share, and the
detector has been structurally incapable of a finding since the day it merged. The
lesson is written into this Dream's Constraints: **the join must be proven against live
data, not a fixture, before the first story closes.**

### What it looks like when real

- **The cheapest test first: a caller outside its own test file.** For a capability whose
  citing story names Python surfaces, the check asks whether any symbol those surfaces
  define is referenced from somewhere that is not that module and not a test. A `shipped`
  capability whose every reference is a test is reported — warn, named, with the file it
  looked in. This single question would have caught all four marshal cases in one pass.
- **The evidence line, when someone has looked.** A CAP may carry `verified: <date> — <what
  was exercised, where>`. The check renders that line beside the capability, and reports
  a `shipped`/`realized` capability that carries none. This is the "realized versus
  verified" column the Unifying Strategy's own review asked for, made mechanical.
- **It renders beside `story-status-check`.** Same ambient surface, same `detectors` run,
  same report. An operator reading "story 33.4 landed" reads "and nothing calls it" on
  the next line, not three weeks later in a readiness pass.
- **It goes quiet when the fleet is in effect.** A capability with live callers and a
  current `verified:` line produces nothing at all.
- **It fails open, loudly.** When a station's `epics.md` cannot be parsed, or a surface
  path no longer exists, the check says *that* — it never renders "could not look" as
  "looked and agreed" (the second lesson [[sibling-dreams-drift]] paid for).

### Constraints / Non-goals

- **Advisory, always.** Warn at most, never a second PR verdict. Doctor's exit-code
  contract is sole-owned by `pyforge.doctor.verdict.exit_code_for` and pinned by
  `tests/meta/test_verdict_sole_ownership.py`; this Source produces `Finding`s and
  nothing else. The fleet already has exactly one fail-closed gate and this is not it.
- **Fail-open, and say so.** An unreadable `epics.md`, an absent surface path, a station
  with no ledger: each degrades to a named finding, never to silence and never to a hard
  failure.
- **The join key is proven on live data before the first story closes.** A fixture that
  constructs both sides from the same synthetic value cannot reproduce a live failure —
  that is precisely how `sibling-dreams-drift` shipped silent.
- **Not a coverage tool, not a call-graph resolver.** "Has a caller outside its own test
  file" is a textual, whole-word reach over declared surfaces — deliberately cheap,
  deliberately approximate, and honest about it in the finding text.
- **Not a re-implementation of `story-status-check`.** That check answers "did the story
  land". This one answers "is the capability reached". They render together and stay
  separate modules.
- **It does not write.** No status is flipped, no ledger row is moved, no `verified:` line
  is authored by the check. Read-only, per doctor's NFR-1.

### Kinships

[[pyforge-unifying-strategy]] (the criterion's home — steward Story 49.2 mints it there;
this Dream is the implementation half the 2026-09-09 batch relayed to doctor, § 2.3 C8) ·
[[intelligence-hub]] (the re-home: Epic 49's gate moves to `hub:CAP-*` Guards once that
Spec is `ready`; a doctor-side Spec makes that a pointer change rather than a migration) ·
[[sibling-dreams-drift]] (the shape — ambient, warn-only, fail-open, one new Source, one
capability — and the cautionary tale about picking a join key nobody shares) ·
[[marshal-token-economy]] (the motivating pathology in its purest form: 24 of 24 stories
`done`, every layer off) · [[pyforge-doctor]] (the station; `bmad_method.py:9-20` is
doctor's own written precedent for a dedicated module over an extension of an existing
Source).

### Realization log

- **2026-09-09** — Captured. Relayed from steward Story 49.2 by the fleet-readiness
  decision batch (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`
  § 2.3 C8, operator-approved the same day): the *criterion* stays on
  `spec-pyforge-unifying-strategy`; the *implementation* comes home to doctor, because
  every other doctor Source arrived through doctor's own chain and because a steward story
  writing a new module into `src/shared/packages/pyforge-doctor/**` is a foreign edit to a
  doctor-governed surface that `spec-surface-check` would red at merge. The incoming
  surface claim is recorded in `spec-pyforge-doctor`'s memlog the same day. The cheapest
  first test — "has a caller outside its own test file" — comes from the readiness pass's
  marshal-B report § E-6, which found three of marshal's four dormant capabilities visible
  by no other means.
- **2026-09-13** — Realized. Shipped via doctor Stories 21.9 (`c27e8386d8`, the caller-reach
  check), 21.10, and 21.11 (`2bb7bc58f5`, wired beside `story-status-check`), plus a
  surface-path resolver fix (`b2e5b9e948`). `sources/capability_effect.py` walks every
  project under `_bmad-output/projects/` (not a hardcoded station list), joining on
  `(spec-slug, CAP-N)` exactly as specced. Live run against the real fleet: 396 findings
  across steward/warden/marshal/doctor Specs, `pixi run -e local-recipes
  capability-effect-check` exit 0 (advisory, as constrained). `pyforge-doctor-test -k
  capability_effect`: 30/30 pass. This unblocks steward Stories 49.2 and 49.8 (49.8 already
  closed separately, `96387a0730`).

## 2026-10-26 — Chain currency sweep — contracts that are re-derived, not decayed (folded from chain-currency-sweep)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 53.1). The body below is `docs/dreams/chain-currency-sweep.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/chain-currency-sweep.md`.*

## Chain currency sweep — contracts that are re-derived, not decayed

### The Dream

Every Dream→Code chain on the board stays **current the way code stays green** — not by
attention, but by a standing loop. When research moves, the brief that was built from it gets
re-derived. When a spec is re-cut, its PRD follows. When code ships, the retro closes the loop.
The Guildhall's chain audit already *detects* all of this (feeds edges, behind-code,
overtaken — doctor's chain-layers audit, FR-150/FR-192); what it detects, nothing yet
*reconciles*. The 2026-08-26 board carried 26 staleness findings across all eight station
flagships and zero audit-sound chains — every one of them a contract that quietly went out of
date while the factory's eyes were on the code.

The marshal project already lives the answer in miniature: a cheap deterministic detector plus
a BMAD-skill reconciler plus a tracked runbook (`SYNC-RUNBOOK.md`), run on trigger, re-stamped
on completion. This Dream is that two-layer pattern **generalized to the fleet's planning
spines** — one repeatable, parameterized sweep any agent (or any framework, per `AGENTS.md`)
can execute identically.

Three grounding sources, all mandatory, per artifact touched:

1. **The newer upstream artifact** that fired the feeds edge (research wave, spec re-stamp).
2. **The Unifying Strategy** (`spec-pyforge-unifying-strategy` + its companion set — stack,
   console-parity inventory, architecture diagrams, resilience invariants): every station's
   contract states its hub-and-spoke role in the Canopy estate.
3. **The as-built code** in `src/` — the contract is reconciled against what actually shipped,
   never re-derived purely from other documents. Divergence gets written down, not papered
   over.

### What it looks like when real

- A `chain-currency-sweep` detector in the auto-discovered registry: the per-project
  chain-layers audit looped across the eight station slugs, red on any finding — staleness
  surfaces every time anyone runs `detectors`, instead of when someone thinks to look.
- A tracked **runbook** (doctor project) encoding the audit's real mechanics — the feeds
  cascade order, the 2-day grace window, the strict `updated:` frontmatter precedence, the
  finding→remedy map — so a sweep is dispatched, not re-reverse-engineered.
- Each sweep run = eight independent per-station cascades (brief → PRD → arch → epics
  validation, one commit per station, inside one grace window), dispatched as single-story
  work with physical paths, never a shared orchestrator or `bmad-switch`.
- Retros land while they're cheap: any retro-reached station whose code has moved past its
  retro gets one in the same sweep.
- Worked Examples accumulate per run, timeless-workflow style. Run 1 is the 26-finding
  clearance of 2026-08-26 — which is also the runbook's validation pass.
- The sweep itself appears as a chain on the board it maintains.

### What this is not

- Not stamp-gaming: an `updated:` bump without a genuine reconcile is lying to the board; the
  runbook forbids it in as many words.
- Not a second gate: findings stay advisory (doctor's standing constraint) — the sweep is the
  remedy loop, not a new red light.
- Not a replacement for the marshal SYNC-RUNBOOK loop, which keeps its own scope (skill-facing
  volatile facts); this sweep owns the planning-spine feeds edges.

### Realization log

- **2026-08-26 — specified.** `bmad-spec` produced
  `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-chain-currency-sweep/SPEC.md`
  (status `ready`; success bound to `chain-currency-sweep-check` exit 0 across all 8 stations,
  stamp-only diffs forbidden). The detector shipped the same day
  (`scripts/chain_currency_sweep_check.py`, auto-discovered by the registry), and Run 1 — the
  26-finding clearance — executed as eight parallel per-station cascades, validating the
  runbook on its first outing.

## 2026-10-26 — Deferred-work audit completeness (folded from deferred-work-audit-completeness)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 53.1). The body below is `docs/dreams/deferred-work-audit-completeness.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/deferred-work-audit-completeness.md`.*

## Deferred-work audit completeness

### The dream

`pixi run -e local-recipes deferred-work-check` should be able to answer
"does every station's Tier-3 deferred-work record have a durable, tracked
twin?" with full confidence — not just "every entry that already carries a
`## DW-<id>` heading and isn't yet in the tracked ledger." Two real blind
spots survived a full manual fleet audit on 2026-08-15 and would recur on
the next station that ships an old-format or headerless Tier-3 file.

### Why now

A user challenge ("just because a station is complete doesn't mean it has
no deferred work") drove a by-hand, content-level audit of all 8 stations'
`implementation-artifacts/deferred-work.md` against their tracked
`planning-artifacts/deferred-work-ledger.md` twins — not trusting the
`tier3-only-deferral` finding's id-diff alone. It found:

1. **Pre-convention formats are invisible to id-based detection.**
   pyforge-warden's Tier-3 file predates the `## DW-<id>` heading
   convention entirely (`## Deferred from: code review of <spec> (<date>)`
   section headers, no id anywhere) — turned out to be already fully
   promoted and even code-verified (PRs #145-147), so no harm done, but
   the *reason* it read "0 findings" had nothing to do with the detector
   actually checking it. pyforge-atlas's Tier-3 file carries a **second**,
   different pre-convention format: a `bmad-dev-auto step-04 defer
   category` block of flat `- source_spec: / summary: / evidence:`
   bullets with an explicit comment ("one entry per finding") and no id
   or header at all. This one was NOT already promoted — 58 real findings
   (dating back to Story A1, 2026-07) sat undetected in gitignored
   Tier-3 storage, at the exact kind of risk CLAUDE.md's Tier-3 warning
   describes (pyforge-warden's own tracked-ledger preamble: "this repo has
   already lost data that way").

2. **A `#`-prefixed header swallows its own body in a paragraph-level
   content-diff**, producing false "already covered" reads. Bare
   `### DW-<n>: Follow-up review still recommended for <story>...`
   review-budget-followup entries in atlas, marshal, mason, and steward
   were missed by both the id-based detector (their content WAS promoted
   under a different id after a prior session's manual rename, which any
   raw id-string diff can't see) and by an ad-hoc content check built
   during this audit (which skips any paragraph starting with `#`,
   silently including the header+body together and then discarding it as
   "not a bullet to check"). 5 entries recovered by hand once the false
   read was caught.

3. **Doctor already has half the answer.** `_check_project_deferred_work`
   (`pyforge.doctor.sources.chain`) has a Story 7.3 grandfather-baseline
   mechanism (`scripts/.deferred-work-baseline.json`) that already
   detects headerless/anonymous Tier-3 entries beyond a stamped count —
   this is `tier3-entry-unidentified`, and it correctly flagged 72 more
   entries across marshal (30), steward (38), mason (2), and herald (2)
   that this session did NOT attempt to promote (see below). The
   detection half of this capability already exists; only the
   **promotion** half (mint a real id, append to the tracked ledger,
   verify no collision/duplicate) is missing, and doing it by hand
   tonight proved error-prone.

### What went wrong trying to do this by hand (evidence for why this needs
real code, not another one-off script)

Two distinct bugs shipped and were caught only by re-running the detector
after each pass:

- **Content duplication**: a flat-bullet scanner that doesn't check
  whether a `- source_spec:` bullet is already owned by a `##`/`###`
  header directly above it will re-promote already-headed entries under a
  fresh id. Caught by a summary-text uniqueness scan across the whole
  ledger (6 duplicates found in atlas, removed).
- **Structural mismatch across stations**: the same "look at the nearest
  non-blank line above; if it's a header, this bullet is owned" heuristic
  that correctly parsed atlas's flat-append format (one header, one
  bullet, always adjacent) overcounted by roughly 10x on marshal/steward
  (231 and 91 spurious mints against a true count of 30 and 38) because
  those stations' `### DW-FU-<story>` entries can have **multiple**
  `- source_spec:` bullets stacked under one header — a shape the
  heuristic can't distinguish from an orphan. All spurious entries were
  identified via the "pass 3" marker text and mechanically stripped
  before commit; no bad content shipped, but it took two clean-up passes
  including one that (transiently, before being caught by a count check)
  deleted legitimate already-committed content via an over-broad
  string-split filter.

Both incidents were caught before landing because every promotion pass
was followed by a full re-run of `deferred-work-check` plus a
duplicate-id/duplicate-content scan — that verification loop is exactly
what a real implementation should encode as a test fixture, not
re-improvise by hand each time.

### Proposed capability (for `bmad-spec` to size properly — this is a
sketch, not a committed design)

Extend `pyforge.doctor.sources.chain`'s deferred-work check (or a sibling
module) with:

1. **A real entry-boundary parser** that understands all three Tier-3
   shapes seen in production: `## DW-<id>` / `### DW-<id>` headed entries
   (single or multi-bullet body), bare `### DW-<n>: Follow-up review...`
   review-budget-followup entries, and headerless flat
   `- source_spec: / summary: / evidence:` bullets under a top-of-file
   marker comment. Each shape needs its own tested boundary rule — the
   header-ownership question (is this bullet part of the entry above it,
   or an orphan?) is exactly the thing two ad-hoc heuristics got wrong
   tonight.
2. **A promotion mode** (`--fix`, mirroring `spec_surface_check.py
   --write-baseline`'s existing pattern) that mints a collision-free
   `DW-<epic>-<story>-<n>` id per orphan entry (querying the tracked
   ledger's existing max suffix per story, not a fixed starting number),
   appends it with a `status: open` line and a `promoted:` provenance
   note, and refuses to run if it would produce a duplicate id or
   duplicate summary text against the existing ledger.
3. **Extend the Story 7.3 grandfather baseline's role**: today it only
   suppresses re-flagging already-accepted anonymous entries. It should
   also be the input to `--fix` (promote everything *not* covered by the
   baseline, then re-stamp the baseline to the new total).

### Relationship to the sibling Dream

This Dream is "get every real finding into durable, tracked storage,
correctly and without duplication." It says nothing about whether a
tracked entry is still *true* once it's there — that's a distinct,
harder, code-comprehension problem with its own precedent (a fleet-wide
by-hand verification campaign, PR #147, 2026-07-30) and its own proposed
capability: see `docs/dreams/deferred-work-resolution-sweep.md`. The two
share one root-cause bug worth fixing together (a heading-less entry
breaks both this Dream's promotion detection AND that campaign's
`normalize_deferred_ledgers.py` status tracking — the same blind spot,
independently rediscovered six weeks apart) but are different enough in
kind to size as separate stories.

### Known remaining scope (not yet promoted, tracked by the detector today)

`pixi run -e local-recipes deferred-work-check`'s `tier3-entry-unidentified`
finding, as of 2026-08-15, still names real content beyond the grandfather
baseline: **marshal 30, steward 38, mason 2, herald 2** (72 total). These
are not at the same acute loss risk as atlas's flat-append format was
(they're already visible to the detector, just not yet promoted) — but
they are real deferred findings sitting in gitignored Tier-3 storage.
Whoever implements this capability should promote them as its first real
run.

### Realization log

- **2026-08-15** — Seeded (`8fdcb0b15a`) and specified the same day by extending
  `spec-deferred-work-visibility` rather than opening a new Spec (`2ffa858b5d`, CAP-4..10 across the
  three 2026-08-15 doctor seeds; this Dream's share is CAP-4..7 per `specified-by`).

## 2026-10-26 — Deferred-work resolution sweep (folded from deferred-work-resolution-sweep)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 53.1). The body below is `docs/dreams/deferred-work-resolution-sweep.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/deferred-work-resolution-sweep.md`.*

## Deferred-work resolution sweep

### The dream

Getting a Tier-3 finding into the tracked ledger (see the sibling Dream,
`deferred-work-audit-completeness.md`) only proves it survives a worktree
teardown. It says nothing about whether the finding is still *true*. A
tracked `status: open` line is a claim about the code at authoring time —
nobody re-checks it once it lands. That re-check — read the entry, find
the code it names, confirm the defect is still there (or isn't) — is a
distinct capability from promotion, and it has already been proven
valuable exactly once, by hand, and never made repeatable.

### The precedent (2026-07-30, PR #147, `deferred-work-verify-campaign`)

Every tracked entry across the fleet-as-it-existed-then (atlas 57, warden
43, herald 24, marshal 17, doctor 4 — **145 total**, mason/steward/scribe
didn't exist yet) was individually re-verified against live code, entirely
by hand (`bmad-loop-sweep` is automation-only and scoped to the wrong
tier — Tier-3, not the tracked ledger — so it could not be used). What it
found is the whole argument for doing this again:

- **12 entries were already resolved and nobody closed them.** The
  sharpest case: one root defect (`bmad-ui` losing its local
  `./build_artifacts` channel) had been independently hit and fixed
  THREE times across three different stories in three different
  projects, and two of the three ledger entries still read `open`.
- **2 entries got *worse* since authoring** (a duplication bug that
  roughly doubled, a per-entry cost that grew) — a stale `status: open`
  cannot show drift in either direction; only re-reading the code can.
- **5 entries understated their own scope** once the pattern was traced
  to sibling packages that cloned the same defect.
- **1 finding could only be verified by reading a DIFFERENT project's
  code** (`atlas DW-I5-1`'s part (b) turned out to be resolved in
  marshal's `core/policy.py`) — a single-project sweep cannot catch this
  class at all.

That is real, cross-cutting signal a stale ledger entry actively hides.
Full account in auto-memory `project_deferred_work_verification_campaign`.

### Why this needs to become systematic (not just "run it again")

1. **It's badly stale.** The campaign is six weeks old and covered 5 of
   what are now 8 stations. mason (48 tracked entries as of tonight),
   steward (74), and scribe (7) have **never** been verified once. Every
   entry the two promotion passes tonight added (67 in atlas, 5 more
   across marshal/mason/steward) is also unverified from day one — they
   were moved from Tier-3 to tracked storage verbatim, not re-checked
   against current code.
2. **The campaign named its own tooling gaps, and none of them are
   fixed**, meaning a re-run today hits the identical failure modes:
   - `normalize_deferred_ledgers.py` cannot see a heading-less entry
     (undercounted marshal's real deferral count by 2 at the time). This
     is the **exact same blind spot** `deferred-work-audit-completeness.md`
     documents from tonight's atlas/marshal/mason/steward audit — the
     same bug class independently rediscovered six weeks apart because
     nothing fixed the root cause the first time it was named.
   - `warden DW-1-4-1` — marked `done` off the wrong half of two
     deferrals sharing one id — still needs splitting into two ids;
     never done.
   - atlas's own frontmatter declared an `entries: 55` count against 57
     real entries, in a file whose whole job is to declare that count
     correctly.
3. **The protocol that worked is real evidence for what a tool needs to
   preserve**, not just automate: batch 8-14 entries, gather evidence
   with a few wide greps covering many entries per pass, apply results
   via `{id: (status, note)}` (not per-entry `Edit`, since every
   `status:` line is textually identical and unaddressable), commit per
   project, and — the part that resists full automation — **prove each
   verdict by reading or executing the actual code**, not by pattern-
   matching the entry's own prose back at itself. Three entries in the
   2026-07-30 campaign were only correctly resolved by actually running
   the code (AST-evasion, dict-key collapse, schema gap reproduction).

### Beyond the precedent: what a real capability needs that the one-off
### campaign didn't have to solve

The 2026-07-30 campaign was a single, bounded, human-paced push. A
*repeatable* capability inherits every cost problem that a one-time
effort can ignore, plus a few the campaign never had to face because the
fleet was smaller and it only ran once. Thinking past just replaying
warden's protocol:

- **Cost has to be bounded structurally, not by discipline.** ~400+
  tracked entries exist today (atlas 122, marshal 109, steward 74, mason
  48, warden 43, herald 45, doctor 20, scribe 7) and the number only
  grows. A full LLM-driven re-read of every entry on every run doesn't
  scale — this fleet already has two precedents for bounding exactly this
  kind of recurring cost that a resolution sweep should study rather than
  reinvent: bmad-loop's own `limits.max_followup_reviews` damping cap
  (a hard ceiling on repeated review passes per story), and — pointedly
  — **pyforge-warden's own product domain**, which is a compliance gate
  built entirely around baseline/grandfathering/waiver semantics for
  "known finding, don't re-flag every run until something changes."
  Verifying warden's OWN deferred-work ledger with warden's OWN
  baseline-and-waiver *model* (not the tool itself — the design pattern)
  would be a fitting, self-referential fit.
- **Prioritize by what actually could have changed.** Most tracked
  entries name a specific file. If that file has zero commits since the
  entry's last `verified:` (or since authoring, if never verified), the
  entry is a low-value re-read — nothing could have resolved or worsened
  it. `git log --since=<verified-date> -- <path>` per entry is a cheap
  filter that could shrink a "verify everything" sweep down to "verify
  only entries whose named code actually churned," which is where the
  precedent's real findings concentrated anyway (the incidentally-fixed
  and got-worse cases were all in files that had, in fact, changed).
- **Tier the verification itself, not just its scheduling.** Not every
  entry needs an agent to read and reason about code. Some claims are
  mechanically checkable: "raises a bare `KeyError`", "no `try/except`
  around X", "function Y is unused", a named test that does or doesn't
  exist, a count ("N call sites") that a grep can recompute exactly. A
  sweep should attempt a cheap structural/grep-level check FIRST and only
  escalate to an agent read when the claim genuinely requires judgment
  (does this behavior matter, is the scope still accurate, is this really
  resolved). This mirrors `spec_surface_check.py`'s own two-tier design
  (hash-drift is mechanical; `drift-presumed` needs a human to confirm
  the memlog covers it) — worth reusing that shape rather than a new one.
- **Cross-entry and cross-project correlation, not just per-entry
  verification.** The precedent's sharpest finding — one root cause hit
  three times across three projects — was found by a human noticing a
  pattern while reading, not by any structural check. A systematic sweep
  should actively look for near-duplicate entries (same file/symbol
  named across different projects' ledgers, or similar summary text) and
  surface them as a *defect class*, not three independent low-priority
  entries nobody connects. This is the same shape of value BMAD's own
  cross-spec-sync convention already recognizes for specs
  (`feedback_specs_cross_sync` in auto-memory) — deferred-work entries
  deserve the same treatment.
- **Close the loop into future planning, not just the ledger.** Today an
  entry says `owner: Story 4.5` in prose and nothing enforces that Story
  4.5's actual scope addresses it — closing an entry depends entirely on
  someone remembering to grep the ledger when writing that story's spec.
  A resolution sweep's natural complement is a **backlog-intake check**:
  when a new story/spec is drafted for an epic, surface any tracked
  deferred-work entries whose `owner:`/prose names that epic or story, so
  they become candidate acceptance criteria instead of staying inert
  prose forever (or worse, silently missed the way FR-28's attribution
  scope was almost over-built earlier this session before the CRITICAL
  escalation caught it).
- **Handle the "this code doesn't exist anymore" case explicitly,
  distinct from "verified still open."** A file or whole package can be
  deleted, superseded, or a project can move to `shipped`/archived status
  between one sweep and the next (pyforge-atlas's own legacy Kedro
  migration retired entire modules this way). The precedent's protocol
  only had two outcomes it exercised (confirm-still-open,
  confirm-resolved) — a real sweep needs a third: **moot/superseded**,
  closed with the same evidentiary bar (cite what replaced or removed
  the code), not silently dropped and not left open forever pointing at
  nothing.
- **Surface staleness as an ongoing signal, not just a campaign trigger.**
  `fleet_picture.py`'s ATTENTION block already aggregates cross-cutting
  fleet health (it grew a baseline-drift check this very session). A
  "% of tracked entries verified within N days, per project" line there
  would make the NEXT six-week staleness gap visible incrementally
  instead of requiring another pointed user challenge to notice it went
  quiet again.
- **Escalation, not forced resolution.** Some entries will be genuinely
  undecidable by reading code alone (a design-tradeoff entry, a
  "revisit when Story X lands" entry where Story X hasn't landed yet).
  The sweep needs a legitimate third verdict beyond
  open/resolved — **still-pending-on-a-named-precondition** — so it
  doesn't force a false confirm just to close the loop, the same failure
  mode `feedback_verify_before_destructive_or_debt_claims` warns against
  in a different context.

### Proposed capability (sketch — size properly via `bmad-spec`)

A repeatable resolution sweep, likely agent-driven rather than purely
mechanical (verifying "is this defect still in the code" is not a
parseable fact the way "does this id exist in file X" is):

1. **A due-for-verification selector**: every tracked entry gains (or
   already has, per the 2026-07-30 convention) a `verified: <date> —
   <verdict>` line. A sweep should be able to select entries with no
   `verified:` line at all (everything promoted since the last real
   campaign — currently ~150+ entries across mason/steward/scribe plus
   tonight's fresh promotions) or with a `verified:` date older than
   some staleness threshold, batched per project the way the precedent
   did it by hand.
2. **Fix the machinery gaps the precedent already named** before or
   alongside building this: `normalize_deferred_ledgers.py`'s
   heading-less blind spot (shared root cause with the promotion-side
   Dream — worth fixing once, used by both), the still-unsplit
   `warden DW-1-4-1`, and a self-consistency check so a project's
   declared entry count can't silently drift from the real count again.
3. **Batch dispatch to a verification agent** per the proven protocol:
   read the entry, locate the named code, confirm/refute by reading or
   executing it, write a `verified:` line with the same evidentiary bar
   the precedent set (a `file:line` or a measured/reproduced count, not
   a restatement of the entry's own claim) — and, critically, **do not
   silently narrow scope**: if an entry claims 2 packages and the sweep
   finds it now affects 8, that's the finding, not a reason to leave the
   `2` uncorrected.
4. **Cross-project reach**: the precedent's `atlas DW-I5-1` case shows a
   per-project sweep structurally cannot catch a fix that landed in a
   sibling project's code. Whatever selects work for a batch should be
   able to look at any project's source tree, not just the owning
   project's.

### Realization log

- **2026-08-15** — Spec'd as `spec-deferred-work-resolution-sweep` (pyforge-doctor), CAP-1..8, decomposed into Epic 11 (Stories 11.1-11.8). CAP-8's own scope-boundary question (this Dream's "backlog-intake check" bullet above) left open at spec time.
- **2026-08-21** — **CAP-8 split into its own companion Spec, `spec-backlog-intake-check`** (operator decision, tracked `DW-11-8-1` in pyforge-doctor's deferred-work-ledger.md pending it). Epic 11 shipped cleanly as Stories 11.1-11.7, a self-contained read-only sweep pipeline; bundling CAP-8's write-adjacent, story-drafting-time capability into it after the fact would have muddied that result. This Dream remains the owner-dream for both Specs — the "resolution sweep" (periodic re-verification, CAP-1..7) and the "backlog-intake check" (drafting-time surfacing, `spec-backlog-intake-check`'s CAP-1) are two capabilities this one Dream always named, now two Specs.

### Relationship to the sibling Dream

`deferred-work-audit-completeness.md` is "get every real finding into
durable, tracked storage, with a correct id, without duplicating or
colliding." This Dream is "once it's there, periodically confirm it's
still true." They share one root-cause bug (heading-less entries breaking
both `deferred-work-check`'s promotion detection and
`normalize_deferred_ledgers.py`'s status tracking) worth fixing together,
but the promotion problem is a parsing problem and the resolution problem
is a code-comprehension problem — different enough in kind that they
should very likely be scoped as two stories, not one, when this reaches
`bmad-spec`.

## 2026-10-26 — A deferral that nobody can see is a deferral that never happened (folded from deferred-work-visibility)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 53.1). The body below is `docs/dreams/deferred-work-visibility.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/deferred-work-visibility.md`.*

## A deferral that nobody can see is a deferral that never happened

### The Dream

`deferred_work_check` exists to guarantee one thing: that work a review pass chose to defer
reaches a **tracked, durable ledger** instead of dying in a gitignored Tier-3 file that no
clone will ever have. It reports `OK: every Tier-3 deferral has a tracked twin` and exits 0.

It cannot see **470 of them**.

The dream is that the guarantee is real — that "every deferral has a tracked twin" means every
deferral, not every deferral that happens to carry an id.

### What is real

**The measurement, taken with the detector's own parser** (`_anonymous()`, 2026-08-10) — not a
grep, because a grep over `source_spec:` bullets overcounts by including the fields inside
identified entries:

| station | ID'd | anonymous |
|---|---|---|
| marshal | 12 | 202 |
| doctor | 4 | 72 |
| steward | 1 | 56 |
| atlas | 12 | 54 |
| warden | 2 | 41 |
| herald | 1 | 26 |
| mason | 1 | 13 |
| scribe | 0 | 6 |
| **total** | **33** | **470** |

**The mechanism.** `_DW_RE` (`scripts/deferred_work_check.py:71`) harvests `DW-*` ids from the
Tier-3 file and the tracked ledger and compares those two **sets**. `bmad-dev-auto`'s mandated
defer format (`.claude/skills/bmad-dev-auto/step-04-review.md`) writes bare `- source_spec:`
bullets with **no id at all**. Anonymous entries therefore appear in neither set and are never
compared; the identified ones all do have twins, so the comparison passes and the detector
reports success.

**Proven by execution, not inference** — the finding came from story 4-14's own review pass,
which recorded the commands: `grep -c 'spec-4-14-…'` on Tier-3 returns 11, `grep -c '4-14'` on
the tracked ledger returns 0, and `deferred_work_check.py` nonetheless prints `OK` and exits 0.

**Half the machinery already exists, and is already hardened.** `_anonymous()` parses exactly
this shape, and its docstring records this same vacuity class being caught once before and
fixed by mutation testing — *"an earlier version latched `seen_id` true until the next heading,
which made it unable to see an anonymous entry in any file that had at least one id… proved by
mutation: deleting an id heading did not red the detector."* It is called on the **tracked**
ledger only, never on the Tier-3 file.

**A grandfathering precedent exists in-house.** `spec-pyforge-warden` already ships
baseline-and-grandfathering for exactly this shape of problem: a real gate that would otherwise
red on a large pre-existing backlog.

### What it looks like when real

- A review pass defers something and the entry carries an identity from birth, under the
  station's own convention — `DW-FU-<story>` for doctor/atlas/marshal/warden, `DW-<story>-<n>`
  for mason. The convention is the station's, not a fleet-wide imposition.
- `deferred_work_check` sees anonymous Tier-3 entries and says so.
- The 470 that already exist do not red every landing pass on day one. They are baselined, and
  the gate bites on what is **new**.
- The count of invisible deferrals goes to zero and stays there, because nothing new can be
  created without an id.

### The shape of the answer

Both sides move, in order. **Neither alone is sufficient, and the ordering is not arbitrary:**

1. **The emitter first.** `bmad-dev-auto` writes ids. This stops producing invisible entries
   and reds nothing.
2. **The detector second, with a baseline.** `_anonymous()` is called on the Tier-3 file too,
   the existing 470 are grandfathered, and the gate applies to new entries.

Detector-first would turn one green check into **470 findings overnight**. Every landing pass
would fail, and the realistic outcome is that the finding gets suppressed — strictly worse than
today, because then it is suppressed *and* invisible. Emitter-only stops the bleeding but
leaves all 470 permanently unseeable.

### The ordering constraint that decides where the code goes

**`scripts/deferred_work_check.py` is one of the eight shims doctor story 6-9 deletes.** Its
logic moves into `pyforge.doctor.sources`' `REGISTRY`. Confirmed against 6-9's branch:
`D scripts/deferred_work_check.py`.

So a fix written against the shim is **work thrown away**. The detector half belongs in
Doctor's `sources/`, which places it after — or deliberately alongside — the 6-9 rewiring the
operator has chosen to land on purpose rather than as a side effect.

### Why this is not just a fix

It is cross-station (all eight ledgers), it changes a skill file every future story uses, it
needs a grandfathering decision, and it has a hard ordering dependency on another story's
landing. That is a contract, not a patch.

### Open questions

- **Who owns which half?** The detector half looks like Doctor's — Epic 6 has spent six stories
  re-homing exactly these verdicts. The emitter half looks like Marshal's — it owns loop
  orchestration and the `bmad-dev-auto` skill. Splitting one effort across two stations needs
  deciding rather than assuming.
- **Are all 470 worth keeping?** They accumulated unseen. Some may be stale, duplicated, or
  already resolved. Grandfathering them wholesale preserves noise as well as signal; triage may
  be cheaper than it looks, or may be a second effort.
- **Does the emitter assign ids, or does promotion?** Ids could be minted by `bmad-dev-auto` at
  defer time, or by the promotion step that moves an entry into the tracked ledger. The first
  makes Tier-3 self-describing; the second keeps id-minting in one place. Marshal Story 4.13
  already automated the promotion step, which argues for the second — but 4.13 promotes by id,
  so it inherits the same blind spot.
- **Should the tracked ledger's own anonymous entries red too?** `_anonymous()` already reports
  them there. If Tier-3 gains the same check, the two sides should agree on severity.

### Non-goals

- **Not a rewrite of the deferral format.** The existing entries carry real content; only
  identity is missing.
- **Not a change to what gets deferred.** Review passes decide that; this is about durability
  of the record, not the decision.
- **Not a fleet-wide id convention.** Stations already differ (`DW-FU-<story>` vs
  `DW-<story>-<n>`) and that difference is deliberate. Whatever ships must respect the
  station's own precedent.
- **Not coupled to landing 6-9.** The ordering constraint is real, but this Dream does not
  force that landing's timing.

### Realization log

- **2026-08-10** — Seeded from a finding in marshal story 4-14's review pass, which proved the
  blind spot by execution rather than inference. Measured fleet-wide with the detector's own
  `_anonymous()` parser (470 anonymous vs 33 identified) after an initial grep estimate was
  identified as an upper bound and discarded. Operator asked for the Dream explicitly, on the
  grounds that repo tooling deserves a chain rather than a patch smuggled into a landing pass.

- **2026-08-10** — Specified, recorded by the fleet audit (Phase 2b): the Spec's four
  open questions were closed (`377611d5e4`) and it stands at `ready`; doctor 6-9 (the
  sequencing dependency) landed via PRs #394/#395. Decomposition-ready.

## 2026-10-26 — One home for leftover docs — fold into Diátaxis, same page for agents and humans (folded from docs-shelf-alignment)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 53.1). The body below is `docs/dreams/docs-shelf-alignment.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/docs-shelf-alignment.md`.*

## One home for leftover docs — fold into Diátaxis, same page for agents and humans

> **Seed Dream.** Operator asked 2026-09-14 to make the leftover-docs sweep
> repeatable as Dream → Spec → stories, not a chat cleanup. This is the
> **residue** of [[general-docs-consistency]] after Epic 22 shipped — not a
> reopen of that realized campaign. Scribe recall the same morning
> (`scribe recall "general documentation Diátaxis docs alignment shelf fold"
> --mode planning`) → **no grounded answer** beyond the shipped Spec.

### The Dream

The general-facing documentation layer has **one home per fact**, in the
Diátaxis-adapted tree [[general-docs-consistency]] already designed
(`docs/MAP.md`, tutorials / how-to / reference / explanation). Related pages
fold into that one page. `AGENTS.md`, `CLAUDE.md`, `README.md`, and station
`SKILL.md`s are **indexes and wielding notes** — they point, they do not
restate. If a page is useful to a human operator, it is useful to an agent;
there is no second binder "for humans only."

Leftover shelf prose — root notes, intake dumps, dated campaign stamps,
legacy `docs/specs/` husks, and brownfield guides that duplicate the
quadrants — is routed: fold, archive, or keep as a named exception on the
MAP. The routing is a **repeatable capability**, not a one-session canvas.

### Why this is a sibling, not a reopen

[[general-docs-consistency]] is `realized`. Epic 22 (Stories 22.1–22.6)
fixed identity contradictions, shipped `general_docs_consistency`, designed
the map, populated tutorials/how-to, and repointed entry files. Its Spec
`spec-general-docs-consistency` is `shipped`. CAP-4..6 **explicitly forbade**
touching `docs/specs/` and `_bmad-output/*/planning-artifacts/`.

That prohibition is why the leftover shelf is still here. This Dream
**widens** that non-goal for a second campaign: sunset legacy Tier-1 specs
*by their own `status:` frontmatter*, and **extract** unique operational
prose from marshal brownfield binders into `docs/` (the planning tree stays;
the binder becomes a stub). CAP-1..6 stay shipped. Nothing here unships them.

### What is real (measured 2026-09-14, not remembered)

- `docs/MAP.md` exists and names four quadrants plus an "outside this map"
  table. Story 22.6 shipped (`local-recipes#1257`) and still left
  **redirect stubs** at `docs/reference/{manticore-studio,antigravity-developer-startup,mcp-server-architecture,enterprise-deployment}.md`.
- Legacy `docs/specs/*.md` **do** have disposition: YAML `status`
  (`shipped` / `workflow` / `in-progress` / `superseded`). Live split:
  3 `workflow` (presentation-deck, feedstock-platform-expansion,
  feedstock-failure-remediation), 2 `in-progress` (feedstock-refresh, flyte),
  the rest shipped or superseded. `bmad-drift --specs` and `CLAUDE.md`'s
  index still read this folder.
- Intake dumps have **no** per-file `status:` / `disposition:`.
  `docs/intake/README.md` and `docs/intake/gists/INDEX.md` are the ledgers.
  Open folders named there: `agentic-sdlc/` (feeds pitched
  [[agentic-sdlc-autonomy]]), `jira-github-projects-sync/` (Dream
  `specified`), `secure-live-dashboards/` (Dream `specified` — intake is
  leftover). Five `_bmad-output/` root notes already moved to
  `archive/_bmad-output/`; inbound citations still point at the old paths.
- Marshal `development-guide.md` says it is **for humans**; agents should
  read `project-context.md` and `SKILL.md`. That split is the same failure
  mode Epic 22's CAP-2 already punished in README vs CLAUDE. The file is
  also a mixed tutorial+how-to+reference binder whose header disagrees with
  itself on pixi env/task counts.
- Air-gap facts live in at least three places:
  `docs/explanation/enterprise-deployment.md`,
  `docs/how-to/air-gapped-mirror-setup.md`, marshal `deployment-guide.md`,
  plus the `docs/reference/enterprise-deployment.md` stub.
- `docs/dashboard/` is a **publish root**, not a quadrant. The live tree is
  already `docs/dashboard/kedro-viz/` (generated Pages upload). Vizro is a
  different product ([[secure-live-dashboards]]). Do not rename kedro-viz
  to vizro.
- Operator pass-2 rule, accepted in the shelf-sweep canvas: **one owner per
  fact, in `docs/`**. Fold clusters, not thirty one-off moves.

### What it looks like when real

- A newcomer and an agent hit the same tutorial / how-to / reference /
  explanation page for the same fact. Entry points are thin pointers.
- The three `workflow` legacy specs have become how-tos (or a how-to plus
  archived husk). Shipped and superseded Tier-1 files live under
  `archive/docs/specs/`. The two in-progress files stay until those
  efforts close, then archive.
- Intake is empty of anything a Dream already specified or absorbed.
  Gist leftovers follow `INDEX.md`.
- Marshal brownfield binders are stubs that point at `docs/`. Unique
  steps were folded, not copied a third time.
- `archive/_bmad-output/` citations resolve. Redirect stubs are gone
  after the pointer sweep.
- A Doctor check (or an extension of `general_docs_consistency` / MAP
  hygiene) fails when a new leftover-shelf file appears outside the map
  and the intake/archive rules — warn-only, fail-open, never a second
  PR gate.

### Non-goals

- Reopening or rewriting Epic 22 / CAP-1..6. Identity fixes and the
  existing detector stay as shipped.
- Moving Dreams, active Tier-2 Specs, or gitignored Tier-3 output into
  Diátaxis. Extracting *duplicate operational prose* from a brownfield
  guide is in scope; relocating `epics.md` is not.
- Regenerating accurate prose "for consistency." Fold and correct;
  do not rewrite from scratch.
- Renaming `docs/dashboard/kedro-viz/` to vizro.
- Minting Dream YAML onto raw gist dumps.
- A full editorial pass of every skill, presentation, or recipe README.

### Kinships

- [[general-docs-consistency]] — parent; realized; this is the residue.
- [[bmad-output-hygiene]] — archived; same class of leftover
  `_bmad-output/` debris, already campaigned once.
- [[secure-live-dashboards]] — specified; owns the Vizro pattern, not
  the kedro-viz publish tree.
- [[agentic-sdlc-autonomy]] — pitched/specified; owns `archive/docs/intake/agentic-sdlc/`.
- [[jira-github-projects-sync]] — specified; owns that intake folder
  until the operator decision.
- [[enterprise-airgap]] — realized; air-gap fold must not invent a
  second contract.
- [[pyforge-marshal]] — brownfield binders live under its planning tree.
- [[pyforge-doctor]] — owning station; detector half.

### Settled 2026-09-14 (Spec `ready`)

1. **Workflow specs — stub, not a full move.** Archive shipped/superseded
   to `archive/docs/specs/`. Keep `in-progress` in place. Move each
   `workflow` body to `docs/how-to/`; leave `docs/specs/<name>.md` as a
   stub with `status: workflow` so `bmad_drift_check.py --specs` and the
   CLAUDE.md filename index still see them.
2. **Brownfield — extract, then stub.** Unique operational steps go to
   Diátaxis. Binders become pointers to `docs/` plus `SYNC-RUNBOOK.md`
   for pin re-ground. Do not keep a humans-vs-agents pair.
3. **New Doctor source**, not an extension of `general_docs_consistency`
   (that module is identity-only).
4. **Doctor Epic 23.** Steward stays kinship only.
5. **Do not mint `docs/dashboard/vizro/` now.** MAP states the rule;
   the directory appears when that board publishes.

`spec-docs-shelf-alignment` is `ready`. Epic 23 decomposes CAP-1..7.

### Realization log

- **2026-09-14** — Seeded (`4e533c54e7`) from the operator's ask to make the leftover-docs
  sweep repeatable as Dream → Spec → stories; the same day `spec-docs-shelf-alignment` was
  settled at `ready` and Epic 23 decomposed CAP-1..7 (§ *Settled 2026-09-14* above).
- **2026-09-17** — Folded into [[pyforge-doctor]] by the doctor one-chain-per-station fold
  (`4d3ae19674`): `status: specified` became `archived` with `archived-reason:
  folded-into-station-dream`, and the *Consolidated into* banner was added. New work appends
  to the station Dream.
- **2026-10-10** — The [[agentic-sdlc-autonomy]] Kinship now names
  `archive/docs/intake/agentic-sdlc/`, repointed when doctor Story 37.1 retired the legacy
  `docs/specs/` tier (`c9e4f1539c`).
- **2026-10-24** — This log added from the file's own text and `git log --follow` (doctor
  Story 30.4); no status change.

## 2026-10-26 — Fleet hygiene, verification & exemplar-standard program (folded from fleet-hygiene-verification-exemplar-program)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 53.1). The body below is `docs/dreams/fleet-hygiene-verification-exemplar-program.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/fleet-hygiene-verification-exemplar-program.md`.*

## Fleet hygiene, verification & exemplar-standard program

### The dream

Tonight's deferred-work audit found two things at once: a real gap (58+
findings invisible to the detector that's supposed to catch exactly
that), and a *pattern* — this is not the first time this fleet has needed
a one-off, by-hand sweep to catch something no always-on gate watches for.
This Dream is the catalog: every recurring hygiene / verification / audit
/ dashboard-metric / exemplar-standard need this fleet has actually hit,
organized by what already has a Dream, what's mechanically gated today,
what's been done once by hand and never systematized, and what has never
been done at all. The goal is not to build all of this — it's to stop
re-discovering the same shape of gap in isolated sessions six weeks apart
(the `normalize_deferred_ledgers.py` heading-less blind spot was named
once on 2026-07-30 and hit again, independently, on 2026-08-15) by making
the whole landscape visible in one place first.

**Exemplar is the load-bearing concept, not one category among six —
and it already has a real document, not just a memory of one.**
`_bmad-output/EXEMPLAR-STANDARD.md` (see Category 5) designates
`pyforge-atlas` as the exemplar for the whole planning-artifact shape and
states the invariants + conformance table that define "done and clean"
structurally, fleet-wide. Categories 1-4 and 6 answer "is X true /
tracked / fresh / bug-free" — necessary, but none of them say what "fully
done and clean" actually *looks like* for a given kind of artifact.
Category 5's exemplars — `EXEMPLAR-STANDARD.md` foremost, plus the
narrower deck/test-architecture/recipe-pattern ones alongside it — are
that definition. Read the other categories as instruments that measure
conformance *to* an exemplar (or flag that no exemplar has been
designated yet for a given artifact class) rather than as a parallel,
unrelated set of checks. Where no exemplar exists yet for something
Categories 1-4 or 6 name, that absence is itself a finding this catalog
should surface — "we can check whether this drifted, but we've never
actually said what 'not drifted' should look like." And where an
exemplar document DOES exist, as `EXEMPLAR-STANDARD.md` proves, it needs
the same freshness discipline as everything else here — see Category 5's
note on its now-stale conformance table.

### Category 1 — Mechanically gated today (the six detectors + meta-suite)

`python -m pyforge.doctor.sources` exposes 10 subcommands:
`bmad-drift`, `chain-completeness`, `check-layout`, `dashboard-drift`,
`deferred-work`, `dream-chain`, `forward-dependency`, `ledger-regression`,
`spec-surface`, `story-status`. These are the fleet's real always-on
floor — deterministic, CI-enforced, exit-code gated. Tonight's audit
proved even a mechanical detector can have a real blind spot
(`deferred-work`'s `tier3-only-deferral` finding is id-diff-based and
cannot see a headerless or pre-convention Tier-3 entry) — so "mechanically
gated" is not the same claim as "complete." Each of these deserves the
same "is what it actually checks the same as what it claims to check"
scrutiny `deferred-work` just got, on its own schedule, not just when a
user happens to challenge one.

**A second one is already confirmed, in a different detector.**
`chain-completeness`'s INV-A decides "this open Spec is decomposed" with a
bare substring test — does the Spec's slug appear anywhere in the
project's PRD/epics prose (`board.py:463-477`). It parses no `CAP-` ids on
either side. So a Spec can grow from 3 capabilities to 10 and still report
`ok -- every open Spec is decomposed` while seven of them have no story
anywhere in the fleet. Found by execution on 2026-08-15 against
`spec-deferred-work-visibility`, and logged as `DW-CHAIN-COMPLETENESS-1`
in pyforge-doctor's tracked deferred-work ledger. It is structurally the
*same* defect class as the one the extended Spec exists to fix — which is
the point of this category: these are not one-off bugs, they are a
recurring shape, and finding the second one within hours of the first is
the evidence.

### Category 2 — Has its own Dream already (don't re-derive, just link)

- **Deferred-work promotion** (Tier-3 → tracked ledger, id-collision-safe,
  format-complete) — `docs/dreams/deferred-work-audit-completeness.md`,
  **now `status: specified`**: converged into the pre-existing
  `spec-deferred-work-visibility` (CAP-4..7) rather than a new spec-kernel,
  after that Spec's own Q2 turned out to have already named this exact
  follow-on. This Dream's own fleet-wide hygiene-sweep angle (Category 3
  below) converged the same way, as CAP-8/9.
- **Deferred-work resolution** (is a tracked entry still true) —
  `docs/dreams/deferred-work-resolution-sweep.md` (still `status: dreamt`
  — deliberately NOT folded into the same Spec; it's a code-verification
  problem, not a promotion/detection one, and spec-deferred-work-visibility
  names it as a distinct future effort pending its own convergence check).
- **`engine.pid` two-field liveness footgun** (a float+identity string
  misread as a bare pid, corrupting `marshal status`, `fleet-picture`,
  and `dashboard-gen`'s in-flight card alike) —
  `docs/dreams/bmad-loop-liveness-footgun.md` (captured 2026-08-14/15,
  still unspecced per the `dream-chain` detector).

### Category 3 — Done once by hand, never systematized (the real gap
### class this Dream exists to name)

- **`bmad-output-hygiene` sweep** (`CAP-1` dead test scaffolding
  archival, `CAP-2` hollow `sprint-status.yaml`, `CAP-4` README
  placeholders, `CAP-5` orphan files, `CAP-12` stale currency pairs, plus
  a stale-Dream-status flip and a "research-dot" bug fix) — run once,
  for one project (pyforge-warden, commits `bfa9fd68`/`1567a478`/
  `5c5e3727`/`22da995c`/`f7654a4c` on 2026-08-14/15). Never run against
  the other 7 projects. Each `CAP-*` is itself a small, well-scoped
  hygiene check that could become a `pyforge.doctor.sources` subcommand
  the same way `deferred-work`'s Story 7.3 grandfather baseline did —
  but right now it's a memory of a manual session, not a tool.
- **Repo-wide audit remediation waves** (`AUD-CFE-*`, `AUD-REPO-001`
  findings, PRs #131/#133-138) — a broad, one-time repo audit whose
  findings were fixed but whose *audit methodology* was never turned into
  a repeatable check. Worth asking: did the underlying audit questions
  ("is PR #131's remediation actually runnable", the class of question
  that motivated wave 2) get a permanent gate, or just a one-time fix?
- **Deferred-work resolution campaign itself** (see Category 2) — already
  has its own Dream; listed here too because it's the sharpest example of
  this whole category's failure mode: done once, named its own tooling
  gaps, gaps never fixed, gap rediscovered independently six weeks later.
- **Loop-home branch staleness** — tonight's session found all 4 active
  stations' `loop/pyforge-<slug>` branches 55-60 commits behind
  `origin/main` (confirmed pure ancestors, fast-forwarded by hand after
  explicit user authorization). Nothing watches for this — a station
  could re-spin from a stale branch and silently miss weeks of fixes to
  shared infrastructure (the exact `spec-django-accelerator-framework`
  spec-surface-drift-blind bug earlier this session was independently
  rediscovered by 3 stations *because* their branches hadn't caught up).
  A `fleet-picture` ATTENTION line ("loop/pyforge-X is N commits behind
  main") would have surfaced this without a user having to ask "want
  those fast-forwarded" out of nowhere.

### Category 4 — Dashboard / fleet health metrics (the visibility layer)

`fleet_picture.py`'s ATTENTION block already aggregates cross-cutting
health (it grew the baseline-drift check this very session — a good
exemplar of "a finding this shape belongs in the ambient report, not just
a detector run someone has to remember to invoke"). Candidate additions
surfaced by tonight's work alone:
- **Deferred-work verification staleness** — "% of tracked entries with a
  `verified:` date, per project" (ties directly to the resolution-sweep
  Dream).
- **Loop-home branch staleness** — commits-behind-main per
  `loop/pyforge-<slug>` (Category 3, above).
- **`dream-chain` gap count** in the ambient report rather than only a
  separate detector run — `bmad-loop-liveness-footgun.md` sitting
  unspecced is exactly the kind of thing that should nag quietly instead
  of waiting to be noticed.
- The published **GuildHall Fleet Status Dashboard**
  (`docs/reference/GuildHall_Fleet_Status.md`,
  https://rxm7706.github.io/local-recipes/) is the human-facing mirror of
  all of this — worth asking, as this program matures, which of these
  new signals belong on that board too, not just in the CLI report.

### Category 5 — Exemplar / golden-standard references (a different kind
### of "audit" — quality-bar conformance, not correctness)

Everything above is about *correctness* (is this still true, is this
tracked, is this fresh). This category is about *quality* — this fleet
has already designated several artifacts as the standard other work
should match.

**The primary one is not a memory entry — it's a real, structured
document: `_bmad-output/EXEMPLAR-STANDARD.md`.** It designates
`pyforge-atlas`'s `planning-artifacts/` tree as the single exemplar for
the entire 16-stage Dream-to-Code chain (Dream · Deck · Spec · Rsch ·
Brief · PRD · UX · Arch · Context · Epics · Sprint · TEA · Gates · Code ·
Tested · Retro), states five binding invariants (INV-0..INV-5 — one Spec
per Dream, one build-tree shape, detector self-ownership, one canonical
convention register), carries an explicit conformance table scoring every
other station against it, and names its own detector
(`scripts/dream_chain_check.py`) as the mechanical arbiter. This is not
aspirational prose — it's the closest thing this repo has to Category 5's
own answer to "what does 'done and clean' mean," already partially
mechanically enforced, and it should be the anchor everything else in
this category is checked against or modeled on, not a peer example.

**Its conformance table is stale on exactly the row this session's work
touched.** The table (`## Conformance status`) scores a "DW ledger"
column and shows only `pyforge-atlas` as ✅, with warden, doctor, mason,
herald, scribe, steward, and marshal all ❌. That was true when the table
was last written — it is not true now. Tonight's two promotion passes
gave every one of those projects a real, populated, git-tracked
`deferred-work-ledger.md` (warden 43 entries since 2026-07-29, atlas 122,
marshal 109, mason 48, steward 74, herald 45, doctor 20, scribe 7). This
is a live instance of the exact failure mode `EXEMPLAR-STANDARD.md` warns
about in its own text ("a detector's own bugs propagate outward as
confident, wrong numbers") — except here it's the *document*, not a
detector, that went stale, because nothing re-runs `dream_chain_check.py`
against a state change like this one and reconciles the hand-written
table against it. Refreshing that table (and checking whether the other
columns — companions, story specs, delivery records, README — are
equally stale) is a concrete, bounded, immediately-actionable first task
for whoever picks this Dream up — arguably before anything else here,
since it's the one place in Category 5 that already has teeth.

Below that primary reference, the fleet also carries several
narrower, purely-manual exemplars with no mechanical backing at all:
- **The six-act deck framework** (`docs/reference/reference_six_act_deck_framework.md`
  equivalent in auto-memory — cover hook, Acts I-VI, appendix personas,
  L.A.T.C.H. visual principles) — the canonical template for all 21
  station decks.
- **Warden-standalone as the infographic exemplar** (Design `100ca8cc`,
  user-designated best) — the shape reference for server-side infographic
  work.
- **"Full depth + acts for ALL Herald deck/infographic work"** — a
  standing instruction that work should never be size-restricted at
  authoring time, i.e. the exemplar sets a *floor*, not a target to
  economize against.
- Recipe-domain exemplars inside `conda-forge-expert` itself (the
  canonical npm recipe pattern, the v0↔v1 about-field mapping) — same
  shape: a hand-curated "this is what good looks like," consulted by
  convention, never checked mechanically.
- Narrower canonical-*form* conventions, same failure mode at smaller
  scale: BMAD conda-forge specs must use CFE's `add-recipe-<name>`
  branch-naming convention (drift here was found once, 2026-06-10 S1
  retro, and is easy to silently reintroduce in a future hand-authored
  spec since nothing checks it).

Two data points on what "graduating" an exemplar out of pure convention
looks like — worth studying as the aspirational end-state for the ones
still purely manual above, not just naming the gap:
- **The universal conda-forge.yml pre-seed** started as a hand-maintained
  convention (established 2026-06-16), got a per-setting applicability
  audit (G83) that corrected real drift in it, and is now **auto-emitted
  by the recipe generator itself** — the exemplar became the default,
  so there's nothing left for an author to forget. This is the target
  shape a lightweight checklist should aim for, not settle for.
- **Herald's TEA+Playwright test-architecture was designated the fleet's
  canonical reference** (2026-08-02 decision) specifically so the other
  7 stations wouldn't each re-derive their own test strategy — and,
  checked directly while writing this Dream, the fleet-wide rollout
  actually happened: all 8 stations carry a real
  `planning-artifacts/test-architecture.md` today (Category 3's own
  `bmad-output-hygiene` sweep independently confirms this — one of its
  fixes was replacing several stations' *fabricated* test-architecture
  files with real ones). A genuine success case of an exemplar becoming
  a fleet-wide standard through a repeatable script rather than staying
  a one-station reference nobody else copies.

For the exemplars still purely manual (the deck/infographic family,
recipe-domain patterns), the open question is the same one these two
success cases answer differently: does becoming mechanical mean baking
the standard into a generator/template (conda-forge.yml's path), or does
it mean a repeatable apply-to-the-whole-fleet script plus a durable
"is this still the reference" check (Herald's path)? Worth deciding
per-exemplar when this program is sized, not assuming one shape fits all
of Category 5.

### Category 6 — Named ledger/artifact machinery bugs (small, concrete,
### currently untracked as their own fix)

Bugs specific enough to fix directly rather than needing a whole Dream,
but real enough that they shouldn't just live in a memory file:
- `normalize_deferred_ledgers.py`'s heading-less-entry blind spot (shared
  root cause between Category 2's two deferred-work Dreams).
- `warden DW-1-4-1` — still needs splitting into two ids (named
  2026-07-30, never done).
- `scripts/spec_surface_check.py --write-baseline`'s unlocked
  read-modify-write race on `scripts/.spec-surface-baseline.json` — named
  as a deferred finding by this very session's atlas promotion
  (`DW-13-5-2`), real given this repo's own documented history of
  concurrent-agent races on shared per-worktree state.

### What this Dream is NOT

Not a commitment to build all of this. Not a spec — none of these
categories are sized, prioritized against each other, or scoped for
implementation here. The point is narrower: the next time someone (human
or agent) is about to spend a session rediscovering "huh, nothing
actually checks for X" for some X that rhymes with one of the six
categories above, this file should be the first thing they read, so the
finding lands as "yes, catalogued, category 3, still not done" rather
than as a fresh, isolated discovery that fades from context again in six
weeks.

### Realization log

- **2026-08-15** — Seeded (`92355c3eba`) as the catalog of recurring hygiene, verification,
  audit, dashboard-metric and exemplar needs, beside `deferred-work-resolution-sweep`, with
  `_bmad-output/EXEMPLAR-STANDARD.md` refreshed in the same commit. The same day its
  hygiene-sweep angle (Category 3) converged into `spec-deferred-work-visibility` as CAP-8/9
  (`2ffa858b5d`; Category 2 records it), and the second confirmed detector blind spot
  (`chain-completeness` INV-A, `DW-CHAIN-COMPLETENESS-1`) was added to Category 1
  (`fbde190a47`).
- **2026-09-05** — `title:` added from the H1 by the dreams-hygiene sweep (`e4016f4aa1`);
  status stayed `dreamt`.
- **2026-09-17** — Folded into [[pyforge-doctor]] by the doctor one-chain-per-station fold
  (`4d3ae19674`): `status: dreamt` became `archived` with `archived-reason:
  folded-into-station-dream`, `type: dream` was added, and the *Consolidated into* banner
  was added. New work appends to the station Dream.
- **2026-10-24** — This log added from the file's own text and `git log --follow` (doctor
  Story 30.4); no status change.

## 2026-10-26 — General documentation stops contradicting itself, and stays that way (folded from general-docs-consistency)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 53.1). The body below is `docs/dreams/general-docs-consistency.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/general-docs-consistency.md`.*

## General documentation stops contradicting itself, and stays that way

### The Dream

This repo's BMAD-tier documentation already has real hygiene detectors —
`capability-effect-verified`, `status-body-consistency`, `sibling-dreams-drift`,
`dreams-hygiene` — all owned by Doctor, all catching the same underlying failure
mode: a claim that used to be true and silently isn't anymore. None of them reach
the **general, human-facing documentation layer**: `README.md`, `CLAUDE.md`,
`AGENTS.md`, station `README.md`s, `.claude/skills/*/skill-brief.yaml`, and
`docs/dreams/*.md`'s own identity claims about what each PyForge station *is*.
That layer has never had a detector, and a two-pass live audit this session
(2026-09-11) proved it needs one. The initial framing was that the tree itself
is fine — `docs/reference/`, `docs/intake/`, `docs/dreams/`, `docs/specs/`,
`archive/docs/` are internally coherent and deliberately maintained — and only
the *content* drifts and contradicts itself across files nobody cross-checks.
That first half still holds for the BMAD spec-driven tier specifically (see
Non-goals). But "internally coherent" is not the same claim as "recognizable
to someone arriving with no prior context" — see the second finding below,
which widens this Dream to cover that gap too.

**Confirmed evidence, this session, each independently verified by direct
file reads before being trusted:**

1. **Doctor's own README contradicts three other authoritative sources about
   itself.** `src/shared/packages/pyforge-doctor/README.md` claims doctor
   consolidates warden + cf_atlas signals into "its own exit-code gate."
   `.claude/skills/pyforge-doctor/skill-brief.yaml`, `CLAUDE.md`'s SKF block, and
   `AGENTS.md` all say explicitly: "Findings stay advisory — not a second PR
   gate," "never a competing PR verdict." "Gate" is a loaded, specifically-owned
   term in this repo (Warden legitimately is one); Doctor's README borrows it
   for a station that everywhere else is defined by NOT being one.
2. **`AGENTS.md` and Herald's own Dream assign the identical named
   responsibility to two different stations.** `docs/dreams/pyforge-herald.md`:
   *"Not infrastructure — BMAD monorepo/multi-project machinery and
   cross-agent portability belong to [[pyforge-marshal]] (the 2026-07-23
   ownership review...)."* `AGENTS.md`: *"Keeping the Dream → spec handoff
   portable across agents is **Herald's** job."* Herald's own Dream disclaims
   this by name, citing a dated ownership review; `AGENTS.md` — the highest-
   visibility cross-tool entry point in the repo — hands it back anyway.
3. **`README.md`'s "GitHub Actions Workflows" section describes 4 of 19 real
   workflow files** and claims CI is "manual trigger only to preserve quota" —
   false for the 15 it omits, several of which (`staged-recipes-linter.yml`,
   `detectors.yml`, `coverage-gates.yml`, `pyforge-station-tests.yml`,
   `platform-ci.yml`) are the repo's actual automatic PR-gate CI.
4. **`README.md` contradicts itself within the same file.** Its own "Project
   structure" tree lists `docs/bmad-setup-plan.md` and `docs/developer-guide.md`
   — neither exists at those paths (real paths: `archive/docs/bmad-setup-plan.md`,
   `docs/reference/developer-guide.md`) — while the SAME file's own prose,
   fifteen and one hundred lines later respectively, cites the correct paths.
5. **The active-project-resolution-priority list is duplicated verbatim in
   `README.md` and `CLAUDE.md`,** with `CLAUDE.md`'s copy carrying the
   two-symlink mechanism and the parallel-agents hazard that `README.md`'s
   copy omits entirely — one fact, two owners, already unequal.
6. **`CLAUDE.md` states two different station counts in the same file.** Line
   30 names all 8 PyForge Guild stations; its own "SKF Skills" block, further
   down, says "7 skills" and lists 7 — omitting Mason. (Mason genuinely has no
   `.claude/skills/pyforge-mason/` — confirmed deliberate, documented policy in
   `AGENTS.md`, not a gap — but the SKF block doesn't say so, so a reader hits
   an unexplained-looking discrepancy.)

A **light identity-consistency pass on the other 6 stations** (atlas, marshal,
mason, scribe, steward, warden) found nothing comparable — so this is not "the
whole fleet's documentation is rotten," it's "two specific stations and five
specific shared-doc facts have drifted, and nothing would have caught it."

**Second finding, operator-directed (2026-09-11), widening the Dream:** the
content-correctness problem above is real, but it is not the whole complaint.
The operator's own framing: *"content is incorrect and outdated and
inconsistent, [and it] does not align to a standard or structure that people
are familiar with, e.g. Diátaxis — with just adaption / limited customization
to fit BMAD-METHOD and PyForge needs."* The general-facing documentation layer
this Dream scopes (`README.md`, `CLAUDE.md`, `AGENTS.md`, station `README.md`s,
`docs/reference/`, `docs/intake/`, onboarding/operational material) has no
recognizable information-architecture lens applied to it — a newcomer has no
Diátaxis-shaped map of "where do I start" vs. "how do I do X" vs. "what's the
exact config/CLI surface" vs. "why does this work this way." `docs/reference/`
already accidentally IS most of a Diátaxis "Reference" quadrant; nothing plays
the "Tutorials" (learning-oriented, get-something-running) or "How-to guides"
(task-oriented, operational) roles explicitly, so that content is scattered
across `README.md`'s "Common Commands," `docs/reference/developer-guide.md`,
and skill-scoped guides instead of living somewhere a newcomer would predict.

**This is explicitly an *adaptation*, not an import.** The BMAD spec-driven
tier — `docs/dreams/` (Tier 0), `docs/specs/` (Tier 1, legacy),
`_bmad-output/*/planning-artifacts/` (Tier 2), gitignored
`implementation-artifacts/` (Tier 3) — is Diátaxis-orthogonal: it is not
"documentation" in the sense Diátaxis addresses (explaining a working system
to its users), it is the spec-and-build pipeline itself, already coherent, and
explicitly out of scope for restructuring (see Non-goals). Diátaxis's four
quadrants apply only to the general/human-facing layer this Dream already
scoped in its first finding.

**What this Dream asks for, now in two parts:**

1. **Content correctness** (the original ask, unchanged): fix the confirmed
   instances (the 2 identity conflicts + 4 cross-cutting decay findings above),
   AND make it a repeatable capability rather than a one-off cleanup — a Doctor
   detector (or an extension of an existing one) that periodically
   cross-references what a station's README/skill-brief/Dream/AGENTS.md say
   against each other and flags a real divergence, the same discipline
   `capability-effect-verified` already applies to BMAD specs, applied one
   layer up to the general docs a human actually reads first.
2. **Structural adaptation** (new): reorganize the general-facing documentation
   layer only — `README.md`, `docs/reference/`, `docs/intake/`, and any
   onboarding/operational content currently scattered outside them — into a
   Diátaxis-shaped map (something like Tutorials/Getting Started, How-to
   Guides, Reference, Explanation), customized to this repo's real needs
   rather than a generic four-folder template. `docs/reference/`'s existing
   content is the seed of the Reference quadrant, not something to discard and
   rebuild. `CLAUDE.md` and `AGENTS.md` stay where they are (tool entry
   points, not general docs) but gain corrected, non-duplicated pointers into
   the reorganized structure. The downstream Spec (already drafted once
   against this Dream's narrower first version, now stale) needs re-deriving
   against this expanded scope before any restructuring work starts.

### Non-goals

- **The BMAD spec-driven tier is out of scope, full stop.** `docs/dreams/`,
  `docs/specs/` (legacy Tier 1), `_bmad-output/*/planning-artifacts/`, and
  gitignored `implementation-artifacts/` are not touched, moved, merged, or
  reorganized by this Dream — they are a different layer (the spec-and-build
  pipeline, not general documentation) with their own already-coherent
  convention, documented at length in this repo's own `CLAUDE.md`.
- **Diátaxis is adapted, not imported wholesale.** No generic
  `/docs/getting-started/` + `/docs/guides/` + `/docs/reference/` scaffold
  bolted on regardless of fit — the new structure grows from what's already
  here (`docs/reference/` survives as the Reference quadrant's home) and is
  sized to this repo's actual content volume, not a template's assumed shape.
- **Content is relocated and corrected, not regenerated.** Moving a file into
  the new structure and fixing a confirmed contradiction in it is in scope;
  rewriting accurate prose from scratch "for consistency" is not — the same
  surgical discipline as the original content-correctness finding, now applied
  to files that also move.
- Not a call graph or NLP-based "meaning" checker for the repeatable-detector
  half — matching Doctor's existing detectors' own discipline (bounded,
  textual, explainable, never a false green), not a heavier tool than the
  problem needs.

### Realization log

- **2026-09-11 (operator-directed widening)** — Scope expanded from
  content-correctness-only to include a Diátaxis-adapted restructure of the
  general-facing documentation layer, per the operator's own stated
  motivation (content is "incorrect and outdated and inconsistent" AND
  "does not align to a standard or structure that people are familiar with").
  The BMAD spec-driven tier stays explicitly out of scope (see Non-goals);
  this is an adaptation of Diátaxis to this repo's existing `docs/reference/`
  seed, not an import of a generic four-folder template. The Spec already
  drafted against this Dream's original, narrower version
  (`_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-general-docs-consistency/`)
  is now stale and needs re-deriving via `bmad-spec` against this widened
  Dream before any restructuring work starts.
- **2026-09-11 (later, same day)** — Spec re-derived via `bmad-spec` against
  the widened Dream (6 capabilities, self-validate PASS on both passes).
  Decomposed into doctor Epic 22 (Stories 22.1-22.6), minted `backlog`, per
  the operator's own request to get this Dream dispatch-ready for `marshal`.
  Status: dreamt → specified.
- **2026-09-11 (later, same session)** — Epic 22 drained 6/6, dispatched via
  `marshal factory dispatch`. Story 22.1: the two identity contradictions
  fixed at their source (`local-recipes#1251`). Story 22.2: the four
  cross-cutting decay findings corrected (`local-recipes#1253`). Story 22.3:
  the repeatable `general_docs_consistency` doctor detector, recovered from
  an orphaned dispatch session and finished by hand (`local-recipes#1254`).
  Story 22.4: the Diátaxis-adapted information architecture designed
  (`local-recipes#1252`). Story 22.5: the Tutorials/How-to quadrants
  populated (`local-recipes#1256`). Story 22.6: `README.md`/`CLAUDE.md`/
  `AGENTS.md` repointed into the reorganized structure (`local-recipes#1257`).
  All six capabilities in `spec-general-docs-consistency/SPEC.md` are done;
  the Spec and this Dream both close as `shipped`/`realized`. Status:
  `specified` → `realized`.
- **2026-09-14 (residue — leftover shelf)** — Epic 22 shipped the map
  (`docs/MAP.md`), the four quadrants, the identity detector, and entry-point
  pointers. A live shelf sweep the same day (operator + pass-2 fold analysis)
  found the **leftover class** that campaign's own Non-goals left on the
  table: dated `_bmad-output/` notes, intake dumps with no disposition
  frontmatter, three `workflow` files still living in legacy `docs/specs/`,
  marshal brownfield binders that tell humans and agents to read different
  pages, and air-gap / getting-started facts still copied in three places.
  That residue is **not a reopen of CAP-1..6**. It is the next campaign, seeded
  as [[docs-shelf-alignment]] (`docs/dreams/docs-shelf-alignment.md`, Spec
  `spec-docs-shelf-alignment`, `draft`). This Dream stays `realized` — the
  first campaign ran. The sibling owns fold, sunset-by-status, dual-audience
  indexes, and the repeatable check that the shelf does not grow back.

## 2026-10-26 — Every pixi.toml dependency — in or out, floor or latest — carries a live reason, not a silent guess (folded from pixi-candidate-currency)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 53.1). The body below is `docs/dreams/pixi-candidate-currency.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/pixi-candidate-currency.md`.*

## Every pixi.toml dependency — in or out, floor or latest — carries a live reason, not a silent guess

### The Dream

`pixi.toml`'s `[feature.local-recipes.dependencies]` block (and its `pypi-dependencies` /
`target.*` siblings) has accumulated **44 commented-out candidate packages** across 64 lines —
some with a one-line reason trailing the entry, most with none at all. Today the only way to
know whether any one of them is genuinely blocked, safely addable, dead upstream, or just never
revisited is to re-derive it from scratch — which is exactly what happened this session for
`caveman`, `headroom-ai`, `codegraph`, `ppt-master`, `ocrmypdf`, and (transitively, via the
click conflict it shares with `headroom-ai`) the `dbt-*` trio. Each of those took real
investigation — conda-forge repodata queries, actual `pixi install` solves, upstream release
notes — to answer a question that, once answered, should never need re-answering unless the
world underneath it changes.

The deeper discovery this session made: **most of these 44 already have a local recipe**, many
already built successfully (`cfe-local-build-status: success`), several already confirmed live
on conda-forge or SelfExplainML. The packaging half of the work is frequently *done* — what's
missing is a tracked answer to "why isn't this in the environment, then," which today lives
nowhere but a git blame and a half-line trailing comment.

This is one half of a single problem; the other half is the mirror image. `pixi.toml` already
carries a canonical bulk-upgrade command (top of file, 19 excludes, each with an inline reason)
for *active* dependencies the maintainer already knows are deliberately held back below latest.
What's missing is the same accounting for everything else already IN the environment: is a given
active package at its true latest, and if not, is that a *choice* or a *conflict*, and if a
conflict, *whose*? The literal trigger: "what is blocking the latest networkx, what's blocking
latest click" — both answerable, and both illustrate the two shapes this half takes. `networkx`
is already on the canonical exclude list (`2.4.*`, "pinned for conda-build compat" — a choice,
documented, done). `click` is not excluded at all, isn't even directly declared, and is stuck at
`8.2.1` while conda-forge ships `8.4.2` — because `conda-recipe-manager 0.10.5` hard-pins
`click==8.2.1` exactly (a feedstock bug — its own `pyproject.toml` declares click unpinned),
which is the *exact same* root cause already named above as the reason `headroom-ai` and the
whole `dbt-*` trio can't be added. One root cause, symptoms on both sides of the comment
boundary — which is why this stays one Dream, not two.

### What it looks like when real

- Every commented-out `pixi.toml` entry carries a **disposition** answering one of five
  questions definitively: *blocked* (a real, currently-verified conflict, with a re-check
  trigger named — new upstream release, ecosystem migration landing), *archived* (upstream is
  dead; no action possible, ever), *stale* (a dead duplicate or superseded entry; delete it),
  *ready* (verified clean, just needs the line uncommented), or *unexamined* (nobody has
  checked yet — the honest default, not a guess dressed as one).
- Re-checking a `blocked` disposition is cheap because the trigger condition is named, not
  because someone remembers to look — the same "re-derive, don't decay" discipline
  [[chain-currency-sweep]] applies to planning-spine artifacts, applied here to a dependency
  ledger instead.
- A `blocked` disposition that shares a root cause across multiple packages (the
  `conda-recipe-manager` `click==8.2.1` pin blocks `headroom-ai` *and* the entire `dbt-*`
  trio identically) is recorded once, not rediscovered three times.
- The same discipline applies to ACTIVE dependencies stuck below their true latest: a
  `blocked` disposition names the **exact** upstream package + spec doing the blocking, found
  by scanning what our *actually-resolved* builds declare in `depends`/`constrains` — not
  inferred, read directly off conda-forge's repodata for the builds genuinely in our lock.
  `platform-gap` (the newest release genuinely hasn't shipped a build for one of our three
  platforms/python 3.14 yet) is a distinct disposition from `blocked` (a real, fixable-elsewhere
  version conflict) — the fix path differs (wait vs. an upstream feedstock PR).
- The canonical upgrade command's exclude list and this Dream's `deliberate` bucket are the same
  list, checked against each other — an exclude with no reason, or a real block missing from the
  excludes, is the kind of drift [[chain-currency-sweep]] exists to catch elsewhere.

### What is real

Verified this session, each via an actual `pixi install` solve or a real local build — not
inferred from comments:

- **Added**: `ppt-master` (base deps, SelfExplainML noarch build) and `codegraph` (linux-64
  target, SelfExplainML linux-64-only build) — both solve clean, zero downgrades.
- **Blocked, root-caused**: `headroom-ai` and the `dbt-core`/`dbt-duckdb`/`dbt-postgres` trio
  all hit the *same* wall — `conda-recipe-manager`'s feedstock pins `click==8.2.1` exactly,
  which conflicts with anything needing `click>=8.3`. This is a documented upstream feedstock
  bug (`pixi.toml`'s own dbt comment already names it), not something fixable in this repo.
  `caveman` is blocked separately — it hard-requires `nodejs>=26.5.0`, which conflicts with
  `marp-cli`'s `nodejs` 22/24 pin; this environment hasn't adopted nodejs 26 yet (a separate,
  already-documented `a2a-sdk`/`libabseil` conflict).
- **Reconfirmed still valid**: `ocrmypdf`'s linux-64-only placement (its hard dep `pngquant` is
  still absent from conda-forge's `osx-arm64`/`win-64` repodata, verified live).
- **Fixed at the source, not here**: `pngquant`'s own osx_64 cross-compile bug (a
  `PKG_CONFIG_ALLOW_CROSS` gap in `libpng-sys`'s build.rs) was root-caused and patched in the
  upstream feedstock PR (conda-forge/pngquant-feedstock#16) — once that merges and pngquant
  ships win-64/osx-arm64, `ocrmypdf`'s own gate can be revisited.

**Addendum 2026-08-30 — the click wall fell, and caveman got a patched build (all
solver-verified, landed):**

- **`headroom-ai` ACTIVE (0.37.0, all platforms) + `dbt-core`/`dbt-duckdb`/`dbt-postgres`
  ACTIVE**: the shared `conda-recipe-manager` `click==8.2.1` wall was removed rather than
  waited out — nothing in this repo invokes `crm`/`conda_recipe_manager`/`feedrattler`
  (verified: zero task/script/source hits), so `conda-recipe-manager` + `feedrattler` (which
  transitively requires it) moved out of `feature.grayskull`/`feature.local-recipes` into a
  new grayskull-env-only `[feature.crm.dependencies]`. Migration tooling still runs via
  `pixi run -e grayskull …`; feedstock PR #44 closed unmerged 2026-09-01 (2026-10-10
  correction); crm 0.10.6 caps click >=8.2.1,<=8.4.1 and lifting that cap is Story 67.4
  sbom-crm-click-cap if local-recipes ever needs click 8.5.x. Note the
  false-dawn on the way: headroom-ai 0.37.0's `pixi search` listing appeared click-free, but
  anaconda.org repodata shows every 0.37.0 build carries `click >=8.3.3` — the wall was real
  until crm left the env.
- **`caveman` ACTIVE (2.4.0 build 2, linux-64 target)** via a patched SelfExplainML rebuild:
  the blocker was SHARPENED first — not (only) marp-cli's nodejs, but `codegraph` 1.6.0's own
  `nodejs >=24.19,<25` run-export makes caveman (build 1: `nodejs >=26.6,<27` run-export from
  a host that resolved 26.6.0) mutually exclusive with an active Layer-2 instrument. Upstream's
  true floor is `engines >=18`, so build 2 holds host nodejs at `24.*` and its run-export lands
  inside codegraph's window (`recipes/caveman` documents the hold + lift trigger: the env
  moving to nodejs 26 once the marp-cli/a2a-sdk libabseil gap closes).

**Active-dependency version currency** (the other half of this Dream): a full audit pass, same
session, grounded entirely in live solver output and repodata — not guessed. Parsed `pixi.lock`'s
`local-recipes` environment (1147 packages on linux-64), diffed against fresh conda-forge
repodata to find everything below latest (149), then used `pixi update --dry-run` (re-solves
*within existing manifest constraints*, no manifest edits) as the oracle for "genuinely stuck" vs
"just a stale lock nobody refreshed": 38 of 149 were stale-lock only; **111 stay capped even
after a full re-solve**. Of those:

- **Root causes found and solver-verified for 8 packages**, collapsing to 6 distinct upstream
  culprits: `conda-recipe-manager==8.2.1` (blocks `click`, and per the candidate ledger above,
  `headroom-ai`/`dbt-*`); `instructor`'s `constrains: anthropic==0.76.0` (a soft constraint,
  G67-class, binding because `anthropic` is separately active — blocks `anthropic` and
  transitively `langchain-anthropic`) plus its hard `depends: rich>=13.7.0,<15.0.0` (blocks
  `rich`); `conda-smithy`'s `depends: py-rattler>=0.22,<0.23` (blocks `py-rattler` and
  transitively `pixi-to-conda-lock`); `pytorch`'s + `vsts-python-api`'s `setuptools<82` caps
  (block `setuptools`); `panel-core`'s `bokeh>=3.7.0,<3.10.0` cap; `conda`'s own
  `ruamel.yaml>=0.11.14,<0.19` cap.
- **One platform-support gap solver-verified directly**: temporarily bumped `pyarrow`/
  `pyarrow-all`'s floor to `25.0.0` and re-ran `pixi update --dry-run` for real (edit reverted
  after) — `pyarrow-core 25.0.0`'s osx-arm64 build needs *either* `python>=3.13,<3.14.0a0`
  (conflicts with this workspace's python 3.14 floor) *or* an unreachable `libabseil` window — a
  genuine upstream platform gap, not a local conflict, plausibly explaining the ~20-package
  Arrow/AWS-C transitive cluster too.
- **One hard, unfixable-locally ceiling**: `speechrecognition 3.17.0`'s own build declares
  `python>=3.10,<3.13` — no py3.14 build exists yet.
- **Two checked but left genuinely undiagnosed** (`diffusers`, `conda` itself — small deltas,
  no offending cap found in this pass).
- **All 93 remaining packages evidence-verified, not left as hypotheses**: for each, either a
  currently-locked package's own `depends`/`constrains` excludes the latest version, or the
  target's own newest build introduces a new requirement conflicting with something already
  locked. Every finding was traced through its full chain to a terminal package, and every
  terminal package was independently confirmed to already be at ITS OWN conda-forge latest —
  these are real upstream compatibility caps, not stale locks. 59 trace to 34 distinct terminal
  packages (`aws-sdk-cpp` alone blocks 13 — the single highest-leverage check), 28 are
  same-recipe-family siblings needing a coordinated bump rather than an upstream fix, 4
  (`grpcio`/`grpcio-status`/`libgrpc`/`libabseil`) are a genuine multi-producer ecosystem
  version-diamond (G97-class — no single feedstock fix, needs convergence across release
  trains), and 2 are deliberate tradeoffs (bumping would force downgrading something kept newer
  on purpose) — see the version currency ledger below.

### The full candidate ledger

Grouped by disposition. "Local recipe" = a `recipes/<name>/` directory exists in this repo
(most already do); "cfe build" is that recipe's own `cfe-local-build-status` field where one is
recorded.

#### ✅ Resolved this session

| Package | Location | Outcome |
|---|---|---|
| `ppt-master` | base deps | Added — bumped 4.2.0→5.1.0, built, published to SelfExplainML |
| `codegraph` | linux-64 target | Added — SelfExplainML linux-64-only build |

#### 🔴 Blocked — real, verified conflict (re-check trigger named)

| Package | Local recipe / build | Conflict | Re-check when |
|---|---|---|---|
| `headroom-ai` | ✅ success | `conda-recipe-manager` pins `click==8.2.1`; headroom-ai needs `click>=8.3.3` | `conda-recipe-manager-feedstock` relaxes the pin (upstream `pyproject.toml` already declares unpinned `click` — it's a feedstock bug, not an upstream constraint) |
| `dbt-core` | build status unrecorded | same `click==8.2.1` conflict (dbt-core needs `click>=8.3.0,<9.0`) | same fix as above |
| `dbt-duckdb` | build status unrecorded | transitively blocked by `dbt-core` | same fix as above |
| `dbt-postgres` | ❌ failed (cf: confirmed-on-conda-forge) | same `click` conflict | same fix as above |
| `caveman` | ✅ success (SelfExplainML, this session) | needs `nodejs>=26.5.0`; conflicts with `marp-cli`'s `nodejs` 22/24 pin | this env adopts nodejs 26 (blocked on a separate `a2a-sdk`/`libabseil` conflict) OR marp-cli 4.5.0 is adopted |

#### ⚫ Archived / no action possible — upstream is dead

| Package | Why |
|---|---|
| `agntcy-acp` | upstream project archived |
| `python-a2a` | upstream stalled, no updates |
| `imaginairy` | flagged outdated/unmaintained on conda-forge |

#### ⚪ Stale — dead duplicates or superseded entries, safe to delete without investigation

| Package | Line | Why |
|---|---|---|
| `ocrmypdf` | 1596 (base deps) | already active in the linux-64 target block — this is a dead second copy |
| `pyarrow` | 1515 | superseded by the already-active `pyarrow-all` in the same block |
| `pydantic` | 1410 (`>=2.11.9,<2.13`) | superseded by the second, newer-pinned entry at 1635 |
| `networkx` | 1420 (`2.4.*`) | exact duplicate of the identical entry at line 57 |
| `ixi-build-go` | 1468 | **typo** — missing leading `p`, should read `pixi-build-go` (currently can't even be found under this name) |

#### 🟡 High confidence — packaging already done, worth trying first

Local recipe exists, `cfe-local-build-status: success`, and upstream availability is already
confirmed (conda-forge or SelfExplainML):

| Package | On | Note |
|---|---|---|
| `networkx` | conda-forge | recipe flags a `missing-license-file` blocker — check before adding |
| `tomli-w` | conda-forge | clean |
| `mybmad-dashboard` | staged-recipes PR #33513 (pending) | linux/osx only per its own recipe note |
| `bmalph` | staged-recipes PR #33557 (pending) | we verified this exact PR **green** earlier this session (as a side effect of the caveman-installer PR fix) — likely close to merge, worth checking PR state before re-investigating |
| `bmad-autopilot` | pending-submission | unix-only |
| `claude-mem` | pending-submission | — |
| `litellm` | conda-forge, confirmed | pixi.toml's own comment says "NOT ADDED — Tier-3 LLM router" — investigate why it was deliberately held back before assuming it's just unexamined |
| `ibis-framework` | conda-forge, confirmed | `missing-license-file` blocker flagged, same as networkx |
| `agent-framework` | pending-submission | recipe exists, never built locally (`not-attempted`) |

#### 🟠 Known local build failures — investigate the recorded failure before retrying

| Package | Recorded status |
|---|---|
| `appthreat-vulnerability-db` | failed — `missing-license-file` blocker ×3 (likely multi-output) |
| `pydantic` (active entry, line 1635) | failed |
| `streamlit` | failed — `missing-license-file` blocker |
| `pygwalker` | failed (separately, also has its own upstream `python-quickjs`-on-osx-arm64 gap noted inline) |
| `chainlit` | build-clean-test-blocked (artifact built; test env solve blocked) |

#### ⚪ Special case — likely stale, needs re-verification against this session's own work

| Package | Recorded blocker | Why it's suspect |
|---|---|---|
| `langflow` | `blocked-pending-prerequisites`: langflow-base, lfx, opendsstar | This session's own ancestor work (the `langflow-suite` bundle: langflow-base + langflow + lfx + langflow-sdk) built, tested, and submitted to staged-recipes successfully. This local recipe's blocker list almost certainly predates that and needs a fresh check, not a repeat of the original investigation. |

#### 🔵 Recipe exists locally, no CFE build record — genuinely unexamined, but packaging groundwork may already exist

`regex`, `portalocker`, `dlt`, `perspective`, `django-pygwalker`, `crawl4ai`,
`azure-identity-broker`, `microsoft-agents-m365copilot`, `kedro-dagster`, `generator-code`,
`crewai`. Several of these (`regex`, `portalocker`, `dlt`, `django-pygwalker`) carry a
`meta.yaml` alongside `recipe.yaml` — this repo's convention for mirroring a feedstock that's
**already deployed on v0 conda-forge**, meaning these are plausibly already on conda-forge and
simply never re-tried in this environment.

`microsoft-agents-m365copilot` is worth flagging specifically: the pixi.toml entry names only
the bare package, but a full 14-recipe local closure already exists
(`microsoft-agents-activity`, `-copilotstudio-client`, `-hosting-aiohttp`, `-hosting-core`,
`-m365copilot`, `-m365copilot-beta`, `-m365copilot-core`, plus the eight `microsoft-kiota-*`
recipes it depends on) — investigating this one means investigating the closure, not one
package.

#### ⬜ No local recipe at all — genuinely never investigated

`oras-py`, `conda-tree`, `pixi-build-nodejs`, `pixi-devenv`, `pixi-browse`, `nebi-desktop`
(already carries a real blocker note — `webkit2gtk4.1` needs `__glibc>=2.34`, unsatisfiable —
so this one is closer to *blocked* than *unexamined*), `aichat`, `vscodepy`, `daft`,
`pyarrow-all` (only inside the fully-commented scratch template at the bottom of the file, not
the active `pyarrow-all` already in use elsewhere), `m2-bash`, `posix` (this exact package name
is independently flagged in a skill gotcha as deprecated in favor of `m2-base` on Windows).

### The version currency ledger

The mirror image of the candidate ledger above: ACTIVE dependencies stuck below their true
conda-forge latest even after a full `pixi update --dry-run` re-solve within existing manifest
constraints (111 of 149 found below-latest; 38 were stale-lock only and excluded here as
non-findings).

#### Already deliberate — on the canonical exclude list, each with a stated reason (no action)

`conda-libmamba-solver`, `conda-build`, `conda-index`, `conda-forge-ci-setup`,
`conda-forge-pinning`, `frozendict`, `networkx` (`2.4.*` — conda-build compat),
`rattler-build-conda-compat`, `grayskull`, `conda-recipe-manager` (excluded from the *upgrade*
command, but its own pin is exactly what blocks `click` below — exclusion from upgrade attempts
doesn't mean its effects are excluded), `conda-smithy` (`<4` — CalVer needs `conda`, absent
here), `shellcheck`, `nodejs` (`<27.0,!=25.*` — LTS-track policy), `python`, `django` (`<6.0`,
paired with `wagtail<8.0`), `channels`, `daphne`, `wagtail` (`<8.0`), `coderedcms`.

#### 🔴 Blocked — root cause solver/repodata-verified, exact culprit named

| Package | Locked → Latest | Blocked by |
|---|---|---|
| `click` | 8.2.1 → 8.4.2 | `conda-recipe-manager==8.2.1` (exact pin, feedstock bug) |
| `anthropic` | 0.76.0 → 1.2.0 | `instructor`'s `constrains: anthropic==0.76.0` (binds because anthropic is separately active) |
| `rich` | 14.3.4 → 15.0.0 | `instructor`'s hard `depends: rich>=13.7.0,<15.0.0` |
| `langchain-anthropic` | 1.3.1 → 1.7.0 | transitively via `anthropic` above (1.7.0 needs `anthropic>=0.120.0`) |
| `py-rattler` | 0.22.0 → 0.25.0 | `conda-smithy`'s `depends: py-rattler>=0.22,<0.23` |
| `pixi-to-conda-lock` | 0.4.3 → 0.4.5 | transitively via `py-rattler` above (0.4.5 needs `py-rattler>=0.24,<0.25`) |
| `setuptools` | 81.0.0 → 84.0.0 | `pytorch`'s `depends: setuptools<82` + `vsts-python-api`'s `depends: setuptools<82.0a0` |
| `bokeh` | 3.9.2 → 3.10.0 | `panel-core`'s `depends: bokeh>=3.7.0,<3.10.0` |
| `ruamel.yaml` | 0.18.17 → 0.19.1 | `conda`'s own `depends: ruamel.yaml>=0.11.14,<0.19` |

#### 🟠 Platform/upstream-support gap — verified, no local fix, just wait

| Package | Locked → Latest | Gap |
|---|---|---|
| `pyarrow` / `pyarrow-all` | 24.0.0 → 25.0.0 | `pyarrow-core 25.0.0`'s osx-arm64 build needs `python<3.14` or an unreachable `libabseil` window (solver-verified) |
| `speechrecognition` | 3.10.4 → 3.17.0 | 3.17.0's own build declares `python>=3.10,<3.13` — no py3.14 build yet |

#### ⚪ Undiagnosed — checked, real blocker not found in this pass

| Package | Locked → Latest | Note |
|---|---|---|
| `diffusers` | 0.39.0 → 0.40.0 | own deps look satisfiable; blocker not identified |
| `conda` | 26.5.0 → 26.7.1 | py3.14 build exists, no offending cap found; small delta, low priority |

#### 🔵 Transitive-only — solver/repodata-verified, 93 packages, every row a real finding

Verified this session (continued from the request to make the book of work accurate): for every one of the 93, either (a) a package *currently in our lock* declares a `depends`/`constrains` spec that excludes the latest version (`BLOCKED-BY-EXISTING-PIN`), or (b) the target's own newest build introduces a *new* requirement that conflicts with something already locked (`NEW-BUILD-CONFLICTS-WITH-LOCKED`). Every finding was then **traced through its full chain** to a terminal package, and every terminal package was independently checked — **all of them are already at their own conda-forge latest**, confirming these are genuine upstream compatibility caps (the fix is that package's own next release), not stale locks or local misconfiguration.

#### Sprint priority — fix one upstream package, unblock N

Sorted by blast radius. This is the actual actionable list: checking (or filing against) **one** terminal package's feedstock clears every row underneath it.

| Terminal package (check/file upstream) | Unblocks | Packages |
|---|---|---|
| `aws-sdk-cpp` | 13 | `aws-c-auth`, `aws-c-cal`, `aws-c-common`, `aws-c-compression`, `aws-c-event-stream`, `aws-c-http`, `aws-c-io`, `aws-c-mqtt`, `aws-c-s3`, `aws-c-sdkutils`, `aws-checksums`, `aws-crt-cpp`, `s2n` |
| `conda-lock` | 3 | `dulwich`, `hatch`, `virtualenv` |
| `getdaft` | 3 | `fsspec`, `pins`, `tqdm` |
| `leptonica` | 3 | `giflib`, `libdeflate`, `libgdal-core` |
| `omegaconf` | 2 | `antlr-python-runtime`, `python_abi` |
| `libavif16` | 2 | `aom`, `dav1d` |
| `dagster` | 2 | `coloredlogs`, `grpcio-health-checking` |
| `coderedcms` | 2 | `django-bootstrap5`, `icalendar` |
| `wagtail` | 2 | `django-treebeard`, `draftjs_exporter` |
| `instructor` | 2 | `jiter`, `openai` |
| `graphifyy` | 2 | `tree-sitter-julia`, `tree_sitter` |
| `at-spi2-atk` | 1 | `at-spi2-core` |
| `azure-identity-cpp` | 1 | `azure-core-cpp` |
| `libmamba` | 1 | `fmt` |
| `click` | 1 | `huggingface_hub` |
| `opentelemetry-api` | 1 | `importlib-metadata` |
| `lumen` | 1 | `intake` |
| `kedro-viz` | 1 | `ipython` |
| `pngquant` | 1 | `libimagequant` |
| `markitdown` | 1 | `magika` |
| `great-expectations` | 1 | `marshmallow` |
| `liblief` | 1 | `mbedtls` |
| `mupdf` | 1 | `mesalib` |
| `vsts-python-api` | 1 | `msrest` |
| `apptainer` | 1 | `openssl` |
| `a2a-sdk` | 1 | `protobuf` |
| `conda-oci-mirror` | 1 | `oras-py` |
| `pixi-build-cmake` | 1 | `pixi-build-api-version` |
| `libmambapy` | 1 | `pybind11-abi` |
| `playwright-python` | 1 | `pyee` |
| `graphviz2drawio` | 1 | `svg.path` |
| `bleach` | 1 | `tinycss2` |
| `matplotlib-base` | 1 | `tk` |
| `google-genai` | 1 | `websockets` |

Full per-package detail (locked → latest, terminal blocker):

| Package | Locked | Latest | Blocked by (terminal, already at ITS OWN latest) |
|---|---|---|---|
| `aws-c-auth` | 0.10.4 | 0.10.5 | `aws-sdk-cpp` |
| `aws-c-cal` | 0.9.14 | 0.9.15 | `aws-sdk-cpp` |
| `aws-c-common` | 0.14.2 | 0.14.5 | `aws-sdk-cpp` |
| `aws-c-compression` | 0.3.2 | 0.3.3 | `aws-sdk-cpp` |
| `aws-c-event-stream` | 0.7.1 | 0.7.2 | `aws-sdk-cpp` |
| `aws-c-http` | 0.11.0 | 0.11.1 | `aws-sdk-cpp` |
| `aws-c-io` | 0.27.3 | 0.27.7 | `aws-sdk-cpp` |
| `aws-c-mqtt` | 0.16.0 | 0.16.2 | `aws-sdk-cpp` |
| `aws-c-s3` | 0.12.8 | 0.13.1 | `aws-sdk-cpp` |
| `aws-c-sdkutils` | 0.2.7 | 0.2.10 | `aws-sdk-cpp` |
| `aws-checksums` | 0.2.10 | 0.2.11 | `aws-sdk-cpp` |
| `aws-crt-cpp` | 0.40.1 | 0.43.5 | `aws-sdk-cpp` |
| `s2n` | 1.7.5 | 1.7.8 | `aws-sdk-cpp` |
| `dulwich` | 0.24.10 | 1.2.10 | `conda-lock` |
| `hatch` | 1.16.3 | 1.17.1 | `conda-lock` |
| `virtualenv` | 20.39.0 | 21.7.7 | `conda-lock` |
| `fsspec` | 2026.4.0 | 2026.7.0 | `getdaft` |
| `pins` | 0.9.0 | 0.9.1 | `getdaft` |
| `tqdm` | 4.67.3 | 4.70.0 | `getdaft` |
| `giflib` | 5.2.2 | 6.1.3 | `leptonica` |
| `libdeflate` | 1.25 | 1.26 | `leptonica` |
| `libgdal-core` | 3.13.2 | 3.13.3 | `leptonica` |
| `antlr-python-runtime` | 4.9.3 | 4.13.2 | `omegaconf` |
| `python_abi` | 3.14 | 3.15 | `omegaconf` |
| `aom` | 3.14.1 | 3.15.0 | `libavif16` |
| `dav1d` | 1.2.1 | 1.5.4 | `libavif16` |
| `coloredlogs` | 14.0 | 15.0.1 | `dagster` |
| `grpcio-health-checking` | 1.78.1 | 1.83.0 | `dagster` |
| `django-bootstrap5` | 25.2 | 26.3 | `coderedcms` |
| `icalendar` | 6.3.2 | 7.3.0 | `coderedcms` |
| `django-treebeard` | 5.3.0 | 7.0.1 | `wagtail` |
| `draftjs_exporter` | 5.2.0 | 7.1.0 | `wagtail` |
| `jiter` | 0.11.1 | 0.16.0 | `instructor` |
| `openai` | 2.53.0 | 3.6.0 | `instructor` |
| `tree-sitter-julia` | 0.23.1 | 0.25.0 | `graphifyy` |
| `tree_sitter` | 0.25.2 | 0.26.0 | `graphifyy` |
| `at-spi2-core` | 2.40.3 | 2.58.3 | `at-spi2-atk` |
| `azure-core-cpp` | 1.16.3 | 1.16.4 | `azure-identity-cpp` |
| `fmt` | 12.1.0 | 12.2.0 | `libmamba` |
| `huggingface_hub` | 1.16.1 | 1.29.0 | `click -> conda-recipe-manager==8.2.1` |
| `importlib-metadata` | 8.7.1 | 9.0.1 | `opentelemetry-api` |
| `intake` | 0.7.0 | 2.0.9 | `lumen` |
| `ipython` | 8.37.0 | 9.17.0 | `kedro-viz` |
| `libimagequant` | 2.17.0 | 4.4.1 | `pngquant` |
| `magika` | 0.6.2 | 1.0.3 | `markitdown` |
| `marshmallow` | 3.26.2 | 4.3.1 | `great-expectations` |
| `mbedtls` | 3.6.3.1 | 4.2.0 | `liblief` |
| `mesalib` | 26.1.6 | 26.2.1 | `mupdf` |
| `msrest` | 0.6.21 | 0.7.1 | `vsts-python-api` |
| `openssl` | 3.6.4 | 4.0.1 | `apptainer` |
| `protobuf` | 6.33.5 | 7.35.1 | `a2a-sdk` (also independently capped `<7` by `dagster`) |
| `oras-py` | 0.1.14 | 0.2.43 | `conda-oci-mirror` |
| `pixi-build-api-version` | 7 | 12 | `pixi-build-cmake` |
| `pybind11-abi` | 11 | 12 | `libmambapy` |
| `pyee` | 13.0.1 | 14.0.0 | `playwright-python` |
| `svg.path` | 6.3 | 7.1 | `graphviz2drawio` |
| `tinycss2` | 1.4.0 | 1.5.1 | `bleach` |
| `tk` | 8.6.13 | 9.0.4 | `matplotlib-base` |
| `websockets` | 16.1.1 | 17.1 | `google-genai` |

#### Same-recipe-family — needs a coordinated version bump, not an upstream fix (28 packages)

These aren't blocked by a single named upstream bug — they're siblings from the same
multi-output recipe or a deliberately lockstep-versioned pair, and just need bumping together
once the real blocker clears.

| Package | Locked | Latest | Real blocker |
|---|---|---|---|
| `google-cloud-bigquery-storage` | 2.38.0 | 2.41.0 | google-cloud-bigquery-storage-core sibling pair |
| `google-cloud-bigquery-storage-core` | 2.38.0 | 2.41.0 | google-cloud-bigquery-storage sibling pair |
| `httpcore2` | 2.5.0 | 2.12.0 | httpx2 lockstep pair (a real conda-forge fork/rename pair this repo consumes — both builds already exist at 2.12.0, nothing external blocks either; just needs a coordinated bump) |
| `httpx2` | 2.5.0 | 2.12.0 | httpcore2 lockstep pair (same note) |
| `libarrow` | 24.0.0 | 25.0.0 | pyarrow platform-gap |
| `libarrow-acero` | 24.0.0 | 25.0.0 | pyarrow platform-gap |
| `libarrow-compute` | 24.0.0 | 25.0.0 | pyarrow platform-gap |
| `libarrow-dataset` | 24.0.0 | 25.0.0 | pyarrow platform-gap |
| `libarrow-flight` | 24.0.0 | 25.0.0 | pyarrow platform-gap |
| `libarrow-flight-sql` | 24.0.0 | 25.0.0 | pyarrow platform-gap |
| `libarrow-gandiva` | 24.0.0 | 25.0.0 | pyarrow platform-gap |
| `libarrow-substrait` | 24.0.0 | 25.0.0 | pyarrow platform-gap |
| `libgoogle-cloud` | 3.6.0 | 3.8.0 | pyarrow platform-gap |
| `libgoogle-cloud-storage` | 3.6.0 | 3.8.0 | pyarrow platform-gap |
| `libparquet` | 24.0.0 | 25.0.0 | pyarrow platform-gap |
| `libprotobuf` | 6.33.5 | 7.36.0 | pyarrow platform-gap (pulled in transitively by `libarrow`'s own exact pin) |
| `libtorch` | 2.12.0 | 2.13.0 | pytorch sibling pair |
| `pytorch` | 2.12.0 | 2.13.0 | libtorch sibling pair |
| `mesa-lavapipe` | 26.1.6 | 26.2.1 | mesalib sibling |
| `mesa-llvmpipe` | 26.1.6 | 26.2.1 | mesalib sibling |
| `microsoft-kiota-abstractions` | 1.10.1 | 1.12.0 | microsoft-kiota closure siblings |
| `microsoft-kiota-authentication-azure` | 1.10.1 | 1.12.0 | microsoft-kiota closure siblings |
| `microsoft-kiota-http` | 1.10.1 | 1.12.0 | microsoft-kiota closure siblings |
| `msgraph-core` | 1.4.0 | 1.5.1 | microsoft-kiota closure siblings |
| `orc` | 2.3.0 | 2.3.1 | pyarrow platform-gap |
| `pyarrow-core` | 24.0.0 | 25.0.0 | pyarrow platform-gap |
| `pybind11` | 3.0.4 | 3.1.0 | pybind11-global sibling pair |
| `pybind11-global` | 3.0.4 | 3.1.0 | pybind11 sibling pair |

**`grpcio` / `grpcio-status` / `libgrpc` / `libabseil` (4 packages) — a genuine ecosystem
version-diamond, not a single-package fix.** These don't collapse to one terminal package the
way the rest of this table does. `grpcio 1.83.0`'s own build requires `libabseil
>=20260526.0,<20260527.0a0`; separately, `protobuf 6.33.5` (itself capped `<7` by both
`a2a-sdk` and `dagster` — see the sprint-priority table above) requires `libabseil
>=20260107.1,<20260108.0a0` — two different consumers wanting two different, non-overlapping
`libabseil` windows at once. Even resolving the `protobuf<7` cap wouldn't automatically clear
this: `grpcio`/`protobuf`'s release trains would also need to land on a *shared* `libabseil`
window simultaneously. This is the same shape as the `G97`-class "ERA DIAMOND between ecosystem
pin epochs" already documented in the conda-forge-expert skill (`SKILL.md`) — the fix is
upstream convergence across multiple release trains, not a single feedstock PR.

| Package | Locked | Latest |
|---|---|---|
| `grpcio` | 1.78.1 | 1.83.0 |
| `grpcio-status` | 1.78.1 | 1.83.0 |
| `libgrpc` | 1.78.1 | 1.83.0 |
| `libabseil` | 20260107.1 | 20260817.0 |

#### Tradeoff — not a bug, a deliberate non-upgrade (2 packages)

Bumping these would force *downgrading* something we're deliberately keeping newer. No feedstock fix applies; the call is whether the tradeoff is worth revisiting.

| Package | Locked | Latest | What it would cost |
|---|---|---|---|
| `azure-core` | 1.38.2 | 1.41.0 | flask (azure-core wants flask 2.2.5, we run 3.1.3) |
| `db-dtypes` | 1.4.3 | 1.7.1 | numpy (db-dtypes wants numpy<=2.2.6, we run 2.5.2) |

### The channel-sourcing debt ledger

A third shape of the same problem: every active dependency that does NOT come from
conda-forge is a standing bet that a non-default channel or a bare PyPI wheel keeps
working — currency debt exactly like the two ledgers above, just on the *source* axis
instead of the *version* axis. Verified against `pixi.lock`'s own resolved URLs (ground
truth — not `pixi.toml`'s comments, which describe availability/history and can lag what
actually got locked), not inferred from intent.

#### SelfExplainML-channel packages (30, all locally authored)

Every one of the 30 packages `pixi.lock` actually resolves from the `SelfExplainML`
channel has a `recipes/<name>/` in this repo — none is a third-party channel dependency
we don't control, but every one is a conda-forge submission still in flight (or, for a
few, permanently out of reach of conda-forge by construction). Grouped by area, with each
recipe's own `cfe-on-conda-forge-status`:

| Area | Packages | Status |
|---|---|---|
| BMAD suite tooling | `bmad-builder`, `bmad-creative-intelligence-suite`, `bmad-dashboard`, `bmad-method-test-architecture-enterprise`, `bmad-module-skill-forge`, `bmad-module-template`, `bmad-utility-skills`, `mybmad-dashboard` (WDS retired 2026-09-05) | `pending-approval-on-conda-forge` |
| BMAD suite tooling | `bmad-labs-skills`, `bmad-loop`, `bmad-manticore` | `pending-submission-to-conda-forge` |
| Token-economy instruments (§ see "What is real" above / [[marshal-token-economy]]) | `caveman` | `pending-submission-to-conda-forge` |
| Token-economy instruments | `codegraph` | `pending-approval-on-conda-forge` |
| MCP tooling | `fastmcp` | `confirmed-on-conda-forge` — **check needed**: still resolving from SelfExplainML despite the metadata; per `pixi.toml`'s own comment, conda-forge tops out at `3.4.7` (hard-requires `mcp<2.0`) while this env pins `>=4.0.0b5` — the recipe metadata likely describes the OLD `<=3.4.7` package, not the `>=4.0` build actually locked |
| MCP tooling | `fastmcp-slim` | no status field recorded |
| Kedro tooling | `kedro-mcp` | `pypi-only` — describes the *upstream* package (no conda-forge feedstock exists for it at all); this repo's own recipe packages a locally source-patched fork (swaps the `fastmcp` import for the official `mcp` SDK) that has no upstream conda-forge counterpart to converge toward |
| Kedro tooling | `kedro-skills` | no status field recorded |
| Enterprise/deploy | `liquibase`, `liquibase-postgresql` | no status field recorded (vendored JDBC per `pixi.toml`'s own comment) |
| Enterprise/deploy (OpenFeature) | `openfeature-flagd-api`, `openfeature-flagd-core`, `openfeature-provider-flagd`, `openfeature-sdk` | `pending-submission-to-conda-forge` — OpenFeature is absent from conda-forge AND anaconda.org entirely (Grounding 2026-08-24 ruling in [[pyforge-unifying-strategy]]); this is the closest any of these four will get until conda-forge itself gains the feedstocks |
| Presentation/deck tooling | `ppt-master`, `pptxgenjs`, `pptxgenjs-plus`, `vizro-e2e-flow` | `pending-submission-to-conda-forge` |
| Misc | `panzi-json-logic` | `pending-submission-to-conda-forge` |
| Misc | `slowapi` | `confirmed-on-conda-forge` — **same check needed as `fastmcp`**: still locked from SelfExplainML despite the metadata; `pixi.toml`'s own comment names a specific `0.1.10` SelfExplainML build as expected in the lock, so this is very likely a version/channel-priority nuance (SelfExplainML's build satisfies a constraint conda-forge's doesn't) rather than a stale field — worth a real re-check, not a guess |

**What this actually means:** 25 of 30 are genuinely "our own packaging work, not yet
merged upstream" — the fix path is finishing the staged-recipes submission each already
has in flight, same lifecycle every other recipe in this repo follows. The 4 OpenFeature
packages and the whole BMAD-suite family are the closest thing to *permanent* SelfExplainML
residents in this list — OpenFeature by a documented upstream absence, BMAD-suite tooling
because it's a thin npm/npx wrapper ecosystem unlikely to ever grow conda-forge feedstocks
of its own. `kedro-mcp` is permanent for a different reason: the package itself is a
local fork with no upstream to converge toward. The 2 `confirmed-on-conda-forge` outliers
(`fastmcp`, `slowapi`) are the one genuinely open question in this table — each needs a
real repodata check (which exact version conda-forge ships today vs. what this env's
`pixi.toml` constraint actually requires), not an assumption that the field is simply
stale.

#### Bare-PyPI dependency (1)

`[feature.vuln-db.pypi-dependencies]` carries exactly one active entry:
**`appthreat-vulnerability-db`** (multi-source CVE DB — NVD/GHSA/OSV/npm/Snyk), pulled
directly from PyPI with no conda-forge equivalent at all. This is the CVE-scanning engine
behind `vdb-refresh`/`cve-watcher`, not a candidate for conda packaging in this pass — its
own dependency tree (multiple scanner backends) makes it a poor fit for a single conda
recipe, and nothing else in this repo needs the exact same debt this dependency creates.
The commented-out `crewai` line in the same table is not live debt — it's a dormant
placeholder for a package already tracked in the candidate ledger's own "unexamined"
bucket above.

### The external-tracking gap ledger

A fourth shape of currency debt, on the *visibility* axis rather than source/version:
which of this environment's active dependencies have no corresponding tracking item on
OpenTeams-WFT-CDO's own conda-forge-packaging project board
(`github.com/orgs/OpenTeams-WFT-CDO/projects/1`, "OSS Enhancements (Conda Forge, Pixi,
ect)" milestone — that org's own `[Conda-Forge Packaging] <name>` / `Add <name> to
conda-forge` / `Build <name> vX on conda-forge` title conventions). Verified 2026-08-31:
extracted 1309 distinct tracked names from that milestone's ~1332 items, parsed all 335
active `pixi.toml` dependency keys via `tomllib`, cross-referenced. **197 of 335 are not
tracked there.** After excluding base conda/pixi ecosystem infra (52 — `conda`, `pixi`,
`python`, `conda-build`, `rattler-build`, the `pixi-*` plugin family, system tools like
`gh`/`tmux`/`nodejs`/`postgresql`) and this repo's own `pyforge-*` packages (10, not
third-party OSS), **135 remain as genuine candidates**:

- **108 with a local `recipes/<name>/`** — real packaging debt this repo already did the
  work for, invisible to that tracker: `bmad-labs-skills`, `bmad-loop`, `bmad-manticore`,
  `bmad-module-skill-forge`, `bokeh-django`, `boring-semantic-layer`, `caveman`,
  `channels`, `cocoindex`, `codegraph`, `coderedcms`, `cookiecutter`, `copier`,
  `cyclonedx-bom`, `cyclonedx-python-lib`, `dagster`, `dagster-webserver`, `daphne`,
  `dask-core`, `dbt-duckdb`, `deptry`, `diffusers`, `django-anymail`, `django-appconf`,
  `django-compressor`, `django-ipware`, `django-lasuite`, `django-mcp-server`,
  `django-model-utils`, `djlint`, `dlt`, `duckdb-server`, `elevenlabs`, `fido2`,
  `frozendict`, `github-copilot-sdk`, `graphifyy`, `great-expectations`, `headroom-ai`,
  `httpx2`, `ibis-framework`, `import-linter`, `ipdb`, `jinja2-ospath`, `kedro`,
  `kedro-dagster`, `kedro-datasets`, `kedro-mcp`, `kedro-skills`, `kedro-viz`,
  `langchain-chroma`, `langflow`, `liquibase`, `liquibase-postgresql`, `mammoth`,
  `markitdown`, `marp-cli`, `mermaid-py`, `mlx`, `mlx-lm`, `moto`, `msgraph-sdk`,
  `mybmad-dashboard`, `nbqa`, `ocrmypdf`, `odfpy`, `office2pdf`, `ollama-python`,
  `openfeature-flagd-api`, `openfeature-flagd-core`, `openfeature-provider-flagd`,
  `openfeature-sdk`, `openlineage-python`, `opentelemetry-instrumentation-psycopg`,
  `osv-scanner`, `pandera`, `pandoc`, `panel`, `panel-graphic-walker`, `pdf2image`,
  `pip-audit`, `playwright-python`, `pptxgenjs`, `pptxgenjs-plus`, `psycopg2`, `pyrefly`,
  `pyright`, `python-build`, `python-graphviz`, `qrcode`, `rank-bm25`, `rcssmin`,
  `redis-py`, `rjsmin`, `ruamel.yaml`, `sentencepiece`, `spec-kit`, `speechrecognition`,
  `sphinx-autobuild`, `tablib`, `truststore`, `twine`, `uvicorn-worker`, `vizro`,
  `vizro-ai`, `vizro-e2e-flow`, `vizro-mcp`, `wagtail`.
- **27 with no local recipe** — genuinely unverified, several plausibly already fine on
  conda-forge with no packaging needed at all (`pgvector`, `llama.cpp`, the `ibis-*`
  backend family) rather than real debt: `age`, `cachebox`, `channels-redis`,
  `claude-agent-acp`, `cruft`, `d2`, `dagster-pipes`, `dbgpt`, `dbgpt-app`, `dbgpt-serve`,
  `fasta2a`, `go-sops`, `graphviz2drawio`, `ibis-duckdb`, `ibis-mssql`, `ibis-oracle`,
  `ibis-polars`, `ibis-postgres`, `ibis-sqlite`, `llama.cpp`, `lumen-ai-anthropic`,
  `mcp-types`, `nebi-cli`, `pdfminer.six`, `pgvector`, `pyarrow-all`, `pydantic-ai`.

**This is a visibility gap, not a packaging verdict.** A package missing from OpenTeams'
board is not necessarily un-packaged or blocked — the 108-with-recipe bucket already has
its own disposition in the ledgers above (most `pending-*` on conda-forge already); this
ledger only says that disposition isn't mirrored onto that external tracker. Whether it
should be is an operator call, not something this Dream decides unilaterally per package.

### Constraints

- **A `blocked` disposition must name what would unblock it**, not just that it's blocked —
  the difference between this ledger and the status quo is exactly that a re-check has a
  trigger instead of requiring someone to remember to look.
- **Don't re-derive a shared root cause per package.** `headroom-ai` and the `dbt-*` trio are
  one investigation, not four.
- **Trust local `cfe-*` metadata as a hint, not ground truth** — the `langflow` entry above is
  the live proof it can drift stale within a single session's own timeframe.
- **A `blocked`-vs-`platform-gap` disposition for an active dependency must name the exact
  upstream package + spec**, read off the actually-resolved build's own `depends`/`constrains` —
  never "something conflicts." `platform-gap` findings need solver verification (an actual
  bumped-floor solve, as done for `pyarrow`), not just "conda-forge has a newer version" — a
  package can be behind latest for reasons that have nothing to do with platform support.

### Non-goals

- **Not a commitment to add any specific package**, and not a commitment to unblock any specific
  active dependency — this Dream separates "safe to try" from "blocked" from "dead" on the
  candidate side, and "deliberate" from "blocked" from "platform-gap" from "undiagnosed" on the
  currency side; several blockers are pinned deliberately elsewhere for good reasons
  (`conda-smithy<4`) and unblocking their symptoms may not be worth the tradeoff — that stays a
  separate call per finding.
- **Not re-litigating conda-forge submission strategy** for the recipes already
  `pending-approval`/`pending-submission` — that's the recipes' own `cfe-on-conda-forge-status`
  lifecycle, tracked per-recipe already.
- **Not a commitment to actually fix any of the 33 terminal-package findings** — each is
  evidence-verified (a real `depends`/`constrains` spec, a real conflicting requirement, a real
  confirmed-at-latest terminal), which is different from deciding it's worth an upstream issue
  or a local workaround. That triage stays a separate call per finding, same as the candidate
  ledger's own non-goal above.
- **A verified finding that later turns out wrong belongs in this same ledger as a correction**,
  not a silent re-derivation — the whole point of naming the exact evidence (which package,
  which spec, which build) is that it can be checked and, if wrong, fixed in place.

### Kinships

[[chain-currency-sweep]] (the same "re-derive, don't decay" discipline, applied to a dependency
ledger instead of a planning-spine chain) · [[pyforge-doctor-dependency-health]] (archived, but
the closest prior framing of "every dependency gets a tracked health disposition" — this Dream
is narrower and repo-local rather than factory-wide)

### Realization log

- **2026-08-30** — Dream captured directly from a live audit: all 64 commented-out lines in
  `pixi.toml` enumerated, cross-referenced against `recipes/` (37 of 44 packages already have a
  local recipe — more than expected going in), and each existing recipe's own `cfe-*` metadata
  pulled where present. Six packages got a *fully verified* disposition this session
  (`ppt-master`, `codegraph` added; `headroom-ai`, `caveman`, `dbt-core`/`dbt-duckdb`/
  `dbt-postgres` root-caused as blocked; `ocrmypdf` reconfirmed; `pngquant`'s own separate
  cross-compile bug fixed upstream). The rest are triaged by disposition but not individually
  re-verified in this pass — that re-verification is the Dream's own future work, not assumed
  done. **Owner picked as `doctor`** (dependency/environment-health framing, advisory not
  gating) as the best fit among the eight-station enum; this is a repo-local housekeeping
  concern rather than a PyForge Guild product, so the fit is imperfect — correct trivially if
  another owner reads better.
- **2026-08-30 (same session, continued)** — folded in the mirror-image half: a full
  version-currency audit of ACTIVE `local-recipes` dependencies (originally drafted as a
  separate sibling Dream, then merged in here on request — "this is all related to currency").
  Parsed `pixi.lock` (1147 packages), diffed against fresh conda-forge repodata (149 behind
  latest), used `pixi update --dry-run` as the oracle to separate stale-lock (38) from
  genuinely-capped (111), then built a reverse-dependency index from actually-resolved builds'
  own `depends`/`constrains` to name real culprits instead of guessing. 8 packages got a fully
  verified root cause (collapsing to 6 upstream culprits, one of which — `conda-recipe-manager
  ==8.2.1` — turned out to be the SAME root cause already blocking `headroom-ai`/`dbt-*` on the
  candidate side, confirming this really is one Dream). One platform-gap hypothesis
  (`pyarrow-core` on osx-arm64) was confirmed with a real solver test (temporary floor bump,
  reverted after — nothing left in the manifest).
- **2026-08-30 (same session, continued again)** — the remaining 93 were left as unconfirmed
  cluster hypotheses; asked to verify them so the book of work is accurate before treating any
  of it as sprint-ready. Built a verifier reusing the already-downloaded repodata (no new network
  calls): for each of the 93, checked whether a currently-locked package's own
  `depends`/`constrains` excludes the latest version, and where none did, checked whether the
  target's own newest build introduces a new requirement conflicting with something already
  locked — 79 hit the first check, 14 the second, **zero came back with no explanation**. Every
  finding was then traced through its full blocking chain to a terminal package (recursively —
  e.g. `s2n → aws-c-io → aws-c-auth → aws-c-s3 → aws-crt-cpp → aws-sdk-cpp`), and every one of
  those terminals was independently confirmed to already be at ITS OWN conda-forge latest —
  ruling out "just needs `pixi update`" as an explanation for any of them. Result: 59 packages
  trace to 34 distinct terminal packages (sorted by blast radius — `aws-sdk-cpp` alone explains
  13 of the 59), 28 turned out to be same-recipe-family siblings (needing a coordinated version
  bump, not an upstream fix — folded into the `pyarrow`/kiota/etc. findings already on record)
  rather than independent findings, and 2 are deliberate tradeoffs (upgrading would force
  downgrading `flask`/`numpy`, which we don't want). One sub-finding required a second pass: the
  first draft mis-collapsed `grpcio`/`grpcio-status`/`libgrpc`/`libabseil` into the same-family
  bucket under a dangling "(see below)" that never resolved — re-checked their real evidence and
  reclassified as a genuine 4-package multi-producer ecosystem version-diamond (`grpcio 1.83.0`
  and `protobuf 6.33.5` want non-overlapping `libabseil` windows simultaneously; `protobuf`
  itself traces to `a2a-sdk`, now correctly counted among the 34 terminals) — a real, distinct
  finding, not a single-package fix, called out explicitly rather than hidden inside a table
  note. The hypothesis-only language was removed from every section that referenced it.
- **2026-08-31** — Added the third ledger, channel-sourcing debt: operator direction that
  packages depending on SelfExplainML or bare PyPI "are also currency / workarounds and
  debt." Queried `pixi.lock`'s own resolved URLs (ground truth, not `pixi.toml` comments)
  for every package actually served from SelfExplainML — 30 found, cross-checked against
  `recipes/` (all 30 have a local recipe — none is a third-party channel risk, all are our
  own in-flight conda-forge submissions) and each recipe's own `cfe-on-conda-forge-status`.
  25 are `pending-*`, 4 (OpenFeature) and the BMAD-suite family are effectively permanent
  SelfExplainML residents (documented upstream absence / thin npm-wrapper ecosystem), 1
  (`kedro-mcp`) is permanent for a different reason (a local fork with no upstream to
  converge toward), and 2 (`fastmcp`, `slowapi`) are flagged `confirmed-on-conda-forge` yet
  still lock from SelfExplainML — a real open question (likely a version/constraint
  mismatch between the recipe metadata and what's actually locked), not resolved in this
  pass. Also found the one active bare-PyPI dependency (`appthreat-vulnerability-db`, no
  conda-forge equivalent) and confirmed the commented-out `crewai` pypi-dependencies line
  is dormant, not live debt (already tracked in the candidate ledger's own "unexamined"
  bucket).
- **2026-08-31 (same session, continued)** — added the fourth ledger, external-tracking
  gap: cross-referenced all 335 active `pixi.toml` packages against OpenTeams-WFT-CDO's
  own conda-forge-packaging project board (1309 tracked names extracted from its "OSS
  Enhancements" milestone). 197 untracked; after excluding base conda/pixi infra and this
  repo's own `pyforge-*` packages, 135 genuine candidates remain — 108 with a local
  recipe already (real packaging debt invisible to that tracker) and 27 without one
  (unverified; several plausibly already fine on conda-forge with no debt at all). Framed
  explicitly as a visibility gap, not a packaging verdict — this Dream doesn't decide
  per-package whether external tracking is warranted.
- **2026-09-16** — `dreamt` → `realized` (fleet-inbox-disposition). Doctor Story
  `21-7-the-pixi-candidate-ledgers-get-their-staleness-check` is `done`. The
  ledgers exist; remaining per-package currency is maintenance, not a second
  decompose. Record:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-inbox-disposition-2026-09-16.md`.

## 2026-10-26 — Dream — PyForge Doctor: Dependency Health Diagnostics (folded from pyforge-doctor-dependency-health)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 53.1). The body below is `docs/dreams/pyforge-doctor-dependency-health.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/pyforge-doctor-dependency-health.md`.*

> **Superseded 2026-08-02.** Created in a bulk commit later found to contain fabricated
> content elsewhere (a false migration note, boilerplate test-architecture docs invented
> for six stations). This dream's four genuinely new items — health scoring, a persistent
> fleet-health dashboard, adoption tracking, and safe upgrade-path recommendation — survived
> verification against Doctor's real PRD and are now captured, grounded in Doctor's actual
> constraints, in [`docs/dreams/pyforge-doctor.md`](pyforge-doctor.md)'s "frontier" section
> and decomposed into a real Epic 4 (CAP-5..CAP-8, FR-10..FR-13). The rest of this dream's
> content — precision numbers like "95%+ obsolescence catch rate," "1000+ real packages,"
> "80%+ operator acceptance" — had no grounding anywhere in this project's real work and does
> not carry forward. See `spec-pyforge-doctor-dependency-health` for the retirement record.

## PyForge Doctor — Dependency Health Diagnostics

### Vision

**Doctor** diagnoses Python and Conda dependency health — tracking versions, detecting obsolescence, monitoring adoption signals, and providing actionable remediation. It's the health monitor for every package in the factory's dependency tree.

**The ask**: Build a compliance and health diagnostics engine that makes stale, unsafe, or abandoned dependencies visible and actionable across the entire factory.

### Problem

- **Stale dependencies hide.** A package pins `numpy<1.20` from 2020. Is it intentional? Forgotten? Incompatible? No signal.
- **Obsolescence is silent.** Upstream unmaintained for 3+ years. No release in 24 months. Community moved on. The operator still doesn't know.
- **Version hell is manual.** Operators grep logs, check PyPI manually, guess when to update. No automated discovery.
- **Remediation is reactive.** Security CVE drops; factories scramble. No proactive health scoring or priority ranking.

### Realization

**Doctor** delivers:

1. **Health Scoring** — Multi-axis scoring (age, velocity, maintenance signal, adoption, community size) producing a single health grade (A–F). Operators know instantly: is this package healthy?

2. **Obsolescence Detection** — Detects packages unmaintained >N months, replaced by newer libraries, archived on GitHub, or deprecated upstream. Flags them for review.

3. **Version Intelligence** — Tracks all available versions, release cadence, breaking changes, and security patches. Recommends safe upgrade paths.

4. **Adoption Tracking** — Monitors PyPI download trends, conda adoption by # of feedstocks using it, GitHub stars, and ecosystem maturity signals.

5. **Actionable Remediation** — For each unhealthy package, suggests: "Update to X.Y.Z (safe)", "Replace with Z (recommended)", or "Pin and monitor (acceptable risk)".

6. **Fleet-wide Health Dashboard** — Operators see at a glance: how many deps are healthy, stale, or in critical condition. Sortable by risk, age, velocity.

### Success Criteria

- ✅ **Coverage**: Every dependency in the factory (Python + Conda) gets a health grade
- ✅ **Accuracy**: Health scores validated against real-world data (3+ months of trending)
- ✅ **Speed**: Health diagnosis <1 sec per dependency; fleet scan <5 min
- ✅ **Remediation**: Every unhealthy package has a suggested action (update, replace, or accept-risk)
- ✅ **Integration**: Works with Warden (compliance layer) to enforce health thresholds
- ✅ **Observability**: Every diagnosis logged, every recommendation attributed, every action auditable

### Acceptance

Doctor is done when:
1. Health scoring algorithm validated against 1000+ real packages
2. Obsolescence detection catches 95%+ of truly abandoned packages
3. Fleet-wide health dashboard deployed and tracking real factory data
4. Remediation recommendations accepted by operators in 80%+ of cases
5. Integration with Warden compliance gates proven in CI

## 2026-10-26 — Sibling dreams directories don't drift silently (folded from sibling-dreams-drift)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 53.1). The body below is `docs/dreams/sibling-dreams-drift.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/sibling-dreams-drift.md`.*

## Sibling dreams directories don't drift silently

### The Dream

A sibling PyForge instantiation exists (OpenTeams-WFT-CDO
mgmt-wf-python-modernization) sharing this repo's Dream-first convention:
13 of its 15 dreams have local counterparts (8 byte-identical filenames),
independently evolving, with station ownership already diverging (their
deck work = scribe; ours = herald). Nothing detects the drift. The dream:
an ambient doctor finding — a periodic shared-title diff naming dreams that
exist in both trees with diverging content/status/owner, warn-only,
fail-open when the sibling is unreachable.

### Constraints / Non-goals

Read-only, never a sync engine (reconciliation is human, per-dream);
the sibling is private — access via the operator's token, degrade silently
without it; no content is copied across (their prose is unlicensed).
Kin: `bmad-method-version-drift` (the ambient-signal shape),
the 2026-08-22 intake report (the demonstrated drift).

### Realization log

- **2026-08-22** — Seeded from the seven-repo external analysis (`f0c695758c`);
  `spec-sibling-dreams-drift` derived under pyforge-doctor and decomposed into the station backlog
  the same day (`a20192dd84`). Spec status `ready`.
- **2026-09-09** — Still `specified`, and deliberately not `realized`. Story 16.1 is `done`,
  but the capability it shipped cannot fire against the live estate: the detector joins the
  two trees on frontmatter `title:` (`sibling_dreams.py:118`, `:155`, `:189`), and measured
  live this day with the operator's token the trees share **0 titles and 8 filenames** — the
  overlap this Dream itself named ("8 byte-identical filenames", above). The three sampled
  shared filenames all carry real divergence (`developer-machine-bootstrap.md`: local
  `specified` vs sibling `dreamt`), so the signal exists and the key does not reach it.
  `spec-sibling-dreams-drift` moves `ready` → `in-progress` with the re-key on filename
  (title demoted to a reported axis) and an explicit `sibling-dreams-unreachable` finding in
  place of today's silent `return ()` — so "could not look" stops rendering as "looked and
  agreed". Recorded in the fleet-readiness decision batch of 2026-09-09 (row doctor-B4).

## 2026-10-26 — A document's prose agrees with its own status (folded from status-body-consistency)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 53.1). The body below is `docs/dreams/status-body-consistency.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/status-body-consistency.md`.*

## A document's prose agrees with its own status

### The Dream

The document tier drifts faster than any detector polices it. `bmad-drift-check` guards
frontmatter *vocabulary* (is `status:` a legal value) and *counts* (does the artifact's
stated number match ground truth). `dreams-hygiene` guards *presence* (does a Dream carry
a status, a Realization log, a Spec). Nothing guards the one thing a reader actually
believes: that the **body still means what the frontmatter says**.

One readiness pass, 2026-09-09, found **six** documents where it does not — and none of
them is exotic:

- `docs/dreams/pyforge-scribe.md` reads `status: realized` while its own body says
  "3 of 9 stories complete overall" (`:69`); its Spec repeats the same stale figure.
- `docs/dreams/pyforge-herald.md` and `spec-pyforge-herald` both describe a mid-build
  station under `realized`/`shipped`.
- `docs/governance/spec-pyforge-charter/SPEC.md` declares `open_questions: []` (`:16`)
  while its own memlog carries a question opened 2026-07-31 that no later entry closes
  (`.memlog.md:9`, the `owner: guild` Lexicon question).
- `spec-unified-container` sits `shipped` over a container the estate does not build.

Every one of these is a lie a machine can catch, and every one of them was found by a
human reading carefully — which is exactly the labour this fleet exists to stop paying.

The Dream is a warn-only check that reads a Dream's or a Spec's prose beside its own
`status:` and reports the contradiction. Cheap signals, honestly bounded, never a gate.

### Candidate signals (each proven on the six live cases, or dropped)

- **Progress phrases under a terminal status.** A body matching "N of M stories" (or
  "N/M", "N of M capabilities") where `N < M`, under `realized` / `shipped` / `done`.
  Catches scribe's Dream and its Spec directly.
- **`open_questions: []` over a live memlog question.** The Spec declares no open
  questions while the companion `.memlog.md`'s last `(question)`/`(open)` entry has no
  subsequent `(decision)` closing it. Catches the Charter's Spec — where it is not
  hygiene at all: Charter CAP-2 makes the Lexicon's own integrity constitutional.
- **Future-tense build language under a terminal status.** A body whose section headings
  or lead sentences are still promissory ("will", "is being built", "queued", "not yet")
  under `realized`/`shipped`. Catches the herald pair. The loosest of the three, and the
  one most likely to be narrowed or dropped once measured.
- **A frontmatter status comment that contradicts the ledger it cites.** The
  `status: realized   # … → Epic 14 backlog` shape, where the named epic reads `done`.
  Found live on `bmad-method-version-drift`; mechanical, and the cheapest of all.

Each signal ships only after it is shown to fire on its named live case **and** to stay
silent across the rest of the tier. A signal that cannot demonstrate both is not shipped
— it is recorded as measured-and-rejected, with the number.

### What it looks like when real

- One more ambient row in the doctor report and the fleet-picture ATTENTION block,
  beside `dream-vocab` and `spec-status-missing`: *"`pyforge-scribe.md` reads `realized`
  but its body says 3 of 9 stories complete (`:69`)."*
- The finding names the **line** it read, never a verdict on the document. A reader
  disagrees with the check by fixing the prose or the status — never by arguing with a
  score.
- The tier stops needing a readiness pass to find this class. The 2026-09-09 sweep is the
  validation fixture: six documents, six findings, and nothing else.

### Constraints / Non-goals

- **Warn-only, fail-open, read-only.** Never a second PR verdict —
  `pyforge.doctor.verdict.exit_code_for` is the sole exit-code owner
  (`tests/meta/test_verdict_sole_ownership.py`); never a mutation — doctor's NFR-1 holds.
  An unparseable document degrades to a named finding, never to silence.
- **No natural-language judgement.** Every signal is a bounded textual pattern with a
  named line number. This is not "does the prose feel current" — a check that cannot
  point at a line is not shipped.
- **False positives are the expensive failure here, not false negatives.** A tier-wide
  narrative check that cries wolf gets muted, and a muted detector is worse than none.
  Each signal carries its measured precision over the live tier at the time it shipped.
- **Not a rewriter.** It never edits prose, flips a status, or proposes replacement text.
  Reconciliation is the [[chain-currency-sweep]] loop's job; this is its detector half.
- **Not a replacement for `bmad-drift-check` or `dreams-hygiene`.** Vocabulary, counts and
  presence stay where they are; this adds only the narrative axis none of them own.

### Kinships

[[capability-effect-check]] (minted the same day from the same pass — the two halves of
"the artifact says done and the estate disagrees": that one asks whether code reaches a
capability, this one asks whether prose agrees with a status) ·
[[sibling-dreams-drift]] (the shape — ambient, warn-only, fail-open, one Source — and the
standing lesson that a detector's join must be proven against live documents before its
story closes) · [[bmad-drift-new-artifact-shape]] (the sibling detector class this
extends: it polices frontmatter vocabulary and counts, never narrative) ·
[[chain-currency-sweep]] (the reconciler loop that clears what this reports; detector and
reconciler are the same two-layer pattern applied one tier down) ·
[[pyforge-charter]] (CAP-2 — the Lexicon's own integrity — makes one of the six cases
constitutional rather than cosmetic) · [[pyforge-doctor]] (the station).

### Realization log

- **2026-09-09** — Captured. Raised as D1 of the fleet-readiness decision batch
  (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`
  § 2.4, operator-approved the same day) by two independent station reports — guild § E-5
  and scribe § E-3 — after each ran into the same missing detector from a different
  station. Six documents in one pass; the pass itself is the validation fixture.
