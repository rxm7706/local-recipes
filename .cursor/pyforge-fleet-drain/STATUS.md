# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23  
**Playbook:** [PLAN.md](./PLAN.md) — **merge-in-agent** fleet-wide (dispatch agent merges when CI green + finalizes own station)  
**Queues:** [queues.yaml](./queues.yaml) (regenerate with `generate-queues.py`)

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` |
| Merge | **`merge_in_agent: true`** (all stations) |
| Auto-coordinator | **ON** — see [COORDINATOR.md](./COORDINATOR.md) |
| Active stations | **marshal**, **steward** |
| Drained (ledger) | atlas, doctor, herald, mason, scribe, warden |

## In-flight dispatches (2026-08-23)

| Station | Story | PR / branch |
|---------|-------|-------------|
| marshal | `12-1` | `marshal/12-1-pixi-wiring` (dispatching) |
| steward | `12-6` | dispatching next |

## Recently merged (2026-08-23)

| Station | Story | PR |
|---------|-------|-----|
| steward | `12-5` | [#640](https://github.com/rxm7706/local-recipes/pull/640) — merge `a16e8686f06` |
| marshal | `11-6` | [#641](https://github.com/rxm7706/local-recipes/pull/641) — merge `e48ea1292d`, finalize `e854930401` |
| marshal | `11-5` | [#639](https://github.com/rxm7706/local-recipes/pull/639) |
| steward | `12-4` | [#638](https://github.com/rxm7706/local-recipes/pull/638) |

## Next queue (after in-flight)

| Station | Next | Remaining |
|---------|------|-----------|
| marshal | `12-2` (after 12-1) | 47 → 46 |
| steward | `12-7` (after 12-6; skip 12-7 if OCP blocked) | 23 → 22 |

## Operator commands

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
pixi run -e local-recipes fleet-picture
gh pr list --repo rxm7706/local-recipes --state open
```
