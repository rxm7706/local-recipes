---
title: "34.13: Atlas declares the brotli its nixpkgs store decodes"
type: 'fix'
created: '2026-10-25'
status: 'done'
baseline_revision: '529f06d52b6d6469b847519905c20bf528a60334'
review_loop_iteration: 1
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
  `brotli-python` differ, so the test gains a small conda-to-PyPI name map (`CONDA_TO_PYPI`: `brotli-python` → `brotli`). The library catalog
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
- 2026-10-25: implemented (`061bc2e4c2`); review round 1 FAIL on AC5 (the DW row was still open), fixed: the row is
  closed with this story's evidence; the map's direction (conda to PyPI) corrected in the Approach; the catalog and
  test comments no longer call the `brotli` conda package "the C library alone" (the package `pixi.toml` comment keeps
  that wording, so the manifest the lock hashes does not move). Moved to `in-review`.
- 2026-10-25: promoted to `done` in the landing PR (#2317) after its review round 1 fixes, with its ledger key, as
  multi-story landings do (Pages #2240; steward 105.1).

## Run results

2026-10-25, at `061bc2e4c2` and after the round-1 fixes:
- `pixi lock` re-derived only the three `pyforge-atlas[...]` source entries: each gains `brotli-python >=1.2`, their
  hashes change and the entries re-sort; no package re-solved (the reviewer parsed old and new `host_packages`).
- Clean clone (`git clone --shared` into `$HOME/.cache/pyforge-lockproof-34-13`, at `061bc2e4c2`):
  `pixi install -e pyforge-atlas --locked -v` exit 0, "the lock file is up-to-date" (AC2). The reviewer's run of the
  same command under the long scratchpad path failed in pixi-build-python (a panic on a 260-character path, for
  marshal, steward and the testing kit, never atlas), a path-length limit, not a stale lock.
- `pixi run -e pyforge-ci pyforge-deps-test`: 131 passed, 3 skipped; with `CONDA_TO_PYPI` broken, the two atlas
  parity tests and the new ratchet fail (AC3).
- `pixi run -e pyforge-guild llms-full-check`: exit 0, clean (AC4).
- `pixi run -e pyforge-atlas pyforge-atlas-test`: 3478 passed, 20 skipped; the quartet run 103 passed (AC5).
- `pixi run -e pyforge-guild lint-types`: exit 0.

## Review Triage Log

**Review 1 (independent, 2026-10-25): FAIL** — AC1, AC3, AC4 met; AC2 met in the lock, its clean-clone proof
unrecorded; AC5 not met. 1 must-fix, 2 should-fix, 4 nits.
- must-fix: `DW-atlas-34-5-1` still `open`. Fixed: closed with this story's evidence.
- should-fix: the ledger key is `backlog` and this spec `ready-for-dev`. Both are promoted to `done` in the landing PR,
  as multi-story landings do (this PR lands 34.13 and 33.2 under one merge subject).
- should-fix: record the clean-clone proof. Recorded above.
- nits: the map direction wording (fixed); "the C library alone" (fixed in the catalog and the test, kept in the
  package `pixi.toml` comment so the lock's manifest does not move); `_run_dependencies` silently overwrites if two
  conda names map to one PyPI name, and the CONDA_ONLY ratchet compares conda names against a PyPI-keyed set (latent,
  harmless with one entry; not changed); the ratchet test does not check the mapped PyPI name (the parity tests do).
