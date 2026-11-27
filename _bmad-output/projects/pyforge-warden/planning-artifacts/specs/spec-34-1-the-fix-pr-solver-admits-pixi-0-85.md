---
title: '34.1: The fix-PR solver admits pixi 0.85'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 34-1-the-fix-pr-solver-admits-pixi-0-85
spec: spec-pyforge-warden
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py'
  - 'src/shared/packages/pyforge-warden/tests/meta/test_engine_version_range_sync.py'
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - docs/dreams/pyforge-warden.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The fix-PR solver refuses a pixi outside `PIXI_VERSION_RANGE`, `>=0.80.0,<0.82`. Steward Story 148.2 moves `requires-pixi`, CI and the workspace to pixi 0.85.0, and `test_pixi_range_floor_matches_workspace.py` holds the range's floor to `requires-pixi`'s.

**Approach:** The range moves to `>=0.85.0,<0.86`: its floor is the new `requires-pixi` floor, and it still closes before the next untested minor. The range test checks 0.85.0 in, and 0.84.2 and 0.86.0 out.

Ledger key: `34-1-the-fix-pr-solver-admits-pixi-0-85`.

### Living CAP citations

- spec-pyforge-warden CAP-12 (the fix-PR actuator; realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- The floor equals `requires-pixi`'s, and the range closes before the next minor.

**Never:**
- Never open the range's ceiling.

## Acceptance Criteria

**Given** `requires-pixi = ">=0.85.0"`
**When** warden's range tests run
**Then** 0.85.0 is in range, 0.84.2 and 0.86.0 are not, and the floor matches the workspace

- **AC1 — The range tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-warden python -m pytest src/shared/packages/pyforge-warden/tests/meta -q -k "range"
  ```

</intent-contract>

## Result (2026-11-27)

- `PIXI_VERSION_RANGE` is `>=0.85.0,<0.86`, with a comment naming this story and steward Story 148.2.
- `test_pixi_range_admits_the_tested_pixi_and_no_untested_minor` checks 0.85.0 in range, and 0.84.2 and 0.86.0 out.
- AC1 is read from warden's suites in the full preflight.
