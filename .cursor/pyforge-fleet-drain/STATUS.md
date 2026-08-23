# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~11:16 CDT  
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
| Backlog | **marshal 34** · **steward 14** (**48 total**; 12-7 skipped) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical PR / agent |
|---------|-------|----------------------|
| marshal | `18-2` | [Marshal 18-2](e4dc56cf-2ccc-46bd-b344-6d32050aed43) — parity + coverage gates |
| steward | `14-4` | [Steward 14-4](c2144c44-a067-4a28-84f4-21b0ae234a49) — pin fan-out enum (skip 12-7) |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| steward | `14-3` | [#669](https://github.com/rxm7706/local-recipes/pull/669) merge `e7d2ead159` · finalize (this commit) ([Steward 14-3](dd93a8c7-9027-41b2-821f-f185afdc6992)) |
| marshal | `18-1` | [#668](https://github.com/rxm7706/local-recipes/pull/668) merge `657c6bbe1e` · finalize `4ff73ba127` ([Marshal 18-1](b5923e5a-38cc-4e9c-a635-9a897c3e7d0e)) |
| marshal | `17-4` | [#667](https://github.com/rxm7706/local-recipes/pull/667) |
| steward | `14-2` | [#666](https://github.com/rxm7706/local-recipes/pull/666) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
