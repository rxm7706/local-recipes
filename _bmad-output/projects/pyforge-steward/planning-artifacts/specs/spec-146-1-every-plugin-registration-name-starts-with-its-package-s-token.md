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

## Review (2026-11-26)

An independent `bmad-review` pass read the diff against the stated intent only. It confirmed the core claim: `PluginRegistry.load_entry_points` uses an entry-point name only in error labels, mason selects by `engine_name` and marshal and steward by `plugin_id`, and none of the nine old names is read by code, a script, a workflow, a task, a skill or the lock. Findings and what was done:

1. **Mason CAP-37 named the old entry points** (intent and success). Fixed: a memlog decision and an anchored render amend CAP-37 to name `mason-engine-*`; FR-59 and the spine are re-stamped; Epic 45 no longer says no Spec text moves.
2. **The three station tests that read `pyproject.toml` pinned the old names** (`test_build_hooks.py`, `test_loop_runner_hook.py`, `test_deploy_profile_plugins.py`), and marshal's edited line failed `ruff format --check`. Fixed: the pins read the new names, the line is wrapped, and each test is in its story's surface.
3. **The station Specs had no reconcile entry for the moved paths.** Fixed: each governing Spec's memlog names its paths, with scoped stamps; the cascade also named paths that the 2026-11-25 exit-declaration change and the 2026-11-26 JSON change had left unnamed on doctor, marshal, warden, core and unifying-strategy.
4. **Only `pyforge-*` packages are scanned.** Kept, and the test's docstring states the scope: no `django-*` portal or `src/platform` registers on the group today.
5. **The token came from the directory name.** Fixed: it comes from `[project].name`.
6. **A synthetic case still used `dummy`.** Fixed: `core-dummy`.
