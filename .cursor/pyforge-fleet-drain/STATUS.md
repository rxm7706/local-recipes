# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23  
**Playbook:** [PLAN.md](./PLAN.md) — **merge-in-agent** fleet-wide  
**Queues:** [queues.yaml](./queues.yaml)

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · auto-coordinator ON |
| Active | **marshal** (46 left), **steward** (23 left) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight

| Station | Story | PR |
|---------|-------|-----|
| marshal | `12-2` | dispatching (`marshal/12-2-empty-plan-oracle`) |
| steward | `12-6` | [#644](https://github.com/rxm7706/local-recipes/pull/644) |

## Recently merged (2026-08-23)

| Station | Story | PR |
|---------|-------|-----|
| steward | `12-5` | [#640](https://github.com/rxm7706/local-recipes/pull/640) — `a16e8686f06` / finalize `30f19c817e` |
| marshal | `12-1` | [#643](https://github.com/rxm7706/local-recipes/pull/643) |
| marshal | `11-6` | [#641](https://github.com/rxm7706/local-recipes/pull/641) |

## Next after in-flight

| Station | Next | Left |
|---------|------|------|
| marshal | `12-3` | 46 → 45 |
| steward | `12-7` (skip→12-8 if OCP blocked) | 23 → 22 |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
