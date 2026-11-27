---
title: '149.3: Every environment that carries pixi locks the requires-pixi version'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 149-3-every-environment-that-carries-pixi-locks-the-requires-pixi-version
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'scripts/target_version_check.py'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_target_version_check_surfaces.py'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - scripts/pixi_version_registry.py
  - pixi.toml
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `pixi-version-check` holds every pin site to `requires-pixi`: the CI workflows, the Containerfiles and the feature floors. But the features that put pixi inside an environment name only a floor, `>=0.85.0`, and nothing reads what each environment locks. A later solve could give one environment a newer pixi than CI and the containers run.

**Approach:** `target-version-check` reads the pixi of every environment-platform pair in the lock and reds any that is not the `requires-pixi` version.

Ledger key: `149-3-every-environment-that-carries-pixi-locks-the-requires-pixi-version`.

### Living CAP citations

- spec-pyforge-steward CAP-153 (realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- `requires-pixi` stays the one pixi declaration, and `pixi-version-check` and `bump-pixi-version` keep its pin sites.

**Never:**
- Never cap pixi in a manifest (operator ruling of 2026-09-28).

## Acceptance Criteria

**Given** the lock
**When** `target-version-check` reads it
**Then** every environment that carries pixi locks the `requires-pixi` version

- **AC1 — One pixi in the lock.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild target-version-check
  ```

</intent-contract>

## Result (2026-11-27)

- All 44 environment-platform pairs that carry pixi lock 0.85.0, the `requires-pixi` version; `pixi-version-check` is clean at every pin site.
- A `requires-pixi` that is not `>=X.Y.Z`, and a lock on another pixi, each red the check; the cases sit with Story 149.2's in `test_target_version_check_surfaces.py`.
- AC1: exit 0.
