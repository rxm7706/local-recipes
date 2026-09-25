---
title: '67.2: One laptop gate proves the laptop needs nothing beyond the SBOM'
type: 'feature'
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

**Problem:** Nothing proves the laptop needs nothing beyond `pyforge-foundry-full`.

**Approach:** One `sbom-laptop-gate` task run from the SBOM + layer alone: lint-types, every station suite, the platform bring-up smoke, a channel audit; a missing dependency is a named gap.

## Boundaries & Constraints

**Always:**
- Exit codes follow `docs/reference/judgement-vocabulary.md`.
- The gate runs from `-e pyforge-foundry-full` and its layer only.

**Never:**
- Do not merge PRs #1563 / #1564 / #1576; port their payload by hand where this story names it.
- Do not flip any Epic 44 `blocked` key or `pyforge.cutover_root`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.
- Do not edit `rxm7706/python-foundry`.
- Never fall back to `-e local-recipes`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| complete SBOM | gate on `main` | exit 0 | n/a |
| planted missing dependency | fixture removes one imported package | non-zero; the package is named as a gap | fail loud |

</intent-contract>

## Binding

Parent Spec capability: `spec-python-foundry-cutover fnd:CAP-13`.
Dream: `docs/dreams/pyforge-unifying-strategy.md` § *Where next* → *Consolidation — 2026-09-25*.
Ledger key: `67-2-one-laptop-gate-proves-the-laptop-needs-nothing-beyond-the-sbom`.
Ledger status at mint: `backlog`.
Minted 2026-09-25 from `epics.md` so `marshal factory dispatch` can resolve `spec-67-2-one-laptop-gate-proves-the-laptop-needs-nothing-beyond-the-sbom.md`.

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** S-67.1 • **FR/AD:** fnd:CAP-13 • Dream 2026-09-25 (campaign phase 2)
**Surface:** `pixi.toml` (`[feature.guild-tasks.tasks.sbom-laptop-gate]`), `scripts/sbom_laptop_gate.py` (new), `tests/scripts/test_sbom_laptop_gate.py` (new).
**Given** no check proves the laptop needs nothing beyond `pyforge-foundry-full`
**When** this story lands
**Then** `pixi run -e pyforge-foundry-full sbom-laptop-gate` runs `lint-types`, every station suite, the platform bring-up smoke from the layer environment, and a channel audit (every locked package comes from the declared channels; no PyPI-only entry) and exits 0 on `main`; exit codes follow `docs/reference/judgement-vocabulary.md`
**And** a fixture that removes one dependency a station imports makes the gate exit non-zero and name that dependency as a gap; the gate never falls back to `-e local-recipes`

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-foundry-full sbom-laptop-gate` — expected: exit 0 on `main`.
