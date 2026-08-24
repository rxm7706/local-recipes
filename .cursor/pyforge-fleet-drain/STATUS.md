# PyForge fleet drain — status snapshot

**Updated:** 2026-08-24 ~00:10 CDT
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
| Backlog | **marshal 5** · steward **12-7 only** (skipped) — **marshal-only drain** |
| Drained | atlas, doctor, herald, mason, scribe, **steward**, warden |

## Merge policy (operator override — 2026-08-23)

GitHub Actions billing blocks CI. Until restored: **local tests green → `gh pr merge <n> --merge --admin`** (never squash). Document in spec `shipped_ref` + Auto Run Result.

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical agent |
|---------|-------|-----------------|
| marshal | `24-1` | [1ca7ee92-378c-4a36-8279-85f0b97426d9](1ca7ee92-378c-4a36-8279-85f0b97426d9) |

## Dispatch sequencing (operator — 2026-08-24)

**Epic 23 complete.** Epic 24 sequential: `24-1` → `24-2` → `24-3` → then Epic 25 (`25-6`, `25-7`).

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged (admin merge, no CI)

| Station | Story | PR |
|---------|-------|-----|
| marshal | `23-3` | [#716](https://github.com/rxm7706/local-recipes/pull/716) merge `e47efc11e19` ([Marshal 23-3](e6c7ce15-f86c-4100-9174-1e8bda9eda7f)) · **Epic 23 done** |
| marshal | `23-2` | [#714](https://github.com/rxm7706/local-recipes/pull/714) merge `6488062c31` ([Marshal 23-2 retry](370ff5d0-3984-4727-aab9-43e703653012)) |
| marshal | `23-1` | [#711](https://github.com/rxm7706/local-recipes/pull/711) merge `fbe1bc935a` |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
