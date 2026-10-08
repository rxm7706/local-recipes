---
title: '60.2: Publish uses tools we wield; steward records the review'
type: 'feature'
created: '2026-09-16'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/catalog.py
warnings: []
deferred: []
declared_low_risk: false
baseline_revision: 'ce29e073d3375a852b194f034613d4f249a67d10'
---

<intent-contract>

## Intent

**Problem:** A module can appear without a recorded review.

**Approach:** A listing cannot appear without steward review, unless it is already in the wielded suite (Certified). Tiers are Unverified / Community Reviewed / BMad Certified.

## Boundaries & Constraints

**Always:**
- No listing without steward review unless already Certified in the wielded suite.
- Tiers are Unverified / Community Reviewed / BMad Certified.

**Never:**
- Do not invent a fourth tier.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| unreviewed module | publish without steward review | refused unless already Certified | refuse |

</intent-contract>

## Binding

Parent Spec capability: `spec-self-hosted-bmad-marketplace CAP-2` / `spec-pyforge-steward CAP-118`.
Surface: Builder / module-template / SKF publish path; the estate catalog registry YAML.
Ledger key: `60-2-publish-uses-tools-we-wield-steward-records-the-review`.

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/catalog.py` — extend `CatalogEngine` with `_review_findings()`, `publish()`; review records under `registry/reviews/<name>.yaml`; `check` emits `listing-no-review`; `CatalogDuty` verb `publish`.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — `_add_catalog_subparsers`: `publish --listing PATH --review PATH [--dry-run]`.
- `src/shared/packages/pyforge-steward/catalog/registry/reviews/` — steward review records (git-tracked; `.gitkeep` seeds the dir).
- `src/shared/packages/pyforge-steward/catalog/registry/estate.yaml` — only rows appended via `publish` (or hand-edited, then caught by `check`).
- `src/shared/packages/pyforge-steward/tests/unit/test_catalog.py` — I/O matrix + publish/check tests.

## Tasks & Acceptance

**Execution:**
- `catalog.py` — `publish` refuses missing review, wielded duplicate, and `bmad-certified` via review; writes `registry/estate.yaml`.
- `cli.py` — wire `catalog publish`.
- `tests/unit/test_catalog.py` — matrix row + publish happy path + `listing-no-review` on hand edit.

**Acceptance Criteria:**
- Given a listing draft and no review file, when `steward catalog publish` runs, then it refuses with `publish-refused`.
- Given a wielded-suite module name, when `publish` runs, then it refuses with `publish-certified-wielded`.
- Given a review record and listing draft for a new module, when `publish` then `render` then `check` run, then exit 0.
- Given a hand-edited `estate.yaml` row without `registry/reviews/<name>.yaml`, when `steward catalog check` runs, then `listing-no-review` fires.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass.

## Auto Run Result

Status: in-review (review pass pending)

**Summary.** Story 60.2 adds `steward catalog publish --listing … --review …` so community modules enter `registry/estate.yaml` only alongside a steward review record in `registry/reviews/<name>.yaml`. Wielded-suite modules stay BMad Certified via `wielded-suite` only. `catalog check` reports `listing-no-review` for unreviewed estate rows.

**Verification.** `pixi run --frozen -e pyforge-steward pyforge-steward-test` — 2049 passed, 5 skipped. `python scripts/spec_surface_reconcile.py` — OK (memlog reconcile on `spec-pyforge-steward` and co-governor `spec-pyforge-core`; no `--write-baseline`).
