---
title: '26.1: The dossier reads the A→B cutover as control-plane fact'
type: 'docs'
created: '2026-09-25'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The dossier is a forensic inventory of A; the cutover's state lives in the Spec, the capability ledger and B's `PIN.md`.

**Approach:** Rewrite the Estate, Foundation, Synthesis and Verified sections of `docsite/content/dossier.yml` as control-plane fact, porting PR #1576's diff by hand; each Verified claim cites its evidence.

## Boundaries & Constraints

**Always:**
- A is never archived; B is the lasting root rebuilt from Frame + Spec; modes never `move`.
- SBOM claims are labelled A-side.
- Every Verified claim cites `docs/foundry/capability-ledger.yaml`, B's `case-list.md`, or a named CI run.

**Never:**
- Do not merge PRs #1563 / #1564 / #1576; port their payload by hand where this story names it.
- Do not flip any Epic 44 `blocked` key or `pyforge.cutover_root`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.
- Do not edit `rxm7706/python-foundry`.
- Do not state the cutover as flipped or B as a mirror of A.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Verified claim without a source | dossier.yml | rejected in review | fail loud |
| site render | `pixi run -e site site-check` | green | fail loud |

</intent-contract>

## Binding

Parent Spec capability: `spec-python-foundry-cutover fnd:CAP-14`.
Dream: `docs/dreams/pyforge-unifying-strategy.md` § *Where next* → *Consolidation — 2026-09-25*.
Ledger key: `26-1-the-dossier-reads-the-a-b-cutover-as-control-plane-fact`.
Ledger status at mint: `backlog`.
Minted 2026-09-25 from `epics.md` so `marshal factory dispatch` can resolve `spec-26-1-the-dossier-reads-the-a-b-cutover-as-control-plane-fact.md`.

## Epic excerpt

**Type:** docs • **Effort:** M • **Deps:** — • **FR/AD:** fnd:CAP-14 • cross-station: steward index 67.6 flips `done` when this closes; reference payload PR #1576 (branch `docs/pyforge-estate-whitepaper`, 118 insertions in `dossier.yml`)
**Surface:** `docsite/content/dossier.yml` (Estate, Foundation, Synthesis and Verified sections), `docsite/` templates only if a new section needs one, herald tests that assert dossier structure.
**Given** the dossier (re-verified 2026-09-13) is a forensic inventory of A's stations, and the cutover's state — A/B roles, modes, `pyforge.cutover_root`, the four campaign verbs — lives in the Spec, the capability ledger and B's `PIN.md`
**When** this story lands
**Then** the Estate section states A (`local-recipes`: control plane, oracle, root of record until the flip, never archived) and B (`python-foundry`: lasting root, engines rebuilt from Frame + Spec), the modes with "never `move`", and the four campaign verbs each with a done / not-done line; SBOM claims are labelled A-side; the Verified section cites, per claim, `docs/foundry/capability-ledger.yaml`, B's `case-list.md`, or a named CI run
**And** `pixi run -e site site-check` is green, and no claim reads the cutover as flipped or B as a mirror of A

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e site site-check` — expected: exit 0.
