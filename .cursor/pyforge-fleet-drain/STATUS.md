# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~08:28 CDT  
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · coordinator ON |
| Backlog | **marshal 43** · **steward 21** (**64 total**) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight

| Station | Story | Status |
|---------|-------|--------|
| marshal | `12-5` | re-dispatched after phantom STATUS entry |
| steward | `13-1` | [#650](https://github.com/rxm7706/local-recipes/pull/650) — CI pending |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — skip until CRC |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| marshal | `12-4` | [#649](https://github.com/rxm7706/local-recipes/pull/649) + harden [#651](https://github.com/rxm7706/local-recipes/pull/651) |
| steward | `12-9` | [#648](https://github.com/rxm7706/local-recipes/pull/648) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
