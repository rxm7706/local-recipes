# PyForge fleet drain — status snapshot

**Updated:** 2026-08-24 ~02:00 CDT
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
| Backlog | **marshal 3** · steward **12-7 only** (skipped) — **marshal-only drain** |
| Drained | atlas, doctor, herald, mason, scribe, **steward**, warden |

## Merge policy (operator override — 2026-08-23)

GitHub Actions billing blocks CI. Until restored: **local tests green → `gh pr merge <n> --merge --admin`** (never squash). Document in spec `shipped_ref` + Auto Run Result.

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical agent |
|---------|-------|-----------------|
| marshal | `24-3` | [6f6cbc47-608d-4d14-bd66-795f56adc3eb](6f6cbc47-608d-4d14-bd66-795f56adc3eb) |

## Dispatch sequencing (operator — 2026-08-24)

Epic 24 last story `24-3` in flight → then Epic 25 (`25-6`, `25-7`).

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged (admin merge, no CI)

| Station | Story | PR |
|---------|-------|-----|
| marshal | `24-2` | [#719](https://github.com/rxm7706/local-recipes/pull/719) merge `6e2d536f3f` ([Marshal 24-2](068a887f-c2e2-4cdd-b1c6-2598bcdc304f)) · landing-pass liveness docs |
| marshal | `24-1` | [#718](https://github.com/rxm7706/local-recipes/pull/718) merge `67ae6237a4` · `HarnessPort.engine_liveness` |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
