---
title: The landing-evidence grammar
type: feature
created: '2026-08-23'
status: ready
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 9b488aee70
---

<intent-contract>

## Intent

**Problem:** FR-191 CAP-1 — doctor, marshal promotion, MRS-STATUS-010, and `marshal retire` each speak a partial landing-evidence dialect, causing false FAILs (marshal 8-2, 10-1, mason 3-7) and 26 UNCONFIRMED warns. Recovery landings (`accc097e6a`, `5290c9bcd2`, `03d8fc8c86`) match no predicate.

**Approach:** Ship ONE shared grammar of landing-evidence shapes (merge-subject templates, branch-name grammars `land/<station>-<story>…` / `bmad-loop/<run>/<story>`, documented recovery-commit convention). Placement is this story's design decision inside the doctor-never-imports-`pyforge.marshal` boundary (contract + conformance test, shared artifact, or `pyforge-core` module). Recognize the three live recovery commits as written or via one-time reviewed allowlist — never history rewrite. Conformance surface both packages test against. Do not implement 20.9–20.10 consumer wiring.

## Acceptance Criteria

- ONE grammar artifact exists covering sanctioned landing paths (subjects, branch names, recovery convention).
- Three recovery commits recognized (exact match or documented allowlist).
- Cross-package conformance tests both marshal and doctor can run without doctor importing `pyforge.marshal`.
- Does not wire doctor `story-status` routes (20.9) or marshal promotion/MRS-STATUS-010/retire (20.10).

## Boundaries & Constraints

**Never:** Doctor imports `pyforge.marshal`. Never rewrite git history. Never implement 20.9–20.10. Finalize marshal ledger only. Do not touch steward 16-5.

</intent-contract>

## Code Map

- Parent: `spec-landing-evidence-grammar/SPEC.md` (CAP-1)
- Grammar home TBD (pyforge-core / shared artifact / contract module)
- Conformance tests importable from doctor + marshal test suites
- Recovery commits: `accc097e6a`, `5290c9bcd2`, `03d8fc8c86`

## Verification

- Conformance matrix: known-good landing shapes parse; recovery commits recognized
- Doctor-side test does not import pyforge.marshal
- Related tests green locally
