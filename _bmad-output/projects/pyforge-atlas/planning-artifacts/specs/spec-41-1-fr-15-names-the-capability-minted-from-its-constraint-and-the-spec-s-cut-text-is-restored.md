---
title: "41.1: FR-15 names the capability minted from its Constraint, and the Spec's cut text is restored"
type: 'chore'
created: '2026-10-26'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/.memlog.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md
  - docs/dreams/pyforge-atlas.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/one_chain.py
  - docs/foundry/capability-ledger.yaml
---

<intent-contract>

## Intent

**Problem:** FR-15 cites a Spec Constraint, not a capability, by the 2026-10-25 ruling for Story 40.1; the 2026-10-26 re-audit showed the standard forbids that form (CHAIN-STANDARD § 2 and § 6), the capability ledger routes only capabilities to pyforge-foundry, Constraints have no stable id, and AD-16 already carries the Constraint. Separately, the 2026-09-17 fold (`86d1cdf3ee`) rendered 86 of the Spec's intent and success bullets as their first source line only.

**Approach:**
- **Mint, then point.** The Constraint "Conda-forge-only, pixi-managed, py3.14-floored provisioning" promises a guarantee an operator can see (the stack resolves at its pins on 3.14; `llms-full-check`; both air-gap routing layers), so it is minted as CAP-72 through the memlog decision of 2026-10-26 and an anchor-asserting script render after CAP-71 (the #1605 route; both self-validate passes logged). FR-15's arrow becomes `← CAP-72`; the Constraint stays as CAP-72's provenance.
- **The AD carries the Constraint.** AD-16 gains an *Implements* line naming the Constraint and CAP-72 (CHAIN-STANDARD § 12).
- **Restore the cut text.** Every capability block whose intent or success is a strict prefix of its pre-fold source block (`git show 86d1cdf3ee^:…/spec-pyforge-atlas/SPEC.md`) is rejoined to the full source text by script; the memlog `correction` entries of 2026-10-26 record the method and counts. No id, order or provenance line moves.
- **The ledger.** `docs/foundry/capability-ledger.yaml` gains the CAP-72 row, mode `rebuild` (`fcl` CAP-2 makes an unclassified CAP HARD).
- **`type: chore`, no flag.** Planning artifacts only; built in the chain PR, not dispatched.

Ledger key: `41-1-fr-15-names-the-capability-minted-from-its-constraint-and-the-spec-s-cut-text-is-restored`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- **`spec-pyforge-atlas` CAP-72** (every atlas component provisions from conda-forge through pixi on the 3.14 floor, air-gapped): minted by this story; FR-15 cites it.
- **`spec-one-chain-per-station` CAP-5** (FRs and NFRs derive from CAPs, amended 2026-10-26) and **CAP-3** (the station fold procedure): the rule and the fold this story corrects.
- **Origin.** `docs/dreams/pyforge-atlas.md` Realization log, the 2026-10-26 entry; the operator's 2026-10-26 rulings (b) and (e).

## Acceptance Criteria

- **AC1 — FR-15's arrow.** The PRD's `#### FR-15:` heading ends with `← CAP-72` and no other FR line's arrow changed (a diff of the PRD's `#### FR-` lines against `92fa3edbbd` shows exactly 1 changed line).
- **AC2 — CAP-72 is defined.** `spec-pyforge-atlas/SPEC.md` carries `- **CAP-72 — …** ← Constraint "Conda-forge-only, pixi-managed, py3.14-floored provisioning"` after CAP-71 with an intent and a success; CAP-1..CAP-71 keep their lines' ids, order and provenance.
- **AC3 — The cut text.** 86 intent/success bullets changed in `SPEC.md`, each the pre-fold source text in full (the restore script's report, logged in the memlog); zero bullets still end mid-sentence where the source continued.
- **AC4 — AD-16 and the ledger.** AD-16 names the Constraint and CAP-72; `docs/foundry/capability-ledger.yaml` has `pyforge-atlas:CAP-72` with `mode: rebuild`; `capability-ledger-check` is green.
- **AC5 — Gates.** `fr-without-cap` (upgraded by doctor 50.1), `chain-completeness`, `chain-currency` (atlas) and `detectors-ci` are green.

## Boundaries & Constraints

**Always:**
- Mint through the memlog decision first, then the script render; log both `bmad-spec` self-validate passes; re-stamp PRD, spine and epics in the same commit.

**Never:**
- Never change an FR's number, title or body beyond FR-15's arrow; never renumber or remove a CAP; never hand-edit `SPEC.md`.

## I/O & Edge-Case Matrix

| Line | Before | After |
|---|---|---|
| FR-15 | `← Constraint "Conda-forge-only, pixi-managed, py3.14-floored provisioning"` | `← CAP-72` |
| SPEC.md CAP-72 | absent | defined after CAP-71, provenance the Constraint |
| SPEC.md CAP-1..CAP-69 bullets | 86 cut at the first source line | the full pre-fold text |
| AD-16 | `(FR-15)` | + *Implements* the Constraint, CAP-72 |
| capability-ledger | no CAP-72 row | `pyforge-atlas:CAP-72`, rebuild |

</intent-contract>

## Binding

- Parent capabilities: `spec-pyforge-atlas` CAP-72 (minted); `spec-one-chain-per-station` CAP-5 and CAP-3.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-26 entry.
- Epic: Epic 41 (new), minted with this story and with Stories 41.2 and 41.3 (`backlog`). `epic-41` and `epic-41-retrospective` are minted with it.
- Ledger key: `41-1-fr-15-names-the-capability-minted-from-its-constraint-and-the-spec-s-cut-text-is-restored`.
- Deps: —.
- Minted 2026-10-26 in one chain commit; built in the same PR (the one-PR "every requirement derives from a capability" effort: atlas 41.1, doctor 50.1, herald 47.1, marshal 108.1, mason 33.1, scribe 27.1, steward 111.1, warden 20.1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-atlas pyforge-atlas-test` — expected: pass (the station's `verify_commands`; this story touches no atlas code).

**Run before the push (not dispatch gates):**
- `git diff 92fa3edbbd -- _bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md | grep -c '^+#### FR-'` — expected: `1` (AC1).
- `grep -c '^- \*\*CAP-72 — ' _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md` — expected: `1` (AC2).
- `pixi run -e pyforge-guild python -m pyforge.doctor.sources fr-without-cap` — expected: no FAIL for atlas (AC5).
- `pixi run -e pyforge-guild capability-ledger-check` — expected: exit 0 (AC4).
- `pixi run -e pyforge-guild python scripts/chain_currency_sweep_check.py --json --project pyforge-atlas` — expected: no errors (AC5).
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0 (AC5).

## Auto Run Result

Status: done (hand-built in the chain PR; promoted after the independent reviews, inside the PR)
Implementation: CAP-72 rendered after CAP-71 from the memlog decision (self-validate passes 1 and 2 logged); FR-15 `← CAP-72`; AD-16's *Implements* line; 86 bullets restored by `restore_caps.py` from `86d1cdf3ee^` (memlog `correction` entries); the capability-ledger row; PRD, spine and epics re-stamped with § Currency reconciliation — 2026-10-26.

## Spec Change Log

- 2026-10-26: minted from the station Dream's entry of 2026-10-26 (every requirement derives from a capability) at the operator's rulings of 2026-10-26 ("yes forbid it"; the ruling sheet accepted in full).

- 2026-10-26: promoted to `done` inside the chain PR after the independent reviews of 2026-10-26 (planning tables: FAIL then PASS on the amendments; detector diff: FAIL then PASS on round 2), every finding applied in the chain PR.

## Review Triage Log

- 2026-10-26: the independent reviews of 2026-10-26 (planning tables: FAIL then PASS on the amendments; detector diff: FAIL then PASS on round 2), every finding applied in the chain PR; no blocker open at promotion.
