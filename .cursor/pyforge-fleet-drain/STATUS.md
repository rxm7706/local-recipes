# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~14:35 CDT
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
| Backlog | **marshal 28** · **steward 8** (**36 total**; 12-7 skipped forever) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical agent |
|---------|-------|-----------------|
| marshal | `20-2` | [Marshal 20-2](cac55d3b-b3aa-446a-b852-5916494676b8) |
| steward | `16-2` | _(ready — next after 16-1 finalize)_ |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged

| Station | Story | PR |
| steward | `16-1` | [#682](https://github.com/rxm7706/local-recipes/pull/682) |
|---------|-------|-----|
| steward | `15-4` | [#681](https://github.com/rxm7706/local-recipes/pull/681) merge `0c04823619` · finalize `4d9c58ae85` · epic-15 done ([Steward 15-4](8b034e60-b98a-4394-81ef-6b34cc91895e)) |
| marshal | `20-1` | [#680](https://github.com/rxm7706/local-recipes/pull/680) merge `3a4a7bd854` · finalize `9ca74754a3` ([Marshal 20-1](a99b474c-bc0d-457d-963c-45e13ad364d6)) |
| marshal | `19-4` | [#679](https://github.com/rxm7706/local-recipes/pull/679) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
