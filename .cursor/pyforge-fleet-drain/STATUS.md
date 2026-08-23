# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~12:30 CDT
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
| Backlog | **marshal 31** · **steward 12** (**43 total**; 12-7 skipped forever) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical agent |
|---------|-------|-----------------|
| marshal | `19-3` | launching |
| steward | `15-1` | [Steward 15-1](635f8c65-d9d8-462a-b658-6d837bb74862) · [#675](https://github.com/rxm7706/local-recipes/pull/675) (skip 12-7) |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| marshal | `19-2` | [#674](https://github.com/rxm7706/local-recipes/pull/674) merge `a132b8b7b2` · finalize `15c004c4c2` ([Marshal 19-2](fe84e424-0f33-4d6b-9de2-4bcad6dfab26)) |
| marshal | `19-1` | [#673](https://github.com/rxm7706/local-recipes/pull/673) |
| steward | `14-5` | [#672](https://github.com/rxm7706/local-recipes/pull/672) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
