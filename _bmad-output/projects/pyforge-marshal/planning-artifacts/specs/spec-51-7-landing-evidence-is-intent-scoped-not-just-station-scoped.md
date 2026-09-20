---
title: '51.7: Landing evidence is intent-scoped, not just station-scoped'
type: 'fix'
created: '2026-09-19'
status: 'in-review'
baseline_revision: 'f819e046250a3bf9d8f41a803408e2e245d424ec'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** on 2026-09-18 doctor Story 27.4 was minted on `doctor/27-4-mint`; when PR #1477 merged, `story_merged_on_main` read true for 27.4 and its first dispatch completed in one second and detached from a live session (story re-keyed to 27.5, 27.4 a reserved hole)

**Approach:** corroborate by content, not name — for the dispatch consumers (`dispatch_supervisor` `story_merged_on_main`, `dispatch_land`'s already-landed check, `dispatch_land_finalize`'s promotion) a station-branch match reached through a GitHub PR-merge subject counts as a landing only when the key's tracked story spec on `origin/main` reads `status: done` (a mint/fallout/fix PR merges it `ready`/`backlog`; a landing merges the promoted twin); the retrospective scanners are unchanged. Amended 2026-09-19 (night) after run `pyforge-marshal-20260919T202703469Z-0b70f736` returned blocked: name-based corroboration is unreachable through `promotion._classify_merge_subject` (a branch is only present when the GitHub PR-merge grammar already matched), and an exact-match branch grammar drops the only landing evidence for 83 of 347 marshal `done` rows (baseline worktree sweep). Saved attempt: `implementation-artifacts/story-51-7-attempted-change-2026-09-19.patch` — do not reuse its grammar tightening.

## Boundaries & Constraints

**Always:**
- on the PR #1477 fixture (`Merge pull request #1477 from rxm7706/doctor/27-4-mint`, spec-27-4 at `status: ready`) 27.4 is absent from `promotion.corroborated_merged_story_keys` and present in `merged_story_keys`; every `done` row of the eight tracked ledgers with real landing evidence still classifies through `merged_story_keys` (the CAP-247 regression fixture extended; the 347-key marshal sweep yields 0 regressions)
- a landing whose tracked spec is not `status: done` on `origin/main` (a hollow landing) is not corroborated — the same posture as CAP-252 / Story 51.9
- `landing_evidence.py` stays a pure parser (no filesystem, no git): `LandingEvidenceMatch` gains the branch-derived shape; the `spec_status_for(key)` reader is injected by marshal (`promotion.corroborated_merged_story_keys(subjects, template, slug, *, spec_status_for)`), never read inside core
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
Surface: `src/shared/packages/pyforge-core/src/pyforge/core/landing_evidence.py` (`LandingEvidenceMatch` exposes the branch-derived shape a GitHub PR-merge subject matched through — `dispatch/<slug>/<key>` vs a bare station branch; parsers otherwise unchanged, no grammar tightening), `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py` (new `corroborated_merged_story_keys(subjects, template, slug, *, spec_status_for)` beside the unchanged `merged_story_keys`; a `spec_status_for` reader over `origin/main:<planning-artifacts>/specs/spec-<key>-*.md` frontmatter, banner-tolerant per CAP-256), the three dispatch consumers `dispatch_supervisor/__main__.py` (`story_merged_on_main`), `dispatch_land.py` (already-landed check), `dispatch_land_finalize/__main__.py`; tests in both packages incl. the PR #1477 fixture; `cli/status.py`, `cli/deploy.py`, `cli/land.py` and doctor's `sources/marshal.py` untouched, verified green (`pyforge-doctor-test`, `pyforge-core-test` — outside marshal's `verify_commands`, so run by hand before land).
Ledger key: `51-7-landing-evidence-is-intent-scoped-not-just-station-scoped`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` (51.x) or a hand-driven `bmad-build-auto` (52.x) can resolve `spec-51-7-landing-evidence-is-intent-scoped-not-just-station-scoped.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The Then/And of Story 51.7 in `epics.md` hold on the named fixture; the mutation or byte-identical check named there is run, not inferred.
