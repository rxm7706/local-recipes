# docs/dashboard — GitHub Pages publish root

The Guildhall static console (`generate.py`, `data.js`) was **deleted** in
steward Story 30.2 (PRD FR-7). Operator surfaces live on Lane 1 at
**`/console/`**.

This directory is **not** the GitHub Pages upload root anymore (Story 27.2).
The Pages build copies what it holds, minus this README, into
`docs-site/build/site/dashboard/` beside the Starlight shelf (`/`) and the
herald dossier mount (`/herald/`). The PyForge site is built by
`docsite/build.py` into that `herald/` prefix; legacy HTML URLs at the old root
paths are redirect stubs in the unified artifact.

The Kedro-Viz board is staged locally under `kedro-viz/` (gitignored). CI
builds it with `pixi run -e pyforge-atlas viz-publish-stage`, then uploads the
tree as the GitHub Actions workflow artifact **`kedro-viz-export`** (see
`.github/workflows/kedro-viz-publish.yml`). When the
`pyforge.atlas.viz_export_artifact` flag is on, the staged tree includes
**`manifest.json`** beside `index.html` (`export_commit`, `export_date`,
`kedro_viz_version`). Steward's Pages workflow is to download the newest
successful artifact here (steward Story 102.4, not landed as of 2026-10-15:
until it does, the Pages build in CI takes the absent path below). The Pages
build mounts whatever is here at
`/dashboard/kedro-viz/` (herald Story 42.2): with an export present it also
writes the `/kedro-viz/` redirect and herald's pipelines page at `/dashboard/`,
whose commit and date come from `manifest.json` — so a present export without a
well-formed `manifest.json` fails `pages-check`, naming the file. With none, the
build carries on: no mount, no redirect, and no Kedro-Viz entry in the menus or
the overview tiles.

Deploy is `.github/workflows/pages.yml`, which uploads `docs-site/build/site`.

The Vizro boards (atlas Story 30.2) are staged locally under `vizro/`
(gitignored) by `pixi run -e local-recipes vizro-static-export` when the
`pyforge.atlas.vizro_static_boards` flag is on: one static page per board at
`vizro/<page-id>/index.html`, the board index at `vizro/index.html`, one
vendored `vizro/assets/plotly.min.js` (copied from the env's plotly, never a
CDN) and `vizro/manifest.json` (`exported_at`, `export_commit`, and `boards[]`
with each board's `id`, `title`, `path` and `data_build_timestamp`). CI's
`vizro` job on `.github/workflows/kedro-viz-publish.yml` uploads that tree as
the workflow artifact **`vizro-static-export`** (90 days). Pages mounts it at
`/dashboard/vizro/` once the consumer lands (steward 102.4's download step and
herald Story 43.3's mount; neither is on `main` as of 2026-10-15). The live
Vizro server stays on Lane 1; the static boards carry no filters and no scan
controls.
