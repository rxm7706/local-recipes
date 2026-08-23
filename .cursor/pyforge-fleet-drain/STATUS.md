# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~17:20 CDT
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)

## Coordinator lock (singleton)

| Field | Value |
|-------|--------|
| `owner` | `parent-chat` (this Cursor session — sole dispatcher) |
| `held_since` | 2026-08-23T09:40-05:00 |
| `state` | `active` |

**HARD:** Do not launch another fleet-drain coordinator Task.

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · **singleton coordinator** |
| Backlog | **marshal 20** · **steward 4** (**24 total**; 12-7 skipped forever) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## Merge policy (operator override — 2026-08-23)

GitHub Actions billing blocks CI. Until restored: **local tests green → `gh pr merge <n> --merge --admin`** (never squash). Document in spec `shipped_ref` + Auto Run Result.

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical agent |
|---------|-------|-----------------|
| marshal | `20-10` | [a791594c-fc51-4ac4-b900-42417dd46de3](a791594c-fc51-4ac4-b900-42417dd46de3) |
| steward | `16-5` | [c761dd9e-227d-4665-ab4f-df178b70d268](c761dd9e-227d-4665-ab4f-df178b70d268) (skip 12-7) |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged (admin merge, no CI)

| Station | Story | PR |
|---------|-------|-----|
| marshal | `20-9` | [#695](https://github.com/rxm7706/local-recipes/pull/695) merge `047eadf4b2` ([Marshal 20-9](3204d1e5-5e2f-4430-99f9-dff06aff0fe7)) |
| marshal | `20-8` | [#694](https://github.com/rxm7706/local-recipes/pull/694) merge `57ccfe94dc` ([Marshal 20-8](4797d1c3-a04f-4f77-aafb-bbbe1e3c68a7)) |
| steward | `16-4` | [#693](https://github.com/rxm7706/local-recipes/pull/693) merge `b439626af4` ([Steward 16-4](cb73af2f-982d-4638-9f98-fda65b7ff656)) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
