---
title: "39.1: Every atlas PRD FR arrow names the Spec capability that realizes it"
type: 'chore'
created: '2026-10-25'
status: 'ready-for-dev'
baseline_revision: 'f8803da678fc3f0864545db0135c865f7badb0f8'
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
  - docs/governance/fr-baseline.json
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/one_chain.py
deferred:
  - summary: >-
      Atlas PRD FR-15, FR-61 and FR-63 have no realizing capability: they keep the 2026-09-17 fold's counted arrows CAP-15, CAP-1 and CAP-3 until the operator picks their source.
    evidence: |-
      Story 39.1 (2026-10-25) re-mapped the fold's counted FR arrows from evidence, and the operator ruled ("Approve as proposed") to leave these three unchanged pending a source-capability decision. FR-61 (kedro-skills audit-then-adopt) and FR-63 (a recorded verdict on vscode-kedro) come from spec-kedro-org-tooling-adoption, which numbered its capabilities as a plain list ("Capability 1..3"), not CAP-n. The fold (86d1cdf3ee) minted spec-pyforge-atlas CAPs only from CAP-n lines, so Capabilities 1 and 3 never became capabilities, while their stories (atlas 11.1, 11.3) stayed done; Capability 2 survives as CAP-41 through spec-atlas-kedro-catalog-expansion CAP-6. FR-15 (Pixi-first, nebi-scaffolded, conda-forge-only) derives from the Spec's Constraints bullet "Conda-forge-only, pixi-managed, py3.14-floored provisioning", not from a CAP; its arrow names CAP-15, the derived layer. Options: restore kedro-org Capabilities 1 and 3 as spec-pyforge-atlas CAPs through bmad-spec and point FR-61 and FR-63 at them, or retire those FRs; for FR-15, mint a toolchain CAP from the constraint, or let the FR cite the constraint instead of a CAP.
    location: >-
      _bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md (FR-15, FR-61, FR-63)
    severity: low
---

<intent-contract>

## Intent

**Problem:** most of the atlas PRD's `FR-n ← CAP-m` arrows name the wrong capability. Line numbers are at
`f8803da678`.

- **Where the arrows came from.** The one-chain fold commit `86d1cdf3ee` (2026-09-17, "land atlas fold: one chain")
  appended them by counting: FR-1..FR-22 read CAP-1..CAP-22, and FR-61..FR-68 read CAP-1..CAP-8. The PRD's
  `## Fold provenance (2026-09-17)` (prd.md:12-14) states the rule. Of those 30 headings, only FR-3, FR-8, FR-12 and
  FR-13 landed on the capability that realizes them. Arrows written later by Spec renders (FR-69..FR-77) are right.
- **Why nothing noticed.** Doctor's `fr-without-cap` (`pyforge/doctor/sources/one_chain.py:326-363`) is the only
  reader. It skips FRs in `docs/governance/fr-baseline.json`, which holds atlas FR-1..FR-68, and it never checks that
  a citation is the right one.
- **What it costs.** A fix under a kernel CAP lands on the wrong FR. Story 33.1 was "a fix under CAP-9" (agents
  trigger and read the pipeline natively), and the PRD's CAP-9 arrow sat on FR-9 (the Vizro read surface), not on
  FR-7 (the MCP surface that CAP-9 realizes).

**Approach:**
- **The table is the contract.** `spec-pyforge-atlas`'s memlog carries the approved re-map (the 2026-10-25 decision
  entry "the approved re-map for Story 39.1"): 23 headings, each `FR-n <- <new> (was CAP-k) [evidence]`. It was
  derived from each CAP's full intent and success text at `86d1cdf3ee^` (this Spec's `SPEC.md` cut those bullets to
  their first line at the fold), the FR title and body, and, for FR-61..FR-68, the source Specs'
  own capabilities mapped through the `← spec-<old> CAP-k` provenance lines.
- **The rewrite.** Each of the 23 headings' arrow is replaced, nothing else on the line. Two more fold-written lines
  change on the operator's rulings: `### FR-61..FR-68 delivered ← CAP-1` (a section summary in § Currency
  reconciliation — 2026-08-26) loses its arrow, and `## Fold provenance (2026-09-17)` keeps its text and gains one
  correction sentence.
- **FR-15, FR-61 and FR-63 stay.** No capability carries them (the `deferred:` item above); per the ruling they keep
  their arrows, the PRD's currency section names them as awaiting a source-capability decision, and the `deferred:`
  item becomes a deferred-work ledger row.
- **The record.** A PRD `## Currency reconciliation — 2026-10-25 (Story 39.1)` section lists the re-map; the PRD,
  spine and epics `updated:` stamps move with notes (no FR, AD or story text changes).
