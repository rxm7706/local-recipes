---
title: '67.3: Every gap and every fat-only pin has a disposition and an owner'
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

**Problem:** Residual solve gaps and fat-only `local-recipes` pins exist only in PR #1564's text.

**Approach:** Derive the list from `pixi.toml` into `docs/foundry/sbom-gaps.md`: a residual solve gap is every feature declared in `pixi.toml` that is in neither the SBOM nor its layer environment (`conda-smithy`, `python-agent-platform` today); a fat-only pin is every package in `[feature.local-recipes.dependencies]` and in no SBOM feature. Each row gets promote / won't-do / upstream, a reason and an owner station; `sbom-gaps-check` keeps file and derivation equal.

## Boundaries & Constraints

**Always:**
- Derive, never hand-list: the check reds a missing or stale row of either kind.
- Conda-forge packaging rows name Mason as owner.
- Co-governor reconcile before landing: a memlog entry on every Spec `spec-surface-check` names, `git add`, then `python scripts/spec_surface_check.py --write-baseline --spec <project>/<spec>` per named Spec, re-run the check and read its exit code; never a bare stamp.

**Never:**
- Do not merge PRs #1563 / #1564 / #1576; port their payload by hand where this story names it.
- Do not flip any Epic 44 `blocked` key or `pyforge.cutover_root`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.
- Do not edit `rxm7706/python-foundry`.
- Do not open upstream issues here (Story 67.4, outward).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| new fat-only pin appears | derivation vs file | check reds naming the pin | fail loud |
| feature outside the SBOM and layer added or removed | derivation vs file | check reds naming the feature | fail loud |
| row no longer derivable | file keeps a stale row | check reds naming the row | fail loud |

</intent-contract>

## Binding

Parent Spec capability: `spec-python-foundry-cutover fnd:CAP-13`.
Dream: `docs/dreams/pyforge-unifying-strategy.md` § *Where next* → *Consolidation — 2026-09-25*.
Ledger key: `67-3-every-gap-and-every-fat-only-pin-has-a-disposition-and-an-owner`.
Ledger status at mint: `backlog`.
Minted 2026-09-25 from `epics.md` so `marshal factory dispatch` can resolve `spec-67-3-every-gap-and-every-fat-only-pin-has-a-disposition-and-an-owner.md`.

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** S-67.1 • **FR/AD:** fnd:CAP-13 • Dream 2026-09-25 (campaign phase 3)
**Surface:** `docs/foundry/sbom-gaps.md` (new), `scripts/sbom_gap_derive.py` (new), `tests/scripts/test_sbom_gap_derive.py` (new), `pixi.toml` (a read-only `sbom-gaps-check` task in `guild-tasks`).
**Given** the residual solve gaps (`conda-smithy`: py-rattler / conda co-solve; `python-agent-platform`: langflow vs pandas / onnxruntime) and the fat-only pins exist only in #1564's PR text
**When** this story lands
**Then** `docs/foundry/sbom-gaps.md` lists every feature declared in `pixi.toml` that is in neither the SBOM nor its layer environment (the residual solve gaps — `conda-smithy` and `python-agent-platform` today) and every package declared in `[feature.local-recipes.dependencies]` and in no SBOM feature, each with a disposition — `promote`, `won't-do` or `upstream` — a one-line reason and an owner station
**And** `sbom-gaps-check` reds when the derivation finds a row the file lacks (a feature outside the SBOM and layer, or a fat-only pin), or the file keeps a row the derivation no longer finds; rows whose fix is conda-forge packaging name Mason as owner and become Mason stories in a later mint

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild sbom-gaps-check` — expected: exit 0 on the landed list.
