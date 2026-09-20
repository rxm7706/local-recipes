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

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `6d092e571c` (2026-09-05, "suite(pin): bmad-eval-quality >=0.2.0.dev0 in the unix target tables, WDS pin dropped; Story 45.1 done"). Ledger row `45-1-eval-quality-joins-the-suite: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/.memlog.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pixi-candidate-currency/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-install-class-wiring/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-install-class-wiring/install-class-playbook.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-mcp-era-isolation/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-platform-image-one-pixi-env/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `docs/dreams/bmad-eval-quality.md`, `docs/reference/library-llms-full.md` (+6 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
