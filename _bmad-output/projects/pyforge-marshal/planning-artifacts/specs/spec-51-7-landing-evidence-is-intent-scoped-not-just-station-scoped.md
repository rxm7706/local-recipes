---
title: '51.7: Landing evidence is intent-scoped, not just station-scoped'
type: 'fix'
created: '2026-09-19'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** on 2026-09-18 doctor Story 27.4 was minted on `doctor/27-4-mint`; when PR #1477 merged, `story_merged_on_main` read true for 27.4 and its first dispatch completed in one second and detached from a live session (story re-keyed to 27.5, 27.4 a reserved hole)

**Approach:** a station-prefixed branch counts as a landing only under the landing grammar, and the retrospective scan corroborates the un-scoped shape with the branch it actually came from

## Boundaries & Constraints

**Always:**
- `merged_story_keys` for `pyforge-doctor` against `origin/main` no longer contains 27.4, while every `done` row of the eight tracked ledgers with real landing evidence still classifies (the CAP-247 regression fixture extended)
- live history is never re-attributed; the MRS-GATE scope advisory for `pyforge-core/**` is expected and recorded, not suppressed

**Never:**
- Do not make the supervisor trust a session's self-report, perform the merge marshal only materialises, add a second gate or verdict owner, move a primary checkout that is not a clean `main`, or re-attribute landed history — the Epic 51/52 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the named fixture | the real run/journal/PR named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-255`.
Surface: `src/shared/packages/pyforge-core/src/pyforge/core/landing_evidence.py` (`parse_station_branch_name` requires the landing grammar — `dispatch/<slug>/<key>` or the key as the whole last segment; `parse_github_pr_merge_subject` stops accepting a key-prefixed token; `_branch_belongs_to_project` gains its production caller), `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py::_classify_merge_subject` / `merged_story_keys` (passes real branch data, not `branch=None`), tests in both packages; doctor's `sources/marshal.py` consumers verified green (`pyforge-doctor-test`, `pyforge-core-test` — outside marshal's `verify_commands`, so run by hand before land).
Ledger key: `51-7-landing-evidence-is-intent-scoped-not-just-station-scoped`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` (51.x) or a hand-driven `bmad-build-auto` (52.x) can resolve `spec-51-7-landing-evidence-is-intent-scoped-not-just-station-scoped.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The Then/And of Story 51.7 in `epics.md` hold on the named fixture; the mutation or byte-identical check named there is run, not inferred.
