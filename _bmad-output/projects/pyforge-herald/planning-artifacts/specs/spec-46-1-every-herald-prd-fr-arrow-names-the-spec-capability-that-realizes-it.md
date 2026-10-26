---
title: "46.1: Every herald PRD FR arrow names the Spec capability that realizes it"
type: 'chore'
created: '2026-10-25'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/prds/prd-pyforge-herald-2026-08-01/prd.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/one_chain.py
---

<intent-contract>

## Intent

**Problem:** eleven of the herald PRD's `FR-n ← CAP-m` arrows name the wrong capability. Line numbers are at
`fd06415e4d`.

- **Where the arrows came from.** The 2026-09-17 fold commit `4251c42229` ("Land herald fold") gave every FR in a
  feature group the arrow of one capability. That holds for Feature Groups 3, 4 and 5 (one Moment each) and is wrong for
  three others: Feature Group 1, the Moments CLI (`herald progress`, `herald success`, `herald notice`), reads CAP-1,
  whose "CLI foundation" is the deck CLI (`seed`, `pull`, `status`, `watch`); Feature Group 2, the web surface that
  lays out the three Moment tabs, reads only CAP-3 (the visual identity); and Feature Group 6, evidence linking, reads
  CAP-11, whose success has no evidence clause.
- **Why nothing noticed.** Doctor's `fr-without-cap` (`pyforge/doctor/sources/one_chain.py`) checks only that a cited
  CAP exists, and its `FR-\d+` grammar reads `FR-1.1` as `FR-1`, so 36 of herald's 48 dotted FRs are never read.
- **What found it.** The fleet audit of 2026-10-25, after marshal Story 105.1 (#2314). The PRD's 2026-10-10 section had
  already corrected FR-7.1..FR-7.4 for the same cause.

**Approach:**
- **The table is the contract.** `spec-pyforge-herald`'s memlog carries the approved table (the 2026-10-25 decision
  entry "the approved table for Story 46.1", amended after the round-1 review): eleven lines, each `FR-n ← <new> (was CAP-k)`. Evidence: the pre-fold
  Spec (`4251c42229^`) constraint "All three Moments must integrate with Herald CLI and Herald web surface" and its
  signal "Herald CLI supports `herald progress`, `herald success`, `herald notice`; Herald web surface unifies all three
  Moments in nav + layout" (both under HER-11..HER-13); each HER-11..HER-13 "What it does" names its CLI verb and web
  surface; CAP-12's and CAP-13's successes require evidence and proof links; Story 6.4 (the evidence protocol) sits in
  the CLI foundation epic and Story 11.3 (cross-moment evidence linking) in the integration epic.
- **The rewrite.** Each of the eleven lines' arrow is replaced, nothing else on the line.
- **The record.** A PRD `## Currency reconciliation — 2026-10-25 (Story 46.1)` section lists the change by group; the
  PRD, spine and epics `updated:` stamps move with notes (no FR, AD or story text changes).
- **`type: chore`, no flag.** A traceability correction to a planning artifact; under `spec-feature-flag-governance`
  Q1 a chore carries no flag. Planning files only, so it is built in its own chain PR, not dispatched.

Ledger key: `46-1-every-herald-prd-fr-arrow-names-the-spec-capability-that-realizes-it`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- **`spec-one-chain-per-station` CAP-5** (FRs derive from CAPs): every FR names the capability it derives from; this
  story makes herald's names true.
- **`spec-one-chain-per-station` CAP-3** (the station fold procedure): the fold this story corrects.
- No `spec-pyforge-herald` CAP is minted, and no `SPEC.md` text changes.
- **Origin.** `docs/dreams/pyforge-herald.md` Realization log, the 2026-10-25 (the PRD's FR arrows were mapped by
  section, not traced) entry; the operator's rulings of 2026-10-25.

## Acceptance Criteria

