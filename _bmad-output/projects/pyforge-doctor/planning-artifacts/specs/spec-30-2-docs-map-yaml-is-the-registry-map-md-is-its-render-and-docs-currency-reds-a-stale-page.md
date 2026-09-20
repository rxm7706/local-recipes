---
title: '30.2: docs/map.yaml is the registry, MAP.md is its render, and `docs-currency` reds a stale page'
type: 'feature'
created: '2026-09-20'
status: 'draft'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/research/documentation-currency-and-repeatable-refresh-2026-09-19.md']
warnings: ['oversized']
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `docs/MAP.md` is hand-maintained and no page declares what it derives from or explains, so nothing can say a page is stale — the 14 pages PR #1529 added shipped with dead paths and a non-existent CLI grammar and nothing noticed.

**Approach:** a machine registry `docs/map.yaml` (quadrant, owner, `kind ∈ {generated, authored, pointer}`, `sources`, stamp) from which `docs/MAP.md` is rendered; `sources:` / `verified:` frontmatter on every authored page; a Doctor source `docs-currency` with four warn-first checks (map alignment, stale generated page, stale authored page, stray file in a managed skill dir); the unmapped-page class promoted from warn to fail.

## Boundaries & Constraints

**Always:** CAP-62's posture (warn first, fail-open on unreadable input); `MAP.md` is a render — a byte diff between it and its render is a finding; schema for `map.yaml` ships in the doctor package.
**Never:** copy a docs page into a per-tool instruction file; make `docs-currency` write anything.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| `map.yaml` page with `sources:` newer (git last-touch) than `verified:` | warn naming the page and the source |
| authored page with a backticked path / `pixi run … task` / CLI grammar that no longer resolves | warn naming the token |
| `MAP.md` hand-edited so it differs from the render | warn (fail after promotion) |
| quadrant page absent from `map.yaml` | fail (promoted from CAP-83's warn in this story) |
| a `README.md` or other non-layout file inside a managed skill dir | warn naming it |
| `map.yaml` missing or invalid | fail-open: one `could-not-evaluate` warn, never a false green |

## Binding

Parent Spec capability: `spec-pyforge-doctor CAP-84`.
Surface: `docs/map.yaml` (new), a `docs-map-render` task, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/docs_currency.py` (new) + unit tests, `scripts/detectors.py`, `pixi.toml`, the authored pages' frontmatter, `docs_map_hygiene.py` (retired into or kept beside `docs-currency` — decided and recorded in the story).
Ledger key: `30-2-docs-map-yaml-is-the-registry-map-md-is-its-render-and-docs-currency-reds-a-stale-page`.
Ledger status at mint (unchanged): `backlog`.
Minted 2026-09-19 (night) from `epics.md` so `marshal factory dispatch` can resolve this file.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks:** `pixi run -e pyforge-guild detectors-ci` green on the branch; hand-edit `docs/MAP.md` → `docs-currency` warns; revert → OK.

</intent-contract>
