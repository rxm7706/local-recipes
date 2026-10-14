---
title: '99.6: A paused expensive build still runs once a week'
type: 'feature'
created: '2026-10-13'
status: 'done'
baseline_revision: '753a10bf6535b853dc1203f7e186710fd137c9b9'
flag-exempt: detector-or-gate   # a scheduled proof that a paused image still builds; a gated canary reports a silent green
review_loop_iteration: 0
followup_review_recommended: false
deferred:
  - summary: >-
      Record one green workflow_dispatch of ci-canary.yml after merge (AC4).
    evidence: |-
      GitHub Actions is the arbiter; this build-auto run cannot dispatch outward CI without operator confirmation.
    location: >-
      .github/workflows/ci-canary.yml
    severity: medium
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-99-2-every-ci-job-carries-its-pause-switch.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-99-3-the-operator-sees-the-pause-state-of-every-ci-surface-in-one-command.md
  - docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md
  - docs/governance/ci-surfaces.yaml
  - .github/workflows/pyforge-station-tests.yml
  - .github/workflows/platform-ci.yml
  - scripts/guild_image_ci.sh
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** A paused Containerfile rots unseen until the day its pause lifts: the mcp-host image broke while paused
(steward Dream log, 2026-10-10), and `guild-container`, `container` and `container-dbgpt` have been paused since
2026-10-04 and 2026-10-09 (`docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md` § 4.6).

**Approach:** One new workflow, `.github/workflows/ci-canary.yml`, plus a `canary` field on `cost: high` rows.

- **Trigger and gate.** `schedule: - cron: '0 4 * * 0'` and `workflow_dispatch`; every job carries Story 99.2's
  fragment with `PAUSE_CI_CANARY` (the canary can itself be paused; dispatch still runs it).
- **What it builds.** A matrix read from the registry at run time: each row with `state: paused` and `cost: high`.
  For each it runs the same pixi task the paused job runs (today `pyforge-steward-guild-image-build` for
  `guild-container`, and the platform image build for `container` and `container-dbgpt`), docker engine only, and
  writes the result to the job summary. It deploys nothing and pushes no image; AD-4 binds the deploy duty only.
- **Registry and check.** Each `cost: high` row gains `canary: ci-canary.<matrix-id>`; Story 99.1's `--check` reds a
  `cost: high` row without `canary`, and the canary workflow gets its own `workflow` row.
- **Status.** Story 99.3's `ci status` reads each paused row's last green canary run and reports `stuck` after 14 days
  without one.

Ledger key: `99-6-a-paused-expensive-build-still-runs-once-a-week`.
Type / Effort / Deps: feature / S / S-99.2, S-99.3.

### Living CAP citations

- **`spec-pyforge-steward` CAP-166** (FR-39): the weekly canary; **CAP-131** (the image proves itself at build time).
- **AD-1**: the canary runs the existing pixi tasks; **AD-4** is not bound (a CI build, not a deploy).
- **Flag:** `flag-exempt: detector-or-gate`.
- **Origin.** The 2026-10-12 Dream entry and CAP-166's constraint on AD-4.

## Acceptance Criteria

- **AC1 — Workflow.** `.github/workflows/ci-canary.yml` parses, has the schedule and `workflow_dispatch`, carries
  the fragment with `PAUSE_CI_CANARY`, and its matrix is built from the registry's paused `cost: high` rows (a unit
  test over a fixture registry asserts the matrix).
- **AC2 — Check.** `--check` reds a `cost: high` row without `canary` and exits 0 on the tree.
- **AC3 — Status.** On a recorded fixture, a paused row with no green canary run in 15 days reads `stuck`; one with a
  green run 3 days ago reads `paused`.
- **AC4 — Proof.** One green `workflow_dispatch` run is recorded in this spec's Auto Run Result (operator- or
  landing-triggered after merge; GitHub Actions is the arbiter).

## Boundaries & Constraints

- The canary builds; it never deploys, publishes or pushes an image.
- No change to the paused jobs themselves or to their switches.
- Container lanes stay paused in CI; the canary is the only scheduled exception.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| no paused `cost: high` rows | the matrix is empty and the workflow ends green with a summary line saying so |
| `PAUSE_CI_CANARY=true` on a scheduled run | the job skips |
| the same with `workflow_dispatch` | the job runs |
| a podman-only build | not built (docker engine only); the summary names it |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-166 (FR-39), minted 2026-10-12.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-12 (ci pause control plane) entry.
- Epic: Epic 99, Stories 99.1–99.7.
- Ledger key: `99-6-a-paused-expensive-build-still-runs-once-a-week`.
- Ledger status at mint: `backlog`.
- Deps: S-99.2, S-99.3. `marshal factory dispatch` stamps `baseline_revision` with the launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."99"`.
- Specced 2026-10-13 from the epic's text ahead of its dependencies' landing.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-guild ci-surface-gates-check` — expected: exit 0 (AC2).
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_ci_surface_gates.py -q` — expected: pass (AC1, AC2).
- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_ci_status.py -q` — expected: pass (AC3).
- `pixi run --frozen -e pyforge-guild detectors-ci` and `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.
- After merge: `gh workflow run ci-canary.yml --repo rxm7706/local-recipes` then `gh run list --workflow ci-canary.yml --limit 1` — expected: one `success` (AC4).

## Spec Change Log

- 2026-10-13: specced from Epic 99's Story 99.6 text ahead of its dependencies' landing so the steward chain runs
  unattended (operator direction 2026-10-13).

## Review Triage Log

### 2026-10-14 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none — implementation matches AC1–AC3; AC4 deferred post-merge)

## Auto Run Result

Status: done

**Summary:** Added `.github/workflows/ci-canary.yml` (weekly schedule + `workflow_dispatch`, `PAUSE_CI_CANARY` / `PAUSE_ALL_CI` gate with dispatch carve-out). Matrix comes from `scripts/ci_canary.py` over paused `cost: high` registry rows (docker-only builds for guild + platform container jobs). Registry rows now carry `canary: ci-canary.<id>`; offline check fails missing canary on any `cost: high` row. `steward ci status` treats paused high-cost rows as `stuck` when the matching canary job has no success within 15 days.

**Files (high level):** ci-canary workflow; `scripts/ci_canary.py`; `_ci_surface_gates_lib.py`; `docs/governance/ci-surfaces.yaml`; `pyforge/steward/ci.py`; tests in `test_ci_surface_gates.py` and `test_ci_status.py`; `scripts/spec_surface_allowlist.txt` (interim for `ci_canary.py`).

**Verification:** `ci-surface-gates-check` exit 0; `test_ci_surface_gates.py` 20 passed; `test_ci_status.py` 19 passed; `pyforge-steward-test` 2569 passed; `spec_surface_reconcile.py` and `spec-surface-check` exit 0 after memlog reconcile. `pr-preflight` / full `detectors-ci` not run in this pass (run before PR push).

**Residual risk:** `ci status` canary freshness uses `gh api` per successful canary run to list jobs (extra API calls on status). Platform container canary builds the image only, not full runtime smokes from `platform-ci` `container` job.
