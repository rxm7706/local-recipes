---
title: '59.1: Herald''s site builds run side by side, each worker in its own copy of docs-site'
type: 'chore'
created: '2026-11-26'
status: 'ready-for-dev'
story: 59-1-herald-s-site-builds-run-side-by-side-each-worker-in-its-own-copy-of-docs-site
spec: spec-pyforge-herald
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-herald/tests/meta/pages_astro.py'
  - 'src/shared/packages/pyforge-herald/tests/conftest.py'
  - 'src/shared/packages/pyforge-herald/tests/meta/test_agent_surface_and_changes.py'
  - 'src/shared/packages/pyforge-herald/tests/meta/test_site_builders_share_a_worker.py'
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `pyforge-herald-live-test` takes 189 s alone and 465 s inside a full preflight, where it is the critical path; its CI shards take 132 to 148 s of tests. Its site builds, 162 s alone, all run in one xdist worker, because every build writes the one `docs-site/` tree (`public/`, `.astro/`, Astro's cache under `node_modules/`). The modules whose fixtures build are also built again in each worker that runs one of their tests.

**Approach:** `pages_astro` gives each worker its own copy of the repository for building: every top-level entry a link to the real one, `docs-site/`'s sources copied, and `node_modules/` a directory of links, so a build writes only its worker's copy. Every build helper runs Astro there. `tests/conftest.py` groups the tests of a module that builds by the module-scoped fixtures they use, so a module fixture is built in one worker and the modules' builds spread over the workers.

Ledger key: `59-1-herald-s-site-builds-run-side-by-side-each-worker-in-its-own-copy-of-docs-site`.

### Living CAP citations

- spec-pyforge-steward:CAP-175 (realized here; no text change in this station's Spec).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Measure before and after with the harness that measured the baseline.
- Build from a copy of `docs-site/` taken when the worker starts; the real tree is read, never written, by a test's build.

**Never:**
- Never delete, skip or re-mark a test to gain time.
- Never lower a coverage floor.
- Never change the preflight's docs-site mutex or its lane order (steward Story 105.1).

## Acceptance Criteria

**Given** herald's live half with every build in one worker
**When** each worker builds in its own copy and a builder module's tests are grouped by the module fixtures they use
**Then** the live half passes with the counts it had and takes under 90 s alone on 16 threads

- **AC1 — Herald's live half passes.** Expected: exit 0; `812 passed`.

  ```bash
  HERALD_DOCS_SITE_REQUIRED=1 pixi run --frozen -e pyforge-herald pyforge-herald-live-test
  ```

- **AC2 — The build-isolation tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/meta/test_site_builders_share_a_worker.py -q
  ```

</intent-contract>

## Evidence (2026-11-26)

Three builds in three private copies ran side by side in 7.5 s where one build in the real tree takes 6.4 s (`astro build`, 109 pages, 461 files). The three copies wrote identical sites; against the real tree's build, 95 HTML files differ only in Astro's scoped class names (`astro-g5ptsecz` against `astro-ck64acg7`), which Astro derives from file paths. Single-process module times: `test_one_generator.py` 57 s, `test_site_shell.py` 37 s, `test_agent_surface_and_changes.py` 36 s, `test_pages_artifact.py` 25 s, `test_docs_site_nav.py` 7 s.
