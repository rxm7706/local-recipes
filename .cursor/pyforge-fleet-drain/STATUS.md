# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~09:45 CDT  
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)

## Coordinator lock (singleton)

| Field | Value |
|-------|--------|
| `owner` | `parent-chat` (this Cursor session — sole dispatcher) |
| `held_since` | 2026-08-23T09:40-05:00 |
| `state` | `active` |
| Prior owners | `049171e2` → `8743ca82` → `7b8cb929` → `3759fbbd` — **RETIRED** (interrupted 09:42) |

**HARD:** Do not launch another fleet-drain coordinator Task while `state: active`. See [COORDINATOR.md § Singleton lock](./COORDINATOR.md).

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · **singleton coordinator** |
| Backlog | **marshal 38** · **steward 19** (**57 total**; 12-7 skipped) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical PR / agent |
|---------|-------|----------------------|
| steward | `13-3` | [#660](https://github.com/rxm7706/local-recipes/pull/660) · [Steward 13-3](e202173d-b074-4fd8-ad77-61ea7a5179d0) — merge+finalize when CI green |

**HALTed duplicates (do not resume):** [85301175](85301175-9153-4487-9999-574f2927bcd2), [f5c6ec2b](f5c6ec2b-37bf-4345-aca6-ed8522531c1b), [cf7d5e5c](cf7d5e5c-fd6e-4e36-b1f7-cf4f5cda3fc8).

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| steward | `13-2` | [#656](https://github.com/rxm7706/local-recipes/pull/656) |
| marshal | `17-1` | [#661](https://github.com/rxm7706/local-recipes/pull/661) `208093926d3` |
| marshal | `15-2` | [#657](https://github.com/rxm7706/local-recipes/pull/657) canonical · [#658](https://github.com/rxm7706/local-recipes/pull/658)/[#659](https://github.com/rxm7706/local-recipes/pull/659) closed as dups |
| steward | `13-1` | [#650](https://github.com/rxm7706/local-recipes/pull/650) |
| marshal | `15-1` | [#655](https://github.com/rxm7706/local-recipes/pull/655) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
