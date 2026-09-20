---
title: '66.1: Lint and types gate the ten packages, locally and on the runners alike'
type: 'feature'
created: '2026-09-20'
status: 'done'
baseline_revision: '5e70a51cc1'
final_revision: 'pending — the merge commit of PR #1553'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - .github/workflows/platform-ci.yml
  - scripts/pixi_version_registry.py
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** As a contributor to any `pyforge-*` package, I want `ruff`, `ruff format --check` and `mypy` to run over all ten packages from one pixi task, in CI and in `pr-preflight`, So that a lint or type regression reds the PR the same way locally and on the runners, instead of not at all (verified 2026-09-20: no `[tool.ruff]` / `[tool.mypy]` in any of the ten `pyproject.toml` files, no task, no lane — only `src/platform` is gated).

**Approach:** per-package `[tool.ruff]` / `[tool.mypy]` on py314 targets (strict for `pyforge-core`); `ruff`, `ruff-format`, `mypy`, `target-version-check` tasks in `[feature.guild-tasks.tasks]`; `scripts/target_version_check.py` as a registry check shaped like `pixi_version_registry.py`; one CI lane and one `pr-preflight` leg calling exactly those tasks.

Ledger key: `66-1-lint-and-types-gate-the-ten-packages-locally-and-on-the-runners-alike`.
Ledger status (do not edit the ledger): `done`.

### Living CAP citations

- `spec-pyforge-steward` CAP-153.

## Acceptance Criteria

- Given the ten packages have no lint or type gate anywhere, When this story lands, Then `pixi run -e pyforge-guild ruff` / `ruff-format` / `mypy` exit 0 on `main`.
- The CI lane and the `pr-preflight` leg invoke exactly those tasks; a deliberately planted violation in any package reds both.
- `target-version-check` reds a package whose `target-version` / `python_version` drifts from the interpreter pinned in `pixi.toml`.
- `src/platform`'s `platform-ci` lane is unchanged.

## Boundaries & Constraints

- `src/platform`'s `platform-ci` lane and `platform-ci-local` stay untouched; this story is about the ten `pyforge-*` packages and the repo's hooks.
- The CI lane and the `pr-preflight` leg call the SAME pixi tasks — never a second invocation that can drift.
- Only `pyforge-guild` exists at runtime (CAP-152): every new task lives in `guild-tasks` and runs from `-e pyforge-guild`.
- `pixi.toml` is shared surface: regenerate `environment.yaml`, run `pyforge-station-tests` before pushing.

## Surface

- `src/shared/packages/pyforge-*/pyproject.toml`, `pixi.toml`, `scripts/target_version_check.py`, `.github/workflows/` (one lane), `tests/scripts/`, `docs/reference/library-llms-full.md` if a pin moves.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary checkout's copy of this file).

**Manual checks:**
- Plant one ruff violation and one mypy error in two different packages; `pr-preflight` and the CI lane both red, naming the file.
- `pixi run -e pyforge-guild pyforge-station-tests` green on the final lock; `environment.yaml` in sync.

</intent-contract>

## Review Triage Log

### 2026-09-20 — hand-driven pass (operator: "we implement and do this now")
  - `[high]` `[patch]` No `[tool.ruff]` / `[tool.mypy]` in any of the ten packages, no task, no lane. Each package gained both blocks (py314, line-length 120, E/F/W/I with E501 off; mypy 3.14 with `explicit_package_bases` for the `pyforge` namespace and `import-untyped` disabled for the un-`py.typed` siblings); `pyforge-core` strict with its eight findings fixed; the other nine baselined per module, per error code (`[[tool.mypy.overrides]]`, never `ignore_errors`) — atlas 22, doctor 10, herald 11, marshal 42, mason 4, scribe 2, steward 11, testing-kit 1, warden 7 modules.
  - `[high]` `[patch]` 100 real ruff findings fixed: two genuinely undefined names (`_DeployRun` in marshal `cli/land.py`, now a `TYPE_CHECKING` import), four byte-identical duplicate scribe tests, unused variables/imports, `== True` comparisons, an ambiguous `l`; 516 import blocks sorted; 1030 files `ruff format`ted.
  - `[medium]` `[patch]` mypy run by package NAME (`-p pyforge.<station>` over `mypy_path = src`), never `mypy src`: each station is also an editable install on `sys.path`, and crawling the directory made mypy see every module twice.
  - `[medium]` `[patch]` `scripts/lint_types.py` is the one runner; `guild-tasks` `ruff` / `ruff-format` / `ruff-format-fix` / `mypy` / `target-version-check` / `lint-types`; `.github/workflows/lint-types.yml` and `pr-preflight`'s first leg both run `pixi run --frozen -e pyforge-guild lint-types` verbatim; the workflow's setup-pixi pin registered in `pixi_version_registry.py` the day it was added.

  - `[high]` `[patch]` Found by the pre-push hook's first live run: the touched-module coverage floor counted every reformatted file as touched (atlas: 16 modules under 80% from formatting alone). `pyforge.marshal.coverage_gate.ast_fingerprint` (imports and docstrings dropped from the AST dump) + `format_only_paths`; `scripts/coverage_gates_ci.py` drops files whose fingerprint equals the merge-base's before naming touched modules — the floor now measures code that changed, never the formatter. All eight station gates pass.

## Auto Run Result

**Status:** done
**Summary:** the ten `pyforge-*` packages are lint- and type-gated from one task set that CI and `pr-preflight` call verbatim; `src/platform`'s lane untouched.
**Verification:** `pixi run --frozen -e pyforge-guild lint-types` exit 0 (ruff ×10 ok, ruff-format ×10 ok, mypy ×10 ok, target-version ok, precommit-config ok); `pyforge-station-tests` on the reformatted tree — see the PR body; `tests/scripts/test_lint_types_gate.py` 11 passed; `pixi-version-check` clean (19 sites).
**Files changed:** see the Surface, plus every `.py` under the ten packages' `src/` and `tests/` (format + import sort) and the hand fixes named in the triage log.
**Residual risks:** a `.py` whose only change is an import is not measured by the floor (imports carry no behaviour); the mypy baseline is a ratchet — 110 module entries to tighten as modules are touched; E501 is off in favour of `ruff format`'s 120-column code width (290 legacy long strings/comments).
**Follow-up review recommendation:** false
