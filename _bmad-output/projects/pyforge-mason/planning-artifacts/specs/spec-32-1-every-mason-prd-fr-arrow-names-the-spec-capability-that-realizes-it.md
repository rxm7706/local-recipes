---
title: "32.1: Every mason PRD FR arrow names the Spec capability that realizes it"
type: 'chore'
created: '2026-10-25'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/prds/prd-pyforge-mason-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/.memlog.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/one_chain.py
---

<intent-contract>

## Intent

**Problem:** three of the mason PRD's `FR-n ← CAP-m` arrows name the wrong capability. Line numbers are at
`fd06415e4d`.

- **Where the arrows came from.** The 2026-09-17 fold commit `e062c19c9d` ("land mason fold") mapped each PRD feature
  section to one capability. § 4.7 "Seam enforcement" became `← CAP-7` (proving the seam holds) for every FR in it.
  That is right for FR-42..FR-47 and wrong for FR-48 (the configuration surface), FR-49 (logging and child-output
  handling) and FR-50 (rehearsal before an irreversible publish), which PRD revision 2's adversarial review added to
  the same section.
- **Why nothing noticed.** Doctor's `fr-without-cap` (`pyforge/doctor/sources/one_chain.py`) checks only that a cited
  CAP exists, never that the citation is the right one.
- **What found it.** The fleet audit of 2026-10-25, after marshal Story 105.1 (#2314).

**Approach:**
- **The table is the contract.** `spec-pyforge-mason`'s memlog carries the approved table (the 2026-10-25 decision
  entry "the approved table for Story 32.1"): FR-48 ← CAP-5, CAP-1; FR-49 ← CAP-5, CAP-2; FR-50 ← CAP-3 (each was
  CAP-7). Evidence: each CAP's success text in `spec-pyforge-mason/SPEC.md`, and `epics.md`'s own placement of the three
  FRs (FR-48 and FR-49 in Epic 1's S-1.10 with AD-13 and AD-25; FR-50 in Epic 3's S-3.9 with AD-26).
- **The rewrite.** Each of the three headings' arrow is replaced, nothing else on the line.

- **The record.** A PRD `## Currency reconciliation — 2026-10-25 (Story 32.1)` section lists the change; the PRD,
  spine and epics `updated:` stamps move with notes.
- **`type: chore`, no flag.** A traceability correction to a planning artifact; under `spec-feature-flag-governance`
  Q1 a chore carries no flag. Planning files only, so it is built in its own chain PR, not dispatched.

Ledger key: `32-1-every-mason-prd-fr-arrow-names-the-spec-capability-that-realizes-it`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- **`spec-one-chain-per-station` CAP-5** (FRs derive from CAPs): every FR names the capability it derives from; this
  story makes mason's names true.
- **`spec-one-chain-per-station` CAP-3** (the station fold procedure): the fold this story corrects.
- No `spec-pyforge-mason` CAP is minted, and no `SPEC.md` text changes.
- **Origin.** `docs/dreams/pyforge-mason.md` Realization log, the 2026-10-25 (the PRD's section 4.7 arrows were mapped by section, not traced) entry; the operator's ruling of 2026-10-25 "Do rows 1-5 in one PR".

## Acceptance Criteria

- **AC1 — The three arrows.** FR-48, FR-49 and FR-50 carry exactly their new arrows, and no other FR heading's
  arrow changed (a diff of the PRD's `#### FR-` lines against `fd06415e4d` shows exactly 3 changed lines).
- **AC2 — Every cited capability exists.** Each `CAP-n` in a changed arrow without a `spec-` prefix is declared in
  `spec-pyforge-mason/SPEC.md`.
- **AC3 — Gates.** `fr-without-cap`, `chain-currency`, `chain-completeness` and `detectors-ci` stay green.

## Boundaries & Constraints

**Always:**
- Change only the arrow text of the lines in the table, and re-stamp what chain currency requires in the same commit.
- Touch no CFE file, `src/shared/packages/pyforge-mason/`, `pixi.toml` or `recipes/**` file.

**Never:**
- Never change an FR's number, title or body, `SPEC.md`, or a detector.

## I/O & Edge-Case Matrix

| Heading | Before | After |
|---|---|---|
| FR-42..FR-47 | CAP-7 | unchanged |
| FR-48 | CAP-7 | CAP-5, CAP-1 |
| FR-49 | CAP-7 | CAP-5, CAP-2 |
| FR-50 | CAP-7 | CAP-3 |
| FR-1..FR-41, FR-51..FR-57 | section-mapped or hand-written, traced | unchanged |

</intent-contract>

## Binding

- Parent capabilities: `spec-one-chain-per-station` CAP-5 and CAP-3. No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-mason.md` § *Realization log*, the 2026-10-25 (the PRD's section 4.7 arrows were mapped by section, not traced) entry.
- Epic: Epic 32 (new), minted with this story. `epic-32` and `epic-32-retrospective` are minted with it.
- Ledger key: `32-1-every-mason-prd-fr-arrow-names-the-spec-capability-that-realizes-it`.
- Deps: —.
- Minted 2026-10-25 in one chain commit; built in the same PR (the five-station FR-arrow PR: herald 46.1, mason 32.1,
  warden 19.1, steward 110.1, marshal 106.1 and 106.2, atlas 40.1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`).

**Run before the push (not dispatch gates):**
- `git diff fd06415e4d -- _bmad-output/projects/pyforge-mason/planning-artifacts/prds/prd-pyforge-mason-2026-07-25/prd.md | grep -c '^+#### FR-'` — expected: `3`` (AC1).
- `pixi run -e pyforge-guild python -m pyforge.doctor.sources fr-without-cap` — expected: OK.
- `pixi run -e pyforge-guild python scripts/chain_currency_sweep_check.py --json --project pyforge-mason` — expected: no errors.
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0.

## Auto Run Result

Status: in-review (hand-built in the chain PR)
Implementation: the PRD FR arrows rewritten from the memlog table; PRD and spine § Currency reconciliation —
2026-10-25 (Story 32.1) added; PRD, spine and epics re-stamped.

## Spec Change Log

- 2026-10-25: minted from the Dream entry of 2026-10-25 (the PRD's section 4.7 arrows were mapped by section, not traced) at the operator's ruling of 2026-10-25 "Do rows 1-5 in one PR". `type: chore`, no flag.
- 2026-10-25: implemented in the chain PR; moved to `in-review`.

## Review Triage Log

- (none yet)
