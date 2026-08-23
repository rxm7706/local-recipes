# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~13:15 CDT
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
| Backlog | **marshal 30** · **steward 10** (**40 total**; 12-7 skipped forever) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical agent |
|---------|-------|-----------------|
| marshal | `19-4` | [Marshal 19-4](1ff742ec-f685-4c84-aced-efb1288c24e3) |
| steward | `15-3` | [Steward 15-3](acccef8b-ef1d-49fd-975f-b3a8e73ec953) (skip 12-7) |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| marshal | `19-3` | [#677](https://github.com/rxm7706/local-recipes/pull/677) merge `b1ec8b96ff` · finalize `18221846fd` ([Marshal 19-3](042ec63d-ebc8-4319-843c-928fe42457fb)) |
| steward | `15-2` | [#676](https://github.com/rxm7706/local-recipes/pull/676) |
| steward | `15-1` | [#675](https://github.com/rxm7706/local-recipes/pull/675) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
