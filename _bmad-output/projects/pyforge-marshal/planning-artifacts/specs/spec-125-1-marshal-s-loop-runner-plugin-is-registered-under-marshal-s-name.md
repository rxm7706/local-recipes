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

## Review (2026-11-26)

An independent `bmad-review` pass read the diff against the stated intent only. It confirmed the core claim: `PluginRegistry.load_entry_points` uses an entry-point name only in error labels, mason selects by `engine_name` and marshal and steward by `plugin_id`, and none of the nine old names is read by code, a script, a workflow, a task, a skill or the lock. Findings and what was done:

1. **Mason CAP-37 named the old entry points** (intent and success). Fixed: a memlog decision and an anchored render amend CAP-37 to name `mason-engine-*`; FR-59 and the spine are re-stamped; Epic 45 no longer says no Spec text moves.
2. **The three station tests that read `pyproject.toml` pinned the old names** (`test_build_hooks.py`, `test_loop_runner_hook.py`, `test_deploy_profile_plugins.py`), and marshal's edited line failed `ruff format --check`. Fixed: the pins read the new names, the line is wrapped, and each test is in its story's surface.
3. **The station Specs had no reconcile entry for the moved paths.** Fixed: each governing Spec's memlog names its paths, with scoped stamps; the cascade also named paths that the 2026-11-25 exit-declaration change and the 2026-11-26 JSON change had left unnamed on doctor, marshal, warden, core and unifying-strategy.
4. **Only `pyforge-*` packages are scanned.** Kept, and the test's docstring states the scope: no `django-*` portal or `src/platform` registers on the group today.
5. **The token came from the directory name.** Fixed: it comes from `[project].name`.
6. **A synthetic case still used `dummy`.** Fixed: `core-dummy`.
