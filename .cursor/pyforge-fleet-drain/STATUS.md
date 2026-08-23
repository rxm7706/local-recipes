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

| Station | Story | Branch prefix |
|---------|-------|---------------|
| marshal | `11-6` | `marshal/11-6-seed-explain-and-version` |
| steward | `12-5` | `steward/12-5-dbgpt-sidecar-chart` |

## Recently merged (2026-08-23)

| Station | Story | PR |
|---------|-------|-----|
| marshal | `11-5` | [#639](https://github.com/rxm7706/local-recipes/pull/639) — merge `899bdda78b`, finalize `f8c8df5469` |
| steward | `12-4` | [#638](https://github.com/rxm7706/local-recipes/pull/638) — merge `3773229684` |

## Next queue (after in-flight)

| Station | Next | Remaining |
|---------|------|-----------|
| marshal | `12-1` (after 11-6) | 48 → 47 |
| steward | `12-6` (after 12-5) | 24 → 23 |

## Operator commands

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
pixi run -e local-recipes fleet-picture
gh pr list --repo rxm7706/local-recipes --state open
```
