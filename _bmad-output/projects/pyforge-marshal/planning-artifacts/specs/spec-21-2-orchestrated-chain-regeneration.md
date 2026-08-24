---
title: Orchestrated chain regeneration
type: feature
created: '2026-08-23'
status: ready
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 4eaf2751fc
---

<intent-contract>

## Intent

**Problem:** Regenerating Dream→Spec→Research→Brief→PRD→Architecture→Epics still requires hand-carrying files between BMAD skills (FR-192 CAP-1; spec-fleet-chain-completeness Q1–Q4 now resolved).

**Approach:** Ship `marshal planning chain-regenerate --project <slug> --dream <path>` that orchestrates skills headlessly via the FR-52 harness seam. Default mode **Full** (all eight Dream phases including `bmad-deep-recon` → `bmad-product-brief`). Optional `--minimal` skips Research/Brief. Resume-from-phase journal under `planning-artifacts/.chain-regen/<run-id>/`. Per-invocation `BMAD_ACTIVE_PROJECT` + physical paths (never `scripts/bmad-switch`). Deps: none for CAP-1 core; Q1–Q4 resolved 2026-08-23. Do not implement CAP-2 code-status preservation (21.3), CAP-4 orphan apply (21.4), or CAP-5 parameter polish (21.5) beyond what CAP-1 needs to run.

## Acceptance Criteria

- `marshal planning chain-regenerate` invokes Full phase order: bmad-spec → bmad-deep-recon → bmad-product-brief → bmad-prd → bmad-architecture → bmad-create-epics-and-stories → code-linkage verify (read-only) → orphan **report** (manifest only; apply is 21.4).
- `--minimal` skips phases 2–3.
- Run journal at `planning-artifacts/.chain-regen/<run-id>/state.yaml`; `--resume` continues last incomplete phase; skill `blocked` halts; transient failure retries current phase ≤2×.
- Skills driven through FR-52 harness; memlog-derivation invariant preserved (never hand-overwrite derived artifacts).
- Regeneration output left unstaged; never auto-commit/push.
- Does not implement Stories 21.3–21.5 beyond stub hooks needed for CAP-1.

## Boundaries & Constraints

**Never:** Absorb skill logic. Never `scripts/bmad-switch`. Never auto-commit. Finalize marshal ledger only.

</intent-contract>

## Code Map

- Parent: `spec-fleet-chain-completeness/SPEC.md` (CAP-1; Q1–Q4 resolved)
- `cli/planning.py`, `core/chain_regen.py`, FR-52 harness seam
- Journal under `_bmad-output/projects/<slug>/planning-artifacts/.chain-regen/`
- Tests: Full phase sequence, `--minimal`, resume, blocked halt, no-commit

## Verification

- `pixi run -e pyforge-marshal pyforge-marshal-test` green
- Unit/integration covering phase orchestration + journal resume
