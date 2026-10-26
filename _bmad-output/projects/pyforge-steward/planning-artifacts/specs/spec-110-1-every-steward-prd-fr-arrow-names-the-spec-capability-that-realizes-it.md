---
title: "110.1: Every steward PRD FR arrow names the Spec capability that realizes it"
type: 'chore'
created: '2026-10-25'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/one_chain.py
---

<intent-contract>

## Intent

**Problem:** the steward PRD's FR-1..FR-31 carry no `← CAP-m` arrow. Line numbers are at `fd06415e4d`.

- **Why they have none.** `spec-one-chain-per-station` CAP-5 makes a PRD re-derive a step of every fold PR. The
  2026-09-17 steward fold commit `97e0816ad2` ("Land steward fold") skipped it, so the requirements written before the
  fold never named the capability they derive from. FR-32..FR-41, written later by Spec renders, carry correct arrows.
- **Why nothing noticed.** Doctor's `fr-without-cap` (`pyforge/doctor/sources/one_chain.py`) reads only FRs absent from
  `docs/governance/fr-baseline.json`, and all 31 are in it.
- **What found it.** The fleet audit of 2026-10-25, after marshal Story 105.1 (#2314).

**Approach:**
- **The table is the contract.** `spec-pyforge-steward`'s memlog carries the approved table (the 2026-10-25 decision
  entry "the approved table for Story 110.1"): FR-1..FR-7 ← CAP-1; FR-8..FR-11 ← CAP-2; FR-12..FR-15 ← CAP-3;
  FR-16..FR-18 ← CAP-4; FR-19..FR-21 ← CAP-18..CAP-20; FR-22..FR-26 ← CAP-127..CAP-131; FR-27..FR-31 ← CAP-57..CAP-61,
  one capability per FR in order. Evidence: CAP-1..CAP-4's intent text names the four duties of PRD § 4.1..§ 4.4
  (their titles are fold placeholders); the other three blocks match their capabilities title for title, through each
  capability's `← spec-<old> CAP-k` provenance.
- **The addition.** Each heading gains ` ← CAP-n` at its end, in FR-32's shape; nothing else on the line changes.

- **The record.** A PRD `## Currency reconciliation — 2026-10-25 (Story 110.1)` section lists the change; the PRD,
  spine and epics `updated:` stamps move with notes.
- **`type: chore`, no flag.** A traceability correction to a planning artifact; under `spec-feature-flag-governance`
  Q1 a chore carries no flag. Planning files only, so it is built in its own chain PR, not dispatched.

Ledger key: `110-1-every-steward-prd-fr-arrow-names-the-spec-capability-that-realizes-it`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- **`spec-one-chain-per-station` CAP-5** (FRs derive from CAPs): every FR names the capability it derives from; this
  story makes steward's names true.
- **`spec-one-chain-per-station` CAP-3** (the station fold procedure): the fold this story corrects.
- No `spec-pyforge-steward` CAP is minted, and no `SPEC.md` text changes.
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, the 2026-10-25 (FR-1..FR-31 never got their arrows) entry; the operator's ruling of 2026-10-25 "Do rows 1-5 in one PR".

## Acceptance Criteria

- **AC1 — The 31 arrows.** FR-1..FR-31 each carry exactly their arrow, and no other FR heading changed (a diff of
  the PRD's `#### FR-` lines against `fd06415e4d` shows exactly 31 changed lines).
- **AC2 — Every cited capability exists.** Each `CAP-n` in a changed arrow without a `spec-` prefix is declared in
  `spec-pyforge-steward/SPEC.md`.
- **AC3 — Gates.** `fr-without-cap`, `chain-currency`, `chain-completeness` and `detectors-ci` stay green.

## Boundaries & Constraints

**Always:**
- Change only the arrow text of the lines in the table, and re-stamp what chain currency requires in the same commit.

**Never:**
- Never change an FR's number, title or body, `SPEC.md`, or a detector.

## I/O & Edge-Case Matrix

| Headings | Before | After |
|---|---|---|
| FR-1..FR-7 (§ 4.1 Keys) | no arrow | CAP-1 |
| FR-8..FR-11 (§ 4.2 Deploy) | no arrow | CAP-2 |
| FR-12..FR-15 (§ 4.3 Provision) | no arrow | CAP-3 |
| FR-16..FR-18 (§ 4.4 Budget) | no arrow | CAP-4 |
| FR-19..FR-21 (module provisioning) | no arrow | CAP-18, CAP-19, CAP-20 |
| FR-22..FR-26 (the one-container Guild) | no arrow | CAP-127..CAP-131 |
| FR-27..FR-31 (two boards, one truth) | no arrow | CAP-57..CAP-61 |
| FR-32..FR-41 | hand-written by Spec renders | unchanged |

</intent-contract>

## Binding

- Parent capabilities: `spec-one-chain-per-station` CAP-5 and CAP-3. No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-25 (FR-1..FR-31 never got their arrows) entry.
- Epic: Epic 110 (new), minted with this story. `epic-110` and `epic-110-retrospective` are minted with it. Epic 109
  is claimed by the open draft PR #2274.
- Ledger key: `110-1-every-steward-prd-fr-arrow-names-the-spec-capability-that-realizes-it`.
- Deps: —.
- Minted 2026-10-25 in one chain commit; built in the same PR (the five-station FR-arrow PR: herald 46.1, mason 32.1,
  warden 19.1, steward 110.1, marshal 106.1 and 106.2, atlas 40.1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Run before the push (not dispatch gates):**
- `git diff fd06415e4d -- _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md | grep -c '^+#### FR-'` — expected: `31`` (AC1).
- `pixi run -e pyforge-guild python -m pyforge.doctor.sources fr-without-cap` — expected: OK.
- `pixi run -e pyforge-guild python scripts/chain_currency_sweep_check.py --json --project pyforge-steward` — expected: no errors.
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0.

## Auto Run Result

Status: in-review (hand-built in the chain PR)
Implementation: the PRD FR arrows rewritten from the memlog table; PRD and spine § Currency reconciliation —
2026-10-25 (Story 110.1) added; PRD, spine and epics re-stamped.

## Spec Change Log

- 2026-10-25: minted from the Dream entry of 2026-10-25 (FR-1..FR-31 never got their arrows) at the operator's ruling of 2026-10-25 "Do rows 1-5 in one PR". `type: chore`, no flag.
- 2026-10-25: implemented in the chain PR; moved to `in-review`.

## Review Triage Log

- (none yet)
