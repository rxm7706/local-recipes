---
title: "106.2: FR-144..FR-147 trace to the capabilities the fold dropped"
type: 'chore'
created: '2026-10-25'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - docs/foundry/capability-ledger.yaml
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/one_chain.py
---

<intent-contract>

## Intent

**Problem:** FR-144..FR-147 (the marshal PRD's § 16.5, detector self-verification) cite capabilities that do not
carry them. Line numbers are at `fd06415e4d`.

- **Why.** Their source, `spec-dream-to-code-model-self-verification`, listed its four capabilities as a plain numbered
  list ("Scope (capabilities)": fixtures for the Dream-chain detector, fixtures for the drift detector, a
  detector-incident log, the `--dreams` hygiene mode). The 2026-09-16 pilot fold (`1e845b55fc`) minted CAPs only from
  `CAP-n` lines, so it minted none of these, and counted the FRs' arrows instead: CAP-102..CAP-105, which are fleet
  chain-completeness capabilities. Marshal Stories 17.1 and 17.2 realized all four and stay done.
- **Where it stands.** Story 105.1 (#2314) left the four unchanged and opened `DW-marshal-105-1` for a source decision.
  No `spec-pyforge-doctor` capability carries them either, although the detectors now run as doctor sources.
- **The ruling.** The operator chose to restore the four as `spec-pyforge-marshal` capabilities (2026-10-25).

**Approach:**
- **The decision is the contract.** `spec-pyforge-marshal`'s memlog carries the four capabilities' text (the 2026-10-25
  decision entry "the four capabilities Story 106.2 restores"), derived from the source Spec at `1e845b55fc^`. It is
  rendered into `SPEC.md` after CAP-292 by an anchor-asserting script (the operator's ruling named that route), and both
  `bmad-spec` self-validate passes are logged on the memlog.
- **The rewrite.** FR-144 ← CAP-293, FR-145 ← CAP-294, FR-146 ← CAP-295, FR-147 ← CAP-296; only the arrow text changes.
- **The ledgers.** The capability ledger classifies the four (`rebuild`, as every other `spec-pyforge-marshal` CAP), and
  `DW-marshal-105-1` is closed with its resolution.

- **The record.** A PRD `## Currency reconciliation — 2026-10-25 (Story 106.2)` section lists the change; the PRD,
  spine and epics `updated:` stamps move with notes.
- **`type: chore`, no flag.** A traceability correction to a planning artifact; under `spec-feature-flag-governance`
  Q1 a chore carries no flag. Planning files only, so it is built in its own chain PR, not dispatched.

Ledger key: `106-2-fr-144-to-fr-147-trace-to-the-capabilities-the-fold-dropped`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- **`spec-pyforge-marshal` CAP-293..CAP-296** (restored by this story): the capabilities FR-144..FR-147 derive from.
- **`spec-one-chain-per-station` CAP-5** (FRs derive from CAPs) and **CAP-8** (the marshal pilot): the fold that
  dropped them.
- No `SPEC.md` text changes except the capabilities this story restores, rendered from the memlog decision.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, the 2026-10-25 (FR-144..FR-147's capabilities were dropped by the fold) entry; the operator's ruling of 2026-10-25 "Restore 4 marshal CAPs (Recommended)" on DW-marshal-105-1.

## Acceptance Criteria

- **AC1 — The four arrows.** FR-144..FR-147 cite CAP-293..CAP-296 one to one, and no other FR heading changed in
  this story (a diff of the PRD against `fd06415e4d` shows exactly 4 changed `#### FR-14[4-7]:` headings).
- **AC2 — Every cited capability exists.** Each `CAP-n` in a changed arrow without a `spec-` prefix is declared in
  `spec-pyforge-marshal/SPEC.md`.
- **AC3 — The capabilities and ledgers.** `spec-pyforge-marshal/SPEC.md` declares CAP-293..CAP-296 with the memlog
  decision's text; `docs/foundry/capability-ledger.yaml` classifies each; `DW-marshal-105-1` reads `closed`.
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
| `spec-pyforge-marshal` CAP-293..CAP-296 | absent | declared, shipped, `← spec-dream-to-code-model-self-verification Capability 1..4` |
| FR-144 | CAP-102 | CAP-293 |
| FR-145 | CAP-103 | CAP-294 |
| FR-146 | CAP-104 | CAP-295 |
| FR-147 | CAP-105 | CAP-296 |
| `DW-marshal-105-1` | open | closed |
| CAP-102..CAP-105 and FR-148..FR-151 | fleet chain completeness | unchanged |

</intent-contract>

## Binding

- Parent capabilities: `spec-one-chain-per-station` CAP-5 and CAP-8. The restored capabilities are minted on `spec-pyforge-marshal`.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-25 (FR-144..FR-147's capabilities were dropped by the fold) entry.
- Epic: Epic 106, minted with Story 106.1.
- Ledger key: `106-2-fr-144-to-fr-147-trace-to-the-capabilities-the-fold-dropped`.
- Deps: —.
- Minted 2026-10-25 in one chain commit; built in the same PR (the five-station FR-arrow PR: herald 46.1, mason 32.1,
  warden 19.1, steward 110.1, marshal 106.1 and 106.2, atlas 40.1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).

**Run before the push (not dispatch gates):**
- `git diff fd06415e4d -- _bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md | grep -c '^+#### FR-14[4-7]:'` — expected: `4`` (AC1).
- `pixi run -e pyforge-guild python -m pyforge.doctor.sources fr-without-cap` — expected: OK.
- `pixi run -e pyforge-guild python scripts/chain_currency_sweep_check.py --json --project pyforge-marshal` — expected: no errors.
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0.

## Auto Run Result

Status: in-review (hand-built in the chain PR)
Implementation: the PRD FR arrows rewritten from the memlog table; PRD and spine § Currency reconciliation —
2026-10-25 (Story 106.2) added; PRD, spine and epics re-stamped.

## Spec Change Log

- 2026-10-25: minted from the Dream entry of 2026-10-25 (FR-144..FR-147's capabilities were dropped by the fold) at the operator's ruling of 2026-10-25 "Restore 4 marshal CAPs (Recommended)" on DW-marshal-105-1. `type: chore`, no flag.
- 2026-10-25: implemented in the chain PR; moved to `in-review`.

## Review Triage Log

- (none yet)
