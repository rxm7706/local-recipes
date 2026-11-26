---
title: '117.15: A fresh worktree admits lanes longest-first and an xdist lane''s workers follow its expected work'
type: 'fix'
created: '2026-11-26'
status: 'ready-for-dev'
story: 117-15-a-fresh-worktree-admits-lanes-longest-first-and-an-xdist-lane-s-workers-follow-its-expected-work
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_xdist.py'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_budget.py'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_preflight_critical_path.py'
  - 'docs/governance/preflight-budgets.toml'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Story 117.3's admission is inert on the run that matters most. `lane_medians` counts green runs of the worktree's own journal, so a fresh worktree weighs every lane 30 s and admits in declared order; `xdist_share_at_admission` splits the free cores evenly among the xdist lanes still to start, 2 workers each while sixteen are pending. In two full runs `pyforge-marshal-test` took 370 and 417 s where it takes 95 s alone, the steward halves started 132 to 254 s in, and the last 290 s used 22 to 52% of the machine.

**Approach:** A lane with no journal median takes its expected seconds from the tracked `docs/governance/preflight-budgets.toml` (the journal still wins where it has a green run). An xdist lane's share at admission is its part of the free cores in proportion to its expected seconds among the xdist lanes still to start, floored at `MIN_XDIST_WORKERS` and capped by the free cores. Journal each lane's workers. The kill switch `pyforge.steward.preflight_critical_path` turns both off.

Ledger key: `117-15-a-fresh-worktree-admits-lanes-longest-first-and-an-xdist-lane-s-workers-follow-its-expected-work`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (the wall is the longest lane and never a queue; realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Measure before and after with the harness that measured the baseline (same tree shape, same machine).
- Keep the workers of the lanes in flight at or under the logical cores.

**Never:**
- Never change a lane's command, its exit code or the red-lane stop.
- Never start an xdist lane on fewer than `MIN_XDIST_WORKERS`.

## Acceptance Criteria

**Given** a worktree whose journal holds no green run
**When** a full preflight starts
**Then** the longest lanes by the tracked budgets are admitted first and take the larger shares
**And** with the kill switch off the order and shares are the declared ones

- **AC1 — The admission tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_preflight_critical_path.py src/shared/packages/pyforge-steward/tests/unit/test_preflight_xdist.py -q
  ```

- **AC2 — A full preflight on a fresh journal is faster than the baseline.** Expected: exit 0 and `total_seconds` under the 606 s baseline, read from `.steward/preflight-runs.jsonl`.

  ```bash
  PYFORGE_PREFLIGHT_SCOPE=full pixi run --frozen -e pyforge-guild pr-preflight
  ```

</intent-contract>

## Evidence (2026-11-26)

Run 1 (fresh worktree, 50 lanes): 590.5 s of lanes, `pyforge-steward-live-test` admitted at 206.1 s, `pyforge-marshal-test` at 97.8 s. Run 2: 641.0 s, admitted at 253.6 s and 82.3 s. CPU by `vmstat`: 96% busy to 300 s, then 52%, 32%, 23%, 24%, 21% per minute.
