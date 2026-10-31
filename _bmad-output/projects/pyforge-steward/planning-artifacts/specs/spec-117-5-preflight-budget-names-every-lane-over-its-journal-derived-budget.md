---
title: "117.5: preflight-budget names every lane over its journal-derived budget"
type: 'feature'
created: '2026-10-27'
status: 'done'
followup_review_recommended: false
baseline_revision: 'c66c5f855d8301f45e996f036a1fe8a741932623'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a CI job, a test task or a preflight report (spec-feature-flag-governance Q1; roster list)
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
  - docs/dreams/pyforge-steward.md
  - docs/governance/ci-surfaces.yaml
  - .github/workflows/pyforge-station-tests.yml
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
---

<intent-contract>

## Intent

**Problem:** Nothing enforces or even reports the per-lane cost: `preflight-budget` (Story 71.7) is report-only with a 60 s default that no hook runs, so a lane can grow 35× (steward's did) and the first sign is a 20-minute pre-push.

**Approach:** A steward-owned `docs/governance/preflight-budgets.toml` (sibling of `coverage-thresholds.toml`) with per-mode defaults and per-lane budgets; `preflight_budget.judge_run` gains per-lane judgement from `lane_medians`; `scripts/pre_push_preflight.sh` runs `preflight --budget` after a green preflight and prints the rows. Exit codes do not change (D3). Flipping to red is a later one-line story once the numbers settle.

Ledger key: `117-5-preflight-budget-names-every-lane-over-its-journal-derived-budget`.
Type / Effort / Deps: feature / S / none.

### Living CAP citations

- **`spec-pyforge-steward` CAP-175** — the preflight and a PR's CI answer within a measured budget, and a station suite runs once, as its package-local and live-tree halves; this story is one of its eight parts (Epic 117). Operator rulings D1–D4 of 2026-10-27 in the Spec's `.memlog.md`.
- **`spec-pyforge-steward` CAP-159** (Epic 71: the preflight's journal, CI-rule lane selection, concurrency, coverage reuse, xdist for the then-large suites) and **CAP-166** (the CI surfaces registry, its switches and render) — extended, not rewritten.
- **`spec-pyforge-steward` CAP-174**, **`spec-pyforge-core:CAP-8`** (the shared-surface rule) and **`spec-coverage-gate-independence`** — kept as written.

## Acceptance Criteria

- **AC1 — The file.** `docs/governance/preflight-budgets.toml` exists with `[defaults]` and `[lanes]`, and `preflight_budget` reads it (a missing lane uses the mode default).
- **AC2 — The rows.** On a journal fixture with one lane at 2× its budget the report names the lane, its median, its budget and the delta; on a journal with every lane under budget it prints nothing but the totals.
- **AC3 — Warn only.** `preflight-budget` exits 0 on an over-budget fixture; `pre_push_preflight.sh` exits with the preflight's code regardless of the report.
- **AC4 — Journal only.** The report reads `.steward/preflight-runs.jsonl` through `_read_journal` and starts no process.

## Boundaries & Constraints

**Always:**
- Read every verdict from an exit code, never through a pipe; keep `PYFORGE_PREFLIGHT_SKIP=1` the one journaled opt-out.
- Regenerate `environment.yaml` in the same PR as any `pixi.toml` edit; label the PR `maintenance`.

**Never:**
- Never skip a lane where CI's own rule would run it; never delete, skip or re-mark a test to meet a budget; never narrow a `*_paths` array by hand (Story 98.1, rulings 2026-10-12); never pause, disable or set `continue-on-error` on a lane; never hand-edit `SPEC.md`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-steward` CAP-175.

Parent: `spec-pyforge-steward` CAP-175

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-27 (the preflight answers in eleven minutes, a PR's CI in thirteen) entry.
- Epic: Epic 117, minted with this story.
- Ledger key: `117-5-preflight-budget-names-every-lane-over-its-journal-derived-budget`.
- Deps: none.
- Surface: `marshal-policy.toml` `[epic_surfaces]."117"`.
- Minted 2026-10-27 in one chain commit (the preflight and CI budget effort: steward Epic 117; doctor, herald, mason, atlas, scribe and warden chains follow).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass; `tests/unit/test_preflight_budget.py` is in the suite.

**Manual checks (the Commands bind to the policy verify command; these are the story's own proof):**
- `pixi run -e pyforge-guild preflight-budget` — expected: exit 0; the report lists any lane over budget.

**Run before the push:**
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check`, `spec-surface-check` — expected: exit 0 each.

## Auto Run Result

Status: done

Summary: Added `docs/governance/preflight-budgets.toml` with mode defaults and journal-derived per-lane budgets; `preflight_budget` compares `preflight.lane_medians` at 1.5× budget (warn-only, exit 0); `pre_push_preflight.sh` runs `preflight --budget` after a green pr-preflight; tests and memlogs updated; `pyforge-steward-test` and `spec_surface_reconcile.py` green.

Files changed:
- `docs/governance/preflight-budgets.toml` — declared per-lane budgets (CAP-175 measurement baseline 2026-10-27).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_budget.py` — load TOML, per-lane report, D3 exit codes.
- `scripts/pre_push_preflight.sh` — post-green budget report (`|| true`).
- `src/shared/packages/pyforge-steward/tests/unit/test_preflight_budget.py` — AC2/AC3/unknown lane/empty journal.
- `src/shared/packages/pyforge-steward/tests/unit/test_preflight_lane_identity.py` — warn-only judge_run line.
- `pixi.toml`, `environment.yaml`, derived docs — preflight-budget task description.

Review: 2026-10-31 pass — 0 findings (self-review against AC1–AC4; steward suite 1744 passed).

Verification:
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — exit 0.
- `python scripts/spec_surface_reconcile.py` — exit 0.
- `chain-completeness-check`, `story-status-check`, `flag-gate-check`, `spec-surface-check` — exit 0 each.

Residual risk: lane budgets in TOML are static until refreshed from new journal medians; over-budget signal depends on five green runs in `.steward/preflight-runs.jsonl`.

## Spec Change Log

- 2026-10-31: Implemented AC1–AC4 (build-auto); baseline `c66c5f855d`.
- 2026-10-31: Commands rebound to the policy verify command (`pyforge-steward-test`) before dispatch; the story's own checks moved under Manual checks (MRS-GATE-011 otherwise).

- 2026-10-27: minted from the station Dream's entry of 2026-10-27 and the operator's rulings D1–D4 of the same date.

## Review Triage Log

### 2026-10-31 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings:
  - (none)
