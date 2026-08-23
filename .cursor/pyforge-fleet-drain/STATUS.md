# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 (wave 8 — marshal 15-2 finalized)  
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · coordinator **active** |
| Backlog | **marshal 39** · **steward 20** (**59 total**; 12-7 skipped) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight

| Station | Story | Status |
|---------|-------|--------|
| steward | `13-2` | [#656](https://github.com/rxm7706/local-recipes/pull/656) — CI / merge pending |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — skip until CRC available |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| marshal | `15-2` | [#657](https://github.com/rxm7706/local-recipes/pull/657) merge `7c126bc39de` |
| steward | `13-1` | [#650](https://github.com/rxm7706/local-recipes/pull/650) merge `ce08ef4218` |
| marshal | `15-1` | [#655](https://github.com/rxm7706/local-recipes/pull/655) |
| marshal | `12-6` | [#654](https://github.com/rxm7706/local-recipes/pull/654) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
pixi run -e local-recipes gh pr list --repo rxm7706/local-recipes --state open
```
