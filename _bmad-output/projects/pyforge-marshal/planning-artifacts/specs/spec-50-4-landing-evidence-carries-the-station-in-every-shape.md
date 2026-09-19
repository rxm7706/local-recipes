---
title: '50.4: Landing evidence carries the station in every shape'
type: 'fix'
created: '2026-09-18'
status: 'done'
updated: '2026-09-18'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** on 2026-09-18 atlas's seven `Merge 23-N into main` commits marked herald's 23.1/23.2/23.5/23.6 `story_merged_on_main` (doctor's 23.1–23.3 dispatches completed in one second that morning and detached from live sessions), and steward's `Story 48.2:` / `Story 48.4:` subjects poison marshal 48.2/48.4 today — Story 35.1's `known_keys` corroboration cannot help when the key exists in both ledgers

**Approach:** the templated shape renders and parses with the station slug and the un-scoped direct-commit shape needs a station-scoped branch (`<station>/…`, `dispatch/<slug>/…`, `land/<station>-…`) or the recovery allowlist to corroborate it

## Boundaries & Constraints

**Always:**
- `merged_story_keys` for `pyforge-marshal` against today's `origin/main` no longer contains 48.2/48.4 and for `pyforge-herald` no longer contains 23.1..23.6 via atlas, while every `done` row of all eight tracked ledgers that has real landing evidence still classifies (regression fixture: ledgers × `git log origin/main --format=%s`)
- live history is never re-attributed: the existing `Merge {key} into main` and `Story N.M:` subjects on `main` are grandfathered through the SHA/recovery allowlist and branch-scoped shapes only; the new default applies to landings after this story merges

**Never:**
- Do not make the supervisor trust a session's self-report, add a second gate, or re-attribute landed history — the Epic 50 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the 2026-09-18 fixture | the real run/journal named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-247`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` (repo default `merge_subject_template` → `"Merge {slug}/{key} into main"`, `{slug}` a second placeholder validated beside `{key}`), `.../core/identity.py` (`render_merge_subject` / `parse_merge_subject` / `_split_template` learn `{slug}`), `src/shared/packages/pyforge-core/src/pyforge/core/landing_evidence.py` (`parse_templated_merge_subject` refuses a foreign slug; `parse_story_direct_commit_subject` requires branch/station corroboration before it counts), `.../core/promotion.py` (`_classify_merge_subject`), `.../core/dispatch_landing.py::merge_subject_is_marshal_native`, the eight stations' `marshal-policy.toml` (herald's #1458 override becomes redundant and is removed), tests.
Ledger key: `50-4-landing-evidence-carries-the-station-in-every-shape`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-50-4-landing-evidence-carries-the-station-in-every-shape.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- `merged_story_keys('pyforge-marshal')` over today's `origin/main` no longer contains 48.2/48.4; herald no longer inherits atlas's `Merge 23-N into main`; every `done` row with real evidence across all eight ledgers still classifies; live history is grandfathered, never re-attributed.
