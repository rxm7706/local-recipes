---
title: "47.1: The herald Spec's fold-cut capability text is restored"
type: 'chore'
created: '2026-10-26'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/prds/prd-pyforge-herald-2026-08-01/prd.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/architecture/architecture-pyforge-herald-2026-08-01/ARCHITECTURE-SPINE.md
  - docs/dreams/pyforge-herald.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
---

<intent-contract>

## Intent

**Problem:** The 2026-09-17 herald fold (`4251c42229`) rendered 20 capabilities with the placeholder title `from spec-<old>` (their source lines were title-less), wrote 'See absorbed Spec memlog and git history.' into 12 intent/success bullets, and cut 8 bullets at their first source line. A PRD arrow pointing at such a block says nothing, and a title-overlap guard reads nothing.

**Approach:**
- **Memlog first.** A `correction` entry names the fold, the source (`git show 4251c42229^:<absorbed Spec>/SPEC.md`, and the source memlog's `(capability)` entries where the SPEC.md carried none) and the counts; a `decision` entry carries every authored title and bullet for review.
- **Script render.** `restore_caps.py` rejoins each cut bullet to the full source text, restores each placeholder bullet from the source, restores 9 titles from source lines that had one, and takes the 11 authored titles and 4 authored bullets from the decision; the CAP count is asserted unchanged; both `bmad-spec` self-validate passes are logged.
- **Authored text is marked.** Titles authored from intent share a content word with it and duplicate no other herald title; the 3 intents for CAP-1..CAP-3 (whose pre-fold HER lines carried a title and a *Success:* only) and CAP-42's success are written from the title and success text, not invented.
- **No CAP minted.** Herald's PRD arrows were re-traced by Story 46.1; this story changes no PRD requirement.

Ledger key: `47-1-the-herald-spec-s-fold-cut-capability-text-is-restored`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- **`spec-one-chain-per-station` CAP-5** (amended): the capability tier a requirement's arrow must land on, now readable.
- **`spec-one-chain-per-station` CAP-3**: the fold this story corrects.
- **Origin.** `docs/dreams/pyforge-herald.md` Realization log, the 2026-10-26 entry.

## Acceptance Criteria

- **AC1 — No placeholder.** `grep -c ' — from spec-' SPEC.md` is 0 and `grep -c 'ee absorbed Spec memlog' SPEC.md` is 0 (both were 20 and 12).
- **AC2 — Counts.** 61 `- **CAP-` lines before and after; the restore report (memlog) reads 9 titles restored, 11 authored, 8 placeholder bullets restored, 4 authored, 8 bullets rejoined.
- **AC3 — Fidelity.** Each restored bullet equals the pre-fold source text modulo line wrapping; each authored title shares a content word with its intent; the independent review reads every authored line.
- **AC4 — Gates.** `chain-completeness`, `chain-currency` (herald), `capability-ledger-check` and `detectors-ci` are green.

## Boundaries & Constraints

**Always:**
- Memlog decision before the render; the script asserts the CAP count; re-stamp PRD, spine and epics in the same commit.

**Never:**
- Never hand-edit `SPEC.md`; never renumber, add or remove a CAP; never change a PRD requirement.

## I/O & Edge-Case Matrix

| Block | Before | After |
|---|---|---|
| CAP-14..CAP-28, CAP-43..CAP-47 (20) | `from spec-…` titles | 9 source titles, 11 authored |
| CAP-1..CAP-3, CAP-37..CAP-42 bullets (12) | 'See absorbed Spec memlog' | source text (8), authored (4) |
| 8 cut bullets | first source line | full source text |

</intent-contract>

## Binding

- Parent capabilities: `spec-one-chain-per-station` CAP-5 (amended) and CAP-3. No herald CAP is minted.
- Dream: `docs/dreams/pyforge-herald.md` § *Realization log*, the 2026-10-26 entry.
- Epic: Epic 47 (new), minted with this story. `epic-47` and `epic-47-retrospective` are minted with it.
- Ledger key: `47-1-the-herald-spec-s-fold-cut-capability-text-is-restored`.
- Deps: —.
- Minted 2026-10-26 in one chain commit; built in the same PR (the one-PR "every requirement derives from a capability" effort: atlas 41.1, doctor 50.1, herald 47.1, marshal 108.1, mason 33.1, scribe 27.1, steward 111.1, warden 20.1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (this story touches no herald code).

**Run before the push (not dispatch gates):**
- `grep -c ' — from spec-' _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md` — expected: `0` (AC1).
- `grep -c '^- \*\*CAP-' _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md` — expected: `61` (AC2).
- `pixi run -e pyforge-guild python scripts/chain_currency_sweep_check.py --json --project pyforge-herald` — expected: no errors (AC4).
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0 (AC4).

## Auto Run Result

Status: done (hand-built in the chain PR; promoted after the independent reviews, inside the PR)
Implementation: `restore_caps.py` over `4251c42229^` (memlog correction entries, the authored-text decision, self-validate passes 1 and 2 logged); PRD, spine and epics re-stamped with § Currency reconciliation — 2026-10-26 (Story 47.1).

## Spec Change Log

- 2026-10-26: minted from the station Dream's entry of 2026-10-26 (every requirement derives from a capability) at the operator's rulings of 2026-10-26 ("yes forbid it"; the ruling sheet accepted in full).

- 2026-10-26: promoted to `done` inside the chain PR after the independent reviews of 2026-10-26 (planning tables: FAIL then PASS on the amendments; detector diff: FAIL then PASS on round 2), every finding applied in the chain PR.

## Review Triage Log

- 2026-10-26: the independent reviews of 2026-10-26 (planning tables: FAIL then PASS on the amendments; detector diff: FAIL then PASS on round 2), every finding applied in the chain PR; no blocker open at promotion.
