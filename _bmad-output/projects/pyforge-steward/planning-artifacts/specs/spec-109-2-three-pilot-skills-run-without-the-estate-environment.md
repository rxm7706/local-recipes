---
title: '109.2: Three pilot skills run without the estate environment'
type: 'docs'
created: '2026-10-21'
status: 'in-review'
baseline_revision: '53aed16fe1957ab340c6146cb7bf0c3f810c1746'
flag-exempt: docs-only
review_loop_iteration: 0
followup_review_recommended: false
context:
  - .claude/skills/mason-environment/SKILL.md
  - .claude/skills/mason-package/SKILL.md
  - .claude/skills/pyforge-warden/active/pyforge-warden/SKILL.md
  - src/shared/packages/pyforge-steward/catalog/marketplace/skills/mason/environment/SKILL.md
  - src/shared/packages/pyforge-steward/catalog/marketplace/skills/mason/package/SKILL.md
  - src/shared/packages/pyforge-steward/catalog/marketplace/skills/warden/scan/SKILL.md
  - src/shared/packages/pyforge-steward/tests/unit/test_pilot_skills.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `@mason/environment`, `@mason/package`, and `@warden/scan` as they live under `.claude/skills/` assume this repository's pixi environments. A teammate cannot follow them in their own project.

**Approach:** Portable copies under `catalog/marketplace/skills/<scope>/<slug>/`, each with `SKILL.md` and `steps.md`. Commands are the ones the station engines assemble, verified 2026-10-21. Unpublished `pyforge-mason`, `pyforge-warden`, and `pyforge-core` are named, with the 404 check. The estate skill files are not edited.

## Acceptance criteria

1. Each of the three folders contains `SKILL.md` and `steps.md`.
2. Neither file contains `pixi run -e` or `pixi run --frozen -e`.
3. Environment steps include `conda-lock lock -f pyproject.toml --lockfile conda-lock.yml` and say the station check uses a temporary copy. They do not include the paper prototype's `env.lock` sample command. `steps.md` is the runbook the Pages card renders.
4. Package steps include `pyproject-build --no-isolation` and `pixi build --output-dir dist`, and tell the reader not to run `twine upload` or `pixi upload`.
5. Warden steps include `warden scan .` and say `deptry` and `osv-scanner` are not a warden verdict.
6. Each file records that the station package was unpublished on 2026-10-21.

## Boundaries

- Do not change `.claude/skills/mason-environment/`, `.claude/skills/mason-package/`, or `.claude/skills/pyforge-warden/`.
- Do not publish a package. Do not add a recipe.

</intent-contract>

## Verification

**Commands:**

- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_pilot_skills.py -q` — expected: exit 0.

**Manual checks:**

- The versions in `steps.md` match a fresh `--version` of `conda-lock`, `build`, `pixi`, `twine`, `deptry`, and `osv-scanner` on the day the story is reviewed. A mismatch is a doc edit, not a new command.
