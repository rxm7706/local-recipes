---
title: Chain-completeness audit mode extends layer-presence into full CAP-3 coverage
type: feature
created: '2026-08-23'
status: ready
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: a9ed21a903
---

<intent-contract>

## Intent

**Problem:** FR-192 CAP-3 delta — Story 17.3 reports layer presence only; fleet needs coherence/staleness/orphan-freedom verdicts on the dashboard, not terminal-only (spec-fleet-chain-completeness).

**Approach:** Extend 17.3's read-only audit mode: per-station pass/fail per contract checkpoint (coherent, not just present); computed from real artifact presence + cross-references each run (never cached table). Surface verdict on fleet dashboard. Generates/changes nothing. Deps: 17.3 done. Do not implement 21.2–21.5.

## Acceptance Criteria

- Audit extends 17.3 with coherence/staleness/orphan-freedom (not just layer presence).
- Pass/fail per checkpoint derived live (dream_chain_check-equivalent signals).
- Verdict visible on fleet dashboard, not terminal-only.
- Read-only — generates/changes nothing.
- Does not implement orchestrated regeneration (21.2) or other Epic 21 stories.

## Boundaries & Constraints

**Never:** Cached per-station hardcoded tables. Never orchestrate bmad-spec/prd chain (21.2). Finalize marshal ledger only. Do not touch steward 17-2.

</intent-contract>

## Code Map

- Parent: `spec-fleet-chain-completeness/SPEC.md` (CAP-3)
- Extends: 17.3 chain-completeness audit (`pyforge-doctor` / fleet dashboard surface)
- Dashboard: fleet chain-status / chain-completeness verdict surface

## Verification

- Audit mode against live stations returns pass/fail matching manual dream_chain_check
- Dashboard shows verdict
- Related doctor/marshal tests green locally
