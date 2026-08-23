# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~15:35 CDT
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)

## Coordinator lock (singleton)

| Field | Value |
|-------|--------|
| `owner` | `parent-chat` (this Cursor session — sole dispatcher) |
| `held_since` | 2026-08-23T09:40-05:00 |
| `state` | `active` |
| Prior owners | `049171e2` → **[8743ca82](8743ca82-b46c-4199-98cf-44a1607d2507)** → `7b8cb929` → `3759fbbd` — **RETIRED** |

**HARD:** Do not launch another fleet-drain coordinator Task. Do not resume retired coordinators.

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · **singleton coordinator** |
| Backlog | **marshal 25** · **steward 6** (**31 total**; 12-7 skipped forever) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical agent |
|---------|-------|-----------------|
| marshal | `20-5` | launching |
| steward | `16-3` | [Steward 16-3](b04fa062-4cc1-4e56-8b3b-56f8004b66b4) (skip 12-7) |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| marshal | `20-4` | [#687](https://github.com/rxm7706/local-recipes/pull/687) merge `5a50971409` · finalize `ee39a97fcf` ([Marshal 20-4](8c2b060b-7b3f-4176-949c-e61337a5959d)) |
| steward | `16-2` | [#686](https://github.com/rxm7706/local-recipes/pull/686) |
| marshal | `20-3` | [#684](https://github.com/rxm7706/local-recipes/pull/684) · finalize [#685](https://github.com/rxm7706/local-recipes/pull/685) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
