---
title: '61.1: Herald''s test builds keep the docs pages they already rendered'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 61-1-herald-s-test-builds-keep-the-docs-pages-they-already-rendered
spec: spec-pyforge-herald
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'docs-site/src/loaders/shelf-docs-loader.ts'
  - 'docs-site/astro.config.mjs'
  - 'src/shared/packages/pyforge-herald/tests/meta/pages_astro.py'
  - 'src/shared/packages/pyforge-herald/tests/meta/test_agent_surface_and_changes.py'
  - 'src/shared/packages/pyforge-herald/tests/unit/test_shelf_docs_loader_reuse.py'
  - '_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/contract.md'
  - 'docs-site/README.md'
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
  - docs-site/src/rehype-shelf-links.js
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `herald-live-test` is the station-tests job that ends a PR's run: 91 to 106 s per shard on PR #2423,
with a test step of 51 to 69 s. Most of that time is about 20 Astro builds of 7 s each. Of each build's 7 s, 4.3 s is
content sync, because `docs-site/src/loaders/shelf-docs-loader.ts` renders all 94 docs pages every time. Astro's own
glob loader keeps a page whose source has not changed; this loader keeps none.

Astro also empties its content store whenever its config changes. The tests turn the Kedro-Viz mount on and off,
which changes the config's redirects, so 6 of 16 measured test builds emptied the store.

**Approach:** a variable, `PAGES_REUSE_RENDERED_DOCS`, turns page keeping on. Herald's test builds set it
(`pages_astro.astro_build` and the agent-surface module's own builds); the Pages build does not. With it on:

1. The docs loader digests each page's source and path together with the rendering pipeline. The pipeline is the
   config, the three link plugins, `shelf.mjs`, `reader-text.ts`, the loader itself, the base path and the
   repository a link to an unpublished file goes to.
2. A page whose digest matches the stored entry keeps its stored rendering.
3. `astro.config.mjs` names a content store for each set of redirects, so switching the mount no longer empties it.

The variable stays off for the Pages build because rendering also reads whether the files a page links to exist, and
which are folders (`rehype-shelf-links.js`). Nothing in the digest sees those change. Only a test process's tree
cannot change between its builds: its copy links the real repository, which no test edits.

The loader also deletes every stored page it did not see in the current walk, whether the variable is on or off. The
store outlives a build in the same tree, so before this a page deleted from the docs stayed in the store.

The contract lists the new variable.

Ledger key: `61-1-herald-s-test-builds-keep-the-docs-pages-they-already-rendered`.

### Living CAP citations

- spec-pyforge-steward:CAP-175 (realized here; no text change in this station's Spec).
- No AD moves.

## Boundaries & Constraints

**Always:**
- The Pages build renders every page.
- A build that keeps pages writes the same site as one that renders them.

**Never:**
- Never remove or weaken an assertion.
- Never skip or re-mark a test.

## Acceptance Criteria

**Given** two builds in one copy of the repository with the variable on
**When** the second build runs
**Then** it keeps all 94 docs pages and writes the same site; with the variable off, every page renders.

- **AC1 — The loader keeps, renders and drops pages as specified.** Expected: exit 0. The tests check: off, every
  load renders every page and a page that is gone leaves the store; on, a second load keeps all; a page stored with
  the variable off renders again; a change of base path, repository or server renders every page again.

  ```bash
  pixi run --frozen -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/unit/test_shelf_docs_loader_reuse.py -q
  ```

- **AC2 — The site is the same.** Two builds of the real site in one copy are byte for byte the same (`diff -rq`
  prints nothing) when the second keeps every page.

- **AC3 — The live half passes and costs less.** Herald's live half passes with every test it had. In an A/B run on
  four workers, with another session's run on the machine, it took 88 s and 79 s with the variable on, against 111 s
  and 96 s with it off.

</intent-contract>

## Result (2026-11-27)

- **AC1:** 6 passed. Each of four mutations made at least one test fail: dropping the repository link or the base
  path from the fingerprint, never dropping a gone page, and never keeping a page.
- **AC2:** with the variable on, a second build kept 94 of 94 pages, took 3.6 s against 7.0 s, and `diff -rq` printed
  nothing.
- **Probe of eight build variants in one copy** (the real site, status on, a fixture tree, a fixture tree with the
  exports mounted, the shell on, then each again): only the first build of each redirect set rendered pages, and none
  emptied the store.
- **AC3:** the live half passed with 831 tests in every A/B run.

  | Round | Off: wall | Off: CPU | On: wall | On: CPU |
  | --- | --- | --- | --- | --- |
  | 1 | 111 s | 587 s | 88 s | 453 s |
  | 2 | 96 s | 489 s | 79 s | 414 s |
