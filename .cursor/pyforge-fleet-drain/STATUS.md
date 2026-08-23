# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23  
**Playbook:** [PLAN.md](./PLAN.md) — **merge-in-agent** fleet-wide (dispatch agent merges when CI green + finalizes own station)  
**Queues:** [queues.yaml](./queues.yaml) (regenerate with `generate-queues.py`)

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` |
| Merge | **`merge_in_agent: true`** (all stations) |
| Active stations | **marshal**, **steward** |
| Drained (ledger) | atlas, doctor, herald, mason, scribe, warden |

## In-flight dispatches (2026-08-23)

| Station | Story | Agent |
|---------|-------|--------|
| marshal | `11-5` | merge + finalize per PLAN Phase 3 when CI green |

## Recently merged (this session)

| Station | Story | PR |
|---------|-------|-----|
| steward | `12-4` | [#638](https://github.com/rxm7706/local-recipes/pull/638) — merge `3773229684` |

## Next queue after in-flight land

| Station | Next | Remaining |
|---------|------|-----------|
| marshal | `11-6` (after 11-5) | 49 → 48 |
| steward | `12-5` | 24 |

## Operator commands

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
pixi run -e local-recipes fleet-picture
```
