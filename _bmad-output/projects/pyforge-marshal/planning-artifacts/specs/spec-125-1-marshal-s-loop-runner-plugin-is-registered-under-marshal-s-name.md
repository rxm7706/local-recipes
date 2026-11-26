---
title: '125.1: Marshal''s loop-runner plugin is registered under marshal''s name'
type: 'chore'
created: '2026-11-26'
status: 'done'
story: 125-1-marshal-s-loop-runner-plugin-is-registered-under-marshal-s-name
spec: spec-pyforge-marshal
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-marshal/pyproject.toml'
  - 'src/shared/packages/pyforge-marshal/tests/unit/test_loop_runner_hook.py'
  - '_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/contract.md'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Marshal registers `bmad-loop` on the shared hook group, a name that says nothing about whose plugin it is.

**Approach:** Register `marshal-runner-bmad-loop` in `pyproject.toml` and name it in `contract.md` (the hook spec row says the default plugin's `plugin_id` is `bmad-loop`). Marshal selects its plugin by `plugin_id`, which does not change.

Ledger key: `125-1-marshal-s-loop-runner-plugin-is-registered-under-marshal-s-name`.

### Living CAP citations

- spec-pyforge-unifying-strategy:CAP-18 (success amended 2026-11-26; realized here).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep every value an operator types: a plugin is still selected by its own attribute (`plugin_id`, `engine_name`).

**Never:**
- Never change `plugin_id`.
- Never select a plugin by its entry-point name.

## Acceptance Criteria

**Given** marshal registers `bmad-loop`
**When** it registers `marshal-runner-bmad-loop`
**Then** the conformance test's name check passes for marshal
**And** marshal still selects its plugin by `plugin_id`

- **AC1 — The conformance test passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-core pytest src/shared/packages/pyforge-core/tests/meta/test_plugin_registration_conformance.py -q -m live_tree
  ```

- **AC2 — Marshal's plugin tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_loop_runner_hook.py -q
  ```

</intent-contract>
