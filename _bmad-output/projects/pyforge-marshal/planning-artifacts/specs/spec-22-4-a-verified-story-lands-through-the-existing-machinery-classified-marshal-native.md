---
title: A verified story lands through the existing machinery, classified marshal-native
type: feature
created: '2026-08-23'
status: done
updated: '2026-08-23'
final_revision: b4c32b80df
context: []
warnings: []
baseline_revision: b2c47f209a
---

<intent-contract>

## Intent

**Problem:** Verified dispatched stories have no landing path — completion/verification (22.2–22.3) do not advance spec promotion, ledger, or marshal-native merge classification (FR-193 CAP-4).

**Approach:** After verification passes, land via existing Epic 4 machinery (`cli/land.py`/`deploy`) with FR-187 detectable merge subject, Story 4.1 spec promotion, Epic 15 ledger advance — zero new landing/promotion code paths. Classify landing as marshal-native via `marshal_native_merged_keys` (never FR-186 `not-loop-native`). Deps: 22.2, 22.3 done. Do not implement overlap guard (22.5) or attach/resume (22.6).

## Acceptance Criteria

- Verified dispatch triggers existing land/deploy semantics (no parallel landing implementation).
- Merge subject is FR-187 detectable; spec durably promoted (Story 4.1); ledger key advances (Epic 15).
- Landing classified marshal-native by `marshal_native_merged_keys`, not `not-loop-native`.
- Unverified or failed-verification dispatch never lands.
- Does not implement CAP-5..CAP-6 (Stories 22.5–22.6).

## Boundaries & Constraints

**Never:** New landing or promotion code paths. Never land on self-report without passing 22.3 verification. Finalize marshal ledger only.

</intent-contract>

## Code Map

- Parent: `spec-marshal-single-story-dispatch/SPEC.md` (CAP-4)
- Composition over `cli/land.py`, `deploy`, FR-187 merge subject, Story 4.1 promotion, Epic 15 ledger
- `dispatch_supervisor` / verification → land handoff
- Tests: verified dispatch lands + marshal-native classification; failed verification refuses land

## Verification

- `pixi run -e pyforge-marshal pyforge-marshal-test` green
- Regression: unverified dispatch does not advance ledger or promote spec

## Auto Run Result

Status: done
PR: https://github.com/rxm7706/local-recipes/pull/704
Merge: b4c32b80df3b52fecf2b46b8d3fe6368dae5aeb0
Merge policy: admin merge (`gh pr merge 704 --merge --admin --repo rxm7706/local-recipes`) — GitHub Actions billing blocks CI; local tests green before merge.
Summary: Story 22.4 (FR-193 CAP-4) wires verified dispatch landing through existing Epic 4 composition: `dispatch_land` opens/merges PR with FR-187 `render_merge_subject`, `dispatch_land_finalize` subprocess runs `deploy promote` + `_promote_sprint_ledger` (AD-9: supervisor never imports cli). Unverified verification refuses land (`MRS-DISP-014`); marshal-native classification pinned via `marshal_native_merged_keys`.
Files:
- `core/dispatch_landing.py` — pure landing eligibility + marshal-native subject check
- `dispatch_land.py` — forge PR merge edge (no cli import)
- `dispatch_land_finalize/__main__.py` — promote + ledger subprocess (cli composition)
- `dispatch_supervisor/__main__.py` — land after VERIFIED, journal `dispatch-land`
- `tests/unit/test_dispatch_landing.py` — verified land + unverified refusal regression
Verification: `pixi run -e pyforge-marshal pyforge-marshal-test` — **6184 passed**, 12 deselected.
Out of scope (Stories 22.5–22.6): overlap guard, attach/resume.
