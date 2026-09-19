# docs/dashboard — GitHub Pages publish root

The Guildhall static console (`generate.py`, `data.js`) was **deleted** in
steward Story 30.2 (PRD FR-7). Operator surfaces live on Lane 1 at
**`/console/`**.

This directory is the GitHub Pages upload root — a generated publish tree,
not authored documentation (see `docs/MAP.md` § Outside this map
(untouched)). The convention is **one subfolder per published dashboard
board**. The one exception is the PyForge dossier/infographic site (built
by `docsite/build.py`, deployed by `.github/workflows/dashboard.yml`),
which publishes directly at this root — `index.html`, `dossier/`,
`infographics/`, `decks/`, `artifact/` — not into its own subfolder. Today
the only board publishing here is atlas Kedro-Viz, under `kedro-viz/`; that
name stays as-is (it is not renamed to match any other product). Rebuild with
`pixi run -e pyforge-atlas viz-publish-stage`, then `steward deploy
dashboard` (see `.github/workflows/kedro-viz-publish.yml`).

Vizro is a separate dashboard product from Kedro-Viz. If a Vizro board is
ever published here too, it gets its own subfolder (e.g. `vizro/`) at that
time — this directory does not mint an empty `vizro/` tree ahead of an
actual publish.
