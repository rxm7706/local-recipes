---
title: '53.3: Atlas''s comments cite the test layout and the specs that exist'
type: 'fix'
created: '2026-11-25'
status: 'in-review'
story: 53-3-atlas-s-comments-cite-the-test-layout-and-the-specs-that-exist
spec: spec-pyforge-atlas
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-atlas/**'
  - '_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md'
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-atlas.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-atlas-46-1-1`. Comments and docstrings under `src/shared/packages/pyforge-atlas/` name test paths that moved under `tests/unit/` on 2026-09-07 and `spec § n` sections of `docs/specs/cfe-atlas-datapipeline-kedro-migration.md`, now under `archive/`. On 2026-11-25, `git grep -c "tests/catalog\|tests/parity\|spec §"` counts 89 hits in 50 files. The row was held because the touched-module coverage floor counts a changed module.

**Approach:** Re-count, then fix each citation: an old test path becomes the path the test has today (verified with `git ls-files`; a test that no longer exists loses its citation), and a `spec § n` citation names the archived file by its `archive/` path or, where the Spec's capability is known, the capability. The coverage gate does not count a file whose AST is unchanged, so a `#` comment is free and a docstring is not. Change every `#` comment. Change a docstring only in a module the gate already passes after the change: run `scripts/coverage_gates_ci.py` for atlas in `-e pyforge-atlas` after the sweep, and for a module it names below its floor either add the tests that lift it, where that is small, or revert that module's docstring change and list the module. Config (`conf/`) and `tools/` files are not Python modules and are all fixed.

Ledger key: `53-3-atlas-s-comments-cite-the-test-layout-and-the-specs-that-exist`.

### Living CAP citations

- spec-pyforge-atlas CAP-73 (the package says what the tree has; realized, no text change); reads spec-pyforge-steward:CAP-175 (the touched-module coverage floor counts an AST change; no text change); no AD moves.

## Boundaries & Constraints

**Always:**
- Reproduce what the row reports on the unchanged tree before changing it, and record the reproduction in the Spec Change Log.
- Append the surface reconcile to the memlog of each Spec that governs a moved file before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never change a statement of code.
- Never lower a coverage floor or except a module from the gate.
- Never add a flag, a capability or an architecture decision; a fix that would need one stops and is reported.

## Acceptance Criteria

**Given** `DW-atlas-46-1-1` reports comments and docstrings in the atlas package that cite the pre-`tests/unit/` test layout and section numbers of an archived intake spec
**When** every `#` comment and config citation is corrected, and each docstring citation is corrected wherever the touched-module coverage floor still holds
**Then** each remaining test-path citation under the package resolves with `git ls-files`, each spec citation names a file that exists, and atlas's coverage gate passes on the branch
**And** no statement of code changes (a module's AST differs only in docstrings), the modules whose docstrings were left are listed with their coverage, and the row reads resolved or is replaced by one row naming exactly those modules

- **AC1 — Every cited test path resolves.** Expected: exit 0.

  ```bash
  python3 -c "import re,subprocess,sys; tracked=set(subprocess.run(['git','ls-files','src/shared/packages/pyforge-atlas'],capture_output=True,text=True,check=True).stdout.split()); hits=subprocess.run(['git','grep','-n','-o','-E','tests/[A-Za-z0-9_/.-]+\\.py','--','src/shared/packages/pyforge-atlas/src','src/shared/packages/pyforge-atlas/conf','src/shared/packages/pyforge-atlas/tools'],capture_output=True,text=True).stdout.splitlines(); bad=[h for h in hits if 'src/shared/packages/pyforge-atlas/'+h.rsplit(':',1)[1] not in tracked]; print(len(hits), len(bad)); [print(b) for b in bad[:40]]; sys.exit(1 if bad else 0)"
  ```

- **AC2 — Atlas's coverage gate holds.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-atlas pyforge-atlas-coverage-gate
  ```

- **AC3 — Atlas's package suite holds.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-atlas pyforge-atlas-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-atlas CAP-73 (the package says what the tree has; realized, no text change); reads spec-pyforge-steward:CAP-175 (the touched-module coverage floor counts an AST change; no text change); no AD moves.
- Dream: `docs/dreams/pyforge-atlas.md`, the 2026-11-25 entry (the rows a lapsed blocker held close); operator ruling of 2026-11-25: "All 22 rows".
- Epic: Epic 53, minted with this story.
- Ledger key: `53-3-atlas-s-comments-cite-the-test-layout-and-the-specs-that-exist`.
- Deferred-work row: `DW-atlas-46-1-1`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."53"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry (the rows a lapsed blocker held close) and the operator's ruling of the same date. Not implemented.

- 2026-11-25: reproduction on the unchanged tree: `git grep -c "tests/catalog\|tests/parity\|spec §"` counts 89 hits in 50 files under the package; AC1 exits 1 with 38 of 48 cited test paths unresolved. A wider scan (every `tests/<x>` citation whose first segment is not in today's layout) finds 98 across `src/`, `conf/`, `tools/` and `tests/`.
- 2026-11-25: finding: the gate's fingerprint (`scripts/coverage_gate.py` `ast_fingerprint`) drops every docstring as well as every import, so a docstring-only edit is not a touched module. Every docstring citation was therefore changed; no module's docstrings were left, and no module is listed.
- 2026-11-25: change: 71 files (3 `conf/base/*.yml`, 33 under `src/pyforge/atlas/`, 33 test modules, `tests/unit/parity/PARITY_NOTES.md`, `tools/lasuite_bringup.py`), 135 citations. Each old test path now names the path `git ls-files` has (all under `tests/unit/` except `tests/integration/dashboard/conftest.py` and `test_dashboard_e2e.py`); the six cited `::test` functions exist. Each `spec § n` names `archive/docs/specs/cfe-atlas-datapipeline-kedro-migration.md` (sections 3.3, 3.4, 4.5, 5.1, 5.2, 5.4, 5.5, 5.9, 9, 11, 12, 13.1 and FR-3, FR-20, FR-21 are in the file), and `docs/specs/trendshift-conda-forge.md` gains its `archive/` prefix. Two comments cited the repository root's `tests/packaging/test_dependency_completeness.py`, which exists but not under the package; they now name the test and the root folder in words, so AC1's package-relative check holds.
- 2026-11-25: left, because each is a string literal and changing it changes a statement: `parity/legacy_surface.py` lines 64 and 74 (`scope_note=` values holding `spec §3.3`), `tests/unit/catalog/test_catalog_resolution.py` line 59 (an assertion message holding `tests/catalog/conftest.py`), `tests/unit/orchestration/conftest.py` line 96 and `tests/unit/test_admission.py` line 354 (the generated stub's text holding `tests/orchestration/conftest.py`). After the sweep the row's grep counts 3 hits in 2 files, all among these.
- 2026-11-25: no statement changed: for all 71 files' Python modules the AST with docstrings stripped equals `git show HEAD:<file>`, except the three files Story 53.2 changes (`observability.py` and its two test modules). Working-tree coverage gate over the AST-changed files: one touched module, `pyforge.atlas.observability` (Story 53.2's), exit 0. `lint-types` for pyforge-atlas: ruff, ruff-format and mypy ok.
- 2026-11-25: AC1 exit 0 (46 cited paths, 0 unresolved); AC2 exit 0 (as written it diffs `origin/main...HEAD` and sees no uncommitted file, so the working-tree run above is the verdict that counts until the commit); AC3 exit 0 (2995 passed, 27 skipped; 53 passed, 5 skipped). `pyforge-atlas-live-test` exit 0 (341, 164 and 103 passed).
