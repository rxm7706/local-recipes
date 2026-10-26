---
title: "112.1: The Platform CI `test` job installs only what its runner image lacks, and its budget covers a slow mirror"
type: 'fix'
created: '2026-10-26'
status: 'in-progress'
baseline_revision: 'a3cfc63fcd5a33266fb3164ce7cda8f2bf4a0322'
flag-exempt: detector-or-gate   # a CI job's install step and budget; a flag-gated gate reports a silent green
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
  - .github/workflows/platform-ci.yml
  - .github/actions/platform-test-setup/action.yml
  - docs/governance/ci-surfaces.yaml
  - src/platform/tests/test_herald_portal_deck_viewer.py
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** the Platform CI `test` job is cancelled at its 15-minute ceiling whenever the runner's apt mirror is slow,
and the apt download it waits on buys nothing the job needs. Read from the Actions API's step timings of the last 200
`test` jobs (2026-10-11..26) and three job logs:

- **The cancellations.** Runs 39925508594 (2026-10-23) and 40306113110 (2026-10-26), both `main`'s own push runs,
  and 40351088193 (attempt 1, PR #2322) were cancelled at 909–919 s. Two cut the suite at 59 % and 69 %; on
  39925508594 the suite finished (1,346 passed) and the job's teardown was cancelled.
- **The one slow step.** `Install Chromium for the herald deck viewer browser check`
  (`python -m playwright install --with-deps chromium`, `platform-ci.yml:234` at `a3cfc63fcd`) took 636–668 s on
  those runs and 23 s at the median. Nearly all of it was the apt download, 23.9–25.9 MB from
  `azure.archive.ubuntu.com` at 38–43 kB/s (10 min 7 s to 10 min 35 s). The browser zips come from Playwright's CDN
  in 8–11 s on every run, slow or fast.
- **What apt installed.** Every library the headless shell links (`libnss3`, `libnspr4`, `libgbm1`,
  `libatk1.0-0t64`, `libatk-bridge2.0-0t64`, `libcups2t64`, `libxkbcommon0`, `libxcomposite1`, `libxdamage1`,
  `libxrandr2`, `libasound2t64`, `libpango-1.0-0`, `libcairo2` and the rest) is already on the image; apt reported
  most as already the newest version, and `libnss3` and `libglib2.0-0t64` took a point upgrade. It installed nine
  font packages (`fonts-ipafont-gothic`, `fonts-wqy-zenhei`, `fonts-tlwg-loma-otf`, `fonts-unifont`,
  `fonts-freefont-ttf`, four `xfonts-*`) and upgraded eight (`libglib2.0-*`, `libnss3`, `xvfb`). The one browser
  test, `test_playwright_records_zero_foreign_origin_requests` (`src/platform/tests/test_herald_portal_deck_viewer.py:418`),
  launches `playwright.chromium.launch()` and counts request origins.
- **The rest is not slow.** Every other step sums to 365 s at worst over 178 green jobs. The pixi install is 15 s at
  the median and 26–32 s on a cache miss (`main` runs 40229905972, 40231618468, 40254324378 read `Cache miss`); the
  suite is 197 s at the median and 243 s at worst, and on the cancelled runs it kept the fast run's pace.
- **Unseen.** `main` has no required status check, so the two `main` runs went unnoticed, and PR #2322 merged while
  its attempt 2 was still running.

**Approach:**

- **Install only what the image lacks.** The step runs `python -m playwright install chromium` (the browser alone),
  launches it once in a short Python probe, and runs `python -m playwright install-deps chromium` only when that
  launch fails, after a `::warning::` that names the fallback; it then launches the browser again and fails the step
  with an `::error::` if it still does not launch, so a failure shows beside its cause. On today's image the log
  reads the launch succeeding and shows no apt call.
- **A budget sized from what the job does.** `timeout-minutes` moves from 15 to 25. The slowest path the job can still
  take is the fallback on the slowest mirror measured (668 s) plus the worst of the other steps (365 s): 1,033 s.
  1,500 s leaves about 45 % headroom (every step at its own worst at once, 1,116 s, still leaves 34 %); without the fallback the job runs about 6 minutes. The comment beside the
  number names these figures.
- **Kept as it is.** The setup action and its pixi cache, the `platform-ci-test` environment, every check and suite
  step, the job's CAP-166 `if:` fragment and its `platform-ci.test` registry row (`cost: low`, `state: live`).

**Rejected:**
- **Raise the budget alone.** It hides the slow step instead of removing it: every run would still wait on the mirror.
- **An apt cache.** `/var/cache/apt/archives` is root-owned and its contents follow the mirror's day; restoring it
  needs `sudo` around `actions/cache` and still runs `apt-get update`.
- **A Playwright browser cache keyed on `pixi.lock`.** The CDN download is 8–11 s; a cache saves seconds and adds
  hundreds of MB to the repository's cache quota.
- **A pixi cache change.** The setup action restores in about 15 s and installs cold in 26–32 s.
- **`continue-on-error`, a pause or a disable.** The brief rules them out, and each hides a failure as well as a slow run.

Ledger key: `112-1-the-platform-ci-test-job-installs-only-what-its-runner-image-lacks-and-its-budget-covers-a-slow-mirror`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **`spec-pyforge-steward` CAP-174** (minted 2026-10-26 with this story): the Platform CI `test` job's time budget
  covers what it does on a slow runner, and it installs only what its runner image lacks. FR-48 ← CAP-174.
- **CAP-166** (works with): the job's `if:` fragment and registry row stay as they are; `ci status` reads the job as before.
- **AD-1** (wrap, never reimplement): Playwright's own installer and `install-deps`, never a hand-kept apt list.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag; the frontmatter records
  `flag-exempt: detector-or-gate` (a CI job's own install step and budget), recorded though not required (Story
  106.1's precedent).
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, the 2026-10-26 entry (the Platform CI test job's budget
  is sized for a fast mirror).

## Acceptance Criteria

- **AC1 — The step.** The `test` job's Chromium step runs `python -m playwright install chromium`, then a launch probe;
  `python -m playwright install-deps chromium` appears only in the probe's failure branch, after a `::warning::` line,
  and is followed by a second probe whose failure exits the step after an `::error::` line. `--with-deps` appears
  nowhere in the job.
- **AC2 — The budget.** The job's `timeout-minutes` is 25, and the comment above it names 668 s, 365 s, 1,033 s and the
  run ids of the three cancellations' source.
- **AC3 — The PR's own run.** The PR's Platform CI `test` job installs the browser from scratch, completes inside 25
  minutes, its log reads the probe's success line and no `apt` download, and
  `test_playwright_records_zero_foreign_origin_requests` reads `PASSED`. The PR body names the run.
- **AC4 — Unchanged around it.** `git diff` shows no change to `.github/actions/platform-test-setup/`, `pixi.toml`,
  `pixi.lock`, `docs/governance/ci-surfaces.yaml` or `src/platform/`; the job's `if:` line is byte-identical.
- **AC5 — Gates.** `python scripts/ci_surface_gates.py --check`, `pixi run -e pyforge-guild detectors-ci` and a
  full-scope `pr-preflight` exit 0.

## Boundaries & Constraints

**Always:** read every verdict from its exit code; name the proving run in the PR body.

**Never:** pause, disable or set `continue-on-error` on the lane; touch another workflow's Chromium step; edit the
setup action, the environment or the suite.

## I/O & Edge-Case Matrix

| Runner | Probe | apt | Expected |
|---|---|---|---|
| `ubuntu-latest` today (every library present) | launches | none | ~6 min, green |
| image missing a library | fails | `install-deps` | warning, second probe launches, green; up to ~17 min on the slowest mirror seen |
| `install-deps` succeeds, browser still does not launch | fails twice | `install-deps` | `::error::`, the step reds beside its cause |
| slow apt mirror, libraries present | launches | none | unaffected |
| browser download fails | — | — | `install chromium` exits non-zero and the step reds (`bash -e`); loud, never a skip |

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-steward` CAP-174 (FR-48), minted with this story; works with CAP-166.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-26 entry.
- Epic: Epic 112 (new), minted with this story; `epic-112` and `epic-112-retrospective` minted with it. Epic 112 because
  draft PR #2274 claims Epic 109 with CAP-169..CAP-173 and FR-42..FR-47.
- Ledger key: `112-1-the-platform-ci-test-job-installs-only-what-its-runner-image-lacks-and-its-budget-covers-a-slow-mirror`.
- Deps: —.

## Verification

**Commands:**
- `python scripts/ci_surface_gates.py --check` — expected: exit 0 (AC5).
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0 (AC5).

**Run before the push (not dispatch gates):**
- `grep -c -- '--with-deps' .github/workflows/platform-ci.yml` — expected: `0` (AC1).
- `TMPDIR=$HOME/.cache/pyforge-preflight-tmp PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0 (AC5).

**After the push:** the PR's Platform CI `test` job — expected: success inside 25 minutes, the probe's success line, no apt
download, the browser test `PASSED` (AC3).

## Auto Run Result

Status: in-progress (hand-built in the chain PR)

## Spec Change Log

- 2026-10-26: minted from the station Dream's entry of 2026-10-26 (the Platform CI test job's budget is sized for a fast mirror).
- 2026-10-26: review round 1 applied: the second launch probe after `install-deps` (AC1, the edge-case matrix); the
  library, apt-rate, `main`-run and suite-cut wording; the line citation pinned to `a3cfc63fcd`.

## Review Triage Log

- 2026-10-26, round 1 (an independent reviewer reading commit `84f12d8258` against this spec and CAP-174): PASS, no
  blocker or major; four minor and six nit findings, every one applied. Minor: `libnss3` and `libglib2.0-0t64` took a
  point upgrade (the wording said every library was already the newest); run 39925508594 finished its suite and is a
  `main` push run too; two `main` push runs, not one, and "merged unseen" was wrong for them; the matrix's
  failed-download row (the install line reds the step under `bash -e`). Nit: `1,033 s` spelled alike in the comment
  and the ACs; `platform-ci.yml:234` pinned to the base; "the last 200 test jobs"; the apt figures are a range
  (23.9–25.9 MB, 38–43 kB/s) and the 636–668 s are the whole step; the flag-exempt value is recorded though not
  required; the step launches the browser again after `install-deps` and reds with an `::error::` when it still does
  not launch. The reviewer ran the step under `bash -e` with a stub `python` (both branches, both failure exits) and
  confirmed every figure against the Actions API.
