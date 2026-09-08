---
name: sprint-change-proposal-2026-08-24-operating-model
type: sprint-change-proposal
status: approved
created: '2026-08-24'
scope: pyforge-unifying-strategy operating-model Q1–Q8 — pyforge-scribe (planning-only)
approach: Direct Adjustment
---

# Sprint Change Proposal — Operating-model obligations (pyforge-scribe)

## 1. Issue summary

**Trigger:** Operator revisit of steward SCP §6, then a further bind:
**hooks and plugins are an architecture principle** (canopy:AD-21). As far as
possible every layer is replaceable — process-owned hook specs; plugins that
implement or replace a layer without a fork. Kedro *names* the split; it does
not require a Kedro project. OM Nevers still apply to every station. **Warden
owns** PR-gate hook specifications (Q8); scanner plugins *implement* them.
Every station owns its process hooks and must not publish a competing PR
verdict.

**This pass:** append `## Operating-model obligations (2026-08-24)` to `epics.md`
and `DW-OM-2026-08-24` to the deferred-work ledger. **No new station epic.**

## 2. Impact

- Existing station epics: unchanged.
- Canopy obligations (2026-08-24): still stand; five-tier rows now read as **03**.
- Steward Epics 18–30: already corrected; this file is the spoke record.

## 3. Approach

Direct Adjustment. Same Phase 5 pattern as the Canopy SCP.

## 4. Station-local

**Scribe-local:** Graph-store / recall-backend plugins are station hooks. Memory completeness is not a PR quality gate. CAP-14 backing-store work is unchanged.

## 5. Approval

Approved with the operator revisit (2026-08-24): all eight stations, not Warden-only.
