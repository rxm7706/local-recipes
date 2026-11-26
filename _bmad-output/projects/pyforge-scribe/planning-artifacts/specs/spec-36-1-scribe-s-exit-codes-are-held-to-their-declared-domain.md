---
title: '36.1: Scribe''s exit codes are held to their declared domain'
type: 'fix'
created: '2026-11-26'
status: 'done'
story: 36-1-scribe-s-exit-codes-are-held-to-their-declared-domain
spec: spec-pyforge-scribe
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-scribe/tests/meta/test_exit_codes_match_the_exit_declaration.py'
  - 'src/shared/packages/pyforge-scribe/src/pyforge/scribe/__init__.py'
  - 'src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py'
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md
  - docs/dreams/pyforge-scribe.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Scribe's exit codes were left out of the one exit-code declaration. `__init__.py` still calls compile and recall stubs; `compile.py` twice says seven surfaces.

**Approach:** Add a package-half meta-test that scans the package for `typer.Exit` codes and holds the set to the `scribe` domain. Correct the two docstrings, naming no count.

Ledger key: `36-1-scribe-s-exit-codes-are-held-to-their-declared-domain`.

### Living CAP citations

- spec-pyforge-steward:CAP-184 (amended 2026-11-26; the declaration this story binds to).
- spec-pyforge-steward:CAP-184 (the declaration; amended 2026-11-26); no capability text of spec-pyforge-scribe moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep every exit number the station returns today.

**Never:**
- Never change an exit number.
- Never edit the SKF-compiled station skill.

## Acceptance Criteria

**Given** scribe's exit codes are declared only in scribe, and two docstrings describe an earlier state of the code
**When** the meta-test is added and the two docstrings are corrected
**Then** the test fails when the set of codes scribe's `typer.Exit` calls carry differs from the `scribe` domain, or one carries a code that is not a literal
**And** no exit number changes and no code path moves

- **AC1 — Scribe's meta-test passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-scribe pytest src/shared/packages/pyforge-scribe/tests/meta/test_exit_codes_match_the_exit_declaration.py -q
  ```

- **AC2 — Scribe's package half passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-scribe pyforge-scribe-test
  ```

</intent-contract>

## Review (2026-11-26)

Independent review by a fresh reviewer running `bmad-review`, given the diff and the stated intent and not the implementer's reasoning. Fourteen findings; all accepted and applied in the same change. For this story: the scan also reads `SystemExit`, `sys.exit` and a bare imported `Exit`; the three further counts of surfaces in `compile.py` are reworded; the declaration's note no longer says only the catalog check exits 1 (Click exits 1 on an aborted run).
