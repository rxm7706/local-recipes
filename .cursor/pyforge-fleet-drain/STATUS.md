# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 (auto-coordinator)  
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)  
**Queues:** [queues.yaml](./queues.yaml)

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · auto-coordinator ON |
| Backlog | **marshal 45** · **steward 22** (67 total) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight (wave 4)

| Station | Story | Branch / agent |
|---------|-------|----------------|
| marshal | `12-3` | `marshal/12-3-egress-counter` |
| steward | `12-8` | `steward/12-8-github-projects-dlt` (12-7 skipped) |

## Operator skip

| Station | Story | Reason |
|---------|-------|--------|
| steward | `12-7` | Live OCP cluster required — **skipped** per `skip_policies`; re-queue when cluster available |

## Merged this session (2026-08-23)

| Station | Story | PR |
|---------|-------|-----|
| marshal | `12-2` | [#645](https://github.com/rxm7706/local-recipes/pull/645) |
| steward | `12-6` | [#644](https://github.com/rxm7706/local-recipes/pull/644) |
| marshal | `12-1` | [#643](https://github.com/rxm7706/local-recipes/pull/643) (closed dup #642) |
| steward | `12-5` | [#640](https://github.com/rxm7706/local-recipes/pull/640) — rescued ruff E501 |
| marshal | `11-6` | [#641](https://github.com/rxm7706/local-recipes/pull/641) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
pixi run -e local-recipes gh pr list --repo rxm7706/local-recipes --state open
```
