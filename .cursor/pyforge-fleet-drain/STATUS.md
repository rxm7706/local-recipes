# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 (auto-coordinator)  
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)  
**Queues:** [queues.yaml](./queues.yaml)

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · auto-coordinator ON |
| Backlog | **marshal 44** · **steward 21** (65 total) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## In-flight (wave 5)

| Station | Story | Branch / agent |
|---------|-------|----------------|
| marshal | `12-4` | `marshal/12-4-pattern-meta-tests` (dispatching) |
| steward | `12-9` | `steward/12-9-ocp-portability` (dispatching) |

## Operator attention

| Item | Detail |
|------|--------|
| steward `12-7` | **Skipped** — live OCP cluster required; re-queue when cluster available |
| marshal `12-2` K-02 | Slow oracle fails on `main` (21 adopt actions + symlink preconditions); recorded in spec `deferred` + `followup_review_recommended: true` — not a re-dispatch of 12-2 |

## Merged this session (2026-08-23)

| Station | Story | PR |
|---------|-------|-----|
| marshal | `12-3` | [#647](https://github.com/rxm7706/local-recipes/pull/647) |
| steward | `12-8` | [#646](https://github.com/rxm7706/local-recipes/pull/646) |
| marshal | `12-2` | [#645](https://github.com/rxm7706/local-recipes/pull/645) |
| steward | `12-6` | [#644](https://github.com/rxm7706/local-recipes/pull/644) |
| marshal | `12-1` | [#643](https://github.com/rxm7706/local-recipes/pull/643) (dup #642 closed) |
| steward | `12-5` | [#640](https://github.com/rxm7706/local-recipes/pull/640) |
| marshal | `11-6` | [#641](https://github.com/rxm7706/local-recipes/pull/641) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
pixi run -e local-recipes gh pr list --repo rxm7706/local-recipes --state open
```
