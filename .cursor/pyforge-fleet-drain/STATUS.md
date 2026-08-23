# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~16:30 CDT
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
| Backlog | **marshal 23** · **steward 5** (**28 total**; 12-7 skipped forever) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical agent |
|---------|-------|-----------------|
| marshal | `20-7` | launching |
| steward | `16-4` | [Steward 16-4](cb73af2f-982d-4638-9f98-fda65b7ff656) (skip 12-7) |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| marshal | `20-6` | [#691](https://github.com/rxm7706/local-recipes/pull/691) merge `54425c84f4` · finalize `049c416ca6` ([Marshal 20-6](d7bc992e-eb0e-4b66-8bd4-625a89e8b4fe)) |
| steward | `16-3` | [#688](https://github.com/rxm7706/local-recipes/pull/688) merge `b0782c48b4` · finalize `0e1a41be0f` ([Steward 16-3](b04fa062-4cc1-4e56-8b3b-56f8004b66b4)) |
| marshal | `20-5` | [#689](https://github.com/rxm7706/local-recipes/pull/689) · finalize [#690](https://github.com/rxm7706/local-recipes/pull/690) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
