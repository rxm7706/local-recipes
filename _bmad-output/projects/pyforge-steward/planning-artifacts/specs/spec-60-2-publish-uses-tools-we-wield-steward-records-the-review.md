---
title: '60.2: Publish uses tools we wield; steward records the review'
type: 'feature'
created: '2026-09-16'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/catalog.py
warnings: []
deferred:
  - summary: >-
      Builder / module-template / SKF publish paths do not yet invoke `steward catalog publish`; operators can still hand-edit estate.yaml until upstream wiring lands.
    evidence: |-
      CAP-118 names Builder/module-template/SKF as the publish path; this story ships the steward gate (`catalog publish`, review records, check/render enforcement) only.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/catalog.py
    severity: low
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

## Review Triage Log

### 2026-10-08 — Review pass

- verdicts: 10 findings — high 0, medium 2, low 5, false 2, maybe-false 1
- findings:
  - `[medium]` `[patch]` publish must install review at `registry/reviews/<name>.yaml` — copies `--review` into canonical path on success.
  - `[medium]` `[patch]` unreviewed rows must not reach manifests — `render`/`drift` refuse on `_review_findings()`.
  - `[low]` `[patch]` preserve `estate.yaml` comment header on publish — `_estate_registry_header`.
  - `[low]` `[patch]` example review record — `registry/reviews/review-record.example.yaml`.
  - `[low]` `[patch]` module docstring cites CAP-118 / Story 60.2.
  - `[low]` `[reject]` duplicate-test ordering — set comparison already used; message asserts remain stable for this fixture.
  - `[low]` `[reject]` auto-seed in `_estate_engine` — intentional to keep 60.1 fixtures green; sneaky-mod test omits seed.
  - `[false]` `[reject]` publish without canonical review leaves check red — closed by canonical copy patch.
  - `[false]` `[reject]` render allows unreviewed listings — closed by render refusal patch.
  - `[maybe-false]` `[defer]` Builder/module-template/SKF must call publish — upstream wiring is a separate chain; this story ships the steward gate only.

## Spec Change Log

- 2026-10-08 (review): publish copies review records into `registry/reviews/`; render refuses review findings; estate header preserved on publish.

## Auto Run Result

Status: done

**Summary.** Story 60.2 adds `steward catalog publish --listing … --review …` so community modules enter `registry/estate.yaml` only with a steward review record (`registry/reviews/<name>.yaml`, installed from `--review` when needed). Wielded-suite modules stay BMad Certified via `wielded-suite` only. `catalog check`, `render`, and `render --check` enforce review findings (`listing-no-review`, tier mismatch, wielded-in-estate).

**Files changed.**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/catalog.py` — publish, review findings, render/drift refusal.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — `catalog publish` subparser.
- `src/shared/packages/pyforge-steward/tests/unit/test_catalog.py` — 60.2 tests.
- `src/shared/packages/pyforge-steward/catalog/registry/reviews/.gitkeep`, `review-record.example.yaml`.
- `src/shared/packages/pyforge-steward/catalog/registry/estate.yaml` — review pointer comment.
- Story spec + `spec-pyforge-steward` / `spec-pyforge-core` memlog reconciles.

**Review breakdown.** Patches: 5 (medium 2, low 3). Deferred: 1 (Builder/SKF funnel). Rejected: 2 false after patches, 2 low test-harness choices.

**Follow-up review recommendation:** `false` — medium patches verified by 2050 passing steward tests.

**Verification.** `pixi run --frozen -e pyforge-steward pyforge-steward-test` — 2050 passed, 5 skipped. `python scripts/spec_surface_reconcile.py` — OK (no `--write-baseline`).

**Governed paths reconciled (memlog).** `src/shared/packages/pyforge-steward/src/pyforge/steward/catalog.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py`, `src/shared/packages/pyforge-steward/tests/unit/test_catalog.py`, `src/shared/packages/pyforge-steward/catalog/registry/reviews/.gitkeep`, `src/shared/packages/pyforge-steward/catalog/registry/reviews/review-record.example.yaml`, `src/shared/packages/pyforge-steward/catalog/registry/estate.yaml`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-60-2-publish-uses-tools-we-wield-steward-records-the-review.md`; co-governor `spec-pyforge-core` memlog for `catalog.py` and `cli.py`.
