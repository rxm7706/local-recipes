---
title: The public Pages root is one dossier, not two copies
type: dream
owner: herald
status: archived
archived-reason: absorbed
---
> **Consolidated into [[pyforge-herald]]** on 2026-09-17 (one-chain-per-station herald fold; folded from `pyforge-pages`).
# The public Pages root is one dossier, not two copies

## The Dream

The factory already has a public GitHub Pages tree (`docs/dashboard/`) and a
Kedro-Viz export that lives under it. What it does **not** have is a single
checked-in source for the **PyForge dossier** — the narrative, figures, and
standalone infographics that explain the estate. Those have lived in a published
artifact. Updating the dossier and updating the site were two acts of copying,
and they drifted.

The Dream is **one YAML, many renders**. `docsite/content/dossier.yml` is the
source of truth. The Pages landing page, the dossier HTML, the infographic
gallery, and the Claude Artifact build are all renders of that file. Kedro-Viz
stays at `/kedro-viz/` and is linked from the new landing page. There is still
exactly one Pages deployment.

> A number that is true in the repo and false on the public page is not a
> published number.

## Why now

A complete site already exists as a git bundle (`pyforge-pages.bundle`, tip
`5b6a540477`, based on `50504e52e` when `main` was that commit). Landing it
without a Dream and Spec would skip the contract this repo requires, and would
leave foundry with no five-field to rebuild from — the exact failure
`foundry-regenerate-not-fold` exists to prevent.

Today on `main` (measured 2026-09-13, `origin/main` `08613ac92f`):

| Finding | Where it is visible |
|---|---|
| Pages publishes `docs/dashboard/` as the site root | `.github/workflows/dashboard.yml` uploads that path |
| The live content of that tree is Atlas Kedro-Viz | workflow comment; `kedro-viz-publish.yml` stages `docs/dashboard/kedro-viz/` |
| There is no `docsite/`, no `feature.site`, no `site-check` | `pixi.toml` / repo root |
| The Guildhall generator is retired; Lane 1 `/console/` is the operator console | `dashboard.yml` header; steward 30.2 |
| The dossier is not a tracked source | nothing named `dossier.yml` on `main` |

## What it looks like when real

- **Edit the YAML, rebuild, publish.** A sentence change is a line in
  `docsite/content/dossier.yml`. `pixi run -e site site-check` proves the
  render. Push to `main` rebuilds Pages.
- **The landing page is the site.** `https://rxm7706.github.io/local-recipes/`
  is the dossier landing page. Kedro-Viz remains at `/kedro-viz/` and is linked
  from it.
- **One Pages deploy.** `dashboard.yml` builds the site *into* `docs/dashboard/`
  and is still the only workflow that calls `deploy-pages`. A second deploy
  would race and wipe Kedro-Viz.
- **Figures have a check.** `site-verify` compares marked dossier stats to the
  source tree. CI annotates drift and never blocks a deploy — editorial
  judgment stays human.
- **The artifact is a render too.** `dist/artifact/dossier.html` is the Claude
  Artifact host shape (no wrapping `<html>`), from the same templates.
- **Foundry can rebuild it.** After Story 54.5, B authors the equivalent
  Dream/Frame/Spec and the `docsite/` + `feature.site` + Pages-build step from
  this contract. A is the pin. No `_bmad-output` rsync, no comment-copy.

## Constraints / Non-goals

- **One Pages deployment.** Never a second `deploy-pages` job.
- **`build.py` owns only its outputs.** Never a blanket `rmtree` of
  `docs/dashboard/` — Kedro-Viz is Atlas-owned and stays.
- **New pixi feature only.** `environment.yaml` (`-e build` export) stays
  byte-identical; the `site` feature is not on that export.
- **`maintenance` label** on the landing PR (nothing under `recipes/`).
- **Verify is advisory** in CI. Local `site-verify` may exit 1; the Action
  `continue-on-error`.
- **Not Lane 1.** `/console/` stays the operator console.
- **Not a fold.** This is not Story 44.4 / `src/shared/packages/` path-rename.
- **Infographic sources are not rewritten.** The build injects a back-link bar
  only.

## Kinships

[[pyforge-herald]] (proclamation — the public dossier is Herald's voice) ·
[[factory-console]] (the Pages tree this landing page now occupies; generator
retired, Kedro-Viz kept) · [[pyforge-steward]] (Pages deploy duct;
`dashboard.yml`) · [[pyforge-atlas]] (Kedro-Viz at `/kedro-viz/`) ·
[[deck-family-currency]] (infographics the gallery publishes; facts stay on
their own ledger) · [[foundry-regenerate-not-fold]] (B rebuilds this surface
from the Spec after 54.5; A pins) · [[pyforge-unifying-strategy]] (its
`spec-python-foundry-cutover`: cargo on the kernel move list, not a 44.4 fold;
since 2026-09-25 `fnd:CAP-14` makes this dossier the cutover's control plane —
herald Story 26.1).

## Realization log

- **2026-09-13** — Seeded from the operator-supplied git bundle and the
  accompanying Pages/CI gates. Next act: `bmad-spec` under `pyforge-herald`,
  then Story 22.1, then rebase the bundle onto `origin/main` in a steward
  worktree.
