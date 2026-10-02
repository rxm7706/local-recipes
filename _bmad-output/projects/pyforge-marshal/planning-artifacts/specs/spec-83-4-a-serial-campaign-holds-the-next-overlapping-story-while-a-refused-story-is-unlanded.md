---
title: '83.4: A serial campaign holds the next overlapping story while a refused story is unlanded'
type: 'fix'
created: '2026-10-02'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Wave planning in `core/dispatch_fleet.py` refuses a story whose surfaces overlap a wave member (surface-overlap), but the members are only in-flight stories. A story whose session finished and whose landing was refused leaves the wave, so the next overlapping story dispatches from a `main` without it. On 2026-10-02 82.5 launched while 82.4's PR sat refused on a red check; both edited the supervisor and minted the same finding codes, and 82.5's landing conflicted.

**Approach:** The campaign cycle counts a station story that finished but whose landing was refused, with its PR still open, as occupying its surfaces: overlapping stories are held with a finding naming it until it lands or its PR closes.

Ledger key: `83-4-a-serial-campaign-holds-the-next-overlapping-story-while-a-refused-story-is-unlanded`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- Story 28.16 (wave planning) and Story 22.11 (the campaign supervisor). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a finished station story refused at landing with its PR open When the next cycle plans a wave Then every story whose surfaces overlap it is held with a finding naming it
- Given a story with disjoint surfaces When the cycle plans Then it dispatches
- Given the refused story lands or its PR closes When the next cycle plans Then the hold is released
- Given the hold removed When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Fix the defect where the shipped behaviour lives, and pin it with a test that fails without the fix.

**Never:** Do not hold a story with disjoint surfaces. Do not relaunch the refused story.

</intent-contract>

## Binding

Parent: Story 28.16 (wave planning) and Story 22.11 (the campaign supervisor).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 (night) entry.
Ledger key: `83-4-a-serial-campaign-holds-the-next-overlapping-story-while-a-refused-story-is-unlanded`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-02 at the operator's request to chain the defects found landing Phase 2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
