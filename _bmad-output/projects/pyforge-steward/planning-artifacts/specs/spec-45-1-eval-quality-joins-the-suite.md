---
title: '45.1: eval-quality joins the suite'
type: 'feature'
created: '2026-09-18'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `bmad-eval-quality` packaged, enrolled and pinned like every other suite member

**Approach:** every consumer of the suite gets the 0.2.0-line binary that has `score`, and the fourteenth member costs one manifest line, not a parallel list.

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-45-1-eval-quality-joins-the-suite.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| `recipes/bmad-eval-quality/recipe.yaml` commit-pinned `0.2.0.dev0 @ 3172162fbdc7c4bb70ed11c1367dc3e433797535` (sha256 `a8b1ddfb…`), built through `conda-forge-… | `recipe-build` runs **Then** it is green and `eval-quality --version` prints `0.2.0`, `--help` lists `score`, and `comp… | it is green and `eval-quality --version` prints `0.2.0`, `--help` lists `score`, and `compile` on a shipped corpus contract exits 0 | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | enrolment is ONE line in `recipes/bmad-suite/suite-members.yaml`; `generate-bmad-suite` regenerates the metapackage run deps and CalVer (the same pass retires `bmad-method-wds-expansion` — deprecated… | n/a |
| And-clause from epics.md | when the story lands | `pixi.toml` pins `bmad-eval-quality = ">=0.2.0.dev0"`, `environment.yaml` is regenerated, `tests/packaging/test_bmad_suite_full_feature.py`'s baseline set, steward's `suite.py` `SuitePackageDef` + pi… | n/a |
| And-clause from epics.md | when the story lands | publishing to SelfExplainML (`anaconda upload`) is the operator's step and is not claimed by this story | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-bmad-eval-quality CAP-1`.
Surface: named on the story in epics.md
Ledger key: `45-1-eval-quality-joins-the-suite`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-45-1-eval-quality-joins-the-suite.md`.

## Epic excerpt

As a fleet operator,
I want `bmad-eval-quality` packaged, enrolled and pinned like every other suite member,
So that every consumer of the suite gets the 0.2.0-line binary that has `score`, and the fourteenth member costs one manifest line, not a parallel list.

**Type:** feature • **Effort:** M • **Deps:** none • **FR/AD:** spec-bmad-eval-quality CAP-1 • `packaging.md` • CFE Rule 1 + Rule 2 • overrides spec-bmad-suite-channel-product § Non-goals for this one member (operator 2026-09-05)
**Given** `recipes/bmad-eval-quality/recipe.yaml` commit-pinned `0.2.0.dev0 @ 3172162fbdc7c4bb70ed11c1367dc3e433797535` (sha256 `a8b1ddfb…`), built through `conda-forge-expert` in the `bmad-method` npm-CLI class **When** `recipe-build` runs **Then** it is green and `eval-quality --version` prints `0.2.0`, `--help` lists `score`, and `compile` on a shipped corpus contract exits 0
**And** enrolment is ONE line in `recipes/bmad-suite/suite-members.yaml`; `generate-bmad-suite` regenerates the metapackage run deps and CalVer (the same pass retires `bmad-method-wds-expansion` — deprecated in the 6.12.0 core module registry, absorbed by `bmad-ux` — so the suite stays at 13 active members)
**And** `pixi.toml` pins `bmad-eval-quality = ">=0.2.0.dev0"`, `environment.yaml` is regenerated, `tests/packaging/test_bmad_suite_full_feature.py`'s baseline set, steward's `suite.py` `SuitePackageDef` + pipeline-truth fixture, `install-matrix.md`, `install-class-playbook.md` and `library-llms-full.md` each carry the member; `llms-full-check` is green; the PR carries `maintenance`
**And** publishing to SelfExplainML (`anaconda upload`) is the operator's step and is not claimed by this story

