# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~12:05 CDT
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
| Backlog | **marshal 32** · **steward 12** (**44 total**; 12-7 skipped forever) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical agent |
|---------|-------|-----------------|
| marshal | `19-2` | launching |
| steward | `15-1` | launching (skip 12-7) |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| marshal | `19-1` | [#673](https://github.com/rxm7706/local-recipes/pull/673) merge `48423b19b7` · finalize `89896c9458` ([Marshal 19-1](4bbb6333-a1b5-4960-bb11-4371e149233a)) |
| steward | `14-5` | [#672](https://github.com/rxm7706/local-recipes/pull/672) finalize `48ec846f71` |
| marshal | `18-2` | [#671](https://github.com/rxm7706/local-recipes/pull/671) |
| steward | `14-4` | [#670](https://github.com/rxm7706/local-recipes/pull/670) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