- **`type: chore`, no flag.** A traceability correction to a planning artifact; under `spec-feature-flag-governance`
  Q1 a chore carries no flag. Planning files only, so it is built in its own chain PR, not dispatched.

Ledger key: `39-1-every-atlas-prd-fr-arrow-names-the-spec-capability-that-realizes-it`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- **`spec-one-chain-per-station` CAP-5** (FRs derive from CAPs): every FR names the capability it derives from; this
  story makes atlas's names true.
- **`spec-one-chain-per-station` CAP-3** (the station fold procedure): the atlas fold this story corrects.
- No `spec-pyforge-atlas` CAP is minted, and no `SPEC.md` text changes.
- **Origin.** `docs/dreams/pyforge-atlas.md` Realization log, the 2026-10-25 (the PRD's FR arrows were counted, not
  traced) entry; the operator's rulings of 2026-10-25.

## Acceptance Criteria

- **AC1 — The 23 arrows.** Every heading in the memlog table carries exactly its new arrow, and no other FR heading's
  arrow changed: a diff of the PRD's `#### FR-` lines against `f8803da678` shows exactly 23 changed lines.
- **AC2 — The two other fold lines.** `### FR-61..FR-68 delivered` carries no arrow, and `## Fold provenance
  (2026-09-17)` keeps its original sentences and adds one that points at the Story 39.1 currency section.
- **AC3 — Every cited capability exists.** Each `CAP-n` in a changed arrow is declared in
  `spec-pyforge-atlas/SPEC.md` (`- **CAP-n —`).
- **AC4 — FR-15, FR-61, FR-63.** Their arrows are unchanged; the PRD's Story 39.1 currency section names them as
  awaiting a source-capability decision; the deferred-work ledger carries the row ingested from this spec's
  `deferred:` list.
- **AC5 — Gates.** `fr-without-cap`, `chain-currency` (atlas), `chain-completeness` and `ad-citation-check` stay green,
  and `detectors-ci` has no new findings against `main`.

## Boundaries & Constraints

**Always:**
- Change only the arrow text of the 23 headings, the two lines AC2 names, and the currency section; re-stamp what
  chain currency requires in the same commit.

**Never:**
- Never change an FR's number, title or body, `SPEC.md`, or a detector.
- Never re-point FR-15, FR-61 or FR-63 without an operator decision.
- Never touch the Unity or Wasm satellite FRs (their renumbering is Story 39.2, minted only on an operator ruling).

## I/O & Edge-Case Matrix

| Heading block | Before | After |
|---|---|---|
| FR-1..FR-22 (kernel) | CAP-1..CAP-22, counted by the fold | the table's arrows; FR-3, FR-8, FR-12, FR-13 unchanged (right); FR-15 unchanged (deferred) |
| FR-61..FR-68 (2026-08-08 addendum) | CAP-1..CAP-8, counted | FR-62, FR-64..FR-68 the table's arrows; FR-61, FR-63 unchanged (deferred) |
| `### FR-61..FR-68 delivered ← CAP-1` | a counted arrow on a summary heading | no arrow |
| FR-69..FR-77 | written by Spec renders | unchanged |
| Unity FR-1..FR-60, Wasm FR-1..FR-17 (satellites) | no arrows | unchanged |

</intent-contract>

## Binding

- Parent capabilities: `spec-one-chain-per-station` CAP-5 and CAP-3. No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-25 (the PRD's FR arrows were counted, not
  traced) entry.
- Epic: Epic 39 (new), minted with this story. `epic-39` and `epic-39-retrospective` are minted with it.
- Ledger key: `39-1-every-atlas-prd-fr-arrow-names-the-spec-capability-that-realizes-it`.
- Deps: —.
- Surface: planning files only (the PRD, the spine and epics re-stamps, the deferred-work ledger, this spec, the
  memlogs). Hand-built in its chain PR and never dispatched, so no `[epic_surfaces]."39"` entry is added.
- Minted 2026-10-25 in one chain commit; built in the same PR.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (the station's `verify_commands`).

**Run before the push (not dispatch gates):**
- `git diff f8803da678 -- _bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md | grep -c '^+#### FR-'` — expected: `23` (AC1).
- `pixi run -e pyforge-guild python -m pyforge.doctor.sources fr-without-cap` — expected: OK (AC5).
- `pixi run -e pyforge-guild python scripts/chain_currency_sweep_check.py --json --project pyforge-atlas` — expected: exit 0 (AC5).
- `pixi run -e pyforge-guild detectors-ci` — expected: no new findings against `main` (AC5).

## Spec Change Log

- 2026-10-25: minted from the Dream entry of 2026-10-25 (the PRD's FR arrows were counted, not traced) at the
  operator's rulings "Approve as proposed (Recommended)", "Drop the arrow (Recommended)" and "Append a correction
  (Recommended)". `type: chore`, no flag, no CAP.
