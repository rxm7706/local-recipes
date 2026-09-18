---
title: '23.5: The family is browsable and downloadable on Pages'
type: 'feature'
created: '2026-09-16'
status: 'in-review'
baseline_revision: '36ccbfa9f9d2c1b06a2a5ff7a0c2561a8a10778b'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** docsite/build.py publishes standalone infographics only — no PPTX, Marp, exec summary, or per-deck page.

**Approach:** One family page per registered deck plus an index. Poster, Infographic Deck, Executive Summary in view; PPTX(s) and Marp as downloads; etag and tree stamps. dashboard.yml remains the only deploy-pages caller.

## Boundaries & Constraints

**Always:**
- Kedro-Viz stays at /kedro-viz/.
- One deploy-pages caller.

**Never:**
- Do not add a second Pages deploy.
- Do not bind a new Pages product.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| site-check | after family pages land | passes | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-design-sync-loop CAP-7; spec-pyforge-pages CAP-1/CAP-2`.
Surface: docsite/build.py; docsite/templates/**; docsite/content/**; docs/dashboard/**; site-check..
Ledger key: `23-5-the-family-is-browsable-and-downloadable-on-pages`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-5-the-family-is-browsable-and-downloadable-on-pages.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's policy `verify_commands` entry; MRS-GATE-010 binds the dispatch gate to this Success signal, and it is read from the primary tree's tracked spec, so it must be declared here before dispatch, not by the session).

**Manual checks:**
- `site-check` passes after the family pages land; each family page shows the poster, Infographic Deck and Executive Summary in view, offers the PPTX(s) and Marp sources as downloads, and stamps each with its etag and tree; `dashboard.yml` is still the only `deploy-pages` caller and Kedro-Viz is still at `/kedro-viz/`.
