---
title: '30.1: Warden''s verdict takes its exit codes from the declaration'
type: 'fix'
created: '2026-11-25'
status: 'ready-for-dev'
story: 30-1-warden-s-verdict-takes-its-exit-codes-from-the-declaration
spec: spec-pyforge-warden
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-warden/src/pyforge/warden/verdict.py'
  - 'src/shared/packages/pyforge-warden/tests/meta/test_verdict_reads_the_exit_declaration.py'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-warden.md
  - docs/reference/judgement-vocabulary.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-VOCAB-2026-09-14-8`. `verdict.py` spells `_EXIT_BY_STATUS` (seven rungs to `0`, `1` and `2`), `_EXIT_WARN_AS_ERROR = 1`, `EXIT_SIGINT = 130` and the `allow_empty` downgrade's `0` itself.

**Approach:** Build `_EXIT_BY_STATUS` from `exit_code("warden", status.value)` over the seven rungs, and bind the warn-as-error, SIGINT and allow-empty codes from the same domain; add a meta-test that fails when `LATTICE.exit_codes | {EXIT_SIGINT}` differs from `domain_codes("warden")`.

Ledger key: `30-1-warden-s-verdict-takes-its-exit-codes-from-the-declaration`.

### Living CAP citations

- spec-pyforge-steward:CAP-184 (each verdict module reads the declaration; no text change) and spec-pyforge-warden's verdict lattice (verdict.py stays its sole owner; no text change); no AD moves.

## Boundaries & Constraints

**Always:**
- Show on the unchanged tree what each constant returns, and show the same values after the change; record both in the Spec Change Log.
- Append the surface reconcile to the memlog of each Spec that governs a moved file before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never change an exit code warden returns.
- Never move the projection out of `verdict.py`.
- Never add a flag, a second declaration or an architecture decision; a change that would need one stops and is reported.

## Acceptance Criteria

**Given** warden's `verdict.py` spells its exit numbers
**When** it takes them from the `warden` domain of `pyforge.core.exit_domains`
**Then** `exit_code_for` returns the same code for every input it returned before, including `--warn-is-error` and `--allow-empty`, and a meta-test fails when warden's lattice domain differs from its declared domain
**And** `verdict.py` stays the sole owner of warden's exit projection

- **AC1 — Warden's verdict tests and the new meta-test hold.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -k 'verdict or exit'
  ```

- **AC2 — No exit number is spelled in the rung table.** Expected: exit 1 (no line matches).

  ```bash
  grep -nE 'Status\.[A-Z_]+: [0-9]' src/shared/packages/pyforge-warden/src/pyforge/warden/verdict.py
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward:CAP-184 (each verdict module reads the declaration; no text change) and spec-pyforge-warden's verdict lattice (verdict.py stays its sole owner; no text change); no AD moves.
- Dream: `docs/dreams/pyforge-warden.md`, the 2026-11-25 entry (one declaration names every exit-code domain); operator ruling of 2026-11-25: "Unify for real".
- Epic: Epic 30, minted with this story.
- Ledger key: `30-1-warden-s-verdict-takes-its-exit-codes-from-the-declaration`.
- Deferred-work row: `DW-VOCAB-2026-09-14-8`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."30"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry (one declaration names every exit-code domain) and the operator's ruling of the same date. Not implemented.
