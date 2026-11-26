---
title: '43.1: Mason''s exit codes are held to their declared domain'
type: 'fix'
created: '2026-11-26'
status: 'done'
story: 43-1-mason-s-exit-codes-are-held-to-their-declared-domain
spec: spec-pyforge-mason
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-mason/tests/meta/test_exit_codes_match_the_exit_declaration.py'
  - 'src/shared/packages/pyforge-mason/src/pyforge/mason/engines/gh.py'
  - 'src/shared/packages/pyforge-mason/src/pyforge/mason/models.py'
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Mason's exit codes are spelled in `exit_codes.py` and were left out of the one exit-code declaration. Two docstrings are stale: `engines/gh.py` says `ship_conda_forge` does not exist; `models.py` says nothing produces `ShipState.TERMINAL`.

**Approach:** Add a package-half meta-test that holds `exit_codes.py`'s names and numbers to the `mason` domain of `pyforge.core.exit_domains`. Correct the two docstrings. `exit_codes.py` is not edited: `test_public_contract.py` reads its literals.

Ledger key: `43-1-mason-s-exit-codes-are-held-to-their-declared-domain`.

### Living CAP citations

- spec-pyforge-steward:CAP-184 (amended 2026-11-26; the declaration this story binds to).
- spec-pyforge-steward:CAP-184 (the declaration; amended 2026-11-26) and spec-pyforge-mason CAP-5 (the CLI shell and output contract; realized, no text change).

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep every exit number the station returns today.

**Never:**
- Never change an exit number.
- Never edit the SKF-compiled station skill.

## Acceptance Criteria

**Given** mason's exit codes are declared only in mason, and two docstrings contradict `package.py`
**When** the meta-test is added and the two docstrings are corrected
**Then** the test fails when an `EXIT_*` name is added, removed or renumbered without the declaration, and pins the five numbers mason always used
**And** no exit number changes and no code path moves

- **AC1 — Mason's meta-test passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/meta/test_exit_codes_match_the_exit_declaration.py -q
  ```

- **AC2 — Mason's package half passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-mason pyforge-mason-test
  ```

</intent-contract>

## Review (2026-11-26)

Independent review by a fresh reviewer running `bmad-review`, given the diff and the stated intent and not the implementer's reasoning. Fourteen findings; all accepted and applied in the same change. For this story: the meta-test also holds any integer literal `cli.py` returns to the domain. Not covered by any test: the argparse `SystemExit` integer `cli.main` passes through.
