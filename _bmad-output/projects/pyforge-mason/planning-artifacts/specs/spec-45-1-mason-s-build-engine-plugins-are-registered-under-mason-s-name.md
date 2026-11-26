---
title: '45.1: Mason''s build-engine plugins are registered under mason''s name'
type: 'chore'
created: '2026-11-26'
status: 'done'
story: 45-1-mason-s-build-engine-plugins-are-registered-under-mason-s-name
spec: spec-pyforge-mason
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-mason/pyproject.toml'
  - 'src/shared/packages/pyforge-mason/tests/unit/test_build_hooks.py'
  - '_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md'
  - '_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/.memlog.md'
  - '_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/contract.md'
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Mason registers `rattler-build` and `conda-build` on the shared hook group, a name that says nothing about whose plugin it is.

**Approach:** Register `mason-engine-rattler-build` and `mason-engine-conda-build` in `pyproject.toml` and name it in `contract.md`, with the `engine_name` a caller selects by, and amend CAP-37, which names the entry points, through its memlog and a render. Mason selects its plugin by `engine_name`, which does not change.

Ledger key: `45-1-mason-s-build-engine-plugins-are-registered-under-mason-s-name`.

### Living CAP citations

- spec-pyforge-unifying-strategy:CAP-18 (success amended 2026-11-26; realized here).
- spec-pyforge-mason CAP-37 (amended 2026-11-26: names the entry points `mason-engine-*`; the engine names a caller selects by do not change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep every value an operator types: a plugin is still selected by its own attribute (`plugin_id`, `engine_name`).

**Never:**
- Never change `engine_name`.
- Never select a plugin by its entry-point name.

## Acceptance Criteria

**Given** mason registers `rattler-build` and `conda-build`
**When** it registers `mason-engine-rattler-build` and `mason-engine-conda-build`
**Then** the conformance test's name check passes for mason
**And** mason still selects its plugin by `engine_name`

- **AC1 — The conformance test passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-core pytest src/shared/packages/pyforge-core/tests/meta/test_plugin_registration_conformance.py -q -m live_tree
  ```

- **AC2 — Mason's plugin tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/unit/test_build_hooks.py -q
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
