---
title: '146.1: Every plugin registration name starts with its package''s token'
type: 'feature'
created: '2026-11-26'
status: 'done'
story: 146-1-every-plugin-registration-name-starts-with-its-package-s-token
spec: spec-pyforge-unifying-strategy
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a conformance check and registration names the registry never selects by; nothing is switched
surface:
  - 'src/shared/packages/pyforge-core/tests/meta/test_plugin_registration_conformance.py'
  - 'src/shared/packages/pyforge-core/pyproject.toml'
  - 'src/shared/packages/pyforge-steward/pyproject.toml'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_deploy_profile_plugins.py'
  - '_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/contract.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-unifying-strategy.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Nine names on the shared hook group `pyforge.core.hooks` carry no package, so a name says nothing about whose plugin it is, and nothing stops a second package registering a name already taken.

**Approach:** Amend CAP-18's success through its memlog and a render. Add two checks to `test_plugin_registration_conformance.py` that read every package's `pyproject.toml`, core's included: a name must start with the package token and a hyphen (`pyforge-testing-kit` registers `testing-kit-…`), and no name may be registered twice. Rename core's `dummy` to `core-dummy` and steward's six to `steward-deploy-<id>`. The registry never selects by these names, so no value an operator types moves.

Ledger key: `146-1-every-plugin-registration-name-starts-with-its-package-s-token`.

### Living CAP citations

- spec-pyforge-unifying-strategy:CAP-18 (success amended 2026-11-26).
- canopy:FR-43 (consequence added).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep every value an operator types: a plugin is still selected by its own attribute (`plugin_id`, `engine_name`).

**Never:**
- Never change a `plugin_id` or `engine_name`.
- Never select a plugin by its entry-point name.

## Acceptance Criteria

**Given** nine registration names carry no package
**When** the checks are added and core and steward rename theirs
**Then** a bare or repeated name fails the conformance test by package or by name, and a synthetic case proves each check fires
**And** steward's deploy profiles are still selected by `plugin_id`

- **AC1 — The conformance test passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-core pytest src/shared/packages/pyforge-core/tests/meta/test_plugin_registration_conformance.py -q -m live_tree
  ```

- **AC2 — Steward's deploy-profile plugins still load and select by id.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_deploy_profile_plugins.py -q
  ```

</intent-contract>
