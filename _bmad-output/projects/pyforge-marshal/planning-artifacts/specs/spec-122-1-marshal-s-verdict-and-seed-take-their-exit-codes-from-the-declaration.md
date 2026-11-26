---
title: '122.1: Marshal''s verdict and seed take their exit codes from the declaration'
type: 'fix'
created: '2026-11-25'
status: 'done'
story: 122-1-marshal-s-verdict-and-seed-take-their-exit-codes-from-the-declaration
spec: spec-pyforge-marshal
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py'
  - 'src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/errors.py'
  - 'src/shared/packages/pyforge-marshal/tests/meta/test_verdict_reads_the_exit_declaration.py'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-marshal.md
  - docs/reference/judgement-vocabulary.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-VOCAB-2026-09-14-8`. `core/verdict.py` spells `_EXIT_BY_VERDICT` (six rungs to `0` through `4`), `EXIT_SIGINT = 130`, `EXIT_OK = 0` and `EXIT_USAGE = 2`, and `seed/errors.py` spells six `exit_code` class variables (`1` to `5` and `10`).

**Approach:** Build `_EXIT_BY_VERDICT` from `exit_code("marshal", verdict.value)`, bind `EXIT_SIGINT`, `EXIT_OK` and `EXIT_USAGE` from the same domain, and bind each seed leaf's `exit_code` from `marshal-seed`; add a meta-test that fails when `GUARDED_EXIT_CODES` differs from `domain_codes("marshal")` or `SEED_EXIT_CODES` from `domain_codes("marshal-seed")`.

Ledger key: `122-1-marshal-s-verdict-and-seed-take-their-exit-codes-from-the-declaration`.

### Living CAP citations

- spec-pyforge-steward:CAP-184 (each verdict module reads the declaration; no text change), spec-pyforge-marshal:CAP-304 (the public contract and its exit codes; no text change) and marshal AD-7 (the frozen exit domain; no AD moves).

## Boundaries & Constraints

**Always:**
- Show on the unchanged tree what each constant returns, and show the same values after the change; record both in the Spec Change Log.
- Append the surface reconcile to the memlog of each Spec that governs a moved file before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never change an exit code marshal returns.
- Never add a code to AD-7's frozen domain.
- Never add a flag, a second declaration or an architecture decision; a change that would need one stops and is reported.

## Acceptance Criteria

**Given** marshal's `core/verdict.py` and `seed/errors.py` spell their exit numbers
**When** they take them from the `marshal` and `marshal-seed` domains of `pyforge.core.exit_domains`
**Then** every verb exits with the same code for the same outcome as before, `GUARDED_EXIT_CODES` and `SEED_EXIT_CODES` are unchanged, and a meta-test fails when either differs from its declared domain
**And** `contract.md`'s exit codes do not move

- **AC1 — Marshal's verdict, seed and contract tests and the new meta-test hold.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests -q -k 'verdict or seed_errors or exit or public_contract'
  ```

- **AC2 — No exit number is spelled in the rung table or a seed leaf.** Expected: exit 1 (no line matches).

  ```bash
  grep -nE 'Verdict\.[A-Z_]+: [0-9]|exit_code: ClassVar\[int\] = [0-9]' src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/errors.py
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward:CAP-184 (each verdict module reads the declaration; no text change), spec-pyforge-marshal:CAP-304 (the public contract and its exit codes; no text change) and marshal AD-7 (the frozen exit domain; no AD moves).
- Dream: `docs/dreams/pyforge-marshal.md`, the 2026-11-25 entry (one declaration names every exit-code domain); operator ruling of 2026-11-25: "Unify for real".
- Epic: Epic 122, minted with this story.
- Ledger key: `122-1-marshal-s-verdict-and-seed-take-their-exit-codes-from-the-declaration`.
- Deferred-work row: `DW-VOCAB-2026-09-14-8`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."122"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry (one declaration names every exit-code domain) and the operator's ruling of the same date. Not implemented.
- 2026-11-25: before and after: the six rungs (clean 0, warn 0, unevaluable 1, scope-violation 2, gate-failed 3, error 4), `EXIT_OK` 0, `EXIT_USAGE` 2, SIGINT 130, `GUARDED_EXIT_CODES` and the six seed leaves (1, 2, 3, 4, 5, 10), equal; `contract.md` did not move. `seed/errors.py` imports the helper as `_declared_exit_code` so the class attribute `exit_code` is not shadowed. AC1 exit 0 (1,314 passed), AC2 exit 1 (no line matches).
- 2026-11-25: closed. Implemented, independently reviewed against this spec (a read-only reviewer over the whole diff, every Acceptance Criterion run and read from its exit code), its findings applied; the full local `pr-preflight` gates the PR that lands it (branch `exit-code-vocabulary-2026-11-25`).
