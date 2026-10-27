---
title: "117.9: The steward suite's slowest tests shed their subprocesses, repos and sleeps"
type: 'chore'
created: '2026-10-27'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-117-1-the-steward-suite-runs-under-pytest-xdist-and-its-serial-remainder-alone.md
  - docs/dreams/pyforge-steward.md
  - src/shared/packages/pyforge-steward/tests/unit/test_workspace_stacked_landing.py
  - src/shared/packages/pyforge-steward/tests/unit/test_estate.py
---

<intent-contract>

## Intent

**Problem:** Story 117.1 put the steward suite under `pytest-xdist` and the lane fell from 698 s to 186 s on 16 workers — still 0.9 worker-seconds per test, because the heaviest files create 19 real `git init` repos, run ~60 `subprocess.run` calls (`pixi run …`, `python -m pyforge.steward …`) and poll with `time.sleep`. Parallelism cannot buy the ≤ 70 s mark CAP-175 names for a single-station branch; the tests' own cost must fall.

**Approach:** Take the `--durations=30` list 117.1 recorded and fix by class: one module-scoped `git init` template copied with `shutil.copytree` per test instead of a fresh `git init` each; `cli.main(argv)` in-process where a `pixi run` subprocess proves nothing extra, keeping one true subprocess test per entry point for the exit-code domain (AD-8); `threading.Event.wait` on the coordinator's events instead of polling sleeps. No test is deleted, skipped or re-marked; the three alone-run files keep their real signals.

Ledger key: `117-9-the-steward-suite-s-slowest-tests-shed-their-subprocesses-repos-and-sleeps`.
Type / Effort / Deps: chore / M / 117.1.

### Living CAP citations

- **`spec-pyforge-steward` CAP-175** — the preflight answers within a measured budget; this is the test-level half of its steward-suite story, split from 117.1 at build on 2026-10-27.
- **`spec-pyforge-steward` AD-8** — exit-code sole ownership: one true subprocess test per entry point stays.

## Acceptance Criteria

- **AC1 — Same count.** `pixi run --frozen -e pyforge-steward pyforge-steward-test` collects the count 117.1 recorded (3056) and passes.
- **AC2 — The mark.** A touched-scope `pr-preflight` on a steward-only diff journals `pyforge-steward-test` at ≤ 70 s on 16 cores.
- **AC3 — By class.** No `git init` in a per-test fixture where the template fixture serves; no `pixi run` subprocess in a test that an in-process `cli.main(argv)` call covers, except the one kept per entry point; no `time.sleep` polling loop in the preflight tests.
- **AC4 — Nothing cut.** No test deleted, skipped or re-marked; the alone-run files unchanged in count.

## Boundaries & Constraints

**Always:**
- Keep one true subprocess test per CLI entry point; keep the exit-code domain tests real.

**Never:**
- Never delete, skip or re-mark a test to meet the mark; never mock away the behaviour a test exists to prove.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-steward` CAP-175.

Parent: `spec-pyforge-steward` CAP-175

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-27 (the preflight answers in eleven minutes, a PR's CI in thirteen) entry.
- Epic: Epic 117 (split from Story 117.1 at build, 2026-10-27).
- Ledger key: `117-9-the-steward-suite-s-slowest-tests-shed-their-subprocesses-repos-and-sleeps`.
- Deps: 117.1.
- Surface: `marshal-policy.toml` `[epic_surfaces]."117"`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass, 3056 collected.
- `PYFORGE_PREFLIGHT_SCOPE=touched pixi run -e pyforge-guild pr-preflight` on a steward-only diff — expected: exit 0; the journal's `pyforge-steward-test` lane ≤ 70 s.

## Auto Run Result

Status: backlog

Summary: not started.

## Spec Change Log

- 2026-10-27: split from Story 117.1 at build, when xdist alone measured 186 s against the ≤ 70 s mark.

## Review Triage Log

- (none yet)