- **AC1 — The eleven arrows.** Every line in the memlog table carries exactly its new arrow, and no other FR line's
  arrow changed (a diff of the PRD's `**FR-` lines against `fd06415e4d` shows exactly 11 changed lines).
- **AC2 — Every cited capability exists.** Each `CAP-n` in a changed arrow is declared in `spec-pyforge-herald/SPEC.md`.
- **AC3 — Gates.** `fr-without-cap`, `chain-currency`, `chain-completeness` and `detectors-ci` stay green.

## Boundaries & Constraints

**Always:**
- Change only the arrow text of the eleven lines, and re-stamp what chain currency requires in the same commit.

**Never:**
- Never change an FR's number, title or body, `SPEC.md`, or a detector.

## I/O & Edge-Case Matrix

| Line | Before | After |
|---|---|---|
| FR-1.1, FR-1.2, FR-1.3 | CAP-1 | CAP-11, CAP-12, CAP-13 |
| FR-2.1 | CAP-3 | CAP-3, CAP-11, CAP-12, CAP-13 |
| FR-2.2 | CAP-3 | unchanged |
| FR-2.3 | CAP-3 | CAP-11, CAP-12, CAP-13 |
| FR-6.1, FR-6.3 | CAP-11 | CAP-12, CAP-13 |
| FR-6.2 | CAP-11 | CAP-12, CAP-13, CAP-39 (review) |
| FR-3.2 | CAP-11 | CAP-11, CAP-38, CAP-39 (review) |
| FR-4.2 | CAP-12 | CAP-12, CAP-38 (review) |
| FR-4.5 | CAP-12 | CAP-12, CAP-39 (review) |
| the other FR-3.x and FR-4.x, FR-5.x, FR-7.x, FR-8.1..FR-12.5 | traced or hand-written | unchanged |

</intent-contract>

## Binding

- Parent capabilities: `spec-one-chain-per-station` CAP-5 and CAP-3. No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-herald.md` § *Realization log*, the 2026-10-25 (the PRD's FR arrows were mapped by
  section, not traced) entry.
- Epic: Epic 46 (new), minted with this story. `epic-46` and `epic-46-retrospective` are minted with it.
- Ledger key: `46-1-every-herald-prd-fr-arrow-names-the-spec-capability-that-realizes-it`.
- Deps: —.
- Minted 2026-10-25 in one chain commit; built in the same PR (the five-station FR-arrow PR, with mason 32.1, warden
  19.1, steward 110.1, marshal 106.1 and 106.2, and atlas 40.1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`).

**Run before the push (not dispatch gates):**
- `git diff fd06415e4d -- _bmad-output/projects/pyforge-herald/planning-artifacts/prds/prd-pyforge-herald-2026-08-01/prd.md | grep -c '^+\*\*FR-'` — expected: `11` (AC1).
- `pixi run -e pyforge-guild python -m pyforge.doctor.sources fr-without-cap` — expected: OK (AC3).
- `pixi run -e pyforge-guild python scripts/chain_currency_sweep_check.py --json --project pyforge-herald` — expected: no errors (AC3).
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0 (AC3).

## Auto Run Result

Status: in-review (hand-built in the chain PR)
Implementation: the eleven PRD FR arrows rewritten from the memlog table as amended (`**FR-` lines changed: 11); PRD and spine
§ Currency reconciliation — 2026-10-25 (Story 46.1) added; PRD, spine and epics re-stamped.

## Spec Change Log

- 2026-10-25: minted from the Dream entry of 2026-10-25 (the PRD's FR arrows were mapped by section, not traced) at the
  operator's rulings "Do rows 1-5 in one PR" and "CAP-11..13 (Recommended)". `type: chore`, no flag, no CAP.
- 2026-10-25: implemented in the chain PR (eight arrows, PRD and spine sections, re-stamps); moved to `in-review`.
- 2026-10-25: round-1 review amendments applied on the operator's ruling "Apply all (Recommended)": FR-6.2 gains CAP-39 and
  FR-3.2, FR-4.2 and FR-4.5 gain CAP-38 or CAP-39; eleven lines.

## Review Triage Log

- **Round 1, 2026-10-25 (an independent reviewer over `fd06415e4d..efc10887a7`, reading the diff against the
  Specs and the pre-fold text): PASS, 0 blockers, 5 should-fix, 9 nits across the seven stories.**
  Herald: FR-1.x, FR-2.1, FR-2.3, FR-6.1 and FR-6.3 confirmed. Should-fix: FR-6.2 also needs CAP-39 (its async
  weekly re-validation is the live backend's LB-3), and three untouched rows bind the live backend too: FR-3.2
  (CAP-38, CAP-39), FR-4.2 (CAP-38), FR-4.5 (CAP-39). Nits: the Dream said herald's dotted ids are never read (36 of
  48 are not); the ruling entry could read as moving FR-2.2. All applied on the operator's ruling "Apply all
  (Recommended)", with a memlog amendment and clarification; eleven lines change.
