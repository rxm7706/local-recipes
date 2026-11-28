---
title: '117.40: Platform CI''s opt-in jobs run on a dispatch only when its inputs ask'
type: 'fix'
created: '2026-11-27'
status: 'done'
story: 117-40-platform-ci-s-opt-in-jobs-run-on-a-dispatch-only-when-its-inputs-ask
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'docs/governance/ci-surfaces.yaml'
  - '.github/workflows/platform-ci.yml'
  - 'tests/scripts/test_ci_surface_gates.py'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - scripts/_ci_surface_gates_render.py
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** a bare dispatch of `Platform CI` (no inputs), as the runner-times probe (46102692069) and PR #2446's proof run (46105322486) were, runs four jobs:
- `gke-portability-smoke` and `ocp-portability-smoke`, which fail at `helm install` ("sidecar.image.digest or sidecar.image.tag is required");
- `air-gap-parity`;
- `build-platform-image`, the image build the three share.

Each job's own condition reads its dispatch input (`air_gap_parity`, `gke_portability_smoke`, `ocp_portability_smoke`, each default off). But the fragment `ci_surface_gates.py --render` puts in front of it, `dispatch || (pause switches && inner)`, lets every dispatch past it.

**Approach:** mark the six registry rows of those four jobs `dispatch: pause-only` in `docs/governance/ci-surfaces.yaml`. That is the shape Story 102.3 gave `pages.deploy`, rendered as `(dispatch || pause switches) && inner`. Then re-render. For a push or a pull request the two shapes are the same expression: `false || (p && i)` and `(false || p) && i` both reduce to `p && i`. On a dispatch, each job's input now decides. `test_the_live_pages_deploy_row_renders_pause_only` pins the exact set of pause-only jobs.

Ledger key: `117-40-platform-ci-s-opt-in-jobs-run-on-a-dispatch-only-when-its-inputs-ask`.

### Living CAP citations

- spec-pyforge-steward CAP-166 (the CI pause registry and its rendered fragments) and CAP-175 / FR-49 (realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- A push or pull request evaluates every condition exactly as before; a dispatch still bypasses the pause switches.

**Never:**
- Never change the `jobs` choice input's handling, or any other job's condition.

## Acceptance Criteria

**Given** a dispatch of Platform CI with no inputs
**When** the four jobs' conditions are rendered pause-only
**Then** none of the four runs, and with an input set the job it names runs
**And** the CI-surface check and its tests pass

- **AC1 — The registry and the rendered conditions agree.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild python scripts/ci_surface_gates.py --check
  ```

- **AC2 — The CI-surface tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_ci_surface_gates.py -q
  ```

- **AC3 — A bare dispatch on the branch.** Expected: the four jobs are skipped.

</intent-contract>

## Result (2026-11-27)

`--render` changed exactly the four jobs' `if:` lines, each with balanced parentheses, and `--render --dry-run` then reports nothing to change. `test_ci_surface_gates.py` passes (25), and steward's preflight-selection and workflow-filter tests pass (109).
