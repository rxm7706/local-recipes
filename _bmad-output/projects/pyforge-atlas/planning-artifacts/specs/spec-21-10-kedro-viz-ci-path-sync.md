---
title: 'Kedro-Viz CI path sync for catalog and datasets (Story 21.10, Epic 21, optional follow-on)'
type: 'feature'
created: '2026-08-30'
status: 'ready-for-dev'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/operator-surfaces.md'
---

<intent-contract>

## Intent

**Problem:** `.github/workflows/kedro-viz-publish.yml` triggers only on pushes to `main`
touching `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/**`. A catalog-only
change — a new `catalog.yml` entry, a `globals.yml` endpoint edit, or a new dataset class
under `datasets/**` — can merge without republishing the static kedro-viz DAG export, so
`docs/dashboard/kedro-viz/` silently drifts behind the real DAG.

**Approach:** Extend the workflow's `on.push.paths` trigger list with the 3 additional glob
patterns `operator-surfaces.md` § Story 21.10 specifies. A pure CI-config change — no
application code, no build-step logic touched.

## Boundaries & Constraints

**Always:**
- Edit ONLY the `on.push.paths` list in `.github/workflows/kedro-viz-publish.yml` (currently
  a single entry, L29–34: `on:` / `push:` / `branches: [main]` / `paths:` /
  `pipelines/**` / `workflow_dispatch:`); add entries under `paths:`, do not replace the
  existing one.
- Add exactly these 3 path patterns (verbatim, per `operator-surfaces.md` § Story 21.10):
  - `src/shared/packages/pyforge-atlas/conf/base/catalog.yml`
  - `src/shared/packages/pyforge-atlas/conf/base/globals.yml`
  - `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/**`
- This is a `recipes/`-external change (`.github/**`) — per CLAUDE.md's PR-CI-gates rule, the
  PR must carry the `maintenance` label
  (`gh pr edit <n> --repo rxm7706/local-recipes --add-label maintenance`) at PR open/update
  time. `pixi.toml` is not touched by this story, so the `environment.yaml` sync rule does not
  apply.

**Block If:** Implementing this reveals the publish step itself (`viz-publish-stage` /
`kedro viz build`) cannot resolve a dataset class newly reachable via the widened
`datasets/**` trigger, for a reason unrelated to path-trigger scope (e.g. a genuinely broken
DAG node) — pause and confirm with the human whether the fix belongs in this story or a
separate follow-up, per this story's own `invoke_dev_with` scope note ("workflow paths only
unless publish step needs dataset node registration fix").

**Never:**
- Do not change the workflow's build/publish steps (`viz-publish-stage`,
  `steward deploy dashboard`) unless the Block-If condition above is hit and confirmed in
  scope.
- Do not add a path trigger for `conf/local/**` — gitignored credentials, would never fire in
  CI.
- Do not touch `dashboard.yml` (the separate, already-passive Pages publish workflow this
  workflow's own header comment documents as unconditionally re-publishing once this
  workflow's commit lands on `main`).
- Do not implement the operator-surfaces.md "Optional: document `regenerate-kedro-viz-proto`"
  aside — that tool builds the unrelated TARGET-STATE prototype stub DAG
  (`src/prototype/packages/pyforge-atlas-kedro-viz`, pixi task `regenerate-kedro-viz-proto`),
  not this workflow's real-DAG publish step (`viz-publish-stage`); conflating the two would
  over-scope this story (see Design Notes).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| PR touches only `conf/base/catalog.yml` | push to `main` | `kedro-viz-publish` workflow is triggered | n/a |
| PR touches only `conf/base/globals.yml` | push to `main` | `kedro-viz-publish` workflow is triggered | n/a |
| PR touches only a new/changed file under `src/pyforge/atlas/datasets/` | push to `main` | `kedro-viz-publish` workflow is triggered | n/a |
| PR touches only `pipelines/**` (existing trigger) | push to `main` | workflow is triggered (regression check — unchanged behavior) | n/a |
| PR touches only `conf/local/credentials.yml` or unrelated atlas files (e.g. `dashboard/`) | push to `main` | workflow is NOT triggered (out of scope, unchanged) | n/a |

</intent-contract>

## Code Map

- `.github/workflows/kedro-viz-publish.yml` — `on.push.paths` (L29–34) — the sole edit site.
- `src/shared/packages/pyforge-atlas/conf/base/catalog.yml`,
  `src/shared/packages/pyforge-atlas/conf/base/globals.yml`,
  `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/` — the 3 new trigger roots
  (confirmed to exist in the repo today).
- `docs/dashboard/kedro-viz/` — the static DAG export this workflow publishes; unaffected by
  this story's edit except that it now refreshes on a wider set of merges.

## Tasks & Acceptance

**Execution:**
- [ ] `.github/workflows/kedro-viz-publish.yml` — add the 3 `paths:` entries under the
  existing `on.push.paths` list, after the current `pipelines/**` line — widens the CI
  trigger so catalog/globals/dataset-only changes republish the DAG export.
- [ ] PR housekeeping — apply the `maintenance` label per CLAUDE.md's non-recipe-PR gate
  (`.github/**` is outside `recipes/`).

**Acceptance Criteria:**
- Given `.github/workflows/kedro-viz-publish.yml` after this change, when inspected, then
  `on.push.paths` contains exactly 4 entries: the original `pipelines/**` plus the 3 new ones
  listed above, byte-for-byte matching `operator-surfaces.md` § Story 21.10.
- Given a PR touching only `conf/base/catalog.yml` merged to `main`, when GitHub evaluates the
  workflow's path filter, then `kedro-viz-publish` is scheduled to run (verified by YAML
  path-glob inspection, not a live merge within this story).
- Given the pre-existing `pipelines/**` trigger, when this change lands, then it is
  unmodified — a PR touching only pipeline files still triggers the workflow (no regression).

## Spec Change Log

<!-- Empty — no review loopback has occurred yet. -->

## Design Notes

`operator-surfaces.md` § Story 21.10 appends an "Optional: document
`regenerate-kedro-viz-proto` in bootstrap operator runbook" aside to this story. That pixi
task is a DIFFERENT tool from the one this workflow calls: `regenerate-kedro-viz-proto`
(re)generates the dependency-free TARGET-STATE prototype stub mirror under
`src/prototype/packages/pyforge-atlas-kedro-viz` (77 stub nodes / 81 datasets, Graphviz SVG
output), used for pre-implementation DAG planning — it has no relationship to
`viz-publish-stage` (this workflow's actual build step, which runs `kedro viz build` against
the REAL shipped DAG and stages the normalized output to `docs/dashboard/kedro-viz/`). No
"bootstrap operator runbook" doc exists yet in this repo (the closest candidate is
`src/shared/packages/pyforge-atlas/README.md`). Per this story's own tightly-scoped
`invoke_dev_with` note ("Workflow paths only … Do not over-scope"), that documentation aside
is explicitly excluded from this story rather than adopted — a future story can add it if an
operator confusion actually surfaces.

## Verification

**Commands:**
- `git diff .github/workflows/kedro-viz-publish.yml` — expected: only the `paths:` list
  changed, 3 lines added, nothing else.
- `gh pr edit <n> --repo rxm7706/local-recipes --add-label maintenance` — expected: label
  applied (required since this PR touches `.github/**`, not `recipes/**`).

**Manual checks (if no CLI):**
- Re-read the edited `paths:` block and confirm it still parses as a valid YAML list under
  `on.push` (no indentation drift) and that the `workflow_dispatch:` trigger directly below it
  is untouched.
