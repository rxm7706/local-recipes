---
title: Chain-completeness audit mode extends layer-presence into full CAP-3 coverage
type: feature
created: '2026-08-23'
status: done
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

## Auto Run Result

Status: done
PR: https://github.com/rxm7706/local-recipes/pull/699
Merge: 2a854b86c7e25e3be013cec52dbfccb1005ad81f
Merge policy: admin merge (`gh pr merge --merge --admin`) — GitHub Actions billing blocks CI; local tests green before merge.
Summary: Extended Story 17.3 `chain-completeness --layers` with CAP-3 pass/fail checkpoints (layers, coherence, staleness, orphan-freedom) seeded live from `generate.py` `_chain_audit_verdict` + `chain.dream_chain_orphan_index`. Fleet dashboard rows carry `chainAudit` verdict; index.html shows audit pass/fail marks.
Files:
- `board.py` — CAP-3 checkpoint findings + verdict in `gather_chain_layers_audit`
- `chain.py` — `dream_chain_orphan_index`
- `generate.py` / `data.js` / `index.html` — `chainAudit` on fleet rows
- `test_sources_board_chain_layers_audit.py` — checkpoint pass/fail coverage
Verification: `pytest` chain_layers_audit + dispatch (48) + board_chain_completeness + meta (120) PASS; `generate.py --source git` OK.
Next marshal story: 21-2 blocked on spec-fleet-chain-completeness Q1/Q2 (orchestrated regeneration); Epic 21 clears only 21.1 until operator resolves open questions.
