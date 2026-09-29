---
title: 'Verify blast radius is pre-existing-gate, not story-refuse (Story 28.22, Epic 28)'
type: 'feature'
created: '2026-09-01'
status: 'done'
updated: '2026-09-01'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: medium
baseline_revision: 20e88e8b0fd1ccd2cc38101691ac72aeb8df71cc
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-drain-self-resolution/SPEC.md
  - docs/dreams/marshal-dependency-aware-dispatch.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `pyforge-deps-test` collection-failed on pandas in two atlas
packaging tests. 28.13 did not touch those files. `MRS-GATE-001` refused the
story; 28.17 would have redispatched into the same red.

**Approach:** Classify a `verify_commands` failure whose failing files/imports
are outside the story diff and effective surface as `pre-existing-gate`
(WARN). Do not refuse the story. Do not transient-retry that command for this
story. Marshal package tests still refuse marshal diffs.

## Acceptance Criteria

- Given a story diff that does not include the failing packaging test, when
  `pyforge-deps-test` collection-fails on pandas, then verification is not
  `MRS-GATE-001` refuse.
- Given `pyforge-marshal-test` failing on the marshal package, when verify
  runs, then the story is still refused.
- Given a `pre-existing-gate` WARN, when the next drain tick runs, then it
  does not redispatch solely to re-hit the same unrelated command.

## Boundaries & Constraints

**Never:** Skip story-caused red CI. Weaken AD-49 hard scope. `scripts/bmad-switch`.

Ledger key: `28-22-verify-blast-radius-pre-existing-gate`.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_verification.py`
  — `extract_failure_paths_from_verify_output`, `path_in_story_blast_radius`,
  `reclassify_pre_existing_gate_findings`, `MRS-GATE-014` / `pre_existing_gate_finding`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py`
  — call reclassifier after scope check (`scope_check_completed`, not truthy
  `changed_files`)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_retry.py`
  — `MRS-GATE-014` in `_TERMINAL_FAILED_GATES` (no transient redispatch)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py`
  — `_CLASSIFY_TABLE["MRS-GATE-014"] = Verdict.WARN`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py`
  — register `MRS-GATE-014`
- Tests: `tests/unit/test_dispatch_verification.py`, `test_dispatch_hotfix.py`,
  `test_findings.py`

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`

## Review Triage Log

### 2026-09-01 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 1, low 0)
- defer: 0
- reject: 2
- addressed_findings:
  - `[medium]` `[patch]` Reclassification in `dispatch_verify.py` was gated on truthy `changed_files`, skipping doc-only / empty-diff scope results; switched to `scope_check_completed` and added unit test.

## Auto Run Result

Status: done

Summary of implemented change: Verify failures whose extracted paths fall
outside the story diff and effective surface downgrade from `MRS-GATE-001`
(GATE_FAILED / refuse) to `MRS-GATE-014` (WARN / pre-existing-gate).
Independent verification then VERIFIES; drain classifies `MRS-GATE-014` as
terminal so it does not transient-redispatch into the same unrelated command.
Marshal-package verify failures inside blast radius stay `MRS-GATE-001`.

Files changed:
- `core/dispatch_verification.py` — blast-radius helpers + reclassifier
- `dispatch_verify.py` — wire reclassifier after scope check
- `core/dispatch_retry.py` — terminal block for `MRS-GATE-014`
- `core/verdict.py`, `core/findings.py` — register/classify new code
- `tests/unit/test_dispatch_verification.py` — AC fixtures + integration
- `tests/unit/test_dispatch_hotfix.py` — terminal retry classification
- `tests/unit/test_findings.py` — registration parity

Review findings breakdown: 1 patch applied; 0 deferred; 2 rejected (noise:
duplicate registration comment nits).

Follow-up review recommendation: false (0 high patches; medium score 3 < 5).

Verification performed: `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
— 7441 passed, 12 deselected, exit 0 (2026-09-01).

Residual risks: failure-path extraction is best-effort from pytest/pixi output;
unparseable output keeps `MRS-GATE-001` (never weakens on ambiguity).
