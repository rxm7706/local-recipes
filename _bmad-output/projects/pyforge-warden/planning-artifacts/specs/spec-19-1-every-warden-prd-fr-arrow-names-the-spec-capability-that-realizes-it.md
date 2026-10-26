---
title: "19.1: Every warden PRD FR arrow names the Spec capability that realizes it"
type: 'chore'
created: '2026-10-25'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/prds/prd-pyforge-warden-2026-07-14/prd.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - docs/dreams/pyforge-warden.md
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/one_chain.py
---

<intent-contract>

## Intent

**Problem:** four of the warden PRD's FR arrows are wrong or missing. Line numbers are at `fd06415e4d`.

- **Where the arrows came from.** The 2026-09-17 fold commit `548e907247` ("land warden fold") gave each requirement
  bullet the capability of its PRD subsection. FR-11 (an offline, air-gapped vulnerability database that records its
  source and snapshot time) and FR-12 (a stale database routes the run to `indeterminate`) sit under the vulnerability
  subsection and read CAP-4, although CAP-11 (air-gapped operation) states both almost word for word. FR33 and FR35
  (the license and currency gate flags) are written without the hyphen (`**FR33 *(v1, flag-activated …)*:**`), so the
  fold's extractor skipped them and they carry no arrow.
- **Why nothing noticed.** Doctor's `fr-without-cap` (`pyforge/doctor/sources/one_chain.py`) checks only that a cited
  CAP exists, and its `FR-\d+` grammar cannot see an unhyphenated id.
- **What found it.** The fleet audit of 2026-10-25, after marshal Story 105.1 (#2314).

**Approach:**
- **The table is the contract.** `spec-pyforge-warden`'s memlog carries the approved table (the 2026-10-25 decision
  entry "the approved table for Story 19.1"): FR-11 ← CAP-11, CAP-4; FR-12 ← CAP-11, CAP-4 (both were CAP-4);
  FR33 ← CAP-5; FR35 ← CAP-5 (both had none). Evidence: CAP-11's and CAP-5's success text in
  `spec-pyforge-warden/SPEC.md`.
- **The rewrite.** FR-11's and FR-12's arrows are replaced. FR33 and FR35 gain `← CAP-5` after the bold id, in FR-32's
  shape (`- **FR33** ← CAP-5 *(v1, flag-activated — D12 2026-07-16)*: …`); their ids keep their spelling, and no word
  of their text changes.

- **The record.** A PRD `## Currency reconciliation — 2026-10-25 (Story 19.1)` section lists the change; the PRD,
  spine and epics `updated:` stamps move with notes.
- **`type: chore`, no flag.** A traceability correction to a planning artifact; under `spec-feature-flag-governance`
  Q1 a chore carries no flag. Planning files only, so it is built in its own chain PR, not dispatched.

Ledger key: `19-1-every-warden-prd-fr-arrow-names-the-spec-capability-that-realizes-it`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- **`spec-one-chain-per-station` CAP-5** (FRs derive from CAPs): every FR names the capability it derives from; this
  story makes warden's names true.
- **`spec-one-chain-per-station` CAP-3** (the station fold procedure): the fold this story corrects.
- No `spec-pyforge-warden` CAP is minted, and no `SPEC.md` text changes.
- **Origin.** `docs/dreams/pyforge-warden.md` Realization log, the 2026-10-25 (the PRD's FR arrows were mapped by subsection, not traced) entry; the operator's ruling of 2026-10-25 "Do rows 1-5 in one PR".

## Acceptance Criteria

- **AC1 — The four arrows.** FR-11, FR-12, FR33 and FR35 carry exactly their new arrows, and no other FR bullet
  changed (a diff of the PRD's `- **FR` lines against `fd06415e4d` shows exactly 4 changed lines).
- **AC2 — Every cited capability exists.** Each `CAP-n` in a changed arrow without a `spec-` prefix is declared in
  `spec-pyforge-warden/SPEC.md`.
- **AC3 — Gates.** `fr-without-cap`, `chain-currency`, `chain-completeness` and `detectors-ci` stay green.

## Boundaries & Constraints

**Always:**
- Change only the arrow text of the lines in the table, and re-stamp what chain currency requires in the same commit.
- Keep FR33 and FR35 spelled without the hyphen; renaming them needs an operator ruling.

**Never:**
- Never change an FR's number, title or body, `SPEC.md`, or a detector.

## I/O & Edge-Case Matrix

| Bullet | Before | After |
|---|---|---|
| FR-10, FR-13 | CAP-4 | unchanged |
| FR-11, FR-12 | CAP-4 | CAP-11, CAP-4 |
| FR33, FR35 | no arrow (unhyphenated, skipped by the fold) | CAP-5; spelling kept |
| every other FR | section-mapped or hand-written, traced | unchanged |

</intent-contract>

## Binding

- Parent capabilities: `spec-one-chain-per-station` CAP-5 and CAP-3. No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-warden.md` § *Realization log*, the 2026-10-25 (the PRD's FR arrows were mapped by subsection, not traced) entry.
- Epic: Epic 19 (new), minted with this story. `epic-19` and `epic-19-retrospective` are minted with it.
- Ledger key: `19-1-every-warden-prd-fr-arrow-names-the-spec-capability-that-realizes-it`.
- Deps: —.
- Minted 2026-10-25 in one chain commit; built in the same PR (the five-station FR-arrow PR: herald 46.1, mason 32.1,
  warden 19.1, steward 110.1, marshal 106.1 and 106.2, atlas 40.1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).

**Run before the push (not dispatch gates):**
- `git diff fd06415e4d -- _bmad-output/projects/pyforge-warden/planning-artifacts/prds/prd-pyforge-warden-2026-07-14/prd.md | grep -c '^+- \*\*FR'` — expected: `4`` (AC1).
- `pixi run -e pyforge-guild python -m pyforge.doctor.sources fr-without-cap` — expected: OK.
- `pixi run -e pyforge-guild python scripts/chain_currency_sweep_check.py --json --project pyforge-warden` — expected: no errors.
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0.

## Auto Run Result

Status: in-review (hand-built in the chain PR)
Implementation: the PRD FR arrows rewritten from the memlog table; PRD and spine § Currency reconciliation —
2026-10-25 (Story 19.1) added; PRD, spine and epics re-stamped.

## Spec Change Log

- 2026-10-25: minted from the Dream entry of 2026-10-25 (the PRD's FR arrows were mapped by subsection, not traced) at the operator's ruling of 2026-10-25 "Do rows 1-5 in one PR". `type: chore`, no flag.
- 2026-10-25: implemented in the chain PR; moved to `in-review`.

## Review Triage Log

- (none yet)
