---
title: '42.2: overlap tolerance narrows a false positive without widening what counts as reconciled'
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

**Problem:** An OR across co-governors could hide a genuine FAIL if a second spec only moved for something else.

**Approach:** Keep the strongest residual severity. Existing single-owner fixtures stay green; a neither-named fixture still finds; mixed never-moved + presumed stays FAIL.

</intent-contract>

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `ec5aed9bb8` (2026-09-02, "steward: Story 42.2 follow-up review — off-loop limiter, terminal-wins revoke, retention chain"); also `a3127dbdb6` (2026-09-02, "steward: Story 42.2 — agent rate limits and run bounds"). Ledger row `42-2-overlap-tolerance-narrows-a-false-positive-without-widening-what-counts-as-reconciled: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-42-2-agent-rate-limits-and-run-bounds.md`, `src/platform/tests/test_agent_rate_limits_and_run_bounds.py`, `src/platform/tests/test_start_get_survives_disconnect.py`, `src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py`, `src/shared/packages/django-pyforge/src/django_pyforge/mcp_start_get.py`, `src/shared/packages/django-pyforge/src/django_pyforge/rate_limit.py`, `src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py`, `src/shared/packages/django-pyforge/src/django_pyforge/tasks.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/revoke.py`, `src/shared/packages/pyforge-steward/tests/unit/test_revoke_duty.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
