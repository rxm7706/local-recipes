# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~14:40 CDT
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
| Backlog | **marshal 27** · **steward 7** (**34 total**; 12-7 skipped forever) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical agent |
|---------|-------|-----------------|
| marshal | `20-3` | [Marshal 20-3](369a274f-e5e1-407e-949a-6603a1215b29) |
| steward | `16-2` | [Steward 16-2](320ec42e-8ae9-4950-861c-41b8e7e2c336) (skip 12-7) |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| marshal | `20-2` | [#683](https://github.com/rxm7706/local-recipes/pull/683) merge `d12779380c` · finalize `96c0678145` ([Marshal 20-2](cac55d3b-b3aa-446a-b852-5916494676b8)) |
| steward | `16-1` | [#682](https://github.com/rxm7706/local-recipes/pull/682) merge `bec9707bf8` · finalize `6044d2bef4` ([Steward 16-1](348b627d-3cea-42ad-b97c-e63cc04e877f)) |
| steward | `15-4` | [#681](https://github.com/rxm7706/local-recipes/pull/681) |
| marshal | `20-1` | [#680](https://github.com/rxm7706/local-recipes/pull/680) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
