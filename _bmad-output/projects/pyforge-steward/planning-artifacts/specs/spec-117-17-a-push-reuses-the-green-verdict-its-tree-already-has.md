---
title: '117.17: A push reuses the green verdict its tree already has'
type: 'feature'
created: '2026-11-26'
status: 'ready-for-dev'
story: 117-17-a-push-reuses-the-green-verdict-its-tree-already-has
spec: spec-pyforge-steward
difficulty: 'medium'
flag-exempt: detector-or-gate   # the preflight is a check that judges; a gated gate reports a silent green (spec-feature-flag-governance Q2)
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_preflight_verdict_reuse.py'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/oracle-map.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The operator runs the full preflight before a push, as AGENTS.md asks, and the pre-push hook then runs `pr-preflight` again on the same tree: 98 s at touched scope, about ten minutes at full, judging nothing a green run has not judged.

**Approach:** Before any install or lane, `pr-preflight` looks in its journal for a run with verdict `ok` whose recorded tree hash, base commit and gate-variable digest (`PYFORGE_*`, `HERALD_*`, `CI*` and `PYTEST_ADDOPTS`) equal this run's, and in which every lane this run selects passed; that makes a wider scope cover a narrower one and never the reverse. The tree hash covers the lane graph and `pixi.lock`, which are tracked files, so neither needs a digest of its own. On a clean working tree with such a run it prints the run it reuses, journals a `reuse` record naming it, and exits 0. Each run of a clean tree that did not move while its lanes ran journals those three values. Anything else runs the lanes. `PYFORGE_PREFLIGHT_REUSE=0` runs them regardless.

Ledger key: `117-17-a-push-reuses-the-green-verdict-its-tree-already-has`.

### Living CAP citations

- spec-pyforge-steward CAP-154 (un-preflighted pushes are refused; realized, no text change).
- spec-pyforge-steward CAP-175 / FR-49.
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Measure before and after with the harness that measured the baseline (same tree shape, same machine).
- Journal every reuse with the run id it reuses.

**Never:**
- Never reuse a red, interrupted or deferred-lane verdict, a verdict of a narrower scope, or a `reuse` record itself.
- Never reuse across a dirty or untracked file, another tree, another base or another lane graph.

## Acceptance Criteria

**Given** a journaled green run of this tree at this scope or wider
**When** `pr-preflight` runs again on the clean tree
**Then** it exits 0 without starting a lane and journals the reuse
**And** every difference the story names runs the lanes

- **AC1 — The reuse tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_preflight_verdict_reuse.py -q
  ```

- **AC2 — A second full preflight of an unchanged clean tree reuses the first.** Expected: exit 0 in under 15 s, a `reuse` record in `.steward/preflight-runs.jsonl`.

  ```bash
  PYFORGE_PREFLIGHT_SCOPE=full pixi run --frozen -e pyforge-guild pr-preflight
  ```

</intent-contract>

## Evidence (2026-11-26)

`grep -n head_sha src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py`: the head sha is journaled and never read back. Two full runs of one tree: 606 s and 652 s.
