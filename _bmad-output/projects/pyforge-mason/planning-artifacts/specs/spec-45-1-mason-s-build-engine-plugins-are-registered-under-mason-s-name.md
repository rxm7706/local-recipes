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
