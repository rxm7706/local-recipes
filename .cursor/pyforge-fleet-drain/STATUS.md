# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~20:35 CDT
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
| Backlog | **marshal 9** · steward **12-7 only** (skipped) — **marshal-only drain** |
| Drained | atlas, doctor, herald, mason, scribe, **steward**, warden |

## Merge policy (operator override — 2026-08-23)

GitHub Actions billing blocks CI. Until restored: **local tests green → `gh pr merge <n> --merge --admin`** (never squash). Document in spec `shipped_ref` + Auto Run Result.

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical agent |
|---------|-------|-----------------|
| marshal | `21-5` | [d20f4848-3b44-40da-8647-80784afb83b3](d20f4848-3b44-40da-8647-80784afb83b3) |

## Dispatch sequencing (operator — 2026-08-23)

**Epic 22 complete.** Epic 21 last story `21-5` in flight → then Epics 23–25.

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged (admin merge, no CI)

| Station | Story | PR |
|---------|-------|-----|
| marshal | `21-4` | [#709](https://github.com/rxm7706/local-recipes/pull/709) merge `584818efcb` ([Marshal 21-4](159c24e8-616a-46b4-b943-0b73908009fb)) · CAP-4 orphan cleanup |
| marshal | `21-3` | [#708](https://github.com/rxm7706/local-recipes/pull/708) merge `765497a06b` ([Marshal 21-3](d30e5dfd-7551-4690-b6ea-d88d275f674f)) · CAP-2 code-status preserve |
| marshal | `21-2` | [#707](https://github.com/rxm7706/local-recipes/pull/707) merge `2710dc06e1` ([Marshal 21-2](36410bee-290d-4f7d-bf29-0fa3ed1faf8a)) · CAP-1 chain-regenerate |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
