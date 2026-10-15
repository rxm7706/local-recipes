# docs/dashboard — GitHub Pages publish root

The Guildhall static console (`generate.py`, `data.js`) was **deleted** in
steward Story 30.2 (PRD FR-7). Operator surfaces live on Lane 1 at
**`/console/`**.

This directory is **not** the GitHub Pages upload root anymore (Story 27.2).
CI copies its tracked contents into `docs-site/build/site/dashboard/` beside
the Starlight shelf (`/`) and the herald dossier mount (`/herald/`). The
PyForge site is built by `docsite/build.py` into that `herald/` prefix; legacy
HTML URLs at the old root paths are redirect stubs in the unified artifact.

The Kedro-Viz board is staged locally under `kedro-viz/` (gitignored). CI
builds it with `pixi run -e pyforge-atlas viz-publish-stage`, then uploads the
tree as the GitHub Actions workflow artifact **`kedro-viz-export`** (see
`.github/workflows/kedro-viz-publish.yml`). When the
`pyforge.atlas.viz_export_artifact` flag is on, the staged tree includes
**`manifest.json`** beside `index.html` (`export_commit`, `export_date`,
`kedro_viz_version`). Steward's Pages workflow downloads the newest successful
artifact into the site mount (Story 102.4).

Deploy is `.github/workflows/pages.yml`, which uploads `docs-site/build/site`.

Vizro is a separate dashboard product from Kedro-Viz. If a Vizro board is
ever published here too, it gets its own subfolder (e.g. `vizro/`) at that
time — this directory does not mint an empty `vizro/` tree ahead of an
actual publish.
