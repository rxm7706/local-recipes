---
name: "before-pushing-a-non-recipe-branch-replicate-every-ci-lane-t"
description: "Before pushing a non-recipe branch, replicate every CI lane the diff will trigger, locally, and read each verdict from…"
metadata:
  type: feedback
---

Before pushing a non-recipe branch, replicate every CI lane the diff will trigger, locally, and read each verdict from its exit code — never through a pipe. pixi run -e pyforge-guild pr-preflight is the local twin of the four lanes that red a PR (detectors-ci, test-ci, pyforge-station-tests incl. pyforge-core, pyforge-station-coverage-gates); it does not cover container/guild-container, atlas's Chromium/DuckDB/WASM gate (required under CI=1 — run without CI=1 for atlas in a fresh worktree), herald's browser check, or scribe's Postgres (scribe-pg-up first). A pixi.toml change fires all eight station suites in CI, not only the station touched. GitHub Actions is the arbiter, not the debugger: one push per batch of fixes.
