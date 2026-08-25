---
title: wired-or-not is class-correct
type: feature
created: '2026-08-25'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
baseline_revision: 5991574f8bfc6c91a10eb39ae4489aca44ab1caa
---

<intent-contract>

## Intent

**Problem:** Pipeline-truth's `wired-or-not` column still scores several non-module suite pieces with a skills/`_bmad` census boolean that only `--module` targets can honestly satisfy, so a fresh clone can look "wired" for the wrong reason (and a template-into-this-repo must never look wired).

**Approach:** Extend the existing steward `suite pipeline-truth` duty so each of the six non-module pieces is judged by its install-class predicate from `install-class-playbook.md` (installer tree / runner home / own installer / plugin path / VS Code extension / scaffold N/A), named by class in the report.

## Acceptance Criteria

- Given the pipeline-truth `wired-or-not` column, then each of the six is judged by its class predicate, not a boolean only `--module` targets can satisfy.
- Given template-into-this-repo, then the report never claims wired.
- Given a fresh-clone-shaped tree, then the report names each of the six by class.

## Boundaries & Constraints

**Always:** Epic 15 stays done — this extends 15.1's report, it is not 15.5+. Wrap, don't absorb. Dual-path remains. Template is scaffold-only forever.

**Block If:** A change would reopen CAP-3's five (`bmb`, `tea`, `cis`, `utility-skills`, `manticore`) or the WDS skip.

**Never:** `steward provision --module skf`. Implement 31.3 (fresh-clone proof). Put `pyforge.*` under `src/platform/`. Run `scripts/bmad-switch`. Replace Epic 15's channel pipeline / advance command.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Six named by class | live `probe_wired` / report for the six | each row carries `install_class` installer-tree, runner-home, own-installer, plugin-path, vscode-extension, scaffold-n/a | fail-open probe never raises |
| Template never wired | template pkg even with fake `_bmad`/skills census hits | value is `n/a`, never `wired` | test fails if wired |
| Loop not module-boolean | loop skill prefix present, no `scripts/bmad-loop-worktree` | not `wired`; class `runner-home` | missing until provisionable |
| Labs not module-boolean | labs skill names present, no playbook/matrix | not `wired`; class `plugin-path` | documented only when playbook/matrix cites the plugin path |
| Dashboard not docs census | `docs/dashboard` exists, no pixi install task | not `wired`; class `vscode-extension` | runnable when the named pixi task exists |
| CAP-3 five unchanged | module packages | still census `wired`/`unwired`; WDS still `skip` | test fails if module set or WDS skip changes |
| Baseline replay | `--baseline` | 2026-08-22 recorded wired column unchanged | no network |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/suite.py` — `SuitePackageDef.install_class`, `probe_wired` class dispatch, `PackageTruth.install_class`, text/JSON report names class. Keep `--baseline` replay.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-install-class-wiring/install-class-playbook.md` — CAP-2 predicates (read-only).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py` — `_SUPPORTED_MODULES` / `_SKIPPED_MODULES` read-only.
- `src/shared/packages/pyforge-steward/tests/unit/test_suite_pipeline_truth.py` — 15.1 baseline still green.
- `src/shared/packages/pyforge-steward/tests/unit/test_suite_wired_class_predicates.py` — CAP-2: template never wired; non-modules not scored by module-only census.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/suite.py` -- add per-class wired predicates and name `install_class` on the report -- CAP-2
- `src/shared/packages/pyforge-steward/tests/unit/test_suite_wired_class_predicates.py` -- lock template-never-wired and module-boolean refusal -- tests fail on class-incorrect scoring
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-31-2-wired-or-not-is-class-correct.md` -- this spec, tracked in the implementation PR

**Acceptance Criteria:**
- Given the six, when pipeline-truth runs live, then each is named by class.
- Given template-into-this-repo, when wired is probed, then it is never `wired`.
- Given this story, when the diff is reviewed, then no `pyforge.*` was added under `src/platform/` and Epic 15 module wiring is untouched.

## Spec Change Log

## Review Triage Log

### 2026-08-25 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 1, low 0)
- defer: 0
- reject: 3: (low 3)
- addressed_findings:
  - `[medium]` `[patch]` Tightened dashboard pixi-task match to `[feature.bmad-ui.tasks.<name>]` so a substring of another task cannot count as runnable

Rejected (noise): requiring `--baseline` live probes to also emit `present`/`provisionable` (recorded 2026-08-22 column is the CAP-1 fixture); splitting mybmad into a seventh playbook class (playbook keeps dashboards on one row; both packages share `vscode-extension`); adding `pyforge.*` under `src/platform/`.

## Auto Run Result

Status: done

Summary: Pipeline-truth `wired-or-not` now names each of the six non-module pieces by install class and judges them with class predicates. Template-into-this-repo is always `n/a` (never `wired`). Loop/labs/dashboards are no longer scored by a skills/`docs/dashboard` module census. Epic 15 CAP-3 five and WDS skip unchanged. No `pyforge.*` under `src/platform/`.

Files:
- `suite.py` — `install_class` on roster + `probe_wired` class dispatch + report field
- `test_suite_wired_class_predicates.py` — CAP-2 conformance
- `spec-31-2-wired-or-not-is-class-correct.md` — tracked story spec

Review: 1 medium patch applied; deferred 0; rejected 3 (low). Follow-up review recommended: false (patched high=0; score 1×3=3 < 5).

Verification: 27 passed (`test_suite_wired_class_predicates.py` + `test_suite_pipeline_truth.py`); 31.1 playbook tests previously 30-passed with pipeline-truth in the same session.

Residual: live HTTP stages still the 15.1 deferred probe gap; `--baseline` still replays the 2026-08-22 wired strings while naming `install_class`.


## Design Notes

Class tokens match the playbook's rightmost column, not `_SUPPORTED_MODULES`:

- method → `installer-tree` (`_bmad/core` + `bmm`)
- loop → `runner-home` (`scripts/bmad-loop-worktree` present ⇒ provisionable)
- skf → `own-installer` (`_bmad/skf` or `skf-*` skills)
- labs → `plugin-path` (playbook or install-matrix cites `bmad-labs/skills`; never skill-census `wired`)
- dashboards → `vscode-extension` (pixi task `bmad-dashboard-install` / `mybmad`)
- template → `scaffold-n/a` (always `n/a`)

`--baseline` still replays the 2026-08-22 recorded column; class naming is the live probe + report field.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_suite_wired_class_predicates.py src/shared/packages/pyforge-steward/tests/unit/test_suite_pipeline_truth.py src/shared/packages/pyforge-steward/tests/unit/test_provision_install_class_playbook.py -q` -- expected: all passed
- `git grep -n 'pyforge\.' -- src/platform/` on this story's diff -- expected: no new `pyforge.*` under `src/platform/`
