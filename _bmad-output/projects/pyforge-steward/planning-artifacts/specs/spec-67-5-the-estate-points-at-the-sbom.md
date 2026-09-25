---
title: '67.5: The estate points at the SBOM'
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

**Problem:** Install instructions still teach `-e local-recipes` for everyday work.

**Approach:** Name `pixi install -e pyforge-foundry-full` as the laptop install in the developer guide, `AGENTS.md` (through `bmad-project-context`), and the CFE / steward docs; keep `local-recipes` for recipe-factory work at scale.

## Boundaries & Constraints

**Always:**
- CFE files: invoke `conda-forge-expert` (Rule 1) and land its retro + `CHANGELOG.md` entry (Rule 2).

**Never:**
- Do not merge PRs #1563 / #1564 / #1576; port their payload by hand where this story names it.
- Do not flip any Epic 44 `blocked` key or `pyforge.cutover_root`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.
- Do not edit `rxm7706/python-foundry`.
- Do not change the managed block by hand.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| doc names an install | any listed surface | `pyforge-foundry-full` for laptops | fix in the same change |

</intent-contract>

## Binding

Parent Spec capability: `spec-python-foundry-cutover fnd:CAP-12`.
Dream: `docs/dreams/pyforge-unifying-strategy.md` § *Where next* → *Consolidation — 2026-09-25*.
Ledger key: `67-5-the-estate-points-at-the-sbom`.
Ledger status at mint: `backlog`.
Minted 2026-09-25 from `epics.md` so `marshal factory dispatch` can resolve `spec-67-5-the-estate-points-at-the-sbom.md`.

## Epic excerpt

**Type:** docs • **Effort:** S • **Deps:** S-67.2 • **FR/AD:** fnd:CAP-12 • Dream 2026-09-25 (campaign phase 4)
**Surface:** `docs/reference/developer-guide.md`, `AGENTS.md` (managed-block lines through `bmad-project-context`), `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md` (Rule 1: invoke `conda-forge-expert`; Rule 2: the CFE retro and `CHANGELOG.md` entry land with it), `.claude/skills/pyforge-steward/SKILL.md` if it names an install.
**Given** the laptop gate is green on `main`
**When** this story lands
**Then** each surface names `pyforge-foundry-full` as the laptop install and `local-recipes` only for recipe-factory work at scale; `governance-currency` and scribe's parity meta-test stay green

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0 (`governance-currency`).
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (parity meta-test).
