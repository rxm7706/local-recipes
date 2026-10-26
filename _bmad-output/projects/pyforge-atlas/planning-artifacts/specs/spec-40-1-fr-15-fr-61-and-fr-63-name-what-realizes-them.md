---
title: "40.1: FR-15, FR-61 and FR-63 name what realizes them"
type: 'chore'
created: '2026-10-25'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/.memlog.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - docs/dreams/pyforge-atlas.md
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - docs/foundry/capability-ledger.yaml
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/one_chain.py
---

<intent-contract>

## Intent

**Problem:** three atlas PRD FRs keep the 2026-09-17 fold's counted arrows because none had a capability to name.
Line numbers are at `fd06415e4d`.

- **FR-61 and FR-63.** They come from `spec-kedro-org-tooling-adoption`, which listed its three capabilities as a plain
  numbered list. The fold (`86d1cdf3ee`) minted CAPs only from `CAP-n` lines, so it minted none of them and counted the
  FRs' arrows instead (CAP-1, CAP-3). Capability 2 survives as CAP-41; Capabilities 1 (the kedro-skills audit) and 3
  (the vscode-kedro decision) were dropped although atlas Stories 11.1 and 11.3 delivered them and stay done.
- **FR-15.** It derives from the Spec's Constraints bullet "Conda-forge-only, pixi-managed, py3.14-floored
  provisioning"; no capability states it, and its counted arrow names CAP-15.
