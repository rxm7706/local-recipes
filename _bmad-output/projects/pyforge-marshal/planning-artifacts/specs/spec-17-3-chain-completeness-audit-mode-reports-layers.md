---
title: Chain-completeness audit mode reports layers
type: feature
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: f5b1c15e645
---

<intent-contract>

## Intent

**Problem:** Chain-completeness audit (FR-150 residual / `spec-fleet-chain-completeness` CAP-3) and per-project invocation (FR-152; AD-72) are incomplete — operators still hand-check which Dream/Spec/brief/PRD/architecture/epics/stories layers exist.

**Approach:** Add a read-only audit mode on doctor board/chain sources that reports, for a named project, which chain layers exist and which are missing. Seed layer computation from `generate.py`'s existing derivation (never a second derivation). Invocable per-project without touching another's tree.

## Acceptance Criteria

- Read-only mode reports presence/absence of chain layers: Dream, Spec, brief, PRD, architecture, epics, stories (and any other layers the existing `generate.py` computation already names).
- Layer computation is seeded from the existing derivation in dashboard `generate.py` — never a second independent derivation.
- Invocable for one named project without mutating or scanning another project's tree (FR-152).
- Fixture-covered; distinct from dreams-hygiene (`--dreams`) and INV-0..3 semantics.

## Boundaries & Constraints

**Never:** Implement orchestrated regeneration (FR-148 / Story 17.4) or orphan cleanup (FR-151). Never invent a parallel layer graph. Surface: `pyforge.doctor.sources` (board/chain). Finalize marshal ledger only (doctor code surface).

</intent-contract>

## Code Map

- `docs/dashboard/generate.py` — existing layer computation (seed; do not fork)
- `src/shared/packages/pyforge-doctor/` — board/chain sources + CLI mode
- Fixture tests under `pyforge-doctor/tests/`
- Parent: `spec-fleet-chain-completeness/SPEC.md` CAP-3

## Verification

- Targeted doctor pytest for the audit mode + per-project isolation
- Live named-project run reports layers without writing files
