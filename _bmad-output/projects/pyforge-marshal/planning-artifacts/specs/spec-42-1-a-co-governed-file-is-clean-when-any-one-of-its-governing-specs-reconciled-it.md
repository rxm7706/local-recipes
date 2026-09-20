---
title: '42.1: a co-governed file is clean when any one of its governing specs reconciled it'
type: 'feature'
created: '2026-09-16'
status: 'done'
baseline_revision: 'a799295fd6'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** spec-surface-check judged each governing spec independently, so a kernel spec stayed red after a narrower spec already named the same path.

**Approach:** Group _drift_findings by path and OR the existing clean-pass bar (memlog moved AND names the path) across co-governors.

</intent-contract>

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `6247c168ee` (2026-09-02, "steward: Story 42.1 follow-up review — widen the sidecar hop's failure catch"); also `1cbcc78637` (2026-09-02, "steward: Story 42.1 — MCP transport authorization and a streaming proxy"). Ledger row `42-1-a-co-governed-file-is-clean-when-any-one-of-its-governing-specs-reconciled-it: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-42-1-mcp-transport-authorization.md`, `src/platform/tests/test_mcp_transport_auth.py`, `src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
