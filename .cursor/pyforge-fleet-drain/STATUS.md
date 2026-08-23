# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~08:18 CDT  
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · **coordinator ON** |
| Backlog | **marshal 43** · **steward 21** (**64 total**; 12-7 skipped) |
| Drained | atlas, doctor, herald, mason, scribe, warden |
| `main` | `b8d60003b5` (12-4 finalize) |

## In-flight

| Station | Story | Status |
|---------|-------|--------|
| marshal | `12-5` | [Marshal 12-5](17123367-7ec1-4843-a9f7-3ea61ea3888e) dispatched — `marshal/12-5-cli-contract-gates` |
| steward | `13-1` | Impl done in worktree; review/PR in progress ([10f81195](10f81195-3bf7-450c-99b6-8757cb9916a5)) |
| coordinator | drain loop | [7b8cb929](7b8cb929-8d78-4be6-869f-a1215a578030) |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| marshal | `12-4` | [#649](https://github.com/rxm7706/local-recipes/pull/649) merge `7d4357acab` · finalize `b8d60003b5` |
| steward | `12-9` | [#648](https://github.com/rxm7706/local-recipes/pull/648) |
| marshal | `12-3` | [#647](https://github.com/rxm7706/local-recipes/pull/647) |

## Prep specs ready

- marshal `12-5` · steward `13-2`

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
