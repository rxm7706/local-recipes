# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~08:05 CDT  
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · **coordinator RESUMED** |
| Backlog | **marshal 44** · **steward 21** (**65 total**; 12-7 skipped) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight (wave resume)

| Station | Story | Branch |
|---------|-------|--------|
| marshal | `12-4` | `marshal/12-4-pattern-meta-tests` |
| steward | `13-1` | `steward/13-1-workspace-verbs` (12-7 skipped; 12-9 finalized) |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — re-queue when CRC available |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| steward | `12-9` | [#648](https://github.com/rxm7706/local-recipes/pull/648) — finalize on this commit wave |
| marshal | `12-3` | [#647](https://github.com/rxm7706/local-recipes/pull/647) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
