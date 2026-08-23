# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 (post 15-2 confirm)  
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · coordinator **active** |
| Backlog | **marshal 39** · **steward 20** (**59 total**; 12-7 skipped) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight

| Station | Story | Status |
|---------|-------|--------|
| marshal | `17-1` | [Marshal 17-1](36704e6f-3115-4629-a10d-904a76397362) dispatched (doctor surface, marshal ledger) |
| steward | `13-2` | [#656](https://github.com/rxm7706/local-recipes/pull/656) — test/detectors/linter green; container jobs pending |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — skip until CRC available |

## Recently merged

| Station | Story | PR |
|---------|-------|-----|
| marshal | `15-2` | [#657](https://github.com/rxm7706/local-recipes/pull/657) merge `7c126bc39de` · finalize `3c0d74fa09` ([Marshal 15-2](b223139e-d4d4-46a9-9081-965fc2d38fac)) — dup #659 closed |
| steward | `13-1` | [#650](https://github.com/rxm7706/local-recipes/pull/650) |
| marshal | `15-1` | [#655](https://github.com/rxm7706/local-recipes/pull/655) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
pixi run -e local-recipes gh pr list --repo rxm7706/local-recipes --state open
```
