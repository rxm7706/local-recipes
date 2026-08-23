# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~09:45 CDT  
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)

## Coordinator lock (singleton)

| Field | Value |
|-------|--------|
| `owner` | `parent-chat` (this Cursor session — sole dispatcher) |
| `held_since` | 2026-08-23T09:40-05:00 |
| `state` | `active` |
| Prior owners | `049171e2` → `8743ca82` → **[7b8cb929](7b8cb929-8d78-4be6-869f-a1215a578030)** → **[3759fbbd](3759fbbd-db33-4928-a7e1-8297eba3bacd)** — **RETIRED** |

**HARD:** Do not launch another fleet-drain coordinator Task while `state: active`. See [COORDINATOR.md § Singleton lock](./COORDINATOR.md).

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · **singleton coordinator** |
| Backlog | **marshal 38** · **steward 18** (**56 total**; 12-7 skipped) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight

| Station | Story | Status |
|---------|-------|--------|
| — | — | **idle** — ready for next wave under parent-chat only |

## Next (do not dual-dispatch)

| Station | Story | Notes |
|---------|-------|-------|
| marshal | `17-2` | dreams hygiene mode |
| steward | `13-4` | skip `12-7` (live OCP) |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged (consolidation)

| Station | Story | PR |
|---------|-------|-----|
| steward | `13-3` | [#660](https://github.com/rxm7706/local-recipes/pull/660) merge `fd7b36a64e` |
| marshal | `17-1` | [#661](https://github.com/rxm7706/local-recipes/pull/661) merge `208093926d` · finalize `0307597b63` |
| steward | `13-2` | [#656](https://github.com/rxm7706/local-recipes/pull/656) |
| marshal | `15-2` | [#657](https://github.com/rxm7706/local-recipes/pull/657) · dups [#658](https://github.com/rxm7706/local-recipes/pull/658)/[#659](https://github.com/rxm7706/local-recipes/pull/659) closed |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
