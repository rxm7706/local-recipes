---
name: "2026-11-27-landed-herald-s-test-builds-keep-the-docs-pages-t"
description: "2026-11-27 LANDED: herald's test builds keep the docs pages they already rendered. PR #2426 merged as a3aacf4c72 (Merge…"
metadata:
  type: project
---

2026-11-27 LANDED: herald's test builds keep the docs pages they already rendered. PR #2426 merged as a3aacf4c72 (Merge pyforge-herald/61-1 into main; herald Story 61.1, Epic 61, spec-pyforge-steward:CAP-175 realized with no text change), with 25 checks passed. With PAGES_REUSE_RENDERED_DOCS on, docs-site/src/loaders/shelf-docs-loader.ts keeps a page whose source, path and rendering pipeline match the stored digest, and astro.config.mjs gives each set of redirects its own content store. Herald's test builds set it (pages_astro.astro_build and the agent-surface module); the Pages build does not. In every build the loader drops a page that is gone. A second build in one copy keeps 94 of 94 pages, takes 3.6 s against 7.0 s, and writes the same site. In an A/B run of herald's live half on four workers, with another session's run on the machine, wall time fell from 111 to 88 s and from 96 to 79 s, and CPU time from 587 to 453 s and from 489 to 414 s. The full preflight passed all 31 lanes in 280.9 s. Measured and left: four test builds repeat another's inputs; sharing an output would join tests that each read their own build. Still open from the 2026-11-27 lever survey: Platform CI's fixed cost per shard, every job's checkout plus setup-pixi (30 to 40 s), and no lane lints _bmad/scripts/.
