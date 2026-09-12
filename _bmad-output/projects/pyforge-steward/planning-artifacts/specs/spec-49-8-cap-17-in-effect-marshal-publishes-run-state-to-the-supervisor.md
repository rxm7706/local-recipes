---
title: "Story 49.8: CAP-17 in effect — marshal publishes run state to the supervisor"
type: story
created: 2026-09-12
baseline_revision: b978aa9b2aaa7cd9ba71fcef046c67216e1ae6fe
status: backlog
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-run-state-one-publisher/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-33-4-cap-18-one-publisher-run-state-and-savings-telemetry-reach-the-supervisor.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py
warnings: []
deferred: []
declared_low_risk: true
---

# Story 49.8: CAP-17 in effect — marshal publishes run state to the supervisor

<intent-contract>

## Intent

**Problem:** `spec-pyforge-unifying-strategy`'s CAP-17 (run state as a service) is the last of nine 2026-09-09 realization-gap rows still open. Its criterion — the front door shows a live bmad-loop run in a deployed namespace with no operator-home access, and a completed run's timing survives the workstation — is met by marshal's own act (Story 33.4's single publisher), not by a second implementation on steward's side. This story is the joint-landing acceptance half: it is ledger-`blocked` on marshal 33.4 by design and never dispatches alone.

**Approach:** This story does **no** independent engineering. It (1) accepts the incoming `django-pyforge/**` and realm surface claim that Story 33.4 records against steward's own memlogs before it edits that surface, (2) carries the one deliberately-deferred doctor comment reword that could not land ahead of time without going stale, and (3) verifies CAP-17's criterion against the artifact 33.4 actually produces. Doctor minted no separate story for its half — that comment plus the memlog line on `spec-pyforge-doctor` is doctor's whole action here, and it rides this story's diff.

## Boundaries & Constraints

**Always:**
- Dispatch this story in the same session/window as marshal 33.4 — never before it (there is nothing to verify yet) and never left stranded after it (the joint-landing gate exists precisely so neither ships without the other).
- Verify CAP-17's criterion against marshal 33.4's actual landed artifact, not against this story's own diff.
- Confirm marshal 33.4's incoming `django-pyforge/**`/realm surface claim landed in steward's own memlog (spec-pyforge-doctor or the relevant steward spec, per the cross-station rule) before treating this story as mergeable — or `spec-surface-check` reds the merge.

**Never:**
- Do not build a second publisher, a second `run_state` write path, or any steward-side duplicate of marshal 33.4's work.
- Do not reword the doctor comment before marshal 33.4 has actually landed the retirement it describes — a comment about a retirement that has not happened goes stale before it merges (the standing correction already on record in `spec-pyforge-doctor`'s own memlog).
- Do not touch `django-pyforge/**` beyond accepting the incoming claim marshal 33.4 already records — this story's own surface is the one comment line plus its memlog note.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| MARSHAL_33_4_LANDED | Story 33.4's publisher is merged and its meta-test proves zero `django_pyforge` imports in marshal | Doctor comment reworded; CAP-17 criterion verified live | N/A |
| MARSHAL_33_4_NOT_YET_LANDED | This story is attempted before 33.4 merges | Refused — nothing to verify | Re-queue behind 33.4 |
| SURFACE_CLAIM_MISSING | Marshal 33.4's `django-pyforge/**` incoming claim is not yet recorded in steward's memlog | `spec-surface-check` would red the merge | Block merge until the claim note lands (in 33.4's own commit, per its Code Map) |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py:223` — reword the existing `# gather_story_status reads host state (~/.bmad-loops) -- preserve, don't redesign` comment to additionally note the read is scheduled for retirement under Unifying CAP-17, now that marshal 33.4 has actually landed the publisher this comment refers to
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md` — the memlog line recording this comment change (doctor's whole action here, ridden by this story per the standing correction already on record there)
- `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md` — no edit expected; Story 49.8's own text already names the corrected mechanism (verified 2026-09-12, no wording change needed)

## Tasks & Acceptance

**Execution:**
1. Confirm marshal Story 33.4 has landed on `main` (its meta-test asserting zero `django_pyforge` imports in `pyforge-marshal/src/` passes live).
2. Reword the `sources/__init__.py:223` comment per the Code Map above.
3. Append the corresponding memlog line to `spec-pyforge-doctor/.memlog.md`.
4. Verify CAP-17's criterion live: a bmad-loop run appears at `/runs/` sourced from the published plane, and a completed run's timing is queryable after the run ends.

**Acceptance Criteria:**
- Given marshal 33.4 has landed, when `sources/__init__.py:223` is read, then its comment names the CAP-17 retirement, no longer only "preserve, don't redesign".
- Given the front door's `/runs/` view, when a bmad-loop run is live, then it appears there sourced from the published plane, not from a filesystem scrape.
- Given a bmad-loop run completes, when the workstation that launched it is gone, then its timing is still queryable from the published plane.
- Given `spec-surface-check`, when run after this story lands, then it is clean — marshal 33.4's incoming `django-pyforge/**` claim is already recorded.

## Verification

**Commands:**
- `grep -n "CAP-17" src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` — expected: the reworded comment is present at line 223
- `python scripts/spec_surface_reconcile.py -core` — expected: clean
- `pixi run -e pyforge-doctor pyforge-doctor-test` — expected: full suite green (no behavior change, comment-only edit)
- Manual: start a bmad-loop story, confirm it renders at `/runs/`; let it finish, confirm the completed record and its timing are still queryable after closing the terminal that launched it

## Non-Goals

- No independent engineering — see Intent. All CAP-17 engineering is marshal 33.4's.
- Does not touch `hub:CAP-3` (the Track, on `spec-intelligence-hub`) beyond what 33.4 already feeds it.
- Does not implement token-economy CAP-7's five per-layer savings getters — that is marshal's own Story 33.1 scope, unrelated to this story's doctor-comment action.

## Spec Change Log

## Review Triage Log

## Design Notes

Steward's Story 49.9 ("Index — marshal realization-gate effect stories") is a separate index row that flips once marshal's Epic 33 lands its effect stories broadly — do not conflate it with this story, which is specifically CAP-17's own joint-landing half.

## Auto Run Result
