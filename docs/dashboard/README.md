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
`kedro_viz_version`). Steward's Pages workflow downloads the newest successful,
unexpired artifact here before `pages-check` (steward Story 102.4,
`scripts/pages_artifact_download.py`, behind `pyforge.steward.pages_duty`) and
exports `KEDRO_VIZ_EXPORT=present|absent` with the run id and date; with no
artifact it takes the absent path below. Nothing published is tracked here, so
this directory is not in `pages.yml`'s path filter. The Pages
build mounts whatever is here at
`/dashboard/kedro-viz/` (herald Story 42.2): with an export present it also
writes the `/kedro-viz/` redirect and herald's pipelines page at `/dashboard/`,
whose commit and date come from `manifest.json` — so a present export without a
well-formed `manifest.json` fails `pages-check`, naming the file. With none, the
build carries on: no mount, no redirect, and no Kedro-Viz entry in the menus or
the overview tiles.

Deploy is `.github/workflows/pages.yml`, which uploads `docs-site/build/site`.
`pixi run -e pyforge-guild pyforge steward pages deploy` triggers one run of it on `main`,
`steward pages status` reads the live root, the last run and the `pages` registry verdict, and
`steward pages build` rehearses the build locally (steward Story 102.3). No verb commits to
`main`.

Vizro is a separate dashboard product from Kedro-Viz. If a Vizro board is
ever published here too, it gets its own subfolder (e.g. `vizro/`) at that
time — this directory does not mint an empty `vizro/` tree ahead of an
actual publish.
