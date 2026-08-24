---
title: One story in flight per station; stations in parallel; overlap is loud
type: feature
created: '2026-08-23'
status: in-progress
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 3aa7e3925046c71f755c2b63716495ffbf6e7850
---

<intent-contract>

## Intent

**Problem:** Dispatch has no in-flight guard — a second dispatch on a station with live progress can duplicate work; cross-station parallel is fine but overlapping frozen surfaces are silent (FR-193 CAP-5).

**Approach:** Refuse second dispatch onto a station whose in-flight story (judged by 22.2 git/process facts) has not completed, naming that story. Allow concurrent dispatches on different stations. Detect overlap between in-flight stories' declared frozen surfaces and emit loud advisory (operator may proceed). Deps: 22.1, 22.2 done. Do not implement attach/resume (22.6).

## Acceptance Criteria

- Second dispatch on same station with live in-flight story is refused with evidence naming the story.
- Dispatches on different stations proceed concurrently (FR-184 in-loop clamp untouched).
- Overlapping frozen surfaces between concurrent in-flight stories produce loud advisory.
- Does not implement CAP-6 (Story 22.6 attach/resume).

## Boundaries & Constraints

**Never:** Block cross-station parallel dispatch. Never modify bmad-loop in-loop station clamp. Finalize marshal ledger only.

</intent-contract>

## Code Map

- Parent: `spec-marshal-single-story-dispatch/SPEC.md` (CAP-5)
- `cli/dispatch.py` — in-flight refusal + overlap advisory
- `core/dispatch.py` / `core/status.py` — frozen-surface overlap detection
- Tests: refuse same-station redispatch; allow cross-station; overlap advisory fixture

## Verification

- `pixi run -e pyforge-marshal pyforge-marshal-test` green
