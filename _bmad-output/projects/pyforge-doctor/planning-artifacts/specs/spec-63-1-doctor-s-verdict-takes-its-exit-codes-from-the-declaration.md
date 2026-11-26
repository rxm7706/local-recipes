---
title: '63.1: Doctor''s verdict takes its exit codes from the declaration'
type: 'fix'
created: '2026-11-25'
status: 'done'
story: 63-1-doctor-s-verdict-takes-its-exit-codes-from-the-declaration
spec: spec-pyforge-doctor
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/verdict.py'
  - 'src/shared/packages/pyforge-doctor/tests/meta/test_verdict_reads_the_exit_declaration.py'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-doctor.md
  - docs/reference/judgement-vocabulary.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-VOCAB-2026-09-14-8`. `verdict.py` spells `_EXIT_OK = 0`, `_EXIT_FAIL = 2` and `EXIT_SIGINT = 130` itself, so the declaration Story 137.1 adds would be one more copy, not the source.

**Approach:** Bind the three constants, and so `LATTICE.exit_by_member`, from `exit_code("doctor", ...)`; add a meta-test that fails when `LATTICE.exit_codes | {EXIT_SIGINT}` differs from `domain_codes("doctor")` or when the declaration stops declaring doctor's domain a narrowing of warden's.

Ledger key: `63-1-doctor-s-verdict-takes-its-exit-codes-from-the-declaration`.

### Living CAP citations

- spec-pyforge-steward:CAP-184 (each verdict module reads the declaration; no text change) and spec-pyforge-doctor's exit-code projection (verdict.py stays its sole owner; no text change); no AD moves.

## Boundaries & Constraints

**Always:**
- Show on the unchanged tree what each constant returns, and show the same values after the change; record both in the Spec Change Log.
- Append the surface reconcile to the memlog of each Spec that governs a moved file before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never change an exit code doctor returns.
- Never move the projection out of `verdict.py`.
- Never add a flag, a second declaration or an architecture decision; a change that would need one stops and is reported.

## Acceptance Criteria

**Given** doctor's `verdict.py` spells its three exit numbers
**When** it takes them from the `doctor` domain of `pyforge.core.exit_domains`
**Then** `exit_code_for` returns the same code for every finding list it returned before, and a meta-test fails when doctor's lattice domain differs from its declared domain
**And** `verdict.py` stays the sole owner of doctor's exit projection

- **AC1 — Doctor's verdict tests and the new meta-test hold.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/meta/test_verdict_reads_the_exit_declaration.py src/shared/packages/pyforge-doctor/tests/meta -q -k 'verdict'
  ```

- **AC2 — No exit number is spelled in the module's constants.** Expected: exit 1 (no line matches).

  ```bash
  grep -nE '^(_EXIT_OK|_EXIT_FAIL|EXIT_SIGINT) = [0-9]' src/shared/packages/pyforge-doctor/src/pyforge/doctor/verdict.py
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward:CAP-184 (each verdict module reads the declaration; no text change) and spec-pyforge-doctor's exit-code projection (verdict.py stays its sole owner; no text change); no AD moves.
- Dream: `docs/dreams/pyforge-doctor.md`, the 2026-11-25 entry (one declaration names every exit-code domain); operator ruling of 2026-11-25: "Unify for real".
- Epic: Epic 63, minted with this story.
- Ledger key: `63-1-doctor-s-verdict-takes-its-exit-codes-from-the-declaration`.
- Deferred-work row: `DW-VOCAB-2026-09-14-8`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."63"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry (one declaration names every exit-code domain) and the operator's ruling of the same date. Not implemented.
- 2026-11-25: before and after: `_EXIT_OK` 0, `_EXIT_FAIL` 2, `EXIT_SIGINT` 130 and `LATTICE.exit_by_member` `{fail: 2, warn: 0, ok: 0}`, equal. `tests/meta/test_public_contract.py`'s `_exit_items` read only literal constants, so it found none; it now also reads an `exit_code("<domain>", "<member>")` binding as the declared number, and `contract.md` lists `pyforge.core.exit_domains` in its import closure (ten core modules) and says how an exit constant is read. Both are in this story's surface by necessity and recorded here. AC1 exit 0, AC2 exit 1 (no line matches).
- 2026-11-25: closed. Implemented, independently reviewed against this spec (a read-only reviewer over the whole diff, every Acceptance Criterion run and read from its exit code), its findings applied; the full local `pr-preflight` gates the PR that lands it (branch `exit-code-vocabulary-2026-11-25`).
