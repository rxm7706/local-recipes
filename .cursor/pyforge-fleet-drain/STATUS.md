# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~09:52 CDT  
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)

## Coordinator lock (singleton)

| Field | Value |
|-------|--------|
| `owner` | `parent-chat` (this Cursor session — sole dispatcher) |
| `held_since` | 2026-08-23T09:40-05:00 |
| `state` | `active` |
| Prior owners | `049171e2` → `8743ca82` → `7b8cb929` → `3759fbbd` — **RETIRED** |

**HARD:** Do not launch another fleet-drain coordinator Task while `state: active`. See [COORDINATOR.md](./COORDINATOR.md).

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · **singleton coordinator** |
| Backlog | **marshal 38** · **steward 18** (**56 total**; 12-7 skipped) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical agent |
|---------|-------|-----------------|
| marshal | `17-2` | [Marshal 17-2](1e8346b1-803f-4b53-9b06-e9944e3ec437) — dreams hygiene (doctor surface, marshal ledger) |
| steward | `13-4` | [Steward 13-4](ea53abb8-7969-4281-9d05-ce542faab5c2) — set status + safe teardown |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| marshal | `17-1` | [#661](https://github.com/rxm7706/local-recipes/pull/661) |
| steward | `13-3` | [#660](https://github.com/rxm7706/local-recipes/pull/660) |
| steward | `13-2` | [#656](https://github.com/rxm7706/local-recipes/pull/656) |
| marshal | `15-2` | [#657](https://github.com/rxm7706/local-recipes/pull/657) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
