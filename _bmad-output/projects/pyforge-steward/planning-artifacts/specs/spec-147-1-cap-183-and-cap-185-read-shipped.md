---
title: '147.1: CAP-183 and CAP-185 read shipped'
type: 'chore'
created: '2026-11-26'
status: 'done'
story: 147-1-cap-183-and-cap-185-read-shipped
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a removal, a type fix, a skill regeneration or a planning record; nothing is switched
surface:
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** CAP-183 and CAP-185 read `ready` though every story that builds them landed: Epic 135 through 6db8d6e60f on 2026-11-25, Story 144.1 and its five relays through 3556bd1f2e on 2026-11-26.

**Approach:** Append a memlog decision naming each landing and re-render the two markers by an anchored render.

Ledger key: `147-1-cap-183-and-cap-185-read-shipped`.

### Living CAP citations

- spec-pyforge-steward CAP-183 and CAP-185 (markers).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Cite the merge commit of each landing.

**Never:**
- Never move an intent or a success.

## Acceptance Criteria

**Given** two capabilities read `ready`
**When** their markers are re-rendered
**Then** CAP-183 reads (shipped 2026-11-25) and CAP-185 (shipped 2026-11-26)
**And** no other line of the Spec moves

- **AC1 — The chain detectors pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild detectors-ci
  ```

</intent-contract>

## Review (2026-11-26)

An independent `bmad-review` pass read the diff against the stated intent only (the skill files excluded, being regenerated). It found nothing blocking; it checked both markers against `git log origin/main`: CAP-183 against `02c15042b5` (steward 135.1 to 135.3) merged as `6db8d6e60f` on 2026-11-25, CAP-185 against Story 144.1 merged as `3556bd1f2e` on 2026-11-26.
