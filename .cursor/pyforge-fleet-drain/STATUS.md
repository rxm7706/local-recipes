# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 (wave 7 — marshal 15-1 finalized)  
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · coordinator **active** |
| Backlog | **marshal 40** · **steward 21** (**61 total**; 12-7 skipped) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight

| Station | Story | Status |
|---------|-------|--------|
| steward | `13-1` | [#650](https://github.com/rxm7706/local-recipes/pull/650) — CI after import-linter fix `fbbb4f1907` |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — skip until CRC available |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| marshal | `15-1` | [#655](https://github.com/rxm7706/local-recipes/pull/655) |
| marshal | `12-6` | [#654](https://github.com/rxm7706/local-recipes/pull/654) |
| marshal | `12-5` | [#652](https://github.com/rxm7706/local-recipes/pull/652) + [#653](https://github.com/rxm7706/local-recipes/pull/653) |
| marshal | `12-4` | [#649](https://github.com/rxm7706/local-recipes/pull/649) |
| steward | `12-9` | [#648](https://github.com/rxm7706/local-recipes/pull/648) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
pixi run -e local-recipes gh pr list --repo rxm7706/local-recipes --state open
```
