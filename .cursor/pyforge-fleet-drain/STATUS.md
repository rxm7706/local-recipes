# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~09:35 CDT  
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · coordinator ON |
| Backlog | **marshal 39** · **steward 19** (**58 total**; 12-7 skipped) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight

| Station | Story | Status |
|---------|-------|--------|
| marshal | `17-1` | dispatching after spec commit |
| steward | `13-3` | dispatching after spec commit (12-7 skipped) |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — skip until CRC |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| steward | `13-2` | [#656](https://github.com/rxm7706/local-recipes/pull/656) merge `89724f0a70` |
| marshal | `15-2` | [#657](https://github.com/rxm7706/local-recipes/pull/657) merge `7c126bc39d` |
| steward | `13-1` | [#650](https://github.com/rxm7706/local-recipes/pull/650) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
export PATH="$PWD/.pixi/envs/local-recipes/bin:$PATH"
gh pr list --repo rxm7706/local-recipes --state open
```
