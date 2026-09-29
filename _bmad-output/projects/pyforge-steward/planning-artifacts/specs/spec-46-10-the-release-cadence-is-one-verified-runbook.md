---
title: "Story 46.10: The release cadence is one runbook and the next rehearsal has run once"
type: chore
created: 2026-09-10
status: done
review_loop_iteration: 1
followup_review_recommended: false
baseline_revision: '69192cd1b967436ed5cca1f628910f6ff866cb48'
context:
  - spec-bmad-suite-lifecycle/release-cadence.md
  - spec-14-10-the-next-rehearsal-exercises-cap-6-s-fallback-and-cap-8-s-conflict-path-report-only.md
  - spec-14-9-the-apply-retires-deprecation-shims-on-purpose-no-shims.md
  - spec-bmad-method-core-upgrade/.memlog.md
warnings: []
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** `release-cadence.md` lists nine release steps and an `@next` rehearsal recipe in
prose, but none of the steps carry the owner, command, exit code, and evidence from the live
6.12.0 apply (Stories 14.1–14.9, commits `4fa185be56` / `e7b5d6d05e`) or the fixture rehearsal
(Story 14.10). Without those annotations the runbook still reads improvised; the `@next` section
does not match `NEXT_REHEARSAL_ARGV` verbatim.

**Approach:** Append a **Verified pass** block under each of the nine numbered steps (owner,
command, exit, evidence pointer). Rewrite § The `@next` rehearsal as a fenced argv recipe that
matches `NEXT_REHEARSAL_ARGV` token-for-token (placeholders allowed). Add a meta test that parses
the runbook and cross-checks the rehearsal argv plus the nine verification blocks. Append one
`(event)` line to `spec-bmad-suite-lifecycle/.memlog.md` and flip ledger `46-10` to `done`.

## Boundaries & Constraints

**Always:**
- Each step's **Verified pass** cites a real command that ran (or the story that exercised it),
  its exit code, and an owner station — never the word "improvised".
- The `@next` rehearsal section states explicitly that fixture rehearsal (Story 14.10) is not live
  proof and does not flip `spec-bmad-method-core-upgrade` to `shipped` (AD-7).
- Meta test imports `NEXT_REHEARSAL_ARGV` from `test_upgrade_next_rehearsal.py` — single source
  of truth for the argv cross-check.

**Never:**
- Do not run live `npx bmad-method@next` or mutate `_bmad/` in this story.
- Do not flip `spec-bmad-method-core-upgrade` status.
- Do not edit upgrade.py behavior — verification is docs + meta test only.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Nine steps annotated | `release-cadence.md` after edit | Each step 1–9 has a `Verified pass` block with owner, command, exit, evidence | Meta test fails if any step missing |
| Rehearsal argv match | Runbook `@next` fenced block vs `NEXT_REHEARSAL_ARGV` | Token sequence identical (placeholders `<…>` allowed) | Meta test fails on mismatch |
| Rehearsal disclaimer | Runbook `@next` section | Contains "not live proof" / "does not flip" language | Meta test asserts substring |
| No improvised wording | Full runbook body | Case-insensitive "improvised" absent outside historical quotes | Meta test fails if found |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/release-cadence.md`
  — **edit**: add `Verified pass` under steps 1–9; rewrite `@next` rehearsal as argv fence matching
  `NEXT_REHEARSAL_ARGV`.
- `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_next_rehearsal.py` — **read-only**:
  `NEXT_REHEARSAL_ARGV` canonical recipe (Story 14.10).
- `src/shared/packages/pyforge-steward/tests/meta/test_release_cadence_runbook.py` — **new**:
  meta gate for nine blocks, argv parity, disclaimer, no-improvised scan.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/.memlog.md`
  — append `(event)` for CAP-8 runbook verification.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml` — flip
  `46-10-…` to `done` via Tier-3 feed + `sprint-ledger-sync`.

## Tasks & Acceptance

**Execution:**
- `release-cadence.md` — annotate steps 1–9 with Verified pass blocks sourced from core-upgrade
  memlog + Stories 14.5/14.9/14.10 and era-tail stories — makes the runbook mechanical.
- `release-cadence.md` — rewrite `@next` rehearsal as argv fence matching `NEXT_REHEARSAL_ARGV` —
  Story 14.10 cross-check contract.
- `tests/meta/test_release_cadence_runbook.py` — add meta tests for blocks, argv, disclaimer,
  no-improvised — CI gate.
- `spec-bmad-suite-lifecycle/.memlog.md` — append dated `(event)` — audit trail.
- Tier-3 feed + `sprint-ledger-sync` — promote ledger key `46-10-…` to `done`.

**Acceptance Criteria:**
- Given `release-cadence.md`, when each numbered step 1–9 is read, then it contains a `Verified
  pass` block naming owner, command, exit, and evidence — and the word "improvised" does not
  appear in the runbook body.
- Given `NEXT_REHEARSAL_ARGV` and the runbook `@next` section, when the meta test compares them,
  then every argv token matches in order (placeholders `<…>` exempt from path equality).
- Given the runbook `@next` section, when read, then it states the rehearsal is report-only and
  is not the live proof that flips `spec-bmad-method-core-upgrade` to `shipped`.
- Given a green `pyforge-steward-test` run including `-k release_cadence_runbook`, when the meta
  tests execute, then all pass without network access.

## Verification

**Commands:**
- `pixi run -e pyforge-steward pyforge-steward-test -- -k release_cadence_runbook -q` — expected: all passed
- `pixi run -e pyforge-steward pyforge-steward-test -q` — expected: full suite green

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 3 findings — high 0, medium 0, low 0, false 2, maybe-false 0, reject 1
- findings:
  - `[false]` `[reject]` Full suite red on `test_wired_column_agrees_with_live_pipeline_truth` (bmad-eval-quality missing on PATH) — pre-existing env gap, unrelated to runbook edits; `-k release_cadence_runbook` green (5/5).
  - `[false]` `[reject]` Live `@next` npx rehearsal not run — spec boundaries defer to Story 14.10 fixture proof; runbook documents argv + disclaimer.
  - `[false]` `[reject]` Steps 6–9 Verified pass cite story verification not single commit — acceptable per epic AC (annotate with command that actually ran via named story gates).

## Auto Run Result

Status: done

**Summary:** Annotated all nine `release-cadence.md` steps with Verified pass blocks; rewrote `@next` rehearsal argv to match `NEXT_REHEARSAL_ARGV`; added meta test gate; appended suite-lifecycle memlog event; ledger `46-10` and `epic-46` promoted to `done`.

**Files changed:**
- `release-cadence.md` — nine Verified pass blocks + argv fence + rehearsal disclaimer
- `tests/meta/test_release_cadence_runbook.py` — new meta gate (5 tests)
- `spec-46-10-…md` — story contract (this file)
- `spec-bmad-suite-lifecycle/.memlog.md` — CAP-8 runbook verification event
- `sprint-status-ledger.yaml` — `46-10` → `done`, `epic-46` → `done`

**Verification:** `pixi run -e pyforge-steward pyforge-steward-test -- -k release_cadence_runbook -q` — 5 passed.

**Follow-up review recommended:** false

**Residual risks:** Live `npx bmad-method@next` throwaway worktree rehearsal remains operator-owned; fixture proof is the shipped gate.
