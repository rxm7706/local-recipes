---
title: '48.1: The recipe audits read each recipe once, and the meta suite runs under xdist'
type: 'chore'
created: '2026-11-26'
status: 'ready-for-dev'
story: 48-1-the-recipe-audits-read-each-recipe-once-and-the-meta-suite-runs-under-xdist
spec: spec-pyforge-mason
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'pixi.toml'
  - '.claude/skills/conda-forge-expert/tests/meta/test_recipe_yaml_parse_audit.py'
  - '.claude/skills/conda-forge-expert/tests/meta/test_split_distribution_run_deps.py'
  - '.claude/skills/conda-forge-expert/tests/_recipe_trees.py'
  - '.claude/skills/conda-forge-expert/CHANGELOG.md'
  - '.claude/skills/conda-forge-expert/SKILL.md'
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `test-ci-meta`, the PR lane of the CFE regression net, is one pytest process: 79 s alone for `7790 passed, 7 skipped`, 209 to 291 s inside a full preflight, 155 s as the `cfe-meta` job. Four tests each parse every one of 7,566 `recipe.yaml` files with PyYAML's pure-Python loader, about 13 s a pass (52.6 s summed); the C loader parses them all in 1.4 s.

**Approach:** Give the audits that need a recipe's parsed document one shared parse per file, made by `yaml.CSafeLoader` where libyaml is built in and `yaml.SafeLoader` otherwise, with the parse error kept beside the file that raised it. Pass `-n auto --dist loadgroup` in the task. The parse audit (`test_all_recipe_yaml_parse`) still reads every recipe with `yaml.safe_load` and fails when the shared parse disagrees with it; the duplicate-key audit's strict loader is built on the same C loader.

Ledger key: `48-1-the-recipe-audits-read-each-recipe-once-and-the-meta-suite-runs-under-xdist`.

### Living CAP citations

- spec-pyforge-steward:CAP-175 (the preflight and a PR's CI answer within a measured budget; realized here, no text change in this station's Spec).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Measure before and after with the harness that measured the baseline.
- Invoke the `conda-forge-expert` skill before the edit and close with its retro and a CHANGELOG entry.
- Keep each audit's failure message naming the files it names today.

**Never:**
- Never delete, skip or re-mark a test to gain time.
- Never drop a recipe from an audit.
- Never move the full net (`test-ci`).

## Acceptance Criteria

**Given** the lane on one process
**When** the audits share one parse per file and the lane runs under xdist
**Then** it passes with the same passed and skipped counts
**And** it takes under 30 s alone on 16 threads

- **AC1 — The lane passes with the count it had.** Expected: exit 0, `7790 passed, 7 skipped` plus the tests this story adds.

  ```bash
  pixi run --frozen -e pyforge-guild test-ci-meta
  ```

</intent-contract>

## Evidence (2026-11-26)

Standalone `test-ci-meta`: 80.3 s wall, 77 CPU-seconds. `test_no_crm_sentinel_keys_in_recipe_yaml` 13.2 s, `test_no_duplicate_mapping_keys_anywhere` 13.2 s, `test_no_noarch_python_recipe_depends_on_the_wrong_half` 13.2 s, `test_all_recipe_yaml_parse` 13.0 s. Loader bench over 7,566 recipes: `CSafeLoader` 1.42 s, `safe_load` about 15.3 s.
