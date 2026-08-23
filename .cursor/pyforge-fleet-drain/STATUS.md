# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 (auto-coordinator)  
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)  
**Queues:** [queues.yaml](./queues.yaml)

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · auto-coordinator |
| State | **HALTED** — Cursor monthly usage limit (on-demand quota exhausted) |
| Backlog | **marshal 44** · **steward ~20** (12-9 done; 12-7 still skipped) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## HALT — operator action required

Both wave-5 dispatch agents failed with **Total usage limit reached**:

| Agent | Story | Outcome |
|-------|-------|---------|
| [Marshal 12-4 bmad-build-auto](83ec0282-7fc6-47c0-aaca-efa7a3f6ec58) | `12-4` | Interrupted mid-implementation. WIP on `marshal/12-4-pattern-meta-tests` (`ddc4669f67`) — **not** PR'd / not verified green |
| [Steward 12-9 bmad-build-auto](64f04c43-ca23-45d0-851d-367483c504b0) | `12-9` | **Shipped** — [#648](https://github.com/rxm7706/local-recipes/pull/648) merge `fa1436585c`; finalize already on main (`6e2a0d0133`) despite agent error mid-finalize |

**Resume after quota reset:**

1. Raise Cursor on-demand limit (or wait for monthly reset).
2. Resume marshal 12-4 from `origin/marshal/12-4-pattern-meta-tests` (finish tests → CI → merge → finalize). Do **not** re-dispatch from scratch without checking that branch.
3. Steward next after skip policy: **12-7** needs live OCP, else continue **13-1**.
4. Continue drain until both stations `drained: true`.

## Operator attention (unchanged)

| Item | Detail |
|------|--------|
| steward `12-7` | **Skipped** — live OCP cluster required |
| marshal `12-2` K-02 | Slow oracle deferred in spec |

## Merged this session (2026-08-23)

| Station | Story | PR |
|---------|-------|-----|
| steward | `12-9` | [#648](https://github.com/rxm7706/local-recipes/pull/648) |
| marshal | `12-3` | [#647](https://github.com/rxm7706/local-recipes/pull/647) |
| steward | `12-8` | [#646](https://github.com/rxm7706/local-recipes/pull/646) |
| marshal | `12-2` | [#645](https://github.com/rxm7706/local-recipes/pull/645) |
| steward | `12-6` | [#644](https://github.com/rxm7706/local-recipes/pull/644) |
| marshal | `12-1` | [#643](https://github.com/rxm7706/local-recipes/pull/643) (dup #642 closed) |
| steward | `12-5` | [#640](https://github.com/rxm7706/local-recipes/pull/640) |
| marshal | `11-6` | [#641](https://github.com/rxm7706/local-recipes/pull/641) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
pixi run -e local-recipes gh pr list --repo rxm7706/local-recipes --state open
```
