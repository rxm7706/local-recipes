---
title: '47.1: Mason''s types are checked whole'
type: 'fix'
created: '2026-11-26'
status: 'done'
story: 47-1-mason-s-types-are-checked-whole
spec: spec-pyforge-mason
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a removal, a type fix, a skill regeneration or a planning record; nothing is switched
surface:
  - 'src/shared/packages/pyforge-mason/pyproject.toml'
  - 'src/shared/packages/pyforge-mason/src/pyforge/mason/cli.py'
  - 'src/shared/packages/pyforge-mason/src/pyforge/mason/cfe.py'
  - 'src/shared/packages/pyforge-mason/src/pyforge/mason/recipe.py'
  - 'src/shared/packages/pyforge-mason/src/pyforge/mason/package.py'
  - 'src/shared/packages/pyforge-mason/tests/unit/test_cfe.py'
  - 'src/shared/packages/pyforge-mason/tests/unit/test_recipe.py'
  - 'src/shared/packages/pyforge-mason/tests/unit/test_package.py'
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Four `[[tool.mypy.overrides]]` entries (`pyforge.mason.cli`, `.cfe`, `.package`, `.recipe`) hid 28 type errors; Story 42.1 grew `cli`'s from 6 to 9, and the 2026-11-12 retro's action to fix them did not land.

**Approach:** Remove the four overrides. `cli.py`: each dispatch branch names its own result. `cfe.ensure_cfe_root` returns the proven root and every caller passes it. `recipe.build(docker=True)` refuses a missing config before spawning. `package.py`: the version-mismatch and ship guards check the paths and versions they pass; a CHANNEL target with no name fails that target with `InvalidShipTargetError`; the ship loop builds a list of results it filled. A typed cast only where the runtime type is certain (text-mode Popen's stderr buffer).

Ledger key: `47-1-mason-s-types-are-checked-whole`.

### Living CAP citations

- spec-pyforge-mason CAP-5 (no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Fix each error at its cause.

**Never:**
- Never add an override or a `# type: ignore`.

## Acceptance Criteria

**Given** four overrides hide 28 errors
**When** the overrides are removed and each error fixed
**Then** `lint-types` exits 0 with no mason override, and each newly refused path has a test
**And** every existing mason test passes

- **AC1 — Lint and types pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild lint-types
  ```

- **AC2 — Mason's suite passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-mason pyforge-mason-test
  ```

</intent-contract>

## Review (2026-11-26)

An independent `bmad-review` pass read the diff against the stated intent only (the skill files excluded, being regenerated). It found nothing blocking; it confirmed each narrowing: `ensure_cfe_root`'s new `root is None` refusal cannot fire for a value from `resolve_cfe_root`; the package.py version and path guards are unreachable (`engines/pep517.py` and `engines/pixi.py` set a version only with its path); the ship loop keeps order and the single rehearsal; `parse_ship_targets` never yields an unnamed CHANNEL target; and `recipe.build(docker=True, config=None)`'s `ValueError` matches `cfe.build_docker`'s own refusal of a missing config, now raised before the interpreter resolves. The CLI is `recipe.build`'s only caller and refuses `--docker` without `--config` first.
