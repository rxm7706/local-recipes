---
title: "Story 49.8: CAP-17 in effect — marshal publishes run state to the supervisor"
type: story
created: 2026-09-12
baseline_revision: 40ec440c1f51c6fb319e6ab2dc2ed2271bb8accc
status: backlog
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-run-state-one-publisher/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-33-4-cap-18-one-publisher-run-state-and-savings-telemetry-reach-the-supervisor.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-33-12-cap-1-2-4-5-in-effect-held-runs-publisher-identity-and-the-loop-home-reads-retire.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py
warnings: []
deferred: []
declared_low_risk: true
---

# Story 49.8: CAP-17 in effect — marshal publishes run state to the supervisor

<intent-contract>

## Intent

**Problem:** `spec-pyforge-unifying-strategy`'s CAP-17 (run state as a service) is the last of nine 2026-09-09 realization-gap rows still open. Its criterion — the front door shows a live bmad-loop run in a deployed namespace with no operator-home access, and a completed run's timing survives the workstation — is met by marshal's own act, not by a second implementation on steward's side. This story is the joint-landing acceptance half: it is ledger-`blocked` on that act by design and never dispatches alone.

**Correction (2026-09-12, before dispatch):** marshal's act landed in TWO stories, not one — Story 33.4 (merged 2026-09-12, PR #1269) shipped only the mechanical publisher (CAP-18/CAP-7: zero `django_pyforge` imports, best-effort publish/heartbeat/complete) and explicitly deferred the held-run lifecycle, identity, and every loop-home-read retirement. Story 33.12 (merged 2026-09-12, PR #1270) is the story that actually did the retirement this story's own doctor-comment reword describes — it re-pointed doctor's `sources/marshal.py` and marshal's `cli/init.py`/`cli/spin.py` at the published plane and added the CAP-4 guard. Every reference to "marshal 33.4" below in the context of the doctor-comment retirement means **33.12**, not 33.4; both are merged as of this dispatch, so this story is no longer blocked on anything and can proceed standalone.

**Approach:** This story does **no** independent engineering. It (1) confirms the incoming `django-pyforge/**` and realm surface claim that Story 33.12 already recorded on `spec-pyforge-unifying-strategy`'s memlog before its surface edits landed, (2) carries the one deliberately-deferred doctor comment reword that could not land ahead of time without going stale, and (3) verifies CAP-17's criterion against the artifacts 33.4 and 33.12 actually produced. Doctor minted no separate story for its half — that comment plus the memlog line on `spec-pyforge-doctor` is doctor's whole action here, and it rides this story's diff.

## Boundaries & Constraints

**Always:**
- Verify CAP-17's criterion against marshal 33.4 + 33.12's actual landed artifacts (both merged 2026-09-12), not against this story's own diff.
- Confirm marshal 33.12's incoming `django-pyforge/**`/realm surface claim landed in steward's own memlog (recorded on `spec-pyforge-unifying-strategy`'s memlog ahead of 33.12's landing, per the cross-station rule) before treating this story as mergeable — or `spec-surface-check` reds the merge.

**Never:**
- Do not build a second publisher, a second `run_state` write path, or any steward-side duplicate of marshal 33.4/33.12's work.
- Do not touch `django-pyforge/**` beyond confirming the incoming claim marshal 33.12 already recorded — this story's own surface is the one comment line plus its memlog note.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| MARSHAL_33_4_AND_33_12_LANDED | Both stories merged: 33.4's publisher (zero `django_pyforge` imports) and 33.12's held-run lifecycle + published-plane re-point | Doctor comment reworded; CAP-17 criterion verified live | N/A (true as of this dispatch) |
| SURFACE_CLAIM_MISSING | Marshal 33.12's `django-pyforge/**` incoming claim is not yet recorded in steward's memlog | `spec-surface-check` would red the merge | Already recorded on `spec-pyforge-unifying-strategy`'s memlog before 33.12 landed — not expected to trigger |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py:223` — reword the existing `# gather_story_status reads host state (~/.bmad-loops) -- preserve, don't redesign` comment to note the read now checks the published plane FIRST (marshal Story 33.12 re-pointed `sources/marshal.py`'s `_harness_tasks`/`gather_story_status`) and falls back to `~/.bmad-loops` only when the plane is unreachable — the retirement Unifying CAP-17 named has landed, not merely scheduled
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md` — the memlog line recording this comment change (doctor's whole action here, ridden by this story per the standing correction already on record there)
- `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md` — no edit expected; Story 49.8's own text already names the corrected mechanism (verified 2026-09-12, no wording change needed)

## Tasks & Acceptance

**Execution:**
1. Confirm marshal Stories 33.4 AND 33.12 have both landed on `main` (33.4's meta-test asserting zero `django_pyforge` imports in `pyforge-marshal/src/` passes live; 33.12's `tests/meta/test_no_loop_home_run_state_read.py` guard passes live and doctor's `sources/marshal.py::_harness_tasks` reads the published plane first).
2. Reword the `sources/__init__.py:223` comment per the Code Map above.
3. Append the corresponding memlog line to `spec-pyforge-doctor/.memlog.md`.
4. Verify CAP-17's criterion live: a bmad-loop run appears at `/runs/` sourced from the published plane, and a completed run's timing is queryable after the run ends.

**Acceptance Criteria:**
- Given marshal 33.4 and 33.12 have both landed, when `sources/__init__.py:223` is read, then its comment names the CAP-17 retirement as landed, no longer only "preserve, don't redesign".
- Given the front door's `/runs/` view, when a bmad-loop run is live, then it appears there sourced from the published plane, not from a filesystem scrape.
- Given a bmad-loop run completes, when the workstation that launched it is gone, then its timing is still queryable from the published plane.
- Given `spec-surface-check`, when run after this story lands, then it is clean — marshal 33.12's incoming `django-pyforge/**` claim is already recorded on `spec-pyforge-unifying-strategy`'s memlog.

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

### 2026-09-12 — Pre-dispatch correction
This story was authored assuming marshal Story 33.4 alone would land the loop-home-read
retirement its doctor-comment reword describes. In fact 33.4 (merged, PR #1269) landed only the
mechanical publisher (CAP-18/CAP-7); the actual retirement — doctor's `sources/marshal.py` and
marshal's `cli/init.py`/`cli/spin.py` re-pointed at the published plane, plus the CAP-4 guard —
landed in the newly-minted follow-up Story 33.12 (merged, PR #1270). Corrected every "marshal
33.4" reference in this story's Intent/Boundaries/I-O-Matrix/Tasks that was actually about the
retirement to name 33.12 instead (33.4-specific references — the zero-`django_pyforge`-imports
criterion — are untouched, since those genuinely are 33.4's). `baseline_revision` bumped to
`40ec440c1f51c6fb319e6ab2dc2ed2271bb8accc` (both prerequisite stories merged). Both stories are
now landed, so this story is no longer blocked and dispatches standalone.

## Review Triage Log

## Design Notes

Steward's Story 49.9 ("Index — marshal realization-gate effect stories") is a separate index row that flips once marshal's Epic 33 lands its effect stories broadly — do not conflate it with this story, which is specifically CAP-17's own joint-landing half.

## Auto Run Result
