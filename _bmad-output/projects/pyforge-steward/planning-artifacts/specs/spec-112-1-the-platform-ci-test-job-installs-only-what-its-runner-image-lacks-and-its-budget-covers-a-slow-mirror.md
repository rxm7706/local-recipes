---
title: "112.1: The Platform CI `test` job installs only what its runner image lacks, and its budget covers a slow mirror"
type: 'fix'
created: '2026-10-26'
status: 'in-progress'
baseline_revision: 'a3cfc63fcd5a33266fb3164ce7cda8f2bf4a0322'
flag-exempt: detector-or-gate   # a CI job's install step and budget; a flag-gated gate reports a silent green
review_loop_iteration: 0
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

- **The cancellations.** Runs 39925508594 (2026-10-23), 40306113110 (2026-10-26, `main`'s own push run) and
  40351088193 (attempt 1, PR #2322) were cancelled at 909–919 s, the suite cut at 59–69 %.
- **The one slow step.** `Install Chromium for the herald deck viewer browser check`
  (`python -m playwright install --with-deps chromium`, `platform-ci.yml:234`) took 636–668 s on those runs and 23 s
  at the median. Its apt download of 25.9 MB from `azure.archive.ubuntu.com` ran at about 41 kB/s (`Fetched 25.9 MB
  in 10min 7s`). The browser zips come from Playwright's CDN in 8–11 s on every run, slow or fast.
- **What apt installed.** apt reported every library the headless shell links (`libnss3`, `libnspr4`, `libgbm1`,
  `libatk1.0-0t64`, `libatk-bridge2.0-0t64`, `libcups2t64`, `libxkbcommon0`, `libxcomposite1`, `libxdamage1`,
  `libxrandr2`, `libasound2t64`, `libpango-1.0-0`, `libcairo2` and the rest) as already the newest version. It
  installed nine font packages (`fonts-ipafont-gothic`, `fonts-wqy-zenhei`, `fonts-tlwg-loma-otf`, `fonts-unifont`,
  `fonts-freefont-ttf`, four `xfonts-*`) and upgraded eight (`libglib2.0-*`, `libnss3`, `xvfb`). The one browser
  test, `test_playwright_records_zero_foreign_origin_requests` (`src/platform/tests/test_herald_portal_deck_viewer.py:418`),
  launches `playwright.chromium.launch()` and counts request origins.
- **The rest is not slow.** Every other step sums to 365 s at worst over 178 green jobs. The pixi install is 15 s at
  the median and 26–32 s on a cache miss (`main` runs 40229905972, 40231618468, 40254324378 read `Cache miss`); the
  suite is 197 s at the median and 243 s at worst, and on the cancelled runs it kept the fast run's pace.
- **Unseen.** `main` has no required status check, so PR #2322 merged past the cancelled attempt.

**Approach:**

- **Install only what the image lacks.** The step runs `python -m playwright install chromium` (the browser alone),
  launches it once in a short Python probe, and runs `python -m playwright install-deps chromium` only when that
  launch fails, after a `::warning::` that names the fallback. On today's image the log reads the launch succeeding
  and shows no apt call.
- **A budget sized from what the job does.** `timeout-minutes` moves from 15 to 25. The slowest path the job can still
  take is the fallback on the slowest mirror measured (668 s) plus the worst of the other steps (365 s): 1,033 s.
  1,500 s leaves about 45 % headroom; without the fallback the job runs about 6 minutes. The comment beside the
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
  `flag-exempt: detector-or-gate` (a CI job's own install step and budget).
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, the 2026-10-26 entry (the Platform CI test job's budget
  is sized for a fast mirror).

## Acceptance Criteria

- **AC1 — The step.** The `test` job's Chromium step runs `python -m playwright install chromium`, then a launch probe;
  `python -m playwright install-deps chromium` appears only in the probe's failure branch, after a `::warning::` line.
  `--with-deps` appears nowhere in the job.
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
| image missing a library | fails | `install-deps` | warning, then green; up to ~17 min on the slowest mirror seen |
| slow apt mirror, libraries present | launches | none | unaffected |
| browser download fails | fails | `install-deps` | the browser test reds the job: loud, never a skip |

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

## Review Triage Log

