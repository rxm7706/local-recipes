---
title: '53.3: Atlas''s comments cite the test layout and the specs that exist'
type: 'fix'
created: '2026-11-25'
status: 'ready-for-dev'
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
