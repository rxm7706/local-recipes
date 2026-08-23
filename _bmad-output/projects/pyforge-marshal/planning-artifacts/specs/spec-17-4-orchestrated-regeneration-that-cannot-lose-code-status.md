---
title: Orchestrated regeneration that cannot lose code status
type: feature
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: a38a2dbdfb
---

<intent-contract>

## Intent

**Problem:** Regenerating a project's Dream→Spec→…→epics chain is still manual and fragile (FR-148); a regen can rewrite story keys and lose `done` code-status (FR-149); orphaned specs/epics have no review-gated report path (FR-151). Story 17.3 shipped layer presence only — not orchestration.

**Approach:** Add one marshal CLI/orchestration invocation that regenerates a named project's chain in dependency order, reuses the existing `promote_sprint_status.py` / ledger guard so every `done` story key is byte-identical after regen (only backlog epics may restructure), and reports orphaned specs/epics for review-gated cleanup (nothing deleted without review). Per-project only (AD-72 / FR-152) — never touch another station's tree.

## Acceptance Criteria

- One invocation regenerates a named project's chain in dependency order (FR-148).
- Every story key with `status=done` (or ledger `done`) before regen is byte-identical afterward; only backlog epics may restructure (FR-149) — reuse existing ledger/promote guards, do not invent a second guard.
- Orphaned specs (referencing deleted Dreams) and epics (referencing orphaned specs) are reported; nothing is deleted without review (FR-151).
- Invocable for one named project without mutating another's tree (AD-72).
- Fixture-covered; does not regress Story 17.3 `--layers` audit.

## Boundaries & Constraints

**Never:** Blind-delete orphans. Never rewrite `done` story keys. Never `scripts/bmad-switch`. Finalize marshal ledger only. Surface: new `cli/` verb + `core/` orchestration under pyforge-marshal; may call existing doctor/generate helpers read-only.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/` — new regeneration verb
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/` — orchestration
- `scripts/promote_sprint_status.py` — reuse code-status / ledger guard (do not fork)
- Story 17.3 `chain-completeness --layers` — leave intact; regen may call it for pre/post evidence
- Unit/meta tests under `pyforge-marshal/tests/`

## Verification

- `pixi run --frozen -e pyforge-marshal` relevant unit/meta tests green
- Fixture: done keys preserved across regen; orphans reported not deleted
- CI: detectors, linter, package tests
