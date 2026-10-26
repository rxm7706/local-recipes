---
title: "20.1: The warden Spec's fold-cut capability text is restored"
type: 'chore'
created: '2026-10-26'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/prds/prd-pyforge-warden-2026-07-14/prd.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/architecture/architecture-pyforge-warden-2026-07-14/ARCHITECTURE-SPINE.md
  - docs/dreams/pyforge-warden.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
---

<intent-contract>

## Intent

**Problem:** The 2026-09-17 warden fold (`548e907247`) rendered multi-line intent and success bullets as their first source line only (10 cut intent/success bullets rejoined, and the intent/success bullets the fold dropped from CAP-13..CAP-17 added back from the source). A PRD arrow pointing at such a block says less than the Spec once did.

**Approach:**
- **Memlog first.** A `correction` entry names the fold, the source (`git show 548e907247^:<absorbed Spec>/SPEC.md`; the source memlog's `(capability)` entries where the SPEC.md carried none) and the counts.
- **Script render.** `restore_caps.py` rejoins each cut bullet to the full source text and adds the intent/success bullets the fold dropped from a block; the CAP count is asserted unchanged; both `bmad-spec` self-validate passes are logged; a second correction entry records the parser fix the fleet-wide render needed.
- **No CAP minted; no PRD requirement changes.**

Ledger key: `20-1-the-warden-spec-s-fold-cut-capability-text-is-restored`.
Type / Effort / Deps: chore / XS / —.

### Living CAP citations

- **`spec-one-chain-per-station` CAP-5** (amended): the capability tier a requirement's arrow must land on, now readable.
- **`spec-one-chain-per-station` CAP-3**: the fold this story corrects.
- **Origin.** the station Dream's Realization log, the 2026-10-26 entry.

## Acceptance Criteria

- **AC1 — Counts.** The restore report (memlog) reads 10 cut intent/success bullets rejoined, and the intent/success bullets the fold dropped from CAP-13..CAP-17 added back from the source; the `- **CAP-` line count is unchanged.
- **AC2 — Fidelity.** Each restored bullet equals the pre-fold source text modulo line wrapping; no bullet still ends mid-sentence where the source continued.
- **AC3 — Gates.** `chain-completeness`, `chain-currency` (warden) and `detectors-ci` are green.

## Boundaries & Constraints

**Always:**
- Memlog correction before the render; the script asserts the CAP count; re-stamp PRD, spine and epics in the same commit.

**Never:**
- Never hand-edit `SPEC.md`; never renumber, add or remove a CAP; never change a PRD requirement.

## I/O & Edge-Case Matrix

| Block | Before | After |
|---|---|---|
| cut bullets | first source line | full source text |
| blocks missing intent/success | none | the source's bullets |

</intent-contract>

## Binding

- Parent capabilities: `spec-one-chain-per-station` CAP-5 (amended) and CAP-3. No warden CAP is minted.
- Dream: `docs/dreams/pyforge-warden.md` § *Realization log*, the 2026-10-26 entry.
- Epic: Epic 20 (new), minted with this story. `epic-20` and `epic-20-retrospective` are minted with it.
- Ledger key: `20-1-the-warden-spec-s-fold-cut-capability-text-is-restored`.
- Deps: —.
- Minted 2026-10-26 in one chain commit; built in the same PR (the one-PR "every requirement derives from a capability" effort: atlas 41.1, doctor 50.1, herald 47.1, marshal 108.1, mason 33.1, scribe 27.1, steward 111.1, warden 20.1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (this story touches no warden code).

**Run before the push (not dispatch gates):**
- `pixi run -e pyforge-guild python scripts/chain_currency_sweep_check.py --json --project pyforge-warden` — expected: no errors (AC3).
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0 (AC3).

## Auto Run Result

Status: in-review (hand-built in the chain PR)
Implementation: `restore_caps.py` over `548e907247^` (memlog correction entries; self-validate passes 1 and 2 logged); PRD, spine and epics re-stamped with § Currency reconciliation — 2026-10-26 (Story 20.1).

## Spec Change Log

- 2026-10-26: minted from the station Dream's entry of 2026-10-26 (every requirement derives from a capability) at the operator's rulings of 2026-10-26 ("yes forbid it"; the ruling sheet accepted in full).

## Review Triage Log

- (none yet)