- **Where it stands.** Story 39.1 (#2316) left the three unchanged and opened `DW-atlas-39-1`; the operator ruled on it
  on 2026-10-25.

**Approach:**
- **The decision is the contract.** `spec-pyforge-atlas`'s memlog carries the two capabilities' text and FR-15's arrow
  (the 2026-10-25 decision entry "the two capabilities Story 40.1 restores"), derived from the source Spec at
  `86d1cdf3ee^`. The capabilities are rendered into `SPEC.md` after CAP-69 by an anchor-asserting script (the
  operator's ruling named that route), and both `bmad-spec` self-validate passes are logged on the memlog.
- **The rewrite.** FR-61 ← CAP-70, FR-63 ← CAP-71, FR-15 ← `Constraint "Conda-forge-only, pixi-managed, py3.14-floored
  provisioning"`; only the arrow text changes. The fold-provenance paragraph's 2026-10-25 correction gains one sentence.
- **The ledgers.** The capability ledger classifies the two (`rebuild`, as every other `spec-pyforge-atlas` CAP), and
  `DW-atlas-39-1` is closed with its resolution.

- **The record.** A PRD `## Currency reconciliation — 2026-10-25 (Story 40.1)` section lists the change; the PRD,
  spine and epics `updated:` stamps move with notes.
- **`type: chore`, no flag.** A traceability correction to a planning artifact; under `spec-feature-flag-governance`
  Q1 a chore carries no flag. Planning files only, so it is built in its own chain PR, not dispatched.

Ledger key: `40-1-fr-15-fr-61-and-fr-63-name-what-realizes-them`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- **`spec-pyforge-atlas` CAP-70, CAP-71** (restored by this story): the capabilities FR-61 and FR-63 derive from.
- **`spec-one-chain-per-station` CAP-5** (FRs derive from CAPs) and **CAP-3** (the station fold procedure): the fold
  that dropped them.
- No `SPEC.md` text changes except the capabilities this story restores, rendered from the memlog decision.
- **Origin.** `docs/dreams/pyforge-atlas.md` Realization log, the 2026-10-25 (FR-15, FR-61 and FR-63 had no capability to name) entry; the operator's rulings of 2026-10-25 on DW-atlas-39-1, "Restore 2 atlas CAPs (Recommended)" and "Cite the constraint (Recommended)".

## Acceptance Criteria

- **AC1 — The three arrows.** FR-61 cites CAP-70, FR-63 cites CAP-71 and FR-15 cites its constraint, and no other FR
  heading changed in this story (a diff of the PRD against `fd06415e4d` shows exactly 3 changed `#### FR-` lines).
- **AC2 — Every cited capability exists.** Each `CAP-n` in a changed arrow without a `spec-` prefix is declared in
  `spec-pyforge-atlas/SPEC.md`.
- **AC3 — The capabilities and ledgers.** `spec-pyforge-atlas/SPEC.md` declares CAP-70 and CAP-71 with the memlog
  decision's text; `docs/foundry/capability-ledger.yaml` classifies both; `DW-atlas-39-1` reads `closed`.
- **AC4 — Gates.** `fr-without-cap`, `chain-currency`, `chain-completeness` and `detectors-ci` stay green.

## Boundaries & Constraints

**Always:**
- Change only the arrow text of the lines in the table, and re-stamp what chain currency requires in the same commit.
- Render `SPEC.md` only from the memlog decision, by an anchor-asserting script; log both self-validate passes.

**Never:**
- Never change an FR's number, title or body, a detector.

## I/O & Edge-Case Matrix

| Item | Before | After |
|---|---|---|
| `spec-pyforge-atlas` CAP-70, CAP-71 | absent | declared, shipped, `← spec-kedro-org-tooling-adoption Capability 1, 3` |
| FR-61 | CAP-1 (counted) | CAP-70 |
| FR-63 | CAP-3 (counted) | CAP-71 |
| FR-15 | CAP-15 (counted) | the Spec constraint it derives from |
| `DW-atlas-39-1` | open | closed |
| every other kernel FR; the satellite FR series | — | unchanged |

</intent-contract>

## Binding

- Parent capabilities: `spec-one-chain-per-station` CAP-5 and CAP-3. The restored capabilities are minted on `spec-pyforge-atlas`.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-25 (FR-15, FR-61 and FR-63 had no capability to name) entry.
- Epic: Epic 40 (new), minted with this story. `epic-40` and `epic-40-retrospective` are minted with it.
- Ledger key: `40-1-fr-15-fr-61-and-fr-63-name-what-realizes-them`.
- Deps: —.
- Minted 2026-10-25 in one chain commit; built in the same PR (the five-station FR-arrow PR: herald 46.1, mason 32.1,
  warden 19.1, steward 110.1, marshal 106.1 and 106.2, atlas 40.1).

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (the station's `verify_commands`).

**Run before the push (not dispatch gates):**
- `git diff fd06415e4d -- _bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md | grep -c '^+#### FR-'` — expected: `3` (AC1).
- `pixi run -e pyforge-guild python -m pyforge.doctor.sources fr-without-cap` — expected: OK.
- `pixi run -e pyforge-guild python scripts/chain_currency_sweep_check.py --json --project pyforge-atlas` — expected: no errors.
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0.

## Auto Run Result

Status: done (hand-built and promoted to `done` in the chain PR, as #2240 did; the merge subject names marshal 106.1's key, the others land through their ledgers at `main` reading `done`)
Implementation: the PRD FR arrows rewritten from the memlog table; PRD and spine § Currency reconciliation —
2026-10-25 (Story 40.1) added; PRD, spine and epics re-stamped.

## Spec Change Log

- 2026-10-25: minted from the Dream entry of 2026-10-25 (FR-15, FR-61 and FR-63 had no capability to name) at the operator's rulings of 2026-10-25 on DW-atlas-39-1, "Restore 2 atlas CAPs (Recommended)" and "Cite the constraint (Recommended)". `type: chore`, no flag.
- 2026-10-25: implemented in the chain PR; moved to `in-review`.
- 2026-10-25: promoted to `done` in the chain PR after the independent review and its round-1 amendments: this spec, its `epics.md` Status line and its ledger keys.

## Review Triage Log

- **Round 1, 2026-10-25 (an independent reviewer over `fd06415e4d..efc10887a7`, reading the diff against the
  Specs and the pre-fold text): PASS, 0 blockers, 5 should-fix, 9 nits across the seven stories.**
  Atlas: FR-61 ← CAP-70, FR-63 ← CAP-71 and FR-15's constraint arrow confirmed; CAP-70 and CAP-71 restate
  `spec-kedro-org-tooling-adoption`'s Capabilities 1 and 3 faithfully, and the files they name exist. No change needed.
