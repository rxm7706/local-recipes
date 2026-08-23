# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~09:09 CDT  
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · coordinator ON |
| Backlog | **marshal 40** · **steward 20** (**60 total**; 12-7 skipped) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight

| Station | Story | Status |
|---------|-------|--------|
| marshal | `15-2` | dispatching `marshal/15-2-landing-ledger-staleness` |
| steward | `13-2` | dispatching `steward/13-2-workspace-status` (12-7 skipped) |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — skip until CRC |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| steward | `13-1` | [#650](https://github.com/rxm7706/local-recipes/pull/650) merge `ce08ef4218` |
| marshal | `15-1` | [#655](https://github.com/rxm7706/local-recipes/pull/655) |
| marshal | `12-6` | [#654](https://github.com/rxm7706/local-recipes/pull/654) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
