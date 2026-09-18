---
title: '24.2: The docsite has a PR gate'
type: 'feature'
created: '2026-09-18'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** no `pull_request`-triggered workflow and no `pr-preflight` leg references `docsite` or `site-check` (verified 2026-09-18: `dashboard.yml` runs the build on `push: branches: [main]` only, and `pyforge-herald-test` has zero coverage of `docsite/`), so 23.5's 296-line family-page change merged with every gate green

**Approach:** a PR that touches the docsite runs `build.py --check` + `site-check` before merge, locally and in CI

## Boundaries & Constraints

**Always:**
- a fixture regression (a family-page template with an unrendered Jinja tag) reds the lane and `main` is green, `pr-preflight` predicts the lane, and `dashboard.yml` is still the only `deploy-pages` caller
- the lane is path-filtered so a `recipes/`-only or station-only PR never runs it, and Kedro-Viz stays at `/kedro-viz/`

**Never:**
- Do not re-mint a verb, build or command that exists — bind to it; do not add a second Pages deployment or a second PR gate; a live proof stays opt-in and operator-run (the Epic 24 HARD boundaries in `epics.md`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the deferral's own case | the DW row's evidence reproduced as a fixture | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-herald CAP-49`.
Surface: `.github/workflows/` (one new `pull_request` lane, path-filtered to `docsite/**`, `docs/dashboard/**` render inputs and the workflow itself, running `docsite/build.py --check` and `site-check`), `pixi.toml` (`pr-preflight` gains the same leg; `site-check` task reused, not re-minted), `docs/how-to/presentation-deck.md` § verify checklist (names the lane), `planning-artifacts/deferred-work-ledger.md` (DW-FU-23-5 → done citing the lane's first green run).
Ledger key: `24-2-the-docsite-has-a-pr-gate`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-24-2-the-docsite-has-a-pr-gate.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).

**Manual checks:**
- A fixture regression (unrendered Jinja tag in a family-page template) reds the new lane; `main` is green; `pixi run -e pyforge-guild pr-preflight` runs the same leg; `dashboard.yml` is still the only `deploy-pages` caller; DW-FU-23-5 is marked done citing the lane's first green run.
