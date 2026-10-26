---
title: "99.8: A red main run on a CI surface reaches the next preflight"
type: 'fix'
created: '2026-10-25'
status: 'in-review'
baseline_revision: '529f06d52b6d6469b847519905c20bf528a60334'
flag-exempt: detector-or-gate   # a fix needs no flag (spec-feature-flag-governance Q1; operator ruling 2026-10-25 "Fix, no flag (Recommended)"), and pr-preflight is a gate
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/retros/retro-pyforge-atlas-2026-10-25.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/ci.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/data/ci-status-schema.json
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_ci.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
  - docs/how-to/pause-ci.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** a workflow that fails on `main` and gates no PR is red in silence. Line numbers are at `529f06d52b`.

- The atlas `kedro-viz-publish` workflow's `vizro` job failed on five consecutive merges to `main` on 2026-10-23, and 7
  of its last 15 `main` runs failed; each next landing went ahead without knowing (the 2026-10-25 atlas retro's
  Finding 2, candidate fix 3). `main` has no required checks, and a PR's own checks never include a push-only workflow.
- `steward ci status` already lists each registered workflow's last 20 runs (`ci.py:191`-`:216`, `--json
  databaseId,conclusion,status,createdAt,event`) and reports only `last_green_run`; it never reads `headBranch`.
- `pr-preflight` already prints CI pause lines from the gitignored `.steward/ci-vars.json` when the snapshot is under
  24 hours old and `pyforge.steward.ci_pause_control` is on (`preflight_ci.py:584`-`:700`; `preflight.py:1122`-`:1138`).

**Approach (operator rulings 2026-10-25: "Red-main banner (Recommended)", "Fix, no flag (Recommended)"):**
- `_fetch_runs` asks for `headBranch` too. Each surface row gains `latest_main_run`: the newest run of its workflow
  with `headBranch == "main"` and `status == "completed"`, as `{conclusion, created_at, run_id}`, or `null` when the
  listed runs hold none (and for a retired row). The schema gains that row property; the envelope stays frozen and
  additive (`additionalProperties: false` is kept by declaring it).
- `run_status` writes the envelope it built to `.steward/ci-status.json` (gitignored), complete or partial and
  atomically, so any `ci status`, including the one marshal's landing runs, refreshes it; a `.steward/` it cannot write
  is named in the result's details and never costs the envelope.
- `pr-preflight`, when the flag is on, reads that snapshot and prints `preflight: main is red on <id>: <conclusion>,
  run <run_id> (<created_at>)` for each row whose `latest_main_run` conclusion is not `success`, `skipped` or
  `neutral` or `cancelled` (a run a newer push superseded says nothing about `main`), one line per workflow run (rows
  of one workflow share it). A snapshot older than 24 hours, missing or
  unreadable (or dated in the future) prints one line saying so, and the banner never raises. It is advisory only: lane selection, the verdict and the exit code never
  change, and the preflight makes no GitHub call.
- A `fix` under CAP-166 ("visible in one place"): no CAP, no flag.

Ledger key: `99-8-a-red-main-run-on-a-ci-surface-reaches-the-next-preflight`. Type / Effort / Deps: fix / S / —.

## Acceptance Criteria

- **AC1 — The row.** For runs listed newest first, `latest_main_run` is the first completed run on `main`; an
  in-progress `main` run, a run on another branch, and a PR run are skipped; `null` when none qualifies; a retired row
  reads `null`. Unit tests pin each case.
- **AC2 — The schema.** Every `ci status --json` envelope, the repo's fixtures included, validates against
  `ci-status-schema.json` with the new property; the property is optional, so an envelope without it still validates.
- **AC3 — The snapshot.** `run_status` writes `.steward/ci-status.json` (the envelope plus nothing else) on a complete
  and on a partial read; `.gitignore` ignores it.
- **AC4 — The banner.** With the flag on and a fresh snapshot, `pr-preflight` prints one line per red `main` run and
  nothing for a green one; a stale, missing or unreadable snapshot prints one line; with the flag off it prints nothing;
  selection, verdict and exit code are the same as without the banner. Unit tests pin each case.
- **AC5 — Docs and gates.** `docs/how-to/pause-ci.md` names the field and the banner; `pixi run --frozen -e
  pyforge-steward pyforge-steward-test` passes.

## Boundaries & Constraints

**Never:** make the banner block, change lane selection, add a GitHub call to the preflight, or remove or rename an
envelope field.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-steward` CAP-166. No CAP is minted.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, 2026-10-25 (a red main run reaches no landing).
- Epic 99 (done; reopened by this story under doctor Story 41.5's rule). Ledger key above. Deps: —.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0, read from a file (on a
  host whose `/tmp` is tmpfs, with `TMPDIR` on the repository's filesystem).

**Manual check (not a dispatch gate):** `pixi run -e pyforge-steward pyforge steward ci status --json` writes
`.steward/ci-status.json`; a following `pr-preflight` names any red `main` run.

## Spec Change Log

- 2026-10-25: drafted from the Dream entry of 2026-10-25 and the 2026-10-25 atlas retro's candidate fix 3, at the
  operator's rulings "Red-main banner (Recommended)" and "Fix, no flag (Recommended)".
- 2026-10-25: review round 1 FAIL on AC4, fixed: a call-site test (flag on and off, a red, an unreadable and an odd
  snapshot: same lanes, same exit code), the banner never raises, the snapshot write is atomic and cannot cost the
  envelope; `cancelled` is not red; a future `fetched_at` is not fresh; a boolean run id is not a run id. Moved to
  `in-review`.

## Run results

2026-10-25, after the round-1 fixes:
- `test_ci_status.py`, `test_preflight_ci.py`, `test_preflight.py`: pass. Mutations: removing the banner call, or
  moving it outside the flag gate, fails `test_the_red_main_banner_never_changes_the_run` (AC4).
- jsonschema (2020-12): the master-on fixture, a payload with the field, a row without it: valid; a malformed
  `latest_main_run` is rejected (AC2).
- `git check-ignore -v .steward/ci-status.json`: `.gitignore:1001` (AC3).
- `pixi run -e pyforge-guild lint-types`: exit 0; `docs-currency` no longer warns on `pause-ci.md` (verified 2026-10-25).

## Review Triage Log

**Review 1 (independent, 2026-10-25): FAIL** — AC1-AC3 met, AC4 and AC5 partly. 2 must-fix, 3 should-fix, 12 nits.
- must-fix: no test covered the call in `preflight.py`. Fixed: `test_the_red_main_banner_never_changes_the_run`.
- must-fix: invalid UTF-8 or an unhashable row id raised out of the banner. Fixed: decode errors read as unreadable,
  keys are strings, and `print_main_red_banner` catches anything else as one `main CI state unknown` line.
- should-fix: an unwritable `.steward/` crashed `ci status`. Fixed: an atomic write whose `OSError` lands in
  `details["status_snapshot_error"]`.
- should-fix: `pause-ci.md` verified date stale. Bumped; the field, the flag gate, the rows without the field and the
  dispatch gap are now stated.
- should-fix (71.14's): see that spec.
- nits fixed: `cancelled` not red; a future `fetched_at` not fresh; a boolean run id; `pull_request_target` pinned; the
  epics `Then` and the Dream say one line per red run; the fixture is on the Surface line. Left: `--limit 20` without
  `--branch main` (the field reads `null` for a workflow whose last 20 runs are all PR runs, as stated in the doc), and
  a dispatched landing still skips `pr-preflight` (stated in the doc).
