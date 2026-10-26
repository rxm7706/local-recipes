---
title: "111.1: The steward Spec's fold-cut capability text is restored, and the foundry inherits the amended rule"
type: 'chore'
created: '2026-10-26'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - docs/dreams/pyforge-steward.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/.memlog.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/SPEC.md
  - docs/foundry/capability-ledger.yaml
---

<intent-contract>

## Intent

**Problem:** The 2026-09-17 steward fold (`97e0816ad2`) rendered 23 capabilities with the placeholder title `from spec-<old>` (CAP-1..CAP-4, steward's own duties, among them), wrote 'See absorbed Spec memlog' into 29 bullets, cut 147 bullets at their first source line and joined 15 `verified:` sub-bullets onto success lines. The chain standard pyforge-foundry inherits (`spec-foundry-regenerate-not-fold` CAP-7) named FR ← CAP in its pre-amendment form, so B would have inherited the 2026-10-25 exception. And three CAPs minted in this effort need their ledger rows.

**Approach:**
- **Restore the Spec text.** A `correction` entry names the fold, the source and the counts; a `decision` entry carries the 14 authored titles; `restore_caps.py` over `97e0816ad2^` (SPEC.md blocks; the source memlog's `(capability)` entry where the SPEC.md carried only a status paragraph) rejoins the cut bullets, restores the placeholders, restores 9 titles from source lines, takes the 14 authored titles, and splits the 15 joined `verified:` sub-bullets back out; three correction entries record the render and its parser fixes; both `bmad-spec` self-validate passes are logged.
- **The foundry inherits the amendment.** A CAP-7 event on `spec-foundry-regenerate-not-fold`'s memlog: the chain standard B inherits is amended, not excepted — a requirement cites defined CAPs only, a Constraint reaches code through an AD, only capabilities cross through the ledger; the eight station Specs keep their ids; no Epic 44 key moves; `spec-pyforge-unifying-strategy` carries no FR rule and is untouched.
- **The ledger.** Rows for `pyforge-atlas:CAP-72`, `pyforge-doctor:CAP-92` and `pyforge-doctor:CAP-93`, each `mode: rebuild` (ruling (e)); `updated:` bumped.
- **`type: chore`, no flag.** Planning artifacts only; built in the chain PR.

Ledger key: `111-1-the-steward-spec-s-fold-cut-capability-text-is-restored-and-the-foundry-inherits-the-amended-rule`.
Type / Effort / Deps: chore / M / —.

### Living CAP citations

- **`spec-one-chain-per-station` CAP-5** (amended), **CAP-3** and **CAP-7**: the rule, the fold this story corrects, and the on-ramp this story updates.
- **`spec-foundry-regenerate-not-fold` CAP-7**: B's starting discipline, now the amended form.
- **`spec-foundry-capability-ledger` CAP-2**: every minted CAP classified from the extract; three rows added.
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, the 2026-10-26 entry.

## Acceptance Criteria

- **AC1 — No placeholder.** `grep -c ' — from spec-' SPEC.md` is 0 (was 23) and `grep -c 'ee absorbed Spec memlog' SPEC.md` is 0 (was 29).
- **AC2 — Counts.** 168 `- **CAP-n —` capability lines before and after; the restore report reads 9 titles restored, 14 authored, 29 placeholder bullets restored, 147 rejoined, 15 split; `grep -c '^  - \*\*verified:\*\*' SPEC.md` is 15 more than before and no success line contains `- **verified:**`.
- **AC3 — The foundry memlog.** `spec-foundry-regenerate-not-fold/.memlog.md` ends with a 2026-10-26 CAP-7 event naming the amended rule; no Epic 44 ledger key moved (`git diff` on the steward ledger shows only this story's keys).
- **AC4 — The ledger.** `docs/foundry/capability-ledger.yaml` has the three rows with `mode: rebuild`; `pixi run -e pyforge-guild capability-ledger-check` exits 0.
- **AC5 — Gates.** `chain-completeness`, `chain-currency` (steward) and `detectors-ci` are green; the independent review reads every authored title.

## Boundaries & Constraints

**Always:**
- Memlog decision before the render; the script asserts the CAP count; re-stamp PRD, spine and epics in the same commit; classify every minted CAP in the same PR.

**Never:**
- Never hand-edit `SPEC.md`; never renumber, add or remove a steward CAP; never flip an Epic 44 key; never change a PRD requirement.

## I/O & Edge-Case Matrix

| Block | Before | After |
|---|---|---|
| 23 placeholder titles (CAP-1..4, 73, 74, 104..108, 124..126, …) | `from spec-…` | 9 source titles, 14 authored |
| 29 'See absorbed' bullets | placeholder | source text |
| 147 cut bullets | first source line | full source text |
| 15 success lines | joined `- **verified:**` text | success + its own `verified:` bullet |
| foundry memlog | CAP-7 line of 2026-09-17 | + 2026-10-26 CAP-7 event (amended rule) |
| capability ledger | no rows for CAP-72/92/93 | three `rebuild` rows |

</intent-contract>

## Binding

- Parent capabilities: `spec-one-chain-per-station` CAP-5 (amended), CAP-3, CAP-7; `spec-foundry-regenerate-not-fold` CAP-7; `spec-foundry-capability-ledger` CAP-2. No steward CAP is minted.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-26 entry.
- Epic: Epic 111 (new), minted with this story (draft PR #2274 claims Epic 109; Epic 110 is Story 110.1's). `epic-111` and `epic-111-retrospective` are minted with it.
- Ledger key: `111-1-the-steward-spec-s-fold-cut-capability-text-is-restored-and-the-foundry-inherits-the-amended-rule`.
- Deps: —.
- Minted 2026-10-26 in one chain commit; built in the same PR (the one-PR "every requirement derives from a capability" effort: atlas 41.1, doctor 50.1, herald 47.1, marshal 108.1, mason 33.1, scribe 27.1, steward 111.1, warden 20.1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (this story touches no steward code).

**Run before the push (not dispatch gates):**
- `grep -c ' — from spec-' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md` — expected: `0` (AC1).
- `grep -c '^- \*\*CAP-[0-9]* —' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md` — expected: `168` (AC2).
- `pixi run -e pyforge-guild capability-ledger-check` — expected: exit 0 (AC4).
- `pixi run -e pyforge-guild python scripts/chain_currency_sweep_check.py --json --project pyforge-steward` — expected: no errors (AC5).
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0 (AC5).

## Auto Run Result

Status: in-review (hand-built in the chain PR)
Implementation: `restore_caps.py` over `97e0816ad2^` (three correction entries, the authored-text decision, self-validate passes 1 and 2 logged); the foundry memlog's CAP-7 event; the three capability-ledger rows; PRD, spine and epics re-stamped with § Currency reconciliation — 2026-10-26 (Story 111.1).

## Spec Change Log

- 2026-10-26: minted from the station Dream's entry of 2026-10-26 (every requirement derives from a capability) at the operator's rulings of 2026-10-26 ("yes forbid it"; the ruling sheet accepted in full).

## Review Triage Log

- (none yet)
