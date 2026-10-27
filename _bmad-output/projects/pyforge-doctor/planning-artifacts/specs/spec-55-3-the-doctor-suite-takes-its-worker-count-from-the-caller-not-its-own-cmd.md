---
title: "55.3: The doctor suite takes its worker count from the caller, not its own cmd"
type: 'chore'
created: '2026-10-27'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-doctor.md
  - docs/dreams/pyforge-steward.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/hygiene.py
  - scripts/chain_currency_sweep_check.py
  - pixi.toml
---

<intent-contract>

## Intent

**Problem:** Story 71.6 made the doctor suite xdist but pinned four workers in the task's own cmd; the preflight then cannot hand the lane its share (steward `preflight.py:1040-1042` sets the variable the cmd overrides), and a laptop with sixteen cores runs the suite on four.

**Approach:** Drop the `env …=4` prefix; `-n auto` takes `PYTEST_XDIST_AUTO_NUM_WORKERS` from the environment when set (the preflight sets it) and the CPU count otherwise. CI's runner has four vCPUs, so the CI job's worker count is unchanged without a pin; the description names the new contract.

Ledger key: `55-3-the-doctor-suite-takes-its-worker-count-from-the-caller-not-its-own-cmd`.
Type / Effort / Deps: chore / XS / none.

### Living CAP citations

- **spec-pyforge-steward:CAP-175 (relay: the preflight hands each xdist lane its share; Story 71.6 made the suite xdist) — no doctor CAP.**
- **`spec-pyforge-steward:CAP-175`** — the preflight and a PR's CI answer within a measured budget, and a station suite runs once, as its package-local and live-tree halves; doctor's part of its fleet, measured and ruled 2026-10-27 (D1–D4 in that Spec's `.memlog.md`).
- **`spec-pyforge-doctor` AD-1, AD-2, AD-5** — a Doctor source is a library call; the exit-code space is closed; `run_git` is the one subprocess site.

## Acceptance Criteria

- **AC1 — The cmd.** `pixi.toml`'s `pyforge-doctor-test` cmd carries no `PYTEST_XDIST_AUTO_NUM_WORKERS`; `-n auto --dist loadgroup` and the `--ignore` + alone-run of the speed budget stay.
- **AC2 — Share applies.** In a touched-scope preflight on a doctor-only diff, the journal's `pyforge-doctor-test` lane ran with the preflight's share (the lane env the `test_preflight_workers.py` fixture reads), not four.
- **AC3 — Green everywhere.** `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` passes locally with the same collected count; the `doctor-test` CI job passes.

## Boundaries & Constraints

**Always:**
- Keep every finding's shape and verdict; read every verdict from an exit code, never through a pipe.
- Keep `run_git` the one subprocess site for `git grep`; keep the exit-code space `{0, 2, 130}`.

**Never:**
- Never delete, skip or re-mark a test to meet a time; never narrow `doctor_paths` by hand (Story 98.1, rulings 2026-10-12); never hand-edit `SPEC.md`; never reimplement a Doctor source as a subprocess.

</intent-contract>

## Binding

- Parent capability: spec-pyforge-steward:CAP-175.

Parent: spec-pyforge-steward:CAP-175

- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-27 (the repo-scope detectors and the doctor suite answer in seconds) entry.
- Epic: Epic 55, minted with this story.
- Ledger key: `55-3-the-doctor-suite-takes-its-worker-count-from-the-caller-not-its-own-cmd`.
- Deps: none.
- Surface: `marshal-policy.toml` `[epic_surfaces]."55"`.
- Minted 2026-10-27 in one chain commit beside steward Epic 117 (the preflight and CI budget effort).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass.
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_preflight_workers.py -q` — expected: pass.

**Run before the push:**
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check`, `spec-surface-check` — expected: exit 0 each.

## Auto Run Result

Status: done

Summary: built in PR #2331 (2026-10-27): the `env PYTEST_XDIST_AUTO_NUM_WORKERS=4` prefix left `pyforge-doctor-test`; the description names the contract. The full doctor suite measured 38.9 s on 16 workers locally (390 s on four).

## Spec Change Log

- 2026-10-27: minted from the station Dream's entry of 2026-10-27 beside steward Epic 117 (spec-pyforge-steward:CAP-175).

## Review Triage Log

- (none yet)
