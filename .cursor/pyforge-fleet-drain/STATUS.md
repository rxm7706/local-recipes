# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~10:35 CDT  
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)

## Coordinator lock (singleton)

| Field | Value |
|-------|--------|
| `owner` | `parent-chat` (this Cursor session — sole dispatcher) |
| `held_since` | 2026-08-23T09:40-05:00 |
| `state` | `active` |
| Prior owners | `049171e2` → **[8743ca82](8743ca82-b46c-4199-98cf-44a1607d2507)** → `7b8cb929` → `3759fbbd` — **RETIRED** (re-retired 10:28 after zombie resume) |

**HARD:** Do not launch another fleet-drain coordinator Task while `state: active`. Do not resume `8743ca82`.

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · **singleton coordinator** |
| Backlog | **marshal 36** · **steward 16** (**52 total**; 12-7 skipped) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical PR / agent |
|---------|-------|----------------------|
| — | — | marshal **17-3** merged [#665](https://github.com/rxm7706/local-recipes/pull/665) (`f318609126`); next marshal ready: **17-4** |
| steward | `14-2` | [Steward 14-2](54c7190f-d6d1-4225-9eb5-a5864782d7fe) — deliberate branched apply (skip 12-7); worktree `steward-14-2-1787498789` |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| steward | `14-1` | [#664](https://github.com/rxm7706/local-recipes/pull/664) merge `521806b5e2` · finalize `8da99901e7` ([Steward 14-1](12f9accb-11d3-4a00-a38d-36ed37d91009)) |
| marshal | `17-2` | [#663](https://github.com/rxm7706/local-recipes/pull/663) |
| steward | `13-4` | [#662](https://github.com/rxm7706/local-recipes/pull/662) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
