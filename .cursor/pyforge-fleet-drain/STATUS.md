# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~18:00 CDT
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
| Backlog | **marshal 17** · steward **12-7 only** (skipped) — **marshal-only drain** |
| Drained | atlas, doctor, herald, mason, scribe, **steward**, warden |

## Merge policy (operator override — 2026-08-23)

GitHub Actions billing blocks CI. Until restored: **local tests green → `gh pr merge <n> --merge --admin`** (never squash). Document in spec `shipped_ref` + Auto Run Result.

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical agent |
|---------|-------|-----------------|
| marshal | `22-2` | launching |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |
| marshal `21-2`…`21-5` | `spec-fleet-chain-completeness` Q1–Q4 need operator decisions; dispatch **22-2** next |

## Recently merged (admin merge, no CI)

| Station | Story | PR |
|---------|-------|-----|
| marshal | `22-1` | [#701](https://github.com/rxm7706/local-recipes/pull/701) merge `94708563fd` ([Marshal 22-1](4aca90fd-684b-4f22-9fa0-d83a43b91fea)) · `marshal factory dispatch` |
| steward | `17-2` | [#700](https://github.com/rxm7706/local-recipes/pull/700) merge `84d6fb3ad3` ([Steward 17-2](6e832704-9d4f-4aea-8c42-ed5f96f6d300)) · **Epic 17 done · steward drained** |
| marshal | `21-1` | [#699](https://github.com/rxm7706/local-recipes/pull/699) merge `2a854b86c7` ([Marshal 21-1](addb4c0e-f017-4e3c-b652-2394f4c7088f)) · Epic 21 CAP-3 done |
| marshal | `20-10` | [#698](https://github.com/rxm7706/local-recipes/pull/698) merge `1bd2196439` ([Marshal 20-10](a791594c-fc51-4ac4-b900-42417dd46de3)) · **Epic 20 done** |
| steward | `17-1` | [#697](https://github.com/rxm7706/local-recipes/pull/697) merge `551de2ecdd` ([Steward 17-1](9a857f04-8492-4d33-948d-f50a44271365)) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
