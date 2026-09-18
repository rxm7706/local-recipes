---
title: '19.2: One real ship records itself against a persistent store'
type: 'feature'
created: '2026-09-18'
status: 'blocked'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred:
  - 'DW-13-6-1: `steward deploy perimeter` renders only a hardcoded `myproject.asgi:application` (`steward/deploy.py:484`) with no `--asgi-application` flag. This story names the host it used or stays explicitly foundry-side and blocked on the cutover giving Herald a perimeter — it never closes on a throwaway store.'
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Epic 13 closed 6/6 `done` while `herald-live-demo.yml` is `disabled_manually` with 100 failed runs and zero successes (last run 2026-08-24). Its own header declares it "never a persistent, publicly-reachable deployment" and writes to a `runner.temp` DB discarded when the job ends — so a ship has never recorded itself.

**Approach:** Deliver one real ship event to the webhook against a store that survives the process. The progress record exists in that store after the process exits, is readable by `herald progress`, and the run is cited by evidence (run id or store path) in this story's completion note.

## Boundaries & Constraints

**Always:**
- The store is a persistent path or a provisioned DB — never `${{ runner.temp }}`.
- Hosting is honest about its blocker: either name the host used, or stay explicitly `foundry-side` and blocked on the cutover giving Herald a perimeter.
- HMAC verification and webhook handler behavior stay the Story 19.1 seam.

**Never:**
- Never close this story on a throwaway store.
- Never flip this ledger key off `blocked` from this mint — the row stays `blocked` until the operator confirms the host/cutover.
- Never enable `herald-live-demo.yml` as the success signal for a `runner.temp` store.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| real ship | signed event against a surviving store | progress row readable by `herald progress` after process exit | cite run id or store path |
| throwaway store | `${{ runner.temp }}` / job-local DB | refuse as success | story stays open/blocked |
| no perimeter | steward deploy cannot name Herald ASGI | remain `blocked` / foundry-side | DW-13-6-1 |

</intent-contract>

## Binding

Parent Spec capability: `spec-herald-moments-2-4-live-backend` LB-2 / LB-3; Epic 13's success signal; unifying-strategy batch rows C6, C11.
Surface: `src/shared/packages/pyforge-herald/src/pyforge/herald/{webhook.py,webhook_host.py,scheduler.py,db.py,locking.py}`, the persistent store (never `${{ runner.temp }}`), `HERALD_WEBHOOK_SECRET` provisioning, the host that actually runs the listener.
Deps: S-19.1.
Ledger key: `19-2-one-real-ship-records-itself-against-a-persistent-store`.
Minted 2026-09-18 from `epics.md` (Intent + ACs only) so the filename matches CHAIN-STANDARD §5 (`spec-` + ledger key). Ledger status remains `blocked`; this file does not flip it.
