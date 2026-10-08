# docs/dashboard — GitHub Pages publish root

The Guildhall static console (`generate.py`, `data.js`) was **deleted** in
steward Story 30.2 (PRD FR-7). Operator surfaces live on Lane 1 at
**`/console/`**.

This directory is **not** the GitHub Pages upload root anymore (Story 27.2).
CI copies its tracked contents into `docs-site/build/site/dashboard/` beside
the Starlight shelf (`/`) and the herald dossier mount (`/herald/`). The
PyForge site is built by `docsite/build.py` into that `herald/` prefix; legacy
HTML URLs at the old root paths are redirect stubs in the unified artifact.

Today the only board tracked here is atlas Kedro-Viz, under `kedro-viz/`; that
name stays as-is. Rebuild with `pixi run -e pyforge-atlas viz-publish-stage`,
then `steward deploy dashboard` (see `.github/workflows/kedro-viz-publish.yml`).
Deploy is `.github/workflows/dashboard.yml`, which uploads `docs-site/build/site`.

Vizro is a separate dashboard product from Kedro-Viz. If a Vizro board is
ever published here too, it gets its own subfolder (e.g. `vizro/`) at that
time — this directory does not mint an empty `vizro/` tree ahead of an
actual publish.
