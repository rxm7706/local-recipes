# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~21:30 CDT
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
| Backlog | **marshal 7** · steward **12-7 only** (skipped) — **marshal-only drain** |
| Drained | atlas, doctor, herald, mason, scribe, **steward**, warden |

## Merge policy (operator override — 2026-08-23)

GitHub Actions billing blocks CI. Until restored: **local tests green → `gh pr merge <n> --merge --admin`** (never squash). Document in spec `shipped_ref` + Auto Run Result.

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical agent |
|---------|-------|-----------------|
| marshal | `23-2` | [370ff5d0-3984-4727-aab9-43e703653012](370ff5d0-3984-4727-aab9-43e703653012) (retry; prior [d553482b](d553482b-ed82-4027-9dad-e5c0987a110a) resource_exhausted, no PR) |

## Dispatch sequencing (operator — 2026-08-23)

**Epics 21 + 22 complete.** Epic 23: `23-2` → `23-3`, then Epics 24–25.

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged (admin merge, no CI)

| Station | Story | PR |
|---------|-------|-----|
| marshal | `23-1` | [#711](https://github.com/rxm7706/local-recipes/pull/711) merge `fbe1bc935a` ([Marshal 23-1](37fbb462-a605-4fc8-8cce-4bbf6209aafa)) · wall-clock fallback (+ #712/#713 finalize/repair) |
| marshal | `21-5` | [#710](https://github.com/rxm7706/local-recipes/pull/710) merge `3155ec626b` ([Marshal 21-5](d20f4848-3b44-40da-8647-80784afb83b3)) · **Epic 21 done** |
| marshal | `21-4` | [#709](https://github.com/rxm7706/local-recipes/pull/709) merge `584818efcb` ([Marshal 21-4](159c24e8-616a-46b4-b943-0b73908009fb)) · CAP-4 orphan cleanup |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
