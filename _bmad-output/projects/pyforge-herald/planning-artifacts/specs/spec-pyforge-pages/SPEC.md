---
id: SPEC-pyforge-pages
spec: pyforge-pages
status: ready
owner-dream: docs/dreams/pyforge-pages.md
companions: []
surface:
  - docsite/**
  - pixi.toml
  - .github/workflows/dashboard.yml
  - .gitignore
  - docs/dashboard/index.html
sources:
  - ../../../../../../docs/dreams/pyforge-pages.md
open_questions: []
---

> **Canonical contract.** This SPEC is the complete contract for what to build, test and validate.
> `docs/dreams/pyforge-pages.md` is listed in `sources:` for narrative rationale.

# The public Pages root is one dossier, not two copies

## Why

A pain to solve and a vision to realize. The public GitHub Pages tree already
publishes `docs/dashboard/` (Kedro-Viz under `kedro-viz/`; Lane 1 `/console/` is
the operator console). The PyForge dossier — the estate narrative, figures, and
standalone infographics — has lived in a published artifact instead of a
tracked source, so "update the dossier" and "update the site" were two copies
and they drifted. An incoming git bundle already implements the render; this
Spec is the five-field so the landing is a Story, and so python-foundry can
rebuild the same surface after 54.5 instead of inheriting comments.

## Capabilities

- **CAP-1**
  - **intent:** The dossier YAML is the only source of truth; the Pages site,
    the infographic gallery, and the Claude Artifact build are renders of it.
  - **success:** Changing a sentence in `docsite/content/dossier.yml` and
    running `pixi run -e site site-check` rebuilds every page from that file;
    no second hand-edited HTML copy of the dossier exists in git.
- **CAP-2**
  - **intent:** The Pages root is the dossier landing page; Kedro-Viz stays at
    `/kedro-viz/` and is linked from it; the repository still has one Pages
    deployment.
  - **success:** `dashboard.yml` builds the site into `docs/dashboard/` and
    remains the only workflow that calls `deploy-pages`; Kedro-Viz is still
    served at `/kedro-viz/`.
- **CAP-3**
  - **intent:** Operators have a local pixi loop — build, check, verify
    figures, serve — without growing the `build` environment export.
  - **success:** `site`, `site-check`, `site-verify`, and `site-serve` exist
    under `[feature.site]`; `pixi project export conda-environment -e build`
    leaves `environment.yaml` byte-identical.
- **CAP-4**
  - **intent:** Marked dossier figures are compared to the source tree so
    drift is visible; editorial judgment stays human.
  - **success:** `verify_claims.py` runs in CI as an annotation with
    `continue-on-error`; local `site-verify` may exit 1 on drift.
- **CAP-5**
  - **intent:** The Claude Artifact host receives a body-only render from the
    same templates as the site.
  - **success:** `build.py --check` asserts the artifact shell has no wrapping
    `<html>` / `<body>` that the host already supplies.

## Constraints

- **One Pages deployment.** A second `deploy-pages` job would race and wipe
  Kedro-Viz.
- **`build.py` deletes only the outputs it owns.** Never a blanket `rmtree` of
  `docs/dashboard/`.
- **Infographic sources are not rewritten.** The build may inject a back-link
  bar; it does not edit the source HTML.
- **New pixi feature only.** The `-e build` export (`environment.yaml`) does
  not change.
- **`maintenance` label** on any PR that lands this (nothing under `recipes/`).
- **Not Lane 1.** `/console/` stays the operator console.
- **Not a package fold.** This is not Story 44.4 / `src/shared/packages/`
  path-rename.
- **Foundry rebuilds, it does not copy comments.** After 54.5, B re-derives
  Dream / Frame / Spec and the `docsite/` + `feature.site` + `dashboard.yml`
  build step from this contract; A pins the SHA. Same CAP-N. No `_bmad-output`
  rsync.

## Non-goals

- A second Pages workflow or a second `deploy-pages` caller.
- Making `verify_claims.py` a merge gate or a `detectors-ci` member.
- Rewriting or relocating Atlas Kedro-Viz.
- Replacing the Lane 1 operator console.
- Rsyncing this tree onto python-foundry as file cargo without a B-side Spec.

## Success signal

`pixi run -e site site-check` is green; Pages (after merge to `main`) serves
the dossier landing at the site root with Kedro-Viz still at `/kedro-viz/`;
`environment.yaml` is unchanged; foundry's 54.5 kit can name this surface as
rebuild cargo with `pgs:CAP-1..5`.

## Assumptions

- The incoming bundle's two commits are the intended implementation of
  CAP-1..5, rebased onto current `origin/main`.
- Pixi 0.80.0 `-e build` export remaining byte-identical after adding
  `feature.site` holds on the rebase; re-run the export in the worktree.

## Open Questions

<!-- none — landing PR and foundry-cargo rule are decided -->
