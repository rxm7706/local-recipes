# docs/dashboard — Kedro-Viz publish tree

The Guildhall static console (`generate.py`, `data.js`) was **deleted** in
steward Story 30.2 (PRD FR-7). Operator surfaces live on Lane 1 at
**`/console/`**.

This directory remains as the GitHub Pages upload root so atlas Kedro-Viz
keeps its URL under `kedro-viz/`. Rebuild with `pixi run -e pyforge-atlas
viz-publish-stage`, then `steward deploy dashboard` (see
`.github/workflows/kedro-viz-publish.yml`).
