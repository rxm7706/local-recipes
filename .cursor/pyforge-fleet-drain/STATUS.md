# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~08:47 CDT  
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · **coordinator ON** |
| Backlog | **marshal 41** · **steward 21** (**62 total**; 12-7 skipped) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight

| Station | Story | Status |
|---------|-------|--------|
| marshal | `15-1` | dispatching — fleet homes refresh |
| steward | `13-1` | [#650](https://github.com/rxm7706/local-recipes/pull/650) — Platform CI fix loop (`67b53a9377`) |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| marshal | `12-6` | [#654](https://github.com/rxm7706/local-recipes/pull/654) finalize `52fbe2fac3` |
| marshal | `12-5` | [#652](https://github.com/rxm7706/local-recipes/pull/652) |
| marshal | `12-4` | [#649](https://github.com/rxm7706/local-recipes/pull/649) |
| steward | `12-9` | [#648](https://github.com/rxm7706/local-recipes/pull/648) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
