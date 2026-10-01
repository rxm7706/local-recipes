---
title: "81.2: The drain plan reads a prose park only where one is written, never in a story's own rules"
type: 'fix'
created: '2026-10-01'
status: 'in-progress'
baseline_revision: '70c074d58076180ce75919a4ee3bcde1a7244f00'
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

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_prelaunch.py` -- `find_prose_park` (the one change site) scans `epics_block` then `spec_text` through `_park_line`; `_PARKED_RE` / `_DO_NOT_DISPATCH_RE` are read-only (Never: no regex change). Core is pure (AD-4): no I/O.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/drain_plan.py` -- callers at `evaluate_story` (~l.354) and `_scan_prose_park` (~l.722) pass the raw spec text in; read-only, no change needed.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_prelaunch.py` -- `find_prose_park` tests (~l.63-136); add the contract-skip tests beside them.
- `src/shared/packages/pyforge-marshal/tests/unit/test_drain_plan.py` -- `test_a_prose_park_in_the_tracked_spec_is_found` (~l.1215) is the plan-level twin; add the no-finding twin for a contract-only line.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-73-2-a-drain-schedules-the-follow-up-review-a-landed-story-recommended.md` -- read-only evidence: its only park-matching line (l.65) sits inside its `<intent-contract>` (l.16-91); never edit it.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_prelaunch.py` -- strip each `<intent-contract>` ... `</intent-contract>` block from `spec_text` (not `epics_block`) before `_park_line`; update the docstring -- the contract holds a feature's own rules, not a hold decision
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_prelaunch.py` -- tests for the contract ACs: a contract-only line is `None` (mutation: this test fails with the skip removed); a line outside the contract still reports `source == "tracked spec"`; a contract line in an `epics_block` still reports; an unclosed tag scans the whole spec
- `src/shared/packages/pyforge-marshal/tests/unit/test_drain_plan.py` -- a plan over a spec whose only "do not dispatch" line is in its contract raises no MRS-DRAINPLAN-002
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` -- append the surface-reconcile entry naming the changed governed paths (via `_bmad/scripts/memlog.py`, never hand-edit `SPEC.md`), and on each co-governor `spec-surface` names

## Spec Change Log

## Design Notes

Strip the block, never scan it line by line: a regex `<intent-contract>.*?</intent-contract>` (non-greedy, `re.DOTALL`) replaced with a newline keeps the surrounding lines apart. An unclosed tag matches nothing, so the whole spec is scanned -- a malformed spec reports a park rather than silencing one (AD-8, unevaluable is never clean).

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
