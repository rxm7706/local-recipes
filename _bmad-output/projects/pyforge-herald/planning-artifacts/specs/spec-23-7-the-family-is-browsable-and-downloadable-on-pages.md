---
title: '23.7: The family is browsable and downloadable on Pages'
type: 'feature'
created: '2026-09-16'
status: 'ready'
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
Ledger key: `23-7-the-family-is-browsable-and-downloadable-on-pages`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-7-the-family-is-browsable-and-downloadable-on-pages.md`.
