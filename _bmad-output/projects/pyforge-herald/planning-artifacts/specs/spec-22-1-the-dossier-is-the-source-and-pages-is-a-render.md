---
title: The dossier is the source and Pages is a render
type: feature
created: '2026-09-13'
status: ready-for-dev
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-pages/SPEC.md'
  - '{project-root}/docs/dreams/pyforge-pages.md'
declared_low_risk: false
---
<intent-contract>

## Intent

**Problem:** The public Pages tree publishes `docs/dashboard/` (Kedro-Viz at `kedro-viz/`). The PyForge dossier lives only as a published artifact, so the site and the dossier drift. Landing the incoming bundle without a Story would skip the contract and leave foundry with nothing to rebuild.

**Approach:** Realize `spec-pyforge-pages` CAP-1..5 in one PR: rebase `pyforge-pages.bundle` onto `origin/main`, keep `feature.site` off the `-e build` export, build the site in `dashboard.yml` into `docs/dashboard/`, never add a second `deploy-pages`.

## Boundaries & Constraints

**Always:**
- One Pages deployment. `dashboard.yml` is the only `deploy-pages` caller.
- `build.py` deletes only the outputs it owns.
- `pixi project export conda-environment -e build > environment.yaml` is byte-identical.
- `maintenance` label.
- After 54.5, foundry re-derives this surface; same CAP-N; no `_bmad-output` rsync.

**Never:**
- Second Pages workflow.
- `verify_claims.py` in `detectors-ci`.
- Blanket `rmtree` of `docs/dashboard/`.
- Lane 1 `/console/` replacement.
- Story 44.4 fold.

## Tasks & Acceptance

**Execution:**
- Rebase bundle commits onto this worktree.
- Confirm `environment.yaml` unchanged.
- `pixi run -e site site-check`.
- Open PR with `maintenance`.

**Acceptance Criteria:**
- `site-check` green.
- `environment.yaml` `git diff` empty after `-e build` export.
- `dashboard.yml` still the sole `deploy-pages` caller; Kedro-Viz path unchanged.
- Dream `specified`, Spec `ready`, ledger key `22-1-the-dossier-is-the-source-and-pages-is-a-render` present.

</intent-contract>
