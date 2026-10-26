---
title: "34.13: Atlas declares the brotli its nixpkgs store decodes"
type: 'fix'
created: '2026-10-25'
status: 'ready-for-dev'
baseline_revision: '529f06d52b6d6469b847519905c20bf528a60334'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/tier3_sources.py
  - src/shared/packages/pyforge-atlas/pyproject.toml
  - src/shared/packages/pyforge-atlas/pixi.toml
  - tests/packaging/test_dependency_completeness.py
  - .claude/memory/feedback/a-cached-local-pixi-false-greens-a-lock-whose-path-dependenc.md
deferred: []
---

<intent-contract>

## Intent

**Problem:** pyforge-atlas imports a module it does not declare. Line numbers are at `529f06d52b`.

- The nixpkgs Tier-3 index is `packages.json.br`. `datasets/tier3_sources.py` decodes it through
  `_brotli_decompress` (`importlib.import_module("brotli")` inside a try/except, :93-101), and
  `NixpkgsPackagesDataset._frame` (:378-380) checks `find_spec("brotli")` and raises `DatasetError` when it is absent,
  which the store's AD-13 fallback reads as `stale`.
- The atlas env has the module only because conda-forge's `urllib3` depends on `brotli-python` (`pixi.lock`:
  `brotli-python 1.2.0` in the pyforge-atlas env on linux-64, osx-arm64 and win-64). PyPI's `urllib3` makes brotli an
  extra, so a pip install of the wheel has none (`DW-atlas-34-5-1`, Story 34.5 review round 1 S4, round 2 nit 3).
- The import is dynamic, so the AST scan in `tests/packaging/test_dependency_completeness.py` does not see it, and
  `pyforge-deps-test` passes today.

**Approach:**
- Declare it in both manifests at the floor the env already resolves, with one string: `"brotli>=1.2"` in
  `pyproject.toml` `[project].dependencies` (PyPI distribution `Brotli`) and `brotli-python = ">=1.2"` in the package
  `pixi.toml` `[package.run-dependencies]`, each with the comment the `filelock` and `numpy` lines carry.
- Re-lock so every pyforge-atlas source entry in `pixi.lock` records `brotli-python >=1.2`, and prove it in a clean
  clone with a fresh `pixi install --locked` (the 2026-10-25 trap: a cached local pixi reads a stale lock as current).
- The dependency-parity test compares PEP 503 names between the two manifests; PyPI `brotli` and conda
  `brotli-python` differ, so the test gains a small PyPI-to-conda name map. The library catalog
  (`docs/reference/library-llms-full.md`) lists the package, or `llms-full-check` reds `undocumented-dep`.
- A `fix` under CAP-64 (Story 34.5's source): no CAP, no flag (`spec-feature-flag-governance` Q1). No new package
  enters the env, and the import stays guarded.

Ledger key: `34-13-atlas-declares-the-brotli-its-nixpkgs-store-decodes`. Type / Effort / Deps: fix / S / —.

## Acceptance Criteria

- **AC1 — Both manifests.** `pyproject.toml` declares `"brotli>=1.2"` and the package `pixi.toml` declares
  `brotli-python = ">=1.2"`.
- **AC2 — The lock.** Every `pyforge-atlas` source entry in `pixi.lock` records `brotli-python >=1.2` among its run
  dependencies, and in a clean clone a fresh `pixi install -e pyforge-atlas --locked` succeeds (no "lock file not
  up-to-date"); so does every other environment that carries the pyforge-atlas package.
- **AC3 — Parity.** `pixi run -e pyforge-ci pyforge-deps-test` passes, and fails when the name map is removed (the
  test would read `brotli` in the pyproject and `brotli-python` in conda as two different packages).
- **AC4 — Catalog.** `pixi run -e pyforge-guild llms-full-check` exits 0 with a catalog bullet for brotli.
- **AC5 — No behaviour change.** `tier3_sources.py` is unchanged; `pixi run -e pyforge-atlas pyforge-atlas-test`
  passes; `DW-atlas-34-5-1` is closed with this story's evidence.

## Boundaries & Constraints

**Always:** the same `>=1.2` string in both manifests and the lock; a clean-clone `--locked` proof before the push.

**Never:** no new package in any env, no change to the guarded import, no `pixi update` of other packages.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-atlas` CAP-64 (Story 34.5's nixpkgs source). No CAP is minted.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-25 (the nixpkgs store decodes brotli by luck).
- Epic 34 (done; reopened by this story under doctor Story 41.5's rule). Ledger key above. Deps: —.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (the station's `verify_commands`).
- `pixi run -e pyforge-ci pyforge-deps-test` — expected: pass (AC3).
- `pixi run -e pyforge-guild llms-full-check` — expected: exit 0 (AC4).

**Run before the push:** a `git clone --shared` of the branch into the scratchpad, then
`pixi install -e pyforge-atlas --locked -v` — expected: exit 0 (AC2).

## Spec Change Log

- 2026-10-25: drafted from the Dream entry of 2026-10-25 and `DW-atlas-34-5-1`, at the operator's ruling
  "brotli + brotli-python (Recommended)".
