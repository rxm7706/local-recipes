# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~19:25 CDT
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
| Backlog | **marshal 12** · steward **12-7 only** (skipped) — **marshal-only drain** |
| Drained | atlas, doctor, herald, mason, scribe, **steward**, warden |

## Merge policy (operator override — 2026-08-23)

GitHub Actions billing blocks CI. Until restored: **local tests green → `gh pr merge <n> --merge --admin`** (never squash). Document in spec `shipped_ref` + Auto Run Result.

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical agent |
|---------|-------|-----------------|
| marshal | `21-2` | launching |

## Dispatch sequencing (operator — 2026-08-23)

**Epic 22 complete** (22-1…22-6). Now Epic 21 regen: `21-2` → `21-3` → `21-4` → `21-5`, then Epics 23–25.

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged (admin merge, no CI)

| Station | Story | PR |
|---------|-------|-----|
| marshal | `22-6` | [#706](https://github.com/rxm7706/local-recipes/pull/706) merge `b38604e61d` ([Marshal 22-6](13ea872d-0166-46df-883d-ece717cb2f5c)) · **Epic 22 done** |
| marshal | `22-5` | [#705](https://github.com/rxm7706/local-recipes/pull/705) merge `11c32c673c` ([Marshal 22-5](e9beb5c8-fad9-41b4-b0f9-b0535a1cbab5)) · CAP-5 in-flight guard |
| marshal | `22-4` | [#704](https://github.com/rxm7706/local-recipes/pull/704) merge `b4c32b80df` ([Marshal 22-4](8dc548b0-8f8a-40dc-8a00-861dfa13f337)) · CAP-4 land path |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
