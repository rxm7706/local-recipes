# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~11:12 CDT  
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)

## Coordinator lock (singleton)

| Field | Value |
|-------|--------|
| `owner` | `parent-chat` (this Cursor session — sole dispatcher) |
| `held_since` | 2026-08-23T09:40-05:00 |
| `state` | `active` |
| Prior owners | `049171e2` → **[8743ca82](8743ca82-b46c-4199-98cf-44a1607d2507)** → `7b8cb929` → `3759fbbd` — **RETIRED** |

**HARD:** Do not launch another fleet-drain coordinator Task while `state: active`. Do not resume `8743ca82`.

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · **singleton coordinator** |
| Backlog | **marshal 34** · **steward 15** (**49 total**; 12-7 skipped) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical agent |
|---------|-------|-----------------|
| steward | `14-3` | [Steward 14-3](dd93a8c7-9027-41b2-821f-f185afdc6992) — clobbered custom re-apply (skip 12-7) |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| marshal | `18-1` | [#668](https://github.com/rxm7706/local-recipes/pull/668) merge `657c6bbe1e` · finalize `4ff73ba127` |
| marshal | `17-4` | [#667](https://github.com/rxm7706/local-recipes/pull/667) merge `7aa120fe86` · finalize `3dd4e0a277` ([Marshal 17-4](632da240-9d79-443e-987f-e78b82e17f93)) |
| steward | `14-2` | [#666](https://github.com/rxm7706/local-recipes/pull/666) merge `3f58e30916` · finalize `76df1d3388` ([Steward 14-2](54c7190f-d6d1-4225-9eb5-a5864782d7fe)) |
| marshal | `17-3` | [#665](https://github.com/rxm7706/local-recipes/pull/665) |
| steward | `14-1` | [#664](https://github.com/rxm7706/local-recipes/pull/664) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
