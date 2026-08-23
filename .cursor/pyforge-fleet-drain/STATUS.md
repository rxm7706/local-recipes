# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~08:12 CDT  
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · **coordinator RESUMED** |
| Backlog | **marshal 44** · **steward 21** (**65 total**; 12-7 skipped) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight (wave resume)

| Station | Story | PR / branch | Agent |
|---------|-------|-------------|-------|
| marshal | `12-4` | [#649](https://github.com/rxm7706/local-recipes/pull/649) `marshal/12-4-pattern-meta-tests` | CI pending merge |
| steward | `13-1` | `steward/13-1-workspace-verbs` (worktree `local-recipes-wt-steward-13-1`) | [10f81195](10f81195-3bf7-450c-99b6-8757cb9916a5) → nested [2a8ad409](2a8ad409-2f0e-4d32-9caa-8cdb4c65dd88) |
| coordinator | drain loop | — | [7b8cb929](7b8cb929-8d78-4be6-869f-a1215a578030) |

## Prep specs (ready on main)

| Station | Story | Spec |
|---------|-------|------|
| marshal | `12-5` | `spec-12-5-cli-contract-idempotence-harness-and-performance-gates.md` |
| steward | `13-2` | `spec-13-2-status-and-the-feed-mirror-decision.md` |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| steward | `12-9` | [#648](https://github.com/rxm7706/local-recipes/pull/648) |
| marshal | `12-3` | [#647](https://github.com/rxm7706/local-recipes/pull/647) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
