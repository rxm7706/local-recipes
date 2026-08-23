# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~11:36 CDT  
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
| Backlog | **marshal 33** · **steward 13** (**46 total**; 12-7 skipped) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical agent |
|---------|-------|-----------------|
| marshal | `19-1` | [Marshal 19-1](4bbb6333-a1b5-4960-bb11-4371e149233a) — test-architecture generator |
| steward | `14-5` | [Steward 14-5](e91a99ad-f418-4fa1-92e0-f0f27ad4e705) — prove upgrade landed (skip 12-7) |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| marshal | `18-2` | [#671](https://github.com/rxm7706/local-recipes/pull/671) merge `d6f562df4b` · finalize `e163eb9216` ([Marshal 18-2](e4dc56cf-2ccc-46bd-b344-6d32050aed43)) |
| steward | `14-4` | [#670](https://github.com/rxm7706/local-recipes/pull/670) merge `b9f1000a67` · finalize `667ed9003f` ([Steward 14-4](c2144c44-a067-4a28-84f4-21b0ae234a49)) |
| steward | `14-3` | [#669](https://github.com/rxm7706/local-recipes/pull/669) |
| marshal | `18-1` | [#668](https://github.com/rxm7706/local-recipes/pull/668) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
