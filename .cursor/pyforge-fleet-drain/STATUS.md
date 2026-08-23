# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~17:20 CDT
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)

## Coordinator lock (singleton)

| Field | Value |
|-------|--------|
| `owner` | `parent-chat` (this Cursor session — sole dispatcher) |
| `held_since` | 2026-08-23T09:40-05:00 |
| `state` | `active` |
| Prior owners | `049171e2` → `8743ca82` → `7b8cb929` → `3759fbbd` — **RETIRED** |

**HARD:** Do not launch another fleet-drain coordinator Task.

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · **singleton coordinator** |
| Backlog | **marshal 20** · **steward 3** (**23 total**; 12-7 skipped forever) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## Merge policy (operator override — 2026-08-23)

GitHub Actions billing blocks CI. Until restored: **local tests green → `gh pr merge <n> --merge --admin`** (never squash). Document in spec `shipped_ref` + Auto Run Result.

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical agent |
|---------|-------|-----------------|
| marshal | `20-10` | [a791594c-fc51-4ac4-b900-42417dd46de3](a791594c-fc51-4ac4-b900-42417dd46de3) |
| steward | `17-1` | [9a857f04-8492-4d33-948d-f50a44271365](9a857f04-8492-4d33-948d-f50a44271365) (skip 12-7) |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged (admin merge, no CI)

| Station | Story | PR |
|---------|-------|-----|
| steward | `16-5` | [#696](https://github.com/rxm7706/local-recipes/pull/696) merge `eb3ab8c95d` ([Steward 16-5](c761dd9e-227d-4665-ab4f-df178b70d268)) · **Epic 16 done** |
| marshal | `20-9` | [#695](https://github.com/rxm7706/local-recipes/pull/695) merge `047eadf4b2` ([Marshal 20-9](3204d1e5-5e2f-4430-99f9-dff06aff0fe7)) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
