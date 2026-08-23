---
title: The dreams hygiene mode exists
type: feature
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: df8c8a546f
---

<intent-contract>

## Intent

**Problem:** The `--dreams` hygiene mode promised by the 2026-07-23 restructure (FR-147 / `spec-dream-to-code-model-self-verification` capability 4) does not exist; Dream-tier hygiene checks (vocab, table sync, realization-log presence / per-Dream frontmatter validity) still run by hand.

**Approach:** Add a read-only dreams-hygiene mode on the doctor dream-chain surface that reports Dream-tier hygiene findings. Boundary (fixed in the parent Spec): hygiene = per-Dream-file frontmatter validity (`status` from README vocabulary, `owner:` in known station set or `guild`, `title:` present) plus the epic's Phase-2b checks (vocab, table sync, realization-log presence) — distinct from chain completeness (INV-1/2/3). Fixture-covered from day one.

## Acceptance Criteria

- A dreams-hygiene mode exists and is invocable (CLI spelling may be `--dreams` or folded into `--inv` as a fourth value — pick one, document it).
- Reports Dream-tier hygiene findings: frontmatter validity (status vocab, owner in station/`guild`, title present) and Phase-2b hygiene (vocab / table sync / realization-log presence as applicable).
- Distinct from chain-completeness INV-1/2/3 — does not reimplement those checks.
- Fixture suite covers the mode from day one (no untested ship).

## Boundaries & Constraints

**Never:** Change INV-1/2/3 semantics. Never mutate the live Dream tree in tests (temp fixtures only). Detectors stay stdlib + PyYAML if implemented in detector scripts. Surface: `pyforge.doctor.sources` (dream-chain) / related CLI. Finalize marshal ledger only (doctor code surface).

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/` — dream-chain source + hygiene mode
- Doctor CLI / `dream_chain_check` (or equivalent) — mode invocation
- Fixture tests under `pyforge-doctor/tests/`
- Parent: `spec-dream-to-code-model-self-verification/SPEC.md` capability 4

## Verification

- `pixi run --frozen -e pyforge-doctor` established doctor test task / targeted pytest for the new mode
- Live conformant tree: no new findings vs baseline for already-valid Dreams
