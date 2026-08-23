# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 (coordinator resume)  
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · coordinator **resumed** |
| Backlog | **marshal 44** · **steward 21** (**65 total**) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight (wave 5)

| Station | Story | Branch |
|---------|-------|--------|
| marshal | `12-4` | `marshal/12-4-pattern-meta-tests` |
| steward | `12-9` | `steward/12-9-ocp-portability` (12-7 skipped) |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP cluster — re-queue when CRC available |

## Session merges (#641–#647)

marshal 11-6, 12-1, 12-2, 12-3 · steward 12-5, 12-6, 12-8

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
