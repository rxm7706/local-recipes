---
title: '50.2: A harness''s own usage-wall wording is a transient outcome'
type: 'fix'
created: '2026-09-18'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `classify_session_log` returned `unknown` for `ActionRequiredError: Increase limits for faster responses You're out of usage. Switch to Auto, or ask your admin to increase your limit to continue.` (none of `monthly spend limit` / `spend limit` / `usage limit` / `rate limit` / `quota exceeded` / `insufficient quota` match), so `classify_dispatch_block` returned `terminal` and the drain refused 23.1 until a human re-dispatched it

**Approach:** the marker table recognises `out of usage` and `increase your limit` (Cursor) beside the Claude Code weekly/monthly-limit text already catalogued, keyed per harness in one place

## Boundaries & Constraints

**Always:**
- the fixture classifies `QUOTA_EXCEEDED`, `classify_dispatch_block(session_log=fixture, failed_gate=None, changed_path_count=0)` returns `TRANSIENT`, and `exclude_harness_profiles_after_transient_failure` drops the first preference entry for it
- removing the new markers re-terminalises the fixture (mutation test), and no existing classification changes (the current marker fixtures stay green)

**Never:**
- Do not make the supervisor trust a session's self-report, add a second gate, or re-attribute landed history — the Epic 50 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the 2026-09-18 fixture | the real run/journal named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-245`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_session.py` (`_QUOTA_MARKERS` becomes per-harness and covers Cursor's live text), `.../core/dispatch_retry.py` (no behaviour change expected; covered by test), tests with the real `pyforge-herald-20260918T132400673Z-194af3a0` session log as a fixture.
Ledger key: `50-2-a-harness-s-own-usage-wall-wording-is-a-transient-outcome`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-50-2-a-harness-s-own-usage-wall-wording-is-a-transient-outcome.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- `classify_session_log` on the real `pyforge-herald-20260918T132400673Z-194af3a0` session.log returns `QUOTA_EXCEEDED`; `classify_dispatch_block(..., changed_path_count=0)` returns `TRANSIENT`; removing the marker re-terminalises it.
