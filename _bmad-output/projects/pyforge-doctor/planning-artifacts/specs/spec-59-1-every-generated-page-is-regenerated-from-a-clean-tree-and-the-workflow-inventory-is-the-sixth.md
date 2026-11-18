---
title: '59.1: Every generated page is regenerated from a clean tree, and the workflow inventory is the sixth'
type: 'chore'
created: '2026-11-17'
status: 'ready-for-dev'
story: 59-1-every-generated-page-is-regenerated-from-a-clean-tree-and-the-workflow-inventory-is-the-sixth
spec: spec-pyforge-doctor
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a check that judges; a gated gate is a silent green (spec-feature-flag-governance Q1; roster list)
surface:
  - 'scripts/docs_github_workflows.py'
  - 'tests/scripts/test_docs_github_workflows.py'
  - 'pixi.toml'
  - 'docs/reference/github-workflows.md'
  - 'docs/how-to/github-actions-recipe-ci.md'
  - 'docs/how-to/pixi-tasks.md'
  - 'docs/reference/detectors.md'
  - 'docs/reference/environments.md'
  - 'docs/reference/skills-catalog.md'
  - 'docs/reference/station-cheat-sheet.md'
  - 'docs/reference/bmad-estate-llms-full.md'
  - 'docs/map.yaml'
  - 'docs/MAP.md'
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/prds/prd-pyforge-doctor-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md
  - docs/dreams/pyforge-doctor.md
  - docs/MAP.md
  - docs/_STYLE_GUIDE.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The generated pages were last stamped on dirty trees, and the workflow inventory is hand-written: it names 9 of 18 workflow files and dates itself 2026-08-15.

**Approach:** Add the sixth generator in the siblings' pattern (PyYAML reads `on` as `True`; handle it). Move the prose a table cannot carry, where still true, into the recipe-CI how-to. Regenerate all six and the estate catalog once the branch's sources stop moving (Story 59.8 re-runs them last).

Ledger key: `59-1-every-generated-page-is-regenerated-from-a-clean-tree-and-the-workflow-inventory-is-the-sixth`.
Type / Effort / Deps: chore / M / —.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-84** — documentation currency; amended 2026-11-17: every authored page is stamped or declares its detector, the currency classes fail, the workflow inventory is generated, package-level pages fold into the quadrants.

## Boundaries & Constraints

**Always:**
- Check every command, path, flag, count and link in a page against the tree before its stamp moves; keep `sources:` narrow (the file a page restates, not a hub file).
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never hand-edit a generated page, the generated section of `docs/MAP.md`, a compiled station skill, a `SPEC.md` or `sprint-status-ledger.yaml`.
- Never run a bare `spec_surface_check.py --write-baseline`; Story 59.8 stamps each governing Spec scoped, once, last.
- Never move a station's code, CLI or capability to make a page true: fix the page.

## Acceptance Criteria

**Given** four of the five generated pages carry a stamp taken on a `-dirty` tree, and the hand-written `docs/reference/github-workflows.md` says "refreshed 2026-08-15" and names 9 of the 18 workflow files
**When** `scripts/docs_github_workflows.py` joins the five generators in their pattern (`_docs_gen_common.py`, a `docs-github-workflows` task, a file in `docs-gen-test`), the page's still-true prose moves to `docs/how-to/github-actions-recipe-ci.md`, and all six generators and `scribe catalog bmad-estate --write` run after the last commit that touches their sources
**Then** every workflow file under `.github/workflows/` has a row; each generator is idempotent on the unchanged tree; no generated page's `tree` stamp ends in `-dirty`; `docs/map.yaml` registers the page as `kind: generated`
**And** `docs-gen-test`, `docs-currency-check` and `bmad-estate-check` exit 0

- **AC1 — The generator's tests pass in the generators' lane.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild docs-gen-test
  ```

- **AC2 — The inventory names every workflow file.** Expected: prints 0.

  ```bash
  for w in .github/workflows/*.yml; do grep -q "$(basename $w)" docs/reference/github-workflows.md || echo "$w"; done | wc -l
  ```

- **AC3 — The generator is idempotent and no generated stamp is dirty.** Expected: the first command exits 0; the second prints 0.

  ```bash
  pixi run --frozen -e pyforge-guild docs-github-workflows -- --check; grep -c -- '-dirty' docs/map.yaml
  ```

- **AC4 — The flag gate passes this story's spec.** Expected: exit 0; the printed JSON object has "verdict": "pass".

  ```bash
  pixi run --frozen -e pyforge-guild flag-gate-check -- --spec "$(ls _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-59-1-*.md)"
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-84 (amended 2026-11-17); FR-17 ← CAP-84.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-17 (the full documentation refresh) entry; operator ruling of 2026-11-17.
- Epic: Epic 59, minted with this story.
- Ledger key: `59-1-every-generated-page-is-regenerated-from-a-clean-tree-and-the-workflow-inventory-is-the-sixth` (`backlog`).
- Deps: —.
- Surface: `marshal-policy.toml` `[epic_surfaces]."59"`.
- Minted 2026-11-17 in the chain commit of the integration branch `docs-full-refresh-2026-11-17`, the first commit of the branch.

## Notes

- One integration branch and one PR carry Stories 59.1 to 59.8 (operator ruling 2026-11-17). Stories 59.1 to 59.6 run in parallel on disjoint files; 59.7 lands on a tree its source already reads green; 59.8 runs last.
- Measured at main `33c96fd0bb`: 57 authored pages, 19 stamped, 17 of those stale, 38 unstamped; 6 generated; 7 pointers.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code (never through a pipe).

**Run before the push:**
- `pixi run --frozen -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check` — expected: exit 0 each.

## Spec Change Log

- 2026-11-17: minted from the station Dream's 2026-11-17 entry (the full documentation refresh) and the operator's ruling of 2026-11-17.
