# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~10:10 CDT  
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)

## Coordinator lock (singleton)

| Field | Value |
|-------|--------|
| `owner` | `parent-chat` (this Cursor session — sole dispatcher) |
| `held_since` | 2026-08-23T09:40-05:00 |
| `state` | `active` |
| Prior owners | `049171e2` → `8743ca82` → `7b8cb929` → `3759fbbd` — **RETIRED** |

**HARD:** Do not launch another fleet-drain coordinator Task while `state: active`.

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · **singleton coordinator** |
| Backlog | **marshal 37** · **steward 17** (**54 total**; 12-7 skipped) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical agent |
|---------|-------|-----------------|
| marshal | `17-3` | [Marshal 17-3](pending) |
| steward | `14-1` | [Steward 14-1](pending) — skip 12-7 |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| steward | `13-4` | [#662](https://github.com/rxm7706/local-recipes/pull/662) merge `a6ad8c4125653efbe9562b6448a84ffb99a43c45` (coordinator rescue-merge; agents stalled) |
| marshal | `17-2` | [#663](https://github.com/rxm7706/local-recipes/pull/663) merge `14b8c06178` · finalize `f5b1c15e64` ([Marshal 17-2](8651f8dc-c0fc-4874-84fe-c1a84d9f56fc)) |
| marshal | `17-1` | [#661](https://github.com/rxm7706/local-recipes/pull/661) |
| steward | `13-3` | [#660](https://github.com/rxm7706/local-recipes/pull/660) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
