# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~15:20 CDT
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
| Backlog | **marshal 26** · **steward 6** (**32 total**; 12-7 skipped forever) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical agent |
|---------|-------|-----------------|
| marshal | `20-4` | [Marshal 20-4](8c2b060b-7b3f-4176-949c-e61337a5959d) |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| steward | `16-2` | [#686](https://github.com/rxm7706/local-recipes/pull/686) merge `6e157b892b` |
| marshal | `20-3` | [#684](https://github.com/rxm7706/local-recipes/pull/684) merge `b0c10436ec` · finalize [#685](https://github.com/rxm7706/local-recipes/pull/685) `68687966e1` · upstream [bmad-loop#701](https://github.com/bmad-code-org/bmad-loop/issues/701) ([Marshal 20-3](369a274f-e5e1-407e-949a-6603a1215b29)) |
| marshal | `20-2` | [#683](https://github.com/rxm7706/local-recipes/pull/683) |
| steward | `16-1` | [#682](https://github.com/rxm7706/local-recipes/pull/682) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
