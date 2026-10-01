---
title: "81.2: The drain plan reads a prose park only where one is written, never in a story's own rules"
type: 'fix'
created: '2026-10-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-73-2-a-drain-schedules-the-follow-up-review-a-landed-story-recommended.md
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** `core/dispatch_prelaunch.py::find_prose_park` reports a story as parked in prose when its `epics.md` block or
its tracked spec has a line matching "parked" or "do not dispatch". It scans the whole spec, including the
`<intent-contract>` block, where a feature's own rules live. On 2026-10-01 `drain --plan` reported 73.2 as parked
(MRS-DRAINPLAN-002) on its Never bullet "Do not dispatch a follow-up whose row is closed or absent…", which describes
what 73.2 builds, not a decision to hold 73.2.

**Approach:** in the tracked spec, `find_prose_park` skips the `<intent-contract>` … `</intent-contract>` block; every
other line of the spec, and the whole `epics.md` block, is scanned as today.

Ledger key: `81-2-the-drain-plan-reads-a-prose-park-only-where-one-is-written-never-in-a-story-s-own-rules`.
Type / Effort / Deps: fix / XS / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-274 (Story 65.1, `drain --plan`). A defect of shipped behaviour, so no new CAP;
  `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a spec whose only "do not dispatch" line is inside its `<intent-contract>` block When `find_prose_park` scans it Then it returns `None`
- Given a spec with a "parked" or "do not dispatch" line outside the intent contract When it is scanned Then the park is reported as today
- Given a story's `epics.md` block with such a line When it is scanned Then the park is reported as today
- Given 73.2's tracked spec When `drain --plan` runs Then no MRS-DRAINPLAN-002 names 73.2
- Given the intent-contract skip removed When the new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Keep `find_prose_park` pure. `skip_policies` stays the one park mechanism.

**Never:** Do not change the park regexes. Do not edit 73.2's spec to dodge the check.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal` CAP-274 (Story 65.1); defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-01 (evening) entry.
Ledger key: `81-2-the-drain-plan-reads-a-prose-park-only-where-one-is-written-never-in-a-story-s-own-rules`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-01 by operator ruling: fix the defect now.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
